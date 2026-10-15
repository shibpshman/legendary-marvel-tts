"""Renders the official one-page Player Mat PDF into a landscape PNG for the table.
Usage: python make_player_mat.py [LegendaryPlayerMat.pdf] [out.png]
Default input: TTS_work\\assets_in\\LegendaryPlayerMat.pdf, output TTS_work\\playermat.png (2400 px wide). build_save.py uses it automatically."""
import os, sys, time
import numpy as np
import pypdfium2 as pdfium

WORK = r'E:\Media\Board Games\TTS_work'
PDF = os.path.join(WORK, 'assets_in', 'LegendaryPlayerMat.pdf')
OUT = os.path.join(WORK, 'playermat.png')
args = [x for x in sys.argv[1:]]
if args: PDF = args[0]
if len(args) > 1: OUT = args[1]
T0 = time.time()


def log(m): print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


log('rendering %s at 4x' % PDF)
im = pdfium.PdfDocument(PDF)[0].render(scale=4).to_pil().convert('RGB')
a = np.array(im)
blue = (a[:, :, 2] > 100) & (a[:, :, 0] < 60) & (a[:, :, 1] < 120)
ys, xs = np.where(blue)
log('cropping the blue mat area (%d x %d px) and rotating to landscape' % (xs.max() - xs.min() + 1, ys.max() - ys.min() + 1))
c = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)).rotate(-90, expand=True)
w = 2400
c = c.resize((w, int(round(w * c.size[1] / c.size[0]))))
os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
c.save(OUT)
log('DONE: %s  (%dx%d, aspect %.3f)' % (OUT, c.size[0], c.size[1], c.size[0] / c.size[1]))
