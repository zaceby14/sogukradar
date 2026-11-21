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
        ok, page, info = http.fetch(url, use_cache=False)
        aday = [u for u in re.findall(r'https?://[^"\'\s<>\\]+', page or "")
                if not re.search(r"google|gstatic|youtube|schema\.org|w3\.org", u)]
        print("  google news -> %s" % (aday[0][:150] if aday else "cozulemedi (status %s)" % info.get("status")))
        if aday:
            hedef = html.unescape(aday[0])
    ok, page, info = http.fetch(hedef, use_cache=False)
    if not ok:
        print("  SONUC: ACILAMADI (%s)" % (info.get("hata") or info.get("status")))
        continue
    doc = htmlx.parse_article(page)
    t = (doc.get("title") or "").strip()
    print("  durum: %s  son adres: %s" % (info.get("status"), (info.get("final") or hedef)[:150]))
    print("  sayfa basligi: %s" % t[:150])
    print("  sayfa tarihi : %s" % (doc.get("date") or doc.get("published") or "-"))
    print("  metin: %s" % re.sub(r"\s+", " ", doc.get("text") or "")[:400])
    a, b = baglanti._sozcukler(bas), baglanti._sozcukler(t + " " + (doc.get("text") or "")[:2500])
    print("  baslik-sayfa ortak sozcuk: %d/%d -> %s" % (len(a & b), len(a),
          "UYUMLU" if len(a) and len(a & b) >= max(2, int(0.4 * len(a))) else "KONTROL ET"))
