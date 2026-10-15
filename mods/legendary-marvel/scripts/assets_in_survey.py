"""Lists everything under TTS_work\\assets_in: path, size, type, image size / PDF pages / zip contents, plus contact sheets of the images.
Usage: python assets_in_survey.py [folder]        -> assets_in_survey.csv and assets_in_sheets\\sheet_NN.png next to the folder
Prints timestamped progress; zips are listed, not extracted."""
import csv, os, sys, time, zipfile
from PIL import Image, ImageDraw, ImageFont

ROOT = r'E:\Media\Board Games\TTS_work\assets_in'
if len(sys.argv) > 1: ROOT = sys.argv[1]
OUT_CSV = os.path.join(os.path.dirname(ROOT.rstrip('\\/')), 'assets_in_survey.csv')
SHEETS = os.path.join(os.path.dirname(ROOT.rstrip('\\/')), 'assets_in_sheets')
IMG = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tif', '.tiff'}
T0 = time.time()
Image.MAX_IMAGE_PIXELS = None


def log(m): print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


log('walking %s' % ROOT)
files = []
for r, _, fs in os.walk(ROOT):
    for f in fs: files.append(os.path.join(r, f))
log('%d files' % len(files))
rows, thumbs, last = [], [], time.time()
for i, p in enumerate(sorted(files), 1):
    ext = os.path.splitext(p)[1].lower()
    size = os.path.getsize(p)
    info = ''
    try:
        if ext in IMG:
            with Image.open(p) as im:
                info = '%dx%d %s' % (im.size[0], im.size[1], im.mode)
                t = im.convert('RGB'); t.thumbnail((360, 260)); thumbs.append((os.path.relpath(p, ROOT), info, t.copy()))
        elif ext == '.pdf':
            try:
                import pypdfium2 as pdfium
                info = '%d pages' % len(pdfium.PdfDocument(p))
            except Exception as e: info = 'pdf (%s)' % e
        elif ext == '.zip':
            with zipfile.ZipFile(p) as z:
                names = z.namelist(); info = '%d entries: %s' % (len(names), '; '.join(names[:12]))
    except Exception as e:
        info = 'ERROR %s' % e
    rows.append([os.path.relpath(p, ROOT), ext, size, info])
    if time.time() - last > 5 or i == len(files):
        log('[%d/%d] %s (%.1f MB)' % (i, len(files), os.path.basename(p), size / 1e6)); last = time.time()
with open(OUT_CSV, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['path', 'type', 'bytes', 'info']); w.writerows(rows)
log('wrote %s' % OUT_CSV)
os.makedirs(SHEETS, exist_ok=True)
font = ImageFont.load_default()
per, n = 12, 0
for s0 in range(0, len(thumbs), per):
    g = thumbs[s0:s0 + per]
    sheet = Image.new('RGB', (4 * 370, 3 * 310), 'white'); d = ImageDraw.Draw(sheet)
    for k, (name, info, t) in enumerate(g):
        x, y = (k % 4) * 370 + 5, (k // 4) * 310 + 5
        sheet.paste(t, (x, y)); d.text((x, y + 264), name[-52:], fill='black', font=font); d.text((x, y + 278), info, fill='black', font=font)
    n += 1; sheet.save(os.path.join(SHEETS, 'sheet_%02d.png' % n))
log('DONE: %d files, %d images on %d sheets in %s; list in %s' % (len(files), len(thumbs), n, SHEETS, OUT_CSV))
