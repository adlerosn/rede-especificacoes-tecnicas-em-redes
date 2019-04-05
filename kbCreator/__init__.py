#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from pathlib import Path

from .documents import fromFile as DocumentFromFile
from .document_finder import classes as docClasses


def main():
    rootsrc, rootname = Path("rootdoc.txt").read_text().splitlines()
    docfn = docClasses[rootsrc](rootname).cached()
    doc = DocumentFromFile(str(docfn)).parse()
    print(doc[:50]+'...')
