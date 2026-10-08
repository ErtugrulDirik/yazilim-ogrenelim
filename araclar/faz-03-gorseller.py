# Faz 3 derslerinin görsellerini src/assets/faz-03/ altına SVG olarak üretir.
# Çalıştırmak için: python3 araclar/faz-03-gorseller.py
import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'assets', 'faz-03')
C = dict(bg='#0f172a', kenar='#1e293b', yazi='#e2e8f0', etiket='#cbd5e1', soluk='#64748b',
         c='#22d3ee', cpp='#818cf8', io='#34d399', karar='#fbbf24', pembe='#f472b6')
FONT = "font-family='ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif'"
MONO = "font-family='ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'"

def svg(w, h, body, aria):
    return f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='{w}' height='{h}' role='img' aria-label='{aria}'>
<rect width='{w}' height='{h}' rx='16' fill='{C['bg']}' stroke='{C['kenar']}'/>
{body}
</svg>
"""

def yazi(x, y, t, size=14, renk=None, weight=500, mono=False, anchor='middle'):
    return f"<text x='{x}' y='{y}' text-anchor='{anchor}' dominant-baseline='central' {MONO if mono else FONT} font-size='{size}' font-weight='{weight}' fill='{renk or C['yazi']}'>{t}</text>"

def kaydet(ad, s):
    open(os.path.join(OUT, ad), 'w').write(s)

# ── Ders 3.2: veri modelleri ───────────────────────────────────────────────
modeller = [
    ('Linux, macOS (64 bit)', 'LP64', [1, 2, 4, 8, 8, 8]),
    ('Windows (64 bit)', 'LLP64', [1, 2, 4, 4, 8, 8]),
    ('32 bit sistemler', 'ILP32', [1, 2, 4, 4, 8, 4]),
    ('Arduino Uno (AVR)', '16 bit', [1, 2, 2, 4, 8, 2]),
]
tipler = ['char', 'short', 'int', 'long', 'long long', 'pointer']
renkler = [C['soluk'], C['cpp'], C['c'], C['karar'], C['io'], C['pembe']]
KX, KW, KY, SH, BOX = 250, 118, 70, 62, 13
b = []
for j, t in enumerate(tipler):
    b.append(yazi(KX + j * KW + KW / 2 - 8, 38, t, size=13, renk=renkler[j], weight=700, mono=True))
for i, (ad, model, boyut) in enumerate(modeller):
    y = KY + i * SH
    b.append(yazi(24, y + 8, ad, size=13, weight=700, anchor='start'))
    b.append(yazi(24, y + 28, model, size=12, renk=C['etiket'], mono=True, anchor='start'))
    for j, n in enumerate(boyut):
        x0 = KX + j * KW
        for k in range(n):
            b.append(f"<rect x='{x0 + k * BOX}' y='{y}' width='{BOX - 2}' height='22' rx='2' fill='{renkler[j]}55' stroke='{renkler[j]}' stroke-width='1.5'/>")
        vurgu = (model == 'LLP64' and j == 3) or (model == '16 bit' and j == 2)
        b.append(yazi(x0 + KW / 2 - 8, y + 38, f'{n} byte', size=11, renk=C['karar'] if vurgu else C['etiket'], weight=700 if vurgu else 500, mono=True))
b.append(yazi(KX + 3 * KW, KY + 4 * SH + 4, 'her kutu 1 byte (8 bit) · ölçümler: clang ile her platform için ayrı derleme', size=12, renk=C['etiket']))
kaydet('veri-modelleri.svg', svg(KX + 6 * KW + 10, KY + 4 * SH + 30, '\n'.join(b), 'Dört platformda C tiplerinin byte cinsinden boyutları'))
print('tamam', sorted(os.listdir(OUT)))
