import os, sys, csv, json, collections
from concurrent.futures import ProcessPoolExecutor
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

SRC  = r'E:\Media\Board Games\Marvel Legendary Cards'
WORK = r'E:\Media\Board Games\TTS_work'
MAXW, MAXCELL, MIN_GAIN = 10000, 2000, 1.3
SKIP = ('D0E247ACC36F3655.png', '3A58A7E95DAF637D.png', 'E6DAE27A60C002D0.png')   # fan sheets

def process(args):
    file, nx, ny, rows = args
    with Image.open(os.path.join(WORK, 'orig', file)) as im0:
        im = im0.convert('RGB')
    W, H = im.size
    ow, oh = W / nx, H / ny
    cw = min(MAXW // nx, MAXCELL, int(MAXW * ow / (oh * ny)))
    if cw < MIN_GAIN * ow: return file, 'skipped: no gain', 0
    ch = int(cw * oh / ow)
    out = im.resize((nx * cw, ny * ch), Image.LANCZOS)
    cache, n = {}, 0
    for r in rows:
        idx = int(r['idx']); c, rr = idx % nx, idx // nx
        if rr >= ny: continue
        key = (r['best_card'], r['rot'])
        if key not in cache:
            with Image.open(os.path.join(SRC, r['best_card'])) as cim0:
                cim = cim0.convert('RGB')
            if r['rot'] == '90': cim = cim.rotate(90, expand=True)
            elif r['rot'] == '270': cim = cim.rotate(-90, expand=True)
            cache[key] = cim.resize((cw, ch), Image.LANCZOS)
        out.paste(cache[key], (c * cw, rr * ch)); n += 1
    dst = os.path.join(WORK, 'new', file)
    if file.lower().endswith('.jpg'): out.save(dst, 'JPEG', quality=93, subsampling=0)
    else: out.save(dst, 'PNG', compress_level=3)
    return file, f'{nx*cw}x{ny*ch}', n

def main():
    only = sys.argv[1:]
    rows = list(csv.DictReader(open(os.path.join(WORK, 'matches.csv'), encoding='utf-8')))
    by = collections.defaultdict(list)
    for r in rows: by[r['sheet']].append(r)
    os.makedirs(os.path.join(WORK, 'new'), exist_ok=True)
    jobs, review = [], []
    for f, rs in by.items():
        if f.endswith(SKIP): review += rs; continue
        if only and not any(f.endswith(o) for o in only): continue
        sure = [r for r in rs if r['status'] == 'sure']
        review += [r for r in rs if r['status'] != 'sure']
        if sure: jobs.append((f, int(rs[0]['nx']), int(rs[0]['ny']), sure))
    print(len(jobs), 'sheets to build')
    with open(os.path.join(WORK, 'build_report.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(['file', 'new_size_or_note', 'cells_replaced'])
        with ProcessPoolExecutor(max_workers=3) as ex:
            for f, info, n in ex.map(process, jobs):
                print(f[-24:], info, n); w.writerow([f, info, n])
    with open(os.path.join(WORK, 'review.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(['sheet', 'idx', 'status', 'best_card', 'sim', 'margin'])
        for r in review:
            if r['status'] != 'sure': w.writerow([r['sheet'], r['idx'], r['status'], r['best_card'], r['sim'], r['margin']])

if __name__ == '__main__':
    main()