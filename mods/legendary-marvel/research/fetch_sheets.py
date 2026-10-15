import json, re, os, sys, shutil, urllib.request, urllib.error, collections
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

mod = sys.argv[1]
work = sys.argv[2] if len(sys.argv) > 2 else r'E:\Media\Board Games\TTS_work'
IMAGES = r'E:\Documents\My Games\Tabletop Simulator\Mods\Images'
orig = os.path.join(work, 'orig'); os.makedirs(orig, exist_ok=True)
key = lambda u: re.sub(r'[^A-Za-z0-9]', '', u or '')

def canon(u):
    m = re.match(r'https?://cloud-\d+\.steamusercontent\.com(/ugc/.*)', u or '')
    return 'https://steamusercontent-a.akamaihd.net' + m.group(1) if m else u

data = json.load(open(mod, encoding='utf-8'))
decks = {}
def walk(o):
    if isinstance(o, dict):
        cd = o.get('CustomDeck')
        if isinstance(cd, dict):
            for v in cd.values():
                if isinstance(v, dict) and v.get('FaceURL'):
                    decks.setdefault(v['FaceURL'], {'url': v['FaceURL'], 'back': v.get('BackURL'),
                        'nx': v.get('NumWidth'), 'ny': v.get('NumHeight'),
                        'unique_back': v.get('UniqueBack'), 'used': set(), 'names': {}})
            if 'CardID' in o:
                v = cd.get(str(o['CardID'] // 100))
                if v and v.get('FaceURL') in decks:
                    d = decks[v['FaceURL']]; i = o['CardID'] % 100
                    d['used'].add(i)
                    if o.get('Nickname') and i not in d['names']: d['names'][i] = o['Nickname']
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(data)

cache_files = {os.path.splitext(f)[0]: f for f in os.listdir(IMAGES)}
have = {os.path.splitext(f)[0]: f for f in os.listdir(orig)}
stats = collections.Counter()

def get(d):
    url = d['url']; ck = key(canon(url))
    d['cache_hit'] = cache_files.get(ck) or cache_files.get(key(url))
    if ck in have: stats['already'] += 1; return os.path.join(orig, have[ck])
    if d['cache_hit']:
        src = os.path.join(IMAGES, d['cache_hit'])
        dst = os.path.join(orig, ck + os.path.splitext(src)[1].lower())
        shutil.copy2(src, dst); have[ck] = os.path.basename(dst); stats['from_cache'] += 1
        return dst
    err = None
    for u in dict.fromkeys([canon(url), url.replace('http://', 'https://', 1), url]):
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        for _ in range(2):
            try:
                b = urllib.request.urlopen(req, timeout=90).read()
                ext = '.png' if b[:8] == b'\x89PNG\r\n\x1a\n' else '.jpg' if b[:2] == b'\xff\xd8' else '.bin'
                path = os.path.join(orig, ck + ext)
                open(path, 'wb').write(b); have[ck] = ck + ext; stats['downloaded'] += 1
                return path
            except urllib.error.HTTPError as e:
                err = e
                if e.code in (403, 404): break
            except Exception as e:
                err = e
    print('FAIL', url, err); stats['failed'] += 1
    return None

rep = open(os.path.join(work, 'fetch_out.txt'), 'w', encoding='utf-8')
manifest, shapes, total, consec = [], collections.Counter(), 0, 0
for i, (url, d) in enumerate(decks.items(), 1):
    path = get(d); dim = None
    if path:
        consec = 0; total += os.path.getsize(path)
        try:
            with Image.open(path) as im: dim = im.size
        except Exception: dim = None
    else:
        consec += 1
        if consec >= 5 and stats['already'] + stats['from_cache'] + stats['downloaded'] == 0:
            print('\n5 failures in a row and nothing fetched. Stopping. Load the mod once in TTS so its images are cached, then re-run.')
            sys.exit(1)
    cell = (dim[0] // d['nx'], dim[1] // d['ny']) if dim and d['nx'] and d['ny'] else None
    shapes[(dim, d['nx'], d['ny'])] += 1
    manifest.append({'url': d['url'], 'back': d['back'], 'nx': d['nx'], 'ny': d['ny'], 'unique_back': d['unique_back'],
                     'used': sorted(d['used']), 'names': {str(k): v for k, v in d['names'].items()},
                     'cache_hit': d['cache_hit'], 'file': os.path.basename(path) if path else None, 'size': dim})
    line = f"{i:>3} grid={d['nx']}x{d['ny']} sheet={dim} cell={cell} used={len(d['used'])} cached={'Y' if d['cache_hit'] else 'N'} {os.path.basename(path or 'FAILED')}"
    print(line); rep.write(line + '\n')

json.dump(manifest, open(os.path.join(work, 'manifest.json'), 'w'), indent=1)
rep.write(f"\nTotal: {total/1e9:.2f} GB   {dict(stats)}\nShape histogram (sheet size, nx, ny): count\n")
for s, c in shapes.most_common(): rep.write(f"  {s}: {c}\n")
print(f"done. {total/1e9:.2f} GB, {dict(stats)} -> {work}")