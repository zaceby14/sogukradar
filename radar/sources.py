# -*- coding: utf-8 -*-
"""SogukRadar kaynak rosteri - 2026-W33 kalibrasyon kosusundan sonra duzeltildi.

Alanlar
-------
id         : dosya/log anahtari (benzersiz)
publisher  : rapora yazilan yayinci adi
kind       : oem | dergi | kurum
url        : haber LISTE sayfasi (zorunlu)
rss        : bilinen besleme adresi; None ise `radar discover` bulmaya calisir
lang       : "tr" ise Turkce kapsam sozlugu de calisir
country    : merkez ulke (bilgi amacli)
verified   : adres GERCEK bir istekle dogrulandi mi
note       : bilinen kisit

verified=False satirlar "calisiyor" varsayimi degildir. Erisilemeyen kaynak
raporun basindaki KOR NOKTA blogunda listelenir - kapsam eksigi sessizce
kaybolmaz.
"""

SOURCES = [
    # ------------------------------------------------------------------
    # OEM / ekipman ureticileri
    # ------------------------------------------------------------------
    dict(id="danieli",       publisher="Danieli",                 kind="oem", country="IT",
         url="https://www.danieli.com/en/news.htm", rss=None, verified=True,
         note="eski adres (news_37.htm) 403 veriyordu"),
    dict(id="tenova",        publisher="Tenova",                  kind="oem", country="IT",
         url="https://www.tenova.com/news", rss=None, verified=True),
    dict(id="primetals",     publisher="Primetals Technologies",  kind="oem", country="GB",
         url="https://www.primetals.com/press-media/news", rss=None, verified=True),
    dict(id="johncockerill", publisher="John Cockerill",          kind="oem", country="BE",
         url="https://johncockerill.com/en/press-and-news/news/", rss=None, verified=True),
    dict(id="andritz",       publisher="Andritz Metals",          kind="oem", country="AT",
         url="https://www.andritz.com/newsroom-en/metals", rss=None, verified=True),
    dict(id="smsgroup",      publisher="SMS group",               kind="oem", country="DE",
         url="https://www.sms-group.com/press-and-media/press-releases", rss=None,
         verified=False, note="Cloudflare bot korumasi; tarayici basliklariyla deneniyor"),
    dict(id="fives",         publisher="Fives Group",             kind="oem", country="FR",
         url="https://www.fivesgroup.com/newspress", rss=None, verified=True),
    dict(id="clecim",        publisher="Clecim",                  kind="oem", country="FR",
         url="https://www.clecim.com/news", rss=None, verified=False),
    dict(id="butechbliss",   publisher="Butech Bliss",            kind="oem", country="US",
         url="https://butechbliss.com/latest-news/", rss=None, verified=True),
    dict(id="herkules",      publisher="Herkules Group",          kind="oem", country="DE",
         url="https://www.herkulesgroup.com/news/", rss=None, verified=True),
    dict(id="achenbach",     publisher="Achenbach Buschhutten",   kind="oem", country="DE",
         url="https://www.achenbach.de/en/company/newsroom/", rss=None, verified=True,
         note="listede tarih yok; tarih makale sayfasindan alinir"),
    dict(id="ebner",         publisher="Ebner Industrieofenbau",  kind="oem", country="AT",
         url="https://www.ebner.cc/en/news/", rss=None, verified=False),
    dict(id="nseng",         publisher="Nippon Steel Engineering", kind="oem", country="JP",
         url="https://www.eng.nipponsteel.com/english/whatsnew/", rss=None, verified=False),
    dict(id="abbmetals",     publisher="ABB Metals",              kind="oem", country="CH",
         url="https://www.abb.com/global/en/company/media?filter=Business%3AMetals",
         rss=None, verified=False, note="dusuk guven: filtreli genel medya sayfasi"),
    dict(id="isravision",    publisher="ISRA Vision (Atlas Copco)", kind="oem", country="DE",
         url="https://www.isravision.com/en-en/company/newsroom", rss=None, verified=True,
         note="yuzey muayene (SIS)"),
    dict(id="cognex",        publisher="Cognex",                  kind="oem", country="US",
         url="https://www.cognex.com/en/company/press-releases", rss=None,
         verified=False, note="bot korumasi (429); yuzey muayene"),
    dict(id="bronx",         publisher="The Bronx Group",         kind="oem", country="US",
         url="https://thebronxgroup.com/news/", rss=None, verified=True,
         note="firma 'Bronx International' adindan degisti"),
    dict(id="delta",         publisher="Delta Steel Technologies", kind="oem", country="US",
         url="https://www.deltasteeltech.com/news/", rss=None, verified=False),

    # ------------------------------------------------------------------
    # Dergi / sektor haber siteleri
    # ------------------------------------------------------------------
    dict(id="steeltimesint", publisher="Steel Times International", kind="dergi", country="GB",
         url="https://www.steeltimesint.com/news", rss=None, verified=True,
         note="sunucu IP'sinden 403 gelebiliyor"),
    dict(id="steelturk",     publisher="SteelTurk",               kind="dergi", country="TR",
         url="https://www.steelturk.com.tr/global-celik-haberleri/", rss=None,
         verified=True, lang="tr", note="dogru alan adi .com.tr (.net degil)"),
    dict(id="steelradar",    publisher="Steel Radar",             kind="dergi", country="TR",
         url="https://www.steelradar.com/en/", rss=None, verified=True),
    dict(id="metaldunyasi",  publisher="Metal Dunyasi",           kind="dergi", country="TR",
         url="https://metaldunyasi.com.tr/tr/sektorel-haberler/20/demir-elik/",
         rss=None, verified=True, lang="tr"),
    dict(id="steelorbis",    publisher="SteelOrbis",              kind="dergi", country="TR",
         url="https://www.steelorbis.com/steel-news/latest-news/", rss=None, verified=True),
    dict(id="eurometal",     publisher="EUROMETAL",               kind="dergi", country="LU",
         url="https://eurometal.net/news/", rss="https://eurometal.net/feed/",
         verified=True, note="WordPress beslemesi - tarih yapisal gelir"),
    dict(id="canmaker",      publisher="The Canmaker",            kind="dergi", country="GB",
         url="https://canmaker.com/news/", rss="https://canmaker.com/feed",
         verified=True, note="teneke (ETL); WordPress beslemesi"),
    dict(id="kallanish",     publisher="Kallanish",               kind="dergi", country="GB",
         url="https://www.kallanish.com/en/news/steel/live", rss=None, verified=True,
         note="tam metin odeme duvarinda; baslik+tarih kullanilir"),
    dict(id="gmk",           publisher="GMK Center",              kind="dergi", country="UA",
         url="https://gmk.center/en/news/", rss=None, verified=True),
    dict(id="meps",          publisher="MEPS International",      kind="dergi", country="GB",
         url="https://mepsinternational.com/gb/en/news", rss=None, verified=True),
    dict(id="steelguru",     publisher="SteelGuru",               kind="dergi", country="IN",
         url="https://www.steelguru.com/", rss=None, verified=True,
         note="goreli tarih ('2 hours ago') - kod bunu cozuyor"),
    dict(id="magnetics",     publisher="Magnetics Magazine",      kind="dergi", country="US",
         url="https://magneticsmag.com/magnetics-news/", rss=None, verified=True,
         note="elektrik celigi (CRGO/CRNO)"),
    dict(id="yieh",          publisher="Yieh Corp",               kind="dergi", country="TW",
         url="https://www.yieh.com/en/News/", rss=None, verified=True),
    dict(id="fastmarkets",   publisher="Fastmarkets",             kind="dergi", country="GB",
         url="https://www.fastmarkets.com/metals-and-mining/steel-and-steel-raw-materials/",
         rss=None, verified=True, note="cogu icerik odeme duvarinda"),

    # ------------------------------------------------------------------
    # Kurum
    # ------------------------------------------------------------------
    dict(id="worldsteel",    publisher="worldsteel",              kind="kurum", country="BE",
         url="https://worldsteel.org/media/press-releases/",
         rss="https://worldsteel.org/feed/", verified=True),
    dict(id="aist",          publisher="AIST",                    kind="kurum", country="US",
         url="https://www.aist.org/news-events/", rss=None, verified=False,
         note="liste JavaScript ile yukleniyor olabilir"),
]

# Bilerek disarida birakilanlar - raporda acikca gorunur.
KNOWN_GAPS = [
    ("Redex Group", "sitesinde haber/basin bolumu yok"),
    ("Drever International", "tum adresler bot korumasiyla 403 doneyor"),
    ("Sarralle", "haber listesi JavaScript ile yukleniyor"),
    ("Cin yerel OEM'leri (CISDI, MCC)", "yalniz Cince yayin"),
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
