import csv, os, re, shutil, collections
from PIL import Image
SRC  = r'E:\Media\Board Games\Marvel Legendary Cards'
WORK = r'E:\Media\Board Games\TTS_work'
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def words(s): return frozenset(re.findall(r'[a-z0-9]+', (s or '').lower()))

by_norm, by_words = collections.defaultdict(list), collections.defaultdict(list)
for top in ('Base Sets', 'Expansions'):
    for r, _, fs in os.walk(os.path.join(SRC, top)):
        for f in fs:
            if not f.lower().endswith('.png'): continue
            stem = os.path.splitext(f)[0]; full = os.path.join(r, f)
            by_norm[norm(stem)].append(full)
            if len(words(stem)) >= 2: by_words[words(stem)].append(full)

src = os.path.join(WORK, 'matches.csv')
shutil.copy2(src, os.path.join(WORK, 'matches_pre_rescue.csv'))
rows = list(csv.DictReader(open(src, encoding='utf-8')))
fields = list(rows[0].keys())
out = open(os.path.join(WORK, 'rescue_out.txt'), 'w', encoding='utf-8')
def p(*a):
    print(*a); print(*a, file=out)

done, skipped_land, sheets = [], [], collections.OrderedDict()
for r in rows:
    if r['status'] == 'sure' or len(norm(r['nick'])) < 6: continue
    cands = by_norm.get(norm(r['nick'])) or by_words.get(words(r['nick'])) or []
    good = [c for c in cands if 'copy' not in os.path.basename(c).lower()] or cands
    if not good: continue
    pick = sorted(good, key=len)[0]
    with Image.open(pick) as im: w, h = im.size
    if w > h: skipped_land.append((r, pick)); continue
    r['best_card'] = os.path.relpath(pick, SRC); r['rot'] = '0'; r['status'] = 'sure'
    r['card_w'], r['card_h'] = w, h
    done.append((r, pick, len(set(good)))); sheets[r['sheet']] = 1

with open(src, 'w', newline='', encoding='utf-8') as f:
    wr = csv.DictWriter(f, fieldnames=fields); wr.writeheader(); wr.writerows(rows)
p(f'rescued {len(done)} cells on {len(sheets)} sheets; skipped (landscape file) {len(skipped_land)}')
for r, pick, n in done:
    p(f"  {r['sheet'][-20:]} #{r['idx']} {r['nick']!r} -> {os.path.basename(pick)}" + (f'  ({n} files share this title)' if n > 1 else ''))
for r, pick in skipped_land: p(f"  SKIPPED landscape: {r['nick']!r} -> {os.path.basename(pick)}")
left = sum(1 for r in rows if r['status'] != 'sure')
p(f'\nstill not sure: {left}')
if sheets:
    p('\nrebuild command:\npython C:\\Users\\steph\\build.py ' + ' '.join(s[-24:] for s in sheets))