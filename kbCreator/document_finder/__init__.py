#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import re
import sys
import json
import datetime

from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import Optional
from pathlib import Path

from ..downloader import BeautifulSoup
from ..downloader import simpleDownloader


classes = dict()

rgx_itu = re.compile(r"""((?:ITU-\w)|(?:CCITT))(?: Recommendation)? ([A-Z]+\.[-\d\.]+)(?: \(((?:\d{2}\/)?\d{4})\))?""")
rgx_iso = re.compile(r"""(ISO(?:\/EC)?(?:\/IEC)?(?:\/IEEE)?)(?: (TR))? ([\d+-\.]+)(?::(\d+))?""")
rgx_rfc = re.compile(r"""(RFC) ([0-9]+)""")

rgx_itu_fix = re.compile(r"""(\w\.[-\d\.]+)(?:-)(\d{4})""")

status_itu_text2code = {
    'In force': 0,
    'Superseded': 1,
    'Withdrawn': 2,
    'Unknown': 3,
}

status_itu_code2text = dict(map(lambda a: a[::-1], status_itu_text2code.items()))


def expand_year(yr):
    yr = int(yr)
    if yr < 100:
        if yr > int(str(datetime.datetime.now().year)[-2:]):
            return str(int(str(datetime.datetime.now().year)[:-2])-1)+("%02d" % yr)
        else:
            return str(datetime.datetime.now().year)[:-2]+("%02d" % yr)
    else:
        return str(yr)


def dwnld_iso_list():
    return None
    return simpleDownloader.getUrl("https://standards.iso.org/ittf/PubliclyAvailableStandards/index.html")


def dwnld_iso(match):
    return None
    simpleDownloader.cleanCookies()
    isofiles = dwnld_iso_list()
    isofile = None
    path = f"/ittf/PubliclyAvailableStandards/{isofile}"
    simpleDownloader.setCookie("url_ok", path)
    return simpleDownloader.getUrlBytes(f"https://standards.iso.org{path}")


class OnlineStandard(object):
    cachedir = Path('cache', 'online_standard')

    def __init__(self, identifier: str, revision: Optional[str] = None, citing_date: Optional[str] = None):
        self._identifier: str = identifier
        self._revision: Optional[Tuple[int, int]] = None
        self._citing_date: Tuple[int, int] = (sys.maxsize, sys.maxsize)
        if citing_date is not None:
            yr, mo, *_ = (citing_date+'-99-99').split('-')
            yr = expand_year(yr)
            mo = int(mo)
            self._citing_date = (yr, mo)
        if revision is not None:
            yr, mo, *_ = (revision+'-99-99').split('-')
            yr = expand_year(yr)
            mo = int(mo)
            self._revision = (yr, mo)

    def download_all(self) -> Dict[str, bytes]: pass
    def cached_all(self) -> Dict[str, Path]: pass
    def cached(self) -> Optional[Path]: pass
    def is_cached(self) -> bool: return False
    def slowness(self) -> int: return 0
    def context(self, path: Path) -> Dict[str, str]: return dict()


class RFCStandard(OnlineStandard):
    cachedir = Path('cache', 'rfc')

    def download_all(self) -> Dict[str, bytes]:
        simpleDownloader.cleanCookies()
        return {'latest': simpleDownloader.getUrlBytes(f"https://tools.ietf.org/rfc/rfc{self._identifier}.txt")}

    def cached_all(self) -> Dict[str, Path]:
        type(self).cachedir.mkdir(parents=True, exist_ok=True)
        cached_all = type(self).cachedir.joinpath(self._identifier+'.txt')
        if not cached_all.exists():
            data = self.download_all()['latest']
            cached_all.write_bytes(b'' if data is None else data)
        return {'latest': cached_all}

    def is_cached(self) -> bool:
        cached_all = type(self).cachedir.joinpath(self._identifier+'.txt')
        return cached_all.exists()

    def slowness(self) -> int: return 1

    def cached(self) -> Optional[Path]:
        return self.cached_all().get('latest')


class ITURecommendation(OnlineStandard):
    cachedir = Path('cache', 'itu')
    langorder = ('en', 'fr', 'es', 'ar', 'ru', 'ch')
    extorder = ('pdf', 'doc', 'epub', 'zip', 'doc.zip')

    def download_all(self) -> Dict[str, bytes]:
        d = dict()
        simpleDownloader.cleanCookies()
        print(f"https://www.itu.int/rec/T-REC-{self._identifier}/en")
        bt_documents = simpleDownloader.getUrlBytes(f"https://www.itu.int/rec/T-REC-{self._identifier}/en")
        if bt_documents is None:
            return d
        bs_documents = BeautifulSoup(bt_documents)
        for match in bs_documents.select('tr'):
            if match.find('a', href=True) is not None and match.find('table') is None:
                if match.find('a')['href'].startswith('./recommendation.asp?lang=en'):
                    pdflinkrel = match.find('a')['href'][2:]
                    pdfpage = f"https://www.itu.int/rec/T-REC-{self._identifier}/{pdflinkrel}"
                    brute_year = match.find('a').text.strip().split('(', 1)[-1].split(')', 1)[0].split('/')[-1]
                    brute_month = match.find('a').text.strip().split('(', 1)[-1].split(')', 1)[0].split('/')[0]
                    mo, yr = None, None
                    try:
                        mo, yr = "%02d" % int(brute_month), expand_year(brute_year)
                    except ValueError:
                        dts = pdflinkrel.split('-')[-2]
                        mo, yr = dts[4:6], dts[0:4]
                    st = str(status_itu_text2code.get(match.findAll('td')[-1].text.strip(), 3))
                    bs_pdfpage = BeautifulSoup(simpleDownloader.getUrlBytes(pdfpage))
                    lng_prev = ''
                    for table in bs_pdfpage.findAll('table', width=True):
                        if 'Access : Freely available items' not in table.strings:
                            continue
                        if 'Publications' in table.strings or 'Status : ' in table.strings:
                            continue
                        for download_allline in table.find('table').findAll('tr'):
                            if download_allline.find('a', href=True) is None:
                                continue
                            if 'bytes' not in download_allline.findAll('td')[2].text:
                                continue
                            lng = download_allline.findAll('td')[0].text.strip().rstrip(':').rstrip().lower()[:2]
                            if len(lng) == 0:
                                lng = lng_prev
                            else:
                                lng_prev = lng
                            dwn = download_allline.find('a', href=True)['href']
                            print(dwn)
                            type = dwn.split('!', 2)[2].split('&', 1)[0].split('-', 1)[0].lower()
                            ext = ({
                                'pdf': 'pdf',
                                'msw': 'doc',
                                'zwd': 'doc.zip',
                                'soft': 'zip',
                                'soft1': 'zip',
                                'zpf': 'zip',
                                'epb': 'epub',
                            })[type]
                            d['_'.join([yr, mo, st, lng])+'.'+ext] = simpleDownloader.getUrlBytes(dwn)
        return d

    def cached_all(self) -> Dict[str, Path]:
        outdir = type(self).cachedir.joinpath(self._identifier)
        outdir.mkdir(parents=True, exist_ok=True)
        cached_all = outdir.joinpath('complete.flag')
        if not cached_all.exists():
            for file, content in self.download_all().items():
                outdir.joinpath(file).write_bytes(content)
            cached_all.touch(exist_ok=True)
        out = dict()
        for file in outdir.glob('*'):
            if not file.is_file() or file.name == cached_all.name:
                continue
            out[file.name] = file
        return out

    def cached(self) -> Optional[Path]:
        all_cached = self.cached_all()
        candidates = sorted(
            [
                (int(it[0]), int(it[1]), it[2], it[3], it[4])
                for it in [
                    (
                        *it.name.split('.', 1)[0].split('_'),
                        it.name.split('.', 1)[1],
                    )
                    for it in all_cached.values()
                ]
            ],
            key=lambda a: (
                type(self).extorder.index(a[4]),
                type(self).langorder.index(a[3]),
                -a[0],
                -a[1],
                int(a[2]),
            )
        )
        done = False
        if self._revision is not None:
            yr = self._revision[0]
            mo = self._revision[1]
            filtered = list(filter(
                lambda cand: (int(cand[0]) == int(yr)) if (int(mo) > 12) else (int(cand[0]) == int(yr) and int(cand[1]) == int(mo)),
                candidates
            ))
            if len(filtered) > 0:
                candidates = filtered
                done = True
        if self._citing_date is not None and not done:
            yr = self._citing_date[0]
            mo = self._citing_date[1]
            filtered = list(filter(
                lambda cand: (int(cand[0]), int(cand[1])) <= (int(yr), int(mo)),
                candidates
            ))
            if len(filtered) > 0:
                candidates = filtered
        if len(candidates) == 0:
            return None
        else:
            return all_cached['%02d_%02d_%s_%s.%s' % candidates[0]]

    def is_cached(self) -> bool:
        outdir = type(self).cachedir.joinpath(self._identifier)
        cached_all = outdir.joinpath('complete.flag')
        return cached_all.exists()

    def slowness(self) -> int: return 9

    def context(self, path: Path) -> Dict[str, str]:
        return {'citing_date': '-'.join(path.name.split('_', 2)[:2])}


class ISOStandard(OnlineStandard):
    cachedir = Path('cache', 'iso')


def find_references(text: str, context: Optional[Dict[str, str]] = None) -> List[OnlineStandard]:
    refs = list()
    for match in rgx_itu.finditer(text):
        groups = list(match.groups())
        rec = groups[1].strip('\t\n -.,')
        fixmatch = rgx_itu_fix.match(rec)
        if fixmatch is not None:
            fixgroups = fixmatch.groups()
            groups[1] = fixgroups[0]
            groups[2] = fixgroups[1]
            rec = groups[1].strip('\t\n -.,')
        if '..' in rec or '--' in rec or '.-' in rec or '-.' in rec:
            continue
        yr = None
        mo = None
        rev = None
        if groups[2] is not None:
            yr = expand_year(groups[2].split('/')[-1])
            if '/' in groups[2]:
                mo = groups[2].split('/')[-2]
        if yr is not None:
            if mo is not None:
                rev = "%04d-%02d" % (int(yr), int(mo))
            else:
                rev = "%04d" % (int(yr),)
        refs.append(ITURecommendation(rec, rev, **context))
    for match in rgx_rfc.finditer(text):
        rfcno = match.groups()[1]
        refs.append(RFCStandard(str(int(rfcno)), **context))
    for match in rgx_iso.finditer(text):
        groups = match.groups()
        nm = groups[2]
        yr = None if groups[3] is None else expand_year(groups[3])
        nm = nm.strip('\t\n -.,')
        if len(nm) == 0:
            continue
        refs.append(ISOStandard(nm, yr, **context))
    return refs


classes['itu'] = ITURecommendation
classes['rfc'] = RFCStandard
classes['iso'] = ISOStandard

__all__ = [
    'classes',
    'find_references',
]
