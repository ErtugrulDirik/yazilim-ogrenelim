# Faz 1 derslerinin akış diyagramlarını src/assets/faz-01/ altına SVG olarak üretir.
# Çalıştırmak için: python3 araclar/akis-diyagramlari.py
import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'assets', 'faz-01')
C = dict(bg='#0f172a', kenar='#1e293b', yazi='#e2e8f0', ok='#94a3b8',
         uc='#22d3ee', islem='#818cf8', io='#34d399', karar='#fbbf24', etiket='#cbd5e1')
FONT = "font-family='ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif'"

def svg(w, h, body, aria):
    return f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='{w}' height='{h}' role='img' aria-label='{aria}'>
<defs><marker id='u' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' markerHeight='7' orient='auto-start-reverse'><path d='M0,0 L10,5 L0,10 z' fill='{C['ok']}'/></marker></defs>
<rect width='{w}' height='{h}' rx='16' fill='{C['bg']}' stroke='{C['kenar']}'/>
{body}
</svg>
"""

def yazi(x, y, t, size=14, renk=None, weight=500):
    return f"<text x='{x}' y='{y}' text-anchor='middle' dominant-baseline='central' {FONT} font-size='{size}' font-weight='{weight}' fill='{renk or C['yazi']}'>{t}</text>"

def dolgu(r):  # yarı saydam dolgu
    return r + '22'

def uc(x, y, t, w=110, h=38):
    return f"<rect x='{x-w/2}' y='{y-h/2}' width='{w}' height='{h}' rx='{h/2}' fill='{dolgu(C['uc'])}' stroke='{C['uc']}' stroke-width='2'/>" + yazi(x, y, t, weight=700)

def islem(x, y, t, w=180, h=40):
    return f"<rect x='{x-w/2}' y='{y-h/2}' width='{w}' height='{h}' rx='4' fill='{dolgu(C['islem'])}' stroke='{C['islem']}' stroke-width='2'/>" + yazi(x, y, t)

def io(x, y, t, w=170, h=40, s=14):
    p = f"{x-w/2+s},{y-h/2} {x+w/2+s},{y-h/2} {x+w/2-s},{y+h/2} {x-w/2-s},{y+h/2}"
    return f"<polygon points='{p}' fill='{dolgu(C['io'])}' stroke='{C['io']}' stroke-width='2'/>" + yazi(x, y, t)

def karar(x, y, t, w=150, h=76):
    p = f"{x},{y-h/2} {x+w/2},{y} {x},{y+h/2} {x-w/2},{y}"
    return f"<polygon points='{p}' fill='{dolgu(C['karar'])}' stroke='{C['karar']}' stroke-width='2'/>" + yazi(x, y, t)

def ok(*pts, bas=True):
    p = ' '.join(f'{x},{y}' for x, y in pts)
    m = " marker-end='url(#u)'" if bas else ''
    return f"<polyline points='{p}' fill='none' stroke='{C['ok']}' stroke-width='2' stroke-linejoin='round'{m}/>"

def etiket(x, y, t):
    return yazi(x, y, t, size=12, renk=C['etiket'], weight=600)

def kaydet(ad, s):
    open(os.path.join(OUT, ad), 'w').write(s)

# 1) Semboller
b = []
b.append(uc(90, 70, 'BAŞLA')); b.append(etiket(90, 125, 'Başla / Bitir'))
b.append(islem(245, 70, 'x ← x + 1', w=140)); b.append(etiket(245, 125, 'İşlem'))
b.append(io(410, 70, 'Oku: x', w=130)); b.append(etiket(410, 125, 'Girdi / Çıktı'))
b.append(karar(570, 70, 'x &gt; 0?', w=130, h=70)); b.append(etiket(570, 125, 'Karar'))
b.append(ok((680, 70), (750, 70))); b.append(etiket(715, 125, 'Akış oku'))
kaydet('semboller.svg', svg(790, 160, '\n'.join(b), 'Akış diyagramı sembolleri'))

# 2) Vücut kitle indeksi: sıralı akış
x = 200; b = []
b += [uc(x, 40, 'BAŞLA'), ok((x, 59), (x, 88)),
      io(x, 110, 'Oku: kilo, boy'), ok((x, 130), (x, 158)),
      islem(x, 180, 'vki ← kilo / (boy × boy)', w=230), ok((x, 200), (x, 228)),
      io(x, 250, 'Yaz: vki', w=140), ok((x, 270), (x, 299)),
      uc(x, 320, 'BİTİR')]
kaydet('vki-hesap.svg', svg(400, 360, '\n'.join(b), 'Vücut kitle indeksi hesabının akış diyagramı'))

# 3) Vücut kitle indeksi: karar zinciri
x, r, bus = 190, 420, 545; b = []
b += [uc(x, 40, 'BAŞLA'), ok((x, 59), (x, 88)),
      io(x, 110, 'Oku: kilo, boy'), ok((x, 130), (x, 158)),
      islem(x, 180, 'vki ← kilo / (boy × boy)', w=230), ok((x, 200), (x, 222))]
ys = [260, 370, 480]
kosul = ['vki &lt; 18,5?', 'vki &lt; 25?', 'vki &lt; 30?']
grup = ['Yaz: zayıf', 'Yaz: normal', 'Yaz: fazla kilolu']
for i, y in enumerate(ys):
    b.append(karar(x, y, kosul[i], w=160))
    b.append(ok((x + 80, y), (r - 85 - 14, y))); b.append(etiket(x + 105, y - 12, 'evet'))
    b.append(io(r, y, grup[i], w=170))
    b.append(ok((r + 85 + 14 - 7, y), (bus, y), bas=False))
    if i < 2:
        b.append(ok((x, y + 38), (x, ys[i + 1] - 38))); b.append(etiket(x - 26, y + 55, 'hayır'))
b.append(ok((x, ys[2] + 38), (x, 568))); b.append(etiket(x - 26, ys[2] + 55, 'hayır'))
b.append(io(x, 590, 'Yaz: obez', w=150)); b.append(ok((x, 610), (x, 649)))
b.append(ok((bus, ys[0]), (bus, 670), (x + 55, 670)))
b.append(uc(x, 670, 'BİTİR'))
kaydet('vki-grup.svg', svg(590, 710, '\n'.join(b), 'Vücut kitle indeksi grubunu bulan akış diyagramı'))

# 4-6) "OLDUĞU SÜRECE" döngüsü şablonu
def surece(ad, aria, girdi, baslat, kosul, govde, cikti):
    x, r = 200, 390; b = []; y = 40
    b.append(uc(x, y, 'BAŞLA'))
    adimlar = []
    if girdi: adimlar.append(('io', girdi))
    adimlar += [('islem', t) for t in baslat]
    for tur, t in adimlar:
        b.append(ok((x, y + 20), (x, y + 45))); y += 65
        b.append(io(x, y, t) if tur == 'io' else islem(x, y, t))
    b.append(ok((x, y + 20), (x, y + 55))); y += 93; ky = y
    b.append(karar(x, ky, kosul))
    for t in govde:
        b.append(ok((x, y + (38 if y == ky else 20)), (x, y + (38 if y == ky else 20) + 30)))
        b.append(etiket(x + 24, ky + 52, 'evet')) if y == ky else None
        y += (88 if y == ky else 65)
        b.append(islem(x, y, t))
    alt = y + 20
    b.append(ok((x, alt), (x, alt + 25), (55, alt + 25), (55, ky), (x - 75, ky)))
    b.append(ok((x + 75, ky), (r, ky), (r, ky + 70))); b.append(etiket(x + 105, ky - 12, 'hayır'))
    b.append(io(r, ky + 90, cikti, w=130)); b.append(ok((r, ky + 110), (r, ky + 151)))
    b.append(uc(r, ky + 170, 'BİTİR'))
    h = max(alt + 55, ky + 210)
    kaydet(ad, svg(480, h, '\n'.join(b), aria))

surece('toplam.svg', '1den n e kadar toplam akış diyagramı', 'Oku: n', ['s ← 0', 'i ← 1'],
       'i ≤ n?', ['s ← s + i', 'i ← i + 1'], 'Yaz: s')
surece('faktoriyel.svg', 'Faktöriyel akış diyagramı', 'Oku: n', ['f ← 1', 'i ← 1'],
       'i ≤ n?', ['f ← f × i', 'i ← i + 1'], 'Yaz: f')
surece('gizem.svg', 'Gizemli akış diyagramı', None, ['x ← 1'],
       'x &lt; 50?', ['x ← x × 3'], 'Yaz: x')

# 7) "TEKRARLA … OLANA KADAR": basamak sayısı
x = 210; b = []
b += [uc(x, 40, 'BAŞLA'), ok((x, 59), (x, 85)),
      io(x, 105, 'Oku: n', w=130), ok((x, 125), (x, 150)),
      islem(x, 170, 'sayaç ← 0'), ok((x, 190), (x, 218)),
      islem(x, 240, 'n ← n ÷ 10'), ok((x, 260), (x, 283)),
      islem(x, 305, 'sayaç ← sayaç + 1', w=190), ok((x, 325), (x, 352)),
      karar(x, 390, 'n = 0?'),
      ok((x - 75, 390), (50, 390), (50, 240), (x - 90, 240)), etiket(x - 105, 378, 'hayır'),
      ok((x, 428), (x, 470)), etiket(x + 24, 446, 'evet'),
      io(x, 490, 'Yaz: sayaç', w=150), ok((x, 510), (x, 541)),
      uc(x, 560, 'BİTİR')]
kaydet('basamak.svg', svg(420, 600, '\n'.join(b), 'Basamak sayısı akış diyagramı'))

# ── Ders 1.3 ──────────────────────────────────────────────────────────────

surece('oklid.svg', 'Öklid algoritmasının akış diyagramı', 'Oku: a, b', [],
       'b ≠ 0?', ['r ← a mod b', 'a ← b', 'b ← r'], 'Yaz: a')
surece('hatali.svg', 'Hatalı döngünün akış diyagramı', None, ['s ← 0', 'i ← 0'],
       'i ≠ 10?', ['s ← s + i', 'i ← i + 3'], 'Yaz: s')
surece('basamak-toplami.svg', 'Basamak toplamı akış diyagramı', 'Oku: n', ['t ← 0'],
       'n &gt; 0?', ['t ← t + n mod 10', 'n ← n ÷ 10'], 'Yaz: t')

# Asal sayı: döngünün içinde ikinci bir karar ve erken çıkış
x, r1, r2 = 200, 420, 600; b = []
b += [uc(x, 40, 'BAŞLA'), ok((x, 59), (x, 85)),
      io(x, 105, 'Oku: n', w=130), ok((x, 125), (x, 150)),
      islem(x, 170, 'd ← 2', w=130), ok((x, 190), (x, 224)),
      karar(x, 262, 'd × d ≤ n?', w=160),
      ok((x, 300), (x, 334)), etiket(x + 24, 316, 'evet'),
      karar(x, 372, 'n mod d = 0?', w=170),
      ok((x, 410), (x, 444)), etiket(x + 28, 426, 'hayır'),
      islem(x, 464, 'd ← d + 1', w=130),
      ok((x, 484), (x, 510), (55, 510), (55, 262), (x - 80, 262)),
      ok((x + 85, 372), (r1 - 80 - 14, 372)), etiket(x + 112, 360, 'evet'),
      io(r1, 372, 'Yaz: asal değil', w=160), ok((r1, 392), (r1, 541)),
      ok((x + 80, 262), (r2, 262), (r2, 300)), etiket(x + 108, 250, 'hayır'),
      io(r2, 320, 'Yaz: asal', w=120), ok((r2, 340), (r2, 560), (r1 + 55, 560)),
      uc(r1, 560, 'BİTİR')]
kaydet('asal.svg', svg(700, 600, '\n'.join(b), 'Asal sayı testinin akış diyagramı'))

# Turnike durum diyagramı
def durum(cx, cy, ad, r=52):
    return (f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='{dolgu(C['islem'])}' stroke='{C['islem']}' stroke-width='2'/>"
            + yazi(cx, cy, ad, size=15, weight=700))

k, a, y = 190, 450, 140; b = []
b += [durum(k, y, 'Kilitli'), durum(a, y, 'Açık'),
      ok((k, 30), (k, y - 54)), etiket(k + 32, 42, 'başlangıç'),
      f"<path d='M {k+40},{y-34} Q {(k+a)/2},{y-110} {a-40},{y-34}' fill='none' stroke='{C['uc']}' stroke-width='2' marker-end='url(#u)'/>",
      etiket((k + a) / 2, y - 86, 'jeton'),
      f"<path d='M {a-40},{y+34} Q {(k+a)/2},{y+110} {k+40},{y+34}' fill='none' stroke='{C['karar']}' stroke-width='2' marker-end='url(#u)'/>",
      etiket((k + a) / 2, y + 86, 'it'),
      f"<path d='M {k-37},{y-37} C {k-140},{y-90} {k-140},{y+90} {k-37},{y+37}' fill='none' stroke='{C['karar']}' stroke-width='2' marker-end='url(#u)'/>",
      etiket(k - 140, y, 'it'),
      f"<path d='M {a+37},{y-37} C {a+140},{y-90} {a+140},{y+90} {a+37},{y+37}' fill='none' stroke='{C['uc']}' stroke-width='2' marker-end='url(#u)'/>",
      etiket(a + 150, y, 'jeton')]
kaydet('turnike.svg', svg(640, 280, '\n'.join(b), 'Turnike durum diyagramı'))

print('tamam', sorted(os.listdir(OUT)))
