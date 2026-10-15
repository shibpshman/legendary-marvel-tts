import csv, os, re, json, difflib, collections
from PIL import Image
SRC  = r'E:\Media\Board Games\Marvel Legendary Cards'
WORK = r'E:\Media\Board Games\TTS_work'
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def words(s): return frozenset(re.findall(r'[a-z0-9]+', (s or '').lower()))
def tscore(a, b):
    a, b = norm(a), norm(b)
    if len(a) < 3 or not b: return None
    if a in b: return 1.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return min(1.0, sum(x.size for x in sm.get_matching_blocks()) / len(a))

by_norm, by_words = collections.defaultdict(list), collections.defaultdict(list)
for top in ('Base Sets', 'Expansions'):
    for r, _, fs in os.walk(os.path.join(SRC, top)):
        for f in fs:
            if not f.lower().endswith('.png'): continue
            stem = os.path.splitext(f)[0]; full = os.path.join(r, f)
            by_norm[norm(stem)].append(full)
            if len(words(stem)) >= 2: by_words[words(stem)].append(full)

manifest = json.load(open(os.path.join(WORK, 'manifest.json')))
names = {m['file']: (m.get('names') or {}) for m in manifest if m['file']}
rows = list(csv.DictReader(open(os.path.join(WORK, 'matches_pre_rescue.csv'), encoding='utf-8')))
fields = list(rows[0].keys())
before = {(r['sheet'], r['idx']): (r['best_card'], r['status']) for r in rows}
for r in rows: r['nick'] = names.get(r['sheet'], {}).get(str(r['idx']), '')

out = open(os.path.join(WORK, 'rescue_out.txt'), 'w', encoding='utf-8')
def p(*a):
    print(*a); print(*a, file=out)

# A. clusters whose members have different titles: keep only members that agree with their file
clusters = collections.defaultdict(list)
for r in rows: clusters[(r['sheet'], r['cluster'])].append(r)
mixed, split = 0, []
for rs in clusters.values():
    if len({norm(r['nick']) for r in rs if norm(r['nick'])}) > 1:
        mixed += 1
        for r in rs:
            if r['status'] != 'sure' or not norm(r['nick']): continue
            stem = os.path.splitext(os.path.basename(r['best_card']))[0]
            ts = max(tscore(r['nick'], r['ocr_title']) or 0, tscore(r['nick'], stem) or 0)
            if ts < 0.9: r['status'] = 'splitfix'; split.append(r)

# B. exact-title lookup for everything that is not sure
done = []
for r in rows:
    if r['status'] == 'sure' or len(norm(r['nick'])) < 6: continue
    cands = by_norm.get(norm(r['nick'])) or by_words.get(words(r['nick'])) or []
    good = [c for c in cands if 'copy' not in os.path.basename(c).lower()] or cands
    if not good: continue
    pick = sorted(good, key=len)[0]
    with Image.open(pick) as im: w, h = im.size
    if w > h: continue
    r['best_card'] = os.path.relpath(pick, SRC); r['rot'] = '0'; r['status'] = 'sure'
    r['card_w'], r['card_h'] = w, h; done.append((r, pick))

with open(os.path.join(WORK, 'matches.csv'), 'w', newline='', encoding='utf-8') as f:
    wr = csv.DictWriter(f, fieldnames=fields); wr.writeheader(); wr.writerows(rows)
sheets = collections.OrderedDict()
for r in rows:
    if before[(r['sheet'], r['idx'])] != (r['best_card'], r['status']): sheets[r['sheet']] = 1
p(f'clusters with different titles inside: {mixed}')
p(f'\ndemoted because a merged cell disagreed with its file: {len(split)}')
for r in split: p(f"  {r['sheet'][-20:]} #{r['idx']} {r['nick']!r} was -> {os.path.basename(r['best_card'])}")
p(f'\nrescued by exact title: {len(done)}')
for r, pick in done: p(f"  {r['sheet'][-20:]} #{r['idx']} {r['nick']!r} -> {os.path.basename(pick)}")
p(f"\nstill not sure: {sum(1 for r in rows if r['status'] != 'sure')}")
p('\nrebuild command:\npython C:\\Users\\steph\\build.py ' + ' '.join(s[-24:] for s in sheets))