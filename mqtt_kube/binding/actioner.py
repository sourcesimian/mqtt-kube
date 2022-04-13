import logging
import uuid

import mqtt_kube.binding.association
import mqtt_kube.k8s.template
import mqtt_kube.k8s.workload


class Actioner(mqtt_kube.binding.association.Association):
    def __init__(self, workload, mqtt, topic, valuemap, binding, action):
        super().__init__(mqtt, topic, valuemap)
        self._workload = workload
        self._binding = binding
        self._action = action

    def open(self):                 # pylint: disable=R0801
        self._mqtt.subscribe(self._topic, self._on_payload)

    def _on_payload(self, payload, _timestamp):

        ctx = {
            'binding': self._binding,
            'action': self._action,
            'uid': str(uuid.uuid4().hex[:8])
        }

        match = self._valuemap.lookup(payload)

        if match is None:
            return
        action = match.value
        ctx['match'] = match.context

        if action == 'launch':
            self._workload.launch_template(self._action['launch'], ctx)
        elif action == 'delete':
            self._workload.delete(self._binding['name'])
        else:
            logging.warning('Action not implemented: "%s"', action)
