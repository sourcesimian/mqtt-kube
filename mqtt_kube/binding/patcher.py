import mqtt_kube.binding.association


class Patcher(mqtt_kube.binding.association.Association):
    def __init__(self, locus, mqtt, topic, valuemap):
        super().__init__(mqtt, topic, valuemap)
        self._locus = locus

    def open(self):
        self._mqtt.subscribe(self._topic, self._on_payload)

    def _on_payload(self, payload, _timestamp):
        match = self._valuemap.lookup(payload)
        if match:
            self._locus.write(match.value)
