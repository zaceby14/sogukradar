# -*- coding: utf-8 -*-
"""Kapsam ve siniflandirma sozlukleri.

KAPSAM: sicak hadde SONRASI yassi celik islem hatlari ve bunlarin teknolojisi.
KAPSAM DISI: fiyat/piyasa, finansal sonuc, ticaret davalari, uzun urun,
sivi celik oncesi (YF/DRI/EAF/sureklidokum), demir disi metaller, ilan/fuar/odul.
"""
import re

# ----------------------------------------------------------------------
# Hat tipi. SIRA ONEMLIDIR: ilk eslesen kazanir.
# Elektrik celigi en ustte, cunku "electrical steel processing line"
# haberinin icindeki tavlama/asitleme kelimeleri onu yanlis hatta dusuruyordu.
# ----------------------------------------------------------------------
LINE_MAP = [
    (r"electrical steel|silicon steel|\bcrgo\b|\bcrno\b|\bngo\b|\bgoes\b|grain[- ]oriented"
     r"|elektrik ..?eli..?i|silisli ..?elik|y..?nlendirilmi..? tane",
     "Elektrik celigi hatti"),
    (r"tandem cold mill|\bpltcm\b|\btcm\b|tandem cold rolling|continuous tandem"
     r"|tandem so..?uk", "Tandem soguk hadde (TCM)"),
    (r"reversing cold mill|\brcm\b|sendzimir|20[- ]?hi|18[- ]?hi|6[- ]?hi reversing"
     r"|reversing hadde", "Reversing soguk hadde (RCM)"),
    (r"cold roll|cold mill|cold[- ]strip|cold strip|\bdcr\b|double cold reduc"
     r"|so..?uk hadde|so..?uk haddel|so..?uk sac|so..?uk ..?ekme", "Soguk hadde"),
    (r"acid regenerat|\barp\b|pickling line regenerat|asit rejenerasyon",
     "Asit rejenerasyonu (ARP)"),
    (r"pickling|\bcpl\b|\bppl\b|push[- ]pull line|asitleme|as..?t hatt",
     "Asitleme hatti"),
    (r"continuous annealing|annealing line|\bcal\b|\bcapl\b|annealing furnace|radiant tube"
     r"|s..?rekli tavlama|tavlama hatt|tav f..?r..?n", "Surekli tavlama (CAL)"),
    (r"batch annealing|\bbaf\b|bell annealing|hood[- ]type furnace|kutu tavlama|"
     r"..?an tipi tavlama", "Kutu tavlama (BAF)"),
    (r"zn[- ]?al[- ]?mg|zinc[- ]aluminium[- ]magnesium|magnelis|zam coating|galvalume|aluzinc|"
     r"alu[- ]?zinc|55% al", "Zn-Al-Mg / Galvalume kaplama"),
    (r"electro[- ]?galvaniz|electro[- ]?galvanis|\begl\b", "Elektro galvaniz (EGL)"),
    (r"tinplate|tin mill|electrolytic tinning|\betl\b|tin[- ]free steel|\btfs\b|teneke",
     "Teneke hatti (ETL)"),
    (r"coil coating|colou?r coat|\bccl\b|pre[- ]?painted|\bppgi\b|\bppgl\b|painting line"
     r"|boyama hatt|boyal..? sac|boya hatt", "Boyama hatti (CCL)"),
    (r"galvaniz|galvanis|hot[- ]dip|\bcgl\b|\bhdg\b|galvanneal|\bga\b coating|zinc coating line"
     r"|s..?cak dald..?rma|..?inko kaplama", "Galvaniz hatti (CGL)"),
    (r"skin[- ]?pass|temper mill|temper rolling|\bdcr/temper\b|temper hatt",
     "Temper / skin pass"),
    (r"slitting|cut[- ]to[- ]length|\bctl\b|tension level|stretch level|recoiling|"
     r"service cent(er|re) line|dilme hatt|boy kesme|kesme hatt|servis merkezi",
     "Dilme / boy kesme"),
    (r"roll shop|roll grind|roll textur|\bedt\b|thermal spray.{0,20}roll|roll coating|"
     r"work roll|backup roll|merdane ta..?lama|merdane atolyesi|silindir ta..?lama",
     "Roll shop / merdane"),
    (r"surface inspection|defect detection|machine vision|automatic optical inspection|\bsis\b"
     r"|y..?zey muayene|y..?zey kontrol|kusur tespit", "Yuzey muayene (SIS)"),
    (r"digital twin|level 2|level[- ]2|\bl2\b|\bl3\b|process automation|thickness gauge|"
     r"flatness control|\bagc\b|\bafc\b|shape meter|x[- ]ray gauge|machine learning.{0,20}mill|"
     r"\bmes\b .{0,10}steel", "Otomasyon / dijital"),
    (r"strip processing|processing line|finishing line|entry section|exit section|looper|welder",
     "Serit isleme hatti"),
]

# ----------------------------------------------------------------------
# Yatirim asamasi. SIRA ONEMLIDIR.
# "begins production" / "starts up" = ILK URUN'dur, Seri uretim degildir.
# ----------------------------------------------------------------------
EVENT_WORDS = [
    (r"full capacity|ramp[- ]?up complet|commercial shipment|full production|nameplate capacity|"
     r"reaches design capacity|tam kapasite|seri ..?retim", "Seri uretim"),
    (r"first coil|produces? first|produced first|begins? production|starts? production|"
     r"start[- ]?up|starts? up|commission(s|ed|ing)\b|inaugurat|officially open|opens\b|"
     r"rolls? first|first production|goes on stream|hands? over|handover|taken over"
     r"|ilk bobin|devreye al|devreye gir|..?retime ba..?la|hizmete gir|a..?..?l..?..?..? yap",
     "Ilk urun"),
    (r"cold test|hot test|trial run|test run|commissioning phase|under test|"
     r"first tests|no[- ]load test|deneme ..?retim|test ..?retim", "Test"),
    (r"under construction|construction (of|begins|began|started|starts)|breaks? ground|"
     r"ground[- ]?breaking|foundation stone|erection (of|begins|started)|civil works|"
     r"steel structure erect|temel at|in..?aat..?na ba..?la|yap..?m..?na ba..?la", "Insaat"),
    (r"revamp|moderniz|modernis|upgrade|retrofit|rebuild|refurbish|overhaul|life extension|"
     r"capacity expansion of existing|yenileme|revizyon|kapasite art..?r", "Modernizasyon"),
    (r"contract|order|awarded|awards|wins|won|secures|selects|selected|to supply|signs|signed|"
     r"letter of intent|\bloi\b|agreement to|places order|book(s|ed) order|will supply|"
     r"has been chosen|s..?zle..?me|sipari..?|ihale|anla..?ma imzala|imzalad", "Sozlesme"),
    (r"unveils|launches|introduc|new technology|patent|licen[cs]e|develops|presents|"
     r"showcases|debut|world first|innovation|r&d|research (project|partnership)"
     r"|yeni teknoloji|geli..?tirdi|tan..?tt..?|lisans", "Teknoloji"),
]

# ----------------------------------------------------------------------
# Sert red: bu kaliplardan biri eslesirse haber KAPSAM DISI sayilir.
# (Once pozitif kapsam kapisi calisir; bu ikinci savunma hattidir.)
# ----------------------------------------------------------------------
HARD_REJECT = re.compile(
    r"("
    r"price(s|d|ing)?\b|pricing|tariff|anti[- ]dumping|countervail|safeguard|quota|"
    r"trade case|duty|duties|import|export volume|market (report|outlook|update|share)|"
    r"quarterly result|annual result|earnings|revenue|profit|loss|ebitda|dividend|"
    r"share price|stock|ipo|bond|financ(ing|ial results)|"
    r"blast furnace|\bbf\b|\bdri\b|\bhbi\b|direct reduc|\beaf\b|electric arc|"
    r"basic oxygen|\bbof\b|converter|continuous cast|caster|slab caster|billet|bloom|"
    r"sinter plant|coke oven|pellet plant|scrap yard|ladle furnace|"
    r"rebar|wire rod|long product|section mill|\bbeam\b|rail mill|seamless|welded pipe|"
    r"pipe mill|tube mill|profile mill|"
    r"iron ore|coking coal|aluminium|aluminum|copper|zinc price|nickel|stainless melt|"
    r"appoint(s|ed|ment)|new ceo|new chief|resign|retire|obituary|passes away|"
    r"award(s|ed) (to|for) (excellence|safety)|prize|medal|anniversar|celebrat|"
    r"conference|exhibition|trade fair|webinar|seminar|congress|expo\b|"
    r"job opening|vacancy|career|recruit|internship|"
    r"acquisition|acquires|merger|takeover|stake|joint venture agreement to invest|"
    r"solar|wind farm|defen[cs]e|automotive sales|car production|"
    r"decarboni[sz]ation target|net[- ]zero pledge|esg report|sustainability report|"
    # Turkce red kaliplari
    r"fiyat|ihracat|ithalat|damping|g..?mr..?k|kota|bilan..?o|ciro|kar marj|"
    r"y..?ksek f..?r..?n|ark oca..?..?|s..?rekli d..?k..?m|in..?aat demiri|"
    r"filma..?in|profil hadde|atand..?|..?d..?l ald|fuar|kongre|i..? ilan"
    r")", re.I)

# Pozitif kapsam kapisi: hicbiri eslesmezse haber alinmaz.
SCOPE_GATE = re.compile(
    r"(cold roll|cold mill|cold strip|pickl|anneal|galvaniz|galvanis|hot[- ]dip|coating line|"
    r"coil coating|colou?r coat|pre[- ]?painted|ppgi|ppgl|tinplate|tin mill|electrolytic tin|"
    r"skin[- ]?pass|temper mill|slitting|cut[- ]to[- ]length|tension level|roll shop|roll grind|"
    r"roll textur|surface inspection|strip processing|processing line|finishing line|"
    r"electrical steel|silicon steel|crgo|crno|\bngo\b|grain[- ]oriented|"
    r"acid regenerat|\bcgl\b|\bcal\b|\bbaf\b|\bcpl\b|\bppl\b|\btcm\b|\bpltcm\b|\brcm\b|"
    r"\bccl\b|\betl\b|\begl\b|\barp\b|sendzimir|20[- ]?hi|galvalume|aluzinc|zn[- ]?al[- ]?mg|"
    r"flat steel (line|plant|complex)|strip mill|sheet plant|service cent(er|re)|"
    # Turkce kapsam kapisi
    r"so..?uk hadde|so..?uk haddel|so..?uk sac|asitleme|tavlama|galvaniz|..?inko kaplama|"
    r"boyama hatt|boyal..? sac|teneke|dilme hatt|boy kesme|merdane ta..?lama|"
    r"y..?zey muayene|elektrik ..?eli..?i|silisli ..?elik|kaplama hatt|"
    r"s..?cak dald..?rma|yass..? ..?elik)", re.I)

COUNTRY_MAP = [
    (r"\bturkey|turkiye|turkish\b", "Turkiye"),
    (r"\bindia|indian\b", "Hindistan"),
    (r"\bchina|chinese\b", "Cin"),
    (r"\bjapan|japanese\b", "Japonya"),
    (r"\bkorea|korean\b", "G. Kore"),
    (r"\btaiwan", "Tayvan"),
    (r"\bvietnam", "Vietnam"),
    (r"\bindonesia", "Endonezya"),
    (r"\bmalaysia", "Malezya"),
    (r"\bthailand|thai\b", "Tayland"),
    (r"\bphilippines", "Filipinler"),
    (r"\bpakistan", "Pakistan"),
    (r"\bbangladesh", "Banglades"),
    (r"\bsaudi", "S. Arabistan"),
    (r"\buae|emirates|abu dhabi|dubai", "BAE"),
    (r"\boman\b", "Umman"),
    (r"\bqatar", "Katar"),
    (r"\begypt", "Misir"),
    (r"\bmorocco", "Fas"),
    (r"\balgeria", "Cezayir"),
    (r"\bsouth africa", "G. Afrika"),
    (r"\bnigeria", "Nijerya"),
    (r"\brussia|russian\b", "Rusya"),
    (r"\bukraine|ukrainian\b", "Ukrayna"),
    (r"\bkazakh", "Kazakistan"),
    (r"\buzbek", "Ozbekistan"),
    (r"\bpoland|polish\b", "Polonya"),
    (r"\bgermany|german\b", "Almanya"),
    (r"\bfrance|french\b", "Fransa"),
    (r"\bitaly|italian\b", "Italya"),
    (r"\bspain|spanish\b", "Ispanya"),
    (r"\bportugal", "Portekiz"),
    (r"\bbelgium|belgian\b", "Belcika"),
    (r"\bnetherlands|dutch\b", "Hollanda"),
    (r"\baustria|austrian\b", "Avusturya"),
    (r"\bsweden|swedish\b", "Isvec"),
    (r"\bfinland|finnish\b", "Finlandiya"),
    (r"\bczech", "Cekya"),
    (r"\bslovak", "Slovakya"),
    (r"\bhungar", "Macaristan"),
    (r"\bromania", "Romanya"),
    (r"\bserbia", "Sirbistan"),
    (r"\bgreece|greek\b", "Yunanistan"),
    (r"\bbritain|\buk\b|united kingdom|england|wales", "Birlesik Krallik"),
    (r"\busa\b|united states|u\.s\.|american\b", "ABD"),
    (r"\bcanada|canadian\b", "Kanada"),
    (r"\bmexico|mexican\b", "Meksika"),
    (r"\bbrazil|brazilian\b", "Brezilya"),
    (r"\bargentina", "Arjantin"),
    (r"\bchile", "Sili"),
    (r"\baustralia", "Avustralya"),
]

# Puanda agirligi olan tedarikci adlari.
SUPPLIERS = (
    "danieli", "tenova", "primetals", "sms group", "smsgroup", "john cockerill",
    "andritz", "fives", "clecim", "redex", "butech", "bliss", "herkules",
    "achenbach", "sundwig", "pomini", "i2s", "ebner", "drever", "nippon steel engineering",
    "mitsubishi", "abb", "siemens", "isra vision", "cognex", "sarralle", "loi",
    "thermprocess", "delta steel", "bronx", "herr-voss", "nordson", "chemetall",
)


def match_line(text):
    for pat, name in LINE_MAP:
        if re.search(pat, text, re.I):
            return name
    return "Belirsiz"


def match_stage(text):
    for pat, name in EVENT_WORDS:
        if re.search(pat, text, re.I):
            return name
    return "Belirsiz"


def match_country(text):
    for pat, name in COUNTRY_MAP:
        if re.search(pat, text, re.I):
            return name
    return ""


def in_scope(title, body=""):
    """(alinir_mi, sebep)

    ONEMLI: sert red YALNIZCA BASLIGA bakar. Onceki surumde govde metnine de
    bakiyordu ve bu, gecerli bir yatirim haberini govdesinde "prices" ya da
    "ihracat" gectigi icin eliyordu - 2026-W33 kosusunda 187 satirin kapsam
    disi sayilmasinin ana sebebi buydu. Haberin NE OLDUGUNU baslik soyler;
    govde sadece konuyu dogrulamak (kapsam kapisi) icin kullanilir.
    """
    if HARD_REJECT.search(title or ""):
        return False, "sert_red"
    if not SCOPE_GATE.search((title or "") + " " + (body or "")):
        return False, "kapsam_disi"
    return True, ""
