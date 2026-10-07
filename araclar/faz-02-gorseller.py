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
b.append(yazi(40, 284, 'Akraba sanılanlar: sanal makinede çalışır, belleği çöp toplayıcı yönetir', size=13, renk=C['baska'], weight=700, anchor='start'))
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
dos = ['merhaba.c', 'merhaba.i', 'merhaba.s', 'merhaba.o', 'merhaba']
alt = ['kaynak kod', 'genişletilmiş kaynak', 'assembly', 'nesne dosyası', 'çalıştırılabilir']
ara = [('ön işlemci', 'gcc -E'), ('derleyici', 'gcc -S'), ('assembler', 'gcc -c'), ('bağlayıcı', 'gcc')]
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
print('tamam', sorted(os.listdir(OUT)))
