#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from ..string_enumerator import StringListDeenumerator
from .vector_mixin import VectorMixin

empty_deenum = StringListDeenumerator()


class Token(VectorMixin):
    def __init__(self, doc, data, enums=None):
        self._parent = doc
        self._corpus = doc._corpus
        self._document = doc
        self._index = data['index']
        self._vector = data['vector']
        self._text = enums['words'][data['text']]
        self._parent = data['parent']
        self._is_root = data['is_root']
        self._ent_type = enums['enttype'][data['ent_type']]
        self._ent_iob = enums['entiob'][data['ent_iob']]
        self._lemma = enums['lemma'][data['lemma']]
        self._norm = enums['norm'][data['norm']]
        self._pos = enums['posgen'][data['pos']]
        self._tag = enums['posspc'][data['tag']]
        self._is_oov = data['is_oov']
        self._prob = data['prob']
        self._sentiment = data['sentiment']

    @property
    def sentence(self):
        return self._sentence

    @property
    def related_entities(self):
        yield from iter(list())
