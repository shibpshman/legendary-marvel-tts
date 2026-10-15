"""Puts the inline icons (Hero classes, team logos, Attack, Recruit) back into the scheme / Mastermind card text.

The OCR reads "reveals a Hero" where the card shows "reveals a [Strength] Hero", because the icon is a picture. This script
  1. reads the icon legend (class, team, Attack, Recruit) off pages 46-47 of the Universal Rules PDF,
  2. finds those icons on each scheme and Mastermind card by template matching inside every OCR text line,
  3. re-reads the text left and right of each icon so it keeps its exact place in the sentence,
  4. writes card_text_icons.csv (icons shown as <<Strength>>, <<X-Men>> ...) plus icon_debug\\ pictures to check by eye.

Usage: python build_icons.py [rules.pdf] [card_text_ocr.csv] [card_text_icons.csv]
If TTS_work\\icons already holds the 28 icon PNGs (from icons_pack.zip) they are used and the PDF is not read.
Everything prints timestamped progress; icons that cannot be named are written as <<?>> and their crops saved in icon_debug."""
import csv, glob, os, re, sys, time
import numpy as np
import cv2
from PIL import Image, ImageDraw
import pypdfium2 as pdfium
from rapidocr_onnxruntime import RapidOCR

WORK = r'E:\Media\Board Games\TTS_work'
SRC = r'E:\Media\Board Games\Marvel Legendary Cards'
PDF = os.path.join(WORK, 'Marvel_Legendary_Universal_Rules_v9.pdf')
IN_CSV = os.path.join(WORK, 'card_text_ocr.csv')
OUT_CSV = os.path.join(WORK, 'card_text_icons.csv')
ICON_DIR = os.path.join(WORK, 'icons')
DEBUG_DIR = os.path.join(WORK, 'icon_debug')
PAGES = (45, 46)                     # 0-based: viewer pages 46 and 47 hold the class and team legend
THRESH = 0.62                        # weakest score looked at
MIN_USE = 0.72                       # icons scoring below this are only reported, never written into the text (override: --min=0.68)
args = [a for a in sys.argv[1:] if not a.startswith('--')]
if len(args) > 0: PDF = args[0]
if len(args) > 1: IN_CSV = args[1]
if len(args) > 2: OUT_CSV = args[2]
for a in sys.argv[1:]:
    if a.startswith('--pages='): PAGES = tuple(int(x) for x in a[8:].split(','))
    if a.startswith('--src='): SRC = a[6:]
    if a.startswith('--min='): MIN_USE = float(a[6:])
T0 = time.time()


def log(m):
    print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


CLASSES = ['Strength', 'Instinct', 'Covert', 'Tech', 'Ranged']
TEAMS = ['Avengers', 'Brotherhood', 'Cabal', 'Champions', 'Crime Syndicate', 'Fantastic Four', 'Foes of Asgard', 'Guardians of the Galaxy',
         'Heroes of Asgard', 'HYDRA', 'Illuminati', 'Marvel Knights', 'Mercs for Money', 'New Warriors', 'S.H.I.E.L.D.', 'Sinister Six',
         'Spider Friends', 'Venomverse', 'Warbound', 'X-Force', 'X-Men']
BIG_PT = 12                          # icons taller than this (points) are class / team logos; the Attack / Recruit marks are smaller


# ------------------------------------------------------------------------------------------------ 1. icons from the PDF
# The legend icons are not picture objects in this PDF, so the pages are rendered and read like a scan: OCR finds the heading lines,
# each icon sits just left of its heading, and the Attack / Recruit marks are the coloured shapes in the Half-Points paragraph.
def nrm(s): return re.sub(r'[^a-z0-9]', '', s.lower())


def ocr_boxes(ocr, rgb):
    res, _ = ocr(rgb)
    return [(min(p[0] for p in b), min(p[1] for p in b), max(p[0] for p in b), max(p[1] for p in b), t) for b, t, sc in (res or [])]


def biggest_blob(rgb, x0, y0, x1, y1, dil, others):
    """Largest ink cluster inside the window."""
    reg = rgb[y0:y1, x0:x1].copy()
    ink = (np.abs(reg.astype(int) - 255).max(axis=2) > 45).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(ink, np.ones((dil, dil), np.uint8)))
    if n < 2: return None
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    ys, xs = np.where((lab == k) & (ink > 0))
    return Image.fromarray(rgb[y0 + ys.min():y0 + ys.max() + 1, x0 + xs.min():x0 + xs.max() + 1])


def page_icons(ocr, rgb, wanted):
    """Large icons on one rendered page, in reading order (left column then right, top to bottom)."""
    H, W = rgb.shape[:2]
    boxes = [b for b in ocr_boxes(ocr, rgb) if b[3] - b[1] > 10 and b[1] < 0.93 * H]
    found = []
    for col in (0, 1):
        cb = [b for b in boxes if (b[0] < W / 2) == (col == 0)]
        if not cb: continue
        left = float(np.percentile([b[0] for b in cb], 12))
        used = set()
        for b in sorted(cb, key=lambda b: b[1]):
            h = b[3] - b[1]
            if b[0] > left + 0.9 * h:                                   # heading line pushed right by its icon
                x0, y0, x1, y1 = b[:4]
                im = biggest_blob(rgb, max(0, int(x0 - 1.8 * h)), max(0, int(y0 - 0.6 * h)), int(x0 + 0.1 * h), min(H, int(y1 + 0.5 * h)), 5, [])
                if im is not None: found.append((col, y0, im, b[4])); used.add(id(b))
        for nm in wanted:                                               # headings whose OCR box swallowed the icon
            if any(nrm(f[3])[:len(nrm(nm)) + 2].startswith(nrm(nm)[:5]) for f in found if f[0] == col): continue
            for b in cb:
                if id(b) in used: continue
                h = b[3] - b[1]
                head = nrm(b[4])[:len(nrm(nm)) + 3]
                if nrm(nm) in head and b[0] <= left + 0.9 * h:
                    im = biggest_blob(rgb, max(0, int(left - 0.3 * h)), max(0, int(b[1])), int(left + 1.25 * h), min(H, int(b[3])), 5, [])
                    if im is not None: found.append((col, b[1], im, b[4])); used.add(id(b)); break
    found.sort(key=lambda f: (f[0], f[1]))
    return found, boxes


def small_marks(rgb, boxes):
    H, W = rgb.shape[:2]
    hw = [b for b in boxes if nrm(b[4]).startswith('halfpoints') and b[0] < W / 2]
    hc = [b for b in boxes if nrm(b[4]).startswith('hero') and nrm(b[4]).endswith('classes') and b[0] < W / 2]
    out = {}
    if not hw or not hc: return out
    y0, y1 = int(hw[0][3]), int(hc[0][1])
    reg = rgb[y0:y1, :W // 2]
    hsv = cv2.cvtColor(reg, cv2.COLOR_RGB2HSV)
    colored = (hsv[:, :, 1] > 90) & (hsv[:, :, 2] > 90)
    hue = hsv[:, :, 0].astype(int)
    for nm, sel in (('Recruit', (hue >= 12) & (hue <= 40)), ('Attack', (hue <= 12) | (hue >= 170))):
        m = (colored & sel).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((9, 9), np.uint8)))
        if n < 2: continue
        k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        ys, xs = np.where((lab == k) & (m > 0))
        out[nm] = Image.fromarray(reg[max(0, ys.min() - 3):ys.max() + 4, max(0, xs.min() - 3):xs.max() + 4])
    return out


def load_pack():
    """Uses the 28 ready-made icon PNGs in the icons folder when all are there (icons_pack.zip); --harvest forces reading the PDF instead."""
    if '--harvest' in sys.argv: return None
    want = {nm: os.path.join(ICON_DIR, re.sub(r'[^A-Za-z0-9]+', '_', nm) + '.png') for nm in CLASSES + TEAMS + ['Recruit', 'Attack']}
    if not all(os.path.isfile(p) for p in want.values()): return None
    log('using the %d ready-made icons in %s (pass --harvest to re-read the PDF instead)' % (len(want), ICON_DIR))
    return {nm: Image.open(p).convert('RGB') for nm, p in want.items()}


def harvest(ocr):
    if not os.path.isfile(PDF):
        hits = glob.glob(os.path.join(WORK, '**', '*Universal_Rules*.pdf'), recursive=True) + \
            glob.glob(os.path.join(os.path.dirname(WORK), '**', '*Universal_Rules*.pdf'), recursive=True)
        if not hits: log('ERROR: rules PDF not found. Pass it as the first argument.'); sys.exit(2)
        globals()['PDF'] = hits[0]
    log('opening %s' % PDF)
    doc = pdfium.PdfDocument(PDF)
    big, icons = [], {}
    os.makedirs(ICON_DIR, exist_ok=True)
    for pi in PAGES:
        log('   reading page %d' % (pi + 1))
        img = doc[pi].render(scale=3).to_pil().convert('RGB')
        img.save(os.path.join(ICON_DIR, '_page_%d.png' % (pi + 1)))
        rgb = np.array(img)
        found, boxes = page_icons(ocr, rgb, CLASSES + TEAMS)
        log('   page %d: %d large icons' % (pi + 1, len(found)))
        big += [(pi, f[0], f[1], f[2], f[3]) for f in found]
        for k, v in small_marks(rgb, boxes).items(): icons[k] = v
    names = CLASSES + TEAMS
    import difflib
    pairs = []                                                          # name each icon from the heading text beside it, not from its position
    for rec in big:
        head = nrm(rec[4])
        for nm in names:
            r = difflib.SequenceMatcher(None, head[:len(nrm(nm)) + 1], nrm(nm)).ratio()
            if r >= 0.7: pairs.append((r, nm, rec))
    pairs.sort(key=lambda p: -p[0])
    used_n, used_r = set(), set()
    for r, nm, rec in pairs:
        if nm in used_n or id(rec) in used_r: continue
        icons[nm] = rec[3]; used_n.add(nm); used_r.add(id(rec))
    missing = [nm for nm in names if nm not in icons]
    leftover = [rec for rec in big if id(rec) not in used_r]
    for i, rec in enumerate(leftover): rec[3].save(os.path.join(ICON_DIR, 'unnamed_%02d.png' % i))
    log('   named %d of %d large icons from their headings' % (len(used_n), len(names)))
    if missing:
        log('   WARNING: no icon found for: %s' % ', '.join(missing))
        log('            (unmatched crops are in %s as unnamed_NN.png; the page renders are _page_N.png)' % ICON_DIR)
        if len(missing) > 6: sys.exit(3)
    for nm in ('Recruit', 'Attack'):
        if nm not in icons: log('   WARNING: %s mark not found in the Half-Points paragraph' % nm)
    for nm, im in icons.items(): im.save(os.path.join(ICON_DIR, re.sub(r'[^A-Za-z0-9]+', '_', nm) + '.png'))
    log('   saved %d icon templates to %s' % (len(icons), ICON_DIR))
    return icons


def prep_templates(icons):
    out = {}
    for nm, im in icons.items():
        a = np.asarray(im.convert('RGB')).astype(np.float32)
        near_white = (np.abs(a - 255).max(axis=2) < 30).astype(np.uint8)
        h, w = near_white.shape
        pad = cv2.copyMakeBorder(near_white, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=1)
        flood = pad.copy(); ff = np.zeros((h + 4, w + 4), np.uint8)
        cv2.floodFill(flood, ff, (0, 0), 2)                              # white that touches the border is background; white inside the icon stays
        alpha = (flood[1:-1, 1:-1] != 2).astype(np.float32)
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
        ys, xs = np.where(alpha > 0.5)
        if len(ys) == 0: continue
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        if min(y1 - y0, x1 - x0) < 14: log('   WARNING: the %s icon crop is only %dx%d px, skipping it' % (nm, x1 - x0, y1 - y0)); continue
        out[nm] = (a[y0:y1, x0:x1, ::-1].copy(), alpha[y0:y1, x0:x1].copy())
    return out


# ------------------------------------------------------------------------------------------------ 2. card scan
def lines_of(items):
    items = sorted(items, key=lambda b: (b[1] + b[3]) / 2)
    lines, cur, cy = [], [], None
    for b in items:
        c = (b[1] + b[3]) / 2; h = b[3] - b[1]
        if cur and abs(c - cy) <= 0.6 * h: cur.append(b)
        else:
            if cur: lines.append(cur)
            cur, cy = [b], c
    if cur: lines.append(cur)
    return [sorted(l, key=lambda b: b[0]) for l in lines]


def find_icons(bgr, h, templates):
    """Template matches inside one padded line crop, done at a reduced size (line height ~30 px) for speed.
    Returns [(score, name, x, y, w, h, ambiguous)] in crop pixels."""
    f = min(1.0, 30.0 / h)
    small = cv2.resize(bgr, (max(1, int(bgr.shape[1] * f)), max(1, int(bgr.shape[0] * f))), interpolation=cv2.INTER_AREA) if f < 1 else bgr
    hs = h * f
    bg = np.median(small.reshape(-1, 3), axis=0)
    cand = []
    for nm, (tb, ta) in templates.items():
        for ih in np.geomspace(0.55 * hs, 2.4 * hs, 10):
            sc = ih / tb.shape[0]
            w, hh = max(4, int(round(tb.shape[1] * sc))), max(4, int(round(ih)))
            if hh > small.shape[0] or w > small.shape[1]: continue
            t = cv2.resize(tb, (w, hh), interpolation=cv2.INTER_AREA)
            a = cv2.resize(ta, (w, hh), interpolation=cv2.INTER_AREA)[:, :, None]
            comp = (t * a + bg * (1 - a)).astype(np.uint8)
            res = np.nan_to_num(cv2.matchTemplate(small, comp, cv2.TM_CCOEFF_NORMED))
            for _ in range(3):
                _, mx, _, loc = cv2.minMaxLoc(res)
                if mx < THRESH: break
                cand.append((float(mx), nm, loc[0], loc[1], w, hh))
                y0, x0 = max(0, loc[1] - hh // 2), max(0, loc[0] - w // 2)
                res[y0:loc[1] + hh // 2 + 1, x0:loc[0] + w // 2 + 1] = -1
    cand.sort(reverse=True)
    kept = []
    for c in cand:
        cx, cy = c[2] + c[4] / 2, c[3] + c[5] / 2
        if not [k for k in kept if abs(k[2] + k[4] / 2 - cx) < 0.6 * max(k[4], c[4]) and abs(k[3] + k[5] / 2 - cy) < 0.6 * max(k[5], c[5])]:
            kept.append(c)
    out = []
    for k in kept:
        cx, cy = k[2] + k[4] / 2, k[3] + k[5] / 2
        rivals = [c[0] for c in cand if c[1] != k[1] and abs(c[2] + c[4] / 2 - cx) < 0.6 * k[4] and abs(c[3] + c[5] / 2 - cy) < 0.6 * k[5]]
        out.append((k[0], k[1], int(k[2] / f), int(k[3] / f), int(k[4] / f), int(k[5] / f), bool(rivals) and k[0] - max(rivals) < 0.04))
    return sorted(out, key=lambda k: k[2])


def ocr_items(ocr, rgb):
    res, _ = ocr(rgb)
    return [(min(p[0] for p in b), min(p[1] for p in b), max(p[0] for p in b), max(p[1] for p in b), t) for b, t, sc in (res or [])]


WEAK = []


def scan_card(ocr, path, templates, tag):
    del WEAK[:]
    im = Image.open(path).convert('RGB')
    s = min(1.0, 1990 / max(im.size))
    if s < 1: im = im.resize((int(im.size[0] * s), int(im.size[1] * s)), Image.LANCZOS)
    rgb = np.array(im); bgr = rgb[:, :, ::-1].copy()
    items = ocr_items(ocr, rgb)
    found, boxes = [], []
    for line in lines_of(items):
        x0, y0 = min(b[0] for b in line), min(b[1] for b in line)
        x1, y1 = max(b[2] for b in line), max(b[3] for b in line)
        h = float(np.median([b[3] - b[1] for b in line]))
        px, py = int(1.8 * h), int(0.8 * h)
        cx0, cy0, cx1, cy1 = max(0, int(x0 - px)), max(0, int(y0 - py)), min(bgr.shape[1], int(x1 + px)), min(bgr.shape[0], int(y1 + py))
        if h < 8: continue
        for sc, nm, hx, hy, hw, hh, amb in find_icons(bgr[cy0:cy1, cx0:cx1], h, templates):
            if sc < MIN_USE:
                WEAK.append((sc, nm)); continue
            found.append((nm, sc, amb))
            boxes.append((cx0 + hx, cy0 + hy, hw, hh, nm, sc, amb, h))
    if not boxes:
        return ' | '.join(' '.join(b[4] for b in l) for l in lines_of(items)), found
    # blank every icon, stamp a "#" where it was, read the text again; the "#" marks the exact place in the sentence
    mask = np.zeros(bgr.shape[:2], np.uint8)
    for x, y, w, hh, nm, sc, amb, h in boxes: mask[max(0, y - 2):y + hh + 2, max(0, x - 2):x + w + 2] = 255
    clean = cv2.inpaint(bgr, mask, 5, cv2.INPAINT_TELEA)
    for x, y, w, hh, nm, sc, amb, h in boxes:
        scale = 0.62 * h / 22.0
        (tw, th), _ = cv2.getTextSize('#', cv2.FONT_HERSHEY_SIMPLEX, scale, max(2, int(h / 9)))
        cv2.putText(clean, '#', (int(x + (w - tw) / 2), int(y + (hh + th) / 2)), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), max(2, int(h / 9)), cv2.LINE_AA)
    items2 = ocr_items(ocr, clean[:, :, ::-1].copy())
    text = ' | '.join(' '.join(b[4] for b in l) for l in lines_of(items2))
    order = sorted(range(len(boxes)), key=lambda i: (round(boxes[i][1] / max(1, boxes[i][7])), boxes[i][0]))   # reading order: line, then left to right
    marks = len(re.findall(r'#', text))
    if marks == len(boxes):
        it = iter(order)
        text = re.sub(r'\s*#+\s*', lambda m: ' <<%s>> ' % boxes[next(it)][4], text)
        text = re.sub(r'\s+', ' ', text)
    else:
        log('   WARNING %s: %d icons found but %d markers read; icons appended to the end of the text, check icon_debug' % (tag, len(boxes), marks))
        text = ' | '.join(' '.join(b[4] for b in l) for l in lines_of(items)) + ' ' + ' '.join('<<%s>>' % boxes[i][4] for i in order)
    os.makedirs(DEBUG_DIR, exist_ok=True)
    dbg = im.copy(); d = ImageDraw.Draw(dbg)
    for x, y, w, hh, nm, sc, amb, h in boxes:
        d.rectangle([x, y, x + w, y + hh], outline=(255, 0, 0), width=3)
        d.text((x, max(0, y - 14)), '%s %.2f%s' % (nm, sc, '?' if amb else ''), fill=(255, 0, 0))
    dbg.thumbnail((1000, 1400)); dbg.save(os.path.join(DEBUG_DIR, re.sub(r'[^A-Za-z0-9]+', '_', tag) + '.png'))
    return text, found


# ------------------------------------------------------------------------------------------------ main
log('phase 1/3: harvesting icons from the rulebook')
ocr = RapidOCR()
templates = prep_templates(load_pack() or harvest(ocr))
log('phase 2/3: loading the card list %s' % IN_CSV)
rows = list(csv.DictReader(open(IN_CSV, encoding='utf-8-sig')))
log('phase 3/3: scanning %d cards for inline icons' % len(rows))
out, tstart, tot_icons, ambiguous, with_icons = [], time.time(), 0, 0, 0
for i, r in enumerate(rows, 1):
    t1 = time.time()
    path = os.path.join(SRC, r['file'])
    if not os.path.isfile(path):
        log('[%d/%d] %s: file missing, kept old text' % (i, len(rows), r['name'])); out.append(dict(r, icons='')); continue
    text, found = scan_card(ocr, path, templates, '%s_%s' % (r['kind'], r['name']))
    tot_icons += len(found); ambiguous += sum(1 for f in found if f[2]); with_icons += bool(found)
    out.append(dict(r, text=text, icons='; '.join('%s %.2f%s' % (f[0], f[1], '?' if f[2] else '') for f in found)))
    eta = (time.time() - tstart) / i * (len(rows) - i)
    weak = ' [ignored below %.2f: %s]' % (MIN_USE, ', '.join('%s %.2f' % (n, sc) for sc, n in sorted(WEAK, reverse=True)[:2])) if WEAK else ''
    log('[%d/%d] %s %r: %s%s (%.1fs, ETA %d min)' % (i, len(rows), r['kind'], r['name'], ', '.join('<<%s>> %.2f%s' % (f[0], f[1], '?' if f[2] else '') for f in found) or 'no icons', weak, time.time() - t1, eta / 60))
os.makedirs(os.path.dirname(OUT_CSV) or '.', exist_ok=True)
with open(OUT_CSV, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['kind', 'name', 'set', 'file', 'match', 'text', 'icons'])
    for r in out: w.writerow([r['kind'], r['name'], r['set'], r['file'], r['match'], r['text'], r['icons']])
log('DONE: %d icons on %d of %d cards (%d ambiguous, marked ? in the log) -> %s ; annotated pictures in %s' % (tot_icons, with_icons, len(rows), ambiguous, OUT_CSV, DEBUG_DIR))
