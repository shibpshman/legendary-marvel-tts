import json, os, re
WORK = r'E:\Media\Board Games\TTS_work'
mod  = r'E:\Documents\My Games\Tabletop Simulator\Mods\Workshop\2410733963.json'
raw  = open(mod, encoding='utf-8').read()
man  = json.load(open(os.path.join(WORK, 'manifest.json')))
out  = open(os.path.join(WORK, 'unused_sheets.txt'), 'w', encoding='utf-8')
for m in man:
    if m['used']: continue
    hits = [x.start() for x in re.finditer(re.escape(m['url']), raw)]
    out.write(f"{m['nx']}x{m['ny']} size={m['size']} occurrences={len(hits)}\n  {m['url']}\n")
    for s in hits[:2]:
        out.write('    ... ' + raw[max(0, s-220): s+len(m['url'])+100].replace('\\n', ' | ') + '\n')
    out.write('\n')
print('done')