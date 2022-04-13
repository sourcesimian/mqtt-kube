class Association:
    def __init__(self, mqtt, topic, valuemap):
        self._mqtt = mqtt
        self._topic = topic
        self._valuemap = valuemap
