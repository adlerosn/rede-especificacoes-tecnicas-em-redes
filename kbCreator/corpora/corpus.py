#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from ..string_enumerator import StringListDeenumerator
from .named_entity import NamedEntity
from .document import Document

import en_vectors_web_lg

empty_iter = iter(list())


class Corpus(object):
    _nlp_cached = None

    @property
    def _nlp(self):
        if type(self)._nlp_cached is None:
            type(self)._nlp_cached = en_vectors_web_lg.load()
        return type(self)._nlp_cached

    def __init__(self, json_primitives):
        self._raw_data = json_primitives
        enums = {k: StringListDeenumerator(v) for k, v in json_primitives['enums'].items()}
        self._documents = {doc['source']: Document(self, doc, enums) for doc in json_primitives['documents']}
        self._raw_data = None
        self._parent = None
        self._corpus = self

    def find_knowledge_source(self, k1, k2, max_distance=2):
        ne1 = NamedEntity(self._nlp(str(k1)))
        ne2 = NamedEntity(self._nlp(str(k2)))
        return self._knowledge_path(ne1, ne2, max_distance)

    def _knowledge_path(self, e1, e2, max_distance=2, paths=None, min_similarity=1):
        if max_distance < 0:
            yield from empty_iter
        if paths is None:
            paths = list()
        simFunc = None
        if min_similarity < 1:
            def simFunc(tk): return e1.similarity_with(tk) >= min_similarity
        else:
            def simFunc(tk): return e1.similar_with(tk)
        if simFunc(e2):
            yield paths
        elif isinstance(e1, NamedEntity):
            for ne1 in self.related_entities:
                if simFunc(ne1):
                    yield from self._knowledge_path(ne1, e2, max_distance, [*paths, ne1], min_similarity)
        else:
            for ne1 in e1.related_entities:
                if ne1 != e1:
                    yield from self._knowledge_path(ne1, e2, max_distance-1, [*paths, ne1], min_similarity)

    @property
    def documents(self):
        yield from self._documents.values()

    @property
    def related_entities(self):
        for doc in self.documents:
            yield from doc.related_entities
        yield from empty_iter

    @property
    def tokens(self):
        for doc in self.documents:
            yield from doc.tokens
        yield from empty_iter

    @property
    def chunks(self):
        for doc in self.documents:
            yield from doc.chunks
        yield from empty_iter

    @property
    def clusters(self):
        for doc in self.documents:
            yield from doc.clusters
        yield from empty_iter
