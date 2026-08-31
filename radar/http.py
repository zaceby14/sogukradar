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


# ------------------------------------------------------------------ #
# HOST KORUMASI - AYNI HATAYI IKI KEZ YAPTIM, UCUNCUSU OLMASIN.
#
# 2026-08-31'de iki gerileme de ayni sebeptendi: PAYLASILAN BIR HOST'A
# FAZLADAN ISTEK GONDERDIM VE FATURAYI BASKA BIR IS ODEDI.
#   1) Sitemap zinciri gercek istegin ONUNE gecti; tahmin adresleri 404
#      alinca site kapiyi kapatti ve BES kaynak (ABB Metals, Nippon Steel,
#      China Baowu, SteelGuru, Kocks) v19 oncesinde ACILIRKEN erisilemez
#      oldu.
#   2) Tarih dogrulamak icin news.google.com'a 40 ek istek attim. O host'ta
#      169 kaynagin 80'i duruyor. Google 503 dondu, erisilemeyen kaynak
#      9'dan 89'a cikti, kazanc SIFIR oldu ve kosu 35 dakikadan 60 dakikaya
#      uzadi.
#
# Ders yamayla ogrenilmez, YAPISAL olarak zorlanir. Iki kural:
#   - Her host icin kosu basina istek BUTCESI vardir. Butce dolunca istek
#     GONDERILMEZ; hangi is isterse istesin.
#   - Bir host hiz siniri sinyali (429/503) dondurdugunde SOGUTMAYA alinir.
#     Israr etmek yumusak kisitlamayi sert bloga cevirir - dun tam bu oldu.
#
# Boylece yeni bir katman eklemek artik mevcut katmani riske atamaz; en
# kotu ihtimalle yeni katman kendi butcesini tuketir.
# ------------------------------------------------------------------ #
HOST_BUTCE = int(os.environ.get("RADAR_HOST_BUTCE", "140"))
SOGUTMA_SN = int(os.environ.get("RADAR_SOGUTMA", "600"))
HIZ_SINIRI = (429, 503, 502, 504)

_host_sayac = {}
_host_sogutma = {}      # host -> ne zamana kadar sogutmada
_host_uyari = {}        # host -> kac kez hiz siniri gordu


def host_of(url):
    return re.sub(r"^https?://([^/]+).*$", r"\1", url or "").lower()


def host_raporu():
    """Kosu sonunda gorunur olsun - sessiz kisitlama en kotusudur."""
    hepsi = set(_host_sayac) | set(_host_uyari) | set(_host_sogutma)
    out = {}
    for h in sorted(hepsi, key=lambda h: -_host_sayac.get(h, 0)):
        n = _host_sayac.get(h, 0)
        if n <= 20 and not _host_uyari.get(h):
            continue
        out[h] = {"istek": n,
                  "hiz_siniri": _host_uyari.get(h, 0),
                  "sogutmada": _host_sogutma.get(h, 0) > time.time()}
    return out


def host_sifirla():
    _host_sayac.clear()
    _host_sogutma.clear()
    _host_uyari.clear()


def host_izin(url):
    """(izin_var_mi, sebep). Istek GONDERILMEDEN once sorulur."""
    h = host_of(url)
    if _host_sogutma.get(h, 0) > time.time():
        return False, "host sogutmada"
    if HOST_BUTCE and _host_sayac.get(h, 0) >= HOST_BUTCE:
        return False, "host butcesi doldu"
    return True, None


def _host_kaydet(url):
    """Gonderilen her istek sayilir - basarili da basarisiz da."""
    h = host_of(url)
    _host_sayac[h] = _host_sayac.get(h, 0) + 1


def _host_hiz_siniri(url):
    """Hiz siniri sinyali: ilk sinyalde uyar, ikincide kosu boyu sogut.

    Hiz siniri bir RICADIR; israr etmek onu yasaga cevirir. 2026-08-31'de
    news.google.com'a israr edilince 80 kaynak birden HTTP 503'e dustu.
    """
    h = host_of(url)
    _host_uyari[h] = _host_uyari.get(h, 0) + 1
    if _host_uyari[h] >= 2:
        _host_sogutma[h] = time.time() + SOGUTMA_SN


def _throttle(url):
    host = host_of(url)
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

    izin, sebep = host_izin(url)
    if not izin:
        return False, "", {"status": 0, "final": url, "hata": sebep, "cache": False}

    err = None
    for attempt in range(RETRIES + 1):
        try:
            _throttle(url)
            _host_kaydet(url)
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ctx) as r:
                raw = r.read()
                raw = _decompress(raw, (r.headers.get("Content-Encoding") or "").lower())
                text = raw.decode(_charset(r.headers, raw), errors="replace")
                info = {"status": r.status, "final": r.geturl(), "cache": False,
                        "last_modified": r.headers.get("Last-Modified") or ""}
            if cp:
                try:
                    with open(cp, "w", encoding="utf-8") as f:
                        f.write(text)
                except Exception:
                    pass
            return True, text, info
        except urllib.error.HTTPError as e:
            err = "HTTP %s" % e.code
            if e.code in HIZ_SINIRI:
                _host_hiz_siniri(url)
            if e.code in (403, 404, 410):
                break                      # tekrar denemek anlamsiz
            if e.code in HIZ_SINIRI:
                break                      # HIZ SINIRINDA ISRAR EDILMEZ
        except Exception as e:
            err = type(e).__name__ + ": " + str(e)[:120]
        time.sleep(1.2 * (attempt + 1))
    return False, "", {"status": 0, "final": url, "hata": err, "cache": False}
