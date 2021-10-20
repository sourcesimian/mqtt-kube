import logging

from contextlib import contextmanager

import mqtt_kube.k8s.text
import mqtt_kube.k8s.workload


class Listener(object):
    def __init__(self, api_client):
        logging.debug('API Client: %s', api_client.configuration.host)
        self._api_client = api_client
        self._delegate_map = {}

    def _resource_key(self, namespace, resource):
        return f'{namespace}:{resource}'

    def patch(self, namespace, resource, name):
        key = self._resource_key(namespace, resource)

        if key not in self._delegate_map:
            self._delegate_map[key] = ListenerDelegate(self._api_client, namespace, resource)

        return self._delegate_map[key].patch(name)

    def watch(self, namespace, resource, name, on_change):
        key = self._resource_key(namespace, resource)

        if key not in self._delegate_map:
            self._delegate_map[key] = ListenerDelegate(self._api_client, namespace, resource)

        self._delegate_map[key].watch(name, on_change)


class ListenerDelegate(object):
    def __init__(self, api_client, namespace, resource):
        resource = mqtt_kube.k8s.text.camel_to_snake(resource)
        if resource in ('deployment', 'daemon_set'):
            self._resource = mqtt_kube.k8s.workload.Workload(api_client, namespace, resource)
        else:
            self._resource = None
            logging.error('Unsupported resource type "%s"', resource)
        self._name_change_map = {}

    def patch(self, name):
        if not self._resource:
            logging.warning('Not patching unsupported resource type')
            return
        return self._resource.patch(name)

    def watch(self, name, on_change):
        if not self._resource:
            logging.warning('Not watching unsupported resource type')
            return
        if not self._name_change_map:
            self._resource.watch(self._on_change)
        self._name_change_map[name] = on_change

    def _on_change(self, obj):
        try:
            self._name_change_map[obj.metadata.name](obj)
        except KeyError:
            pass
