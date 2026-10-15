import os, re, json, glob, urllib.request
from PIL import Image
TTS = r'E:\Documents\My Games\Tabletop Simulator\Mods'
WORK = r'E:\Media\Board Games\TTS_work'
MOD = os.path.join(TTS, 'Workshop', '2410733963.json')
OUT = os.path.join(WORK, 'mod_assets_out.txt')
os.makedirs(os.path.join(WORK, 'assets_orig'), exist_ok=True)
def canon(u): return re.sub(r'^https?://cloud-\d+\.steamusercontent\.com', 'https://steamusercontent-a.akamaihd.net', u)
def ckey(u): return re.sub(r'[^A-Za-z0-9]', '', canon(u))
found = {}
def add(u, kind, name):
    found.setdefault(u, {'kinds': set(), 'names': set(), 'n': 0})
    found[u]['kinds'].add(kind); found[u]['names'].add(name[:30]); found[u]['n'] += 1
def walk(o, name=''):
    if isinstance(o, dict):
        nm = o.get('Nickname') or o.get('Name') or name
        for k, v in o.items():
            if isinstance(v, str) and re.match(r'https?://', v) and k != 'FaceURL':
                add(v, k, nm)
            elif k in ('LuaScript', 'XmlUI') and isinstance(v, str):
                for u in re.findall(r'https?://[^\s"\'<>)]+', v): add(u, 'lua/ui', nm or 'global')
            else: walk(v, nm)
    elif isinstance(o, list):
        for x in o: walk(x, name)
walk(json.load(open(MOD, encoding='utf-8')))
o = open(OUT, 'w', encoding='utf-8')
def p(*a):
    print(*a); print(*a, file=o)
p(f'{len(found)} unique non-deck-face URLs')
for u, d in sorted(found.items(), key=lambda kv: (sorted(kv[1]['kinds']), kv[0])):
    k = ckey(u)
    hits = glob.glob(os.path.join(TTS, 'Images', k + '.*')) + glob.glob(os.path.join(TTS, 'PDF', k + '.*'))
    src = hits[0] if hits else ''
    if not src:
        dst = os.path.join(WORK, 'assets_orig', k[-60:] + '.bin')
        try:
            req = urllib.request.Request(canon(u), headers={'User-Agent': 'Mozilla/5.0'})
            open(dst, 'wb').write(urllib.request.urlopen(req, timeout=30).read()); src = dst
        except Exception as e: src = ''
    dim = '-'
    try:
        with Image.open(src) as im: dim = f'{im.size[0]}x{im.size[1]}'
    except Exception: pass
    p(f"{'/'.join(sorted(d['kinds']))} | x{d['n']} | {sorted(d['names'])[:3]} | {dim} | cache={'yes' if hits else 'no'}")
    p(f'   {u}')
    p(f'   key={k}')