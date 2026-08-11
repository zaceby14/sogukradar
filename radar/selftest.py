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
                  "tek tek açılıp", "Lazer kesim"):
        eq(parca in mail, True, "mailde eksik: " + parca)
    eq("Yönetici özeti" in mail, False, "eski baslik kalmamali")


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


def run():
    for fn in (test_dates, test_article_date_chain, test_firm, test_scope,
               test_line_and_stage, test_listing_parser, test_feed_parser,
               test_state, test_build_row, test_w33_regresyon, test_compose_ve_mail):
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
