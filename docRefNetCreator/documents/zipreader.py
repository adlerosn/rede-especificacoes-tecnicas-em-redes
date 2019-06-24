#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import zipfile
from io import BytesIO
from pathlib import Path
from typing import Union
from typing import List
from .document import Document

fromExtension = None
readers = list()


def lateInit_fromExtension(fe):
    global fromExtension
    fromExtension = fe


class ZipReader(Document):
    @classmethod
    def _opens(cls):
        return ['zip']

    def __init__(self, resource: Union[str, bytes, Path]):
        if isinstance(resource, Path):
            return self.__init__(resource.read_bytes())
        if isinstance(resource, str):
            return self.__init__(Path(resource).read_bytes())
        if hasattr(resource, 'read'):
            return self.__init__(resource.read())
        if not isinstance(resource, bytes):
            raise ValueError("Constructor argument is not bytes or anything known to be converted to bytes")
        super().__init__()
        self._set_document_pages(self.__try_split_text(resource))

    def __try_split_text(self, resource) -> List[str]:
        f = BytesIO(resource)
        zf = zipfile.ZipFile(f)
        zfns = zf.namelist()
        szfns = sorted(zfns, key=lambda fn: (len(fn), fn))
        priority = [ext for r in readers for ext in r._opens()]
        prios = [list() for _ in priority]
        for zfn in szfns:
            fn = zfn.replace('\\', '/').split('/')[-1]
            if '.' in fn:
                ext = fn.split('.')[-1]
                if ext in priority:
                    prios[priority.index(ext)].append(zfn)
        for p in prios:
            for zfn in p:
                fn = zfn.replace('\\', '/').split('/')[-1]
                ext = fn.split('.')[-1]
                try:
                    return fromExtension(ext)(zf.read(zfn))._document_pages
                except zipfile.BadZipFile:
                    pass
        return list()
