"""Builds the 'Villains' expansion bag (Legendary Villains core set) in the exact format of the other expansion bags,
from the card images in Base Sets\\Villains Core Set and villains_set_spec.json (card names, copies, classes, teams).

Templates (bag, nested bags, decks, cards, backs, Lua) are copied from the Venom expansion bag of the Workshop mod JSON, so the new bag
unpacks and repacks like the others. Decks reference sheet images this module writes into the assets folder."""
import copy, difflib, glob, json, os, random, re, time

from scenario_names import norm

from PIL import Image

TEMPLATE_BAG = '1ebd5a'          # Venom
BAG_GUID = 'c0de11'
CELL_W, CELL_H = 600, 843
MAX_COLS, MAX_ROWS = 7, 5
BAG_POS = {'posX': 30.55, 'posY': 3.436482, 'posZ': 22.4}


def n2(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def deck_name(s):
    """Mod style: no punctuation (Dr. Octopus -> Dr Octopus)."""
    return re.sub(r'\s+', ' ', re.sub(r"[^A-Za-z0-9 ]", '', s.replace('-', ' ').replace('&', 'And'))).strip()


def title_case(s):
    return ' '.join(w[:1].upper() + w[1:] for w in s.split(' '))


class Log:
    def __init__(self, fn=None): self.t0 = time.time(); self.fn = fn
    def __call__(self, m):
        line = '[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - self.t0, m)
        (self.fn or print)(line) if self.fn else print(line, flush=True)


class Sheets:
    """Packs card images into grids and writes them as JPEG sheets; add() returns (deck id, index)."""
    _next_id = 200

    def __init__(self, label, out_dir, url_dir, log, cols=MAX_COLS, rows=MAX_ROWS):
        self.label, self.out_dir, self.url_dir, self.log = label, out_dir, url_dir, log
        self.cols, self.rows = cols, rows
        self.sheets = []        # dicts: id, paths, file
        self.n = 0

    def add(self, path):
        if not self.sheets or len(self.sheets[-1]['paths']) >= self.cols * self.rows:
            Sheets._next_id += 1
            self.n += 1
            self.sheets.append({'id': Sheets._next_id, 'paths': [], 'file': '%s_%d.jpg' % (self.label, self.n)})
        s = self.sheets[-1]
        s['paths'].append(path)
        return s['id'], len(s['paths']) - 1

    def entry(self, deck_id, back_url):
        s = next(x for x in self.sheets if x['id'] == deck_id)
        n = len(s['paths'])
        cols = min(self.cols, n)
        rows = -(-n // self.cols)
        return {'FaceURL': 'file:///' + os.path.join(self.url_dir, s['file']).replace('\\', '/'), 'BackURL': back_url, 'NumWidth': cols, 'NumHeight': rows,
                'BackIsHidden': False, 'UniqueBack': False, 'Type': 0}

    def write(self):
        os.makedirs(self.out_dir, exist_ok=True)
        for s in self.sheets:
            n = len(s['paths'])
            cols, rows = min(self.cols, n), -(-n // self.cols)
            sheet = Image.new('RGB', (cols * CELL_W, rows * CELL_H), (0, 0, 0))
            for i, p in enumerate(s['paths']):
                with Image.open(p) as im:
                    im = im.convert('RGBA')
                    bg = Image.new('RGB', im.size, (0, 0, 0)); bg.paste(im, mask=im.split()[3])
                    sheet.paste(bg.resize((CELL_W, CELL_H), Image.LANCZOS), ((i % self.cols) * CELL_W, (i // self.cols) * CELL_H))
            dst = os.path.join(self.out_dir, s['file'])
            sheet.save(dst, 'JPEG', quality=90)
            self.log('   wrote %s (%d cards, %dx%d px, %.1f MB)' % (s['file'], n, sheet.size[0], sheet.size[1], os.path.getsize(dst) / 1e6))


class Namer:
    """Reads card names off the images (OCR) to tell apart cards whose files are only numbered."""
    def __init__(self, cache_path, log, enabled=True):
        self.cache_path, self.log, self.enabled = cache_path, log, enabled
        self.cache = json.load(open(cache_path, encoding='utf-8')) if cache_path and os.path.exists(cache_path) else {}
        self.engine = None

    def lines(self, path):
        key = os.path.basename(path)
        if key in self.cache: return self.cache[key]
        if not self.enabled: return []
        if self.engine is None:
            from rapidocr_onnxruntime import RapidOCR
            self.engine = RapidOCR()
        import numpy as np
        with Image.open(path) as im:
            im = im.convert('RGB')
            s = min(1.0, 1990 / max(im.size))
            if s < 1: im = im.resize((int(im.size[0] * s), int(im.size[1] * s)), Image.LANCZOS)
            res, _ = self.engine(np.array(im))
        out = [t for _, t, sc in (res or [])]
        self.cache[key] = out
        if self.cache_path: json.dump(self.cache, open(self.cache_path, 'w', encoding='utf-8'))
        return out

    def score(self, name, lines):
        a = n2(name)
        best = 0.0
        for l in lines:
            b = n2(l)
            if not b: continue
            if a in b: return 1.0
            best = max(best, difflib.SequenceMatcher(None, a, b).ratio())
        return best

    def assign(self, paths, names, what):
        """Returns {path: name}: the permutation with the best total OCR score; falls back to the given order."""
        import itertools
        if len(paths) != len(names): raise ValueError('%s: %d images for %d names' % (what, len(paths), len(names)))
        lines = {p: self.lines(p) for p in paths}
        best, best_perm = -1, tuple(range(len(names)))
        for perm in itertools.permutations(range(len(names))):
            s = sum(self.score(names[perm[i]], lines[p]) for i, p in enumerate(paths))
            if s > best + 1e-9: best, best_perm = s, perm
        avg = best / max(1, len(paths))
        if avg < 0.6:
            self.log('   WARNING: %s: names could not be read reliably (score %.2f); using list order, check them in game' % (what, avg))
            best_perm = tuple(range(len(names)))
        return {p: names[best_perm[i]] for i, p in enumerate(paths)}, avg


def all_guids(o, acc):
    if isinstance(o, dict):
        g = o.get('GUID')
        if isinstance(g, str): acc.add(g)
        for v in o.values(): all_guids(v, acc)
    elif isinstance(o, list):
        for v in o: all_guids(v, acc)
    return acc


REPACK_HENCH = '''        if v.name == "Henchmen" then
            self.takeObject({guid = v.guid})
            local henchmen = getObjectFromGUID(v.guid)
            local objs = henchmenBag.getObjects()
            for key, val in pairs(objs) do
                henchmenBag.takeObject({guid = val.guid})
                local hench = getObjectFromGUID(val.guid)
                if hench.hasTag("%(TAG)s") then
                    henchmen.putObject(hench)
                else
                    henchmenBag.putObject(hench)
                end
            end
            self.putObject(henchmen)
        end
'''


def build(mod, spec, lib_dir, assets_img, work_dir, log, ocr=True):
    tops = {o.get('GUID'): o for o in mod['ObjectStates']}
    if TEMPLATE_BAG not in tops: raise SystemExit('Template bag %s (Venom) not found in the mod JSON' % TEMPLATE_BAG)
    tpl = tops[TEMPLATE_BAG]
    kids = {c['Nickname']: c for c in tpl['ContainedObjects']}
    hero_deck_t, vill_deck_t, mm_deck_t, scheme_deck_t = [kids[k]['ContainedObjects'][0] if k != 'Schemes' else kids[k] for k in ('Heroes', 'Villains', 'Masterminds', 'Schemes')]
    hero_card_t, vill_card_t, scheme_card_t = hero_deck_t['ContainedObjects'][0], vill_deck_t['ContainedObjects'][0], scheme_deck_t['ContainedObjects'][0]
    tactic_t = next(c for c in mm_deck_t['ContainedObjects'] if 'Tactic' in (c.get('Tags') or []))
    face_t = next(c for c in mm_deck_t['ContainedObjects'] if 'Face Card' in (c.get('Tags') or []))
    back = lambda d: next(iter(d['CustomDeck'].values()))['BackURL']
    BACK = {'hero': back(hero_card_t), 'villain': back(vill_card_t), 'scheme': back(scheme_card_t), 'tactic': back(tactic_t), 'face': back(face_t)}
    tag = spec['exp_tag']
    used = all_guids(mod, set())
    rng = random.Random(20260101)

    def guid():
        while True:
            g = '%06x' % rng.randrange(0x100000, 0xffffff)
            if g not in used: used.add(g); return g

    if BAG_GUID in used: raise SystemExit('GUID %s is already used in the mod' % BAG_GUID)
    used.add(BAG_GUID)
    Sheets._next_id = 200
    out_dir = assets_img
    sh = {k: Sheets('villains_' + k, out_dir, out_dir, log) for k in ('heroes', 'villains', 'henchmen', 'tactics', 'faces', 'schemes')}
    sh['tactics'].cols, sh['tactics'].rows = 4, 4
    sh['faces'].cols, sh['faces'].rows = 2, 2
    namer = Namer(os.path.join(work_dir, 'ocr_cache.json'), log, ocr)
    report = []

    def card(templ, name, tags, deck_id, idx, entry, name_type=None):
        c = copy.deepcopy(templ)
        c['GUID'] = guid(); c['Nickname'] = name; c['Tags'] = sorted(tags)
        c['CardID'] = deck_id * 100 + idx
        c['CustomDeck'] = {str(deck_id): entry}
        if name_type: c['Name'] = name_type
        return c

    def deck(templ, name, tags, cards, ids_entries):
        d = copy.deepcopy(templ)
        d['GUID'] = guid(); d['Nickname'] = name; d['Tags'] = sorted(tags)
        d.pop('_trimmed', None)
        d['ContainedObjects'] = cards
        d['DeckIDs'] = [c['CardID'] for c in cards]
        d['CustomDeck'] = {str(k): v for k, v in ids_entries.items()}
        return d

    # ---- collect work: (kind, deck spec, [(card spec, image path)]) ---------------------------------------------------
    def folder(*parts): return os.path.join(lib_dir, *parts)
    heroes_work, villains_work, hench_work, mm_work, scheme_work = [], [], [], [], []
    log('matching card images to card names')
    for h in spec['heroes']:
        fol = next((d for d in os.listdir(folder('Villains')) if n2(d) == n2(h['name'])), None)
        if fol is None: raise SystemExit('No image folder for Hero %r under %s' % (h['name'], folder('Villains')))
        files = sorted(glob.glob(os.path.join(folder('Villains', fol), '*.png')))
        if len(files) != len(h['cards']): raise SystemExit('Hero %s: %d images for %d cards' % (h['name'], len(files), len(h['cards'])))
        by_copies = {}
        for c in h['cards']: by_copies.setdefault(c['copies'], []).append(c)
        rare = [f for f in files if 'Rare' in os.path.basename(f)]; unc = [f for f in files if 'Uncommon' in os.path.basename(f)]
        com = [f for f in files if 'Common' in os.path.basename(f) and 'Uncommon' not in os.path.basename(f)]
        pairs = []
        if len(rare) == 1 and len(unc) == 1 and len(com) == 2 and len(by_copies.get(5, [])) == 2:
            pairs.append((rare[0], by_copies[1][0])); pairs.append((unc[0], by_copies[3][0]))
            m, avg = namer.assign(com, [c['name'] for c in by_copies[5]], 'Hero ' + h['name'])
            for p in com: pairs.append((p, next(c for c in by_copies[5] if c['name'] == m[p])))
            report.append('hero %-12s commons: %s (ocr %.2f)' % (h['name'], ', '.join('%s=%s' % (os.path.basename(p)[-14:], c['name']) for p, c in pairs[2:]), avg))
        else:
            for f, c in zip(files, h['cards']): pairs.append((f, c))
            report.append('hero %-12s WARNING: unusual file set, matched in order' % h['name'])
        heroes_work.append((h, pairs))
    for g in spec['villains']:
        fol = next((d for d in os.listdir(folder('Adversaries')) if n2(d) == n2(g['name'])), None)
        if fol is None: raise SystemExit('No image folder for Villain group %r' % g['name'])
        files = glob.glob(os.path.join(folder('Adversaries', fol), '*.png'))
        pairs = []
        for c in g['cards']:
            f = next((x for x in files if n2(os.path.splitext(os.path.basename(x))[0]).endswith(n2(c['name']))), None)
            if f is None: raise SystemExit('Group %s: no image for %r among %s' % (g['name'], c['name'], [os.path.basename(x) for x in files]))
            pairs.append((f, c))
        villains_work.append((g, pairs))
    stems = {n2(os.path.splitext(f)[0]): os.path.join(folder('Backup Adversaries'), f) for f in os.listdir(folder('Backup Adversaries')) if f.lower().endswith('.png')}
    for h in spec['henchmen']:
        key = next((k for k in stems if k.startswith(n2(h['name'])) or n2(h['name']).startswith(k)), None)
        if key is None: raise SystemExit('No image for Henchmen group %r' % h['name'])
        hench_work.append((h, stems[key]))
    for m in spec['masterminds']:
        fol = next((d for d in os.listdir(folder('Commanders')) if n2(d) == n2(m['name'])), None)
        if fol is None: raise SystemExit('No image folder for Commander %r' % m['name'])
        files = sorted(glob.glob(os.path.join(folder('Commanders', fol), '*.png')))
        tact = [f for f in files if 'Tactic' in os.path.basename(f)]; face = [f for f in files if 'Tactic' not in os.path.basename(f)]
        if len(face) != 1 or len(tact) != len(m['tactics']): raise SystemExit('Commander %s: %d face and %d tactic images' % (m['name'], len(face), len(tact)))
        assigned, avg = namer.assign(tact, [t['name'] for t in m['tactics']], 'Commander ' + m['name'])
        report.append('mastermind %-10s tactics: %s (ocr %.2f)' % (m['name'], ', '.join('%s=%s' % (os.path.basename(p)[-9:-4], assigned[p]) for p in tact), avg))
        mm_work.append((m, face[0], [(p, assigned[p]) for p in tact]))
    plots = {norm(os.path.splitext(f)[0].replace('+', ' ')): os.path.join(folder('Plot'), f) for f in os.listdir(folder('Plot')) if f.lower().endswith('.png')}
    for s in spec['schemes']:
        key = next((k for k in plots if k == norm(s['name']) or k.startswith(norm(s['name'])[:20])), None)
        if key is None: raise SystemExit('No image for Plot %r' % s['name'])
        fname = os.path.splitext(os.path.basename(plots[key]))[0].replace('+', ' ')
        scheme_work.append((s, plots[key], title_case(fname)))
    namer_cache_saved = True

    # ---- put every image on a sheet ----------------------------------------------------------------------------------
    log('packing sheets')
    pos = {}
    for h, pairs in heroes_work:
        for f, c in pairs: pos[('h', h['name'], c['name'])] = sh['heroes'].add(f)
    for g, pairs in villains_work:
        for f, c in pairs: pos[('v', g['name'], c['name'])] = sh['villains'].add(f)
    for h, f in hench_work: pos[('n', h['name'])] = sh['henchmen'].add(f)
    for m, face, tact in mm_work:
        pos[('mf', m['name'])] = sh['faces'].add(face)
        for f, nm in tact: pos[('mt', m['name'], nm)] = sh['tactics'].add(f)
    for s, f, nm in scheme_work: pos[('s', s['name'])] = sh['schemes'].add(f)
    for k, s in sh.items(): s.write()
    ent = lambda kind, did: sh[kind].entry(did, BACK[{'heroes': 'hero', 'villains': 'villain', 'henchmen': 'villain', 'tactics': 'tactic', 'faces': 'face', 'schemes': 'scheme'}[kind]])

    # ---- objects -------------------------------------------------------------------------------------------------------
    log('building decks')
    hero_decks = []
    for h, pairs in heroes_work:
        name = 'Venom Sinister Six' if n2(h['name']) == 'venom' else deck_name(h['name'])
        team = '' if h['team'] == 'Unaffiliated' else h['team']
        dtags = [name, 'Hero', tag] + ([team] if team else [])
        cards, entries = [], {}
        for f, c in pairs:
            did, idx = pos[('h', h['name'], c['name'])]
            e = ent('heroes', did); entries[did] = e
            for _ in range(c['copies']):
                cards.append(card(hero_card_t, c['name'], dtags + ([c['cls']] if c['cls'] else []), did, idx, e))
        hero_decks.append(deck(hero_deck_t, name, dtags, cards, entries))
        report.append('hero deck %-20s %d cards, team %s' % (name, len(cards), team or '-'))
    vill_decks = []
    for g, pairs in villains_work:
        name = deck_name(g['name'])
        t = [name, tag, 'Villain']
        cards, entries = [], {}
        for f, c in pairs:
            did, idx = pos[('v', g['name'], c['name'])]
            e = ent('villains', did); entries[did] = e
            cards += [card(vill_card_t, c['name'], t, did, idx, e) for _ in range(c['copies'])]
        vill_decks.append(deck(vill_deck_t, name, t, cards, entries))
    hench_decks = []
    for h, f in hench_work:
        name = deck_name(h['name']).replace('SHIELD Assault Squad', 'SHIELD Assault Squad')
        t = [tag, 'Henchman']
        did, idx = pos[('n', h['name'])]
        e = ent('henchmen', did)
        hench_decks.append(deck(vill_deck_t, name, t, [card(vill_card_t, name, t, did, idx, e) for _ in range(10)], {did: e}))
    mm_decks = []
    for m, face, tact in mm_work:
        name = deck_name(m['name'])
        cards, entries = [], {}
        for f, nm in tact:
            did, idx = pos[('mt', m['name'], nm)]
            e = ent('tactics', did); entries[did] = e
            cards.append(card(tactic_t, nm, [name, 'Mastermind', 'Tactic', tag], did, idx, e))
        did, idx = pos[('mf', m['name'])]
        e = ent('faces', did); entries[did] = e
        cards.append(card(face_t, name, ['Face Card', name, 'Mastermind', tag], did, idx, e))
        mm_decks.append(deck(mm_deck_t, name, [name, 'Mastermind', tag], cards, entries))
    s_cards, s_entries = [], {}
    for s, f, nm in scheme_work:
        did, idx = pos[('s', s['name'])]
        e = ent('schemes', did); s_entries[did] = e
        s_cards.append(card(scheme_card_t, nm, ['Scheme', tag], did, idx, e))
    schemes = deck(scheme_deck_t, 'Schemes', ['Scheme', tag], s_cards, s_entries)

    def nested(nick, decks):
        b = copy.deepcopy(kids['Villains'] if nick != 'Heroes' and nick != 'Masterminds' else kids[nick])
        b['GUID'] = guid(); b['Nickname'] = nick; b['ContainedObjects'] = decks
        return b

    top = copy.deepcopy(tpl)
    top['GUID'] = BAG_GUID
    top['Nickname'] = spec.get('bag_name', 'Villains')
    top['Transform'].update(BAG_POS)
    top['ContainedObjects'] = [nested('Heroes', hero_decks), nested('Villains', vill_decks), nested('Masterminds', mm_decks), nested('Henchmen', hench_decks), schemes]
    lua = tpl['LuaScript'].replace('Venom Expansion', tag)
    marker = '    local schemesFound = 0\n'
    if marker not in lua: raise SystemExit('The Venom bag script has no repack marker; cannot add Henchmen handling')
    at = lua.rfind('\n    end\n', 0, lua.index(marker)) + 1      # the 'end' that closes the for-loop over the bag contents
    lua = lua[:at] + REPACK_HENCH.replace('%(TAG)s', tag) + lua[at:]
    top['LuaScript'] = lua
    return top, report
