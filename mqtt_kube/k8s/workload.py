import time
import logging

from contextlib import contextmanager

import gevent

import kubernetes
import kubernetes.config
import kubernetes.client
import kubernetes.stream
import kubernetes.watch

import mqtt_kube.k8s.text


class Workload:
    def __init__(self, api_client, namespace, resource):
        self._api_client = api_client
        self._resource = mqtt_kube.k8s.text.camel_to_snake(resource)
        assert self._resource in ('deployment', 'daemon_set', 'job')
        self._namespace = namespace
        self._o = {}
        self._watch_greenlet = None
        self._on_watch = None

    def _get_api(self):
        if self._resource in ('deployment', 'daemon_set'):
            return kubernetes.client.AppsV1Api(self._api_client)
        if self._resource in ('job'):
            return kubernetes.client.BatchV1Api(self._api_client)
        raise NotImplementedError(f'Resource type not supported: {self._resource}')

    def _api_op(self, op):
        api = self._get_api()
        return getattr(api, f'{op}_{self._resource}')

    def exists(self, name):
        try:
            self._o[name] = self._api_op('read_namespaced')(name=name, namespace=self._namespace)
            logging.debug('{%s:%s} Object exists "%s"', self._namespace, self._resource, name)
            return True
        except kubernetes.client.exceptions.ApiException as ex:
            if ex.reason == 'Not Found' and ex.status == 404:
                return False
            raise

    def delete(self, name):
        try:
            propagation_policy = 'Foreground'
            self._o[name] = self._api_op('delete_namespaced')(name=name, namespace=self._namespace,
                                                              orphan_dependents=None,
                                                              propagation_policy=propagation_policy)
            logging.info('{%s:%s} Deleted object "%s"', self._namespace, self._resource, name)
        except kubernetes.client.exceptions.ApiException as ex:
            logging.error('{%s:%s} Deleting object "%s" failed: %s: %s', self._namespace, self._resource, name, ex.__class__.__name__, ex)

    @contextmanager
    def patch(self, name):
        # if not self._watch_greenlet or not self._o:
        #     print('## get latest', name)
        try:
            self._o[name] = self._api_op('read_namespaced')(name=name, namespace=self._namespace)
        except kubernetes.client.exceptions.ApiException as ex:
            if ex.reason == "Not Found" and ex.status == 404:
                logging.info('{%s:%s} Not patching object "%s" because it was not found', self._namespace, self._resource, name)
            else:
                logging.error('{%s:%s} Fetching object "%s" failed: %s: %s', self._namespace, self._resource, name, ex.__class__.__name__, ex)
            yield None
            return

        yield self._o[name]

        logging.debug('{%s:%s} Patching object "%s"', self._namespace, self._resource, name)

        try:
            self._o[name] = self._api_op('patch_namespaced')(name=name, namespace=self._namespace, body=self._o[name])
        except kubernetes.client.exceptions.ApiException as ex:
            logging.error('{%s:%s} Patching object "%s" failed: %s: %s', self._namespace, self._resource, name, ex.__class__.__name__, ex)

    def watch(self, on_watch):
        if not self._watch_greenlet:
            self._on_watch = on_watch
            self._watch_greenlet = gevent.spawn(self._watch_forever)

    def close(self):
        if self._watch_greenlet:
            self._watch_greenlet.kill()
            self._watch_greenlet = None

    def _watch_forever(self):
        while True:
            try:
                self._watch()
            except kubernetes.client.exceptions.ApiException as ex:
                logging.warning('{%s:%s} Watch failed: %s: %s', self._namespace, self._resource, ex.__class__.__name__, ex)
                if ex.reason.startswith('Expired: too old resource version'):
                    pass
                self._o = {}
            except Exception:  # pylint: disable=W0703
                logging.exception('{%s:%s} Watch failed', self._namespace, self._resource,)
            time.sleep(30)

    def _watch(self):
        w = kubernetes.watch.Watch()

        logging.debug('{%s:%s} Watching ...', self._namespace, self._resource)
        for item in w.stream(
            self._api_op('list_namespaced'),
            namespace=self._namespace,
            limit=1,
            resource_version=self._resource_version,
            timeout_seconds=0,
            watch=True
        ):
            watch_type = item['type']

            if watch_type == 'ERROR':
                logging.error('{%s:%s} Watch ERROR: %s %s (%s): %s', self._namespace, self._resource, item['raw_object']['status'], item['raw_object']['reason'], item['raw_object']['code'], item['raw_object']['message'])
                self._o = {}
                return
            if watch_type in ('ADDED', 'MODIFIED'):
                obj = item['object']
                self._o[obj.metadata.name] = obj
                logging.debug('{%s:%s} Watch %s %s %s', self._namespace, self._resource, watch_type, obj.metadata.name, obj.metadata.resource_version)
                self._on_watch(obj, deleted=False)
            elif watch_type in ('DELETED',):
                obj = item['object']
                self._o[obj.metadata.name] = None
                logging.debug('{%s:%s} Watch %s %s %s', self._namespace, self._resource, watch_type, obj.metadata.name, obj.metadata.resource_version)
                self._on_watch(obj, deleted=True)
            else:
                logging.warning('{%s:%s} Watch %s unhandled', self._namespace, self._resource, watch_type)

    @property
    def _resource_version(self):
        version = 0
        if not self._o:
            return 0
        for obj in self._o.values():
            if obj is None:
                continue
            if obj.metadata is None:
                continue
            version = max(version, int(obj.metadata.resource_version))
        return version

    def _ensure(self, obj, path, value):
        try:
            for p in path[:-1]:
                obj = obj[p]
            p = path[-1]
            if obj[p] != value:
                logging.warning('Forcing value %s=%s to %s', '.'.join(path), obj[p], value)
                obj[p] = value
        except KeyError:
            pass

    def launch_template(self, path, context):
        launch_object = mqtt_kube.k8s.template.load_yaml_template(path, context)
        if launch_object is None:
            return
        if mqtt_kube.k8s.text.camel_to_snake(launch_object['kind']) != self._resource:  # pylint: disable=E1136
            logging.warning('Did not launch object, because resource does not match the binding')
        # self._ensure(launch_object, ('kind',), self._resource)
        # self._ensure(launch_object, ('metadata', 'name'), self._name)
        self._ensure(launch_object, ('metadata', 'namespace'), self._namespace)
        try:
            kubernetes.utils.create_from_dict(self._api_client,
                                              data=launch_object,
                                              namespace=self._namespace)
            logging.info("{%s:%s} Launched '%s'", self._namespace, launch_object['kind'],
                         launch_object['metadata']['name'])
        except kubernetes.utils.FailToCreateError as ex:
            logging.error('Failed to launch object: %s', ex)
