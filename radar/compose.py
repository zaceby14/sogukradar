# -*- coding: utf-8 -*-
"""Deterministik Turkce metin uretici.

Mail Pazartesi 07:05'te otomatik gider; o saatte yapay zeka oturumu henuz
calismamis olabilir. Bu modul, YALNIZCA dogrulanmis alanlardan (tarih, firma,
ulke, hat, asama) kurallı Turkce cumleler kurar - ozgur metin uretmez,
dolayisiyla uydurma riski sifirdir. Yapay zeka oturumu daha iyi bir ozet
yazarsa (ozet.json), o metin bununkinin yerine gecer.
"""

STAGE_PHRASE = {
    "Ilk urun": "%s, %s tesisinde ilk uretimi gerceklestirdi",
    "Insaat": "%s, %s insaatina basladi",
    "Test": "%s, %s hattinda test uretimine gecti",
    "Seri uretim": "%s, %s hattinda tam kapasiteye ulasti",
    "Teknoloji": "%s, %s alaninda yeni teknoloji duyurdu",
}


def _top_countries(rows, n=3):
    d = {}
    for r in rows:
        c = r.get("ulke") or ""
        if c:
            d[c] = d.get(c, 0) + 1
    return sorted(d.items(), key=lambda kv: -kv[1])[:n]


def _top(rows, key, n=2):
    d = {}
    for r in rows:
        v = r.get(key) or ""
        if v and v != "Belirsiz":
            d[v] = d.get(v, 0) + 1
    return sorted(d.items(), key=lambda kv: -kv[1])[:n]


def row_sentence(r):
    if r.get("kategori") == "Yatirim":
        return r.get("baslik", "")
    firma = r.get("firma") or r.get("kaynak") or "Ilgili uretici"
    hat = (r.get("hat") or "hat").lower()
    asama = r.get("asama") or "Belirsiz"
    ted = r.get("tedarikci") or ""
    # Ozne tedarikcinin kendisiyse "X isini X'e verdi" denmez (2026-08-12)
    self_award = ted and (ted.lower() in firma.lower() or firma.lower() in ted.lower())
    if asama == "Sozlesme":
        if self_award:
            s = "%s, %s icin yeni bir sozlesme aldi" % (ted, hat)
        elif ted:
            s = "%s, %s yatirimini %s'e siparis etti" % (firma, hat, ted)
        else:
            s = "%s, %s icin siparis verdi" % (firma, hat)
    elif asama == "Modernizasyon":
        if self_award:
            s = "%s, %s yenileme isini ustlendi" % (ted, hat)
        elif ted:
            s = "%s, %s yenileme isini %s'e verdi" % (firma, hat, ted)
        else:
            s = "%s, %s yenileme isini baslatti" % (firma, hat)
    elif asama in STAGE_PHRASE:
        s = STAGE_PHRASE[asama] % (firma, hat)
    else:
        s = "%s: %s" % (firma, r.get("baslik", ""))
    if r.get("tutar"):
        s += " (%s)" % r["tutar"]
    return s + "."


def exec_summary(rows, stats):
    """Kurallı 'AI Ozeti' paragrafi - sadece dogrulanmis alanlardan."""
    n = len(rows)
    if n == 0:
        er = stats.get("erisilemeyen", 0)
        return ("Bu hafta tarih dogrulamasindan gecen gelisme kaydedilmedi. "
                "%d kaynak tarandi, %d kaynaga erisilemedi; sifir sonuc cogu zaman "
                "sektorel durgunluk degil erisim sorunudur, detay kapsam tablosundadir."
                % (stats.get("kaynak", 0), er))
    parts = []
    cs = _top_countries(rows)
    if cs:
        if len(cs) == 1:
            parts.append("Bu haftanin %d dogrulanmis gelismesinin tamami %s kaynakli."
                         % (n, cs[0][0]))
        else:
            lead = cs[0]
            rest = ", ".join(c for c, _ in cs[1:])
            parts.append("Bu hafta %d dogrulanmis gelisme kaydedildi; %s %d gelismeyle "
                         "one cikarken %s takip ediyor." % (n, lead[0], lead[1], rest))
    hl = _top(rows, "hat", 2)
    if hl:
        parts.append("Hat tarafinda agirlik %s." % " ve ".join(h.lower() for h, _ in hl))
    st = _top(rows, "asama", 2)
    if st:
        parts.append("Asama dagiliminda %s onde." %
                     " ve ".join(("%s (%d)" % (a.lower(), k)) for a, k in st))
    tr = [r for r in rows if r.get("ulke") == "Turkiye" or "tosyali" in
          (r.get("firma") or "").lower()]
    if tr:
        parts.append("Turkiye baglantili gelisme: " + row_sentence(tr[0]))
    top = rows[0]
    if not tr or top is not tr[0]:
        parts.append("Haftanin one cikan olayi: " + row_sentence(top))
    return " ".join(parts)


HAT_TR = {
    "Elektrik celigi hatti": "elektrik çeliği (trafo/motor sacı) üretim hatları",
    "Tandem soguk hadde (TCM)": "tandem soğuk haddeleme",
    "Reversing soguk hadde (RCM)": "reversing soğuk haddeleme",
    "Soguk hadde": "soğuk haddeleme",
    "Asitleme hatti": "asitleme hatları",
    "Asit rejenerasyonu (ARP)": "asit geri kazanımı",
    "Surekli tavlama (CAL)": "sürekli tavlama hatları",
    "Kutu tavlama (BAF)": "kutu tavlama fırınları",
    "Galvaniz hatti (CGL)": "sıcak daldırma galvaniz hatları",
    "Zn-Al-Mg / Galvalume kaplama": "gelişmiş çinko-alüminyum kaplamalar",
    "Elektro galvaniz (EGL)": "elektro galvaniz hatları",
    "Teneke hatti (ETL)": "teneke (ambalaj sacı) hatları",
    "Boyama hatti (CCL)": "boyalı sac hatları",
    "Temper / skin pass": "temper haddeleme",
    "Dilme / boy kesme": "dilme ve boy kesme hatları",
    "Roll shop / merdane": "merdane işleme (roll shop)",
    "Yuzey muayene (SIS)": "otomatik yüzey muayene sistemleri",
    "Otomasyon / dijital": "hat otomasyonu ve dijitalleşme",
    "Serit isleme hatti": "şerit işleme hatları",
}


def tech_blurb(t):
    """Otomatik mail icin KISA TURKCE aciklama. Ozgur ceviri yapilmaz;
    hangi alana ait oldugu ve kaynagi soylenir - detayi editor oturumu
    zenginlestirir."""
    hat = HAT_TR.get(t.get("hat") or "", "")
    kaynak = t.get("kaynak", "")
    tarih = t.get("tarih", "")
    if hat:
        return ("%s alanında yeni bir geliştirme duyuruldu (%s, %s). "
                "Ayrıntı kaynak bağlantısında." % (hat.capitalize(), kaynak, tarih))
    return "Yeni teknoloji duyurusu (%s, %s). Ayrıntı kaynak bağlantısında." % (kaynak, tarih)


# ----------------------------------------------------------------------
# AI KONTROLU VE EKLEMELERI (2026-08-17)
#
# Bulten okuyucusuna "bu listenin neresi yazilim, neresi editor" sorusunun
# cevabini verir. Bolum HER ZAMAN cikar: bos hafta da bir bilgidir - editor
# baktiysa ve duzeltilecek bir sey bulmadiysa okuyucu bunu bilmelidir.
# ----------------------------------------------------------------------
AI_BOLUM_BOS = "Bu hafta yazılım çıktısında düzeltilecek bir şey bulunmadı."

AI_GRUPLAR = [
    ("ai_eklenen", "Yazılımın kaçırdığı, elle eklenen"),
    ("ai_duzeltme", "Düzeltilen satırlar"),
    ("ai_cikarilan", "Listeden çıkarılanlar"),
    ("ai_kontrol", "Çapraz kontrol"),
]


def _ai_satir(x):
    """Bir AI bolumu maddesini tek satirlik metne indirir.

    Sozluk de duz metin de kabul edilir - editorun ozet.json'da her alan
    icin ayni sekli kullanmak zorunda kalmamasi icin.
    """
    if not isinstance(x, dict):
        return str(x or "").strip()
    baslik = (x.get("baslik") or x.get("konu") or "").strip()
    kaynak = (x.get("kaynak") or "").strip()
    neden = (x.get("neden") or x.get("sebep") or x.get("aciklama") or "").strip()
    parcalar = [p for p in (baslik, ("(%s)" % kaynak) if kaynak else "") if p]
    metin = " ".join(parcalar)
    if neden:
        metin = ("%s — %s" % (metin, neden)) if metin else neden
    return metin.strip()


def ai_bolumu(ozet):
    """[(baslik, [satir, ...]), ...] - bos gruplar atilir.

    Hicbir grup dolu degilse [] doner; render bunu gorunce AI_BOLUM_BOS
    metnini basar. Bolumun KENDISI her durumda render edilir.
    """
    ozet = ozet or {}
    out = []
    for anahtar, baslik in AI_GRUPLAR:
        ham = ozet.get(anahtar) or []
        if isinstance(ham, (str, dict)):
            ham = [ham]
        satirlar = [s for s in (_ai_satir(x) for x in ham) if s]
        if satirlar:
            out.append((baslik, satirlar))
    return out
