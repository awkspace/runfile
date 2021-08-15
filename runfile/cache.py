#!/usr/bin/env python3
import os
import yaml
from collections.abc import MutableMapping


def to_cache(cache, d):
    for key in d:
        if isinstance(d[key], dict):
            d[key] = RunfileCache(cache, to_cache(cache, d[key]))
    return d


def to_dict(cache):
    d = {}
    for key in cache:
        if isinstance(cache[key], RunfileCache):
            d[key] = to_dict(cache[key])
        else:
            d[key] = cache[key]
    return d


class RunfileCache(MutableMapping):

    def __init__(self, container=None, data=None):
        if container is None:
            self.container = self
        else:
            self.container = container

        if data:
            self.data = data
        elif os.path.exists('.runcache') and self.container is self:
            with open('.runcache', 'r') as f:
                d = yaml.load(f, Loader=yaml.SafeLoader)
                self.data = to_cache(self, d)
        else:
            self.data = {}

    def sync(self):
        if self.container is self:
            with open('.runcache', 'w') as f:
                yaml.dump(to_dict(self.data), f)
        else:
            self.container.sync()

    def __getitem__(self, item):
        if item not in self.data:
            self.data[item] = RunfileCache(self.container)
        return self.data[item]

    def __setitem__(self, item, value):
        self.data[item] = value
        self.sync()

    def __delitem__(self, item):
        del self.data[item]
        self.sync()

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __bool__(self):
        return len(self.data) > 0

    def __repr__(self):
        return repr(self.data)

    def __str__(self):
        return yaml.dump(to_dict(self.data))
