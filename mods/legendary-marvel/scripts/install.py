"""Installs the Legendary build scripts into C:\\Users\\steph (or the folder you pass) and checks that everything is in place.
Usage: python install.py [destination]          (run it from the unzipped folder)
Prints a line per file, verifies each copy by SHA-256, compiles every script, and lists which generated files still need making."""
import hashlib, json, os, py_compile, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\steph'
WORK = r'E:\Media\Board Games\TTS_work'
T0 = time.time()


def log(m): print('[%s +%3ds] %s' % (time.strftime('%H:%M:%S'), time.time() - T0, m), flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


man = json.load(open(os.path.join(HERE, 'manifest.json'), encoding='utf-8'))
files = man['files']
log('installing %d files into %s' % (len(files), DEST))
os.makedirs(DEST, exist_ok=True)
bad, copied = [], 0
for i, (name, info) in enumerate(sorted(files.items()), 1):
    src, dst = os.path.join(HERE, name), os.path.join(DEST, name)
    if not os.path.isfile(src):
        bad.append('%s missing from the zip' % name); log('[%d/%d] %s: MISSING FROM THE ZIP' % (i, len(files), name)); continue
    if sha(src) != info['sha256']:
        bad.append('%s is damaged in the zip' % name); log('[%d/%d] %s: DAMAGED IN THE ZIP' % (i, len(files), name)); continue
    shutil.copy2(src, dst)
    ok = sha(dst) == info['sha256'] and os.path.getsize(dst) == info['bytes']
    copied += ok
    log('[%d/%d] %-26s %7d bytes  %s' % (i, len(files), name, info['bytes'], 'OK' if ok else 'COPY FAILED'))
    if not ok: bad.append('%s did not copy correctly' % name)
log('compiling the scripts')
for name in sorted(files):
    if name.endswith('.py'):
        try: py_compile.compile(os.path.join(DEST, name), doraise=True)
        except Exception as e: bad.append('%s: %s' % (name, e)); log('   %s: SYNTAX ERROR %s' % (name, e))
sys.path.insert(0, DEST)
try:
    import importlib
    for mod in ('mat_config', 'counter_lua', 'turn_lua', 'menu_lua', 'lua_patch'):
        importlib.import_module(mod)
    log('import check: mat_config, counter_lua, turn_lua, menu_lua, lua_patch all load')
except Exception as e:
    bad.append('import check failed: %s' % e); log('import check FAILED: %s' % e)

log('generated files the build needs (make them with the commands shown):')
need = [(os.path.join(WORK, 'reference_data.json'), 'python %s\\build_reference.py' % DEST),
        (os.path.join(WORK, 'playermat.png'), 'python %s\\make_player_mat.py' % DEST),
        (os.path.join(WORK, 'skins', 'mat_skin_1.jpg'), 'python %s\\make_mat_skins.py' % DEST),
        (os.path.join(WORK, 'card_text_ocr.csv'), '(already made earlier by card_text_ocr.py)')]
for path, how in need:
    log('   %-60s %s' % (path, 'present' if os.path.exists(path) else 'MISSING -> ' + how))
if bad:
    log('PROBLEMS: ' + '; '.join(bad)); sys.exit(1)
log('DONE: %d files installed and verified. Next: build_reference.py (if reference text changed), then build_save.py' % copied)
