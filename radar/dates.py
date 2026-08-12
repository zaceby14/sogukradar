# -*- coding: utf-8 -*-
"""Deterministik tarih cikarma.

Kural: tarih TAHMIN EDILMEZ. Asagidaki zincirden hicbiri sonuc vermezse
haber listeye ALINMAZ. Bu, "eski haberi bu haftanin gelismesi gibi sunmak"
hatasini kodun icinde imkansiz hale getirir.

Zincir (extract_article_date icinde, sirayla):
  1. JSON-LD  datePublished / dateCreated
  2. <meta property="article:published_time"> ve akrabalari
  3. <time datetime="...">
  4. URL icindeki /2026/08/09/ veya -2026-08-09- deseni
  5. Sayfa metninde gorunur tarih (ilk 4000 karakter)
RSS/Atom kaynaklarinda zincir hic calismaz; tarih beslemeden yapisal gelir.
"""
import re
import datetime as dt

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    # Turkce
    "ocak": 1, "subat": 2, "şubat": 2, "mart": 3, "nisan": 4, "mayis": 5,
    "mayıs": 5, "haziran": 6, "temmuz": 7, "agustos": 8, "ağustos": 8,
    "eylul": 9, "eylül": 9, "ekim": 10, "kasim": 11, "kasım": 11,
    "aralik": 12, "aralık": 12,
}
_MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))

# NOT: \b kullanilamaz - "2026-07-13T06:00:00Z" gibi ISO damgalarinda
# gun ile 'T' arasinda kelime siniri olusmadigi icin eslesme kaciyordu.
RE_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
RE_ISO_SLASH = re.compile(r"(?<!\d)(\d{4})/(\d{1,2})/(\d{1,2})(?!\d)")
RE_DMY_TEXT = re.compile(r"\b(\d{1,2})\s*(?:st|nd|rd|th)?[\s.\-]+(" + _MONTH_ALT + r")[\s.,\-]+(\d{4})\b", re.I)
RE_MDY_TEXT = re.compile(r"\b(" + _MONTH_ALT + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", re.I)
RE_NUM = re.compile(r"(?<!\d)(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})(?!\d)")
RE_URL_YMD = re.compile(r"/(20\d{2})[/\-](\d{1,2})[/\-](\d{1,2})(?:/|\b)")
RE_URL_YM = re.compile(r"/(20\d{2})[/\-](\d{1,2})/")
# "new orders 2026, 21st July ..." -> yil ONCE, gun+ay SONRA (Danieli)
RE_YMD_TEXT = re.compile(r"\b(20\d{2})\s*,\s*(\d{1,2})\s*(?:st|nd|rd|th)?\s+("
                         + _MONTH_ALT + r")\b", re.I)
# "21.07.26" / "21/07/26" iki haneli yil
RE_NUM2 = re.compile(r"(?<!\d)(\d{1,2})[./\-](\d{1,2})[./\-](\d{2})(?!\d)")
RE_RELATIVE = re.compile(r"\b(\d{1,2})\s+(day|days|hour|hours|week|weeks)\s+ago\b", re.I)

MIN_YEAR = 2015


def _mk(y, m, d, today=None):
    try:
        date = dt.date(int(y), int(m), int(d))
    except ValueError:
        return None
    if date.year < MIN_YEAR:
        return None
    today = today or dt.date.today()
    if date > today + dt.timedelta(days=2):   # gelecek tarihli satir = hata
        return None
    return date.isoformat()


def parse_date_text(s, dayfirst=True, today=None):
    """Metinden ILK guvenilir tarihi ISO olarak dondurur, yoksa None."""
    if not s:
        return None
    s = s.strip()
    today = today or dt.date.today()

    m = RE_ISO.search(s)
    if m:
        r = _mk(m.group(1), m.group(2), m.group(3), today)
        if r:
            return r

    m = RE_DMY_TEXT.search(s)
    if m:
        r = _mk(m.group(3), MONTHS[m.group(2).lower()], m.group(1), today)
        if r:
            return r

    m = RE_MDY_TEXT.search(s)
    if m:
        r = _mk(m.group(3), MONTHS[m.group(1).lower()], m.group(2), today)
        if r:
            return r

    m = RE_YMD_TEXT.search(s)
    if m:
        r = _mk(m.group(1), MONTHS[m.group(3).lower()], m.group(2), today)
        if r:
            return r

    m = RE_ISO_SLASH.search(s)
    if m:
        r = _mk(m.group(1), m.group(2), m.group(3), today)
        if r:
            return r

    m = RE_NUM.search(s)
    if m:
        a, b, y = m.group(1), m.group(2), m.group(3)
        if int(a) > 12:            # 25/07/2026 -> gun kesin
            r = _mk(y, b, a, today)
        elif int(b) > 12:          # 07/25/2026 -> ay kesin
            r = _mk(y, a, b, today)
        else:
            r = _mk(y, b, a, today) if dayfirst else _mk(y, a, b, today)
        if r:
            return r

    m = RE_NUM2.search(s)
    if m:
        a, b, y2 = m.group(1), m.group(2), int(m.group(3))
        yil = 2000 + y2 if y2 < 80 else 1900 + y2
        r = (_mk(yil, b, a, today) if (int(a) > 12 or dayfirst)
             else _mk(yil, a, b, today))
        if r:
            return r

    m = RE_RELATIVE.search(s)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        delta = {"day": 1, "days": 1, "hour": 0, "hours": 0,
                 "week": 7, "weeks": 7}[unit]
        days = n * delta if delta else 0
        return (today - dt.timedelta(days=days)).isoformat()

    return None


def date_from_url(url, today=None):
    if not url:
        return None
    m = RE_URL_YMD.search(url)
    if m:
        return _mk(m.group(1), m.group(2), m.group(3), today)
    return None


def month_from_url(url):
    """Sadece yil/ay veren adresler icin: ayin 1'i DEGIL, None doner.
    Gun bilinmiyorsa tarih yok sayilir - uydurma yapilmaz."""
    return None


def extract_article_date(doc, url="", dayfirst=True, today=None):
    """doc: htmlx.parse_article ciktisi. (iso, kaynak_etiketi) doner."""
    today = today or dt.date.today()

    for key in ("datePublished", "dateCreated", "datepublished"):
        for v in doc.get("jsonld_dates", []):
            if v.get("key", "").lower() == key.lower():
                r = parse_date_text(v.get("value", ""), dayfirst, today)
                if r:
                    return r, "json-ld"

    meta_keys = ("article:published_time", "article:published", "og:published_time",
                 "publish-date", "publishdate", "date", "dc.date", "dc.date.issued",
                 "datepublished", "pubdate", "sailthru.date", "parsely-pub-date")
    for k in meta_keys:
        v = doc.get("meta", {}).get(k)
        if v:
            r = parse_date_text(v, dayfirst, today)
            if r:
                return r, "meta:" + k

    for v in doc.get("times", []):
        r = parse_date_text(v, dayfirst, today)
        if r:
            return r, "time"

    r = date_from_url(url, today)
    if r:
        return r, "url"

    head = (doc.get("text") or "")[:4000]
    r = parse_date_text(head, dayfirst, today)
    if r:
        return r, "metin"

    return None, "yok"


def iso_week(d):
    y, w, _ = dt.date.fromisoformat(d).isocalendar()
    return "%04d-W%02d" % (y, w)


# ---------------------------------------------------------------------------
# Baslik-tarih celiskisi denetimi.
#
# v4 kosusunda "August 2024 JOINT STEEL INVESTMENT WITH SONANGOL IN ANGOLA BY
# TOSYALI" basligi 2026-08-10 tarihiyle listeye girdi: sayfanin HTTP
# Last-Modified basligi bugunu gosteriyordu, icerik ise iki yil oncesine ait.
# Kural: baslikta yil geciyorsa ve GECEN TUM YILLAR tarihin yilindan KUCUKSE
# bu satir eski bir icerigin yeniden servis edilmesidir; elenir.
# Gelecek yillar ("2028'e kadar 2 milyon ton") elenmez - onlar hedef beyanidir.
RE_TITLE_YEAR = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")


def title_year_conflict(title, date_iso):
    if not date_iso:
        return False
    yrs = [int(y) for y in RE_TITLE_YEAR.findall(title or "")]
    if not yrs:
        return False
    dy = int(date_iso[:4])
    return max(yrs) < dy


# Tarihin "yapisal" (yayincinin kendi beyani) mi yoksa "dolayli" mi
# oldugunu soyler. Dolayli tarihler rapora "tarih?" isaretiyle girer.
KESIN_TARIH = ("rss", "json-ld", "time", "capraz-rss")


def kesin_mi(src):
    s = (src or "").split(":")[0]
    return s in KESIN_TARIH or s.startswith("meta")
