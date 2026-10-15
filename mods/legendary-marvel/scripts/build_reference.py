"""Builds reference_data.json (scheme / mastermind card text + keyword glossary) from the OCR output.
Usage: python build_reference.py [card_text_ocr.csv] [rulebook.ocr.txt] [out.json]
Prints timestamped progress. Every OCR correction is listed in reference_corrections.txt next to the output."""
import csv, collections, difflib, json, os, re, sys, time

WORK = r'E:\Media\Board Games\TTS_work'
CARDS = os.path.join(WORK, 'card_text_ocr.csv')
RULES = os.path.join(WORK, 'rules_txt', 'Marvel_Legendary_Universal_Rules_v9.ocr.txt')
OUT = os.path.join(WORK, 'reference_data.json')
if not os.path.isfile(RULES):                         # the OCR file may sit elsewhere under TTS_work or in Downloads
    import glob
    hits = glob.glob(os.path.join(WORK, '**', '*Universal_Rules*.ocr.txt'), recursive=True) + \
        glob.glob(os.path.join(os.path.expanduser('~'), 'Downloads', '*Universal_Rules*.ocr.txt'))
    if hits: RULES = hits[0]
if len(sys.argv) > 1: CARDS = sys.argv[1]
if len(sys.argv) > 2: RULES = sys.argv[2]
if len(sys.argv) > 3: OUT = sys.argv[3]
T0 = time.time()


def log(m):
    print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


KEYWORDS = ['Abomination', 'Artifacts', 'Berserk', 'Bribe', 'Burrow', 'Card Values', 'Charge', 'Cheering Crowds', 'Chivalrous Duel',
    'Circle of Kung-Fu (and Quack-Fu)', 'Conqueror', 'Coordinate', 'Cosmic Threat', 'Cross-Dimensional Rampage', 'Danger Sense', 'Dark Memories',
    'Defeat', 'Demolish', 'Digest', 'Dodge', 'Dominate', 'Elusive', 'Empowered', 'Excessive Violence', 'Fateful Resurrection', 'Feast', 'Focus',
    'Fortify', 'Grey Heroes', 'Half-Points', 'Hidden Witnesses', 'Human Shields', 'HYDRA Level', 'Hyperspeed', 'Indigestion', 'Infinity Gems',
    'Investigate', 'Last Stand', 'Locations', 'Lightshow', 'Man (and Woman) Out of Time', 'Microscopic Size-Changing', 'Outwit', 'Patrol',
    'Phasing', 'Piercing Energy', 'Poison Villains', 'Reveal', 'Revenge', 'Rise of the Living Dead', 'Savior', 'Shards', 'S.H.I.E.L.D. Clearance',
    'S.H.I.E.L.D. Level', 'Size-Changing', 'Smash', 'Soaring Flight', 'Spectrum', 'Striker', 'Symbiote Bonds', 'Switcheroo', 'Teleport',
    'Thrown Artifacts', 'Transform', 'Ultimate Abomination', 'Undercover', 'Uru-Enchanted Weapons', 'Versatile', 'Villainous Weapons', 'Wall Crawl',
    'Worthy', 'Wounded Fury', 'X-Gene', 'X-Treme Attack']

ASCII = {'\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'", '\u2013': '-', '\u2014': '-', '\u2026': '...', '\u00b7': '-', '\u2022': '-',
         '\u2605': '', '\u2606': '', '\u00a0': ' ', '\u00d7': 'x'}


def ascii_only(s):
    for k, v in ASCII.items(): s = s.replace(k, v)
    return s.encode('ascii', 'ignore').decode('ascii')


def norm(s): return re.sub(r'[^a-z0-9]', '', s.lower())


# ---------------------------------------------------------------- vocabulary (what is real English / game text)
rules_text = ascii_only(open(RULES, encoding='utf-8', errors='replace').read())
rows = list(csv.DictReader(open(CARDS, encoding='utf-8-sig')))
word = re.compile(r"[A-Za-z][A-Za-z'-]*[A-Za-z]|[A-Za-z]")
vocab = collections.Counter(w.lower() for w in word.findall(rules_text))
card_words = collections.Counter(w.lower() for r in rows for w in word.findall(ascii_only(r['text'])))
for w, n in card_words.items():
    if n >= 3: vocab[w] += n                      # words that recur across cards are not typos
log('vocabulary: %d distinct words from the rulebook, %d recurring card words' % (len(vocab), sum(1 for n in card_words.values() if n >= 3)))
corrections = collections.Counter()


def edits1(w):
    letters = 'abcdefghijklmnopqrstuvwxyz'
    sp = [(w[:i], w[i:]) for i in range(len(w) + 1)]
    return set([a + b[1:] for a, b in sp if b] + [a + b[1] + b[0] + b[2:] for a, b in sp if len(b) > 1] +
               [a + c + b[1:] for a, b in sp if b for c in letters] + [a + c + b for a, b in sp for c in letters])


def correct_word(w, protect):
    lw = w.lower()
    if len(lw) < 6 or lw in vocab or lw in protect or "'" in lw or '-' in lw: return w
    best, bn = None, 0
    for c in edits1(lw):
        n = vocab.get(c, 0)
        if n > bn: best, bn = c, n
    if best is None or bn < 8: return w                      # only trust well-attested words
    if lw.startswith(best) or best.startswith(lw) or lw.rstrip('s') == best.rstrip('s'): return w   # inflections are not typos
    if lw[0] != best[0]: return w                            # OCR rarely misreads the first letter of a real word
    corrections['%s -> %s' % (lw, best)] += 1
    return best.capitalize() if w[0].isupper() else best


FIXES = [   # known OCR glitches of this card font / layout
    (r'\bT[wv]{1,2}i?s?ts?\b', None), ]
def fix_glitches(t):
    t = re.sub(r'\b(?:Tvvist|Twvist|Tvist|Iwist|Twist|Tist|Twis t|Tvwist|Twlst)(s?)\b', lambda m: 'Twist' + m.group(1), t)
    t = re.sub(r'\b(?:Tvvists|Tvists|Twvists)\b', 'Twists', t)
    t = re.sub(r'\bTw\s?ists\b', 'Twists', t)
    t = re.sub(r'(?<=: )B(?= Twists?)', '8', t)                                  # "Setup: B Twists"
    t = re.sub(r'\b(\d) (\d) (Twists?)\b', r'\1\2 \3', t)                        # "1 1 Twists"
    t = re.sub(r'(?<=\d)O(?=\d|\b)', '0', t)                                     # 3O -> 30
    t = re.sub(r'\bS\.H\.[1l]\.E\.L\.D\.', 'S.H.I.E.L.D.', t)
    t = t.replace('""', '"')
    t = re.sub(r'\bAame\b', 'name', t)
    t = re.sub(r'\bHeroe\b', 'Hero', t)
    t = re.sub(r'(?<=\w)\s+([,.;:])', r'\1', t)
    t = re.sub(r"\bTwist [GB](?=:)", lambda m: 'Twist ' + ('6' if m.group(0)[-1] == 'G' else '8'), t)
    t = re.sub(r"\bE[vy][il1!][lt1i] [Ww]ins?:?\s*!", 'Evil Wins!', t)
    t = re.sub(r"\bE[vy][il1!][lt1i] [Ww]ins?(?:['`:]|\s+(?=[A-Z@]))?(?!\w*!)", 'Evil Wins:', t)
    for a, b in (('Deek', 'Deck'), ('Scherme', 'Scheme'), ('Tuvist', 'Twist'), ('Tiwist', 'Twist'), ("next, to'this", 'next to this'),
                 ('Villaln', 'Villain'), ('Vilain', 'Villain')):
        t = t.replace(a, b)
    return t


def clean_prose(t, protect=frozenset()):
    t = fix_glitches(ascii_only(t))
    out = []
    for tok in re.split(r'(\s+)', t):
        m = re.fullmatch(r'([^A-Za-z0-9]*)(.*?)([^A-Za-z0-9]*)', tok)           # keep punctuation, correct only the word core
        core = m.group(2)
        if tok.strip() and word.fullmatch(core): core = correct_word(core, protect)
        out.append(m.group(1) + core + m.group(3))
    return re.sub(r'\s+', ' ', ''.join(out)).strip()


# ---------------------------------------------------------------- schemes and masterminds
FOOT = re.compile(r"\s(?:\S{0,3}\s?&\s?[@O(0]?\s?\S{0,3}20\d\d|[@O(]\s?\S{0,2}20\d\d|\S*[Ss]ubs?[.,]|\S*U[D0O]\(?C\b|\S*\bUDC|\S*(?:IM|TM|TA|JM)\s*&|\S*[@]\S*|\s&\s?\S*|\S*[MN]a?r[vw]e?l\S*\s*&|\S*MARVEL|\S*AARVEL)")


JUNK_OK = {'HQ', 'KO', 'MK', 'VP', 'HYDRA', 'SHIELD', 'A', 'I'}


def junk_tok(tok):
    c = tok.strip('.,;:!?()"\'[]')
    if c in JUNK_OK or re.fullmatch(r'\d+', c): return False
    if re.search(r'[@&]', tok) or not c: return True
    if re.search(r'[A-Za-z]\d|\d[A-Za-z]', c) and not re.search(r"\d(?:st|nd|rd|th|VP|\*)$", c): return True
    if re.search(r'[a-z][A-Z]|[A-Z]{2,}[a-z]', c) and not re.search(r"^KO'?d?$", c): return True
    if len(c) <= 2 and not c.isupper() is False and c.isalpha() and not re.search(r'[.!?]$', tok) and c.upper() == c: return True
    if c.isupper() and len(c) >= 3 and not re.fullmatch(r'(?:[A-Z]\.)+', c + '.' if not c.endswith('.') else c): return True
    return False


def strip_tail(t):
    toks = t.split()
    while toks and junk_tok(toks[-1]): toks.pop()
    return ' '.join(toks)


def cut_footer(t):
    t = t.replace(' | ', ' ')
    m = FOOT.search(t, len(t) // 3)
    if m: t = t[:m.start()]
    return strip_tail(t.strip())


START_S = re.compile(r'(Setup:|Special Rules:|Twists? ?\d*(?:-\d+)?:|Evil Wins?:|Evil wins!)', re.I)


def card_sections(kind, name, text):
    t = cut_footer(fix_glitches(ascii_only(text)))
    if kind == 'mastermind':
        m = re.search(r'(?i)\bAl\s?w[a-z]*ys Leads', t)
        pre = ''
        if m:
            lab = re.search(r'\bMAS[A-Z]{2,6}M[A-Z]{0,2}ND\b', t[:m.start()])
            pre = t[lab.end():m.start()].strip() if lab else ''
            t = t[m.start():]
        if len(pre) >= 10 or pre.split(' ')[0] in KEYWORDS:                  # static Mastermind rules / keyword printed above Always Leads
            pre = re.sub(r'\s+', ' ', pre)
            t = 'Mastermind Rules: ' + pre + ' ' + t
        t = re.sub(r'(?i)\bAl\s?w[a-z]*ys Leads:?', 'Always Leads:', t)
        t = re.sub(r'(?i)\bMaster\s*St[a-z]*e?:?', 'Master Strike:', t)
    else:
        m = START_S.search(t)
        t = t[m.start():] if m else t
    t = clean_prose(t, protect=frozenset(re.findall(r'[a-z]+', name.lower())))
    if kind == 'mastermind':
        for _ in range(4):
            t = re.sub(r'\s+(?:\d{1,2}|\S{1,3}!|[A-Z][a-z]{1,2}|[a-z]{1,2})\s*$', '', t)      # attack value / footer remnants
        if not re.search(r'[.!?]$', t): t += '.'
        t = re.sub(r'(Always Leads:?)', r'\n\1', t); t = re.sub(r'(Master Strike:)', r'\n\1', t)
        t = re.sub(r'Always Leads(?!:)', 'Always Leads:', t)
    else:
        for k in ('Setup:', 'Special Rules:', 'Evil Wins:'): t = t.replace(k, '\n' + k)
        t = re.sub(r'\s(Twists? \d+(?:-\d+)?:|Twist:)', r'\n\1', t)
    t = re.sub(r'(Twist \d+:)\s*\n?Evil Wins:?$', r'\1 Evil Wins!', t)
    t = t.replace('[ ?.MK etc.J', '(A, X-Men, Spider Friends, MK, etc.)').replace(']', ')').replace('[', '(')
    t = re.sub(r'<<([^>]+)>>', r'[\1]', t)
    return '\n'.join(x.strip() for x in t.split('\n') if x.strip())


schemes, masterminds = {}, {}
for r in rows:
    txt = card_sections(r['kind'], r['name'], r['text'])
    (schemes if r['kind'] == 'scheme' else masterminds)[r['name']] = {'set': r['set'], 'text': txt}
log('cleaned %d scheme cards and %d mastermind cards' % (len(schemes), len(masterminds)))

# hand-read card text (icons included) replaces the OCR text for the cards listed in icon_fixes.json
FIXES_PATH = next((p for p in (os.path.join(WORK, 'icon_fixes.json'), os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon_fixes.json'), 'icon_fixes.json') if os.path.isfile(p)), None)
if FIXES_PATH:
    fixes = json.load(open(FIXES_PATH, encoding='utf-8'))
    hit = 0
    for nm, txt in fixes.items():
        tgt = schemes if nm in schemes else (masterminds if nm in masterminds else None)
        if tgt is None: log('   icon_fixes.json: no card named %r' % nm); continue
        tgt[nm]['text'] = ascii_only(txt).strip(); hit += 1
    log('applied %d hand-read cards from %s' % (hit, FIXES_PATH))
else:
    log('no icon_fixes.json found; using the OCR text as it is')

# ---------------------------------------------------------------- keyword glossary from the Universal Rulebook OCR
start = rules_text.index('Keyword Abilities', rules_text.index('===== PAGE 5 ====='))
end = rules_text.index('Card Clarifications', start)
body = rules_text[start:end]
body = re.sub(r'===== PAGE \d+ =====', '', body)
lines = [l.strip() for l in body.split('\n')]
lines = [l for l in lines if l and not re.fullmatch(r'\d{1,2}', l) and l != 'Keyword Abilities']
heads, pos = [], 0
for name in KEYWORDS:
    target = norm(name)
    found = None
    for i in range(pos, len(lines)):
        ln = norm(lines[i])
        if ln == target or (len(ln) >= 5 and difflib.SequenceMatcher(None, ln, target).ratio() >= 0.88 and len(lines[i]) < len(name) + 12):
            found = i; break
    if found is None:
        log('   keyword heading not found: %s' % name); continue
    heads.append((name, found)); pos = found + 1
keywords = collections.OrderedDict()
for k, (name, i) in enumerate(heads):
    j = heads[k + 1][1] if k + 1 < len(heads) else len(lines)
    para, cur = [], ''
    for l in lines[i + 1:j]:
        if re.match(r'^[-.:\u00b7\u2022]\s+(?=[A-Z"\'(])', l) or re.match(r'^[\u2022\u00b7]', l):
            if cur: para.append(cur)
            cur = '- ' + re.sub(r'^[-.:\u00b7\u2022]\s*', '', l)
        else:
            cur = (cur + ' ' + l).strip() if cur else l
    if cur: para.append(cur)
    keywords[name] = clean_prose('\n'.join(para)).replace(' - ', '\n- ') if False else '\n'.join(clean_prose(p) for p in para)
log('%d of %d keywords parsed' % (len(keywords), len(KEYWORDS)))

KFIX = next((p for p in (os.path.join(WORK, 'keyword_fixes.json'), os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keyword_fixes.json'), 'keyword_fixes.json') if os.path.isfile(p)), None)
if KFIX:
    kf = json.load(open(KFIX, encoding='utf-8'))
    for nm, txt in kf.items():
        if nm not in keywords: log('   keyword_fixes.json: no keyword named %r' % nm); continue
        keywords[nm] = ascii_only(txt).strip()
    log('applied %d hand-read keywords from %s' % (len(kf), KFIX))

VSPEC = next((p for p in (os.path.join(WORK, 'villains_set_spec.json'), os.path.join(os.path.dirname(os.path.abspath(__file__)), 'villains_set_spec.json'), 'villains_set_spec.json') if os.path.isfile(p)), None)
if VSPEC:
    vs = json.load(open(VSPEC, encoding='utf-8'))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from scenario_names import to_normal_play, VILLAINS_GLOSSARY
    for s in vs['schemes']:
        schemes[s['deck_name']] = {'text': to_normal_play('\n'.join(s['text'])), 'set': 'Villains'}
    for m in vs['masterminds']:
        masterminds[m['deck_name']] = {'text': to_normal_play('\n'.join(m['text'])), 'set': 'Villains'}
    keywords['Villains Set Terms'] = VILLAINS_GLOSSARY
    log('added the Villains set: %d Plots, %d Commanders (catalog text, translated to normal-play wording) and the Villains Set Terms keyword' % (len(vs['schemes']), len(vs['masterminds'])))

data = {'schemes': schemes, 'masterminds': masterminds, 'keywords': keywords}
os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
json.dump(data, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=True)
with open(os.path.splitext(OUT)[0] + '_corrections.txt', 'w', encoding='utf-8') as f:
    for k, n in corrections.most_common(): f.write('%4d  %s\n' % (n, k))
size = sum(len(v['text']) for v in schemes.values()) + sum(len(v['text']) for v in masterminds.values()) + sum(len(v) for v in keywords.values())
log('DONE: %d chars of reference text, %d automatic word corrections -> %s' % (size, sum(corrections.values()), OUT))
