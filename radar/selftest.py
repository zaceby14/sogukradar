# -*- coding: utf-8 -*-
"""Agsiz birim testleri.

Her test, gecmiste GERCEKTEN yasanmis bir hatanin tekrarini engeller.
GitHub Actions her kosudan ONCE bunu calistirir; kirmizi ise haftalik
kosu hic baslamaz - bozuk mantikla rapor uretmektense rapor uretmemek yegdir.
"""
import os
import datetime as dt

from . import classify, dates, feeds, htmlx, state, taxonomy

TODAY = dt.date(2026, 8, 11)
FAILS = []


def eq(got, want, msg):
    if got != want:
        FAILS.append("%s\n     beklenen: %r\n     gelen   : %r" % (msg, want, got))


def test_dates():
    eq(dates.parse_date_text("2026-08-09", today=TODAY), "2026-08-09", "ISO")
    eq(dates.parse_date_text("Mon, 09 Aug 2026 10:00:00 +0000", today=TODAY),
       "2026-08-09", "RFC822")
    eq(dates.parse_date_text("9 August 2026", today=TODAY), "2026-08-09", "gun ay yil")
    eq(dates.parse_date_text("August 9, 2026", today=TODAY), "2026-08-09", "ay gun yil")
    eq(dates.parse_date_text("Aug. 9, 2026", today=TODAY), "2026-08-09", "kisa ay")
    eq(dates.parse_date_text("09.08.2026", today=TODAY), "2026-08-09", "AB noktali")
    eq(dates.parse_date_text("08/09/2026", dayfirst=False, today=TODAY),
       "2026-08-09", "ABD slash")
    eq(dates.parse_date_text("25/07/2026", today=TODAY), "2026-07-25", "gun>12 kesin")
    eq(dates.parse_date_text("9 Ağustos 2026", today=TODAY), "2026-08-09", "turkce ay")
    eq(dates.parse_date_text("3 days ago", today=TODAY), "2026-08-08", "goreli")
    # UYDURMAMA testleri
    eq(dates.parse_date_text("no date here", today=TODAY), None, "tarihsiz metin")
    eq(dates.parse_date_text("2031-01-01", today=TODAY), None, "gelecek tarih reddi")
    eq(dates.parse_date_text("1998-01-01", today=TODAY), None, "cok eski reddi")
    eq(dates.date_from_url("https://x.com/2026/08/09/haber", TODAY), "2026-08-09", "url")
    eq(dates.date_from_url("https://x.com/haber-listesi", TODAY), None, "url tarihsiz")
    eq(dates.month_from_url("https://x.com/2026/08/"), None, "yil-ay ayin 1'i degil")


def test_article_date_chain():
    page = """<html><head>
      <meta property="article:published_time" content="2026-07-14T08:30:00Z">
      <script type="application/ld+json">{"@type":"NewsArticle",
        "datePublished":"2026-07-13T06:00:00+02:00"}</script>
      </head><body><time datetime="2026-07-12">12 July</time><p>metin</p></body></html>"""
    doc = htmlx.parse_article(page)
    iso, src = dates.extract_article_date(doc, "https://x/y", today=TODAY)
    eq(iso, "2026-07-13", "zincir: JSON-LD meta'dan once gelmeli")
    eq(src, "json-ld", "tarih kaynagi etiketi")

    page2 = "<html><body><p>Published 5 June 2026 by us</p></body></html>"
    iso2, src2 = dates.extract_article_date(htmlx.parse_article(page2),
                                            "https://x/y", today=TODAY)
    eq(iso2, "2026-06-05", "zincir: metin")
    iso3, src3 = dates.extract_article_date(
        htmlx.parse_article("<html><body>hicbir tarih yok</body></html>"),
        "https://x/haber", today=TODAY)
    eq(iso3, None, "tarih yoksa None (haber elenir)")


def test_firm():
    eq(classify.detect_firm("John Cockerill India Inaugurates Roll Shop at Taloja"),
       "John Cockerill India", "cok kelimeli ozne (Taloja hatasi)")
    eq(classify.detect_firm("Tenova I2S Awarded Cold Mill Contract in Brazil"),
       "Tenova I2S", "fiil isme yapismamali")
    eq(classify.detect_firm("India's JIL commissions continuous colour coating line"),
       "JIL", "ulke eki atilmali")
    eq(classify.detect_firm("Danieli to supply new pickling line to Acme Steel"),
       "Danieli", "to supply")


def test_scope():
    ok, _ = taxonomy.in_scope("Angang starts up new hot-dip galvanizing line")
    eq(ok, True, "kapsam ici")
    ok2, why = taxonomy.in_scope("HRC prices rise in Europe amid import pressure")
    eq(ok2, False, "fiyat haberi reddedilmeli")
    ok3, why3 = taxonomy.in_scope("Company X commissions new blast furnace")
    eq(ok3, False, "yuksek firin reddedilmeli")
    ok4, _ = taxonomy.in_scope("Steelmaker appoints new CEO of flat rolling division")
    eq(ok4, False, "atama haberi reddedilmeli")
    # 2026-W33 kosusunun ana hatasi: govdede 'prices' gecti diye gecerli haber elenmisti
    ok5, _ = taxonomy.in_scope(
        "Danieli to supply new pickling line to Acme Steel",
        "Acme said the investment comes as hot rolled coil prices rise in Europe.")
    eq(ok5, True, "govdedeki fiyat kelimesi haberi elememeli")
    # Turkce kaynak testi
    ok6, _ = taxonomy.in_scope("Tosyalı yeni galvaniz hattını devreye aldı")
    eq(ok6, True, "turkce baslik kapsam ici")
    eq(taxonomy.match_line("Yeni sürekli galvaniz hattı"), "Galvaniz hatti (CGL)",
       "turkce hat tespiti")
    eq(taxonomy.match_stage("Tosyalı yeni hattı devreye aldı"), "Ilk urun",
       "turkce asama tespiti")


def test_w33_regresyon():
    """2026-W33 kosusunda rapora sizan 4 cop satirin tekrarini engeller."""
    eq(taxonomy.is_junk_title("info@remove-this.herkules-machinetools.de"), True,
       "e-posta adresi haber degil")
    eq(taxonomy.is_junk_title("Read more"), True, "menu baglantisi haber degil")
    eq(taxonomy.in_scope("Almost €25,000 for volunteer initiatives!")[0], False,
       "bagis duyurusu elenmeli")
    eq(taxonomy.in_scope("Primetals Technologies to Revamp CSP Mill at WISCO in China")[0],
       False, "CSP/sicak hadde kapsam disi")
    eq(taxonomy.in_scope("thyssenkrupp Rasselstein installs 8 MW photovoltaic system "
                         "to advance decarbonization goals")[0], False,
       "gunes enerjisi duyurusu elenmeli")
    # Turkce buyuk harf: "İ".lower() sorunu fold() ile cozuldu
    t = "TOSYALI ALGÉRİE, SOĞUK HADDELEME KOMPLEKSİNDE İLK ÜRETİMİ YAPTI"
    eq(taxonomy.in_scope(t)[0], True, "turkce buyuk harf baslik kapsam ici")
    eq(taxonomy.match_line(t), "Soguk hadde", "turkce buyuk harf hat")
    eq(taxonomy.match_stage(t), "Ilk urun", "turkce buyuk harf asama")
    eq(taxonomy.match_country(t), "Cezayir", "yatirimin yeri sirketin merkezi degil")
    eq(classify.detect_firm("Primetals Technologies to Revamp Mill at WISCO in China"),
       "Primetals Technologies", "fiil musteri adi sanilmamali")


def test_w33d_regresyon():
    """2026-08-12 final kalibrasyon kosusunun hatalari: uclu KG Steel,
    baslik basindaki '11 Aug Free' pisligi, cift Hydnum."""
    eq(htmlx._trim_title("11 Aug Free KG Steel selects Primetals for Dangjin "
                         "PLTCM upgrade and capacity expansion"),
       "KG Steel selects Primetals for Dangjin PLTCM upgrade and capacity expansion",
       "bastaki tarih+Free etiketi atilmali")
    eq(taxonomy.similar_titles(
        "İspanya, Hydnum Steel'in Yeşil Çelik Tesisine 150 Milyon Euro Destek Sağlayacak",
        "Hydnum Steel, İber Yarımadası'nın ilk temiz çelik tesisi için 150 milyon "
        "euroluk yatırım taahhüdü aldı"), True, "Hydnum varyantlari ayni haber")
    eq(taxonomy.similar_titles(
        "Danieli wins cold mill order in Vietnam",
        "Primetals to modernise Korean pickling line"), False,
       "farkli haberler benzer sayilmamali")
    # ayni olayin uc varyanti ayni parmak izini vermeli (ulke alani guvenilmez)
    mk = lambda ulke: {"tedarikci": "Primetals", "firma": "KG Steel",
                       "hat": "Tandem soguk hadde (TCM)", "asama": "Modernizasyon",
                       "ulke": ulke}
    fp = lambda r: (taxonomy.fold(r["tedarikci"]) + "|" + r["hat"] + "|" + r["asama"])
    eq(fp(mk("Turkiye")) == fp(mk("")) == fp(mk("G. Kore")), True,
       "olay parmak izi ulkeden bagimsiz olmali")


def test_uclu_kg_senaryosu():
    """2026-08-12: ayni olay uc gazetede uc hat vurgusuyla cikti ve uc satir
    oldu. Cok bacakli parmak izi + baslik benzerligi bunu tek satira indirir."""
    from . import collect as col
    r1 = {"tedarikci": "Primetals", "firma": "KG Steel", "ulke": "G. Kore",
          "hat": "Tandem soguk hadde (TCM)", "asama": "Modernizasyon"}
    r2 = {"tedarikci": "Primetals", "firma": "Primetals Technologies",
          "ulke": "G. Kore", "hat": "Soguk hadde", "asama": "Modernizasyon"}
    r3 = {"tedarikci": "Primetals", "firma": "Primetals", "ulke": "G. Kore",
          "hat": "Asitleme hatti", "asama": "Modernizasyon"}
    k1, k2, k3 = col.event_keys(r1), col.event_keys(r2), col.event_keys(r3)
    eq(bool(k1 & k2), True, "varyant 2 ulke bacagıyla yakalanmali")
    eq(bool(k1 & k3), True, "varyant 3 ulke bacagıyla yakalanmali")


def test_iki_katmanli_liste():
    """Katman 2 = YASSI celik ile ilgili genel yatirim haberi.

    2026-08-12'de kapi "dunya geneli her celik yatirimi" idi. 2026-W35
    bulteni bu sozlesmenin yanlis oldugunu gosterdi: 9 Yatirim satirinin
    9'u da kapsam disiydi (pelet tesisi, sicak haddehane, entegre tesis,
    ham celik istatistigi, lojistik hisse devri, 110 milyar dolarlik
    projeksiyon). Okuyucu soguk haddehanede calisiyor; genel bir yatirim
    haberi ancak YASSI tarafa dokunuyorsa listeye girer.
    """
    ok = [# yassi isareti YOK -> artik girmez (uzun/profil ureticisi)
          ("Kocaer Çelik ABD'de Üretim İçin Şirket Kuruyor", False),
          # "sheet mill" yassi -> girer
          ("Nucor announces new sheet mill investment in West Virginia", True),
          # entegre yesil celik tesisi = yukari akis, yassi isareti yok
          ("Baowu Group and SNS eye green steel plant investment in Algeria", False),
          ("Jindal plans Rs 40,000 crore investment in new steel facility", False),
          # ...ama ayni yatirim yassi hat adiyla anlatilirsa girer
          ("Jindal plans Rs 40,000 crore investment in cold rolling complex", True),
          ("EREGL Hissesi 42,24 TL'de Kapanış Yaptı", False),
          ("Çin'in Çelik İhracatı, İlk 7 Ayda Yüzde 4,4 Geriledi", False),
          ("Electrical Steel Market Outlook (2026-2031)", False),
          # --- v4.1: Katman 2 artik gurultu denetimi uygular -----------------
          ("Hindistan, 2030'da 300 Milyon Ton Çelik Kapasitesi Hedefini Sürdürüyor", False),
          ("Metinvest'in 2026 İlk Yarı Çelik Üretimi %13 Arttı", False),
          ("SMS Group Strengthens Financial Performance and Accelerates Investment", False),
          ("Pakistan abandons liquidation plan for Pakistan Steel Mills", False),
          ("India's LMEL to invest in solar and wind power projects", False),
          ("Hoa Phat plans $765 million expansion of Dung Quat rail steel project", False),
          ("Steel demand in East Africa will be supported by infrastructure investment", False),
          ("Rebar and wire rod mill investment announced", False)]
    for t, w in ok:
        eq(taxonomy.genel_yatirim(t), w, "genel yatirim: " + t[:50])


def test_kapsam_havuzu():
    """KAPSAM DENETIMI (v4): her hat tipinden ve ekipman grubundan gercek
    baslik ornekleri. Hepsi kapsam ici cikmali - kapsam bir daha sessizce
    daralamaz. Ters ornekler ise KESINLIKLE girmemeli."""
    girmeli = [
        "ANDRITZ to supply new pickling section for heavy-duty push pickling line",
        "Danieli wins order for tandem cold mill and pickling line",
        "New reversing cold mill with Sendzimir stand ordered",
        "Continuous annealing line with radiant tube furnace commissioned",
        "Batch annealing plant with hood-type furnaces upgraded",
        "New hot-dip galvanizing line with air knife system starts up",
        "Zinc pot and pot roll replacement at galvanizing line",
        "Galvannealed steel line expansion announced",
        "Zn-Al-Mg coating line ordered for automotive steel",
        "Electrolytic tinning line modernization for tinplate producer",
        "ECCS tin-free steel line investment announced",
        "New colour coating line for prepainted steel commissioned",
        "Skin pass mill and tension leveller supplied to steel producer",
        "Slitting line and cut-to-length line for steel service centre",
        "Side trimmer and edge trimming upgrade on strip processing line",
        "Laser blanking line installed at steel service center",
        "Roll grinding machine and roll shop automation delivered",
        "Work roll texturing EDT system for cold mill",
        "Surface inspection system installed on galvanizing line",
        "X-ray thickness gauge and shapemeter for rolling mill",
        "Flash butt welder replaced on continuous pickling line",
        "New strip welder for coil joining at processing line",
        "Coil handling and coil packaging system for steel plant",
        "Electrolytic cleaning line for cold rolled strip ordered",
        "Acid regeneration plant with spray roaster for pickling line",
        "Electrical steel CRGO plant investment announced",
        "Digital twin for cold rolling mill process automation",
        "Steel coil warehouse automation with walking beam system",
        "Passivation and chromating line for galvanized steel",
        "TOSYALI ALGERIE, SOGUK HADDELEME KOMPLEKSINDE ILK URETIMI YAPTI",
        "Yeni galvaniz hatti devreye alindi",
        "Asitleme hatti modernizasyonu tamamlandi",
        "Surekli tavlama hatti icin siparis verildi",
        "Boyama hatti yatirimi acilandi ve boyali sac uretimi basladi",
        "Dilme hatti ve boy kesme hatti kuruldu",
        "Merdane taslama tezgahi merdane atolyesine alindi",
        "Serit kaynak makinesi bobin birlestirme icin yenilendi",
        "Celik servis merkezi yeni sac isleme hatti kuruyor",
        "Elektrik celigi tesisi icin tavlama hatti siparisi",
        "Bobin tasima ve paketleme sistemi devreye girdi",
    ]
    for t in girmeli:
        ok, sebep = taxonomy.in_scope(t)
        eq(ok, True, "KAPSAM ICI olmali (%s): %s" % (sebep, t[:60]))

    girmemeli = [
        "HRC prices rise in Europe amid import pressure",
        "EU considers curbs on electrical steel imports",
        "Electrical Steel Market Outlook 2026-2031 forecast",
        "Company X commissions new blast furnace",
        "Primetals Technologies to Revamp CSP Mill at WISCO",
        "New hot strip mill ordered in India",
        "Steelmaker appoints new CEO of flat rolling division",
        "Almost 25,000 euro for volunteer initiatives",
        "Divilma Headed to Orlando for New Cinnamon Roll Shop",
        "ANDRITZ starts up new surface treatment line for aluminum strip at AMAG",
        "New copper strip rolling mill for electronics",
        "Paper mill installs new slitting line",
        "Glass annealing furnace commissioned",
        "Rebar and wire rod mill investment announced",
        "Quarterly results: net profit rises 14 percent",
        "info@remove-this.example.de",
        # --- v4.1 sizinti regresyonlari (2026-08-12 kosusu) -----------------
        "powercore traction NGO 025-125Y420",
        "Hot-dip galvanized steel, thickness 0.4 - 3.0 mm",
        "Cold rolled steel strip, width up to 1850 mm",
        "Steel imports rise 12% year on year",
        "Global Cold Rolled Steel Market Size Worth USD 210 Billion by 2032",
        "Detailed Project Report on cold rolling mill with ROI and IRR",
        "Anti-dumping duties imposed on galvanized steel imports",
    ]
    for t in girmemeli:
        ok, sebep = taxonomy.in_scope(t)
        eq(ok, False, "KAPSAM DISI olmali: %s" % t[:60])


def test_tarih_celiskisi():
    """v4.1: eski icerik bugun servis edilirse (HTTP Last-Modified) baslikta
    gecen yil ile bulunan tarih catisir. Tosyali/Sonangol 2024 vakasi."""
    eq(dates.title_year_conflict(
        "August 2024 JOINT STEEL INVESTMENT WITH SONANGOL IN ANGOLA BY TOSYALI",
        "2026-08-10"), True, "2024 basligi 2026 tarihiyle gelemez")
    eq(dates.title_year_conflict(
        "Tosyali to reach 2 million tonnes by 2028", "2026-08-10"), False,
        "gelecek yil hedefi elenmemeli")
    eq(dates.title_year_conflict(
        "Primetals wins pickling line order", "2026-08-10"), False,
        "yilsiz baslik elenmemeli")
    eq(dates.kesin_mi("meta:article:published_time"), True, "meta yapisaldir")
    eq(dates.kesin_mi("json-ld"), True, "json-ld yapisaldir")
    eq(dates.kesin_mi("last-modified"), False, "last-modified dolayli")
    eq(dates.kesin_mi("liste"), False, "liste dolayli")


def test_tarih_acilari():
    """v4: Danieli tipi 'yil, gun ay' formati ve iki haneli yil."""
    eq(dates.parse_date_text("new orders 2026, 21st July Danieli", today=TODAY),
       "2026-07-21", "Danieli formati (yil once)")
    eq(dates.parse_date_text("top performances 2026, 18th June", today=TODAY),
       "2026-06-18", "Danieli formati 2")
    eq(dates.parse_date_text("21.07.26", today=TODAY), "2026-07-21", "iki haneli yil")


def test_compose_ve_mail():
    from . import compose, render
    rows = [
        {"anahtar": "a1", "tarih": "2026-08-05", "firma": "Tosyali Algerie",
         "ulke": "Cezayir", "hat": "Soguk hadde", "asama": "Ilk urun",
         "tedarikci": "", "kapasite": "", "tutar": "", "baslik": "t1",
         "kaynak": "SteelTurk", "url": "https://x/1", "puan": 70, "eksik": [],
         "tarih_kaynagi": "json-ld", "kaynak_id": "steelturk"},
        {"anahtar": "a2", "tarih": "2026-08-03", "firma": "KG Steel",
         "ulke": "G. Kore", "hat": "Tandem soguk hadde (TCM)",
         "asama": "Modernizasyon", "tedarikci": "Primetals", "kapasite": "",
         "tutar": "", "baslik": "t2", "kaynak": "Primetals",
         "url": "https://x/2", "puan": 60, "eksik": [], "tarih_kaynagi": "meta",
         "kaynak_id": "primetals"},
    ]
    stats = {"kaynak": 72, "ham": 900, "makale_acildi": 120, "tarihsiz_elendi": 40,
             "pencere_disi": 100, "kapsam_disi": 500, "tekrar": 3, "erisilemeyen": 6}
    oz = compose.exec_summary(rows, stats)
    eq("2" in oz and "Cezayir" in oz, True, "ozet sayilari ve ulkeyi anmali")
    eq("Tosyali" in oz, True, "Turkiye baglantili satir ozette olmali")
    s = compose.row_sentence(rows[1])
    eq("Primetals" in s and "yenileme" in s, True, "modernizasyon cumlesi")
    payload = {"rows": rows, "stats": stats, "unreachable": [("SMS group", "403")],
               "window": ["2026-07-21", "2026-08-11"], "period": "2026-W33"}
    mail = render.email_html(payload, None,
                             [{"konu": "Lazer kesim", "metin": "m",
                               "url": "https://x/3", "tarih": "2026-06-01"}], 5)
    for parca in ("Değerli yöneticilerim", "AI Özeti", "Zeynel", "Sayı #5",
                  "Soğuk Haddehane", "Teknoloji Köşesi",
                  "Bu Haftanın Taraması", "Elendi: kapsam dışı", "Lazer kesim"):
        eq(parca in mail, True, "mailde eksik: " + parca)
    eq("Yönetici özeti" in mail, False, "eski baslik kalmamali")
    eq("powered by" in mail and "Zeynel Abidin Çopur" in mail, True, "powered by")
    eq("Görüş ve önerilerinizi" in mail, False, "kapanis cumlesi silinmis olmali")
    payload["rows"] = rows + [{"anahtar": "w1", "tarih": "2026-08-07",
        "firma": "Kocaer", "ulke": "Turkiye", "hat": "Belirsiz",
        "asama": "Belirsiz", "tedarikci": "", "kapasite": "", "tutar": "",
        "baslik": "Kocaer Celik ABD'de sirket kuruyor", "kaynak": "SteelTurk",
        "url": "https://x/4", "puan": 5, "eksik": [], "tarih_kaynagi": "rss",
        "kaynak_id": "steelturk", "kategori": "Yatirim"}]
    mail2 = render.email_html(payload, None, [], 5)
    eq("YATIRIM" in mail2 and "Kocaer" in mail2, True, "yatirim katmani listede")
    # Kocaer profil/uzun urun ureticisi: yassi isareti tasimayan genel
    # yatirim haberi Katman 2'ye de girmez (2026-W35 karari).
    eq(taxonomy.watch_worthy("Kocaer Çelik ABD'de Üretim İçin Şirket Kuruyor"),
       False, "watch: yassi isareti olmayan TR yatirimi girmez")
    eq(taxonomy.watch_worthy("Borçelik Bursa'da soğuk hadde ve galvaniz tesisi kuruyor"),
       True, "watch: yassi hat adi tasiyan TR yatirimi girer")
    eq(taxonomy.watch_worthy("EREGL Hissesi 42,24 TL'de Kapanış Yaptı"),
       False, "watch: borsa haberi girmez")


def test_w33b_regresyon():
    """2026-08-12 kosusunun iki hatasi tekrarlanmasin."""
    # USS Gary restart karari teknoloji DEGILDIR (baslikta teknoloji fiili yok)
    eq(taxonomy.match_stage("U. S. Steel Announces Plans to Restart Gary Tin Mill")
       == "Teknoloji", False, "restart karari teknoloji sayilmamali")
    # Google News basligi "Baslik - Yayinci" ayristirilabilmeli
    t = "Danieli wins cold mill order in Vietnam - Steel Times International"
    b, _, pub = t.rpartition(" - ")
    eq((b, pub), ("Danieli wins cold mill order in Vietnam",
                  "Steel Times International"), "gnews baslik ayrimi")


def test_w33c_regresyon():
    """2026-08-12 aksam kosusunun hatalari: cift haber, tarcinli corek,
    ithalat kisiti haberi, 'launches production' teknoloji sanilmasi."""
    from . import compose
    eq(taxonomy.match_stage(
        "Tosyali Algérie Launches Production at Its New Cold Rolling Complex"),
       "Ilk urun", "'launches production' = ilk urun")
    eq(taxonomy.in_scope(
        "EU Considers Curbs on Electrical Steel Imports Amid Industry Pressures")[0],
       False, "ithalat kisiti haberi kapsam disi")
    eq(taxonomy.watch_worthy(
        "Electrical Steel Market Outlook (2026-2031) Forecast USD 52 Billion Capacity"),
       False, "pazar arastirmasi spam'i dikkat cekenlere giremez")
    eq(bool(taxonomy.STEEL_CONTEXT.search(taxonomy.fold(
        "Divilma Headed to Orlando for New Cinnamon Roll Shop"))),
       False, "tarcinli corek dukkani celik degildir")
    s = compose.row_sentence({"firma": "Primetals", "tedarikci": "Primetals",
                              "hat": "Asitleme hatti", "asama": "Modernizasyon",
                              "baslik": "x"})
    eq("Primetals'e verdi" in s, False, "kendi kendine ihale cumlesi yasak")
    eq("ustlendi" in s, True, "tedarikci bakis acisiyla yazilmali")
    # POSCO Ar-Ge basligi teknoloji sayilmali ('to Develop' kalibi kacmisti)
    eq(taxonomy.match_stage(
        "POSCO Partners with Hyundai Motor and 8 Organizations to Develop "
        "Next-Generation High-Efficiency Electrical Steel for EVs"),
       "Teknoloji", "'to develop' ar-ge haberi teknoloji sayilmali")


def test_line_and_stage():
    eq(taxonomy.match_line(
        "JVML awards electrical steel annealing and pickling lines to John Cockerill"),
       "Elektrik celigi hatti", "elektrik celigi asitlemeye dusmemeli")
    eq(taxonomy.match_stage("JIL commissions new colour coating line"),
       "Ilk urun", "'commissions' = ilk urun")
    eq(taxonomy.match_stage("Angang begins production at new CGL"),
       "Ilk urun", "'begins production' seri uretim DEGIL")
    eq(taxonomy.match_stage("Danieli wins contract for tandem cold mill"),
       "Sozlesme", "sozlesme")
    eq(taxonomy.match_stage("Mill reaches full capacity after ramp-up complete"),
       "Seri uretim", "seri uretim")
    eq(taxonomy.match_country("New line for Tosyali in Turkey"), "Turkiye", "ulke")


def test_listing_parser():
    page = """<html><body><ul>
      <li><time datetime="2026-08-05">5 Aug</time>
          <a href="/news/first-coil-cgl">Angang produces first coil at new galvanizing line</a></li>
      <li><span>01 August 2026</span>
          <a href="/news/tcm-order">Danieli wins tandem cold mill order in Vietnam</a></li>
      <li><a href="/about">Home</a></li>
    </ul></body></html>"""
    items = htmlx.parse_listing(page, "https://ex.com/news")
    eq(len(items), 2, "gezinme baglantisi elenmeli")
    eq(items[0]["url"], "https://ex.com/news/first-coil-cgl", "mutlak adres")
    eq(dates.parse_date_text(items[0]["date_hint"], today=TODAY), "2026-08-05", "ipucu 1")
    eq(dates.parse_date_text(items[1]["date_hint"], today=TODAY), "2026-08-01", "ipucu 2")


def test_feed_parser():
    xml = """<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>New pickling line for Acme</title>
        <link>https://ex.com/a</link>
        <pubDate>Tue, 04 Aug 2026 07:00:00 GMT</pubDate>
        <description>Acme ordered a push-pull pickling line.</description></item>
    </channel></rss>"""
    eq(feeds.looks_like_feed(xml), True, "besleme tanindi")
    it = feeds.parse_feed(xml)
    eq(len(it), 1, "1 kayit")
    eq(dates.parse_date_text(it[0]["date_raw"], today=TODAY), "2026-08-04", "pubDate")


def test_state():
    k1 = state.norm_key("Angang produces first coil at new galvanizing line", "u1")
    k2 = state.norm_key("Angang Produces First Coil At New Galvanizing Line!", "u2")
    eq(k1, k2, "normalizasyon: ayni haber ayni anahtar")
    k3 = state.norm_key("Danieli wins tandem cold mill order", "u3")
    eq(k1 == k3, False, "farkli haber farkli anahtar")
    eq(state._migrate_seen([{"t": ["a", "b"], "d": "2026-01-01"}]).__class__, dict,
       "v1 state gocu")


def test_build_row():
    r = classify.build({
        "title": "India's JIL commissions continuous colour coating line",
        "url": "https://ex.com/x", "date": "2026-05-20", "publisher": "Steel Times",
        "source_id": "steeltimesint",
        "text": "JIL has invested $155 million in the 300,000 tpy line supplied by Danieli.",
        "date_src": "json-ld"})
    eq(r["firma"], "JIL", "firma")
    eq(r["hat"], "Boyama hatti (CCL)", "hat")
    eq(r["asama"], "Ilk urun", "asama")
    eq(r["ulke"], "Hindistan", "ulke")
    eq(r["tedarikci"], "Danieli", "tedarikci")
    eq(bool(r["kapasite"]), True, "kapasite yakalandi")
    eq(bool(r["tutar"]), True, "tutar yakalandi")
    eq(r["eksik"], [], "eksik alan yok")


def test_olay_kapisi_v5():
    """v5 (2026-08-17): OLAY kapisi + baslik temizligi.

    Vakalarin TAMAMI gercek kosu ciktilarindan alindi: 37 commit'in
    reddedilenler.json + hafta_*.json dosyalarindan cikan 1154 benzersiz
    baslik havuzunda olculdu. Eski kapi 92 basligi kabul ediyordu, bunlarin
    yaklasik 40'i OEM urun katalogu, pazarlama yazisi ya da ticaret/finans
    haberiydi. Yeni kapi 48 kabul ediyor; asagidaki ayrimlar sarttir.
    """
    def gecer(b):
        """collect.py ile AYNI zincir: temizle -> kapsam -> olay."""
        tb = taxonomy.temiz_baslik(b)
        ok, _ = taxonomy.in_scope(tb, "")
        if ok and taxonomy.haber_olayi(tb):
            return "Hat"
        if taxonomy.genel_yatirim(tb):
            return "Yatirim"
        return None

    # --- GECMESI SART: gercek hat olaylari -----------------------------
    for b in [
        "ANDRITZ to supply new cut-to-length line to Olympic Steel, USA",
        "ANDRITZ to upgrade continuous galvanizing line for Tangsteel, China",
        "ANDRITZ receives final acceptance for pickling line and acid "
        "regeneration plant at voestalpine, Austria",
        "Tata Steel awards ANDRITZ order for acid regeneration plant",
        "KG Steel selects Primetals for Dangjin PLTCM upgrade",
        "Primetals to modernise Korean pickling line",
        "CSC orders overhaul of two roll grinding machines",
        "MINO Process Control Completes Bliss Cold Mill Upgrade at ELVAL",
        "Olympic Metals Installs DELTA Steel Technologies Cut-To-Length Line",
        # Turkce: ek alan kokler kapida kalmamali (sondaki \b tuzagi)
        "TOSYALI ALGERIE, SOGUK HADDELEME KOMPLEKSINDE ILK URETIMI YAPTI",
        "Kirac Galvaniz Bulgaristan'da 10 Milyon Euro'luk Anlasmaya Imza Atti",
    ]:
        eq(gecer(b), "Hat", "Hat gecmeli: " + b[:52])

    # --- ELENMESI SART: konu dogru ama OLAY YOK (urun katalogu) --------
    for b in [
        "Flying Shear Cut-to-Length Lines",
        "Roll Feed / Stop - Start Plate Cut-To-Length Lines",
        "View All Cut-To-Length Lines",
        "Strip processing line, Annealing and Pickling line with vertical "
        "annealing furnace",
        "Degreasing and Pickling lines, finish-brushing and passivation",
        "High convection chamber-type furnaces for the annealing of strip coils",
        "Strip width measurement - EMG BREIMO",
        "Flotation dryer for coated silicon steel strip",
        "Hot-Dip Zn-Al-Mg Coated Steel",
        "Electro Galvanized Steel (EGI)",
    ]:
        eq(gecer(b), None, "katalog elenmeli: " + b[:52])

    # --- ELENMESI SART: pazarlama / kose yazisi ------------------------
    for b in [
        "Case Study: Cut-to-Length Line (.179 x 60.00)",
        "Choosing the Right Scrap Solution for Your Slitting Line",
        "Modern Strip Production Requires More Than Conventional Width "
        "Measurement",
        "Delta Steel Technologies Showcases Next-Level Temper Pass CTL Line",
    ]:
        eq(gecer(b), None, "pazarlama elenmeli: " + b[:52])

    # --- ELENMESI SART: W33 bulteninde sizan iki satir -----------------
    eq(gecer("Russian strike halts Metinvest's Zaporizhstal steel production"),
       None, "Metinvest 'invest' icerdigi icin yatirim sanilmamali")
    eq(gecer("Domestic steel capacity expansion to boost higher-grade iron "
             "ore demand - report"), None, "rapor satisi elenmeli")

    # --- ELENMESI SART: gurultu artik Hat katmaninda da calisir --------
    for b in [
        "Sale of thyssenkrupp's Indian electrical steel business completed",
        "thyssenkrupp Electrical Steel: Temporary plant shutdowns in Germany",
        "PPGI Galvanized Coil / Turkey / Ex-Works USD/t",
        "Amalgamation of The Tinplate Company of India into Tata Steel",
        "Cliffs CEO says grain-oriented steel essential for transformers",
        "Uluslararasi Galvaniz Sektorunun Buyuk Bulusmasi Istanbul'da",
        "Hoberg & Driesch ve ATTEC'den Turkiye'ye Stratejik Celik Boru Yatirimi",
    ]:
        eq(gecer(b), None, "gurultu elenmeli: " + b[:52])

    # --- BASLIK TEMIZLIGI: ayni haber tek anahtara inmeli --------------
    a = "ANDRITZ to supply new cut-to-length line to Olympic Steel, USA"
    b = (a + " 2025-02-11 International technology group ANDRITZ has received "
         "an order from Olympic Steel")
    eq(taxonomy.temiz_baslik(a), taxonomy.temiz_baslik(b), "lede ayiklanmali")
    eq(state.norm_key(taxonomy.temiz_baslik(a)),
       state.norm_key(taxonomy.temiz_baslik(b)),
       "temizlikten sonra tekrar anahtari ayni olmali")
    eq(taxonomy.temiz_baslik("11 Aug Free KG Steel selects Primetals for PLTCM"),
       "KG Steel selects Primetals for PLTCM", "Kallanish on eki ayiklanmali")
    eq(taxonomy.temiz_baslik("Daily press | 2025-01-30 Sale of business completed"),
       "Sale of business completed", "thyssenkrupp on eki ayiklanmali")
    eq(taxonomy.temiz_baslik("new orders 2026, 28th July FAC achieved for caster"),
       "FAC achieved for caster", "Danieli on eki ayiklanmali")


def test_w34_sicak_hadde():
    """2026-W34 bulteninin bozuk satiri: govde kapsam KURAMAZ.

    "Nippon Steel, 6 Milyon Tonluk Yeni SICAK Haddeleme Hattini Devreye Aldi"
    basliginda soguk taraf terimi yok; govdesinde hadde/serit kelimeleri
    geciyordu ve haber "Serit isleme hatti" rozetiyle Hat katmanina girdi.
    Kapsam: sicak hadde SONRASI - sicak hadde hattinin kendisi Hat olamaz.
    """
    tr = "Nippon Steel, 6 Milyon Tonluk Yeni Sicak Haddeleme Hattini Devreye Aldi"
    govde = ("Nippon Steel'in yeni hatti yilda 6 milyon ton serit uretecek; "
             "hadde parki ve bobin tasima sistemleri yenilendi.")
    eq(taxonomy.in_scope(tr, govde)[0], False,
       "sicak hadde hatti govde yuzunden Hat'a girmemeli")
    # 2026-W35 DUZELTMESI: bu satir Katman 2'de de KALAMAZ. Onceki surum
    # yukari akisi "genel yatirim" sayip muaf tutuyordu ve ayni Nippon
    # Steel sicak haddehane haberi W35 bulteninde YATIRIM rozetiyle
    # okuyucuya ulasti. Kapsam vetosu artik her iki katmanda calisir.
    eq(taxonomy.genel_yatirim(tr), False,
       "sicak hadde Katman 2'ye de giremez")
    # Ayni kural gercek hat haberini ELEMEMELI: baslikta terim varsa gecer
    eq(taxonomy.in_scope("Primetals to modernise Korean pickling line", "")[0],
       True, "baslikta hat terimi varsa govdeye gerek yok")
    eq(taxonomy.in_scope(
        "Danieli to supply new pickling line to Acme Steel",
        "Acme said the investment comes as hot rolled coil prices rise.")[0],
       True, "govdedeki sicak hadde/fiyat kelimesi haberi elememeli")
    # v5.2: govde kapsami KURABILIR - baslikta hat adi gecmeyen gercek haber
    eq(taxonomy.in_scope(
        "Marcegaglia selects Fives for digital upgrade",
        "The upgrade covers the annealing and pickling line at Gazoldo.")[0],
       True, "govde kapsam kurabilmeli (baslikta hat adi yok)")
    # ...ama baslik yukari akis diyorsa govde onu kurtaramaz
    eq(taxonomy.in_scope(
        "Hybar orders continuous minimill from SMS group",
        "The minimill will feed a downstream galvanizing line.")[0],
       False, "baslikta yukari akis varsa govde kurtaramaz")
    # karma baslik: guclu soguk terim vetoyu kaldirir
    eq(taxonomy.in_scope(
        "ANDRITZ to supply cold rolling mill and hot strip mill to Acme", "")[0],
       True, "baslikta guclu soguk terim varsa veto kalkar")
    # muteahhit atamasi kisi atamasi degildir
    eq(taxonomy.in_scope(
        "Welsh contractor appointed for pickle line construction at Port Talbot",
        "")[0], True, "muteahhit atamasi elenmemeli")



def test_niyet_kapisi_ilk_urun():
    """v9 (2026-08-17): "Ilk urun" rozeti niyet basligina verilmez.

    2026-W34 kosusunun UC satirinin UCU de "Ilk urun" rozetiyle cikti.
    Ucunun de basligi olay sozcugu tasimiyor (match_stage(baslik)=Belirsiz),
    yani asama GOVDEden okundu; govdedeki "opens/commissioned/start-up"
    kelimeleri rozeti kurdu. Ikisinde rozet YANLISTI:

      Jindal Stainless  -> yatirim karari, hatlar 2027-28'de bitecek
      Hoa Binh/Pomina   -> mutabakat zapti, insaat ekimde baslayacak

    Ucuncusunde (tk accelis) rozet DOGRUYDU - yeni dilme hattinda ilk 500
    bobin islendi. Bu yuzden govde toptan susturulmaz; ayirt eden sey
    BASLIKTAKI niyet dilidir.
    """
    ortak = {"url": "https://www.steelorbis.com/x", "date": "2026-08-17",
             "publisher": "SteelOrbis", "source_id": "steelorbis",
             "source_kind": "dergi", "source_country": "TR", "date_src": "json-ld"}
    # Govde metinleri "Ilk urun" tetikleyicisini TASIYOR - kapinin isini
    # gordugu ancak boyle olculebilir.
    tetikleyici = ("The group opens a new chapter in Asia; its previous line "
                   "was commissioned in 2019 and reached start-up in months.")

    r1 = classify.build(dict(ortak, title=(
        "India's Jindal Stainless Limited to invest $94 million to ramp up "
        "cold rolling capacity"), text=tetikleyici))
    eq(r1["asama"] != "Ilk urun", True,
       "'to invest' basligi govdeden Ilk urun rozeti alamaz")

    r2 = classify.build(dict(ortak, title=(
        "Hoa Binh and Pomina Steel partner on 1.2 million mt flat steel "
        "plant expansion"), text=tetikleyici))
    eq(r2["asama"] != "Ilk urun", True,
       "'partner on' basligi govdeden Ilk urun rozeti alamaz")

    # ...ama niyet dili YOKSA govde eskisi gibi rozeti kurabilmeli
    r3 = classify.build(dict(ortak, title=(
        "tk accelis announces milestone at Stuttgart steel service center"),
        text=("tk accelis Processing Europe has processed the first 500 coils "
              "on its new slitting line and commissioned a packaging line.")))
    eq(r3["asama"], "Ilk urun",
       "niyet dili olmayan baslikta govde Ilk urun rozetini kurabilmeli")
    eq(r3["hat"], "Dilme / boy kesme / SSC", "tk accelis hat tipi")

    # Baslik kendi asamasini soyluyorsa kapi hic calismaz
    eq(taxonomy.match_stage(
        "Tosyali to supply and commission new galvanizing line"), "Sozlesme",
       "baslik asamasi varsa niyet kapisi devreye girmez")
    # exclude parametresi siradaki eslesmeye duser, Belirsiz'e atlamaz
    eq(taxonomy.match_stage("Acme commissions revamped pickling line",
                            exclude=("Ilk urun", "Seri uretim")),
       "Modernizasyon", "exclude siradaki asamayi bulmali")


def test_capraz_kontrol():
    """v9 (2026-08-17): capraz kontrolun agsiz cekirdegi.

    Vaka 2026-W34'un GERCEK verisidir. Haftalik liste uc satir uretti;
    ayni gun SteelOrbis sitemap'inde kapsam ici DORDUNCU bir haber daha
    duruyordu ve listeye girmemisti:

      .../kg-steel-selects-primetals-for-dangjin-pltcm-upgrade-...-1470187.htm

    Beklenen davranis: uc listedeki adres "listede" diye ayiklanir, KG
    Steel "kacan" olarak kalir. Ayrica ayni haberin BASKA bir yayindaki
    varyanti (STI'nin kendi adresi) baslik benzerligiyle ayiklanmalidir -
    yoksa her hafta ayni haber iki kez "kacan" diye gosterilir.
    """
    from . import capraz as cp

    payload = {"rows": [
        {"baslik": ("India's Jindal Stainless Limited to invest $94 million "
                    "to ramp up cold rolling capacity"),
         "url": ("https://www.steelorbis.com/steel-news/latest-news/indias-jindal-"
                 "stainless-limited-to-invest-94-million-to-ramp-up-cold-rolling-"
                 "capacity-1471127.htm")},
        {"baslik": "tk accelis announces milestone at Stuttgart steel service center",
         "url": ("https://www.steelorbis.com/steel-news/latest-news/tk-accelis-"
                 "announces-milestone-at-stuttgart-steel-service-center-1469079.htm")},
        {"baslik": ("Hoa Binh and Pomina Steel partner on 1.2 million mt flat "
                    "steel plant expansion"),
         "url": ("https://www.steelorbis.com/steel-news/latest-news/hoa-binh-and-"
                 "pomina-steel-partner-on-12-million-mt-flat-steel-plant-"
                 "expansion-1469094.htm")}]}
    adresler, basliklar = cp.listedekiler(payload, {"son_basliklar": []})
    eq(len(adresler), 3, "listedeki adres sayisi")

    # Sitemap adaylari: basliklar ADRES SLUG'INDAN uretilir (makale acilmadan)
    KACAN = ("https://www.steelorbis.com/steel-news/latest-news/kg-steel-selects-"
             "primetals-for-dangjin-pltcm-upgrade-and-capacity-expansion-1470187.htm")
    # Ayni KG Steel haberinin ikinci SteelOrbis adresi (www yok, sondaki
    # slash var): adres normalizasyonu tek satira indirmeli.
    KACAN2 = KACAN.replace("https://www.", "https://").replace(".htm", ".htm/")
    # tk accelis haberinin Yieh'teki varyanti: haftalik listede SteelOrbis
    # basligiyla var, baslik benzerligiyle ayiklanmali.
    YIEH = ("https://yieh.com/en/News/tk-accelis-processing-europe-expands-"
            "stuttgart-steel-service-center-capacity/161883")
    # Kapsam disi: sicak hadde.
    SICAK = ("https://www.steelorbis.com/steel-news/latest-news/nippon-steel-"
             "completes-new-hot-rolling-line-at-nagoya-works-1469660.htm")

    urls = [r["url"] for r in payload["rows"]] + [KACAN, KACAN2, YIEH, SICAK]
    import radar.collect as col
    adaylar = [{"title": col.slug_baslik(u), "url": u} for u in urls]

    kalan, atlanan = cp.eleme(adaylar, adresler, basliklar)
    eq(len(kalan), 1, "yalniz KG Steel kacan olarak kalmali")
    eq("kg-steel-selects-primetals" in kalan[0]["url"], True, "kacan KG Steel olmali")
    eq(kalan[0]["katman"], "Hat", "KG Steel Hat katmani")

    sebepler = {a["url"]: a["sebep"] for a in atlanan}
    for r in payload["rows"]:
        eq(sebepler.get(r["url"], "").startswith("listede"), True,
           "listedeki satir ayiklanmali: " + r["baslik"][:45])
    eq(sebepler[KACAN2], "listede (adres)",
       "ayni haberin ikinci adresi tekrar uretmemeli")
    eq(sebepler[YIEH], "listede (benzer baslik)",
       "tk accelis Yieh varyanti baslik benzerligiyle ayiklanmali")
    eq(sebepler[SICAK], "yukari_akis", "sicak hadde kapida elenmeli")

    # Adres normalizasyonu: www / sondaki slash / sorgu farki tekrar uretmemeli
    eq(cp._norm_url("https://WWW.SteelOrbis.com/a/b.htm?x=1#y"),
       "steelorbis.com/a/b.htm", "adres normalizasyonu")

    # robots.txt kesfi: elle yazilan adresler eskiyor. 2026-08-17 kosusunda
    # Mysteel icin denenen DORT adresin dordu de 404/bos dondu.
    robots = ("User-agent: *\n"
              "Disallow: /admin\n"
              "Sitemap: https://news.mysteel.com/sitemap-index.xml\n"
              "sitemap: https://news.mysteel.com/sitemap-news-1.xml\n"
              "Sitemap: /gorece/olmaz.xml\n")
    import radar.http as H
    eski = H.fetch
    try:
        H.fetch = lambda u, use_cache=True: (True, robots, {"status": 200, "final": u})
        bulunan = cp.robots_sitemaplari("https://news.mysteel.com/")
    finally:
        H.fetch = eski
    eq(bulunan[0], "https://news.mysteel.com/sitemap-news-1.xml",
       "haber sitemap'i one alinmali")
    eq(len(bulunan), 2, "gorece adres atlanmali")


def test_teknoloji_ve_ai_bolumleri():
    """v10 (2026-08-17): iki KALICI bolum - Teknoloji Kosesi ve AI Kontrolu.

    Ikisi de aday/icerik cikmayan haftalarda da render edilir. Sebep: bolumun
    hic gorunmemesi ile "bakildi, cikmadi" ayni sey degildir; okuyucu kosenin
    unutuldugunu mu yoksa gercekten bos mu oldugunu bilemiyordu. 2026-W34'te
    teknoloji kosesi tam olarak bu yuzden sessizce yok olmustu.

    Vakalar 2026-W34'un gercek verisidir.
    """
    from . import compose, render
    from .cli import _eklenen_satirlar

    rows = [{"anahtar": "c0b5f864813ba8fd", "tarih": "2026-08-17",
             "firma": "Jindal Stainless Limited", "ulke": "Hindistan",
             "hat": "Soguk hadde", "asama": "Modernizasyon", "tedarikci": "",
             "kapasite": "", "tutar": "$94 million", "kategori": "Hat",
             "baslik": ("India's Jindal Stainless Limited to invest $94 million "
                        "to ramp up cold rolling capacity"),
             "kaynak": "SteelOrbis", "kaynak_id": "steelorbis",
             "url": "https://www.steelorbis.com/x-1471127.htm", "puan": 59.0,
             "eksik": [], "tarih_kaynagi": "json-ld"}]
    stats = {"kaynak": 133, "ham": 2451, "makale_acildi": 220, "tarihsiz_elendi": 84,
             "pencere_disi": 191, "kapsam_disi": 2148, "tekrar": 20, "erisilemeyen": 10}
    payload = {"rows": rows, "stats": stats, "unreachable": [],
               "window": ["2026-08-02", "2026-08-17"], "period": "2026-W34"}

    # --- BOS teknoloji kosesi + BOS AI bolumu ---
    bos = render.email_html(payload, {}, [], 15)
    eq("Teknoloji Köşesi" in bos, True, "bos haftada da kose basligi cikmali")
    eq(render.TEKNOLOJI_BOS in bos, True, "bos kose metni basilmali")
    eq("AI Kontrolü ve Eklemeleri" in bos, True, "bos haftada da AI bolumu cikmali")
    eq(compose.AI_BOLUM_BOS in bos, True, "bos AI metni basilmali")
    # Kose HER ZAMAN listeden ONCE gelir
    eq(bos.index("Teknoloji Köşesi") < bos.index("Haftanın Gelişmeleri"), True,
       "bos kose bile listeden once gelmeli")

    # --- DOLU teknoloji kosesi: yine listeden once ---
    dolu_t = render.email_html(payload, {}, [
        {"konu": "PLTCM'de AI destekli proses otomasyonu", "metin": "m",
         "url": "https://x/1", "tarih": "2026-08-11"}], 15)
    eq(dolu_t.index("Teknoloji Köşesi") < dolu_t.index("Haftanın Gelişmeleri"), True,
       "dolu kose de listeden once gelmeli")
    eq(render.TEKNOLOJI_BOS in dolu_t, False, "icerik varken bos metin cikmamali")

    # --- DOLU AI bolumu: dort grup da gorunmeli ---
    ozet = {
        "ai_eklenen": [{"baslik": "KG Steel selects Primetals for Dangjin PLTCM upgrade",
                        "kaynak": "SteelOrbis",
                        "neden": "STI 403 verdi, haber sitemap'ten gec dustu",
                        "url": "https://www.steelorbis.com/kg-1470187.htm",
                        "tarih": "2026-08-11", "firma": "KG Steel",
                        "ulke": "G. Kore", "hat": "Tandem soguk hadde (TCM)",
                        "asama": "Sozlesme"}],
        "ai_duzeltme": [{"baslik": "Jindal Stainless",
                         "neden": "rozet 'Ilk urun' idi; yatirim karari, Modernizasyon yapildi"}],
        "ai_cikarilan": [{"baslik": "Nucor to invest $59 million in steel grating capacity",
                          "neden": "grating uzun/imalat urunu, kapsam disi"}],
        "ai_kontrol": "SteelOrbis, STI ve Mysteel sitemap'leri tarandi; 1 kacan bulundu",
    }
    gruplar = compose.ai_bolumu(ozet)
    eq(len(gruplar), 4, "dort grup da dolu olmali")
    dolu = render.email_html(payload, ozet, [], 15)
    eq(compose.AI_BOLUM_BOS in dolu, False, "icerik varken bos metin cikmamali")
    for parca in ("Yazılımın kaçırdığı", "Düzeltilen satırlar",
                  "Listeden çıkarılanlar", "Çapraz kontrol",
                  "KG Steel selects Primetals", "grating", "1 kacan bulundu"):
        eq(parca in dolu, True, "AI bolumunde eksik: " + parca)

    # --- ai_eklenen GERCEKTEN satir uretir ve satir "+ AI" ile isaretlenir ---
    eklenen = _eklenen_satirlar(ozet["ai_eklenen"], payload)
    eq(len(eklenen), 1, "ai_eklenen bir satir uretmeli")
    eq(eklenen[0]["elle_eklendi"], True, "satir elle_eklendi isaretli olmali")
    eq(eklenen[0]["kategori"], "Hat", "varsayilan katman Hat")
    p2 = dict(payload, rows=rows + eklenen)
    isaretli = render.email_html(p2, ozet, [], 15)
    eq("+ AI" in isaretli, True, "elle eklenen satir '+ AI' rozeti tasimali")
    eq(isaretli.count("+ AI"), 1, "yalniz elle eklenen satir isaretlenmeli")

    # Sadece aciklama olan madde (url/baslik yok) satir URETMEZ ama bolumde kalir
    eq(_eklenen_satirlar([{"neden": "STI 403 verdi, elle bakildi"}], payload), [],
       "url'siz madde satir uretmemeli")
    eq(len(compose.ai_bolumu({"ai_eklenen": [{"neden": "STI 403 verdi"}]})), 1,
       "url'siz madde AI bolumunde yine gorunmeli")
    # Ayni URL listede varsa tekrar eklenmez
    eq(_eklenen_satirlar([{"baslik": "x", "url": rows[0]["url"]}], payload), [],
       "listedeki URL tekrar eklenmemeli")


def test_w34_sifir_satir_teshisi():
    """v11 (2026-08-18): 2026-W34 kosusu neden 0 satir uretti.

    Celiski: hafta_2026-W34.json'da kabul=0 ama tekrar=22 iken
    state/state.json'da seen=0 ve events=0. Bos hafizayla 22 "tekrar"
    olamaz - olamamasi gerekirdi.

    SEBEP: KALIBRASYON modu seen/events/tech_seen'i sifirliyor ama tekrar
    savunmasinin UCUNCU bacagini, son_basliklar'i (35 kayit) BIRAKIYORDU.
    Baslik benzerligi bacagi calismaya devam etti; mod ekrana "tekrar
    engeli kapali" yazarken engel aciktı.

    IKINCI SEBEP: son_basliklar'da v8 oncesi kosulardan kalan URUN
    KATALOGU basliklari vardi - bunlar bugunku kapiya gore haber bile
    degil ama her gercek elektrik celigi / galvaniz haberini eliyorlardi.

    UCUNCU SEBEP: reddedilenler.json ilk 600 kaydi aliyordu; akisin basi
    kapsam_disi (2149 adet) ile doldugu icin tekrar kayitlari dosyaya HIC
    girmedi ve celiski gorunmez kaldi.
    """
    # state.json'dan alinan GERCEK cop basliklar
    cop = ["Electrical steel, non grain oriented",
           "powercore\u00ae traction NGO 025-125Y420",
           "Hot-dip galvanized narrow strip"]
    for t in cop:
        eq(taxonomy.is_junk_title(t), True, "cop baslik taninmali: " + t[:40])

    # ...ve bunlarin oldurdugu GERCEK haber (2026-08-17 kosusunun kacani)
    gecmis = [{"b": "KG Steel Selects Primetals Technologies for PLTCM Revamp",
               "t": "2026-08-11", "a": "Modernizasyon"}]
    yeni_haber = "KG Steel selects Primetals for Dangjin PLTCM upgrade and capacity expansion"
    eq(any(taxonomy.similar_titles(yeni_haber, b["b"]) for b in gecmis), True,
       "ayni olayin varyanti gecmise karsi yakalanmali (bu DOGRU davranis)")

    # Cop suzgeci: katalog basligi hafizada dursa bile eleme yapamaz
    kirli = gecmis + [{"b": c, "t": "2026-08-11", "a": "Teknoloji"} for c in cop]
    temiz = [b for b in kirli if not taxonomy.is_junk_title(b.get("b", ""))]
    eq(len(temiz), 1, "cop basliklar karsilastirma havuzundan dusmeli")

    # KALIBRASYON modu son_basliklar'i da sifirlamali
    import radar.cli as C
    kaynak = __import__("inspect").getsource(C.cmd_run)
    eq('st0["son_basliklar"] = []' in kaynak, True,
       "KALIBRASYON son_basliklar'i da sifirlamali")
    # v16: "gonderildi" isaretini artik tarama DEGIL finalize koyar, cunku
    # postayi editor onayi gonderiyor. Onaylanmayan her kosu gercek haberleri
    # yakiyordu (olcum: gonderilen 3 satira karsilik 21 satir "gonderilmis"
    # isaretliydi). Bu yuzden cop-baslik suzgeci de finalize tarafinda.
    import inspect as _i
    fin = _i.getsource(C.cmd_finalize)
    eq('taxonomy.is_junk_title(r.get("baslik", ""))' in fin, True,
       "cop baslik son_basliklar'a yazilmamali (finalize tarafinda)")
    eq('st["seen"][r["anahtar"]]' in kaynak, False,
       "tarama 'gonderildi' isareti koymamali")

    # Reddedilenler: sebep basina kota olmadan "tekrar" kayitlari kaybolur
    from .config import REJECT_SEBEP_KOTA, REJECT_TOPLAM
    eq(REJECT_SEBEP_KOTA > 0 and REJECT_TOPLAM > REJECT_SEBEP_KOTA, True,
       "sebep kotasi tanimli olmali")
    sayac, kayit = {}, []
    for sebep in ["kapsam_disi"] * 2149 + ["tekrar"] * 22:
        sayac[sebep] = sayac.get(sebep, 0) + 1
        if sayac[sebep] <= REJECT_SEBEP_KOTA and len(kayit) < REJECT_TOPLAM:
            kayit.append(sebep)
    eq(kayit.count("tekrar"), 22, "22 tekrar kaydinin hepsi dosyaya girmeli")


def test_w35_katman2_kapsam_kapisi():
    """v12 (2026-08-27): Katman 2'nin kapsam kapisi. 2026-W35 GERCEK kosusu.

    Kosu 11 satir uretti; 9'u Yatirim katmanindaydi ve DOKUZUNUN DA in_scope
    sonucu "kapsam disi" idi. Katman 2'nin kapsam vetosu yoktu, bulteni
    yukari akis ve piyasa haberi doldurdu. Asagidakiler o koşunun gercek
    basliklaridir.
    """
    girmemeli = [
        "India's SEPC Limited wins $90 million contract to build pellet plant at SAIL's IISCO mill",
        "Nippon Steel, 6 Milyon Tonluk Yeni Sıcak Haddeleme Hattını Devreye Aldı",
        "Indian fair trade regulator approves Tata Steel's acquisition of additional stake in logistics firm",
        "Baowu Group and SNS eye integrated green steel plant investment in Algeria",
        "Hybar advances low-carbon steel expansion in Arkansas",
        "Avustralya'nın Yeşil Çelik Hedefi İçin 14 Yılda 110 Milyar Dolarlık Yatırım Gerekiyor",
        "India: Crude steel expansion approvals reach 19 mnt/year in Apr-Jul'26",
        "Manaksia Steels plans \u20b9800 crore investment to nearly triple speciality steel capacity by FY34",
    ]
    for t in girmemeli:
        eq(taxonomy.genel_yatirim(t), False, "Katman 2'ye girmemeli: " + t[:52])
        eq(taxonomy.in_scope(t, "")[0], False, "Hat'a da girmemeli: " + t[:52])

    # ...ama ayni koşunun IKI GERCEK satiri kalmali
    for t in ["KG Steel selects Primetals for Dangjin PLTCM upgrade and capacity expansion",
              "India's Jindal Stainless Limited to invest $94 million to ramp up cold rolling capacity"]:
        eq(taxonomy.in_scope(t, "")[0], True, "kapsam ici kalmali: " + t[:52])

    # YASSI isareti tasiyan genel yatirim haberi GIRER
    for t in ["Hoa Binh and Pomina Steel partner on 1.2 million mt flat steel plant expansion",
              "Nucor announces new sheet mill investment in West Virginia",
              "India's Manaksia Steel to invest $84 million to expand value-added flats capacities"]:
        eq(taxonomy.genel_yatirim(t), True, "yassi yatirim girmeli: " + t[:52])

    # SMM bicimi: "[Baslik]Govde..." - govde ayiklanmali
    smm = ("[Algeria Plans to Build New Steel Complex in Oran]According to Algerian "
           "media reports, Algeria plans to build a new steel complex in Ain El Biya, "
           "Oran Province, as a key project to advance")
    eq(taxonomy.temiz_baslik(smm), "Algeria Plans to Build New Steel Complex in Oran",
       "koseli parantez basligi ayiklanmali")

    # "Oran Province" icindeki "vinc": kelime siniri olmayan kisa kalip
    # Cezayir entegre tesisini Hat katmanina sokmustu.
    eq(bool(taxonomy.SCOPE_WEAK.search(taxonomy.fold("Oran Province"))), False,
       "'province' icindeki 'vinc' eslesmemeli")
    eq(bool(taxonomy.SCOPE_WEAK.search(taxonomy.fold("bobin vinci"))), True,
       "gercek 'vinc' (ekli hali dahil) eslesmeli")
    eq(bool(taxonomy.SCOPE_WEAK.search(taxonomy.fold("tavlama firini"))), True,
       "gercek 'firin' (ekli hali dahil) eslesmeli")


def test_w35_ornek_kosu():
    """v13 (2026-08-27): W35 ornek koşusunun (33040687548) bes satiri.

    v12'den sonra kosu 11 -> 5 satira indi ama uçu hala yanlisti. Vakalar o
    kosunun GERCEK basliklaridir.
    """
    # 1) TICARET DAVASI Hat katmanina girmisti: "cold rolled" tasiyor diye.
    ad = "Pakistan launches AD sunset review on cold rolled steel imports"
    eq(taxonomy.in_scope(ad, "")[0], False, "AD sunset review kapsam disi")
    eq(taxonomy.genel_yatirim(ad), False, "ticaret davasi Katman 2'ye de girmez")
    for t in ["India imposes anti-dumping duty on galvanized sheet",
              "EU opens safeguard investigation on flat steel imports"]:
        eq(taxonomy.in_scope(t, "")[0], False, "ticaret davasi: " + t[:45])

    # 2) CELIKHANE yukari akistir; govde kapsam kuramaz.
    cliffs = "Cleveland-Cliffs Invests $1B in Steelmaking Modernization"
    eq(taxonomy.in_scope(cliffs, "The plan also covers the cold mill complex.")[0],
       False, "steelmaking basligi Hat'a giremez")
    # ...baslikta soguk taraf terimi varsa veto kalkar
    eq(taxonomy.in_scope("Steelmaking and cold rolling complex for Acme", "")[0],
       True, "baslikta soguk terim varsa veto kalkar")

    # 3) TEKNOLOJI asamasi dar: pazarlama fiili tek basina yetmez. Bir tesis
    #    acilisi ve bir ticaret davasi teknoloji kosesi havuzuna dusmustu.
    roofings = "Roofings Unveils $125m Steel Mill, Doubles Cold-Rolled Capacity to 300,000 Tonnes"
    eq(taxonomy.match_stage(roofings) != "Teknoloji", True,
       "tesis acilisi teknoloji sayilmamali")
    eq(taxonomy.match_stage(ad) != "Teknoloji", True,
       "ticaret davasi teknoloji sayilmamali")
    eq(taxonomy.match_stage("Primetals unveils new annealing technology"), "Teknoloji",
       "gercek teknoloji duyurusu Teknoloji kalmali")

    # 4) TIRE. Sozluklerdeki cok kelimeli kaliplar bosluklu yazilmisti;
    #    Ingilizce baslik tireleyince hicbiri tutmuyordu.
    eq(taxonomy.match_line(roofings), "Soguk hadde", "cold-rolled hat tipi")
    eq(taxonomy.match_line("Tosyali orders hot-dip galvanizing line"),
       "Galvaniz hatti (CGL)", "hot-dip hat tipi")
    eq(taxonomy.match_line("New temper-mill for Acme"), "Temper / skin pass",
       "temper-mill hat tipi")
    eq(taxonomy.match_line("CPL-TCM hatti devreye alindi"),
       "Tandem soguk hadde (TCM)", "yalin tireli kalip korunmali")

    # 5) CINCE hat terimi. Kosunun gercek satiri:
    cn = "\u4e09\u5b9d\u96c6\u56e2SACL3#\u65b0\u80fd\u6e90\u9ad8\u724c\u53f7" \
         "\u65e0\u53d6\u5411\u7845\u94a2\u9000\u706b\u7089\u987a\u5229\u6295\u4ea7"
    eq(taxonomy.in_scope(cn, "")[0], True, "Cince elektrik celigi kapsam ici")
    eq(taxonomy.match_line(cn), "Elektrik celigi hatti", "Cince hat tipi cozulmeli")
    eq(taxonomy.match_stage(cn), "Ilk urun", "Cince asama cozulmeli")

    # 6) Koşunun DOGRU satiri bozulmamali
    jsw = "JSW Steel, India, orders ANDRITZ galvanizing line for advanced automotive steel"
    eq(taxonomy.in_scope(jsw, "")[0], True, "JSW satiri kapsam ici")
    eq(taxonomy.match_line(jsw), "Galvaniz hatti (CGL)", "JSW hat tipi")
    eq(taxonomy.match_stage(jsw), "Sozlesme", "JSW asamasi")


def test_rezerv_ve_teknoloji_havuzu():
    """v14 (2026-08-27): hacim hedefi 7-8 satir + her hafta 1 teknoloji.

    Olcum: taze kapsam ici arz haftada ~1-3 haber. Hedefi kapiyi gevseterek
    tutturmak 2026-W35'te denendi ve bulteni yukari akisla doldurdu. Dogru
    yol REZERV: gecmis kosularda kapiyi gecmis, tarihi SAYFADAN dogrulanmis
    ama pencere disinda kaldigi icin hic gonderilmemis satirlar.

    Vakalar gercek: son kosuda elenen 30 kapsam ici satirin 26'si sirf
    pencere disiydi; 11'i 2026 tarihliydi ve okuyucu hicbirini gormemisti.
    """
    from . import render
    from .cli import _rezerv_guncelle, _tech_havuz

    def _r(anahtar, tarih, baslik):
        return {"anahtar": anahtar, "tarih": tarih, "baslik": baslik,
                "hat": "Soguk hadde", "asama": "Ilk urun", "kategori": "Hat",
                "rezerv": True}

    havuzdaki = [
        _r("a1", "2026-07-29", "Tosyalı Algerie produces first cold rolled products at new complex"),
        _r("a2", "2026-07-29", "Eastern Steel commissions 650,000 mt temper mill in Malaysia"),
        _r("a3", "2026-04-16", "U. S. Steel Announces Plans to Restart Gary Tin Mill"),
    ]
    st = {"seen": {"a3": "2026-04-16"}, "rezerv": havuzdaki[:1]}
    kalan = _rezerv_guncelle(st, havuzdaki[1:], rows=[])
    eq([r["anahtar"] for r in kalan], ["a1", "a2"],
       "raporlanmis satir (a3) havuzdan dusmeli, kalanlar yeniden eskiye")

    # Bu koşuda listeye giren bir satir rezervden de dusmeli
    kalan2 = _rezerv_guncelle(dict(st, rezerv=havuzdaki), [],
                              rows=[{"anahtar": "a1"}])
    eq([r["anahtar"] for r in kalan2], ["a2"], "bu kosudaki satir rezervde durmaz")

    # Rezerv satiri mailde "GEC YAKALANDI" rozetiyle gorunur
    payload = {"rows": [dict(havuzdaki[1], firma="Eastern Steel", ulke="Malezya",
                             tedarikci="", tutar="", kaynak="SteelOrbis",
                             url="https://x/1")],
               "stats": {"kaynak": 133}, "unreachable": [],
               "window": ["2026-08-12", "2026-08-27"], "period": "2026-W35"}
    mail = render.email_html(payload, {}, [], 16)
    eq("GEÇ YAKALANDI" in mail, True, "rezerv satiri rozetle isaretlenmeli")

    # TEKNOLOJI HAVUZU kalicidir: taze aday cikmayan hafta bos kalmaz
    t1 = {"anahtar": "tech:1", "tarih": "2026-06-15", "baslik": "POSCO NGO"}
    t2 = {"anahtar": "tech:2", "tarih": "2026-07-28", "baslik": "Severstal CherMK"}
    st2 = {"tech_rezerv": [t1], "tech_seen": {}}
    havuz = _tech_havuz(st2, [t2])
    eq([t["anahtar"] for t in havuz], ["tech:2", "tech:1"], "havuz birikir, yeniden eskiye")
    # taze aday YOKKEN de havuz dolu kalir -> kose bos gecmez
    eq(len(_tech_havuz({"tech_rezerv": havuz, "tech_seen": {}}, [])), 2,
       "taze aday olmasa da havuz durur")
    # tanitilan madde bir daha cikmaz
    eq([t["anahtar"] for t in _tech_havuz({"tech_rezerv": havuz,
                                           "tech_seen": {"tech:2": "x"}}, [])],
       ["tech:1"], "tanitilan teknoloji havuzdan duser")


def test_rezervin_ortaya_cikardigi_delikler():
    """v15 (2026-08-27): rezerv ilk kez calisinca gorunen kapi delikleri.

    Rezerv havuzu devreye girince liste 8 satira ciktI ama BESI COPTU.
    Hepsi daha once "pencere disi" etiketiyle sessizce eleniyordu; havuz
    onlari gorunur kildi. Basliklar o koşunun gercek satirlaridir.

    Ortak mekanizma: MALZEME VETOSU baslik+GOVDE uzerinde bakiyordu ve
    govdedeki tek bir "steel" kelimesi vetoyu kaldiriyordu.
    """
    # ALUMINYUM - govdede "steel" gecince veto kalkiyordu
    alu = ("MINO awarded Phase One modernization contract for Golden Aluminum, "
           "Fort Lupton CO Tandem Cold Rolling Mill")
    govde = "MINO supplies rolling mills to the steel and aluminium industries worldwide."
    eq(taxonomy.in_scope(alu, govde)[0], False, "aluminyum basligi govdeyle kurtulamaz")
    eq(taxonomy.in_scope(alu, "")[1], "baska_malzeme", "sebep: baska malzeme")
    eq(taxonomy.in_scope("First Coil Successfully Rolled on MINO-Revamped Cold "
                         "Rolling Mill at JW Aluminium, Goose Creek", govde)[0],
       False, "JW Aluminium satiri girmemeli")
    # ...ama celik + aluminyum birlikte gecen GERCEK celik haberi girmeli
    eq(taxonomy.in_scope("ANDRITZ to supply cold rolling mill for steel and "
                         "aluminium strip", "")[0], True,
       "baslikta celik varsa aluminyum vetosu calismaz")

    # DERNEK / ETKINLIK
    eq(taxonomy.in_scope("EGGA-Galvanizing Europe Presidency: Benelux to Spain",
                         "galvanizing association news")[0], False,
       "dernek baskanligi devri haber degil")
    eq(taxonomy.in_scope("PRE Open House: Celebrating Growth, Community, and the Future",
                         "PRE serves the steel coil processing industry.")[0], False,
       "acik kapi gunu haber degil")

    # BORU - ama "radiant tube" gercek bir tavlama bileseni, bozulmamali
    eq(taxonomy.in_scope("Marion Die & Fixture Bender: Precision Forming for "
                         "Drainage Tubing", "The line processes steel strip.")[0],
       False, "boru urunu kapsam disi")
    eq(taxonomy.in_scope("Ebner supplies radiant tube furnace for annealing line",
                         "")[0], True, "radiant tube bozulmamali")

    # TEKNOLOJI KOSESI ADAY KAPISI satir asamasindan BAGIMSIZ. Asama kapisi
    # daraltilinca (v13) kose havuzu 0'a dusmustu.
    for t in ["POSCO Partners with Hyundai Motor and 8 Organizations to Develop "
              "Next-Generation High-Efficiency Electrical Steel for EVs",
              "Severstal develops digital installation technology for CherMK galvanizing line",
              "ANDRITZ Schuler Develops Innovative Laser Technology for Cut-to-Length Lines"]:
        eq(bool(taxonomy.TECH_ADAY.search(taxonomy.fold(t))), True,
           "kose adayi olmali: " + t[:45])
    for t in ["Roofings Unveils $125m Steel Mill, Doubles Cold-Rolled Capacity",
              "Pakistan launches AD sunset review on cold rolled steel imports"]:
        eq(bool(taxonomy.TECH_ADAY.search(taxonomy.fold(t))), False,
           "kose adayi OLMAMALI: " + t[:45])

    # Gercek satirlar korunmali
    for t in ["TOSYALI ALGERIE, SOGUK HADDELEME KOMPLEKSINDE ILK URETIMI YAPTI",
              "tk accelis announces milestone at Stuttgart steel service center"]:
        eq(taxonomy.in_scope(t, "")[0], True, "gercek satir korunmali: " + t[:45])


def test_gunluk_tarama_modu():
    """v17 (2026-08-27): gunluk tarama havuzu besler, postaya dokunmaz.

    Haftalik kosu tek basina yetmiyordu: yayincilar haberi gec indeksliyor,
    kaynak gun icinde 403 verip ertesi gun aciliyor ve 15 gunluk pencere
    kapaninca haber BIR DAHA yakalanmiyordu. Olcum: son haftalik kosuda
    elenen 30 kapsam ici satirin 26'si sirf pencere disiydi.

    Gunluk tarama bunu kapiyi GEVSETMEDEN cozer - satir sayisi kaynak
    tarafindan yukselir, filtre ayni kalir.
    """
    import inspect as _i
    from . import cli as C
    kaynak = _i.getsource(C.cmd_run)

    # --sadece-tarama posta govdesine DOKUNMAMALI
    i_tarama = kaynak.index("if a.sadece_tarama:")
    i_mail = kaynak.index('render.email_html')
    eq(i_tarama < i_mail, True, "sadece-tarama posta uretiminden ONCE donmeli")

    # ...ama havuz kaydi erken donusten ONCE olmali, yoksa gunluk kosu
    # hicbir sey biriktirmez (ilk yazimda tam olarak bu hata yapildi).
    i_commit = kaynak.index("if a.commit_state:")
    eq(i_commit < i_tarama, True, "havuz kaydi erken donusten once olmali")
    i_tech = kaynak.index("_tech_havuz(st_r")
    eq(i_tech < i_tarama, True, "teknoloji havuzu da erken donusten once")

    # Tarama hicbir kosulda "gonderildi" isareti koymamali
    eq('st["seen"][' in kaynak, False, "tarama seen'e yazmamali")
    eq('st["tech_seen"]' in kaynak, False, "tarama tech_seen'e yazmamali")

    # Gunluk is akisi posta gondermemeli
    import os as _os
    yol = _os.path.join(_os.path.dirname(_os.path.dirname(
        _os.path.abspath(__file__))), ".github", "workflows", "gunluk.yml")
    if _os.path.exists(yol):
        y = open(yol, encoding="utf-8").read()
        eq("--sadece-tarama" in y, True, "gunluk kosu --sadece-tarama kullanmali")
        eq("send-mail" in y or "ONAY" in y, False, "gunluk kosu posta gondermemeli")


def test_rezerv_tekrar_denetimi():
    """v18 (2026-08-27): rezervden secim de tekrar denetiminden gecer.

    Ilk surum havuzun basindan "eksik" kadar satiri DOGRUDAN aliyordu; taze
    satirlarda calisan uc bacakli tekrar savunmasi rezervde hic calismiyordu.
    Ilk gunluk taramada iki tekrar birden listeye girdi - ikisi de gercek:

      ayni olay, iki yayin, farkli hat vurgusu:
        "KG Steel selects Primetals for Dangjin PLTCM upgrade"  (SteelOrbis)
        "Primetals to modernise Korean pickling line"           (STI)
      W34'te ZATEN GONDERILMIS haberin baska yayindaki varyanti:
        "tk accelis Processing Europe expands Stuttgart steel service center"
    """
    from .cli import _rezervden_sec

    def _r(a, tarih, baslik, ted="", ulke="", asama="Modernizasyon", olaylar=()):
        return {"anahtar": a, "tarih": tarih, "baslik": baslik, "tedarikci": ted,
                "ulke": ulke, "asama": asama, "olaylar": list(olaylar),
                "hat": "Soguk hadde", "kategori": "Hat", "rezerv": True}

    _bugun = (dt.date.today() - dt.timedelta(days=12)).isoformat()
    kg = _r("k1", _bugun,
            "KG Steel selects Primetals for Dangjin PLTCM upgrade and capacity expansion",
            ted="Primetals", olaylar=["primetals|hat|Tandem soguk hadde (TCM)|Modernizasyon"])
    sti = _r("k2", _bugun, "Primetals to modernise Korean pickling line",
             ted="Primetals", ulke="G. Kore",
             olaylar=["primetals|ulke|G. Kore|Modernizasyon"])
    # Ayni tedarikci + ayni asama + AYNI GUN -> ayni olay. Ulke bir yayinda
    # bos oldugu icin ulke tek basina yetmiyor.
    sec = _rezervden_sec([kg, sti], rows=[], st={}, eksik=8)
    eq(len(sec), 1, "ayni olayin iki varyantindan biri alinmali")

    # Farkli GUN ve farkli ULKE ise iki ayri is: ikisi de alinir.
    # NOT: tarih BUGUNE GORE hesaplanir. 2026-08-31'de "rezervden bultene
    # girebilecek en eski haber" kurali kondu; sabit tarihli vaka zamanla
    # kendiliginden eskiyip testi kirardi - nitekim 2026-06-02 yazilmisti.
    baska = _r("k3", (dt.date.today() - dt.timedelta(days=20)).isoformat(),
               "Primetals to modernise Indian pickling line",
               ted="Primetals", ulke="Hindistan")
    eq(len(_rezervden_sec([kg, baska], rows=[], st={}, eksik=8)), 2,
       "farkli gun+ulke iki ayri is sayilmali")

    # GECMISTE GONDERILMIS haberin varyanti alinmamali
    gecmis = {"son_basliklar": [
        {"b": "tk accelis announces milestone at Stuttgart steel service center",
         "t": (dt.date.today() - dt.timedelta(days=10)).isoformat(),
         "a": "Ilk urun"}]}
    yieh = _r("k4", (dt.date.today() - dt.timedelta(days=8)).isoformat(),
              "tk accelis Processing Europe expands Stuttgart steel service center capacity",
              asama="Ilk urun")
    eq(_rezervden_sec([yieh], rows=[], st=gecmis, eksik=8), [],
       "gonderilmis haberin baska yayindaki varyanti girmemeli")

    # Bu koşuda ZATEN listede olan satirin varyanti da girmemeli
    eq(_rezervden_sec([yieh], rows=[{
        "baslik": "tk accelis announces milestone at Stuttgart steel service center",
        "asama": "Ilk urun", "olaylar": []}], st={}, eksik=8), [],
       "listedeki satirin varyanti girmemeli")

    # eksik=0 ise hicbir sey alinmaz
    eq(_rezervden_sec([kg], rows=[], st={}, eksik=0), [], "eksik yoksa alinmaz")


def test_v20_sitemap_geri_dusus():
    """v20 (2026-08-29): kaynagin KENDI adresi once, sitemap zinciri sonra.

    v19'da 14 kaynaga sitemap ZINCIRI ekledim ve zincir kaynagin kendi
    adresinin ONUNE gecti. Zincirdeki adresler TAHMIN; bir kismi 404 dondu
    ve erisilemeyen kaynak sayisi 10'dan 16'ya cikti.

    Ilk duzeltmede yalnizca GERI DUSUS ekledim - yetmedi. Olcum (2026-08-29
    kosusu, v19 oncesiyle karsilastirmali):
      zincirin KAZANDIRDIGI : GMK Center, Mysteel
      zincirin KAYBETTIRDIGI: ABB Metals, Nippon Steel, China Baowu,
                              SteelGuru, Kocks
    Bes kaynak da v19 oncesinde ACILIYORDU ve kendi adresleri degismemisti.
    Sebep zincirin kendisi: gercek istekten hemen once ayni sunucuya 1-4
    basarisiz istek gidiyor, site bunu bot davranisi sayip kapiyi kapatiyor.
    Bu yuzden sira TERSINE cevrildi - tahmin, kaynagin kendi adresi is
    gormediginde devreye girer.

    Ikinci kusur: zincirin hatasi kaynagin hatasini golgeliyordu. Kendi
    adresi ACILIP da liste bos donduyse kaynak ERISILEMEZ DEGILDIR; zincirin
    "sitemap bos" hatasi bu duruma yazilinca China Baowu ile SteelGuru
    erisilemeyen listesine yanlis girdi.
    """
    from . import collect as C
    kaynak = os.path.join(os.path.dirname(__file__), "collect.py")
    src = open(kaynak, encoding="utf-8").read()
    eq(hasattr(C, "_items_from_web"), True,
       "normal yol ayri fonksiyona alinmali ki geri dusus mumkun olsun")

    cagrilar = []

    def sahte_zincir(s, log):
        cagrilar.append("zincir")
        return [], "HTTP 404"

    def sahte_web(s, log):
        cagrilar.append("web:" + (s.get("rss") or s["url"]))
        return [{"title": "Cold rolling mill complex for SSAB in Lulea Sweden",
                 "url": "https://x/y", "date_raw": "", "summary": ""}], None

    eski_z, eski_w = C._sitemap_zinciri, C._items_from_web
    s = {"url": "https://new.abb.com/metals", "publisher": "ABB Metals",
         "sitemaps": ["https://new.abb.com/sitemap.xml"]}
    try:
        C._sitemap_zinciri, C._items_from_web = sahte_zincir, sahte_web
        items, err = C._items_from_source(s, lambda *a: None)
        eq(len(items), 1, "kaynagin kendi adresi is goruyorsa satir gelmeli")
        eq(err, None, "calisan kaynak icin hata bildirilmemeli")
        eq(cagrilar, ["web:https://new.abb.com/metals"],
           "KENDI ADRESI ONCE - zincir hic denenmemeli, cunku zincirin "
           "basarisiz istekleri sunucuyu kapatiyor")

        # Kendi adresi tutmazsa zincir devreye girer
        del cagrilar[:]
        C._items_from_web = lambda s, log: ([], "HTTP 404")
        C._sitemap_zinciri = lambda s, log: (cagrilar.append("zincir") or
                                             ([{"title": "x y z w", "url": "u",
                                                "date_raw": "", "summary": ""}], None))
        items, err = C._items_from_source(s, lambda *a: None)
        eq(len(items), 1, "kendi adresi tutmazsa zincir devreye girmeli")
        eq(cagrilar, ["zincir"], "zincir yalnizca ikinci sirada denenmeli")

        # KENDI ADRESI ACILIP LISTE BOS ise kaynak ERISILEMEZ DEGILDIR
        C._items_from_web = lambda s, log: ([], None)
        C._sitemap_zinciri = lambda s, log: ([], "sitemap bos")
        items, err = C._items_from_source(s, lambda *a: None)
        eq(items, [], "iki yol da satir vermedi")
        eq(err, None,
           "sayfa acilip liste bos donduyse zincirin hatasi rapor edilemez")

        # Kendi adresi GERCEKTEN tutmadiysa hata bildirilir
        C._items_from_web = lambda s, log: ([], "HTTP 403")
        items, err = C._items_from_source(s, lambda *a: None)
        eq(err, "HTTP 403", "kaynagin kendi hatasi bildirilmeli")
    finally:
        C._sitemap_zinciri, C._items_from_web = eski_z, eski_w


def test_v20_gonderilmis_hafiza():
    """v20 (2026-08-29): gonderilmis satir hafizasinin uc kusuru.

    2026-08-29 gunluk taramasi rezervden dort satir cikardi ve ikisi
    tekrardi. Sebep state'te goruldu - son_basliklar 11 kayitti ama
    yalnizca 6 farkli baslik tasiyordu:

    (1) finalize ayni hafta icin iki kez calisinca ayni basligi ikinci kez
        ekliyordu (tekrar denetimi yoktu);
    (2) budama 21 gunluktu, oysa REZERV 540 gun geriye uzaniyor - W34'te
        GONDERILEN "tk accelis" satiri hafizadan dusmustu ve ayni haberin
        Yieh varyanti rezervden geri geldi;
    (3) kayitta tedarikci/ulke yoktu, bu yuzden "ayni tedarikci + ayni asama
        + (ayni ulke ya da ayni gun)" imzasi GONDERILMIS satirlara karsi hic
        isletilemiyordu - W35'te giden KG Steel/Primetals olayinin STI
        varyanti ("Primetals to modernise Korean pickling line") boyle
        gecti.
    """
    from .cli import _rezervden_sec

    # (1) yazma tarafi: ayni baslik iki kez yazilamaz, bos alan dolar
    d = state.dedup_basliklar([
        {"b": "Fives supplies technologies for Xinyu's new electrical steel facility",
         "t": "2026-08-28", "a": "Sozlesme", "ted": "Fives", "u": ""},
        {"b": "Fives supplies technologies for Xinyu's new electrical steel facility",
         "t": "2026-08-28", "a": "Sozlesme", "ted": "Fives", "u": "Çin"}])
    eq(len(d), 1, "ayni baslik hafizada iki kez durmamali")
    eq(d[0]["u"], "Çin", "tekrar kayitta dolu olan alan korunmali")

    # (2) budama: 21 gunden eski ama rezerv penceresi icindeki kayit KALIR
    st = {"son_basliklar": [
        {"b": "tk accelis announces milestone at Stuttgart steel service center",
         "t": (dt.date.today() - dt.timedelta(days=90)).isoformat(),
         "a": "Ilk urun", "ted": "", "u": ""}],
        "seen": {}, "events": {}, "rezerv": [], "tech_rezerv": []}
    state.prune(st)
    eq(len(st["son_basliklar"]), 1,
       "rezerv 540 gun geriye bakarken hafiza 21 gunde silinemez")

    # (3) imza gonderilmis satirlara karsi da isler
    gecmis = {"son_basliklar": [
        {"b": "KG Steel selects Primetals for Dangjin PLTCM upgrade and capacity expansion",
         "t": (dt.date.today() - dt.timedelta(days=12)).isoformat(),
         "a": "Modernizasyon", "ted": "Primetals", "u": "G. Kore"}]}
    _t = (dt.date.today() - dt.timedelta(days=12)).isoformat()
    sti = {"anahtar": "k2", "tarih": _t,
           "baslik": "Primetals to modernise Korean pickling line",
           "tedarikci": "Primetals", "ulke": "G. Kore", "asama": "Modernizasyon",
           "olaylar": ["primetals|ulke|G. Kore|Modernizasyon"],
           "hat": "Asitleme hatti", "kategori": "Hat", "rezerv": True}
    eq(_rezervden_sec([sti], rows=[], st=gecmis, eksik=8), [],
       "gonderilmis olayin varyanti rezervden geri donmemeli")

    # Ayni tedarikcinin BASKA ulkedeki, baska gundeki isi hala gecerli haber
    # NOT: tarih bugune gore. Sabit 2026-05-02 yazilmisti ve "rezervden
    # bultene girebilecek en eski haber" kurali konunca kendiliginden
    # eskiyip testi kirdi.
    baska = dict(sti, anahtar="k3",
                 tarih=(dt.date.today() - dt.timedelta(days=25)).isoformat(),
                 ulke="Hindistan",
                 baslik="Primetals to modernise Indian pickling line", olaylar=[])
    eq(len(_rezervden_sec([baska], rows=[], st=gecmis, eksik=8)), 1,
       "farkli ulke+gun ayri istir, elenmemeli")


def test_v20_gunluk_tarama_arsivi_ezmez():
    """v20 (2026-08-29): gunluk tarama gonderilen bultenin kaydini ezemez.

    Tarama modu email.html'e dokunmuyordu ama satir arsivini hala hafta
    adiyla yaziyordu. 2026-08-29 taramasi, gonderilen 6 satirlik W35
    bulteninin kaydini rezervden gelen 4 satirla EZDI; ne gonderildigini
    ancak git gecmisinden cikarabildim.
    """
    src = open(os.path.join(os.path.dirname(__file__), "cli.py"),
               encoding="utf-8").read()
    g = src[src.index("def cmd_run("):src.index("def cmd_finalize(")]
    eq('_w(base + ".json", payload)' not in g, True,
       "tarama modunda haftalik arsive yazilmamali")
    eq('cikti = os.path.join(OUT, "tarama") if a.sadece_tarama else base' in g, True,
       "tarama ciktisi ayri dosyaya gitmeli")
    eq('"tarama_needs_ai.json" if a.sadece_tarama' in g, True,
       "needs_ai de tarama modunda ayri dosyaya gitmeli")


def test_v20_indiana_hindistan_degil():
    """v20 (2026-08-29): \\bindia sinirsizken INDIANA'yi yakaliyordu.

    Rezervden gelen gercek satir yanlis etiketle cikti:
      "U. S. Steel Announces Plans to Restart Gary Tin Mill" -> Hindistan
    Gary, INDIANA. Ustelik "U. S. Steel" foldlaninca "u. s. steel" oluyor,
    ABD deseni ise noktadan sonra bosluk beklemedigi icin tutmuyordu; yani
    dogru ulke de bulunamiyordu. "Province" icinde eslesen "vinc" hatasinin
    ayni ailesi.
    """
    import re as _re

    def ulke(t):
        b = taxonomy.fold(t)
        for pat, u in taxonomy.COUNTRY_MAP:
            if _re.search(pat, b):
                return u
        return ""

    eq(ulke("U. S. Steel Announces Plans to Restart Gary Tin Mill"), "ABD",
       "Gary Indiana ABD'dir")
    eq(ulke("Nucor to add a cold mill in Indiana"), "ABD", "Indiana ABD")
    # Gercek Hindistan haberleri bozulmamali
    eq(ulke("India's Jindal Stainless Limited to invest $94 million to ramp up "
            "cold rolling capacity"), "Hindistan", "India hala Hindistan")
    eq(ulke("JSW Steel, India, orders ANDRITZ galvanizing line"), "Hindistan",
       "India hala Hindistan")
    eq(ulke("Indian mill starts up new pickling line"), "Hindistan",
       "Indian hala Hindistan")
    # crore/lakh Hindistan'a ozgu sayi birimi; baslikta ulke adi hic
    # gecmeyen Hint haberinde tek sinyal olabiliyor (2026-08-29 taramasi)
    eq(ulke("Jindal Stainless investing Rs 900 crore to increase cold "
            "rolling capacity"), "Hindistan", "crore Hindistan sinyalidir")


def test_w36_girisim_turu_hat_haberi_degil():
    """2026-09-01: tohum/seri yatirim turu bir hat gelismesi degildir.

    Temizlik sonrasi kosuda su satir Hat katmanina girdi:
      "Ex-SpaceX engineers open robotic steel factory in Cincinnati on
       $15 million seed"
    Sebep: "robot" ZAYIF kapsam terimi olarak HAT OTOMASYONU icin
    konmustu ve "steel" baglami yetti. Oysa haber bir girisimin tohum
    yatirimi; ortada yassi isleme hatti yok.

    Kalip DAR: gercek hat yatirimlari ("to invest $59 million in cold
    rolling capacity") korunur - ayirt eden sey PARA degil, paranin
    NEYE gittigidir.
    """
    for t in ("Ex-SpaceX engineers open robotic steel factory in Cincinnati "
              "on $15 million seed",
              "Steel tech startup raises $20 million in Series B funding"):
        eq(taxonomy.in_scope(t)[0], False, "girisim turu Hat degil: " + t[:46])
        eq(bool(taxonomy.genel_yatirim(t)), False,
           "girisim turu Katman 2'ye de girmemeli: " + t[:46])

    # GERCEK HAT YATIRIMLARI KORUNMALI
    for t in ("Nucor to invest $59 million in cold rolling capacity",
              "Roofings Unveils $125m Steel Mill, Doubles Cold-Rolled "
              "Capacity to 300000 Tonnes",
              "John Cockerill Signs Contract with A1 Iron & Steel for "
              "Integrated Cold Rolling Complex",
              "ArcelorMittal approves Tubarao flat steel expansion",
              "KG Steel selects Primetals for Dangjin PLTCM upgrade and "
              "capacity expansion"):
        eq(taxonomy.in_scope(t)[0], True, "gercek hat haberi: " + t[:46])
    # ...Katman 2'den gecen gercek yatirim da korunur
    eq(bool(taxonomy.genel_yatirim(
        "India's Manaksia Steel to invest $84 million to expand "
        "value-added flats capacities")), True,
        "yassi kapasite yatirimi Katman 2'de kalmali")


def test_w36_ocak_parcasi_tavlama_firini_degildir():
    """2026-09-01: "furnace roof" tavlama firini degil ARK OCAGI catisidir.

    Uc haftalik pencerenin ilk kosusunda su satir Hat katmanina girdi:
      "Primetals to supply furnace roof to British Steel"
    Sebep: "furnace" ZAYIF kapsam terimi olarak tavlama firini icin
    konmustu ve baslikta "steel" gecince celik baglami da saglaniyordu.
    Oysa ocak catisi celikhane parcasidir - kapsam sicak hadde SONRASI.

    Kalip DAR: tavlama, galvaniz hatti ve isleme hatti firinlari kapsam ici
    kalir ve burada tek tek bekcilenir. Ayirt eden sey "firin" kelimesi
    degil, HANGI firin oldugudur.
    """
    for t in ("Primetals to supply furnace roof to British Steel",
              "New electric arc furnace for Salzgitter",
              "Danieli to supply ladle furnace and electrode arms"):
        eq(taxonomy.in_scope(t)[0], False, "ocak parcasi kapsam disi: " + t[:46])

    for t in ("Fives to supply Baosteel with two new processing line furnaces",
              "Successful thermal performance at NLMK Strasbourg galvanizing "
              "line furnace",
              "CERI Technology Company awards annealing furnace contract to "
              "ANDRITZ",
              "ANDRITZ to supply combi-line furnace to Borcelik, Turkiye",
              "Sanbao Group SACL 3 annealing furnace for non-oriented silicon "
              "steel commissioned",
              "High convection chamber-type furnaces for the annealing of "
              "strip coils"):
        eq(taxonomy.in_scope(t)[0], True, "hat firini kapsam ici: " + t[:46])


def test_w36_pencere_uc_hafta():
    """2026-08-31 (kullanici karari): pencere 15 gun -> 21 gun (UC HAFTA).

    Once 7, sonra 15 gundu. Olcum: 6,5 aylik gecmiste kapsam ici haber
    haftada 0,83 ve haftalarin %40'i SIFIR; kaynak 403 verdiginde ya da
    tarih gec cozuldugunde dar pencerede haber BIR DAHA yakalanmiyordu.

    Gecmis kosularin "pencere_disi" kayitlari uzerinde olculdu: 15-21 gun
    arasinda, kapiyi GECEN dort benzersiz baslik var -
      "Primetals to modernise Korean pickling line"          (11.08)
      "KG Steel selects Primetals for Dangjin PLTCM upgrade"  (11.08)
      "US Steel Targets 2027 Restart of Ind. Tin Mill"        (14.08)
      "Jindal Stainless investing Rs 900 cr ... cold rolling" (15.08)

    TEKRAR RISKI YOK: pencerenin genisligi tekrar URETMEZ, yalnizca
    KACIRMAYI azaltir. Ayni haber uc bacakli savunmadan geciyor - seen,
    olay parmak izi, baslik benzerligi. Nitekim yukaridaki dordunun ucu
    zaten gonderilmis haberlerin varyanti ve dedup onlari eliyor.

    Bu test AYARIN KENDISINI bekciler: is akislari ile config'in ayni
    degeri soylemesi gerekir, yoksa gunluk ve haftalik kosu farkli
    pencerelerde calisir ve rezerv/bulunan havuzlari tutarsiz dolar.
    """
    import re as _re
    from .config import WINDOW_DAYS

    eq(WINDOW_DAYS, 21, "varsayilan pencere uc hafta olmali")

    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ak = os.path.join(kok, ".github", "workflows")
    bulunan = 0
    for dosya in ("weekly.yml", "gunluk.yml", "dogrula.yml"):
        yol = os.path.join(ak, dosya)
        if not os.path.exists(yol):
            continue
        icerik = open(yol, encoding="utf-8").read()
        for d in _re.findall(r'RADAR_WINDOW_DAYS:\s*"(\d+)"', icerik):
            bulunan += 1
            eq(d, "21", "%s pencereyi config ile ayni tutmali" % dosya)
    eq(bulunan >= 3, True, "is akislarinda pencere ayari bulunmali")

    # Tekrar savunmasinin ucuncu bacagi pencereyle AYNI uzunlukta olmali:
    # daha kisa olursa pencerenin geri getirdigi haber tekrar denetimsiz
    # kalir.
    csrc = open(os.path.join(os.path.dirname(__file__), "collect.py"),
                encoding="utf-8").read()
    eq("sb_floor = (today - dt.timedelta(days=21)).isoformat()" in csrc, True,
       "baslik benzerligi bacagi da uc hafta olmali")


def test_w36_kose_kendi_kapisi_ve_turkiye_katmani():
    """2026-08-31 (kullanici: "sayi ve icerik yine yetersiz").

    HUNI OLCULDU ve kapinin YANLIS eleme yapmadigi gorundu: reddedilenlerin
    icerigi urun katalogu sayfalari, kurumsal duyurular, bagis haberleri,
    konferanslar ve yukari akis (DRI, sicak hadde). Gizli bir kapsam ici
    haber yigini YOK. Yani sayi kapiyla degil ARZLA sinirli.

    Icerik iki yerde eksikti ve ikisi de kapsam ICI:

    A) TEKNOLOJI KOSESI IKI HAFTADIR BOS. Sebeplerden biri arz, digeri
       KAPI: in_scope hat ISMI ariyor ("annealing line"), oysa kosenin
       konusu hattin kendisi degil PROSES TEKNOLOJISIDIR. Gercek basliklar
       bu yuzden dusuyordu:
         "SMS group I-Furnace intelligent annealing process model"
         "John Cockerill unveils jet vapor deposition coating technology"
       Ayrica kalip modern teknoloji sozlugunu hic tanimiyordu (digital
       twin, AI-based, machine vision, process model).
       Kose kendi kapsam kapisini aldi. HABER KAPISI DEGISMEDI.

    B) OKUYUCU TURK ama 2026-W36'da Turkiye ile ilgili TEK satir yoktu.
       Kaynak listesinde Erdemir ve Tosyali var; Borcelik, MMK Metalurji,
       Colakoglu, Yildiz Demir Celik, Tezcan Galvaniz, Habas YOK.
       site: hedefi burada ise yaramaz - Google News YAYINCILARI
       indeksler, sirketlerin kurumsal sayfalarini degil; sirketler icin
       dogru yol ADLARINI aramaktir.
    """
    from . import sources as S

    # --- A) Kose kapisi: proses teknolojisi hat ismi olmadan da girer
    for t in ("SMS group I-Furnace intelligent annealing process model",
              "John Cockerill unveils jet vapor deposition coating "
              "technology for steel strip",
              "Danieli introduces digital twin for cold rolling mill automation",
              "AI-based surface inspection for galvanized strip",
              "Primetals Technologies develops new process model for "
              "continuous annealing lines"):
        eq(taxonomy.tech_kapsam(t), True, "kose adayi olmali: " + t[:46])
        eq(bool(taxonomy.TECH_ADAY.search(taxonomy.fold(t))), True,
           "teknoloji kalibi tutmali: " + t[:46])

    # IKI KAPI AYRIDIR ve ikisi de gerekir. Olcum kalibi olan ama TEKNOLOJI
    # HABERI olmayan urun katalogu sayfasi kapsami gecer, aday kapisini
    # GECMEZ - kose haber tanitir, katalog maddesi degil.
    katalog = ("XR SMC multichannel thickness profile measuring system with "
               "integrated surcon 2D surface inspection")
    eq(taxonomy.tech_kapsam(katalog), True, "olcum sistemi kapsam icidir")
    eq(bool(taxonomy.TECH_ADAY.search(taxonomy.fold(katalog))), False,
       "katalog sayfasi teknoloji HABERI degildir")

    # KOSEYE DE GIRMEYECEKLER - vetolar aynen isler
    for t in ("Nippon Steel commissions new hot rolling line in Nagoya",
              "New DRI plant technology from Energiron",
              "MINO develops new cold rolling mill for Golden Aluminum",
              "Galva Hub to commission Emirates largest galvanizing kettle",
              "thyssenkrupp Steel Supervisory Board appoints new COO"):
        eq(taxonomy.tech_kapsam(t), False, "kose disi olmali: " + t[:46])

    # YUKARI AKIS VETOSUNU YALNIZ ASAGI AKIS HATTI KALDIRIR. Olcum:
    # "surface inspection" guclu terimdir ve in_scope'ta vetoyu kaldirir;
    # kosede kaldirmamali cunku muayene sistemi her iki tarafta da var.
    sicak = ("Experience Report: How SDI Butler enhances quality control in "
             "hot rolling mill through the implementation of surcon 2D "
             "surface inspection system")
    eq(taxonomy.tech_kapsam(sicak), False,
       "sicak haddehanedeki muayene sistemi koseye girmemeli")
    eq(taxonomy.tech_kapsam(
        "First Combined surcon 2D and 3D Surface Inspection in a Pickling Line"),
       True, "asitleme hattindaki AYNI sistem kose adayidir")

    # --- B) Turk yassi celik ureticileri aranmali
    tr = [x for x in S.SOURCES if x["id"].startswith("gtr_")]
    eq(len(tr) >= 6, True, "Turk uretici sorgulari olmali")
    hepsi = " ".join(x["rss"] for x in tr)
    import urllib.parse as _up
    for ad in ("Borçelik", "MMK Metalurji", "Çolakoğlu", "Tezcan"):
        eq(_up.quote(ad) in hepsi or _up.quote('"%s"' % ad) in hepsi, True,
           "Turk uretici aranmali: " + ad)
    eq(all("ceid=TR:tr" in x["rss"] for x in tr), True,
       "Turk sorgulari Turkce katmandan sorulmali")
    # Aynalari da olmali
    eq(len([x for x in S.SOURCES if x["id"].startswith("bgtr_")]), len(tr),
       "Turk sorgularinin da Bing aynasi olmali")


def test_w36_rezerv_kalici_hafizayi_sorar():
    """2026-08-31: rezervden secim KALICI olay hafizasini hic sormuyordu.

    Taze satirlar collect icinde state["events"]'e karsi denetleniyor;
    rezervden secim ise yalnizca BU KOSUNUN satirlarina bakiyordu. Sonuc
    olculdu - 2026-W36 kosusunda su satir listeye girdi:
      gonderilen (W35): "Roofings Unveils $125m Steel Mill, Doubles
                         Cold-Rolled Capacity to 300,000 Tonnes"  (Uganda)
      rezervden gelen : "RRM starts up new cold-mill complex with Danieli
                         technology"
    RRM = Roofings Rolling Mills; AYNI Uganda soguk hadde kompleksi, baska
    yayin, baska kisaltma. Ustelik satirin ulkesi "Turkiye" okunmustu, yani
    ulke bacagi da korlesmisti - ama TEDARIKCI+HAT+ASAMA bacagi hafizada
    duruyordu ve sorulsaydi yakalanacakti.

    NOT: izleri yeniden URETMEK cozum DEGIL - denendi ve gercek haber
    kaybettirdi. event_keys'in "kim|hat|..." bacagi ULKESIZDIR; tedarikci
    ayni olunca "Primetals to modernise Korean pickling line" ile
    "Primetals to modernise Indian pickling line" birlesiyor. Cozum
    havuzdaki mevcut izleri KALICI HAFIZAYA karsi sormaktir.
    """
    from .cli import _rezervden_sec

    def _r(a, tarih, baslik, ted="", ulke="", asama="Ilk urun", hat="Soguk hadde"):
        return {"anahtar": a, "tarih": tarih, "baslik": baslik, "tedarikci": ted,
                "ulke": ulke, "asama": asama, "hat": hat, "kategori": "Hat",
                "olaylar": [], "rezerv": True}

    rrm = _r("r1", "2026-02-12",
             "RRM starts up new cold-mill complex with Danieli technology",
             ted="Danieli", ulke="Turkiye")
    rrm["olaylar"] = ["danieli|hat|Soguk hadde|Ilk urun",
                      "danieli|ulke|Turkiye|Ilk urun"]
    hafiza = {"events": {"danieli|hat|Soguk hadde|Ilk urun": "2026-08-25",
                         "danieli|ulke|Uganda|Ilk urun": "2026-08-25"},
              "son_basliklar": []}
    eq(_rezervden_sec([rrm], rows=[], st=hafiza, eksik=6), [],
       "kalici hafizadaki olayin varyanti rezervden gelemez")

    # Hafizada olmayan satir GECER - temizlik cop toplar, haber degil.
    # NOT: tarih BUGUNE GORE hesaplanir. Sabit tarih yazilamaz cunku
    # 2026-08-31'de "rezervden bultene girebilecek en eski haber 60 gun"
    # kurali kondu ve sabit tarihli vaka zamanla kendiliginden eskiyip
    # testi kirardi - nitekim ilk yazimda 2026-05-20 kullanilmisti.
    _yeni_tarih = (dt.date.today() - dt.timedelta(days=10)).isoformat()
    yeni_satir = _r("r2", _yeni_tarih,
                    "India's JIL commissions continuous color coating line",
                    ulke="Hindistan", hat="Boyama hatti (CCL)")
    yeni_satir["olaylar"] = ["|hat|Boyama hatti (CCL)|Ilk urun"]
    eq(len(_rezervden_sec([yeni_satir], rows=[], st=hafiza, eksik=6)), 1,
       "hafizada olmayan gercek satir gecmeli")

    # ESKI HABER BULTENE GIREMEZ (2026-08-31, kullanici: "eski haberleri
    # tekrar tekrar cikartmasin"). Rezerv 540 gun SAKLAR - ama saklamak ile
    # bultene koymak ayni sey degil. 2026-W36 listesi Mart (MINO), Mayis
    # (JIL) ve Temmuz (Marcegaglia) tarihli satirlarla dolduruldu; "GEC
    # YAKALANDI" rozeti tasisalar da okuyucu icin bu haftalik bulten degil
    # arsiv taramasi olur.
    #
    # Ayrim: saklama TEKRAR SAVUNMASI icindir (eski haberin varyanti bir
    # daha giremesin); bultene KOYMA hakki REZERV_KULLANIM_GUN ile sinirli.
    # Boylece eski haber ne tekrar eder ne de yeniden yayinlanir.
    from .config import REZERV_KULLANIM_GUN, REZERV_DAR_GUN, REZERV_ESIK
    gun = lambda n: (dt.date.today() - dt.timedelta(days=n)).isoformat()
    mino = lambda a, n: _r(a, gun(n),
                           "New MINO Double-Stand Six-High Cold Reversing "
                           "Mill in North America", ulke="ABD", hat="Soguk hadde")

    # LISTE BOS (5'ten az) -> 3 aya kadar geriye gidilir
    eq(len(_rezervden_sec([mino("r3", REZERV_KULLANIM_GUN - 10)],
                          rows=[], st={}, eksik=6)), 1,
       "liste zayifken 3 aylik veriye erisilmeli")
    eq(_rezervden_sec([mino("r4", REZERV_KULLANIM_GUN + 30)],
                      rows=[], st={}, eksik=6), [],
       "3 aydan eski haber hicbir kosulda bultene girmemeli")

    # LISTE DOLU (5+ satir) -> yalnizca son ayin haberi eklenir
    dolu = [{"baslik": "x%d" % i, "asama": "Belirsiz", "olaylar": []}
            for i in range(REZERV_ESIK)]
    eq(_rezervden_sec([mino("r5", REZERV_DAR_GUN + 20)],
                      rows=dolu, st={}, eksik=1), [],
       "liste doluyken eski rezerv satiri eklenmemeli")
    eq(len(_rezervden_sec([mino("r6", REZERV_DAR_GUN - 5)],
                          rows=dolu, st={}, eksik=1)), 1,
       "liste doluyken son ayin haberi eklenebilmeli")

    # HAVUZ EN YENIDEN ESKIYE taranir - "en yakin tarihli" once
    a, b = mino("r7", 50), mino("r8", 5)
    b["baslik"] = "Primetals to modernise Indian pickling line"
    b["hat"] = "Asitleme hatti"
    sec2 = _rezervden_sec([a, b], rows=[], st={}, eksik=1)
    eq(len(sec2), 1, "eksik kadar satir alinmali")
    eq(sec2[0]["anahtar"], "r8", "once EN YAKIN tarihli alinmali")

    # Izler YENIDEN URETILMEZ - iki ayri Primetals isi birlesmemeli
    src = open(os.path.join(os.path.dirname(__file__), "cli.py"),
               encoding="utf-8").read()
    g = src[src.index("def _rezervden_sec("):src.index("def _bulunan_guncelle(")]
    eq('r["olaylar"] = sorted(set(r.get("olaylar")' not in g, True,
       "rezervde iz yeniden uretilmemeli - gercek haber kaybettirir")
    eq('olaylar = set(st.get("events") or {})' in g, True,
       "kalici hafiza olaylar kumesine konulmali")


def test_w36_pota_galvaniz_hat_degildir():
    """2026-08-31: galvaniz POTASI, serit isleyen galvaniz HATTI degildir.

    "KEZAD galvanising facility moves closer to commissioning" satiri
    2026-W36 kosusunda HAT katmanina "Galvaniz hatti (CGL)" rozetiyle
    girdi. Denetimde cikti: haber bir GALVANIZ POTASI - 610 ton ergimis
    cinko, 16,2 metrelik kazan, 5,5 metreye kadar YAPILAR icin cift
    daldirma, yilda 150 bin ton. Yani celik konstruksiyonun parca parca
    daldirildigi genel galvaniz tesisi; bobin/serit isleyen SUREKLI
    galvaniz hatti degil. Soguk haddehane muduru icin bu haber degildir.

    BASLIKTA TEK BIR POTA KELIMESI YOK - kanit govdededir. Bu yuzden veto
    govdede de isler. Govde vetosu yalnizca DARALTIR: "govde bir haberi
    kapsam ici YAPAMAZ" kuralinin tersi degil, tamamlayicisidir - govde
    bir haberin kapsam DISI oldugunu kanitlayabilir.
    """
    kezad = ("The facility will hold 610 metric tons of molten zinc at "
             "around 450C in a 16.2-metre galvanising kettle with "
             "double-dipping capability for structures up to 5.5 metres, "
             "providing capacity to galvanize up to 150,000 tonnes annually.")
    ok, why = taxonomy.in_scope(
        "KEZAD galvanising facility moves closer to commissioning", kezad)
    eq(ok, False, "pota tesisi kapsam disi olmali")
    eq(why, "pota_galvaniz", "sebep dogru olmali")
    eq(taxonomy.in_scope(
        "Galva Hub to commission Emirates largest galvanizing kettle")[0],
       False, "basliktaki pota da vetolanmali")

    # KANIT METNE BAGLI OLDUGU SURECE KURAL KIRILGAN (2026-08-31, olculdu).
    # KEZAD satiri bir kosuda "kettle / double-dipping / structures"
    # kelimeleriyle elendi; ERTESI KOSUDA ayni haber baska bir yayinin
    # metniyle geldi, kalip tutmadi ve satir geri dondu.
    #
    # Saglam ayrim: SUREKLI galvaniz hatti haberi mutlaka serit/bobin/sac ya
    # da "hat" der - CGL, "galvanizing line", "first coil", "strip". Genel
    # galvaniz tesisi tesisin kendisinden bahseder ve serit demez, cunku
    # parca daldirir.
    ok, why = taxonomy.in_scope(
        "KEZAD galvanising facility moves closer to commissioning",
        "The facility in Abu Dhabi will serve fabricators in the industrial hub.")
    eq(ok, False, "hat isareti tasimayan galvaniz TESISI girmemeli")
    eq(why, "galvaniz_hat_isareti_yok", "sebep dogru olmali")

    # KURAL DAR TUTULMALI: "galvaniz" SIRKET ADININ parcasi olabilir ve o
    # haber gercek bir yassi is olabilir. Ilk yazdigim genis hal bu satiri
    # eledi ve KENDI TESTIM yakaladi - veto yalnizca TESIS kelimesiyle
    # birlikte gelen galvaniz haberine uygulanir.
    eq(taxonomy.in_scope(
        "Kirac Galvaniz Bulgaristan'da 10 Milyon Euro'luk Anlasmaya Imza Atti")[0],
       True, "sirket adindaki 'Galvaniz' vetoya sebep olmamali")

    # SUREKLI SERIT HATLARI KORUNMALI - kalip dar tutuldu
    for t, g in (
        ("JSW Steel, India, orders ANDRITZ galvanizing line for advanced "
         "automotive steel",
         "The continuous galvanizing line will produce high-strength coated "
         "sheet for the automotive industry."),
        ("Primetals Technologies awarded contract for hot-dip galvanizing "
         "line at JFE Steel",
         "The hot-dip galvanizing line processes cold-rolled strip in coil form."),
        ("Galvanizing line upgrade by SMS group enables Villacero to meet "
         "the growing demand for skin-passed strip and coil",
         "The continuous galvanizing line upgrade includes a new zinc pot "
         "and air knife system."),
        ("Angang Guangzhou produces first coil at new galvanizing line", ""),
        ("Partnering with Shandong Zhongxin to Deliver High-End Galvanizing "
         "and Continuous Annealing Lines for Automotive Steel Upgrading", ""),
        ("Roofings Unveils $125m Steel Mill, Doubles Cold-Rolled Capacity "
         "to 300000 Tonnes",
         "The plant houses cold rolling, galvanizing and colour coating lines."),
        ("ArcelorMittal Poland completes construction of ZAM roll coating line", ""),
    ):
        eq(taxonomy.in_scope(t, g)[0], True,
           "surekli galvaniz hatti kapsam icinde kalmali: " + t[:44])


def test_w36_yayinci_kuyrugu():
    """2026-08-31: yayinci adi basligin sonuna yapisip rapora giriyordu.

    2026-W36 kosusunda satir bu haliyle cikti:
      "Marcegaglia upgrades pickling line at Gazoldo degli Ippoliti
       stainless steel plant | Mesteel - Online News"
    Iki zarari var: okuyucuya cop gosterir, VE ayni haberin iki yayindaki
    hali farkli tekrar anahtari uretir - yani tekrar savunmasini da deler.

    Kesim IHTIYATLI olmali: ayiricidan sonraki parca kisa olmali, yayinci
    isareti tasimali ve geriye anlamli bir baslik kalmali. Aksi halde
    "New MINO Double-Stand Six-High Cold Reversing Mill in North America"
    gibi tireli gercek basliklar kirpilir.
    """
    eq(taxonomy.temiz_baslik(
        "Marcegaglia upgrades pickling line at Gazoldo degli Ippoliti "
        "stainless steel plant | Mesteel - Online News"),
       "Marcegaglia upgrades pickling line at Gazoldo degli Ippoliti "
       "stainless steel plant", "Mesteel kuyrugu atilmali")
    eq(taxonomy.temiz_baslik(
        "Angang starts production at new galvanizing line - Yieh Corp Steel News"),
       "Angang starts production at new galvanizing line", "Yieh kuyrugu atilmali")
    # KUYRUK KAYNAGIN ALAN ADINA BENZIYORSA da atilir. "... ZAM roll
    # coating line » Metallurgprom" hicbir yayincilik sozcugu tasimiyor;
    # ayni haber bu yuzden havuzda IKI KEZ durdu. Alan adi karsilastirmasi
    # keyfi bir yayinci listesi tutmaktan hem daha genel hem daha guvenli.
    eq(taxonomy.temiz_baslik(
        "ArcelorMittal Poland completes construction of ZAM roll coating "
        "line » Metallurgprom",
        "https://metallurgprom.org/en/news/europe/18814-x.html"),
       "ArcelorMittal Poland completes construction of ZAM roll coating line",
       "alan adina benzeyen kuyruk atilmali")

    # KORUNMALI - kuyruk degil, basligin kendisi
    for t in ("KEZAD galvanising facility moves closer to commissioning",
              "KG Steel selects Primetals for Dangjin PLTCM upgrade and "
              "capacity expansion",
              "Primetals to modernise Korean pickling line",
              "U. S. Steel Announces Plans to Restart Gary Tin Mill",
              "New MINO Double-Stand Six-High Cold Reversing Mill in North America",
              "Tosyali Algerie launches cold-rolled steel production"):
        eq(taxonomy.temiz_baslik(t), t, "gercek baslik kirpilmamali: " + t[:44])
    # ...adres verilse de kirpilmamali
    eq(taxonomy.temiz_baslik(
        "Primetals to modernise Korean pickling line",
        "https://www.steeltimesint.com/news/primetals-to-modernise-korean-"
        "pickling-line"),
       "Primetals to modernise Korean pickling line",
       "adres verilince de gercek baslik kirpilmamali")

    # Havuz tekrari: ayni haber iki yoldan girince BASLIK bazli birlesmeli
    from .cli import _havuz_tekrarsiz
    a = {"baslik": "ArcelorMittal Poland completes construction of ZAM roll "
                   "coating line » Metallurgprom",
         "url": "https://metallurgprom.org/en/news/europe/18814-x.html"}
    b = {"baslik": "ArcelorMittal Poland completes construction of ZAM roll "
                   "coating line",
         "url": "https://news.google.com/rss/articles/CBMi?oc=5"}
    out = _havuz_tekrarsiz([b, a])
    eq(len(out), 1, "ayni haber havuzda iki kez durmamali")
    eq(out[0]["url"].startswith("https://metallurgprom.org"), True,
       "yayincinin kendi adresi tercih edilmeli - aggregator yonlendirmesi degil")


def test_w36_editor_bulur_makine_dogrular():
    """2026-08-31 (kullanici: "bulamadigi haftalar sen bul").

    Taze arz olculmus haliyle haftada ~1-3 kapsam ici haber; hedef 5-6.
    Zayif haftalarda editorun ARAMA ile haber bulmasi gerekiyor. Ama
    editorun buldugu bir haberi dogrudan rapora yazmak IKI kurali birden
    cignerdi: tarih uydurulamaz, ve kapsam kapisi editorun kanaatiyle
    degil ayni kapiyla isler.

    COZUM: editor YALNIZ BASLIK + ADRES verir; "radar dogrula" Actions'ta
    sayfayi acar, SAYFANIN GERCEK basligini alir, ayni kapidan gecirir,
    tarihi YAPISAL olarak cikarir ve tekrar denetiminden gecirir. Editorun
    katkisi ADAY GOSTERMEKTIR, karar makinenindir.

    Bu testin bekcilik ettigi sey: dogrulama zincirinin hicbir halkasinin
    atlanamamasi. Zincir kirilirsa editorun kanaati rapora sizar.
    """
    import json as _json
    from . import dogrula as D

    src = open(os.path.join(os.path.dirname(__file__), "dogrula.py"),
               encoding="utf-8").read()
    # Sayfa acilamiyorsa HICBIR SEY girmez
    eq('red(k, "sayfa acilamadi"' in src, True, "acilamayan sayfa girmemeli")
    # Editorun yazdigi baslik degil, SAYFANIN basligi kullanilir
    eq('gercek = (doc.get("title") or "").strip()' in src, True,
       "sayfanin gercek basligi kullanilmali")
    # Tarih YAPISAL olarak cikarilir, cikmazsa girmez
    eq("dates.extract_article_date(doc" in src, True, "tarih yapisal cikarilmali")
    eq('red(k, "yayin tarihi sayfadan okunamadi")' in src, True,
       "tarihi okunamayan haber girmemeli")
    eq("dates.title_year_conflict(baslik, iso)" in src, True,
       "baslik yili celiskisi denetlenmeli")
    # Kapi ve tekrar denetimi
    eq("_kapi(baslik, govde)" in src, True, "ayni kapsam kapisi isletilmeli")
    eq('set(row["olaylar"]) & ev' in src, True, "olay izi denetlenmeli")
    eq("taxonomy.similar_titles(baslik, b" in src, True,
       "gonderilmis varyant denetlenmeli")
    # Dosyada TARIH ALANI olamaz - kural bu kanalda da gecerli
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = _json.load(open(os.path.join(kok, "veri", "elle_besleme.json"),
                        encoding="utf-8"))
    for k in d["kayitlar"]:
        for alan in ("tarih", "date", "pubDate", "tarih_kaynagi"):
            eq(alan in k, False, "elle beslemede tarih alani olamaz: " + alan)
    # Adaylar ULASILABILIR yayinlardan olmali - olculdu: kapali yayinlarin
    # kendi adresleri hic satir uretmedi, cunku sayfa 403 verince tarih de
    # dogrulanamiyor.
    kapali = ("steeltimesint.com", "sms-group.com",
              "corporate.arcelormittal.com", "bigmint.co",
              "furnaces-international.com")
    for k in d["kayitlar"]:
        for kap in kapali:
            eq(kap in k["url"], False,
               "kapali yayinin adresi aday olamaz (%s)" % kap)

    # Ag yokken cokmez ve HICBIR SEY eklemez
    eski = D.http.fetch
    try:
        D.http.fetch = lambda u, **kw: (False, "", {"hata": "ag yok"})
        st_once = _json.dumps(state.load().get("bulunan", []), sort_keys=True)
        D.dogrula(log=lambda *a: None)
        eq(_json.dumps(state.load().get("bulunan", []), sort_keys=True), st_once,
           "sayfa acilamiyorsa havuza hicbir sey eklenmez")
    finally:
        D.http.fetch = eski


def test_w36_adres_ve_teknoloji_havuzu():
    """2026-08-31: okuyucunun tikladigi baglanti ve kosenin tekrarlari.

    (1) AGGREGATOR YONLENDIRMESI OKUYUCUYA GITMEMELI. Rapordaki baglanti
        okuyucunun tikladigi seydir; yonlendirme once arama motoruna gider.
        W35'te Roofings satirinin baglantisini bu yuzden ELLE duzeltmek
        zorunda kaldim. Arama katmani artik kaynaklarin yarisi oldugu icin
        bu tek tek duzeltilecek bir is degil.
        Bing adresi gercek adresi ICINDE tasir, cozum agi hic kullanmaz.
        Google'in yeni bicimi (CBMi...) SIFRELIDIR ve cevrimdisi cozulemez;
        o adresler oldugu gibi kalir.

    (2) TEKNOLOJI HAVUZUNDA AYNI MADDE UC KEZ. Iki aggregator ayni haberi
        farkli yonlendirme adresiyle donduruyor; anahtar ayni ama havuza
        uc kopya girdi.

    (3) GONDERILMIS OLAYIN VARYANTI KOSEYE GIREMEZ. "ham in seen" kontrolu
        ANAHTAR bazlidir; baska yayinin ayni olayi anlatan varyantinin
        anahtari farklidir. Havuza "Primetals Technologies to Modernize
        PLTCM for KG Steel in South Korea" girdi - W35 bulteninde
        "KG Steel selects Primetals for Dangjin PLTCM upgrade and capacity
        expansion" olarak zaten gitmisti.
    """
    from .collect import temiz_adres

    bing = ("http://www.bing.com/news/apiclick.aspx?ref=FexRss&aid=&tid=6a95"
            "&url=https%3a%2f%2fwww.msn.com%2fen-ae%2fnews%2fother%2fkezad-"
            "galvanising-facility-moves-closer-to-commissioning%2far-AA2ayC80"
            "&c=548&mkt=en-us")
    eq(temiz_adres(bing).startswith("https://www.msn.com/en-ae/news/other/"
                                    "kezad-galvanising"), True,
       "Bing yonlendirmesi yayincinin adresine cozulmeli")
    gnews = "https://news.google.com/rss/articles/CBMijwFBVV95cUxN?oc=5"
    eq(temiz_adres(gnews), gnews, "sifreli Google adresi bozulmadan kalmali")
    eq(temiz_adres("https://www.steelorbis.com/steel-news/x.htm"),
       "https://www.steelorbis.com/steel-news/x.htm", "normal adres degismez")
    eq(temiz_adres(""), "", "bos adres cokmemeli")
    eq(temiz_adres(None), None, "None cokmemeli")

    src = open(os.path.join(os.path.dirname(__file__), "collect.py"),
               encoding="utf-8").read()
    g = src[src.index("def maybe_tech("):src.index("def maybe_rezerv(")]
    eq('any(t["anahtar"] == key for t in tech_pool)' in g, True,
       "ayni madde havuza iki kez girmemeli")
    eq("gonderilmis" in g, True,
       "gonderilmis olayin varyanti koseye girmemeli")

    # VAKANIN DAYANAGI: basligi benzerlik YAKALAMAZ - olculdu. Ortak ayirt
    # edici kelimeler yalniz "steel" ve "pltcm", oran %30. Bu yuzden koseye
    # OLAY PARMAK IZI bacagi konuldu, baslik bacagi degil.
    a = "Primetals Technologies to Modernize PLTCM for KG Steel in South Korea"
    b = ("KG Steel selects Primetals for Dangjin PLTCM upgrade and capacity "
         "expansion")
    eq(taxonomy.similar_titles(a, b), False,
       "baslik bacagi bu cifti yakalamaz - vakanin dayanagi")
    from .collect import event_keys
    gonderilen = {"tedarikci": "Primetals", "firma": "KG Steel",
                  "hat": "Tandem soguk hadde (TCM)", "ulke": "G. Kore",
                  "asama": "Modernizasyon"}
    aday = {"tedarikci": "Primetals Technologies", "firma": "KG Steel",
            "hat": "Tandem soguk hadde (TCM)", "ulke": "G. Kore",
            "asama": "Modernizasyon"}
    eq(bool(event_keys(aday) & event_keys(gonderilen)), True,
       "olay parmak izi ayni KG Steel/Primetals olayini yakalamali")
    eq("set(event_keys(aday_satir)) & set(ev_state)" in g, True,
       "kose adayi olay parmak izinden gecmeli")


def test_w36_bulunan_havuzu_ve_yanlis_tekrar():
    """2026-08-31: hacim sorununun ASIL sebebi - gorulen haber unutuluyordu.

    Gunluk tarama kabul ettigi satiri hicbir yere kaydetmiyordu:
    out/tarama.json ertesi gun uzerine yaziliyor, rezerv ise yalniz PENCERE
    DISI satirlari tutuyor. Aggregator sonuclari ise OYNAK - bir gun gorunen
    haber ertesi gun beslemede yok.

    OLCULDU (bu haftanin gunluk taramalarinin git gecmisi): sistem hafta
    boyunca birbirinden farkli satirlar gordu ve her biri TEK bir taramada
    gorunup kayboldu -
      29.08  "India's Manaksia Steel to invest $84 million to expand..."
      31.08  "ArcelorMittal Confirms Up to R$ 5 Billion for New Cold..."
      31.08  "KEZAD galvanising facility moves closer to commissioning"
    Bultene 2 satir girdi. Kapi degil, HAFIZA eksikti.

    BULUNAN HAVUZU: pencere ici, kapiyi gecmis, tarihi dogrulanmis, henuz
    gonderilmemis satirlar. Kapi GEVSEMEZ - satirlar zaten ayni kapidan
    gecmistir, degisen tek sey unutulmamalaridir.

    IKINCI KUSUR - YANLIS "TEKRAR" ELEMESI. Havuz kurulunca gorundu:
      "India's Manaksia Steel to invest $84 million to expand value-added
       steel capacity"
      "India's Jindal Stainless Limited to invest $94 million to ramp up
       cold rolling capacity"                            (W34'te gonderildi)
    IKI AYRI HINT SIRKETI ayni haber sayilip elendi. Paylastiklari sey
    invest / million / capacity idi - ucu de kalip. Yanlis tekrar elemesi
    gercek haber kaybettirir ve bunu kimse gormez, cunku eleme sessizdir.
    """
    from .cli import _bulunan_guncelle, _rezerv_hala_gecerli

    # --- Havuz: taze satir girer, rezervden gelen GIRMEZ
    st = {"bulunan": [], "seen": {}, "tech_seen": {}}
    # NOT: vaka basligi 2026-08-31'de degistirildi. Once KEZAD kullanilmisti;
    # ayni gun "galvaniz haberi hat/serit isareti tasimali" kurali konunca o
    # baslik kapiyi gecmez oldu ve test kirildi - dogru davranis. Yerine ayni
    # kosunun bir baska GERCEK satiri konuldu.
    taze = {"anahtar": "a1", "tarih": "2026-08-24", "baslik":
            "NS-SUS Completes Installation of New Danieli Coil-Handling Cranes",
            "hat": "Bobin tasima / paketleme", "asama": "Belirsiz"}
    rez = {"anahtar": "a2", "tarih": "2026-03-13", "rezerv": True, "baslik":
           "New MINO Double-Stand Six-High Cold Reversing Mill in North America"}
    _bulunan_guncelle(st, [taze, rez])
    eq([r["anahtar"] for r in st["bulunan"]], ["a1"],
       "yalniz taze satir havuza girer; rezerv kendi havuzundadir")

    # Bu kosuda listede olan satir havuzda KALIR ama tekrar EKLENMEZ:
    # bulten onaylanmazsa gelecek hafta yine cikabilmeli
    eq(_bulunan_guncelle(st, [taze]), [], "bu kosudaki satir yeniden eklenmez")
    eq(len(st["bulunan"]), 1, "ama havuzdan da dusmez")

    # Gonderilmis satir havuzdan duser
    st2 = {"bulunan": [dict(taze)], "seen": {"a1": "2026-08-24"}, "tech_seen": {}}
    _bulunan_guncelle(st2, [])
    eq(st2["bulunan"], [], "gonderilen satir havuzda kalmaz")

    # Havuz da guncel kapiya sokulur (havuz karari tasir, kodu degil)
    st3 = {"bulunan": [{"anahtar": "x", "tarih": "2026-08-05", "baslik":
                        "Triple-S Steel acquires Camden Yards Steel"}],
           "seen": {}, "tech_seen": {}}
    _bulunan_guncelle(st3, [])
    eq(st3["bulunan"], [], "kapali kapidan gecen satir havuzda kalmaz")

    # --- Yanlis tekrar elemesi: AYIRT EDICI ortak kelime yoksa kalip yetmez
    manaksia = ("India's Manaksia Steel to invest $84 million to expand "
                "value-added steel capacity")
    jindal = ("India's Jindal Stainless Limited to invest $94 million to "
              "ramp up cold rolling capacity")
    eq(taxonomy.similar_titles(manaksia, jindal), False,
       "iki ayri Hint sirketi ayni haber sayilamaz")
    eq(taxonomy.similar_titles(
        "Nucor to invest $59 million in steel grating capacity", jindal), False,
       "Nucor ile Jindal ayni haber degildir")

    # ...ama GERCEK tekrarlar yakalanmaya devam etmeli
    eq(taxonomy.similar_titles(
        "Jindal Stainless investing Rs 900 crore to increase cold rolling "
        "capacity to 2.67 MT by FY28", jindal), True,
       "ayni Jindal duyurusunun iki yayini")
    eq(taxonomy.similar_titles(
        "tk accelis Processing Europe expands Stuttgart steel service "
        "center capacity",
        "tk accelis announces milestone at Stuttgart steel service center"),
        True, "ayni tk accelis haberi")
    # Tek ayirt edici ad + zayif ortusme (Hydnum) korunmali
    eq(taxonomy.similar_titles(
        "İspanya, Hydnum Steel'in Yeşil Çelik Tesisine 150 Milyon Euro "
        "Destek Sağlayacak",
        "Hydnum Steel, İber Yarımadası'nın ilk temiz çelik tesisi için "
        "150 milyon euroluk yatırım taahhüdü aldı"), True,
        "tek ayirt edici ad yeterli olmali")


def test_w36_havuz_karari_tasir_kodu_degil():
    """2026-08-31: kapiyi duzeltmek havuzdaki eski karari DUZELTMEZ.

    Ayni gun iki delik kapatildi (sirket satin alma, QSP) ve AYNI KOSUDA
    o iki satir REZERVDEN listeye girdi:
      "Triple-S Steel acquires Camden Yards Steel"
      "Ezz Flat Steel signs agreement with Danieli for QSP modernization"
    Ikisi de kapali kapidan bir daha GECEMEZ - ama rezervden secim kapiyi
    hic sormuyordu. Rezerv 540 gun geriye uzaniyor, yani her kapi
    duzeltmesi havuzda 18 aya kadar etkisiz kaliyordu.

    AYNI AILE, ucuncu kez: havuz KARARI tasir, KODU degil.
      - _rezerv_alanlarini_tazele : ulkeyi guncel sozlukle yeniden turetir
                                    (Gary/Indiana -> Hindistan vakasi)
      - finalize                  : olay izini duzeltmeden SONRA uretir
                                    (Roofings vakasi)
      - _rezerv_hala_gecerli      : havuzu her kosuda guncel kapiya sokar
    """
    from .cli import _rezerv_hala_gecerli

    for t in ("Triple-S Steel acquires Camden Yards Steel",
              "Ezz Flat Steel signs agreement with Danieli for QSP "
              "modernization in Ain Sokhna",
              "Cleveland-Cliffs matches $500M federal grant for Ohio steel "
              "mill without hydrogen retrofit"):
        eq(_rezerv_hala_gecerli({"baslik": t}), False,
           "kapali kapidan gecen satir havuzda kalmamali: " + t[:45])

    # Gercek satirlar havuzda KALMALI - temizlik cop toplar, haber degil
    for t in ("Primetals to modernise Korean pickling line",
              "U. S. Steel Announces Plans to Restart Gary Tin Mill",
              "tk accelis Processing Europe expands Stuttgart steel "
              "service center capacity",
              "New MINO Double-Stand Six-High Cold Reversing Mill in "
              "North America"):
        eq(_rezerv_hala_gecerli({"baslik": t}), True,
           "gercek haber havuzda kalmali: " + t[:45])

    eq(_rezerv_hala_gecerli({}), False, "baslik yoksa havuzda duramaz")

    # Temizlik havuz TAZELENIRKEN isler - dusen satir bir daha maliyet
    # cikarmasin diye kalici olarak duser
    src = open(os.path.join(os.path.dirname(__file__), "cli.py"),
               encoding="utf-8").read()
    g = src[src.index("def _rezerv_guncelle("):src.index("def cmd_review(")]
    eq("_rezerv_hala_gecerli(r)" in g, True,
       "havuz her kosuda guncel kapiya sokulmali")

    # HIDROJEN KALIBI DAR OLMALI: hidrojen tavlama gercek bir hat konusudur
    eq(taxonomy.in_scope("New hydrogen annealing furnace commissioned at "
                         "cold rolling complex")[0], True,
       "hidrojen TAVLAMA kapsam icindedir")
    eq(taxonomy.in_scope("SMS supplies HNx hydrogen atmosphere batch "
                         "annealing line")[0], True,
       "HNx atmosferi kapsam icindedir")


def test_w36_bing_katmaninin_actigi_uc_delik():
    """2026-08-31: ikinci arama host'u acilinca kapinin UC deligi gorundu.

    Bing ayna katmani ham baglantiyi 2730'dan 3296'ya cikardi (+%21) ve BES
    yeni satir uretti. Besinin de yayinlanamaz oldugunu denetimde buldum -
    katman calisti, KAPI sizdirdi. Rezervin daha once yaptigi isi bu sefer
    yeni katman yapti: havuzu buyutunce delikler gorunur oldu.

    DELIK 1 - OLAY PARMAK IZI DUZELTMEDEN SONRA URETILMIYORDU.
      2026-W35'te giden Roofings satirinin kayitli anahtari
      "roofings unveils|hat|Soguk hadde|Belirsiz" idi: firma adi baslikta
      "Roofings Unveils" okunmus, ulke bos, asama Belirsiz kalmisti. Editor
      hepsini duzeltti (Roofings Group / Uganda / Ilk urun / Danieli) ama
      hafizada bozuk anahtar kaldi. Sonuc: AYNI olayin iki varyanti daha
      listeye girdi -
        "Museveni Unveils $120 Million Steel Complex to Boost Ugandan..."
        "Roofings Group, Uganda'da 125 milyon dolarlik yeni celik tesisini
         faaliyete gecirdi"                        (ayni haberin Turkcesi)
      Baslik benzerligi bunlari yakalayamaz - biri cumhurbaskanini one
      cikariyor, digeri baska dilde. Olay parmak izi yakalamaliydi.

    DELIK 2 - SIRKET SATIN ALMA YALNIZ KATMAN 2'DE VETOLUYDU.
        "Triple-S Steel acquires Camden Yards Steel"
      Govdede servis merkezi/dilme gecince Hat katmani acildi. Bir servis
      merkezinin EL DEGISTIRMESI hat gelismesi degildir.

    DELIK 3 - QSP YUKARI AKIS VETOSUNDA YOKTU.
        "Ezz Flat Steel signs agreement with Danieli for QSP modernization"
      QSP = Quality Strip Production, ince slab dokum + sicak hadde. Firma
      adinda "Flat Steel" gecmesi haberi yassi ISLEM hatti yapmaz.
    """
    from .collect import event_keys

    # DELIK 1: duzeltilmis alanlardan parmak izi uretilmeli
    ham = {"firma": "Roofings Unveils", "ulke": "", "asama": "Belirsiz",
           "tedarikci": "", "hat": "Soguk hadde"}
    duzeltilmis = dict(ham, firma="Roofings Group", ulke="Uganda",
                       asama="Ilk urun", tedarikci="Danieli")
    eq(event_keys(ham) & event_keys(duzeltilmis), set(),
       "bozuk okumanin anahtari duzeltilmisle KESISMIYOR - vakanin dayanagi")

    # ...ve duzeltilmis kayit, iki GERCEK varyanti da yakalamali
    hafiza = event_keys(duzeltilmis)
    museveni = {"firma": "Boost Ugandan Manufacturing", "ulke": "Uganda",
                "hat": "Soguk hadde", "asama": "Ilk urun", "tedarikci": ""}
    turkce = {"firma": "Roofings Group", "ulke": "Uganda",
              "hat": "Soguk hadde", "asama": "Ilk urun", "tedarikci": ""}
    eq(bool(event_keys(museveni) & hafiza), True,
       "firma adi bambaska bozulsa da ayni olay yakalanmali")
    eq(bool(event_keys(turkce) & hafiza), True,
       "ayni haberin Turkcesi yakalanmali")

    # Ulke haritasi: bos ulke butun ulke bacaklarini korlestiriyordu
    eq(taxonomy.match_country("Museveni Unveils Steel Complex to Boost "
                              "Ugandan Manufacturing"), "Uganda",
       "sifat hali 'Ugandan' taninmali")
    eq(taxonomy.match_country("Roofings Group, Uganda'da yeni tesis"),
       "Uganda", "Turkce ek 'Uganda'da' taninmali")

    # KIMSIZ BACAK YALNIZ ILK URETIM ICIN. Sozlesme/modernizasyon
    # haberleri buyuk ureticilerde ayni ay mesru sekilde tekrarlanir;
    # orada bu bacak GERCEK haber kaybettirirdi.
    a = {"firma": "A", "ulke": "Cin", "hat": "Galvaniz hatti (CGL)",
         "asama": "Sozlesme", "tedarikci": ""}
    b = {"firma": "B", "ulke": "Cin", "hat": "Galvaniz hatti (CGL)",
         "asama": "Sozlesme", "tedarikci": ""}
    eq(event_keys(a) & event_keys(b), set(),
       "iki AYRI sozlesme haberi ayni olay sayilmamali")
    c = dict(a, asama="Ilk urun")
    d2 = dict(b, asama="Ilk urun")
    eq(bool(event_keys(c) & event_keys(d2)), True,
       "ayni ulkede ayni hatta iki ILK URETIM ayni olaydir")
    csrc = open(os.path.join(os.path.dirname(__file__), "cli.py"),
                encoding="utf-8").read()
    g = csrc[csrc.index("def cmd_finalize("):]
    i_fix = g.index('fixes.get(r["anahtar"])')
    i_olay = g.index('r["olaylar"] = sorted(eski | set(event_keys(r)))')
    eq(i_fix < i_olay, True,
       "parmak izi DUZELTMEDEN SONRA yeniden uretilmeli")
    eq("eski | set(event_keys(r))" in g, True,
       "eski anahtar da korunmali - baska yayin ayni bozuk okumayi uretebilir")

    # DELIK 2 ve 3: kapi artik sizdirmamali
    for t in ("Triple-S Steel acquires Camden Yards Steel",
              "ANDRITZ to acquire Salico Group",
              "Ezz Flat Steel signs agreement with Danieli for QSP "
              "modernization in Ain Sokhna"):
        eq(taxonomy.in_scope(t)[0], False, "kapsam disi olmali: " + t[:45])
        eq(bool(taxonomy.genel_yatirim(t)), False,
           "Katman 2'ye de girmemeli: " + t[:45])

    # COP EKLEMEDEN: gercek hat haberleri KORUNMALI
    for t in ("JSW Steel, India, orders ANDRITZ galvanizing line for "
              "advanced automotive steel",
              "KG Steel selects Primetals for Dangjin PLTCM upgrade and "
              "capacity expansion",
              "Primetals to modernise Korean pickling line",
              "U. S. Steel Announces Plans to Restart Gary Tin Mill",
              "Fives supplies technologies for Xinyu's new electrical "
              "steel facility"):
        eq(taxonomy.in_scope(t)[0], True, "kapsam ici kalmali: " + t[:45])


def test_w36_host_korumasi_ve_ikinci_arama_hostu():
    """2026-08-31: AYNI HATAYI IKI KEZ YAPTIM - ucuncusu yapisal olarak engellendi.

    Iki gerileme de ayni sebeptendi: PAYLASILAN BIR HOST'A FAZLADAN ISTEK
    GONDERDIM VE FATURAYI BASKA BIR IS ODEDI.
      1) Sitemap zinciri gercek istegin onune gecti; tahmin adresleri 404
         alinca site kapiyi kapatti ve BES kaynak erisilemez oldu.
      2) Tarih icin news.google.com'a 40 ek istek: erisilemeyen kaynak
         9 -> 89 (80'i Google, HTTP 503), kazanc 0, kosu 35 -> 60 dakika.

    Ders yamayla ogrenilmez, ZORLANIR. Iki yapisal degisiklik:

    A) HOST BUTCESI + SOGUTMA. Her host icin kosu basina istek butcesi var;
       butce dolunca istek GONDERILMEZ, hangi is isterse istesin. Hiz
       siniri sinyali (429/503) gelince host sogutmaya alinir - israr
       yumusak kisitlamayi sert bloga cevirir, 31 Agustos'ta tam bu oldu.
       Boylece yeni bir katman eklemek mevcut katmani riske ATAMAZ.

    B) IKINCI ARAMA HOST'U. 169 kaynagin 80'i tek host'taydi; arama
       katmaninin tamami tek saglayiciya bagliydi ve o saglayicinin kotu
       gunu butun bulteni dusuruyordu. Her Google News sorgusunun Bing News
       aynasi OTOMATIK uretilir - elle ikinci liste tutulmaz, sorgu
       eklendiginde aynasi bedava gelir ve iki liste asla sapmaz.
       Kapi GENISLEMEZ: ayni sorgular, ayni kapsam kapisi, ayni tarih
       zinciri; degisen tek sey ayni sorunun ikinci bir yere de sorulmasi.
    """
    from . import http as H
    from . import sources as S
    import re as _re
    import urllib.parse as _up

    # --- A) butce istegi gercekten keser
    eski_butce = H.HOST_BUTCE
    try:
        H.host_sifirla()
        H.HOST_BUTCE = 3
        for _ in range(3):
            eq(H.host_izin("https://news.google.com/rss/x")[0], True, "butce icinde")
            H._host_kaydet("https://news.google.com/rss/x")
        izin, sebep = H.host_izin("https://news.google.com/rss/y")
        eq(izin, False, "butce dolunca istek gonderilmemeli")
        eq(sebep, "host butcesi doldu", "sebep bildirilmeli")
        # BASKA host etkilenmez - ceza host'a ozeldir
        eq(H.host_izin("https://www.steelorbis.com/x")[0], True,
           "butce baska host'u baglamaz")

        # --- A2) hiz sinirinda israr edilmez
        H.host_sifirla()
        H._host_hiz_siniri("https://news.google.com/x")
        eq(H.host_izin("https://news.google.com/y")[0], True,
           "ilk sinyal uyaridir, kapatmaz")
        H._host_hiz_siniri("https://news.google.com/x")
        eq(H.host_izin("https://news.google.com/y")[0], False,
           "ikinci sinyalde host sogutmaya alinmali")
        r = H.host_raporu()
        eq(r.get("news.google.com", {}).get("sogutmada"), True,
           "sogutma raporda GORUNMELI - sessiz kisitlama en kotusudur")
    finally:
        H.HOST_BUTCE = eski_butce
        H.host_sifirla()

    # 429/503'te tekrar denenmemeli (kodun kendisi)
    hsrc = open(os.path.join(os.path.dirname(__file__), "http.py"),
                encoding="utf-8").read()
    eq("HIZ SINIRINDA ISRAR EDILMEZ" in hsrc, True, "hiz sinirinda retry olmamali")
    eq("izin, sebep = host_izin(url)" in hsrc, True, "fetch butceyi sormali")

    # --- B) arama katmani tek host'ta olmamali
    hostlar = {}
    for x in S.SOURCES:
        u = x.get("rss") or x.get("url") or ""
        m = _re.match(r"https?://([^/]+)", u)
        if m:
            hostlar[m.group(1)] = hostlar.get(m.group(1), 0) + 1
    en_buyuk = max(hostlar.values())
    eq(en_buyuk <= len(S.SOURCES) * 0.40, True,
       "hicbir host kaynaklarin %%40'indan fazlasini tutmamali (en buyuk %d/%d)"
       % (en_buyuk, len(S.SOURCES)))

    # KAPALI YAYININ KENDI HABERI site: ile hedeflenir (2026-08-31).
    # Olcum: kapsam ici haberin ~%72'si STI + SteelOrbis'ten geliyor ve STI
    # HER adreste 403. Mevcut vekil sorgular yayinin ADINI ariyordu - "SMS
    # group" HAKKINDAKI haberleri buluyor, sms-group.com'un KENDI
    # haberlerini degil; aradaki fark o yayinlarin butun uretimi kadardir.
    # 403 burada engel degildir: arama katmani makaleyi HIC ACMAZ, tarih
    # beslemenin pubDate'inden yapisal gelir.
    site_q = [x for x in S.SOURCES if x["id"].startswith("gs_")]
    eq(len(site_q) >= 8, True, "kapali yayinlar site: ile hedeflenmeli")
    alanlar = " ".join(x["rss"] for x in site_q)
    for alan in ("steeltimesint.com", "sms-group.com",
                 "corporate.arcelormittal.com", "bigmint.co",
                 "furnaces-international.com", "mysteel.com"):
        eq(_up.quote("site:" + alan) in alanlar, True,
           "erisilemeyen yayin hedeflenmeli: " + alan)
    # site: sorgulari da AYNALANMALI - bir aggregator indekslemezse digeri
    eq(len([x for x in S.SOURCES if x["id"].startswith("bgs_")]), len(site_q),
       "site: sorgularinin da aynasi olmali")

    ayna = [x for x in S.SOURCES if x["publisher"] == "Bing News"]
    gnews = [x for x in S.SOURCES if x["publisher"] == "Google News"]
    eq(len(ayna), len(gnews), "her Google sorgusunun aynasi olmali")
    eq(all("when:" not in (x["rss"] or "") for x in ayna), True,
       "Google'a ozgu when: kalibi aynada kalmamali")
    eq(all("format=RSS" in x["rss"] for x in ayna), True, "ayna besleme olmali")
    # Dil katmani korunmali
    eq(any("tr-TR" in x["rss"] for x in ayna), True, "TR katmani aynada da olmali")
    eq(any("zh-CN" in x["rss"] for x in ayna), True, "ZH katmani aynada da olmali")
    # id catismasi olmamali
    ids = [x["id"] for x in S.SOURCES]
    eq(len(set(ids)), len(ids), "kaynak id'leri benzersiz olmali")


def test_w36_aci7_geri_alindi_paylasilan_host():
    """2026-W36 (2026-08-31): tarih icin fazladan istek GERI TEPTI - olculdu.

    NIYET dogruydu: tarihi dogrulanamadigi icin elenen 96 kaydin 9'u
    BASLIKLA kapiyi geciyordu ve 8'i makale sayfasi 403 veren yayinlardandi
    (Tata Steel Port Talbot asitleme hatti, SMS/Hyundai galvaniz, Ternium/
    Fives galvaniz...). Kapsami da olayi da belliydi; eksik olan tek sey
    tarihti. Tarihi Google News beslemesinin pubDate'inden sormayi denedim.

    SONUC (canli kosu, 33414160429):
      erisilemeyen kaynak   9 -> 89    (80'i Google News, HTTP 503)
      kurtarilan tarih                  0
      kabul edilen satir    2 ->  0
      kosu suresi                      60 dakika

    SEBEP YAPISAL: 169 kaynagin ~90'i Google News ARAMA beslemesidir. O tek
    host'a giden fazladan 40 istek, butun arama katmanini birden dusurdu.
    Sitemap zincirinin bes kaynagi bozmasiyla AYNI AILE (bkz.
    test_v20_sitemap_geri_dusus): paylasilan bir host'a fazladan istek
    bedava degildir ve faturayi baska bir is oder.

    KURAL: news.google.com'a kosu basina gonderilen istek sayisi
    artirilmaz. Elle besleme kanalinin ~13 sorgusu olculen tolerans
    icindedir (o kosuda erisilemeyen 9'du); uzerine cikilmamali.
    """
    from . import collect as C
    src = open(os.path.join(os.path.dirname(__file__), "collect.py"),
               encoding="utf-8").read()

    # Aci 7 akistan KALKMIS olmali
    eq("gnews_butce" not in src, True,
       "tarih icin fazladan Google News istegi akista kalmamali")
    i_drop = src.index('drop("tarihsiz_elendi", it)')
    onceki = src[max(0, i_drop - 1500):i_drop]
    eq("_elle_tarih(it[" not in onceki, True,
       "tarihsiz eleme oncesinde besleme sorgusu olmamali")

    # Olcum araci duruyor ve dogru calisiyor
    for b in ("Tata Steel breaks ground on new pickle line at Port Talbot site",
              "SMS upgrades Hyundai Steel galvanising line"):
        eq(C._tarih_sorulur_mu(b), True, "kapsam ici baslik: " + b[:40])
    for b in ("Turkey's crude steel output rises in July",
              "Nippon Steel completes 6Mt hot-rolling line"):
        eq(C._tarih_sorulur_mu(b), False, "kapsam disi baslik: " + b[:40])

    # Elle besleme kanali TEK sorgu kaynagi olarak kalmali, sayisi da sinirli
    import json as _json
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = _json.load(open(os.path.join(kok, "veri", "elle_besleme.json"),
                        encoding="utf-8"))
    eq(len(d["kayitlar"]) <= 20, True,
       "elle besleme kayit sayisi olculen tolerans icinde kalmali (%d)"
       % len(d["kayitlar"]))


def test_w36_tekrar_ve_kose_yonu():
    """2026-W36 (2026-08-31): iki gercek kusur, ikisi de canli kosuda cikti.

    (1) TEKRAR BACAGI AYNI ASAMAYI SART KOSUYORDU. Kosul "benzer baslik VE
        ayni asama" idi ve su tekrari gecirdi:
          gonderilen (W34): "India's Jindal Stainless Limited to invest
                             $94 million to ramp up cold rolling capacity"
                            asama: Ilk urun
          yeni gelen      : "Jindal Stainless investing Rs 900 crore to
                             increase cold rolling capacity to 2.67 MT by
                             FY28"                    asama: Belirsiz
        Ayni duyuru, iki yayin, farkli para birimi. Asama zaten yayindan
        yayina degisen bir OKUMA; onu sart kosmak savunmayi tam da en cok
        gerektigi yerde kapatiyor.

    (2) "KOSEDE TANITILMIS HABER SATIR OLAMAZ" KURALI TEK YONLUYDU. Tersi
        serbestti ve W36'da teknoloji havuzunun TEK adayi, W35 bulteninde
        satir olarak zaten gitmis olan "Fives supplies technologies for
        Xinyu's new electrical steel facility" idi. Okuyucu icin ikisi ayni
        haberdir; yon fark etmez.
    """
    src = open(os.path.join(os.path.dirname(__file__), "collect.py"),
               encoding="utf-8").read()

    # (1) Iki gercek baslik gercekten "benzer" sayilmali
    gonderilen = ("India's Jindal Stainless Limited to invest $94 million "
                  "to ramp up cold rolling capacity")
    yeni = ("Jindal Stainless investing Rs 900 crore to increase cold "
            "rolling capacity to 2.67 MT by FY28: MD")
    eq(taxonomy.similar_titles(yeni, gonderilen), True,
       "iki Jindal basligi ayni haberdir")
    # ...ve kod artik asamayi SART KOSMAMALI
    eq('and b.get("a", "") == row["asama"] for b in gecmis' not in src, True,
       "gecmis basliklarla karsilastirmada asama sarti kalkmali")

    # (2) seen'deki bir haber teknoloji havuzuna giremez
    eq("if ham in seen:" in src, True,
       "satir olarak gonderilmis haber koseye giremez")
    g = src[src.index("def maybe_tech("):src.index("def maybe_rezerv(")]
    eq("ham in seen" in g, True, "kontrol maybe_tech icinde olmali")


def test_w36_finalize_ozetsiz_calismaz():
    """2026-W36 (2026-08-31): "-s" unutulunca finalize sessizce her seyi atliyordu.

    "-s" verilmeyince doc bos kaliyor ve finalize editorun BUTUN kararlarini
    - duzeltmeleri, cikarilan satirlari, Turkce cumleleri, teknoloji kosesini
    - atlayip yine de bulten uretiyor VE her satiri "gonderildi" isaretliyordu.
    Bugun tam bu oldu: cikarilmasi gereken iki satir (biri tekrar, birinin
    tarihi celiskili) postaya girecekti ve dordu birden hafizaya yazildi.
    Ozet dosyasi diskte duruyorken onu ATLAMAK bir secim olamaz.
    """
    src = open(os.path.join(os.path.dirname(__file__), "cli.py"),
               encoding="utf-8").read()
    g = src[src.index("def cmd_finalize("):]
    g = g[:g.index("def cmd_capraz(")]
    eq('doc = json.load(open(a.summaries, encoding="utf-8")) if a.summaries else {}'
       not in g, True, "ozetsiz sessiz gecis kalmamali")
    eq('ozet_yolu = a.summaries or os.path.join(OUT, "ozet.json")' in g, True,
       "-s yoksa varsayilan ozet dosyasi kullanilmali")
    eq("return 1" in g, True, "ozet hic yoksa finalize hata vermeli")


def test_elle_besleme_kanali():
    """v19 (2026-08-29): bot korumasindaki yayinlar icin elle besleme.

    On bes kaynak sorunlu: yedisi 403/429 (SMS group, ArcelorMittal, STI,
    BigMint, MetalMiner, Furnaces Int, Cognex), yedisinde sayfa aciliyor ama
    link cikmiyor, biri 404. Editorun kendi oturumu da ayni egress proxy'nin
    arkasinda - o da bu sitelere giremiyor. Cozum: editor basliklari ARAMA
    ile bulur, dosyaya BASLIK + ADRES yazar; tarihi Actions makale sayfasini
    acarak dogrular.

    KRITIK KURAL: dosya TARIH TASIMAZ. Editorun beyan ettigi bir tarih
    rapora asla giremez - "tarih uydurulmaz" kurali bu kanalda da gecerli.

    v20c (2026-08-29) - TARIHI KIM DOGRULAR? Kanalin ilk hali OLCULDU ve
    15 kaydin 14'u "tarihsiz_elendi" ile dustu; kanal HIC satir uretmedi.
    Tasarim hatasi bendeydi: tarihin "Actions'ta makale sayfasi acilarak"
    dogrulanacagini varsaymistim, oysa bu yayinlar zaten bot korumasinda -
    makale sayfasi da 403. Kapali yayinin sayfasi kapaliysa tarihi de
    kapalidir. Tarih artik ULASILABILIR bir beslemeden (Google News RSS,
    yayincinin kendi pubDate'i) baslik ortusmesi araniyor; ortusme yoksa
    tarih yok, satir da yok. Editor yine tarih beyan etmiyor.
    """
    import json as _json
    import os as _os
    import radar.collect as col

    kok = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    yol = _os.path.join(kok, "veri", "elle_besleme.json")
    eq(_os.path.exists(yol), True, "elle besleme dosyasi bulunmali")
    d = _json.load(open(yol, encoding="utf-8"))

    # Dosya TARIH ALANI TASIMAMALI - bu kuralin bekcisi
    for k in d.get("kayitlar", []):
        for alan in ("tarih", "date", "tarih_kaynagi", "pubDate"):
            eq(alan in k, False, "elle beslemede tarih alani olmamali: " + alan)
        eq(k.get("url", "").startswith("http"), True, "adres http ile baslamali")
        eq(len(k.get("baslik", "").split()) >= 4, True,
           "baslik anlamli olmali: " + k.get("baslik", "")[:40])

    # Okuyucu dogru calismali ve tarih URETMEMELI
    kaynak = dict(id="elle", publisher="Elle besleme", kind="dergi",
                  dosya="veri/elle_besleme.json")
    # Aginin olmadigi yerde tarih dogrulama BOS doner, cokmez
    eski_fetch = col.http.fetch
    try:
        col.http.fetch = lambda u, **kw: (False, "", {"hata": "ag yok"})
        items, err = col._items_from_dosya(kaynak, lambda *a: None)
        eq(err, None, "dosya okunabilmeli")
        eq(len(items), len(d["kayitlar"]), "tum kayitlar aday olmali")
        for it in items:
            eq(it["date_raw"], "", "dogrulanamayan tarih URETILMEZ")
            eq(it.get("from_feed", False), False, "tarih yoksa yapisal isaret de yok")

        # BASLIK ORTUSURSE yayincinin kendi pubDate'i alinir
        besleme = ('<rss><channel><item>'
                   '<title>SMS upgrades Hyundai Steel galvanising line</title>'
                   '<link>https://news.google.com/x</link>'
                   '<pubDate>Tue, 25 Aug 2026 09:00:00 GMT</pubDate>'
                   '</item></channel></rss>')
        col.http.fetch = lambda u, **kw: (True, besleme, {"final": u})
        eq(col._elle_tarih("SMS upgrades Hyundai Steel galvanising line",
                           lambda *a: None)[:3], "Tue",
           "ortusen baslikta yayincinin tarihi alinmali")

        # BASLIK ORTUSMEZSE tarih ALINMAZ - baska haberin tarihini bu
        # baslıga yapistirmak, tarih uydurmakla ayni sonucu verir
        eq(col._elle_tarih("Ternium contracts Fives for new galvanizing line",
                           lambda *a: None), "",
           "ortusmeyen baslikta tarih alinmamali")

        # Olcutun kendisi: tekrar elemenin toleransi burada KULLANILAMAZ.
        # taxonomy.similar_titles bu iki basligi AYNI sayiyor (ortak
        # "galvanizing line"); tekrar elemede bu dogru, tarih atamada ise
        # baska bir haberin tarihini bu basliga yapistirir.
        a = "SMS upgrades Hyundai Steel galvanising line"
        b = "Ternium contracts Fives for new galvanizing line"
        eq(taxonomy.similar_titles(a, b), True,
           "tekrar olcutu bu ikiliyi ayni sayar - vakanin dayanagi")
        eq(col._ayni_baslik(a, b), False,
           "tarih olcutu ayni saymamali")
        eq(col._ayni_baslik(a, "SMS upgrades Hyundai Steel galvanising line"),
           True, "birebir baslik ortusmeli")
    finally:
        col.http.fetch = eski_fetch

    # Kayip dosya cokmemeli
    _, err2 = col._items_from_dosya(dict(dosya="veri/yok.json"), lambda *a: None)
    eq(err2, "dosya yok", "kayip dosya nazikce bildirilmeli")

    # Adaylar kapsam kapisindan gecmeli - kanal muafiyet DEGIL
    kapsam_ici = sum(1 for it in items
                     if taxonomy.in_scope(it["title"], "")[0]
                     and taxonomy.haber_olayi(it["title"]))
    eq(kapsam_ici >= 4, True,
       "beslemedeki adaylarin cogu kapsam kapisini gecmeli (gecen: %d)" % kapsam_ici)


def test_sitemap_okuyucu():
    """v6 (2026-08-17): haber sitemap'i kaynak turu.

    Olcum: 2026-02-01..08-17 arasindaki 25 kapsam ici haberin 18'i (%72)
    Steel Times International + SteelOrbis'ten cikti. STI'nin /news sayfasi
    bota 403 veriyordu, yani havuzun en verimli kaynagi sisteme hic
    girmiyordu. Sitemap yolu 403 vermiyor VE basligi adresin icinde tasiyor,
    boylece kapsam elemesi makale acilmadan yapilabiliyor.
    """
    import radar.collect as col

    # Baslik adresten dogru cikarilmali (sondaki haber numarasi atilir)
    eq(col.slug_baslik(
        "https://www.steelorbis.com/steel-news/latest-news/"
        "kg-steel-selects-primetals-for-dangjin-pltcm-upgrade-1470187.htm"),
       "kg steel selects primetals for dangjin pltcm upgrade",
       "SteelOrbis slug basligi")
    eq(col.slug_baslik(
        "https://www.steeltimesint.com/news/primetals-to-modernise-korean-pickling-line"),
       "primetals to modernise korean pickling line", "STI slug basligi")
    eq(col.slug_baslik("https://x.com/news/2026-06-11-saritas-group"),
       "saritas group", "bastaki tarih atilmali")

    # SITEMAP ZINCIRI (2026-08-27): STI hem /news hem sitemap adresinde 403,
    # Mysteel'in adresleri 404 veriyor. Tek adres yerine zincir denenir ve
    # aday RSS cikarsa besleme olarak ayristirilir.
    import radar.http as H
    RSS = ('<?xml version="1.0"?><rss><channel><item>'
           '<title>Primetals to modernise Korean pickling line</title>'
           '<link>https://x/1</link>'
           '<pubDate>Mon, 24 Aug 2026 10:00:00 +0000</pubDate></item></channel></rss>')

    def _sahte(u, use_cache=True):
        if u.endswith("-sitemap.xml"):
            return False, "", {"status": 403, "hata": "HTTP 403"}
        if u.endswith("sitemap.xml"):
            return False, "", {"status": 404, "hata": "HTTP 404"}
        if u.endswith("/feed"):
            return True, RSS, {"status": 200, "final": u}
        return False, "", {"status": 404, "hata": "HTTP 404"}

    eski_fetch = H.fetch
    try:
        H.fetch = _sahte
        kaynak = dict(id="sti", publisher="STI", kind="dergi",
                      sitemaps=["https://x/a-sitemap.xml", "https://x/sitemap.xml",
                                "https://x/feed"])
        items, err = col._sitemap_zinciri(kaynak, lambda *a: None)
    finally:
        H.fetch = eski_fetch
    eq(err, None, "zincir ucuncu adreste tutmali")
    eq(len(items), 1, "besleme ayristirilmali")
    eq(items[0]["title"], "Primetals to modernise Korean pickling line", "besleme basligi")
    eq(items[0].get("from_feed"), True, "besleme isareti")


    # Slug basligi kapsam + olay kapisindan gecmeli (makale acilmadan)
    for slug in ("primetals to modernise korean pickling line",
                 "kg steel selects primetals for dangjin pltcm upgrade"):
        ok, _ = taxonomy.in_scope(slug, "")
        eq(ok and taxonomy.haber_olayi(slug), True,
           "slug baslik kapiyi gecmeli: " + slug[:40])

    # Sitemap XML ayristirmasi
    xml = ("""<?xml version="1.0"?><urlset>"""
           """<url><loc>https://a.com/news/danieli-to-supply-pickling-line-to-acme</loc>"""
           """<lastmod>2026-08-14T10:00:00+03:00</lastmod></url>"""
           """<url><loc>https://a.com/news/contact</loc><lastmod>2026-08-15</lastmod></url>"""
           """<url><loc>https://a.com/news/tenova-awarded-cold-mill-revamp-brazil</loc>"""
           """<lastmod>2026-08-16</lastmod></url></urlset>""")
    got = []

    class _FakeHttp(object):
        @staticmethod
        def fetch(url, use_cache=True):
            return True, xml, {"status": 200, "final": url}

    real = col.http
    try:
        col.http = _FakeHttp
        items, err = col._items_from_sitemap(
            {"sitemap": "https://a.com/sm.xml"}, lambda *a: None)
    finally:
        col.http = real
    eq(err, None, "sitemap okunmali")
    eq(len(items), 2, "kisa/menu adresi ('contact') elenmeli")
    eq(items[0]["url"].endswith("tenova-awarded-cold-mill-revamp-brazil"), True,
       "en yeni lastmod basta olmali")
    eq(all(i.get("_sitemap") for i in items), True,
       "_sitemap isareti sart - lastmod'a dusulmesin diye")
    eq(items[0]["date_raw"], "2026-08-16", "lastmod okunmali (yalniz kesif icin)")


def test_olculen_25_haber():
    """2026-02-01..08-17 arasinda ELLE OLCULEN 25 gercek kapsam ici haber.

    Bu vakalar uydurulmadi: alti buçuk aylik donemde kapsam tanimina birebir
    uyan haberler tek tek dogrulanip sayildi (haftalik ortalama 0,83; haftalarin
    %40'i sifir). Filtrenin isi bu 25'i kaybetmemek. Asagidakiler YALNIZ
    BASLIKTAN yakalanmali - govde yardimi olmadan.
    """
    def gecer(b):
        tb = taxonomy.temiz_baslik(b)
        ok, _ = taxonomy.in_scope(tb, "")
        if ok and taxonomy.haber_olayi(tb):
            return "Hat"
        return "Yatirim" if taxonomy.genel_yatirim(tb) else None

    for b in [
        # ciplak "starts" + hat adi
        "Ternium starts cold rolling and galvanizing lines in Mexico",
        # "restart"
        "US Steel to restart Gary tin mill",
        # "annealing furnace" kapsam bosluguydu
        "Fives signs contract with Yongfeng Group for annealing furnaces",
        "CERI Technology Company awards annealing furnace contract to ANDRITZ",
        # fiilsiz tedarikci duyurusu: "new" + hat adi
        "New MINO Double-Stand Six-High Cold Reversing Mill in North America",
        # "to invest ... ramp up"
        "India's Jindal Stainless to invest $94 million to ramp up cold "
        "rolling capacity",
        # muteahhit atamasi (kisi atamasi degil)
        "Welsh contractor appointed for pickle line construction at Port Talbot",
        # olculen donemden diger dogrulanmis vakalar
        "SMS upgrades Hyundai Steel galvanising line",
        "Gazi Metal orders new roll grinder from Pomini Tenova",
        "India's JIL commissions continuous colour coating line",
        "Tenova I2S awarded 6-Hi cold rolling mill modernization in Brazil",
        "Eastern Steel commissions 650,000 mt temper mill in Malaysia",
        "Tosyali Algerie produces first cold rolled products at new complex",
        "KG Steel selects Primetals for Dangjin PLTCM upgrade",
        "Primetals Technologies to upgrade Shougang Shunyi pickling line and "
        "tandem cold mill automation",
        "Granite City Processing orders Butech Bliss stretch levelling "
        "cut-to-length line",
        "Fives to supply full electrical steel lines to Sanbao Group",
    ]:
        eq(gecer(b) is not None, True, "olculen haber kaybolmamali: " + b[:48])

    # ...ve ayni donemde ELENMESI gereken, ayni sayfalarda duran satirlar
    for b in [
        "Nippon Steel completes 6MT hot rolling line",
        "Hybar orders continuous minimill from SMS group",
        "Danieli installs billet grinding machine in China",
        "Nucor reports earnings increase in Q2",
        "How does the European market view quota system changes",
        "Turkish motor vehicle output down 8.1 percent in Jan-July 2026",
    ]:
        eq(gecer(b), None, "kapsam disi kalmali: " + b[:48])


def test_cin_katmani():
    """v7 (2026-08-17): Cince kaynak destegi.

    Olcum: 3-17 Agustos 2026'da Bati basini gercekten bostu (yaz durusu) ama
    Mysteel ayni iki haftada ekipman sozlesmesi yayinladi ve havuz gormedi.
    Sebep tek bir satirdi: is_junk_title kelime sayisina bakiyordu, Cince'de
    ise BOSLUK YOK - her Cince baslik "cok kisa" sayilip eleniyordu.
    """
    # Cince baslik artik cop sayilmamali
    eq(taxonomy.is_junk_title("\u9540\u950c\u673a\u7ec4\u9879\u76ee\u5408\u540c\u7b7e\u8ba2"), False,
       "Cince baslik cop sayilmamali (bosluk yok)")
    eq(taxonomy.is_junk_title("\u94a2"), True, "tek karakter yine cop")

    def gecer(b):
        ok, _ = taxonomy.in_scope(b, "")
        if ok and taxonomy.haber_olayi(b):
            return "Hat"
        return "Yatirim" if taxonomy.genel_yatirim(b) else None

    # GECMELI - gercek Cince hat duyurulari
    for b, ne in [
        ("\u9632\u57ce\u6e2f\u699b\u6cf01\u53f7\u9540\u950c\u673a\u7ec4\u9879\u76ee\u5408\u540c\u7b7e\u8ba2", "galvaniz hatti sozlesmesi"),
        ("\u9996\u94a2\u51b7\u8f67\u9178\u6d17\u8fde\u8f67\u673a\u7ec4\u81ea\u52a8\u5316\u6539\u9020", "PLTCM otomasyon modernizasyonu"),
        ("\u67d0\u94a2\u5382\u5f69\u6d82\u673a\u7ec4\u6295\u4ea7", "boyama hatti devreye alindi"),
        ("\u8fde\u7eed\u9000\u706b\u673a\u7ec4\u5408\u540c\u7b7e\u8ba2", "surekli tavlama sozlesmesi"),
        ("\u5b9d\u94a2\u9540\u9521\u673a\u7ec4\u6295\u4ea7", "teneke hatti devreye alindi"),
    ]:
        eq(gecer(b), "Hat", "Cince hat haberi gecmeli: " + ne)

    # ELENMELI - ayni sayfalarda duran Cince gurultu ve yukari akis
    for b, ne in [
        ("\u5e7f\u4e1c\u91d1\u6657\u51701780\u6beb\u7c73\u70ed\u8fde\u8f67\u9879\u76ee\u5408\u540c\u7b7e\u8ba2", "SICAK hadde"),
        ("\u672c\u5468\u51b7\u8f67\u677f\u5377\u4ef7\u683c\u8c03\u4ef7", "fiyat"),
        ("7\u6708\u7c97\u94a2\u4ea7\u91cf\u540c\u6bd4\u589e\u957f", "uretim istatistigi"),
        ("\u67d0\u516c\u53f8\u9ad8\u7089\u5927\u4fee\u5b8c\u6210", "yuksek firin"),
    ]:
        eq(gecer(b), None, "Cince kapsam disi elenmeli: " + ne)

    # Mysteel adres bicimi tarih verir (on eleme icin)
    eq(dates.date_from_url("https://news.mysteel.com/a/26081415/CA0AAA8FC351E3AA.html",
                           dt.date(2026, 8, 17)), "2026-08-14", "Mysteel adres tarihi")


def run():
    for fn in (test_dates, test_article_date_chain, test_firm, test_scope,
               test_line_and_stage, test_listing_parser, test_feed_parser,
               test_state, test_build_row, test_w33_regresyon, test_w33b_regresyon,
               test_w33c_regresyon, test_w33d_regresyon, test_uclu_kg_senaryosu,
               test_iki_katmanli_liste, test_kapsam_havuzu, test_tarih_acilari,
               test_olay_kapisi_v5, test_w34_sicak_hadde,
               test_niyet_kapisi_ilk_urun, test_capraz_kontrol,
               test_w35_katman2_kapsam_kapisi, test_w35_ornek_kosu,
               test_rezerv_ve_teknoloji_havuzu,
               test_rezervin_ortaya_cikardigi_delikler,
               test_gunluk_tarama_modu, test_rezerv_tekrar_denetimi,
               test_elle_besleme_kanali,
               test_v20_sitemap_geri_dusus,
               test_v20_gonderilmis_hafiza,
               test_v20_gunluk_tarama_arsivi_ezmez,
               test_v20_indiana_hindistan_degil,
               test_w36_girisim_turu_hat_haberi_degil,
               test_w36_ocak_parcasi_tavlama_firini_degildir,
               test_w36_pencere_uc_hafta,
               test_w36_kose_kendi_kapisi_ve_turkiye_katmani,
               test_w36_rezerv_kalici_hafizayi_sorar,
               test_w36_pota_galvaniz_hat_degildir,
               test_w36_yayinci_kuyrugu,
               test_w36_editor_bulur_makine_dogrular,
               test_w36_adres_ve_teknoloji_havuzu,
               test_w36_bulunan_havuzu_ve_yanlis_tekrar,
               test_w36_havuz_karari_tasir_kodu_degil,
               test_w36_bing_katmaninin_actigi_uc_delik,
               test_w36_host_korumasi_ve_ikinci_arama_hostu,
               test_w36_aci7_geri_alindi_paylasilan_host,
               test_w36_tekrar_ve_kose_yonu,
               test_w36_finalize_ozetsiz_calismaz,
               test_w34_sifir_satir_teshisi,
               test_teknoloji_ve_ai_bolumleri,
               test_sitemap_okuyucu, test_olculen_25_haber,
               test_cin_katmani,
               test_compose_ve_mail):
        try:
            fn()
        except Exception as e:
            FAILS.append("%s PATLADI: %s: %s" % (fn.__name__, type(e).__name__, e))
    if FAILS:
        print("SELFTEST BASARISIZ (%d):" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        return 1
    print("selftest: tum testler gecti")
    return 0
