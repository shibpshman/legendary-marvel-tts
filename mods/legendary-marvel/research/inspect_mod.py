import json, re, sys, os
from collections import defaultdict
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
mod = sys.argv[1]
images = sys.argv[2] if len(sys.argv) > 2 else r'E:\Documents\My Games\Tabletop Simulator\Mods\Images'
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inspect_out.txt'), 'w', encoding='utf-8')
def p(*a): print(*a, file=out)

raw = open(mod, encoding='utf-8').read()
data = json.loads(raw)
cache = {os.path.splitext(f)[0]: f for f in os.listdir(images)}
key = lambda u: re.sub(r'[^A-Za-z0-9]', '', u or '')

decks, refs = {}, defaultdict(list)
def walk(o):
    if isinstance(o, dict):
        cd = o.get('CustomDeck')
        if isinstance(cd, dict):
            for v in cd.values():
                if isinstance(v, dict): decks.setdefault(v.get('FaceURL'), v)
            if 'CardID' in o:
                v = cd.get(str(o['CardID'] // 100))
                if v: refs[v.get('FaceURL')].append((o['CardID'] % 100, o.get('Nickname', ''), (o.get('Description') or '')[:40]))
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(data)

p(f"MOD {os.path.basename(mod)}  name={data.get('SaveName')}")
p(f"{len(decks)} unique CustomDeck face sheets in JSON; {sum(len(v) for v in refs.values())} card refs\n")
for url, v in decks.items():
    f = cache.get(key(url)); dim = ''
    if f:
        try:
            with Image.open(os.path.join(images, f)) as im: dim = f"{im.width}x{im.height}"
        except Exception as e: dim = 'unreadable'
    r = refs.get(url, [])
    distinct = sorted(set(r))[:6]
    p(f"{v.get('NumWidth')}x{v.get('NumHeight')} | cached={'Y '+dim if f else 'N'} | refs={len(r)} | {url}")
    for d in distinct: p(f"      idx {d[0]:>2}  {d[1]!r}  {d[2]!r}")

urls = set(re.findall(r'https?://[^\s"\\\']+', raw))
img = [u for u in urls if re.search(r'steamusercontent|imgur|\.(png|jpe?g)', u, re.I)]
miss = [u for u in img if key(u) not in cache]
p(f"\nWhole-file URL scan: {len(img)} image-like URLs, {len(img)-len(miss)} cached, {len(miss)} not cached")
for u in miss[:15]: p("  uncached:", u)
p("\nTop-level object names:", [o.get('Nickname') or o.get('Name') for o in data.get('ObjectStates', [])][:40])
print("done -> inspect_out.txt")