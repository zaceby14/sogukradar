# SogukRadar — Haftalık Editör Kuralları

> Haftalık koşuya başlamadan **önce bu dosya okunur.** Routine prompt'un
> kendisi değişmez; kurallar burada durur ve burada güncellenir.

Bülten: **"Soğuk Haddehane ve Nihai Hatlarda Sektör & Teknoloji Takibi"**.
Alıcı, soğuk haddehane tarafında çalışan bir yönetici. Ona yalnızca kendi
hattını ilgilendiren, tarihi doğrulanmış gelişme gider.

---

## 1. Kapsam

**İÇERİDE** — sıcak hadde **sonrası** yassı çelik işlem hatları: asitleme,
soğuk hadde (tandem/reversing), temper/skin-pass, sürekli ve kutu tavlama,
galvaniz/kaplama (CGL, EGL, Zn-Al-Mg), boyama (CCL), teneke (ETL), dilme /
boy kesme / servis merkezi, merdane atölyesi, şerit birleştirme, bobin
taşıma-paketleme, yüzey muayene, ölçüm, hat otomasyonu, elektrik çeliği.

**DIŞARIDA** — sıcak hadde, yüksek fırın, DRI/EAF, döküm, uzun ürün, boru,
demir dışı metaller. Bunlar **hiçbir katmana** giremez; "Yatırım" katmanı
bunlar için muafiyet değildir.

**KATMAN 2 (Yatırım) = yassı çelikle ilgili genel yatırım haberi.** "Dünya
geneli her çelik yatırımı" DEĞİL. Bir haberin bu katmana girmesi için yassı
tarafa dokunması gerekir (flat steel / sheet / coil / strip / galvaniz /
soğuk hadde / teneke / elektrik çeliği / servis merkezi...). Pelet tesisi,
entegre tesis, EAF minimill, ham çelik istatistiği, hisse devri, "10 yılda
şu kadar milyar dolar gerekiyor" türü projeksiyonlar girmez — 2026-W35
bülteninde 9 Yatırım satırının 9'u da bu türdendi.

**HİÇBİR KATMANA GİRMEZ** — fiyat, borsa, bilanço, ciro, ihracat/ithalat,
damping/kota, pazar araştırması ve rapor satışı, kişi ataması, fuar/kongre.

## 2. Değişmez kurallar

1. **Haber, tarih veya detay UYDURULMAZ.** Doğrulanamayan tarih girmez.
2. Elle eklenen her satır için **makale açılır ve yayın tarihi sayfadan
   doğrulanır.** Doğrulanamıyorsa satır alınmaz.
3. `begins/starts/launches production`, `commissions`, `devreye aldı`
   = **İLK ÜRÜN**. Başlık niyet dili taşıyorsa ("to invest", "plans to",
   "partner on", "imzaladı") aşama İlk ürün **olamaz** — bunu `NIYET`
   kapısı da kod tarafında engeller, ama gözle de kontrol edilir.
4. **0 satırsa "haber yok" denmez.** Teşhis konur: reddedilenler, erişim
   durumu, kaynak sağlığı.
5. **Bozuk bülten göndermektense göndermemek yeğdir.** Emin değilsen
   `out/ONAY` yazma, kullanıcıya nedenini anlat.
6. Mailde **ek yoktur**. Kapanış "Saygılarımla, Zeynel", altta
   "powered by Zeynel Abidin Çopur".

## 3. Haftalık akış

1. **TAZELİK.** `out/hafta_*.json` içindeki `period` bu ISO haftası değilse
   rapor üretme: `git log -3` ve Actions koşusuna bak, teşhis koy,
   kullanıcıya yaz, `out/ONAY` YAZMA, bitir.
2. **OKU.** `hafta_<donem>.json`, `needs_ai.json`, `kacanlar.json`,
   `reddedilenler.json`, `email.html`, `source_health.json`.
3. **ÇAPRAZ KONTROL.** Artık koşu içinde `python -m radar capraz`
   çalışıyor; sonucu `out/kacanlar.json`'dadır. **Bu dosya bülten değil,
   denetim listesidir** — içindeki satır bültene ancak editör baktıktan
   sonra girer (haber daha önce teknoloji köşesinde çıkmış olabilir).
   `dogrulanamayan` ve `acildi_elendi` listelerini de oku: kaçanın sıfır
   olması ile kontrolün çalışmamış olması ayrı şeylerdir.
4. **KALİTE KONTROL.** Tekrar var mı (aynı olay iki katmandaysa Hat'takini
   tut). Çöp/fiyat/rapor satışı sızmış mı. Sıcak hadde satırı Hat'a girmiş
   mi. Aşama rozetleri doğru mu — özellikle **İlk ürün**. `needs_ai.json`
   içindeki "düzelt" eksiklerini makaleyi açarak doldur.
5. **TEKNOLOJİ KÖŞESİ.** 1-3 madde seç (piyasa haberi ve arşivdekiler
   hariç), her biri için makaleyi açıp 1-2 cümle Türkçe tanıt. Aday yoksa
   köşe **boş bırakılabilir** — bölüm zaten her zaman render edilir ve
   "aday çıkmadı" yazar. Uydurma madde konmaz.
6. **ÜRET VE GÖNDER.** `out/ozet.json` yaz (§4), sonra
   `python3 -m radar finalize -s out/ozet.json -p <donem>`,
   `out/email.html`'i gözden geçir, `out/ONAY` yaz (ilk satır dönem,
   ikinci satır tarih + kısa not), commit + push. Push `gonder.yml`'i
   tetikler. Commit mesajına `[skip ci]` YAZMA.
7. **ALGORİTMAYI GELİŞTİR — atlanmaz.** 3. ve 4. adımda gördüğün somut
   hatadan **birini** seç ve kalıcı çöz (`radar/taxonomy.py`,
   `radar/collect.py`, `radar/classify.py`). **Gerçek başlığı vaka olarak
   `radar/selftest.py`'ye ekle** — uydurma örnek kullanma. `python3 -m
   radar selftest && python3 tests/e2e_offline.py` yeşilse ayrı commit ile
   push et; kırmızıysa geri al ve raporda söyle.
   **Ölçüm alışkanlığı:** filtre değişikliğini gözle değil, geçmiş
   koşuların `reddedilenler.json` + `hafta_*.json` dosyalarından çıkardığın
   benzersiz başlık havuzunda eski/yeni karşılaştırarak doğrula. Yeni sürüm
   çöp **EKLEMEMELİ**.
8. **KULLANICIYA RAPOR.** Kaç Hat + kaç Yatırım satırı, öne çıkanlar,
   teknolojiler, elle eklediklerin, bu haftanın algoritma iyileştirmesi,
   erişilemeyen kaynak sayısı, posta gitti mi.

## 4. `out/ozet.json` biçimi

```json
{
  "exec": "Yönetici özeti.",
  "cumleler": {"<anahtar>": "Türkçe tek cümle."},
  "duzeltmeler": {"<anahtar>": {"asama": "Modernizasyon"}},
  "cikar": ["<anahtar>"],
  "teknolojiler": [{"anahtar": "tech:...", "konu": "...", "metin": "...",
                    "url": "...", "tarih": "2026-06-15"}],

  "ai_eklenen":   [{"baslik": "...", "url": "...", "tarih": "2026-08-11",
                    "kaynak": "SteelOrbis", "neden": "neden kaçırıldı",
                    "firma": "...", "ulke": "...", "hat": "...",
                    "asama": "...", "kategori": "Hat"}],
  "ai_duzeltme":  [{"baslik": "...", "neden": "ne yanlıştı, ne yapıldı"}],
  "ai_cikarilan": [{"baslik": "...", "neden": "çıkarma sebebi"}],
  "ai_kontrol":   "Hangi kaynaklar çapraz kontrol edildi, sonuç ne"
}
```

`cumleler` **yalnız Hat satırları** için zorunludur; ama Yatırım satırına
cümle yazılmazsa mailde İngilizce başlık çıkar — yazmak daha iyidir.

**`ai_eklenen` iki iş birden yapar:** listeye satır ekler *ve* postadaki
"AI Kontrolü ve Eklemeleri" bölümünü besler. `url` + `baslik` taşıyan madde
satır olur ve mailde **`+ AI`** rozetiyle görünür; yalnız `neden` taşıyan
madde satır üretmez, sadece bölümde görünür.

## 4b. Hacim hedefi: 7-8 gelişme + 1 teknoloji

Bülten **ortalama 7-8 gelişme** ve **her hafta 1 teknoloji** taşımalı.

**Bu hedef kapıyı gevşeterek tutturulmaz.** 2026-W35'te tam olarak bu
denendi: Katman 2 "her çelik yatırımını" alınca liste 11 satıra çıktı ama
9'u kapsam dışıydı. Doğru yol **rezerv**:

- Pencere dışında kalan ama **aynı kapıdan geçmiş ve tarihi sayfadan
  doğrulanmış** satırlar `state.rezerv`'de birikir.
- Taze liste 8'in altındaysa eksik buradan, yeniden eskiye doğru tamamlanır.
- Bu satırlar mailde **"GEÇ YAKALANDI"** rozetiyle çıkar — okuyucu neden
  eski tarihli bir satır gördüğünü bilir.
- Teknoloji köşesi de aynı mantıkla `state.tech_rezerv`'den beslenir; aday
  çıkmayan hafta köşe boş kalmaz.

**Ölçülen arz:** taze kapsam içi haber haftada ~1-3. Yani 7-8'in bir kısmı
düzenli olarak rezervden gelecek — bu bir kusur değil, tasarım. Rezerv
tükenirse liste kısalır; **kısa liste, yanlış listeden iyidir.** O hafta
diagnoz yaz: erişilemeyen kaynak sayısı ve rezerv havuzunun boyutu.

Hacmi kalıcı yükseltmenin tek gerçek yolu **erişim**: ölçüme göre kapsam içi
haberin %72'si STI + SteelOrbis'ten geliyor ve STI 403 veriyor.

## 4c. "Gönderildi" işareti yalnız onayla konur

Tarama (`radar run`) posta **göndermez**; postayı `out/ONAY` gönderir. Bu
yüzden tarama hiçbir satırı "gönderilmiş" saymaz — o işareti **yalnız
`finalize`** koyar.

Neden önemli: aksi hâlde onaylanmayan her koşu gerçek haberleri sessizce
yakar. 2026-08-27'de ölçüldü — gerçekten gönderilen tek bülten 3 satırlıktı
ama state'te **21 satır** "gönderilmiş" işaretliydi; 18 haber okuyucuya hiç
ulaşmadan bir daha çıkamaz hâle gelmişti. Doğrulama için elle başlatılan her
koşu da aynı zararı veriyordu.

Sonuç: onaylanmayan bir satır **gelecek hafta yine listede çıkar.** Bu bir
kusur değil — gönderilmediyse gönderilmemiştir.

## 4d. Günlük tarama

`gunluk.yml` her gün 03:17 UTC'de `radar run --sadece-tarama` çalıştırır.
**Posta göndermez, posta gövdesine dokunmaz.** Tek işi havuzu beslemek:
rezerv + teknoloji adayları.

Neden: yayıncılar haberi geç indeksliyor, kaynak gün içinde 403 verip ertesi
gün açılıyor, ve 15 günlük pencere kapanınca haber bir daha yakalanmıyordu.
Ölçüm: bir haftalık koşuda elenen 30 kapsam içi satırın **26'sı sırf pencere
dışıydı.** Günlük tarama bunu **kapıyı gevşetmeden** çözer — satır sayısı
kaynak tarafından yükselir, filtre aynı kalır.

Pazartesi editör koşusu bu havuzun üstüne oturur.

Günlük tarama **hiçbir zaman** haftalık arşive yazmaz. Kendi çıktısı ayrı
dosyadadır: `out/tarama.json` + `out/tarama_needs_ai.json`. (2026-08-29'da
tersi oldu: tarama, gönderilen 6 satırlık W35 bülteninin kaydı olan
`out/hafta_2026-W35.json`'u rezervden gelen 4 satırla ezdi; ne gönderdiğimi
ancak git geçmişinden çıkarabildim.)

### Rapordaki bağlantı okuyucunun tıkladığı şeydir

Aggregator yönlendirmesi tıklandığında önce arama motoruna gider. W35'te
Roofings satırının bağlantısını bu yüzden **elle** düzeltmek zorunda kaldım;
arama katmanı artık kaynakların yarısı olduğu için bu tek tek düzeltilecek
bir iş değil. Bing adresi gerçek adresi `&url=` içinde taşır ve ağ
kullanmadan çözülür. Google'ın yeni biçimi (`CBMi…`) **şifrelidir**,
çevrimdışı çözülemez — o adresler olduğu gibi kalır ve editörün düzeltme
listesinde görünür.

### Köşe adayı da tekrar denetiminden geçer

"Köşede tanıtılmış haber satır olamaz" kuralı çift yönlü olmakla kalmaz;
**gönderilmiş olayın varyantı da köşeye giremez.** `seen` kontrolü anahtar
bazlıdır ve başka yayının aynı olayı anlatan varyantının anahtarı farklıdır.
Ölçüldü: "Primetals Technologies to Modernize PLTCM for KG Steel in South
Korea" havuza girdi — W35'te "KG Steel selects Primetals for Dangjin PLTCM
upgrade" olarak zaten gitmişti. **Başlık benzerliği bu çifti yakalamaz**
(ortak ayırt edici kelime yalnız `steel` ve `pltcm`, oran %30); yakalayan
bacak olay parmak izidir, bu yüzden köşe adayı için de aday bir satır
kurulup aynı izler hesaplanır.

## 4i. Bulunan havuzu — görülen haber unutulmaz

**Hacim sorununun asıl sebebi buydu.** Günlük tarama kabul ettiği satırı
hiçbir yere kaydetmiyordu: `out/tarama.json` ertesi gün üzerine yazılıyor,
rezerv ise yalnızca **pencere dışı** satırları tutuyor. Aggregator sonuçları
ise **oynak** — bir gün görünen haber ertesi gün beslemede yok.

Ölçüldü (günlük taramaların git geçmişi): sistem hafta boyunca birbirinden
farklı satırlar gördü ve her biri **tek bir taramada** görünüp kayboldu:

| bulunduğu tarama | haber |
|---|---|
| 29.08 | India's Manaksia Steel to invest $84 million… |
| 31.08 | ArcelorMittal Confirms Up to R$ 5 Billion for New Cold Rolling Mill |
| 31.08 | KEZAD galvanising facility moves closer to commissioning |

Bültene 2 satır girdi. **Kapı değil, hafıza eksikti.**

`state.bulunan`: pencere içi, kapıyı geçmiş, tarihi doğrulanmış, henüz
gönderilmemiş satırlar. Haftalık koşu önce buradan tamamlar (taze, rozetsiz),
sonra rezerve bakar (pencere dışı, "GEÇ YAKALANDI"). Kapı gevşemez —
satırlar zaten aynı kapıdan geçmiştir; değişen tek şey unutulmamaları.
Havuz çıkışta da güncel kapıya sokulur ve gönderilmiş olan düşer.

### Yanlış "tekrar" elemesi gerçek haber kaybettirir

Havuz kurulunca görüldü: iki **ayrı** Hint şirketinin haberi aynı sayılıp
elenmişti — paylaştıkları şey `invest` / `million` / `capacity` idi, üçü de
kalıp. Kural: **ayırt edici ortak kelime yoksa, kalıp örtüşmesi tek başına
yetmez.** Ölçüm (400 başlıkta çift sayımı): 1816 → 1794; 22 yanlış
birleştirme kalktı, yeni birleştirme olmadı. Tek ayırt edici ad + zayıf
örtüşme (Hydnum vakası) korunur.

Eleme **sessizdir** — yanlış elenen haberi kimse görmez. Bu yüzden tekrar
kapısının hatası, kapsam kapısınınkinden daha pahalıdır.

## 4h. Rezervdeki satır, sözlük düzelince kendini düzeltir

Rezerv 540 gün geriye uzanır; havuza giren satır **o günkü kodun kararını**
taşır. Sözlükteki bir hata düzeltildiğinde havuzdaki eski satır hâlâ bozuk
değeri taşır — 2026-08-29'da tam bu oldu: `\bindia` deseni düzeltildikten
sonra bile "U. S. Steel … Gary Tin Mill" satırı rezervden **Hindistan**
olarak çıkmaya devam etti. Rezervden seçilen satırın ülkesi, seçim anında
güncel sözlükle **başlıktan** yeniden türetilir; başlık ülke taşımıyorsa
(KG Steel/Dangjin gibi) gövdeden gelen eski değer korunur.

## 4g. Gönderilmiş satır hafızası (`son_basliklar`)

Rezerv **540 gün** geriye uzanır, dolayısıyla hafıza da o kadar uzun tutulur
— 21 günlük budama, üç hafta önce gönderilmiş bir haberin başka yayındaki
varyantının rezervden geri dönmesine izin veriyordu. 21 günlük pencereyi
kullanan taraf (`collect.py` üçüncü bacak) kesimini kendisi yapar.

Her kayıt `{b, t, a, ted, u}` taşır — başlık, tarih, aşama, **tedarikçi,
ülke**. Tedarikçi/ülke olmadan "aynı tedarikçi + aynı aşama + (aynı ülke ya
da aynı gün)" imzası gönderilmiş satırlara karşı hiç işletilemiyordu.

`finalize` yazarken tekrar denetimi yapar (`state.dedup_basliklar`): aynı
hafta iki kez finalize edilirse hafıza şişmez.

Bu üç kusur 2026-08-29'da birlikte görüldü: 11 kayıtlık hafızada yalnızca 6
farklı başlık vardı, W34'te gönderilen "tk accelis" satırı düşmüştü ve aynı
haberin Yieh varyantı ile W35'te giden KG Steel/Primetals olayının STI
varyantı rezervden listeye girdi.

## 4e. Otonomi: sistem sensiz çalışır

```
her gün 03:17 UTC   gunluk.yml   tarama → rezerv + teknoloji havuzu
                                 (posta yok, "gönderildi" işareti yok)
pazartesi 04:37     weekly.yml   haftalık koşu + çapraz kontrol
pazartesi 05:30     editör       EDITOR.md akışı → ozet.json → finalize
                                 → out/ONAY → main'e push
                    gonder.yml   ONAY'ı görür, postayı gönderir
pazartesi 07:00     bekçi        gitmediyse kullanıcıya bildirim
```

Kullanıcıdan **hiçbir onay beklenmez.** Editör kendi kararını verir ve
gönderir. Tek durum: bülten bozuksa `out/ONAY` yazılmaz, sebep rapor edilir
— bekçi de bunu kullanıcıya bildirir.

**Hedef 5-6 gelişme + 1 teknoloji.** Taze arz yetmezse rezervden tamamlanır;
rezerv de boşsa liste kısalır. Sayıyı tutturmak için kapı gevşetilmez.

## 4f. Kapalı kaynaklar ve elle besleme

15 kaynak sorunlu: 7'si bot koruması (403/429), 7'sinde sayfa açılıyor ama
link çıkmıyor, 1'i ölü adres. **Editörün kendi oturumu da aynı egress
proxy'nin arkasında** — o da bu sitelere giremiyor. İki yönlü çözüm:

### Zayıf haftalarda editör bulur, MAKİNE doğrular

Taze arz ölçülmüş haliyle haftada ~1-3 kapsam içi haber; hedef 5-6. Zayıf
haftada editörün arama ile haber bulması **gerekir** — ama bulduğunu
doğrudan rapora yazmak iki kuralı birden çiğner: tarih uydurulamaz, ve
kapsam kapısı editörün kanaatiyle değil aynı kapıyla işler.

**Akış:** editör arama yapar → `veri/elle_besleme.json`'a **yalnız başlık +
adres** yazar → push → `dogrula.yml` tetiklenir → `radar dogrula` Actions'ta
her adresi açar, **sayfanın gerçek başlığını** alır, aynı kapıdan geçirir,
tarihi **yapısal olarak** çıkarır, tekrar denetiminden geçirir ve pencere
içindeyse `bulunan`a, dışındaysa `rezerv`e yazar → editör `finalize` eder.

Zincirin hiçbir halkası atlanamaz; `selftest` bunun bekçiliğini yapar.
**Editörün katkısı ADAY GÖSTERMEKTİR, karar makinenindir.**

Aday seçerken: **sayfası açılabilen yayın** (MEsteel, Metallurgprom,
SteelOrbis, Yieh, Danieli, Primetals, John Cockerill, Fives, ANDRITZ,
Tenova, üreticilerin kendi newsroom'ları). Kapalı yayınların kendi adresi
ölçüldü ve hiç satır üretmedi — sayfa 403 verince tarih de doğrulanamıyor;
o yayınların haberleri artık arama katmanında `site:` hedefiyle yakalanıyor.

#### Arama motoru ESKİ sayfaları öne çıkarır — ölçüldü, üç kez

İlk gerçek doğrulama koşusu (2026-08-31): editörün 11 adayının **hiçbiri**
pencere içinde değildi.

| sonuç | adet |
|---|---|
| doğrulanıp rezerve eklendi | 3 |
| **"çok eski" (2024 tarihli)** | **3** |
| gönderilmiş haberin varyantı | 3 |
| kapsam dışı | 2 |

Üç 2024 haberi (Tata/Danieli birleşik hat, Borçelik ×2) doğrulama olmasa
bültene girecekti. Daha önce de aynı şey olmuştu: JFE Guangzhou hattı
2012'den, "CMI" ise şirketin 2019'da John Cockerill olmasından önceden.

**Kural:** editörün bulduğu hiçbir aday, yaşı doğrulanmadan bültene
giremez — ve editör bunu kendi oturumundan doğrulayamaz. Bu yüzden
`radar dogrula` bir kolaylık değil, **zorunlu halkadır.** Aday yazarken
yayının tarih taşıyan listesinden (arşiv/haber indeksi) gitmek, arama
sonucundan gitmekten daha güvenilirdir.

**1. Sitemap zinciri + robots.txt keşfi.** 16 kaynağa yedek adres listesi
bağlandı. Sitemap çoğu zaman ana sayfayla aynı korumada değil — SteelOrbis
bunu kanıtladı (sayfa 403, sitemap 1000 adres).

**2. `veri/elle_besleme.json`.** Editör kapalı yayınların başlıklarını
**arama ile** bulur ve bu dosyaya yazar. Kurallar:

- Dosya **yalnız başlık + adres** taşır. **TARİH YAZILMAZ.**
- Editörün beyan ettiği bir tarih rapora asla giremez — "tarih uydurulmaz"
  kuralı burada da geçerli, `selftest` bunun bekçiliğini yapar.
- **Tarihi kim doğrular:** ulaşılabilir bir beslemeden (Google News RSS),
  yayıncının kendi `pubDate`'inden, **başlık örtüşmesi aranarak**. Örtüşme
  yoksa tarih yok, satır da yok.

  İlk tasarımda tarih "Actions makale sayfasını açarak" doğrulanacaktı; bu
  yanlıştı ve ölçüldü — 15 kaydın 14'ü `tarihsiz_elendi` ile düştü, kanal
  **hiç satır üretmedi.** Kapalı yayının sayfası kapalıysa tarihi de
  kapalıdır.

- **Kanalın ölçülmüş verimi düşüktür.** Google News doğrulaması eklendikten
  sonra 15 kaydın **1'i** tarih alabildi (o da pencere dışıydı): Google News
  bu yayınların çoğunu ya indekslemiyor ya da başlık birebir örtüşmüyor.
  **Bu yüzden dosyayı doldururken önceliğin ULAŞILABİLİR bir yayının
  adresidir** — aynı haberi yazan başka bir yayın. O zaman tarih makale
  sayfasından normal yoldan doğrulanır ve satır gerçekten çıkar. Kapalı
  yayının kendi adresi son çaredir ve genellikle satır üretmez. Başlık örtüşme ölçütü tekrar elemeninkinden **katıdır**:
  `similar_titles` "SMS upgrades Hyundai Steel galvanising line" ile
  "Ternium contracts Fives for new galvanizing line"i aynı sayıyor; tekrar
  elemede bu tolerans doğru, tarih atamada başka haberin tarihini bu
  başlığa yapıştırır.
- Kapsam kapısı değişmez; bu kanal yalnızca **aday** taşır.
- Pencere dışında kalanlar rezerve düşer, kaybolmaz.

Bu dosya **her hafta tazelenir** (ayrı routine, `SogukRadar elle besleme`).
Kapalı yayınlar için arama sorguları: yayın adı + hat terimleri, son 30 gün.

### Kaynağın kendi adresi önce, sitemap zinciri sonra

Sitemap **zinciri tahmindir** ve yalnızca kaynağın kendi adresi iş
görmediğinde denenir. Sıra v19'da tersti; geri düşüş eklemek yetmedi.
Ölçüm (2026-08-29 koşusu, v19 öncesiyle karşılaştırmalı):

| | kaynak |
|---|---|
| zincirin **kazandırdığı** | GMK Center, Mysteel |
| zincirin **kaybettirdiği** | ABB Metals, Nippon Steel, China Baowu, SteelGuru, Kocks |

Beş kaynak da v19 öncesinde açılıyordu ve kendi adresleri değişmemişti.
Sebep zincirin kendisi: gerçek istekten hemen önce aynı sunucuya 1-4
başarısız istek gidiyor, site bunu bot davranışı sayıp kapıyı kapatıyor.

İkinci kural: **zincirin hatası kaynağın hatasını gölgelemez.** Kendi adresi
açılıp da liste boş döndüyse kaynak *erişilemez değildir* — v20'nin ilk
halinde zincirin "sitemap boş" hatası bu duruma yazılıyor ve China Baowu ile
SteelGuru erişilemeyen listesine yanlış giriyordu.

### Havuz KARARI taşır, KODU değil — üç yerde aynı ders

Rezerv 540 gün geriye uzanır ve içindeki her satır **havuza girdiği günkü
kodun kararını** taşır. Kapıyı düzeltmek havuzdaki eski kararı düzeltmez.
Aynı ders 2026-08-31'de üç ayrı yerde çıktı:

| yer | vaka | çözüm |
|---|---|---|
| ülke alanı | `\bindia` düzeltildi ama rezervdeki Gary satırı hâlâ "Hindistan" | `_rezerv_alanlarini_tazele` — ülkeyi güncel sözlükle başlıktan yeniden türetir |
| olay parmak izi | editör Roofings satırını düzeltti, hafızada bozuk iz kaldı → aynı haberin iki varyantı geri geldi | `finalize` izi **düzeltmeden sonra** üretir, eskisini de saklar |
| kapsam kapısı | M&A ve QSP vetoları eklendi, aynı koşuda o iki satır **rezervden** listeye girdi | `_rezerv_hala_gecerli` — havuz her koşuda güncel kapıya sokulur, düşen satır kalıcı olarak çıkar |

Kural: **kalıcı bir havuza yazılan her karar, okunurken güncel kodla
yeniden sınanmalıdır.** Yeni bir havuz eklenirse bu soru sorulmalı.

### Havuzu büyütmek kapının deliklerini gösterir

Rezerv ilk açıldığında beş delik göstermişti; ikinci arama host'u açılınca
üç delik daha çıktı. Bu bir kural: **arzı artıran her değişiklik, aynı
koşuda kapının denetimidir.** Yeni katmanın getirdiği satırlar tek tek
okunmadan katman "çalıştı" sayılmaz — 2026-08-31'de Bing aynası ham
bağlantıyı %21 artırdı ve beş satır üretti, beşi de yayınlanamazdı.

1. **Olay parmak izi düzeltmeden sonra üretilir.** İz koşu anında, henüz
   düzeltilmemiş alanlardan üretiliyordu; editörün düzeltmesi hafızaya hiç
   yansımıyordu. Eski iz de korunur (başka yayın aynı bozuk okumayı
   üretebilir).
2. **Şirket satın alma her iki katmanda vetoludur.** Veto yalnız Katman
   2'deydi; gövdede servis merkezi geçince Hat katmanı açılıyordu. Bir
   servis merkezinin el değiştirmesi hat gelişmesi değildir.
3. **QSP / ince slab döküm yukarı akıştır.** Firma adında "Flat Steel"
   geçmesi haberi yassı *işlem* hattı yapmaz.
4. **Kimsiz parmak izi bacağı** — aynı ülkede, aynı hatta, aynı ay içinde
   iki ayrı tesis **ilk üretime geçmez**. Bacak yalnız `İlk ürün` /
   `Seri üretim` için açılır; sözleşme ve modernizasyon haberleri büyük
   üreticilerde meşru şekilde tekrarlanır ve orada bu bacak gerçek haber
   kaybettirirdi.

### Host bütçesi ve soğutma — bu hata sınıfı artık yapısal olarak kapalı

`http.fetch` her isteği göndermeden **host bütçesini sorar**. Bütçe dolunca
istek gönderilmez — hangi iş isterse istesin. Bir host hız sınırı sinyali
(429/503) döndürdüğünde **soğutmaya alınır** ve o koşuda bir daha
denenmez; ısrar, yumuşak kısıtlamayı sert bloğa çevirir.

Bunun anlamı şudur: **yeni bir katman eklemek mevcut katmanı artık riske
atamaz.** En kötü ihtimalle yeni katman kendi bütçesini tüketir. Host
sağlığı koşu çıktısına ve `hafta_*.json`'a yazılır — sessiz kısıtlama en
kötüsüdür.

### İkinci arama host'u — tek noktadan çökme bitti

169 kaynağın 80'i tek host'taydı (news.google.com), yani arama katmanının
**tamamı** tek sağlayıcıya bağlıydı. Her Google News sorgusunun **Bing News
aynası otomatik üretilir** (`sources._bing_aynalari`) — elle ikinci liste
tutulmaz, sorgu eklendiğinde aynası bedava gelir ve iki liste asla sapmaz.
Ayrı host, ayrı hız sınırı, ayrı indeks: biri çökerse diğeri ayakta kalır.

Kapı **genişlemez** — aynı sorgular, aynı kapsam kapısı, aynı tarih
zinciri. Değişen tek şey aynı sorunun ikinci bir yere de sorulması. Ayrıca
besleme maddesi yapısal tarih (`pubDate`) taşır, yani bu katmandan gelen
haber "tarihsiz elendi" kovasına hiç düşmez — haftalık kaybın en büyük
kalemi oydu (96 kayıt).

### Paylaşılan host'a fazladan istek bedava değildir

169 kaynağın **~90'ı Google News arama beslemesidir** — hepsi tek host.
O host'a giden her fazladan istek bütün arama katmanını riske atar.

Ölçüldü (2026-08-31, koşu 33414160429). Tarihi doğrulanamadığı için elenen
96 kaydın 9'u başlıkla kapıyı geçiyordu ve 8'i makale sayfası 403 veren
yayınlardandı; tarihlerini Google News `pubDate`'inden sormayı denedim:

| | öncesi | sonrası |
|---|---|---|
| erişilemeyen kaynak | 9 | **89** (80'i Google News, HTTP 503) |
| kurtarılan tarih | — | **0** |
| kabul edilen satır | 2 | **0** |
| koşu süresi | ~35 dk | 60 dk |

Geri alındı. Sitemap zincirinin beş kaynağı bozmasıyla **aynı aile**: fazladan
istek bedava değildir, faturayı başka bir iş öder. Elle beslemenin ~13
sorgusu ölçülen tolerans içindedir (o koşuda erişilemeyen 9'du); üzerine
çıkılmamalı. `selftest` bunun bekçiliğini yapıyor.

**Hacim artırmanın hâlâ açık olan yolları:** kapalı yayınların haberini
*ulaşılabilir* bir yayından yakalamak (elle besleme kuralı), günlük taramanın
rezervi beslemesi, ve kaynak listesini Google News'e yüklenmeden genişletmek.

## 5. Kalıcı bölümler

Bu iki bölüm **her hafta**, içerik olmasa da render edilir — bölümün hiç
görünmemesi ile "bakıldı, çıkmadı" aynı şey değildir:

- **Teknoloji Köşesi** — her zaman ve her zaman *Haftanın Gelişmeleri'nden
  önce*. Boşsa "aday çıkmadı" yazar.
- **AI Kontrolü ve Eklemeleri** — listeden hemen sonra. Boşsa "düzeltilecek
  bir şey bulunmadı" yazar.

## 6. Sistem notları

- **Tarama haftada bir çalışır** (Pazartesi 04:37 UTC). `weekly.yml`'in
  push tetikleyicisi kaldırıldı: her kod push'u tam tarama başlatıyordu,
  `out/` dosyalarını eziyordu ve her koşu kabul ettiği satırı `seen`'e
  yazdığı için **listeyi boşaltıyordu**. Kodu denemek için
  `workflow_dispatch` kullan.
- Posta `weekly.yml`'den **çıkarıldı**; `out/ONAY` push'uyla `gonder.yml`
  gönderir. Editör onaylamazsa posta gitmez.
- Editör oturumunun ağ çıkışı haber alan adlarına **kapalıdır** (egress
  proxy 403). Sayfa açman gereken iş `radar capraz` ile koşucuya taşındı.
- **Tekrar engeli AÇIK** (2026-08-18). `KALIBRASYON` dosyası silindi; artık
  aynı haber ikinci kez gönderilmez. Hafıza `state/state.json` içinde
  `seen` / `events` / `son_basliklar` olarak tutulur ve **Actions** günceller.
  Bir haberi bilerek tekrar göstermek istersen `out/ozet.json` →
  `ai_eklenen` ile elle ekle; `state`'e elle dokunma.
- Tekrar savunması **üç bacaklıdır**: başlık anahtarı (`seen`), olay parmak
  izi (`events`), başlık benzerliği (`son_basliklar`, son 21 gün). Üçüncü
  bacak ürün kataloğu başlıklarını artık dikkate almaz — v8 öncesinden kalan
  çöp, gerçek haberi "tekrar" diye eliyordu (2026-W34'te 0 satırın sebebi).

## 7. Teknoloji arşivi (bir daha seçme)

1. EV motorları için %6,5 silisyumlu geniş elektrik çeliği (POSCO/Hyundai)
2. PLTCM modernizasyonunda AI destekli proses otomasyonu (Primetals/KG Steel)
3. Galvaniz hattı yenilemesinde dijital montaj + yapay görü ile yüzey kalite
   kontrolü (Severstal / CherMK) — 2026-W35

> Seçtiğin teknolojiyi **bu listeye ekle** — arşiv artık routine prompt'ta
> değil, burada tutulur.
