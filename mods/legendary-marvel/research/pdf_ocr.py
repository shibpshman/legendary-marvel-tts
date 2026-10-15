"""OCR for rulebook PDFs whose text layer is missing or garbled (scans, custom font encodings).
Pages are rendered at the given dpi but never above ~2000 px on the long side (tested: no lost lines).
Usage:  python pdf_ocr.py "<folder or pdf>" ["<folder or pdf>" ...] [--all] [--dpi 200] [--pages N]
  default: only PDFs whose text layer is empty or unreadable are OCRed; --all OCRs everything.
Writes <name>.ocr.txt into TTS_work\\rules_txt. Prints timestamped progress and an ETA per page."""
import os, re, sys, time
import numpy as np
import pypdfium2 as pdfium
from pypdf import PdfReader
from rapidocr_onnxruntime import RapidOCR

WORK = r'E:\Media\Board Games\TTS_work'
OUT = os.path.join(WORK, 'rules_txt')
T0 = time.time()
COMMON = set('the and of to a in is that you your card cards hero heroes villain each with this from may can when if or as are for it on be by at not'.split())


def log(m):
    print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


def readable(text):
    """True if the extracted text looks like English prose (catches empty and font-garbled layers)."""
    toks = re.findall(r"[A-Za-z']+", text.lower())
    if len(toks) < 40: return False
    return sum(t in COMMON for t in toks) / len(toks) >= 0.08


def needs_ocr(path, sample_pages=6):
    try:
        rd = PdfReader(path)
        n = len(rd.pages)
        idx = sorted(set([min(n - 1, int(i * (n - 1) / max(sample_pages - 1, 1))) for i in range(sample_pages)]))
        text = ' '.join((rd.pages[i].extract_text() or '') for i in idx)
        return (not readable(text)), n
    except Exception as e:
        log('   could not read text layer (%s): will OCR' % e)
        return True, 0


def order_boxes(items, width):
    """items: (x0, y0, x1, y1, text). Returns text in reading order, handling two-column pages."""
    if not items: return ''
    wide = sum((b[2] - b[0]) > 0.6 * width for b in items)
    left = [b for b in items if (b[0] + b[2]) / 2 < width * 0.5 and (b[2] - b[0]) <= 0.6 * width]
    right = [b for b in items if (b[0] + b[2]) / 2 >= width * 0.5 and (b[2] - b[0]) <= 0.6 * width]
    two_col = wide < 0.15 * len(items) and len(left) > 0.25 * len(items) and len(right) > 0.25 * len(items)
    groups = [items] if not two_col else [[b for b in items if (b[2] - b[0]) > 0.6 * width], left, right]
    out = []
    for g in groups:
        g = sorted(g, key=lambda b: (b[1] + b[3]) / 2)
        lines, cur, cy = [], [], None
        for b in g:
            c = (b[1] + b[3]) / 2; h = b[3] - b[1]
            if cur and abs(c - cy) <= 0.6 * h: cur.append(b)
            else:
                if cur: lines.append(cur)
                cur, cy = [b], c
        if cur: lines.append(cur)
        out += [' '.join(x[4] for x in sorted(l, key=lambda b: b[0])) for l in lines]
    return '\n'.join(out)


def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    do_all = '--all' in args
    dpi = int(args[args.index('--dpi') + 1]) if '--dpi' in args else 200
    maxp = int(args[args.index('--pages') + 1]) if '--pages' in args else None
    paths = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] not in ('--dpi', '--pages'))]
    out_dir = OUT if os.name == 'nt' else os.environ.get('RULES_OUT', 'rules_txt')
    os.makedirs(out_dir, exist_ok=True)
    pdfs = []
    for p in paths:
        if os.path.isfile(p): pdfs.append(p)
        for r, _, fs in os.walk(p): pdfs += [os.path.join(r, f) for f in fs if f.lower().endswith('.pdf')]
    pdfs = sorted(set(pdfs))
    log('found %d PDFs; checking which need OCR ...' % len(pdfs))
    todo = []
    for i, p in enumerate(pdfs, 1):
        bad, n = needs_ocr(p)
        if bad or do_all:
            todo.append((p, n)); log('   [%d/%d] OCR needed: %s (%d pages)' % (i, len(pdfs), os.path.basename(p), n))
        else:
            log('   [%d/%d] text layer is fine: %s' % (i, len(pdfs), os.path.basename(p)))
    total_pages = sum(min(n, maxp) if maxp else n for _, n in todo)
    log('%d PDFs to OCR, %d pages in total (dpi %d)' % (len(todo), total_pages, dpi))
    ocr = RapidOCR()
    done, tstart = 0, time.time()
    for fi, (p, n) in enumerate(todo, 1):
        name = re.sub(r'[^\w\-. ]+', '_', os.path.basename(p))[:-4]
        pdf = pdfium.PdfDocument(p)
        pages = []
        for k in range(len(pdf) if not maxp else min(len(pdf), maxp)):
            t1 = time.time()
            pw, ph = pdf[k].get_size()
            scale = min(dpi / 72, 1990 / max(pw, ph))   # the OCR engine downscales anything over ~2000 px and then misses lines
            img = pdf[k].render(scale=scale).to_pil().convert('RGB')
            res, _ = ocr(np.array(img))
            items = [(min(pt[0] for pt in b), min(pt[1] for pt in b), max(pt[0] for pt in b), max(pt[1] for pt in b), t) for b, t, s in (res or [])]
            pages.append('\n\n===== PAGE %d =====\n%s' % (k + 1, order_boxes(items, img.size[0])))
            done += 1
            eta = (time.time() - tstart) / done * (total_pages - done)
            log('   [%d/%d] %s page %d/%d: %d text boxes, %.1fs   (overall %d/%d pages, ETA %d min)' % (
                fi, len(todo), os.path.basename(p)[:40], k + 1, len(pdf), len(items), time.time() - t1, done, total_pages, eta / 60))
        dest = os.path.join(out_dir, name + '.ocr.txt')
        open(dest, 'w', encoding='utf-8').write(''.join(pages))
        log('   wrote %s (%d chars)' % (dest, sum(len(x) for x in pages)))
    log('DONE: %d PDFs OCRed into %s' % (len(todo), out_dir))


main()