#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from .vector_mixin import VectorMixin


class Sentence(VectorMixin):
    def __init__(self, doc, data):
        self._parent = doc
        self._corpus = doc._corpus
        self._document = doc
        self._vector = data['vector']
        self._sentiment = data['sentiment']
        self._tokens = [self._document._tokens[ndx] for ndx in data['tokens']]
        self._chunks = [self._document._chunks[ndx] for ndx in data['noun_chunks']]
        self._clusters = [self._document._clusters[ndx] for ndx in data['coref_cluster']]
        for ndx in data['tokens']:
            self._document._tokens[ndx]._sentence = self
