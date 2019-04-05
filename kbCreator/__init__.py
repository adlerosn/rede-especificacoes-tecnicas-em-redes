#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from pathlib import Path

from .documents import fromFile as DocumentFromFile
from .document_finder import classes as docClasses
from .document_finder import find_references as referenceFinder


def main():
    rootsrc, rootname = Path("rootdoc.txt").read_text().splitlines()
    docCchMgr = docClasses[rootsrc](rootname)
    docPath = docCchMgr.cached()
    doc = DocumentFromFile(str(docPath)).parse()
    referenceFinder(doc, docCchMgr.context(docPath))
    print(doc[:50]+'...')
