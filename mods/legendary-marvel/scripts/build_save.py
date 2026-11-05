"""Builds the frozen 'Legendary Universal' TTS save from the Workshop mod JSON.

 - every image URL that has a rebuilt file in TTS_work\\new becomes a file:/// URL in ASSETS\\img
 - main board gets the Universal Mat transform, boards/zone updated, Lua patched (lua_patch.py)
 - writes into an existing save slot whose in-file SaveName matches --name (create it once in game)
Never modifies the Workshop JSON. Prints timestamped progress; long steps print a heartbeat every 10 s.

Base-mod pinning: every Lua patch is an exact-text match against the Workshop mod, so the build hashes the mod
(SHA-256) and compares it with the recorded baseline in base_mod_sha256.txt. A difference is always reported;
--strict stops the build on it (or when no baseline is recorded). --record-base writes the current hash as the
baseline (next to this script); copy it to the repo's data/ to version it."""
import argparse, glob, hashlib, json, os, re, shutil, sys, threading, time
import lua_patch as P
import mat_config as C

ap = argparse.ArgumentParser()
ap.add_argument('--mod', default=r'E:\Documents\My Games\Tabletop Simulator\Mods\Workshop\2410733963.json')
ap.add_argument('--saves', default=r'E:\Documents\My Games\Tabletop Simulator\Saves')
ap.add_argument('--work', default=r'E:\Media\Board Games\TTS_work')
ap.add_argument('--assets', default=r'E:\Legendary_TTS_Assets')
ap.add_argument('--name', default='Legendary Universal')
ap.add_argument('--dry', action='store_true', help='report only, write nothing')
ap.add_argument('--calibrate', action='store_true', help='draw the calibration overlay in game (see cal_lua.py); rebuild without it for the normal save')
ap.add_argument('--strict', action='store_true', help='stop if the Workshop mod differs from the recorded baseline hash (or none is recorded)')
ap.add_argument('--record-base', action='store_true', help='record the Workshop mod\'s current hash as the baseline (base_mod_sha256.txt next to this script)')
a = ap.parse_args()
if a.calibrate: os.environ['LEGENDARY_CAL'] = '1'
HERE = os.path.dirname(os.path.abspath(__file__))
BASE_SHA_CANDIDATES = [os.environ.get('LEGENDARY_BASE_SHA', ''), os.path.join(a.work, 'base_mod_sha256.txt'),
                       os.path.join(HERE, 'base_mod_sha256.txt'), 'base_mod_sha256.txt',
                       os.path.join(HERE, '..', 'data', 'base_mod_sha256.txt')]

MAIN_BOARD, ZONE_BOARD = '083da5', 'a63bcd'
MOVES = C.MOVES
IMG = os.path.join(a.assets, 'img')
T0 = time.time()


def log(msg):
    print('[%s +%4ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, msg), flush=True)


class Heartbeat:
    """prints 'still <label>' every 10 s while a long single step runs"""
    def __init__(self, label, probe=None):
        self.label, self.probe, self.stop = label, probe, threading.Event()
    def __enter__(self):
        self.t0 = time.time()
        threading.Thread(target=self._run, daemon=True).start()
        return self
    def _run(self):
        while not self.stop.wait(10):
            extra = ''
            try:
                extra = ' ' + self.probe() if self.probe else ''
            except Exception:
                pass
            log('   ... still %s (%ds)%s' % (self.label, time.time() - self.t0, extra))
    def __exit__(self, *e):
        self.stop.set()


def canon(u):
    return re.sub(r'^https?://cloud-\d+\.steamusercontent\.com', 'https://steamusercontent-a.akamaihd.net', u)


def key(u):
    return re.sub(r'[^A-Za-z0-9]', '', canon(u))


# ---- rebuilt files ----------------------------------------------------------------------
log('phase 1/6: listing rebuilt files in %s' % a.work)
src_new = os.path.join(a.work, 'new')
files = {}
for f in os.listdir(src_new):
    stem, ext = os.path.splitext(f)
    files[stem] = f
log('   %d rebuilt files available' % len(files))

log('phase 2/6: reading the mod JSON (%s, %.0f MB)' % (a.mod, os.path.getsize(a.mod) / 1e6))
with Heartbeat('reading the mod JSON'):
    mod = json.load(open(a.mod, encoding='utf-8'))
log('   %d top-level objects' % len(mod['ObjectStates']))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def base_check():
    """(line for the report, ok). ok is False when the hash differs from the baseline or no baseline is recorded."""
    cur = sha256_file(a.mod)
    if a.record_base:
        dst = os.path.join(HERE, 'base_mod_sha256.txt')
        with open(dst, 'w', encoding='ascii') as f: f.write(cur + '\n')
        return 'base mod sha256 %s: RECORDED as the baseline in %s (copy it to the repo\'s data/ to version it)' % (cur, dst), True
    path = next((p for p in BASE_SHA_CANDIDATES if p and os.path.isfile(p)), None)
    if path is None:
        return 'base mod sha256 %s: NO BASELINE recorded (run with --record-base once the build is known good)' % cur, False
    want = open(path, encoding='ascii').read().split()[0].lower()
    if want == cur:
        return 'base mod sha256 %s: matches the baseline in %s' % (cur, path), True
    return ('base mod sha256 %s: DIFFERS from the baseline %s in %s. The Workshop mod changed: read the Lua patch report '
            'below; if every patch applied and the game plays, run --record-base to accept it' % (cur, want, path)), False


with Heartbeat('hashing the mod JSON'):
    base_line, base_ok = base_check()
log('   ' + base_line)
if a.strict and not base_ok:
    sys.exit('--strict: stopping because the Workshop mod does not match the recorded baseline (see the line above).')

stats = {'url': 0, 'kept': 0, 'bag_lua': 0}
used = set()
URLKEYS = ('FaceURL', 'BackURL', 'ImageURL', 'ImageSecondaryURL')
bag_counts = {}


def to_file_url(name):
    return 'file:///' + os.path.join(IMG, name).replace('\\', '/')


def walk(o):
    if isinstance(o, dict):
        for k, v in list(o.items()):
            if k in URLKEYS and isinstance(v, str) and v.startswith('http'):
                kk = key(v)
                if kk in files:
                    o[k] = to_file_url(files[kk]); used.add(kk); stats['url'] += 1
                else:
                    stats['kept'] += 1
            elif k == 'LuaScript' and isinstance(v, str) and v and o is not mod:
                new, counts = P.patch_bag(v)
                if new != v:
                    o[k] = new; stats['bag_lua'] += 1
                    for lit, n in counts.items(): bag_counts[lit] = bag_counts.get(lit, 0) + n
            else:
                walk(v)
    elif isinstance(o, list):
        for x in o: walk(x)


# ---- Villains expansion bag (made by build_villains_set.py) -------------------------------------------------------
VB = os.path.join(a.work, 'villains_set', 'villains_bag.json')
if os.path.exists(VB):
    vbag = json.load(open(VB, encoding='utf-8'))
    mod['ObjectStates'] = [o for o in mod['ObjectStates'] if o.get('GUID') != vbag['GUID']] + [vbag]
    log('   Villains expansion bag %s added (%d nested objects); it shows up in the Expansions list' % (vbag['GUID'], len(vbag['ContainedObjects'])))
else:
    log('   no Villains expansion bag (%s): run build_villains_set.py to add the Villains set' % VB)

log('phase 3/6: patching Lua, rewriting image URLs, placing board/zone/decks')
SKIN_DIR = os.path.join(a.work, 'skins')
skin_files = sorted(glob.glob(os.path.join(SKIN_DIR, 'mat_skin_*.jpg')), key=lambda p: int(re.search(r'_(\d+)\.jpg', p).group(1)))
C.SKIN_URLS = ['file:///' + os.path.join(IMG, os.path.basename(p)).replace('\\', '/') for p in skin_files]
if skin_files: log('   %d mat skins found in %s (skin %d is the default)' % (len(skin_files), SKIN_DIR, C.MAT_SKIN))
else: log('   no mat skins in %s: run make_mat_skins.py to use the 28_Inch mats (the old mat image stays)' % SKIN_DIR)
new_lua, report = P.patch_global(mod['LuaScript'])
mod['LuaScript'] = new_lua
with Heartbeat('rewriting image URLs'):
    walk(mod)

tops = {o.get('GUID'): o for o in mod['ObjectStates']}
if C.SKIN_URLS:
    _bi = tops[MAIN_BOARD].setdefault('CustomImage', {})
    _bi['ImageURL'] = C.SKIN_URLS[min(max(C.MAT_SKIN, 1), len(C.SKIN_URLS)) - 1]
    _bi.pop('ImageSecondaryURL', None)
board, zone = tops[MAIN_BOARD], tops[ZONE_BOARD]
s = C.MAT_REF_SCALE * C.BOUNDS_W / C.MAT_REF_WIDTH   # calibrated from the width measured in game (see mat_config.py)
t = board['Transform']
t.update(posX=P.CX, posZ=P.CZ, rotY=180, scaleX=s, scaleY=s, scaleZ=s)
zt = zone['Transform']
zt.update(**C.ZONE)
moved = []
for g, slot_name in MOVES.items():
    if g in tops:
        x, z = P.S(slot_name)
        tops[g]['Transform'].update(posX=x, posZ=z)
        moved.append('%s %r -> %s slot (%.2f, %.2f)' % (g, tops[g].get('Nickname'), slot_name, x, z))
    else:
        log('WARNING: deck %s not found, not moved' % g)

# ---- player mats: official Player Mat image, starting decks onto the Draw Deck slot ------------------------------
def versioned(path, stem):
    """stem_<hash of the file>.png: TTS caches images by URL, so a changed file under the same name would show the old art."""
    return '%s_%s.png' % (stem, hashlib.md5(open(path, 'rb').read()).hexdigest()[:8])


PM_PNG = os.path.join(a.work, 'playermat.png')
PM_NAME = versioned(PM_PNG, 'playermat') if os.path.exists(PM_PNG) else 'playermat.png'
pm_report = []
if os.path.exists(PM_PNG):
    import math
    from PIL import Image
    with Image.open(PM_PNG) as _im: pm_aspect = _im.size[0] / _im.size[1]
    pm_url = 'file:///' + os.path.join(IMG, PM_NAME).replace(chr(92), '/')
    # the two side mats were 2.7 units off each other (z 8.6 and 5.9): put both at the same height, and move each one's cleanup trigger with it
    SIDE_Z = 7.25
    for mg, zg in (('17be32', 'a6fa1d'), ('9d07a8', '619189')):
        mo, zo = tops.get(mg), tops.get(zg)
        if mo is None: continue
        dz = SIDE_Z - mo['Transform']['posZ']
        mo['Transform']['posZ'] = SIDE_Z
        if zo is not None: zo['Transform']['posZ'] = round(zo['Transform']['posZ'] + dz, 2)
        pm_report.append('side mat %s moved %.2f in z to %.2f (its trigger %s with it)' % (mg, dz, SIDE_Z, zg))
    mats = []
    for g in C.PLAYER_MATS:
        o = tops.get(g)
        if o is None: log('WARNING: player mat %s not found' % g); continue
        o.setdefault('CustomImage', {})['ImageURL'] = pm_url
        o['CustomImage'].pop('ImageSecondaryURL', None)
        tr = o['Transform']
        sc = tr['scaleX']
        pw = C.PM_BOARD_H * sc * pm_aspect * C.PM_PRINTED_FRAC
        ph = C.PM_BOARD_H * sc * C.PM_PRINTED_FRAC
        mats.append((g, tr, pw, ph))
        pm_report.append('%s -> player mat image (scale %.2f, printed %.1f x %.1f)' % (g, sc, pw, ph))
    for dg in C.PM_STARTER_DECKS:
        d = tops.get(dg)
        if d is None: continue
        dt = d['Transform']
        best = min(mats, key=lambda m: (m[1]['posX'] - dt['posX']) ** 2 + (m[1]['posZ'] - dt['posZ']) ** 2) if mats else None
        if best is None: continue
        g, tr, pw, ph = best
        lx, lz = (C.PM_DRAW_UV[0] - .5) * pw, -(C.PM_DRAW_UV[1] - .5) * ph
        th = math.radians(tr['rotY'] - 180)
        dt['posX'] = round(tr['posX'] + lx * math.cos(th) + lz * math.sin(th), 2)
        dt['posZ'] = round(tr['posZ'] - lx * math.sin(th) + lz * math.cos(th), 2)
        pm_report.append('starting deck %s -> Draw Deck slot of mat %s (%.2f, %.2f)' % (dg, g, dt['posX'], dt['posZ']))
        # the starting cards have no Nickname in the base mod; naming them lets the Played count read them inside a stacked deck
        named = 0
        for c in d.get('ContainedObjects', []) or []:
            nm = {3: 'S.H.I.E.L.D. Agent', 5: 'S.H.I.E.L.D. Trooper'}.get(c.get('CardID', -1) % 100)
            if nm and not c.get('Nickname'): c['Nickname'] = nm; named += 1
        pm_report.append('starting deck %s: %d cards named' % (dg, named))

    # The three counter pads of each seat (Attack, Recruit, Shards) are chained together with fixed joints. Moving one without the others
    # makes the joints yank them around, so each trio is released and every pad goes onto its own box on the nearest mat.
    import turn_lua as _T
    def mat_xz(tr, pw, ph, uv):
        lx, lz = (uv[0] - .5) * pw, -(uv[1] - .5) * ph
        th = math.radians(tr['rotY'] - 180)
        return round(tr['posX'] + lx * math.cos(th) + lz * math.sin(th), 2), round(tr['posZ'] - lx * math.sin(th) + lz * math.cos(th), 2)
    def joined(g): return ((tops.get(g) or {}).get('JointFixed') or {}).get('ConnectedBodyGUID')
    for ag in _T.ATTACK_COUNTERS:
        at = tops.get(ag)
        if at is None or not mats: pm_report.append('WARNING: Attack counter %s not found' % ag); continue
        rg = next((r for r in _T.RECRUIT_COUNTERS if joined(r) == ag), None)
        sg = joined(ag)
        ref = at['Transform']
        g, tr, pw, ph = min(mats, key=lambda m: (m[1]['posX'] - ref['posX']) ** 2 + (m[1]['posZ'] - ref['posZ']) ** 2)
        for guid, uv, nm in ((ag, C.PM_ATTACK_UV, 'Attack'), (rg, C.PM_RECRUIT_UV, 'Recruit'), (sg, C.PM_SHARDS_UV, 'Shards')):
            co = tops.get(guid) if guid else None
            if co is None: pm_report.append('WARNING: %s counter for seat %s not found' % (nm, ag)); continue
            co.pop('JointFixed', None)
            co['Locked'] = False
            ct = co['Transform']
            ct['posX'], ct['posZ'] = mat_xz(tr, pw, ph, uv)
            ct['rotY'] = (tr['rotY'] + 180) % 360        # a pad faces its seat when it is turned half a turn from the mat
            ct['posY'] = round(tr['posY'] + 1.2, 2)       # centre was inside the mat slab (0.93 vs 0.98): spawn above it and let it settle
            ct['rotX'] = ct['rotZ'] = 0
            ct['scaleX'] = ct['scaleY'] = ct['scaleZ'] = 0.85   # at full size a pad covers 90 % of its box and hides the label
            pm_report.append('%s counter %s -> its box on mat %s (%.2f, %.2f)' % (nm, guid, g, ct['posX'], ct['posZ']))
    # Five seats, one hand zone beside each mat on the player's side. The base mod has 8 zones round the table, only some of them near a mat.
    SEATS = {'51edf5': '182660', '6212f9': '5bde5d', '446b40': '248022', '17be32': 'fbc0d5', '9d07a8': 'd02301'}   # mat -> hand zone (Red, Green, White, Yellow, Purple)
    for mg, hg in SEATS.items():
        m = next((m for m in mats if m[0] == mg), None); hz = tops.get(hg)
        if m is None or hz is None: pm_report.append('WARNING: seat for mat %s not built' % mg); continue
        _, tr, pw, ph = m
        ht = hz['Transform']
        rot = round(tr['rotY']) % 360
        if rot == 180:   ht['posX'], ht['posZ'], ht['rotY'] = tr['posX'], round(tr['posZ'] - ph / 2 - 0.5 - 9.2 / 2, 2), 0
        elif rot == 270: ht['posX'], ht['posZ'], ht['rotY'] = round(tr['posX'] - ph / 2 - 0.5 - 9.2 / 2, 2), tr['posZ'], 90
        else:            ht['posX'], ht['posZ'], ht['rotY'] = round(tr['posX'] + ph / 2 + 0.5 + 9.2 / 2, 2), tr['posZ'], 270
        pm_report.append('seat %s: hand zone %s -> (%.2f, %.2f) rot %d' % (hz.get('FogColor'), hg, ht['posX'], ht['posZ'], ht['rotY']))
    drop = {'86a578', '3b9aeb', 'e5f681'}      # Orange, Pink, Blue
    before = len(mod['ObjectStates'])
    mod['ObjectStates'][:] = [o for o in mod['ObjectStates'] if o.get('GUID') not in drop]
    pm_report.append('hand zones removed: %d (Orange, Pink, Blue)' % (before - len(mod['ObjectStates'])))
else:
    log('no playermat.png in %s, player mats keep their old image (run make_player_mat.py to use the official one)' % a.work)

x0, x1, z0, z1 = P.CX - P.W / 2 - 1.2, P.CX + P.W / 2 + 1.2, P.CZ - P.H / 2 - 1.2, P.CZ + P.H / 2 + 1.2
hits = []
for g, o in tops.items():
    if g in (MAIN_BOARD, ZONE_BOARD) or o.get('Name') in ('ScriptingTrigger', 'HandTrigger', 'Custom_Board'): continue
    tr = o['Transform']
    if x0 <= tr['posX'] <= x1 and z0 <= tr['posZ'] <= z1 and tr['posY'] < 3.0 and g not in MOVES:
        hits.append('%s %r %s at (%.2f, %.2f)' % (g, o.get('Nickname'), o.get('Name'), tr['posX'], tr['posZ']))

print(P.describe())
print('\n' + base_line)
print('\nLua patches (global):')
for line in report: print('  ', line)
print('bag scripts patched: %d  literal counts: %s' % (stats['bag_lua'], bag_counts))
print('mat skins: %d (default %d)' % (len(skin_files), C.MAT_SKIN))
print('main board scale set to %.4f for an object width of %.1f (load message should say OK)' % (s, C.BOUNDS_W))
print('image URLs rewritten: %d   left on their original URL: %d   rebuilt files actually referenced: %d of %d'
      % (stats['url'], stats['kept'], len(used), len(files)))
unused = sorted(set(files) - used)
if unused: print('rebuilt files NOT referenced by the mod JSON:', [files[k][-34:] for k in unused[:10]])
print('player mats:')
for m in pm_report: print('   ', m)
print('decks moved onto their new slots:')
for m in moved: print('   ', m)
print('other objects overlapping the new mat footprint (%d):' % len(hits))
for h in hits: print('   ', h)
sys.stdout.flush()

if a.dry:
    log('--dry: nothing written'); sys.exit(0)

# ---- table: a flat custom table instead of the wooden RPG table, and the expansion bags in tidy rows -------------------------
TABLE_PNG = os.path.join(a.work, 'table.png')
TABLE_NAME = versioned(TABLE_PNG, 'table') if os.path.exists(TABLE_PNG) else 'table.png'
if os.path.exists(TABLE_PNG):
    mod['Table'] = 'Table_Custom'
    mod['TableURL'] = 'file:///' + os.path.join(IMG, TABLE_NAME).replace(chr(92), '/')
    log('table: Table_Custom with %s' % TABLE_PNG)
else:
    log('no table.png in %s (python make_table.py): the save keeps its wooden table' % a.work)
# the four core bags stay in the back row (z 20) with the Scheme / Twist / Strike decks; every other bag goes into two rows behind it,
# sorted by name, with room between them for each bag's Unpack / Repack buttons
CORE_BAGS = {'Heroes', 'Villains', 'Henchmen', 'Masterminds'}
bags = [o for o in mod['ObjectStates'] if o.get('Name') == 'Bag']
rest = [o for o in bags if not (o.get('Nickname') in CORE_BAGS and abs(o['Transform']['posZ'] - 20.1) < 0.3)]
rest.sort(key=lambda o: (o.get('Nickname', '').startswith('Extra'), o.get('Nickname', '').lower()))
PER_ROW, DX, ROW_Z, DZ = 12, 5.0, 26.0, 4.0
for i, o in enumerate(rest):
    r, c = divmod(i, PER_ROW)
    n = min(PER_ROW, len(rest) - r * PER_ROW)
    t = o['Transform']
    t['posX'] = round((c - (n - 1) / 2) * DX, 2)
    t['posZ'] = round(ROW_Z + r * DZ, 2)
    t['posY'] = 2.0
    t['rotX'] = t['rotZ'] = 0
log('bags: %d left in the back row, %d laid out in %d rows at z %.1f..%.1f' % (len(bags) - len(rest), len(rest), (len(rest) + PER_ROW - 1) // PER_ROW, ROW_Z, ROW_Z + DZ * ((len(rest) - 1) // PER_ROW)))
for o in mod['ObjectStates']:
    if o.get('Nickname', '').startswith('Expansion Bags Here'):
        o['Transform']['posX'], o['Transform']['posZ'] = -36.5, 28.0

# ---- find the save slot ------------------------------------------------------------------
log('phase 4/6: looking for a save named %r in %s' % (a.name, a.saves))
slot = None
cands = sorted(glob.glob(os.path.join(a.saves, 'TS_Save_*.json')))
for i, f in enumerate(cands, 1):
    try:
        head = open(f, encoding='utf-8', errors='replace').read(400000)
        m = re.search(r'"SaveName"\s*:\s*"([^"]*)"', head)
        if m and m.group(1) == a.name: slot = f
    except Exception:
        pass
    if i % 25 == 0: log('   checked %d/%d save files' % (i, len(cands)))
if not slot:
    sys.exit('No save named %r in %s. In TTS: start any game, Games > Save & Load > save as %r, close TTS, rerun.' % (a.name, a.saves, a.name))
log('   using %s' % slot)

# ---- copy images -------------------------------------------------------------------------
os.makedirs(IMG, exist_ok=True)
todo = []
for k in sorted(used):
    d = os.path.join(IMG, files[k]); sp = os.path.join(src_new, files[k])
    if not os.path.exists(d) or os.path.getsize(d) != os.path.getsize(sp): todo.append((files[k], sp, d))
total_mb = sum(os.path.getsize(sp) for _, sp, _ in todo) / 1e6
log('phase 5/6: copying images: %d to copy (%.0f MB), %d already in place' % (len(todo), total_mb, len(used) - len(todo)))
done_mb, tlast = 0.0, time.time()
for i, (name, sp, d) in enumerate(todo, 1):
    mb = os.path.getsize(sp) / 1e6
    log('   [%d/%d] copying %s (%.1f MB)  total so far %.0f/%.0f MB' % (i, len(todo), name[-40:], mb, done_mb, total_mb))
    with Heartbeat('copying ' + name[-30:]):
        shutil.copy2(sp, d)
    done_mb += mb
if os.path.exists(PM_PNG):
    shutil.copy2(PM_PNG, os.path.join(IMG, PM_NAME))
    log('   copied %s' % PM_NAME)
if os.path.exists(TABLE_PNG):
    shutil.copy2(TABLE_PNG, os.path.join(IMG, TABLE_NAME))
    log('   copied %s' % TABLE_NAME)
for p in skin_files:
    dst = os.path.join(IMG, os.path.basename(p))
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(p):
        log('   copying %s (%.1f MB)' % (os.path.basename(p), os.path.getsize(p) / 1e6))
        with Heartbeat('copying ' + os.path.basename(p)):
            shutil.copy2(p, dst)
bad = [u for u in re.findall(r'file:///[^"\\]+', json.dumps(mod)) if not os.path.exists(u[len('file:///'):].replace('/', '\\' if os.name == 'nt' else '/'))]
if bad: sys.exit('missing asset files: %s' % bad[:5])
log('   all %d referenced image files are present' % len(used))

# ---- write the save ----------------------------------------------------------------------
log('phase 6/6: writing the save')
mod['SaveName'] = a.name
mod['Date'] = time.strftime('%m/%d/%Y %I:%M:%S %p'); mod['EpochTime'] = int(time.time())
tmp = slot + '.new'
with Heartbeat('writing the save JSON', probe=lambda: '%.0f MB written' % (os.path.getsize(tmp) / 1e6)):
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(mod, f, ensure_ascii=False, indent=2)
shutil.copy2(slot, slot + '.bak')
os.replace(tmp, slot)
log('DONE: wrote %s (%.0f MB). Previous content kept as .bak. Images in %s' % (slot, os.path.getsize(slot) / 1e6, IMG))
