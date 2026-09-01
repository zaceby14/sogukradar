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


# Tire ve tire benzeri isaretler BOSLUGA cevrilir (2026-08-27).
#
# Ingilizce baslik surekli tireler: "cold-rolled", "hot-dip", "temper-mill".
# Sozluklerdeki cok kelimeli kaliplarin neredeyse tamami bosluklu yazilmisti,
# yani tireli hal HICBIRINE uymuyordu. Olcum: LINE_MAP'in 120 kalibindan
# 120'si tireli halde tutmuyordu - "Roofings ... Doubles COLD-ROLLED Capacity"
# haberi kapsam kapisini geciyor ama hat "Belirsiz" kaliyordu.
#
# Kaliplari tek tek duzeltmek yerine esleştirme katmani normallestirilir;
# "[- ]" yazan mevcut kaliplar bosluga da uydugu icin bozulmaz. Yalin tire
# tasiyan uc kalip ("cpl-tcm", "ar[- ]ge", "ex[- ]works") "[- ]" olarak guncellendi.
# DIKKAT: tarih ayristirma fold() kullanmaz (radar/dates.py), "2026-08-27"
# bicimleri etkilenmez.
_TIRE = re.compile(r"[-\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")


def fold(s):
    return _TIRE.sub(" ", (s or "").translate(_TRMAP).lower())


# ----------------------------------------------------------------------
# Hat tipi. SIRA ONEMLIDIR: ilk eslesen kazanir.
# ----------------------------------------------------------------------
LINE_MAP = [
    # Cince hat terimleri (2026-08-27): "三宝集团...无取向硅钢退火炉顺利投产"
    # kapsam kapisindan geciyor ama hat "Belirsiz" kaliyordu - LINE_MAP'te
    # Cince yoktu.
    (r"electrical steel|silicon steel|\bcrgo\b|\bcrno\b|\bngo\b|\bgoes\b|"
     r"grain[- ]oriented|elektrik celigi|silisli celik|trafo saci|"
     r"\u7845\u94a2|\u65e0\u53d6\u5411|\u53d6\u5411\u7845\u94a2",
     "Elektrik celigi hatti"),
    (r"tandem cold mill|\bpltcm\b|\bcpl[- ]tcm\b|\btcm\b|tandem cold rolling|"
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
    # TEKNOLOJI - dar tutulur (2026-08-27). Onceki surumde yalin "unveils |
    # launches | introduc | presents | debut" fiilleri vardi ve bir tesis
    # acilisini ("Roofings UNVEILS $125m Steel Mill") ya da bir ticaret
    # davasini ("Pakistan LAUNCHES AD sunset review") teknoloji sayiyordu;
    # ikisi de teknoloji kosesi havuzuna dusmustu. Pazarlama fiili TEK
    # BASINA yetmez, yaninda teknoloji nesnesi aranir.
    (r"new technology|patent|licen[cs]e|joint(ly)? develop|next[- ]generation|"
     r"\br&d\b|research (project|partnership|collaboration)|world first|"
     # Pazarlama fiili + EN COK 30 karakter icinde teknoloji nesnesi.
     # "unveils new ANNEALING technology" gecer; "Unveils $125m Steel Mill"
     # gecmez. "\bgrade": "upgrade" icindeki "grade" eslesmesin.
     r"(unveil|launch|introduc|present|showcase|debut)\w*\s+.{0,30}?"
     r"(technolog|process|solution|system|method|\bgrade|innovation)|"
     r"develop(s|ing|ment)?\b.{0,30}(technolog|process|grade|steel)|"
     r"yeni teknoloji|gelistir|lisans|is birligi.{0,30}gelistir|ar[- ]ge", "Teknoloji"),
]

# ----------------------------------------------------------------------
# KADEME A - guclu terimler: tek basina kapsam ici sayilir.
# ----------------------------------------------------------------------
SCOPE_STRONG = re.compile(
    # soguk hadde ailesi
    r"(cold roll|cold mill|cold strip|cold[- ]rolled|\bpltcm\b|\bcpl[- ]tcm\b|"
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
    r"slitting|blanking|level(l)?ing|leveler|leveller|\bshear|trimming|"
    r"\boiler\b|polishing|brushing|buffing|texturing|shot blast|scale breaker|"
    r"\bcrane|warehouse automation|packaging line|strapping|weighing|"
    r"thickness|flatness|width measurement|inspection line|"
    r"entry section|exit section|digital twin|level 2|process automation|"
    r"machine learning|\brobot|"
    r"kaynak makinesi|\bfirin|duzeltme|\bkesme|paketleme|\btartim|\bvinc|"
    r"parlatma|fircalama|temizleme|kaplama|\bolcum)")

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
    # GENEL/POTA GALVANIZ - YASSI HAT DEGILDIR (2026-08-31).
    #
    # "KEZAD galvanising facility moves closer to commissioning" satiri
    # 2026-W36'da HAT katmanina "Galvaniz hatti (CGL)" olarak girdi.
    # Denetimde cikti: haber bir GALVANIZ POTASI - 610 ton ergimis cinko,
    # 16,2 metrelik kazan, 5,5 metreye kadar YAPILAR icin cift daldirma.
    # Yani celik konstruksiyonun parca parca daldirildigi genel galvaniz
    # tesisi; serit/bobin isleyen SUREKLI galvaniz hatti degil. Soguk
    # haddehane muduru icin bu haber degildir.
    #
    # Kalip DAR: "hot-dip galvanizing LINE" (CGL) kapsam icindedir ve
    # korunmasi test edilir. Vetolanan sey pota/kazan/batch/genel galvaniz
    # ve yapi daldirmadir.
    r"galvani[sz]ing kettle|galvani[sz]ing bath|zinc kettle|"
    r"batch galvani|general galvani|galvani[sz]ing plant for (steel )?structur|"
    r"double[- ]dipping|galvani[sz]e (steel )?structur|fabricated steel galvani|"
    r"galvaniz kazan|daldirma galvaniz|sicak daldirma galvaniz tesisi|"
    # GIRISIM SERMAYESI TURU - HAT HABERI DEGILDIR (2026-09-01).
    # "Ex-SpaceX engineers open robotic steel factory in Cincinnati on $15
    # million SEED" satiri Hat katmanina girdi: "robot" zayif kapsam terimi
    # (HAT otomasyonu icin konmustu) ve "steel" baglami yetti. Oysa haber
    # bir girisimin tohum yatirimi; yassi isleme hatti yok.
    r"\bseed (round|funding|investment|capital)\b|\bpre[- ]seed\b|"
    r"(million|milyon|\bm\b|\bbn\b)\s+seed\b|seed\s+(of|round)\b|"
    r"series [a-e] (round|funding)\b|\bventure (capital|round|funding)\b|"
    r"\bstartup\b.{0,30}\b(raise[sd]?|funding|round)|tohum yatirim|"
    r"melek yatirim|girisim sermayesi|"
    # SIRKET SATIN ALMA / BIRLESME - HER IKI KATMANDA (2026-08-31).
    # Kural bastan beri "sirket satin alma rapora girmez" diyordu ama veto
    # yalniz Katman 2'deydi. Bing ayna katmani acilinca su satir HAT
    # katmanina girdi: "Triple-S Steel acquires Camden Yards Steel" -
    # govdede servis merkezi/dilme gecince kapsam kapisi acildi. Bir servis
    # merkezinin EL DEGISTIRMESI bir hat gelismesi degildir; ayni sirketin
    # yeni bir dilme hatti kurmasi haberdir, sirketi satin almasi degil.
    r"\bacquires?\b|\bacquired\b|\bacquisition\b|to acquire|"
    r"\bmerger\b|\bmerges?\b|takeover|buys? (out|stake)|satin ald|"
    r"devral|birlesme anlasmasi|"
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
    r"usd/t\b|eur/t\b|\$/t\b|ex[- ]works|\bfob\b|\bcfr\b|\bcif\b|"
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
    r"direct reduc|yuksek \bfirin|ark ocagi|"
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
    # DERNEK / ETKINLIK / KURUMSAL TOREN (2026-08-27). Rezerv havuzu bunlari
    # gorunur kildi: "EGGA-Galvanizing Europe PRESIDENCY: Benelux to Spain"
    # ve "PRE OPEN HOUSE: Celebrating Growth, Community, and the Future"
    # satirlari galvaniz/bobin terimleri tasidiklari icin listeye girmisti.
    r"open house|presidency|elected president|board of directors|"
    r"annual (meeting|general)|general assembly|celebrat|"
    r"grand opening ceremon|ribbon cutting|"
    # BORU kapsam disi. "tube" tek basina yasaklanamaz - "radiant tube"
    # gercek bir tavlama hatti bilesenidir; yalniz boru urunu kaliplari.
    r"\btubing\b|tube mill|pipe mill|\bboru hatt|boru uretim|"
    r"job opening|vacancy|internship|"
    # enerji / karbon duyurulari
    r"photovoltaic|solar (park|plant|panel)|wind farm|power purchase|\bppa\b|"
    r"green energy deal|renewable (energy|power) (deal|agreement)|"
    r"esg report|sustainability report|"
    # Turkce
    # TICARET DAVASI - Ingilizce sozluk eksikti (2026-08-27). "Pakistan
    # launches AD sunset review on cold rolled steel imports" basligi
    # "cold rolled" tasidigi icin HAT katmanina girdi; oysa ticaret davasi
    # hicbir katmana giremez.
    r"anti[- ]?dumping|\bad\b sunset|sunset review|countervailing|\bcvd\b|"
    r"safeguard (measure|duty|investigation)|trade (remedy|case|investigation)|"
    r"dumping (duty|margin|investigation)|import (duty|tariff|quota|curb)|"
    r"export (duty|tariff|quota|curb|ban)|provisional dut|definitive dut|"
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
    # QSP (Quality Strip Production) Danieli'nin INCE SLAB DOKUM + SICAK
    # HADDE hattidir; 2026-08-31'de "Ezz Flat Steel signs agreement with
    # Danieli for QSP modernization" satiri Hat katmanina girdi. Firma
    # adinda "Flat Steel" gecmesi haberi yassi ISLEM hatti yapmaz.
    r"\bqsp\b|quality strip production|thin slab|endless strip production|\besp\b|"
    # "hot rolling LINE": Nippon Steel Nagoya haberinin gectigi kalip
    # (2026-08-17). "mill" varyantlari vardi, "line" yoktu ve haber
    # yukari akis vetosuna takilmadan kapsam_disi'na dusuyordu - sonuc
    # ayniydi ama sebep yanlisti; kaplama/tavlama terimi tasiyan bir
    # sicak hadde basligi bu acikten Hat katmanina girebilirdi.
    r"hot roll(ing)? line|hot strip line|hot mill\b|"
    # HIDROJEN TABANLI DEMIR URETIMI = YUKARI AKIS (2026-08-31).
    # "Cleveland-Cliffs matches $500M federal grant for Ohio steel mill
    # without hydrogen retrofit" satiri Hat katmanina girdi; haber demir
    # uretiminin karbonsuzlastirilmasi hakkinda, bir islem hatti hakkinda
    # degil. Kalip DAR tutuldu: "hydrogen annealing" ve HNx atmosferi
    # gercek bir tavlama hatti konusudur, onlar eslesmemeli.
    r"hydrogen[- ]?(retrofit|ready|based|ironmaking|dri)|"
    r"h2[- ](retrofit|based) |green hydrogen (plant|project)|"
    # OCAK/CELIKHANE PARCALARI (2026-09-01). "furnace" zayif kapsam terimi
    # olarak tavlama firini icin konmustu; "Primetals to supply FURNACE ROOF
    # to British Steel" satiri bu yuzden Hat katmanina girdi - oysa ocak
    # catisi ARK OCAGI parcasidir, celikhanedir. Tavlama/galvaniz firini
    # kalıpları kapsam ici kalir ve testle bekcilenir.
    r"furnace roof|furnace shell|furnace transformer|arc furnace|"
    r"melting furnace|melt(ing)? shop furnace|ergitme firin|pota firin|"
    r"\belectrode\b|elektrot|tapping|ocak catisi|"
    r"sinter plant|coke oven|pellet plant|scrap yard|ladle furnace|"
    # "steelmaking" = celikhane. Baslikta soguk taraf terimi yokken bunu
    # kapsam ici saymak yanlis: "Cleveland-Cliffs Invests $1B in Steelmaking
    # Modernization" govdesi yuzunden Hat katmanina girmisti (2026-W35).
    r"steel ?making|steel shop|melt shop|melting shop|celikhane|"
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

# POTA / GENEL GALVANIZ: govdede de aranir (bkz. in_scope). Serit isleyen
# SUREKLI galvaniz hatti kapsam icidir; celik konstruksiyonun parca parca
# daldirildigi pota tesisi degildir.
POTA_GALVANIZ = re.compile(
    r"(galvani[sz]ing kettle|galvani[sz]ing bath|zinc kettle|molten zinc"
    r"[^.]{0,60}(kettle|bath)|batch galvani|general galvani|double[- ]dipping|"
    r"galvani[sz]e (steel )?structur|galvani[sz]ing (of )?(steel )?structur|"
    r"fabricated steel galvani|galvaniz kazan|daldirma galvaniz)")

COUNTRY_MAP = [
    (r"turkey|turkiye|turkish", "Turkiye"),
    # \bindia SONUNDA SINIR ISTER (2026-08-29): sinirsiz hali INDIANA'nin
    # icinde tutuyordu ve "U. S. Steel ... Gary Tin Mill" satiri Hindistan
    # olarak etiketlendi - Gary, Indiana. Ayni aile "Province" icinde
    # eslesen "vinc" hatasiyla ayni.
    # crore/lakh Hindistan'a ozgu sayi birimleridir ve baslikta ulke adi
    # gecmeyen Hint haberlerinde tek sinyal olabiliyor: 2026-08-29
    # taramasinda "Jindal Stainless investing Rs 900 crore to increase
    # cold rolling capacity" satirinin ulkesi bos kalmisti.
    (r"\bindia\b|\bindias\b|\bindian\b|\bcrore\b|\blakh\b", "Hindistan"),
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
    # 2026-08-31: W35'te Uganda'daki Roofings soguk hadde kompleksi
    # bultene girdi ama ULKESI BOS kaldi - haritada Uganda yoktu. Ulke
    # bos kalinca olay parmak izinin ulke bacagi calismiyor ve ayni
    # haberin baska cerceveli ("Museveni Unveils...") ve BASKA DILDEKI
    # varyantlari tekrar listeye giriyor. Ek kalibi "Uganda'da" ve sifat
    # hali "Ugandan" da kapsanir.
    (r"\bugand", "Uganda"),
    (r"\bkenya", "Kenya"),
    (r"\bethiopia|etiyopya", "Etiyopya"),
    (r"\btanzania", "Tanzanya"),
    (r"\bghana\b", "Gana"),
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
    # "U. S. Steel" foldlanınca "u. s. steel" oluyor - noktadan sonra
    # BOSLUK var, eski desen tutmuyordu. Indiana/Ohio gibi yassi celik
    # eyaletleri de ABD'ye baglanir.
    (r"\busa\b|united states|u\.s\.|u\. ?s\. ?steel|u\. ?s\.\b|american\b|"
     r"\bindiana\b|\bohio\b|\bpennsylvania\b|\bkentucky\b|\balabama\b", "ABD"),
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


def temiz_baslik(title, url=""):
    """Liste sayfasindan kopup gelen on ek ve lede'yi baslikdan ayiklar.

    Ayni haber bir kaynakta temiz, digerinde 'Baslik 2025-07-08 International
    technology group ANDRITZ ...' seklinde geliyordu; iki farkli metin iki
    farkli tekrar anahtari uretiyor ve haber listede IKI KEZ cikiyordu
    (2026-08-17, kullanici sikayeti).
    """
    t = (title or "").strip()
    if not t:
        return t
    # SMM/Mysteel bicimi: "[Gercek Baslik]Govde metni devam eder..."
    # Koseli parantez basligi tasir, arkasina lede yapisir. Ayiklanmazsa
    # baslik 180 karakterlik govde olur; kapsam kapisi o govdede rastgele
    # bir terime takilip haberi iceri alir (2026-W35: "Oran Province"
    # icindeki "vinc" yuzunden Cezayir entegre tesisi Hat katmanina girdi).
    m = re.match(r"^\s*\[([^\]]{15,200})\]\s*\S", t)
    if m:
        t = m.group(1).strip()
    for pat, rep in _BAS_ONEK:
        t = re.sub(pat, rep, t, flags=re.I).strip()
    # YAYINCI KUYRUGU (2026-08-31). Cok yayinci basligin sonuna kendi adini
    # ekliyor: "... stainless steel plant | Mesteel - Online News",
    # "... galvanizing line - Yieh Corp Steel News". Kuyruk rapora oldugu
    # gibi girdi (2026-W36) ve iki zarari var: okuyucuya cop gosterir, VE
    # ayni haberin iki yayindaki hali farkli tekrar anahtari uretir.
    # Kesim ihtiyatli: yalnizca AYIRICIDAN SONRAKI kisa parca ve ancak
    # geriye anlamli bir baslik kaliyorsa atilir.
    # Ayirici olarak »/•/· da kullaniliyor: Metallurgprom basligi
    # "... ZAM roll coating line » Metallurgprom" seklinde geliyor ve ayni
    # haber iki farkli baslikla havuzda IKI KEZ durdu (2026-08-31).
    m = re.search(r"^(.{25,}?)\s+[|\u2013\u2014\u00bb\u2022\u00b7-]\s+"
                  r"([^|\u2013\u2014\u00bb\u2022\u00b7]{3,45})$", t)
    if m and len(m.group(1).split()) >= 5:
        kuyruk = m.group(2).lower()
        # Iki isaretten biri yeterli: (a) kuyrukta yayincilik sozcugu,
        # (b) kuyruk KAYNAGIN ALAN ADINA benziyor. Ikincisi olmadan
        # "... ZAM roll coating line » Metallurgprom" kesilmiyordu -
        # "metallurgprom" hicbir yayincilik sozcugu tasimiyor. Alan adi
        # karsilastirmasi keyfi bir liste tutmaktan hem daha genel hem
        # daha guvenli.
        alan = re.sub(r"^https?://(www\.)?", "", (url or "").lower()).split("/")[0]
        alan_kok = re.sub(r"\.(com|org|net|co|io|info)(\.[a-z]{2})?$", "", alan)
        alan_kok = alan_kok.split(".")[-1] if alan_kok else ""
        sade = re.sub(r"[^a-z0-9]", "", kuyruk)
        if (re.search(r"(news|online|magazine|daily|press|corp|group|"
                      r"steel news|com\b|\.net|haber|gazete)", kuyruk)
                or (len(alan_kok) >= 5 and len(sade) >= 5
                    and (sade in alan_kok or alan_kok in sade))):
            t = m.group(1).strip()
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


# TEKNOLOJI KOSESI ADAY KALIBI (2026-08-27).
#
# Kose adaylari daha once match_stage(...) == "Teknoloji" ile bulunuyordu.
# 2026-08-27'de o asama kapisi DARALTILDI (tesis acilisini teknoloji sayiyordu)
# ve yan etki olarak kose havuzu kurudu: aday sayisi 0'a dustu. Kose kapisi
# ile satir asamasi AYNI SEY DEGIL - kose biraz daha genis olmali, cunku
# oradaki madde editor tarafindan elle okunup tanitiliyor.
TECH_ADAY = re.compile(
    r"new technology|technolog\w* (for|to|that)|patent|licen[cs]e|"
    r"joint(ly)? develop|next[- ]generation|\br&d\b|"
    r"research (project|partnership|collaboration)|world first|"
    r"first[- ]of[- ]its[- ]kind|pilot (line|plant|project)|demonstrat\w+ plant|"
    r"develop(s|ed|ing)\b.{0,40}(technolog|process|grade|line|steel|coating)|"
    r"(unveil|launch|introduc|present|showcase|debut)\w*\s+.{0,30}?"
    r"(technolog|process|solution|system|method|\bgrade|innovation)|"
    r"yeni teknoloji|yeni nesil|gelistir|lisans|ar[- ]ge|patent|"
    # MODERN TEKNOLOJI SOZLUGU (2026-08-31). Kose iki haftadir bostu ve
    # olcumde gorundu ki kalip su gercek basliklari hic tutmuyordu:
    #   "Danieli introduces digital twin for cold rolling mill automation"
    #   "AI-based surface inspection for galvanized strip"
    #   "SMS group I-Furnace intelligent annealing process model"
    r"digital twin|dijital ikiz|\bai[- ]based|\bai\b[- ]?(destekli|powered|driven)|"
    r"machine learning|makine ogrenmesi|machine vision|yapay gor|"
    r"digitali[sz]ation|dijitallesme|process model|proses model|"
    r"predictive (maintenance|model|control)|kestirimci|"
    r"\bsensor\b|olcum sistemi|inspection system|muayene sistemi|"
    r"automation (upgrade|package|system)|otomasyon (yenile|paket|sistem)")


# TEKNOLOJI KOSESININ KENDI KAPSAM KAPISI (2026-08-31).
#
# Kose iki haftadir bos. Sebeplerden biri arz, digeri KAPI: in_scope hat
# ISMI ariyor ("annealing line", "galvanizing line"), oysa kosenin konusu
# hattin kendisi degil PROSES TEKNOLOJISIDIR. Olculdu - su gercek kaliplar
# kapida dusuyordu:
#   "John Cockerill unveils jet vapor deposition coating technology for
#    steel strip"
#   "SMS group I-Furnace intelligent annealing process model"
#
# HABER KAPISI DEGISMEZ. Bu kapi YALNIZ koseye uygulanir; kosedeki madde
# editor tarafindan elle okunup tanitildigi icin biraz daha genis olabilir -
# ayni gerekce TECH_ADAY'in satir asamasindan ayrilmasinda da kullanildi.
# Kapsam yine YASSI CELIK VE SICAK HADDE SONRASIDIR: yukari akis ve baska
# malzeme vetolari aynen isler.
TECH_KAPSAM = re.compile(
    r"(cold roll|cold mill|cold strip|cold[- ]rolled|soguk hadde|"
    r"pickl|asitleme|anneal|tavlama|galvani|kaplama|coating|coated|"
    r"tinplate|tin mill|teneke|colou?r coat|pre[- ]?paint|boyama|"
    r"skin[- ]?pass|temper mill|slitting|dilme|cut[- ]to[- ]length|boy kesme|"
    r"roll grind|roll shop|merdane|electrical steel|silicon steel|"
    r"elektrik celigi|grain[- ]oriented|strip surface|serit yuzey|"
    # OLCUM VE YUZEY MUAYENE kapsam listesinde acikca var; kose kapisi
    # bunlari da tanimali (IMS "thickness profile measuring system with
    # integrated surcon 2D surface inspection" vakasi).
    r"thickness (gauge|profile|measur)|flatness|planarite|kalinlik olcum|"
    r"duzluk olcum|profile measuring|width (gauge|measur)|serit genislik|"
    r"surface inspect|yuzey muayene|coating weight|kaplama agirlig|"
    r"\bcgl\b|\bcal\b|\bbaf\b|\bccl\b|\betl\b|\bctl\b|\bpltcm\b|"
    r"(steel|celik) (strip|serit|coil|bobin|sheet|sac))")


# Asagi akis HATTI/PROSESI - yukari akis vetosunu yalnizca bunlar kaldirir.
# Olcum ve muayene terimleri bilerek DISARIDA: onlar her iki tarafta da var.
ASAGI_AKIS = re.compile(
    r"(cold roll|cold mill|cold strip|cold[- ]rolled|soguk hadde|"
    r"pickling|pickle line|asitleme|continuous anneal|annealing (line|furnace)|"
    r"tavlama hatt|galvani[sz]ing line|galvaniz hatt|hot[- ]dip galvani|"
    r"coil coating|colou?r coat|pre[- ]?paint|boyama hatt|tinplate|tin mill|"
    r"teneke|temper mill|skin[- ]?pass|slitting line|dilme hatt|"
    r"cut[- ]to[- ]length|boy kesme|roll grind|roll shop|"
    r"electrical steel|silicon steel|elektrik celigi|"
    r"\bcgl\b|\bcal\b|\bbaf\b|\bccl\b|\betl\b|\bctl\b|\bpltcm\b)")


def tech_kapsam(title, lead=""):
    """Kose adayi kapsam ici mi? in_scope'tan tek farki: hat ISMI sart degil.

    Yukari akis, baska malzeme ve gurultu vetolari AYNEN isler - genisleyen
    tek sey hat isminin zorunlu olmamasi.
    """
    if is_junk_title(title):
        return False
    ft = fold(title)
    blob = ft + " " + fold(lead)
    if NOISE_REJECT.search(ft) or POTA_GALVANIZ.search(blob):
        return False
    if MATERIAL_BLOCK.search(ft) and not re.search(r"(steel|celik)", ft):
        return False
    # YUKARI AKIS VETOSUNU YALNIZ ASAGI AKIS HATTI KALDIRIR (2026-08-31).
    #
    # in_scope'ta vetoyu herhangi bir "guclu terim" kaldirir; kose kapisinda
    # bu yetmiyor cunku olcum/muayene terimleri her iki tarafta da geciyor.
    # Olculdu: "Experience Report: How SDI Butler enhances quality control in
    # HOT ROLLING MILL through the implementation of surcon's 2D SURFACE
    # INSPECTION system" - "surface inspection" vetoyu kaldirdi ve sicak
    # haddehane haberi koseye girdi. Muayene sistemi her yerde var; haberi
    # kapsam ici yapan sey HANGI HATTA oldugudur.
    if UPSTREAM_RE.search(ft) and not ASAGI_AKIS.search(ft):
        return False
    return bool(TECH_KAPSAM.search(blob))


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
    # POTA/GENEL GALVANIZ VETOSU GOVDEDE DE ISLER (2026-08-31).
    #
    # "KEZAD galvanising facility moves closer to commissioning" basliginda
    # tek bir pota kelimesi yok; kanit GOVDEDE - 610 ton ergimis cinko,
    # 16,2 metrelik kazan, 5,5 metreye kadar YAPILAR icin cift daldirma.
    # Satir 2026-W36'da "Galvaniz hatti (CGL)" rozetiyle Hat katmanina
    # girdi ve denetimde yakalandi.
    #
    # Govde vetosu YALNIZCA DARALTIR, asla genisletmez - "govde kurtaramaz"
    # kuralinin tersi degil, tamamlayicisidir: govde bir haberi kapsam ici
    # YAPAMAZ ama kapsam disi oldugunu KANITLAYABILIR.
    if POTA_GALVANIZ.search(blob):
        return False, "pota_galvaniz"
    # GALVANIZ HABERI BIR HAT/SERIT ISARETI TASIMALI (2026-08-31).
    #
    # Pota kalibi govdeye baglidir ve govde her zaman ayni gelmiyor: KEZAD
    # satiri bir kosuda "kettle / double-dipping / structures" kelimeleriyle
    # elendi, ertesi kosuda AYNI haber baska bir yayinin metniyle geldi ve
    # kalip tutmadi. Kanit metne bagli oldugu surece kural kirilgan.
    #
    # Saglam ayrim su: SUREKLI galvaniz hatti haberi mutlaka serit/bobin/sac
    # ya da "hat" der - CGL, "galvanizing line", "first coil", "strip". Genel
    # galvaniz tesisi ise tesisin kendisinden bahseder ("galvanising
    # facility/plant") ve serit demez, cunku parca daldirir.
    # KURAL DAR TUTULDU: "galvaniz" kelimesi SIRKET ADININ parcasi olabilir
    # ("Kirac Galvaniz Bulgaristan'da anlasma imzaladi") ve o haber gercek
    # bir yassi is olabilir. Bu yuzden veto yalnizca TESIS kelimesiyle
    # birlikte gelen galvaniz haberine uygulanir - KEZAD'in sekli tam budur:
    # "galvanising FACILITY moves closer to commissioning", hicbir serit
    # isareti yok.
    if (re.search(r"galvani[sz]\w*\s+(facility|plant|works|hub|kettle|bath)|"
                  r"(facility|plant|hub)\s+\w{0,12}\s?galvani[sz]|"
                  r"galvaniz\w*\s+(tesis|fabrika|kazan)", blob)
            and not re.search(r"(\bline\b|\blines\b|hatt|strip|serit|coil|bobin|"
                              r"sheet|sac\b|\bcgl\b|\bcgal\b|mill|hadde|anneal|"
                              r"tavlama|pickl|asitleme|tandem|skin[- ]?pass|temper)",
                              blob)):
        return False, "galvaniz_hat_isareti_yok"
    # HARD_REJECT = NOISE + UPSTREAM. NOISE yukarida ayri bakildi; UPSTREAM
    # asagida KOSULLU bakilir (guclu soguk terim vetoyu kaldirir), bu yuzden
    # burada HARD_REJECT'i toptan uygulamak yanlis olur - "cold rolling mill
    # and hot strip mill" gibi karma basliklari kesiyordu.
    # MALZEME VETOSU BASLIKTA (2026-08-27). Onceki surum baslik+govde
    # uzerinde bakiyordu: govdede gecen TEK BIR "steel" kelimesi (OEM
    # sayfalarindaki "we serve the steel and aluminium industries" gibi
    # bir cumle) vetoyu kaldiriyordu. Rezerv havuzu bunu gorunur kildi -
    # "MINO ... for Golden ALUMINUM ... Tandem Cold Rolling Mill" ve
    # "First Coil ... at JW ALUMINIUM" satirlari boyle listeye girdi.
    # Baslik baska malzeme diyorsa govde onu kurtaramaz.
    if MATERIAL_BLOCK.search(ft) and not re.search(r"(steel|celik)", ft):
        return False, "baska_malzeme"
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
            "cockerill", "technologies",
            # GENEL IS SOZLUGU "guclu token" SAYILMAZ (2026-08-31).
            # Olcum: "India's Manaksia Steel to invest $84 million to expand
            # value-added steel capacity" satiri, GONDERILMIS olan "India's
            # Jindal Stainless Limited to invest $94 million to ramp up cold
            # rolling capacity" ile ayni haber sayilip ELENDI. Iki AYRI Hint
            # sirketi; paylastiklari tek sey "invest" ve %43 onek ortusmesi
            # idi. Bu kelimeler yatirim baslıklarinda kaliptir, ayirt edici
            # degildir - ayirt edici olan sirket adi ve hat turudur.
            # Yanlis "tekrar" elemesi GERCEK HABER kaybettirir.
            "invest", "investing", "invests", "invested", "expand",
            "expansion", "expanding", "million", "billion", "crore",
            "increase", "increasing", "facility", "facilities", "project",
            "projects", "announce", "announces", "announced", "complete",
            "completes", "completed", "yatirimi", "milyon", "milyar",
            "genisletme", "kapasitesi", "artirma"}


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
    # AYIRT EDICI ORTAK KELIME YOKSA, KALIP ORTUSMESI YETMEZ (2026-08-31).
    #
    # Eski kural bu noktada yalnizca onek oranina bakiyordu ve KALIP
    # kelimeler tek basina esigi asabiliyordu:
    #   "Nucor to invest $59 million in steel grating capacity"
    #   "India's Jindal Stainless Limited to invest $94 million to ramp up
    #    cold rolling capacity"
    # Ortak onekleri invest / million / capacity idi - ucu de kalip, hicbiri
    # ayirt edici degil. Oran tam %50 cikti ve iki AYRI sirketin haberi ayni
    # sayildi. Ayni sekilde Manaksia ile Jindal birlestirildi. Yanlis
    # "tekrar" elemesi GERCEK HABER kaybettirir ve bunu kimse gormez.
    #
    # Kural buraya konuluyor, oranin kendisine degil: guclu ortak kelime
    # VARSA (Hydnum vakasi - tek ayirt edici ad + zayif ortusme) eski
    # davranis korunur; HIC yoksa en az dort ayirt edici ortak kelime
    # aranir.
    ayirt_edici = {w for w in ta & tb if w not in _COMMON6}
    if not ayirt_edici:
        return False
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
    # "cold roll" / "soguk hadde" celik baglamidir ama listede yoktu: "Rs
    # 40,000 crore investment in cold rolling complex" basligi celik
    # baglami bulunamadigi icin Katman 2'den duşuyordu (2026-08-27).
    r"(steel|celik|hadde|cold roll|cold mill|soguk hadde|"
    r"\bcoil\b|\bstrip\b|galvaniz|galvanis|tinplate|teneke|"
    r"pickl|anneal|tavlama|asitleme|\bsac\b|\bmill\b|metallurg|metalurji|"
    r"\bcgl\b|\bpltcm\b|\btcm\b)")


# YASSI TARAF ISARETI - Katman 2'nin kapsam kapisi (2026-08-27).
# Katman 2 "dunya geneli her celik yatirimi" DEGILDIR; bu bultenin okuyucusu
# soguk haddehanede calisir. Genel bir yatirim haberinin listeye girmesi icin
# YASSI tarafa dokunmasi gerekir.
YASSI = re.compile(
    # "flats" sektor kullanimidir ("value-added flats capacities") ve
    # kalibi yokken gercek bir yassi yatirim haberi dusuyordu (2026-08-27).
    r"(flat steel|flat[- ]rolled|flat product|\bflats\b|\bhrc\b|\bcrc\b|"
    r"hot[- ]rolled coil|"
    r"cold[- ]rolled coil|steel sheet|steel strip|steel coil|\bcoil\b|\bstrip\b|"
    r"\bsheet\b|sheet mill|\bplate mill\b(?!)|"
    r"service cent(er|re)|galvaniz|galvanis|tinplate|electrical steel|silicon steel|"
    r"coating line|colou?r coat|pre[- ]?painted|cold roll|cold mill|pickling|"
    r"anneal|yassi|yassi celik|soguk hadde|\bsac\b|\brulo\b|teneke|kaplama|"
    r"\u51b7\u8f67|\u9540\u950c|\u5f69\u6d82|\u9540\u9521|\u677f\u5e26)")

# Katman 2'ye ozgu gurultu: istatistik, onay/izin, projeksiyon, hisse/ortaklik
# devri. Bunlar "yatirim" kelimesi tasidiklari icin WATCH_INVEST'i geciyor ama
# hicbiri bir HAT haberi degil (2026-W35 bulteninde besi birden sizdi).
WATCH_ISTATISTIK = re.compile(
    r"crude steel|ham celik|capacity (approval|approvals)|approvals reach|"
    r"\bmnt\b|million tonnes? (per|a) year target|"
    r"regulator (approves|clears)|fair trade|competition commission|"
    r"acquisition of .{0,20}stake|stake (in|acquisition)|hisse devri|"
    r"gerekiyor|ihtiyac duyuluyor|will need|is needed|hedefi icin|"
    r"\bforecast\b|\boutlook\b|projection|road ?map|yol haritasi")


def genel_yatirim(title, lead=""):
    """Katman 2 - YASSI celik ile ilgili genel yatirim haberleri.

    2026-W35 dersi: kapi yalnizca "celik + yatirim" ariyordu ve bulteni
    yukari akisla doldurdu - 9 Yatirim satirinin 9'u da kapsam disiydi
    (pelet tesisi, sicak haddehane, entegre tesis, ham celik istatistigi,
    lojistik hisse devri, 110 milyar dolarlik projeksiyon...). Kapsam
    vetosu artik HER IKI katmanda calisir.
    """
    t = fold(title)
    blob = t + " " + fold(lead)
    if is_junk_title(title) or WATCH_SPAM.search(t):
        return False
    if WATCH_ISTATISTIK.search(blob):
        return False
    # YUKARI AKIS VETOSU KATMAN 2'DE DE GECERLI. Onceki surumun yorumunda
    # "Katman 2'de SERBESTTIR" yaziyordu; bu, kullanicinin kapsam tanimiyla
    # (sicak hadde / YF / DRI-EAF / dokum / uzun urun HICBIR katmana giremez)
    # celisiyordu ve W35'te bulteni bozdu.
    if UPSTREAM_RE.search(blob) and not SOGUK_TARAF.search(blob):
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
    if not (STEEL_CONTEXT.search(t) and WATCH_INVEST.search(t)):
        return False
    # KAPSAM KAPISI: ya haber zaten kapsam ici, ya da en azindan YASSI tarafa
    # dokunuyor olmali. "Celik + yatirim" tek basina yetmez.
    return bool(in_scope(title, lead)[0] or YASSI.search(blob))


def watch_worthy(title):
    return genel_yatirim(title)


# Rapor/pazar arastirmasi satan siteler: Google News uzerinden geliyor,
# icerikleri haber degil reklam (v4 kosusunda openPR sizdi).
SPAM_PUBLISHER = re.compile(
    r"(openpr|prnewswire|einpresswire|globenewswire|marketwatch|"
    r"researchandmarkets|imarcgroup|marketsandmarkets|expertmarketresearch|"
    r"businesswire|abnewswire|digitaljournal|benzinga|marketreport)")
