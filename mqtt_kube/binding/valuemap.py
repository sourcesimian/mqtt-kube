import json
import logging
import re

import jsonpath_ng


class ValueMap:
    def __init__(self, values):
        self._transform = None
        if 'transform' in values:
            try:
                self._transform = eval(values['transform'])  # pylint: disable=W0123
            except SyntaxError as ex:
                logging.warning('Failed to parse transform "%s" because: %s: %s', values['transform'], ex.__class__.__name__, ex)
                raise ValueError('Bad Configuration')  # pylint: disable=W0707

        self._jsonpath = None
        if 'jsonpath' in values:
            self._jsonpath = jsonpath_ng.parse(values['jsonpath'])

        self._value_map = []
        if 'map' in values:
            for match, value in values['map'].items():
                value = ValueMatcher(match, value)
                self._value_map.append(value)

        self._format = values.get('format', None)

    def _value(self, value, ctx):
        try:
            if isinstance(value, str):
                return value.format(**ctx)
            return value
        except Exception as ex:                     # pylint: disable=W0703
            logging.warning('Failed to format value "%s" because: %s:%s', value, ex.__class__.__name__, ex)
        return None

    def lookup(self, needle):
        ctx = {'input': needle}
        if self._transform:
            try:
                needle = self._transform(needle)
            except Exception as ex:                     # pylint: disable=W0703
                logging.warning('Failed to transform value "%s" because: %s:%s', needle, ex.__class__.__name__, ex)
                return None

        if self._jsonpath:
            try:
                needle = json.loads(needle)
                ctx['json'] = needle
            except json.JSONDecodeError:
                logging.warning('JSON loads failed for {key}')
                return None
            found = self._jsonpath.find(needle)
            if found:
                needle = found[0].value  # take first value
            else:
                logging.warning('JSONPath lookup failed with {self._jsonpath} in {key}')
                return None
        ctx['value'] = needle
        if self._value_map:
            for value in self._value_map:
                ret, m_ctx = value.match(needle)
                if m_ctx is None:
                    continue
                ctx.update(m_ctx)
                needle = ret
                break
            else:
                return None
        return ValueMatch(self._render_value(needle, ctx), ctx)

    @staticmethod
    def _render_value(value, ctx):
        try:
            if isinstance(value, str):
                return value.format(**ctx)
            return value
        except Exception as ex:                     # pylint: disable=W0703
            logging.warning('Failed to format value "%s" because: %s:%s', value, ex.__class__.__name__, ex)
        return None


class ValueMatcher:
    def __init__(self, match, value):
        self._match = match
        self._value = value

        if isinstance(match, str):
            if match.startswith('re:'):
                try:
                    self._match = re.compile(match[3:])
                except re.error as ex:
                    logging.warning("Ignoring regex match: \"%s\" because %s", match, ex)
                    raise ValueError(f'Ignoring regex match: "{match}"') from ex
            elif match.startswith('lambda '):
                try:
                    self._match = eval(match)     # pylint: disable=W0123
                except Exception as ex:     # pylint: disable=W0703
                    logging.warning("Ignoring lambda match: \"%s\" because %s", match, ex)
                    raise ValueError(f'Ignoring lambda match: "{match}" because {ex}') from ex

    def match(self, needle):

        if callable(self._match):
            try:
                m = self._match(needle)
                if m:
                    return self._value, {}
            except Exception:               # pylint: disable=W0703
                pass
        elif isinstance(self._match, re.Pattern):
            if not isinstance(needle, str):
                return None, None
            m = self._match.match(needle)
            if m:
                return self._value, m.groupdict()
        else:
            if self._match == needle:
                return self._value, {}
        return None, None


class ValueMatch:
    def __init__(self, value, ctx):
        self._value = value
        self._ctx = ctx

    @property
    def value(self):
        return self._value

    @property
    def context(self):
        return self._ctx
