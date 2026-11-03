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


def mailto(adres, madde, isaret):
    from urllib.parse import quote
    k = kod(madde.get("anahtar"))
    konu = "SR%s %s" % (isaret, k)
    govde = ("Bu e-postayi oldugu gibi gonderin; sistem tercihinizi ogrenecek.\n\nMadde: %s"
             % (madde.get("baslik") or madde.get("konu") or "")[:120])
    return "mailto:%s?subject=%s&body=%s" % (adres, quote(konu), quote(govde))
