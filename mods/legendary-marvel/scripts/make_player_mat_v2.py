"""Draws our own player mat: Victory, Draw, Artifacts, Discard, a big Played box and Attack / Recruit counter boxes.

Usage: python make_player_mat_v2.py [--out TTS_work\\playermat.png] [--art TTS_work\\assets_up\\boardA_upscayl_4x_realesrgan-x4plus-anime.png]
The first run keeps the official render as playermat_official.png next to the output. Same pixel size and aspect as the
official render, so build_save.py's maths is unchanged. Slot positions are the PM_* values in mat_config.py: this script
imports them, so the art and the Lua always agree."""
import argparse, os, shutil, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
import mat_config as C

WORK = r'E:\Media\Board Games\TTS_work'
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=os.path.join(WORK, 'playermat.png'))
ap.add_argument('--art', default=os.path.join(WORK, 'assets_up', 'boardA_upscayl_4x_realesrgan-x4plus-anime.png'))
a = ap.parse_args()

W, H = 2400, 1698
CARD_W, CARD_H = 400, 560            # slot frame, about one card (2.2 x 3.1 world units at the saved scale)
FONT = r'C:\Windows\Fonts\bahnschrift.ttf'


def font(sz):
    f = ImageFont.truetype(FONT, sz)
    try: f.set_variation_by_name('Bold')
    except Exception: pass
    return f


def px(uv): return int(round(uv[0] * W)), int(round(uv[1] * H))


# ---- background: the hero art, cropped to the mat's shape, darkened and tinted navy ----------------------------------
art = Image.open(a.art).convert('RGB')
r = W / H
# the source board prints its own labels and rules text in the side panels: keep only the central art
cw = int(art.size[0] * 0.52); ch = int(cw / r)
x0, y0 = (art.size[0] - cw) // 2, int((art.size[1] - ch) * 0.35)
bg = art.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3))
bg = ImageEnhance.Brightness(bg).enhance(0.62)
bg = ImageEnhance.Color(bg).enhance(1.05)
navy = Image.new('RGB', (W, H), (8, 14, 38))
bg = Image.blend(bg, navy, 0.35)
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


def slot(uv, label, accent):
    cx, cy = px(uv)
    box = (cx - CARD_W // 2, cy - CARD_H // 2, cx + CARD_W // 2, cy + CARD_H // 2)
    panel(box, None, accent=accent)
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
panel((bx0, by0, bx1, by1), 'PLAYED', 'cards in this box count: stack or spread them, then press Apply', accent=WHITE, fill=(6, 10, 30, 110), r=40)

for uv, label, col in ((C.PM_ATTACK_UV, 'ATTACK', RED), (C.PM_RECRUIT_UV, 'RECRUIT', GOLD)):
    cx, cy = px(uv)
    panel((cx - 270, cy - 150, cx + 270, cy + 150), label, accent=col, fill=(10, 16, 40, 170), r=34)

os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
official = os.path.join(os.path.dirname(a.out), 'playermat_official.png')
if os.path.exists(a.out) and not os.path.exists(official): shutil.copy2(a.out, official)
im.convert('RGB').save(a.out)
print('wrote %s (%d x %d)' % (a.out, W, H))
