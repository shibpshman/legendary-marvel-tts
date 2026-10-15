import os, json, csv, collections
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
Image.MAX_IMAGE_PIXELS = None

SRC  = r'E:\Media\Board Games\Marvel Legendary Cards'
WORK = r'E:\Media\Board Games\TTS_work'
TW, TH = 32, 44
CROP = (0.08, 0.06, 0.92, 0.94)       # ignore rounded corners and edges

def vec(im):
    im = im.convert('RGB'); w, h = im.size
    im = im.crop((int(w*CROP[0]), int(h*CROP[1]), int(w*CROP[2]), int(h*CROP[3])))
    k = min(im.width // (TW*4), im.height // (TH*4))
    if k > 1: im = im.reduce(k)
    a = np.asarray(im.resize((TW, TH), Image.LANCZOS), dtype=np.float32).ravel()
    s = float(a.std()); a = a - a.mean()
    return a / (np.linalg.norm(a) + 1e-6), s

def card_job(path):
    try:
        with Image.open(path) as im:
            w, h = im.size
            if not (0.6 <= w / h <= 0.8): return path, None, (w, h)
            return path, vec(im)[0], (w, h)
    except Exception as e:
        return path, None, ('ERR', str(e))

def main():
    out = open(os.path.join(WORK, 'match_out.txt'), 'w', encoding='utf-8')
    def p(*a):
        print(*a); print(*a, file=out)

    cache = os.path.join(WORK, 'thumbs.npz')
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        paths, vecs, skipped = list(z['paths']), z['vecs'], list(z['skipped'])
    else:
        files = []
        for top in ('Base Sets', 'Expansions'):
            for r, _, fs in os.walk(os.path.join(SRC, top)):
                files += [os.path.join(r, f) for f in fs if f.lower().endswith('.png')]
        print(len(files), 'png files; thumbnailing (takes a while)...')
        paths, vs, skipped = [], [], []
        with ProcessPoolExecutor() as ex:
            for i, (pth, v, dim) in enumerate(ex.map(card_job, files, chunksize=8), 1):
                if v is None: skipped.append(f'{pth}  {dim}')
                else: paths.append(pth); vs.append(v)
                if i % 200 == 0: print(i, '/', len(files))
        vecs = np.stack(vs).astype(np.float32)
        np.savez(cache, paths=np.array(paths, dtype=object), vecs=vecs, skipped=np.array(skipped, dtype=object))
    p(f'library: {len(paths)} portrait card images; {len(skipped)} skipped (non-portrait, sheets, errors)')
    for s in skipped[:25]: p('  skipped:', s)

    manifest = json.load(open(os.path.join(WORK, 'manifest.json')))
    orig = os.path.join(WORK, 'orig')
    rows, bests = [], []
    p('\nsheet | grid | cell px | used | blank | sim>=.90 | .80-.90 | <.80')
    for m in manifest:
        if not m['file'] or not m['used']: continue
        nx, ny = m['nx'], m['ny']
        with Image.open(os.path.join(orig, m['file'])) as im:
            im = im.convert('RGB'); W, H = im.size
            blank = hi = mid = lo = 0
            for idx in m['used']:
                c, r = idx % nx, idx // nx
                if r >= ny: continue
                box = (round(c*W/nx), round(r*H/ny), round((c+1)*W/nx), round((r+1)*H/ny))
                v, s = vec(im.crop(box))
                if s < 6: blank += 1; continue
                sims = vecs @ v
                t = np.argpartition(-sims, 1)[:2]
                b = t[np.argmax(sims[t])]; sec = t[np.argmin(sims[t])]
                sim, sim2 = float(sims[b]), float(sims[sec])
                hi += sim >= .90; mid += .80 <= sim < .90; lo += sim < .80
                rows.append((m['file'], idx, nx, ny, W // nx, H // ny, os.path.relpath(paths[b], SRC), round(sim, 4), round(sim2, 4)))
                bests.append((sim, int(b)))
        p(f"{m['file'][-20:]:>20} | {nx}x{ny} | {W//nx}x{H//ny} | {len(m['used'])} | {blank} | {hi} | {mid} | {lo}")

    with open(os.path.join(WORK, 'matches.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['sheet', 'idx', 'nx', 'ny', 'cell_w', 'cell_h', 'best_card', 'sim', 'second_sim']); w.writerows(rows)

    sims = np.array([s for s, _ in bests])
    h, _ = np.histogram(sims, bins=[-1, .5, .7, .8, .9, .95, .98, 1.01])
    p('\nbest-similarity histogram (<.5, .5-.7, .7-.8, .8-.9, .9-.95, .95-.98, >=.98):', h.tolist())
    chosen = {b for s, b in bests if s >= .90}
    p(f'library cards matched by at least one cell at >=.90: {len(chosen)} / {len(paths)}')
    un = [os.path.relpath(paths[i], SRC) for i in range(len(paths)) if i not in chosen]
    p('library cards NOT matched, by folder:')
    for k, c in collections.Counter('\\'.join(u.split('\\')[:3]) for u in un).most_common(40): p(f'  {c:>4}  {k}')
    p('\nlowest-similarity cells:')
    for r in sorted(rows, key=lambda r: r[7])[:25]: p(' ', r[0][-20:], 'idx', r[1], r[6], r[7])

if __name__ == '__main__':
    main()