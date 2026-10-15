import os, sys, json, csv, collections, pickle, re, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import cv2
from PIL import Image
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from match2 import feats, build_lib, SRC, WORK
from match4 import hp, cell_tmpl, classify, ROTS, TOPK, TIE, LAM, TAU
Image.MAX_IMAGE_PIXELS = None

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def tscore(a, b):
    if len(a) < 3 or not b: return None
    if a in b: return 1.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return min(1.0, sum(x.size for x in sm.get_matching_blocks()) / len(a))

def main():
    out = open(os.path.join(WORK, 'match5_out.txt'), 'w', encoding='utf-8')
    def p(*a):
        print(*a); print(*a, file=out)
    paths, A, B, dims = build_lib(); nf = len(paths)
    rels = [os.path.relpath(q, SRC) for q in paths]
    tp = os.path.join(WORK, 'titles.json')
    titles = json.load(open(tp, encoding='utf-8')) if os.path.exists(tp) else {}
    ocr = [titles.get(r, '') for r in rels]; tit = [norm(t) for t in ocr]
    p(f'OCR titles for {sum(1 for t in tit if t)} / {nf} library cards')
    uniq = np.array([('Tactic' in os.path.basename(q)) or ('\\Masterminds\\' in q) for q in paths])
    winp = os.path.join(WORK, 'textwin.pkl')
    WIN = pickle.load(open(winp, 'rb')) if os.path.exists(winp) else {}

    def lib_window(f, rot):
        key = (f, rot)
        if key not in WIN:
            with Image.open(paths[f]) as im0:
                im = im0.convert('RGB')
            k = max(1, min(im.size) // 800)
            if k > 1: im = im.reduce(k)
            if rot == '90': im = im.rotate(90, expand=True)
            elif rot == '270': im = im.rotate(-90, expand=True)
            g = np.asarray(im.convert('L').resize((400, 570), Image.LANCZOS), dtype=np.float32)
            WIN[key] = hp(g)[313:553, 24:376].astype(np.float16)
        return WIN[key].astype(np.float32)

    manifest = json.load(open(os.path.join(WORK, 'manifest.json')))
    orig = os.path.join(WORK, 'orig')
    rows, tot, reranked, claimed, tconf = [], collections.Counter(), 0, set(), 0
    p(f'TAU={TAU}\nsheet | grid | cell | used | clusters | sure | weak | ambig | forced | none')
    for m in manifest:
        if not m['file'] or not m['used']: continue
        nx, ny = m['nx'], m['ny']; cells = []
        with Image.open(os.path.join(orig, m['file'])) as im0:
            im = im0.convert('RGB')
        W, H = im.size
        for idx in m['used']:
            c, r = idx % nx, idx // nx
            if r >= ny: continue
            box = (round(c*W/nx), round(r*H/ny), round((c+1)*W/nx), round((r+1)*H/ny))
            crop = im.crop(box); a, b, s = feats(crop)
            if s >= 6: cells.append((idx, a, b, crop))
        if not cells: continue
        Ca = np.stack([c[1] for c in cells]); Cb = np.stack([c[2] for c in cells])
        Scc = 0.45 * (Ca @ Ca.T) + 0.55 * (Cb @ Cb.T)
        nm0 = {int(k): v for k, v in (m.get('names') or {}).items()}
        nk = [norm(nm0.get(c[0], '')) for c in cells]
        for i in range(len(cells)):
            for j in range(len(cells)):
                if nk[i] and nk[j] and nk[i] != nk[j]: Scc[i, j] = 0
        n, lab = connected_components(csr_matrix(Scc >= TAU), directed=False)
        S3 = (0.45 * (Ca @ A.T) + 0.55 * (Cb @ B.T)).reshape(len(cells), nf, 3)
        S3c = np.stack([S3[lab == k].mean(0) for k in range(n)])
        Sf, Rf = S3c.max(2), S3c.argmax(2)
        Sv = Sf.copy()

        names = {int(k): v for k, v in (m.get('names') or {}).items()}
        nick, tsc = {}, {}
        for k in range(n):
            nick[k] = next((names[cells[i][0]] for i in range(len(cells)) if lab[i] == k and names.get(cells[i][0])), '')
            a = norm(nick[k])
            if len(a) < 3: continue
            cand_f = {int(f) for f in np.argsort(-Sv[k])[:12]} | {f for f in range(nf) if tit[f] and a in tit[f]}
            for f in cand_f:
                if Sv[k, f] < 0.50: continue
                s = tscore(a, tit[f])
                if s is None: continue
                tsc[(k, f)] = s
                Sf[k, f] += 0.20 if s >= 0.90 else 0.10 if s >= 0.80 else (-0.05 if s < 0.50 else 0.0)

        for k in range(n):                       # text re-rank of near-ties
            order = np.argsort(-Sf[k])[:TOPK]
            tie = [int(f) for f in order if Sf[k, f] >= Sf[k, order[0]] - TIE][:6]
            if len(tie) < 2: continue
            rep = next(cells[i][3] for i in range(len(cells)) if lab[i] == k)
            tm = cell_tmpl(rep)
            ncc = {f: float(cv2.matchTemplate(lib_window(f, ROTS[int(Rf[k, f])]), tm, cv2.TM_CCOEFF_NORMED).max()) for f in tie}
            mx = max(ncc.values())
            for f in tie: Sf[k, f] += LAM * (ncc[f] - mx)
            reranked += 1

        kk = min(TOPK, nf - 1)
        cand = np.unique(np.argpartition(-Sf, kk, axis=1)[:, :kk])
        cf, cp = [], []
        for f in cand:
            pens = [0.0, 0.04] if uniq[f] else [0.002 * j for j in range(10)]
            cf += [int(f)] * len(pens); cp += pens
        if len(cf) < n:
            for f in np.argsort(-Sf.max(0))[:n]:
                if int(f) not in set(cf): cf.append(int(f)); cp.append(0.0)
        cf, cp = np.array(cf), np.array(cp)
        ri, ci = linear_sum_assignment(-(Sf[:, cf] - cp[None, :]))
        assign = {int(i): int(cf[j]) for i, j in zip(ri, ci)}

        cnt = collections.Counter()
        for ci_, (idx, a, b, _) in enumerate(cells):
            k = int(lab[ci_]); f = assign[k]; sim = float(Sv[k, f]); rot = ROTS[int(Rf[k, f])]
            margin = float(Sf[k, f] - np.delete(Sf[k], f).max())
            ts = tsc.get((k, f))
            status = classify(sim, margin)
            if ts is not None and ts >= 0.90 and sim >= 0.55:
                status = 'sure'; tconf += 1
            cnt[status] += 1
            if status == 'sure': claimed.add(f)
            rows.append((m['file'], idx, nx, ny, W // nx, H // ny, rels[f], round(sim, 4), rot, status, k,
                         int((lab == k).sum()), round(margin, 4), int(dims[f][0]), int(dims[f][1]),
                         nick[k], ocr[f], '' if ts is None else round(ts, 3)))
        tot.update(cnt)
        p(f"{m['file'][-20:]:>20} | {nx}x{ny} | {W//nx}x{H//ny} | {len(m['used'])} | {n} | "
          f"{cnt['sure']} | {cnt['weak']} | {cnt['ambig']} | {cnt['forced']} | {cnt['none']}")

    pickle.dump(WIN, open(winp, 'wb'))
    pth = os.path.join(WORK, 'matches.csv')
    if os.path.exists(pth): os.replace(pth, os.path.join(WORK, 'matches_prev.csv'))
    with open(pth, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['sheet', 'idx', 'nx', 'ny', 'cell_w', 'cell_h', 'best_card', 'sim', 'rot', 'status',
                    'cluster', 'csize', 'margin', 'card_w', 'card_h', 'nick', 'ocr_title', 'tscore'])
        w.writerows(rows)
    p(f"\ncells: {dict(tot)}   title-confirmed: {tconf}   clusters re-ranked by text: {reranked}")
    p(f'library cards used by a sure cell: {len(claimed)} / {nf}')
    t = collections.Counter(r[9] for r in rows if 'Tactic' in r[6] or '\\Masterminds\\' in r[6])
    p('tactic/mastermind cells by status:', dict(t))

if __name__ == '__main__':
    main()