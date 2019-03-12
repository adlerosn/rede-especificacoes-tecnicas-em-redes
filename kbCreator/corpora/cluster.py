#!/usr/bin/env python3
# -*- encoding: utf-8 -*-


class Cluster:
    def __init__(self, doc, data):
        self._parent = doc
        self._corpus = doc._corpus
        self._document = doc
        self._main = [self._document._tokens[tk] for tk in data['main']]
        self._mentions = [[self._document._tokens[tk] for tk in mention] for mention in data['mentions']]

    def contains(self, other):
        return False
