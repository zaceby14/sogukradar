# -*- coding: utf-8 -*-
"""Google News yonlendirmesi yerine YAYINCININ adresini bulur (2026-11-21).

NEDEN: bultende bazi maddeler news.google.com/rss/articles/... adresiyle
gidiyordu. Bu adresler sifreli; sistem sayfayi acip dogrulayamiyordu
(baglanti.py atliyordu) ve okuyucu yayinciyi gormeden tikliyordu.

YONTEM: haber basligi, sistemin zaten kullandigi herkese acik Bing News RSS
aramasinda tirnak icinde aranir. Bing beslemesindeki adres yayincinin
adresini acikca tasir (collect.temiz_adres). YALNIZ basligi neredeyse ayni
olan sonuc kabul edilir; bulunamazsa adres OLDUGU GIBI kalir.
"""
import re
import urllib.parse as _up

from . import feeds, http, taxonomy


def _gn_mi(url):
    return "news.google.com" in (url or "")


def _sozler(metin):
    f = taxonomy.fold(re.sub(r"\s+-\s+[^-]{2,60}$", "", metin or ""))
    return [w for w in re.findall(r"[a-z0-9]+", f) if len(w) > 2]


def ayni_baslik(a, b):
    """Iki baslik ayni haber mi - siki olcu: kisa olanin sozcuklerinin %80'i."""
    sa, sb = _sozler(a), _sozler(b)
    if len(sa) < 3 or len(sb) < 3:
        return False
    kisa, uzun = (sa, set(sb)) if len(sa) <= len(sb) else (sb, set(sa))
    return sum(1 for w in kisa if w in uzun) >= 0.8 * len(kisa)


def bul(baslik, fetch=None):
    """Basligin yayinci adresini dondurur; bulunamazsa None."""
    from .collect import temiz_adres
    fetch = fetch or http.fetch
    temiz = re.sub(r"\s+-\s+[^-]{2,60}$", "", baslik or "").strip()
    if len(temiz) < 15:
        return None
    u = ("https://www.bing.com/news/search?q=" + _up.quote('"%s"' % temiz[:150])
         + "&format=RSS&setmkt=en-US")
    try:
        ok, page, _ = fetch(u)
    except Exception:
        return None
    if not ok or not page:
        return None
    for it in feeds.parse_feed(page):
        adres = temiz_adres(it.get("url", ""))
        # MSN/Yahoo da toplayicidir (2026-11-21: Jindal -> msn.com, sayfa bos)
        if not adres.startswith("http") or taxonomy.TOPLAYICI.search(adres):
            continue
        if ayni_baslik(temiz, it.get("title", "")):
            return adres
    return None


def degistir(maddeler, alan="baslik", log=print, fetch=None):
    """Google News adresli maddelerin adresini yayinci adresiyle degistirir.
    Eski adres 'url_toplayici' alanina yazilir. Degisen madde sayisini dondurur."""
    n = 0
    for m in maddeler or []:
        if not _gn_mi(m.get("url")):
            continue
        b = m.get(alan) or m.get("baslik") or m.get("konu") or ""
        yeni = bul(b, fetch=fetch)
        if yeni:
            m["url_toplayici"] = m["url"]
            m["url"] = yeni
            n += 1
            log("  yayinci adresi bulundu: %s -> %s" % (b[:50], yeni[:80]))
        else:
            log("  yayinci adresi bulunamadi (Google News adresi kalir): %s" % b[:60])
    return n
