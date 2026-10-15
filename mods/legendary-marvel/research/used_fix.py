import json, os
WORK = r'E:\Media\Board Games\TTS_work'
mod  = r'E:\Documents\My Games\Tabletop Simulator\Mods\Workshop\2410733963.json'
data = json.load(open(mod, encoding='utf-8'))
used, names = {}, {}

def walk(o, ctx=()):
    if isinstance(o, dict):
        cd = o.get('CustomDeck')
        if isinstance(cd, dict): ctx = ctx + (cd,)
        ids = []
        if isinstance(o.get('CardID'), int): ids.append(o['CardID'])
        ids += [i for i in (o.get('DeckIDs') or []) if isinstance(i, int)]
        for cid in ids:
            v = next((c[str(cid // 100)] for c in reversed(ctx) if str(cid // 100) in c), None)
            if isinstance(v, dict) and v.get('FaceURL'):
                u, i = v['FaceURL'], cid % 100
                used.setdefault(u, set()).add(i)
                if o.get('CardID') == cid and o.get('Nickname'):
                    names.setdefault(u, {}).setdefault(i, o['Nickname'])
        for v in o.values(): walk(v, ctx)
    elif isinstance(o, list):
        for v in o: walk(v, ctx)
walk(data)

mp = os.path.join(WORK, 'manifest.json')
man = json.load(open(mp))
json.dump(man, open(mp + '.bak', 'w'))
changed = 0
for m in man:
    cells = (m['nx'] or 0) * (m['ny'] or 0)
    new = sorted(i for i in (set(m['used']) | used.get(m['url'], set())) if i < cells)
    if new != m['used']:
        changed += 1; print(f"{m['nx']}x{m['ny']} {(m['file'] or '')[-20:]}: used {len(m['used'])} -> {len(new)}")
    m['used'] = new
    nm = {str(k): v for k, v in names.get(m['url'], {}).items()}
    for k, v in (m.get('names') or {}).items(): nm.setdefault(k, v)
    m['names'] = nm
json.dump(man, open(mp, 'w'), indent=1)
print('sheets changed:', changed)