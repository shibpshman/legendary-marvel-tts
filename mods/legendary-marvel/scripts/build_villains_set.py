"""Builds the Villains expansion bag for the Legendary Universal save.

Usage: python build_villains_set.py [--lib "<Villains Core Set folder>"] [--no-ocr]
Reads the Workshop mod JSON (templates), the card images in Base Sets\\Villains Core Set and villains_set_spec.json; writes the sheet images into
E:\\Legendary_TTS_Assets\\img and the finished bag to TTS_work\\villains_set\\villains_bag.json (build_save.py picks it up). Prints timestamped progress."""
import argparse, json, os, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import villains_set

ap = argparse.ArgumentParser()
ap.add_argument('--mod', default=r'E:\Documents\My Games\Tabletop Simulator\Mods\Workshop\2410733963.json')
ap.add_argument('--lib', default=r'E:\Media\Board Games\Marvel Legendary Cards\Base Sets\Villains Core Set')
ap.add_argument('--work', default=r'E:\Media\Board Games\TTS_work')
ap.add_argument('--assets', default=r'E:\Legendary_TTS_Assets')
ap.add_argument('--spec', default=None)
ap.add_argument('--no-ocr', action='store_true', help='do not read card names off the images; use the catalog order')
a = ap.parse_args()
log = villains_set.Log()
spec_path = a.spec or next((p for p in (os.path.join(a.work, 'villains_set_spec.json'), os.path.join(HERE, 'villains_set_spec.json')) if os.path.exists(p)), None)
if not spec_path: sys.exit('villains_set_spec.json not found (it ships in the install zip)')
spec = json.load(open(spec_path, encoding='utf-8'))
log('spec: %d Heroes, %d Villain groups, %d Henchmen groups, %d Commanders, %d Plots' % tuple(len(spec[k]) for k in ('heroes', 'villains', 'henchmen', 'masterminds', 'schemes')))
if not os.path.isdir(a.lib): sys.exit('Image folder not found: %s' % a.lib)
stop = threading.Event()
t0 = time.time()
def beat():
    while not stop.wait(10): log('   ... still working (%ds)' % (time.time() - t0))
threading.Thread(target=beat, daemon=True).start()
log('reading the mod JSON (%s, %.0f MB)' % (a.mod, os.path.getsize(a.mod) / 1e6))
mod = json.load(open(a.mod, encoding='utf-8'))
img = os.path.join(a.assets, 'img')
os.makedirs(img, exist_ok=True)
out_dir = os.path.join(a.work, 'villains_set')
os.makedirs(out_dir, exist_ok=True)
top, report = villains_set.build(mod, spec, a.lib, img, out_dir, log, ocr=not a.no_ocr)
for line in report: log('   ' + line)
dst = os.path.join(out_dir, 'villains_bag.json')
json.dump(top, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
stop.set()
n = lambda nick: len(next(c for c in top['ContainedObjects'] if c['Nickname'] == nick)['ContainedObjects'])
log('DONE: bag %s with %d Heroes, %d Villain groups, %d Masterminds, %d Henchmen groups, %d Schemes -> %s' % (
    top['GUID'], n('Heroes'), n('Villains'), n('Masterminds'), n('Henchmen'), len(next(c for c in top['ContainedObjects'] if c['Nickname'] == 'Schemes')['ContainedObjects']), dst))
