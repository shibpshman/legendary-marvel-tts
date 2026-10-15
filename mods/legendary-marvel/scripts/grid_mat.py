"""Draws a 0.05 grid (u across, v down) over a mat image so slot positions can be read off by eye.
Usage: python grid_mat.py [image]     default: TTS_work\\assets_in\\28_Inch_Template_-_1.jpg
Writes next to TTS_work: grid_full.jpg (2000 px wide), grid_left.jpg and grid_right.jpg (left / right halves, 1500 px each)."""
import os, sys, time
from PIL import Image, ImageDraw, ImageFont

WORK = r'E:\Media\Board Games\TTS_work'
SRC = os.path.join(WORK, 'assets_in', '28_Inch_Template_-_1.jpg')
if len(sys.argv) > 1: SRC = sys.argv[1]
T0 = time.time()


def log(m): print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


Image.MAX_IMAGE_PIXELS = None
log('opening %s' % SRC)
im = Image.open(SRC).convert('RGB')
try: font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 16)
except Exception: font = ImageFont.load_default()


def gridded(img, u0, u1):
    """grid over the u range [u0, u1] of the full image, labelled with full-image fractions"""
    W, H = img.size
    crop = img.crop((int(u0 * W), 0, int(u1 * W), H))
    cw, ch = crop.size
    d = ImageDraw.Draw(crop)
    n = int(round((u1 - u0) / 0.05))
    for i in range(0, n + 1):
        u = u0 + i * 0.05
        x = int((u - u0) * W)
        d.line([x, 0, x, ch], fill=(255, 255, 0), width=max(1, cw // 1200))
        d.text((x + 3, 3), '%.2f' % u, fill=(255, 255, 0), font=font)
    for j in range(0, 21):
        v = j * 0.05; y = int(v * ch)
        d.line([0, y, cw, y], fill=(255, 255, 0), width=max(1, cw // 1200))
        d.text((3, y + 3), '%.2f' % v, fill=(255, 255, 0), font=font)
    return crop


for name, u0, u1, w in (('grid_full.jpg', 0, 1, 2000), ('grid_left.jpg', 0, .5, 1500), ('grid_right.jpg', .5, 1, 1500)):
    g = gridded(im, u0, u1)
    g = g.resize((w, int(round(w * g.size[1] / g.size[0]))))
    path = os.path.join(WORK, name); g.save(path, quality=88)
    log('wrote %s' % path)
log('DONE')
