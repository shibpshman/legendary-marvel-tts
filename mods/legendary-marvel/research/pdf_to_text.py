"""Extracts text from rulebook PDFs so they can be searched and cross-checked.
Usage:  python pdf_to_text.py "<folder or pdf>" ["<folder or pdf>" ...]
Writes one .txt per PDF into TTS_work\\rules_txt and a rules_summary.txt. Prints timestamped progress."""
import os, sys, time, re
from pypdf import PdfReader

WORK = r'E:\Media\Board Games\TTS_work'
OUT = os.path.join(WORK, 'rules_txt')
T0 = time.time()


def log(m):
    print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


def find_pdfs(paths):
    out = []
    for p in paths:
        if os.path.isfile(p) and p.lower().endswith('.pdf'): out.append(p)
        for r, _, fs in os.walk(p):
            out += [os.path.join(r, f) for f in fs if f.lower().endswith('.pdf')]
    return sorted(set(out))


def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    if os.name != 'nt': globals()['OUT'] = os.environ.get('RULES_OUT', 'rules_txt')
    os.makedirs(OUT, exist_ok=True)
    pdfs = find_pdfs(sys.argv[1:])
    log('found %d PDF files' % len(pdfs))
    rows, scans = [], []
    for i, p in enumerate(pdfs, 1):
        name = re.sub(r'[^\w\-. ]+', '_', os.path.basename(p))[:-4]
        try:
            rd = PdfReader(p)
            n = len(rd.pages)
            log('[%d/%d] %s (%d pages, %.1f MB)' % (i, len(pdfs), os.path.basename(p), n, os.path.getsize(p) / 1e6))
            chunks, tlast = [], time.time()
            for k, pg in enumerate(rd.pages, 1):
                try: t = pg.extract_text() or ''
                except Exception as e: t = '[page %d: extract failed: %s]' % (k, e)
                chunks.append('\n\n===== PAGE %d =====\n%s' % (k, t))
                if time.time() - tlast > 10:
                    log('   ... page %d/%d' % (k, n)); tlast = time.time()
            text = ''.join(chunks)
            chars = len(text) - 20 * n
            dest = os.path.join(OUT, name + '.txt')
            open(dest, 'w', encoding='utf-8').write(text)
            per = chars / max(n, 1)
            flag = '' if per >= 200 else '  <-- LOW TEXT: probably scanned, needs OCR'
            if flag: scans.append(os.path.basename(p))
            log('   wrote %s: %d chars (%d per page)%s' % (os.path.basename(dest), chars, per, flag))
            rows.append('%-70s pages=%-4d chars=%-8d%s' % (os.path.basename(p), n, chars, flag))
        except Exception as e:
            log('   FAILED %s: %s' % (os.path.basename(p), e))
            rows.append('%-70s FAILED %s' % (os.path.basename(p), e))
    open(os.path.join(OUT, 'rules_summary.txt'), 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
    log('DONE: %d PDFs, %d need OCR. Summary in %s' % (len(pdfs), len(scans), os.path.join(OUT, 'rules_summary.txt')))
    for s in scans: log('   needs OCR: ' + s)


main()