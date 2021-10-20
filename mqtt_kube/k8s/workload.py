import time
import os
import logging
import gevent
from contextlib import contextmanager

import mqtt_kube.k8s.jsonpathadaptor
import mqtt_kube.k8s.text

import kubernetes
import kubernetes.config
import kubernetes.client
import kubernetes.stream
import kubernetes.watch


class Workload(object):
    def __init__(self, api_client, namespace, resource):
        self._api_client = api_client
        self._resource = resource
        assert resource in ('deployment', 'daemon_set')
        self._namespace = namespace
        self._o = None
        self._watch_greenlet = None
        self._on_change = None

    def _api_op(self, api, op):
        return getattr(api, '%s_%s' % (op, self._resource))

    @contextmanager
    def patch(self, name):
        api = kubernetes.client.AppsV1Api(self._api_client)

        # if not self._watch_greenlet or not self._o:
        #     print('## get latest', name)
        try:
            self._o = self._api_op(api, 'read_namespaced')(name=name, namespace=self._namespace)
        except kubernetes.client.exceptions.ApiException as ex:
            logging.error('{%s:%s} Fetching object failed for "%s": %s: %s', self._namespace, self._resource, name, ex.__class__.__name__, ex)
            return

        yield self._o

        logging.debug('{%s:%s} Patching "%s" ...', self._namespace, self._resource, name)

        try:
            self._o = self._api_op(api, 'patch_namespaced')(name=name, namespace=self._namespace, body=self._o)
        except kubernetes.client.exceptions.ApiException as ex:
            logging.error('{%s:%s} Patch failed for "%s": %s: %s', self._namespace, self._resource, name, ex.__class__.__name__, ex)

    def watch(self, on_change):
        if not self._watch_greenlet:
            self._on_change = on_change
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
                self._o = None
            except:
                logging.exception('{%s:%s} Watch failed', self._namespace, self._resource, )
            time.sleep(30)

    def _watch(self):
        api = kubernetes.client.AppsV1Api(self._api_client)
        w = kubernetes.watch.Watch()

        logging.debug('{%s:%s} Watching ...', self._namespace, self._resource)
        for item in  w.stream(
            self._api_op(api, 'list_namespaced'),
            namespace=self._namespace,
            limit=1,
            resource_version=self._resource_version,
            timeout_seconds=0,
            watch=True
        ):
            watch_type = item['type']

            if watch_type == 'ERROR':
                logging.error('{%s:%s} Watch ERROR: %s %s (%s): %s', self._namespace, self._resource, item['raw_object']['status'], item['raw_object']['reason'], item['raw_object']['code'], item['raw_object']['message'])
                self._o = None
                return
            elif watch_type in ('ADDED', 'MODIFIED'):
                obj = item['object']
                self._o = obj
                logging.debug('{%s:%s} Watch %s %s %s', self._namespace, self._resource, watch_type, self._o.metadata.name, self._o.metadata.resource_version)
                self._on_change(obj)
            else:
                logging.info('{%s:%s} Watch %s Unhandled', self._namespace, self._resource, watch_type)

    @property
    def _resource_version(self):
        if self._o is None:
            return 0
        if self._o.metadata is None:
            return 0
        
        return self._o.metadata.resource_version
