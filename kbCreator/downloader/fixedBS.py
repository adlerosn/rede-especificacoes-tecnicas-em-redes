#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from bs4 import BeautifulSoup as _BS


def BeautifulSoup(*args, **kwargs):
    return _BS(features="html5lib", *args, **kwargs)
