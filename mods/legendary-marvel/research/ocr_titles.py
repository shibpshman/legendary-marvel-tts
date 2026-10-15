import os, json
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
Image.MAX_IMAGE_PIXELS = None
SRC  = r'E:\Media\Board Games\Marvel Legendary Cards'
WORK = r'E:\Media\Board Games\TTS_work'
ENG = None

def init():
    global ENG
    from rapidocr_onnxruntime import RapidOCR
    ENG = RapidOCR()

def read(img):
    res, _ = ENG(np.asarray(img))
    if not res: return '', 0.0
    return ' '.join(r[1] for r in res), sum(float(r[2]) * len(r[1]) for r in res)

def job(path):
    try:
        with Image.open(path) as im0:
            im = im0.convert('RGB')
        k = max(1, min(im.size) // 900)
        if k > 1: im = im.reduce(k)
        variants = [im] if im.width <= im.height else [im.rotate(90, expand=True), im.rotate(-90, expand=True)]
        best = ('', -1.0)
        for v in variants:
            top = v.crop((0, 0, v.width, int(v.height * 0.13)))
            if top.width > 900: top = top.resize((900, max(1, round(top.height * 900 / top.width))))
            txt, conf = read(top)
            if conf > best[1]: best = (txt, conf)
        return path, best[0]
    except Exception:
        return path, ''

def main():
    out = os.path.join(WORK, 'titles.json')
    titles = json.load(open(out, encoding='utf-8')) if os.path.exists(out) else {}
    files = []
    for top in ('Base Sets', 'Expansions'):
        for r, _, fs in os.walk(os.path.join(SRC, top)):
            files += [os.path.join(r, f) for f in fs if f.lower().endswith('.png')]
    todo = [f for f in files if os.path.relpath(f, SRC) not in titles]
    print(len(files), 'cards;', len(todo), 'to read')
    with ProcessPoolExecutor(max_workers=3, initializer=init) as ex:
        for i in range(0, len(todo), 150):
            for p, t in ex.map(job, todo[i:i+150]):
                titles[os.path.relpath(p, SRC)] = t
            json.dump(titles, open(out, 'w', encoding='utf-8'))
            print(min(i + 150, len(todo)), '/', len(todo))

if __name__ == '__main__':
    main()