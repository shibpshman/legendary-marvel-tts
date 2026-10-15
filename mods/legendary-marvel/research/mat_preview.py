import os, glob
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
SRC  = r'E:\Media\Board Games\Marvel Legendary Cards'
WORK = r'E:\Media\Board Games\TTS_work'
IMG  = r'E:\Documents\My Games\Tabletop Simulator\Mods\Images'
KEYS = {
    'MOD board A (geekdo, 5 objects)': 'httpscfgeekdoimagescomimagepageimgGEPGkSM9tZAv8bqFaqoHp0LZq8fitin900x600filtersnoupscalepic1727283jpg',
    'MOD board B (imgur, 1 object)':   'httpsiimgurcom1lNZvGsjpg',
}
CANDS = [r'Legendary_Universal_Mat_large_v6.5.png', r'Rules etc\Legendary_Mat.png',
         r'Rules etc\Legendary_Universal_Mat_large.png', r'Rules etc\SHST3_Legendary.png',
         r'mat_bag_full_color.jpg']
items = []
for label, k in KEYS.items():
    hits = glob.glob(os.path.join(IMG, k + '.*'))
    bk = os.path.join(WORK, 'cache_backup', os.path.basename(hits[0])) if hits else ''
    p = bk if os.path.exists(bk) else (hits[0] if hits else None)
    if p: items.append((label, Image.open(p).convert('RGB')))
for c in CANDS: items.append((c, Image.open(os.path.join(SRC, c)).convert('RGB')))
H = 420; tiles = []
for label, im in items:
    t = im.resize((int(im.size[0] * H / im.size[1]), H), Image.LANCZOS)
    d = ImageDraw.Draw(t); d.rectangle((0, 0, t.size[0], 22), fill=(0, 0, 0))
    d.text((4, 4), f'{label}  {im.size[0]}x{im.size[1]}', fill=(255, 255, 0)); tiles.append(t)
W = 1800; rows, row, w = [], [], 0
for t in tiles:
    if row and w + t.size[0] > W: rows.append(row); row, w = [], 0
    row.append(t); w += t.size[0] + 10
rows.append(row)
sheet = Image.new('RGB', (W, len(rows) * (H + 10)), (40, 40, 40)); y = 0
for r in rows:
    x = 0
    for t in r: sheet.paste(t, (x, y)); x += t.size[0] + 10
    y += H + 10
out = os.path.join(WORK, 'asset_preview'); os.makedirs(out, exist_ok=True)
sheet.save(os.path.join(out, 'mats.jpg'), quality=88); print('wrote', os.path.join(out, 'mats.jpg'))