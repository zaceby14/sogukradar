# -*- coding: utf-8 -*-
"""SogukRadar komut satiri.

  python -m radar check                 kaynak saglik taramasi
  python -m radar discover              RSS/Atom besleme avi
  python -m radar run                   HAFTALIK KOSU (GitHub Actions bunu calistirir)
  python -m radar review                bana sorulacaklari ozetler
  python -m radar finalize -s ozet.json Turkce cumleleri isler, state'i gunceller
  python -m radar capraz                sitemap capraz kontrolu -> out/kacanlar.json
  python -m radar selftest              agsiz birim testleri
"""
import argparse
import datetime as dt
import json
import os
import sys

from . import collect, render, score, state, taxonomy
from .config import HEDEF_SATIR, OUT, REZERV_MAX, TARGET_ROWS, VERSION
from .sources import SOURCES


def _period(d):
    y, w, _ = d.isocalendar()
    return "%04d-W%02d" % (y, w)


def _w(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def cmd_check(a):
    health = collect.check_sources()
    _w(os.path.join(OUT, "source_health.json"), health)
    bad = [k for k, v in health.items() if v["durum"] in ("erisilemedi", "bos_liste")]
    print("\ntoplam %d kaynak, sorunlu %d: %s" % (len(health), len(bad), ", ".join(bad)))
    return 0


def cmd_discover(a):
    found = collect.discover()
    _w(os.path.join(OUT, "feeds_found.json"), found)
    print("\n%d besleme bulundu -> out/feeds_found.json" % len(found))
    print("Bunlari sources.py icinde rss= alanina islemek kosuyu hizlandirir.")
    return 0


def cmd_run(a):
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    per = _period(today)

    # KALIBRASYON MODU: repo kokunde "KALIBRASYON" adli bir dosya varsa
    # hafiza o kosu icin sifirlanir - daha once cikan haber ve teknolojiler
    # yeniden kullanilabilir. Sistem oturunca dosya silinir, tekrar engeli
    # kendiliginden geri gelir.
    #
    # "son_basliklar" DA SIFIRLANIR (2026-08-18). Onceki surum yalnizca
    # seen/events/tech_seen'i temizliyordu; tekrar savunmasinin UCUNCU bacagi
    # (baslik benzerligi, collect.py) son_basliklar'a bakiyor ve calismaya
    # devam ediyordu. Sonuc: mod ekrana "tekrar engeli kapali" yaziyor ama
    # engel aciktı. 2026-W34 kosusu tam olarak boyle 0 satir uretti -
    # seen=0 iken tekrar=22 gibi kendi icinde celiskili bir istatistikle.
    from .config import ROOT
    if os.path.exists(os.path.join(ROOT, "KALIBRASYON")):
        st0 = state.load()
        st0["seen"], st0["events"], st0["tech_seen"] = {}, {}, {}
        st0["son_basliklar"] = []
        state.save(st0)
        print("*** KALIBRASYON MODU: hafiza sifirlandi, tekrar engeli kapali ***")

    payload = collect.collect(today=today)
    rows = score.rank(payload["rows"], payload["kinds"], today)

    # REZERV (2026-08-27). Bulten ortalama 7-8 gelisme tasimali ama taze arz
    # bunu her hafta karsilamiyor (olcum: haftada ~1-3 kapsam ici haber).
    # Kapiyi GEVSETMEK yerine, gecmiste kapiyi gecmis ve tarihi dogrulanmis
    # ama pencere disinda kaldigi icin hic gonderilmemis satirlar kullanilir.
    st_r = state.load()
    rezerv = _rezerv_guncelle(st_r, payload.pop("rezerv", []), rows)
    eksik = max(HEDEF_SATIR - len(rows), 0)
    kullanilan = []
    if eksik and rezerv:
        # En yeniden eskiye: okuyucu once guncel olani gorsun.
        kullanilan = sorted(rezerv, key=lambda r: r.get("tarih", ""),
                            reverse=True)[:eksik]
        rows = rows + kullanilan
        print("rezervden %d satir eklendi (havuzda %d kaldi)"
              % (len(kullanilan), len(rezerv) - len(kullanilan)))
    payload["rezerv_kullanilan"] = len(kullanilan)
    payload["rezerv_havuz"] = len(rezerv) - len(kullanilan)

    payload["rows"] = rows[:max(TARGET_ROWS, 0)] if a.limit else rows
    payload["period"] = per
    payload["generated"] = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    payload["version"] = VERSION

    base = os.path.join(OUT, "hafta_%s" % per)
    # Elenenler ayri dosyaya: kaynak/sozluk ayarini ancak bunu okuyarak yapabilirim.
    rejects = payload.pop("rejects", [])
    _w(os.path.join(OUT, "reddedilenler.json"),
       {"donem": per, "adet": len(rejects), "kayitlar": rejects})
    _w(base + ".json", payload)

    ask = [{"anahtar": r["anahtar"], "baslik": r["baslik"], "url": r["url"],
            "eksik": r["eksik"], "mevcut": {k: r[k] for k in
                                            ("firma", "ulke", "hat", "asama")}}
           for r in payload["rows"] if r["eksik"]]
    say = [{"anahtar": r["anahtar"], "tarih": r["tarih"], "firma": r["firma"],
            "ulke": r["ulke"], "hat": r["hat"], "asama": r["asama"],
            "baslik": r["baslik"], "url": r["url"]}
           for r in payload["rows"] if r.get("kategori") != "Yatirim"]
    _w(os.path.join(OUT, "needs_ai.json"),
       {"donem": per, "duzelt": ask, "cumle_yaz": say,
        "teknoloji_adaylari": payload.get("tech_pool", [])})

    # Otomatik posta govdesi: yapay zeka ozeti yoksa kurallı metin kullanilir.
    from . import compose
    sayi = len(state.load().get("periods", [])) + 1
    # TEKNOLOJI KOSESI HER HAFTA DOLU OLMALI (2026-08-27). Taze aday cikmayan
    # hafta cok: kosenin havuzu 6 aylik olsa da bir haftada 0 aday olabiliyor
    # (2026-W34'te tam olarak boyle oldu). Bu yuzden aday havuzu da KALICI:
    # kullanilmayan adaylar state'te birikir, koşe onlardan doldurulur.
    payload["tech_pool"] = _tech_havuz(st_r, payload.get("tech_pool", []))
    tech = payload["tech_pool"][:3]
    for t in tech:
        t["konu"] = t["baslik"]
        t["metin"] = compose.tech_blurb(t)
    with open(os.path.join(OUT, "email.html"), "w", encoding="utf-8") as f:
        f.write(render.email_html(payload, None, tech, sayi))
    if a.commit_state and tech:
        # kosede cikan teknolojiler bir daha cikmasin
        st2 = state.load()
        for t in tech:
            st2["tech_seen"][t["anahtar"]] = t["tarih"]
        state.save(st2)

    html = render.html_report(payload)
    with open(base + "_taslak.html", "w", encoding="utf-8") as f:
        f.write(html)
    render.write_csv(base + ".csv", payload["rows"])
    render.write_email(os.path.join(OUT, "email_body.md"), payload)

    if a.commit_state:
        # State GitHub Actions tarafinda guncellenir: bulut oturumumun repoya
        # yazma imkani yok. Boylece "ayni haber ikinci kez cikmasin" garantisi
        # benim adimima bagli kalmaz.
        st = state.load()
        for r in payload["rows"]:
            st["seen"][r["anahtar"]] = r["tarih"]
            for k in r.get("olaylar", []):
                st["events"][k] = r["tarih"]
            # Cop baslik hafizaya YAZILMAZ (2026-08-18). v8 oncesi kosular
            # "Electrical steel, non grain oriented" gibi urun katalogu
            # basliklarini satir olarak kabul etmisti; bunlar son_basliklar'a
            # dusunce baslik benzerligi bacagi her gercek elektrik celigi /
            # galvaniz haberini "tekrar" diye eliyordu.
            if not taxonomy.is_junk_title(r["baslik"]):
                st["son_basliklar"].append({"b": r["baslik"], "t": r["tarih"],
                                            "a": r["asama"]})
        # Rezerv havuzu da kalici: bir sonraki kosu buradan devam eder.
        st["rezerv"] = [r for r in (st_r.get("rezerv") or [])
                        if r["anahtar"] not in st["seen"]]
        st["tech_rezerv"] = [t for t in (st_r.get("tech_rezerv") or [])
                             if t["anahtar"] not in st.get("tech_seen", {})]
        st["periods"] = (st.get("periods") or []) + [{
            "donem": per, "satir": len(payload["rows"]),
            "uretim": payload["generated"], "stats": payload["stats"]}]
        state.prune(st)
        state.save(st)
        print("state guncellendi: %d kayit" % len(st["seen"]))

    s = payload["stats"]
    print("\n[%s] ham %d -> aday %d -> makale %d -> KABUL %d  (tarihsiz %d, "
          "pencere disi %d, kapsam disi %d, tekrar %d)"
          % (per, s["ham"], s["on_eleme_gecti"], s["makale_acildi"], s["kabul"],
             s["tarihsiz_elendi"], s["pencere_disi"], s["kapsam_disi"], s["tekrar"]))
    print("duzeltilecek satir: %d | cumle yazilacak: %d" % (len(ask), len(say)))
    print("cikti: %s.json / _taslak.html / .csv" % base)
    return 0


def _tech_havuz(st, taze):
    """Teknoloji adaylarini KALICI havuzda biriktirir ve siralar.

    Daha once kosede tanitilmis (tech_seen) adaylar dusulur. Boylece aday
    cikmayan haftada bile kose bos kalmaz - gecmis haftalarin kullanilmamis
    adaylari beklemede durur.
    """
    havuz = {t["anahtar"]: t for t in (st.get("tech_rezerv") or [])}
    for t in taze:
        havuz.setdefault(t["anahtar"], t)
    gorulen = st.get("tech_seen") or {}
    kalan = [t for k, t in havuz.items() if k not in gorulen]
    kalan.sort(key=lambda t: t.get("tarih", ""), reverse=True)
    st["tech_rezerv"] = kalan[:60]
    return list(st["tech_rezerv"])


def _rezerv_guncelle(st, yeni_adaylar, rows):
    """Rezerv havuzunu tazeler ve KULLANILABILIR satirlari dondurur.

    Havuza giren satir zaten kapsam kapisini gecmis ve tarihi sayfadan
    dogrulanmistir; tek farki tarihinin haftalik pencerenin disinda
    kalmasidir. Raporlanmis (seen) ya da bu koşuda zaten listeye girmis
    olanlar havuzdan dusulur.
    """
    havuz = {r["anahtar"]: r for r in (st.get("rezerv") or [])}
    for r in yeni_adaylar:
        havuz.setdefault(r["anahtar"], r)
    seen = st.get("seen") or {}
    bu_kosu = {r.get("anahtar") for r in rows}
    temiz = [r for k, r in havuz.items() if k not in seen and k not in bu_kosu]
    temiz.sort(key=lambda r: r.get("tarih", ""), reverse=True)
    st["rezerv"] = temiz[:REZERV_MAX]
    return list(st["rezerv"])


def cmd_review(a):
    p = os.path.join(OUT, "needs_ai.json")
    if not os.path.exists(p):
        print("once `run` calistirin"); return 1
    d = json.load(open(p, encoding="utf-8"))
    print("Donem: %s" % d["donem"])
    print("\n--- DUZELTME GEREKEN (%d) ---" % len(d["duzelt"]))
    for r in d["duzelt"]:
        print("%s | eksik=%s | %s" % (r["anahtar"], ",".join(r["eksik"]), r["baslik"][:90]))
    print("\n--- CUMLE YAZILACAK (%d) ---" % len(d["cumle_yaz"]))
    for r in d["cumle_yaz"]:
        print("%s | %s | %s" % (r["anahtar"], r["tarih"], r["baslik"][:90]))
    return 0


def _eklenen_satirlar(ham, payload):
    """ozet.json'daki "ai_eklenen" maddelerini rapor satirina cevirir.

    Yalnizca URL'si ve basligi olan maddeler satir olur; sadece aciklama
    icin yazilmis bir madde (ornek "STI 403 verdi, elle bakildi") listeye
    girmez ama AI bolumunde yine gorunur. Ayni URL listede zaten varsa
    tekrar eklenmez.
    """
    varolan = {(r.get("url") or "").rstrip("/") for r in payload["rows"]}
    out = []
    for x in ham:
        if not isinstance(x, dict):
            continue
        url, baslik = (x.get("url") or "").strip(), (x.get("baslik") or "").strip()
        if not url or not baslik or url.rstrip("/") in varolan:
            continue
        varolan.add(url.rstrip("/"))
        out.append({
            "tarih": x.get("tarih", ""), "firma": x.get("firma", ""),
            "ulke": x.get("ulke", ""), "hat": x.get("hat") or "Belirsiz",
            "asama": x.get("asama") or "Belirsiz",
            "tedarikci": x.get("tedarikci", ""), "kapasite": x.get("kapasite", ""),
            "tutar": x.get("tutar", ""), "baslik": baslik,
            "kaynak": x.get("kaynak", ""), "kaynak_id": x.get("kaynak_id", ""),
            "url": url, "tarih_kaynagi": x.get("tarih_kaynagi") or "editor",
            "eksik": [], "anahtar": x.get("anahtar") or state.norm_key(baslik, url),
            "kategori": x.get("kategori") or "Hat", "olaylar": [],
            "puan": 0.0, "elle_eklendi": True,
        })
    return out


def cmd_finalize(a):
    per = a.period or _period(dt.date.today())
    base = os.path.join(OUT, "hafta_%s" % per)
    payload = json.load(open(base + ".json", encoding="utf-8"))
    doc = json.load(open(a.summaries, encoding="utf-8")) if a.summaries else {}
    fixes = doc.get("duzeltmeler", {})
    for r in payload["rows"]:
        for k, v in (fixes.get(r["anahtar"]) or {}).items():
            if k in r and v:
                r[k] = v
    drop = set(doc.get("cikar", []))
    if drop:
        payload["rows"] = [r for r in payload["rows"] if r["anahtar"] not in drop]

    # ELLE EKLENEN SATIRLAR (2026-08-17). "ai_eklenen" hem listeye satir
    # ekler hem de postadaki "AI Kontrolu ve Eklemeleri" bolumunu besler -
    # tek kaynak, tek dogru. Satir "elle_eklendi" isaretiyle gelir, posta
    # bunu "+ AI" rozetiyle gosterir.
    eklenen = _eklenen_satirlar(doc.get("ai_eklenen") or [], payload)
    if eklenen:
        payload["rows"] += eklenen
        # Hat satirlari once, Yatirim sonra. Kararli siralama, mevcut
        # satirlarin score.rank'ten gelen sirasini bozmaz.
        payload["rows"].sort(key=lambda r: r.get("kategori") == "Yatirim")

    html = render.html_report(payload, doc.get("cumleler", {}), doc.get("exec", ""))
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(html)
    render.write_csv(base + ".csv", payload["rows"])

    # Posta govdesi: yapay zeka ozetiyle yeniden uretilir.
    # ozet.json "teknolojiler" alani: [{"anahtar","konu","metin","url","tarih"}]
    tech = doc.get("teknolojiler", [])
    sayi = len(state.load().get("periods", [])) or 1
    with open(os.path.join(OUT, "email.html"), "w", encoding="utf-8") as f:
        f.write(render.email_html(payload, doc, tech, sayi))
    if tech:
        st2 = state.load()
        for t in tech:
            if t.get("anahtar"):
                st2["tech_seen"][t["anahtar"]] = t.get("tarih", "")
        state.save(st2)

    # GIDEN BULTEN HAFIZAYA YAZILIR (2026-08-27). Onceden yalniz `run
    # --commit-state` seen'i guncelliyordu; editorun finalize ettigi liste
    # (elle eklenen satirlar dahil) hicbir yere islenmiyordu. Sonuc: 2026-W34
    # bulteniyle GIDEN "Jindal Stainless" satiri bir sonraki hafta yeniden
    # listeye girdi. Postaya giren satir bir daha girmemeli.
    st3 = state.load()
    for r in payload["rows"]:
        if r.get("anahtar"):
            st3["seen"][r["anahtar"]] = r.get("tarih", "")
        for k in r.get("olaylar", []):
            st3["events"][k] = r.get("tarih", "")
        if not taxonomy.is_junk_title(r.get("baslik", "")):
            st3["son_basliklar"].append({"b": r.get("baslik", ""),
                                         "t": r.get("tarih", ""),
                                         "a": r.get("asama", "")})
    state.prune(st3)
    state.save(st3)
    print("hafiza: %d satir 'gonderildi' olarak isaretlendi" % len(payload["rows"]))

    pdf_ok = render.to_pdf(base + ".html", base + ".pdf")
    print("final: %s.html (%d satir), pdf=%s, email.html yenilendi"
          % (base, len(payload["rows"]), pdf_ok))
    return 0


def cmd_capraz(a):
    """Haftalik listenin kacirdiklarini bulur -> out/kacanlar.json.

    Editorun elle yaptigi capraz kontrolun makine karsiligi. Ayrintili
    gerekce icin radar/capraz.py bas yorumuna bakiniz.
    """
    from . import capraz as cp
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    sonuc = cp.capraz(today=today)
    _w(os.path.join(OUT, "kacanlar.json"), sonuc)
    print("\ncapraz kontrol: sitemap adayi %d -> kapiyi gecen %d -> KACAN %d"
          % (sonuc["sitemap_adayi"], sonuc["kapiyi_gecen"], sonuc["adet"]))
    for r in sonuc["kacanlar"]:
        print("  %s | %-9s | %s" % (r["tarih"], r["katman"], r["baslik"][:90]))
    # Kapiyi gecip de listeye girmeyen adaylarin NEREDE dustugu gorunmeli:
    # denetim listesinin sessizce bosalmasi, dolu olmasindan tehlikelidir.
    for r in sonuc["acildi_elendi"]:
        print("  - elendi (%s): %s" % (r["sebep"], r["baslik"][:75]))
    for r in sonuc["dogrulanamayan"]:
        print("  ? dogrulanamadi (%s): %s" % (r["sebep"], r["baslik"][:70]))
    for k, v in sonuc["kaynaklar"].items():
        if v["durum"] != "ok":
            print("  ! %s erisilemedi: %s" % (v["publisher"], v.get("hata")))
    print("-> out/kacanlar.json")
    return 0


def cmd_selftest(a):
    from .selftest import run as run_tests
    return run_tests()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="radar", description="SogukRadar v" + VERSION)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("discover").set_defaults(fn=cmd_discover)

    r = sub.add_parser("run")
    r.add_argument("--today")
    r.add_argument("--limit", action="store_true", help="TARGET_ROWS ile kirp")
    r.add_argument("--commit-state", action="store_true",
                   help="raporlanan satirlari state'e isle (Actions bunu kullanir)")
    r.set_defaults(fn=cmd_run)

    sub.add_parser("review").set_defaults(fn=cmd_review)

    f = sub.add_parser("finalize")
    f.add_argument("-s", "--summaries")
    f.add_argument("-p", "--period")
    f.set_defaults(fn=cmd_finalize)

    c = sub.add_parser("capraz")
    c.add_argument("--today")
    c.set_defaults(fn=cmd_capraz)

    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
