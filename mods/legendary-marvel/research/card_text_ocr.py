"""OCRs the scheme and mastermind cards of the library so their setup / Always Leads text can be audited.
Usage: python card_text_ocr.py            (writes TTS_work\\card_text_ocr.csv, prints timestamped progress and an ETA)"""
import csv, difflib, os, re, sys, time
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

SRC = r'E:\Media\Board Games\Marvel Legendary Cards'
OUT = r'E:\Media\Board Games\TTS_work\card_text_ocr.csv'
if len(sys.argv) > 1: SRC = sys.argv[1]
if len(sys.argv) > 2: OUT = sys.argv[2]
SCHEMES = [["Midtown Bank Robbery", "Core"], ["Negative Zone Prison Breakout", "Core"], ["Portals To The Dark Dimension", "Core"], ["Replace Earth's Leaders With Killbots", "Core"], ["Secret Invasion Of The Skrull Shapeshifters", "Core"], ["Super Hero Civil War", "Core"], ["The Legacy Virus", "Core"], ["Unleash The Power Of The Cosmic Cube", "Core"], ["Save Humanity", "Dark City"], ["Organized Crime Wave", "Dark City"], ["Massive Earthquake Generator", "Dark City"], ["X-Cutioner's Song", "Dark City"], ["Steal The Weaponized Plutonium", "Dark City"], ["Capture Baby Hope", "Dark City"], ["Transform Citizens Into Demons", "Dark City"], ["Detonate The Helicarrier", "Dark City"], ["Bathe Earth In Cosmic Rays", "Fantastic Four"], ["Invincible Force Field", "Fantastic Four"], ["Pull Reality Into The Negative Zone", "Fantastic Four"], ["Flood The Planet With Melted Glaciers", "Fantastic Four"], ["Weave A Web Of Lies", "Paint The Town Red"], ["Splice Humans With Spider DNA", "Paint The Town Red"], ["The Clone Saga", "Paint The Town Red"], ["Invade The Daily Bugle News HQ", "Paint The Town Red"], ["The Kree-Skrull War", "Guardians Of The Galaxy"], ["Forge The Infinity Gauntlet", "Guardians Of The Galaxy"], ["Unite The Shards", "Guardians Of The Galaxy"], ["Intergalactic Kree Nega-Bomb", "Guardians Of The Galaxy"], ["Master Of Tyrants", "Secret Wars, Volume 1"], ["Fragmented Realities", "Secret Wars, Volume 1"], ["Corrupt The Next Generation Of Heroes", "Secret Wars, Volume 1"], ["Smash Two Dimensions Together", "Secret Wars, Volume 1"], ["Build An Army Of Annihilation", "Secret Wars, Volume 1"], ["Dark Alliance", "Secret Wars, Volume 1"], ["Pan-Dimensional Plague", "Secret Wars, Volume 1"], ["Crush Them With My Bare Hands", "Secret Wars, Volume 1"], ["Sinister Ambitions", "Secret Wars, Volume 2"], ["The Mark Of Khonshu", "Secret Wars, Volume 2"], ["Deadlands Hordes Charge The Wall", "Secret Wars, Volume 2"], ["Enthrone The Barons Of Battleworld", "Secret Wars, Volume 2"], ["The Fountain Of Eternal Life", "Secret Wars, Volume 2"], ["Master The Mysteries Of Kung-Fu", "Secret Wars, Volume 2"], ["Secret Wars", "Secret Wars, Volume 2"], ["The God-Emperor Of Battleworld", "Secret Wars, Volume 2"], ["Deadpool Kills The Marvel Universe", "Deadpool"], ["Deadpool Wants A Chimichanga", "Deadpool"], ["Deadpool Writes A Scheme", "Deadpool"], ["Everybody Hates Deadpool", "Deadpool"], ["The Unbreakable Enigma Code", "Captain America 75th"], ["Go Back In Time To Slay Heroes' Ancestors", "Captain America 75th"], ["Change The Outcome Of WWII", "Captain America 75th"], ["Brainwash The Military", "Captain America 75th"], ["Imprison Unregistered Superhumans", "Civil War"], ["Reveal Heroes' Secret Identities", "Civil War"], ["Predict Future Crime", "Civil War"], ["Nitro The Supervillain Threatens Crowds", "Civil War"], ["United States Split By Civil War", "Civil War"], ["Epic Super Hero Civil War", "Civil War"], ["Dark Reign Of H.A.M.M.E.R. Officers", "Civil War"], ["Avengers VS. X-Men", "Civil War"], ["Silence The Witnesses", "Noir"], ["Find The Split Personality Killer", "Noir"], ["Five Families Of Crime", "Noir"], ["Hidden Heart Of Darkness", "Noir"], ["X-Men Danger Room Goes Beserk", "X-Men"], ["The Dark Phoenix Saga", "X-Men"], ["Mutant-Hunting Super Sentinels", "X-Men"], ["Nuclear Armageddon", "X-Men"], ["Horror Of Horrors", "X-Men"], ["Alien Brood Encounters", "X-Men"], ["Televised Deathtraps Of Mojoworld", "X-Men"], ["Anti-Mutant Hatred", "X-Men"], ["Steal All Oxygen On Earth", "Champions"], ["Hypnotize Every Human", "Champions"], ["Divide And Conquer", "Champions"], ["Clash Of The Monsters Unleashed", "Champions"], ["Gladiator Pits Of Sakaar", "World War Hulk"], ["Break The Planet Asunder", "World War Hulk"], ["Subjugate With Obedience Disks", "World War Hulk"], ["Shoot Hulk Into Space", "World War Hulk"], ["Fall Of The Hulks", "World War Hulk"], ["Mutating Gamma Rays", "World War Hulk"], ["Cytoplasm Spike Invasion", "World War Hulk"], ["World War Hulk", "World War Hulk"], ["Age Of Ultron", "Ant-Man"], ["Pull Earth Into Medieval Times", "Ant-Man"], ["Transform Commuters Into Giant Ants", "Ant-Man"], ["Trap Heroes In The Microverse", "Ant-Man"], ["Invasion Of The Venom Symbiotes", "Venom"], ["Maximum Carnage", "Venom"], ["Paralyzing Venom", "Venom"], ["Symbiotic Absorption", "Venom"], ["Secret Hydra Corruption", "Revelations"], ["The Korvac Saga", "Revelations"], ["Earthquake Drains The Ocean", "Revelations"], ["House Of M", "Revelations"], ["Hail Hydra", "S.H.I.E.L.D."], ["Hydra Helicarriers Hunt Heroes", "S.H.I.E.L.D."], ["SHIELD vs Hydra War", "S.H.I.E.L.D."], ["Secret Empire Of Betrayal", "S.H.I.E.L.D."], ["War Of The Frost Giants", "Heroes Of Asgard"], ["The Dark World Of Svartalfheim", "Heroes Of Asgard"], ["Ragnarok, Twilight Of The Gods", "Heroes Of Asgard"], ["Asgardian Test Of Worth", "Heroes Of Asgard"], ["Crash The Moon Into The Sun", "The New Mutants"], ["Trapped In The Insane Asylum", "The New Mutants"], ["Superhuman Baseball Game", "The New Mutants"], ["The Demon Bear Saga", "The New Mutants"], ["Annihilation: Conquest", "Into The Cosmos"], ["The Contest Of Champions", "Into The Cosmos"], ["Destroy The Nova Corps", "Into The Cosmos"], ["Turn The Soul Of Adam Warlock", "Into The Cosmos"], ["Devolve with Xerogen Crystals", "Realm of Kings"], ["Ruin the Perfect Wedding", "Realm of Kings"], ["Tornado of Terrigen Mists", "Realm of Kings"], ["War of Kings", "Realm of Kings"]]
MASTERMINDS = [["Loki", "Core"], ["Red Skull", "Core"], ["Magneto", "Core"], ["Dr Doom", "Core"], ["Mr Sinister", "Dark City"], ["Kingpin", "Dark City"], ["Stryfe", "Dark City"], ["Mephisto", "Dark City"], ["Apocalypse", "Dark City"], ["Mole Man", "Fantastic Four"], ["Galactus", "Fantastic Four"], ["Carnage", "Paint The Town Red"], ["Mysterio", "Paint The Town Red"], ["Thanos", "Guardians Of The Galaxy"], ["Supreme Intelligence Of The Kree", "Guardians Of The Galaxy"], ["Madelyne Pryor Goblin Queen", "Secret Wars Volume 1"], ["Nimrod Super Sentinel", "Secret Wars Volume 1"], ["Wasteland Hulk", "Secret Wars Volume 1"], ["Zombie Green Goblin", "Secret Wars Volume 1"], ["Immortal Emperor Zheng Zhu", "Secret Wars Volume 2"], ["King Hyperion", "Secret Wars Volume 2"], ["Shiklah The Demon Bride", "Secret Wars Volume 2"], ["Spider Queen", "Secret Wars Volume 2"], ["Arnim Zola", "Captain America 75th Anniversary"], ["Baron Heinrich Zemo", "Captain America 75th Anniversary"], ["Evil Deadpool", "Deadpool"], ["Macho Gomez", "Deadpool"], ["Authoritarian Iron Man", "Civil War"], ["Baron Helmut Zemo", "Civil War"], ["Maria Hill Director Of SHIELD", "Civil War"], ["Misty Knight", "Civil War"], ["Ragnarok", "Civil War"], ["Charles Xavier Professor Of Crime", "Noir"], ["The Goblin Underworld Boss", "Noir"], ["Arcade", "X-Men"], ["Dark Phoenix", "X-Men"], ["Deathbird", "X-Men"], ["Mojo", "X-Men"], ["Onslaught", "X-Men"], ["Shadow King", "X-Men"], ["Fin Fang Foom", "Champions"], ["Pagliacci", "Champions"], ["General Thunderbolt Ross", "World War Hulk"], ["Illuminati Secret Society", "World War Hulk"], ["King Hulk Sakaarson", "World War Hulk"], ["MODOK", "World War Hulk"], ["The Sentry", "World War Hulk"], ["The Red King", "World War Hulk"], ["Morgan Le Fay", "Ant-Man"], ["Ultron", "Ant-Man"], ["Hybrid", "Venom"], ["Poison Thanos", "Venom"], ["J Jonah Jameson", "Dimensions"], ["Grim Reaper", "Revelations"], ["Mandarin", "Revelations"], ["The Hood", "Revelations"], ["Hydra High Council", "SHIELD"], ["Hydra Super Adaptoid", "SHIELD"], ["Hela Goddess Of Death", "Heroes Of Asgard"], ["Malekith The Accursed", "Heroes Of Asgard"], ["Belasco Demon Lord Of Limbo", "The New Mutants"], ["Emma Frost The White Queen", "The New Mutants"], ["The Beyonder", "Into The Cosmos"], ["The Grandmaster", "Into The Cosmos"], ["Magus", "Into The Cosmos"], ["Emperor Vulcan of the Shiar", "Realm of Kings"], ["Maximus the Mad", "Realm of Kings"]]
T0 = time.time()


def log(m):
    print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


def toks(s): return re.findall(r'[a-z0-9]+', s.lower())
def key(s): return frozenset(t for t in toks(s) if t not in ('the', 'core', 'copy'))
def norm(s): return re.sub(r'[^a-z0-9]', '', s.lower())


log('indexing the library under %s' % SRC)
lib = []
for top in ('Base Sets', 'Expansions'):
    for r, _, fs in os.walk(os.path.join(SRC, top)):
        for f in fs:
            if f.lower().endswith('.png'):
                lib.append((os.path.join(r, f), os.path.splitext(f)[0]))
log('   %d card files' % len(lib))
by_key = {}
for p, stem in lib:
    by_key.setdefault(key(stem), []).append((p, stem))


def find(name):
    c = by_key.get(key(name), [])
    c = [x for x in c if 'copy' not in x[1].lower()] or c
    if c:
        good = []
        for p, stem in c:
            try:
                with Image.open(p) as im:
                    if im.size[0] <= im.size[1]: good.append(p)
            except Exception: pass
        if good: return sorted(good, key=len)[0], 'exact'
    best, second, bp = 0, 0, None
    for p, stem in lib:
        s = difflib.SequenceMatcher(None, norm(name), norm(' '.join(t for t in toks(stem) if t not in ('the', 'core', 'copy')))).ratio()
        if s > best: best, second, bp = s, best, p
        elif s > second: second = s
    if bp and best >= 0.93 and best - second >= 0.03: return bp, 'fuzzy %.2f' % best
    return None, 'not found'


def order(items, width):
    items = sorted(items, key=lambda b: (b[1] + b[3]) / 2)
    lines, cur, cy = [], [], None
    for b in items:
        c = (b[1] + b[3]) / 2; h = b[3] - b[1]
        if cur and abs(c - cy) <= 0.6 * h: cur.append(b)
        else:
            if cur: lines.append(cur)
            cur, cy = [b], c
    if cur: lines.append(cur)
    return [' '.join(x[4] for x in sorted(l, key=lambda b: b[0])) for l in lines]


targets = [('scheme', n, e) for n, e in SCHEMES] + [('mastermind', n, e) for n, e in MASTERMINDS]
log('%d cards to read (%d schemes, %d masterminds)' % (len(targets), len(SCHEMES), len(MASTERMINDS)))
ocr = RapidOCR()
rows, missing, tstart = [], [], time.time()
for i, (kind, name, exp) in enumerate(targets, 1):
    path, how = find(name)
    if not path:
        missing.append((kind, name)); log('[%d/%d] %s %r: NO FILE FOUND' % (i, len(targets), kind, name)); continue
    t1 = time.time()
    im = Image.open(path).convert('RGB')
    s = min(1.0, 1990 / max(im.size))      # the OCR engine downscales above ~2000 px and then misses lines
    if s < 1: im = im.resize((int(im.size[0] * s), int(im.size[1] * s)), Image.LANCZOS)
    res, _ = ocr(np.array(im))
    items = [(min(p[0] for p in b), min(p[1] for p in b), max(p[0] for p in b), max(p[1] for p in b), t) for b, t, sc in (res or [])]
    text = ' | '.join(order(items, im.size[0]))
    rows.append([kind, name, exp, os.path.relpath(path, SRC), how, text])
    eta = (time.time() - tstart) / i * (len(targets) - i)
    log('[%d/%d] %s %r (%s): %d boxes, %.1fs, ETA %d min' % (i, len(targets), kind, name, how, len(items), time.time() - t1, eta / 60))
os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
with open(OUT, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['kind', 'name', 'set', 'file', 'match', 'text']); w.writerows(rows)
log('DONE: %d cards read, %d files not found -> %s' % (len(rows), len(missing), OUT))
for k, n in missing: log('   not found: %s %r' % (k, n))