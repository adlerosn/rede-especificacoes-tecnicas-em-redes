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
        yield self._tokens[0]._sentence

    def __str__(self):
        return 'Noun Chunk: %s @ Snt #%s from %s' % (
            ' '.join(map(lambda a: a._text, self._tokens)),
            str(self._tokens[0]._sentence._seq),
            self._document._source
        )
