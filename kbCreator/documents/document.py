#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from os import linesep as eol
import re

toc_line_regex = re.compile(r'.+(\s*?[\.]){6,}\s*\d+')
toc_line_parsing_regex = re.compile(r'^\s*?((?:(?:[^\s\.]+?)(?:[\s\.])?)+?)[-–\s]+(.*?)(?:\s*\.)+\s+([\divxdcm]+)$', re.I | re.M | re.S)


def get_possible_header_from_text(ll):
    if len(ll) <= 0:
        return "", ""
    return ll[0].strip(), ll[1:]


def get_possible_header(ll):
    return get_possible_header_from_text(ll)[0]


def get_possible_footer_from_text(ll):
    if len(ll) <= 0:
        return "", ""
    return ll[-1].strip(), ll[:-1]


def get_possible_footer(ll):
    return get_possible_footer_from_text(ll)[0]


def get_middle_sample(dp):
    return dp[1*(len(dp)//4): 3*(len(dp)//4)]


def find_header_footer_ignorable_part(samples, not_found=""):
    if len(samples) <= 0:
        return not_found
    intersection = set(samples[0].split())
    for sample in samples:
        intersection.intersection_update(sample.split())
    if len(intersection) == 0:
        return not_found
    part_ranges = list(zip(*[(i[0], i[0]+i[1]) for i in [(samples[0].find(part), len(part)) for part in intersection]]))
    ignoreable = samples[0][min(part_ranges[0]):max(part_ranges[1])]
    for sample in samples:
        if ignoreable not in sample:
            return not_found
    return ignoreable


def strip_empty_lines(page):
    start = 0
    stop = len(page)
    for i, line in enumerate(page):
        if line.strip() == '':
            start = i
        else:
            break
    for i, line in reversed(list(enumerate(page))):
        if line.strip() == '':
            stop = i+1
        else:
            break
    return page[start:stop]


def cleanup_page_from_header_and_footer(pages, ignorable_header, ignorable_footer):
    cleaned = list()
    for brute_page in pages:
        useful_header = ""
        useful_footer = ""
        page = brute_page
        if ignorable_header != "":
            pntp, ptp = get_possible_header_from_text(page)
            if ignorable_header in pntp:
                useful_header = pntp.replace(ignorable_footer, "").strip()
                page = ptp
        if ignorable_footer != "":
            pntp, ptp = get_possible_footer_from_text(page)
            if ignorable_footer in pntp:
                useful_footer = pntp.replace(ignorable_footer, "").strip()
                page = ptp
        page = strip_empty_lines(page)
        cleaned.append((page, useful_header, useful_footer))
    return cleaned


def parse_toc(pages):
    toc = list()
    for page in pages:
        page_content = '\n'.join(page[0]).split('\n'*3)[0]
        while page_content.startswith(' '*20):
            page_content = '\n'.join(page_content.splitlines()[1:])
        for match in toc_line_parsing_regex.finditer(page_content):
            toc.append((
                match[1].strip().strip('.'),
                ' '.join(match[2].replace('\n', ' ').split()).strip(),
                match[3].strip()
            ))
    return toc


def get_textual_part_default(pages):
    return (pages, list())


def get_textual_part_handling_toc(pages, toc_page):
    current_page = toc_page
    while(toc_line_regex.search('\n'.join(pages[current_page][0]))):
        current_page += 1
        if current_page >= len(pages):
            return None
    toc_pages = pages[toc_page: current_page]
    textual_part = pages[current_page:]
    return (textual_part, parse_toc(toc_pages))


def get_textual_part_from_header_and_footer(pages):
    return (list(filter(lambda a: (a[1].strip().isdigit() or a[2].strip().isdigit()), pages)), list())


def get_textual_part(pages, has_header, has_footer, toc_names):
    for i, page in enumerate(pages):
        possible_title = get_possible_header(page[0])
        if possible_title.strip().lower() in toc_names:
            option = get_textual_part_handling_toc(pages, i)
            if option is None:
                break
            else:
                return option
    if has_header or has_footer:
        return get_textual_part_from_header_and_footer(pages)
    return get_textual_part_default(pages)


def fix_paragraphs(lines):
    fixed = list()
    buff = ''
    for line in lines+[None]:
        if line is None:
            if len(buff) <= 0:
                fixed.append(buff+'.' if not (buff.endswith('.') or buff.endswith(';') or buff.endswith(':')) else buff)
                buff = ''
        elif len(line.strip()) <= 0:
            if len(buff) > 0:
                fixed.append(buff+'.' if not (buff.endswith('.') or buff.endswith(';') or buff.endswith(':')) else buff)
                buff = ''
        else:
            ls = line.strip()
            if buff.endswith('-'):
                buff = buff+ls
            elif len(buff) >= 2 and buff[-2].isdigit() and buff[-1] == ')':
                buff += ' '+ls
            elif len(ls) >= 2 and (ls[0].islower() or (ls[0].isupper() and ls[1].isupper())) and ls[0].isalpha() and (ls[1].isalpha() or ls[1].isspace()):
                buff += ' '+ls
            else:
                if len(buff) > 0:
                    fixed.append(buff+'.' if not (buff.endswith('.') or buff.endswith(';') or buff.endswith(':')) else buff)
                buff = ls
    return [' '.join(ln.split()) for ln in fixed]


class Document(object):
    @classmethod
    def _opens(cls):
        return []

    def _set_document_pages(self, pages):
        self._document_pages = pages

    def __init__(self):
        # self.has_cover = True
        # self.has_cover_sheet = True
        self.detect_number_on_first_page = True
        # self.has_pretextual_elements = True
        # self.entities_to_find = ['table', 'figure', 'image', 'chart']
        self.toc_names = ['contents', 'index', 'table of contents']
        # self.has_header = False
        # self.has_footer = True
        # self.has_tables = True

    def parse(self, cst_eol=eol):
        pages = list(map(str.splitlines, self._document_pages))
        sample_pages = get_middle_sample(pages)
        ignorable_header = find_header_footer_ignorable_part(list(map(get_possible_header, sample_pages)))
        ignorable_footer = find_header_footer_ignorable_part(list(map(get_possible_footer, sample_pages)))
        del sample_pages
        cleaned_pages = list(
            filter(lambda a: len(a[0]) > 0,
                   map(lambda a: (a[1][0], a[1][1], a[1][2], a[0]),
                       enumerate(cleanup_page_from_header_and_footer(pages, ignorable_header, ignorable_footer))
                       )))
        textual_part = get_textual_part(cleaned_pages, ignorable_header != "", ignorable_footer != "", self.toc_names)
        del ignorable_header
        del ignorable_footer
        del cleaned_pages
        joined_pages = cst_eol.join(fix_paragraphs(eol.join(map(lambda a: eol.join(a[0]), textual_part[0])).splitlines()))
        return joined_pages
        # for part in textual_part:
        #     print(part)
        # print(cleaned_page_contents)
        # print(sample_pages)
