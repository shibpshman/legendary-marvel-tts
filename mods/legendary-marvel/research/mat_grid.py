import os
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
SRC  = r'E:\Media\Board Games\Marvel Legendary Cards'
OUT  = r'E:\Media\Board Games\TTS_work\asset_preview'
os.makedirs(OUT, exist_ok=True)
im = Image.open(os.path.join(SRC, r'Rules etc\Legendary_Universal_Mat_large.png')).convert('RGB')
W = 4800; H = round(W * im.size[1] / im.size[0])
im = im.resize((W, H), Image.LANCZOS)
try: font = ImageFont.truetype('arial.ttf', 30)
except Exception: font = ImageFont.load_default()
d = ImageDraw.Draw(im, 'RGBA')
def lab(xy, t): d.text(xy, t, fill=(255, 255, 0, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0, 255))
for i in range(41):
    u = i / 40; x = round(u * (W - 1)); major = i % 2 == 0
    d.line([(x, 0), (x, H)], fill=(255, 255, 0, 210 if major else 70), width=3 if major else 1)
    if major:
        for y in (6, H - 40): lab((x + 4, y), f'{u:.2f}')
for j in range(41):
    v = j / 40; y = round(v * (H - 1)); major = j % 2 == 0
    d.line([(0, y), (W, y)], fill=(255, 255, 0, 210 if major else 70), width=3 if major else 1)
    if major:
        for x in (8, W - 110): lab((x, y + 4), f'{v:.2f}')
im.resize((2400, round(2400 * H / W)), Image.LANCZOS).save(os.path.join(OUT, 'grid_full.jpg'), quality=85)
im.crop((0, 0, int(W * 0.52), H)).save(os.path.join(OUT, 'grid_left.jpg'), quality=85)
im.crop((int(W * 0.48), 0, W, H)).save(os.path.join(OUT, 'grid_right.jpg'), quality=85)
print('wrote grid_full.jpg, grid_left.jpg, grid_right.jpg in', OUT)