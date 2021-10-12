import logging
import mqtt_kube.k8s.locus
import mqtt_kube.k8s.listener


class Binding(object):
    def __init__(self, kube_client, mqtt, bindings):
        self._kube_client = kube_client
        self._mqtt = mqtt
        self._bindings = []
        self._api_listener = mqtt_kube.k8s.listener.Listener(self._kube_client)
        self._init(bindings)

    def _init(self, bindings):
        for binding in bindings:
            try:
                patch = binding.get('patch', None)
                if patch:
                    locus = mqtt_kube.k8s.locus.Locus(self._api_listener, binding['resource'],
                                                      binding['namespace'], binding['name'],
                                                      patch['jsonpath'])

                    values = ValueMap(patch.get('values', None))
                    patcher = Patcher(locus,
                                      self._mqtt, patch['topic'],
                                      values)
                    self._bindings.append(patcher)

                watch = binding.get('watch', None)
                if watch:
                    locus = mqtt_kube.k8s.locus.Locus(self._api_listener, binding['resource'],
                                                      binding['namespace'], binding['name'],
                                                      watch['jsonpath'])
                    values = ValueMap(watch.get('values', None))
                    watcher = Watcher(locus,
                                      self._mqtt, watch['topic'], watch.get('retain', False), watch.get('qos', 0),
                                      values)
                    self._bindings.append(watcher)
            except KeyError as ex:
                logging.error('Loading binding "%s: %s": %s', ex.__class__.__name__, ex, repr(binding))

    def open(self):
        for binding in self._bindings:
            binding.open()


class ValueMap(object):
    def __init__(self, values):
        self._v = values
    
    def payload(self, value):
        if not self._v:
            return value
        try:
            return self._v[value]
        except KeyError:
            pass
        try:
            return self._v['default']
        except KeyError:
            pass
        raise ValueError

    def value(self, payload):
        if not self._v:
            return payload
        try:
            return self._v[payload]
        except KeyError:
            pass
        if 'default' in self._v:
            return self._v['default']
        raise ValueError


class Patcher(object):
    def __init__(self, locus, mqtt, topic, values):
        self._locus = locus
        self._mqtt = mqtt
        self._values = values
        self._topic = topic

    def open(self):
        self._mqtt.subscribe(self._topic, self._on_payload)
    
    def _on_payload(self, payload, timestamp):
        try:
            value = self._values.value(payload)
            self._locus.write(value)
        except ValueError:
            pass


class Watcher(object):
    def __init__(self, locus, mqtt, topic, retain, qos, values):
        self._locus = locus
        self._mqtt = mqtt
        self._values = values
        self._topic = topic
        self._retain = retain
        self._qos = qos
        self._subscription = None
        self._last_payload = None
        self._last_update = None

    def open(self):
        self._locus.watch(self._on_locus)

    def _on_locus(self, value):
        try:
            payload = self._values.payload(value)
            if payload == self._last_payload:
                return
            self._last_payload = payload
            self._mqtt.publish(self._topic, payload, retain=self._retain, qos=self._qos)
        except ValueError:
            pass
        
