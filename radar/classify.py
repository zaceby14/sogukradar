# -*- coding: utf-8 -*-
"""Siniflandirma: firma, hat, asama, ulke, kapasite, yatirim tutari.

Hepsi kural tabanli ve deterministik. Belirsiz kalan alan bos birakilir;
bos alanlar `needs_ai.json`'a dusup TEK TEK bana sorulur - tahmin edilmez.
"""
import re

from . import taxonomy as tx

VERB = (r"(?:awards?|awarded|orders?|selects?|selected|contracts?|chooses?|picks?|taps?|"
        r"commissions?|commissioned|inaugurates?|launch(?:es|ed)?|starts?|started|begins?|"
        r"began|completes?|completed|produces?|produced|secures?|secured|wins?|won|"
        r"receives?|received|installs?|installed|expands?|expanded|adds?|added|opens?|"
        r"opened|signs?|signed|places?|placed|to build|to install|to supply|to modernize|"
        r"to modernise|to upgrade|to invest|invests?|plans?|orders)\b")

TAIL = re.compile(
    r"\s+(Awarded|Awards?|Wins?|Won|Selects?|Orders?|Secures?|Inaugurates?|Commissions?|"
    r"Completes?|Launch(?:es|ed)?|Produces?|Starts?|Begins?|Contracts?|Chooses?|Supplies|"
    r"Installs?|Signs?|Expands?|Adds?|Opens?|Plans?|Invests?)$", re.I)

CAP = re.compile(
    r"\b(\d[\d.,]{2,12})\s*(?:t(?:onnes?|ons?)?)?\s*(?:/|per\s+)?\s*(?:y(?:ear|r)?|annum|a)\b"
    r"|\b(\d+(?:[.,]\d+)?)\s*(million|mn|m)\s*(?:t(?:onnes?|ons?)?)\s*(?:/|per\s+)?"
    r"(?:y(?:ear|r)?|annum|a)?\b"
    r"|\b(\d[\d.,]{2,12})\s*(?:tpy|tpa|mtpa|ktpa|kt/y|kt/a)\b", re.I)

MONEY = re.compile(
    r"(?:(US\$|\$|€|EUR|USD|£|₺|TL|INR|Rs\.?)\s?(\d+(?:[.,]\d+)?)\s*(billion|bn|million|mn|m|crore|lakh)?)"
    r"|(?:(\d+(?:[.,]\d+)?)\s*(billion|bn|million|mn|m|crore)\s*(US\$|\$|€|EUR|USD|£|₺|TL|INR|rupees|dollars|euros))",
    re.I)


def _clean_firm(name):
    name = TAIL.sub("", (name or "").strip())
    name = re.sub(r"^(The|A|An)\s+", "", name, flags=re.I)
    return name.strip(" -,:;'’")


def detect_firm(title, fallback=""):
    """Haberin OZNESINI cikarir. Uc bilinen hata icin ozel onlem var:
       - "India's JIL ..."  -> ulke eki firma adi degildir, atilir
       - "Tenova I2S Awarded ..." -> fiil isme yapismasin
       - "John Cockerill India Inaugurates ..." -> en kisa ozne once denenir
    """
    t = (title or "").strip()
    t = re.sub(r"^[A-Z][a-zA-Z]+(?:'s|s')\s+", "", t)          # India's / China's
    t = re.sub(r"^(?:Exclusive|Update|Breaking|Video|Photo)\s*[:\-]\s*", "", t, flags=re.I)

    words = t.split()
    for n in range(1, 6):
        if len(words) <= n:
            break
        cand = " ".join(words[:n])
        if not re.match(r"^[A-Z0-9]", cand):
            break
        # kalan metnin tamamina bakilir; "to supply" gibi iki kelimeli
        # fiiller tek kelimeye bakinca kaciyordu
        if re.match(VERB, " ".join(words[n:]), re.I):
            c = _clean_firm(cand)
            if c and c.lower() not in ("new", "the", "a", "an", "it"):
                return c

    m = re.search(r"\b(?:for|at|to|by)\s+([A-Z][\w&\.\-']*(?:\s+[A-Z][\w&\.\-']*){0,3})", t)
    if m:
        c = _clean_firm(m.group(1))
        if c:
            return c

    m = re.match(r"^([A-Z][\w&\.\-']*(?:\s+[A-Z][\w&\.\-']*){0,2})", t)
    if m:
        c = _clean_firm(m.group(1))
        if c:
            return c
    return fallback or ""


def detect_supplier(text):
    low = (text or "").lower()
    hits = [s for s in tx.SUPPLIERS if s in low]
    if not hits:
        return ""
    # en uzun eslesme en spesifik olandir ("john cockerill" > "abb")
    hits.sort(key=len, reverse=True)
    return hits[0].title().replace("Sms Group", "SMS group").replace("Abb", "ABB")


def detect_capacity(text):
    m = CAP.search(text or "")
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(0)).strip()


def detect_money(text):
    m = MONEY.search(text or "")
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(0)).strip()


def build(cand):
    """cand: {title, url, date, publisher, source_id, text}
    Tam siniflandirilmis satir doner."""
    title = cand.get("title", "")
    body = (cand.get("text") or "")[:1500]
    blob = title + " . " + body

    line = tx.match_line(blob)
    stage = tx.match_stage(title)
    if stage == "Belirsiz":
        stage = tx.match_stage(blob)
    country = tx.match_country(blob)
    supplier = detect_supplier(blob)
    firm = detect_firm(title, fallback="")
    if supplier and firm.lower().startswith(supplier.lower()[:6]):
        # ozne tedarikci ise musteriyi aramaya calis
        m = re.search(r"\b(?:for|to|at)\s+([A-Z][\w&\.\-']*(?:\s+[A-Z][\w&\.\-']*){0,3})", title)
        if m:
            firm = _clean_firm(m.group(1)) or firm

    row = {
        "tarih": cand.get("date", ""),
        "firma": firm,
        "ulke": country,
        "hat": line,
        "asama": stage,
        "tedarikci": supplier,
        "kapasite": detect_capacity(blob),
        "tutar": detect_money(blob),
        "baslik": title,
        "kaynak": cand.get("publisher", ""),
        "kaynak_id": cand.get("source_id", ""),
        "url": cand.get("url", ""),
        "tarih_kaynagi": cand.get("date_src", ""),
    }
    row["eksik"] = [k for k in ("firma", "ulke") if not row[k]]
    if line == "Belirsiz":
        row["eksik"].append("hat")
    if stage == "Belirsiz":
        row["eksik"].append("asama")
    return row
