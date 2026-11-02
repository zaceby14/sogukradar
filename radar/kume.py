# -*- coding: utf-8 -*-
"""OLAY KUMELEME - ayni olayin birden cok satiri tek satira iner.

NEDEN VAR (2026-11-02). Editor olmadan cikan ilk gercek bulten (2026-W40,
28 Eylul) 14 satirdi ve yarisi cop idi. POSCO'nun TEK yatirimi besi birden
satir olarak girdi:

    POSCO Invests 480 Billion Won in New Auto Steel Coating Plant
    POSCO will invest $359 million to build a continuous galvanizing line
    POSCO to Build State-of-the-Art Galvanized Automotive Steel Sheet Plant
    POSCO Breaks Ground on New Continuous Galvanizing Line
    POSCO, Otomotiv Celigi Icin 359 Milyon Dolarlik Yeni Galvanizleme Hatti

(480 milyar won ~ 359 milyon dolar: ayni yatirim.) Flux Steel de iki kez
girdi. Yani "tekrar savunmasi" gercek dunyada ise yaramiyordu ve bunu yalniz
bir editorun gozu yakaliyordu. Otomasyonun asil isi budur.

NEDEN MEVCUT SAVUNMA YAKALAMADI. Olay parmak izi firma adini kullanir ve
firma alani fiil artiklariyla kirliydi: 'POSCO Breaks Ground', 'POSCO will',
'Nippon Steel Backs', 'Flux Steel Works' ile 'Flux Steel'. Izler hic
kesismedi. Ayrica asama her yayinda farkli okunuyordu (Sozlesme / Insaat /
Teknoloji / Belirsiz) ve asama izin parcasiydi.

KURAL. Ayni FIRMA KOKU + ayni HAT (Belirsiz degil) => ayni kume; asama ve
ulke KARISMAZ, cunku yayindan yayina degisen OKUMALAR bunlardir. Firma ayni
ama hat bilinmiyorsa baslik benzerligi aranir. Kumenin TEMSILCISI en ileri
asamadaki satirdir; eksik alanlar (tutar, kapasite, ulke, tedarikci)
kumenin dogrulanmis uyelerinden doldurulur - uydurma yok. Diger uyeler
satirin 'ilgili' listesine girer: okuyucu "bu haber su kaynaklarda da cikti"
diye gorur, hicbir sey kaybolmaz.

GONDERILMIS HABERE KARSI: ayni firma + ayni hat daha once gonderildiyse,
yalniz YENI satir daha ILERI bir asamadaysa girer (temel atma -> ilk uretim
gercek bir gelismedir); ayni ya da daha geri asama tekrardir.
"""
import re

from . import taxonomy

# Asama sirasi: yuksek = daha ileri. Temsilci secimi ve gecmis karsilastirmasi.
ASAMA_SIRA = {"Ilk urun": 6, "Seri uretim": 6, "Test": 5, "Insaat": 4,
              "Sozlesme": 3, "Modernizasyon": 3, "Teknoloji": 2, "Belirsiz": 0}

# Firma adinin sonuna yapisan KURUMSAL son ekler - kume anahtarindan atilir.
_SON_EK = {"works", "plant", "group", "corp", "corporation", "ltd", "limited",
           "inc", "co", "company", "sa", "ag", "gmbh", "spa", "holding",
           "holdings", "industries", "industry", "technologies", "technology",
           "steelworks", "as", "plc", "llc", "nv", "bv"}

# Firma alanina sizan HABER FIILLERI ve kipleri.
_FIIL = {"breaks", "break", "backs", "back", "will", "secures", "secure",
         "invests", "invest", "plans", "plan", "signs", "sign", "starts",
         "start", "begins", "begin", "opens", "open", "completes", "complete",
         "launches", "launch", "unveils", "unveil", "awards", "award",
         "orders", "order", "selects", "select", "approves", "approve",
         "confirms", "confirm", "announces", "announce", "extends", "extend",
         "targets", "target", "eyes", "moves", "kicks", "ramps", "reaches",
         "to", "and", "for", "at", "by", "in", "on", "of", "is", "has", "set"}

_GENEL_ADLAR = {"steel", "the", "new", "a", "an", "it", "company", "group",
                "ground", "india", "china", "turkey", "korea", "japan"}


def firma_kok(firma):
    """Kume anahtari icin firma koku: kucuk harf, fiil/son ek artiksiz."""
    f = taxonomy.fold(firma or "")
    f = re.sub(r"[^\w\s&/-]", " ", f)
    t = [w for w in f.split() if w]
    # sondan: fiil artiklari ve kurumsal son ekler
    degisti = True
    while t and degisti:
        degisti = False
        if t[-1] in _FIIL or t[-1] in _SON_EK:
            t.pop()
            degisti = True
    # ortada fiil varsa orada kes: "posco breaks ground" zaten sondan gitti
    for i, w in enumerate(t):
        if i > 0 and w in _FIIL:
            t = t[:i]
            break
    k = " ".join(t).strip()
    if len(k) < 3 or k in _GENEL_ADLAR:
        return ""
    return k


def _hat(r):
    h = r.get("hat") or ""
    return "" if h in ("", "Belirsiz") else h


_FIRMA_GENEL = {"group", "steel", "steels", "india", "limited", "ltd", "corp", "corporation",
                "industries", "industry", "metal", "metals", "company", "holding", "works",
                "stainless", "special", "international", "global", "europe", "america"}


def _ortak_firma_sozcugu(fa, fb):
    """Iki firma adi en az bir AYIRT EDICI sozcugu paylasiyor mu (>=5 harf, genel degil)."""
    if not fa or not fb:
        return False
    ta = {w for w in taxonomy.fold(fa).split() if len(w) >= 5 and w not in _FIRMA_GENEL}
    tb = {w for w in taxonomy.fold(fb).split() if len(w) >= 5 and w not in _FIRMA_GENEL}
    return bool(ta & tb)


def _ayni_hat_yakin_tarih(a, b):
    ha, hb = _hat(a), _hat(b)
    if not (ha and hb and ha == hb):
        return False
    try:
        import datetime as _dt
        g = abs((_dt.date.fromisoformat(a.get("tarih", "")) -
                 _dt.date.fromisoformat(b.get("tarih", ""))).days)
    except ValueError:
        return False
    return g <= 10


def _ayni_kume(a, b):
    fa, fb = firma_kok(a.get("firma")), firma_kok(b.get("firma"))
    if not fa or fa != fb:
        # FARKLI YAZILMIS AYNI FIRMA (2026-11-02, W45): "Jindal India" ile
        # "BC Jindal Group" ayni olayi iki satir yapti. Ayirt edici ortak
        # firma sozcugu + AYNI (bilinen) hat + 10 gun icinde ise ayni olay.
        return _ortak_firma_sozcugu(fa, fb) and _ayni_hat_yakin_tarih(a, b)
    ha, hb = _hat(a), _hat(b)
    if ha and hb:
        return ha == hb
    # biri ya da ikisi hatsiz: baslik benzerligi sart
    return taxonomy.similar_titles(a.get("baslik", ""), b.get("baslik", ""))


def _puan(r):
    return (ASAMA_SIRA.get(r.get("asama") or "Belirsiz", 0),
            1 if r.get("tutar") else 0,
            1 if r.get("kapasite") else 0,
            r.get("tarih") or "")


def kumele(rows):
    """(temsilciler, kume_sayisi) - sira korunur, temsilci ilk uyenin yerinde."""
    kumeler = []                       # her kume: satir listesi
    for r in rows:
        for k in kumeler:
            if any(_ayni_kume(r, m) for m in k):
                k.append(r)
                break
        else:
            kumeler.append([r])

    out = []
    for k in kumeler:
        if len(k) == 1:
            out.append(k[0])
            continue
        temsilci = dict(max(k, key=_puan))
        for alan in ("tutar", "kapasite", "ulke", "tedarikci"):
            if not temsilci.get(alan):
                for m in k:
                    if m.get(alan):
                        temsilci[alan] = m[alan]
                        break
        temsilci["ilgili"] = [
            {"baslik": m.get("baslik", ""), "url": m.get("url", ""),
             "kaynak": m.get("kaynak", ""), "tarih": m.get("tarih", "")}
            for m in sorted(k, key=_puan, reverse=True)
            if m.get("anahtar") != temsilci.get("anahtar")]
        # kumenin TUM olay izleri temsilcide toplanir: gonderildikten sonra
        # hicbir uye baska bir yoldan geri donemesin
        izler = set(temsilci.get("olaylar") or [])
        for m in k:
            izler |= set(m.get("olaylar") or [])
        temsilci["olaylar"] = sorted(izler)
        temsilci["kume_anahtarlari"] = [m.get("anahtar") for m in k
                                         if m.get("anahtar")]
        out.append(temsilci)
    return out, sum(1 for k in kumeler if len(k) > 1)


def gecmis_tekrari(r, son_basliklar):
    """Ayni firma + hat daha once GONDERILDI mi ve yeni satir daha ileri degil mi?

    True = tekrar (eleyin). Daha ileri asama gercek bir gelismedir.
    """
    from . import classify
    f = firma_kok(r.get("firma"))
    h = _hat(r)
    if not f or not h:
        return False
    yeni = ASAMA_SIRA.get(r.get("asama") or "Belirsiz", 0)
    for b in son_basliklar or []:
        bf = firma_kok(classify.detect_firm(b.get("b", "")))
        if bf != f:
            continue
        if taxonomy.match_line(b.get("b", "")) != h:
            continue
        eski = ASAMA_SIRA.get(b.get("a") or "Belirsiz", 0)
        if yeni <= eski:
            return True
    return False
