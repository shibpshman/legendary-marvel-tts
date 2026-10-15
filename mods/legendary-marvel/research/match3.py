import os, sys, json, csv, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from match2 import feats, build_lib, SRC, WORK, OK, WEAK, DUP_PENALTY, TOPK
Image.MAX_IMAGE_PIXELS = None
TAU = float(os.environ.get('TAU', '0.985'))   # cell-to-cell similarity that counts as "same card"

def main():
    out = open(os.path.join(WORK, 'match3_out.txt'), 'w', encoding='utf-8')
    def p(*a):
        print(*a); print(*a, file=out)
    paths, A, B, dims = build_lib(); nf = len(paths); ROTS = ['0', '90', '270']
    manifest = json.load(open(os.path.join(WORK, 'manifest.json')))
    orig = os.path.join(WORK, 'orig')
    rows, tot, sizes, claimed, bad = [], collections.Counter(), collections.Counter(), set(), []
    p(f'TAU={TAU}\nsheet | grid | cell | used | clusters | cells ok | weak | none')
    for m in manifest:
        if not m['file'] or not m['used']: continue
        nx, ny = m['nx'], m['ny']; cells = []
        with Image.open(os.path.join(orig, m['file'])) as im:
            im = im.convert('RGB'); W, H = im.size
            for idx in m['used']:
                c, r = idx % nx, idx // nx
                if r >= ny: continue
                box = (round(c*W/nx), round(r*H/ny), round((c+1)*W/nx), round((r+1)*H/ny))
                a, b, s = feats(im.crop(box))
                if s >= 6: cells.append((idx, a, b))
        if not cells: continue
        Ca = np.stack([c[1] for c in cells]); Cb = np.stack([c[2] for c in cells])
        Scc = 0.45 * (Ca @ Ca.T) + 0.55 * (Cb @ Cb.T)
        n, lab = connected_components(csr_matrix(Scc >= TAU), directed=False)
        for k in range(n): sizes[int((lab == k).sum())] += 1
        S3 = (0.45 * (Ca @ A.T) + 0.55 * (Cb @ B.T)).reshape(len(cells), nf, 3)
        S3c = np.stack([S3[lab == k].mean(0) for k in range(n)])
        Sf, Rf = S3c.max(2), S3c.argmax(2)
        kk = min(TOPK, nf - 1)
        cand = np.unique(np.argpartition(-Sf, kk, axis=1)[:, :kk])
        if 2 * len(cand) < n: cand = np.unique(np.concatenate([cand, np.argsort(-Sf.max(0))[:n]]))
        Sc = Sf[:, cand]
        ri, ci = linear_sum_assignment(np.hstack([-Sc, -(Sc - DUP_PENALTY)]))
        assign = {int(i): int(cand[j % len(cand)]) for i, j in zip(ri, ci)}
        cnt = collections.Counter()
        for ci_, (idx, a, b) in enumerate(cells):
            k = int(lab[ci_]); f = assign[k]; sim = float(Sf[k, f]); rot = ROTS[int(Rf[k, f])]
            margin = sim - float(np.delete(Sf[k], f).max())
            status = 'ok' if sim >= OK else 'weak' if sim >= WEAK else 'none'
            cnt[status] += 1
            if status == 'ok': claimed.add(f)
            rows.append((m['file'], idx, nx, ny, W // nx, H // ny, os.path.relpath(paths[f], SRC), round(sim, 4),
                         rot, status, k, int((lab == k).sum()), round(margin, 4), int(dims[f][0]), int(dims[f][1])))
        tot.update(cnt)
        if cnt['none'] >= 0.5 * len(cells): bad.append(m['file'][-20:])
        p(f"{m['file'][-20:]:>20} | {nx}x{ny} | {W//nx}x{H//ny} | {len(m['used'])} | {n} | {cnt['ok']} | {cnt['weak']} | {cnt['none']}")

    pth = os.path.join(WORK, 'matches.csv')
    if os.path.exists(pth) and not os.path.exists(os.path.join(WORK, 'matches_v2.csv')):
        os.replace(pth, os.path.join(WORK, 'matches_v2.csv'))
    with open(pth, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['sheet', 'idx', 'nx', 'ny', 'cell_w', 'cell_h', 'best_card', 'sim', 'rot', 'status',
                    'cluster', 'csize', 'margin', 'card_w', 'card_h'])
        w.writerows(rows)
    p(f"\ncells: ok={tot['ok']} weak={tot['weak']} none={tot['none']}")
    p('cluster size histogram (size: count):', sorted(sizes.items())[:20])
    p(f'library cards used by an ok cluster: {len(claimed)} / {nf}')
    p('ok cells needing rotation:', sum(1 for r in rows if r[8] != '0' and r[9] == 'ok'))
    p('sheets with >=50% none:', bad)

if __name__ == '__main__':
    main()