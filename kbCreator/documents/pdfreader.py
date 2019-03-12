#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import subprocess
from pathlib import Path
from typing import Union
from .document import Document

try:
    version = subprocess.run(
        ['pdftotext', '-v'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    if version.returncode != 0:
        raise ImportError("PdfReader needs that 'pdftotext' properly informs its version.")
    version = tuple(map(int, filter(str.isdigit, version.stderr.decode('utf-8', 'ignore').splitlines()[0].split(' ')[-1].split('.'))))
    if version < (0, 41, 0):
        raise ImportError("Your 'pdftotext' is outdated. Its minimum version is 0.41.0.")
except FileNotFoundError:
    raise ImportError("PdfReader needs 'pdftotext' command in your PATH")


class PdfReader(Document):
    @classmethod
    def _opens(cls):
        return ['pdf']

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
        self._set_document_pages(self.__convert_pdf_to_text(resource))

    def __convert_pdf_to_text(self, resource) -> bytes:
        proc = subprocess.run(
            ['pdftotext', '-layout', '-', '-'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            input=resource
        )
        if proc.returncode != 0:
            raise ValueError("Constructed with an unhealthy PDF")
        return list(map(lambda a: bytes.decode(a, 'utf-8', 'replace'), proc.stdout.split(b'\x0c')))
