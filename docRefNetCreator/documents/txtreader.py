#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from pathlib import Path
from typing import Union
from typing import List
from .document import Document


class TxtReader(Document):
    @classmethod
    def _opens(cls):
        return ['txt']

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
        return list(map(lambda a: bytes.decode(a, 'utf-8', 'replace'), resource.split(b'\x0c')))
