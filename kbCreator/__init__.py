#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from pathlib import Path

from .documents import fromFile as DocumentFromFile


def main():
    rootdoc, rootname = Path("rootdoc.txt").read_text().splitlines()
    rootdoc = DocumentFromFile(rootdoc).parse()
