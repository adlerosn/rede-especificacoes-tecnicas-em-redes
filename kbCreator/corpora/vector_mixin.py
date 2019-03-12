#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import numpy


class VectorMixin:
    @property
    def vector(self):
        if not hasattr(self, '_vector_np'):
            self._vector_np = numpy.array(self._vector)
        return self._vector_np

    @property
    def vector_norm(self):
        if not hasattr(self, '_vector_norm'):
            self._vector_norm = numpy.sqrt((self.vector ** 2).sum())
        return self._vector_norm

    def similar_with(self, other):
        if self._vector is None:
            raise ValueError('Object does not contain a vector: %r' % self)
        if not hasattr(other, '_vector'):
            return other.contains(self)
        if other._vector is None:
            return False
        if str(self) == str(other):
            return True
        if self._vector == other._vector:
            return True
        return False

    def similarity_with(self, other):
        if self.similar_with(other):
            return 1.
        elif other._vector is None:
            return 0.
        else:
            self_norm = self.vector_norm
            other_norm = other.vector_norm
            if self_norm == 0 or other_norm == 0:
                return .0
            return (numpy.dot(self.vector, other.vector) / (self_norm * other_norm))
