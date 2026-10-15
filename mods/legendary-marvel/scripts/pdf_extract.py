"""Pulls the text out of a PDF page by page (OCR fallback for pages without a usable text layer) so a small .txt can be uploaded.
Usage: python pdf_extract.py "path\\to\\file.pdf" [out.txt]
Default output: next to the PDF's name inside E:\\Media\\Board Games\\TTS_work\\pdf_text\\<name>.txt
Prints timestamped progress with an ETA; pages are marked with ===== PAGE n =====."""
import os, re, sys, time
import numpy as np
import pypdfium2 as pdfium

if len(sys.argv) < 2: sys.exit('usage: python pdf_extract.py "file.pdf" [out.txt]')
PDF = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(r'E:\Media\Board Games\TTS_work\pdf_text', os.path.splitext(os.path.basename(PDF))[0] + '.txt')
T0 = time.time()


def log(m): print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


doc = pdfium.PdfDocument(PDF)
n = len(doc)
log('%s: %d pages' % (os.path.basename(PDF), n))
ocr = None
out, t_start, ocr_pages = [], time.time(), 0
for i in range(n):
    page = doc[i]
    txt = page.get_textpage().get_text_range() or ''
    clean = re.sub(r'\s+', ' ', txt).strip()
    letters = sum(c.isalpha() for c in clean)
    words = re.findall(r'[A-Za-z]{3,}', clean)
    ok = len(clean) > 150 and len(words) > 0 and sum(1 for w in words if re.search(r'[aeiou]', w.lower())) / len(words) > 0.8
    if not ok:
        if ocr is None:
            from rapidocr_onnxruntime import RapidOCR
            ocr = RapidOCR(); log('   text layer unusable on page %d, switching to OCR for such pages' % (i + 1))
        img = page.render(scale=2.5).to_pil().convert('RGB')
        s = min(1.0, 1990 / max(img.size))
        if s < 1: img = img.resize((int(img.size[0] * s), int(img.size[1] * s)))
        res, _ = ocr(np.array(img))
        items = sorted(((min(p[1] for p in b), min(p[0] for p in b), t) for b, t, sc in (res or [])), key=lambda x: (round(x[0] / 18), x[1]))
        txt = '\n'.join(t for _, _, t in items); ocr_pages += 1
    out.append('===== PAGE %d =====\n%s\n' % (i + 1, txt))
    eta = (time.time() - t_start) / (i + 1) * (n - i - 1)
    log('[%d/%d] %d chars%s (ETA %d s)' % (i + 1, n, len(txt), ' (OCR)' if not ok else '', eta))
os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
open(OUT, 'w', encoding='utf-8').write('\n'.join(out))
log('DONE: %s (%.0f KB, %d pages, %d read by OCR)' % (OUT, os.path.getsize(OUT) / 1024, n, ocr_pages))
