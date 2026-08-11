# SogukRadar v3.0 — haftalık yassı çelik downstream radarı

Sıcak hadde **sonrası** yassı çelik işlem hatlarına (soğuk hadde, asitleme, tavlama,
kaplama, boyama, teneke, dilme, roll shop, yüzey muayene, otomasyon, elektrik çeliği)
dair yatırım ve teknoloji haberlerini her hafta otomatik toplar, tarihini doğrular,
sınıflandırır ve Türkçe rapor üretir.

**Sıfır bağımlılık.** Yalnızca Python 3.11 standart kütüphanesi. `pip install` adımı yok.

---

## 1. Neden bu sürüm var — iş yükü meselesi

Önceki sürümde toplama işini yazılım değil ben yapıyordum, çünkü çalıştığım
kum havuzunun kabuk erişiminde internet yok: `urllib`/`curl` kapalı, ağa yalnızca
benim tarayıcı araçlarımdan çıkılıyor. Sonuç:

| İş | v2.0 (bulut oturumu) | v3.0 (GitHub Actions) |
|---|---|---|
| Sayfaları indirmek | **Ben** (8 çağrı) | Yazılım (35 kaynak) |
| Yayın tarihini bulmak | **Ben** (haber haber açıp okuyarak) | Yazılım (JSON-LD / meta / `<time>` / RSS) |
| Kapsam elemesi | Yazılım | Yazılım |
| Hat / aşama / ülke / firma | Yazılım | Yazılım |
| Tekrar engeli | Yazılım | Yazılım |
| Puanlama, sıralama | Yazılım | Yazılım |
| HTML / CSV / PDF | Yazılım | Yazılım |
| Belirsiz satırların yorumu | Ben (1 satır) | Ben (yalnızca `needs_ai.json`) |
| Türkçe cümleler | Ben | Ben |
| 25 KB base64 prompt kopyalamak | **Ben — ve her seferinde bozuldu** | **Yok** |

v3.0'da kendini taşıyan prompt tasarımı tamamen kaldırıldı: kod repoda durur,
hafıza `state/state.json` olarak repoda commit edilir. Bozulacak bir şey kalmadı.

## 2. Tarih kuralı — artık kodun içinde

> Tarihi yapısal olarak doğrulanamayan haber rapora **alınmaz**. Tarih tahmin edilmez.

`radar/dates.py` zinciri, sırayla:

1. RSS/Atom `pubDate` / `published` / `updated` (besleme varsa tarih hiç kazınmaz)
2. Makale sayfasındaki JSON-LD `datePublished`
3. `<meta property="article:published_time">` ve akrabaları
4. `<time datetime="...">`
5. Adresteki `/2026/08/09/` deseni
6. Sayfa metnindeki görünür tarih

Hiçbiri tutmazsa satır düşer (`tarihsiz_elendi` sayacına yazılır ve raporun
kapsam ölçümü tablosunda görünür). 3-6 arası kaynaklardan gelen tarihler
`tarih?` etiketiyle `needs_ai.json`'a düşer, yani **bana doğrulatılır**.

Ayrıca: gelecek tarihli ve 2015 öncesi satırlar otomatik reddedilir; ABD kaynaklı
sitelerde `08/09/2026` ay-gün, Avrupa kaynaklılarda gün-ay okunur.

## 3. Kaynaklar

**OEM / ekipman (22):** Danieli, Tenova (+Pomini, I2S), Primetals, SMS group,
John Cockerill, Andritz (+Sundwig), Fives, Clecim, Redex, Butech Bliss, Herkules,
Achenbach, Ebner, Drever, Nippon Steel Engineering, ABB Metals, ISRA Vision,
Cognex, Sarralle, Delta Steel Technologies, Bronx.

**Dergi / kurum (13):** Steel Times International, SteelTürk, Steel Radar,
SteelOrbis, EUROMETAL, Kallanish, GMK Center, AIST, The Canmaker,
Magnetics Magazine, Yieh Corp, worldsteel.

Listede `verified: True` olanlar geçen koşuda erişildiği fiilen doğrulanmış
kaynaklardır. Gerisi `python -m radar check` ile test edilir; erişilemeyen
kaynak **raporun başında açıkça listelenir** — kapsam eksiği sessizce kaybolmaz.

Bilerek dışarıda bırakılanlar `sources.KNOWN_GAPS` içinde yazılıdır
(Çince yerel OEM'ler, tam ödeme duvarlı servisler, LinkedIn).

## 4. Kapsam

**İçeride:** CPL/PPL asitleme, TCM/PLTCM/RCM/Sendzimir soğuk hadde, temper/skin pass,
CGL/GI/GA/Galvalume/Zn-Al-Mg/EGL kaplama, teneke (ETL), boyama (CCL), CAL/BAF tavlama,
dilme/boy kesme/tension leveling, roll shop, asit rejenerasyonu (ARP), yüzey muayene (SIS),
L1–L3 otomasyon, dijital ikiz, elektrik çeliği (NGO/CRGO) hatları.

**Dışarıda:** fiyat/piyasa, finansal sonuç, ticaret davaları, uzun ürün, sıvı çelik
öncesi (YF/DRI/EAF/sürekli döküm), demir dışı metaller, atama/ödül/fuar/ilan.

**Aşamalar:** Sözleşme · İnşaat · Test · İlk ürün · Seri üretim · Modernizasyon ·
Teknoloji. (`begins production` / `starts up` / `commissions` = **İlk ürün**,
Seri üretim değil.)

## 5. Haftalık akış

```
Pazartesi 07:05 TSİ   GitHub Actions
  ├── selftest + e2e (kırmızıysa koşu hiç başlamaz)
  ├── 35 kaynağı tara → tarihleri çıkar → filtrele → sınıflandır → puanla
  ├── out/hafta_YYYY-Www.json        (tam veri)
  ├── out/hafta_YYYY-Www_taslak.html (okunur taslak rapor)
  ├── out/hafta_YYYY-Www.csv
  ├── out/needs_ai.json              (bana sorulacaklar)
  └── state/state.json güncellenir + repoya commit
Pazartesi 08:00 TSİ   Ben (zamanlanmış görev)
  ├── needs_ai.json'u okurum
  ├── yalnızca eksik/şüpheli satırları düzeltirim
  ├── Türkçe cümleleri + yönetici özetini yazarım
  └── radar finalize → nihai HTML/PDF → sana teslim
```

State güncellemesini **Actions** yapar, ben değil. Böylece ben hiç çalışmasam
bile "aynı haber iki kez çıkmaz" garantisi bozulmaz.

## 6. Komutlar

```bash
python -m radar selftest          # ağsız birim testleri (18 regresyon testi)
python tests/e2e_offline.py       # ağsız uçtan uca boru hattı testi
python -m radar check             # kaynak sağlık taraması → out/source_health.json
python -m radar discover          # RSS/Atom besleme avı → out/feeds_found.json
python -m radar run --commit-state
python -m radar review            # bana sorulacakları ekrana döker
python -m radar finalize -s ozet.json -p 2026-W33
```

`ozet.json` biçimi:

```json
{
  "exec": "Yönetici özeti cümlesi.",
  "cumleler": {"a1b2c3d4e5f6a7b8": "Türkçe tek cümlelik özet."},
  "duzeltmeler": {"a1b2c3d4e5f6a7b8": {"firma": "Tosyalı", "ulke": "Türkiye"}},
  "cikar": ["kaldirilacak_anahtar"]
}
```

## 7. Ayarlar (ortam değişkeni)

| Değişken | Varsayılan | Anlamı |
|---|---|---|
| `RADAR_WINDOW_DAYS` | 21 | Tarih penceresi. 7 değil: bazı OEM'ler geç yayınlıyor. Tekrar riski yok, engel state'te. |
| `RADAR_MAX_ARTICLES` | 220 | Koşu başına açılacak azami makale sayfası |
| `RADAR_MAX_LINKS` | 120 | Kaynak başına azami bağlantı |
| `RADAR_PAUSE` | 0.7 | Aynı sunucuya istekler arası bekleme (sn) |
| `RADAR_TARGET_ROWS` | 20 | `--limit` ile kırpma sınırı |
| `RADAR_MIN_ROWS` | 5 | Altına düşülünce rapora "düşük kapsam uyarısı" basılır |

## 8. Kurulum

1. Yeni bir repo aç (public olması Actions dakikası açısından rahat).
2. Bu klasörü içine kopyala, `git push`.
3. Settings → Actions → General → Workflow permissions → **Read and write**.
4. (İsteğe bağlı) `MAIL_USER`, `MAIL_PASS`, `MAIL_TO` secret'larını ekle.
5. Actions sekmesinden `SogukRadar haftalik` → **Run workflow** ile ilk koşuyu
   elle başlat; `check_sources: true` seç ki hangi kaynağın açık olduğu görülsün.
6. `out/source_health.json` ve `out/feeds_found.json` çıktısına göre
   `radar/sources.py` içindeki adresleri düzelt / `rss=` alanlarını doldur.

İlk koşu bir kalibrasyon koşusudur: hangi sitenin 403 verdiği, hangisinin RSS'i
olduğu ancak gerçek ağda görülür.
