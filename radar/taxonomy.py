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
     r"acilisi yapil|faaliyete gec|"
     r"\u6295\u4ea7|\u9996\u5377|\u70ed\u8d1f\u8377\u8bd5\u8f66|\u7ade\u5de5|\u8fd0\u884c", "Ilk urun"),
    (r"cold test|hot test|trial run|test run|commissioning phase|under test|"
     r"first tests|deneme uretim|test uretim", "Test"),
    (r"under construction|construction (of|begins|began|started|starts)|"
     r"breaks? ground|ground[- ]?breaking|foundation stone|"
     r"erection (of|begins|started)|civil works|temel at|insaatina basla|"
     r"yapimina basla", "Insaat"),
    (r"revamp|moderniz|modernis|upgrade|retrofit|rebuild|refurbish|overhaul|"
     r"life extension|yenileme|revizyon|kapasite artir|"
     r"\u6539\u9020|\u5347\u7ea7|\u5927\u4fee", "Modernizasyon"),
    (r"contract|order|awarded|awards|wins|won|secures|selects|selected|"
     r"to supply|signs|signed|letter of intent|\bloi\b|agreement to|"
     r"places order|will supply|has been chosen|sozlesme|siparis|ihale|"
     r"anlasma imzala|imzaladi|"
     r"\u5408\u540c\u7b7e\u8ba2|\u7b7e\u7ea6|\u4e2d\u6807|\u8ba2\u5355|\u91c7\u8d2d", "Sozlesme"),
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
    r"tandem cold|reversing cold mill|cold reversing mill|sendzimir|20[- ]?hi|18[- ]?hi|"
    r"double cold reduc|\bdcr mill\b|"
    # asitleme + asit
    r"pickling|pickle line|pickle plant|push[- ]pull|acid regenerat|spent pickle|pickle liquor|"
    r"spray roaster|"
    # tavlama
    r"continuous annealing|annealing line|batch annealing|bell annealing|"
    r"hood[- ]type furnace|radiant tube|jet cooling|\bcapl\b|annealing furnace|"
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
    # ---------------- CINCE ----------------
    # Dunyanin soguk hadde / kaplama hatti projelerinin buyuk kismi Cin'de
    # ve Cince kaynaklar havuzda hic okunmuyordu (2026-08-17 olcumu:
    # Mysteel 14 Agustos'ta ekipman sozlesmesi yayinladi, havuz gormedi).
    r"\u51b7\u8f67|\u9178\u6d17|\u8fde\u9000|\u8fde\u7eed\u9000\u706b|\u7f69\u5f0f\u9000\u706b|"      # soguk hadde, asitleme, surekli/kutu tavlama
    r"\u9540\u950c|\u70ed\u9540\u950c|\u7535\u9540\u950c|\u9540\u94dd\u950c|\u950c\u94dd\u9541|"      # galvaniz, elektro galvaniz, galvalume, Zn-Al-Mg
    r"\u5f69\u6d82|\u9540\u9521|\u9a6c\u53e3\u94c1|\u5e73\u6574\u673a|"                # boyama, teneke, temper
    r"\u7eb5\u526a|\u5206\u6761|\u6a2a\u5207|\u78e8\u8f8a|\u8868\u9762\u68c0\u6d4b|"          # dilme, boy kesme, merdane, yuzey muayene
    r"\u7845\u94a2|\u53d6\u5411\u7845\u94a2|\u65e0\u53d6\u5411\u7845\u94a2|\u9178\u518d\u751f|"      # silisli/elektrik celigi, ARP
    r"\u51b7\u8f67\u5382|\u51b7\u8f67\u673a\u7ec4|\u9540\u950c\u673a\u7ec4|\u5f69\u6d82\u673a\u7ec4|"   # ...tesis/hat kaliplari
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
    r"cement|food processing|battery foil|battery cell|batarya|"
    r"film line|polymer film)\b")

# ----------------------------------------------------------------------
# Sert red - YALNIZCA BASLIGA uygulanir.
# Kalıplara BAGLAM eklendi: "heavy-duty" artik ticaret vergisi sanilmiyor
# (2026-08-12'de Andritz'in asitleme hatti haberini boyle kaybetmistik).
# ----------------------------------------------------------------------
# GURULTU: bunlar hicbir katmanda haber degildir. Katman 1 (Hat) ve
# Katman 2 (Yatirim) kapilarinin IKISI de bu listeyi uygular. v4 kosusunda
# alakasiz satirlarin tamami buradan sizdi: HARD_REJECT sadece Katman 1'de
# calisiyordu, "genel yatirim" etiketi alan satir denetimi atliyordu.
_NOISE = (
    # fiyat / piyasa / ticaret - hepsi baglamli
    r"\bprices?\b|\bpricing\b|price (rise|drop|increase|hike|index)|"
    r"anti[- ]dumping|countervail|safeguard measure|import (duty|tariff|quota|ban)|"
    r"export (duty|tariff|quota|ban)|customs duty|trade case|tariff|"
    r"curbs? on|considers? curbs|import restriction|"
    # ticaret/istatistik haberi (v4 kosusu sizintilari)
    r"imports? (rise|rose|fall|fell|drop|increase|decline|surge|slip)|"
    r"exports? (rise|rose|fall|fell|drop|increase|decline|surge)|"
    r"top supplier|\bad duties\b|provisional dut|antidumping|"
    r"output (rose|fell|up|down)|production (rose|fell|up \d|down \d)|"
    r"steel demand|demand (will|to) be supported|"
    # rapor satisi / pazar arastirmasi spam'i
    r"market .{0,40}(to reach|size|share|worth|value)|project report|"
    r"\bdpr\b|cost analysis|\broi\b|\birr\b|business plan|"
    r"manufacturing plant project|feasibility report|"
    # kurumsal finans / tasfiye
    r"financial performance|liquidation|insolven|bankrupt|restructuring plan|"
    # uzun urun / enerji
    r"rail steel|rail project|solar and wind|wind power project|"
    r"power (project|plant) invest|"
    # Turkce istatistik
    r"uretimi %|uretimi artti|uretimi geriledi|ihracati artti|talep|"
    r"kapasitesi hedefini|kapasite hedefi|capacity target|"
    r"trade (defence|defense) measure|"
    r"market (report|outlook|update|share|size|research|forecast)|\bcagr\b|"
    # --- v5 (2026-08-17): W33 bulteninde sizan somut vakalar
    # "... capacity expansion to boost iron ore demand - report"
    r"[-–—]\s*report\s*$|\(report\)\s*$|iron ore demand|"
    # uretim durdurma / savas / kaza - yatirim haberi degil
    r"halts? production|production halt|suspends? production|"
    r"idles?\b|idling|curtail|temporary (plant )?shutdown|shut ?downs?\b|"
    r"strike halts|missile|drone attack|shelling|air raid|\bwar\b|"
    # kurumsal el degistirme / birlesme / tasfiye
    r"amalgamation|sale of .{0,60}business|divest|stake sale|to sell\b|"
    r"liquidation plan|abandons?\b|"
    # yorum / demec - olay degil
    r"\bsays\b|\bwarns\b|\bcalls for\b|\burges\b|"
    r"\bplans to consider\b|"
    # fiyat kotasyonu satiri ("PPGI Galvanized Coil / Turkey / Ex-Works USD/t")
    r"usd/t\b|eur/t\b|\$/t\b|ex-works|\bfob\b|\bcfr\b|\bcif\b|"
    # fuar / kongre / tanitim (Turkce)
    r"konferans|kongre|\bfuar\b|zirve|bulusma|sempozyum|"
    # --- v5 Turkce gurultu (2026-08-17 olcumu)
    r"ceyrek (geliri|kari)|geliri %|cirosu|karliligi|net kari|"
    r"kapasitesini .{0,40}hedefliyor|hedefini (surduruyor|koruyor)|"
    r"steel logistics|lojistik|"
    # Cince gurultu: fiyat, kotasyon, ihracat/ithalat, uretim istatistigi,
    # kar, finansal rapor, damping, vadeli islem, stok
    r"\u4ef7\u683c|\u8c03\u4ef7|\u62a5\u4ef7|\u51fa\u53e3|\u8fdb\u53e3|\u4ea7\u91cf|"
    r"\u5229\u6da6|\u8d22\u62a5|\u53cd\u503e\u9500|\u671f\u8d27|\u5e93\u5b58|\u9500\u91cf|"
    r"yatirim ihtiyaci|politikalar merkezi|arastirma merkezi|"
    r"iddiasini guclendir|laborator|"
    # uzun urun / boru - Turkce
    r"\bboru\b|profil celigi|insaat demiri|filmasin|nervurlu|"
    # yukari akis: ergitme tarafi hicbir katmanda yok
    r"\beaf\b|electric arc furnace|blast furnace|\bdri\b|\bhbi\b|"
    r"direct reduc|yuksek firin|ark ocagi|"
    # yesil donusum / enerji anlasmasi - hat yatirimi degil
    r"photovoltaic|solar (park|panel|power)|green (electricity|energy) (deal|"
    r"purchase|agreement)|power purchase agreement|\bppa\b|"
    r"quarterly result|annual result|earnings|revenue|net profit|ebitda|"
    r"dividend|share price|stock exchange|\bipo\b|financial results|"
    # ergitme / dokum yatirimi - duz mamul kapsamimiz disinda
    r"\bergitme\b|\bdokum\b|induction (melting|furnace)|foundry|"
    # uzun urun / boru
    r"rebar|wire rod|long product|section mill|rail mill|seamless tube|"
    r"welded pipe|pipe mill|tube mill|profile mill|"
    # kurumsal gurultu
    # ATAMA: yalniz KISI atamasi gurultudur. "Welsh contractor APPOINTED
    # for pickle line construction" gercek bir hat haberiydi ve sinirsiz
    # "appoint" kalibina takilip elenmisti (2026-08-17).
    r"appoint(s|ed|ment) .{0,25}(ceo|cfo|coo|chief|president|director|"
    r"head of|manager|board|officer)|"
    r"(ceo|cfo|coo|chief|president|director|board) .{0,25}appoint|"
    r"new ceo|new chief|resign|retire|obituary|passes away|"
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
    r"ciro|net kar|hisse|borsa|halka arz|insaat demiri|filmasin|"
    r"atandi|odul ald|fuar|kongre|is ilan|bagis"
)

# YUKARI AKIS: sicak hadde ve oncesi. Bunlar Katman 1'de (islem hatti)
# reddedilir ama Katman 2'de (genel yatirim) SERBESTTIR - "DRI-EAF ile yesil
# celik tesisi yatirimi" gecerli bir dunya yatirim haberidir.
_UPSTREAM = (
    r"blast furnace|\bdri\b|\bhbi\b|direct reduc|\beaf\b|electric arc furnace|"
    r"basic oxygen|\bbof\b|continuous cast|slab caster|\bbillet\b|\bbloom\b|"
    r"csp mill|compact strip production|hot strip mill|hot rolling mill|"
    r"sinter plant|coke oven|pellet plant|scrap yard|ladle furnace|"
    # hammadde
    r"iron ore|coking coal|"
    # Turkce yukari akis
    r"yuksek firin|ark ocagi|surekli dokum|sicak hadde|sicak haddel|"
    r"sicak sac hatti|kutuk|slab dokum|minimill|mini[- ]mill|"
    # Cince yukari akis: sicak hadde, yuksek firin, konvertor, ark ocagi,
    # surekli dokum, sinter, kok, nervurlu, filmasin, boru
    r"\u70ed\u8f67|\u70ed\u8fde\u8f67|\u9ad8\u7089|\u8f6c\u7089|\u7535\u7089|\u8fde\u94f8|"
    r"\u70e7\u7ed3|\u7126\u7089|\u87ba\u7eb9\u94a2|\u7ebf\u6750|\u94a2\u7ba1"
)

# Katman 1 kapisi: gurultu + yukari akis.
HARD_REJECT = re.compile(r"(" + _NOISE + r"|" + _UPSTREAM + r")")
UPSTREAM_RE = re.compile(r"(" + _UPSTREAM + r")")

# Yukari akis vetosunu YALNIZ bunlar kaldirir. SCOPE_STRONG kullanilamaz:
# icindeki genel "strip mill" kalibi "HOT strip mill" basligina da uyuyor
# ve vetoyu kendi kendine iptal ediyordu (2026-08-17).
SOGUK_TARAF = re.compile(
    r"(cold roll|cold mill|cold strip|cold[- ]rolled|\bpltcm\b|tandem cold|"
    r"reversing cold mill|cold reversing mill|sendzimir|pickling|pickle line|acid regenerat|"
    r"continuous annealing|annealing line|annealing furnace|batch annealing|galvaniz|galvanis|"
    r"hot[- ]dip|galvanneal|galvalume|aluzinc|tinplate|tin mill|coil coating|"
    r"colou?r coat|pre[- ]?painted|skin[- ]?pass|temper mill|slitting line|"
    r"cut[- ]to[- ]length|roll grind|roll shop|electrical steel|silicon steel|"
    r"grain[- ]oriented|\bcgl\b|\bcal\b|\bbaf\b|\bccl\b|\betl\b|\bctl\b|"
    r"soguk hadde|soguk haddel|asitleme|tavlama|teneke|dilme hatt|boy kesme)")

# Gurultu tek basina: HER IKI katmanda da uygulanir (v5).
NOISE_REJECT = re.compile(r"(" + _NOISE + r")")

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


# Urun katalogu basliklari (thyssenkrupp vakasi): fiil yok, urun kodu var.
PRODUCT_PAGE = re.compile(
    r"(\u00ae|\u2122|\b[a-z]{2,10}\s?\d{3}[- ]\d{2,3}[a-z]\d{2,3}\b|"
    r"^(electrical steel|hot[- ]dip galvani[sz]ed|cold rolled|"
    r"organic coated|precision steel|manganese|boron)[ ,].{0,40}$)")

# Basligin haber olmasi icin fiil ya da olay isareti tasimasi beklenir.
# DIKKAT: kisa Turkce kokler SINIR ile aranir. Sinirsiz yazildiginda
# "tr-ACTI-on" kelimesi "acti" (acti) sanildi ve thyssenkrupp urun katalogu
# basligi "powercore traction NGO 025-125Y420" habermis gibi listeye girdi
# (v4 kosusu, 2026-08-12).
HAS_VERB = re.compile(
    r"(order|contract|award|win\b|won\b|start|begin|commission|inaugurat|"
    r"complet|suppl|install|expand|invest|launch|develop|sign|select|"
    r"produc|modern|revamp|upgrade|plan\b|build|open\b|announce|deliver|"
    r"acquir|partner|to reach|report"
    r"|\b(?:siparis|sozlesme|ihale|aldi|verdi|basla|basladi|devreye|kurul"
    r"|yatirim|acti|actu|tamamla|uretime|imzala|gelistir|duyur|yapti"
    r"|kuracak|alacak|yapacak|acilis|hatti|tesisi|fabrika))")


# ----------------------------------------------------------------------
# v5 OLAY KAPISI (2026-08-17)
# ----------------------------------------------------------------------
# HAS_VERB pratikte hep dogru donuyordu: "produc" (production), "suppl"
# (supplier), "hatti/tesisi/fabrika" (isim!) gibi kokler her katalog
# sayfasinda geciyor. Sonuc: OEM urun kataloglari ("Flying Shear
# Cut-to-Length Lines", "Strip width measurement - EMG BREIMO") ve
# pazarlama yazilari haber sanilip listeye giriyordu.
#
# OLAY farkli calisir: basligin bir SEYIN OLDUGUNU soylemesini arar -
# siparis verildi, hat devreye alindi, sozlesme imzalandi. Isim tamlamasi
# olan katalog basligi bu kapidan gecemez.
OLAY = re.compile(
    # --- siparis / sozlesme / secim
    r"\b(orders?|ordered|awards?|awarded|wins?\b|won\b|secures?|secured|"
    r"selects?|selected|chooses|chose|has (been )?(chosen|selected)|"
    r"places? (an )?order|placed (an )?order|books? order|"
    # --- tedarik / kurulum taahhudu
    r"to (supply|build|install|modernise|modernize|upgrade|revamp|expand|"
    r"deliver|equip|provide|erect|replace|retrofit)|"
    r"supplies|supplied|delivers|delivered|installs|installed|"
    r"erects|erected|retrofits|retrofitted|"
    # --- devreye alma / ilk urun  (kullanici kurali: ILK URUN)
    r"commissions?|commissioned|inaugurates?|inaugurated|"
    r"starts? up|started up|start[- ]?up of|goes into operation|"
    r"went into operation|enters service|entered service|"
    r"starts? (work|operation|production|commercial)|"
    # "Ternium STARTS cold rolling and galvanizing LINES" - olculen 25
    # haberden cikti: cikplak "starts" + hat/tesis adi da bir olaydir.
    r"\b(starts|started)\b.{0,40}\b(line|lines|mill|plant|complex|furnace)\b|"
    r"restarts?|to restart|resumes?|reopens?|recommission|"
    r"ramps? up|ramp[- ]up of|to invest\b|"
    # Tedarikcinin duyuru basligi bazen fiilsizdir: "NEW Mino double stand
    # six-high cold reversing MILL in North America". Yeni + hat/tesis adi
    # bir olaydir; katalog sayfalari "new" demez, urun adi yazar.
    r"\bnew\b.{0,45}\b(mill|line|plant|complex|furnace)\b|"
    r"begins? (production|operation|commercial)|began (production|operation)|"
    r"first coil|first strip|hot commissioning|final acceptance|"
    r"\bfac achieved\b|provisional acceptance|"
    # --- tamamlama / modernizasyon / genisleme
    r"completes?|completed|modernis|moderniz|revamps?|revamped|"
    r"upgrades|upgraded|expands|expanded|"
    r"invests? in|invested in|signs?|signed|launches|launched|"
    r"announces?|announced|receives?|received|acquires?|acquired|"
    r"unveils?|unveiled|develops?|developed|opens?|opened|"
    r"partners with|partnership with|strengthens partnership|"
    r"has (ordered|awarded|commissioned|completed|installed|signed|started))\b"
    # --- Turkce olay kokleri
    # DIKKAT: bu grupta SADECE BASTA sinir vardir, SONDA YOKTUR. Turkce
    # eklemeli bir dildir: "ilk uretim" koku gercek baslikta "ilk URETIMI
    # yapti", "imza att" ise "imza ATTI" olarak gecer. Sona \b konuldugunda
    # kok ile ekin arasinda sinir aranir, hicbiri eslesmez ve Tosyali'nin
    # ilk uretim haberi ile Kirac Galvaniz sozlesmesi kapida kalir
    # (2026-08-17 olcumunde yakalandi).
    r"|\b(?:siparis (verdi|aldi|etti)|sozlesme imzala|ihaleyi (aldi|kazandi)|"
    r"imza att|imzalad|devreye al|devreye gir|"
    r"uretime gec|uretime basla|ilk uretim|ilk urun|ilk bobin|"
    r"hizmete gir|hizmete ac|faaliyete gec|temel att|temeli atil|"
    r"tamamlad|tamamland|kuracak|kurulacak|kuruyor|yenileyecek|yenilend|"
    r"modernize ed|siparis et|secti|secildi|"
    r"acilisini yap|yatirim yapacak|yatirimi tamamla)"
    # Cince olay kokleri (sinir gerekmez - Cince'de kelime sinirı yok)
    r"|(\u5408\u540c\u7b7e\u8ba2|\u7b7e\u7ea6|\u4e2d\u6807|\u6295\u4ea7|\u9996\u5377|\u5f00\u5de5|\u7ade\u5de5|\u6539\u9020|\u5347\u7ea7|\u8ba2\u5355|\u91c7\u8d2d|\u5f00\u5de5\u5efa\u8bbe)")

# Pazarlama / katalog / kose yazisi isaretleri: konu dogru olsa bile
# bunlar HABER DEGILDIR. Olay fiili tasisalar da elenirler.
PAZARLAMA = re.compile(
    r"(case study|success story|choosing the right|\byour\b .{0,30}\bline\b|"
    r"how to |what is |guide to |whitepaper|white paper|brochure|catalog|"
    r"product range|product portfolio|view all|learn more|read more|"
    r"our (solutions|products|portfolio|technology)|"
    r"sets? (a )?new standard|requires more than|"
    r"experience report|field report|interview|testimonial|"
    r"showcases?|to showcase|presents? (its|innovative|forward|advanced|new)|"
    r"highlights? (its|advanced|innovative)|to (display|exhibit)|"
    r"\bvizyon|\bcozumleri\b|tanitti|tanitiyor|"
    r"blog|podcast|webinar|\bfaq\b)")


# Baslik pisligi: liste sayfalarindan kopan on ek ve arkaya yapisan lede.
_BAS_ONEK = [
    # Kallanish "11 Aug Free ...", Danieli "new orders 2026, 28th July ..."
    (r"^\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+"
     r"(free|premium)\s+", ""),
    (r"^(new orders|plants startup|plant startup)\s+\d{4},\s*"
     r"\d{1,2}(st|nd|rd|th)?\s+[a-z]+\s+", ""),
    # thyssenkrupp "Daily press | 2025-01-30 ...", "Trade press | ..."
    (r"^(daily|trade)\s+press\s*[|,]\s*(\d{4}-\d{2}-\d{2})?\s*", ""),
    # "5.Japan slaps ..." gibi liste numarasi
    (r"^\d{1,2}\s*[.)]\s*(?=[A-Za-z])", ""),
]


def temiz_baslik(title):
    """Liste sayfasindan kopup gelen on ek ve lede'yi baslikdan ayiklar.

    Ayni haber bir kaynakta temiz, digerinde 'Baslik 2025-07-08 International
    technology group ANDRITZ ...' seklinde geliyordu; iki farkli metin iki
    farkli tekrar anahtari uretiyor ve haber listede IKI KEZ cikiyordu
    (2026-08-17, kullanici sikayeti).
    """
    t = (title or "").strip()
    if not t:
        return t
    for pat, rep in _BAS_ONEK:
        t = re.sub(pat, rep, t, flags=re.I).strip()
    # Arkaya yapisan lede: "... Baslik 2025-07-08 International technology..."
    m = re.search(r"^(.{25,}?)\s+\d{4}-\d{2}-\d{2}\s+\S", t)
    if m:
        t = m.group(1).strip()
    # HTML varlik artiklari: "CO#sub;2!sub;-reduced"
    t = re.sub(r"#(sub|sup);(.{0,3}?)!(sub|sup);", r"\2", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -|,;")
    return t


def haber_olayi(title):
    """Baslik bir OLAY anlatiyor mu? (Hat katmani icin sart.)

    Iki kaynak birlikte kullanilir:
      1) OLAY kalibi (siparis/devreye alma/modernizasyon/...)
      2) match_stage()'in ZATEN buldugu somut asama - EVENT_WORDS tablosu
         yillardir bu isi yapiyor, kaliplari burada tekrar yazmak yerine
         ondan faydalanilir. "Tosyali Algerie PRODUCES FIRST cold rolled
         products" basligi OLAY kalibina takilmiyordu ama match_stage zaten
         "Ilk urun" diyordu ve haber elenmisti (2026-08-17'de yakalandi).

    "Teknoloji" asamasi BILEREK disarida: o tablo "presents|showcases|
    innovation" gibi pazarlama sozcuklerini de tasiyor ve urun katalogu
    sayfalarini geri sokar. Teknoloji haberleri kendi kosesinden gelir.
    """
    t = fold(title)
    if PAZARLAMA.search(t):
        return False
    if OLAY.search(t):
        return True
    return match_stage(title) not in ("Belirsiz", "Teknoloji")


# CJK karakter araligi (Cince/Japonca). Bu dillerde kelime sinirı yoktur.
CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff]")


def is_junk_title(title):
    t = fold(title)
    # Urun katalogu sayfasi: urun kodu / tescil isareti var, olay yok.
    # DIKKAT: "fiil yoksa haber degil" kurali TEK BASINA uygulanamaz -
    # "X-ray thickness gauge and shapemeter for rolling mill" gibi gecerli
    # ekipman basliklari isim tamlamasidir, fiil tasimaz (2026-08-12).
    if PRODUCT_PAGE.search(t) and not HAS_VERB.search(t):
        return True
    if JUNK_TITLE.search(t):
        return True
    # CJK (Cince/Japonca) basliklarda BOSLUK YOKTUR: kelime sayisi olcusu
    # her Cince basligi "cok kisa" sayip eliyordu ve Cin kaynaklarindan tek
    # satir gecmiyordu (2026-08-17). Bu dillerde karakter sayisi olculur ve
    # "latin harfi yok" kurali uygulanmaz.
    if CJK.search(t):
        return len(CJK.findall(t)) < 6
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


# NIYET KALIBI - baslik gelecege / karara / mutabakata isaret ediyor mu?
#
# 2026-W34 kosusunda UC satirin UCU de "Ilk urun" rozetiyle cikti, cunku
# baslik hicbir olay sozcugu tasimayinca asama GOVDEden okunuyor ve gövdedeki
# "opens / commissioned / start-up" gibi kelimeler (cogu zaman BASKA bir
# tesisten ya da sayfa sablonundan) rozeti kuruyor:
#
#   "India's Jindal Stainless Limited to invest $94 million to ramp up
#    cold rolling capacity"            -> gercek asama: yatirim karari
#   "Hoa Binh and Pomina Steel partner on 1.2 million mt flat steel plant
#    expansion"                        -> gercek asama: mutabakat zapti
#
# Buna karsilik ayni kosudaki
#   "tk accelis announces milestone at Stuttgart steel service center"
# GERCEKTEN ilk urundur (yeni dilme hattinda ilk 500 bobin). Yani govdeyi
# toptan susturmak dogru degil - ayirt eden sey BASLIKTAKI niyet dilidir.
# Baslik "yapacak / yatirim yapacak / ortak oldu / imzaladi" diyorsa haber
# heniz uretim degildir; govde ILK URUN ya da SERI URETIM rozetini kuramaz.
NIYET = re.compile(
    r"\bto (invest|build|construct|install|supply|deliver|expand|add|"
    r"set up|establish|develop|modernis|moderniz|upgrade|start|open|launch)\b|"
    r"\bplans? to\b|\bplanning\b|\bproposes?\b|"
    r"\bwill (build|invest|supply|install|start|add|expand)\b|"
    r"\bpartners? (on|with)\b|\bteams? up\b|\bjoins? forces\b|"
    r"\bmou\b|memorandum of understanding|letter of intent|\bloi\b|"
    r"\bto be (built|installed|completed|commissioned|delivered)\b|"
    # Turkce niyet dili
    r"yatirim (yapacak|karari|plani)|kuracak|yapacak|kurulacak|"
    r"planliyor|hazirlaniyor|imzaladi|mutabakat|niyet mektubu")


def match_stage(text, exclude=()):
    """EVENT_WORDS tablosundan ilk eslesen asama.

    exclude: bu asamalar atlanir (siradaki eslesme aranir). Niyet kapisi
    icin kullanilir - bkz. NIYET.
    """
    t = fold(text)
    for pat, name in EVENT_WORDS:
        if name in exclude:
            continue
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
    # GURULTU HER IKI KATMANDA DA GECERSIZ (v5, 2026-08-17). Daha once
    # NOISE_REJECT yalnizca genel_yatirim()'da calisiyordu; "Sale of
    # thyssenkrupp's Indian electrical steel business completed" gibi
    # kurumsal el degistirme haberleri Hat katmanindan sizabiliyordu.
    if NOISE_REJECT.search(ft):
        return False, "gurultu"
    # HARD_REJECT = NOISE + UPSTREAM. NOISE yukarida ayri bakildi; UPSTREAM
    # asagida KOSULLU bakilir (guclu soguk terim vetoyu kaldirir), bu yuzden
    # burada HARD_REJECT'i toptan uygulamak yanlis olur - "cold rolling mill
    # and hot strip mill" gibi karma basliklari kesiyordu.
    if MATERIAL_BLOCK.search(blob) and not re.search(r"(steel|celik)", blob):
        return False, "baska_malzeme"
    # YUKARI AKIS VETOSU - BASLIKTA (v5.2, 2026-08-17).
    #
    # 2026-W34 bulteni "Nippon Steel, 6 Milyon Tonluk Yeni SICAK Haddeleme
    # Hattini Devreye Aldi" satiriyla bozuldu: baslikta tek bir soguk taraf
    # terimi yok ama govdesinde hadde/serit kelimeleri geciyordu ve haber
    # "Serit isleme hatti" rozetiyle Hat katmanina girdi. Kapsam ise sicak
    # hadde SONRASI.
    #
    # Once "kapsami yalniz baslik kurabilsin" denedi; o kural gercek
    # haberleri de kesti ("Marcegaglia selects Fives for digital upgrade" -
    # hangi hat oldugu ancak govdede yaziyor). Dogru kural bu:
    # govde kapsami KURABILIR, ama BASLIK yukari akis diyorsa satir Hat
    # olamaz. Baslikta guclu bir soguk taraf terimi varsa veto kalkar
    # ("cold rolling mill and hot strip mill" gibi karma basliklar icin).
    if UPSTREAM_RE.search(ft) and not SOGUK_TARAF.search(ft):
        return False, "yukari_akis"
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
    r"\binvest|new plant|new facility|capacity expansion|acquisition|"
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
    # Gurultu denetimi Katman 2'de de calisir. Bu satir yokken "genel
    # yatirim" etiketi bir muafiyet gibi davraniyordu ve ticaret/istatistik/
    # finans basliklari listeye giriyordu (v4 kosusu, 2026-08-12).
    if NOISE_REJECT.search(t):
        return False
    # Pazarlama/katalog isaretleri Katman 2'de de gecersizdir (v5).
    if PAZARLAMA.search(t):
        return False
    if MATERIAL_BLOCK.search(t) and not re.search(r"(steel|celik)", t):
        return False
    if WATCH_BLOCK.search(t) and not (WATCH_BIG.search(t) and WATCH_INVEST.search(t)):
        return False
    return bool(STEEL_CONTEXT.search(t) and WATCH_INVEST.search(t))


def watch_worthy(title):
    return genel_yatirim(title)


# Rapor/pazar arastirmasi satan siteler: Google News uzerinden geliyor,
# icerikleri haber degil reklam (v4 kosusunda openPR sizdi).
SPAM_PUBLISHER = re.compile(
    r"(openpr|prnewswire|einpresswire|globenewswire|marketwatch|"
    r"researchandmarkets|imarcgroup|marketsandmarkets|expertmarketresearch|"
    r"businesswire|abnewswire|digitaljournal|benzinga|marketreport)")
