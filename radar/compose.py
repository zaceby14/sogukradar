# -*- coding: utf-8 -*-
"""Deterministik Turkce metin uretici.

Mail Pazartesi 07:05'te otomatik gider; o saatte yapay zeka oturumu henuz
calismamis olabilir. Bu modul, YALNIZCA dogrulanmis alanlardan (tarih, firma,
ulke, hat, asama) kurallı Turkce cumleler kurar - ozgur metin uretmez,
dolayisiyla uydurma riski sifirdir. Yapay zeka oturumu daha iyi bir ozet
yazarsa (ozet.json), o metin bununkinin yerine gecer.
"""

STAGE_PHRASE = {
    "Ilk urun": "%s, %s tesisinde ilk uretimi gerceklestirdi",
    "Insaat": "%s, %s insaatina basladi",
    "Test": "%s, %s hattinda test uretimine gecti",
    "Seri uretim": "%s, %s hattinda tam kapasiteye ulasti",
    "Teknoloji": "%s, %s alaninda yeni teknoloji duyurdu",
}


def _top_countries(rows, n=3):
    d = {}
    for r in rows:
        c = r.get("ulke") or ""
        if c:
            d[c] = d.get(c, 0) + 1
    return sorted(d.items(), key=lambda kv: -kv[1])[:n]


def _top(rows, key, n=2):
    d = {}
    for r in rows:
        v = r.get(key) or ""
        if v and v != "Belirsiz":
            d[v] = d.get(v, 0) + 1
    return sorted(d.items(), key=lambda kv: -kv[1])[:n]


def row_sentence(r):
    firma = r.get("firma") or r.get("kaynak") or "Ilgili uretici"
    hat = (r.get("hat") or "hat").lower()
    asama = r.get("asama") or "Belirsiz"
    ted = r.get("tedarikci") or ""
    if asama == "Sozlesme":
        s = ("%s, %s yatirimini %s'e siparis etti" % (firma, hat, ted)) if ted \
            else "%s, %s icin siparis verdi" % (firma, hat)
    elif asama == "Modernizasyon":
        s = ("%s, %s yenileme isini %s'e verdi" % (firma, hat, ted)) if ted \
            else "%s, %s yenileme isini baslatti" % (firma, hat)
    elif asama in STAGE_PHRASE:
        s = STAGE_PHRASE[asama] % (firma, hat)
    else:
        s = "%s: %s" % (firma, r.get("baslik", ""))
    if r.get("tutar"):
        s += " (%s)" % r["tutar"]
    return s + "."


def exec_summary(rows, stats):
    """Kurallı 'AI Ozeti' paragrafi - sadece dogrulanmis alanlardan."""
    n = len(rows)
    if n == 0:
        er = stats.get("erisilemeyen", 0)
        return ("Bu hafta tarih dogrulamasindan gecen gelisme kaydedilmedi. "
                "%d kaynak tarandi, %d kaynaga erisilemedi; sifir sonuc cogu zaman "
                "sektorel durgunluk degil erisim sorunudur, detay kapsam tablosundadir."
                % (stats.get("kaynak", 0), er))
    parts = []
    cs = _top_countries(rows)
    if cs:
        if len(cs) == 1:
            parts.append("Bu haftanin %d dogrulanmis gelismesinin tamami %s kaynakli."
                         % (n, cs[0][0]))
        else:
            lead = cs[0]
            rest = ", ".join(c for c, _ in cs[1:])
            parts.append("Bu hafta %d dogrulanmis gelisme kaydedildi; %s %d gelismeyle "
                         "one cikarken %s takip ediyor." % (n, lead[0], lead[1], rest))
    hl = _top(rows, "hat", 2)
    if hl:
        parts.append("Hat tarafinda agirlik %s." % " ve ".join(h.lower() for h, _ in hl))
    st = _top(rows, "asama", 2)
    if st:
        parts.append("Asama dagiliminda %s onde." %
                     " ve ".join(("%s (%d)" % (a.lower(), k)) for a, k in st))
    tr = [r for r in rows if r.get("ulke") == "Turkiye" or "tosyali" in
          (r.get("firma") or "").lower()]
    if tr:
        parts.append("Turkiye baglantili gelisme: " + row_sentence(tr[0]))
    top = rows[0]
    if not tr or top is not tr[0]:
        parts.append("Haftanin one cikan olayi: " + row_sentence(top))
    return " ".join(parts)


def tech_blurb(t):
    """Teknoloji adayi icin kurallı tanitim cumlesi."""
    hat = t.get("hat") or ""
    s = t["baslik"]
    if hat and hat != "Belirsiz":
        return "%s alaninda: %s (%s, %s)." % (hat, s, t.get("kaynak", ""), t.get("tarih", ""))
    return "%s (%s, %s)." % (s, t.get("kaynak", ""), t.get("tarih", ""))
