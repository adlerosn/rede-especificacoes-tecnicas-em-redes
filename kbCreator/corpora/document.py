#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from ..string_enumerator import StringListDeenumerator
from .token import Token
from .chunk import Chunk
from .cluster import Cluster
from .sentence import Sentence

empty_deenum = StringListDeenumerator()
empty_iter = iter(list())


class Document:
    def __init__(self, corpus, data, enums=None):
        if enums is None:
            enums = dict()
        self._parent = corpus
        self._corpus = corpus
        self._document = self
        self._source = data['source']
        self._tokens = [Token(self, tk, enums) for tk in data['tokens']]
        self._vector = data['vector']
        self._sentiment = data['sentiment']
        self._chunks = [Chunk(self, ck) for ck in data['noun_chunks']]
        self._clusters = [Cluster(self, cl) for cl in data['coref_cluster']]
        self._sentences = [Sentence(self, sn, i+1) for i, sn in enumerate(data['sentences'])]

    @property
    def related_entities(self):
        yield from self.tokens
        yield from self.chunks
        yield from self.clusters
        yield from empty_iter

    @property
    def tokens(self):
        yield from self._tokens
        yield from empty_iter

    @property
    def chunks(self):
        yield from self._chunks
        yield from empty_iter

    @property
    def clusters(self):
        yield from self._clusters
        yield from empty_iter
