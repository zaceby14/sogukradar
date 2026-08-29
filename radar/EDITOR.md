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

> Seçtiğin teknolojiyi **bu listeye ekle** — arşiv artık routine prompt'ta
> değil, burada tutulur.
