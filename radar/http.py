# -*- coding: utf-8 -*-
"""Ag katmani - SADECE standart kutuphane.

Neden bagimlilik yok: GitHub Actions'ta `pip install` adimi olmayinca
kosu daha hizli ve kirilma yuzeyi daha kucuk. requests/bs4 gerekmedi.
"""
import gzip
import hashlib
import io
import os
import re
import ssl
import time
import urllib.error
import urllib.request
import zlib

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36 SogukRadar/3.0 (+haber tarayici; yassi celik)")

# Bazi kurumsal siteler (Cloudflare) veri merkezi IP'lerinden gelen
# "yalin" istekleri 403 ile geri ceviriyor. Asagidaki basliklar gercek bir
# tarayicinin gonderdiklerinin aynisi; bu 403'lerin bir kismini acar.
# Acmayanlar rapordaki KOR NOKTA listesinde acikca gorunur.
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
              "image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-CH-UA": '"Chromium";v="124", "Not:A-Brand";v="99"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Linux"',
    "Cache-Control": "max-age=0",
    "Connection": "close",
}

TIMEOUT = int(os.environ.get("RADAR_TIMEOUT", "25"))
RETRIES = int(os.environ.get("RADAR_RETRIES", "2"))
PAUSE = float(os.environ.get("RADAR_PAUSE", "0.7"))     # ayni sunucuya nazik ol
CACHE_DIR = os.environ.get("RADAR_CACHE", "")
CACHE_TTL = int(os.environ.get("RADAR_CACHE_TTL", "21600"))   # 6 saat

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE   # bazi tedarikci sitelerinde zincir eksik

_last_hit = {}


def _cache_path(url):
    if not CACHE_DIR:
        return None
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, hashlib.sha1(url.encode()).hexdigest() + ".html")


def _decompress(raw, enc):
    if enc == "gzip":
        try:
            return gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except Exception:
            return raw
    if enc == "deflate":
        try:
            return zlib.decompress(raw)
        except Exception:
            try:
                return zlib.decompress(raw, -zlib.MAX_WBITS)
            except Exception:
                return raw
    return raw


def _charset(headers, raw):
    ct = headers.get("Content-Type", "") if headers else ""
    m = re.search(r"charset=([\w\-]+)", ct, re.I)
    if m:
        return m.group(1)
    m = re.search(rb'charset=["\']?([\w\-]+)', raw[:4000], re.I)
    if m:
        try:
            return m.group(1).decode("ascii")
        except Exception:
            pass
    return "utf-8"


def _throttle(url):
    host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    last = _last_hit.get(host, 0)
    wait = PAUSE - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.time()


def fetch(url, use_cache=True):
    """(ok, text, info) doner. info: {'status':..,'final':..,'hata':..,'cache':bool}"""
    cp = _cache_path(url) if use_cache else None
    if cp and os.path.exists(cp) and (time.time() - os.path.getmtime(cp)) < CACHE_TTL:
        with open(cp, encoding="utf-8", errors="replace") as f:
            return True, f.read(), {"status": 200, "final": url, "cache": True}

    err = None
    for attempt in range(RETRIES + 1):
        try:
            _throttle(url)
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ctx) as r:
                raw = r.read()
                raw = _decompress(raw, (r.headers.get("Content-Encoding") or "").lower())
                text = raw.decode(_charset(r.headers, raw), errors="replace")
                info = {"status": r.status, "final": r.geturl(), "cache": False}
            if cp:
                try:
                    with open(cp, "w", encoding="utf-8") as f:
                        f.write(text)
                except Exception:
                    pass
            return True, text, info
        except urllib.error.HTTPError as e:
            err = "HTTP %s" % e.code
            if e.code in (403, 404, 410):
                break                      # tekrar denemek anlamsiz
        except Exception as e:
            err = type(e).__name__ + ": " + str(e)[:120]
        time.sleep(1.2 * (attempt + 1))
    return False, "", {"status": 0, "final": url, "hata": err, "cache": False}
