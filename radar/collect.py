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
    who = taxonomy.fold(row.get("tedarikci") or row.get("firma") or "")
    asama = row.get("asama") or ""
    keys = {who + "|hat|" + (row.get("hat") or "") + "|" + asama}
    if row.get("ulke"):
        keys.add(who + "|ulke|" + row["ulke"] + "|" + asama)
        # ASAMASIZ bacak: ayni olayin Ingilizce ve Turkce anlatimi ayni
        # govde metnini paylasmadigi icin asama farkli cikabiliyor
        # (Baowu/SNS Cezayir haberi 2026-W33'te hem EN hem TR listeye girdi).
        # Firma + ulke + hat ucu ayniysa asama bakilmaksizin ayni olaydir.
        keys.add(who + "|fu|" + row["ulke"] + "|" + (row.get("hat") or ""))
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


def _items_from_source(s, log):
    """(items, hata) -> items: {title,url,date_raw,summary}"""
    if s.get("sitemap") or s.get("sitemaps"):
        return _sitemap_zinciri(s, log)
    url = s.get("rss") or s["url"]
    ok, text, info = http.fetch(url)
    if not ok:
        return [], (info.get("hata") or "HTTP %s" % info.get("status"))

    if feeds.looks_like_feed(text):
        items = feeds.parse_feed(text)[:MAX_LINKS_PER_SOURCE]
        for it in items:
            it["from_feed"] = True
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
                 tarihsiz_elendi=0, pencere_disi=0, kapsam_disi=0, tekrar=0, kabul=0)
    unreachable, rows, kinds, rejects, tech_pool = [], [], {}, [], []
    rezerv, rezerv_keys = [], set()
    rezerv_floor = (today - dt.timedelta(days=REZERV_GUN)).isoformat()
    katki = {}
    tech_seen = st.get("tech_seen", {})
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
        ok_scope, _ = taxonomy.in_scope(it["title"], (text or "")[:700])
        if not ok_scope:
            return
        blob = it["title"] + " . " + (text or "")[:700]
        key = "tech:" + state.norm_key(it["title"], it["url"])
        if key in tech_seen:
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
        baslik = taxonomy.temiz_baslik(it["title"])
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
            it["title"] = taxonomy.temiz_baslik(it["title"])

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
            gecmis = [b for b in st.get("son_basliklar", [])
                      if not taxonomy.is_junk_title(b.get("b", ""))]
            if any(taxonomy.similar_titles(it["title"], r["baslik"])
                   and r["asama"] == row["asama"] for r in rows):
                drop("tekrar", it, "benzer baslik (bu kosuda)")
                continue
            if any(taxonomy.similar_titles(it["title"], b.get("b", ""))
                   and b.get("a", "") == row["asama"] for b in gecmis):
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
    return {"rows": rows, "stats": stats, "unreachable": unreachable,
            "kinds": kinds, "today": today.isoformat(), "rejects": rejects,
            "rezerv": rezerv,
            "tech_pool": tech_pool[:12], "kaynak_katki": katki,
            "window": [floor.isoformat(), today.isoformat()]}
