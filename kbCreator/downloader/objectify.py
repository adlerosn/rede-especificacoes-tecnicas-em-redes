#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json


class objectify(object):
    @property
    def json(self):
        if (len(self.__dict__) == 1) and ('_wrapped' in self.__dict__):
            return self._wrapped
        return self.__dict__

    def __init__(self, data):
        self._wrapped = data
        if isinstance(data, dict):
            self.__dict__ = data
        if isinstance(data, objectify):
            raise ValueError("You're double-wrapping an object")

    def __str__(self): return json.dumps(self.json, indent=4)

    def __repr__(self): return self.__str__()

    def __getitem__(self, item): return self.json[item]
