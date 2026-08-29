# -*- coding: utf-8 -*-
import os

VERSION = "3.0.0"
SYSTEM_NAME = "SogukRadar"
OWNER = "Zaceby"

ROOT = os.environ.get("RADAR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
STATE_DIR = os.path.join(ROOT, "state")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
CACHE = os.path.join(ROOT, ".cache")

# Haftalik kosu. Pencere 7 degil 21 gun: bazi OEM'ler haberi gec yayinliyor,
# bazi dergiler gecmise tarihli giriyor. Tekrar riski YOK - ayni haber
# state'teki 'seen' sayesinde ikinci kez cikamaz. Pencereyi genis tutmak
# "bu hafta haber yok" raporunun panzehiridir.
WINDOW_DAYS = int(os.environ.get("RADAR_WINDOW_DAYS", "21"))
# Teknoloji kosesi icin ayri, genis pencere: bir teknoloji haberi 6 aya kadar
# "yeni" sayilir. Tekrar engeli state.tech_seen ile saglanir.
TECH_WINDOW_DAYS = int(os.environ.get("RADAR_TECH_WINDOW_DAYS", "180"))
TARGET_ROWS = int(os.environ.get("RADAR_TARGET_ROWS", "20"))
MIN_ROWS = int(os.environ.get("RADAR_MIN_ROWS", "5"))

# Kaynak basina liste sayfasindan alinacak azami baglanti
MAX_LINKS_PER_SOURCE = int(os.environ.get("RADAR_MAX_LINKS", "120"))
# Haber sitemap'inden alinacak azami adres. Sitemap'te makale ACILMADAN
# baslik elemesi yapildigi icin bu sayi liste sayfasindan cok daha yuksek
# olabilir - maliyet MAX_ARTICLE_FETCH ile zaten sinirli.
MAX_SITEMAP_LINKS = int(os.environ.get("RADAR_MAX_SITEMAP", "400"))
# Kapsam on elemesini gecip makale sayfasi acilacak azami aday (maliyet freni)
MAX_ARTICLE_FETCH = int(os.environ.get("RADAR_MAX_ARTICLES", "220"))

# Reddedilenler dosyasi: toplam ve SEBEP BASINA kota. Sebep kotasi olmazsa
# akisin basindaki "kapsam_disi" yigini dosyayi doldurur ve "tekrar" gibi
# gec olusan sebepler hic gorunmez (2026-W34 teshisini imkansiz kilmisti).
REJECT_TOPLAM = int(os.environ.get("RADAR_REJECT_TOPLAM", "900"))
REJECT_SEBEP_KOTA = int(os.environ.get("RADAR_REJECT_SEBEP", "200"))

# HEDEF SATIR (2026-08-27 karari): bulten ortalama 7-8 gelisme tasimali.
# Taze arz bunu her hafta karsilamaz (olcum: haftada ~1-3 kapsam ici haber),
# bu yuzden kapi GEVSETILMEZ; eksik REZERV havuzundan tamamlanir. Rezerv,
# gecmis kosularda kapiyi gecmis ve tarihi DOGRULANMIS ama pencere disinda
# kaldigi icin hic gonderilmemis satirlardan olusur.
# 5-6 gelisme (2026-08-27 kullanici karari). Ortalama budur: dolu hafta
# 6, zayif hafta rezervden tamamlanir, rezerv de bosalirsa liste kisalir
# - kisa liste yanlis listeden iyidir.
HEDEF_SATIR = int(os.environ.get("RADAR_HEDEF_SATIR", "6"))
REZERV_MAX = int(os.environ.get("RADAR_REZERV_MAX", "300"))
REZERV_GUN = int(os.environ.get("RADAR_REZERV_GUN", "540"))   # ~18 ay

os.environ.setdefault("RADAR_CACHE", CACHE)

for d in (OUT, STATE_DIR, CACHE):
    os.makedirs(d, exist_ok=True)
