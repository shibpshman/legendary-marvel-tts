"""Builds TTS_work\\catalog.json from the four BoardGameGeek wiki pages 'Legendary Marvel Complete Card Text'
(saved as text): which Hero, Villain group, Henchmen group, Mastermind and Scheme belongs to which set.

Usage: python build_catalog.py [folder with the four .txt files]     (default TTS_work\\catalog_src)
Prints timestamped progress and a summary per set."""
import glob, json, os, re, sys, time

WORK = r'E:\Media\Board Games\TTS_work'
T0 = time.time()


def log(m): print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


def read(folder, pat):
    c = sorted(glob.glob(os.path.join(folder, pat)))
    if not c: sys.exit('Missing page in %s: %s' % (folder, pat))
    return [l.rstrip('\r\n').strip() for l in open(c[0], encoding='utf-8-sig', errors='replace').read().replace('\r', '').split('\n')]


def toc_and_body(lines):
    """Set names from the table of contents, and the lines after the index marker."""
    i = next(k for k, l in enumerate(lines) if l == 'Legendary Marvel Complete Card Text Index')
    toc = [l for l in lines[:i] if l and l not in ('Table of Contents',)]
    return toc, lines[i + 1:]


COPIES = re.compile(r'\s*\(\d+ cop(?:y|ies)\)$')
SECTION_TITLES = ('Bystanders', 'Setup Cards', 'Sidekicks and New Recruits', 'Starting Deck Cards', 'Wounds and Bindings', 'Heroes and Allies',
                  'Schemes and Plots', 'Masterminds and Commanders')


def blocks(body, sets):
    """Splits the page into blocks separated by blank lines; a set heading becomes its own ('SET', name) block,
    even where the page puts it directly after a card without a blank line."""
    out, cur = [], []
    for i, l in enumerate(body):
        nxt = body[i + 1] if i + 1 < len(body) else ''
        if l in SECTION_TITLES and nxt in sets:
            if cur: out.append(cur); cur = []
            out.append([l]); continue
        if l in sets and nxt == '':
            if cur: out.append(cur); cur = []
            out.append(('SET', l)); continue
        if l == '':
            if cur: out.append(cur); cur = []
        else:
            cur.append(l)
    if cur: out.append(cur)
    return out


def plausible_name(n):
    return ':' not in n and not n.endswith('.') and len(n) < 60 and n not in ('Bribe', 'Mastermind Transformed') and not n.startswith(("Whenever", "You can", "Epic ", "''"))


def team_line(l): return bool(l) and l.endswith(')') and (l.startswith('Microbadge') or l.startswith('('))


def heroes_of(lines):
    toc, body = toc_and_body(lines)
    sets = set(toc); out, cur = {}, None
    for b in blocks(body, sets):
        if isinstance(b, tuple): cur = b[1]; continue
        if cur and len(b) >= 2 and team_line(b[1]) and not COPIES.search(b[0]): out.setdefault(cur, []).append(b[0])
    return out


def groups_of(lines, villains):
    toc, body = toc_and_body(lines)
    sets = set(toc); out, cur = {}, None
    bl = blocks(body, sets)
    for k, b in enumerate(bl):
        if isinstance(b, tuple): cur = b[1]; continue
        if cur is None: continue
        if villains:
            # heading block: a single line, followed by a block whose first line is a card with copies
            if len(b) == 1 and k + 1 < len(bl) and not isinstance(bl[k + 1], tuple) and COPIES.search(bl[k + 1][0]):
                out.setdefault(cur, []).append(b[0])
        else:
            text = ' '.join(b)
            if 'VP:' in text and 'Attack:' in text and not COPIES.search(b[0]):
                out.setdefault(cur, []).append(b[0])
            elif len(b) == 1 and k + 1 < len(bl) and not isinstance(bl[k + 1], tuple) and (COPIES.search(b[0]) is None) and 'Attack:' in ' '.join(bl[k + 1]) and k + 2 < len(bl) and False:
                pass
    # headings in the Henchmen page that hold several single cards (Mandarin's Rings): single-line block followed by a card block
    if not villains:
        for k, b in enumerate(bl[:-1]):
            if isinstance(b, tuple): cur = b[1]; continue
            nb = bl[k + 1]
            if len(b) == 1 and not isinstance(nb, tuple) and re.search(r'\(\d+ cop(?:y|ies)\)$', nb[0]) and 'Attack:' in ' '.join(nb):
                out.setdefault(cur, []).append(b[0])
    return out


def main_sections(lines):
    toc, body = toc_and_body_main(lines)
    sets = set(toc)
    res = {'schemes': {}, 'masterminds': {}}
    cur, mode = None, None
    bl = blocks(body, sets)
    for k, b in enumerate(bl):
        if isinstance(b, tuple): cur = b[1]; continue
        if len(b) == 1 and b[0] in SECTION_TITLES:
            mode = 'schemes' if b[0] == 'Schemes and Plots' else ('masterminds' if b[0] == 'Masterminds and Commanders' else None); cur = None; continue
        if mode is None or cur is None: continue
        if mode == 'schemes' and len(b) >= 2 and b[1].startswith(('Setup:', 'Special Rules:', 'Twist', 'Evil Wins')):
            res['schemes'].setdefault(cur, []).append(b[0])
        if mode == 'masterminds' and len(b) >= 3 and plausible_name(b[0]) and not b[0].startswith('Epic ') and '(' not in b[0] and any(x.startswith('Master Strike') for x in b) and any(x.startswith('Attack:') for x in b):
            res['masterminds'].setdefault(cur, []).append(b[0])
        elif mode == 'masterminds' and len(b) == 1 and plausible_name(b[0]) and k + 1 < len(bl) and not isinstance(bl[k + 1], tuple) and any(x.startswith(('Always Leads', 'Master Strike', 'Epic')) for x in bl[k + 1][:4]):
            res['masterminds'].setdefault(cur, []).append(b[0])
    return res


def toc_and_body_main(lines):
    i0 = next(k for k, l in enumerate(lines) if l == 'Table of Contents')
    i1 = next(k for k, l in enumerate(lines) if k > i0 and l == 'Bystanders' and k + 2 < len(lines) and lines[k + 1] == 'Legendary (First Edition)' and lines[k + 2] == '')
    toc = [l for l in lines[i0 + 1:i1] if l]
    return toc, lines[i1:]


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, 'catalog_src')
    log('reading the four pages from %s' % folder)
    H = read(folder, '*Heroes*And*Allies*.txt'); V = read(folder, '*Villains*and*Adversaries*.txt')
    N = read(folder, '*Henchmen*.txt'); M = read(folder, '*Complete_Card_Text.txt')
    cat = {}
    for kind, data in (('heroes', heroes_of(H)), ('villains', groups_of(V, True)), ('henchmen', groups_of(N, False))):
        log('%s: %d sets, %d names' % (kind, len(data), sum(len(v) for v in data.values())))
        for s, names in data.items():
            for n in names: cat.setdefault(s, {}).setdefault(kind, []).append(n)
    log('reading Schemes and Masterminds from the main page')
    for kind, data in main_sections(M).items():
        log('%s: %d sets, %d names' % (kind, len(data), sum(len(v) for v in data.values())))
        for s, names in data.items():
            for n in names: cat.setdefault(s, {}).setdefault(kind, []).append(n)
    for s in cat:
        for k in cat[s]: cat[s][k] = list(dict.fromkeys(cat[s][k]))
    dst = os.path.join(WORK, 'catalog.json') if len(sys.argv) < 3 else sys.argv[2]
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    json.dump(cat, open(dst, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    for s, d in cat.items(): log('  %-45s %s' % (s, ' '.join('%s=%d' % (k, len(v)) for k, v in sorted(d.items()))))
    log('DONE: %d sets, %d names -> %s' % (len(cat), sum(len(v) for d in cat.values() for v in d.values()), dst))


if __name__ == '__main__':
    main()
