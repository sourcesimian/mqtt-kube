import logging
import mqtt_kube.k8s.locus
import mqtt_kube.k8s.listener

from mqtt_kube.binding.actioner import Actioner
from mqtt_kube.binding.patcher import Patcher
from mqtt_kube.binding.valuemap import ValueMap
from mqtt_kube.binding.watcher import Watcher
from mqtt_kube.config import plural


class Binding:
    def __init__(self, kube_client, mqtt, bindings):
        self._kube_client = kube_client
        self._mqtt = mqtt
        self._bindings = []
        self._api_listener = mqtt_kube.k8s.listener.Listener(self._kube_client)
        self._init(bindings)

    def _init(self, bindings):
        for binding in bindings:
            try:
                for patch in plural(binding.get('patch', None)):
                    locus = mqtt_kube.k8s.locus.Locus(self._api_listener, binding['namespace'],
                                                      binding['resource'], binding['name'],
                                                      patch['locus'])

                    valuemap = ValueMap(patch.get('values', {}))
                    patcher = Patcher(locus,
                                      self._mqtt, patch['topic'], valuemap)
                    self._bindings.append(patcher)

                for watch in plural(binding.get('watch', None)):
                    locus = mqtt_kube.k8s.locus.Locus(self._api_listener, binding['namespace'],
                                                      binding['resource'], binding['name'],
                                                      watch['locus'])
                    valuemap = ValueMap(watch.get('values', {}))
                    watcher = Watcher(locus,
                                      self._mqtt, watch['topic'], valuemap,
                                      watch.get('retain', False), watch.get('qos', 0))
                    self._bindings.append(watcher)

                for action in plural(binding.get('action', None)):
                    workload = mqtt_kube.k8s.workload.Workload(self._kube_client, binding['namespace'], binding['resource'])
                    valuemap = ValueMap(action.get('values', {}))
                    actioner = Actioner(workload,
                                        self._mqtt, action['topic'], valuemap,
                                        binding, action)
                    self._bindings.append(actioner)

            except (KeyError, ValueError) as ex:
                logging.error('Loading binding "%s: %s": %s', ex.__class__.__name__, ex, repr(binding))

    def open(self):
        for binding in self._bindings:
            binding.open()
        self._api_listener.open()
