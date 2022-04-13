import hashlib
import logging
import os
import random
import sys

from typing import Any, IO

import yaml

# Prevent YAML loader from interpreting 'on', 'off', 'yes', 'no' as bool
from yaml.resolver import Resolver

for ch in "OoYyNn":
    Resolver.yaml_implicit_resolvers[ch] = [x for x in
                                            Resolver.yaml_implicit_resolvers[ch]
                                            if x[0] != 'tag:yaml.org,2002:bool']


class Loader(yaml.Loader):  # pylint: disable=R0901
    """YAML Loader with custom constructors"""

    def __init__(self, stream: IO) -> None:
        try:
            self._base = os.path.split(stream.name)[0]
        except AttributeError:
            self._base = os.path.curdir

        super().__init__(stream)

    @classmethod
    def construct_relpath(cls, loader, node: yaml.Node) -> Any:
        """Relative path"""

        return os.path.abspath(os.path.join(loader._base, loader.construct_scalar(node)))  # pylint: disable=W0212


yaml.add_constructor('!relpath', Loader.construct_relpath, Loader)


def default(item, key, value):
    if key not in item:
        item[key] = value


class Config:
    def __init__(self, config_file):
        logging.info('Config file: %s', config_file)
        try:
            with open(config_file, 'rt', encoding="utf8") as fh:
                self._d = yaml.load(fh, Loader=Loader)
        except yaml.parser.ParserError:
            logging.exception('Loading %s', config_file)
            sys.exit(1)

        self._hash = hashlib.md5(str(random.random()).encode('utf-8')).hexdigest()

        self._d['mqtt']['client-id'] += f'-{self._hash[8:]}'

    @property
    def log_level(self):
        try:
            level = self._d['logging']['level'].upper()
            return {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'WARN': logging.WARNING,
                'ERROR': logging.ERROR,
            }[level]
        except KeyError:
            return logging.DEBUG

    @property
    def http(self):
        return self._d['http']

    @property
    def mqtt(self):
        return self._d['mqtt']

    @property
    def bindings(self):
        for item in self._d['bindings']:
            yield item


def plural(items):
    if not items:
        return
    if isinstance(items, list):
        yield from items
    else:
        yield items
