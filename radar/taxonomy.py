# -*- coding: utf-8 -*-
"""Kapsam ve siniflandirma sozlukleri.

KAPSAM: sicak hadde SONRASI yassi celik islem hatlari ve bunlarin teknolojisi.
KAPSAM DISI: fiyat/piyasa, finansal sonuc, ticaret davalari, uzun urun,
sicak hadde ve oncesi (YF/DRI/EAF/surekli dokum/CSP/sicak serit), demir disi
metaller, ilan/fuar/odul/bagis, enerji-karbon duyurulari.

TUM eslestirmeler fold() ciktisi uzerinde yapilir: metin ASCII kucuk harfe
indirgenir, kaliplar duz ASCII yazilir. Bu sayede "SOĞUK HADDELEME" ile
"soguk haddeleme" ayni sey olur ve Turkce buyuk 'İ' sorunu ortadan kalkar.
"""
import re

_TRMAP = str.maketrans({
    "İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s", "Ğ": "g", "ğ": "g",
    "Ü": "u", "ü": "u", "Ö": "o", "ö": "o", "Ç": "c", "ç": "c", "Â": "a",
    "â": "a", "É": "e", "é": "e", "È": "e", "è": "e", "Á": "a", "á": "a",
    "Ó": "o", "ó": "o", "Ú": "u", "ú": "u", "Ñ": "n", "ñ": "n", "ß": "ss",
    "ä": "a", "Ä": "a", "å": "a", "Å": "a", "ø": "o", "Ø": "o",
})


def fold(s):
    return (s or "").translate(_TRMAP).lower()


# ----------------------------------------------------------------------
# Hat tipi. SIRA ONEMLIDIR: ilk eslesen kazanir.
# Elektrik celigi en ustte, cunku "electrical steel processing line"
# haberinin icindeki tavlama/asitleme kelimeleri onu yanlis hatta dusuruyordu.
# ----------------------------------------------------------------------
LINE_MAP = [
    (r"electrical steel|silicon steel|\bcrgo\b|\bcrno\b|\bngo\b|grain[- ]oriented"
     r"|elektrik celigi|silisli celik|yonlendirilmis tane", "Elektrik celigi hatti"),
    (r"tandem cold mill|\bpltcm\b|\btcm\b|tandem cold rolling|continuous tandem"
     r"|tandem soguk", "Tandem soguk hadde (TCM)"),
    (r"reversing cold mill|\brcm\b|sendzimir|20[- ]?hi|18[- ]?hi|6[- ]?hi reversing"
     r"|reversing hadde", "Reversing soguk hadde (RCM)"),
    (r"cold roll|cold mill|cold[- ]strip|cold strip|\bdcr\b|double cold reduc"
     r"|soguk hadde|soguk haddel|soguk sac|soguk cekme", "Soguk hadde"),
    (r"acid regenerat|\barp\b|pickling line regenerat|asit rejenerasyon",
     "Asit rejenerasyonu (ARP)"),
    (r"pickling|\bcpl\b|\bppl\b|push[- ]pull line|asitleme|asit hatt", "Asitleme hatti"),
    (r"continuous annealing|annealing line|\bcal\b|\bcapl\b|annealing furnace|radiant tube"
     r"|surekli tavlama|tavlama hatt|tav firin", "Surekli tavlama (CAL)"),
    (r"batch annealing|\bbaf\b|bell annealing|hood[- ]type furnace|kutu tavlama|"
     r"can tipi tavlama", "Kutu tavlama (BAF)"),
    (r"zn[- ]?al[- ]?mg|zinc[- ]aluminium[- ]magnesium|magnelis|galvalume|aluzinc|"
     r"alu[- ]?zinc", "Zn-Al-Mg / Galvalume kaplama"),
    (r"electro[- ]?galvaniz|electro[- ]?galvanis|\begl\b", "Elektro galvaniz (EGL)"),
    (r"tinplate|tin mill|electrolytic tinning|\betl\b|tin[- ]free steel|teneke",
     "Teneke hatti (ETL)"),
    (r"coil coating|colour coat|color coat|\bccl\b|pre[- ]?painted|\bppgi\b|\bppgl\b|"
     r"painting line|boyama hatt|boyali sac|boya hatt", "Boyama hatti (CCL)"),
    (r"galvaniz|galvanis|hot[- ]dip|\bcgl\b|\bhdg\b|galvanneal|zinc coating line|"
     r"sicak daldirma|cinko kaplama", "Galvaniz hatti (CGL)"),
    (r"skin[- ]?pass|temper mill|temper rolling|temper hatt", "Temper / skin pass"),
    (r"slitting|cut[- ]to[- ]length|\bctl\b|tension level|stretch level|recoiling|"
     r"service cent(er|re) line|dilme hatt|boy kesme|kesme hatt", "Dilme / boy kesme"),
    (r"roll shop|roll grind|roll textur|\bedt\b|thermal spray.{0,20}roll|roll coating|"
     r"work roll|backup roll|merdane taslama|merdane atolye|silindir taslama",
     "Roll shop / merdane"),
    (r"surface inspection|defect detection|machine vision|automatic optical inspection|"
     r"yuzey muayene|yuzey kontrol|kusur tespit", "Yuzey muayene (SIS)"),
    (r"digital twin|level 2|level[- ]2|\bl2\b|\bl3\b|process automation|thickness gauge|"
     r"flatness control|\bagc\b|shape meter|x[- ]ray gauge|dijital ikiz|otomasyon sistem",
     "Otomasyon / dijital"),
    (r"strip processing|processing line|finishing line|serit isleme", "Serit isleme hatti"),
]

# ----------------------------------------------------------------------
# Yatirim asamasi. SIRA ONEMLIDIR.
# "begins production" / "starts up" / "ilk uretim" = ILK URUN'dur.
# ----------------------------------------------------------------------
EVENT_WORDS = [
    (r"full capacity|ramp[- ]?up complet|commercial shipment|full production|"
     r"nameplate capacity|reaches design capacity|tam kapasite|seri uretim", "Seri uretim"),
    (r"first coil|produces? first|produced first|begins? production|starts? production|"
     r"start[- ]?up|starts? up|commission(s|ed|ing)\b|inaugurat|officially open|opens\b|"
     r"rolls? first|first production|goes on stream|hands? over|handover|"
     r"launch(es|ed)? (of )?(commercial )?production|production launch|"
     r"ilk bobin|ilk uretim|ilk urun|devreye al|devreye gir|uretime basla|hizmete gir|"
     r"acilisi yapil|faaliyete gec", "Ilk urun"),
    (r"cold test|hot test|trial run|test run|commissioning phase|under test|"
     r"first tests|deneme uretim|test uretim", "Test"),
    (r"under construction|construction (of|begins|began|started|starts)|breaks? ground|"
     r"ground[- ]?breaking|foundation stone|erection (of|begins|started)|civil works|"
     r"temel at|insaatina basla|yapimina basla", "Insaat"),
    (r"revamp|moderniz|modernis|upgrade|retrofit|rebuild|refurbish|overhaul|"
     r"life extension|yenileme|revizyon|kapasite artir", "Modernizasyon"),
    (r"contract|order|awarded|awards|wins|won|secures|selects|selected|to supply|signs|"
     r"signed|letter of intent|\bloi\b|agreement to|places order|will supply|"
     r"has been chosen|sozlesme|siparis|ihale|anlasma imzala|imzaladi", "Sozlesme"),
    (r"unveils|launches|introduc|new technology|patent|licen[cs]e|develops|presents|"
     r"showcases|debut|world first|innovation|yeni teknoloji|gelistirdi|tanitti|lisans",
     "Teknoloji"),
]

# ----------------------------------------------------------------------
# Sert red - YALNIZCA BASLIGA uygulanir (bkz. in_scope aciklamasi).
# ----------------------------------------------------------------------
HARD_REJECT = re.compile(
    r"("
    r"price(s|d|ing)?\b|pricing|tariff|anti[- ]dumping|countervail|safeguard|quota|"
    r"trade case|duty|duties|\bimport(s)?\b|\bexport(s)?\b|considers? curbs|curbs on|market (report|outlook|update|share|size|research|forecast)|\bcagr\b|"
    r"quarterly result|annual result|earnings|revenue|profit|loss|ebitda|dividend|"
    r"share price|stock|ipo|bond|financial results|"
    # sicak hadde ve oncesi
    r"blast furnace|\bdri\b|\bhbi\b|direct reduc|\beaf\b|electric arc|basic oxygen|"
    r"\bbof\b|converter|continuous cast|caster|slab caster|billet|bloom|csp mill|"
    r"compact strip|hot strip mill|hot rolling mill|hot mill|sinter plant|coke oven|"
    r"pellet plant|scrap yard|ladle furnace|"
    # uzun urun / boru
    r"rebar|wire rod|long product|section mill|rail mill|seamless|welded pipe|"
    r"pipe mill|tube mill|profile mill|"
    # hammadde / demir disi
    r"iron ore|coking coal|aluminium|aluminum|copper|nickel|stainless melt|"
    # kurumsal gurultu
    r"appoint(s|ed|ment)|new ceo|new chief|resign|retire|obituary|passes away|"
    r"award(s|ed) (to|for)|prize|medal|anniversar|celebrat|volunteer|donation|"
    r"charity|sponsor|christmas|conference|exhibition|trade fair|webinar|seminar|"
    r"congress|\bexpo\b|job opening|vacancy|career|recruit|internship|"
    r"acquisition|acquires|merger|takeover|"
    # enerji / karbon duyurulari
    r"photovoltaic|solar|wind farm|hydrogen (project|plant)|decarboni|net[- ]zero|"
    r"green energy deal|green (power|electricity)|power purchase|\bppa\b|"
    r"renewable (energy|power)|yesil enerji|"
    r"esg report|sustainability report|emission(s)? (target|reduction)|"
    # Turkce
    r"fiyat|ihracat|ithalat|damping|gumruk|kota|bilanco|ciro|kar marj|"
    r"yuksek firin|ark ocagi|surekli dokum|insaat demiri|filmasin|profil hadde|"
    r"atandi|odul ald|fuar|kongre|is ilan|bagis|sponsor"
    r")")

# Pozitif kapsam kapisi: hicbiri eslesmezse haber alinmaz.
SCOPE_GATE = re.compile(
    r"(cold roll|cold mill|cold strip|pickl|anneal|galvaniz|galvanis|hot[- ]dip|"
    r"coating line|coil coating|colour coat|color coat|pre[- ]?painted|ppgi|ppgl|"
    r"tinplate|tin mill|electrolytic tin|skin[- ]?pass|temper mill|slitting|"
    r"cut[- ]to[- ]length|tension level|roll shop|roll grind|roll textur|"
    r"surface inspection|strip processing|processing line|finishing line|"
    r"electrical steel|silicon steel|crgo|crno|grain[- ]oriented|acid regenerat|"
    r"\bcgl\b|\bcal\b|\bbaf\b|\bcpl\b|\bppl\b|\btcm\b|\bpltcm\b|\brcm\b|\bccl\b|"
    r"\betl\b|\begl\b|\barp\b|sendzimir|20[- ]?hi|galvalume|aluzinc|zn[- ]?al[- ]?mg|"
    r"flat steel|strip mill|sheet plant|"
    # Turkce
    r"soguk hadde|soguk haddel|soguk sac|asitleme|tavlama|galvaniz|cinko kaplama|"
    r"boyama hatt|boyali sac|teneke|dilme hatt|boy kesme|merdane taslama|"
    r"yuzey muayene|elektrik celigi|silisli celik|kaplama hatt|sicak daldirma|"
    r"yassi celik)")

COUNTRY_MAP = [
    (r"turkey|turkiye|turkish", "Turkiye"),
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
    (r"\begypt|misir", "Misir"),
    (r"\bmorocco|fas\b", "Fas"),
    (r"\balgeria|algerie|cezayir", "Cezayir"),
    (r"south africa", "G. Afrika"),
    (r"\bnigeria", "Nijerya"),
    (r"\brussia|russian\b", "Rusya"),
    (r"\bukraine|ukrainian\b", "Ukrayna"),
    (r"\bkazakh", "Kazakistan"),
    (r"\buzbek", "Ozbekistan"),
    (r"\bpoland|polish\b", "Polonya"),
    (r"\bgermany|german\b|almanya", "Almanya"),
    (r"\bfrance|french\b|fransa", "Fransa"),
    (r"\bitaly|italian\b|italya", "Italya"),
    (r"\bspain|spanish\b|ispanya", "Ispanya"),
    (r"\bportugal", "Portekiz"),
    (r"\bbelgium|belgian\b|belcika", "Belcika"),
    (r"netherlands|dutch\b|hollanda", "Hollanda"),
    (r"\baustria|austrian\b|avusturya", "Avusturya"),
    (r"\bsweden|swedish\b|isvec", "Isvec"),
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
    (r"\bbrazil|brazilian\b|brezilya", "Brezilya"),
    (r"\bargentina", "Arjantin"),
    (r"\bchile", "Sili"),
    (r"\baustralia", "Avustralya"),
    # EN SONDA: firma adindan ulke tahmini. Ulke adi gecmiyorsa devreye girer.
    # Basta olsaydi "Tosyali Algerie" haberi Turkiye'ye yazilirdi - yatirimin
    # yeri sirketin merkezi degildir.
    (r"colakoglu|borcelik|erdemir|isdemir|yildiz demir|tezcan|assan|"
     r"tosyali|kardemir|habas|icdas", "Turkiye"),
]

SUPPLIERS = (
    "danieli", "tenova", "primetals", "sms group", "john cockerill", "andritz",
    "fives", "clecim", "redex", "butech", "bliss", "herkules", "achenbach",
    "sundwig", "pomini", "i2s", "ebner", "drever", "nippon steel engineering",
    "mitsubishi", "abb", "siemens", "isra vision", "cognex", "sarralle", "loi",
    "thermprocess", "delta steel", "bronx", "herr-voss", "nordson", "chemetall",
)

# Basligin haber olup olmadigini anlamak icin: e-posta, menu, sayi yigini vb.
JUNK_TITLE = re.compile(
    r"(@|\bhttps?://|^\s*[\d\W]+\s*$|cookie|privacy|newsletter|subscribe|"
    r"contact us|imprint|sitemap|read more|all news|follow us)")


def is_junk_title(title):
    t = fold(title)
    if JUNK_TITLE.search(t):
        return True
    if len(t.split()) < 5:          # 5 kelimeden kisa basliklar haber degil
        return True
    if not re.search(r"[a-z]{3}", t):
        return True
    return False


def match_line(text):
    t = fold(text)
    for pat, name in LINE_MAP:
        if re.search(pat, t):
            return name
    return "Belirsiz"


def match_stage(text):
    t = fold(text)
    for pat, name in EVENT_WORDS:
        if re.search(pat, t):
            return name
    return "Belirsiz"


def match_country(text):
    t = fold(text)
    for pat, name in COUNTRY_MAP:
        if re.search(pat, t):
            return name
    return ""


def in_scope(title, lead=""):
    """(alinir_mi, sebep)

    ONEMLI IKI KURAL:
    1) Sert red YALNIZCA BASLIGA bakar. Govdeye de bakinca, gecerli bir
       yatirim haberi metninde "prices" ya da "ihracat" gectigi icin
       eleniyordu - 2026-W33 kosusunda 187 satiri boyle kaybettik.
    2) Kapsam kapisi baslik + yalnizca GIRIS metnine bakar. Sayfanin
       tamamina bakinca OEM sitelerindeki menu/urun metinleri her sayfayi
       "kapsam ici" gosteriyor, bagis duyurusu roll shop haberi sayiliyordu.
    """
    if is_junk_title(title):
        return False, "haber_degil"
    ft = fold(title)
    if HARD_REJECT.search(ft):
        return False, "sert_red"
    if not SCOPE_GATE.search(ft + " " + fold(lead)):
        return False, "kapsam_disi"
    return True, ""


# ----------------------------------------------------------------------
# "Radar disi ama dikkat ceken" havuzu: cekirdek kapsama girmeyen fakat
# Turkiye baglantili somut YATIRIM haberleri. Rapora ayri bolum olarak girer,
# ana tabloyu kirletmez. (2026-W33 geri bildirimi: "SteelTurk'te bize uygun
# haber var" - bunlar fiyat/ihracat degil, yatirim eksenli olanlardir.)
# ----------------------------------------------------------------------
WATCH_TR = re.compile(
    r"(turkiye|turk\b|tosyali|erdemir|isdemir|borcelik|kardemir|kocaer|oyak|"
    r"assan|habas|icdas|colakoglu|mmk|tatmetal|yildiz demir|tezcan|kuzeyboru|"
    r"hascelik|sidemir)")
WATCH_INVEST = re.compile(
    r"(yatirim|tesis|fabrika|kapasite|acilis|temel at|satin ald|sirket kur|"
    r"uretime basla|uretimi yapti|devreye|modernizasyon|hatti kur|"
    r"invest|new plant|new facility|capacity expansion|acquisition|"
    r"establishes|founds|to build)")
WATCH_BLOCK = re.compile(
    r"(fiyat|hisse|borsa|bilanco|ciro|kar[ i]|net kar|ihracat|ithalat|damping|"
    r"gumruk|kota|price|profit|earnings|revenue|share|dividend|tariff|duty|"
    r"quota|export|import|halka arz|ipo)")


# Buyuk tutarli kuresel yatirimlar da dikkat ceker (or. "3,5 milyar dolarlik
# kapasite yatirimina onay"): para + yatirim + celik baglami.
WATCH_BIG = re.compile(r"(milyar|milyon|billion|million)")
WATCH_STEEL = re.compile(r"(celik|steel|sac\b|galvaniz|teneke)")


# Mutlak engel: pazar arastirmasi/rapor satisi basliklari hicbir kosulda
# dikkat cekenlere giremez ("Market Outlook 2026-2031... USD Billion" vakasi).
WATCH_SPAM = re.compile(
    r"(market (outlook|size|research|report|forecast)|\bcagr\b|"
    r"forecast (to|20)|research report|sample report|\bwebinar\b)")


def watch_worthy(title):
    t = fold(title)
    if WATCH_SPAM.search(t):
        return False
    if WATCH_BLOCK.search(t) and not (WATCH_BIG.search(t) and WATCH_INVEST.search(t)):
        return False
    if WATCH_TR.search(t) and WATCH_INVEST.search(t):
        return True
    return bool(WATCH_BIG.search(t) and WATCH_INVEST.search(t)
                and WATCH_STEEL.search(t))


# Google News gibi genel aramalardan gelen basliklarda celik baglami sarti:
# "cinnamon roll shop" gibi es-sesli tuzaklari eler.
STEEL_CONTEXT = re.compile(
    r"(steel|celik|hadde|\bcoil\b|\bstrip\b|galvaniz|galvanis|tinplate|teneke|"
    r"pickl|anneal|tavlama|asitleme|\bsac\b|\bmill\b|metallurg|metalurji|"
    r"\bcgl\b|\bpltcm\b|\btcm\b)")
