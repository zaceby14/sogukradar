# -*- coding: utf-8 -*-
"""SogukRadar kaynak rosteri.

Alanlar
-------
id         : dosya/log anahtari (benzersiz)
publisher  : rapora yazilan yayinci adi
kind       : oem | dergi | kurum
url        : haber LISTE sayfasi (zorunlu)
rss        : bilinen besleme adresi; None ise `radar discover` bulmaya calisir
country    : merkez ulke (bilgi amacli)
verified   : 2026-08 kosusunda erisildigi FIILEN dogrulandi mi
note       : bilinen kisit

Onemli: verified=False olan satirlar "calisiyor" varsayimi degildir.
`radar check` her kaynagi tek tek dener ve out/source_health.json yazar;
calismayan kaynak rapordaki KOR NOKTA blogunda acikca listelenir.
Boylece kapsam eksigi sessizce kaybolmaz.
"""

SOURCES = [
    # ------------------------------------------------------------------
    # OEM / ekipman ureticileri - birincil kaynak.
    # Sozlesme, devreye alma, ilk bobin haberleri once buradan cikar.
    # ------------------------------------------------------------------
    dict(id="danieli",       publisher="Danieli",                 kind="oem", country="IT",
         url="https://www.danieli.com/en/news-media/news_37.htm", rss=None, verified=True),
    dict(id="tenova",        publisher="Tenova",                  kind="oem", country="IT",
         url="https://www.tenova.com/news", rss=None, verified=True),
    dict(id="primetals",     publisher="Primetals Technologies",  kind="oem", country="GB",
         url="https://www.primetals.com/press-media/news", rss=None, verified=True),
    dict(id="johncockerill", publisher="John Cockerill",          kind="oem", country="BE",
         url="https://johncockerill.com/en/news/", rss=None, verified=True),
    dict(id="andritz",       publisher="Andritz Metals",          kind="oem", country="AT",
         url="https://www.andritz.com/newsroom-en/metals", rss=None, verified=True),
    dict(id="smsgroup",      publisher="SMS group",               kind="oem", country="DE",
         url="https://www.sms-group.com/en/press-and-media/press-releases", rss=None,
         verified=False, note="WebFetch 403 donuyordu; sunucu tarafinda tekrar denenecek"),
    dict(id="fives",         publisher="Fives Group",             kind="oem", country="FR",
         url="https://www.fivesgroup.com/news-press", rss=None, verified=False),
    dict(id="clecim",        publisher="Clecim",                  kind="oem", country="FR",
         url="https://www.clecim.com/news", rss=None, verified=False),
    dict(id="redex",         publisher="Redex Group",             kind="oem", country="FR",
         url="https://www.redex-group.com/en/news/", rss=None, verified=False),
    dict(id="butechbliss",   publisher="Butech Bliss",            kind="oem", country="US",
         url="https://butechbliss.com/news/", rss=None, verified=False),
    dict(id="herkules",      publisher="Herkules Group",          kind="oem", country="DE",
         url="https://www.herkulesgroup.com/en/news", rss=None, verified=False),
    dict(id="achenbach",     publisher="Achenbach Buschhutten",   kind="oem", country="DE",
         url="https://www.achenbach.de/en/news/", rss=None, verified=False),
    dict(id="sundwig",       publisher="Andritz Sundwig",         kind="oem", country="DE",
         url="https://www.andritz.com/newsroom-en", rss=None, verified=False,
         note="Sundwig haberleri Andritz newsroom altinda cikiyor"),
    dict(id="ebner",         publisher="Ebner Industrieofenbau",  kind="oem", country="AT",
         url="https://www.ebner.cc/en/news/", rss=None, verified=False),
    dict(id="drever",        publisher="Drever International",    kind="oem", country="BE",
         url="https://www.drever.be/news/", rss=None, verified=False),
    dict(id="nseng",         publisher="Nippon Steel Engineering", kind="oem", country="JP",
         url="https://www.eng.nipponsteel.com/english/whatsnew/", rss=None, verified=False),
    dict(id="abbmetals",     publisher="ABB Metals",              kind="oem", country="CH",
         url="https://new.abb.com/metals/news", rss=None, verified=False),
    dict(id="isravision",    publisher="ISRA Vision (Atlas Copco)", kind="oem", country="DE",
         url="https://www.isravision.com/en/news/", rss=None, verified=False,
         note="yuzey muayene (SIS)"),
    dict(id="cognex",        publisher="Cognex",                  kind="oem", country="US",
         url="https://www.cognex.com/company/news-events/press-releases", rss=None,
         verified=False, note="yuzey muayene (SIS)"),
    dict(id="sarralle",      publisher="Sarralle",                kind="oem", country="ES",
         url="https://www.sarralle.com/en/news/", rss=None, verified=False),
    dict(id="delta",         publisher="Delta Steel Technologies", kind="oem", country="US",
         url="https://www.deltasteeltech.com/news/", rss=None, verified=False),
    dict(id="bronx",         publisher="Bronx International",     kind="oem", country="US",
         url="https://www.bronxintl.com/news/", rss=None, verified=False),

    # ------------------------------------------------------------------
    # Dergi / sektor haber siteleri - OEM'in duyurmadigi yatirimi yakalar.
    # ------------------------------------------------------------------
    dict(id="steeltimesint", publisher="Steel Times International", kind="dergi", country="GB",
         url="https://www.steeltimesint.com/news", rss=None, verified=True),
    dict(id="steelturk",     publisher="SteelTurk",               kind="dergi", country="TR",
         url="https://www.steelturk.net/", rss=None, verified=False, lang="tr"),
    dict(id="steelradar",    publisher="Steel Radar",             kind="dergi", country="TR",
         url="https://www.steelradar.com/en/news", rss=None, verified=False),
    dict(id="steelorbis",    publisher="SteelOrbis",              kind="dergi", country="TR",
         url="https://www.steelorbis.com/steel-news/latest-news/", rss=None, verified=False,
         note="liste sayfasinda tarih gorunmuyordu; makale sayfasindan tarih cekilecek"),
    dict(id="eurometal",     publisher="EUROMETAL",               kind="dergi", country="LU",
         url="https://eurometal.net/", rss=None, verified=True),
    dict(id="kallanish",     publisher="Kallanish",               kind="dergi", country="GB",
         url="https://www.kallanish.com/en/news/steel/", rss=None, verified=False,
         note="cogu icerik odeme duvarinda; sadece baslik+tarih kullanilir"),
    dict(id="gmk",           publisher="GMK Center",              kind="dergi", country="UA",
         url="https://gmk.center/en/news/", rss=None, verified=False),
    dict(id="aist",          publisher="AIST",                    kind="kurum", country="US",
         url="https://www.aist.org/news-events/", rss=None, verified=False,
         note="liste JavaScript ile yukleniyordu; RSS aranacak"),
    dict(id="canmaker",      publisher="The Canmaker",            kind="dergi", country="GB",
         url="https://canmaker.com/news/", rss=None, verified=True,
         note="teneke (ETL) tarafi icin"),
    dict(id="magnetics",     publisher="Magnetics Magazine",      kind="dergi", country="US",
         url="https://magneticsmag.com/news/", rss=None, verified=False,
         note="elektrik celigi (CRGO/CRNO) tarafi icin"),
    dict(id="yieh",          publisher="Yieh Corp",               kind="dergi", country="TW",
         url="https://www.yieh.com/en/News/", rss=None, verified=False),
    dict(id="worldsteel",    publisher="worldsteel",              kind="kurum", country="BE",
         url="https://worldsteel.org/media/press-releases/", rss=None, verified=False),
]

# Sadece bilgi: neyi bilerek disarida biraktik.
KNOWN_GAPS = [
    ("Cin yerel OEM'leri (CISDI, MCC)", "yalniz Cince yayin, ceviri maliyeti yuksek"),
    ("Fastmarkets / Argus", "tam odeme duvari, baslik bile acik degil"),
    ("LinkedIn duyurulari", "giris zorunlu, otomatik cekilemiyor"),
]


def by_id(sid):
    for s in SOURCES:
        if s["id"] == sid:
            return s
    return None


def active(kinds=None):
    if not kinds:
        return list(SOURCES)
    return [s for s in SOURCES if s["kind"] in kinds]
