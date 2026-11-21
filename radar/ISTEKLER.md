# SoğukRadar — Kullanıcı İstekleri (Zeynel)

Bu dosya, kullanıcının sohbetlerde verdiği bütün istek ve kuralların derli toplu
listesidir. Sistemi değiştiren herkes (insan ya da ajan) önce bunu okur. Çelişkide
en yeni tarihli istek geçerlidir. Teknik ayrıntı: `radar/EDITOR.md`.

## 1. Amaç
- Türkiye'de bir soğuk haddehane yöneticisi ve ekibine **haftalık** bülten:
  haberler (hat + yatırım), **teknoloji köşesi**, **piyasa gündemi**.
- **En önemlileri: teknolojiler ve yatırımlar** (2026-11-21).
- İyi ve güvenilir kaynaklar kullanılsın; kapalı yayıncılara resmi açık kapılardan
  (RSS, sitemap) girilsin, bot koruması aşılmaya çalışılmasın.
- Haftalık ortalama 5–6 haber + 1 teknoloji hedefi; ama **çöp kesinlikle istenmez**
  ("filtreleri genişletme, çöp haber istemiyorum").

## 2. Kapsam
- YALNIZ sıcak haddeleme SONRASI yassı çelik işleme hatları: asitleme, soğuk hadde
  (tandem/reversing/PLTCM), temper/skin pass, tavlama (CAL/BAF), galvaniz/kaplama
  (CGL, ZnAlMg), boyalı sac (CCL), teneke, dilme/boy kesme, merdane atölyesi,
  yüzey muayene, ölçüm, hat otomasyonu, elektrik çeliği.
- KAPSAM DIŞI: sıcak hadde, yüksek fırın, DRI/EAF, döküm, uzun ürün, kalın levha,
  boru, demir dışı; borsa, bilanço, atama, fuar, satın alma/birleşme, girişim
  yatırım turu, pazar araştırması raporları.
- Fiyat/ticaret/koruma önlemi haberleri ana listeye değil **Piyasa Gündemi**'ne.

## 3. Değişmez kurallar
- Haber, tarih, detay **UYDURULMAZ**. Doğrulanamayan tarih girmez.
- "Devreye aldı / ilk üretim" iddiası yalnız gerçekten üretim başladıysa.
- Gönderilmiş haber bir daha gönderilmez (aynı olayın başka yayındaki hali dahil).
- Mail "Saygılarımla, Zeynel" ile kapanır; altta "powered by Zeynel Abidin Çopur";
  ek yok.
- Bozuk bülten göndermektense göndermemek yeğdir — ama bülten **hiç aksamamalı**.

## 4. Zamanlama ve işletme
- Bülten **her Pazartesi 07:30 (TSİ)**'de gelsin (2026-11-09).
- Sistem **Claude'a ve kullanıcıya bağlı olmadan** tam otomatik çalışsın (GitHub
  Actions + Gemini); kullanıcıya iş yaptırılmasın.
- Alıcılar: Gmail ve Erdemir adresi; ikisine de gitmeli.
- Sorun olursa kullanıcıya uyarı maili gitsin.

## 5. Bölümler
- **Teknoloji köşesi:** gerçek yenilik (ilk uygulama, yeni kalite/kaplama, Ar-Ge,
  pilot, yeni proses). Ürün tanıtımı/sipariş/pazar raporu yenilik değil. Ama köşe
  **BOŞ KALMASIN**: gerçek yenilik yoksa en ilgili teknik gelişme konsun
  (2026-11-21). Geriye 1 yıla kadar bakılabilir.
- **Piyasa gündemi:** 2–3 madde, en önemliler; **en güncelleri** seçilsin;
  **boş kalmasın** (2026-11-21).
- **Haberler:** yatırımlar öne çıksın. Haber azsa pencere 15 güne kadar açılabilir
  (şu an 21 gün; liste kısa kalırsa 30/90 gün yedek havuz).

## 6. Mail görünümü
- Sade, güzel, telefonda okunaklı (2026-11-21: tek sütun kart düzeni).
- Deneme mailinin başlığında "DENEME" yazmasın; deneme de iki adrese gitsin.

## 7. Geri bildirim
- Her maddede 👍 Faydalı / 👎 İlgisiz; mail programı açmasın (Google Form, tek tık).
- Herkes oy verebilsin; algoritma beğenilen türe odaklansın.
- Bir maddeye **faydalı** oyu geldiyse **faydasız** oylar dikkate alınmasın.

## 7b. Geliştirme ilkesi
- Düzeltmeler **tek seferlik olmasın**; her hafta, her maddeye otomatik uygulanan
  genel kural olsun (2026-11-21). Bir vaka bulunduğunda: kural + test + eski
  verilerde gerileme ölçümü.
- Bültendeki **her link** (haber, teknoloji, piyasa) gönderimden önce açılır:
  toplayıcı (Google News/Bing/MSN) adresi yayıncı adresine çevrilir, sayfa
  başlığı ve yayın tarihi maddeyle tutmazsa madde düşer (2026-11-21).

## 8. Deneme ve hafıza
- Deneme koşuları haber tüketmez (hafızaya yazmaz); sonraki haftaları etkilemez.
- Gerçek gönderimde gidenler bir daha gönderilmez.
