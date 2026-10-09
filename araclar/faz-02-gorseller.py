# Faz 2 derslerinin görsellerini src/assets/faz-02/ altına SVG olarak üretir.
# Çalıştırmak için: python3 araclar/faz-02-gorseller.py
import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'assets', 'faz-02')
C = dict(bg='#0f172a', kenar='#1e293b', yazi='#e2e8f0', ok='#94a3b8', soluk='#64748b',
         c='#22d3ee', cpp='#818cf8', baska='#f472b6', io='#34d399', karar='#fbbf24', etiket='#cbd5e1')
FONT = "font-family='ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif'"
MONO = "font-family='ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'"

def svg(w, h, body, aria):
    return f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='{w}' height='{h}' role='img' aria-label='{aria}'>
<defs><marker id='u' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' markerHeight='7' orient='auto-start-reverse'><path d='M0,0 L10,5 L0,10 z' fill='{C['ok']}'/></marker></defs>
<rect width='{w}' height='{h}' rx='16' fill='{C['bg']}' stroke='{C['kenar']}'/>
{body}
</svg>
"""

def yazi(x, y, t, size=14, renk=None, weight=500, mono=False, anchor='middle'):
    return f"<text x='{x}' y='{y}' text-anchor='{anchor}' dominant-baseline='central' {MONO if mono else FONT} font-size='{size}' font-weight='{weight}' fill='{renk or C['yazi']}'>{t}</text>"

def hap(x, y, ust, alt, renk, w=104, h=46):
    return (f"<rect x='{x-w/2}' y='{y-h/2}' width='{w}' height='{h}' rx='10' fill='{renk}22' stroke='{renk}' stroke-width='2'/>"
            + yazi(x, y - 8, ust, size=14, weight=700) + yazi(x, y + 10, alt, size=11, renk=C['etiket']))

def ok(*pts, renk=None, kesik=False):
    p = ' '.join(f'{x},{y}' for x, y in pts)
    d = " stroke-dasharray='5 4'" if kesik else ''
    return f"<polyline points='{p}' fill='none' stroke='{renk or C['ok']}' stroke-width='2' stroke-linejoin='round'{d} marker-end='url(#u)'/>"

def kaydet(ad, s):
    open(os.path.join(OUT, ad), 'w').write(s)

# 1) Soy ağacı
b = []
b.append(yazi(30, 34, 'C ailesi', size=13, renk=C['c'], weight=700, anchor='start'))
cx = [80, 200, 320, 460, 580, 700, 820]; cy = 80
c = [('BCPL', '1967'), ('B', '1969'), ('C', '1972'), ('C89', '1989'), ('C99', '1999'), ('C11', '2011'), ('C23', '2024')]
for i, (ad, yil) in enumerate(c):
    b.append(hap(cx[i], cy, ad, yil, C['c']))
    if i: b.append(ok((cx[i-1] + 52, cy), (cx[i] - 54, cy)))
b.append(yazi(30, 150, 'C++ ailesi', size=13, renk=C['cpp'], weight=700, anchor='start'))
px = [400, 520, 640, 760, 880]; py = 196
p = [('C++', '1983'), ('C++98', '1998'), ('C++11', '2011'), ('C++20', '2020'), ('C++23', '2024')]
for i, (ad, yil) in enumerate(p):
    b.append(hap(px[i], py, ad, yil, C['cpp']))
    if i: b.append(ok((px[i-1] + 52, py), (px[i] - 54, py)))
b.append(ok((cx[2], cy + 23), (cx[2], py), (px[0] - 54, py), renk=C['cpp']))
b.append(yazi(cx[2] + 8, 150, 'C’nin üzerine kuruldu', size=11, renk=C['etiket'], anchor='start'))
# Başka dünya
b.append(f"<rect x='24' y='262' width='912' height='112' rx='12' fill='none' stroke='{C['baska']}' stroke-width='1.5' stroke-dasharray='6 5'/>")
b.append(yazi(40, 284, 'Akraba sanılanlar: sanal makinede çalışır, belleği garbage collector yönetir', size=13, renk=C['baska'], weight=700, anchor='start'))
b.append(hap(120, 330, 'Java', '1995 · Sun', C['baska'], w=120))
b.append(hap(280, 330, 'C#', '2000 · Microsoft', C['baska'], w=130))
b.append(ok((180, 330), (215, 330), renk=C['baska']))
b.append(hap(470, 330, 'JavaScript', '1995 · Netscape', C['baska'], w=140))
b.append(yazi(560, 322, 'C#’taki “C” soydan değil, sözdiziminden gelir.', size=12, renk=C['etiket'], anchor='start'))
b.append(yazi(560, 342, 'JavaScript’in de Java ile ilgisi yoktur; adı pazarlamadan.', size=12, renk=C['etiket'], anchor='start'))
kaydet('soy-agaci.svg', svg(960, 392, '\n'.join(b), 'C, C++ ve C# soy ağacı'))

# 2) Spagetti ve yapısal
b = []
b.append(yazi(200, 34, 'GOTO ile: spagetti', size=15, renk=C['baska'], weight=700))
kut = {1: (110, 90), 2: (290, 90), 3: (110, 180), 4: (290, 180), 5: (110, 270), 6: (290, 270)}
for n, (x, y) in kut.items():
    b.append(f"<rect x='{x-55}' y='{y-20}' width='110' height='40' rx='4' fill='{C['cpp']}22' stroke='{C['cpp']}' stroke-width='2'/>")
    b.append(yazi(x, y, f'{n}0 …', mono=True))
egriler = [((165, 90), (235, 180), (230, 110)), ((235, 170), (165, 270), (190, 230)), ((110, 290), (290, 110), (380, 330)),
           ((290, 290), (110, 160), (20, 260)), ((55, 180), (290, 250), (180, 340)), ((345, 180), (165, 85), (390, 40)),
           ((235, 280), (165, 175), (215, 210))]
for (x1, y1), (x2, y2), (qx, qy) in egriler:
    b.append(f"<path d='M {x1},{y1} Q {qx},{qy} {x2},{y2}' fill='none' stroke='{C['baska']}' stroke-width='1.8' opacity='0.85' marker-end='url(#u)'/>")
b.append(f"<line x1='410' y1='24' x2='410' y2='336' stroke='{C['kenar']}' stroke-width='2'/>")
X = 610
b.append(yazi(X, 34, 'Yapısal: sıra, karar, döngü', size=15, renk=C['io'], weight=700))
b.append(f"<rect x='{X-70}' y='60' width='140' height='34' rx='4' fill='{C['cpp']}22' stroke='{C['cpp']}' stroke-width='2'/>"); b.append(yazi(X, 77, 'sıra'))
b.append(ok((X, 94), (X, 116)))
b.append(f"<polygon points='{X},{118} {X+60},{146} {X},{174} {X-60},{146}' fill='{C['karar']}22' stroke='{C['karar']}' stroke-width='2'/>"); b.append(yazi(X, 146, 'karar'))
b.append(ok((X - 60, 146), (X - 110, 146), (X - 110, 200), (X - 4, 200)))
b.append(ok((X + 60, 146), (X + 110, 146), (X + 110, 200), (X + 4, 200)))
b.append(ok((X, 202), (X, 228)))
b.append(f"<polygon points='{X},{230} {X+60},{258} {X},{286} {X-60},{258}' fill='{C['karar']}22' stroke='{C['karar']}' stroke-width='2'/>"); b.append(yazi(X, 258, 'döngü'))
b.append(ok((X + 60, 258), (X + 150, 258), (X + 150, 320), (X, 320), (X, 288)))
b.append(ok((X - 60, 258), (X - 130, 258), (X - 130, 300)))
b.append(yazi(X - 130, 314, 'çıkış', size=11, renk=C['etiket']))
b.append(yazi(X + 100, 334, 'her blok: tek giriş, tek çıkış', size=11, renk=C['etiket']))
kaydet('spagetti.svg', svg(820, 352, '\n'.join(b), 'Spagetti kod ile yapısal kodun karşılaştırması'))

# 3) Derleme hattı
b = []
dos = ['hello.c', 'hello.i', 'hello.s', 'hello.o', 'hello']
alt = ['kaynak kod', 'genişletilmiş kaynak', 'assembly', 'object file', 'çalıştırılabilir']
ara = [('preprocessor', 'clang -E'), ('compiler', 'clang -S'), ('assembler', 'clang -c'), ('linker', 'clang')]
xs = [80, 290, 500, 710, 920]; y = 70
for i, x in enumerate(xs):
    renk = C['io'] if i in (0, 4) else C['c']
    b.append(f"<rect x='{x-62}' y='{y-22}' width='124' height='44' rx='8' fill='{renk}22' stroke='{renk}' stroke-width='2'/>")
    b.append(yazi(x, y, dos[i], mono=True, weight=700))
    b.append(yazi(x, y + 38, alt[i], size=11, renk=C['etiket']))
    if i < 4:
        b.append(ok((x + 64, y), (xs[i + 1] - 66, y)))
        mx = (x + xs[i + 1]) / 2
        b.append(yazi(mx, y - 34, ara[i][0], size=12, renk=C['etiket'], weight=600))
        b.append(yazi(mx, y + 70, ara[i][1], size=12, renk=C['karar'], mono=True))
kaydet('derleme-hatti.svg', svg(1000, 160, '\n'.join(b), 'Derleme hattı: ön işleme, derleme, assembly, bağlama'))

# ── Ders 2.4: diziler ─────────────────────────────────────────────────────

# 1) Tek boyutlu dizi: yan yana kutular
b = []
degerler = [70, 85, 60, 90, 75]
x0, y, w = 150, 80, 90
b.append(yazi(70, y, 'scores', mono=True, weight=700, renk=C['c']))
for i, v in enumerate(degerler):
    x = x0 + i * w
    b.append(f"<rect x='{x}' y='{y-28}' width='{w}' height='56' fill='{C['c']}22' stroke='{C['c']}' stroke-width='2'/>")
    b.append(yazi(x + w / 2, y, str(v), size=18, weight=700, mono=True))
    b.append(yazi(x + w / 2, y + 48, f'scores[{i}]', size=12, renk=C['karar'], mono=True))
b.append(yazi(x0 + 5 * w / 2, 168, 'indeks 0’dan başlar · son indeks = eleman sayısı − 1', size=12, renk=C['etiket']))
kaydet('dizi.svg', svg(660, 190, '\n'.join(b), 'Beş elemanlı bir dizi: yan yana kutular ve indeksleri'))

# 2) İki boyutlu dizi: ızgara
b = []
satir, sutun, hx, hy, w, h = 3, 4, 130, 70, 92, 50
for c_ in range(sutun):
    b.append(yazi(hx + c_ * w + w / 2, hy - 22, f'sütun {c_}', size=12, renk=C['karar']))
for r in range(satir):
    b.append(yazi(hx - 50, hy + r * h + h / 2, f'satır {r}', size=12, renk=C['karar']))
    for c_ in range(sutun):
        x, y = hx + c_ * w, hy + r * h
        b.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{C['cpp']}22' stroke='{C['cpp']}' stroke-width='2'/>")
        b.append(yazi(x + w / 2, y + h / 2, f'grid[{r}][{c_}]', size=12, mono=True))
b.append(yazi(hx + sutun * w / 2, hy + satir * h + 30, 'önce satır, sonra sütun: grid[satır][sütun]', size=12, renk=C['etiket']))
kaydet('dizi-2b.svg', svg(560, 280, '\n'.join(b), 'Üç satır dört sütunluk iki boyutlu dizi'))

# 3) Oyun döngüsü akış diyagramı
def uc_(x, y, t, w=110, h=38):
    return f"<rect x='{x-w/2}' y='{y-h/2}' width='{w}' height='{h}' rx='{h/2}' fill='{C['c']}22' stroke='{C['c']}' stroke-width='2'/>" + yazi(x, y, t, weight=700)
def islem_(x, y, t, w=200, h=40):
    return f"<rect x='{x-w/2}' y='{y-h/2}' width='{w}' height='{h}' rx='4' fill='{C['cpp']}22' stroke='{C['cpp']}' stroke-width='2'/>" + yazi(x, y, t)
def io_(x, y, t, w=200, h=40, s=14):
    p = f"{x-w/2+s},{y-h/2} {x+w/2+s},{y-h/2} {x+w/2-s},{y+h/2} {x-w/2-s},{y+h/2}"
    return f"<polygon points='{p}' fill='{C['io']}22' stroke='{C['io']}' stroke-width='2'/>" + yazi(x, y, t)
def karar_(x, y, t, w=160, h=76):
    p = f"{x},{y-h/2} {x+w/2},{y} {x},{y+h/2} {x-w/2},{y}"
    return f"<polygon points='{p}' fill='{C['karar']}22' stroke='{C['karar']}' stroke-width='2'/>" + yazi(x, y, t)
def et(x, y, t):
    return yazi(x, y, t, size=12, renk=C['etiket'], weight=600)

X = 270; b = []
b += [uc_(X, 40, 'BAŞLA'), ok((X, 59), (X, 85)),
      islem_(X, 105, 'Haritayı ve oyuncuyu hazırla', w=240), ok((X, 125), (X, 155)),
      islem_(X, 175, 'Haritayı çiz'), ok((X, 195), (X, 225)),
      io_(X, 245, 'Tuş oku', w=150), ok((X, 265), (X, 295)),
      islem_(X, 315, 'Yeni konumu hesapla', w=220), ok((X, 335), (X, 362)),
      karar_(X, 400, 'Duvar mı?'),
      ok((X + 80, 400), (X + 120, 400)), et(X + 100, 388, 'evet'),
      io_(X + 230, 400, 'Yaz: hamle başarısız', w=200),
      ok((X + 230, 380), (X + 230, 175), (X + 102, 175)),
      ok((X, 438), (X, 470)), et(X + 26, 454, 'hayır'),
      islem_(X, 490, 'Oyuncuyu taşı'), ok((X, 510), (X, 537)),
      karar_(X, 575, 'Çıkış mı?'),
      ok((X - 80, 575), (60, 575), (60, 175), (X - 102, 175)), et(X - 104, 563, 'hayır'),
      ok((X, 613), (X, 645)), et(X + 24, 629, 'evet'),
      io_(X, 665, 'Yaz: kazandın', w=170), ok((X, 685), (X, 715)),
      uc_(X, 735, 'BİTİR')]
kaydet('oyun-dongusu.svg', svg(620, 780, '\n'.join(b), 'Labirent oyununun akış diyagramı'))

# ── Ders 2.6: gerçek VS Code ekran görüntüsü + numaralı işaretler ─────────
import base64
KAYNAK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kaynak', 'vscode-hata-ayiklama.png')
veri = base64.b64encode(open(KAYNAK, 'rb').read()).decode()
GW, GH = 2143, 1140
SARI = '#fbbf24'
def bolge(x1, y1, x2, y2, no, bx, by):
    return (f"<rect x='{x1}' y='{y1}' width='{x2-x1}' height='{y2-y1}' rx='10' fill='none' stroke='{SARI}' stroke-width='4'/>"
            f"<circle cx='{bx}' cy='{by}' r='26' fill='{SARI}' stroke='#0f172a' stroke-width='3'/>"
            + yazi(bx, by + 1, str(no), size=28, renk='#0f172a', weight=800))
b = [f"<image href='data:image/png;base64,{veri}' x='0' y='0' width='{GW}' height='{GH}'/>"]
b.append(bolge(160, 352, 960, 484, 1, 136, 418))            # VARIABLES
b.append(bolge(1330, 204, 1722, 266, 2, 1752, 235))         # Düğmeler
b.append(bolge(1098, 455, 2000, 492, 3, 1970, 430))         # Durulan satır
b.append(bolge(966, 452, 1012, 496, 4, 989, 535))           # Kesme noktası
b.append(bolge(160, 630, 960, 806, 5, 136, 718))            # CALL STACK
b.append(bolge(160, 828, 960, 996, 6, 136, 912))            # BREAKPOINTS
# Kenarlardaki mor arka planı kırp: pencere ve numaralar kalsın
KX, KY, KW, KH = 100, 118, 1925, 900
kaydet('vscode-hata-ayiklama.svg', f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='{KX} {KY} {KW} {KH}' width='{KW}' height='{KH}' role='img' aria-label='VS Code hata ayıklama ekranı, numaralı açıklamalarla'>\n" + '\n'.join(b) + "\n</svg>\n")

# ── Ders 2.7: çağrı yığını, adım adım ──────────────────────────────────────
anlar = [
    ('1. main başladı', [('main', ['answer = ?'])]),
    ('2. sum_of_squares(3, 4)', [('main', ['answer = ?']), ('sum_of_squares', ['a = 3', 'b = 4', 'first = ?', 'second = ?'])]),
    ('3. square(3)', [('main', ['answer = ?']), ('sum_of_squares', ['a = 3', 'b = 4', 'first = ?', 'second = ?']), ('square', ['x = 3', 'result = 9'])]),
    ('4. square bitti', [('main', ['answer = ?']), ('sum_of_squares', ['a = 3', 'b = 4', 'first = 9', 'second = ?'])]),
    ('5. square(4)', [('main', ['answer = ?']), ('sum_of_squares', ['a = 3', 'b = 4', 'first = 9', 'second = ?']), ('square', ['x = 4', 'result = 16'])]),
    ('6. answer = 25', [('main', ['answer = 25'])]),
]
renk_f = {'main': C['io'], 'sum_of_squares': C['cpp'], 'square': C['c']}
CW, GAP, TABAN = 150, 14, 320
b = []
for k, (baslik, kutular) in enumerate(anlar):
    x = 20 + k * (CW + GAP)
    y = TABAN
    for ad, satirlar in kutular:
        h = 30 + 20 * len(satirlar)
        y -= h
        renk = renk_f[ad]
        b.append(f"<rect x='{x}' y='{y}' width='{CW}' height='{h-6}' rx='6' fill='{renk}22' stroke='{renk}' stroke-width='2'/>")
        b.append(yazi(x + CW/2, y + 14, ad, size=12, weight=700, mono=True, renk=renk))
        for j, s_ in enumerate(satirlar):
            b.append(yazi(x + CW/2, y + 34 + j*20, s_, size=12, mono=True))
    b.append(f"<line x1='{x}' y1='{TABAN+4}' x2='{x+CW}' y2='{TABAN+4}' stroke='{C['ok']}' stroke-width='2'/>")
    b.append(yazi(x + CW/2, TABAN + 24, baslik, size=12, renk=C['karar'], weight=600))
b.append(yazi(20, 24, 'stack’in tepesi = şu an çalışan fonksiyon ↑', size=12, renk=C['etiket'], anchor='start'))
kaydet('cagri-yigini.svg', svg(20 + 6*(CW+GAP) + 6, TABAN + 44, '\n'.join(b), 'stack.c çalışırken çağrı yığınının altı anı'))

# ── Ders 2.8: özyineleme ──────────────────────────────────────────────────

# 1) factorial(4): iniş ve çıkış
b = []
seviyeler = [('main', None), ('factorial(4)', 24), ('factorial(3)', 6), ('factorial(2)', 2), ('factorial(1)', 1), ('factorial(0)', 1)]
x, w, h, y0 = 240, 200, 40, 330
for i, (ad, donus) in enumerate(seviyeler):
    y = y0 - i * (h + 8)
    renk = C['io'] if i == 0 else (C['karar'] if i == 5 else C['c'])
    b.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='6' fill='{renk}22' stroke='{renk}' stroke-width='2'/>")
    b.append(yazi(x + w/2, y + h/2, ad, size=14, weight=700, mono=True))
    if 1 <= i <= 4:
        b.append(yazi(x - 20, y + h/2, f'{5-i} × factorial({4-i})', size=12, renk=C['etiket'], mono=True, anchor='end'))
    if donus is not None:
        b.append(f"<path d='M {x+w+10},{y+h/2} C {x+w+70},{y+h/2} {x+w+70},{y+h/2+48} {x+w+10},{y+h/2+48}' fill='none' stroke='{C['io']}' stroke-width='2' marker-end='url(#u)'/>")
        b.append(yazi(x + w + 78, y + h/2 + 24, f'{donus} döndürür', size=12, renk=C['io'], weight=600, anchor='start'))
b.append(yazi(x + w/2, y0 - 5*(h+8) - 22, 'base case: n == 0', size=12, renk=C['karar'], weight=700))
b.append(f"<line x1='40' y1='{y0+h-4}' x2='40' y2='{y0-5*(h+8)+10}' stroke='{C['c']}' stroke-width='2' marker-end='url(#u)'/>")
b.append(yazi(40, y0 - 5*(h+8) - 6, 'iniş', size=13, renk=C['c'], weight=700))
b.append(yazi(x + w + 120, y0 - 5*(h+8) - 6, 'çıkış ↓', size=13, renk=C['io'], weight=700))
kaydet('faktoriyel-yigini.svg', svg(700, 390, '\n'.join(b), 'factorial(4) çağrısında yığının inişi ve dönüş değerleriyle çıkışı'))

# 2) fib(5) çağrı ağacı
b = []
dugum = {}
def nd(ad, x, y, n):
    renk = C['karar'] if n == 3 else (C['cpp'] if n == 2 else C['c'])
    dugum[ad] = (x, y)
    return f"<rect x='{x-44}' y='{y-17}' width='88' height='34' rx='17' fill='{renk}22' stroke='{renk}' stroke-width='2'/>" + yazi(x, y, f'fib({n})', size=13, weight=700, mono=True)
agac = [('a', 480, 50, 5),
        ('b', 260, 130, 4), ('c', 700, 130, 3),
        ('d', 150, 210, 3), ('e', 370, 210, 2), ('f', 620, 210, 2), ('g', 780, 210, 1),
        ('h', 90, 290, 2), ('i', 210, 290, 1)]
kenar = [('a','b'),('a','c'),('b','d'),('b','e'),('c','f'),('c','g'),('d','h'),('d','i')]
for ad, x, y, n in agac:
    dugum[ad] = (x, y)
for u, v in kenar:
    (x1, y1), (x2, y2) = dugum[u], dugum[v]
    b.append(f"<line x1='{x1}' y1='{y1+17}' x2='{x2}' y2='{y2-17}' stroke='{C['ok']}' stroke-width='2'/>")
for ad, x, y, n in agac:
    b.append(nd(ad, x, y, n))
b.append(yazi(480, 345, '9 çağrı · fib(3) iki kez, fib(2) üç kez baştan hesaplanıyor', size=13, renk=C['etiket'], weight=600))
kaydet('fib-agaci.svg', svg(900, 370, '\n'.join(b), 'fib(5) çağrı ağacı'))

# ── Ders 2.10: ikili arama ile karekök (n = 50) ────────────────────────────
adimlar = [(0, 26, 13, False), (0, 12, 6, True), (6, 12, 9, False), (6, 8, 7, True), (7, 8, 8, False)]
X0, X1, MAXV = 150, 860, 26
def px(v):
    return X0 + (X1 - X0) * v / MAXV
b = []
for i, (lo, hi, mid, ok) in enumerate(adimlar):
    y = 50 + i * 56
    b.append(yazi(30, y, f'{i+1}. adım', size=12, renk=C['etiket'], anchor='start', weight=600))
    b.append(f"<line x1='{X0}' y1='{y}' x2='{X1}' y2='{y}' stroke='{C['kenar']}' stroke-width='2'/>")
    b.append(f"<rect x='{px(lo)-4}' y='{y-9}' width='{px(hi)-px(lo)+8}' height='18' rx='9' fill='{C['c']}33' stroke='{C['c']}' stroke-width='2'/>")
    renk = C['io'] if ok else '#f87171'
    b.append(f"<circle cx='{px(mid)}' cy='{y}' r='7' fill='{renk}'/>")
    b.append(yazi(px(mid), y - 22, f'mid = {mid}', size=12, renk=renk, weight=700, mono=True))
    b.append(yazi(X1 + 14, y, f"{mid}² = {mid*mid} {'≤' if ok else '>'} 50", size=12, renk=renk, mono=True, anchor='start'))
    b.append(yazi(px(lo), y + 22, str(lo), size=11, renk=C['etiket'], mono=True))
    b.append(yazi(px(hi), y + 22, str(hi), size=11, renk=C['etiket'], mono=True))
b.append(yazi((X0 + X1) / 2, 50 + 5 * 56 + 4, 'aralık 7–7\'ye daraldı: ⌊√50⌋ = 7', size=13, renk=C['karar'], weight=700))
kaydet('ikili-arama.svg', svg(1040, 50 + 5 * 56 + 30, '\n'.join(b), 'n = 50 için ikili aramayla karekök: her adımda aralık yarıya iniyor'))
print('tamam', sorted(os.listdir(OUT)))
