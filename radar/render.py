# -*- coding: utf-8 -*-
"""Cikti uretimi: HTML / CSV / Markdown (+ varsa PDF)."""
import csv
import datetime as dt
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


MAIL_TITLE = "Soğuk Haddehane ve Nihai Hatlarda Sektör & Teknoloji Takibi"

STAGE_COLORS = {"Sozlesme": ("#e3edfb", "#14457e", "SÖZLEŞME"),
                "Ilk urun": ("#e4f4e6", "#1d6b2a", "İLK ÜRÜN"),
                "Insaat": ("#fdeee2", "#8a4a12", "İNŞAAT"),
                "Test": ("#fdeee2", "#8a4a12", "TEST"),
                "Seri uretim": ("#e4f4e6", "#1d6b2a", "SERİ ÜRETİM"),
                "Modernizasyon": ("#f3e9fb", "#5b2d82", "MODERNİZASYON"),
                "Teknoloji": ("#fdeee2", "#8a4a12", "TEKNOLOJİ"),
                "Belirsiz": ("#eceff3", "#5a6270", "BELİRSİZ")}


_ROZET_YAT = ('<span style="background:#eef0f4;color:#5a6270;font-size:10px;'
              'font-weight:700;padding:1px 7px;border-radius:3px;'
              'white-space:nowrap;">YATIRIM</span>')


def _badge(stage):
    bg, fg, lbl = STAGE_COLORS.get(stage, STAGE_COLORS["Belirsiz"])
    return ('<span style="background:%s;color:%s;font-size:10px;font-weight:700;'
            'padding:1px 7px;border-radius:3px;white-space:nowrap;">%s</span>'
            % (bg, fg, lbl))


def _kpi(v, lbl, hi=False):
    bg = "#fdf3e3" if hi else "#f4f6f9"
    fg = "#8a6210" if hi else "#6b7480"
    return ('<td style="background:%s;border-radius:6px;padding:10px 6px;'
            'text-align:center;"><div style="font-size:20px;font-weight:700;">%s</div>'
            '<div style="font-size:10px;color:%s;text-transform:uppercase;'
            'letter-spacing:.4px;">%s</div></td><td style="width:8px;"></td>'
            % (bg, v, fg, lbl))


def _dmy(iso):
    try:
        y, m, d = iso.split("-")
        return "%s.%s.%s" % (d, m, y)
    except Exception:
        return iso


def email_html(payload, ozet=None, tech_items=None, sayi=1):
    """Posta govdesi. Tum stiller satir icidir (posta istemcileri harici
    CSS'i budar). ozet: {'exec':..., 'cumleler':{anahtar:cumle}} - yoksa
    compose modulunun kurallı metinleri kullanilir."""
    from . import compose
    ozet = ozet or {}
    rows = payload["rows"]
    st = payload["stats"]
    cumleler = ozet.get("cumleler", {})
    execs = ozet.get("exec") or compose.exec_summary(rows, st)
    tech_items = tech_items or []

    n_tr = sum(1 for r in rows if r.get("ulke") == "Turkiye"
               or "tosyali" in (r.get("firma") or "").lower())
    n_hat = sum(1 for r in rows if r.get("kategori") != "Yatirim")
    n_yat = len(rows) - n_hat

    h = ['<!doctype html><html lang="tr"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width"></head>',
         '<body style="margin:0;padding:0;background:#eef1f4;">',
         '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
         'style="background:#eef1f4;padding:18px 0;"><tr><td align="center">',
         '<table role="presentation" width="680" cellpadding="0" cellspacing="0" '
         'style="max-width:680px;width:100%;background:#fff;border-radius:8px;'
         'overflow:hidden;font-family:-apple-system,Segoe UI,Roboto,Helvetica,'
         'Arial,sans-serif;color:#1c2026;">']

    h.append('<tr><td style="background:#10233c;padding:22px 28px 18px;">'
             '<div style="color:#fff;font-size:19px;font-weight:700;">%s</div>'
             '<div style="color:#9fb2c8;font-size:12px;margin-top:5px;">'
             'Hafta %s · %s – %s &nbsp;|&nbsp; Sayı #%d</div></td></tr>'
             % (MAIL_TITLE, payload.get("period", ""), _dmy(payload["window"][0]),
                _dmy(payload["window"][1]), sayi))

    h.append('<tr><td style="padding:22px 28px 4px;font-size:14px;line-height:1.6;">'
             '<p style="margin:0 0 10px;">Değerli yöneticilerim ve çalışma arkadaşlarım,</p>'
             '<p style="margin:0 0 6px;color:#3d4450;">Bu bülten, Zeynel tarafından '
             'kurulan yazılım + yapay zekâ destekli otomatik takip sistemiyle '
             'hazırlanmaktadır. Sistem her hafta %d kaynağı (ekipman üreticileri, çelik '
             'üreticileri ve sektör yayınları) tarar; yalnızca yayın tarihi doğrulanmış '
             'gelişmeleri raporlar ve aynı haberi ikinci kez göndermez.</p></td></tr>'
             % st.get("kaynak", 0))

    h.append('<tr><td style="padding:12px 28px 0;"><table role="presentation" '
             'cellpadding="0" cellspacing="0" width="100%"><tr>'
             + _kpi(len(rows), "Gelişme") + _kpi(n_hat, "İşlem hattı")
             + _kpi(n_yat, "Genel yatırım") + _kpi(n_tr, "Türkiye ilgili", hi=True)
             + "</tr></table></td></tr>")

    h.append('<tr><td style="padding:20px 28px 0;">'
             '<div style="font-size:11px;font-weight:700;color:#5a6270;'
             'text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid '
             '#e3e6ea;padding-bottom:6px;margin-bottom:10px;">AI Özeti</div>'
             '<div style="background:#f6f8fa;border-left:4px solid #10233c;'
             'padding:12px 15px;font-size:13.5px;line-height:1.6;color:#2a303a;">%s'
             '</div></td></tr>' % _e(execs))

    if tech_items:
        h.append('<tr><td style="padding:20px 28px 0;">'
                 '<div style="font-size:11px;font-weight:700;color:#5a6270;'
                 'text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid '
                 '#e3e6ea;padding-bottom:6px;margin-bottom:10px;">'
                 'Bu Haftanın Öne Çıkan Teknolojileri</div>'
                 '<table role="presentation" width="100%" cellpadding="0" '
                 'cellspacing="0" style="font-size:13px;line-height:1.55;">')
        for t in tech_items:
            h.append('<tr><td style="padding:0 0 10px;"><b>%s</b><br>'
                     '<span style="color:#3d4450;">%s</span> '
                     '<a href="%s" style="color:#12457a;font-size:11px;">kaynak →</a>'
                     '</td></tr>'
                     % (_e(t.get("konu") or t.get("baslik", "")),
                        _e(t.get("metin", "")), _e(t.get("url", ""))))
        h.append('</table><div style="font-size:11px;color:#8b93a0;margin-top:8px;">'
                 'Bu bölümde bir teknoloji yalnızca bir kez tanıtılır; son 6 aydan '
                 'eski duyurular köşeye alınmaz.</div></td></tr>')

    h.append('<tr><td style="padding:20px 28px 0;">'
             '<div style="font-size:11px;font-weight:700;color:#5a6270;'
             'text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid '
             '#e3e6ea;padding-bottom:6px;margin-bottom:8px;">Haftanın Gelişmeleri</div>')
    if rows:
        h.append('<table role="presentation" width="100%" cellpadding="0" '
                 'cellspacing="0" style="font-size:12.5px;">'
                 '<tr>' + "".join(
                     '<th align="left" style="background:#10233c;color:#fff;'
                     'padding:7px 9px;font-size:10.5px;text-transform:uppercase;'
                     'letter-spacing:.4px;">%s</th>' % c
                     for c in ("Tarih", "Firma / Ülke", "Gelişme", "Aşama")) + "</tr>")
        for r in rows:
            is_tr = r.get("ulke") == "Turkiye" or "tosyali" in (r.get("firma") or "").lower()
            bg = "background:#fdf6ec;" if is_tr else ""
            sub = " · ".join(x for x in (r.get("ulke"), r.get("tedarikci"),
                                         r.get("tutar")) if x)
            cum = cumleler.get(r.get("anahtar")) or compose.row_sentence(r)
            h.append('<tr><td style="padding:9px;border-bottom:1px solid #e8eaee;%s'
                     'white-space:nowrap;">%s</td>'
                     '<td style="padding:9px;border-bottom:1px solid #e8eaee;%s">'
                     '<b>%s</b><br><span style="color:#6b7480;font-size:11px;">%s</span></td>'
                     '<td style="padding:9px;border-bottom:1px solid #e8eaee;%s">%s '
                     '<a href="%s" style="color:#12457a;font-size:11px;">%s →</a></td>'
                     '<td style="padding:9px;border-bottom:1px solid #e8eaee;%s">%s</td></tr>'
                     % (bg, _dmy(r["tarih"]), bg, _e(r.get("firma") or "-"), _e(sub),
                        bg, _e(cum), _e(r.get("url")), _e(r.get("kaynak")),
                        bg, (_ROZET_YAT if r.get("kategori") == "Yatirim"
                             else _badge(r.get("asama")))))
        h.append("</table>")
    else:
        h.append('<div style="background:#fdeeee;border-left:4px solid #c0392b;'
                 'padding:10px 14px;font-size:13px;">Bu hafta tarih doğrulamasından '
                 'geçen gelişme kaydedilmedi. Alt bilgideki tarama istatistiği erişim '
                 'sorununu gösterir.</div>')
    h.append("</td></tr>")

    h.append('<tr><td style="padding:20px 28px 6px;font-size:13.5px;line-height:1.6;'
             'color:#3d4450;">Saygılarımla,<br><b>Zeynel</b></td></tr>')

    # TARAMA TABLOSU - kullanici istegi: her mailde taranan/elenen sayilar.
    unreach = payload.get("unreachable", [])
    h.append('<tr><td style="padding:16px 28px 0;">'
             '<div style="font-size:11px;font-weight:700;color:#5a6270;'
             'text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid '
             '#e3e6ea;padding-bottom:6px;margin-bottom:8px;">Bu Haftanın Taraması</div>'
             '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
             'style="font-size:12px;">')
    # Pencere uzunlugu payload'dan okunur. Sabit "7 günlük" yazisi, pencere
    # 15 güne cikarildiktan sonra (2026-08-17) okuyucuya yanlis sayi
    # gosteriyordu - istatistik tablosu raporun kendi olcusudur, sabit olamaz.
    try:
        _w0 = dt.date.fromisoformat(payload["window"][0])
        _w1 = dt.date.fromisoformat(payload["window"][1])
        _pencere = "%d günlük" % ((_w1 - _w0).days or 1)
    except Exception:
        _pencere = "tarama"
    for i, (lbl, val) in enumerate([
            ("Taranan kaynak", st.get("kaynak", 0)),
            ("Erişilemeyen kaynak", len(unreach)),
            ("Görülen haber bağlantısı", st.get("ham", 0)),
            ("Ön elemeyi geçen", st.get("on_eleme_gecti", 0)),
            ("Tarih için açılan makale", st.get("makale_acildi", 0)),
            ("Elendi: tarihi doğrulanamadı", st.get("tarihsiz_elendi", 0)),
            ("Elendi: %s pencere dışı" % _pencere, st.get("pencere_disi", 0)),
            ("Elendi: kapsam dışı", st.get("kapsam_disi", 0)),
            ("Elendi: daha önce raporlandı", st.get("tekrar", 0)),
            ("<b>Rapora giren</b>", "<b>%d</b>" % st.get("kabul", 0))]):
        bg = "background:#f6f8fa;" if i % 2 == 0 else ""
        h.append('<tr><td style="padding:5px 9px;%s">%s</td>'
                 '<td align="right" style="padding:5px 9px;%s">%s</td></tr>'
                 % (bg, lbl, bg, val))
    h.append("</table></td></tr>")

    if unreach:
        h.append('<tr><td style="padding:16px 28px 0;">'
                 '<div style="font-size:11px;font-weight:700;color:#8a6210;'
                 'text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid '
                 '#f0e2c4;padding-bottom:6px;margin-bottom:8px;">'
                 'İnsan Müdahalesi Gerekenler</div>'
                 '<div style="font-size:12px;color:#3d4450;line-height:1.6;">'
                 'Bu kaynaklar bot korumasına takıldı, elle bakılmalı:<br>')
        for ad, hata in unreach[:12]:
            h.append('&bull; %s <span style="color:#8b93a0;">(%s)</span><br>'
                     % (_e(ad), _e(str(hata)[:28])))
        h.append("</div></td></tr>")

    unreach = payload.get("unreachable", [])
    h.append('<tr><td style="background:#f4f6f9;padding:14px 28px;font-size:10.5px;'
             'color:#7b8290;line-height:1.6;">Kapsam: asitleme, soğuk hadde, temper, '
             'tavlama, galvaniz/kaplama, boyama, teneke, dilme/boy kesme, merdane '
             'atölyesi, şerit birleştirme, bobin taşıma, yüzey muayene, ölçüm ve hat '
             'otomasyonu, elektrik çeliği. Yayın tarihi kaynağın kendi beyanından '
             '(RSS, JSON-LD, meta, Last-Modified) okunur; doğrulanamayan haber '
             'rapora alınmaz.</td></tr>')

    h.append('<tr><td style="background:#10233c;padding:10px 28px;text-align:center;'
             'font-size:10.5px;color:#9fb2c8;letter-spacing:.4px;">'
             'powered by <b style="color:#fff;">Zeynel Abidin Çopur</b></td></tr>')
    h.append("</table></td></tr></table></body></html>")
    return "".join(h)


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
