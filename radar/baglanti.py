# -*- coding: utf-8 -*-
"""BAGLANTI DOGRULAMA - postaya girecek her satirin adresi bir kez daha acilir.

NEDEN (2026-11-02, kullanici: "ilk link hatali, primetals olan"). W45
denemesinde Primetals satiri bozuk bir adresle ve BUGUNUN tarihiyle cikti:
sitemap'ten gelen aday, sayfa acildi ama gercek bir haber icermiyordu
(yer tutucu/404 sablonu), tarih sunucunun Last-Modified basligindan "bugun"
okundu. Taramadaki kapilar bunu gecirdi; okuyucu tikladiginda bos sayfa gordu.

KURAL - bir satir YALNIZ su durumlarda CIKARILIR (kanit varsa):
  - adres 404/410 dondurdu,
  - ana sayfaya ya da liste sayfasina yonlendirildi,
  - sayfa acildi ama satirin basligindaki ayirt edici sozcuklerin yeterli bolumu
    sayfada YOK (baska/yer tutucu icerik).
Dogrulanamayanlar (403/429/zaman asimi/host sogutmada) CIKARILMAZ: kapali
yayincilarin bot korumasi kanit degildir; bunlar karar.json'da "dogrulanamadi"
olarak listelenir. Haber toplayici (Google/Bing) yonlendirme adresleri
acilmaz - tarayici onlari kendisi cozer.
"""
import re
from urllib.parse import urlparse

from . import htmlx, http, taxonomy

fetch = http.fetch          # testlerde sahtesiyle degistirilir

_ATLA = ("news.google.com", "bing.com/news", "msn.com", "/rss/articles/")
_DURDURMA = {"with", "from", "that", "this", "will", "into", "line", "lines", "steel",
             "plant", "mill", "new", "for", "and", "the", "its", "to", "of", "in", "at",
             "on", "by", "a", "an"}


def _sozcukler(metin):
    f = taxonomy.fold(metin or "")
    return {w for w in re.findall(r"[a-z0-9]{4,}", f) if w not in _DURDURMA}


def _kok_ya_da_liste(url, son):
    """Satir bir HABER adresi iken sunucu ana sayfa/liste sayfasina atmis mi."""
    p0, p1 = urlparse(url), urlparse(son or url)
    y0 = [s for s in p0.path.split("/") if s]
    y1 = [s for s in p1.path.split("/") if s]
    if not y1 and y0:
        return True
    return len(y0) >= 2 and len(y1) <= 1 and y1 != y0[:1] and p0.netloc == p1.netloc


def kontrol(r):
    """(durum, neden). durum: 'tamam' | 'kotu' | 'dogrulanamadi' | 'atlandi'."""
    url = r.get("url") or ""
    if any(a in url.lower() for a in _ATLA) or taxonomy.TOPLAYICI.search(url.lower()):
        return "atlandi", "toplayici adresi"
    ok, page, info = fetch(url)
    if not ok:
        hata = str(info.get("hata") or "")
        if re.search(r"HTTP (404|410)", hata):
            return "kotu", "adres yok (%s)" % hata
        return "dogrulanamadi", hata or "acilamadi"
    if _kok_ya_da_liste(url, info.get("final")):
        return "kotu", "ana/liste sayfasina yonlendirildi: %s" % info.get("final", "")[:80]
    doc = htmlx.parse_article(page)
    sayfa = _sozcukler((doc.get("title") or "") + " " + (doc.get("text") or "")[:2500])
    baslik = _sozcukler(r.get("baslik"))
    if len(baslik) >= 3:
        ortak = len(baslik & sayfa)
        if ortak < max(2, int(0.4 * len(baslik))):
            return "kotu", ("sayfa baska icerik gosteriyor (ortak sozcuk %d/%d)"
                            % (ortak, len(baslik)))
    # TARIH TUTARLILIGI (2026-11-21): sayfa kendi yayin tarihini beyan ediyorsa
    # maddenin tarihiyle 7 gunden fazla farkli olamaz (yanlis/eski haber).
    sayfa_t = _sayfa_tarihi(doc)
    if sayfa_t and r.get("tarih"):
        try:
            import datetime as _dt
            fark = abs((_dt.date.fromisoformat(sayfa_t) - _dt.date.fromisoformat(r["tarih"][:10])).days)
            if fark > 7:
                return "kotu", "sayfa tarihi %s, madde tarihi %s" % (sayfa_t, r["tarih"][:10])
        except ValueError:
            pass
    return "tamam", ""


def _sayfa_tarihi(doc):
    """Sayfanin beyan ettigi YAYIN tarihi (json-ld datePublished / article:published_time)."""
    for d in doc.get("jsonld_dates") or []:
        if isinstance(d, dict) and d.get("key") == "datePublished":
            m = re.match(r"(\d{4}-\d{2}-\d{2})", str(d.get("value") or ""))
            if m:
                return m.group(1)
    for k, v in (doc.get("meta") or {}).items():
        if "published_time" in k or k in ("datepublished", "pubdate"):
            m = re.match(r"(\d{4}-\d{2}-\d{2})", str(v or ""))
            if m:
                return m.group(1)
    return None


def maddeleri_dogrula(maddeler, alan="baslik", log=print):
    """Teknoloji/piyasa ADAYLARI icin ayni kapi (2026-11-21, kullanici: kontroller
    tek seferlik olmasin, her duruma uysun). Toplayici adresi once yayinci
    adresine cevrilir; kotu (404, baska icerik, tarih uyusmazligi) aday dusulur.
    -> (kalan, elenen[(baslik, neden)])"""
    from . import yayinci
    yayinci.degistir(maddeler, alan=alan, log=log)
    kalan, elenen = [], []
    for m in maddeler or []:
        b = m.get(alan) or m.get("baslik") or ""
        durum, neden = kontrol(dict(m, baslik=b))
        if durum == "kotu":
            elenen.append((b, "baglanti: " + neden))
            log("  aday baglantisi kotu (%s): %s" % (neden, b[:60]))
            continue
        kalan.append(m)
    return kalan, elenen


def dogrula(rows, log=print):
    """-> (kalan_satirlar, elenen[(baslik, neden)], dogrulanamayan[(baslik, neden)])"""
    kalan, elenen, belirsiz = [], [], []
    for r in rows:
        durum, neden = kontrol(r)
        if durum == "kotu":
            elenen.append((r.get("baslik", ""), "baglanti: " + neden))
            log("  baglanti kotu (%s): %s" % (neden, r.get("baslik", "")[:60]))
            continue
        if durum == "dogrulanamadi":
            belirsiz.append((r.get("baslik", ""), neden))
        kalan.append(r)
    return kalan, elenen, belirsiz
