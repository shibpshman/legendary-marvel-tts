"""Draws our own player mat: Victory, Draw, Artifacts, Discard, a big Played box and Attack / Recruit counter boxes.

Usage: python make_player_mat_v2.py [--out TTS_work\\playermat.png]
The first run keeps the official render as playermat_official.png next to the output. Same pixel size and aspect as the
official render, so build_save.py's maths is unchanged. Slot positions are the PM_* values in mat_config.py: this script
imports them, so the art and the Lua always agree."""
import argparse, os, shutil, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import mat_config as C

WORK = r'E:\Media\Board Games\TTS_work'
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=os.path.join(WORK, 'playermat.png'))
a = ap.parse_args()

W, H = 2400, 1698
CARD_W, CARD_H = 400, 560            # slot frame, about one card (2.2 x 3.1 world units at the saved scale)
# label font: Avenir Heavy Oblique (its slant echoes the Legendary logo); falls back to Bahnschrift if it is not installed
FONT_DIRS = [r'C:\Windows\Fonts', os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Windows\Fonts')]
FONT_FILES = ['AvenirLTProHeavyOblique.otf', 'bahnschrift.ttf']
FONT = next((os.path.join(d, f) for f in FONT_FILES for d in FONT_DIRS if os.path.exists(os.path.join(d, f))), None)
if FONT is None: sys.exit('no label font found: install Avenir LT Pro or keep bahnschrift.ttf')


def font(sz):
    f = ImageFont.truetype(FONT, sz)
    if FONT.lower().endswith('bahnschrift.ttf'):
        try: f.set_variation_by_name('Bold')
        except Exception: pass
    return f


def px(uv): return int(round(uv[0] * W)), int(round(uv[1] * H))


# ---- background: abstract and quiet. Navy gradient, a soft glow behind the Played box, faint comic halftone in the corners ----
import numpy as np
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
t = yy / H
base = np.stack([14 + 8 * (1 - t), 22 + 12 * (1 - t), 52 + 22 * (1 - t)], axis=-1)           # top slightly lighter
gx, gy = W * 0.5, H * 0.40
glow = np.exp(-(((xx - gx) / (W * 0.40)) ** 2 + ((yy - gy) / (H * 0.42)) ** 2))[..., None]
base = base + glow * np.array([10, 22, 48], dtype=np.float32)
# halftone dots, strongest in the four corners and gone by the middle
step = 34
dot = (np.hypot((xx % step) - step / 2, (yy % step) - step / 2) < (step * 0.16)).astype(np.float32)
cd = np.minimum(np.minimum(xx, W - xx), 1e9) / (W * 0.30)
cv = np.minimum(yy, H - yy) / (H * 0.30)
edge = np.clip(1 - np.hypot(np.clip(cd, 0, 1), np.clip(cv, 0, 1)) , 0, 1) ** 1.2
base = base + (dot * edge * 22)[..., None]
bg = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB')
im = bg.convert('RGBA')

# vignette so the edges read as a frame
vig = Image.new('L', (W, H), 0)
d = ImageDraw.Draw(vig)
for i in range(60):
    d.rectangle((i, i, W - i, H - i), outline=int(150 * (1 - i / 60)))
im.paste((0, 0, 0, 255), mask=vig)


def panel(box, label, sub=None, accent=(255, 255, 255), fill=(10, 16, 40, 175), r=26, glow=True):
    """Translucent frame with a glowing edge and a label strip under its top edge."""
    global im
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, r, fill=fill)
    im = Image.alpha_composite(im, layer)
    if glow:
        g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle(box, r, outline=accent + (255,), width=10)
        g = g.filter(ImageFilter.GaussianBlur(9))
        im = Image.alpha_composite(im, g)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(box, r, outline=accent + (255,), width=4)
    if label:
        f = font(46)
        tw = d.textlength(label, font=f)
        cx = (box[0] + box[2]) / 2
        ty = box[1] + 16
        d.text((cx - tw / 2, ty), label, font=f, fill=(255, 255, 255, 235), stroke_width=2, stroke_fill=(0, 0, 0, 255))
        if sub:
            f2 = font(26)
            sw = d.textlength(sub, font=f2)
            d.text((cx - sw / 2, ty + 56), sub, font=f2, fill=(205, 215, 235, 220), stroke_width=1, stroke_fill=(0, 0, 0, 255))


def tint(accent, k=0.14):
    base = (10, 16, 40)
    if accent == (255, 200, 60): return (52, 40, 14, 190)    # gold mixed into navy goes grey, so it gets a hand-set warm fill
    return tuple(int(base[i] * (1 - k) + accent[i] * k) for i in range(3)) + (185,)


def slot(uv, label, accent):
    cx, cy = px(uv)
    box = (cx - CARD_W // 2, cy - CARD_H // 2, cx + CARD_W // 2, cy + CARD_H // 2)
    panel(box, None, accent=accent, fill=tint(accent))
    # label under the frame, outside the card area so a card never covers it
    d = ImageDraw.Draw(im)
    f = font(50)
    tw = d.textlength(label, font=f)
    d.text((cx - tw / 2, box[3] + 14), label, font=f, fill=(255, 255, 255, 240), stroke_width=3, stroke_fill=(0, 0, 0, 255))


GOLD, BLUE, RED, GREEN, WHITE = (255, 200, 60), (90, 170, 255), (255, 90, 70), (110, 220, 140), (235, 235, 245)

# ---- the zones ------------------------------------------------------------------------------------------------------
slot(C.PM_VICTORY_UV, 'VICTORY', GOLD)
slot(C.PM_DRAW_UV, 'DRAW', BLUE)
slot(C.PM_ARTIFACTS_UV, 'ARTIFACTS', GREEN)
slot(C.PM_DISCARD_UV, 'DISCARD', RED)

u0, v0, u1, v1 = C.PM_PLAYED_BOX
(bx0, by0), (bx1, by1) = px((u0, v0)), px((u1, v1))
panel((bx0, by0, bx1, by1), 'PLAYED', None, accent=WHITE, fill=(6, 10, 30, 110), r=40)

# faint Legendary icon in the middle of the Played box (flat icon from make_logo_icon.py)
LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'legendary_icon.png')
if os.path.exists(LOGO):
    lg = Image.open(LOGO).convert('RGBA')
    side = int((by1 - by0) * 0.78)
    lg = lg.resize((side, side), Image.LANCZOS)
    lg.putalpha(lg.getchannel('A').point(lambda v: int(v * 0.10)))
    im.alpha_composite(lg, ((bx0 + bx1) // 2 - side // 2, (by0 + by1) // 2 - side // 2 + 30))

# the three counter pads (Attack, Recruit, Shards) sit on these boxes and hide their middle, so each label goes along the box's bottom edge
PURPLE = (190, 140, 255)
for uv, label, col in ((C.PM_ATTACK_UV, 'ATTACK', RED), (C.PM_RECRUIT_UV, 'RECRUIT', GOLD), (C.PM_SHARDS_UV, 'SHARDS', PURPLE)):
    cx, cy = px(uv)
    cy = int(C.PM_BOX_V * H)
    panel((cx - 250, cy - 150, cx + 250, cy + 150), None, accent=col, fill=tint(col, 0.16), r=34)
    _d = ImageDraw.Draw(im)
    _f = font(40)
    _w = _d.textlength(label, font=_f)
    _d.text((cx - _w / 2, cy + 150 - 62), label, font=_f, fill=(255, 255, 255, 240), stroke_width=3, stroke_fill=(0, 0, 0, 255))   # inside the bottom edge: the pad sits above it


# ---- icons: class and team icons cut from the official Player Mat PDF (vector, rendered large), on light tiles so the dark ones show ----
PDF = os.path.join(WORK, 'assets_in', 'LegendaryPlayerMat.pdf')


def pdf_icons():
    """{name: RGBA tile} for the 5 hero classes and 4 teams, from the PDF's legend. Positions are fractions of the 1600 px wide preview."""
    import numpy as np, pypdfium2 as pdfium
    pg = pdfium.PdfDocument(PDF)[0].render(scale=8).to_pil().convert('RGB')
    arr = np.array(pg)
    blue = (arr[:, :, 2] > 100) & (arr[:, :, 0] < 60) & (arr[:, :, 1] < 120)
    ys, xs = np.where(blue)
    mat = pg.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)).rotate(-90, expand=True)
    k = 4800 / 1600
    mat = mat.resize((4800, int(round(4800 * mat.size[1] / mat.size[0]))), Image.LANCZOS)
    where = {'Strength': (1347, 60), 'Instinct': (1347, 100), 'Covert': (1347, 139), 'Tech': (1347, 178), 'Ranged': (1347, 217),
             'X-Men': (254, 61), 'Avengers': (254, 113), 'S.H.I.E.L.D.': (254, 163), 'Spider Friends': (254, 216)}
    out = {}
    for n, (cx, cy) in where.items():
        h = 21 * k
        out[n] = mat.crop((int(cx * k - h), int(cy * k - h), int(cx * k + h), int(cy * k + h)))
    return out


def tile(icon, size):
    t = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(t).rounded_rectangle((0, 0, size - 1, size - 1), size // 5, fill=(236, 240, 248, 255))
    ic = icon.convert('RGB').resize((size - 14, size - 14), Image.LANCZOS)
    # the legend panel behind each icon is white: keep it, it is the tile
    t.paste(ic, (7, 7))
    m = Image.new('L', (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), size // 5, fill=255)
    t.putalpha(m)
    return t


try:
    icons = pdf_icons()
    SZ = 70
    row_y = int(1212)
    classes = ['Strength', 'Instinct', 'Covert', 'Tech', 'Ranged']
    teams = ['X-Men', 'Avengers', 'S.H.I.E.L.D.', 'Spider Friends']
    gap = 18
    total = (len(classes) + len(teams)) * SZ + (len(classes) + len(teams) - 2) * gap + 70
    x = (W - total) // 2
    for n in classes + [None] + teams:
        if n is None: x += 70; continue
        im.alpha_composite(tile(icons[n], SZ), (x, row_y - SZ // 2))
        x += SZ + gap
except Exception as e:
    print('icons skipped:', e)

os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
official = os.path.join(os.path.dirname(a.out), 'playermat_official.png')
if os.path.exists(a.out) and not os.path.exists(official): shutil.copy2(a.out, official)
im.convert('RGB').save(a.out)
print('wrote %s (%d x %d)' % (a.out, W, H))
