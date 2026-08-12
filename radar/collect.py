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

from . import classify, dates, feeds, htmlx, http, sources, state, taxonomy
from .config import (MAX_ARTICLE_FETCH, MAX_LINKS_PER_SOURCE, TECH_WINDOW_DAYS,
                     WINDOW_DAYS)

US_STYLE = {"cognex", "butechbliss", "delta", "bronx", "aist", "magnetics", "worldsteel"}


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


def _items_from_source(s, log):
    """(items, hata) -> items: {title,url,date_raw,summary}"""
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
    watch, seen_watch, katki = [], set(), {}
    tech_seen = st.get("tech_seen", {})

    def maybe_tech(it, date_iso, text, publisher):
        """Teknoloji kosesi adayi mi? Ana pencereden BAGIMSIZ calisir:
        6 aya kadar eski olabilir, ama daha once kosede cikmis olamaz."""
        if date_iso < tech_floor:
            return
        # YALNIZCA BASLIGA bakilir: govdedeki "innovation" gibi pazarlama
        # sozcukleri bir yatirim kararini teknoloji sanmamiza yol aciyordu
        # (2026-08-12, USS Gary teneke haberi).
        if taxonomy.match_stage(it["title"]) != "Teknoloji":
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

    def drop(reason, it, extra=""):
        """Elenen her satir kaydedilir. Ayarlama (kalibrasyon) ancak neyin
        neden elendigi gorulerek yapilabilir; sessiz eleme korlestirir."""
        stats[reason] = stats.get(reason, 0) + 1
        if len(rejects) < 600:
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

        pre = []
        for it in items:
            title = it["title"]
            blob = title + " " + (it.get("summary") or "")
            if taxonomy.is_junk_title(title):
                drop("kapsam_disi", it, "haber degil (menu/e-posta/kisa)")
                continue
            watchable = taxonomy.watch_worthy(title)
            if taxonomy.HARD_REJECT.search(taxonomy.fold(title)) and not watchable:
                drop("kapsam_disi", it, "sert red (baslik)")
                continue
            if (s["kind"] != "oem" and not watchable
                    and not taxonomy.SCOPE_GATE.search(taxonomy.fold(blob))):
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
                if not date_iso:
                    date_iso = it.get("_rough")
                    # Beslemeden gelen tarih yapisaldir - "tarih?" isareti gerekmez
                    src = ("rss" if it.get("from_feed") else "liste") if date_iso else "yok"
            if not date_iso:
                drop("tarihsiz_elendi", it)   # TARIH YOKSA HABER YOK
                continue
            if date_iso < floor.isoformat() or date_iso > today.isoformat():
                maybe_tech(it, date_iso, text, s["publisher"])
                drop("pencere_disi", it, date_iso)
                continue
            maybe_tech(it, date_iso, text, s["publisher"])

            key = state.norm_key(it["title"], it["url"])
            ok_scope, why = taxonomy.in_scope(it["title"], text[:700])
            if not ok_scope:
                # Cekirdek kapsama girmiyor ama dikkat cekici yatirim haberi ise
                # ayri "yakin takip" bolumune alinir - ana tabloyu kirletmez.
                if it.get("_watch") and key not in seen and len(watch) < 6:
                    watch.append({"anahtar": key, "tarih": date_iso,
                                  "baslik": it["title"], "url": it["url"],
                                  "kaynak": s["publisher"]})
                    seen_watch.add(key)
                drop("kapsam_disi", it, why)
                continue

            if key in seen:
                drop("tekrar", it)
                continue

            row = classify.build({
                "title": it["title"], "url": it["url"], "date": date_iso,
                "publisher": it.get("_pub") or s["publisher"], "source_id": s["id"],
                "text": text, "date_src": src,
            })
            # Hat VE asama belirsizse bu cekirdek tablo satiri degildir;
            # dikkat cekense "yakin takip"e iner, degilse elenir
            # (2026-08-12: Hydnum destek haberi boyle bir satirdi).
            if row["hat"] == "Belirsiz" and row["asama"] == "Belirsiz":
                if it.get("_watch") and len(watch) < 6:
                    watch.append({"anahtar": key, "tarih": date_iso,
                                  "baslik": it["title"], "url": it["url"],
                                  "kaynak": it.get("_pub") or s["publisher"]})
                    seen_watch.add(key)
                drop("kapsam_disi", it, "hat+asama belirsiz")
                continue
            row["anahtar"] = key
            if src in ("liste", "url", "metin"):
                # yapisal olmayan tarih: rapora girer ama bana DOGRULAT diye isaretlenir
                row["eksik"] = list(row["eksik"]) + ["tarih?"]
            rows.append(row)
            stats["kabul"] += 1
            katki[s["publisher"]] = katki.get(s["publisher"], 0) + 1

    tech_pool.sort(key=lambda t: t["tarih"], reverse=True)
    watch.sort(key=lambda t: t["tarih"], reverse=True)
    return {"rows": rows, "stats": stats, "unreachable": unreachable,
            "kinds": kinds, "today": today.isoformat(), "rejects": rejects,
            "tech_pool": tech_pool[:12], "watch": watch, "kaynak_katki": katki,
            "window": [floor.isoformat(), today.isoformat()]}
