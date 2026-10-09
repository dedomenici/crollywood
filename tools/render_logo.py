#!/usr/bin/env python3
"""Render a photoreal-ish CROLLYWOOD sign (Hollywood-sign style) as a raster, 5:1, for full-width headers.
Straight-edged letters only. Reference photos (Wikimedia Commons): 'Hollywood Sign (Zuschnitt).jpg',
'Hollywood-Sign-cropped.jpg', 'Hollywood Sign close up.jpg', 'View from behind Hollywood Sign overlooking LA.jpg'.
Output: media/logo.webp + media/logo.jpg (2400x480) and media/logo_sm.webp (1200x240)."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
random.seed(7); rng = np.random.default_rng(7)
W, H, SS = 2400, 480, 2           # final size, supersample
w, h = W * SS, H * SS
def P(pts, ox, oy, sx, sy, rot, cx, cy):
    out = []
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    for x, y in pts:
        x, y = x * sx, y * sy
        dx, dy = x - cx, y - cy
        out.append((ox + cx + dx * ca - dy * sa, oy + cy + dx * sa + dy * ca))
    return out
# letters in unit box: height 100, stroke T; straight edges only (O, D octagonal; real O counters are tall narrow slots)
T = 27
LET = {
 'C': (70, [[(14,0),(70,0),(70,T),(T+6,T),(T,T+6),(T,100-T-6),(T+6,100-T),(70,100-T),(70,100),(14,100),(0,86),(0,14)]], []),
 'R': (72, [[(0,0),(54,0),(70,14),(70,44),(60,54),(74,100),(47,100),(37,60),(T,60),(T,100),(0,100)]],
           [[(T,18),(40,18),(44,22),(44,38),(40,42),(T,42)]]),
 'O': (72, [[(16,0),(56,0),(72,16),(72,84),(56,100),(16,100),(0,84),(0,16)]], [[(T,20),(72-T,20),(72-T,80),(T,80)]]),
 'L': (58, [[(0,0),(T+2,0),(T+2,100-T),(58,100-T),(58,100),(0,100)]], []),
 'Y': (80, [[(0,0),(28,0),(40,36),(52,0),(80,0),(54,58),(54,100),(26,100),(26,58)]], []),
 'W': (98, [[(0,0),(25,0),(30,58),(40,18),(58,18),(68,58),(73,0),(98,0),(86,100),(62,100),(49,52),(36,100),(12,100)]], []),
 'D': (72, [[(0,0),(52,0),(72,20),(72,80),(52,100),(0,100)]], [[(T,20),(45-0,20),(72-T,30),(72-T,70),(45,80),(T,80)]]),
}
WORD = "CROLLYWOOD"
img = Image.new("RGB", (w, h))
# --- sky
sky = np.zeros((h, w, 3), np.float32)
t = np.linspace(0, 1, h)[:, None]
top, hor = np.array([38, 98, 186]), np.array([150, 190, 228])
sky[:] = (top * (1 - t ** 1.3) + hor * t ** 1.3)[:, None, :].reshape(h, 1, 3)
img = Image.fromarray(sky.clip(0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)
# --- layout: letters climb the slope to the right, slight per-letter tilt + perspective shrink
Hl = 250 * SS; gap = 46 * SS
widths = [LET[c][0] / 100 * Hl for c in WORD]
scale = [1.0 - 0.06 * i / 9 for i in range(10)]
total = sum(wd * s for wd, s in zip(widths, scale)) + gap * 9
x = (w - total) / 2
bottoms = [0.835 - 0.10 * i / 9 + random.uniform(-0.012, 0.012) for i in range(10)]
rots = [random.uniform(-1.6, 1.6) for _ in range(10)]
boxes = []
for i, c in enumerate(WORD):
    s = scale[i]; lw, lh = widths[i] * s, Hl * s
    by = bottoms[i] * h; boxes.append((x, by - lh, lw, lh, s, rots[i], c)); x += lw + gap
# ridge line (behind letters, rising to the right) + hillside
def ridge(xx): return h * (0.50 - 0.16 * xx / w) + 18 * SS * math.sin(xx / (170 * SS)) + 10 * SS * math.sin(xx / (53 * SS) + 1)
hill = [(0, h)] + [(xx, ridge(xx)) for xx in range(0, w + 1, 8)] + [(w, h)]
hillmask = Image.new("L", (w, h), 0); ImageDraw.Draw(hillmask).polygon(hill, fill=255)
# dirt base with tonal noise
base = np.zeros((h, w, 3), np.float32); base[:] = (166, 136, 96)
n1 = np.array(Image.fromarray((rng.random((h // 16, w // 16)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255 - .5
n2 = rng.random((h, w)).astype(np.float32) - .5
yy = np.linspace(0, 1, h)[:, None]
base *= (1 + 0.28 * n1[..., None] + 0.10 * n2[..., None]) * (1.05 - 0.35 * yy)[..., None]
dirt = Image.fromarray(base.clip(0, 255).astype(np.uint8))
img.paste(dirt, (0, 0), hillmask)
d = ImageDraw.Draw(img)
# scrub: clumps of shaded olive bushes on tan dirt, denser + larger downhill; a few pale dirt scars
scar = Image.new("L", (w, h), 0); scd = ImageDraw.Draw(scar)
for k in range(120):
    xx = random.uniform(0, w); yr = ridge(xx); yy_ = yr + (h - yr) * random.uniform(0.1, 0.9)
    L_ = random.uniform(30, 90) * SS; ang = random.uniform(-0.5, 0.2)
    scd.line([(xx - L_, yy_ - L_ * ang), (xx + L_, yy_ + L_ * ang)], fill=random.randint(70, 150), width=int(random.uniform(5, 14) * SS))
scar = scar.filter(ImageFilter.GaussianBlur(7 * SS))
scar = Image.fromarray((np.array(scar, np.float32) * np.array(hillmask, np.float32) / 255).astype(np.uint8))
img = Image.composite(Image.new("RGB", (w, h), (196, 172, 132)), img, scar); d = ImageDraw.Draw(img)
def bush(xx, yy_, r):
    col = random.choice([(62, 70, 40), (74, 82, 46), (52, 58, 34), (86, 90, 54), (44, 50, 30)])
    d.ellipse((xx - r + r * .25, yy_ - r * .6 + r * .25, xx + r + r * .25, yy_ + r * .75 + r * .25), fill=(70, 56, 38))   # shadow on dirt
    d.ellipse((xx - r, yy_ - r * .7, xx + r, yy_ + r * .7), fill=tuple(int(v * .8) for v in col))
    d.ellipse((xx - r * .8, yy_ - r * .75, xx + r * .55, yy_ + r * .35), fill=col)
    d.ellipse((xx - r * .55, yy_ - r * .7, xx + r * .05, yy_ - r * .05), fill=tuple(min(255, int(v * 1.25)) for v in col))
for k in range(420):
    xx = random.uniform(0, w); yr = ridge(xx)
    yy_ = yr + (h - yr) * random.random() ** 0.7
    depth = (yy_ - yr) / (h - yr + 1)
    n = int(2 + 14 * depth * random.random())
    for j in range(n):
        r = SS * random.uniform(3, 8) * (0.5 + 1.5 * depth)
        bush(xx + random.gauss(0, 14 * SS * (0.5 + depth)), yy_ + random.gauss(0, 5 * SS), r)
for k in range(900):   # lone shrubs
    xx = random.uniform(0, w); yr = ridge(xx); yy_ = yr + (h - yr) * random.random()
    bush(xx, yy_, SS * random.uniform(2, 5))
# cast shadows of letters onto the hill (sun upper-left)
shadow = Image.new("L", (w, h), 0); sd = ImageDraw.Draw(shadow)
for (bx, by, lw, lh, s, rot, c) in boxes:
    wd, outer, holes = LET[c]; sx = lw / wd; sy = lh / 100
    pts = P(outer[0], bx + 16 * SS, by + 26 * SS, sx, sy * 0.9, rot - 4, lw / 2, lh)
    sd.polygon(pts, fill=120)
shadow = shadow.filter(ImageFilter.GaussianBlur(6 * SS))
shadow = Image.fromarray((np.array(shadow, np.float32) * (np.array(hillmask, np.float32) / 255)).astype(np.uint8))
img = Image.composite(Image.new("RGB", (w, h), (34, 30, 22)), img, shadow)
d = ImageDraw.Draw(img)
# framework behind each letter: only visible through the counters (clipped to the outline) + legs below
steel = (112, 112, 106); steel_d = (78, 78, 74)
for (bx, by, lw, lh, s, rot, c) in boxes:
    wd, outer, holes = LET[c]; sx = lw / wd; sy = lh / 100
    fl = Image.new("RGBA", (w, h), (0, 0, 0, 0)); fd = ImageDraw.Draw(fl)
    for f in (0.2, 0.5, 0.8): fd.line([(bx + lw * f, by), (bx + lw * f, by + lh)], fill=steel_d + (255,), width=int(4 * SS * s))
    for fy in (0.12, 0.3, 0.5, 0.7, 0.88): fd.line([(bx, by + lh * fy), (bx + lw, by + lh * fy)], fill=steel + (255,), width=int(2.6 * SS))
    for fy in (0.12, 0.5):
        fd.line([(bx + lw * .2, by + lh * fy), (bx + lw * .5, by + lh * (fy + .38))], fill=steel + (255,), width=int(2 * SS))
        fd.line([(bx + lw * .8, by + lh * fy), (bx + lw * .5, by + lh * (fy + .38))], fill=steel + (255,), width=int(2 * SS))
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).polygon(P(outer[0], bx, by, sx, sy, rot, lw / 2, lh / 2), fill=255)
    fl.putalpha(Image.fromarray(np.minimum(np.array(fl.split()[3]), np.array(m))))
    img.paste(fl, (0, 0), fl)
    d = ImageDraw.Draw(img)
    bl = P([(wd * .2, 100), (wd * .5, 100), (wd * .8, 100)], bx, by, sx, sy, rot, lw / 2, lh / 2)
    for (lx, ly) in bl:
        d.line([(lx, ly - 4 * SS), (lx + 1 * SS, ly + 24 * SS * s)], fill=steel_d, width=int(5 * SS * s))
    d.line([bl[0], (bl[1][0], bl[1][1] + 20 * SS * s)], fill=steel_d, width=int(2.6 * SS))
    d.line([bl[2], (bl[1][0], bl[1][1] + 20 * SS * s)], fill=steel_d, width=int(2.6 * SS))
# letter faces: off-white sheet metal, sunlit gradient, dust, horizontal panel seams, thin edge depth
face_tex = np.zeros((h, w, 3), np.float32)
g = np.linspace(0, 1, h)[:, None]
face_tex[:] = 253
face_tex *= (1 - 0.045 * (np.array(Image.fromarray((rng.random((h // 40, w // 40)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255))[..., None]
face_tex *= (1 - 0.035 * rng.random((h, w)).astype(np.float32))[..., None]
face_tex[..., 2] *= 0.975; face_tex[..., 1] *= 0.99   # warm off-white
face = Image.fromarray(face_tex.clip(0, 255).astype(np.uint8))
for (bx, by, lw, lh, s, rot, c) in boxes:
    wd, outer, holes = LET[c]; sx = lw / wd; sy = lh / 100
    m = Image.new("L", (w, h), 0); md = ImageDraw.Draw(m)
    side = P(outer[0], bx + 6 * SS * s, by + 3 * SS * s, sx, sy, rot, lw / 2, lh / 2)
    md.polygon(side, fill=255)
    for hp in holes: md.polygon(P(hp, bx + 6 * SS * s, by + 3 * SS * s, sx, sy, rot, lw / 2, lh / 2), fill=0)
    img.paste((168, 164, 154), (0, 0), m)            # metal edge / depth (right + bottom)
    m = Image.new("L", (w, h), 0); md = ImageDraw.Draw(m)
    md.polygon(P(outer[0], bx, by, sx, sy, rot, lw / 2, lh / 2), fill=255)
    for hp in holes: md.polygon(P(hp, bx, by, sx, sy, rot, lw / 2, lh / 2), fill=0)
    # per-letter shading: lit top, dusty lower third
    shade = Image.new("L", (w, h), 0); shd = ImageDraw.Draw(shade)
    for k in range(40):
        f = k / 40; yv = by + lh * f
        shd.rectangle((bx - lw, yv, bx + 2 * lw, yv + lh / 40 + 2), fill=int(22 * max(0, f - 0.55) / 0.45))
    lf = Image.composite(Image.new("RGB", (w, h), (176, 160, 136)), face, shade)
    # horizontal panel seams + faint vertical seams
    sm = ImageDraw.Draw(lf)
    for k in range(1, 7):
        yv = by + lh * k / 7 + random.uniform(-2, 2) * SS
        sm.line([(bx - 4, yv), (bx + lw + 4, yv)], fill=random.choice([(214, 210, 200), (206, 202, 192), (222, 219, 210)]), width=max(2, int(1.1 * SS)))
    if rot: lf = lf  # (rotation is applied by the mask; seams stay level: within ±1.6° it reads as natural)
    img.paste(lf, (0, 0), m)
# atmospheric haze, slight vignette, downsample + unsharp for crispness
img = img.resize((W, H), Image.LANCZOS)
arr = np.array(img, np.float32)
yy, xx = np.mgrid[0:H, 0:W]
vig = 1 - 0.18 * (((xx - W / 2) / (W / 2)) ** 2) * 0.6 - 0.10 * ((yy / H) ** 2)
arr *= vig[..., None]
img = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).filter(ImageFilter.UnsharpMask(radius=1.4, percent=70, threshold=2))
img.save("media/logo.webp", quality=88, method=6)
img.save("media/logo.jpg", quality=88, optimize=True, progressive=True)
img.resize((1200, 240), Image.LANCZOS).save("media/logo_sm.webp", quality=88, method=6)
print("letters bottoms", [round(b, 3) for b in bottoms])
