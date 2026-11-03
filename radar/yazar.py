# -*- coding: utf-8 -*-
"""OTOMATIK EDITOR - Claude Code rutinine bagli kalmadan bulten metnini yazar.

KULLANICI TALEBI (2026-11-02): "claude proya bagli kalmadan halledebilmeni
istiyorum". Editor rutini 21 Eylul'den beri atesllemiyor; bulten 5 haftadir
gitmedi. Bu modul editorun isini Actions icinde yapar.

TASARIM - IKI KATMAN, SISTEM LLM'E BAGLI DEGIL:

  1) KURALSAL YOL (her zaman calisir): compose.py'nin dogrulanmis alanlardan
     kurdugu Turkce cumleler. Ozgur metin uretmez, uydurma riski SIFIR. LLM
     yoksa, anahtar bitmisse, kota dolmussa ya da yanit bozuksa bulten yine
     cikar.
  2) LLM YOLU (varsa): ayni satirlar icin daha dogal Turkce cumle ve ozet.
     Yalnizca IYILESTIRIR; her cumle asagidaki dogrulayicidan gecmezse o
     cumle atilir ve kuralsal cumle kullanilir.

UYDURMA DOGRULAYICISI. Degismez kural: "Haber/tarih/detay UYDURMA." LLM bu
kurali kendi basina GARANTI EDEMEZ; bu yuzden her cumle sunlarla denetlenir:
  - cumledeki her SAYI, kaynak metinde (baslik + lead + kume uyelerinin
    basliklari + alanlar) gecmek zorunda;
  - cumledeki her OZEL AD (buyuk harfle baslayan, cumle basinda olmayan
    sozcuk) kaynakta ya da bilinen Turkce ulke/bolge adlari arasinda olmak
    zorunda;
  - "ilk uretim / devreye aldi / uretime basladi" iddiasi YALNIZ sistemin
    asama alani Ilk urun/Seri uretim ise kurulabilir - bultenin en pahali
    iddiasi, karari LLM'e birakilmaz;
  - cumle Turkce olmak zorunda (Ingilizce yanit reddedilir);
  - uzunluk siniri.
LLM ayrica kapsam disi satirlari ISARETLEYEBILIR; isaretlenen satir yalnizca
CIKARILIR (asla eklenmez), cikarilan her satir bultende gerekcesiyle gorunur
ve toplu silmeye karsi ust sinir vardir.
"""
import json
import os
import re

from . import compose, llm, taxonomy

CUMLE_MIN, CUMLE_MAX = 25, 420
EXEC_MAX = 900
KALDIRMA_USTSINIR = 0.4          # satirlarin en fazla %40'i LLM ile cikarilabilir

# LLM'in Turkceye cevirirken kullanabilecegi, kaynakta AYNEN gecmeyen adlar.
_TR_AD = set()
for _a in ("Türkiye Çin Hindistan Japonya Kore Güney Kuzey Doğu Batı Orta Birleşik "
           "Devletleri Krallık Arap Emirlikleri Suudi Arabistan Katar Umman Kuveyt "
           "Bahreyn İran Irak Mısır Cezayir Fas Tunus Libya Nijerya Gana Kenya "
           "Uganda Tanzanya Etiyopya Afrika Amerika Avrupa Asya Kanada Meksika "
           "Brezilya Arjantin Şili Kolombiya Peru Almanya Fransa İtalya İspanya "
           "Portekiz Polonya Romanya Bulgaristan Yunanistan Sırbistan Macaristan "
           "Çekya Slovakya Avusturya İsviçre Belçika Hollanda Lüksemburg İsveç "
           "Finlandiya Norveç Danimarka İngiltere Rusya Ukrayna Kazakistan "
           "Özbekistan Tayvan Vietnam Tayland Malezya Endonezya Filipinler "
           "Pakistan Bangladeş Avustralya ABD BAE AB Ocak Şubat Mart Nisan Mayıs "
           "Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık Pazartesi").split():
    _TR_AD.add(taxonomy.fold(_a))
for _v in compose.ULKE_GOSTER.values():
    for _p in _v.replace(".", " ").split():
        _TR_AD.add(taxonomy.fold(_p))

_ULKE_ES = {taxonomy.fold(k): v for k, v in {
    "Türkiye": ["turkiye", "turkey", "turkish", "turk"], "Türk": ["turkiye", "turkey", "turkish", "turk"],
    "Çin": ["cin", "china", "chinese"], "Hindistan": ["hindistan", "india", "indian"],
    "Japonya": ["japonya", "japan", "japanese"], "Kore": ["kore", "korea", "korean"],
    "ABD": ["abd", "us", "u\\.s", "usa", "united states", "america", "american"],
    "AB": ["ab", "eu", "european union", "europe"], "Birliği": ["eu", "european union", "birligi", "union"], "Avrupa": ["avrupa", "europe", "european", "eu"],
    "Almanya": ["almanya", "germany", "german"], "İtalya": ["italya", "italy", "italian"],
    "Fransa": ["fransa", "france", "french"], "İspanya": ["ispanya", "spain", "spanish"],
    "Rusya": ["rusya", "russia", "russian"], "Ukrayna": ["ukrayna", "ukraine", "ukrainian"],
    "Vietnam": ["vietnam", "vietnamese"], "Tayvan": ["tayvan", "taiwan"],
    "Mısır": ["misir", "egypt", "egyptian"], "Brezilya": ["brezilya", "brazil"],
    "Meksika": ["meksika", "mexico"], "Kanada": ["kanada", "canada", "canadian"],
    "Pakistan": ["pakistan"], "Endonezya": ["endonezya", "indonesia"],
    "Polonya": ["polonya", "poland", "polish"], "Romanya": ["romanya", "romania"],
    "Slovakya": ["slovakya", "slovakia"], "İran": ["iran"], "Kazakistan": ["kazakistan", "kazakhstan"],
    "Avustralya": ["avustralya", "australia"], "Suudi": ["suudi", "saudi"],
    "Portekiz": ["portekiz", "portugal"], "Belçika": ["belcika", "belgium"],
    "Hollanda": ["hollanda", "netherlands", "dutch"], "İngiltere": ["ingiltere", "uk", "britain", "england"],
}.items()}

_ING = {"the", "and", "for", "with", "has", "have", "will", "from", "this",
        "that", "its", "are", "was", "were", "into", "plans", "said"}
_URETIM_IDDIASI = re.compile(
    r"ilk üretim|üretime başla|üretimi başlat|üretime geçti|devreye al|"
    r"devreye girdi|faaliyete geç|ilk bobin|ilk rulo", re.I)


# ----------------------------------------------------------------------
# DOGRULAYICI
# ----------------------------------------------------------------------
def _rakamlar(metin):
    """Metindeki sayilari ayirici-siz haliyle dondurur: '1.300' / '2,67' -> '1300' / '267'."""
    return {re.sub(r"[.,]", "", m) for m in re.findall(r"\d[\d.,]*\d|\d", metin or "")}


def kaynak_metni(r):
    """Bir satir icin DOGRULAMA kaynagi: hicbir sey uydurulmaz, yalniz bunlar."""
    parca = [r.get("baslik", ""), r.get("lead", ""), r.get("firma", ""),
             r.get("ulke", ""), compose.ulke_goster(r.get("ulke")),
             r.get("tedarikci", ""), r.get("tutar", ""), r.get("kapasite", ""),
             r.get("hat", ""), compose._hat_tr(r), r.get("kaynak", ""),
             r.get("asama", "")]
    for i in r.get("ilgili") or []:
        parca.append(i.get("baslik", ""))
    return " ".join(p for p in parca if p)


def cumle_dogrula(cumle, kaynak, asama=None):
    """(gecerli_mi, neden). Kaynaga SADIK olmayan cumle reddedilir."""
    c = (cumle or "").strip()
    if not (CUMLE_MIN <= len(c) <= CUMLE_MAX):
        return False, "uzunluk (%d)" % len(c)
    kay_fold = taxonomy.fold(kaynak)
    # 1) sayilar
    izinli = _rakamlar(kaynak)
    for n in _rakamlar(c):
        if n not in izinli:
            return False, "kaynakta olmayan sayi: %s" % n
    # 2) ozel adlar
    kelimeler = re.findall(r"[^\s]+", c)
    for i, w in enumerate(kelimeler):
        kok = re.split(r"['’]", w)[0].strip(".,;:()[]\"“”!?-–—")
        if len(kok) < 3 or not kok[0].isupper():
            continue
        if i == 0:                                        # cumle basi buyuk harf olabilir
            continue
        # onceki sozcuk cumleyi bitiriyorsa bu da cumle basidir
        if i > 0 and kelimeler[i - 1].endswith((".", "!", "?")):
            continue
        f = taxonomy.fold(kok)
        # ULKE ADI KAYNAKTA GECMELI (2026-11-03): Turkce ulke adi listesi
        # (_TR_AD) ulkeyi kaynaga bakmadan kabul ediyordu; model kaynakta
        # olmayan "Turkiye"yi ekleseydi yakalanmazdi. Ulke adi icin kaynakta
        # Ingilizce ya da Turkce karsiligi aranir.
        if f in _ULKE_ES:
            if any(re.search(r"\b" + v + r"\b", kay_fold) for v in _ULKE_ES[f]):
                continue
            return False, "kaynakta olmayan ulke: %s" % kok
        if f in kay_fold or f in _TR_AD:
            continue
        # kaynaktaki bir sozcugun TURKCE EKLI hali ('POSCO'nun', 'Danieli'ye')
        if any(f == taxonomy.fold(re.sub(r"[^\w]", "", k)) for k in kaynak.split()):
            continue
        return False, "kaynakta olmayan ozel ad: %s" % kok
    # 3) Ingilizce yanit
    low = {w.lower().strip(".,;:()") for w in kelimeler}
    if len(low & _ING) >= 3:
        return False, "Ingilizce"
    # 4) uretim iddiasi: karari sistemin asama alani verir
    if _URETIM_IDDIASI.search(c) and asama not in ("Ilk urun", "Seri uretim"):
        return False, "asama %s iken uretim iddiasi" % (asama or "Belirsiz")
    return True, ""


# ----------------------------------------------------------------------
# PROMPT
# ----------------------------------------------------------------------
SISTEM = """Sen bir çelik sektörü bülten editörüsün. Okuyucu: Türkiye'de bir soğuk haddehane yöneticisi.

KAPSAM: yalnızca SICAK HADDELEME SONRASI yassı çelik işleme hatları — asitleme, soğuk haddeleme, temper, tavlama, galvaniz/kaplama, boyama, teneke, dilme/boy kesme, merdane atölyesi, yüzey muayene, hat otomasyonu, elektrik çeliği.
KAPSAM DIŞI: sıcak haddeleme, yüksek fırın, DRI/EAF, döküm, uzun ürün (çubuk, filmaşin, profil, ray), boru, demir dışı metaller; fiyat, borsa, ihracat/ithalat, ticaret davası, bilanço, atama, fuar; şirket satın alma/birleşme; girişim yatırım turu.

GÖREVİN, verilen her haber için 1-2 cümlelik doğal Türkçe özet yazmak.

KESİN KURALLAR (ihlal edilen cümle otomatik reddedilir ve yerine kuralsal cümle konur):
1. YALNIZCA verilen başlık, özet metin ve alanlardaki bilgiyi kullan. Metinde olmayan sayı, tarih, ad, ülke, kapasite, tutar ASLA ekleme. Emin değilsen o bilgiyi yazma.
2. "İlk üretim / devreye aldı / üretime başladı" ifadesini YALNIZCA haberin 'asama' alanı "Ilk urun" veya "Seri uretim" ise kullan. 'Sozlesme', 'Insaat', 'Modernizasyon', 'Belirsiz' ise bunlar niyet/sözleşme/yapım aşamasıdır: "yatırım yapacak", "sipariş verdi", "temel attı", "yenileme projesine başladı" gibi yaz.
3. Özel adları (firma, tedarikçi) kaynakta yazıldığı gibi koru; Türkçe ek alacaksa kesme işaretiyle ayır.
4. Tarih yazma (tarih ayrı bir sütunda). Yorum, tahmin, pazarlama dili ekleme.
5. Haberin birden çok kaynağı varsa ('ilgili_basliklar') bunları tek olay olarak, kaynaklardaki bilgileri birleştirerek anlat.
7. PİYASA GÜNDEMİ: 'piyasa_adaylari' listesinden, Türkiye'deki bir soğuk haddehane yöneticisi için EN ÖNEMLİ en fazla 3 tanesini seç (önem sırasıyla): Türkiye/AB'yi doğrudan etkileyen ticaret önlemleri, soğuk taraf ürün fiyat/talep değişimleri, kapasite/arz şokları. Aynı konuyu iki kez seçme. Yalnızca listedeki id'leri kullan; özet yalnız başlık ve özet metindeki bilgiye dayansın.
8. Okuyucu geri bildirimi verildiyse ('tercih_ozeti') seçim ve vurguda dikkate al.
6. Bir haber kapsam dışıysa cümle yazma, 'supheli' listesine gerekçesiyle ekle. SADECE açıkça kapsam dışı olanı işaretle; emin değilsen işaretleme.

ÇIKTI: yalnızca şu JSON nesnesi, başka hiçbir şey:
{"cumleler": {"<id>": "Türkçe cümle"}, "ozet": "Haftanın 2-4 cümlelik Türkçe özeti (yalnızca verilen haberlerden)", "supheli": [{"id": "<id>", "neden": "kısa gerekçe"}], "piyasa": [{"id": "<piyasa id>", "cumle": "1-2 cümlelik Türkçe özet"}], "teknoloji_id": "teknoloji adaylarından GERÇEK YENİLİK olanın id'si ya da boş", "teknoloji": "seçilen yenilik için 1-2 cümlelik Türkçe tanıtım (yalnızca başlık ve özet metindeki bilgiyle); seçim yoksa boş"}

9. TEKNOLOJİ KÖŞESİ: adaylardan YALNIZCA gerçek bir yenilik olanı seç: ilk uygulama, yeni proses/yöntem/kalite/kaplama, Ar-Ge, pilot tesis, patent, hidrojen/yapay zekâ ile yeni yaklaşım. Mevcut ürünün tanıtımı, ürün yelpazesi genişletme, tedarik/sipariş haberi YENİLİK DEĞİLDİR - böyleyse teknoloji_id boş bırak. Emin değilsen boş bırak."""


def _kullanici(rows, stats, tech=None, piyasa_ad=None, tercih_ozeti=""):
    liste = []
    for r in rows:
        liste.append({
            "id": r["anahtar"], "baslik": r.get("baslik", ""),
            "ozet_metin": (r.get("lead") or "")[:420],
            "ilgili_basliklar": [i["baslik"] for i in (r.get("ilgili") or [])][:5],
            "kaynak": r.get("kaynak", ""), "firma": r.get("firma", ""),
            "ulke": compose.ulke_goster(r.get("ulke")), "tedarikci": r.get("tedarikci", ""),
            "hat": compose._hat_tr(r), "asama": r.get("asama", ""),
            "tutar": r.get("tutar", ""), "kapasite": r.get("kapasite", ""),
            "katman": r.get("kategori", "")})
    metin = ("Bu haftanın haberleri (%d adet):\n%s" %
             (len(liste), json.dumps(liste, ensure_ascii=False, indent=1)))
    if piyasa_ad:
        metin += "\n\npiyasa_adaylari:\n" + json.dumps(
            [{"id": m["anahtar"], "baslik": m.get("baslik", ""), "ozet_metin": (m.get("lead") or "")[:300],
              "kaynak": m.get("kaynak", ""), "tarih": m.get("tarih", ""), "konu": m.get("konu", ""),
              "on_puan": m.get("puan")} for m in piyasa_ad], ensure_ascii=False, indent=1)
    if tercih_ozeti:
        metin += "\n\ntercih_ozeti: " + tercih_ozeti
    if tech:
        metin += ("\n\nteknoloji_adaylari:\n" + json.dumps(
            [{"id": t.get("anahtar"), "baslik": t.get("baslik", ""),
              "ozet_metin": (t.get("lead") or "")[:420], "kaynak": t.get("kaynak", "")}
             for t in tech], ensure_ascii=False, indent=1))
    return metin


# ----------------------------------------------------------------------
# ANA AKIS
# ----------------------------------------------------------------------
PIYASA_N = 3


def _piyasa_maddesi(m, metin):
    return {"anahtar": m["anahtar"], "tarih": m.get("tarih", ""), "baslik": m.get("baslik", ""),
            "metin": metin, "url": m.get("url", ""), "kaynak": m.get("kaynak", ""),
            "konu": m.get("konu", ""), "urun": m.get("urun", "")}


def ozet_hazirla(payload, log=print):
    """ozet.json uyumlu sozluk dondurur. LLM yoksa ya da basarisizsa kuralsal."""
    rows = payload["rows"]
    stats = payload["stats"]
    rapor = {"saglayici": None, "llm_hatalar": [], "reddedilen_cumle": [],
             "cumle_llm": 0, "cumle_kuralsal": 0, "supheli_cikarilan": 0}

    ozet = {"exec": compose.exec_summary(rows, stats), "cumleler": {},
            "teknolojiler": [], "cikar": [], "ai_cikarilan": [],
            "ai_duzeltme": [], "ai_kontrol": []}
    for r in rows:
        ozet["cumleler"][r["anahtar"]] = compose.row_sentence(r)
        rapor["cumle_kuralsal"] += 1

    tech_ad = (payload.get("tech_pool") or [])[:8]
    # LLM yoksa (ya da cevap vermezse) kose YALNIZ yenilik isaretli adayla dolar.
    tech = [t for t in tech_ad if t.get("yenilik", True)][:1]
    for t in tech:
        ozet["teknolojiler"].append({
            "anahtar": t.get("anahtar", ""), "tarih": t.get("tarih", ""),
            "konu": t.get("baslik", ""), "metin": compose.tech_blurb(t),
            "url": t.get("url", "")})

    piyasa_ad = payload.get("piyasa_adaylari") or []
    ozet["piyasa"] = [_piyasa_maddesi(m, m.get("baslik", "")) for m in piyasa_ad[:PIYASA_N]]

    if not rows or not llm.saglayicilar():
        if rows:
            ozet["ai_kontrol"].append(
                "Metinler kurallı yolla üretildi (dil modeli kimlik bilgisi tanımlı değil); "
                "yalnızca doğrulanmış alanlardan kurulan cümleler kullanıldı.")
        ozet["_rapor"] = rapor
        return ozet

    veri, saglayici, hatalar = llm.json_iste(
        SISTEM, _kullanici(rows, stats, tech_ad, piyasa_ad,
                           payload.get("tercih_ozeti", "")), log=log)
    rapor["llm_hatalar"] = hatalar
    if not veri:
        # Ham hata metni bultene GIRMEZ (okuyucu icin anlamsiz); ayrinti
        # karar.json'daki _rapor.llm_hatalar'dadir.
        ozet["ai_kontrol"].append(
            "Dil modeli bu hafta yanıt vermedi; metinler yalnızca doğrulanmış "
            "alanlardan kurallı yolla üretildi.")
        ozet["_rapor"] = rapor
        return ozet

    rapor["saglayici"] = saglayici
    by_id = {r["anahtar"]: r for r in rows}

    # --- cumleler: yalnizca DOGRULANANLAR kuralsal cumlenin yerine gecer
    for rid, cum in (veri.get("cumleler") or {}).items():
        r = by_id.get(rid)
        if not r or not isinstance(cum, str):
            continue
        ok, neden = cumle_dogrula(cum, kaynak_metni(r), r.get("asama"))
        if ok:
            ozet["cumleler"][rid] = cum.strip()
            rapor["cumle_llm"] += 1
            rapor["cumle_kuralsal"] -= 1
        else:
            rapor["reddedilen_cumle"].append(
                {"baslik": r.get("baslik", "")[:80], "neden": neden})
            log("    cumle reddedildi (%s): %s" % (neden, r.get("baslik", "")[:50]))

    # --- piyasa gundemi: LLM SECER (yalniz verilen id'ler), ozet dogrulanir
    secim = [x for x in (veri.get("piyasa") or []) if isinstance(x, dict)]
    by_p = {m["anahtar"]: m for m in piyasa_ad}
    yeni = []
    for x in secim:
        m = by_p.get(x.get("id"))
        if not m or any(y["anahtar"] == m["anahtar"] for y in yeni):
            continue
        cum = x.get("cumle") if isinstance(x.get("cumle"), str) else ""
        kay = " ".join([m.get("baslik", ""), m.get("lead", ""), m.get("kaynak", "")])
        ok, neden = cumle_dogrula(cum, kay) if cum else (False, "bos")
        if not ok and cum:
            rapor["reddedilen_cumle"].append({"baslik": "(piyasa) " + m.get("baslik", "")[:60], "neden": neden})
        yeni.append(_piyasa_maddesi(m, cum.strip() if ok else m.get("baslik", "")))
        if len(yeni) >= PIYASA_N:
            break
    if yeni:
        ozet["piyasa"] = yeni

    # --- teknoloji kosesi: LLM adaylardan GERCEK yeniligi secer ya da HICBIRINI.
    # LLM yanit verdiyse karari ona aittir: bos secim = kose bos (tanitim
    # haberi koseye girmez). Metin kaynaga karsi dogrulanir.
    if tech_ad:
        tid = veri.get("teknoloji_id")
        secilen = next((t for t in tech_ad if tid and t.get("anahtar") == tid), None)
        ozet["teknolojiler"] = []
        if secilen:
            tk = veri.get("teknoloji") if isinstance(veri.get("teknoloji"), str) else ""
            kay = " ".join([secilen.get("baslik", ""), secilen.get("lead", ""), secilen.get("kaynak", "")])
            ok, neden = cumle_dogrula(tk, kay) if tk.strip() else (False, "bos")
            if not ok and tk.strip():
                rapor["reddedilen_cumle"].append({"baslik": "(teknoloji kosesi)", "neden": neden})
            ozet["teknolojiler"].append({
                "anahtar": secilen.get("anahtar", ""), "tarih": secilen.get("tarih", ""),
                "konu": secilen.get("baslik", ""), "url": secilen.get("url", ""),
                "metin": tk.strip() if ok else compose.tech_blurb(secilen)})

    # --- ozet
    ex = veri.get("ozet")
    if isinstance(ex, str):
        butun_kaynak = " ".join(kaynak_metni(r) for r in rows)
        # sayi izni: kaynaktakiler + satir sayisi
        # Ozet butun satirlari anlatir: listede ilk urun/seri uretim satiri VARSA
        # uretim iddiasi kurulabilir (2026-11-03: BlueScope ilk bobin haberi varken
        # ozet "asama Belirsiz" sayilip reddedildi).
        en_ileri = next((r.get("asama") for r in rows
                         if r.get("asama") in ("Ilk urun", "Seri uretim")), None)
        ok, neden = cumle_dogrula(ex, butun_kaynak + " %d" % len(rows), en_ileri)
        if ok and len(ex) <= EXEC_MAX:
            ozet["exec"] = ex.strip()
        else:
            rapor["reddedilen_cumle"].append({"baslik": "(haftalik ozet)",
                                              "neden": neden or "uzunluk"})

    # --- supheli satirlar: yalniz CIKARILIR, ust sinir var
    supheli = [x for x in (veri.get("supheli") or []) if isinstance(x, dict)
               and x.get("id") in by_id]
    if supheli:
        if len(supheli) > max(1, int(len(rows) * KALDIRMA_USTSINIR)):
            ozet["ai_kontrol"].append(
                "Dil modeli %d satırı kapsam dışı işaretledi; bu, güvenlik üst sınırını "
                "(%%%d) aştığı için HİÇBİRİ çıkarılmadı." % (len(supheli),
                                                             int(KALDIRMA_USTSINIR * 100)))
        else:
            for x in supheli:
                r = by_id[x["id"]]
                ozet["cikar"].append(r["anahtar"])
                ozet["ai_cikarilan"].append(
                    {"baslik": r.get("baslik", ""),
                     "neden": "Dil modeli kapsam dışı buldu: %s" %
                              str(x.get("neden") or "gerekçe verilmedi")[:160]})
                rapor["supheli_cikarilan"] += 1

    ozet["ai_kontrol"].append(
        "Metinler dil modeliyle (%s) yazıldı; her cümle kaynak metne karşı doğrulandı: "
        "%d cümle kabul, %d cümle reddedilip kuralsal cümleyle değiştirildi."
        % (saglayici, rapor["cumle_llm"], len(rapor["reddedilen_cumle"])))
    ozet["_rapor"] = rapor
    return ozet
