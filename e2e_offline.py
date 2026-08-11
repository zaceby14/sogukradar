# -*- coding: utf-8 -*-
"""Agsiz uctan uca deneme.

http.fetch sahte bir sunucuyla degistirilir; boylece boru hattinin tamami
(liste -> makale -> tarih -> kapsam -> siniflandirma -> tekrar -> puan -> rapor)
internet olmadan dogrulanabilir. GitHub Actions'ta gercek agla ayni kod kosar.
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar import collect, http, render, score, sources  # noqa: E402

TODAY = dt.date(2026, 8, 11)

LISTING = """<html><body><ul>
<li><time datetime="2026-08-07">7 Aug 2026</time>
    <a href="/n/first-coil">Angang produces first coil at new hot-dip galvanizing line in China</a></li>
<li><time datetime="2026-08-05">5 Aug 2026</time>
    <a href="/n/tcm-order">Tosyali awards tandem cold mill contract to Danieli in Turkey</a></li>
<li><time datetime="2026-08-02">2 Aug 2026</time>
    <a href="/n/hrc-price">HRC prices climb in Europe on import quota news</a></li>
<li><time datetime="2026-08-01">1 Aug 2026</time>
    <a href="/n/bf-relining">Steelmaker completes blast furnace relining project</a></li>
<li><time datetime="2025-02-01">1 Feb 2025</time>
    <a href="/n/old-ccl">Old colour coating line started up long ago in India</a></li>
<li><a href="/n/nodate">Mystery pickling line project announced somewhere</a></li>
<li><a href="/about">Home</a></li>
</ul></body></html>"""

ARTICLES = {
    "/n/first-coil": ('<html><head><script type="application/ld+json">'
                      '{"datePublished":"2026-08-07T09:00:00+08:00"}</script></head>'
                      '<body><p>Angang Guangzhou produced the first coil on its new '
                      'continuous hot-dip galvanizing line, with a capacity of '
                      '400,000 tpy. The line was supplied by Primetals.</p></body></html>'),
    "/n/tcm-order": ('<html><head><meta property="article:published_time" '
                     'content="2026-08-05T07:00:00Z"></head><body><p>Tosyali has awarded '
                     'Danieli a contract for a 5-stand tandem cold mill in Turkey. '
                     'The investment is worth $220 million.</p></body></html>'),
    "/n/hrc-price": ('<html><body><time datetime="2026-08-02"></time>'
                     '<p>Hot rolled coil prices rose this week.</p></body></html>'),
    "/n/bf-relining": ('<html><body><time datetime="2026-08-01"></time>'
                       '<p>The blast furnace was relined.</p></body></html>'),
    "/n/old-ccl": ('<html><body><time datetime="2025-02-01"></time>'
                   '<p>A colour coating line in India.</p></body></html>'),
    "/n/nodate": '<html><body><p>A pickling line project with no date anywhere.</p></body></html>',
}


def fake_fetch(url, use_cache=True):
    if url.endswith("/news"):
        return True, LISTING, {"status": 200, "final": url, "cache": False}
    for k, v in ARTICLES.items():
        if url.endswith(k):
            return True, v, {"status": 200, "final": url, "cache": False}
    return False, "", {"status": 0, "final": url, "hata": "sahte sunucu: yok"}


def main():
    http.fetch = fake_fetch
    collect.http.fetch = fake_fetch
    sources.SOURCES[:] = [dict(id="test", publisher="Test Wire", kind="dergi",
                               country="XX", url="https://ex.com/news", rss=None,
                               verified=True)]

    payload = collect.collect(today=TODAY)
    rows = score.rank(payload["rows"], payload["kinds"], TODAY)
    payload.update(period="2026-W33", generated="test", rows=rows)

    print("istatistik:", payload["stats"])
    for r in rows:
        print("  %s | %-10s | %-28s | %-12s | puan %.1f | tarih kaynagi: %s"
              % (r["tarih"], r["firma"], r["hat"], r["asama"], r["puan"],
                 r["tarih_kaynagi"]))

    ok = True

    def chk(cond, msg):
        nonlocal ok
        if not cond:
            ok = False
            print("  HATA:", msg)

    keys = {r["baslik"][:20] for r in rows}
    chk(len(rows) == 2, "2 satir bekleniyordu, %d geldi" % len(rows))
    chk(any("Angang" in r["firma"] for r in rows), "Angang satiri yok")
    chk(any("Tosyali" in r["firma"] for r in rows), "Tosyali satiri yok")
    chk(all("price" not in r["baslik"].lower() for r in rows), "fiyat haberi sizdi")
    chk(all("blast" not in r["baslik"].lower() for r in rows), "yuksek firin sizdi")
    chk(payload["stats"]["tarihsiz_elendi"] >= 1, "tarihsiz haber elenmedi")
    chk(payload["stats"]["pencere_disi"] >= 1, "eski haber pencerede kaldi")
    a = [r for r in rows if "Angang" in r["firma"]][0]
    chk(a["hat"] == "Galvaniz hatti (CGL)", "hat yanlis: " + a["hat"])
    chk(a["asama"] == "Ilk urun", "asama yanlis: " + a["asama"])
    chk(a["tedarikci"] == "Primetals", "tedarikci yanlis: " + str(a["tedarikci"]))
    chk(bool(a["kapasite"]), "kapasite bulunamadi")
    t = [r for r in rows if "Tosyali" in r["firma"]][0]
    chk(t["ulke"] == "Turkiye", "ulke yanlis")
    chk(t["asama"] == "Sozlesme", "asama yanlis: " + t["asama"])
    chk(t["puan"] > a["puan"], "Turkiye satiri ustte olmaliydi")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "e2e_rapor.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(render.html_report(payload, {}, "Test ozeti."))
    print("rapor:", out)
    print("E2E:", "GECTI" if ok else "KALDI")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
