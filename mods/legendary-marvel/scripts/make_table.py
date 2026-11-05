"""Table top for Table_Custom: very dark slate with a soft centre glow and a vignette, so the navy player mats and the main board stand out.
Usage: python make_table.py [--out TTS_work\table.png]. build_save.py copies it to the assets folder and points the save's TableURL at it.
The custom table stretches this image over the whole top, so it has no shapes that would distort: only gradients and fine grain."""
import argparse, os
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('--out', default=r'E:\Media\Board Games\TTS_work\table.png')
a = ap.parse_args()
W, H = 4096, 2048
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
u, v = xx / W - 0.5, yy / H - 0.5
base = np.array([18, 22, 30], dtype=np.float32)
glow = np.exp(-((u / 0.55) ** 2 + (v / 0.55) ** 2))[..., None] * np.array([10, 12, 16], dtype=np.float32)
vig = (1 - 0.55 * np.clip((np.abs(u) * 2) ** 3 + (np.abs(v) * 2) ** 3, 0, 1))[..., None]
img = (base + glow) * vig
rng = np.random.default_rng(7)
img += rng.normal(0, 1.6, (H, W, 1)).astype(np.float32)          # fine felt grain
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB').save(a.out)
print('wrote', a.out, (W, H))
