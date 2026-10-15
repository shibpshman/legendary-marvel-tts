"""Makes contact sheets of every scheme / Mastermind card's rules text so the inline icons can be read by eye.

The automatic icon matching finds the obvious ones but confuses faint icons with text. This script crops the rules text of each
card (the part with the icons), stacks cards into pictures about 1900 px tall and writes them to TTS_work\\icon_review\\review_NN.png.
Upload those pictures; the icons are then written into the reference text by hand, which is exact.

Usage: python icon_review.py [card_text_icons.csv]       (prints timestamped progress and an ETA)"""
import csv, os, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from rapidocr_onnxruntime import RapidOCR

WORK = r'E:\Media\Board Games\TTS_work'
SRC = r'E:\Media\Board Games\Marvel Legendary Cards'
CSV_IN = os.path.join(WORK, 'card_text_icons.csv')
if not os.path.isfile(CSV_IN): CSV_IN = os.path.join(WORK, 'card_text_ocr.csv')
OUT_DIR = os.path.join(WORK, 'icon_review')
args = [a for a in sys.argv[1:] if not a.startswith('--')]
if args: CSV_IN = args[0]
for a in sys.argv[1:]:
    if a.startswith('--src='): SRC = a[6:]
    if a.startswith('--out='): OUT_DIR = a[6:]
CROP_W = 800
T0 = time.time()


def log(m):
    print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


def lines_of(items):
    items = sorted(items, key=lambda b: (b[1] + b[3]) / 2)
    lines, cur, cy = [], [], None
    for b in items:
        c = (b[1] + b[3]) / 2; h = b[3] - b[1]
        if cur and abs(c - cy) <= 0.6 * h: cur.append(b)
        else:
            if cur: lines.append(cur)
            cur, cy = [b], c
    if cur: lines.append(cur)
    return lines


def font(size):
    for f in (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\segoeui.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.isfile(f): return ImageFont.truetype(f, size)
    return ImageFont.load_default()


log('reading %s' % CSV_IN)
rows = list(csv.DictReader(open(CSV_IN, encoding='utf-8-sig')))
ocr = RapidOCR()
os.makedirs(OUT_DIR, exist_ok=True)
crops, t_start, skipped = [], time.time(), []
for i, r in enumerate(rows, 1):
    t1 = time.time()
    path = os.path.join(SRC, r['file'])
    if not os.path.isfile(path):
        skipped.append(r['name']); log('[%d/%d] %s: file missing' % (i, len(rows), r['name'])); continue
    im = Image.open(path).convert('RGB')
    s = min(1.0, 1990 / max(im.size))
    if s < 1: im = im.resize((int(im.size[0] * s), int(im.size[1] * s)), Image.LANCZOS)
    H = im.size[1]
    res, _ = ocr(np.array(im))
    items = [(min(p[0] for p in b), min(p[1] for p in b), max(p[0] for p in b), max(p[1] for p in b), t) for b, t, sc in (res or [])]
    W = im.size[0]                                    # line heights scale with the card width (cards are ~1000-1430 px wide)
    block = [l for l in lines_of(items) if min(b[1] for b in l) > 0.5 * H and 0.03 * W <= (max(b[3] for b in l) - min(b[1] for b in l)) <= 0.058 * W
             and not any(b[4].strip().upper() in ('SCHEME', 'MASTERMIND') for b in l)]
    if not block:
        y0, y1 = int(0.72 * H), int(0.97 * H)
        x0, x1 = 0, im.size[0]
    else:
        y0 = max(0, int(min(b[1] for l in block for b in l)) - 14)
        y1 = min(H, int(max(b[3] for l in block for b in l)) + 14)
        x0 = max(0, int(min(b[0] for l in block for b in l)) - 20)
        x1 = min(im.size[0], int(max(b[2] for l in block for b in l)) + 20)
    crop = im.crop((x0, y0, x1, y1))
    crop = crop.resize((CROP_W, max(20, int(crop.size[1] * CROP_W / crop.size[0]))), Image.LANCZOS)
    crops.append((r, crop))
    eta = (time.time() - t_start) / i * (len(rows) - i)
    log('[%d/%d] %s %r: crop %dx%d (%.1fs, ETA %d min)' % (i, len(rows), r['kind'], r['name'], crop.size[0], crop.size[1], time.time() - t1, eta / 60))

log('building contact sheets')
f_lab = font(22)
groups, cur, cur_h = [], [], 0
for item in crops:                                   # pack cards into pictures no taller than ~2300 px
    ch = item[1].size[1] + 40
    if cur and cur_h + ch > 2300: groups.append(cur); cur, cur_h = [], 0
    cur.append(item); cur_h += ch
if cur: groups.append(cur)
num = 0
for gi, group in enumerate(groups, 1):
    sheet = Image.new('RGB', (CROP_W + 20, sum(c.size[1] + 40 for _, c in group) + 10), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    y = 5
    for r, c in group:
        num += 1
        d.rectangle([0, y, CROP_W + 20, y + 32], fill=(30, 40, 70))
        d.text((8, y + 4), '%d. %s (%s)' % (num, r['name'], r['kind']), fill=(255, 255, 255), font=f_lab)
        sheet.paste(c, (10, y + 36)); y += c.size[1] + 40
    sheet.save(os.path.join(OUT_DIR, 'review_%02d.png' % gi))
log('DONE: %d cards on %d sheets in %s%s' % (len(crops), len(groups), OUT_DIR, ('; skipped (file missing): ' + ', '.join(skipped)) if skipped else ''))
