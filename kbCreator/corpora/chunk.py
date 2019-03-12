#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from .vector_mixin import VectorMixin


class Chunk(VectorMixin):
    def __init__(self, doc, data):
        self._parent = doc
        self._corpus = doc._corpus
        self._document = doc
        self._vector = data['vector']
        self._tokens = [self._document._tokens[tk] for tk in data['token_range']]
        self._sentiment = data['sentiment']

    @property
    def related_entities(self):
        yield from self._tokens
        for snt in {tk.sentence for tk in self._tokens}:
            yield from snt._tokens
            yield from snt._chunks
            yield from snt._clusters
