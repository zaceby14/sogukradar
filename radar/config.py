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

# REZERVDEN BULTENE GIREBILECEK EN ESKI HABER (2026-08-31, kullanici kurali:
# "5 taneden az haber oldugu her an 3 aylik verilere erissin, en uygun ve
# yakin tarihli olanlari alsin").
#
# Rezerv 540 gun SAKLAR - ama saklamak ile BULTENE KOYMAK ayni sey degil.
# 2026-W36'da liste Mart (MINO), Mayis (JIL) ve Temmuz (Marcegaglia) tarihli
# satirlarla dolduruldu; "GEC YAKALANDI" rozeti tasisalar da okuyucu icin bu
# haftalik bulten degil arsiv taramasidir.
#
# Ayrim: 540 gunluk saklama TEKRAR SAVUNMASI icindir - eski bir haberin
# varyanti bir daha giremesin diye. Bultene KOYMA hakki asagidaki sinirlarla
# olculur ve LISTENIN DOLULUGUNA gore degisir:
#   liste 5'ten AZ satir tasiyorsa  -> 3 aya kadar geriye gidilir (DAR gun)
#   liste 5 ya da daha doluysa      -> yalnizca son ayin haberi eklenir
# Havuz her zaman EN YENIDEN ESKIYE taranir, yani once en yakin tarihli.
REZERV_KULLANIM_GUN = int(os.environ.get("RADAR_REZERV_KULLANIM", "90"))
REZERV_DAR_GUN = int(os.environ.get("RADAR_REZERV_DAR", "30"))
REZERV_ESIK = int(os.environ.get("RADAR_REZERV_ESIK", "5"))

# ULASILABILIR BESLEMEDEN TARIH SORMA BUTCESI (2026-08-31).
# Makale sayfasi 403 veren yayinlarin haberleri kapiyi geciyor ama tarihsiz
# kaldigi icin eleniyordu. Tarih, Google News beslemesindeki pubDate'ten -
# yani yayincinin kendi beyanindan - sorulur. Yalniz BASLIKLA kapiyi gecen
# adaylar sorulur; butce, kosu basina istek sayisini sinirlar.
GNEWS_TARIH_BUTCE = int(os.environ.get("RADAR_GNEWS_TARIH", "40"))
REZERV_GUN = int(os.environ.get("RADAR_REZERV_GUN", "540"))   # ~18 ay

os.environ.setdefault("RADAR_CACHE", CACHE)

for d in (OUT, STATE_DIR, CACHE):
    os.makedirs(d, exist_ok=True)
