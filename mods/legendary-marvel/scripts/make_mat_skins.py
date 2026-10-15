"""Makes the nine mat skins: each 28_Inch_Template mat gets the extra slot frames and labels the mod needs
(HORRORS label on the spare top-left box, BINDINGS and PIT frames over the logo band) in the same glassy style.
Usage: python make_mat_skins.py [assets_in folder] [out folder]
Default: TTS_work\\assets_in -> TTS_work\\skins\\mat_skin_1.jpg ... mat_skin_9.jpg (build_save.py picks them up)."""
import glob, os, re, sys, time
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WORK = r'E:\Media\Board Games\TTS_work'
SRC = os.path.join(WORK, 'assets_in')
OUT = os.path.join(WORK, 'skins')
if len(sys.argv) > 1: SRC = sys.argv[1]
if len(sys.argv) > 2: OUT = sys.argv[2]
FRAME_W, FRAME_H = .0865, .2377                       # a card slot, as fractions of the mat (measured on the Twists box)
FRAMES = [('BINDINGS', .545, .186), ('PIT', .645, .186)]
LABELS = [('HORRORS', .089, .044)]                    # label only: the box is already printed
T0 = time.time()
Image.MAX_IMAGE_PIXELS = None


def log(m): print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


def font(size):
    for f in (r'C:\Windows\Fonts\impact.ttf', r'C:\Windows\Fonts\arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        if os.path.isfile(f): return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def label(draw, text, cx, cy, f):
    w = draw.textlength(text, font=f)
    x, y = cx - w / 2, cy
    draw.text((x + 3, y + 3), text, font=f, fill=(0, 0, 0, 150), anchor='lm')
    draw.text((x, y), text, font=f, fill=(255, 255, 255, 255), anchor='lm')


files = sorted(glob.glob(os.path.join(SRC, '28_Inch_Template_-_*.jpg')), key=lambda p: int(re.search(r'_-_(\d+)\.', p).group(1)))
log('%d templates found in %s' % (len(files), SRC))
if not files: sys.exit('no 28_Inch_Template_-_N.jpg files found')
os.makedirs(OUT, exist_ok=True)
for i, p in enumerate(files, 1):
    n = int(re.search(r'_-_(\d+)\.', p).group(1))
    t1 = time.time()
    im = Image.open(p).convert('RGBA')
    W, H = im.size
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f = font(int(H * .021))
    fw, fh = int(FRAME_W * W), int(FRAME_H * H)
    for name, u, v in FRAMES:
        x0, y0 = int(u * W - fw / 2), int(v * H - fh / 2)
        glow = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle([x0 - 6, y0 - 6, x0 + fw + 6, y0 + fh + 6], radius=26, fill=(255, 255, 255, 40))
        ov = Image.alpha_composite(ov, glow.filter(ImageFilter.GaussianBlur(10)))
        d = ImageDraw.Draw(ov)
        d.rounded_rectangle([x0, y0, x0 + fw, y0 + fh], radius=22, fill=(255, 255, 255, 34), outline=(255, 255, 255, 210), width=max(3, W // 1100))
        label(d, name, u * W, (v - FRAME_H / 2 - .023) * H, f)
    for name, u, v in LABELS: label(d, name, u * W, v * H, f)
    out = Image.alpha_composite(im, ov).convert('RGB')
    path = os.path.join(OUT, 'mat_skin_%d.jpg' % n)
    out.save(path, quality=92, subsampling=0)
    log('[%d/%d] %s -> %s (%.1f MB, %.1fs)' % (i, len(files), os.path.basename(p), path, os.path.getsize(path) / 1e6, time.time() - t1))
log('DONE: %d skins in %s' % (len(files), OUT))
