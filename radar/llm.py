# -*- coding: utf-8 -*-
"""LLM ISTEMCISI - sadece standart kutuphane, tum saglayicilar ISTEGE BAGLI.

NEDEN VAR (2026-11-02, kullanici talebi: "Claude Pro'ya bagli kalmadan").
Editor adimi Claude Code rutinine bagliydi; rutinler 21-23 Eylul'den beri
hic atesllenmedi ve bulten 5 haftadir gitmedi. Editorun yaptigi isi
(Turkce cumle, ozet, kapsam suzgeci) Actions icinde, ucretsiz ya da ucuz bir
API ile yapabilmek icin bu modul var.

SAGLAYICILAR (kimlik bilgisi varsa, bu SIRAYLA denenir):
  anthropic  ANTHROPIC_API_KEY   ucretli (token basina; haftalik bulten ~birkac
                                  sent). Claude Pro aboneligi API KREDISI
                                  ICERMEZ - console.anthropic.com ayri.
  gemini     GEMINI_API_KEY      Google AI Studio'dan UCRETSIZ anahtar.
  github     GITHUB_TOKEN        GitHub Models: ANAHTARSIZ, Actions'ta hazir
                                  token ile (is akisinda `models: read` izni
                                  gerekir). Ucretsiz, hiz sinirli.

HICBIRI YOKSA ya da hepsi basarisizsa sistem KURALSAL yola duser (yazar.py);
bulten yine uretilir. LLM yalnizca metni IYILESTIRIR, sistemin calismasi ona
bagli degildir.

DURUSTLUK NOTU: bu modulun HTTP cagrilari gelistirme oturumundan
DENENEMEZ (oturumun ag cikisi yalnizca paket depolari ve GitHub'a acik).
Saglayicilar `python -m radar llm-test` ile ACTIONS'ta denenir; sonuc
is akisi ozetinde gorunur. Test, ag cagrisini sahte yanitlarla dogrular.
"""
import json
import os
import re
import urllib.error
import urllib.request

TIMEOUT = int(os.environ.get("RADAR_LLM_TIMEOUT", "90"))

ANTHROPIC_MODEL = os.environ.get("RADAR_ANTHROPIC_MODEL", "claude-haiku-5-5")
GEMINI_MODELLER = ([os.environ["RADAR_GEMINI_MODEL"]]
                   if os.environ.get("RADAR_GEMINI_MODEL")
                   else ["gemini-2.5-flash", "gemini-2.0-flash"])
GITHUB_MODEL = os.environ.get("RADAR_GITHUB_MODEL", "openai/gpt-4o-mini")


def saglayicilar():
    """Mevcut kimlik bilgilerine gore ONCELIK sirali saglayici adlari."""
    zorla = (os.environ.get("RADAR_LLM") or "").strip().lower()
    if zorla in ("yok", "kapali", "0", "none"):
        return []
    tum = []
    if os.environ.get("ANTHROPIC_API_KEY"):
        tum.append("anthropic")
    if os.environ.get("GEMINI_API_KEY"):
        tum.append("gemini")
    if os.environ.get("GITHUB_TOKEN") and os.environ.get("RADAR_GITHUB_MODELS", "1") != "0":
        tum.append("github")
    if zorla in ("anthropic", "gemini", "github"):
        return [zorla] if zorla in tum else []
    return tum


def _post(url, basliklar, govde):
    """(durum, metin). Ag hatasi durum=0 ile doner, istisna firlatmaz."""
    veri = json.dumps(govde).encode("utf-8")
    istek = urllib.request.Request(url, data=veri, method="POST",
                                   headers=dict(basliklar,
                                                **{"Content-Type": "application/json"}))
    try:
        with urllib.request.urlopen(istek, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            ek = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            ek = ""
        return e.code, ek
    except Exception as e:                              # ag/zaman asimi/TLS
        return 0, "%s: %s" % (type(e).__name__, str(e)[:160])


def _anthropic(sistem, kullanici):
    d, m = _post("https://api.anthropic.com/v1/messages",
                 {"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                  "anthropic-version": "2023-06-01"},
                 {"model": ANTHROPIC_MODEL, "max_tokens": 4096, "temperature": 0.2,
                  "system": sistem,
                  "messages": [{"role": "user", "content": kullanici}]})
    if d != 200:
        return None, "anthropic HTTP %s %s" % (d, m[:120])
    try:
        j = json.loads(m)
        return "".join(b.get("text", "") for b in j["content"]), None
    except Exception as e:
        return None, "anthropic yanit okunamadi: %s | govde: %r" % (e, m[:160])


def _gemini(sistem, kullanici):
    hatalar = []
    for model in GEMINI_MODELLER:
        d, m = _post(
            "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s"
            % (model, os.environ["GEMINI_API_KEY"]), {},
            {"systemInstruction": {"parts": [{"text": sistem}]},
             "contents": [{"role": "user", "parts": [{"text": kullanici}]}],
             "generationConfig": {"temperature": 0.2,
                                  "responseMimeType": "application/json"}})
        if d == 200:
            try:
                j = json.loads(m)
                return "".join(p.get("text", "")
                               for p in j["candidates"][0]["content"]["parts"]), None
            except Exception as e:
                hatalar.append("%s yanit okunamadi: %s | govde: %r" % (model, e, m[:160]))
                continue
        hatalar.append("%s HTTP %s %s" % (model, d, m[:100]))
        if d in (401, 403, 429):         # anahtar/kota sorunu: baska model yardim etmez
            break
    return None, "gemini " + " | ".join(hatalar)


def _github(sistem, kullanici):
    d, m = _post("https://models.github.ai/inference/chat/completions",
                 {"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                  "Accept": "application/vnd.github+json",
                  "X-GitHub-Api-Version": "2022-11-28"},
                 {"model": GITHUB_MODEL, "temperature": 0.2,
                  "messages": [{"role": "system", "content": sistem},
                               {"role": "user", "content": kullanici}]})
    if d != 200:
        return None, "github HTTP %s %s" % (d, m[:120])
    try:
        return json.loads(m)["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, "github yanit okunamadi: %s | govde: %r" % (e, m[:200])


_CAGRI = {"anthropic": _anthropic, "gemini": _gemini, "github": _github}


def json_ayikla(metin):
    """Model yanitindan ilk JSON nesnesini cikarir (kod citlerini atar)."""
    if not metin:
        return None
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", metin.strip(), flags=re.I)
    try:
        return json.loads(t)
    except Exception:
        pass
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        try:
            return json.loads(t[i:j + 1])
        except Exception:
            return None
    return None


def json_iste(sistem, kullanici, log=print):
    """(dict | None, saglayici | None, hatalar[]) - saglayicilari sirayla dener."""
    hatalar = []
    for ad in saglayicilar():
        ham, hata = _CAGRI[ad](sistem, kullanici)
        if hata:
            hatalar.append(hata)
            log("    LLM %s basarisiz: %s" % (ad, hata))
            continue
        veri = json_ayikla(ham)
        if isinstance(veri, dict):
            return veri, ad, hatalar
        hatalar.append("%s: yanit JSON degil" % ad)
        log("    LLM %s: yanit JSON degil" % ad)
    return None, None, hatalar


def baglanti_testi(log=print):
    """Her saglayiciyi KISA bir istekle dener. {ad: 'tamam' | hata}."""
    sonuc = {}
    for ad in saglayicilar():
        ham, hata = _CAGRI[ad]("Yalnizca JSON dondur.",
                               'Su JSON nesnesini aynen dondur: {"durum": "tamam"}')
        sonuc[ad] = hata or ("tamam" if "tamam" in (ham or "") else "yanit beklenmedik: %r" % (ham or "")[:60])
        log("  %-10s %s" % (ad, sonuc[ad]))
    if not sonuc:
        log("  (kimlik bilgisi tanimli degil - kuralsal yola dusulecek)")
    return sonuc
