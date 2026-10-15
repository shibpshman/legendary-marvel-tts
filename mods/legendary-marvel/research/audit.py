import csv, os, re, difflib, collections
WORK = r'E:\Media\Board Games\TTS_work'
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def tscore(nick, ocr):
    a, b = norm(nick), norm(ocr)
    if len(a) < 3 or not b: return None
    if a in b: return 1.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return min(1.0, sum(x.size for x in sm.get_matching_blocks()) / len(a))

rows = list(csv.DictReader(open(os.path.join(WORK, 'matches.csv'), encoding='utf-8')))
out = open(os.path.join(WORK, 'audit_out.txt'), 'w', encoding='utf-8')
def p(*a):
    print(*a); print(*a, file=out)

sure = [r for r in rows if r['status'] == 'sure']
cat, bad = collections.Counter(), []
for r in sure:
    ts = tscore(r['nick'], r['ocr_title']); r['_ts'] = ts
    if ts is None: cat['no title evidence'] += 1
    elif ts >= 0.9: cat['title agrees (>=0.9)'] += 1
    elif ts >= 0.6: cat['title partly agrees (0.6-0.9)'] += 1
    else: cat['title CONTRADICTS (<0.6)'] += 1; bad.append(r)
p('sure cells:', len(sure), dict(cat))
p('\nContradictions (mod title vs library title):')
for r in sorted(bad, key=lambda r: r['_ts']):
    p(f"  {r['sheet'][-20:]} #{r['idx']} nick={r['nick']!r} ocr={r['ocr_title']!r} card={os.path.basename(r['best_card'])} sim={r['sim']} ts={r['_ts']:.2f}")
low = sorted((r for r in sure if float(r['sim']) < 0.75), key=lambda r: float(r['sim']))
p(f'\nSure cells with visual similarity < 0.75: {len(low)}')
for r in low[:40]:
    p(f"  {r['sheet'][-20:]} #{r['idx']} nick={r['nick']!r} card={os.path.basename(r['best_card'])} sim={r['sim']} ts={r['_ts']}")
p('\nNot sure:')
for r in rows:
    if r['status'] != 'sure':
        p(f"  {r['sheet'][-20:]} #{r['idx']} {r['status']:6} nick={r['nick']!r} guess={os.path.basename(r['best_card'])} sim={r['sim']} margin={r['margin']}")