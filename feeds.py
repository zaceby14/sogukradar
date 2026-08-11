# -*- coding: utf-8 -*-
"""RSS / Atom ayrıştırma.

Besleme varsa tarih YAPISAL gelir (pubDate / published / updated) -
tahmine, HTML kazimaya, benim yorumuma hic gerek kalmaz. Bu yuzden
`radar discover` her kaynakta once besleme arar.
"""
import re
import xml.etree.ElementTree as ET

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def looks_like_feed(text):
    head = text.lstrip()[:600].lower()
    return ("<rss" in head or "<feed" in head or "<rdf:rdf" in head
            or "<?xml" in head and ("<channel" in text[:3000].lower()))


def _txt(el):
    if el is None:
        return ""
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def parse_feed(text):
    """[{'title','url','date_raw','summary'}] doner."""
    try:
        root = ET.fromstring(text.encode("utf-8", "replace"))
    except Exception:
        try:
            root = ET.fromstring(re.sub(r"^[^<]+", "", text).encode("utf-8", "replace"))
        except Exception:
            return []

    items = []
    for it in root.iter():
        tag = it.tag.split("}")[-1].lower()
        if tag not in ("item", "entry"):
            continue
        title = link = date_raw = summary = ""
        for ch in it:
            t = ch.tag.split("}")[-1].lower()
            if t == "title" and not title:
                title = _txt(ch)
            elif t == "link":
                href = ch.attrib.get("href")
                rel = ch.attrib.get("rel", "alternate")
                if href and rel == "alternate" and not link:
                    link = href
                elif not href and not link:
                    link = _txt(ch)
            elif t in ("pubdate", "published", "date", "updated", "created") and not date_raw:
                date_raw = _txt(ch)
            elif t in ("description", "summary", "encoded") and not summary:
                summary = re.sub(r"<[^>]+>", " ", _txt(ch))[:1200]
        if title and link:
            items.append({"title": title, "url": link.strip(),
                          "date_raw": date_raw, "summary": summary})
    return items
