"""Lists what is inside every bag/deck of the mod (names, types, tags, counts) for the menu and rules database.
Read-only. Writes TTS_work\\dump\\bag_contents.csv, special_decks.csv (every card of the Scheme/Sidekick/Ambition/Horror decks) and bag_summary.txt. Prints timestamped progress."""
import csv, json, os, sys, time

MOD = r'E:\Documents\My Games\Tabletop Simulator\Mods\Workshop\2410733963.json'
OUTD = r'E:\Media\Board Games\TTS_work\dump'
if len(sys.argv) > 1: MOD = sys.argv[1]
if len(sys.argv) > 2: OUTD = sys.argv[2]
T0 = time.time()


def log(m):
    print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


log('reading %s (%.0f MB)' % (MOD, os.path.getsize(MOD) / 1e6))
mod = json.load(open(MOD, encoding='utf-8'))
tops = mod['ObjectStates']
log('%d top-level objects' % len(tops))
os.makedirs(OUTD, exist_ok=True)
rows, special = [], []
SPECIAL_TAGS = ('Scheme', 'Sidekick', 'Ambition', 'Horror')
DECKS = ('Deck', 'DeckCustom')


def label(o): return o.get('Nickname') or o.get('Name') or ''


def walk(o, top, path, depth):
    for c in (o.get('ContainedObjects') or []):
        kids = c.get('ContainedObjects') or []
        typ = c.get('Name', '')
        first = kids[0] if (typ in DECKS and kids) else None
        rows.append([top.get('GUID'), label(top), depth, path, typ, label(c), c.get('GUID', ''),
                     ','.join(c.get('Tags') or []), len(kids),
                     label(first) if first else '', ','.join(first.get('Tags') or []) if first else '',
                     (c.get('LuaScript') or '')[:0] and 'lua' or ''])
        if typ in DECKS and any(t in SPECIAL_TAGS for t in (c.get('Tags') or [])):
            for k in kids:
                special.append([top.get('GUID'), label(top), path, label(c), ','.join(c.get('Tags') or []), label(k), ','.join(k.get('Tags') or [])])
        if kids and typ not in DECKS and typ != 'Card' and not typ.startswith('Card'):
            walk(c, top, path + ' > ' + label(c), depth + 1)


n_containers = 0
for i, t in enumerate(tops, 1):
    if t.get('ContainedObjects'):
        n_containers += 1
        before = len(rows)
        walk(t, t, label(t), 1)
        log('[%d/%d] %s (%s): %d contained entries' % (i, len(tops), label(t), t.get('Name'), len(rows) - before))
    if t.get('Name') in DECKS and any(x in SPECIAL_TAGS for x in (t.get('Tags') or [])):
        for k in (t.get('ContainedObjects') or []):
            special.append([t.get('GUID'), label(t), '(top level)', label(t), ','.join(t.get('Tags') or []), label(k), ','.join(k.get('Tags') or [])])

with open(os.path.join(OUTD, 'bag_contents.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['top_guid', 'top_name', 'depth', 'path', 'type', 'name', 'guid', 'tags', 'n_children', 'first_child', 'first_child_tags', 'lua'])
    w.writerows(rows)

with open(os.path.join(OUTD, 'special_decks.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['top_guid', 'top_name', 'path', 'deck', 'deck_tags', 'card', 'card_tags'])
    w.writerows(special)
log('%d cards listed from Scheme/Sidekick/Ambition/Horror decks' % len(special))

# summary: per container, how many entries of each type, and the tag vocabulary
from collections import Counter, defaultdict
tagcount = Counter(); by_top = defaultdict(Counter)
for r in rows:
    by_top[r[1]][r[4]] += 1
    for t in (r[7].split(',') if r[7] else []): tagcount[t] += 1
with open(os.path.join(OUTD, 'bag_summary.txt'), 'w', encoding='utf-8') as f:
    f.write('containers: %d, contained entries: %d\n\n' % (n_containers, len(rows)))
    for top, c in by_top.items(): f.write('%-40s %s\n' % (top, dict(c)))
    f.write('\nTAGS on contained entries (count):\n')
    for t, n in tagcount.most_common(): f.write('  %-40s %d\n' % (t, n))
    f.write('\nSAMPLE: first 40 rows of the first bag with decks\n')
    for r in rows[:40]: f.write('  ' + ' | '.join(str(x) for x in r[:11]) + '\n')
log('DONE: %d containers, %d entries -> %s' % (n_containers, len(rows), os.path.join(OUTD, 'bag_contents.csv')))