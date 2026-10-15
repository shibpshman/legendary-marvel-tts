import os, json, csv
TTS  = r'E:\Documents\My Games\Tabletop Simulator'
WORK = r'E:\Media\Board Games\TTS_work'
MOD  = os.path.join(TTS, 'Mods', 'Workshop', '2410733963.json')
OUTD = os.path.join(WORK, 'dump'); os.makedirs(OUTD, exist_ok=True)
mod = json.load(open(MOD, encoding='utf-8'))
objs = mod.get('ObjectStates', [])
o = open(os.path.join(OUTD, 'mod_dump.txt'), 'w', encoding='utf-8')
def p(*a):
    print(*a); print(*a, file=o)
def tf(t):
    t = t or {}
    return (f"pos({t.get('posX',0):.2f},{t.get('posY',0):.2f},{t.get('posZ',0):.2f}) "
            f"rot({t.get('rotX',0):.0f},{t.get('rotY',0):.0f},{t.get('rotZ',0):.0f}) "
            f"scale({t.get('scaleX',1):.2f},{t.get('scaleY',1):.2f},{t.get('scaleZ',1):.2f})")
def url(ob):
    ci = ob.get('CustomImage') or {}
    if ci.get('ImageURL'): return ci['ImageURL']
    cd = ob.get('CustomDeck') or {}
    for v in cd.values(): return v.get('FaceURL', '')
    return ''

p('top-level keys:', sorted(mod.keys()))
p('top-level objects:', len(objs))
for k, fn in (('LuaScript', 'lua_global.lua'), ('XmlUI', 'xml_global.xml'), ('LuaScriptState', 'lua_state.txt')):
    v = mod.get(k) or ''
    p(f'{k}: {len(v)} chars')
    if v: open(os.path.join(OUTD, fn), 'w', encoding='utf-8').write(v)
sp = mod.get('SnapPoints') or []
p(f'global snap points: {len(sp)}')
for s in sp[:80]: p('  ', s)

rows, nlua = [], 0
for ob in objs:
    g = ob.get('GUID', '')
    lua = ob.get('LuaScript') or ''
    if lua:
        nlua += 1; open(os.path.join(OUTD, f'lua_{g}.lua'), 'w', encoding='utf-8').write(lua)
    n = len(ob.get('ContainedObjects') or []) or len(ob.get('DeckIDs') or [])
    rows.append([g, ob.get('Name'), ob.get('Nickname'), tf(ob.get('Transform')), len(lua), n,
                 len(ob.get('AttachedSnapPoints') or []), url(ob)[:90]])
with open(os.path.join(OUTD, 'mod_layout.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['guid', 'name', 'nickname', 'transform', 'lua_len', 'n_children', 'n_snap', 'url'])
    w.writerows(rows)
p(f'objects with their own Lua: {nlua}')

p('\n=== BOARDS / TILES / ZONES ===')
for ob in objs:
    if ob.get('Name') in ('Custom_Board', 'Custom_Tile', 'ScriptingTrigger', 'FogOfWar', 'ReverbTrigger', 'HandTrigger'):
        p(f"{ob.get('Name')} guid={ob.get('GUID')} nick={ob.get('Nickname')!r} {tf(ob.get('Transform'))}")
        if url(ob): p('     image:', url(ob))
        if ob.get('Tags'): p('     tags:', ob['Tags'])
        for s in ob.get('AttachedSnapPoints') or []: p('     snap', s)
p('\n=== all top-level objects by type ===')
from collections import Counter
for k, v in Counter(r[1] for r in rows).most_common(): p(f'  {k}: {v}')
print('\nfiles written to', OUTD)