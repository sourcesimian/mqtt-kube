import json
import re

from datetime import datetime

_re_camel_to_snake = re.compile(r'(?<!^)(?=[A-Z])')


def camel_to_snake(text):
    return _re_camel_to_snake.sub('_', text).lower()


class AdvancedEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return super().default(o)


def k8s_to_mqtt_payload(obj):
    if hasattr(obj, 'to_dict'):
        obj = obj.to_dict()
    if isinstance(obj, dict):
        return json.dumps(obj, separators=(',', ':'), sort_keys=True, cls=AdvancedEncoder)
    if not isinstance(obj, (str, bytearray, int, float, type(None))):
        return str(obj)
    return obj
