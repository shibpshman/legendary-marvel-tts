"""Turns the text of the Marvel History Scenarios PDF into TTS_work\\scenarios.json (one record per scenario).

Usage: python build_scenarios.py [scenarios.txt] [out.json]
The text comes from pdf_extract.py (TTS_work\\pdf_text\\Marvel_History_Scenarios*.txt). Prints timestamped progress and a summary."""
import glob, json, os, re, sys, time

WORK = r'E:\Media\Board Games\TTS_work'
T0 = time.time()


def log(m):
    print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


FIELDS = {'Source': 'Source', 'Scheme': 'Scheme', 'Mastermind': 'Mastermind', 'Villains': 'Villains', 'Villans': 'Villains',
          'Henchmen': 'Henchmen', 'Henchman': 'Henchmen', 'Heroes': 'Heroes', 'Notes': 'Notes'}
FRE = re.compile(r'^(%s):\s*(.*)$' % '|'.join(FIELDS))
SECTIONS = re.compile(r'^(THE \d{4}s|GOLDEN AGE|MARVEL NOIR|SECRET WARS 2015)$')
ASCII = {'\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u2013': '-', '\u2014': '-', '\ufffe': '-', '\uffff': '-', '\ufffd': '-', '\u00a0': ' '}


def clean(s):
    for a, b in ASCII.items(): s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s.encode('ascii', 'ignore').decode('ascii')).strip()


def split_top(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == '(': depth += 1
        if ch == ')': depth -= 1
        if ch == ',' and depth == 0: out.append(cur.strip()); cur = ''
        else: cur += ch
    if cur.strip(): out.append(cur.strip())
    return out


def item(text):
    """One list entry -> {name, fill, n, label, custom}. name has fill-in, count and a trailing (...) qualifier removed;
    qualifier is kept separately. custom is true when the parenthesis lists individual cards (x1, x2 ...)."""
    s = text.strip().rstrip('*').strip()
    label = s
    fill = None
    m = re.search(r'\(\s*fill[ -]?in for ([^)]*)\)', s, re.I)
    if m:
        fill = m.group(1).strip(); s = (s[:m.start()] + s[m.end():]).strip()
    n = None
    m = re.search(r'\s+x(\d+)\s*$', s)
    if m: n = int(m.group(1)); s = s[:m.start()].strip()
    qual, custom = None, False
    m = re.search(r'\((.*)\)\s*$', s)
    if m:
        qual = m.group(1).strip(); s = s[:m.start()].strip()
        custom = bool(re.search(r'\bx\d+\b', qual))
    s = re.sub(r'^(modified|Modified)\s+', '', s)
    return {'name': s, 'qual': qual, 'fill': fill, 'n': n, 'custom': custom, 'label': label}


def parse(txt):
    txt = txt.replace('\ufffe', '-').replace('\uffff', '-')
    pages = re.split(r'===== PAGE (\d+) =====\n', txt)
    phys = []
    for i in range(1, len(pages), 2):
        pg = int(pages[i])
        for ln in pages[i + 1].split('\n'):
            ln = ln.rstrip()
            if not ln.strip() or ln.strip() == str(pg): continue
            if ln.startswith('* = Modified') or ln.startswith('^ = New'): continue
            phys.append((pg, ln))
    recs, cur, pend, era, lastlen, infield = [], None, [], '', 0, False
    for idx, (pg, ln) in enumerate(phys):
        nxt = phys[idx + 1][1] if idx + 1 < len(phys) else ''
        m = FRE.match(ln)
        if m:
            k, v = FIELDS[m.group(1)], m.group(2)
            if k == 'Source':
                tl = [p for p in pend if not re.match(r'^(Note|NOTE)s?:', p) and not SECTIONS.match(p)]
                title = tl[-1] if tl else ''
                for p in pend:
                    if re.match(r'^(Note|NOTE)s?:', p) and recs: recs[-1].setdefault('xnotes', []).append(re.sub(r'^(Note|NOTE)s?:\s*', '', p))
                    elif SECTIONS.match(p): era = p
                cur = {'page': pg, 'title_raw': title, 'era': era, 'Source': v, '_last': 'Source'}
                recs.append(cur); pend = []; lastlen = len(ln); infield = True; continue
            if cur is None: continue
            cur[k] = v; cur['_last'] = k; lastlen = len(ln); infield = True; continue
        if cur is not None and infield and lastlen >= 68 and not nxt.startswith('Source:') and not SECTIONS.match(ln):
            cur[cur['_last']] += ' ' + ln; lastlen = len(ln); continue
        infield = False
        pend.append(ln)
    return recs


def balanced(s):
    """Closes parentheses a wrapped PDF line left open."""
    return s + ')' * max(0, s.count('(') - s.count(')'))


def split_depth0(s, sep=','):
    out, d, cur = [], 0, ''
    for ch in s:
        if ch == '(': d += 1
        if ch == ')': d -= 1
        if ch == sep and d == 0: out.append(cur.strip()); cur = ''
        else: cur += ch
    if cur.strip(): out.append(cur.strip())
    return out


def parse_card(s):
    s = re.sub(r'\(\s*fill[ -]?in for [^)]*\)', '', s, flags=re.I).strip()
    m = re.search(r'\s+x(\d+)\s*$', s)
    return {'name': (s[:m.start()] if m else s).strip().strip('"'), 'n': int(m.group(1)) if m else 1}


def parse_composite(label):
    """'Name (Group (Card x2, Card x1), Group (Card x2))' -> {'name', 'parts': [{'group', 'cards': [{'name', 'n'}]}], 'ok'}.
    ok is false when an entry is not 'Group (cards)' or a card name itself carries parentheses (then Setup refuses and shows the list)."""
    s = balanced(re.sub(r'^(modified|Modified)\s+', '', label.strip()))
    i = s.find('(')
    if i < 0 or not s.endswith(')'): return None
    name, inner = s[:i].strip().strip('"'), s[i + 1:-1]
    parts, ok = [], True
    for ent in split_depth0(inner):
        j = ent.find('(')
        if j < 0 or not ent.endswith(')'):
            ok = False; continue
        grp, cards = ent[:j].strip().strip('"'), ent[j + 1:-1]
        cl = [parse_card(c) for c in split_depth0(cards)]
        if any('(' in c['name'] or ')' in c['name'] or not c['name'] for c in cl): ok = False
        parts.append({'group': grp, 'cards': cl})
    return {'name': name, 'parts': parts, 'ok': ok and bool(parts)}


def split_notes(n):
    return [p.strip() for p in re.split(r'\s*/\s*|;\s*', n) if p.strip()]


VD = re.compile(r'^(?:Put |Add |Include )?(?P<n>.+?)\s+(?:in|to|into)\s+(?:the )?Villain Deck\)?\s*(?:\(fill[ -]?in for [^)]*\))?\)?$', re.I)
KO = re.compile(r'^Put (?P<n>.+?)(?: x\d+)? in KO pile as "(?P<l>[^"]+)"$', re.I)
HD = re.compile(r'^(?:Include|Place|Put|Add) (?P<n>.+?) x(?P<k>\d+) in Hero Deck$', re.I)


def parse_notes(notes):
    """Machine-readable setup instructions found in the Notes: Heroes shuffled into the Villain Deck, Henchmen groups put in the KO pile,
    Henchmen cards added to the Hero Deck. Everything else stays text."""
    out = {'vdeck': [], 'ko': [], 'herodeck': []}
    for p in split_notes(notes):
        p = re.sub(r'\(\s*fill[ -]?in for [^)]*\)', '', p).strip()
        p = re.sub(r'^(?:Solo,\s*)+', '', p, flags=re.I)
        if re.match(r'^(Solo|Use .*|Instead .*|.*instead of.*|.*considered.*|Replace .*)$', p, re.I): continue
        m = KO.match(p)
        if m: out['ko'].append({'name': m.group('n').strip(), 'label': m.group('l')}); continue
        m = HD.match(p)
        if m: out['herodeck'].append({'name': m.group('n').strip(), 'n': int(m.group('k'))}); continue
        m = VD.match(p.rstrip(')'))
        if m and not re.search(r'\b(Villain Mat|Hulk)\b', m.group('n')): out['vdeck'].append(m.group('n').strip())
    return out


def build(recs):
    eras, out = [], []
    for r in recs:
        for fld in ('Mastermind', 'Villains', 'Henchmen', 'Heroes', 'Scheme'):
            v = r.get(fld, '')
            m = re.search(r'\s+Note:\s*(.*)$', v)           # a wrapped Notes line that landed inside a list
            if m:
                r[fld] = v[:m.start()]
                r['xnotes'] = r.get('xnotes', []) + [m.group(1)]
        if r['era'] not in eras: eras.append(r['era'])
        t = r['title_raw']
        mod = 'modified' if t.startswith('*') else 'new' if t.startswith('^') else ''
        notes = clean(' / '.join([r.get('Notes', '')] + r.get('xnotes', []))).strip(' /')
        mm = item(clean(r.get('Mastermind', '')))
        vill = [item(clean(x)) for x in split_top(r.get('Villains', ''))]
        hench = [item(clean(x)) for x in split_top(r.get('Henchmen', ''))]
        heroes = [item(clean(x)) for x in split_top(r.get('Heroes', ''))]
        out.append({
            'title': clean(t.lstrip('*^ ')), 'era': eras.index(r['era']), 'mod': mod, 'page': r['page'], 'source': clean(r.get('Source', '')),
            'scheme': clean(r.get('Scheme', '')), 'mastermind': mm, 'villains': vill, 'henchmen': hench, 'heroes': heroes, 'notes': notes,
            'solo': bool(re.search(r'\bsolo\b', notes, re.I)), 'villain_mat': bool(re.search(r'villain (mat|board)', notes, re.I)),
            'custom': any(v['custom'] for v in vill + hench), 'actions': parse_notes(notes)})
        rec = out[-1]
        for it in vill:
            if it['custom']: it['composite'] = parse_composite(it['label'])
        for it in list(hench):
            mm_ = re.match(r'^(.*?)\s+x(\d+)$', it['name'])
            if it['qual'] and re.search(r'hero deck', it['qual'], re.I) and (it['n'] or mm_):       # 'MODOKs x6 (in Hero Deck)'
                rec['actions']['herodeck'].append({'name': mm_.group(1) if mm_ else it['name'], 'n': it['n'] or int(mm_.group(2))})
                rec['henchmen'] = [h for h in rec['henchmen'] if h is not it]
        rec['custom'] = any((v['custom'] and not (v.get('composite') and v['composite']['ok'])) for v in vill + rec['henchmen'])
        rec['n_composites'] = sum(1 for v in vill if v.get('composite') and v['composite']['ok'])
    return eras, out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    src = args[0] if args else None
    if src is None:
        c = glob.glob(os.path.join(WORK, 'pdf_text', 'Marvel_History_Scenarios*.txt')) + glob.glob('Marvel_History_Scenarios*.txt')
        if not c: sys.exit('No scenarios text found. Run pdf_extract.py on the PDF first, or pass the .txt path.')
        src = c[0]
    dst = args[1] if len(args) > 1 else os.path.join(WORK, 'scenarios.json')
    log('reading %s' % src)
    txt = open(src, encoding='utf-8-sig').read()
    log('parsing %d characters' % len(txt))
    recs = parse(txt)
    log('%d scenarios found; structuring fields' % len(recs))
    eras, out = build(recs)
    for i, r in enumerate(out):
        if i % 100 == 0: log('[%d/%d] checking %r' % (i + 1, len(out), r['title']))
    bad = [r for r in out if not r['title'] or not r['scheme'] or not r['mastermind']['name'] or not r['heroes']]
    for r in bad: log('WARNING: incomplete record on page %s: %r' % (r['page'], r['title']))
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    json.dump({'eras': [e.title() if e.isupper() and not e.startswith('THE') else e.replace('THE ', '') for e in eras], 'scenarios': out}, open(dst, 'w', encoding='utf-8'), indent=0)
    log('DONE: %d scenarios (%d solo, %d with a custom villain deck, %d incomplete) in %d sections -> %s' % (
        len(out), sum(r['solo'] for r in out), sum(r['custom'] for r in out), len(bad), len(eras), dst))


if __name__ == '__main__':
    main()
