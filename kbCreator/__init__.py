#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from pathlib import Path

from .documents import fromFile as DocumentFromFile
from .document_finder import classes as docClasses
from .document_finder import find_references as referenceFinder


def main():
    rootsrc, rootname = Path("rootdoc.txt").read_text().splitlines()
    analyzedDocPaths = list()
    pendingDocCchMgr = [docClasses[rootsrc](rootname)]
    while len(pendingDocCchMgr) > 0:
        docCchMgr, *pendingDocCchMgr = pendingDocCchMgr
        print("Document: %s" % docCchMgr._identifier)
        docPath = docCchMgr.cached()
        if docPath in analyzedDocPaths:
            continue
        analyzedDocPaths.append(docPath)
        docFF = DocumentFromFile(str(docPath))
        if docFF is None:
            continue
        doc = docFF.parse()
        newReferences = referenceFinder(doc, docCchMgr.context(docPath))
        pendingDocCchMgr = sorted([*pendingDocCchMgr, *newReferences], key=lambda dcm: (not dcm.is_cached(), dcm.slowness(), dcm._identifier))
        print("Pending queue: %03d" % len(pendingDocCchMgr))
        print("Uncached on queue: %03d" % len(list(filter(lambda dcm: not dcm.is_cached(), pendingDocCchMgr))))
        print("Unique on queue: %03d" % len(set([dcm._identifier for dcm in pendingDocCchMgr])))
