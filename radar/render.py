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


# Teknoloji kosesi aday cikmayan haftalarda da render edilir; metin budur.
TEKNOLOJI_BOS = ("Bu hafta gerçek bir yenilik (ilk uygulama, yeni proses, Ar-Ge, pilot "
                 "tesis) bulunamadı. Ürün tanıtımı ve tedarik haberleri köşeye alınmaz.")

# Elle eklenen satirlarin gorunur isareti (2026-08-17). Okuyucu hangi satirin
# yazilimdan, hangisinin editorden geldigini ayirt edebilmeli.
_ROZET_AI = ('<span style="background:#e8f1fb;color:#12457a;font-size:9.5px;'
             'font-weight:700;padding:1px 5px;border-radius:3px;'
             'margin-right:5px;white-space:nowrap;">+ AI</span>')


def _baslik(metin):
    """Posta govdesindeki bolum basligi."""
    return ('<div style="font-size:11px;font-weight:700;color:#5a6270;'
            'text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid '
            '#e3e6ea;padding-bottom:6px;margin-bottom:10px;">%s</div>' % _e(metin))


# Rezervden gelen satir: kapiyi gecmis, tarihi dogrulanmis ama pencere
# disinda kaldigi icin daha once gonderilmemis haber. Okuyucu neden eski
# tarihli bir satir gordugunu anlamali.
_ROZET_REZERV = ('<span style="background:#f2eee6;color:#7a6a4f;font-size:9.5px;'
                 'font-weight:700;padding:1px 5px;border-radius:3px;'
                 'margin-right:5px;white-space:nowrap;">GEÇ YAKALANDI</span>')


def _firma_hucresi(r):
    """Firma adi; satirin kaynagina gore rozet eklenir."""
    ad = _e(r.get("firma") or "-")
    if r.get("elle_eklendi"):
        return _ROZET_AI + ad
    if r.get("rezerv"):
        return _ROZET_REZERV + ad
    return ad


_ROZET_YAT = ('<span style="background:#eef0f4;color:#5a6270;font-size:10px;'
              'font-weight:700;padding:1px 7px;border-radius:3px;'
              'white-space:nowrap;">YATIRIM</span>')


def _badge(stage):
    bg, fg, lbl = STAGE_COLORS.get(stage, STAGE_COLORS["Belirsiz"])
    return ('<span style="background:%s;color:%s;font-size:10px;font-weight:700;'
            'letter-spacing:.4px;padding:2px 7px;border-radius:3px;white-space:nowrap;">%s</span>'
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


def _oy(madde):
    """Faydali/Ilgisiz mailto baglantilari (RADAR_GERI_ADRES tanimliysa)."""
    import os
    from . import tercih
    entry = os.environ.get("RADAR_FORM_ENTRY") or ""
    if not entry or not madde.get("anahtar"):
        return ""
    return ('<span style="white-space:nowrap;font-size:12px;">'
            '<a href="%s" style="color:#15803d;text-decoration:none;">&#128077;&nbsp;Faydalı</a>'
            '&nbsp;&nbsp;&nbsp;<a href="%s" style="color:#9ca3af;text-decoration:none;">'
            '&#128078;&nbsp;İlgisiz</a></span>' % (_e(tercih.form_link(entry, madde, "+")),
                         _e(tercih.form_link(entry, madde, "-"))))


def email_html(payload, ozet=None, tech_items=None, sayi=1):
    """Posta govdesi - SADE KART DUZENI (2026-11-21, kurul tasarimi).

    Tek sutun, en fazla 640 px, tablo tabanli ve tum stiller satir ici (Outlook
    ve Gmail uyumu). Her madde bir kart: ustte gri meta satiri (tarih, ulke,
    kaynak), kalin firma, Turkce cumle, altta asama rozeti + kaynak + oylar.
    KPI kutulari ve uzun tarama tablosu kaldirildi; tarama tek satir.
    """
    from . import compose
    ozet = ozet or {}
    rows = payload["rows"]
    st = payload["stats"]
    cumleler = ozet.get("cumleler", {})
    execs = ozet.get("exec") or compose.exec_summary(rows, st)
    tech_items = tech_items or []
    piy = ozet.get("piyasa") or []

    n_tr = sum(1 for r in rows if r.get("ulke") == "Turkiye"
               or "tosyali" in (r.get("firma") or "").lower())
    n_hat = sum(1 for r in rows if r.get("kategori") != "Yatirim")
    n_yat = len(rows) - n_hat
    try:
        pencere = "%s – %s" % (_dmy(payload["window"][0]), _dmy(payload["window"][1]))
    except Exception:
        pencere = ""

    MUREKKEP, LACIVERT, GRI, CIZGI = "#1f2933", "#0f2a47", "#6b7280", "#e5e7eb"
    on_metin = "%d gelişme" % len(rows)
    if rows:
        on_metin += " · " + (rows[0].get("firma") or rows[0].get("baslik", ""))[:60]

    h = ['<!doctype html><html lang="tr"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1"></head>',
         '<body style="margin:0;padding:0;background:#f3f4f6;">',
         '<div style="display:none;max-height:0;overflow:hidden;">%s</div>' % _e(on_metin),
         '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
         'style="background:#f3f4f6;"><tr><td align="center" style="padding:16px 8px;">',
         '<!--[if mso]><table role="presentation" width="640" cellpadding="0" cellspacing="0">'
         '<tr><td><![endif]-->',
         '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
         'style="max-width:640px;background:#ffffff;border-radius:10px;font-family:-apple-system,'
         'Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:' + MUREKKEP + ';">']

    # Baslik
    h.append('<tr><td style="padding:22px 24px 18px;border-bottom:3px solid %s;">'
             '<div style="font-size:12px;color:%s;letter-spacing:.6px;text-transform:uppercase;'
             'font-weight:700;">SoğukRadar &middot; Sayı #%d</div>'
             '<div style="font-size:21px;font-weight:700;color:%s;margin-top:4px;line-height:1.3;">%s</div>'
             '<div style="font-size:13px;color:%s;margin-top:4px;">Hafta %s &middot; %s</div></td></tr>'
             % (LACIVERT, GRI, sayi, LACIVERT, _e(MAIL_TITLE), GRI,
                _e(payload.get("period", "")), _e(pencere)))

    # Giris
    ozet_cumle = ("Bu hafta <b>%d doğrulanmış gelişme</b> var: %d işlem hattı, %d genel yatırım%s."
                  % (len(rows), n_hat, n_yat,
                     ("; %d tanesi Türkiye ile ilgili" % n_tr) if n_tr else ""))
    h.append('<tr><td style="padding:20px 24px 0;font-size:15px;line-height:1.6;">'
             'Değerli yöneticilerim ve çalışma arkadaşlarım,<br>'
             '<span style="color:#4b5563;">%s</span></td></tr>' % ozet_cumle)

    # AI Ozeti
    h.append('<tr><td style="padding:16px 24px 0;"><table role="presentation" width="100%%" '
             'cellpadding="0" cellspacing="0" style="background:#f8fafc;border-left:3px solid %s;">'
             '<tr><td style="padding:12px 16px;font-size:14px;line-height:1.6;color:#374151;">'
             '<b style="color:%s;">AI Özeti &nbsp;</b>%s</td></tr></table></td></tr>'
             % (LACIVERT, LACIVERT, _e(execs)))

    def bolum(baslik):
        h.append('<tr><td style="padding:26px 24px 10px;"><div style="font-size:16px;'
                 'font-weight:700;color:%s;">%s</div></td></tr>' % (LACIVERT, _e(baslik)))

    def kart(meta, firma_html, cumle, url, rozet, oy, arka=""):
        alt = ""
        if rozet:
            alt += rozet + "&nbsp;&nbsp;"
        if url:
            alt += ('<a href="%s" style="color:#1d4ed8;text-decoration:none;font-weight:600;">'
                    'Kaynak&nbsp;&rarr;</a>' % _e(url))
        h.append('<tr><td style="padding:0 24px 12px;"><table role="presentation" width="100%%" '
                 'cellpadding="0" cellspacing="0" style="border:1px solid %s;border-radius:8px;%s">'
                 '<tr><td style="padding:14px 16px;">'
                 '<div style="font-size:12px;color:%s;">%s</div>%s'
                 '<div style="font-size:15px;line-height:1.5;margin-top:4px;">%s</div>'
                 '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" '
                 'style="margin-top:10px;"><tr><td style="font-size:12px;">%s</td>'
                 '<td align="right" style="font-size:12px;white-space:nowrap;">%s</td></tr></table>'
                 '</td></tr></table></td></tr>'
                 % (CIZGI, arka, GRI, meta,
                    ('<div style="font-size:16px;font-weight:700;margin-top:3px;">%s</div>' % firma_html)
                    if firma_html else "", _e(cumle), alt, oy))

    # Teknoloji Kosesi - listeden ONCE (2026-08-17 karari korunur)
    bolum("Teknoloji Köşesi")
    if tech_items:
        for t in tech_items:
            meta = " &middot; ".join(_e(x) for x in (_dmy(t.get("tarih", "")), t.get("kaynak")) if x)
            kart(meta, _e(t.get("konu") or t.get("baslik", "")), t.get("metin", ""), t.get("url"),
                 "", _oy(dict(t, baslik=t.get("konu") or t.get("baslik", ""))))
        h.append('<tr><td style="padding:0 24px;font-size:12px;color:%s;">Bir teknoloji yalnızca '
                 'bir kez tanıtılır; 1 yıldan eski duyurular alınmaz.</td></tr>' % GRI)
    else:
        h.append('<tr><td style="padding:0 24px;font-size:13px;color:#4b5563;">%s</td></tr>'
                 % _e(TEKNOLOJI_BOS))

    # Gelismeler
    bolum("Haftanın Gelişmeleri")
    if rows:
        for r in rows:
            is_tr = r.get("ulke") == "Turkiye" or "tosyali" in (r.get("firma") or "").lower()
            meta = " &middot; ".join(_e(x) for x in (_dmy(r.get("tarih", "")),
                                                    compose.ulke_goster(r.get("ulke")),
                                                    r.get("tedarikci"), r.get("tutar"),
                                                    r.get("kaynak")) if x)
            cum = cumleler.get(r.get("anahtar")) or compose.row_sentence(r)
            # "BELIRSIZ" rozeti okura bilgi vermiyor (2026-11-21, kurul): gosterilmez.
            rozet = _ROZET_YAT if r.get("kategori") == "Yatirim" else (
                _badge(r.get("asama")) if r.get("asama") not in (None, "", "Belirsiz") else "")
            kart(meta, _firma_hucresi(r) if r.get("firma") else "", cum, r.get("url"), rozet, _oy(r),
                 "background:#fffbf2;" if is_tr else "")
    else:
        h.append('<tr><td style="padding:0 24px;font-size:14px;color:#4b5563;">Bu hafta tarih '
                 'doğrulamasından geçen gelişme kaydedilmedi.</td></tr>')

    # Piyasa Gundemi
    if piy:
        bolum("Piyasa Gündemi")
        for m in piy:
            meta = " &middot; ".join(_e(x) for x in (_dmy(m.get("tarih", "")), m.get("kaynak")) if x)
            kart(meta, "", m.get("metin") or m.get("baslik", ""), m.get("url"), "", _oy(m))

    # AI Kontrolu - kisa
    ai = compose.ai_bolumu(ozet)
    h.append('<tr><td style="padding:24px 24px 0;font-size:13px;line-height:1.55;color:#4b5563;">'
             '<b style="color:%s;">AI Kontrolü ve Eklemeleri</b>' % LACIVERT)
    if ai:
        for grup, satirlar in ai:
            h.append('<div style="margin-top:6px;"><b style="color:#374151;">%s:</b> %s</div>'
                     % (_e(grup), " · ".join(_e(x) for x in satirlar)))
    else:
        h.append('<div style="margin-top:4px;">%s</div>' % _e(compose.AI_BOLUM_BOS))
    h.append('</td></tr>')

    if os.environ.get("RADAR_FORM_ENTRY"):
        h.append('<tr><td style="padding:10px 24px 0;font-size:12px;line-height:1.5;color:%s;">'
                 '&#128077; Faydalı / &#128078; İlgisiz bağlantısına tek tıklamanız yeterli; '
                 'sistem oylarınızla sonraki bültenlerde önceliği belirler.</td></tr>' % GRI)

    h.append('<tr><td style="padding:24px 24px 24px;font-size:15px;line-height:1.6;">'
             'Saygılarımla,<br><b>Zeynel</b></td></tr>')

    # Tarama - tek satir
    unreach = payload.get("unreachable", [])
    adlar = []
    for ad, _h in unreach:
        if ad not in adlar and "Google News" not in ad and "Bing" not in ad:
            adlar.append(ad)
    tarama = ("<b style=\"color:#374151;\">Bu Haftanın Taraması:</b> %d kaynak &middot; %s bağlantı "
              "&middot; %d ön eleme &middot; Elendi: kapsam dışı %d, pencere dışı %d, tekrar %d "
              "&middot; <b style=\"color:#374151;\">%d rapora girdi</b>"
              % (st.get("kaynak", 0), format(st.get("ham", 0), ",").replace(",", "."),
                 st.get("on_eleme_gecti", 0), st.get("kapsam_disi", 0), st.get("pencere_disi", 0),
                 st.get("tekrar", 0), len(rows)))
    if adlar:
        tarama += " &middot; erişilemeyen: %s%s" % (_e(", ".join(adlar[:3])),
                                                     " vb." if len(adlar) > 3 else "")
    h.append('<tr><td style="padding:14px 24px;background:#f9fafb;border-top:1px solid %s;'
             'font-size:12px;line-height:1.6;color:%s;">%s'
             '<div style="margin-top:8px;font-size:11px;color:#9ca3af;">Kapsam: asitleme, soğuk hadde, '
             'temper, tavlama, galvaniz/kaplama, boyama, teneke, dilme/boy kesme, merdane atölyesi, '
             'yüzey muayene, ölçüm ve hat otomasyonu, elektrik çeliği. Yayın tarihi kaynağın kendi '
             'beyanından okunur; doğrulanamayan haber alınmaz.</div></td></tr>' % (CIZGI, GRI, tarama))
    h.append('<tr><td style="padding:12px 24px;text-align:center;font-size:11px;color:#9ca3af;'
             'border-top:1px solid %s;">powered by <b style="color:#374151;">Zeynel Abidin Çopur</b>'
             '</td></tr>' % CIZGI)
    h.append('</table><!--[if mso]></td></tr></table><![endif]--></td></tr></table></body></html>')
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
