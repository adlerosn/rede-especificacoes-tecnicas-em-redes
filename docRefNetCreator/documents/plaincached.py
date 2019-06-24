#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from os import linesep as eol
from pathlib import Path
import json


class PlainCachedDocument:
    def __init__(self, cachekey, clazz, *args, **kwargs):
        self._cache_key = cachekey
        self._class = clazz
        self._args = args
        self._kwargs = kwargs

    def parse(self, cst_eol: str = eol):
        return self.parsed_from_cache(cst_eol)

    def parsed_from_cache(self, cst_eol: str = eol):
        cached = None
        cached_disk = Path('plaincache', self._cache_key)
        if cached_disk.exists():
            cached = json.loads(cached_disk.read_text())
        else:
            print("PlainCachedDocument miss: "+str(cached_disk))
            cached = (self._class(*self._args, **self._kwargs)).parse(None)
            cached_disk.parent.mkdir(parents=True, exist_ok=True)
            cached_disk.write_text(json.dumps(cached))
        return cst_eol.join(cached)
