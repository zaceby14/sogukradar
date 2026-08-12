# -*- coding: utf-8 -*-
"""Kapsam ve siniflandirma sozlukleri (v4 - genis havuz).

KAPSAM: sicak hadde SONRASI yassi CELIK islem hatlari, bu hatlarin her turlu
ekipmani (serit birlestirme kaynak makinesi, cinko potasi, hava bicagi, looper,
kenar kesme, bobin tasima, paketleme, olcum sistemleri dahil) ve teknolojisi.

UC KADEMELI KAPI - "genis ol ama yanlis haber cekme" dengesi:
  A) SCOPE_STRONG : bu sektore ozgu, tek basina yeterli terimler
  B) SCOPE_WEAK   : baska sektorlerde de gecen terimler - yaninda celik/serit/
                    bobin/hadde baglami SART
  C) MATERIAL_BLOCK: alüminyum/bakir/kagit/cam gibi baska malzeme geciyor ve
                    celik gecmiyorsa satir DUSER (kullanici karari: sadece celik)

TUM eslestirmeler fold() ciktisi uzerinde yapilir: metin ASCII kucuk harfe
indirgenir. "SOĞUK HADDELEME" ile "soguk haddeleme" ayni sey olur.
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
# ----------------------------------------------------------------------
LINE_MAP = [
    (r"electrical steel|silicon steel|\bcrgo\b|\bcrno\b|\bngo\b|\bgoes\b|"
     r"grain[- ]oriented|elektrik celigi|silisli celik|trafo saci",
     "Elektrik celigi hatti"),
    (r"tandem cold mill|\bpltcm\b|\bcpl-tcm\b|\btcm\b|tandem cold rolling|"
     r"continuous tandem|tandem soguk", "Tandem soguk hadde (TCM)"),
    (r"reversing cold mill|\brcm\b|sendzimir|20[- ]?hi|18[- ]?hi|"
     r"6[- ]?hi reversing|reversing hadde", "Reversing soguk hadde (RCM)"),
    (r"cold roll|cold mill|cold[- ]strip|cold strip|\bdcr\b|double cold reduc|"
     r"soguk hadde|soguk haddel|soguk sac|soguk cekme|haddehane",
     "Soguk hadde"),
    (r"acid regenerat|\barp\b|spent pickle|pickle liquor|spray roaster|"
     r"asit rejenerasyon|asit geri kazan", "Asit rejenerasyonu (ARP)"),
    (r"pickling|\bcpl\b|\bppl\b|push[- ]pull|turbulence pickl|asitleme|asit hatt",
     "Asitleme hatti"),
    (r"continuous annealing|annealing line|\bcal\b|\bcapl\b|annealing furnace|"
     r"radiant tube|jet cooling|surekli tavlama|tavlama hatt|tav firin",
     "Surekli tavlama (CAL)"),
    (r"batch annealing|\bbaf\b|bell annealing|hood[- ]type furnace|kutu tavlama|"
     r"can tipi tavlama", "Kutu tavlama (BAF)"),
    (r"zn[- ]?al[- ]?mg|zinc[- ]aluminium[- ]magnesium|zinc[- ]magnesium|"
     r"magnelis|galvalume|aluzinc|alu[- ]?zinc|\bzam\b coating",
     "Zn-Al-Mg / Galvalume kaplama"),
    (r"electro[- ]?galvaniz|electro[- ]?galvanis|\begl\b|elektro galvaniz",
     "Elektro galvaniz (EGL)"),
    (r"tinplate|tin mill|electrolytic tinning|\betl\b|tin[- ]free steel|\btfs\b|"
     r"\beccs\b|teneke", "Teneke hatti (ETL)"),
    (r"coil coating|colou?r coat|\bccl\b|pre[- ]?painted|\bppgi\b|\bppgl\b|"
     r"painting line|boyama hatt|boyali sac|boyali rulo|boya hatt",
     "Boyama hatti (CCL)"),
    (r"galvaniz|galvanis|hot[- ]dip|\bcgl\b|\bhdgl?\b|galvanneal|zinc pot|"
     r"zinc bath|air knife|gas wiping|zinc coating line|sicak daldirma|"
     r"cinko kaplama|cinko banyosu|hava bicagi", "Galvaniz hatti (CGL)"),
    (r"passivation|chromating|phosphating|oiling machine|\boiler\b|"
     r"pasivasyon|kromatlama|fosfatlama|yaglama", "Yuzey islem / pasivasyon"),
    (r"cleaning line|degreasing|electrolytic cleaning|alkaline cleaning|"
     r"temizleme hatt|yag alma", "Temizleme hatti (ECL)"),
    (r"skin[- ]?pass|temper mill|temper rolling|temper hatt", "Temper / skin pass"),
    (r"slitting|slitter|cut[- ]to[- ]length|\bctl\b|blanking line|laser blanking|"
     r"side trimmer|edge trim|tension level|stretch level|recoiling|rewinding|"
     r"service cent(er|re)|dilme hatt|dilme|boy kesme|kesme hatt|kenar kesme|"
     r"celik servis merkezi", "Dilme / boy kesme / SSC"),
    (r"roll shop|roll grind|roll textur|\bedt\b|thermal spray.{0,20}roll|"
     r"roll coating|work roll|backup roll|chocking|merdane taslama|"
     r"merdane atolye|silindir taslama", "Roll shop / merdane"),
    (r"surface inspection|defect detection|machine vision|"
     r"automatic optical inspection|strip inspection|yuzey muayene|"
     r"yuzey kontrol|kusur tespit", "Yuzey muayene (SIS)"),
    (r"thickness gauge|x[- ]ray gauge|isotope gauge|shapemeter|stressometer|"
     r"flatness control|\bagc\b|\bafc\b|coating weight control|width gauge|"
     r"kalinlik olcum|duzluk kontrol", "Olcum / kalite kontrol"),
    (r"flash butt weld|mash seam weld|strip weld|coil joining|stitcher|"
     r"serit kaynak|bobin birlestir|kaynak makinesi", "Serit birlestirme (kaynak)"),
    (r"coil handling|coil car|walking beam|coil transport|coil packaging|"
     r"strapping|coil weighing|bobin tasima|bobin vinci|paketleme|cemberleme|"
     r"tartim", "Bobin tasima / paketleme"),
    (r"digital twin|level 2|level[- ]2|\bl2\b|\bl3\b|process automation|"
     r"dijital ikiz|otomasyon sistem", "Otomasyon / dijital"),
    (r"strip processing|processing line|finishing line|serit isleme|sac isleme|"
     r"looper|accumulator|uncoiler|decoiler|payoff reel|tension reel",
     "Serit isleme hatti"),
]

# ----------------------------------------------------------------------
# Yatirim asamasi. SIRA ONEMLIDIR.
# ----------------------------------------------------------------------
EVENT_WORDS = [
    (r"full capacity|ramp[- ]?up complet|commercial shipment|full production|"
     r"nameplate capacity|reaches design capacity|tam kapasite|seri uretim",
     "Seri uretim"),
    (r"first coil|produces? first|produced first|begins? production|"
     r"starts? production|start[- ]?up|starts? up|commission(s|ed|ing)\b|"
     r"inaugurat|officially open|opens\b|rolls? first|first production|"
     r"goes on stream|hands? over|handover|launch(es|ed)? (of )?"
     r"(commercial )?production|production launch|ilk bobin|ilk uretim|"
     r"ilk urun|devreye al|devreye gir|uretime basla|hizmete gir|"
     r"acilisi yapil|faaliyete gec", "Ilk urun"),
    (r"cold test|hot test|trial run|test run|commissioning phase|under test|"
     r"first tests|deneme uretim|test uretim", "Test"),
    (r"under construction|construction (of|begins|began|started|starts)|"
     r"breaks? ground|ground[- ]?breaking|foundation stone|"
     r"erection (of|begins|started)|civil works|temel at|insaatina basla|"
     r"yapimina basla", "Insaat"),
    (r"revamp|moderniz|modernis|upgrade|retrofit|rebuild|refurbish|overhaul|"
     r"life extension|yenileme|revizyon|kapasite artir", "Modernizasyon"),
    (r"contract|order|awarded|awards|wins|won|secures|selects|selected|"
     r"to supply|signs|signed|letter of intent|\bloi\b|agreement to|"
     r"places order|will supply|has been chosen|sozlesme|siparis|ihale|"
     r"anlasma imzala|imzaladi", "Sozlesme"),
    (r"unveils|launches|introduc|new technology|patent|licen[cs]e|"
     r"develop(s|ing|ment)?\b|partners? with|joint(ly)? develop|"
     r"next[- ]generation|\br&d\b|research (project|partnership|collaboration)|"
     r"presents|showcases|debut|world first|innovation|yeni teknoloji|"
     r"gelistir|tanitti|lisans|is birligi.{0,30}gelistir|ar-ge", "Teknoloji"),
]

# ----------------------------------------------------------------------
# KADEME A - guclu terimler: tek basina kapsam ici sayilir.
# ----------------------------------------------------------------------
SCOPE_STRONG = re.compile(
    # soguk hadde ailesi
    r"(cold roll|cold mill|cold strip|cold[- ]rolled|\bpltcm\b|\bcpl-tcm\b|"
    r"tandem cold|reversing cold mill|sendzimir|20[- ]?hi|18[- ]?hi|"
    r"double cold reduc|\bdcr mill\b|"
    # asitleme + asit
    r"pickling|push[- ]pull|acid regenerat|spent pickle|pickle liquor|"
    r"spray roaster|"
    # tavlama
    r"continuous annealing|annealing line|batch annealing|bell annealing|"
    r"hood[- ]type furnace|radiant tube|jet cooling|\bcapl\b|"
    # galvaniz + kaplama
    r"hot[- ]dip|galvaniz|galvanis|galvanneal|zinc pot|zinc bath|air knife|"
    r"gas wiping|\bsnout\b|pot roll|zinc coating line|galvalume|aluzinc|"
    r"zn[- ]?al[- ]?mg|zinc[- ]magnesium|magnelis|electro[- ]?galvaniz|"
    # teneke
    r"tinplate|tin mill|electrolytic tinning|tin[- ]free steel|\beccs\b|"
    # boyama
    r"coil coating|colou?r coat|pre[- ]?painted|\bppgi\b|\bppgl\b|"
    r"coating line|painting line|"
    # temper / duzeltme
    r"skin[- ]?pass|temper mill|temper rolling|tension level|stretch level|"
    # SSC
    r"slitting line|slitter|cut[- ]to[- ]length|blanking line|laser blanking|"
    r"side trimmer|edge trim|recoiling line|rewinding line|"
    r"service cent(er|re) line|steel service cent|"
    # merdane
    r"roll grind|roll textur|work roll|backup roll|back[- ]up roll|"
    # olcum / kalite
    r"surface inspection|defect detection|strip inspection|thickness gauge|"
    r"x[- ]ray gauge|isotope gauge|shapemeter|stressometer|flatness control|"
    r"coating weight control|automatic gauge control|"
    # serit birlestirme
    r"flash butt weld|mash seam weld|strip weld|coil joining|"
    # bobin lojistigi
    r"coil handling|coil car|walking beam|coil transport|coil packaging|"
    r"coil weighing|coil warehouse|"
    # yuzey islem
    r"passivation line|chromating|phosphating|oiling machine|"
    r"electrolytic cleaning|alkaline cleaning|degreasing line|"
    # elektrik celigi ve urun
    r"electrical steel|silicon steel|\bcrgo\b|\bcrno\b|\bngo\b|\bgoes\b|"
    r"grain[- ]oriented|press hardened|\bahss\b|\buhss\b|"
    # kisaltmalar
    r"\bcgl\b|\bhdgl\b|\bcal\b|\bbaf\b|\bcpl\b|\bppl\b|\btcm\b|\brcm\b|"
    r"\bccl\b|\betl\b|\begl\b|\barp\b|\bctl\b|\bedt\b|\bsis\b|"
    # genel hat
    r"strip processing|processing line|finishing line|flat steel|strip mill|"
    # ---------------- TURKCE ----------------
    r"soguk hadde|soguk haddel|haddehane|soguk sac|asitleme|asit rejenerasyon|"
    r"surekli tavlama|tavlama hatt|kutu tavlama|tav firin|galvaniz hatt|"
    r"sicak daldirma|cinko kaplama|cinko banyosu|hava bicagi|galvanizli sac|"
    r"boyama hatt|boyali sac|boyali rulo|teneke|dilme hatt|boy kesme|"
    r"kesme hatt|kenar kesme|merdane taslama|merdane atolye|silindir taslama|"
    r"yuzey muayene|yuzey kontrol|elektrik celigi|silisli celik|trafo saci|"
    r"yassi celik|celik servis merkezi|temizleme hatt|yag alma|sac isleme|"
    r"rulo sac|bobin isleme|bobin tasima|bobin birlestir|serit kaynak|"
    r"kaplama hatt|temper hatt|gerdirme duzeltme|cemberleme|pasivasyon)")

# ----------------------------------------------------------------------
# KADEME B - zayif terimler: yanlarinda CELIK BAGLAMI sart.
# "kaynak makinesi" tek basina insaat/gemi haberi getirir; "strip welder"
# ya da "steel + welding machine" getirmez.
# ----------------------------------------------------------------------
SCOPE_WEAK = re.compile(
    r"(roll shop|welder|welding machine|welding line|stitcher|\blooper\b|accumulator|"
    r"uncoiler|decoiler|payoff reel|tension reel|mandrel|"
    r"cleaning line|degreasing|drying oven|annealing|furnace|"
    r"slitting|blanking|level(l)?ing|leveler|leveller|shear|trimming|"
    r"\boiler\b|polishing|brushing|buffing|texturing|shot blast|scale breaker|"
    r"crane|warehouse automation|packaging line|strapping|weighing|"
    r"thickness|flatness|width measurement|inspection line|"
    r"entry section|exit section|digital twin|level 2|process automation|"
    r"machine learning|robot|"
    r"kaynak makinesi|firin|duzeltme|kesme|paketleme|tartim|vinc|"
    r"parlatma|fircalama|temizleme|kaplama|olcum)")

STEEL_CTX = re.compile(
    r"(steel|celik|strip|serit|coil|bobin|rulo|\bmill\b|hadde|sac\b|"
    r"metallurg|metalurji|galvaniz|tinplate|teneke|slab|plate mill)")

# ----------------------------------------------------------------------
# KADEME C - malzeme bariyeri: baska malzeme var, celik yoksa DUSER.
# Kullanici karari (2026-08-12): sadece celik.
# ----------------------------------------------------------------------
MATERIAL_BLOCK = re.compile(
    # KELIME SINIRI SART: "replacement" icindeki "cement", "brasserie"
    # icindeki "brass" gibi tuzaklar 2026-08-12'de gercek haberi elemisti.
    r"\b(alumini?um|alu|copper|brass|bronze|titanium|zirconium|paper mills?|"
    r"papermaking|tissue|textile|nonwoven|glass|timber|lumber|plastics?|"
    r"cement|food processing|battery foil|film line|polymer film)\b")

# ----------------------------------------------------------------------
# Sert red - YALNIZCA BASLIGA uygulanir.
# Kalıplara BAGLAM eklendi: "heavy-duty" artik ticaret vergisi sanilmiyor
# (2026-08-12'de Andritz'in asitleme hatti haberini boyle kaybetmistik).
# ----------------------------------------------------------------------
HARD_REJECT = re.compile(
    r"("
    # fiyat / piyasa / ticaret - hepsi baglamli
    r"\bprices?\b|\bpricing\b|price (rise|drop|increase|hike|index)|"
    r"anti[- ]dumping|countervail|safeguard measure|import (duty|tariff|quota|ban)|"
    r"export (duty|tariff|quota|ban)|customs duty|trade case|tariff|"
    r"curbs? on|considers? curbs|import restriction|"
    r"trade (defence|defense) measure|"
    r"market (report|outlook|update|share|size|research|forecast)|\bcagr\b|"
    r"quarterly result|annual result|earnings|revenue|net profit|ebitda|"
    r"dividend|share price|stock exchange|\bipo\b|financial results|"
    # sicak hadde ve oncesi
    r"blast furnace|\bdri\b|\bhbi\b|direct reduc|\beaf\b|electric arc furnace|"
    r"basic oxygen|\bbof\b|continuous cast|slab caster|\bbillet\b|\bbloom\b|"
    r"csp mill|compact strip production|hot strip mill|hot rolling mill|"
    r"sinter plant|coke oven|pellet plant|scrap yard|ladle furnace|"
    # uzun urun / boru
    r"rebar|wire rod|long product|section mill|rail mill|seamless tube|"
    r"welded pipe|pipe mill|tube mill|profile mill|"
    # hammadde
    r"iron ore|coking coal|"
    # kurumsal gurultu
    r"appoint(s|ed|ment)|new ceo|new chief|resign|retire|obituary|passes away|"
    r"award(s|ed) (to|for) (excellence|safety)|prize|medal|anniversar|"
    r"volunteer|donation|charity|sponsorship|christmas|"
    r"conference|exhibition|trade fair|webinar|seminar|congress|"
    r"job opening|vacancy|internship|"
    # enerji / karbon duyurulari
    r"photovoltaic|solar (park|plant|panel)|wind farm|power purchase|\bppa\b|"
    r"green energy deal|renewable (energy|power) (deal|agreement)|"
    r"esg report|sustainability report|"
    # Turkce
    r"fiyat|ihracat kisit|ithalat kisit|damping|gumruk vergisi|kota|bilanco|"
    r"ciro|net kar|hisse|borsa|halka arz|yuksek firin|ark ocagi|"
    r"surekli dokum|insaat demiri|filmasin|atandi|odul ald|fuar|kongre|"
    r"is ilan|bagis"
    r")")

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
    # EN SONDA: firma adindan ulke tahmini (yatirimin yeri sirketin merkezi
    # olmayabilir, o yuzden ulke adi hep once denenir)
    (r"colakoglu|borcelik|erdemir|isdemir|yildiz demir|tezcan|assan|"
     r"tosyali|kardemir|habas|icdas|kocaer", "Turkiye"),
]

SUPPLIERS = (
    "danieli", "tenova", "primetals", "sms group", "john cockerill", "andritz",
    "fives", "clecim", "redex", "butech", "bliss", "herkules", "achenbach",
    "sundwig", "pomini", "i2s", "ebner", "drever", "nippon steel engineering",
    "mitsubishi", "abb", "siemens", "isra vision", "cognex", "sarralle", "loi",
    "thermprocess", "delta steel", "bronx", "herr-voss", "nordson", "chemetall",
    "arku", "bradbury", "schuler", "salico", "kocks", "mino", "seco/warwick",
    "otto junker", "tmeic", "braner", "waterbury",
)

JUNK_TITLE = re.compile(
    r"(@|\bhttps?://|^\s*[\d\W]+\s*$|cookie|privacy|newsletter|subscribe|"
    r"contact us|imprint|sitemap|read more|all news|follow us|copyright|"
    r"all rights reserved|legal disclaimer|terms of use|working at|"
    r"career|employer|company information|annual report \d{4} published)")


def is_junk_title(title):
    t = fold(title)
    if JUNK_TITLE.search(t):
        return True
    if len(t.split()) < 4:   # Turkce basliklar kisa olabilir
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
    """(alinir_mi, sebep) - uc kademeli kapi.

    1) Cop baslik (menu, copyright, kariyer) -> haber degil
    2) Sert red (fiyat/ticaret/sicak hadde/kurumsal gurultu) -> baslikta arar
    3) Malzeme bariyeri: alüminyum/bakir vb var, celik yok -> duser
    4) Guclu terim varsa -> kapsam ici
    5) Zayif terim + celik baglami varsa -> kapsam ici
    """
    if is_junk_title(title):
        return False, "haber_degil"
    ft = fold(title)
    blob = ft + " " + fold(lead)
    if HARD_REJECT.search(ft):
        return False, "sert_red"
    if MATERIAL_BLOCK.search(blob) and not re.search(r"(steel|celik)", blob):
        return False, "baska_malzeme"
    if SCOPE_STRONG.search(blob):
        return True, ""
    if SCOPE_WEAK.search(blob) and STEEL_CTX.search(blob):
        return True, ""
    return False, "kapsam_disi"


# ----------------------------------------------------------------------
# Baslik benzerligi (ayni haberin farkli dildeki/kaynaktaki varyanti)
# ----------------------------------------------------------------------
_WATCH_STOP = {"ve", "ile", "icin", "bir", "the", "and", "for", "with", "its",
               "yeni", "new", "steel", "celik", "milyon", "milyar", "million",
               "billion", "euro", "dolar", "usd", "ton", "mt"}
_COMMON6 = {"turkiye", "almanya", "hindistan", "yatirim", "kapasite", "tesisi",
            "tesisine", "uretim", "uretimi", "investment", "capacity",
            "production", "galvaniz", "tinplate", "annealing", "pickling",
            "rolling", "modern", "primetals", "danieli", "andritz", "tenova",
            "cockerill", "technologies"}


def title_tokens(title):
    return {w for w in fold(title).replace("'", " ").split()
            if len(w) > 3 and w not in _WATCH_STOP}


def similar_titles(a, b, esik=0.5):
    """Ayni haberin varyanti mi? Tedarikci adlari (primetals, danieli...)
    _COMMON6'ya alindi: iki BAGIMSIZ Primetals haberi sirf adi geciyor diye
    ayni sayilmasin (2026-08-12 dersi)."""
    ta, tb = title_tokens(a), title_tokens(b)
    if not ta or not tb:
        return False
    guclu = [w for w in ta & tb if len(w) >= 6 and w not in _COMMON6]
    pa = {w[:5] for w in ta}
    pb = {w[:5] for w in tb}
    ortak = len(pa & pb)
    oran = ortak / min(len(pa), len(pb))
    if len(guclu) >= 2:
        return True
    if len(guclu) == 1 and oran >= 0.25:
        return True
    return ortak >= 4 or oran >= esik


WATCH_SPAM = re.compile(
    r"(market (outlook|size|research|report|forecast)|\bcagr\b|"
    r"forecast (to|20)|research report|sample report|\bwebinar\b)")
WATCH_INVEST = re.compile(
    r"(yatirim|tesis|fabrika|kapasite|acilis|temel at|satin ald|sirket kur|"
    r"uretime basla|uretimi yapti|devreye|modernizasyon|hatti kur|"
    r"invest|new plant|new facility|capacity expansion|acquisition|"
    r"establishes|founds|to build|expansion|joint venture)")
WATCH_BLOCK = re.compile(
    r"(fiyat|hisse|borsa|bilanco|ciro|net kar|ihracat|ithalat|damping|"
    r"gumruk|kota|price|profit|earnings|revenue|share|dividend|tariff|"
    r"duty|quota|halka arz|ipo)")
WATCH_BIG = re.compile(r"(milyar|milyon|billion|million)")

STEEL_CONTEXT = re.compile(
    r"(steel|celik|hadde|\bcoil\b|\bstrip\b|galvaniz|galvanis|tinplate|teneke|"
    r"pickl|anneal|tavlama|asitleme|\bsac\b|\bmill\b|metallurg|metalurji|"
    r"\bcgl\b|\bpltcm\b|\btcm\b)")


def genel_yatirim(title):
    """Katman 2 - dunya geneli celik yatirim haberleri."""
    t = fold(title)
    if is_junk_title(title) or WATCH_SPAM.search(t):
        return False
    if MATERIAL_BLOCK.search(t) and not re.search(r"(steel|celik)", t):
        return False
    if WATCH_BLOCK.search(t) and not (WATCH_BIG.search(t) and WATCH_INVEST.search(t)):
        return False
    return bool(STEEL_CONTEXT.search(t) and WATCH_INVEST.search(t))


def watch_worthy(title):
    return genel_yatirim(title)
