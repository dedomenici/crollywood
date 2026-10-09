"""Generate the angular, Hollywood-sign-style CROLLYWOOD logo as an SVG <symbol>.
All letters are straight-edged polygons (O and D octagonal). Output: tools/logo_symbol.svg"""
import math, os
T = 17  # stroke thickness in letter units (letter height 100)
L = {
 'C': (56, [[(12,0),(56,0),(56,T),(21,T),(17,21),(17,79),(21,83),(56,83),(56,100),(12,100),(0,88),(0,12)]]),
 'R': (58, [[(0,0),(44,0),(56,12),(56,45),(47,54),(59,100),(41,100),(31,58),(17,58),(17,100),(0,100)],
            [(17,16),(36,16),(39,19),(39,39),(36,42),(17,42)]]),
 'O': (58, [[(14,0),(44,0),(58,14),(58,86),(44,100),(14,100),(0,86),(0,14)],
            [(21,T),(37,T),(41,21),(41,79),(37,83),(21,83),(17,79),(17,21)]]),
 'L': (46, [[(0,0),(T,0),(T,83),(46,83),(46,100),(0,100)]]),
 'Y': (60, [[(0,0),(19,0),(30,36),(41,0),(60,0),(39,58),(39,100),(21,100),(21,58)]]),
 'W': (80, [[(0,0),(17,0),(23,60),(32,18),(48,18),(57,60),(63,0),(80,0),(68,100),(50,100),(40,54),(30,100),(12,100)]]),
 'D': (57, [[(0,0),(41,0),(57,16),(57,84),(41,100),(0,100)],
            [(T,T),(34,T),(40,23),(40,77),(34,83),(T,83)]]),
}
WORD = 'CROLLYWOOD'
GAP = 5
# uneven hillside baseline (y of letter top) + slight tilt per letter
TOPS = [12, 8, 6, 4, 3, 2, 3, 5, 7, 10]
ROT = [-1.5, 1.0, -0.8, 1.2, -0.6, 0.9, -1.0, 0.7, -1.1, 1.4]
X0 = 14
def pathd(polys):
    return ' '.join('M' + ' L'.join(f'{x},{y}' for x, y in p) + ' Z' for p in polys)

out = []
defs = '''<linearGradient id="lgFace" x1="0" y1="0" x2="0.35" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".55" stop-color="#f1f1ef"/><stop offset="1" stop-color="#c9c9c6"/></linearGradient>
<linearGradient id="lgSide" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8f8f8c"/><stop offset="1" stop-color="#4a4a48"/></linearGradient>
<pattern id="lgSeams" width="9" height="100" patternUnits="userSpaceOnUse"><rect x="8.2" width=".8" height="100" fill="#000" opacity=".13"/><rect x="0" y="33" width="9" height=".7" fill="#000" opacity=".08"/><rect x="0" y="66" width="9" height=".7" fill="#000" opacity=".08"/></pattern>
<linearGradient id="lgHill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4b4a3f"/><stop offset="1" stop-color="#16160f"/></linearGradient>
<linearGradient id="lgHill2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2d2c24"/><stop offset="1" stop-color="#0b0b08"/></linearGradient>
<filter id="lgScrub" x="0" y="0" width="1" height="1"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.6 1.05"/><feComposite in2="SourceGraphic" operator="in"/></filter>'''
x = X0
letters = []
for i, ch in enumerate(WORD):
    w, polys = L[ch]
    letters.append((x, TOPS[i], ROT[i], w, pathd(polys)))
    x += w + GAP
W = x - GAP + X0
H = 132
# hill: rises under the letters, letters' feet sink slightly into it
feet = [(lx + w/2, top + 100 + 9 + (2 if i % 3 == 0 else -1)) for i, (lx, top, rot, w, d) in enumerate(letters)]
hill = f'M0 {H} L0 {feet[0][1]+6} ' + ' '.join(f'L{fx:.0f} {fy}' for fx, fy in feet) + f' L{W} {feet[-1][1]+5} L{W} {H} Z'
hill2 = f'M0 {H} L0 127 L80 124 L170 128 L260 123 L350 126 L450 122 L540 126 L{W} 125 L{W} {H} Z'
scaf = []
for (lx, top, rot, w, d) in letters:
    a, b = lx + w * 0.2, lx + w * 0.8
    y1, y2 = top + 30, top + 100 + 14
    yb = top + 100 + 3
    scaf.append(f'M{a:.1f} {y1} V{y2} M{b:.1f} {y1} V{y2} M{a:.1f} {yb} H{b:.1f} M{a:.1f} {yb} L{b:.1f} {y2} M{b:.1f} {yb} L{a:.1f} {y2} M{a:.1f} {y1+30} L{b:.1f} {yb}')
g = []
for (lx, top, rot, w, d) in letters:
    cx, cy = lx + w / 2, top + 50
    tr = f'translate({lx} {top}) rotate({rot} {w/2} 50)'
    g.append(f'<g transform="{tr}">'
             f'<path d="{d}" transform="translate(4.5 3)" fill="url(#lgSide)" fill-rule="evenodd"/>'
             f'<path d="{d}" transform="translate(2.2 1.5)" fill="#9c9c99" fill-rule="evenodd"/>'
             f'<path d="{d}" fill="url(#lgFace)" fill-rule="evenodd"/>'
             f'<path d="{d}" fill="url(#lgSeams)" fill-rule="evenodd"/>'
             f'<path d="{d}" fill="none" stroke="#fff" stroke-width=".8" stroke-opacity=".9" fill-rule="evenodd"/>'
             '</g>')
sym = (f'<symbol id="logo" viewBox="0 0 {W} {H}">\n<defs>{defs}</defs>\n'
       f'<path d="{hill}" fill="url(#lgHill)"/>\n<path d="{hill}" fill="#000" opacity=".35" filter="url(#lgScrub)"/>\n'
       f'<g stroke="#8d8d88" stroke-width="1.5" fill="none" stroke-linecap="square"><path d="{" ".join(scaf)}"/></g>\n'
       + '\n'.join(g) +
       f'\n<path d="{hill2}" fill="url(#lgHill2)"/>\n</symbol>')
here = os.path.dirname(os.path.abspath(__file__))
open(os.path.join(here, 'logo_symbol.svg'), 'w').write(sym)
open('/tmp/logo_preview.html', 'w').write('<html><body style="margin:0;background:#000"><svg width="0" height="0" style="position:absolute">' + sym +
    f'</svg><div style="padding:20px"><svg style="width:900px;aspect-ratio:{W}/{H}"><use href="#logo"/></svg><br><br>'
    f'<svg style="height:44px;aspect-ratio:{W}/{H}"><use href="#logo"/></svg></div></body></html>')
print('viewBox', W, H, 'ratio', round(W / H, 3))
