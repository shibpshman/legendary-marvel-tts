"""(Developer script) Reads the BGG catalog pages and writes villains_set_spec.json: the card names, copies, classes, teams and texts of the
Legendary Villains core set, which build_villains_set.py combines with the card images in Base Sets\\Villains Core Set."""
import json, re, sys
import build_catalog as B

folder = sys.argv[1] if len(sys.argv) > 1 else 'catsrc'
out = sys.argv[2] if len(sys.argv) > 2 else 'villains_set_spec.json'
H = B.read(folder, '*Heroes*And*Allies*.txt'); V = B.read(folder, '*Villains*and*Adversaries*.txt')
N = B.read(folder, '*Henchmen*.txt'); M = B.read(folder, '*Complete_Card_Text.txt')
CLS = re.compile(r'Microbadge: Legendary fan - (Strength|Instinct|Covert|Tech|Ranged) Hero')


def clean(s):
    s = re.sub(r'Microbadge: Legendary fan - (\w+) Hero', r'[\1]', s)
    return s.encode('ascii', 'ignore').decode('ascii').strip()


def set_blocks(lines, setname, villains_page=False):
    toc, body = B.toc_and_body(lines)
    bl = B.blocks(body, set(toc))
    cur, out = None, []
    for b in bl:
        if isinstance(b, tuple): cur = b[1]; continue
        if cur == setname: out.append(b)
    return out


spec = {'exp_tag': 'Villains Expansion', 'set': 'Villains'}
# ---- heroes ----
heroes = []
cur = None
for b in set_blocks(H, 'Villains'):
    if len(b) >= 2 and B.team_line(b[1]) and not B.COPIES.search(b[0]):
        m = re.search(r'-\s*(.*?) Team \(([^)]*)\)', b[1]) or re.search(r'\((.*)\)', b[1])
        team = (re.search(r'Team \(([^)]*)\)', b[1]) or re.search(r'^\(([^)]*)\)$', b[1])).group(1)
        cur = {'name': b[0], 'team': team, 'cards': []}
        heroes.append(cur)
        rest = b[2:]
        if rest: cur['_note'] = rest
    elif cur is not None and re.search(r'\((\d+) cop(?:y|ies)\)$', b[0]):
        m = re.search(r'^(.*?)\s*\((\d+) cop(?:y|ies)\)$', b[0])
        cls = next((CLS.search(x).group(1) for x in b[1:] if CLS.search(x)), '')
        cost = next((int(re.search(r'Cost: (\d+)', x).group(1)) for x in b if re.match(r'Cost: \d+', x)), None)
        cur['cards'].append({'name': clean(m.group(1)), 'copies': int(m.group(2)), 'cls': cls, 'cost': cost, 'text': [clean(x) for x in b[1:] if not x.startswith('Flavor')]})
for h in heroes: h.pop('_note', None)
spec['heroes'] = heroes
# ---- villain groups (Adversaries) ----
groups = []
vb = set_blocks(V, 'Villains')
for k, b in enumerate(vb):
    if len(b) == 1 and k + 1 < len(vb) and B.COPIES.search(vb[k + 1][0]):
        groups.append({'name': b[0], 'cards': []}); continue
    if groups and B.COPIES.search(b[0]):
        m = re.search(r'^(.*?)\s*\((\d+) cop(?:y|ies)\)$', b[0])
        groups[-1]['cards'].append({'name': clean(m.group(1)), 'copies': int(m.group(2)), 'text': [clean(x) for x in b[1:]]})
spec['villains'] = groups
# ---- henchmen (Backup Adversaries) ----
hen = []
for b in set_blocks(N, 'Villains'):
    if 'VP:' in ' '.join(b) and 'Attack:' in ' '.join(b):
        hen.append({'name': b[0], 'text': [clean(x) for x in b[1:]]})
spec['henchmen'] = hen
# ---- masterminds (Commanders) and schemes (Plot) from the main page ----
toc, body = B.toc_and_body_main(M)
bl = B.blocks(body, set(toc))
mode, cur_set, mm, schemes = None, None, [], []
for k, b in enumerate(bl):
    if isinstance(b, tuple): cur_set = b[1]; continue
    if len(b) == 1 and b[0] in B.SECTION_TITLES:
        mode = b[0]; cur_set = None; continue
    if cur_set != 'Villains': continue
    if mode == 'Masterminds and Commanders':
        if len(b) == 1 and k + 1 < len(bl) and not isinstance(bl[k + 1], tuple) and any(x.startswith(('Always Leads',)) for x in bl[k + 1][:2]):
            blk = bl[k + 1]
            leads = re.sub(r'^Always Leads:\s*|\.$', '', blk[0]).strip()
            mm.append({'name': b[0], 'leads': leads, 'text': [clean(x) for x in blk], 'tactics': []})
        elif mm and len(b) >= 2 and b[1].startswith('Fight:') and len(mm[-1]['tactics']) < 4:
            mm[-1]['tactics'].append({'name': b[0], 'text': [clean(x) for x in b[1:]]})
    if mode == 'Schemes and Plots' and len(b) >= 2 and b[1].startswith(('Setup:', 'Special Rules:', 'Twist')):
        schemes.append({'name': b[0], 'text': [clean(x) for x in b[1:]]})
spec['masterminds'] = mm
spec['schemes'] = schemes
json.dump(spec, open(out, 'w', encoding='utf-8'), indent=1, ensure_ascii=True)
print('heroes', len(heroes), [ (h['name'], h['team'], [c['copies'] for c in h['cards']]) for h in heroes])
print('villains', [(g['name'], [(c['name'], c['copies']) for c in g['cards']]) for g in groups])
print('henchmen', [h['name'] for h in hen])
print('masterminds', [(m['name'], m['leads'], [t['name'] for t in m['tactics']]) for m in mm])
print('schemes', [s['name'] for s in schemes])
