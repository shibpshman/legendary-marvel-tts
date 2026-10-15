import os, glob
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

COLOR_MATCH = True   # tint the new card back toward the mod's original indigo

SRC  = r'E:\Media\Board Games\Marvel Legendary Cards'
WORK = r'E:\Media\Board Games\TTS_work'
IMG  = r'E:\Documents\My Games\Tabletop Simulator\Mods\Images'
NEW, PREV = os.path.join(WORK, 'new'), os.path.join(WORK, 'asset_preview')
INP, UP = os.path.join(WORK, 'assets_in'), os.path.join(WORK, 'assets_up')
for d in (NEW, PREV, INP, UP): os.makedirs(d, exist_ok=True)

K_BACK    = 'httpssteamusercontentaakamaihdnetugc17659451668021992586D57DA73D0C48E3DC1B8F77577B87F20ECD7E3BC'
K_BOARD_A = 'httpscfgeekdoimagescomimagepageimgGEPGkSM9tZAv8bqFaqoHp0LZq8fitin900x600filtersnoupscalepic1727283jpg'
K_BOARD_B = 'httpsiimgurcom1lNZvGsjpg'

# label, cache key, source file (glob ok), crop to old aspect?, longest-side cap
JOBS = [
    ('cardback', K_BACK, os.path.join(SRC, r'Rules etc\LegendaryCardBack_ColorAdjusted (1).jpg'), True, 4096),
    ('boardB', K_BOARD_B, os.path.join(SRC, r'Rules etc\Legendary_Universal_Mat_large.png'), False, 8704),
    ('boardA', K_BOARD_A, os.path.join(UP, 'boardA*'), False, 8192),
]

def match_bg(old, new):
    o = np.asarray(old.resize((250, 350)), dtype=np.float32)
    n = np.asarray(new.resize((250, 350)), dtype=np.float32)
    mo, mn = o.mean(2) < 90, n.mean(2) < 90          # dark background pixels only
    gain = o[mo].mean(0) / n[mn].mean(0)
    a = np.asarray(new, dtype=np.float32)
    w = np.clip(1 - a.mean(2) / 200, 0, 1)[..., None]  # protect the bright logo
    a = a * (1 + (gain - 1) * w)
    return Image.fromarray(np.clip(a, 0, 255).astype('uint8'))

for label, key, srcpat, crop, cap in JOBS:
    hits = glob.glob(os.path.join(IMG, key + '.*'))
    if not hits: print(label, 'not in cache, skipped'); continue
    name = os.path.basename(hits[0]); ext = os.path.splitext(name)[1].lower()
    bk = os.path.join(WORK, 'cache_backup', name)
    old = Image.open(bk if os.path.exists(bk) else hits[0]).convert('RGB')
    old.save(os.path.join(INP, label + '.png'))
    srcs = glob.glob(srcpat)
    if not srcs: print(f'{label}: no source yet, original exported to assets_in\\{label}.png'); continue
    new = Image.open(srcs[0]).convert('RGB')
    if label == 'cardback' and COLOR_MATCH: new = match_bg(old, new)
    ar = old.size[0] / old.size[1]; w, h = new.size
    if crop and abs(w / h - ar) > 0.002:
        if w / h > ar: nw = int(round(h * ar)); x = (w - nw) // 2; new = new.crop((x, 0, x + nw, h))
        else: nh = int(round(w / ar)); y = (h - nh) // 2; new = new.crop((0, y, w, y + nh))
    s = min(1.0, cap / max(new.size))
    if s < 1: new = new.resize((int(new.size[0] * s), int(new.size[1] * s)), Image.LANCZOS)
    out = os.path.join(NEW, name)
    if ext in ('.jpg', '.jpeg'): new.save(out, 'JPEG', quality=94)
    else: new.save(out, 'PNG', compress_level=3)
    H = 700
    a = old.resize((int(old.size[0] * H / old.size[1]), H), Image.LANCZOS)
    b = new.resize((int(new.size[0] * H / new.size[1]), H), Image.LANCZOS)
    pv = Image.new('RGB', (a.size[0] + b.size[0] + 20, H), (255, 0, 255))
    pv.paste(a, (0, 0)); pv.paste(b, (a.size[0] + 20, 0))
    pv.save(os.path.join(PREV, label + '.jpg'), quality=90)
    print(f'{label}: old {old.size} -> new {new.size}  (staged as {name[-30:]})')