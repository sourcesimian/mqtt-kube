import logging

DEFAULT = object()


class JsonPathAdaptor(object):
    def __init__(self, obj):
        self._o = obj

    @property
    def raw(self):
        return self._o

    def keys(self):
        return self._o.keys()

    def get(self, key, default=DEFAULT):
        try:
            return self.__class__(self._o.get(key))
        except (KeyError, AttributeError):
            pass
        try:
            return self.__class__(getattr(self._o, key))
        except AttributeError:
            if default is not DEFAULT:
                return default
            raise

    def __len__(self):
        return len(self._o)

    def __instancecheck__(self, instance):
        return isinstance(instance, self._o)

    def __contains__(self, item):
        return hasattr(self._o, item)

    def __getitem__(self, *args):
        return self.__class__(getattr(self._o, *args))

    def __setitem__(self, *args):
        return setattr(self._o, *args)

    def __delitem__(self, *args):
        return delattr(self._o, *args)

    def __eq__(self, value):
        return self._o == value

    def __bool__(self):
        return bool(self._o)
