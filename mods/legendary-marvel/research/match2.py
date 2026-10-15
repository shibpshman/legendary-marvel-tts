import os, json, csv, collections
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
from scipy.optimize import linear_sum_assignment
Image.MAX_IMAGE_PIXELS = None

SRC  = r'E:\Media\Board Games\Marvel Legendary Cards'
WORK = r'E:\Media\Board Games\TTS_work'
TW, TH, XW, XH = 32, 44, 96, 32
OK, WEAK, DUP_PENALTY, TOPK = 0.85, 0.70, 0.04, 8

def _n(a):
    a = a - a.mean()
    return a / (np.linalg.norm(a) + 1e-6)

def feats(im):
    im = im.convert('RGB'); w, h = im.size
    c = im.crop((int(w*.08), int(h*.06), int(w*.92), int(h*.94)))
    k = min(c.width // (TW*4), c.height // (TH*4))
    if k > 1: c = c.reduce(k)
    a = np.asarray(c.resize((TW, TH), Image.LANCZOS), dtype=np.float32).ravel()
    t = im.crop((int(w*.10), int(h*.60), int(w*.90), int(h*.93))).convert('L')
    k = min(t.width // (XW*4), t.height // (XH*4))
    if k > 1: t = t.reduce(k)
    b = np.asarray(t.resize((XW, XH), Image.LANCZOS), dtype=np.float32).ravel()
    return _n(a), _n(b), float(a.std())

def card_job(path):
    try:
        with Image.open(path) as im0:
            w0, h0 = im0.size
            if 0.9 < w0 / h0 < 1.1: return path, None, None      # pre-built sheet, skip
            im = im0.convert('RGB')
        k = max(1, min(im.size) // 800)
        if k > 1: im = im.reduce(k)
        out = []
        for rot, v in (('0', im), ('90', im.rotate(90, expand=True)), ('270', im.rotate(-90, expand=True))):
            a, b, _ = feats(v); out.append((rot, a, b))
        return path, out, (w0, h0)
    except Exception:
        return path, None, None

def build_lib():
    cache = os.path.join(WORK, 'thumbs2.npz')
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        return list(z['paths']), z['A'], z['B'], z['dims']
    files = []
    for top in ('Base Sets', 'Expansions'):
        for r, _, fs in os.walk(os.path.join(SRC, top)):
            files += [os.path.join(r, f) for f in fs if f.lower().endswith('.png')]
    print(len(files), 'png files; building features (several minutes)...')
    paths, A, B, dims = [], [], [], []
    with ProcessPoolExecutor() as ex:
        for i, (p, out, d) in enumerate(ex.map(card_job, files, chunksize=4), 1):
            if out:
                paths.append(p); dims.append(d)
                for rot, a, b in out: A.append(a); B.append(b)
            if i % 200 == 0: print(i, '/', len(files))
    A = np.stack(A).astype(np.float32); B = np.stack(B).astype(np.float32)
    dims = np.array(dims)
    np.savez(cache, paths=np.array(paths, dtype=object), A=A, B=B, dims=dims)
    return paths, A, B, dims

def main():
    out = open(os.path.join(WORK, 'match2_out.txt'), 'w', encoding='utf-8')
    def p(*a):
        print(*a); print(*a, file=out)

    paths, A, B, dims = build_lib()
    nf = len(paths); ROTS = ['0', '90', '270']
    p(f'library: {nf} cards x 3 orientations')
    manifest = json.load(open(os.path.join(WORK, 'manifest.json')))
    orig = os.path.join(WORK, 'orig')
    rows, tot = [], collections.Counter()
    claimed = collections.defaultdict(set)
    bad_sheets = []
    p('\nsheet | grid | cell | used | blank | ok | weak | none | changed-by-assignment')
    for m in manifest:
        if not m['file'] or not m['used']: continue
        nx, ny = m['nx'], m['ny']
        cells = []
        with Image.open(os.path.join(orig, m['file'])) as im:
            im = im.convert('RGB'); W, H = im.size
            blank = 0
            for idx in m['used']:
                c, r = idx % nx, idx // nx
                if r >= ny: continue
                box = (round(c*W/nx), round(r*H/ny), round((c+1)*W/nx), round((r+1)*H/ny))
                a, b, s = feats(im.crop(box))
                if s < 6: blank += 1; continue
                cells.append((idx, a, b))
        if not cells: continue
        Ca = np.stack([c[1] for c in cells]); Cb = np.stack([c[2] for c in cells])
        S3 = (0.45 * (Ca @ A.T) + 0.55 * (Cb @ B.T)).reshape(len(cells), nf, 3)
        Sf, Rf = S3.max(2), S3.argmax(2)
        k = min(TOPK, nf - 1)
        cand = np.unique(np.argpartition(-Sf, k, axis=1)[:, :k])
        Sc = Sf[:, cand]
        cost = np.hstack([-Sc, -(Sc - DUP_PENALTY)])
        ri, ci = linear_sum_assignment(cost)
        ok = weak = none = changed = 0
        for i, j in zip(ri, ci):
            f = int(cand[j % len(cand)]); sim = float(Sf[i, f]); rot = ROTS[int(Rf[i, f])]
            am = int(np.argmax(Sf[i])); asim = float(Sf[i, am])
            status = 'ok' if sim >= OK else 'weak' if sim >= WEAK else 'none'
            ok += status == 'ok'; weak += status == 'weak'; none += status == 'none'
            changed += f != am
            if status == 'ok': claimed[f].add(m['file'])
            rows.append((m['file'], cells[i][0], nx, ny, W // nx, H // ny, os.path.relpath(paths[f], SRC),
                         round(sim, 4), round(asim, 4), rot, status, am != f,
                         os.path.relpath(paths[am], SRC), int(dims[f][0]), int(dims[f][1])))
        tot.update(ok=ok, weak=weak, none=none)
        if none >= 0.5 * len(cells): bad_sheets.append(m['file'][-20:])
        p(f"{m['file'][-20:]:>20} | {nx}x{ny} | {W//nx}x{H//ny} | {len(m['used'])} | {blank} | {ok} | {weak} | {none} | {changed}")

    for name in ('matches.csv',):
        pth = os.path.join(WORK, name)
        if os.path.exists(pth) and not os.path.exists(os.path.join(WORK, 'matches_v1.csv')):
            os.replace(pth, os.path.join(WORK, 'matches_v1.csv'))
    with open(os.path.join(WORK, 'matches.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['sheet', 'idx', 'nx', 'ny', 'cell_w', 'cell_h', 'best_card', 'sim', 'argmax_sim', 'rot',
                    'status', 'changed', 'argmax_card', 'card_w', 'card_h'])
        w.writerows(rows)
    p(f"\ncells: ok={tot['ok']} weak={tot['weak']} none={tot['none']}  (thresholds ok>={OK}, weak>={WEAK})")
    p(f'library cards used by at least one ok cell: {len(claimed)} / {nf}')
    p('sheets with >=50% none (likely content not in your library):', bad_sheets)
    rot_n = sum(1 for r in rows if r[9] != '0' and r[10] == 'ok')
    p(f'ok cells needing rotation: {rot_n}')

if __name__ == '__main__':
    main()