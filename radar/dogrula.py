# -*- coding: utf-8 -*-
"""EDITORUN BULDUGU HABERI MAKINE DOGRULAR.

NEDEN VAR (2026-08-31, kullanici talebi: "bulamadigi haftalar sen bul").

Taze arz olculmus haliyle haftada ~1-3 kapsam ici haber; hedef 5-6. Zayif
haftalarda editorun kendi ARAMA ile haber bulmasi gerekiyor. Ama editorun
buldugu bir haberi dogrudan rapora yazmak IKI kurali birden cigner:
  - "Haber/tarih/detay UYDURMA. Dogrulanamayan tarih girmez."
  - Kapsam kapisi editorun kanaatiyle degil, ayni kapiyla isler.

Bu komut ikisini de korur. Editor YALNIZ BASLIK + ADRES verir
(veri/elle_besleme.json). Komut Actions'ta calisir - orada ag aciktir - ve
her adres icin:
    1) sayfayi ACAR (acilamiyorsa hicbir sey girmez)
    2) sayfanin GERCEK basligini alir (editorun yazdigi baslik degil)
    3) ayni kapsam kapisindan gecirir
    4) yayin tarihini YAPISAL olarak cikarir (JSON-LD / meta / time / url)
       - cikmazsa hicbir sey girmez
    5) baslik yili ile tarih celisiyorsa reddeder
    6) tekrar denetiminden gecirir (seen + olay izi + baslik benzerligi)
    7) pencere icindeyse state.bulunan'a, disindaysa state.rezerv'e yazar

Yani editorun katkisi ADAY GOSTERMEKTIR; karar yine makinenindir. Editorun
beyan ettigi bir tarih ya da kapsam kanaati hicbir zaman rapora giremez.
"""
import datetime as dt
import json
import os

from . import classify, dates, htmlx, http, state, taxonomy
from .collect import event_keys, temiz_adres
from .config import OUT, REZERV_GUN, ROOT, WINDOW_DAYS


def _kapi(baslik, govde=""):
    ok, sebep = taxonomy.in_scope(baslik, govde)
    if ok and taxonomy.haber_olayi(baslik):
        return "Hat", None
    if taxonomy.genel_yatirim(baslik, govde):
        return "Yatirim", None
    return None, (sebep or "olay yok")


def dogrula(today=None, log=print):
    today = today or dt.date.today()
    floor = (today - dt.timedelta(days=WINDOW_DAYS)).isoformat()
    rez_floor = (today - dt.timedelta(days=REZERV_GUN)).isoformat()

    yol = os.path.join(ROOT, "veri", "elle_besleme.json")
    if not os.path.exists(yol):
        log("elle besleme dosyasi yok: %s" % yol)
        return 1
    kayitlar = json.load(open(yol, encoding="utf-8")).get("kayitlar", [])

    st = state.load()
    seen = st.get("seen", {})
    ev = set(st.get("events", {}))
    gecmis = [b for b in (st.get("son_basliklar") or [])
              if not taxonomy.is_junk_title(b.get("b", ""))]
    bilinen = {r["anahtar"] for r in st.get("bulunan", [])} | \
              {r["anahtar"] for r in st.get("rezerv", [])}

    rapor = {"donem": today.isoformat(), "girdi": len(kayitlar),
             "eklenen": [], "reddedilen": []}

    def red(k, sebep, ek=""):
        rapor["reddedilen"].append({"baslik": k.get("baslik", "")[:120],
                                    "url": k.get("url", ""),
                                    "sebep": sebep, "ek": ek})
        log("  RED  %-34s %s" % (sebep, (k.get("baslik") or "")[:56]))

    for k in kayitlar:
        url = temiz_adres((k.get("url") or "").strip())
        if not url.startswith("http"):
            red(k, "adres gecersiz")
            continue

        ok, page, info = http.fetch(url)
        if not ok:
            red(k, "sayfa acilamadi", info.get("hata") or "HTTP %s" % info.get("status"))
            continue

        doc = htmlx.parse_article(page)
        # SAYFANIN GERCEK BASLIGI kullanilir; editorun yazdigi baslik
        # yalnizca bir isarettir, iddia degildir.
        gercek = (doc.get("title") or "").strip()
        baslik = gercek if len(gercek.split()) >= 4 else (k.get("baslik") or "")
        govde = (doc.get("text") or "")[:700]

        katman, sebep = _kapi(baslik, govde)
        if not katman:
            red(k, "kapsam disi", sebep)
            continue

        iso, src = dates.extract_article_date(doc, info.get("final") or url, True, today)
        if not iso:
            red(k, "yayin tarihi sayfadan okunamadi")
            continue
        if iso > today.isoformat():
            red(k, "tarih gelecekte", iso)
            continue
        if dates.title_year_conflict(baslik, iso):
            red(k, "baslik yili tarihle celisiyor", iso)
            continue
        if iso < rez_floor:
            red(k, "cok eski", iso)
            continue

        anahtar = state.norm_key(baslik, url)
        if anahtar in seen:
            red(k, "zaten gonderilmis", iso)
            continue
        if anahtar in bilinen:
            red(k, "zaten havuzda", iso)
            continue

        row = classify.build({"title": baslik, "url": url, "date": iso,
                              "publisher": k.get("kaynak") or "", "text": govde})
        row["anahtar"] = anahtar
        row["tarih"] = iso
        row["tarih_kaynagi"] = src
        row["kategori"] = katman
        row["olaylar"] = sorted(event_keys(row))

        if set(row["olaylar"]) & ev:
            red(k, "ayni olay zaten gonderilmis", iso)
            continue
        if any(taxonomy.similar_titles(baslik, b.get("b", "")) for b in gecmis):
            red(k, "gonderilmis haberin varyanti", iso)
            continue

        havuz = "bulunan" if iso >= floor else "rezerv"
        if havuz == "rezerv":
            row["rezerv"] = True
        st.setdefault(havuz, []).append(row)
        bilinen.add(anahtar)
        rapor["eklenen"].append({"havuz": havuz, "tarih": iso,
                                 "tarih_kaynagi": src, "baslik": baslik[:120],
                                 "url": url, "hat": row.get("hat"),
                                 "asama": row.get("asama")})
        log("  EKLE %-8s %s  %s" % (havuz, iso, baslik[:56]))

    state.prune(st)
    state.save(st)
    with open(os.path.join(OUT, "dogrulama.json"), "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=1)
    log("\ndogrulama: %d aday -> %d eklendi (%d bulunan, %d rezerv), %d reddedildi"
        % (len(kayitlar), len(rapor["eklenen"]),
           sum(1 for e in rapor["eklenen"] if e["havuz"] == "bulunan"),
           sum(1 for e in rapor["eklenen"] if e["havuz"] == "rezerv"),
           len(rapor["reddedilen"])))
    log("-> out/dogrulama.json")
    return 0
