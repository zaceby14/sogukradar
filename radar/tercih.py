# -*- coding: utf-8 -*-
"""OKUYUCU GERI BILDIRIMI - begeni/begenmeme ile ogrenen siralama.

2026-11-03 kullanici: "kisi begene tiklarsa algoritma bunu veri olarak alsa ve
o tarz haberlere daha cok odaklansa".

AKIS (sunucu YOK, hesap YOK):
  1) Bultendeki her madde yaninda "Faydali / Ilgisiz" mailto baglantisi var.
     Tiklayinca konu satiri "SR+ <kod>" ya da "SR- <kod>" olan hazir bir
     e-posta acilir; okuyucu Gonder'e basar. Erdemir adresinden de calisir.
  2) Her taramada `radar geri-bildirim` gonderen Gmail kutusunu IMAP ile okur
     (ayni uygulama sifresi), kodlari maddelerin OZELLIKLERINE dagitir:
     hat, asama, ulke, bolum, kaynak, urun, konu.
  3) Siralama bu agirliklardan SINIRLI bir bonus alir (+-BONUS_SINIR puan).
     Geri bildirim KAPSAMI DEGISTIREMEZ - kapidan gecmeyen haber begeniyle
     giremez; yalniz kapidan gecenlerin sirasi ve secimi degisir.
"""
import email
import email.header
import hashlib
import imaplib
import os
import re
import datetime as dt

BONUS_SINIR = 12.0
AGIRLIK_SINIR = 10
_KOD = re.compile(r"\bSR\s*([+\-])\s*([a-z0-9]{10})\b", re.I)


def kod(anahtar):
    return hashlib.sha1((anahtar or "").encode("utf-8")).hexdigest()[:10]


def ozellikler(m, bolum):
    """Bir maddenin ogrenilebilir ozellikleri (kucuk, kararli dizgeler)."""
    f = ["bolum:" + bolum]
    for alan in ("hat", "asama", "ulke", "kaynak", "urun", "konu"):
        v = (m.get(alan) or "").strip()
        if v and v != "Belirsiz":
            f.append("%s:%s" % (alan, v))
    if m.get("kategori"):
        f.append("kat:" + m["kategori"])
    return f


def bonus(m, bolum, st):
    w = st.get("tercih") or {}
    if not w:
        return 0.0
    t = sum(w.get(f, 0) for f in ozellikler(m, bolum))
    return max(-BONUS_SINIR, min(BONUS_SINIR, 1.5 * t))


def ozet_metni(st, n=5):
    """LLM'e verilecek kisa tercih ozeti."""
    w = st.get("tercih") or {}
    iyi = [k for k, v in sorted(w.items(), key=lambda kv: -kv[1]) if v > 0][:n]
    kotu = [k for k, v in sorted(w.items(), key=lambda kv: kv[1]) if v < 0][:n]
    if not iyi and not kotu:
        return ""
    return "Okuyucu geri bildirimi - daha cok begenilen: %s; begenilmeyen: %s" % (
        ", ".join(iyi) or "-", ", ".join(kotu) or "-")


def kaydet_gonderilen(st, maddeler):
    """maddeler: [(madde, bolum)] - kod -> ozellik eslemesi saklanir (180 gun)."""
    d = st.setdefault("gonderilen_ozellik", {})
    bugun = dt.date.today().isoformat()
    for m, bolum in maddeler:
        a = m.get("anahtar")
        if a:
            d[kod(a)] = {"f": ozellikler(m, bolum), "t": bugun,
                         "b": (m.get("baslik") or "")[:90]}
    sinir = (dt.date.today() - dt.timedelta(days=180)).isoformat()
    st["gonderilen_ozellik"] = {k: v for k, v in d.items() if v.get("t", "") >= sinir}


def uygula(st, oylar):
    """oylar: [(isaret, kod, gonderen)] -> agirliklari gunceller. Kisi basi kod basina 1 oy."""
    d = st.get("gonderilen_ozellik") or {}
    w = st.setdefault("tercih", {})
    sayilan = st.setdefault("gb_oy", {})
    n = 0
    for isaret, k, kimden in oylar:
        if k not in d:
            continue
        anahtar = k + "|" + (kimden or "")
        if anahtar in sayilan:
            continue
        sayilan[anahtar] = isaret
        delta = 1 if isaret == "+" else -1
        for f in d[k]["f"]:
            w[f] = max(-AGIRLIK_SINIR, min(AGIRLIK_SINIR, w.get(f, 0) + delta))
        n += 1
    if len(sayilan) > 3000:
        st["gb_oy"] = dict(list(sayilan.items())[-3000:])
    return n


def _coz(baslik):
    parca = []
    for metin, kod_ in email.header.decode_header(baslik or ""):
        parca.append(metin.decode(kod_ or "utf-8", "replace") if isinstance(metin, bytes) else metin)
    return "".join(parca)


def imap_oku(kullanici, sifre, gun=45, log=print):
    """Gelen kutusundan SR+/SR- postalarini okur -> [(isaret, kod, gonderen)]."""
    oylar = []
    m = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=60)
    try:
        m.login(kullanici, sifre)
        m.select("INBOX", readonly=True)
        once = (dt.date.today() - dt.timedelta(days=gun)).strftime("%d-%b-%Y")
        _, veri = m.search(None, '(SINCE %s SUBJECT "SR")' % once)
        for num in (veri[0] or b"").split()[-500:]:
            _, d = m.fetch(num, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])")
            ham = d[0][1] if d and isinstance(d[0], tuple) else b""
            msg = email.message_from_bytes(ham)
            konu = _coz(msg.get("Subject", ""))
            kimden = email.utils.parseaddr(msg.get("From", ""))[1].lower()
            for isaret, k in _KOD.findall(konu):
                oylar.append((isaret, k.lower(), kimden))
    finally:
        try:
            m.logout()
        except Exception:
            pass
    log("geri bildirim: %d oy okundu" % len(oylar))
    return oylar


def mailto(adres, madde, isaret):  # eski kanal (kapali)
    from urllib.parse import quote
    k = kod(madde.get("anahtar"))
    konu = "SR%s %s" % (isaret, k)
    govde = ("Bu e-postayi oldugu gibi gonderin; sistem tercihinizi ogrenecek.\n\nMadde: %s"
             % (madde.get("baslik") or madde.get("konu") or "")[:120])
    return "mailto:%s?subject=%s&body=%s" % (adres, quote(konu), quote(govde))


# ----------------------------------------------------------------------
# GOOGLE FORM KANALI (2026-11-03): mailto posta programini aciyordu.
# Oy baglantisi formResponse adresine GET'tir: tiklayinca tarayicida yalniz
# Google'in "Yanitiniz kaydedildi" sayfasi acilir. Yanitlar formun bagli
# tablosundan (Web'de yayinla -> CSV) okunur. Form kimligi bilinmeyen kimse
# icin anlamsizdir; entry kimligi formun sayfasindan calisma aninda bulunur.
# ----------------------------------------------------------------------
FORM_ID = os.environ.get("RADAR_FORM_ID", "1FAIpQLScpiVNw2tsnceyk-rImYOrZaKTDlW3egy0UxbbCz-i5afcDTw")
# Yanit tablosu "Web'de yayinla" ile SALT OKUNUR CSV olarak yayinlandi (2026-11-03).
FORM_CSV = os.environ.get("RADAR_FORM_CSV", "https://docs.google.com/spreadsheets/d/e/"
                          "2PACX-1vREgMxfMmwX08k0yb0rx_SxQ6cgiFjPL9dGK3QjIadQQvY572HINJnj-f3HRVReR3rmQCinSVOI_H1a"
                          "/pub?gid=1110406152&single=true&output=csv")
KOD_BASINA_OY_SINIRI = 3          # form kimin tikladigini bilmez: tekrar tiklamaya sinir


def form_entry(fetch=None):
    """Formun ilk sorusunun entry kimligi (FB_PUBLIC_LOAD_DATA_ icinden)."""
    from . import http
    ok, page, _ = (fetch or http.fetch)(
        "https://docs.google.com/forms/d/e/%s/viewform" % FORM_ID)
    if not ok:
        return ""
    m = re.search(r"FB_PUBLIC_LOAD_DATA_\s*=\s*(.*?);\s*</script>", page, re.S)
    if not m:
        return ""
    n = re.search(r"\[\[(\d{6,}),null,", m.group(1))
    return n.group(1) if n else ""


def form_link(entry, madde, isaret):
    from urllib.parse import quote
    deger = "SR%s %s" % (isaret, kod(madde.get("anahtar")))
    return ("https://docs.google.com/forms/d/e/%s/formResponse?entry.%s=%s&submit=Submit"
            % (FORM_ID, entry, quote(deger)))


def form_oku(csv_url, fetch=None):
    """Yayinlanmis yanit tablosu (CSV) -> [(isaret, kod, zaman)]."""
    import csv, io
    from . import http
    ok, metin, _ = (fetch or http.fetch)(csv_url, use_cache=False) if fetch is None else fetch(csv_url)
    if not ok:
        return []
    oylar = []
    for satir in csv.reader(io.StringIO(metin)):
        if len(satir) < 2:
            continue
        for isaret, k in _KOD.findall(" ".join(satir[1:])):
            oylar.append((isaret, k.lower(), "form:" + satir[0]))
    return oylar


def uygula_form(st, oylar):
    """Form oylari: zaman damgasi kimlik yerine; kod basina en fazla N oy sayilir."""
    sayac = st.setdefault("gb_form_sayac", {})
    secili = []
    for isaret, k, kimlik in oylar:
        anahtar = k + isaret
        if (k + "|" + kimlik) in (st.get("gb_oy") or {}):
            continue
        if sayac.get(anahtar, 0) >= KOD_BASINA_OY_SINIRI:
            continue
        sayac[anahtar] = sayac.get(anahtar, 0) + 1
        secili.append((isaret, k, kimlik))
    return uygula(st, secili)


def form_testi(log=print):
    """Uctan uca: entry bul -> test oyu gonder -> CSV'de gor. Actions'ta calisir."""
    import time, urllib.request
    from . import http
    e = form_entry()
    log("entry: %s" % (e or "BULUNAMADI"))
    if not e:
        return False
    test_kod = "testkod000"
    url = ("https://docs.google.com/forms/d/e/%s/formResponse?entry.%s=SR%%2B%%20%s&submit=Submit"
           % (FORM_ID, e, test_kod))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=http.HEADERS), timeout=30) as r:
            sayfa = r.read().decode("utf-8", "replace")
        log("gonderim: HTTP %s, kaydedildi sayfasi: %s" % (r.status, "freebirdFormviewerViewResponseConfirmationMessage" in sayfa or "kaydedildi" in sayfa.lower() or "recorded" in sayfa.lower()))
    except Exception as ex:
        log("gonderim HATA: %s" % ex)
        return False
    for i in range(6):
        time.sleep(20)
        oylar = form_oku(FORM_CSV)
        if any(k == test_kod for _, k, _ in oylar):
            log("CSV: test oyu goruldu (%d. deneme), toplam %d oy satiri" % (i + 1, len(oylar)))
            return True
    log("CSV: test oyu 2 dakikada gorunmedi (yayinlanmis tablo gecikmeli guncellenebilir)")
    return False


# ----------------------------------------------------------------------
# TESLIM KONTROLU (2026-11-09): "Erdemir adresine hic gelmedi". Alici sunucu
# reddederse Gmail gonderene "Mail Delivery Subsystem" bildirimi yollar.
# Bu bildirimler okunur; alici adresinin yerel kismi maskelenir.
# ----------------------------------------------------------------------
def teslim_kontrol(kullanici, sifre, gun=14, log=print):
    import email.utils
    sonuc = []
    m = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=60)
    try:
        m.login(kullanici, sifre)
        for kutu in ("INBOX", '"[Gmail]/Spam"', '"[Gmail]/All Mail"'):
            try:
                if m.select(kutu, readonly=True)[0] != "OK":
                    continue
            except Exception:
                continue
            once = (dt.date.today() - dt.timedelta(days=gun)).strftime("%d-%b-%Y")
            _, veri = m.search(None, '(SINCE %s OR FROM "mailer-daemon" FROM "postmaster")' % once)
            for num in (veri[0] or b"").split()[-40:]:
                _, d = m.fetch(num, "(BODY.PEEK[])")
                ham = d[0][1] if d and isinstance(d[0], tuple) else b""
                msg = email.message_from_bytes(ham)
                govde = ""
                for part in msg.walk():
                    if part.get_content_type() in ("text/plain", "message/delivery-status"):
                        try:
                            govde += part.get_payload(decode=True).decode("utf-8", "replace")
                        except Exception:
                            govde += str(part.get_payload())[:2000]
                govde = re.sub(r"[\w.+-]+@", "***@", govde)
                ozet = " | ".join(l.strip() for l in govde.splitlines()
                                  if re.search(r"(?i)status|diagnostic|action|reason|550|554|553|552|421|451|blocked|reject|spam|policy|quarantin|@", l))[:700]
                kayit = {"kutu": kutu, "tarih": msg.get("Date", ""), "konu": _coz(msg.get("Subject", ""))[:120],
                         "ozet": ozet}
                if kayit not in sonuc:
                    sonuc.append(kayit)
            if kutu == "INBOX" and sonuc:
                break
    finally:
        try:
            m.logout()
        except Exception:
            pass
    log("teslim bildirimi (bounce): %d" % len(sonuc))
    for k in sonuc:
        log("- %s | %s | %s\n    %s" % (k["kutu"], k["tarih"], k["konu"], k["ozet"]))
    return sonuc
