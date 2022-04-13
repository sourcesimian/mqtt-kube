import logging

from datetime import datetime, timedelta
from textwrap import shorten

import jsonpath_ng

import mqtt_kube.k8s.jsonpathadaptor
import mqtt_kube.k8s.text
import mqtt_kube.k8s.workload


class Locus:
    def __init__(self, api_listener, namespace, resource, name, jsonpath):
        self._api_listener = api_listener
        self._namespace = namespace
        self._resource = resource
        self._name = name

        self._id = self._object_id(namespace, resource, name)
        self._last_watch_value = None
        self._last_watch = None

        jsonpath = mqtt_kube.k8s.text.camel_to_snake(jsonpath)
        try:
            self._jsonpath = jsonpath_ng.parse(jsonpath)
        except AttributeError:
            raise ValueError(f"Invalid JSON Path: '{jsonpath}'") from None
        self._on_change = None

    @classmethod
    def _object_id(cls, namespace, resource, name):
        resource = mqtt_kube.k8s.text.camel_to_snake(resource)
        return f'{namespace}:{resource}/{name}'

    def write(self, value):
        with self._api_listener.patch(self._namespace, self._resource, self._name) as obj:
            if obj is None:
                return
            self._jsonpath.update(mqtt_kube.k8s.jsonpathadaptor.JsonPathAdaptor(obj), value)

            values = self._jsonpath.find(mqtt_kube.k8s.jsonpathadaptor.JsonPathAdaptor(obj))
            if values:
                final_value = [v.value.raw for v in values]
                final_value = final_value[0]  # Just use first occurrence TODO: improve

                if final_value == value:
                    logging.debug('Set %s::%s: %s', self._id, self._jsonpath, value)
                else:
                    logging.warning('Not set %s::%s: %s != %s', self._id, self._jsonpath, value, final_value)
            else:
                logging.warning('Value not at %s::%s %s', self._id, self._jsonpath, value)

    def watch(self, on_change):
        self._on_change = on_change
        logging.debug('Watch %s::%s', self._id, self._jsonpath)
        self._api_listener.watch(self._namespace, self._resource, self._name, self._on_watch)

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

    def _on_watch(self, obj, deleted):
        if deleted is True:
            self._on_change(None, deleted=deleted)
            return

        object_id = self._object_id(obj.metadata.namespace, obj.kind, obj.metadata.name)
        if object_id != self._id:
            return

        values = self._jsonpath.find(mqtt_kube.k8s.jsonpathadaptor.JsonPathAdaptor(obj))
        if values:
            value = [v.value.raw for v in values]
            if len(value) == 1:
                value = value[0]

            if self._notify_watch_change(value):
                logging.info('Update %s::%s: %s', self._id, self._jsonpath, shorten(str(value), width=30, placeholder="..."))
                self._on_change(value, deleted=deleted)
