import json

import jsonpath_ng

from mqtt_kube.mqtt import Mqtt


class MqttJson(Mqtt):
    def __init__(self, config):
        Mqtt.__init__(self, config)

    @classmethod
    def _json_loads(cls, payload):
        try:
            if isinstance(payload, str):
                return json.loads(payload)
        except json.JSONDecodeError:
            pass
        raise ValueError('Could not extract JSON')

    @classmethod
    def _partial_jsonpath_find(cls, jsonpath):
        jsonpath = jsonpath_ng.parse(jsonpath)

        def jsonpath_find(payload):
            value = jsonpath.find(payload)
            if value:
                return value[0].value  # take first value
            raise ValueError('JSONPath not found')
        return jsonpath_find

    @classmethod
    def _split_topic(cls, topic):
        parts = topic.split('|')
        topic = parts[0]
        modifiers = []
        for part in parts[1:]:
            if part.startswith(('$', '.')):
                modifiers.append(cls._json_loads)
                modifiers.append(cls._partial_jsonpath_find(part))
            else:
                modifiers.append(eval(part))  # pylint: disable=W0123
        return topic, modifiers

    def subscribe(self, topic, on_payload):
        topic, modifiers = self._split_topic(topic)

        def _on_payload(payload, timestamp):
            value = payload
            for modifier in modifiers:
                value = modifier(value)
                if value is None:
                    break
            on_payload(self._json_loads(payload), value, timestamp)

        Mqtt.subscribe(self, topic, _on_payload)
