import csv, os, re, difflib, shutil
WORK = r'E:\Media\Board Games\TTS_work'
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def tscore(a, b):
    a, b = norm(a), norm(b)
    if len(a) < 3 or not b: return None
    if a in b: return 1.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return min(1.0, sum(x.size for x in sm.get_matching_blocks()) / len(a))
HERO = re.compile(r'_\d(Rare|Common|Uncommon)', re.I)

src = os.path.join(WORK, 'matches.csv')
shutil.copy2(src, os.path.join(WORK, 'matches_m5.csv'))
rows = list(csv.DictReader(open(src, encoding='utf-8')))
fields = list(rows[0].keys())
out = open(os.path.join(WORK, 'finalize_out.txt'), 'w', encoding='utf-8')
def p(*a):
    print(*a); print(*a, file=out)

dem, pro = [], []
for r in rows:
    stem = os.path.splitext(os.path.basename(r['best_card']))[0]
    nick, ocr = r['nick'], r['ocr_title']
    if r['status'] == 'sure':
        if not HERO.search(stem) and len(norm(nick)) >= 3 and len(norm(ocr)) >= 8:
            ts = max(tscore(nick, ocr) or 0, tscore(nick, stem) or 0)
            if ts < 0.6: r['status'] = 'contradict'; dem.append(r)
    elif len(norm(nick)) >= 6 and norm(nick) == norm(stem) and float(r['sim']) >= 0.45:
        r['status'] = 'sure'; pro.append(r)

with open(src, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
p(f'demoted to review: {len(dem)}   promoted to sure: {len(pro)}')
p('\nDemoted:')
for r in dem: p(f"  {r['sheet'][-20:]} #{r['idx']} nick={r['nick']!r} -> {os.path.basename(r['best_card'])} sim={r['sim']}")
p('\nPromoted:')
for r in pro: p(f"  {r['sheet'][-20:]} #{r['idx']} nick={r['nick']!r} -> {os.path.basename(r['best_card'])} sim={r['sim']}")
c = {}
for r in rows: c[r['status']] = c.get(r['status'], 0) + 1
p('\nfinal statuses:', c)