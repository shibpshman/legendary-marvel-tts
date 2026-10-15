import os
from PIL import Image
SRC = r'E:\Media\Board Games\Marvel Legendary Cards'
OUT = r'E:\Media\Board Games\TTS_work\asset_survey_out.txt'
CARD_DIRS = ('Base Sets', 'Expansions')
o = open(OUT, 'w', encoding='utf-8')
def p(*a):
    print(*a); print(*a, file=o)
for r, ds, fs in os.walk(SRC):
    rel = os.path.relpath(r, SRC)
    if rel.split(os.sep)[0] in CARD_DIRS: continue
    ds.sort()
    for f in sorted(fs):
        full = os.path.join(r, f); kb = os.path.getsize(full) // 1024
        try:
            with Image.open(full) as im: d = f'{im.size[0]}x{im.size[1]}'
        except Exception: d = '-'
        p(f'{os.path.join(rel, f)}  {d}  {kb}KB')