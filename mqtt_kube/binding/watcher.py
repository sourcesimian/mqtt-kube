import mqtt_kube.binding.association
from mqtt_kube.k8s.text import k8s_to_mqtt_payload


class Watcher(mqtt_kube.binding.association.Association):
    def __init__(self, locus, mqtt, topic, valuemap, retain, qos):
        super().__init__(mqtt, topic, valuemap)
        self._locus = locus
        self._retain = retain
        self._qos = qos
        self._subscription = None
        self._last_payload = object()
        self._last_update = None

    def open(self):
        self._locus.watch(self._on_locus)

    def _on_locus(self, value, deleted):
        if deleted is True:
            payload = None
        else:
            match = self._valuemap.lookup(value)
            if match:
                payload = match.value
            else:
                payload = value
            if payload == self._last_payload:
                return
        self._last_payload = payload
        payload = k8s_to_mqtt_payload(payload)

        self._mqtt.publish(self._topic, payload, retain=self._retain, qos=self._qos)
