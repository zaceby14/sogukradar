# -*- coding: utf-8 -*-
"""SogukRadar komut satiri.

  python -m radar check                 kaynak saglik taramasi
  python -m radar discover              RSS/Atom besleme avi
  python -m radar run                   HAFTALIK KOSU (GitHub Actions bunu calistirir)
  python -m radar review                bana sorulacaklari ozetler
  python -m radar finalize -s ozet.json Turkce cumleleri isler, state'i gunceller
  python -m radar capraz                sitemap capraz kontrolu -> out/kacanlar.json
  python -m radar selftest              agsiz birim testleri
"""
import argparse
import datetime as dt
import json
import os
import sys

from . import collect, kume, render, score, state, taxonomy
from .config import (HEDEF_SATIR, OUT, REZERV_DAR_GUN, REZERV_ESIK,
                     REZERV_KULLANIM_GUN, REZERV_MAX, TARGET_ROWS,
                     VERSION)
from .sources import SOURCES


def _period(d):
    y, w, _ = d.isocalendar()
    return "%04d-W%02d" % (y, w)


def _w(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def cmd_check(a):
    health = collect.check_sources()
    _w(os.path.join(OUT, "source_health.json"), health)
    bad = [k for k, v in health.items() if v["durum"] in ("erisilemedi", "bos_liste")]
    print("\ntoplam %d kaynak, sorunlu %d: %s" % (len(health), len(bad), ", ".join(bad)))
    return 0


def cmd_discover(a):
    found = collect.discover()
    _w(os.path.join(OUT, "feeds_found.json"), found)
    print("\n%d besleme bulundu -> out/feeds_found.json" % len(found))
    print("Bunlari sources.py icinde rss= alanina islemek kosuyu hizlandirir.")
    return 0


def cmd_run(a):
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    per = _period(today)

    # KALIBRASYON MODU: repo kokunde "KALIBRASYON" adli bir dosya varsa
    # hafiza o kosu icin sifirlanir - daha once cikan haber ve teknolojiler
    # yeniden kullanilabilir. Sistem oturunca dosya silinir, tekrar engeli
    # kendiliginden geri gelir.
    #
    # "son_basliklar" DA SIFIRLANIR (2026-08-18). Onceki surum yalnizca
    # seen/events/tech_seen'i temizliyordu; tekrar savunmasinin UCUNCU bacagi
    # (baslik benzerligi, collect.py) son_basliklar'a bakiyor ve calismaya
    # devam ediyordu. Sonuc: mod ekrana "tekrar engeli kapali" yaziyor ama
    # engel aciktı. 2026-W34 kosusu tam olarak boyle 0 satir uretti -
    # seen=0 iken tekrar=22 gibi kendi icinde celiskili bir istatistikle.
    from .config import ROOT
    if os.path.exists(os.path.join(ROOT, "KALIBRASYON")):
        st0 = state.load()
        st0["seen"], st0["events"], st0["tech_seen"] = {}, {}, {}
        st0["son_basliklar"] = []
        state.save(st0)
        print("*** KALIBRASYON MODU: hafiza sifirlandi, tekrar engeli kapali ***")

    payload = collect.collect(today=today)
    rows = score.rank(payload["rows"], payload["kinds"], today)

    # OLAY KUMELEME (2026-11-02). Ayni olayin birden cok satiri tek satira
    # iner; gonderilmis habere karsi yalniz DAHA ILERI asama gecer. Gerekce
    # ve olcum icin radar/kume.py bas yorumuna bakiniz (2026-W40: POSCO'nun
    # tek yatirimi bes satir olarak girmisti).
    from . import kume
    st_k = state.load()
    gecmis_k = [b for b in (st_k.get("son_basliklar") or [])
                if not taxonomy.is_junk_title(b.get("b", ""))]
    onceki_n = len(rows)
    rows = [r for r in rows if not kume.gecmis_tekrari(r, gecmis_k)]
    gecmisten = onceki_n - len(rows)
    rows, kume_n = kume.kumele(rows)
    if gecmisten or kume_n:
        print("kumeleme: %d satir gecmiste gonderilmis olaya ayni/geri asama, "
              "%d kume birlestirildi -> %d satir" % (gecmisten, kume_n, len(rows)))

    # REZERV (2026-08-27). Bulten ortalama 7-8 gelisme tasimali ama taze arz
    # bunu her hafta karsilamiyor (olcum: haftada ~1-3 kapsam ici haber).
    # Kapiyi GEVSETMEK yerine, gecmiste kapiyi gecmis ve tarihi dogrulanmis
    # ama pencere disinda kaldigi icin hic gonderilmemis satirlar kullanilir.
    st_r = state.load()

    # BULUNAN HAVUZU (2026-08-31) - hacim sorununun asil cozumu.
    #
    # Gunluk tarama kabul ettigi satiri hicbir yere kaydetmiyordu ve
    # aggregator sonuclari OYNAK: bir gun gorunen haber ertesi gun
    # beslemede yok. Olcum, hafta boyunca gorulup kaybolan satirlari
    # gosterdi - Manaksia (29.08), ArcelorMittal Tubarao'nun R$ 5 milyar
    # cercevesi (31.08), KEZAD galvaniz hatti (31.08). Ucu de tek bir
    # taramada gorundu ve bir daha cikmadi. Sistem haftada 5-6 haber
    # GORUYOR, bultene 2 tanesi giriyordu.
    #
    # Bu havuz PENCERE ICI, kapiyi gecmis, tarihi dogrulanmis, henuz
    # gonderilmemis satirlari tutar. Once buradan tamamlanir (taze ve
    # pencere ici), sonra rezerve bakilir (pencere disi, "GEC YAKALANDI").
    # Kapi GEVSEMEZ: satirlar zaten ayni kapidan gecmistir, degisen tek sey
    # unutulmamalaridir.
    # TAZE SATIRLAR DA HAVUZ KAPISINDAN GECER (2026-11-02, W45): tarama kapisi
    # govdeyi de okuyor, havuz/otomatik denetim yalniz BASLIGI. Tutarsizlik
    # sonucu taze bir satir ("Nippon Steel Raises US Mill Upgrade to $3 Billion")
    # listede sayilip sonradan elendi ve liste havuzdan TAMAMLANAMADI. Burada
    # elenirse havuz/rezerv bosluk icin devreye girer.
    once = len(rows)
    rows = [r for r in rows if _rezerv_hala_gecerli(r)]
    if len(rows) != once:
        print("havuz kapisi: %d taze satir basliga gore elendi" % (once - len(rows)))
    bulunan = _bulunan_guncelle(st_r, rows)
    rezerv = _rezerv_guncelle(st_r, payload.pop("rezerv", []), rows)

    eksik = max(HEDEF_SATIR - len(rows), 0)
    bulunandan = _rezervden_sec(bulunan, rows, st_r, eksik)
    if bulunandan:
        for r in bulunandan:
            r.pop("rezerv", None)      # pencere ici - "GEC YAKALANDI" degil
        rows = rows + bulunandan
        print("bulunan havuzundan %d satir eklendi (havuzda %d kaldi)"
              % (len(bulunandan), len(bulunan) - len(bulunandan)))

    eksik = max(HEDEF_SATIR - len(rows), 0)
    kullanilan = _rezervden_sec(rezerv, rows, st_r, eksik)
    if kullanilan:
        rows = rows + kullanilan
        print("rezervden %d satir eklendi (havuzda %d kaldi)"
              % (len(kullanilan), len(rezerv) - len(kullanilan)))
    payload["bulunan_kullanilan"] = len(bulunandan)
    payload["bulunan_havuz"] = len(bulunan) - len(bulunandan)
    payload["rezerv_kullanilan"] = len(kullanilan)
    payload["rezerv_havuz"] = len(rezerv) - len(kullanilan)

    payload["rows"] = rows[:max(TARGET_ROWS, 0)] if a.limit else rows
    payload["period"] = per
    payload["generated"] = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    payload["version"] = VERSION

    base = os.path.join(OUT, "hafta_%s" % per)
    # GUNLUK TARAMA HAFTALIK ARSIVE YAZMAZ (2026-08-29). Tarama modu
    # email.html'e dokunmuyordu ama satir arsivini (hafta_<donem>.json ve
    # needs_ai.json) hafta adiyla yazmaya devam ediyordu: 2026-08-29
    # taramasi, gonderilen 6 satirlik W35 bulteninin kaydini rezervden gelen
    # 4 satirla EZDI. Gonderilen bultenin kaydi yalniz haftalik kosu ve
    # finalize tarafindan yazilir.
    cikti = os.path.join(OUT, "tarama") if a.sadece_tarama else base
    # Elenenler ayri dosyaya: kaynak/sozluk ayarini ancak bunu okuyarak yapabilirim.
    rejects = payload.pop("rejects", [])
    _w(os.path.join(OUT, "reddedilenler.json"),
       {"donem": per, "adet": len(rejects), "kayitlar": rejects})
    _w(cikti + ".json", payload)

    ask = [{"anahtar": r["anahtar"], "baslik": r["baslik"], "url": r["url"],
            "eksik": r["eksik"], "mevcut": {k: r[k] for k in
                                            ("firma", "ulke", "hat", "asama")}}
           for r in payload["rows"] if r["eksik"]]
    say = [{"anahtar": r["anahtar"], "tarih": r["tarih"], "firma": r["firma"],
            "ulke": r["ulke"], "hat": r["hat"], "asama": r["asama"],
            "baslik": r["baslik"], "url": r["url"]}
           for r in payload["rows"] if r.get("kategori") != "Yatirim"]
    _w(os.path.join(OUT, "tarama_needs_ai.json" if a.sadece_tarama
                    else "needs_ai.json"),
       {"donem": per, "duzelt": ask, "cumle_yaz": say,
        "teknoloji_adaylari": payload.get("tech_pool", [])})

    # TEKNOLOJI KOSESI HER HAFTA DOLU OLMALI (2026-08-27). Taze aday cikmayan
    # hafta cok: kosenin havuzu 6 aylik olsa da bir haftada 0 aday olabiliyor
    # (2026-W34'te tam olarak boyle oldu). Bu yuzden aday havuzu da KALICI:
    # kullanilmayan adaylar state'te birikir, koşe onlardan doldurulur.
    payload["tech_pool"] = _tech_havuz(st_r, payload.get("tech_pool", []))

    if a.commit_state:
        # TARAMA "GONDERILDI" ISARETI KOYMAZ (2026-08-27).
        #
        # Tarama posta GONDERMIYOR - postayi editor onayi gonderiyor. Onceki
        # surum her kosuda satirlari seen'e yaziyordu ve onaylanmayan her kosu
        # gercek haberleri sessizce YAKIYORDU: gercekten gonderilen tek bulten
        # 3 satirlik iken state'te 21 satir "gonderilmis" isaretliydi.
        # "Gonderildi" isaretini artik YALNIZ finalize koyar. Tarama sadece
        # kendi kalici havuzlarini tazeler - GUNLUK kosunun butun isi budur.
        st = state.load()
        st["rezerv"] = [r for r in (st_r.get("rezerv") or [])
                        if r["anahtar"] not in st["seen"]]
        st["bulunan"] = [r for r in (st_r.get("bulunan") or [])
                         if r["anahtar"] not in st["seen"]]
        st["tech_rezerv"] = [t for t in (st_r.get("tech_rezerv") or [])
                             if t["anahtar"] not in st.get("tech_seen", {})]
        st["periods"] = (st.get("periods") or []) + [{
            "donem": per, "satir": len(payload["rows"]),
            "uretim": payload["generated"], "stats": payload["stats"]}]
        state.prune(st)
        state.save(st)
        print("havuz: bulunan %d satir, rezerv %d satir, teknoloji adayi %d"
              % (len(st["bulunan"]), len(st["rezerv"]), len(st["tech_rezerv"])))

    if a.sadece_tarama:
        # GUNLUK TARAMA MODU (2026-08-27). Gunluk kosu yalniz HAVUZ besler.
        # email.html ve taslak rapora DOKUNMAZ - editorun o hafta onaylayip
        # gonderdigi metnin kaydi ertesi gunun taramasiyla silinmemeli.
        _rapor_ozet(per, payload, ask, say, cikti)
        return 0

    # Otomatik posta govdesi: yapay zeka ozeti yoksa kurallı metin kullanilir.
    from . import compose
    sayi = len(state.load().get("periods", [])) + 1
    tech = payload["tech_pool"][:3]
    for t in tech:
        t["konu"] = t["baslik"]
        t["metin"] = compose.tech_blurb(t)
    with open(os.path.join(OUT, "email.html"), "w", encoding="utf-8") as f:
        f.write(render.email_html(payload, None, tech, sayi))
    # tech_seen'i de YALNIZ finalize yazar: kosede gorunen aday, postaya
    # girmedikce "tanitilmis" sayilmaz.

    html = render.html_report(payload)
    with open(base + "_taslak.html", "w", encoding="utf-8") as f:
        f.write(html)
    render.write_csv(base + ".csv", payload["rows"])
    render.write_email(os.path.join(OUT, "email_body.md"), payload)

    _rapor_ozet(per, payload, ask, say, base)
    return 0


def _rapor_ozet(per, payload, ask, say, base):
    s = payload["stats"]
    print("\n[%s] ham %d -> aday %d -> makale %d -> KABUL %d  (tarihsiz %d, "
          "pencere disi %d, kapsam disi %d, tekrar %d)"
          % (per, s["ham"], s["on_eleme_gecti"], s["makale_acildi"], s["kabul"],
             s["tarihsiz_elendi"], s["pencere_disi"], s["kapsam_disi"], s["tekrar"]))
    print("rezerv: %d kullanildi, havuzda %d"
          % (payload.get("rezerv_kullanilan", 0), payload.get("rezerv_havuz", 0)))
    print("duzeltilecek satir: %d | cumle yazilacak: %d" % (len(ask), len(say)))
    hs = payload.get("host_saglik") or {}
    if hs:
        print("host: " + " | ".join(
            "%s %d istek%s" % (h.replace("www.", ""), d["istek"],
                               " SOGUTMADA" if d["sogutmada"] else
                               (" (%d hiz siniri)" % d["hiz_siniri"]
                                if d["hiz_siniri"] else ""))
            for h, d in hs.items()))
    print("cikti: %s.json" % base)


def _tech_havuz(st, taze):
    """Teknoloji adaylarini KALICI havuzda biriktirir ve siralar.

    Daha once kosede tanitilmis (tech_seen) adaylar dusulur. Boylece aday
    cikmayan haftada bile kose bos kalmaz - gecmis haftalarin kullanilmamis
    adaylari beklemede durur.
    """
    havuz = {t["anahtar"]: t for t in (st.get("tech_rezerv") or [])}
    for t in taze:
        havuz.setdefault(t["anahtar"], t)
    gorulen = st.get("tech_seen") or {}
    kalan = [t for k, t in havuz.items() if k not in gorulen]
    kalan.sort(key=lambda t: t.get("tarih", ""), reverse=True)
    st["tech_rezerv"] = kalan[:60]
    return list(st["tech_rezerv"])


def _rezerv_alanlarini_tazele(r):
    """Rezervdeki satirin ulkesini GUNCEL sozlukle yeniden turetir.

    Rezerv 540 gun geriye uzaniyor; havuza giren satir o gunku kodun verdigi
    KARARI tasiyor. Sozlukteki bir hata duzeltildiginde havuzdaki eski satir
    hala bozuk degeri taşıyor - 2026-08-29'da tam bu oldu: COUNTRY_MAP'te
    "\\bindia" sinirsizdi ve Gary, INDIANA'daki tesisi anlatan
    "U. S. Steel Announces Plans to Restart Gary Tin Mill" satirina
    "Hindistan" yazmisti. Desen duzeltildikten sonra bile satir rezervden
    Hindistan olarak cikmaya devam etti.

    Yalnizca BASLIKTAN turetilebilen bir ulke varsa yazilir; baslik ulke
    tasimiyorsa (KG Steel/Dangjin gibi) govdeden gelen eski deger korunur.
    """
    # BASLIK DA GUNCEL TEMIZLIKTEN GECER. Havuzdaki baslik, havuza girdigi
    # gunku temizlikle yazilmistir; yayinci kuyrugu kesimi sonradan
    # eklendiginde havuzdaki satir hala "... | Mesteel - Online News"
    # tasiyordu ve rapora oyle girdi (2026-W36).
    tb = taxonomy.temiz_baslik(r.get("baslik") or "", r.get("url") or "")
    if tb and tb != r.get("baslik"):
        r["baslik"] = tb
    u = taxonomy.match_country(r.get("baslik") or "")
    if u and u != (r.get("ulke") or ""):
        r["ulke"] = u
    return r


def _imza_carpisti(r, secili, gecmis):
    """Ayni tedarikci + ayni asama + (ayni ulke YA DA ayni gun) mu?

    Hat vurgusu farkli olsa da ayni olaydir. KG Steel Dangjin vakasinda iki
    yayindan biri ulkeyi hic yazmamisti ("" vs "G. Kore"), bu yuzden ulke tek
    basina yetmiyor; ayni gun ayni tedarikcinin ayni asamadaki iki ayri isi
    olmasi ise pratikte gorulmuyor.

    HEM bu kosunun satirlarina HEM DE gonderilmis satirlara bakilir. Ikincisi
    2026-08-29'da eklendi: W35'te giden "KG Steel selects Primetals for
    Dangjin PLTCM upgrade" satirinin STI varyanti ("Primetals to modernise
    Korean pickling line") rezervde bekliyordu ve imza yalnizca bos olan
    `rows` listesine karsi isletildigi icin geri donuyordu.
    """
    ted = taxonomy.fold(r.get("tedarikci") or "")
    if not ted:
        return False
    asama, ulke, tarih = (r.get("asama") or ""), (r.get("ulke") or ""), (r.get("tarih") or "")
    for x in secili:
        if taxonomy.fold(x.get("tedarikci") or "") != ted:
            continue
        if (x.get("asama") or "") != asama:
            continue
        if (x.get("ulke") or "") == ulke or (x.get("tarih") or "") == tarih:
            return True
    for b in gecmis:
        if taxonomy.fold(b.get("ted") or "") != ted:
            continue
        if (b.get("a") or "") != asama:
            continue
        if (b.get("u") or "") == ulke or (b.get("t") or "") == tarih:
            return True
    return False


def _rezervden_sec(rezerv, rows, st, eksik):
    """Rezervden satir secer - AYNI TEKRAR DENETIMINDEN gecirerek.

    Ilk surum havuzun basindan "eksik" kadar satiri dogrudan aliyordu; hicbir
    tekrar denetimi yoktu. Sonuc 2026-08-27 taramasinda goruldu: ayni KG Steel
    Dangjin olayi listeye IKI KEZ girdi -
        "KG Steel selects Primetals for Dangjin PLTCM upgrade"   (SteelOrbis)
        "Primetals to modernise Korean pickling line"            (STI)
    Iki yayin ayni olayi farkli hat vurgusuyla yazinca olay parmak izleri
    kesismiyor; taze satirlarda calisan uc bacakli savunma burada hic
    calismiyordu.
    """
    if eksik <= 0 or not rezerv:
        return []
    # NE KADAR GERIYE GIDILIR - LISTENIN DOLULUGUNA BAGLI (2026-08-31).
    # Kullanici kurali: "5 taneden az haber oldugu her an 3 aylik verilere
    # erissin, en uygun ve yakin tarihli olanlari alsin."
    #
    # Rezerv 540 gun SAKLAR ama saklamak ile bultene koymak ayni sey degil:
    # 2026-W36 listesi Mart/Mayis/Temmuz tarihli satirlarla dolduruldu ve
    # okuyucu icin bu haftalik bulten degil arsiv taramasi olur. Saklama
    # TEKRAR SAVUNMASI icindir; koyma hakki asagidaki sinirla olculur.
    gun = REZERV_KULLANIM_GUN if len(rows) < REZERV_ESIK else REZERV_DAR_GUN
    en_eski = (dt.date.today() - dt.timedelta(days=gun)).isoformat()
    rezerv = [r for r in rezerv if (r.get("tarih") or "") >= en_eski]
    if not rezerv:
        return []
    secili = list(rows)
    # KALICI OLAY HAFIZASI DA SORULUR (2026-08-31). Taze satirlar collect
    # icinde state["events"]'e karsi denetleniyordu; REZERVDEN secim ise
    # yalnizca BU KOSUNUN satirlarina bakiyordu. Sonuc olculdu:
    #   gonderilen (W35): "Roofings Unveils $125m Steel Mill, Doubles
    #                      Cold-Rolled Capacity to 300,000 Tonnes" (Uganda)
    #   rezervden gelen : "RRM starts up new cold-mill complex with Danieli
    #                      technology"
    # RRM = Roofings Rolling Mills; ayni Uganda soguk hadde kompleksi, baska
    # yayin, baska kisaltma. Ustelik satirin ulkesi "Turkiye" okunmustu,
    # yani ulke bacagi da korlesmisti - ama TEDARIKCI+HAT+ASAMA bacagi
    # hafizada duruyordu ve sorulsaydi yakalanacakti.
    olaylar = set(st.get("events") or {})
    for r in secili:
        olaylar |= set(r.get("olaylar") or [])
    gecmis = [b for b in (st.get("son_basliklar") or [])
              if not taxonomy.is_junk_title(b.get("b", ""))]
    out = []
    # En yeniden eskiye: okuyucu once guncel olani gorsun.
    for r in sorted(rezerv, key=lambda r: r.get("tarih", ""), reverse=True):
        _rezerv_alanlarini_tazele(r)
        # IZLER YENIDEN URETILMEZ - denendi ve GERCEK HABER kaybettirdi.
        # event_keys'in "kim|hat|hat_turu|asama" bacagi ULKESIZDIR ve
        # tedarikci ayni olunca farkli ulkelerdeki iki ayri isi
        # birlestiriyor: "Primetals to modernise Korean pickling line" ile
        # "Primetals to modernise Indian pickling line" ayni sayildi.
        # Havuzdaki iz zaten satirin kendi alanlarindan uretilmisti; RRM
        # tekrarini yakalayan sey iz uretimi degil, KALICI HAFIZANIN
        # sorulmasiydi (asagida olaylar kumesine state["events"] konuldu).
        if len(out) >= eksik:
            break
        eks = set(r.get("olaylar") or [])
        if eks & olaylar:
            continue                                   # ayni olayin varyanti
        if any(taxonomy.similar_titles(r.get("baslik", ""), x.get("baslik", ""))
               for x in secili):
            continue                                   # bu listede benzeri var
        # AYNI FIRMA + AYNI HAT = AYNI OLAY (kume.py): havuzdan gelen satir
        # listede zaten o olayin temsilcisi varsa girmez, gonderilmisse de
        # yalniz daha ileri asama girer.
        if any(kume._ayni_kume(r, x) for x in secili):
            continue
        if kume.gecmis_tekrari(r, gecmis):
            continue
        if any(taxonomy.similar_titles(r.get("baslik", ""), b.get("b", ""))
               for b in gecmis):
            continue                                   # gecmiste gonderilmis
        # AYNI TEDARIKCI + AYNI ASAMA + (ayni ulke YA DA ayni tarih):
        # hat vurgusu farkli olsa da ayni olaydir. KG Steel vakasinda iki
        # yayindan biri ulkeyi hic yazmamisti ("" vs "G. Kore"), bu yuzden
        # ulke tek basina yetmiyor; ayni gun ayni tedarikcinin ayni asamadaki
        # iki ayri isi olmasi ise pratikte gorulmuyor.
        ted = taxonomy.fold(r.get("tedarikci") or "")
        if ted and _imza_carpisti(r, secili, gecmis):
            continue
        out.append(r)
        secili.append(r)
        olaylar |= eks
    return out


def _bulunan_guncelle(st, rows):
    """Bu kosuda KABUL EDILEN satirlari kalici havuza yazar ve havuzu dondurur.

    Havuza yalniz TAZE satirlar girer - rezervden gelenler zaten kendi
    havuzundadir. Cikisa da ayni disiplin uygulanir: gonderilmis olan
    duser, guncel kapiyi gecmeyen duser (bkz. _rezerv_hala_gecerli).
    """
    havuz = {r["anahtar"]: r for r in (st.get("bulunan") or [])}
    for r in rows:
        if r.get("anahtar") and not r.get("rezerv"):
            havuz.setdefault(r["anahtar"], dict(r))
    seen = st.get("seen") or {}
    bu_kosu = {r.get("anahtar") for r in rows}
    kosede = {k[5:] for k in (st.get("tech_seen") or {}) if k.startswith("tech:")}
    temiz = [r for k, r in havuz.items()
             if k not in seen and k not in kosede and _rezerv_hala_gecerli(r)]
    temiz = _havuz_tekrarsiz(temiz)
    temiz.sort(key=lambda r: r.get("tarih", ""), reverse=True)
    st["bulunan"] = temiz[:REZERV_MAX]
    # Bu kosuda zaten listede olanlar tekrar EKLENMEZ ama havuzda KALIR:
    # bulten onaylanmazsa gelecek hafta yine cikabilmeliler.
    return [r for r in st["bulunan"] if r["anahtar"] not in bu_kosu]


def _havuz_tekrarsiz(satirlar):
    """Havuzda ayni haber iki kez durmaz - anahtar DEGIL, BASLIK bazli.

    Havuzlar iki ayri yoldan doluyor (haftalik/gunluk kosu ve "radar
    dogrula") ve ayni haber iki yoldan girince anahtarlari farkli oluyor:
    biri arama beslemesinin yonlendirme adresinden, digeri yayincinin
    kendi adresinden turuyor; baslik da yayinci kuyrugu yuzunden farkli
    olabiliyor. 2026-08-31'de rezervde Marcegaglia ve ArcelorMittal Poland
    satirlari IKISER kez durdu.

    Ayni baslik icin YAYINCININ KENDI adresini tasiyan kayit tutulur -
    okuyucu icin aggregator yonlendirmesinden iyidir.
    """
    ix, out = {}, []
    for r in satirlar:
        k = taxonomy.fold(taxonomy.temiz_baslik(r.get("baslik") or "",
                                                 r.get("url") or "")).strip()
        if not k:
            continue
        j = ix.get(k)
        if j is None:
            ix[k] = len(out)
            out.append(r)
            continue
        eski = out[j]
        yeni_iyi = not _aggregator_adresi(r.get("url"))
        eski_iyi = not _aggregator_adresi(eski.get("url"))
        if yeni_iyi and not eski_iyi:
            out[j] = r
    return out


def _aggregator_adresi(url):
    u = (url or "").lower()
    return ("news.google.com" in u or "bing.com/news" in u
            or "msn.com" in u or "/rss/articles/" in u)


def _rezerv_hala_gecerli(r):
    """Rezervdeki satir BUGUNKU kapiyi hala geciyor mu?

    HAVUZ, KARARI TASIR - KODU DEGIL. Rezerv 540 gun geriye uzaniyor; bir
    satir havuza girdiginde o gunku kapinin verdigi karari yaniyla birlikte
    tasiyor. Kapida bir delik kapatildiginda havuzda duran eski satir
    etkilenmiyor ve haftalar sonra listeye giriyor.

    2026-08-31'de olculdu. Ayni gun iki delik kapatilmisti:
      "Triple-S Steel acquires Camden Yards Steel"        (sirket satin alma)
      "Ezz Flat Steel signs agreement with Danieli for QSP modernization"
                                                          (QSP = sicak taraf)
    Ikisi de kapali kapidan bir daha GECEMEZ - ama ayni kosuda REZERVDEN
    listeye girdiler, cunku rezervden secim kapiyi hic sormuyordu.

    Ayni aile: _rezerv_alanlarini_tazele ulkeyi guncel sozlukle yeniden
    turetir (Gary/Indiana vakasi). Burada da havuz her kosuda guncel kapiya
    gore temizlenir; dusen satir havuzdan KALICI olarak cikar, bir daha
    istek ya da denetim harcatmaz.
    """
    t = r.get("baslik") or ""
    if not t:
        return False
    # Last-Modified'dan gelen tarih havuzda da GECERSIZ (2026-11-02): kaynak
    # kaldirildi, havuzdaki eski kayitlar da dusmeli (Primetals vakasi).
    if r.get("tarih_kaynagi") == "last-modified":
        return False
    ok, _ = taxonomy.in_scope(t)
    if ok and taxonomy.haber_olayi(t):
        return True
    return bool(taxonomy.genel_yatirim(t))


def _rezerv_guncelle(st, yeni_adaylar, rows):
    """Rezerv havuzunu tazeler ve KULLANILABILIR satirlari dondurur.

    Havuza giren satir zaten kapsam kapisini gecmis ve tarihi sayfadan
    dogrulanmistir; tek farki tarihinin haftalik pencerenin disinda
    kalmasidir. Raporlanmis (seen) ya da bu koşuda zaten listeye girmis
    olanlar havuzdan dusulur.
    """
    havuz = {r["anahtar"]: r for r in (st.get("rezerv") or [])}
    for r in yeni_adaylar:
        havuz.setdefault(r["anahtar"], r)
    seen = st.get("seen") or {}
    bu_kosu = {r.get("anahtar") for r in rows}
    kosede = {k[5:] for k in (st.get("tech_seen") or {}) if k.startswith("tech:")}
    temiz = [r for k, r in havuz.items()
             if k not in seen and k not in bu_kosu and k not in kosede
             and _rezerv_hala_gecerli(r)]
    temiz = _havuz_tekrarsiz(temiz)
    temiz.sort(key=lambda r: r.get("tarih", ""), reverse=True)
    st["rezerv"] = temiz[:REZERV_MAX]
    return list(st["rezerv"])


def cmd_review(a):
    p = os.path.join(OUT, "needs_ai.json")
    if not os.path.exists(p):
        print("once `run` calistirin"); return 1
    d = json.load(open(p, encoding="utf-8"))
    print("Donem: %s" % d["donem"])
    print("\n--- DUZELTME GEREKEN (%d) ---" % len(d["duzelt"]))
    for r in d["duzelt"]:
        print("%s | eksik=%s | %s" % (r["anahtar"], ",".join(r["eksik"]), r["baslik"][:90]))
    print("\n--- CUMLE YAZILACAK (%d) ---" % len(d["cumle_yaz"]))
    for r in d["cumle_yaz"]:
        print("%s | %s | %s" % (r["anahtar"], r["tarih"], r["baslik"][:90]))
    return 0


def _eklenen_satirlar(ham, payload):
    """ozet.json'daki "ai_eklenen" maddelerini rapor satirina cevirir.

    Yalnizca URL'si ve basligi olan maddeler satir olur; sadece aciklama
    icin yazilmis bir madde (ornek "STI 403 verdi, elle bakildi") listeye
    girmez ama AI bolumunde yine gorunur. Ayni URL listede zaten varsa
    tekrar eklenmez.
    """
    varolan = {(r.get("url") or "").rstrip("/") for r in payload["rows"]}
    out = []
    for x in ham:
        if not isinstance(x, dict):
            continue
        url, baslik = (x.get("url") or "").strip(), (x.get("baslik") or "").strip()
        if not url or not baslik or url.rstrip("/") in varolan:
            continue
        varolan.add(url.rstrip("/"))
        out.append({
            "tarih": x.get("tarih", ""), "firma": x.get("firma", ""),
            "ulke": x.get("ulke", ""), "hat": x.get("hat") or "Belirsiz",
            "asama": x.get("asama") or "Belirsiz",
            "tedarikci": x.get("tedarikci", ""), "kapasite": x.get("kapasite", ""),
            "tutar": x.get("tutar", ""), "baslik": baslik,
            "kaynak": x.get("kaynak", ""), "kaynak_id": x.get("kaynak_id", ""),
            "url": url, "tarih_kaynagi": x.get("tarih_kaynagi") or "editor",
            "eksik": [], "anahtar": x.get("anahtar") or state.norm_key(baslik, url),
            "kategori": x.get("kategori") or "Hat", "olaylar": [],
            "puan": 0.0, "elle_eklendi": True,
        })
    return out


def cmd_finalize(a):
    per = a.period or _period(dt.date.today())
    base = os.path.join(OUT, "hafta_%s" % per)
    payload = json.load(open(base + ".json", encoding="utf-8"))
    # -s UNUTULURSA SESSIZCE GECMEZ (2026-08-31). "-s" verilmeyince doc bos
    # kaliyor ve finalize editorun BUTUN kararlarini - duzeltmeleri,
    # cikarilan satirlari, Turkce cumleleri, teknoloji kosesini - sessizce
    # atlayip yine de bulten uretiyor VE her satiri "gonderildi"
    # isaretliyordu. 2026-W36'da tam bu oldu: cikarilmasi gereken iki satir
    # (bir tekrar, bir tarihi celiskili) postaya girecekti ve dordu de
    # hafizaya yazildi. Ozet dosyasi diskte duruyorken onu ATLAMAK bir
    # secim olamaz.
    ozet_yolu = a.summaries or os.path.join(OUT, "ozet.json")
    if not a.summaries and os.path.exists(ozet_yolu):
        print("uyari: -s verilmedi, %s kullaniliyor" % ozet_yolu)
    if not os.path.exists(ozet_yolu):
        print("HATA: editor ozeti yok (%s). Ozetsiz finalize, editorun butun\n"
              "      kararlarini atlar ve satirlari 'gonderildi' isaretler." % ozet_yolu)
        return 1
    doc = json.load(open(ozet_yolu, encoding="utf-8"))
    _ozet_uygula(payload, doc)
    tech = doc.get("teknolojiler", [])
    _yaz(payload, doc, tech, base, os.path.join(OUT, "email.html"))
    # Editor yolunda hafiza finalize aninda yazilir (eski davranis); posta
    # ONAY ile gonder.yml'den gider. Donem 'gonderilen_donemler'e YAZILMAZ:
    # onu yalniz otomatik hat, SMTP basarisindan sonra yazar.
    _isaretle(payload, tech)
    pdf_ok = render.to_pdf(base + ".html", base + ".pdf")
    print("final: %s.html (%d satir), pdf=%s, email.html yenilendi"
          % (base, len(payload["rows"]), pdf_ok))
    return 0


def _ozet_uygula(payload, doc):
    """Editor/otomatik yazar ozetini payload'a isler (yerinde degistirir)."""
    fixes = doc.get("duzeltmeler", {})
    for r in payload["rows"]:
        for k, v in (fixes.get(r["anahtar"]) or {}).items():
            if k in r and v:
                r[k] = v
    # OLAY PARMAK IZLERI DUZELTMEDEN SONRA YENIDEN URETILIR (2026-08-31).
    #
    # Parmak izi kosu aninda, HENUZ DUZELTILMEMIS alanlardan uretiliyordu ve
    # editorun duzeltmesi hafizaya hic yansimiyordu. 2026-W35'te giden
    # Roofings satirinin kayitli anahtari sudur:
    #     "roofings unveils|hat|Soguk hadde|Belirsiz"
    # cunku firma adi baslikta "Roofings Unveils" olarak okunmus, ulke bos,
    # asama "Belirsiz" kalmisti. Editor bunlari duzeltti (Roofings Group /
    # Uganda / Ilk urun / Danieli) ama hafizada yine bozuk anahtar kaldi.
    # Sonuc 2026-08-31'de goruldu: AYNI olayin iki varyanti daha listeye
    # girdi -
    #     "Museveni Unveils $120 Million Steel Complex to Boost Ugandan..."
    #     "Roofings Group, Uganda'da 125 milyon dolarlik yeni celik
    #      tesisini faaliyete gecirdi"          (ayni haberin Turkcesi)
    # Baslik benzerligi bunlari yakalayamaz (biri cumhurbaskanini one
    # cikariyor, digeri baska dilde); olay parmak izi yakalamaliydi ve
    # yakalayamamasinin sebebi duzeltmenin ize islenmemesiydi.
    #
    # ESKI ANAHTAR DA KORUNUR: baska bir yayin ayni bozuk okumayi
    # uretebilir, o kapiyi kapatmanin bir zarari yok.
    from .collect import event_keys
    for r in payload["rows"]:
        eski = set(r.get("olaylar") or [])
        r["olaylar"] = sorted(eski | set(event_keys(r)))

    drop = set(doc.get("cikar", []))
    if drop:
        payload["rows"] = [r for r in payload["rows"] if r["anahtar"] not in drop]

    # ELLE EKLENEN SATIRLAR (2026-08-17). "ai_eklenen" hem listeye satir
    # ekler hem de postadaki "AI Kontrolu ve Eklemeleri" bolumunu besler -
    # tek kaynak, tek dogru. Satir "elle_eklendi" isaretiyle gelir, posta
    # bunu "+ AI" rozetiyle gosterir.
    eklenen = _eklenen_satirlar(doc.get("ai_eklenen") or [], payload)
    if eklenen:
        payload["rows"] += eklenen
        # Hat satirlari once, Yatirim sonra. Kararli siralama, mevcut
        # satirlarin score.rank'ten gelen sirasini bozmaz.
        payload["rows"].sort(key=lambda r: r.get("kategori") == "Yatirim")

    return payload


def _yaz(payload, doc, tech, base, email_yolu):
    """html + csv + posta govdesini diske yazar. HAFIZAYA DOKUNMAZ."""
    html = render.html_report(payload, doc.get("cumleler", {}), doc.get("exec", ""))
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(html)
    render.write_csv(base + ".csv", payload["rows"])
    sayi = len(state.load().get("periods", [])) or 1
    with open(email_yolu, "w", encoding="utf-8") as f:
        f.write(render.email_html(payload, doc, tech, sayi))


def _isaretle(payload, tech, donem=None):
    """Giden bulteni hafizaya yazar: seen, events, son_basliklar, tech_seen.

    donem verilirse 'gonderilen_donemler'e de eklenir - YALNIZ otomatik hat
    bunu SMTP basarisindan sonra yapar; gonder.yml ayni donemi ikinci kez
    gondermesin diye buna bakar. DENEME kosulari bu fonksiyonu HIC
    cagirmaz: deneme sirasinda kullanilan haber sonraki gercek gonderimde
    yine kullanilabilir (kullanici karari, 2026-11-02).
    """
    st3 = state.load()
    for t in tech or []:
        if t.get("anahtar"):
            st3["tech_seen"][t["anahtar"]] = t.get("tarih", "")
    for r in payload["rows"]:
        if r.get("anahtar"):
            st3["seen"][r["anahtar"]] = r.get("tarih", "")
        # Kumelenmis (ayni olayi anlatan) diger yayinlar da 'gonderildi' sayilir;
        # yoksa ertesi hafta havuzdan ayni olay ikinci yayiniyla geri doner.
        for k in r.get("kume_anahtarlari") or []:
            if k:
                st3["seen"][k] = r.get("tarih", "")
        for k in r.get("olaylar", []):
            st3["events"][k] = r.get("tarih", "")
        if not taxonomy.is_junk_title(r.get("baslik", "")):
            # ted/u DE YAZILIR (2026-08-29): rezervden satir secerken
            # "ayni tedarikci + ayni asama + (ayni ulke ya da ayni gun)"
            # imzasi kullaniliyor, ama hafizada yalnizca baslik/tarih/asama
            # duruyordu. Imza gonderilmis satirlara karsi hic isletilemiyor,
            # bu yuzden gonderilmis bir olayin baska yayindaki varyanti
            # rezervden geri donebiliyordu.
            st3["son_basliklar"].append({"b": r.get("baslik", ""),
                                         "t": r.get("tarih", ""),
                                         "a": r.get("asama", ""),
                                         "ted": r.get("tedarikci", ""),
                                         "u": r.get("ulke", "")})
    st3["son_basliklar"] = state.dedup_basliklar(st3["son_basliklar"])
    if donem:
        d = st3.setdefault("gonderilen_donemler", [])
        if donem not in d:
            d.append(donem)
        st3["gonderilen_donemler"] = d[-60:]
    state.prune(st3)
    state.save(st3)
    print("hafiza: %d satir 'gonderildi' olarak isaretlendi" % len(payload["rows"]))



# ----------------------------------------------------------------------
# OTOMATIK HAT (2026-11-02): editor rutini olmadan bulten
# ----------------------------------------------------------------------
MIN_SATIR = int(os.environ.get("RADAR_MIN_SATIR", "2"))
MAX_ERISILEMEYEN_ORAN = 0.4
MIN_HAM = 500
MAX_YAS_GUN = 100            # rezerv kullanimi 90 gun + pay


# HAFTALIK (2026-11-02 son karar: "haftalik calisan bir sistem"). Ayni hafta
# icinde ikinci gonderimi engeller (elle tetikleme + zamanlanmis kosu).
DONGU_GUN = int(os.environ.get("RADAR_DONGU_GUN", "7"))


def _son_gonderim(st):
    """Son GERCEK gonderimin Pazartesi tarihi (gonderilen_donemler'den) ya da None."""
    son = None
    for d in st.get("gonderilen_donemler") or []:
        try:
            y, w = d.split("-W")
            g = dt.date.fromisocalendar(int(y), int(w), 1)
        except Exception:
            continue
        if son is None or g > son:
            son = g
    return son


def _satir_suzgeci(payload, bugun, st):
    """Satir bazli SON denetim: kusurlu satiri CIKARIR (tum bulteni durdurmaz).

    Taze bir `run` ciktisinda bunlarin hicbiri tetiklenmemelidir (kapi ve
    kumeleme zaten uygulanmistir); tetiklenirse eski/bozuk veri vardir ve
    cikarilan satir gerekcesiyle karar.json'a yazilir. Donus: [(baslik, neden)].
    """
    from . import kume
    seen = st.get("seen") or {}
    events = st.get("events") or {}
    elenen, kalan = [], []
    for r in payload["rows"]:
        ad = r.get("baslik", "")
        neden = None
        if not (r.get("url") or "").startswith("http"):
            neden = "adresi yok"
        else:
            try:
                gun = (bugun - dt.date.fromisoformat(r.get("tarih", ""))).days
                if gun < -1:
                    neden = "tarihi gelecekte"
                elif gun > MAX_YAS_GUN:
                    neden = "tarih %d gun eski" % gun
            except ValueError:
                neden = "tarihi gecersiz"
        if not neden and not _rezerv_hala_gecerli(r):
            neden = "guncel kapiyi gecmiyor"
        if not neden and (r.get("anahtar") in seen
                          or any(k in events for k in r.get("olaylar") or [])):
            neden = "daha once gonderilmis"
        if not neden and kume.gecmis_tekrari(r, st.get("son_basliklar") or []):
            neden = "gonderilmis olayin tekrari"
        if not neden:
            for k in kalan:
                if kume._ayni_kume(k, r):
                    neden = "ayni olay: " + k.get("baslik", "")[:50]
                    break
        if neden:
            elenen.append((ad, neden))
        else:
            kalan.append(r)
    payload["rows"] = kalan
    return elenen


def _kalite_kapisi(payload, per):
    """Otomatik gonderimin SON kapisi: GLOBAL kosullar. Bos liste = gonderilebilir.

    'Bozuk bulten gondermektense gondermemek yegdir' kurali: bu kapi editor
    onayinin yerini tutan MAKINE denetimidir. Her kosul tek basina gondermeyi
    durdurur; neden karar.json'a ve is akisi ozetine yazilir.
    """
    nedenler = []
    if payload.get("period") != per:
        nedenler.append("tarama donemi %s, beklenen %s" % (payload.get("period"), per))
    s = payload.get("stats") or {}
    if s.get("ham", 0) < MIN_HAM:
        nedenler.append("ham sonuc cok az (%d < %d): tarama saglikli degil"
                        % (s.get("ham", 0), MIN_HAM))
    kay = max(1, s.get("kaynak", 0))
    if s.get("erisilemeyen", 0) / kay > MAX_ERISILEMEYEN_ORAN:
        nedenler.append("kaynaklarin %%%d'i erisilemedi" % round(100 * s["erisilemeyen"] / kay))
    if len(payload["rows"]) < MIN_SATIR:
        nedenler.append("yetersiz satir: %d < %d" % (len(payload["rows"]), MIN_SATIR))
    return nedenler


def cmd_otomatik(a):
    """Editor olmadan bulteni uretir ve gonderilebilir olup olmadigina karar verir.

    Girdi : out/hafta_<donem>.json (ayni is akisinda `run --commit-state` ile
            uretilmis olmali).
    Cikti : out/karar.json + (gercek) out/email.html, hafta_<donem>.html/.csv
            (deneme) out/deneme_email.html, deneme_hafta_<donem>.html
    DENEME modu hafizaya HICBIR sey yazmaz ve out/email.html'e dokunmaz:
    deneme sirasinda gorulen haberler sonraki gercek gonderimde yine
    kullanilabilir. Gercek modda da hafiza BURADA yazilmaz - yalniz posta
    gittikten sonra `isaretle` yazar.
    """
    from . import yazar
    bugun = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    per = a.period or _period(bugun)
    yol = os.path.join(OUT, "hafta_%s.json" % per)
    if not os.path.exists(yol):
        print("HATA: %s yok - once `radar run --commit-state` calismali" % yol)
        return 1
    payload = json.load(open(yol, encoding="utf-8"))
    st = state.load()

    elenen = _satir_suzgeci(payload, bugun, st)
    # BAGLANTI DOGRULAMA (2026-11-02, "ilk link hatali"): satirlar postaya
    # girmeden adresleri acilir; 404/yer tutucu/ana sayfa kanitli olanlar cikar.
    from . import baglanti
    if os.environ.get("RADAR_BAGLANTI", "1") != "0":
        payload["rows"], bg_elenen, bg_belirsiz = baglanti.dogrula(payload["rows"])
        elenen += bg_elenen
    else:
        bg_belirsiz = []
    for ad, neden in elenen:
        print("  satir cikarildi (%s): %s" % (neden, ad[:70]))
    doc = yazar.ozet_hazirla(payload)
    rapor = doc.pop("_rapor", {})
    _ozet_uygula(payload, doc)
    tech = doc.get("teknolojiler", [])
    # teknoloji koseleri de 'gonderildi'ysa cikar
    tech = [t for t in tech if ("tech:" + t.get("anahtar", "")) not in (st.get("tech_seen") or {})
            and t.get("anahtar", "") not in (st.get("tech_seen") or {})]

    nedenler = _kalite_kapisi(payload, per)
    # GONDERIM DONGUSU (DONGU_GUN, varsayilan 7 = haftalik): son gercek gonderimden
    # bu yana DONGU_GUN dolmadiysa bu hafta gonderilmez - hata degil, plan.
    # Tarama yine calisir ve havuzu besler; haber kaybolmaz, sonraki bultene kalir.
    son = _son_gonderim(st)
    atla = bool(son and (bugun - son).days < DONGU_GUN - 1)
    deneme = bool(a.deneme)
    ek = "deneme_" if deneme else ""
    base = os.path.join(OUT, "%shafta_%s" % (ek, per))
    email_yolu = os.path.join(OUT, "deneme_email.html" if deneme else "email.html")
    if nedenler and not deneme:
        # gonderilmeyecek hafta icin eski email.html'i EZME - eski bulten
        # yanlislikla yeni gibi gonderilmesin diye zaten gonderme adimi
        # karar.json'a bakar.
        email_yolu = os.path.join(OUT, "deneme_email.html")
        base = os.path.join(OUT, "deneme_hafta_%s" % per)
    _yaz(payload, doc, tech, base, email_yolu)

    karar = {"donem": per, "gonder": (not nedenler) and (not deneme) and not atla,
             "atla": atla, "son_gonderim": son.isoformat() if son else None,
             "deneme": deneme, "satir": len(payload["rows"]),
             "nedenler": nedenler, "yazar": rapor,
             "elenen_satirlar": [{"baslik": b[:90], "neden": n} for b, n in elenen],
             "baglanti_dogrulanamayan": [{"baslik": b[:90], "neden": n[:100]}
                                         for b, n in bg_belirsiz],
             "email": email_yolu, "uretildi": dt.datetime.utcnow().isoformat() + "Z",
             "basliklar": [r.get("baslik", "")[:90] for r in payload["rows"]]}
    _w(os.path.join(OUT, "karar.json"), karar)
    # isaretleme icin bu hafta KESINLESEN satirlar + teknoloji
    _w(os.path.join(OUT, "karar_satirlar.json"),
       {"donem": per, "rows": payload["rows"], "tech": tech})
    print("\notomatik %s: %d satir | yazar: %s (LLM cumle %d, kuralsal %d, reddedilen %d)"
          % (per, len(payload["rows"]), rapor.get("saglayici") or "kuralsal",
             rapor.get("cumle_llm", 0), rapor.get("cumle_kuralsal", 0),
             len(rapor.get("reddedilen_cumle", []))))
    if atla:
        print("IKI HAFTALIK DONGU: son gonderim %s, bu hafta gonderim yok (plan)." % son)
    if nedenler:
        print("GONDERILMEZ - kalite kapisi:")
        for n in nedenler:
            print("  - " + n)
    elif deneme:
        print("DENEME: kapi gecti ama gonderilmeyecek, hafiza yazilmadi.")
    elif not atla:
        print("KAPI GECTI: gonderilebilir.")
    return 0


def cmd_isaretle(a):
    """Posta GITTIKTEN sonra hafizayi yazar (karar_satirlar.json'dan)."""
    yol = os.path.join(OUT, "karar_satirlar.json")
    kyol = os.path.join(OUT, "karar.json")
    if not (os.path.exists(yol) and os.path.exists(kyol)):
        print("HATA: karar dosyalari yok")
        return 1
    karar = json.load(open(kyol, encoding="utf-8"))
    if karar.get("deneme") or not karar.get("gonder"):
        print("HATA: bu karar gonderim karari degil (deneme=%s gonder=%s) - isaretlenmedi"
              % (karar.get("deneme"), karar.get("gonder")))
        return 1
    d = json.load(open(yol, encoding="utf-8"))
    if d.get("donem") != karar.get("donem"):
        print("HATA: karar ve satir dosyasi farkli donemlerden")
        return 1
    _isaretle({"rows": d["rows"]}, d.get("tech") or [], donem=d["donem"])
    return 0


def cmd_llm_test(a):
    """Tanimli LLM saglayicilarini KISA bir istekle dener (Actions'ta)."""
    from . import llm
    sag = llm.saglayicilar()
    print("saglayicilar (oncelik sirasiyla): %s" % (", ".join(sag) or "YOK"))
    sonuc = llm.baglanti_testi()
    _w(os.path.join(OUT, "llm_test.json"), sonuc)
    return 0


def cmd_nobet(a):
    """SESSIZLIK BEKCISI: bulten uzun suredir gitmediyse uyari yazar.

    2026-09 sonu-11-02 arasi bulten 5 hafta gitmedi ve kimse fark etmedi:
    kirmizi test taramayi, olu rutin editoru durdurmustu; is akislari ya
    atlandi ya da sessiz kaldi. Bu komut gunluk is akisindan calisir; son
    gonderimden bu yana 14 gunden fazla gectiyse out/uyari.txt yazar ve
    GITHUB_OUTPUT'a uyari=true koyar (is akisi bundan posta uyarisi yollar).
    Her gun degil, Carsamba gunleri uyarir.
    """
    bugun = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    st = state.load()
    donemler = st.get("gonderilen_donemler") or []
    son = None
    for d in donemler:
        try:
            y, w = d.split("-W")
            gun = dt.date.fromisocalendar(int(y), int(w), 1)
        except Exception:
            continue
        if son is None or gun > son:
            son = gun
    gecen = (bugun - son).days if son else None
    sessiz = son is None or gecen > DONGU_GUN + 7
    print("nobet: son gonderim donemi=%s, gecen=%s gun, sessiz=%s"
          % (max(donemler) if donemler else "yok", gecen, sessiz))
    cikti = os.environ.get("GITHUB_OUTPUT")
    if sessiz and (bugun.weekday() == 2 or a.her_zaman):
        metin = ("SogukRadar uyarisi: bulten %s.\n\n"
                 "Otomatik hat (otomatik.yml) calismiyor, hata veriyor ya da kalite kapisi\n"
                 "her hafta gonderimi durduruyor olabilir. Actions sekmesinde 'SogukRadar\n"
                 "otomatik bulten' calismalarina bakin; karar.json ve is akisi ozeti\n"
                 "durdurma nedenini yazar.\n"
                 % ("hic gonderilmedi (kayit yok)" if son is None
                    else "%d gundur gonderilmedi (son: %s)" % (gecen, max(donemler))))
        with open(os.path.join(OUT, "uyari.txt"), "w", encoding="utf-8") as f:
            f.write(metin)
        if cikti:
            with open(cikti, "a", encoding="utf-8") as f:
                f.write("uyari=true\n")
        print("UYARI uretildi: out/uyari.txt")
    return 0


def cmd_dogrula(a):
    """Editorun elle_besleme.json'a yazdigi adaylari DOGRULAR.

    Ayrintili gerekce icin radar/dogrula.py bas yorumuna bakiniz.
    """
    from . import dogrula as _dg
    today = dt.date.fromisoformat(a.today) if a.today else None
    return _dg.dogrula(today=today)


def cmd_capraz(a):
    """Haftalik listenin kacirdiklarini bulur -> out/kacanlar.json.

    Editorun elle yaptigi capraz kontrolun makine karsiligi. Ayrintili
    gerekce icin radar/capraz.py bas yorumuna bakiniz.
    """
    from . import capraz as cp
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    sonuc = cp.capraz(today=today)
    _w(os.path.join(OUT, "kacanlar.json"), sonuc)
    print("\ncapraz kontrol: sitemap adayi %d -> kapiyi gecen %d -> KACAN %d"
          % (sonuc["sitemap_adayi"], sonuc["kapiyi_gecen"], sonuc["adet"]))
    for r in sonuc["kacanlar"]:
        print("  %s | %-9s | %s" % (r["tarih"], r["katman"], r["baslik"][:90]))
    # Kapiyi gecip de listeye girmeyen adaylarin NEREDE dustugu gorunmeli:
    # denetim listesinin sessizce bosalmasi, dolu olmasindan tehlikelidir.
    for r in sonuc["acildi_elendi"]:
        print("  - elendi (%s): %s" % (r["sebep"], r["baslik"][:75]))
    for r in sonuc["dogrulanamayan"]:
        print("  ? dogrulanamadi (%s): %s" % (r["sebep"], r["baslik"][:70]))
    for k, v in sonuc["kaynaklar"].items():
        if v["durum"] != "ok":
            print("  ! %s erisilemedi: %s" % (v["publisher"], v.get("hata")))
    print("-> out/kacanlar.json")
    return 0


def cmd_selftest(a):
    from .selftest import run as run_tests
    return run_tests()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="radar", description="SogukRadar v" + VERSION)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("discover").set_defaults(fn=cmd_discover)

    r = sub.add_parser("run")
    r.add_argument("--today")
    r.add_argument("--limit", action="store_true", help="TARGET_ROWS ile kirp")
    r.add_argument("--commit-state", action="store_true",
                   help="rezerv/teknoloji havuzlarini state'e isle (Actions bunu kullanir)")
    r.add_argument("--sadece-tarama", action="store_true",
                   help="gunluk tarama: havuzu besler, posta govdesine dokunmaz")
    r.set_defaults(fn=cmd_run)

    sub.add_parser("review").set_defaults(fn=cmd_review)

    f = sub.add_parser("finalize")
    f.add_argument("-s", "--summaries")
    f.add_argument("-p", "--period")
    f.set_defaults(fn=cmd_finalize)

    c = sub.add_parser("capraz")
    c.add_argument("--today")
    c.set_defaults(fn=cmd_capraz)

    # EDITORUN BULDUGUNU MAKINE DOGRULAR (2026-08-31). Zayif haftalarda
    # editor arama ile haber bulur ve veri/elle_besleme.json'a YALNIZ
    # baslik + adres yazar; bu komut Actions'ta sayfayi acar, gercek
    # basligi alir, ayni kapidan gecirir, tarihi YAPISAL olarak dogrular ve
    # havuza yazar. Editorun beyan ettigi tarih ya da kapsam kanaati rapora
    # asla giremez - katkisi ADAY GOSTERMEKTIR, karar makinenindir.
    dg = sub.add_parser("dogrula")
    dg.add_argument("--today")
    dg.set_defaults(fn=cmd_dogrula)

    o = sub.add_parser("otomatik")
    o.add_argument("--today")
    o.add_argument("-p", "--period")
    o.add_argument("--deneme", action="store_true",
                   help="hafizaya yazmaz, out/email.html'e dokunmaz, gonderim karari vermez")
    o.set_defaults(fn=cmd_otomatik)
    sub.add_parser("isaretle").set_defaults(fn=cmd_isaretle)
    sub.add_parser("llm-test").set_defaults(fn=cmd_llm_test)
    sub.add_parser("yoklama").set_defaults(fn=lambda a: (__import__("radar.yoklama", fromlist=["x"]).yokla(), 0)[1])
    nb = sub.add_parser("nobet")
    nb.add_argument("--today")
    nb.add_argument("--her-zaman", action="store_true")
    nb.set_defaults(fn=cmd_nobet)

    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
