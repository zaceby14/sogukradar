# -*- coding: utf-8 -*-
"""SogukRadar komut satiri.

  python -m radar check                 kaynak saglik taramasi
  python -m radar discover              RSS/Atom besleme avi
  python -m radar run                   HAFTALIK KOSU (GitHub Actions bunu calistirir)
  python -m radar review                bana sorulacaklari ozetler
  python -m radar finalize -s ozet.json Turkce cumleleri isler, state'i gunceller
  python -m radar selftest              agsiz birim testleri
"""
import argparse
import datetime as dt
import json
import os
import sys

from . import collect, render, score, state
from .config import OUT, TARGET_ROWS, VERSION
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
    # hafiza (seen/events/tech_seen) o kosu icin sifirlanir - daha once
    # cikan haber ve teknolojiler yeniden kullanilabilir. Sistem oturunca
    # dosya silinir, tekrar engeli kendiliginden geri gelir.
    from .config import ROOT
    if os.path.exists(os.path.join(ROOT, "KALIBRASYON")):
        st0 = state.load()
        st0["seen"], st0["events"], st0["tech_seen"] = {}, {}, {}
        state.save(st0)
        print("*** KALIBRASYON MODU: hafiza sifirlandi, tekrar engeli kapali ***")

    payload = collect.collect(today=today)
    rows = score.rank(payload["rows"], payload["kinds"], today)
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
    tech = payload.get("tech_pool", [])[:3]
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
            st["son_basliklar"].append({"b": r["baslik"], "t": r["tarih"],
                                        "a": r["asama"]})
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

    pdf_ok = render.to_pdf(base + ".html", base + ".pdf")
    print("final: %s.html (%d satir), pdf=%s, email.html yenilendi"
          % (base, len(payload["rows"]), pdf_ok))
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

    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
