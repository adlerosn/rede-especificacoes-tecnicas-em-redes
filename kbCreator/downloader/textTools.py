#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import re

def slugify(dat):
    return re.sub(r'[^\w\s\.\-\(\)\[\]]', '-', dat)
