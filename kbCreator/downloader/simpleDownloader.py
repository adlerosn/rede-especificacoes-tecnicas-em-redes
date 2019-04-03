#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import time
import urllib.parse
import urllib.request
import urllib.error

cookie = dict()
firefox_version = '65.0.2'


def delCookie(cookiekey):
    cookiekey = str(cookiekey)
    if cookiekey in cookie:
        del cookie[cookiekey]


def setCookie(cookiekey, cookieval):
    cookieval = str(cookieval)
    cookiekey = str(cookiekey)
    if not cookiekey:
        return
    if not cookieval:
        delCookie(cookiekey)
    cookie[cookiekey] = cookieval


def getCookies():
    return dict(cookie.items())


def patchCookies(newCookies):
    for nk, nv in newCookies.items():
        setCookie(nk, nv)


def cleanCookies():
    global cookie
    cookie = dict()


def setCookies(newCookies):
    cleanCookies()
    patchCookies(newCookies)


def getUrlBytes(url, giveUpOn403=False):
    global cookie
    request = urllib.request.Request(url)
    try:
        url.encode('ascii')
    except:
        request = urllib.request.Request(urllib.parse.quote(url, safe='/%?#:'))
    request.add_header('User-Agent', f'Mozilla/5.0 (X11; Linux x86_64; rv:{firefox_version}) ' +
                                     f'Gecko/20100101 Firefox/{firefox_version}'
                       )
    if len(cookie):
        request.add_header("Cookie", '; '.join(map(lambda a: '='.join(a), cookie.items())))
    response = None
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print('[URL] Got 429 (Too Many Requests): sleeping for 5 seconds')
            print('  @   %s' % url)
            time.sleep(5)
            return getUrlBytes(url)
        if e.code == 503:
            print('[URL] Got 503 (Service Temporarily Unavailable): retrying after 5 seconds')
            print('  @   %s' % url)
            time.sleep(5)
            return getUrlBytes(url)
        if e.code == 403 and giveUpOn403:
            print('[URL] Got 403 (Forbidden): assuming "Not Found"')
            print('  @   %s' % url)
            return None
        elif e.code == 500:
            print('[URL] Got 500 (Server Error): assuming "Not Found"')
            return None
        elif e.code == 404:
            return None
        elif e.code == 400:
            return None
        raise e
    except urllib.error.URLError as e:
        if str(e.reason).startswith('EOF occurred in violation of protocol ('):
            print('Server doesn\'t know how to use HTTP properly - assuming "Not Found"')
            return None
        if str(e.reason).startswith('[SSL: CERTIFICATE'):
            print('Their SSL certificate is screwed up - assuming "Not Found"')
            return None
        if str(e.reason).startswith('[Errno -5]'):
            print('Their DNS server is screwed up - assuming "Not Found"')
            return None
        if str(e.reason).startswith('[Errno -2]'):
            return None
        if str(e.reason).startswith('[Errno -3]'):
            print('Check your internet connection. It seems gone.')
        if str(e.reason).startswith('[Errno 110]') or str(e.reason) == 'timed out':
            print('Connection request has timed out - assuming "Not Found"')
            return None
        if str(e.reason).startswith('[Errno 111]') or str(e.reason) == 'timed out':
            print('Connection refused - assuming "Not Found"')
            return None
        raise e
    rcode = response.getcode()
    rinfo = response.info()
    headers = dict()
    headers_l = list(map(lambda a: list(map(str.strip, a.split(':', 1))), str(rinfo).strip().splitlines()))
    for header in headers_l:
        k = header[0].lower()
        v = header[1]
        if k not in headers:
            headers[k] = list()
        headers[k].append(v)
        del k
        del v
        del header
    del headers_l
    if 'set-cookie' in headers:
        for cke in headers['set-cookie']:
            ckek = cke.split('=', 1)[0].strip()
            ckev = cke.split('=', 1)[1].split(';', 1)[0].strip()
            setCookie(ckek, ckev)
            del ckek
            del ckev
            del cke
    if rcode == 429:
        tosleep = 5
        try:
            tosleep = int(headers['retry-after'][0])
        except:
            pass
        if tosleep < 1:
            tosleep = 1
        print('[URL] Got 429 (Too Many Requests): sleeping for %d seconds' % tosleep)
        print('  @   %s' % url)
        time.sleep(tosleep)
        return getUrlBytes(url)
    data = None
    if rcode == 200:
        data = response.read()
    response.close()
    return data


def getUrl(url):
    return getUrlBytes(url).decode('utf-8')
