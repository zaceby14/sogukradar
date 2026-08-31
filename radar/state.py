# -*- coding: utf-8 -*-
"""Kalici hafiza.

seen : {anahtar: "YYYY-MM-DD"}  -> ayni haber bir daha rapora giremez
periods : gecmis kosularin ozeti

Tekrar engeli PENCERE degil STATE'tir. Bu yuzden pencereyi genis tutmak
guvenlidir; eski haber sadece bir kez, ilk gorildugunde cikar.
"""
import hashlib
import json
import os
import re

from .config import STATE_FILE, VERSION

STOP = {"the", "a", "an", "of", "for", "and", "to", "in", "on", "at", "with", "by",
        "new", "s", "its", "will", "from", "as", "has", "have", "is", "are"}


def norm_key(title, url=""):
    t = re.sub(r"[^a-z0-9 ]+", " ", (title or "").lower())
    toks = [w for w in t.split() if w not in STOP and len(w) > 2]
    toks = sorted(set(toks))[:12]
    base = " ".join(toks)
    if not base:
        base = re.sub(r"^https?://", "", url or "")
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def _migrate_seen(seen):
    """v1 'seen' token-listesi diziydi; v2/v3 {anahtar: tarih} sozlugu."""
    if isinstance(seen, dict):
        return {str(k): (v if isinstance(v, str) else "") for k, v in seen.items()}
    out = {}
    for e in seen or []:
        if isinstance(e, str):
            out[e] = ""
        elif isinstance(e, dict):
            toks = e.get("t") or []
            key = hashlib.sha1((" ".join(sorted(toks))).encode("utf-8")).hexdigest()[:16]
            out["v1:" + key] = e.get("d", "")
    return out


def load():
    if not os.path.exists(STATE_FILE):
        return {"version": VERSION, "seen": {}, "periods": [], "source_health": {}}
    with open(STATE_FILE, encoding="utf-8") as f:
        st = json.load(f)
    st["seen"] = _migrate_seen(st.get("seen"))
    st.setdefault("periods", [])
    st.setdefault("source_health", {})
    # Teknoloji kosesinde tanitilmis konular: {slug: tarih}. Bir teknoloji
    # bir kez tanitilir, bir daha kosede cikmaz.
    st.setdefault("tech_seen", {})
    # Olay parmak izleri: {tedarikci|ulke|asama: tarih}. Ayni olayin farkli
    # baslikli varyanti (baska yayin, baska dil) ikinci kez rapora giremez.
    st.setdefault("events", {})
    # Son 21 gunde raporlanan satir basliklari: gec yazan gazetenin ayni
    # olayi farkli baslikla tekrar sokmasini engeller.
    st.setdefault("son_basliklar", [])
    # REZERV: kapiyi gecmis, tarihi dogrulanmis ama pencere disinda kaldigi
    # icin hic gonderilmemis satirlar. Bulten kisa kalinca buradan tamamlanir
    # - kapi gevsetilmeden hacim saglamanin tek durust yolu.
    st.setdefault("rezerv", [])
    # BULUNAN HAVUZU (2026-08-31) - hacim sorununun asil cozumu.
    #
    # Gunluk tarama kabul ettigi satiri hicbir yere KAYDETMIYORDU:
    # out/tarama.json ertesi gun uzerine yaziliyor, rezerv ise yalniz
    # PENCERE DISI satirlari tutuyor. Aggregator sonuclari ise oynak - bir
    # gun gorunen haber ertesi gun beslemede yok. Sonuc olculdu: sistem
    # hafta boyunca 5-6 ayri kapsam ici haber GORDU ama bultene yalniz
    # pazartesi sabahi hala gorunur olanlar girdi.
    #   29.08  India's Manaksia Steel to invest $84 million to expand...
    #   31.08  ArcelorMittal Confirms Up to R$ 5 Billion for New Cold...
    #   31.08  KEZAD galvanising facility moves closer to commissioning
    # Ucu de tek bir taramada gorundu ve kayboldu.
    #
    # Bu havuz PENCERE ICI, kapiyi gecmis, tarihi dogrulanmis ve henuz
    # gonderilmemis satirlari tutar. Haftalik kosu once buradan tamamlar,
    # sonra rezerve bakar. Kapi GEVSEMEZ - satirlar zaten ayni kapidan
    # gecmistir; degisen tek sey unutulmamalari.
    st.setdefault("bulunan", [])
    # Teknoloji kosesi aday havuzu - kalici. Aday cikmayan haftada kose
    # buradan doldurulur; tanitilan madde tech_seen ile bir daha cikmaz.
    st.setdefault("tech_rezerv", [])
    st["version"] = VERSION
    return st


def save(st):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, STATE_FILE)


def dedup_basliklar(lst):
    """Ayni basligi iki kez tutmaz - en dolu kaydi birakir.

    finalize ayni hafta icin iki kez calistirilabilir (editor duzeltip
    yeniden final alir). Tekrar yazilan kayit hafizayi sisirmekle kalmiyor,
    budama sinirini erken doldurup ESKI ve hala gecerli basliklari disari
    itiyordu.
    """
    from . import taxonomy
    out, ix = [], {}
    for b in lst or []:
        k = taxonomy.fold(b.get("b") or "").strip()
        if not k:
            continue
        j = ix.get(k)
        if j is None:
            ix[k] = len(out)
            out.append(dict(b))
            continue
        eski = out[j]
        for alan in ("t", "a", "ted", "u"):
            if not eski.get(alan) and b.get(alan):
                eski[alan] = b[alan]
    return out


def prune(st, keep=1500, event_days=120):
    seen = st.get("seen", {})
    if len(seen) > keep:
        items = sorted(seen.items(), key=lambda kv: kv[1] or "", reverse=True)[:keep]
        st["seen"] = dict(items)
    # olay kayitlari 120 gunden eskiyse dusurulur: ayni tesiste YENI bir
    # modernizasyon mesru sekilde tekrar haber olabilir
    import datetime as _dt
    cut = (_dt.date.today() - _dt.timedelta(days=event_days)).isoformat()
    st["events"] = {k: v for k, v in st.get("events", {}).items()
                    if (v or "9999") >= cut}
    # SON BASLIKLAR: gonderilmis satirlarin hafizasi.
    #
    # 2026-08-29'da IKI kusur birden ortaya cikti. (1) finalize listeye
    # ekleme yaparken tekrar denetimi yapmiyordu; W35 icin iki kez
    # calistirilinca 11 kaydin 5'i cift yazildi. (2) budama 21 gunle
    # sinirliydi; oysa REZERV 540 gun geriye uzaniyor, yani rezervden gelen
    # bir satir 21 gun once GONDERILMIS bir haberin varyanti olabiliyordu.
    # Nitekim W34'te giden "tk accelis" satiri hafizadan dusmustu ve ayni
    # olayin Yieh varyanti rezervden yeniden listeye girdi. Hafiza rezerv
    # kadar uzun tutulur; 21 gunluk pencereyi kullanan taraf (collect.py
    # ucuncu bacak) kendi kesimini kendisi yapar.
    from .config import REZERV_GUN
    cutb = (_dt.date.today() - _dt.timedelta(days=REZERV_GUN)).isoformat()
    st["son_basliklar"] = dedup_basliklar(
        [b for b in st.get("son_basliklar", [])
         if (b.get("t") or "9999") >= cutb])[-400:]
    # Rezerv: raporlanmis olan ve cok eskiyen satirlar dusurulur.
    from .config import REZERV_GUN, REZERV_MAX
    cutr = (_dt.date.today() - _dt.timedelta(days=REZERV_GUN)).isoformat()
    rez = [r for r in st.get("rezerv", [])
           if r.get("anahtar") not in seen and (r.get("tarih") or "9999") >= cutr]
    rez.sort(key=lambda r: r.get("tarih", ""), reverse=True)
    st["rezerv"] = rez[:REZERV_MAX]
    # Bulunan havuzu: gonderilmis olan duser. Pencere disina dusenler zaten
    # rezervde de duruyor (collect ikisine birden yazar), burada tutmanin
    # anlami kalmaz - pencerenin iki kati yas siniri yeterli.
    cutb2 = (_dt.date.today() - _dt.timedelta(days=45)).isoformat()
    bul = [r for r in st.get("bulunan", [])
           if r.get("anahtar") not in seen and (r.get("tarih") or "9999") >= cutb2]
    bul.sort(key=lambda r: r.get("tarih", ""), reverse=True)
    st["bulunan"] = bul[:REZERV_MAX]
    return st
