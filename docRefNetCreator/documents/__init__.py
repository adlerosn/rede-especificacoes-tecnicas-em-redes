#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from .document import Document
from .pdfreader import PdfReader
from .txtreader import TxtReader
from .zipreader import ZipReader
from .plaincached import PlainCachedDocument
from . import zipreader
from typing import Optional
from typing import Type

readers = [
    PdfReader,
    TxtReader,
    ZipReader,
]


def fromExtension(ext: str) -> Optional[Type[Document]]:
    for reader in readers:
        if ext in reader._opens():
            return reader
    return None


def fromFile(path: str) -> Optional[Document]:
    document = fromExtension(path.split('.')[-1])
    return None if document is None else document(path)


zipreader.fromExtension = fromExtension
zipreader.readers = readers

__all__ = [
    'PlainCachedDocument',
    'Document',
    'fromExtension',
    'fromFile',
]
