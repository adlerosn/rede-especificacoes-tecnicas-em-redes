#!/usr/bin/env python3
# -*- encoding: utf-8 -*-


class StringListReenumerator(object):
    def __init__(self, data: dict):
        self._data = {k: v for k, v in data.items() if k != v}

    def __getitem__(self, data: int) -> int:
        return self._data.get(data, data)


class AbstractStringListEnumerator(object):
    def __init__(self, initial=None):
        self._data = list(initial) if initial is not None else list()

    @property
    def as_list(self):
        return self._data[:]

    @property
    def as_tuple(self):
        return tuple(self._data)

    @property
    def enumerator(self):
        return StringListEnumerator(self._data)

    @property
    def deenumerator(self):
        return StringListDeenumerator(self._data)

    def __getitem__(self, data):
        raise NotImplementedError

    def __contains__(self, other) -> bool:
        raise NotImplementedError

    @property
    def reversed(self):
        raise NotImplementedError

    def merge(self, other: 'AbstractStringListEnumerator') -> StringListReenumerator:
        this = self.enumerator
        that = enumerate(other.as_tuple)
        changes = dict()
        for ndx, word in that:
            changes[ndx] = this[word]
        self._data = this._data
        return StringListReenumerator(changes)


class StringListEnumerator(AbstractStringListEnumerator):
    def __getitem__(self, data: str) -> int:
        try:
            return self._data.index(data)
        except ValueError:
            self._data.append(data)
            return len(self._data)-1

    def __contains__(self, other: str) -> bool:
        return other in self._data

    @property
    def reversed(self):
        return self.deenumerator


class StringListDeenumerator(AbstractStringListEnumerator):
    def __getitem__(self, data: int) -> str:
        return self._data[data]

    def __contains__(self, other: int) -> bool:
        return other >= 0 and other < len(self._data)

    @property
    def reversed(self):
        return self.enumerator
