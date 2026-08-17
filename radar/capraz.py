# -*- coding: utf-8 -*-
"""Capraz kontrol - haftalik listenin KACIRDIKLARINI bulur.

NEDEN AYRI BIR KOMUT (2026-08-17 karari)
----------------------------------------
Editorun her hafta yaptigi elle capraz kontrol -- "STI + SteelOrbis +
Mysteel sitemap'lerini ac, son 15 gunun basliklarina bak, listede olmayan
kapsam ici haber var mi" -- editorun kendi kum havuzunda YAPILAMIYOR: o
oturumun ag cikisi yalnizca paket depolarina ve GitHub'a aciktir, haber
alan adlari egress proxy'sinde 403 alir. Actions kosucusunun interneti ise
tam aciktir; is bu yuzden buraya tasindi.

Cikti out/kacanlar.json'dur. Bu dosya BULTEN DEGILDIR - editorun okudugu
bir denetim listesidir. Icindeki bir satirin bultene girmesi icin editor
ayrica bakar (ornegin haber daha once teknoloji kosesinde cikmis olabilir;
capraz kontrol bunu bilmez).

TARIH KURALI BURADA DA GECERLIDIR. Sitemap'teki <lastmod> yayin tarihi
DEGILDIR (bkz. collect._items_from_sitemap). Bu yuzden kapiyi gecen ve
listede bulunmayan her aday icin makale sayfasi ACILIR ve tarih
dates.extract_article_date zinciriyle sayfadan dogrulanir. Dogrulanamayan
aday cikti dosyasina "kacan" olarak YAZILMAZ; ayri bir listede sebebiyle
birlikte durur.
"""
import datetime as dt
import os
import re

from . import collect, dates, htmlx, http, state, taxonomy
from .config import WINDOW_DAYS

# Kapiyi gecip listede bulunmayan kac aday icin makale sayfasi acilir.
MAX_ACILAN = int(os.environ.get("RADAR_CAPRAZ_MAX", "40"))

# Olcum (2026-02..08): kapsam ici 25 haberin 18'i (%72) STI + SteelOrbis'ten
# cikti. Mysteel Cince kanali ise hat sozlesmelerini duyuran ama havuzun
# duzenli goremedigi kaynak. Her kaynak icin birden fazla sitemap adresi
# denenir - yayincilar bu adresleri haber vermeden degistiriyor; ilk cevap
# veren kullanilir, hicbiri vermezse durum "erisilemedi" olarak yazilir.
KAYNAKLAR = [
    dict(id="steeltimesint", publisher="Steel Times International", dayfirst=True,
         sitemaps=["https://www.steeltimesint.com/sitemaps-1-section-news-1-sitemap.xml"],
         robots=["https://www.steeltimesint.com"]),
    dict(id="steelorbis", publisher="SteelOrbis", dayfirst=True,
         sitemaps=["https://www.steelorbis.com/sitemap-news-en-free-1.xml"],
         robots=["https://www.steelorbis.com"]),
    # 2026-08-17: elle yazilan DORT adresin dordu de 404/bos dondu; bu yuzden
    # robots.txt uzerinden kesif sart. Uc alan adi da denenir.
    dict(id="mysteel", publisher="Mysteel", dayfirst=True,
         sitemaps=["https://news.mysteel.com/sitemap_news.xml",
                   "https://news.mysteel.com/sitemap.xml",
                   "https://factory.mysteel.com/sitemap.xml"],
         robots=["https://news.mysteel.com", "https://factory.mysteel.com",
                 "https://www.mysteel.com"]),
]


def _norm_url(u):
    u = (u or "").split("?")[0].split("#")[0].rstrip("/").lower()
    return re.sub(r"^https?://(www\.)?", "", u)


def kapi(baslik):
    """(katman, sebep) - haftalik kosunun kullandigi IKI KATMANLI kapinin
    aynisi. Katman "" ise aday elenmistir."""
    if taxonomy.is_junk_title(baslik):
        return "", "haber_degil"
    ok_scope, why = taxonomy.in_scope(baslik, "")
    if ok_scope and taxonomy.haber_olayi(baslik):
        return "Hat", ""
    if taxonomy.genel_yatirim(baslik):
        return "Yatirim", ""
    return "", (why or "kapsam_disi")


def listedekiler(payload, st=None):
    """(adresler, basliklar) - haftalik listede ZATEN olan haberler.

    Adres karsilastirmasi tek basina yetmez: ayni haber SteelOrbis'te bir,
    STI'de baska adreste durur. Baslik benzerligi ikinci bacaktir. Ucuncu
    bacak state'teki son 21 gunun basliklaridir - gecen hafta raporlanmis
    bir haber bu hafta "kacan" diye gosterilmemeli.
    """
    adresler = {_norm_url(r.get("url")) for r in (payload or {}).get("rows", [])}
    basliklar = [r.get("baslik", "") for r in (payload or {}).get("rows", [])]
    for b in (st or {}).get("son_basliklar", []) or []:
        t = b.get("b") if isinstance(b, dict) else b
        if t:
            basliklar.append(t)
    return adresler, [b for b in basliklar if b]


def eleme(adaylar, adresler, basliklar):
    """AGSIZ cekirdek: sitemap adaylarini kapidan gecirir ve haftalik
    listede olanlari ayiklar. (kalanlar, atlananlar) doner.

    Ag gerektirmedigi icin selftest bu fonksiyonu gercek verilerle olcer.
    """
    kalan, atlanan = [], []
    gorulen = set(adresler)
    havuz = list(basliklar)
    for it in adaylar:
        t = it.get("title", "")
        katman, sebep = kapi(t)
        if not katman:
            atlanan.append(dict(it, sebep=sebep))
            continue
        u = _norm_url(it.get("url"))
        if u in gorulen:
            atlanan.append(dict(it, sebep="listede (adres)"))
            continue
        if any(taxonomy.similar_titles(t, b) for b in havuz):
            atlanan.append(dict(it, sebep="listede (benzer baslik)"))
            continue
        # Kabul edilen aday karsilastirma havuzuna girer: ayni haberi uc
        # yayin birden tasiyorsa denetim listesinde UC kez gorunmesin.
        gorulen.add(u)
        havuz.append(t)
        kalan.append(dict(it, katman=katman))
    return kalan, atlanan


RE_ROBOTS_SITEMAP = re.compile(r"(?im)^\s*sitemap:\s*(\S+)")


def robots_sitemaplari(kok, log=lambda s: None):
    """robots.txt'teki Sitemap: satirlari.

    Elle yazilan aday adresler eskiyor: 2026-08-17 kosusunda Mysteel icin
    denenen DORT adresin dordu de 404/bos dondu. robots.txt yayincinin
    kendi beyanidir; tahmin etmek yerine oradan okunur. Haber sitemap'i
    olma ihtimali yuksek olanlar one alinir.
    """
    ok, text, _ = http.fetch(kok.rstrip("/") + "/robots.txt")
    if not ok:
        return []
    bulunan = []
    for u in RE_ROBOTS_SITEMAP.findall(text):
        if u.startswith("http"):
            bulunan.append(u)
    # Siralama ALAN ADINA degil YOLA bakar: "news.mysteel.com" host'u zaten
    # "news" tasiyor ve her adresi ayni puana sokuyordu (2026-08-17).
    def _puan(u):
        yol = re.sub(r"^https?://[^/]+", "", u)
        return 0 if re.search(r"news|haber|article", yol, re.I) else 1
    bulunan.sort(key=_puan)
    if bulunan:
        log("    (robots.txt: %d sitemap)" % len(bulunan))
    return bulunan[:6]


def _sitemap_adaylari(k, log):
    """(adaylar, hata) - once elle yazilan adresler, sonra robots.txt."""
    son = None
    denenen = list(k["sitemaps"])
    for u in denenen:
        items, err = collect._items_from_sitemap({"sitemap": u}, log)
        if items:
            return items, None
        son = err or "sitemap bos"
        log("    (%s -> %s)" % (u, son))
    for kok in k.get("robots", []):
        for u in robots_sitemaplari(kok, log):
            if u in denenen:
                continue
            denenen.append(u)
            items, err = collect._items_from_sitemap({"sitemap": u}, log)
            if items:
                log("    (robots.txt'ten bulundu: %s)" % u)
                return items, None
            log("    (%s -> %s)" % (u, err or "sitemap bos"))
    return [], son


def capraz(today=None, log=print):
    today = today or dt.date.today()
    floor = today - dt.timedelta(days=WINDOW_DAYS)

    payload, donem = collect_son_hafta()
    st = state.load()
    adresler, basliklar = listedekiler(payload, st)
    log("haftalik liste: %d satir, karsilastirilacak baslik %d"
        % (len(adresler), len(basliklar)))

    kaynak_durum, adaylar = {}, []
    for k in KAYNAKLAR:
        log("- %s" % k["publisher"])
        items, err = _sitemap_adaylari(k, log)
        if err:
            kaynak_durum[k["id"]] = {"publisher": k["publisher"],
                                     "durum": "erisilemedi", "hata": err}
            continue
        kaynak_durum[k["id"]] = {"publisher": k["publisher"], "durum": "ok",
                                 "adres": len(items)}
        for it in items:
            it["_kaynak"] = k["publisher"]
            it["_dayfirst"] = k["dayfirst"]
        adaylar += items

    kalan, atlanan = eleme(adaylar, adresler, basliklar)
    log("sitemap adayi %d -> kapiyi gecen ve listede olmayan %d"
        % (len(adaylar), len(kalan)))

    # Makale ACILDIKTAN SONRA elenenler ayri tutulur. Ilk kosuda (2026-08-17)
    # kapiyi gecen 5 aday bu asamada elendi ama cikti "0 kacan, 0
    # dogrulanamayan" diyordu - denetim listesinin sessizce bosalmasi, dolu
    # olmasindan daha tehlikelidir; sebep gorunmeli.
    kacanlar, dogrulanamayan, acildi_elendi = [], [], []
    acilan = 0
    for it in kalan:
        if acilan >= MAX_ACILAN:
            dogrulanamayan.append({"baslik": it["title"], "url": it["url"],
                                   "sebep": "makale acma limiti (%d)" % MAX_ACILAN})
            continue
        ok, page, info = http.fetch(it["url"])
        if not ok:
            dogrulanamayan.append({"baslik": it["title"], "url": it["url"],
                                   "sebep": info.get("hata") or "HTTP %s" % info.get("status")})
            continue
        acilan += 1
        doc = htmlx.parse_article(page)
        # Slug basligi yerine sayfanin GERCEK basligi kullanilir; kapi da
        # gercek baslikla bir kez daha isletilir (slug yaniltabilir).
        gercek = (doc.get("title") or "").strip()
        baslik = gercek if len(gercek.split()) >= 4 else it["title"]
        katman, sebep = kapi(baslik)
        if not katman:
            acildi_elendi.append({"baslik": baslik, "url": it["url"],
                                  "sebep": "gercek baslikta " + sebep})
            continue
        iso, src = dates.extract_article_date(
            doc, info.get("final") or it["url"], it.get("_dayfirst", True), today)
        if not iso:
            dogrulanamayan.append({"baslik": baslik, "url": it["url"],
                                   "sebep": "yayin tarihi sayfadan okunamadi"})
            continue
        if iso < floor.isoformat() or iso > today.isoformat():
            acildi_elendi.append({"baslik": baslik, "url": it["url"],
                                  "sebep": "pencere disi (%s)" % iso})
            continue
        if dates.title_year_conflict(baslik, iso):
            dogrulanamayan.append({"baslik": baslik, "url": it["url"],
                                   "sebep": "baslik yili tarihle celisiyor (%s)" % iso})
            continue
        kacanlar.append({
            "tarih": iso, "tarih_kaynagi": src, "baslik": baslik,
            "url": it["url"], "kaynak": it.get("_kaynak", ""), "katman": katman,
            "hat": taxonomy.match_line(baslik), "asama": taxonomy.match_stage(baslik),
            "anahtar": state.norm_key(baslik, it["url"]),
        })

    kacanlar.sort(key=lambda r: r["tarih"], reverse=True)
    return {
        "donem": donem,
        "pencere": [floor.isoformat(), today.isoformat()],
        "uretim": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "kaynaklar": kaynak_durum,
        "adet": len(kacanlar),
        "kacanlar": kacanlar,
        "dogrulanamayan": dogrulanamayan,
        "acildi_elendi": acildi_elendi,
        "kapiyi_gecen": len(kalan),
        "sitemap_adayi": len(adaylar),
        "elenen": len(atlanan),
    }


def collect_son_hafta():
    """(payload, donem) - out/ altindaki en yeni haftalik dosya."""
    import glob
    import json
    from .config import OUT
    fs = sorted(glob.glob(os.path.join(OUT, "hafta_*.json")))
    if not fs:
        return {"rows": []}, ""
    d = json.load(open(fs[-1], encoding="utf-8"))
    return d, d.get("period", "")
