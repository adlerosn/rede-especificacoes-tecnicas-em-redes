#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from .vector_mixin import VectorMixin


class Cluster(VectorMixin):
    def __init__(self, doc, data):
        self._parent = doc
        self._corpus = doc._corpus
        self._document = doc
        self._main = [self._document._tokens[tk] for tk in data['main']]
        self._mentions = [[self._document._tokens[tk] for tk in mention] for mention in data['mentions']]
        self._vector = data['vector']

    @property
    def related_entities(self):
        yield self._main[0]._sentence
        for mnt in self._mentions:
            yield mnt[0]._sentence

    def __str__(self):
        return 'Correference Cluster: %s @ Snts ##%s from %s' % (
            ' // '.join(sorted(list(set([' '.join(map(lambda a: a._text, tokens)) for tokens in [self._main, *self._mentions]])))),
            ','.join(map(lambda tklst: str(tklst[0]._sentence._seq), [self._main, *self._mentions])),
            self._document._source
        )
