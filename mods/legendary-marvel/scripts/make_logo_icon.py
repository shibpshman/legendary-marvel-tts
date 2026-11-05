"""Flat Legendary "L in a ring" icon, redrawn as clean shapes from the card back's logo (no photo pixels, transparent background).

The geometry was measured off LegendaryCardBack_ColorAdjusted (1).jpg (crop x 10-90 %, y 24-70 %, then the box 400,200-2200,1800 at half size):
the ring is centred (421, 410), outer radius 311, inner 243, open from -46 deg to +10 deg; the L is the 7-point polygon below.
Usage: python make_logo_icon.py [--out ..\\data\\legendary_icon.png] [--size 1024]
Writes the icon, plus <out>_on_navy.png (a preview on the mat's navy)."""
import argparse, math, os
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=os.path.join(HERE, '..', 'data', 'legendary_icon.png'))
ap.add_argument('--size', type=int, default=1024)
ap.add_argument('--ring', default='#AEBBCB')     # ring colour (flat)
ap.add_argument('--ell', default='#F4F7FB')      # L colour (flat)
ap.add_argument('--gap', type=float, default=13)  # separation cut where the L crosses the ring, in source px
a = ap.parse_args()

CX, CY, R_OUT, R_IN = 421, 410, 311, 243
ARC_FROM, ARC_TO = 10, 314                       # degrees, counter-clockwise from 10 (top-right end) round to 314 (bottom-right end)
L_POLY = [(500, 5), (325, 115), (257, 390), (200, 622), (640, 622), (810, 525), (355, 525)]
K = 4                                            # supersampling
W, H = 900 * K, 800 * K


def sx(p): return (p[0] * K, p[1] * K)


def ring_mask():
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    n = 400
    outer = [(CX + R_OUT * math.cos(math.radians(ARC_FROM + (ARC_TO - ARC_FROM) * i / n)),
              CY - R_OUT * math.sin(math.radians(ARC_FROM + (ARC_TO - ARC_FROM) * i / n))) for i in range(n + 1)]
    inner = [(CX + R_IN * math.cos(math.radians(ARC_TO - (ARC_TO - ARC_FROM) * i / n)),
              CY - R_IN * math.sin(math.radians(ARC_TO - (ARC_TO - ARC_FROM) * i / n))) for i in range(n + 1)]
    d.polygon([sx(p) for p in outer + inner], fill=255)
    return m


def l_mask(grow=0):
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).polygon([sx(p) for p in L_POLY], fill=255)
    if grow:
        import cv2, numpy as np
        k = int(grow * K) * 2 + 1
        m = Image.fromarray(cv2.dilate(np.array(m), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))))
    return m


ring = ring_mask()
ell = l_mask()
cut = l_mask(a.gap)
ring_visible = Image.composite(Image.new('L', (W, H), 0), ring, cut)     # ring minus the L's grown outline

img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
img.paste(Image.new('RGBA', (W, H), a.ring), mask=ring_visible)
img.paste(Image.new('RGBA', (W, H), a.ell), mask=ell)

box = img.getbbox()
pad = 30 * K
box = (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad)
img = img.crop(box)
side = max(img.size)
sq = Image.new('RGBA', (side, side), (0, 0, 0, 0))
sq.paste(img, ((side - img.size[0]) // 2, (side - img.size[1]) // 2))
sq = sq.resize((a.size, a.size), Image.LANCZOS)

os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
sq.save(a.out)
prev = Image.new('RGBA', sq.size, (14, 22, 52, 255))
prev.alpha_composite(sq)
base, ext = os.path.splitext(a.out)
prev.convert('RGB').save(base + '_on_navy.png')
print('wrote', os.path.normpath(a.out), sq.size)
