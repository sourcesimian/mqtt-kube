import logging

from contextlib import contextmanager

import mqtt_kube.k8s.deploy


class Listener(object):
    def __init__(self, api_client):
        logging.debug('API Client: %s', api_client.configuration.host)
        self._api_client = api_client
        self._delegate_map = {}

    def _resource_key(self, resource, namespace):
        return f'{resource}:{namespace}'

    def patch(self, resource, namespace, name):
        key = self._resource_key(resource, namespace)

        if key not in self._delegate_map:
            self._delegate_map[key] = ListenerDelegate(self._api_client, resource, namespace)

        return self._delegate_map[key].patch(name)

    def watch(self, resource, namespace, name, on_change):
        key = self._resource_key(resource, namespace)

        if key not in self._delegate_map:
            self._delegate_map[key] = ListenerDelegate(self._api_client, resource, namespace)

        self._delegate_map[key].watch(name, on_change)


class ListenerDelegate(object):
    def __init__(self, api_client, resource, namespace):
        if resource == 'deployment':
            self._resource = mqtt_kube.k8s.deploy.Deployment(api_client, namespace)
        else:
            self._resource = None
            logging.error('Unknown resource type "%s"', resource)
        self._name_change_map = {}

    def patch(self, name):
        return self._resource.patch(name)

    def watch(self, name, on_change):
        if not self._name_change_map:
            self._resource.watch(self._on_change)
        self._name_change_map[name] = on_change

    def _on_change(self, obj):
        try:
            self._name_change_map[obj.metadata.name](obj)
        except KeyError:
            pass
