#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from .vector_mixin import VectorMixin


class NamedEntity(VectorMixin):
    def __init__(self, doc):
        self._parts = list(map(str, list(doc)))
        self._vector = doc.vector.tolist()
        self._vector_np = doc.vector
        self._vector_norm = doc.vector_norm

    def __str__(self):
        return ' '.join(self._parts).lower()

    def __repr__(self):
        return self.__str__()
