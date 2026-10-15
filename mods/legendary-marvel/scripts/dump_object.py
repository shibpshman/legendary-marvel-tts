"""Writes the exact JSON structure of one top-level object of the mod (default: the Venom expansion bag) so a new expansion can be built to match.

Usage: python dump_object.py [GUID] [out.json]
Decks keep their first two and last two cards (the rest are counted), long Lua scripts are kept whole for the top object only.
Also prints and saves the position, rotation and scale of every expansion bag. Prints timestamped progress."""
import copy, json, os, sys, time

MOD = r'E:\Documents\My Games\Tabletop Simulator\Mods\Workshop\2410733963.json'
WORK = r'E:\Media\Board Games\TTS_work'
GUID = sys.argv[1] if len(sys.argv) > 1 else '1ebd5a'
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(WORK, 'dump', 'object_%s.json' % GUID)
BAGS = ['dc25aa', '14c649', '15de23', 'b0e696', '418349', '15da2a', '3e580d', '4018f0', 'b7126a', '032e6f', '7dc1b5', 'af4886', 'bd8754', '101d51',
        '1ebd5a', '9859de', '8082b9', 'db49df', 'dd5258', '9b4f4d', 'd79b12', '867b86']
T0 = time.time()


def log(m): print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


log('reading %s (%.0f MB)' % (MOD, os.path.getsize(MOD) / 1e6))
mod = json.load(open(MOD, encoding='utf-8'))
tops = {o.get('GUID'): o for o in mod['ObjectStates']}
log('%d top-level objects' % len(tops))


def trim(o, top=False):
    o = copy.deepcopy(o)

    def walk(x, depth):
        if not isinstance(x, dict): return
        kids = x.get('ContainedObjects')
        if kids is not None and x.get('Name') in ('Deck', 'DeckCustom') and len(kids) > 4:
            x['_trimmed'] = '%d cards, showing first 2 and last 2' % len(kids)
            x['ContainedObjects'] = kids[:2] + kids[-2:]
            kids = x['ContainedObjects']
        for k in (kids or []): walk(k, depth + 1)
        for key in ('LuaScript',):
            if depth > 0 and isinstance(x.get(key), str) and len(x[key]) > 300:
                x[key] = x[key][:300] + '... [%d chars]' % len(x[key])
    walk(o, 0)
    return o


if GUID not in tops: sys.exit('GUID %s is not a top-level object' % GUID)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(trim(tops[GUID], True), open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
log('wrote %s (%.0f KB)' % (OUT, os.path.getsize(OUT) / 1e3))
rows = []
for g in BAGS:
    o = tops.get(g)
    if o is None: rows.append({'GUID': g, 'missing': True}); continue
    rows.append({'GUID': g, 'Nickname': o.get('Nickname'), 'Name': o.get('Name'), 'Transform': o.get('Transform'), 'Locked': o.get('Locked'),
                 'Tags': o.get('Tags'), 'keys': sorted(o.keys()), 'lua_chars': len(o.get('LuaScript') or '')})
p2 = os.path.join(os.path.dirname(OUT), 'expansion_bags.json')
json.dump(rows, open(p2, 'w', encoding='utf-8'), indent=1)
for r in rows: log('  %s %-28s %s' % (r['GUID'], r.get('Nickname'), r.get('Transform') and {k: round(v, 2) for k, v in r['Transform'].items() if k.startswith('pos')}))
log('DONE: upload %s and %s' % (OUT, p2))
