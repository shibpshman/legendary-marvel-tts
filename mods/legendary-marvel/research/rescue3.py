import csv, os, re, json, difflib, collections
from PIL import Image
SRC  = r'E:\Media\Board Games\Marvel Legendary Cards'
WORK = r'E:\Media\Board Games\TTS_work'
SKIP_SHEETS = ('A3BC2BAB59D20587.png',)   # custom Horror sheet, not in library
LABELS = ('ambition', 'villain', 'mastermind', 'tactic', 'henchman', 'hero', 'scheme')
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def toks(s): return re.findall(r'[a-z0-9]+', (s or '').lower())
def key(s): return frozenset(t for t in toks(s) if t not in ('the', 'core', 'copy'))
def tscore(a, b):
    a, b = norm(a), norm(b)
    if len(a) < 3 or not b: return None
    if a in b: return 1.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return min(1.0, sum(x.size for x in sm.get_matching_blocks()) / len(a))
def consistent(nick, ocr):
    b = norm(ocr)
    for w in LABELS: b = b.replace(w, '')
    if len(b) < 8: return True                      # nothing readable to contradict
    if (tscore(nick, ocr) or 0) >= 0.6 or b in norm(nick): return True
    sig = [t for t in toks(nick) if len(t) >= 4]
    return bool(sig) and sum(t in b for t in sig) / len(sig) >= 0.5

titles = json.load(open(os.path.join(WORK, 'titles.json'), encoding='utf-8'))
lib = []
for top in ('Base Sets', 'Expansions'):
    for r, _, fs in os.walk(os.path.join(SRC, top)):
        for f in fs:
            if f.lower().endswith('.png'):
                full = os.path.join(r, f); rel = os.path.relpath(full, SRC)
                lib.append({'full': full, 'rel': rel, 'stem': os.path.splitext(f)[0], 'ocr': titles.get(rel, '')})
by_key, by_rel = collections.defaultdict(list), {}
for i, L in enumerate(lib):
    by_rel[L['rel']] = i
    k = key(L['stem'])
    if len(k) >= 2: by_key[k].append(i)

def dims(i):
    with Image.open(lib[i]['full']) as im: return im.size
def pick(idxs):
    idxs = [i for i in idxs if dims(i)[0] <= dims(i)[1]]
    good = [i for i in idxs if 'copy' not in lib[i]['stem'].lower()] or idxs
    return sorted(good, key=lambda i: len(lib[i]['rel']))[0] if good else None

manifest = json.load(open(os.path.join(WORK, 'manifest.json')))
names = {m['file']: (m.get('names') or {}) for m in manifest if m['file']}
rows = list(csv.DictReader(open(os.path.join(WORK, 'matches_pre_rescue.csv'), encoding='utf-8')))
fields = list(rows[0].keys())
for r in rows: r['nick'] = names.get(r['sheet'], {}).get(str(r['idx']), '')

out = open(os.path.join(WORK, 'rescue_out.txt'), 'w', encoding='utf-8')
def p(*a):
    print(*a); print(*a, file=out)

rejected, done = [], []
def rescue(r):
    nick, n = r['nick'], norm(r['nick'])
    if len(n) < 6: return None
    c = by_key.get(key(nick), [])
    if c:
        ok = [i for i in c if consistent(nick, lib[i]['ocr'])]
        if ok:
            i = pick(ok)
            if i is not None: return i, 'filename', None
        else:
            rejected.append((r, lib[c[0]]))
    if len(n) >= 8:                                   # unique card whose own title text matches
        c = [i for i, L in enumerate(lib) if norm(L['ocr']) and (tscore(nick, L['ocr']) or 0) >= 0.9]
        if len(c) == 1 and dims(c[0])[0] <= dims(c[0])[1]: return c[0], 'ocr-title', None
    best, second, bi = 0, 0, None                      # near-identical filename (typos)
    for i, L in enumerate(lib):
        s = difflib.SequenceMatcher(None, n, norm(' '.join(t for t in toks(L['stem']) if t not in ('the', 'core', 'copy')))).ratio()
        if s > best: best, second, bi = s, best, i
        elif s > second: second = s
    if bi is not None and best >= 0.93 and best - second >= 0.03 and consistent(nick, lib[bi]['ocr']) and dims(bi)[0] <= dims(bi)[1]:
        return bi, 'fuzzy-name', None
    i = by_rel.get(r['best_card'])                     # clear visual winner
    if i is not None and float(r['sim']) >= 0.5 and float(r['margin']) >= 0.2 and consistent(nick, lib[i]['ocr']):
        return i, 'big-margin', r['rot']
    return None

for r in rows:
    if r['sheet'].endswith(SKIP_SHEETS): continue
    if r['status'] == 'sure': continue
    res = rescue(r)
    if not res: continue
    i, how, rot = res
    w, h = dims(i)
    r['best_card'], r['rot'], r['status'] = lib[i]['rel'], (rot or '0'), 'sure'
    r['card_w'], r['card_h'] = w, h; done.append((r, how))

with open(os.path.join(WORK, 'matches.csv'), 'w', newline='', encoding='utf-8') as f:
    wr = csv.DictWriter(f, fieldnames=fields); wr.writeheader(); wr.writerows(rows)

p(f'rescued: {len(done)}  ({dict(collections.Counter(h for _, h in done))})')
for r, how in done: p(f"  [{how}] {r['sheet'][-20:]} #{r['idx']} {r['nick']!r} -> {os.path.basename(r['best_card'])}")
p(f'\nLIBRARY FILES WHOSE NAME DISAGREES WITH WHAT THE CARD SAYS (rejected, cells keep original art): {len(rejected)}')
for r, L in rejected: p(f"  {r['sheet'][-20:]} #{r['idx']} {r['nick']!r}: file {L['stem']!r} actually reads {L['ocr']!r}")
left = [r for r in rows if r['status'] != 'sure']
p(f'\nstill not sure: {len(left)}')
for r in left: p(f"  {r['sheet'][-20:]} #{r['idx']} {r['status']:10} {r['nick']!r}")