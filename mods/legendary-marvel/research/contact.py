import os, sys, csv
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
SRC  = r'E:\Media\Board Games\Marvel Legendary Cards'
WORK = r'E:\Media\Board Games\TTS_work'
TW, TH, COLS = 110, 154, 8

rows = list(csv.DictReader(open(os.path.join(WORK, 'matches.csv'), encoding='utf-8')))
os.makedirs(os.path.join(WORK, 'contact'), exist_ok=True)
for suf in sys.argv[1:]:
    rs = sorted((r for r in rows if r['sheet'].endswith(suf)), key=lambda r: int(r['idx']))[:70]
    if not rs: print('no rows for', suf); continue
    n = len(rs); nrows = (n + COLS - 1) // COLS
    tile_w, tile_h = 2*TW + 8, TH + 14
    canvas = Image.new('RGB', (COLS*tile_w, nrows*tile_h), (30, 30, 30))
    d = ImageDraw.Draw(canvas)
    with Image.open(os.path.join(WORK, 'orig', rs[0]['sheet'])) as sh:
        sh = sh.convert('RGB'); W, H = sh.size
        for i, r in enumerate(rs):
            nx, ny, idx = int(r['nx']), int(r['ny']), int(r['idx'])
            c, rr = idx % nx, idx // nx
            cell = sh.crop((round(c*W/nx), round(rr*H/ny), round((c+1)*W/nx), round((rr+1)*H/ny)))
            cell.thumbnail((TW, TH))
            try:
                with Image.open(os.path.join(SRC, r['best_card'])) as cd:
                    cd = cd.convert('RGB')
                    rot = r.get('rot', '0')
                    if rot == '90': cd = cd.rotate(90, expand=True)
                    elif rot == '270': cd = cd.rotate(-90, expand=True)
                    cd.thumbnail((TW, TH))
            except Exception:
                cd = Image.new('RGB', (TW, TH), (90, 0, 0))
            x, y = (i % COLS)*tile_w, (i // COLS)*tile_h
            canvas.paste(cell, (x, y + 14)); canvas.paste(cd, (x + TW + 4, y + 14))
            d.text((x + 2, y + 1), f"#{idx} {float(r['sim']):.2f} {r.get('status','?')[:1]} c{r.get('cluster','')}", fill=(255, 255, 0))
    out = os.path.join(WORK, 'contact', suf.split('.')[0] + '.png')
    canvas.save(out); print(out)