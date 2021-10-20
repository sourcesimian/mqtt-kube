import re

_re_camel_to_snake = re.compile(r'(?<!^)(?=[A-Z])')

def camel_to_snake(str):
    return _re_camel_to_snake.sub('_', str).lower()

