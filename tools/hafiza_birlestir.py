# -*- coding: utf-8 -*-
"""Iki hafiza dosyasini (state.json) BIRLESTIRIR - hicbir 'gonderildi' kaydi kaybolmaz.

NEDEN (2026-11-23): iki otomatik kosu ust uste calisti; ikincisi eski hafizayla
basladi, bulteni ikinci kez gonderdi ve commit adiminda hafizayi uzerine yazdi -
ilk gonderimin kayitlari (JTL, Hoa Sen) silindi. Artik commit oncesi uzak
depodaki hafiza ile bu kosununki birlestirilir:
  - sozlukler (seen, events, tech_seen, piyasa_seen ...): birlesim
  - 'gonderildi' listeleri (son_basliklar, *_gonderilen, gonderilen_donemler ...): birlesim
  - havuzlar ve diger alanlar: bu kosunun degeri (en guncel tarama)
Kullanim: python tools/hafiza_birlestir.py <bu_kosu.json> <uzak.json> <cikti.json>
"""
import json
import sys

HAVUZ = {"bulunan", "rezerv", "tech_rezerv", "piyasa_rezerv", "tercih"}


def birlestir(biz, uzak):
    out = dict(uzak)
    out.update(biz)
    for k, v in uzak.items():
        if k in HAVUZ or k not in biz:
            continue
        b = biz[k]
        if isinstance(v, dict) and isinstance(b, dict):
            m = dict(v)
            m.update(b)
            out[k] = m
        elif isinstance(v, list) and isinstance(b, list):
            gor = {json.dumps(x, sort_keys=True) for x in b}
            out[k] = b + [x for x in v if json.dumps(x, sort_keys=True) not in gor]
    if isinstance(out.get("gonderilen_donemler"), list):
        out["gonderilen_donemler"] = sorted(set(out["gonderilen_donemler"]))
    return out


if __name__ == "__main__":
    biz = json.load(open(sys.argv[1], encoding="utf-8"))
    try:
        uzak = json.load(open(sys.argv[2], encoding="utf-8"))
    except Exception:
        uzak = {}
    json.dump(birlestir(biz, uzak), open(sys.argv[3], "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
