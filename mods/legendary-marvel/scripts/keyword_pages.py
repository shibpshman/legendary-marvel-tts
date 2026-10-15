"""Renders the keyword pages (21-37) of the Universal Rules PDF to pictures so the icons in the glossary text can be read by eye.
Usage: python keyword_pages.py [rules.pdf] [first_page last_page]     -> E:\\Media\\Board Games\\TTS_work\\keyword_pages\\page_NN.png"""
import glob, os, sys, time
import pypdfium2 as pdfium

WORK = r'E:\Media\Board Games\TTS_work'
PDF = os.path.join(WORK, 'Marvel_Legendary_Universal_Rules_v9.pdf')
OUT = os.path.join(WORK, 'keyword_pages')
FIRST, LAST = 21, 37
args = [a for a in sys.argv[1:] if not a.startswith('--')]
if args and args[0].lower().endswith('.pdf'): PDF = args.pop(0)
if len(args) >= 2: FIRST, LAST = int(args[0]), int(args[1])
if '--out' in sys.argv: OUT = sys.argv[sys.argv.index('--out') + 1]
T0 = time.time()


def log(m):
    print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


if not os.path.isfile(PDF):
    hits = glob.glob(os.path.join(os.path.dirname(WORK), '**', '*Universal_Rules*.pdf'), recursive=True)
    if not hits: log('ERROR: rules PDF not found; pass it as the first argument'); sys.exit(2)
    PDF = hits[0]
log('opening %s' % PDF)
doc = pdfium.PdfDocument(PDF)
os.makedirs(OUT, exist_ok=True)
for n in range(FIRST, LAST + 1):
    t1 = time.time()
    img = doc[n - 1].render(scale=2.5).to_pil().convert('RGB')
    path = os.path.join(OUT, 'page_%02d.png' % n)
    img.save(path)
    log('[%d/%d] page %d -> %s (%dx%d, %.1fs)' % (n - FIRST + 1, LAST - FIRST + 1, n, path, img.size[0], img.size[1], time.time() - t1))
log('DONE: %d pages in %s' % (LAST - FIRST + 1, OUT))
