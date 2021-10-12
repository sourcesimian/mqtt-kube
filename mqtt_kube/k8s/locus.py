import logging

from datetime import datetime, timedelta

import jsonpath_ng

import mqtt_kube.k8s.deploy


class Locus(object):
    def __init__(self, api_listener, resource, namespace, name, jsonpath):
        self._api_listener = api_listener
        self._resource = resource
        self._namespace = namespace
        self._name = name

        self._id = self._object_id(namespace, resource, name)
        self._last_watch_value = None
        self._last_watch = None
        
        self._jsonpath = jsonpath_ng.parse(jsonpath)
        self._on_change = None

    @staticmethod
    def _object_id(namespace, resource, name):
        return f'{namespace}:{resource.lower()}/{name}'

    def write(self, value):
        with self._api_listener.patch(self._resource, self._namespace, self._name) as obj:
            self._jsonpath.update(mqtt_kube.k8s.jsonpathadaptor.JsonPathAdaptor(obj), value)

            values = self._jsonpath.find(mqtt_kube.k8s.jsonpathadaptor.JsonPathAdaptor(obj))
            if values:
                final_value = values[0].value.raw
                if final_value == value:
                    logging.debug('Set %s::%s: %s', self._id, self._jsonpath, value)
                else:
                    logging.warning('Not set %s::%s: %s != %s', self._id, self._jsonpath, value, final_value)
            else:
                logging.warning('Value not at %s::%s %s', self._id, self._jsonpath, value)
                logging.debug('obj.spec.replicas: %s', obj.spec.replicas)

    def watch(self, on_change):
        self._on_change = on_change
        logging.debug('Watch %s::%s', self._id, self._jsonpath)
        self._api_listener.watch(self._resource, self._namespace, self._name, self._on_watch)
    
    def _notify_watch_change(self, payload):
        now = datetime.now()
        try:
            if payload != self._last_watch_value:
                return True
            if not self._last_watch:
                return True
            if self._last_watch < (now - timedelta(seconds=10)):
                return True
            return False
        finally:
            self._last_watch_value = payload
            self._last_watch = now

    def _on_watch(self, obj):
        name = self._object_id(obj.metadata.namespace, obj.kind, obj.metadata.name)
        if name != self._id:
            return

        values = self._jsonpath.find(mqtt_kube.k8s.jsonpathadaptor.JsonPathAdaptor(obj))
        if values:
            value = values[0].value.raw
            if self._notify_watch_change(value):
                logging.info('Update %s::%s: %s', self._id, self._jsonpath, value)
                self._on_change(value)
