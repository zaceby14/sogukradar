# -*- coding: utf-8 -*-
"""PIYASA GUNDEMI - soguk taraf urunlerinin piyasa haberleri (2-3 madde).

2026-11-03 kullanici: "listeden cikarilanlara baktim, aslinda elektrik celigi
ile ilgili guzel bir piyasa haberi bu. 2-3 tane piyasa haberi bolumu koysak
ama en onemlileri tercih eden bir algoritma olsa."

Ana listenin kapsami DEGISMEZ (fiyat/ticaret haberleri ana listeye girmez).
Bu ayri bir bolumdur: soguk taraf URUNU + piyasa KONUSU iceren, tarihi
beslemeden yapisal gelen basliklar. Onem puani kuralsaldir (urun, bolge,
konu, kaynak, tazelik) + okuyucu geri bildirimi; LLM varsa en onemli 3'u o
secer ve Turkce ozetler (dogrulamali).
"""
import re

from . import taxonomy

URUN = re.compile(
    r"cold[- ]rolled|\bcrc\b|cold[- ]roll|galvani[sz]ed|\bhdg\b|\bgi\b coil|coated (steel|coil|sheet)|"
    r"\bppgi\b|pre[- ]?painted|colou?r[- ]coated|tinplate|tin plate|tin mill|"
    r"electrical steel|\bcrgo\b|\bcrno\b|grain[- ]oriented|non[- ]oriented|silicon steel|"
    r"flat (steel|products|rolled)|stainless (steel )?(sheet|coil|cold)|"
    r"soguk haddelenmis|galvanizli|boyali sac|teneke|elektrik celigi|yassi celik|yassi urun")
KONU = {
    "koruma": re.compile(r"safeguard|anti[- ]?dumping|countervailing|\bquota|curbs?\b|tariff|\bduty\b|duties|"
                         r"\bcbam\b|import (restriction|measure)|trade (measure|defen)|koruma onlem|"
                         r"damping|kota|gumruk vergisi|ek vergi"),
    "fiyat": re.compile(r"\bprices?\b|\boffers?\b|price (hike|cut|increase)|fiyat"),
    "talep": re.compile(r"\bdemand\b|consumption|shortage|oversupply|\bsupply\b|talep|tuketim|arz"),
    "ticaret": re.compile(r"\bimports?\b|\bexports?\b|ithalat|ihracat|shipments?"),
    "pazar": re.compile(r"\bmarket\b|outlook|forecast|piyasa|pazar"),
}
_VETO = re.compile(
    r"\bshares?\b|\bstocks?\b(?! (of|in) )|dividend|earnings|investment narrative|simply wall|"
    r"price target|market (size|share|report|research)|cagr|forecast (to|till|by) 20\d\d|"
    r"aluminium|aluminum|copper|\bzinc price|nickel|rebar|wire rod|billet|scrap|iron ore|coking coal|"
    r"horoscope|lottery")
URUN_AGIRLIK = [(re.compile(r"electrical steel|crgo|crno|grain[- ]oriented|non[- ]oriented|silicon steel|elektrik celigi"), 4),
                (re.compile(r"galvani|hdg|coated|ppgi|pre[- ]?painted|colou?r|galvanizli|boyali"), 3),
                (re.compile(r"cold[- ]roll|crc|soguk"), 3),
                (re.compile(r"tinplate|tin |teneke"), 2)]
KONU_AGIRLIK = {"koruma": 4, "fiyat": 2, "talep": 2, "ticaret": 2, "pazar": 1}
BOLGE = [(re.compile(r"turk|turkiye|turkey"), 5), (re.compile(r"\beu\b|europe|avrupa|\bab\b"), 3),
         (re.compile(r"\bmena\b|middle east|gulf|egypt|ortadogu"), 2),
         (re.compile(r"china|india|cin|hindistan|asia"), 1)]
GORUS = re.compile(r"\bcould\b|\bmay\b|\bmight\b|saglayabilir|olabilir|bekleniyor|yorum|roportaj|interview|opinion")
IYI_KAYNAK = re.compile(r"kallanish|gmk|steelorbis|eurofer|fastmarkets|argus|metal expert|"
                        r"mysteel|steelradar|bigmint|sanayi|dunya|ekonomim|yieh")


def konu(baslik):
    f = taxonomy.fold(baslik)
    for k, rx in KONU.items():
        if rx.search(f):
            return k
    return ""


def piyasa_mi(baslik):
    """Soguk taraf urunu + piyasa konusu + veto yok."""
    if not baslik or taxonomy.is_junk_title(baslik):
        return False
    f = taxonomy.fold(baslik)
    if _VETO.search(f):
        return False
    if taxonomy.UPSTREAM_RE.search(f) and not URUN.search(f):
        return False
    return bool(URUN.search(f) and konu(baslik))


def urun(baslik):
    f = taxonomy.fold(baslik)
    for rx, _ in URUN_AGIRLIK:
        m = rx.search(f)
        if m:
            return {"electrical": "elektrik celigi", "crgo": "elektrik celigi", "crno": "elektrik celigi",
                    "grain": "elektrik celigi", "non": "elektrik celigi", "silicon": "elektrik celigi",
                    "elektrik": "elektrik celigi"}.get(m.group(0).split()[0].split("-")[0],
                                                       "kaplamali" if rx is URUN_AGIRLIK[1][0] else
                                                       "soguk hadde" if rx is URUN_AGIRLIK[2][0] else "teneke")
    return "yassi"


def puan(m, bugun, st=None):
    from . import tercih
    import datetime as dt
    f = taxonomy.fold(m.get("baslik", ""))
    p = 0.0
    for rx, w in URUN_AGIRLIK:
        if rx.search(f):
            p += w
            break
    p += KONU_AGIRLIK.get(m.get("konu") or konu(m.get("baslik", "")), 0)
    for rx, w in BOLGE:
        if rx.search(f):
            p += w
            break
    # GORUS / ROPORTAJ (2026-11-21, kurul): "Iskenderun PS: ... avantaj
    # saglayabilir" bir onlem degil yorum; Turkiye bonusuyla gercek AD
    # kararinin (Tayland teneke) onune geciyordu.
    if GORUS.search(f) or re.match(r"^[^:]{2,30}:\s", m.get("baslik", "")):
        p -= 4
    if IYI_KAYNAK.search(taxonomy.fold((m.get("kaynak") or "") + " " + (m.get("url") or ""))):
        p += 2
    try:
        # EN GUNCEL ONCE (2026-11-21, kullanici: "piyasada en guncelleri alinsin"):
        # gun basina 0.2 -> 0.7 puan; bir haftalik haber ~5 puan geride kalir.
        p -= 0.7 * max(0, (bugun - dt.date.fromisoformat(m.get("tarih", ""))).days)
    except ValueError:
        p -= 5
    if st is not None:
        p += tercih.bonus(m, "piyasa", st) / 3.0
    return round(p, 2)


_AKTOR = re.compile(r"\b(eu|ab|european union|avrupa|europe|turkey|turkiye|turk\w*|china|cin|india|hindistan|"
                    r"vietnam|korea\w*|kore|japan\w*|japonya|thailand|tayland|malaysia|malezya|indonesia|"
                    r"brazil\w*|brezilya|us|usa|abd|mexico|meksika|canada|kanada|taiwan|tayvan|egypt|misir|"
                    r"uk|britain|australia|pakistan|ukraine|russia\w*)\b")
_AKTOR_ES = {"ab": "eu", "european union": "eu", "avrupa": "eu", "europe": "eu", "turkiye": "turkey",
             "cin": "china", "hindistan": "india", "kore": "korea", "japonya": "japan", "tayland": "thailand",
             "malezya": "malaysia", "brezilya": "brazil", "abd": "us", "usa": "us", "meksika": "mexico",
             "kanada": "canada", "tayvan": "taiwan", "misir": "egypt", "britain": "uk"}


def _aktor_norm(a):
    a = re.sub(r"^(turk|korea|japan|brazil|russia)\w*$", r"\1", a)
    a = _AKTOR_ES.get(a, a)
    return "turkey" if a == "turk" else a


def aktorler(baslik):
    """Basliktaki ulke/bloklar, gecis sirasiyla (ilki: onlemi alan taraf)."""
    out = []
    for mm in _AKTOR.finditer(taxonomy.fold(baslik or "")):
        a = _aktor_norm(mm.group(1))
        if a not in out:
            out.append(a)
    return out


def ayni_piyasa_haberi(a, b):
    """Baslik benzer VE onlemi alan taraf ayni (2026-11-21, kurul: 'Vietnam accepts
    ... AD duties on Chinese and South Korean galvanized' ile 'Korea recommends
    duties on Chinese galvanized steel' ayni sayiliyordu)."""
    if not taxonomy.similar_titles(a, b):
        return False
    xa, ya = aktorler(a), aktorler(b)
    if not xa or not ya:
        return True
    # onlemi alan taraf (ilk aktor) obur basllikta hic gecmiyorsa farkli olay
    return xa[0] in ya and ya[0] in xa


def havuz_guncelle(st, taze, bugun, gun=21):
    """Kalici piyasa havuzu: gonderilmemis, pencere icinde, baslikca tekrarsiz."""
    import datetime as dt
    sinir = (bugun - dt.timedelta(days=gun)).isoformat()
    gorulen = st.get("piyasa_seen") or {}
    havuz = {}
    for m in list(st.get("piyasa_rezerv") or []) + list(taze or []):
        a = m.get("anahtar")
        if not a or a in gorulen or m.get("tarih", "") < sinir or not piyasa_mi(m.get("baslik", "")):
            continue
        if m.get("tarih", "") > bugun.isoformat():         # gelecek tarihli aday
            continue
        if taxonomy.SPAM_PUBLISHER.search(taxonomy.fold((m.get("kaynak") or "") + " " + (m.get("url") or ""))):
            continue
        if any(ayni_piyasa_haberi(m["baslik"], x["baslik"]) for x in havuz.values()):
            continue
        # GONDERILMIS PIYASA HABERININ VARYANTI (2026-11-21): ayni AB anti-damping
        # karari W45, W46, W47'de uc ayri yayindan uc kez gitti.
        if any(ayni_piyasa_haberi(m["baslik"], g.get("b", ""))
               for g in (st.get("piyasa_gonderilen") or [])):
            continue
        havuz.setdefault(a, m)
    st["piyasa_rezerv"] = sorted(havuz.values(), key=lambda m: m.get("tarih", ""), reverse=True)[:60]
    return list(st["piyasa_rezerv"])


def sirala(adaylar, bugun, st, n=10):
    for m in adaylar:
        m["konu"] = m.get("konu") or konu(m.get("baslik", ""))
        m["urun"] = m.get("urun") or urun(m.get("baslik", ""))
        m["puan"] = puan(m, bugun, st)
    return sorted(adaylar, key=lambda m: -m["puan"])[:n]
