"""Lists a card-image folder: every file with size and pixel dimensions, plus a count per sub-folder.

Usage: python folder_survey.py "E:\\Media\\Board Games\\Marvel Legendary Cards\\Base Sets\\Villains Core Set" [out.csv]
Writes TTS_work\\survey_<folder name>.csv. Prints timestamped progress and a summary."""
import collections, csv, os, sys, time
from PIL import Image

WORK = r'E:\Media\Board Games\TTS_work'
T0 = time.time()
Image.MAX_IMAGE_PIXELS = None
IMG = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tif', '.tiff'}


def log(m): print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


if len(sys.argv) < 2: sys.exit('Usage: python folder_survey.py "<folder>" [out.csv]')
root = sys.argv[1].rstrip('\\/')
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(WORK, 'survey_%s.csv' % os.path.basename(root).replace(' ', '_'))
log('walking %s' % root)
files = [os.path.join(r, f) for r, _, fs in os.walk(root) for f in fs]
log('%d files' % len(files))
rows, per, last = [], collections.Counter(), time.time()
for i, p in enumerate(sorted(files), 1):
    rel = os.path.relpath(p, root)
    ext = os.path.splitext(p)[1].lower()
    dims = ''
    if ext in IMG:
        try:
            with Image.open(p) as im: dims = '%dx%d' % im.size
        except Exception as e: dims = 'unreadable: %s' % e
    rows.append([rel, ext, os.path.getsize(p), dims])
    per[os.path.dirname(rel)] += 1
    if time.time() - last > 10:
        log('[%d/%d] %s' % (i, len(files), rel)); last = time.time()
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
with open(out, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['path', 'ext', 'bytes', 'pixels']); w.writerows(rows)
for d, n in sorted(per.items()): log('  %-70s %4d files' % (d or '(top)', n))
sizes = collections.Counter(r[3] for r in rows if r[3])
log('most common image sizes: %s' % ', '.join('%s x%d' % kv for kv in sizes.most_common(6)))
log('DONE: %d files in %d folders -> %s' % (len(rows), len(per), out))
