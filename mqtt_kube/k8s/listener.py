import logging

import mqtt_kube.k8s.text
import mqtt_kube.k8s.workload


class Listener:
    def __init__(self, api_client):
        logging.debug('API Client: %s', api_client.configuration.host)
        self._api_client = api_client
        self._delegate_map = {}

    def open(self):
        for delegate in self._delegate_map.values():
            delegate.open()

    def _resource_key(self, namespace, resource):
        return f'{namespace}:{resource}'

    def _delegate(self, namespace, resource):
        key = self._resource_key(namespace, resource)
        if key not in self._delegate_map:
            self._delegate_map[key] = ListenerDelegate(self._api_client, namespace, resource)
        return self._delegate_map[key]

    def patch(self, namespace, resource, name):
        return self._delegate(namespace, resource).patch(name)

    def watch(self, namespace, resource, name, on_watch):
        return self._delegate(namespace, resource).watch(name, on_watch)


class ListenerDelegate:
    def __init__(self, api_client, namespace, resource):
        resource = mqtt_kube.k8s.text.camel_to_snake(resource)
        if resource in ('deployment', 'daemon_set', 'job'):
            self._workload = mqtt_kube.k8s.workload.Workload(api_client, namespace, resource)
        else:
            self._workload = None
            logging.error('Unsupported resource type "%s"', resource)
        self._name_onwatch_map = {}

    def open(self):
        for name, on_watches in self._name_onwatch_map.items():
            if not self._workload.exists(name):
                for on_watch in on_watches:
                    on_watch(None, deleted=True)

    def patch(self, name):
        if not self._workload:
            logging.warning('Not patching unsupported resource type')
            return None
        return self._workload.patch(name)

    def watch(self, name, on_watch):
        if not self._workload:
            logging.warning('Not watching unsupported resource type')
            return
        if not self._name_onwatch_map:
            self._workload.watch(self._on_watch)
        if name not in self._name_onwatch_map:
            self._name_onwatch_map[name] = []
        self._name_onwatch_map[name].append(on_watch)

    def _on_watch(self, obj, deleted):
        try:
            for on_watch in self._name_onwatch_map[obj.metadata.name]:
                on_watch(obj, deleted=deleted)
        except KeyError:
            pass
