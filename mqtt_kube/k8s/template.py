import logging
import yaml

from mako.template import Template


def render_template(string, ctx):
    tmpl = Template(string)
    return tmpl.render(**ctx)


def load_yaml_template(filename, ctx):
    try:
        tmpl = Template(filename=filename)
    except FileNotFoundError as ex:
        logging.warning('Unable to rener template "%s", because %s', filename, ex)
        return None

    def make_context(ctx):
        context = {}
        for k, v in ctx.items():
            if isinstance(v, dict):
                context[k] = DictWraper(v)
            else:
                context[k] = v
        return context

    try:
        out = tmpl.render(**make_context(ctx))
        return yaml.load(out, Loader=yaml.Loader)
    except (KeyError, AttributeError) as ex:
        logging.warning('Unable to render template "%s", %s %s', filename, ex.__class__.__name__, ex)
    return None


class DictWraper:
    def __init__(self, obj):
        self._o = obj

    def __contains__(self, item):
        return hasattr(self._o, item)

    def __getattr__(self, key):
        if isinstance(self._o[key], dict):
            return self.__class__(self._o[key])
        return self._o[key]
