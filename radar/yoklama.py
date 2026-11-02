# -*- coding: utf-8 -*-
"""KAPALI KAYNAK YOKLAMASI - iyi yayincilarin RESMI acik kapilarini olcer.

2026-11-02 kullanici: "iyi kaynaklara da girme yolu bul". Steel Times, SMS,
ArcelorMittal, BigMint, Kallanish vb. makale sayfalarinda bot korumasi (403)
var. Korumayi ASMAK yerine yayincinin kendi yayimladigi makine kapilari
denenir: RSS/Atom, WordPress REST API, haber sitemap'i, robots.txt'deki
sitemap'ler. Sonuc out/yoklama.json'a yazilir; calisan kapi kaynak listesine
eklenir. Bu modul hicbir seyi havuza/hafizaya yazmaz.
"""
import json
import os
import re
from urllib.parse import urlparse

from . import http

YOLLAR = ["/feed/", "/feed", "/rss", "/rss.xml", "/rss/", "/news/rss", "/news/feed/",
          "/en/rss", "/feeds/posts/default", "/atom.xml", "/index.xml",
          "/wp-json/wp/v2/posts?per_page=5&_fields=date,link,title",
          "/news-sitemap.xml", "/sitemap_news.xml", "/sitemap-news.xml",
          "/post-sitemap.xml", "/sitemap_index.xml", "/sitemap.xml", "/robots.txt"]

ALANLAR = ["https://www.steeltimesint.com", "https://www.sms-group.com",
           "https://corporate.arcelormittal.com", "https://www.bigmint.co",
           "https://www.kallanish.com", "https://www.furnaces-international.com",
           "https://www.metalformingmagazine.com", "https://sanayigazetesi.com.tr",
           "https://www.steelradar.com", "https://www.steelguru.com",
           "https://www.steelorbis.com", "https://www.cognex.com",
           "https://www.primetals.com", "https://www.danieli.com", "https://www.tenova.com",
           "https://www.fivesgroup.com", "https://johncockerill.com",
           "https://www.andritz.com", "https://gmk.center", "https://www.yieh.com",
           "https://www.eurofer.eu", "https://www.fastmarkets.com", "https://www.mysteel.net",
           "https://www.steel-plantech.co.jp", "https://www.redbudindustries.com",
           "https://www.danieli-wean.com", "https://www.stamco.co.jp",
           "https://www.ims-gmbh.de", "https://www.isra-vision.com", "https://www.parsytec.de",
           "https://www.achenbach.de", "https://www.bwg-online.com", "https://www.drever.be",
           "https://www.ebner.cc", "https://www.loi-italimpianti.com", "https://www.steelplantech.com",
           "https://www.siemens.com", "https://www.abb.com", "https://www.vdeh.de",
           "https://www.aist.org", "https://www.worldsteel.org", "https://www.steelnews.biz",
           "https://www.metalbulletin.com", "https://www.dunya.com", "https://www.ekonomim.com"]

_TARIH = re.compile(r"(20\d\d-\d\d-\d\d)")


def _ozet(metin, yol):
    m = metin or ""
    n_item = len(re.findall(r"<item[\s>]", m)) + len(re.findall(r"<entry[\s>]", m))
    n_url = len(re.findall(r"<loc>", m))
    tarihler = sorted(set(_TARIH.findall(m)))
    tur = ("wp-json" if "wp-json" in yol and m.strip().startswith("[") else
           "rss" if n_item else "sitemap" if n_url else
           "robots" if yol.endswith("robots.txt") and "sitemap" in m.lower() else "")
    return {"tur": tur, "oge": n_item, "url": n_url,
            "en_yeni": tarihler[-1] if tarihler else "",
            "sitemaps": re.findall(r"(?im)^sitemap:\s*(\S+)", m)[:6] if "robots" in yol else []}


def _al(url):
    """Tek deneme, kisa zaman asimi, yeniden deneme YOK (yoklama hizli olmali)."""
    import urllib.request, urllib.error
    try:
        req = urllib.request.Request(url, headers=http.HEADERS)
        with urllib.request.urlopen(req, timeout=12, context=http._ctx) as r:
            raw = r.read(3_000_000)
            raw = http._decompress(raw, (r.headers.get("Content-Encoding") or "").lower())
            return True, raw.decode("utf-8", "replace"), {"final": r.geturl()}
    except urllib.error.HTTPError as e:
        return False, "", {"hata": "HTTP %s" % e.code}
    except Exception as e:
        return False, "", {"hata": type(e).__name__}


def _alan(kok):
    bulunan, kapali = [], 0
    ok, _, info = _al(kok + "/")
    ana = "acik" if ok else info.get("hata")
    for y in YOLLAR:
        ok, metin, info = _al(kok + y)
        if not ok:
            if info.get("hata") in ("HTTP 403", "HTTP 429"):
                kapali += 1
                if kapali >= 6:          # tum alan kapali: bosuna istek atma
                    break
            continue
        oz = _ozet(metin, y)
        if oz["tur"]:
            oz["adres"] = info.get("final") or kok + y
            bulunan.append(oz)
    for b in [b for b in bulunan if b["tur"] == "robots"]:
        for sm in b["sitemaps"][:3]:
            ok, metin, info = _al(sm)
            if ok:
                oz = _ozet(metin, sm)
                if oz["tur"]:
                    oz["adres"] = sm
                    bulunan.append(oz)
    return urlparse(kok).netloc, {"ana_sayfa": ana,
                                  "kapilar": [b for b in bulunan if b["tur"] != "robots"]}


def yokla(log=print):
    from concurrent.futures import ThreadPoolExecutor
    sonuc = {}
    os.makedirs("out", exist_ok=True)
    with ThreadPoolExecutor(max_workers=10) as ex:
        for ad, k in ex.map(_alan, ALANLAR):
            sonuc[ad] = k
            log("%-34s ana:%-10s %s" % (ad, str(k["ana_sayfa"])[:10],
                ", ".join("%s(%s %s) %s" % (b["tur"], b["oge"] or b["url"], b["en_yeni"],
                                             b["adres"][-45:]) for b in k["kapilar"][:4]) or "-"),
                flush=True)
            with open("out/yoklama.json", "w", encoding="utf-8") as f:
                json.dump(sonuc, f, ensure_ascii=False, indent=1)
    return sonuc
