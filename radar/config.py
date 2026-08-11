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
TARGET_ROWS = int(os.environ.get("RADAR_TARGET_ROWS", "20"))
MIN_ROWS = int(os.environ.get("RADAR_MIN_ROWS", "5"))

# Kaynak basina liste sayfasindan alinacak azami baglanti
MAX_LINKS_PER_SOURCE = int(os.environ.get("RADAR_MAX_LINKS", "120"))
# Kapsam on elemesini gecip makale sayfasi acilacak azami aday (maliyet freni)
MAX_ARTICLE_FETCH = int(os.environ.get("RADAR_MAX_ARTICLES", "220"))

os.environ.setdefault("RADAR_CACHE", CACHE)

for d in (OUT, STATE_DIR, CACHE):
    os.makedirs(d, exist_ok=True)
