# -*- coding: utf-8 -*-
"""Deterministik Turkce metin uretici.

Mail Pazartesi 07:05'te otomatik gider; o saatte yapay zeka oturumu henuz
calismamis olabilir. Bu modul, YALNIZCA dogrulanmis alanlardan (tarih, firma,
ulke, hat, asama) kurallı Turkce cumleler kurar - ozgur metin uretmez,
dolayisiyla uydurma riski sifirdir. Yapay zeka oturumu daha iyi bir ozet
yazarsa (ozet.json), o metin bununkinin yerine gecer.
"""

STAGE_PHRASE = {
    "Ilk urun": "%s, %s alanında ilk üretimi gerçekleştirdi",
    "Seri uretim": "%s, %s hattında tam kapasiteye ulaştı",
    "Insaat": "%s, %s yatırımında inşaata başladı",
    "Test": "%s, %s hattında test üretimine geçti",
    "Teknoloji": "%s, %s alanında yeni teknoloji duyurdu",
}

# Ekrana ASCII etiketle gelen ulke adlari: okuyucu 'Turkiye' degil 'Türkiye' gorur.
ULKE_GOSTER = {
    "Turkiye": "Türkiye", "Cin": "Çin", "Almanya": "Almanya", "Italya": "İtalya",
    "Ispanya": "İspanya", "Misir": "Mısır", "Belcika": "Belçika", "Avusturya": "Avusturya",
    "Isvec": "İsveç", "Isvicre": "İsviçre", "Cezayir": "Cezayir", "Fas": "Fas",
    "Romanya": "Romanya", "Slovakya": "Slovakya", "Hindistan": "Hindistan",
    "Endonezya": "Endonezya", "Filipinler": "Filipinler", "Banglades": "Bangladeş",
    "Umman": "Umman", "BAE": "BAE", "Katar": "Katar", "S. Arabistan": "S. Arabistan",
    "Ozbekistan": "Özbekistan", "Kazakistan": "Kazakistan", "Rusya": "Rusya",
    "Ukrayna": "Ukrayna", "Polonya": "Polonya", "Fransa": "Fransa",
    "Portekiz": "Portekiz", "G. Afrika": "G. Afrika", "Nijerya": "Nijerya",
    "Etiyopya": "Etiyopya", "Tanzanya": "Tanzanya", "Gana": "Gana",
}


def ulke_goster(u):
    return ULKE_GOSTER.get(u or "", u or "")


ASAMA_TR = {"Sozlesme": "sözleşme", "Insaat": "inşaat", "Ilk urun": "ilk ürün",
            "Seri uretim": "seri üretim", "Modernizasyon": "modernizasyon"}


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


def _hat_tr(r):
    """Hat adinin okunabilir Turkce karsiligi; yoksa hat adi kucuk harfle."""
    h = r.get("hat") or ""
    if not h or h == "Belirsiz":
        return "işleme hattı"
    return HAT_TR.get(h, h.lower())


def row_sentence(r):
    """KURALSAL satir cumlesi - yalniz dogrulanmis alanlardan.

    EK KULLANMAZ. Dinamik ozel isimlere (firma, tedarikci) Turkce hal eki
    (-e/-a, -nin/-nun) dogru takilamaz: 'POSCO'ya' mi 'POSCO'e' mi,
    'Danieli'ye' mi, hepsi ünlü uyumuna bagli. Kural yanlis ek uretmektense
    ekten kacinir: 'tedarikçi: X' kalibi hep dogrudur.
    """
    if r.get("kategori") == "Yatirim":
        # Yatirim satiri yalniz baslikla gelir; Turkce cumle LLM'e ya da
        # editore birakilir. Kuralsal yolda baslik oldugu gibi gosterilir
        # (ceviri uydurulmaz).
        return r.get("baslik", "")
    firma = r.get("firma") or r.get("kaynak") or "İlgili üretici"
    hat = _hat_tr(r)
    asama = r.get("asama") or "Belirsiz"
    ted = r.get("tedarikci") or ""
    # Ozne tedarikcinin kendisiyse "X isini X'e verdi" denmez (2026-08-12)
    self_award = ted and (ted.lower() in firma.lower() or firma.lower() in ted.lower())
    if asama == "Sozlesme":
        if self_award:
            s = "%s, %s için yeni bir sözleşme aldı" % (ted, hat)
        elif ted:
            s = "%s, %s için sipariş verdi (tedarikçi: %s)" % (firma, hat, ted)
        else:
            s = "%s, %s için sipariş verdi" % (firma, hat)
    elif asama == "Modernizasyon":
        if self_award:
            s = "%s, %s yenileme işini üstlendi" % (ted, hat)
        elif ted:
            s = "%s, %s yenileme projesine başladı (tedarikçi: %s)" % (firma, hat, ted)
        else:
            s = "%s, %s yenileme projesine başladı" % (firma, hat)
    elif asama in STAGE_PHRASE:
        s = STAGE_PHRASE[asama] % (firma, hat)
    else:
        # Asama okunamadi: iddia kurulmaz, yalniz konu ve kaynak soylenir.
        s = "%s: %s ile ilgili gelişme" % (firma, hat)
    if r.get("tutar"):
        s += " (%s)" % r["tutar"]
    return s + "."


def exec_summary(rows, stats):
    """Kurallı 'AI Özeti' paragrafı - sadece doğrulanmış alanlardan."""
    n = len(rows)
    if n == 0:
        er = stats.get("erisilemeyen", 0)
        return ("Bu hafta tarih doğrulamasından geçen gelişme kaydedilmedi. "
                "%d kaynak tarandı, %d kaynağa erişilemedi; sıfır sonuç çoğu zaman "
                "sektörel durgunluk değil erişim sorunudur, ayrıntı kapsam tablosundadır."
                % (stats.get("kaynak", 0), er))
    parts = []
    cs = _top_countries(rows)
    bilinen = sum(k for _, k in cs)
    if not cs:
        parts.append("Bu hafta %d doğrulanmış gelişme kaydedildi." % n)
    elif len(cs) == 1 and cs[0][1] == n:
        parts.append("Bu haftanın %d doğrulanmış gelişmesinin tamamı %s kaynaklı."
                     % (n, ulke_goster(cs[0][0])))
    elif len(cs) == 1:
        # Ulkesi okunamayan satirlar var: 'tamami' DENEMEZ (haberin ulkesi
        # bilinmiyorsa onu o ulkeye yazmak uydurmadir).
        parts.append("Bu hafta %d doğrulanmış gelişme kaydedildi; ülkesi belirlenenlerin "
                     "%d'i %s kaynaklı." % (n, cs[0][1], ulke_goster(cs[0][0])))
    else:
        lead = cs[0]
        rest = ", ".join(ulke_goster(c) for c, _ in cs[1:])
        parts.append("Bu hafta %d doğrulanmış gelişme kaydedildi; ülkesi belirlenenler "
                     "arasında %s %d gelişmeyle öne çıkarken %s takip ediyor."
                     % (n, ulke_goster(lead[0]), lead[1], rest))
    hl = _top(rows, "hat", 2)
    if hl:
        parts.append("Hat tarafında ağırlık %s." %
                     " ve ".join(HAT_TR.get(h, h.lower()) for h, _ in hl))
    st = _top(rows, "asama", 2)
    if st:
        parts.append("Aşama dağılımında %s önde." %
                     " ve ".join(("%s (%d)" % (ASAMA_TR.get(a, a.lower()), k)) for a, k in st))
    tr = [r for r in rows if r.get("ulke") == "Turkiye" or "tosyali" in
          (r.get("firma") or "").lower()]
    if tr:
        parts.append("Türkiye bağlantılı gelişme: " + row_sentence(tr[0]))
    top = rows[0]
    if not tr or top is not tr[0]:
        parts.append("Haftanın öne çıkan olayı: " + row_sentence(top))
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
    "Bobin tasima / paketleme": "bobin taşıma ve paketleme sistemleri",
    "Dilme / boy kesme / SSC": "dilme, boy kesme ve servis merkezi hatları",
    "Olcum / kalite kontrol": "ölçüm ve kalite kontrol sistemleri",
    "Serit birlestirme (kaynak)": "şerit birleştirme (kaynak) sistemleri",
    "Temizleme hatti (ECL)": "elektrolitik temizleme hatları",
    "Yuzey islem / pasivasyon": "yüzey işlem ve pasivasyon hatları",
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
