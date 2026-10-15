import os, re, csv
D = r'E:\Media\Board Games\TTS_work\dump'
names = {r['guid']: r['nickname'] for r in csv.DictReader(open(os.path.join(D, 'mod_layout.csv'), encoding='utf-8-sig'))}
vec = re.compile(r'\{\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\}')
o = open(os.path.join(D, 'lua_scan.txt'), 'w', encoding='utf-8')
for f in sorted(os.listdir(D)):
    if not (f.startswith('lua_') and f.endswith('.lua')) or f == 'lua_global.lua': continue
    g = f[4:-4]; src = open(os.path.join(D, f), encoding='utf-8').read(); lines = src.split('\n')
    o.write(f'\n=== {f}  {names.get(g, "?")!r}  {len(src)} chars ===\n')
    o.write('functions: ' + ', '.join(sorted(set(re.findall(r'function\s+([A-Za-z_]\w*)', src)))) + '\n')
    o.write('guids: ' + ', '.join(sorted(set(re.findall(r'getObjectFromGUID\(\s*["\'](\w+)["\']', src)))) + '\n')
    o.write('ui: ' + ', '.join(sorted(set(re.findall(r'(UI\.\w+|createButton|createInput)', src)))) + '\n')
    for i, l in enumerate(lines, 1):
        if vec.search(l): o.write(f'  L{i}: {l.strip()[:140]}\n')
print('wrote', os.path.join(D, 'lua_scan.txt'))