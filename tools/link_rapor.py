# -*- coding: utf-8 -*-
"""Bultendeki her linki acar, sayfanin gercekten o haberi gosterdigini raporlar.
Kullanim: python tools/link_rapor.py out/karar_satirlar.json > out/link_rapor.txt
Hafizaya/postaya dokunmaz."""
import json, re, sys, html
sys.path.insert(0, ".")
from radar import http, htmlx, baglanti

d = json.load(open(sys.argv[1], encoding="utf-8"))
maddeler = [("HABER", r) for r in d.get("rows", [])] + [("TEKNOLOJI", t) for t in d.get("tech", [])] \
    + [("PIYASA", m) for m in d.get("piyasa", [])]
for tur, m in maddeler:
    url = m.get("url", "")
    bas = m.get("baslik") or m.get("konu") or ""
    print("=" * 70)
    print("[%s] %s | %s" % (tur, m.get("tarih", ""), bas[:110]))
    print("  link : %s" % url[:150])
    hedef = url
    if "news.google.com" in url:
        from radar import yayinci
        cozulen = yayinci.bul(bas)
        print("  google news -> yayinci: %s" % (cozulen or "BULUNAMADI"))
        if not cozulen:
            continue
        hedef = cozulen
    ok, page, info = http.fetch(hedef, use_cache=False)
    if not ok:
        print("  SONUC: ACILAMADI (%s)" % (info.get("hata") or info.get("status")))
        continue
    doc = htmlx.parse_article(page)
    t = (doc.get("title") or "").strip()
    print("  durum: %s  son adres: %s" % (info.get("status"), (info.get("final") or hedef)[:150]))
    print("  sayfa basligi: %s" % t[:150])
    print("  sayfa tarihi : %s" % (", ".join(str(x) for x in (doc.get("jsonld_dates") or [])[:2]) or
                                    ", ".join(v for k, v in (doc.get("meta") or {}).items() if "time" in k or "date" in k)[:80] or
                                    ", ".join(str(x) for x in (doc.get("times") or [])[:2]) or "-"))
    print("  metin: %s" % re.sub(r"\s+", " ", doc.get("text") or "")[:400])
    a, b = baglanti._sozcukler(bas), baglanti._sozcukler(t + " " + (doc.get("text") or "")[:2500])
    print("  baslik-sayfa ortak sozcuk: %d/%d -> %s" % (len(a & b), len(a),
          "UYUMLU" if len(a) and len(a & b) >= max(2, int(0.4 * len(a))) else "KONTROL ET"))
