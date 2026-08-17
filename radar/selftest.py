# -*- coding: utf-8 -*-
"""Agsiz birim testleri.

Her test, gecmiste GERCEKTEN yasanmis bir hatanin tekrarini engeller.
GitHub Actions her kosudan ONCE bunu calistirir; kirmizi ise haftalik
kosu hic baslamaz - bozuk mantikla rapor uretmektense rapor uretmemek yegdir.
"""
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
    """2026-08-12 karari: haftalik DOLU liste. Yatirim katmani dunya geneli
    celik yatirim haberlerini alir; fiyat/borsa/rapor-satisi yine giremez."""
    ok = [("Kocaer Çelik ABD'de Üretim İçin Şirket Kuruyor", True),
          ("Nucor announces new sheet mill investment in West Virginia", True),
          ("Baowu Group and SNS eye green steel plant investment in Algeria", True),
          ("Jindal plans Rs 40,000 crore investment in new steel facility", True),
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
                  "Soğuk Haddehane", "Öne Çıkan Teknolojileri",
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
    eq(taxonomy.watch_worthy("Kocaer Çelik ABD'de Üretim İçin Şirket Kuruyor"),
       True, "watch: TR yatirim")
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
    eq(taxonomy.genel_yatirim(tr), True,
       "kapasite yatirimi olarak Katman 2'de kalabilir")
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
               test_niyet_kapisi_ilk_urun,
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
