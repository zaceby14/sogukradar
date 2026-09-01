# -*- coding: utf-8 -*-
"""Toplama boru hatti.

Akis:
  liste/besleme -> on eleme (kapsam + kaba tarih) -> makale sayfasi ->
  KESIN tarih -> pencere -> kapsam -> siniflandirma -> tekrar temizligi -> puan

Makale sayfasi neden aciliyor: liste sayfasindaki tarih ipucu yanlis
eslesebilir. Makale sayfasindaki JSON-LD / meta / <time> yapisal ve
yayincinin kendi beyanidir. Tarih dogrulugu bu adimda kazanilir.
"""
import datetime as dt
import os
import re

from . import classify, dates, feeds, htmlx, http, sources, state, taxonomy
from .config import (MAX_ARTICLE_FETCH, MAX_LINKS_PER_SOURCE, MAX_SITEMAP_LINKS,
                     REJECT_SEBEP_KOTA, REJECT_TOPLAM, REZERV_GUN,
                     TECH_WINDOW_DAYS, WINDOW_DAYS)

US_STYLE = {"cognex", "butechbliss", "delta", "bronx", "aist", "magnetics", "worldsteel"}


def event_keys(row):
    """Olay parmak izleri - COK BACAKLI. Tek anahtar yetmiyor:
    2026-08-12'de ayni KG Steel/Primetals olayi uc gazetede uc farkli hat
    vurgusuyla yazildi (PLTCM / cold rolling / pickling) ve hat-bazli tek
    anahtar ucunu uc ayri olay sandi. Simdi hem hat hem ulke bacagi var;
    HERHANGI biri eslesirse ayni olay sayilir."""
    asama = row.get("asama") or ""
    hat = row.get("hat") or ""
    ulke = row.get("ulke") or ""
    # HEM TEDARIKCI HEM FIRMA BACAGI (2026-08-31). Onceden tedarikci VARSA
    # firma hic kullanilmiyordu; ayni olayi tedarikciyi anmadan yazan bir
    # yayin firma-bazli anahtar uretiyor ve iki anahtar hic kesismiyordu.
    kimler = {taxonomy.fold(row.get("tedarikci") or ""),
              taxonomy.fold(row.get("firma") or "")} - {""}
    keys = set()
    for who in (kimler or {""}):
        keys.add(who + "|hat|" + hat + "|" + asama)
        if ulke:
            keys.add(who + "|ulke|" + ulke + "|" + asama)
            # ASAMASIZ bacak: ayni olayin Ingilizce ve Turkce anlatimi ayni
            # govde metnini paylasmadigi icin asama farkli cikabiliyor
            # (Baowu/SNS Cezayir haberi 2026-W33'te hem EN hem TR listeye
            # girdi). Firma + ulke + hat ucu ayniysa asama bakilmaksizin
            # ayni olaydir.
            keys.add(who + "|fu|" + ulke + "|" + hat)
    # KIMSIZ BACAK - YALNIZ ILK URETIM ICIN (2026-08-31).
    #
    # Vaka: W35'te giden Uganda/Roofings soguk hadde kompleksi ILK URETIM
    # haberinin iki varyanti daha listeye girdi -
    #   "Museveni Unveils $120 Million Steel Complex..."   (firma okumasi
    #                                    "Boost Ugandan Manufacturing")
    #   "Roofings Group, Uganda'da 125 milyon dolarlik..." (Turkce)
    # Her varyantta firma adi BASKA turlu bozuluyor, dolayisiyla kim-bazli
    # butun bacaklar isiksiz kaliyor. Ortak ve saglam olan sey su: ayni
    # ulkede, ayni hatta, ayni ay icinde IKI AYRI tesis ilk uretime
    # gecmez.
    #
    # Bacak YALNIZ "Ilk urun"/"Seri uretim" icin acilir. Sozlesme ve
    # modernizasyon haberleri buyuk ureticilerde ayni ay icinde mesru
    # sekilde tekrarlanir; onlarda bu bacak gercek haber kaybettirirdi.
    if ulke and hat and asama in ("Ilk urun", "Seri uretim"):
        keys.add("*|ulke-hat|" + ulke + "|" + hat + "|" + asama)
    return keys


def _dayfirst(sid):
    return sid not in US_STYLE


def check_sources(srcs=None, log=print):
    """Her kaynagi dener, saglik raporu dondurur. Kor noktalar sessiz kalmaz."""
    srcs = srcs or sources.SOURCES
    health = {}
    for s in srcs:
        ok, text, info = http.fetch(s["url"], use_cache=False)
        entry = {"publisher": s["publisher"], "url": s["url"], "kind": s["kind"]}
        if not ok:
            entry.update(durum="erisilemedi", hata=info.get("hata") or info.get("status"))
        else:
            if feeds.looks_like_feed(text):
                items = feeds.parse_feed(text)
                entry.update(durum="besleme", baglanti=len(items))
            else:
                links = htmlx.parse_listing(text, info["final"])
                found = htmlx.discover_feeds(text, info["final"])
                entry.update(durum="html", baglanti=len(links), besleme_bulundu=found[:3])
                if len(links) == 0:
                    entry["durum"] = "bos_liste"
        health[s["id"]] = entry
        log("  %-14s %s" % (s["id"], entry.get("durum")))
    return health


def discover(log=print):
    """Kaynaklarda RSS/Atom arar; bulunanlari dondurur (sources.py'ye islenir)."""
    found = {}
    for s in sources.SOURCES:
        if s.get("rss"):
            continue
        ok, text, info = http.fetch(s["url"])
        if not ok:
            continue
        if feeds.looks_like_feed(text):
            found[s["id"]] = s["url"]
            continue
        cands = htmlx.discover_feeds(text, info["final"])
        for c in cands:
            ok2, t2, _ = http.fetch(c)
            if ok2 and feeds.looks_like_feed(t2) and feeds.parse_feed(t2):
                found[s["id"]] = c
                log("  besleme: %-14s %s" % (s["id"], c))
                break
    return found


RE_SITEMAP_URL = re.compile(
    r"<url>(.*?)</url>", re.S | re.I)
RE_LOC = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.S | re.I)
RE_LASTMOD = re.compile(r"<lastmod>\s*(.*?)\s*</lastmod>", re.S | re.I)


def temiz_adres(url):
    """Aggregator yonlendirmesinden YAYINCININ KENDI adresini cikarir.

    Bing haber beslemesi adresi su bicimdedir ve gercek adresi ICINDE tasir:
      http://www.bing.com/news/apiclick.aspx?ref=FexRss&tid=...&url=<kodlanmis>&c=...
    Cozum agi HIC kullanmaz - adres zaten elimizde, yalnizca kodu acilir.

    NEDEN ONEMLI (2026-08-31): rapordaki baglanti okuyucunun tikladigi seydir.
    Aggregator yonlendirmesi tiklandiginda once arama motoruna gider; W35'te
    Roofings satirinin baglantisini bu yuzden ELLE duzeltmek zorunda kaldim
    ("kaynak Google News yonlendirmesiydi, okuyucu icin kullanissiz"). Arama
    katmani kaynaklarin yarisi oldugu icin bu artik tek tek duzeltilecek bir
    is degil.

    Google News'in yeni bicimi (CBMi...) SIFRELIDIR ve cevrimdisi cozulemez;
    o adresler oldugu gibi kalir ve editorun duzeltme listesinde gorunur.
    """
    import urllib.parse as _up
    if not url:
        return url
    try:
        p = _up.urlparse(url)
        if p.netloc.endswith("bing.com") and "apiclick" in p.path:
            gercek = _up.parse_qs(p.query).get("url", [""])[0]
            if gercek.startswith("http"):
                return gercek
    except Exception:
        pass
    return url


def slug_baslik(url):
    """Haber adresinin son parcasindan okunabilir bir baslik uretir.

    SteelOrbis ve Steel Times International haber basligini ADRESIN ICINDE
    tasiyor:
      .../kg-steel-selects-primetals-for-dangjin-pltcm-upgrade-1470187.htm
      .../news/primetals-to-modernise-korean-pickling-line
    Bu sayede kapsam elemesi makale ACILMADAN yapilabilir; yalnizca kapiyi
    gecen aday icin sayfa indirilir. Hem 403/bot engelini hem de makale acma
    butcesini rahatlatan asil kazanc budur (2026-08-17 olcumu).
    """
    p = (url or "").split("?")[0].split("#")[0].rstrip("/")
    parca = p.split("/")
    seg = parca[-1]
    # Bazi yayinlar haber numarasini AYRI bir parca yapar (Yieh:
    # /News/tk-accelis-...-capacity/161883). Son parca sadece rakamsa
    # baslik bir onceki parcadadir - yoksa slug "161883" olur ve aday
    # "haber degil" diye elenir (2026-08-17'de capraz kontrolde yakalandi).
    if seg.isdigit() and len(parca) > 1:
        seg = parca[-2]
    seg = re.sub(r"\.(html?|php|aspx?)$", "", seg, flags=re.I)
    seg = re.sub(r"[-_]\d{4,}$", "", seg)          # sondaki haber numarasi
    seg = re.sub(r"^\d{4}-\d{2}-\d{2}[-_]", "", seg)  # bastaki tarih
    seg = re.sub(r"[-_]+", " ", seg).strip()
    return seg


def _items_from_sitemap(s, log):
    """Haber sitemap'inden (loc + lastmod) aday listesi cikarir.

    DIKKAT - lastmod YAYIN TARIHI DEGILDIR. Primetals sitemap'inde lastmod
    2026-07-06 olan haberin gercek tarihi 2022-06-09, lastmod 2026-02-02
    olanin gercek tarihi 2018-11-20 cikti (2026-08-17'de dogrulandi). Bu
    yuzden lastmod yalnizca KESIF/siralama sinyali olarak kullanilir ve
    "_sitemap" isareti tasiyan satirlar, makale sayfasindan tarih
    dogrulanamazsa ELENIR - lastmod'a dusulmez.
    """
    ok, text, info = http.fetch(s["sitemap"])
    if not ok:
        return [], (info.get("hata") or "HTTP %s" % info.get("status"))
    # Aday adres RSS/Atom cikabilir (zincire /feed, /rss gibi adresler de
    # konuyor). Besleme tarihi YAPISALDIR - sitemap lastmod'unun aksine
    # yayincinin kendi yayin tarihi beyanidir, oldugu gibi kullanilir.
    if feeds.looks_like_feed(text):
        items = feeds.parse_feed(text)[:MAX_LINKS_PER_SOURCE]
        for it in items:
            it["from_feed"] = True
            it["url"] = temiz_adres(it.get("url"))
        if items:
            log("    (besleme: %d kayit)" % len(items))
        return items, (None if items else "besleme bos")
    out = []
    for blok in RE_SITEMAP_URL.findall(text):
        m = RE_LOC.search(blok)
        if not m:
            continue
        u = m.group(1).strip()
        if not u.startswith("http"):
            continue
        lm = RE_LASTMOD.search(blok)
        t = slug_baslik(u)
        if len(t.split()) < 4:       # bolum/menu adresi, haber degil
            continue
        out.append({"title": t, "url": u,
                    "date_raw": (lm.group(1).strip() if lm else ""),
                    "summary": "", "_sitemap": True})
    # En yeniden eskiye: pencere disi kalanlar zaten on elemede duser
    out.sort(key=lambda x: x["date_raw"], reverse=True)
    if not out:
        return [], "sitemap bos"
    log("    (sitemap: %d adres)" % len(out))
    return out[:MAX_SITEMAP_LINKS], None


def _sitemap_zinciri(s, log):
    """Kaynagin sitemap adreslerini sirayla dener, sonra robots.txt'e bakar.

    2026-08-27: Steel Times International hem /news hem de elle yazilan
    sitemap adresinde 403 veriyor; Mysteel'in dort aday adresi 404. Olcume
    gore kapsam ici haberin %72'si STI + SteelOrbis'ten geliyor, yani bu iki
    kaynagin yarisi kapaliyken havuz kor. Tek adres yerine ZINCIR denenir ve
    hicbiri tutmazsa robots.txt'teki Sitemap: satirlari okunur - yayincinin
    kendi beyani, tahminden iyidir.
    """
    from .capraz import robots_sitemaplari
    adaylar = s.get("sitemaps") or ([s["sitemap"]] if s.get("sitemap") else [])
    son = None
    for u in adaylar:
        items, err = _items_from_sitemap(dict(s, sitemap=u), log)
        if items:
            return items, None
        son = err or "sitemap bos"
        log("    (sitemap %s -> %s)" % (u, son))
    for kok in (s.get("robots") or []):
        for u in robots_sitemaplari(kok, log):
            if u in adaylar:
                continue
            items, err = _items_from_sitemap(dict(s, sitemap=u), log)
            if items:
                log("    (robots.txt'ten bulundu: %s)" % u)
                return items, None
    return [], son


def _items_from_dosya(s, log):
    """Depodaki bir JSON dosyasindan aday listesi (ELLE BESLEME).

    NEDEN VAR (2026-08-29): kaynaklarin bir kismi bot korumasi yuzunden hem
    yazilima hem de editorun oturumuna kapali (Steel Times International,
    SMS group, ArcelorMittal, BigMint... 403). Editor bu yayinlarin
    basliklarini ARAMA ile bulup bu dosyaya yazar.

    KRITIK: dosya yalnizca BASLIK + ADRES tasir, TARIH TASIMAZ. Tarih her
    zamanki gibi Actions'ta makale sayfasi acilarak dogrulanir - editorun
    beyan ettigi bir tarih hicbir zaman rapora girmez. Kapsam kapisi da
    degismez; bu kanal yalnizca ADAY tasir.
    """
    import json as _json
    from .config import ROOT
    yol = os.path.join(ROOT, s["dosya"])
    if not os.path.exists(yol):
        return [], "dosya yok"
    try:
        d = _json.load(open(yol, encoding="utf-8"))
    except Exception as e:
        return [], "dosya okunamadi: %s" % e
    out, tarihli = [], 0
    for k in d.get("kayitlar", []):
        u, t = (k.get("url") or "").strip(), (k.get("baslik") or "").strip()
        if not (u.startswith("http") and len(t.split()) >= 4):
            continue
        tarih = _elle_tarih(t, log)
        if tarih:
            tarihli += 1
        out.append({"title": t, "url": u, "date_raw": tarih, "summary": "",
                    "from_feed": bool(tarih),
                    "_pub": k.get("kaynak") or s["publisher"]})
    if out:
        log("    (elle besleme: %d aday, %d tanesinin tarihi dogrulandi)"
            % (len(out), tarihli))
    return out, (None if out else "elle besleme bos")


GNEWS_ARA = "https://news.google.com/rss/search?q=%s&hl=en-US&gl=US&ceid=US:en"


def _tarih_sorulur_mu(baslik):
    """Bu baslik BASLIGIYLA kapiyi geciyor mu?

    GERI ALINAN "ACI 7"DEN KALAN OLCUM ARACI (2026-08-31). Tarihi
    dogrulanamadigi icin elenen 96 kaydin 9'u basligiyla kapiyi geciyordu
    ve 8'i makale sayfasi 403 veren yayinlardandi; bu haberlerin tarihini
    Google News beslemesinden sormayi denedim.

    DENEME GERI TEPTI VE OLCULDU. 40 ek istek news.google.com'u bogdu:
      erisilemeyen kaynak   9 -> 89   (80'i Google News, HTTP 503)
      kurtarilan tarih                 0
      kabul edilen satir    2 ->  0
    Sebep yapisal: 169 kaynagin ~90'i Google News ARAMA beslemesidir, yani
    o tek host'a giden fazladan her istek butun arama katmanini riske atar.
    Sitemap zincirinin bes kaynagi bozmasiyla ayni aile: fazladan istek
    bedava degildir. Elle besleme kanalinin ~13 sorgusu olculen tolerans
    icinde kaliyor; onun uzerine cikilmamali.

    Fonksiyon KALDI cunku olcumun bekcisi odur - kapinin basliga
    uygulanabilir oldugunu gosterir ve tarih sorusunun nereye
    harcanacagini bir gun baska bir kanaldan cozersek hazirdir.
    """
    ok, _ = taxonomy.in_scope(baslik)
    if ok and taxonomy.haber_olayi(baslik):
        return True
    return bool(taxonomy.genel_yatirim(baslik))


def _elle_tarih(baslik, log):
    """Elle beslenen basligin tarihini ULASILABILIR bir beslemeden dogrular.

    NEDEN GEREKLI (2026-08-29, olculdu): kanalin ilk hali 15 kaydin 14'unu
    "tarihsiz_elendi" ile kaybediyordu, yani kanal HIC satir uretmiyordu.
    Sebep tasarim hatasiydi: tarihin "Actions'ta makale sayfasi acilarak"
    dogrulanacagini varsaymistim, oysa bu yayinlar zaten bot korumasinda -
    makale sayfasi da 403 veriyor. Kapali yayinin sayfasi kapaliysa tarihi
    de kapalidir.

    Cozum EDITORUN TARIH BEYAN ETMESI DEGILDIR - o kural degismez. Tarih
    yine yayincinin kendi beyanindan gelir, sadece ULASILABILIR bir kanaldan:
    Google News beslemesi haberi indeksledigi zaman yayincinin pubDate'ini
    tasir ve bu, boru hattinin RSS icin zaten guvendigi YAPISAL tarihtir.
    Baslik ortusmesi aranir; ortusme yoksa tarih yok, satir da yok.
    """
    import urllib.parse
    q = urllib.parse.quote('"%s"' % baslik[:110])
    ok, text, _info = http.fetch(GNEWS_ARA % q)
    if not ok or not feeds.looks_like_feed(text):
        return ""
    for e in feeds.parse_feed(text)[:10]:
        if _ayni_baslik(e.get("title", ""), baslik):
            return e.get("date_raw", "")
    return ""


def _ayni_baslik(a, b, esik=0.85):
    """Iki baslik AYNI HABER MI - tarih atamak icin katı olcut.

    taxonomy.similar_titles burada KULLANILAMAZ; o olcut "ayni olayin
    varyanti" icin ayarli ve 2026-08-29'da olculdu:
      "SMS upgrades Hyundai Steel galvanising line"
      "Ternium contracts Fives for new galvanizing line"
    ikilisini AYNI sayiyor (ortak "galvanizing line"). Tekrar elemede bu
    tolerans dogru - fazladan eleme haber kaybettirir, yanlis bilgi
    vermez. Tarih atamada ise ayni tolerans, BASKA bir haberin tarihini bu
    basliga yapistirir; sonucu tarih uydurmakla aynidir. Bu yuzden
    neredeyse birebir ortusme aranir.
    """
    ta, tb = taxonomy.title_tokens(a), taxonomy.title_tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / max(len(ta), len(tb)) >= esik


def _items_from_source(s, log):
    """(items, hata) -> items: {title,url,date_raw,summary}

    SIRA: elle besleme > sitemap zinciri > kaynagin kendi adresi.

    GERI DUSUS NEDEN VAR (2026-08-29): sitemap adresleri TAHMINDIR. v19'da
    14 kaynaga zincir eklendim; tahminlerin bir kismi 404 dondu ve zincir
    tutmayinca kaynagin CALISAN html/rss adresi hic denenmedi - erisilemeyen
    sayisi 10'dan 16'ya cikti (ABB Metals, Nippon Steel, Kocks, MetalForming,
    Mysteel bos_liste'den HTTP 404'e dustu). Tahmin edilen bir adres, calisan
    bir kaynagi asla bozamamali: zincir bos donerse normal yol denenir.
    """
    if s.get("dosya"):
        return _items_from_dosya(s, log)
    zincir = bool(s.get("sitemap") or s.get("sitemaps"))
    if not (s.get("rss") or s.get("url")):
        return _sitemap_zinciri(s, log) if zincir else ([], "adres yok")

    # ONCE KAYNAGIN KENDI ADRESI, SONRA SITEMAP ZINCIRI (2026-08-29, v20b).
    # Ilk denemede sira tersti ve geri dusus eklemek yetmedi: zincir tutmayan
    # bes kaynak (ABB Metals, Nippon Steel, China Baowu, SteelGuru, Kocks)
    # v19 oncesinde ACILIYORDU, v19'dan sonra kendi adreslerinden 404 almaya
    # basladi. Sebep zincirin kendisi - gercek istekten hemen once ayni
    # sunucuya 1-4 basarisiz istek gidiyor ve site bunu bot davranisi sayip
    # kapiyi kapatiyor. Tahmin edilen adres yalnizca kaynagin kendi adresi
    # is gormedigi zaman denenmeli.
    items, err = _items_from_web(s, log)
    if items or not zincir:
        return items, err
    if err:
        log("    (kaynagin kendi adresi tutmadi -> sitemap zinciri)")
    else:
        log("    (liste bos -> sitemap zinciri)")
    items2, err2 = _sitemap_zinciri(s, log)
    if items2:
        return items2, None
    # ZINCIRIN HATASI KAYNAGIN HATASINI GOLGELEMEZ. Kendi adresi acilip da
    # liste bos donduyse kaynak ERISILEMEZ DEGILDIR; v20'nin ilk halinde
    # zincirin "sitemap bos" hatasi bu duruma yaziliyor ve China Baowu ile
    # SteelGuru erisilemeyen listesine yanlis giriyordu.
    return [], (err or None)


def _items_from_web(s, log):
    """Kaynagin kendi adresi: rss > gomulu besleme > html liste."""
    url = s.get("rss") or s["url"]
    ok, text, info = http.fetch(url)
    if not ok:
        return [], (info.get("hata") or "HTTP %s" % info.get("status"))

    if feeds.looks_like_feed(text):
        items = feeds.parse_feed(text)[:MAX_LINKS_PER_SOURCE]
        for it in items:
            it["from_feed"] = True
            it["url"] = temiz_adres(it.get("url"))
        return items, None

    # HTML: once sayfada gomulu besleme var mi bak (tarih yapisal gelsin)
    for f in htmlx.discover_feeds(text, info["final"])[:2]:
        ok2, t2, _ = http.fetch(f)
        if ok2 and feeds.looks_like_feed(t2):
            it = feeds.parse_feed(t2)
            if it:
                log("    (besleme kullanildi: %s)" % f)
                for x in it:
                    x["from_feed"] = True
                return it[:MAX_LINKS_PER_SOURCE], None

    links = htmlx.parse_listing(text, info["final"], max_items=MAX_LINKS_PER_SOURCE)
    return [{"title": l["title"], "url": l["url"], "date_raw": l["date_hint"],
             "summary": ""} for l in links], None


def collect(today=None, log=print):
    today = today or dt.date.today()
    floor = today - dt.timedelta(days=WINDOW_DAYS)
    tech_floor = (today - dt.timedelta(days=TECH_WINDOW_DAYS)).isoformat()
    # On eleme esigi teknoloji penceresinden dar olamaz
    pre_floor = min((today - dt.timedelta(days=max(WINDOW_DAYS * 3, 90))).isoformat(),
                    tech_floor)
    st = state.load()
    seen = st.get("seen", {})

    stats = dict(kaynak=0, erisilemeyen=0, ham=0, on_eleme_gecti=0, makale_acildi=0,
                 tarihsiz_elendi=0, pencere_disi=0, kapsam_disi=0, tekrar=0, kabul=0,
                 gnews_tarih=0)
    unreachable, rows, kinds, rejects, tech_pool = [], [], {}, [], []
    rezerv, rezerv_keys = [], set()
    rezerv_floor = (today - dt.timedelta(days=REZERV_GUN)).isoformat()
    sb_floor = (today - dt.timedelta(days=21)).isoformat()
    katki = {}
    tech_seen = st.get("tech_seen", {})
    gonderilmis = [b for b in (st.get("son_basliklar") or [])
                   if not taxonomy.is_junk_title(b.get("b", ""))]
    # Ayni kosuda ayni haberin ikinci kopyasi (iki gnews sorgusu ayni sonucu
    # dondurur) ve AYNI OLAYIN farkli baslikli varyanti icin iki savunma:
    run_keys = set()
    ev_state = st.get("events", {})
    run_events = set()
    # Capraz tarih odunclemesi: bir adres herhangi bir RSS beslemesinde
    # geciyorsa oradaki yayin tarihi, ayni adresi HTML'den goren kaynak icin
    # de gecerlidir. Tarihsiz eleme sayisini dusuren ucuncu aci.
    url_dates = {}

    def maybe_tech(it, date_iso, text, publisher):
        """Teknoloji kosesi adayi mi? Ana pencereden BAGIMSIZ calisir:
        6 aya kadar eski olabilir, ama daha once kosede cikmis olamaz."""
        if date_iso < tech_floor:
            return
        # YALNIZCA BASLIGA bakilir: govdedeki "innovation" gibi pazarlama
        # sozcukleri bir yatirim kararini teknoloji sanmamiza yol aciyordu
        # (2026-08-12, USS Gary teneke haberi).
        # Kose kapisi satir asamasindan BAGIMSIZ (2026-08-27). Asama kapisi
        # daraltilinca kose havuzu kurumustu (aday 0). Kose biraz daha genis
        # olabilir: oradaki madde editor tarafindan elle okunup tanitiliyor.
        if not (taxonomy.match_stage(it["title"]) == "Teknoloji"
                or taxonomy.TECH_ADAY.search(taxonomy.fold(it["title"]))):
            return
        # KOSENIN KENDI KAPSAM KAPISI (2026-08-31). in_scope hat ISMI ariyor
        # ("annealing line"); kosenin konusu hattin kendisi degil PROSES
        # TEKNOLOJISIDIR ve gercek basliklar bu yuzden dusuyordu ("SMS group
        # I-Furnace intelligent annealing process model"). tech_kapsam ayni
        # yukari akis / baska malzeme / gurultu vetolarini uygular, yalnizca
        # hat ismini sart kosmaz. HABER KAPISI DEGISMEZ.
        if not taxonomy.tech_kapsam(it["title"], (text or "")[:700]):
            return
        blob = it["title"] + " . " + (text or "")[:700]
        ham = state.norm_key(it["title"], it["url"])
        key = "tech:" + ham
        if key in tech_seen:
            return
        # SATIR OLARAK GONDERILMIS HABER KOSEYE GIREMEZ (2026-08-31).
        # Kural bugune kadar tek yonluydu: kosede tanitilmis haber satir
        # olamiyordu, ama tersi serbestti. 2026-W36'da havuzun TEK adayi
        # "Fives supplies technologies for Xinyu's new electrical steel
        # facility" idi ve o haber 2026-W35 bulteninde satir olarak zaten
        # gitmisti. Okuyucu icin ikisi ayni haberdir; yon fark etmez.
        if ham in seen:
            return
        # AYNI MADDE HAVUZA IKI KEZ GIRMEZ (2026-08-31). Iki aggregator ayni
        # haberi farkli yonlendirme adresiyle donduruyor; anahtar ayni ama
        # havuzda uc kopya birikti.
        if any(t["anahtar"] == key for t in tech_pool):
            return
        # GONDERILMIS OLAYIN VARYANTI DA KOSEYE GIREMEZ. "ham in seen"
        # kontrolu ANAHTAR bazlidir; baska yayinin ayni olayi anlatan
        # varyantinin anahtari farklidir. 2026-W36'da havuza
        # "Primetals Technologies to Modernize PLTCM for KG Steel in South
        # Korea" girdi - W35 bulteninde "KG Steel selects Primetals for
        # Dangjin PLTCM upgrade and capacity expansion" olarak zaten
        # gitmisti.
        #
        # BASLIK BENZERLIGI BU CIFTI YAKALAMAZ - olculdu: ortak ayirt edici
        # kelimeler yalniz "steel" ve "pltcm", oran %30. Yakalayan bacak
        # OLAY PARMAK IZIDIR (tedarikci + hat + asama), satirlarda oldugu
        # gibi. Bu yuzden aday icin de aday bir satir kurulup ayni izler
        # hesaplanir.
        aday_satir = {"tedarikci": classify.detect_supplier(blob) or "",
                      "firma": classify.detect_firm(it["title"]) or "",
                      "hat": taxonomy.match_line(blob),
                      "ulke": taxonomy.match_country(blob),
                      "asama": taxonomy.match_stage(it["title"])}
        if set(event_keys(aday_satir)) & set(ev_state):
            return
        if any(taxonomy.similar_titles(it["title"], b.get("b", ""))
               for b in gonderilmis):
            return
        tech_pool.append({"anahtar": key, "tarih": date_iso, "baslik": it["title"],
                          "url": it["url"], "kaynak": publisher,
                          "hat": taxonomy.match_line(blob)})

    def maybe_rezerv(it, date_iso, text, s):
        """Pencere disi ama gonderilmeye DEGER satiri havuza al.

        Ayni kapidan gecer (kapsam + olay), tarihi sayfadan dogrulanmistir.
        Tek farki tarihinin pencere disinda kalmasidir. Daha once
        raporlanmissa alinmaz - "seen" burada da gecerlidir.
        """
        if date_iso < rezerv_floor:
            return
        baslik = taxonomy.temiz_baslik(it["title"], it.get("url") or "")
        ok_scope, _ = taxonomy.in_scope(baslik, (text or "")[:700])
        if not (ok_scope and taxonomy.haber_olayi(baslik)):
            return
        key = state.norm_key(baslik, it["url"])
        if key in seen or key in run_keys or key in rezerv_keys:
            return
        row = classify.build({
            "title": baslik, "url": it["url"], "date": date_iso,
            "publisher": it.get("_pub") or s["publisher"], "source_id": s["id"],
            "source_kind": s["kind"], "source_country": s.get("country", ""),
            "text": text, "date_src": src,
        })
        if row["hat"] == "Belirsiz" and row["asama"] == "Belirsiz":
            return
        row["anahtar"] = key
        row["kategori"] = "Hat"
        row["olaylar"] = sorted(event_keys(row))
        row["rezerv"] = True
        rezerv_keys.add(key)
        rezerv.append(row)

    reject_sayac = {}

    def drop(reason, it, extra=""):
        """Elenen her satir kaydedilir. Ayarlama (kalibrasyon) ancak neyin
        neden elendigi gorulerek yapilabilir; sessiz eleme korlestirir.

        SEBEP BASINA KOTA (2026-08-18). Onceki surum ilk 600 kaydi aliyordu;
        akisin basi "kapsam_disi" ile dolduguntan (tek kosuda 2149 adet)
        "tekrar" kayitlari dosyaya HIC girmiyordu. 2026-W34'te tekrar=22
        iken reddedilenler.json'da sifir tekrar kaydi vardi - istatistikle
        dosya celisiyordu ve teshis imkansizdi.
        """
        stats[reason] = stats.get(reason, 0) + 1
        reject_sayac[reason] = reject_sayac.get(reason, 0) + 1
        if reject_sayac[reason] <= REJECT_SEBEP_KOTA and len(rejects) < REJECT_TOPLAM:
            rejects.append({"sebep": reason, "baslik": it.get("title", "")[:180],
                            "url": it.get("url", ""), "ek": extra})

    for s in sources.SOURCES:
        stats["kaynak"] += 1
        kinds[s["id"]] = s["kind"]
        log("- %s" % s["publisher"])
        items, err = _items_from_source(s, log)
        if err:
            unreachable.append((s["publisher"], err))
            stats["erisilemeyen"] += 1
            log("    ERISILEMEDI: %s" % err)
            continue
        stats["ham"] += len(items)
        df = _dayfirst(s["id"])
        for it in items:
            if it.get("from_feed") and it.get("date_raw") and it.get("url"):
                d0 = dates.parse_date_text(it["date_raw"], df, today)
                if d0:
                    url_dates.setdefault(it["url"].split("?")[0], d0)

        pre = []
        for it in items:
            title = it["title"]
            blob = title + " " + (it.get("summary") or "")
            if taxonomy.is_junk_title(title):
                drop("kapsam_disi", it, "haber degil (menu/e-posta/kisa)")
                continue
            # Rapor/pazar arastirmasi satan yayin dagitim siteleri: icerik
            # haber degil reklamdir (v4 kosusunda openPR sizdi).
            if taxonomy.SPAM_PUBLISHER.search(
                    taxonomy.fold(it.get("url", "") + " " + (it.get("_pub") or ""))):
                drop("kapsam_disi", it, "rapor/bulten dagitim sitesi")
                continue
            watchable = taxonomy.genel_yatirim(title)
            if taxonomy.HARD_REJECT.search(taxonomy.fold(title)) and not watchable:
                drop("kapsam_disi", it, "sert red (baslik)")
                continue
            # On eleme: OEM disi kaynaklarda baslik+ozet en azindan kapsama
            # ya da genel yatirim havuzuna dokunmali (makale acma maliyeti freni)
            if s["kind"] != "oem" and not watchable:
                on_ok, _ = taxonomy.in_scope(title, it.get("summary") or "")
                if not on_ok:
                    drop("kapsam_disi", it, "kapsam kapisi (baslik)")
                    continue
            it["_watch"] = watchable
            # Kaba tarih SADECE maliyet freni icindir: cok eski (arsiv) satirlar
            # icin makale sayfasi hic acilmaz. Esik bilerek genis tutulur -
            # liste sayfasindaki tarih yanlis eslesirse gecerli bir haberi
            # elemeyelim. Asil pencere karari makale tarihinden sonra verilir.
            rough = dates.parse_date_text(it.get("date_raw", ""), df, today) \
                or dates.date_from_url(it["url"], today)
            if rough and rough < pre_floor:
                drop("pencere_disi", it, "on eleme: " + rough)
                continue
            it["_rough"] = rough
            pre.append(it)
        stats["on_eleme_gecti"] += len(pre)

        for it in pre:
            if s["kind"] == "arama":
                # Google News: baglanti yonlendirmedir, makale ACILMAZ;
                # tarih beslemeden yapisal gelir. Baslik "Baslik - Yayinci".
                if " - " in it["title"]:
                    t2, _, pub = it["title"].rpartition(" - ")
                    if t2 and len(pub) < 45:
                        it["title"], it["_pub"] = t2.strip(), pub.strip()
                # Celik baglami sarti: "cinnamon roll shop" tuzagi (2026-08-12)
                if not taxonomy.STEEL_CONTEXT.search(taxonomy.fold(it["title"])):
                    drop("kapsam_disi", it, "celik baglami yok (arama)")
                    continue
                date_iso, src = it.get("_rough"), "rss"
                text = it.get("summary", "")
            else:
                if stats["makale_acildi"] >= MAX_ARTICLE_FETCH:
                    log("    (makale acma limiti doldu)")
                    break
                ok, page, info = http.fetch(it["url"])
                date_iso, src = None, "yok"
                text = it.get("summary", "")
                if ok:
                    stats["makale_acildi"] += 1
                    doc = htmlx.parse_article(page)
                    date_iso, src = dates.extract_article_date(doc, info["final"], df, today)
                    text = doc.get("text", "")[:3000] or text
                    # Sitemap adayinin basligi adres slug'indan uretilmisti
                    # ("kg steel selects primetals for ..."). Sayfa acildigina
                    # gore gercek basligi kullan - rapora slug girmesin.
                    if it.get("_sitemap"):
                        gt = (doc.get("title") or "").strip()
                        if len(gt.split()) >= 4 and not taxonomy.is_junk_title(gt):
                            it["title"] = gt
                if not date_iso:
                    # ACI 5: ayni adres baska bir beslemede gecti mi.
                    # Last-Modified'dan ONCE denenir: capraz besleme yayincinin
                    # kendi tarih beyanidir; HTTP basligi ise sunucunun son
                    # dokunma zamanidir ve eski sayfa bugun servis edilince
                    # yaniltir (Tosyali/Sonangol 2024 vakasi, 2026-08-12).
                    od = url_dates.get(it["url"].split("?")[0])
                    if od:
                        date_iso, src = od, "capraz-rss"
                if not date_iso:
                    # ACI 6: sunucunun Last-Modified basligi - en zayif aci
                    lm = dates.parse_date_text(info.get("last_modified", ""), False, today)
                    if lm:
                        date_iso, src = lm, "last-modified"
                if not date_iso and not it.get("_sitemap"):
                    date_iso = it.get("_rough")
                    # Beslemeden gelen tarih yapisaldir - "tarih?" isareti gerekmez
                    src = ("rss" if it.get("from_feed") else "liste") if date_iso else "yok"
                # SITEMAP ISTISNASI: lastmod'a ASLA dusulmez. Primetals
                # sitemap'inde 2018 ve 2022 tarihli haberler 2026 damgali
                # cikti; lastmod'u yayin tarihi saymak rapora yillik eski
                # haber sokar. Sayfadan tarih cikmadiysa satir elenir.
            if not date_iso:
                drop("tarihsiz_elendi", it)   # TARIH YOKSA HABER YOK
                continue
            # Baslikta gecen yil, bulunan tarihten eskiyse: eski icerik bugun
            # servis edilmis demektir. Tarih guvenilmez, satir elenir.
            if dates.title_year_conflict(it["title"], date_iso):
                drop("tarih_celiskisi", it, "baslik yili < %s" % date_iso)
                continue
            if date_iso < floor.isoformat() or date_iso > today.isoformat():
                maybe_tech(it, date_iso, text, s["publisher"])
                # REZERVE AL (2026-08-27). Pencere disi ama kapiyi gecen ve
                # tarihi DOGRULANMIS satir cope gitmez: hic gonderilmemisse
                # ileride listeyi doldurmak icin saklanir. Olcum: son kosuda
                # elenen 30 kapsam ici satirin 26'si sirf pencere disiydi ve
                # 11'i 2026 tarihliydi - okuyucunun hic gormedigi gercek
                # haberler. Kapiyi gevsetmek yerine bunlar kullanilir.
                maybe_rezerv(it, date_iso, text, s)
                drop("pencere_disi", it, date_iso)
                continue
            maybe_tech(it, date_iso, text, s["publisher"])

            # BASLIK TEMIZLIGI, tekrar anahtarindan ONCE (v5, 2026-08-17).
            # Liste sayfalarindan kopan on ek ("11 Aug Free ...", "Daily press
            # | 2025-01-30 ...") ve arkaya yapisan lede ayni haberi iki farkli
            # anahtara bolup listede IKI KEZ gostermisti. Tarih bu noktada
            # zaten cozulmus durumda, temizlik tarihi etkilemez.
            it["title"] = taxonomy.temiz_baslik(it["title"], it.get("url") or "")

            key = state.norm_key(it["title"], it["url"])
            if key in seen or key in run_keys:
                drop("tekrar", it)
                continue
            # Teknoloji kosesinde ZATEN tanitilmis bir haber satir olarak
            # tekrar cikmamali - okuyucu icin ayni haberdir (2026-W35'te
            # POSCO elektrik celigi hem arsivde hem listede vardi).
            if ("tech:" + key) in tech_seen:
                drop("tekrar", it, "kosede tanitilmis")
                continue

            # IKI KATMANLI LISTE (2026-08-12 karari - "1 haftada tek haber
            # olmaz, liste olacak"): cekirdek islem hatti haberleri "Hat",
            # genel celik yatirim haberleri "Yatirim" etiketiyle AYNI listede.
            ok_scope, why = taxonomy.in_scope(it["title"], text[:700])
            if ok_scope:
                # OLAY KAPISI (v5, 2026-08-17): konu dogru olsa bile baslik bir
                # olay anlatmiyorsa haber degildir. OEM urun katalogu sayfalari
                # ("Flying Shear Cut-to-Length Lines", "Strip processing line,
                # Annealing and Pickling line ...") tam da bu yuzden listeye
                # giriyordu - hepsi isim tamlamasidir.
                if not taxonomy.haber_olayi(it["title"]):
                    if taxonomy.genel_yatirim(it["title"]):
                        kategori = "Yatirim"
                    else:
                        drop("kapsam_disi", it, "olay yok (katalog/pazarlama)")
                        continue
                else:
                    kategori = "Hat"
            elif taxonomy.genel_yatirim(it["title"]):
                kategori = "Yatirim"
            else:
                drop("kapsam_disi", it, why)
                continue

            row = classify.build({
                "title": it["title"], "url": it["url"], "date": date_iso,
                "publisher": it.get("_pub") or s["publisher"], "source_id": s["id"],
                "source_kind": s["kind"], "source_country": s.get("country", ""),
                "text": text, "date_src": src,
            })
            # Hat VE asama belirsiz bir satir cekirdek olamaz; yatirim
            # niteligi tasiyorsa Yatirim katmanina iner, tasimiyorsa elenir.
            if row["hat"] == "Belirsiz" and row["asama"] == "Belirsiz":
                if taxonomy.genel_yatirim(it["title"]):
                    kategori = "Yatirim"
                else:
                    drop("kapsam_disi", it, "hat+asama belirsiz")
                    continue
            # Cekirdek (Hat) satiri en az BIR somut delil tasimali: asama,
            # tedarikci, kapasite ya da tutar. Hicbiri yoksa satir "bir yerde
            # soguk hadde kelimesi geciyor" seviyesindedir - alakasiz gorunur
            # (kullanici geri bildirimi, 2026-08-12).
            if kategori == "Hat" and row["asama"] == "Belirsiz" and not (
                    row["tedarikci"] or row["kapasite"] or row["tutar"]):
                if taxonomy.genel_yatirim(it["title"]):
                    kategori = "Yatirim"
                else:
                    drop("kapsam_disi", it, "delil yok (asama/tedarikci/kapasite/tutar)")
                    continue
            if kategori == "Yatirim" and \
                    sum(1 for r in rows if r.get("kategori") == "Yatirim") >= 12:
                drop("kapsam_disi", it, "yatirim katmani limiti")
                continue
            eks = event_keys(row)
            if (eks & run_events) or any(k in ev_state for k in eks):
                drop("tekrar", it, "ayni olayin varyanti: " + "; ".join(sorted(eks)))
                continue
            # Ucuncu bacak: baslik benzerligi. Ayni asamadaki, bu kosuda ya da
            # son 21 gunde kabul edilmis bir satirla baslik ortusuyorsa tekrar.
            # KULLANIM ANINDA COP SUZGECI (2026-08-18). Yazma tarafi
            # duzeltildi ama state'te DURAN cop de etkisiz kalmali: v8
            # oncesi kosulardan kalan "Electrical steel, non grain oriented"
            # gibi katalog basliklari, her gercek elektrik celigi/galvaniz
            # haberini "benzer baslik" diye eliyordu.
            # 21 GUNLUK KESIM BURADA (2026-08-29): state artik gonderilmis
            # basliklari rezerv kadar (540 gun) tutuyor, cunku rezerv
            # tekrar denetiminin uzun hafizaya ihtiyaci var. Bu bacagin
            # amaci ise dar: gec yazan gazetenin AYNI GUNCEL olayi farkli
            # baslikla tekrar sokmasi. Kapiyi genisletmemek icin kesim
            # burada, kullanim aninda yapilir.
            gecmis = [b for b in st.get("son_basliklar", [])
                      if not taxonomy.is_junk_title(b.get("b", ""))
                      and (b.get("t") or "9999") >= sb_floor]
            if any(taxonomy.similar_titles(it["title"], r["baslik"])
                   and r["asama"] == row["asama"] for r in rows):
                drop("tekrar", it, "benzer baslik (bu kosuda)")
                continue
            # ASAMA SARTI KALKTI (2026-08-31). Kosul "benzer baslik VE ayni
            # asama" idi ve 2026-W36'da su tekrari gecirdi:
            #   gonderilen (W34): "India's Jindal Stainless Limited to invest
            #                      $94 million to ramp up cold rolling
            #                      capacity"              asama: Ilk urun
            #   yeni gelen      : "Jindal Stainless investing Rs 900 crore to
            #                      increase cold rolling capacity to 2.67 MT
            #                      by FY28"               asama: Belirsiz
            # Ayni duyuru, iki yayin, farkli para birimi. Asama zaten
            # yayindan yayina degisen bir OKUMA; onu tekrar denetiminin
            # sartina koymak, savunmayi en cok ihtiyac duyulan yerde -
            # ayni olayin farkli yorumlandigi yerde - kapatiyor.
            if any(taxonomy.similar_titles(it["title"], b.get("b", ""))
                   for b in gecmis):
                drop("tekrar", it, "benzer baslik (gecmis 21 gun)")
                continue
            row["anahtar"] = key
            row["kategori"] = kategori
            row["olaylar"] = sorted(eks)
            run_keys.add(key)
            if row.get("tedarikci") or row.get("firma"):
                run_events |= eks
            if not dates.kesin_mi(src):
                # yapisal olmayan tarih: rapora girer ama bana DOGRULAT diye isaretlenir
                row["eksik"] = list(row["eksik"]) + ["tarih?"]
            rows.append(row)
            stats["kabul"] += 1
            katki[s["publisher"]] = katki.get(s["publisher"], 0) + 1

    tech_pool.sort(key=lambda t: t["tarih"], reverse=True)
    # HOST SAGLIGI RAPORA GIRER (2026-08-31). Hiz sinirlamasi SESSIZ
    # kalmamali: 2026-08-31'de news.google.com 503 dondu, 80 kaynak birden
    # dustu ve bunu ancak kosudan sonra JSON'i okuyarak anladim. Hangi
    # host'a kac istek gittigi ve hangisi sogutmaya alindigi artik
    # raporun kendisinde durur.
    hs = http.host_raporu()
    for h, d in hs.items():
        if d["sogutmada"] or d["hiz_siniri"]:
            log("  ! host %s: %d istek, %d hiz siniri%s"
                % (h, d["istek"], d["hiz_siniri"],
                   ", SOGUTMADA" if d["sogutmada"] else ""))
    return {"rows": rows, "stats": stats, "unreachable": unreachable,
            "kinds": kinds, "today": today.isoformat(), "rejects": rejects,
            "rezerv": rezerv, "host_saglik": hs,
            "tech_pool": tech_pool[:12], "kaynak_katki": katki,
            "window": [floor.isoformat(), today.isoformat()]}
