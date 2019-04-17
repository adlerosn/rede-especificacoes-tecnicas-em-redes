#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from .document import Document
from .pdfreader import PdfReader
from typing import Optional
from typing import Type

readers = [
    PdfReader
]


def fromExtension(ext: str) -> Optional[Type[Document]]:
    for reader in readers:
        if ext in reader._opens():
            return reader
    return None


def fromFile(path: str) -> Optional[Document]:
    document = fromExtension(path.split('.')[-1])
    return None if document is None else document(path)


__all__ = [
    'Document',
    'fromExtension',
    'fromFile',
]
