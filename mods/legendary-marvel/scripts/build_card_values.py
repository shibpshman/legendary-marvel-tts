"""Builds card_values.json: printed Attack / Recruit per Hero card name, for the in-game "Played" count.

The base mod's card objects carry no printed numbers (no GMNotes, Value 0, Description on 11 cards, tags are
name/Hero/set/team/class), so the numbers come from the BGG "Complete Card Text" exports in source-text/.

Usage (from the repo):  python build_card_values.py [--src ../source-text] [--aliases ../data/card_aliases.json] [--out ../data/card_values.json]

Output. Keys are normalised (lower case; "A // B" and "A/B" both become "a/b"):
  cards   card name -> entry
  hero    "hero|card" -> entry, only for names that different Heroes share with different numbers
          (the game looks the card's hero-name tag up here first)
  by_id   CardID (string) -> entry, for cards with no Nickname in the base mod (starting cards)
Entry:
  {"a": 2, "r": 0}            plain card ({} = no Attack or Recruit printed)
  {"a": 0, "ap": 1}           "0+ Attack": the printed number is a minimum (ap / rp = 1)
  {"div": [{...}, {...}]}     divided card: the player picks a half, so there is no single value
  {"x": 1, ...}               shared name, hero unknown: the smallest numbers, marked as minimums
"""
import argparse, json, os, re, time

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--src', default=os.path.join(HERE, '..', 'source-text'))
ap.add_argument('--aliases', default=os.path.join(HERE, '..', 'data', 'card_aliases.json'))
ap.add_argument('--out', default=os.path.join(HERE, '..', 'data', 'card_values.json'))
HEROES = 'Legendary Marvel Complete Card Text - Heroes And Allies.txt'
FILES = [HEROES, 'Legendary Marvel Complete Card Text.txt']
# sets the base mod (plus the Villains bag) contains, as the Heroes export names them; other sets' cards never reach the
# table, and leaving them out keeps reprints (Second Edition, Marvel Studios) from clashing with the cards in play
MOD_SETS = {'Legendary (First Edition)', 'Dark City', 'Fantastic Four', 'Paint the Town Red', 'Villains', 'Guardians of the Galaxy',
            'Secret Wars Volume 1', 'Secret Wars Volume 2', 'Captain America 75th Anniversary', 'Civil War', 'Deadpool', 'Noir', 'X-Men',
            'Champions', 'World War Hulk', 'Ant-Man', 'Venom', 'Dimensions', 'Revelations', 'S.H.I.E.L.D.', 'Heroes of Asgard',
            'New Mutants', 'Into the Cosmos', 'Realm of Kings'}

HEAD = re.compile(r'^(.+?) \((\d+) cop(?:y|ies)[^)]*\)$')
VAL = re.compile(r'^(\d+)(?: (\d)/(\d))?(\+)? (Attack|Recruit)$')


def norm(s):
    """Must match plNorm in played_lua.py."""
    return re.sub(r'\s*/+\s*', '/', s.replace('\u2019', "'")).strip().lower()


def values(lines):
    """Printed Attack / Recruit of one card face (the big numbers, not 'You get +1 Attack' rules text)."""
    e = {}
    for ln in lines:
        m = VAL.match(ln.strip())
        if not m: continue
        k = 'a' if m.group(5) == 'Attack' else 'r'
        if k in e: continue
        n = int(m.group(1)) + (int(m.group(2)) / int(m.group(3)) if m.group(2) else 0)
        e[k] = n
        if m.group(4): e[k + 'p'] = 1
    return e


def toc(text):
    """Set names from the export's Table of Contents (the indented lines under it)."""
    m = re.search(r'Table of Contents\n\n((?:[ \t]+\S.*\n)+)', text.replace('\r', ''))
    return [ln.strip() for ln in m.group(1).split('\n') if ln.strip()] if m else []


def parse(text, sets=None):
    """[(hero or '', card name, entry)]; a card may also appear under a second name (Maria Hill / S.H.I.E.L.D. Officer).
    With sets, only cards from those sets are kept (set headings are the export's Table of Contents names)."""
    out, hero, cur = [], '', None
    names_toc = set(toc(text)) if sets is not None else set()
    body_at = text.find('Complete Card Text Index') if sets is not None else -1
    for blk in re.split(r'\n\s*\n', text[max(body_at, 0):].replace('\r', '')):
        b = [ln.strip() for ln in blk.split('\n') if ln.strip()]
        if b and b[0] == 'Transformed': b = b[1:]
        if not b: continue
        if sets is not None:
            # a set heading is a line of its own, or the last line of the previous card's block (no blank line before it)
            nxt = b.pop() if b[-1] in names_toc else None
            keep = cur is None or cur in sets
            if nxt is not None: cur = nxt
            if not b or not keep: continue
        at = 0 if HEAD.match(b[0]) else (1 if len(b) > 1 and HEAD.match(b[1]) else None)
        if at is None:
            if len(b) > 1 and b[1].startswith('Microbadge') and 'Team' in b[1]: hero = b[0]
            continue
        names = [HEAD.match(b[at]).group(1).strip()] + (b[:1] if at == 1 else [])
        body = b[at + 1:]
        if body and body[0] == 'Divided':
            halves, half = [], []
            for ln in body[1:]:
                if ln == '---': halves.append(half); half = []
                else: half.append(ln)
            halves.append(half)
            e = {'div': [values(h) for h in halves[:2]]}
            if len(halves) != 2: raise SystemExit('divided card %r has %d halves' % (names[0], len(halves)))
        else:
            e = values(body)
        for n in names: out.append((hero, n, e))
    return out


def lower_bound(es):
    if any('div' in e for e in es): return {'x': 1, 'a': 0, 'ap': 1, 'r': 0, 'rp': 1}
    lo = {'x': 1}
    for v in ('a', 'r'):
        if any(v in e for e in es):
            lo[v] = min(e.get(v, 0) for e in es); lo[v + 'p'] = 1
    return lo


def build(entries):
    by_name = {}
    for hero, name, e in entries:
        by_name.setdefault(norm(name), []).append((hero, e))
    cards, heroed, clashes = {}, {}, []
    for k, rows in by_name.items():
        distinct = []
        for _, e in rows:
            if e not in distinct: distinct.append(e)
        if len(distinct) == 1:
            cards[k] = distinct[0]; continue
        clashes.append(k)
        cards[k] = lower_bound(distinct)
        per_hero = {}
        for hero, e in rows:
            if hero: per_hero.setdefault(norm(hero), []).append(e)
        for h, es in per_hero.items():
            same = [e for i, e in enumerate(es) if e not in es[:i]]
            heroed[h + '|' + k] = same[0] if len(same) == 1 else lower_bound(same)
    return cards, heroed, clashes


def main():
    a = ap.parse_args()
    t0 = time.time()
    entries = []
    for f in FILES:
        got = parse(open(os.path.join(a.src, f), encoding='utf-8').read(), MOD_SETS if f == HEROES else None)
        print('%-62s %4d cards' % (f, len(got)))
        entries += got
    cards, heroed, clashes = build(entries)
    al = json.load(open(a.aliases, encoding='utf-8')) if os.path.isfile(a.aliases) else {}
    missing, by_id = [], {}
    for name, e in al.get('extra', {}).items():
        cards[norm(name)] = e
    for nick, target in al.get('aliases', {}).items():
        if isinstance(target, dict): cards[norm(nick)] = target
        elif norm(target) in cards: cards[norm(nick)] = cards[norm(target)]
        else: missing.append('%s -> %s' % (nick, target))
    for cid, target in al.get('by_id', {}).items():
        if isinstance(target, dict): by_id[str(cid)] = target
        elif norm(target) in cards: by_id[str(cid)] = cards[norm(target)]
        else: missing.append('CardID %s -> %s' % (cid, target))
    if missing: raise SystemExit('ALIAS TARGETS NOT FOUND: ' + '; '.join(missing))
    out = {'cards': dict(sorted(cards.items())), 'hero': dict(sorted(heroed.items())), 'by_id': by_id}
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=0)
    plus = sum(1 for e in cards.values() if e.get('ap') or e.get('rp'))
    div = sum(1 for e in cards.values() if 'div' in e)
    print('names %d   printed minimum (X+) %d   divided %d   shared names %d (per-hero entries %d)   by CardID %d'
          % (len(cards), plus, div, len(clashes), len(heroed), len(by_id)))
    print('wrote %s (%.0f KB) in %.1fs' % (os.path.normpath(a.out), os.path.getsize(a.out) / 1024, time.time() - t0))


if __name__ == '__main__':
    main()
