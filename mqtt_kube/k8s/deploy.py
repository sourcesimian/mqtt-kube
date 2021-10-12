import time
import os
import logging
import gevent
from contextlib import contextmanager

import mqtt_kube.k8s.jsonpathadaptor

import kubernetes
import kubernetes.config
import kubernetes.client
import kubernetes.stream
import kubernetes.watch


class Deployment(object):
    def __init__(self, api_client, namespace):
        self._api_client = api_client
        self._namespace = namespace
        self._o = None
        self._watch_greenlet = None
        self._on_change = None

    @contextmanager
    def patch(self, name):
        api = kubernetes.client.AppsV1Api(self._api_client)

        # if not self._watch_greenlet or not self._o:
        #     print('## get latest', name)
        self._o = api.read_namespaced_deployment(name=name, namespace=self._namespace)

        yield self._o

        logging.debug('{%s} Patching "%s" ...', name, self._namespace)

        try:
            self._o = api.patch_namespaced_deployment(name=name, namespace=self._namespace, body=self._o)
        except kubernetes.client.exceptions.ApiException as ex:
            logging.error('{%s} Patch failed for "%s": %s: %s', self._namespace, name, ex.__class__.__name__, ex)

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
                logging.warning('{%s} Watch failed: %s: %s', self._namespace, ex.__class__.__name__, ex)
                if ex.reason.startswith('Expired: too old resource version'):
                    pass
                self._o = None
            except:
                logging.exception('{%s} Watch failed', self._namespace, )
            time.sleep(30)

    def _watch(self):
        api = kubernetes.client.AppsV1Api(self._api_client)
        w = kubernetes.watch.Watch()

        logging.debug('{%s} Watching ...', self._namespace)
        for item in  w.stream(
            api.list_namespaced_deployment,
            namespace=self._namespace,
            limit=1,
            resource_version=self._resource_version,
            timeout_seconds=0,
            watch=True
        ):
            watch_type = item['type']

            if watch_type == 'ERROR':
                logging.error('{%s} Watch ERROR: %s %s (%s): %s', self._namespace, item['raw_object']['status'], item['raw_object']['reason'], item['raw_object']['code'], item['raw_object']['message'])
                self._o = None
                return

            if watch_type in ('ADDED', 'MODIFIED'):
                obj = item['object']
                self._o = obj
                # logging.debug('{%s} Watch %s %s %s', self._namespace, watch_type, self._o.metadata.name, self._o.metadata.resource_version)
                self._on_change(obj)
            else:
                logging.info('{%s} Watch %s Unhandled', self._namespace, watch_type)

    @property
    def _resource_version(self):
        if self._o is None:
            return 0
        if self._o.metadata is None:
            return 0
        
        return self._o.metadata.resource_version
