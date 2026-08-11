# -*- coding: utf-8 -*-
"""Puanlama ve siralama - tamamen deterministik.

Amac: haftalik listeyi ONEM sirasina koymak, boylece benim inceleme yukum
"ilk N satira bak"a inebilsin.
"""
import datetime as dt

STAGE_W = {
    "Sozlesme": 30,
    "Ilk urun": 28,
    "Insaat": 22,
    "Test": 20,
    "Modernizasyon": 18,
    "Seri uretim": 16,
    "Teknoloji": 14,
    "Belirsiz": 4,
}

LINE_W = {
    "Elektrik celigi hatti": 12,
    "Tandem soguk hadde (TCM)": 11,
    "Galvaniz hatti (CGL)": 11,
    "Zn-Al-Mg / Galvalume kaplama": 11,
    "Surekli tavlama (CAL)": 10,
    "Boyama hatti (CCL)": 10,
    "Teneke hatti (ETL)": 9,
    "Reversing soguk hadde (RCM)": 9,
    "Soguk hadde": 9,
    "Asitleme hatti": 8,
    "Elektro galvaniz (EGL)": 8,
    "Temper / skin pass": 6,
    "Asit rejenerasyonu (ARP)": 6,
    "Kutu tavlama (BAF)": 5,
    "Roll shop / merdane": 5,
    "Yuzey muayene (SIS)": 5,
    "Dilme / boy kesme": 4,
    "Otomasyon / dijital": 6,
    "Serit isleme hatti": 5,
    "Belirsiz": 1,
}

KIND_W = {"oem": 8, "uretici": 7, "dergi": 5, "kurum": 4}


def score(row, source_kind="dergi", today=None):
    today = today or dt.date.today()
    s = 0.0
    s += STAGE_W.get(row.get("asama"), 4)
    s += LINE_W.get(row.get("hat"), 1)
    s += KIND_W.get(source_kind, 4)
    if row.get("tedarikci"):
        s += 6
    if row.get("kapasite"):
        s += 4
    if row.get("tutar"):
        s += 4
    if row.get("ulke") == "Turkiye":
        s += 8            # yerel pazar oncelikli
    if not row.get("eksik"):
        s += 3
    try:
        age = (today - dt.date.fromisoformat(row["tarih"])).days
        s += max(0, 10 - age * 0.4)
    except Exception:
        pass
    return round(s, 2)


def rank(rows, kinds, today=None):
    for r in rows:
        r["puan"] = score(r, kinds.get(r.get("kaynak_id"), "dergi"), today)
    rows.sort(key=lambda r: (-r["puan"], r.get("tarih", "")), reverse=False)
    rows.sort(key=lambda r: -r["puan"])
    return rows
