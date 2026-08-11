# -*- coding: utf-8 -*-
"""Cikti uretimi: HTML / CSV / Markdown (+ varsa PDF)."""
import csv
import html
import os
import subprocess

from .config import MIN_ROWS, OWNER, SYSTEM_NAME, VERSION
from .sources import KNOWN_GAPS, SOURCES

CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
 margin:0;padding:28px 34px;color:#16181d;background:#fff;font-size:13.5px;line-height:1.5}
h1{font-size:21px;margin:0 0 2px}h2{font-size:15px;margin:26px 0 8px;
 border-bottom:2px solid #16181d;padding-bottom:4px}
.sub{color:#666;font-size:12px;margin-bottom:18px}
table{border-collapse:collapse;width:100%;margin:6px 0 14px;font-size:12px}
th{background:#16181d;color:#fff;text-align:left;padding:6px 8px;font-weight:600}
td{border-bottom:1px solid #e3e5ea;padding:6px 8px;vertical-align:top}
tr:nth-child(even) td{background:#fafbfc}
.warn{background:#fff8e6;border-left:4px solid #e0a800;padding:10px 14px;margin:10px 0}
.bad{background:#fdeeee;border-left:4px solid #c0392b;padding:10px 14px;margin:10px 0}
.ok{background:#eef7ef;border-left:4px solid #2e7d32;padding:10px 14px;margin:10px 0}
.small{font-size:11px;color:#666}
.tag{display:inline-block;background:#eef0f4;border-radius:3px;padding:1px 6px;
 font-size:11px;margin-right:4px}
.grid{display:flex;gap:26px;flex-wrap:wrap}.grid>div{flex:1;min-width:210px}
a{color:#12457a;text-decoration:none}
.foot{margin-top:26px;border-top:1px solid #ddd;padding-top:10px;font-size:11px;color:#777}
"""


def _e(s):
    return html.escape(str(s or ""))


def _dist(rows, key, top=None):
    d = {}
    for r in rows:
        v = r.get(key) or "-"
        d[v] = d.get(v, 0) + 1
    items = sorted(d.items(), key=lambda kv: -kv[1])
    return items[:top] if top else items


def _table(pairs, head):
    out = ["<table><tr><th>%s</th><th>Adet</th></tr>" % _e(head)]
    for k, v in pairs:
        out.append("<tr><td>%s</td><td>%s</td></tr>" % (_e(k), v))
    out.append("</table>")
    return "".join(out)


def html_report(payload, summaries=None, exec_summary=""):
    rows = payload["rows"]
    st = payload["stats"]
    per = payload.get("period", "")
    summaries = summaries or {}

    p = ['<!doctype html><html lang="tr"><meta charset="utf-8">',
         "<title>%s %s</title><style>%s</style>" % (SYSTEM_NAME, _e(per), CSS)]
    p.append("<h1>%s &mdash; Haftalik Yassi Celik Downstream Radari</h1>" % SYSTEM_NAME)
    p.append('<div class="sub">Donem: <b>%s</b> &nbsp;|&nbsp; Pencere: %s &rarr; %s '
             '&nbsp;|&nbsp; Uretim: %s &nbsp;|&nbsp; %s v%s &nbsp;|&nbsp; %s</div>'
             % (_e(per), _e(payload["window"][0]), _e(payload["window"][1]),
                _e(payload.get("generated", "")), SYSTEM_NAME, VERSION, _e(OWNER)))

    if exec_summary:
        p.append('<div class="ok"><b>Yonetici ozeti.</b> %s</div>' % _e(exec_summary))

    if len(rows) < MIN_ROWS:
        p.append('<div class="bad"><b>Dusuk kapsam uyarisi.</b> Bu hafta yalnizca %d '
                 'dogrulanmis satir uretildi (esik %d). Bu, sektorde gelisme olmadigi '
                 'anlamina GELMEZ; asagidaki erisim tablosunu kontrol edin.</div>'
                 % (len(rows), MIN_ROWS))

    unreach = payload.get("unreachable", [])
    if unreach:
        p.append('<div class="warn"><b>Erisilemeyen kaynaklar (%d).</b><br>' % len(unreach))
        p.append("<br>".join("%s &mdash; <span class='small'>%s</span>" % (_e(a), _e(b))
                             for a, b in unreach))
        p.append("</div>")

    if KNOWN_GAPS:
        p.append('<div class="warn"><b>Bilinen kor noktalar.</b><br>')
        p.append("<br>".join("%s &mdash; <span class='small'>%s</span>" % (_e(a), _e(b))
                             for a, b in KNOWN_GAPS))
        p.append("</div>")

    p.append("<h2>Kapsam olcumu</h2>")
    p.append("<table><tr><th>Adim</th><th>Adet</th></tr>")
    labels = [("kaynak", "Taranan kaynak"), ("erisilemeyen", "Erisilemeyen kaynak"),
              ("ham", "Ham baglanti"), ("on_eleme_gecti", "On elemeyi gecen"),
              ("makale_acildi", "Makale sayfasi acilan"),
              ("tarihsiz_elendi", "Tarihi bulunamadigi icin elenen"),
              ("pencere_disi", "Tarih penceresi disi"),
              ("kapsam_disi", "Kapsam disi"), ("tekrar", "Daha once raporlanmis"),
              ("kabul", "Rapora giren")]
    for k, lbl in labels:
        p.append("<tr><td>%s</td><td>%s</td></tr>" % (_e(lbl), st.get(k, 0)))
    p.append("</table>")

    if rows:
        p.append("<h2>Dagilimlar</h2><div class='grid'>")
        p.append("<div>" + _table(_dist(rows, "ulke"), "Ulke") + "</div>")
        p.append("<div>" + _table(_dist(rows, "hat"), "Hat tipi") + "</div>")
        p.append("<div>" + _table(_dist(rows, "asama"), "Asama") + "</div>")
        p.append("<div>" + _table(_dist(rows, "tedarikci", 10), "Tedarikci") + "</div>")
        p.append("</div>")

        p.append("<h2>Gelismeler (%d)</h2>" % len(rows))
        p.append("<table><tr><th>#</th><th>Tarih</th><th>Firma / Ulke</th>"
                 "<th>Hat &amp; Asama</th><th>Ozet</th><th>Kaynak</th></tr>")
        for i, r in enumerate(rows, 1):
            note = summaries.get(r.get("anahtar")) or ""
            extra = []
            if r.get("tedarikci"):
                extra.append("Tedarikci: " + r["tedarikci"])
            if r.get("kapasite"):
                extra.append("Kapasite: " + r["kapasite"])
            if r.get("tutar"):
                extra.append("Tutar: " + r["tutar"])
            p.append(
                "<tr><td>%d</td><td>%s<div class='small'>%s</div></td>"
                "<td><b>%s</b><div class='small'>%s</div></td>"
                "<td>%s<div class='small'>%s</div></td>"
                "<td>%s<div class='small'>%s</div>%s</td>"
                "<td><a href='%s'>%s</a></td></tr>"
                % (i, _e(r["tarih"]), _e(r.get("tarih_kaynagi")),
                   _e(r.get("firma") or "-"), _e(r.get("ulke") or "-"),
                   _e(r.get("hat")), _e(r.get("asama")),
                   _e(note) if note else _e(r.get("baslik")),
                   _e(r.get("baslik")) if note else "",
                   ("<div class='small'>" + " &middot; ".join(_e(x) for x in extra) + "</div>")
                   if extra else "",
                   _e(r.get("url")), _e(r.get("kaynak"))))
        p.append("</table>")
    else:
        p.append('<div class="bad"><b>Bu donemde dogrulanmis gelisme yok.</b> '
                 'Once erisim tablosunu okuyun: sifir satir cogu zaman piyasa degil '
                 'erisim sorunudur.</div>')

    p.append('<div class="foot">Yontem: %d kaynak (OEM + dergi) otomatik taranir; '
             'her aday haberin yayin tarihi makale sayfasindaki JSON-LD / meta etiketi / '
             '&lt;time&gt; alanindan yapisal olarak okunur. Tarihi yapisal olarak '
             'dogrulanamayan haber rapora ALINMAZ. Kapsam: sicak hadde sonrasi yassi celik '
             'islem hatlari ve teknolojileri. Tekrar engeli kalici state ile saglanir.</div>'
             % len(SOURCES))
    p.append("</html>")
    return "".join(p)


COLS = ["tarih", "firma", "ulke", "hat", "asama", "tedarikci", "kapasite", "tutar",
        "baslik", "kaynak", "url", "puan", "tarih_kaynagi"]


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_email(path, payload, exec_summary=""):
    rows = payload["rows"]
    L = ["# %s &mdash; %s" % (SYSTEM_NAME, payload.get("period", "")), ""]
    if exec_summary:
        L += [exec_summary, ""]
    L.append("**%d dogrulanmis gelisme** | pencere %s - %s | %d kaynak tarandi"
             % (len(rows), payload["window"][0], payload["window"][1],
                payload["stats"].get("kaynak", 0)))
    L.append("")
    for i, r in enumerate(rows, 1):
        L.append("%d. **%s** (%s, %s) &mdash; %s / %s  \n   %s  \n   %s"
                 % (i, r.get("firma") or "-", r.get("ulke") or "-", r["tarih"],
                    r.get("hat"), r.get("asama"), r.get("baslik"), r.get("url")))
    if payload.get("unreachable"):
        L += ["", "> Erisilemeyen kaynaklar: " +
              ", ".join(a for a, _ in payload["unreachable"])]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def to_pdf(html_path, pdf_path):
    for exe in ("/opt/pw-browsers/chromium", "chromium", "chromium-browser",
                "google-chrome"):
        try:
            subprocess.run([exe, "--headless", "--disable-gpu", "--no-sandbox",
                            "--print-to-pdf=" + pdf_path,
                            "--no-pdf-header-footer", "file://" + os.path.abspath(html_path)],
                           check=True, capture_output=True, timeout=90)
            if os.path.exists(pdf_path):
                return True
        except Exception:
            continue
    return False
