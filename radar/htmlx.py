# -*- coding: utf-8 -*-
"""HTML ayrıştırma - standart kutuphanedeki html.parser uzerine.

Iki is yapar:
  parse_listing : liste sayfasindan (baslik, adres, tarih_ipucu) uclulari
  parse_article : makale sayfasindan meta/JSON-LD/time/metin
Tarih karari dates.py'de verilir; burada sadece HAM veri toplanir.
"""
import html
import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag

SKIP_TAGS = {"script", "style", "noscript", "svg"}

DATEISH = re.compile(
    r"(\b\d{4}-\d{2}-\d{2}\b"
    r"|\b\d{1,2}[./\-]\d{1,2}[./\-]\d{4}\b"
    r"|\b\d{1,2}\s+[A-Za-zĞÜŞİÖÇğüşıöç]{3,12}\.?\s+\d{4}\b"
    r"|\b[A-Za-zĞÜŞİÖÇğüşıöç]{3,12}\.?\s+\d{1,2},?\s+\d{4}\b"
    r"|\b\d{1,2}\s+(day|days|week|weeks|hour|hours)\s+ago\b)", re.I)

NAV_WORDS = re.compile(
    r"^(home|news|about|contact|menu|search|more|read more|all news|next|previous|"
    r"privacy|cookie|login|sign in|subscribe|newsletter|share|back|top|en|tr|de|"
    r"products|services|careers|events|media|press|\d+)$", re.I)


class _Listing(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events = []          # ("a", href, text) | ("d", raw_date)
        self._a = None
        self._buf = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP_TAGS:
            self._skip += 1
            return
        if tag == "a" and a.get("href"):
            self._flush_link()
            self._a = a["href"]
            self._buf = []
        elif tag == "time":
            dtv = a.get("datetime") or a.get("data-date") or ""
            if dtv:
                self.events.append(("d", dtv))
        elif a.get("datetime"):
            self.events.append(("d", a["datetime"]))

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
            return
        if tag == "a":
            self._flush_link()

    def handle_data(self, data):
        if self._skip:
            return
        if self._a is not None:
            self._buf.append(data)
        else:
            for m in DATEISH.finditer(data):
                self.events.append(("d", m.group(0)))

    def _flush_link(self):
        if self._a is None:
            return
        txt = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        href = self._a
        self._a, self._buf = None, []
        self.events.append(("a", href, txt))
        for m in DATEISH.finditer(txt):
            self.events.append(("d", m.group(0)))

    def close(self):
        self._flush_link()
        super().close()


LEAD_CRUFT = re.compile(
    r"^(?:\d{1,2}\s+[A-Za-z]{3,9}\.?(?:\s+\d{4})?\s*)?"
    r"(?:Free|Premium|Exclusive|News|Video)?\s*[|:\-–]?\s*", re.I)


def _trim_title(txt, cap=190):
    """Kart metninin tamami baglanti metnine giriyor: "Baslik 2025-12-09 Tata
    Steel has awarded ...". Baslik ilk tarih damgasinda kesilir, uzunsa
    kelime sinirindan kirpilir."""
    txt = LEAD_CRUFT.sub("", txt.strip(), count=1)
    m = DATEISH.search(txt)
    if m and m.start() >= 25:
        txt = txt[:m.start()].strip(" -–|,:")
    if len(txt) > cap:
        txt = txt[:cap].rsplit(" ", 1)[0] + "…"
    return txt.strip()


def parse_listing(page, base_url, min_title=25, max_items=400):
    """Liste sayfasindan aday haberleri cikarir.

    Tarih ipucu: bagimsiz bir tarih olayina en yakin baglanti eslestirilir.
    Bu YALNIZCA on eleme icindir - kesin tarih makale sayfasindan alinir.
    """
    p = _Listing()
    try:
        p.feed(page)
        p.close()
    except Exception:
        pass

    ev = p.events
    date_idx = [(i, v) for i, (k, *rest) in enumerate(ev) if k == "d" for v in [rest[0]]]
    anchor_idx = [i for i, e in enumerate(ev) if e[0] == "a"]

    def hint_for(i):
        """Tarih ipucu SADECE bu baglantinin kendi 'kart'indan alinir:
        onceki baglantidan sonra veya sonraki baglantidan once gelen tarih.
        Yoksa BOS birakilir - komsu haberin tarihini odunc almak, gecerli bir
        haberi 'eski' diye elemeye yol aciyordu."""
        prev = max([a for a in anchor_idx if a < i], default=-1)
        nxt = min([a for a in anchor_idx if a > i], default=len(ev))
        for j, v in date_idx:
            if prev < j < i:
                return v
        for j, v in date_idx:
            if i < j < nxt:
                return v
        return ""

    out, seen = [], set()
    for i, e in enumerate(ev):
        if e[0] != "a":
            continue
        href, txt = e[1], e[2]
        if not txt or len(txt) < min_title or NAV_WORDS.match(txt):
            continue
        url = urldefrag(urljoin(base_url, html.unescape(href)))[0]
        if not url.startswith("http"):
            continue
        if re.search(r"\.(pdf|jpg|jpeg|png|zip|mp4|docx?|xlsx?)$", url, re.I):
            continue
        key = url
        if key in seen:
            continue
        seen.add(key)
        out.append({"url": url, "title": _trim_title(txt), "date_hint": hint_for(i)})
        if len(out) >= max_items:
            break
    return out


class _Article(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta, self.times, self.scripts = {}, [], []
        self.title = ""
        self._chunks = []
        self._skip = 0
        self._in_title = False
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            k = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            v = a.get("content") or ""
            if k and v and k not in self.meta:
                self.meta[k] = v
        elif tag == "time":
            v = a.get("datetime") or ""
            if v:
                self.times.append(v)
        elif tag == "script":
            self._in_script = (a.get("type", "").lower() == "application/ld+json")
            self._skip += 1
            self._chunks and None
        elif tag in SKIP_TAGS:
            self._skip += 1
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False
            self._skip = max(0, self._skip - 1)
        elif tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_script:
            self.scripts.append(data)
            return
        if self._skip:
            return
        if self._in_title:
            self.title += data
        else:
            self._chunks.append(data)

    def text(self):
        return re.sub(r"\s+", " ", " ".join(self._chunks)).strip()


def _jsonld_dates(scripts):
    keys = ("datePublished", "dateCreated", "dateModified", "uploadDate")
    out = []
    for s in scripts:
        for k in keys:
            for m in re.finditer(r'"%s"\s*:\s*"([^"]{4,40})"' % k, s):
                out.append({"key": k, "value": m.group(1)})
        if not out:
            try:
                data = json.loads(s)
            except Exception:
                continue
            stack = [data]
            while stack:
                o = stack.pop()
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k in keys and isinstance(v, str):
                            out.append({"key": k, "value": v})
                        elif isinstance(v, (dict, list)):
                            stack.append(v)
                elif isinstance(o, list):
                    stack.extend(o)
    return out


def parse_article(page):
    p = _Article()
    try:
        p.feed(page)
        p.close()
    except Exception:
        pass
    return {
        "meta": p.meta,
        "times": p.times,
        "jsonld_dates": _jsonld_dates(p.scripts),
        "title": re.sub(r"\s+", " ", p.title).strip(),
        "text": p.text(),
    }


FEED_LINK = re.compile(
    r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>', re.I)
HREF = re.compile(r'href=["\']([^"\']+)["\']', re.I)


def discover_feeds(page, base_url):
    urls = []
    for tag in FEED_LINK.findall(page):
        m = HREF.search(tag)
        if m:
            urls.append(urljoin(base_url, html.unescape(m.group(1))))
    return list(dict.fromkeys(urls))
