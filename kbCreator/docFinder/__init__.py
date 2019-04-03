#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import re
import json

from pathlib import Path

from ..downloader import BeautifulSoup
from ..downloader import simpleDownloader


rgx_itu = re.compile(r"""((?:ITU-\w)|(?:CCITT))(?: Recommendation)? (\w\.[-\d\.]+)(?: \(((?:\d{2}\/)?\d{4})\))?""")
rgx_iso = re.compile(r"""(ISO(?:\/EC)?(?:\/IEC)?(?:\/IEEE)?)(?: (TR))? ([\d+-\.]+)(?::(\d+))?""")
rgx_rfc = re.compile(r"""(RFC) (\d+)""")


def dwnld_itu(match):
    simpleDownloader.cleanCookies()
    bs_documents = BeautifulSoup(simpleDownloader.getUrlBytes(f"https://www.itu.int/rec/T-REC-{match['id']}/en"))

    return


def dwnld_iso_list():
    return None
    return simpleDownloader.getUrl("https://standards.iso.org/ittf/PubliclyAvailableStandards/index.html")


def dwnld_null(match):
    return None


def dwnld_iso(match):
    return None
    simpleDownloader.cleanCookies()
    isofiles = dwnld_iso_list()
    isofile = None
    path = f"/ittf/PubliclyAvailableStandards/{isofile}"
    simpleDownloader.setCookie("url_ok", path)
    return simpleDownloader.getUrlBytes(f"https://standards.iso.org{path}")


def dwnld_rfc(match):
    simpleDownloader.cleanCookies()
    return simpleDownloader.getUrlBytes(f"https://tools.ietf.org/rfc/rfc{match['id']}.txt")
