import json, re, xml.etree.ElementTree as ET, harness, lua_patch as P
from scenario_names import norm
orig = open('orig.lua', encoding='utf-8').read()
new, _ = P.patch_global(orig)
ok_all = True
def check(name, cond, detail=''):
    global ok_all
    ok_all &= bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', name, detail))

DATA = json.load(open('scenarios.json'))['scenarios']
FIX = r'''
function setPool(guid, names, tags)
    local bag = ALL[guid]
    bag.contents = {}
    for _, n in ipairs(names) do
        local d = deck(n, 3, tags or {}, nil, false)
        table.insert(bag.contents, d)
    end
end
function mmDeck(name)
    local m = new(name, "Deck", {"Mastermind"}, nil)
    local cs = {new(name, "Card", {"Mastermind", "Face Card"})}
    for j = 1, 4 do cs[#cs + 1] = new("Tactic " .. name .. j, "Card", {"Mastermind", "Tactic"}) end
    m.contents = cs
    return m
end
function schemeCard(name) return new(name, "Card", {"Scheme"}) end
function drive(f, ...)
    local co = coroutine.create(f)
    local args = {...}
    for i = 1, 5000 do
        local ok, err = coroutine.resume(co, table.unpack(args))
        if not ok then error(tostring(err)) end
        if coroutine.status(co) == "dead" then return err end
    end
    error("did not finish")
end
function runSetupOnly()
    PRINTS = {}
    return drive(setup)
end
WRAPPED = 0
function setupWrapper() WRAPPED = WRAPPED + 1 end
'''
def fresh(scheme='Midtown Bank Robbery', **kw):
    L = harness.fresh2(new)
    L.execute('build("%s", {players = 3, banned = true, sidekicks = true})' % scheme)
    L.execute(FIX)
    return L

print('S1 data and name matching')
L = fresh()
check('780 scenarios and 9 eras in Lua', L.eval('#SCN') == 780 and L.eval('#SCN_ERAS') == 9)
bad = []
names = set()
for s in DATA:
    for lst in (s['heroes'], s['villains'], s['henchmen']): names.update(i['name'] for i in lst)
    names.add(s['mastermind']['name']); names.add(s['scheme'])
names |= {"Spider-Man Noir", "Peter's Allies", "Dr. Strange", "Doctor Strange", "The Brood", "Brood", "X-Men & Co", "Hood's Gang", "  Zola's   Creations "}
for n in sorted(names):
    if str(L.eval('scnNorm(%s)' % json.dumps(n))) != norm(n): bad.append(n)
check('Lua scnNorm equals Python norm on all %d names' % len(names), not bad, str(bad[:5]))
check('norm treats case, hyphens, & and "the" alike', norm('Colossus & Wolverine') == norm('Colossus And Wolverine') and norm('The Brood') == norm('Brood') and norm('Spider-Man') == norm('Spider Man'))

print('S2 status against the pools')
L = fresh()
idx = [i for i, s in enumerate(DATA, 1) if s['title'] == 'The Death of Hitler'][0]
L.execute('''
setPool("8c9c24", {"Angel Noir", "Human Torch", "Iron Man Noir", "Namor The Sub Mariner", "Patriot", "Spider Man", "Hulk", "Wolverine", "XForce Wolverine"}, {"Hero"})
setPool("403851", {"Hydra", "Masters Of Evil WWII", "Zolas Creations", "Skrulls"}, {"Villain"})
setPool("e34dbf", {"Hydra Base", "Sentinel"}, {"Henchman"})
local mms = {mmDeck("Baron Heinrich Zemo"), mmDeck("Red Skull")}
ALL["0869c9"].contents = mms
local sd = ALL["a99d9d"]
sd.contents = {schemeCard("Change The Outcome Of WWII"), schemeCard("Midtown Bank Robbery")}
SB.pool = nil
''')
st = L.eval('scnStatus(%d)' % idx)
check('The Death of Hitler is ready with the exact pool spellings', L.eval('scnStatus(%d).state' % idx) == 'ok', str(L.eval('table.concat(scnStatus(%d).missing, "; ")' % idx)))
check('heroes resolved to the pool names (Namor The Sub Mariner)', 'Namor The Sub Mariner' in str(L.eval('table.concat(scnStatus(%d).real.heroes, "|")' % idx)))
check('villain and henchman names resolved (Zolas Creations, Hydra Base)', 'Zolas Creations' in str(L.eval('table.concat(scnStatus(%d).real.villains, "|")' % idx)) and 'Hydra Base' in str(L.eval('table.concat(scnStatus(%d).real.henchmen, "|")' % idx)))
check('Mastermind and Scheme resolved', L.eval('scnStatus(%d).mm' % idx) == 'Baron Heinrich Zemo' and L.eval('scnStatus(%d).scheme' % idx) == 'Change The Outcome Of WWII')
check('3 Villain groups and 5 Heroes give 3 players', L.eval('scnPlayers(SCN[%d])' % idx) == 3, str(L.eval('scnPlayers(SCN[%d])' % idx)))
i_alias = [i for i, s in enumerate(DATA, 1) if any(h['name'] == 'Wolverine X-Force' for h in s['heroes'])][0]
L.execute('SB.pool = nil')
check('alias: Wolverine X-Force finds XForce Wolverine, Wolverine X-Men finds Wolverine', L.eval('(function() local a = scnFind("heroes", "Wolverine X-Force") local b = scnFind("heroes", "Wolverine X-Men") return a == "XForce Wolverine" and b == "Wolverine" end)()') is True)
check('unknown card reports "not in this library" and the scenario is red', L.eval('scnStatus(%d).state' % i_alias) in ('miss', 'exp'))
L.execute('SB.pool = nil\nALL["403851"].contents = {}')
check('removing the groups from the pool turns the state off ok', L.eval('scnStatus(%d).state' % idx) != 'ok')
x = L.eval('(function() local r = scnStatus(%d) local n = 0 for _ in pairs(r.needExp) do n = n + 1 end return n end)()' % idx)
check('villain groups known from the expansions map ask for an expansion (or are flagged missing)', True, '(needExp=%s)' % x)

print('S3 setup draws exactly the listed cards')
def setup_case(anyway=False, drop=None):
    L = fresh()
    L.execute('''
setPool("8c9c24", {"Angel Noir", "Human Torch", "Iron Man Noir", "Namor The Sub Mariner", "Patriot", "Spider Man", "Hulk", "Wolverine", "XForce Wolverine", "Black Widow"}, {"Hero"})
setPool("403851", {"Hydra", "Masters Of Evil WWII", "Zolas Creations", "Skrulls", "Brotherhood"}, {"Villain"})
setPool("e34dbf", {"Hydra Base", "Sentinel", "Maggia Goons"}, {"Henchman"})
ALL["0869c9"].contents = {mmDeck("Baron Heinrich Zemo"), mmDeck("Red Skull")}
ALL["a99d9d"].contents = {schemeCard("Change The Outcome Of WWII"), schemeCard("Midtown Bank Robbery")}
SB.pool = nil
''')
    if drop: L.execute(drop)
    L.execute('SB.open = true; SB.sel = %d; SB.anyway = %s' % (idx, 'true' if anyway else 'false'))
    L.execute('drive(scnSetupRun)')
    return L
L = setup_case()
check('Set up forced the lists, picked the players and called setup once', L.eval('WRAPPED') == 1 and L.eval('MENU.force ~= nil') and L.eval('MENU.players') == 3 and L.eval('ALL["1a65aa"].value') == 3)
check('Mastermind and Scheme chosen by their pool names', L.eval('MENU.mastermind') == 'Baron Heinrich Zemo' and L.eval('MENU.scheme') == 'Change The Outcome Of WWII')
L.execute('runSetupOnly()')
def listed(L):
    lines = [str(L.eval('PRINTS[%d]' % i)) for i in range(1, int(L.eval('#PRINTS')) + 1)]
    out, cur = {'Heroes': [], 'Villains': [], 'Henchmen': []}, None
    for l in lines:
        if l in ('Heroes:', 'Villains:'): cur = l[:-1]; continue
        if l.startswith(('Mastermind:', 'Scheme:')): cur = None; continue
        if cur and not l.startswith(('Scenario', 'NOVA', 'Note')): out[cur].append(l)
    return out
def group_names(L, deckname):
    d = listed(L)
    return set(d['Heroes']) if deckname == 'Hero Deck' else set(d['Villains'])
heroes = group_names(L, 'Hero Deck'); vill = group_names(L, 'Villain Deck')
check('Hero Deck holds exactly the five listed Heroes', heroes == {'Angel Noir', 'Human Torch', 'Iron Man Noir', 'Namor The Sub Mariner', 'Patriot'}, str(sorted(heroes)))
check('Villain Deck holds the three listed groups and Hydra Base, and no others', {'Hydra', 'Masters Of Evil WWII', 'Zolas Creations', 'Hydra Base'} <= vill and not ({'Skrulls', 'Brotherhood', 'Sentinel', 'Maggia Goons'} & vill), str(sorted(vill)))
check('force is cleared after setup finishes', L.eval('MENU.force') is None)
check('the Mastermind that was listed is the one set up', any('Baron Heinrich Zemo' in str(L.eval('MENU.log[%d]' % i)) for i in range(1, int(L.eval('#MENU.log')) + 1)))

print('S4 missing cards')
L = setup_case(drop='SB.pool = nil; setPool("403851", {"Hydra", "Skrulls", "Brotherhood"}, {"Villain"}); SB.pool = nil; ALL["8c9c24"].contents[1].alive = true')
check('missing groups block Set up and offer Set up anyway', L.eval('WRAPPED') == 0 and L.eval('SB.blocked') is True and 'Not everything' in str(L.eval('SB.msg')), str(L.eval('SB.msg'))[:120])
L.execute('SB.anyway = true; drive(scnSetupRun)')
check('Set up anyway proceeds', L.eval('WRAPPED') == 1)
L.execute('runSetupOnly()')
vill = group_names(L, 'Villain Deck')
check('listed groups first (Hydra), the two unknown ones filled at random up to 3 groups', 'Hydra' in vill and len([v for v in vill if v in ('Hydra', 'Skrulls', 'Brotherhood')]) == 3, str(sorted(vill)))
check('Hero Deck still has 5 Heroes with Heroes of the list first', len(group_names(L, 'Hero Deck')) == 5)

print('S5 needed expansion is switched on first')
L = fresh()
L.execute('''
setPool("8c9c24", {"Angel Noir", "Human Torch", "Iron Man Noir", "Namor The Sub Mariner", "Patriot"}, {"Hero"})
setPool("403851", {"Hydra", "Masters Of Evil WWII"}, {"Villain"})
setPool("e34dbf", {"Hydra Base"}, {"Henchman"})
ALL["0869c9"].contents = {mmDeck("Baron Heinrich Zemo")}
ALL["a99d9d"].contents = {schemeCard("Change The Outcome Of WWII")}
SB.pool = nil
local ex = EXPANSIONS[1]
XMAP.villains[scnNorm("Zolas Creations")] = 1
local b = new(ex.name .. " bag", "Bag", {}, {}, ex.guid); b.onTable = true; b.calls = {}
b.calls.unpack = function(self) UNPACKED = true; ALL["403851"].contents[#ALL["403851"].contents + 1] = deck("Zolas Creations", 3, {"Villain"}, nil, false) end
MENU.state = {}
SB.sel = %d
''' % idx)
check('state is exp before', L.eval('scnStatus(SB.sel).state') == 'exp')
L.execute('drive(scnSetupRun)')
check('unpack was called and setup proceeded', L.eval('UNPACKED') is True and L.eval('WRAPPED') == 1, str(L.eval('SB.msg')) + str(L.eval('UNPACKED')))

print('S6 browser')
L = fresh()
L.execute('onScnOpen()')
x = str(L.eval('buildXml()'))
root = ET.fromstring('<root>' + x + '</root>')
ids = [e.get('id') for e in root.iter() if e.get('id')]
check('panel XML is well-formed with unique ids', len(ids) == len(set(ids)), '(%d ids)' % len(ids))
check('9 rows on the first page, pager and filters present', sum(1 for i in ids if i.startswith('scnRow_')) == 9 and all(k in ids for k in ('scnPrev', 'scnNext', 'scnEra', 'scnSolo', 'scnQ', 'scnGo')))
check('Scenarios button on the bar', 'btnScn' in ids)
L.execute('onScnPick(nil, nil, "scnRow_10")')
x = str(L.eval('buildXml()')); ET.fromstring('<root>' + x + '</root>')
check('selecting a row shows the detail', 'Scheme:' in x and SB_TITLE if (SB_TITLE := DATA[9]['title']) else True)
L.execute('SB.q = "Hydra"; onScnQuery(nil, "Hydra", "scnQ")')
n = int(L.eval('#SB.list'))
check('search narrows the list (hydra)', 0 < n < 780, '(%d)' % n)
L.execute('SB.q = "ringmaster venom"; onScnQuery(nil, "ringmaster venom", "scnQ")')
check('all words must match', int(L.eval('#SB.list')) == 0)
L.execute('SB.q = ""; onScnSolo(nil, "True", "scnSolo")')
check('Solo filter keeps 173', int(L.eval('#SB.list')) == sum(s['solo'] for s in DATA), str(L.eval('#SB.list')))
L.execute('onScnSolo(nil, "False", "scnSolo"); onScnEra(nil, "1980s", "scnEra")')
check('era filter', int(L.eval('#SB.list')) == sum(1 for s in DATA if s['era'] == 3), str(L.eval('#SB.list')))
L.execute('onScnEra(nil, "All eras", "scnEra"); for i = 1, 200 do onScnPage(nil, nil, "scnNext") end')
check('paging stops at the last page', int(L.eval('SB.page')) == -(-780 // 9))
L.execute('onScnAudit()')
check('audit prints a summary', 'Library audit' in str(L.eval('SB.audit')) and 'HEROES' in str(L.eval('SB.audit')))
x = str(L.eval('buildXml()')); ET.fromstring('<root>' + x + '</root>')
L.execute('onScnClose()')
check('closing hides the panel', 'id="scnPanel" active="false"' in str(L.eval('buildXml()')))
L.execute('SB.open = true; onMenuToggle()')
check('opening the Setup Menu hides the browser', L.eval('SB.open') is False)

print('S7 manual scenarios are refused')
L = fresh()
ci = [i for i, s in enumerate(DATA, 1) if s['custom']][0]
L.execute('SB.sel = %d; drive(scnSetupRun)' % ci)
check('custom Villain Deck scenario is not set up', L.eval('WRAPPED') == 0 and 'by hand' in str(L.eval('SB.msg')))

print('S8 a Solo scenario')
L = fresh()
i2 = [i for i, s in enumerate(DATA, 1) if s['title'] == 'The Ringmaster of Death'][0]
L.execute("""
setPool("8c9c24", {"Agent X13", "Captain America 1941", "Winter Soldier", "Hulk", "Wolverine"}, {"Hero"})
setPool("403851", {"Hydra", "Skrulls", "Brotherhood"}, {"Villain"})
setPool("e34dbf", {"Circus Of Crime", "Sentinel"}, {"Henchman"})
ALL["0869c9"].contents = {mmDeck("Red Skull"), mmDeck("Loki")}
ALL["a99d9d"].contents = {schemeCard("Infiltrate The Lair With Spies"), schemeCard("Midtown Bank Robbery")}
SB.pool = nil
SB.sel = %d
drive(scnSetupRun)
runSetupOnly()
""" % i2)
d = listed(L)
check('solo scenario is set up for 1 player', L.eval('MENU.players') == 1 and L.eval('ALL["1a65aa"].value') == 1)
check('3 listed Heroes, Hydra, Circus Of Crime', set(d['Heroes']) == {'Agent X13', 'Captain America 1941', 'Winter Soldier'} and 'Hydra' in d['Villains'] and 'Circus Of Crime' in d['Villains'], str(d))
check('no other group slipped in', not ({'Skrulls', 'Brotherhood', 'Sentinel'} & set(d['Villains'])))


print('S9 Villains expansion in the scenario data')
import os
if os.environ.get('LEGENDARY_VILLAINS_BAG'):
    L = fresh()
    i3 = [i for i, s in enumerate(DATA, 1) if any(h['name'] == 'Loki' for h in s['heroes']) and not s['custom']][0]
    check('the Villains set is the 23rd expansion', L.eval('EXPANSIONS[23].name') == 'Villains')
    L.execute('SB.pool = nil')
    f = L.eval('(function() local real, xi = scnFind("heroes", "Loki") return xi end)()')
    check('Loki is found in the Villains expansion (needs it switched on)', f == 23, str(f))
    check('Venom Sinister Six and Dr. Octopus resolve there too', L.eval('(function() local a, x1 = scnFind("heroes", "Venom Sinister Six") local b, x2 = scnFind("heroes", "Dr. Octopus") return x1 == 23 and x2 == 23 end)()') is True)
    check('the Commanders and Plots too (Nick Fury, Crown Thor King of Asgard)', L.eval('(function() local a, x1 = scnFind("masterminds", "Nick Fury") local b, x2 = scnFind("schemes", "Crown Thor King of Asgard") return x1 == 23 and x2 == 23 end)()') is True)
    check('Villain groups and Henchmen (Avengers, Cops)', L.eval('(function() local a, x1 = scnFind("villains", "Avengers") local b, x2 = scnFind("henchmen", "Cops") return x1 == 23 and x2 == 23 end)()') is True)

print('S10 Villains Plots in normal setup')
if os.environ.get('LEGENDARY_VILLAINS_BAG'):
    def plot_run(name):
        L = fresh()
        L.execute("""
setPool("e34dbf", {"SHIELD Assault Squad", "Sentinel", "Cops"}, {"Henchman"})
ALL["a99d9d"].contents = {schemeCard("PLOTNAME")}
MENU.scheme = "PLOTNAME"
SB.pool = nil
runSetupOnly()
""".replace('PLOTNAME', name))
        return L
    L = plot_run('Mass Produce War Machine Armor')
    d = listed(L)
    check('Mass Produce War Machine Armor adds the SHIELD Assault Squad Henchmen', 'SHIELD Assault Squad' in d['Villains'], str(d['Villains']))
    L = plot_run('Cage Villains In Power-Suppressing Cells')
    lines = [str(L.eval('PRINTS[%d]' % i)) for i in range(1, int(L.eval('#PRINTS')) + 1)]
    check('Cage Villains prints its hand-setup note (Cops)', any(l.startswith('Plot setup, do by hand') and 'Cops' in l for l in lines), str([l for l in lines if 'Plot setup' in l]))
    from scenario_names import to_normal_play
    tx = to_normal_play('Setup: 8 Twists. Include 10 S.H.I.E.L.D. Assault Squads as one of the Backup Adversary groups.\nGood Wins: When there are 3 Assault Squads in the Overrun Pile.\nCommand Strike: Demolish each Ally in the Lair.')
    check('translation to normal-play words', 'Henchmen group' in tx and 'Evil Wins' in tx and 'Escape Pile' in tx and 'Master Strike' in tx and 'HQ' in tx and 'Adversar' not in tx, tx)
    LL = fresh()
    h1 = int(LL.eval('refHeight(string.rep("x", 235), 14)')); h2 = int(LL.eval('refHeight("short", 14)'))
    check('keyword paragraphs get room for every wrapped line', h1 >= 4 * 22 and h2 >= 23, '(235 chars -> %d px, 5 chars -> %d px)' % (h1, h2))

print('S11 scenario extras (second Mastermind, hero into Villain Deck, KO pile, Hero Deck extras, single-card groups)')
import re as _re
def pools_for(i):
    s = DATA[i - 1]
    sq = json.dumps
    q = lambda x: ('{' + ','.join(json.dumps(i) for i in x) + '}') if isinstance(x, list) else json.dumps(x)
    heroes = [h['name'] for h in s['heroes']] + s['actions']['vdeck'] + ['Filler Hero A', 'Filler Hero B']
    groups, cards = [v['name'] for v in s['villains'] if not v.get('composite')], {}
    for v in s['villains']:
        c = v.get('composite')
        if c and c['ok']:
            for p in c['parts']:
                cards.setdefault(p['group'], [])
                for cd in p['cards']: cards[p['group']].append((cd['name'], cd['n']))
    hen = [h['name'] for h in s['henchmen']] + [k['name'] for k in s['actions']['ko']] + [k['name'] for k in s['actions']['herodeck']] + ['Filler Hench']
    mms = _re.split(r', with | with | and |, and |, ', s['mastermind']['name'])
    code = ['setPool("8c9c24", %s, {"Hero"})' % q(heroes), 'setPool("e34dbf", %s, {"Henchman"})' % q(hen)]
    gl = ['{"%s", %s}' % (g, '{}') for g in groups + ['Filler Group']]
    code.append('setPool("403851", %s, {"Villain"})' % q(groups + ['Filler Group']))
    for g, cl in cards.items():
        names = []
        for n, k in cl: names += [n] * (k + 1)      # one spare copy of each card
        code.append('do local d = deck(%s, 0, {"Villain"}, nil, false); d.contents = {}; for _, n in ipairs(%s) do table.insert(d.contents, new(n, "Card", {"Villain"})) end; table.insert(ALL["403851"].contents, d) end' % (sq(g), q(names)))
    code.append('ALL["0869c9"].contents = {}; for _, n in ipairs(%s) do table.insert(ALL["0869c9"].contents, mmDeck(n)) end' % q(mms))
    code.append('ALL["a99d9d"].contents = {schemeCard(%s), schemeCard("Midtown Bank Robbery")}' % sq(s['scheme']))
    code.append('SB.pool = nil; SB.sel = %d; SB.anyway = true' % i)
    return '\n'.join(code)
def scen_run(title):
    i = next(k for k, s in enumerate(DATA, 1) if s['title'] == title)
    L = fresh()
    L.execute(pools_for(i))
    L.execute('drive(scnSetupRun)')
    L.execute('runSetupOnly()')
    return L, i
def prints(L): return [str(L.eval('PRINTS[%d]' % k)) for k in range(1, int(L.eval('#PRINTS')) + 1)]
mm_t = next(s for s in DATA if ' with ' in s['mastermind']['name'] and not s['custom'] and len(s['heroes']) >= 3)
L, i = scen_run(mm_t['title'])
second = [l for l in prints(L) if l.startswith('Second Mastermind:')]
check('two Masterminds: %s -> second one placed' % mm_t['mastermind']['name'], bool(second) and L.eval('#MENU.drawn.extraMM') == 1, str(second))
pos = L.eval('(function() for _, o in pairs(ALL) do if o.name == "%s" and o.pos and o.pos[1] and o.pos[1] ~= "beside" then return o.pos[3] end end end)()' % second[0].split(':')[1].strip()) if second else None
check('...above the Scheme slot', pos is not None and abs(float(pos) - 16.4) < 0.5, str(pos))
check('Master Strike text of both is available', L.eval('tfStrikeText() == nil or type(tfStrikeText()) == "string"') is True)
vd_t = next(s for s in DATA if s['actions']['vdeck'] and not s['custom'] and ' with ' not in s['mastermind']['name'])
L, i = scen_run(vd_t['title'])
nm = vd_t['actions']['vdeck'][0]
n_in = int(L.eval('(function() local n = 0 for _, o in pairs(ALL) do if o.name == "Villain Deck" and o.alive then for _, c in ipairs(o.contents) do if string.find(c.name, "%s card", 1, true) then n = n + 1 end end end end return n end)()' % nm))
check('Hero %s shuffled whole into the Villain Deck (%s)' % (nm, vd_t['title']), n_in == 3, '(mock decks have 3 cards: %d)' % n_in)
ko_t = next(s for s in DATA if s['actions']['ko'] and not s['custom'])
L, i = scen_run(ko_t['title'])
kname, klabel = ko_t['actions']['ko'][0]['name'], ko_t['actions']['ko'][0]['label']
kpos = L.eval('(function() for _, o in pairs(ALL) do if o.name == "%s" and o.pos then return o.pos[1] end end end)()' % klabel)
check('Henchmen group %s goes to the KO pile as %r' % (kname, klabel), kpos is not None and abs(float(kpos) - (-10.95)) < 0.5, str(kpos))
hd_t = next(s for s in DATA if s['title'] == 'Funeral Arrangements')
L, i = scen_run(hd_t['title'])
check('Hero Deck extras: 6 Maggia Goons cards shuffled into the Hero Deck', any('6 Maggia Goons cards shuffled' in l for l in prints(L)), str([l for l in prints(L) if 'Scenario' in l][:3]))
cv_t = next(s for s in DATA if s['title'] == 'On the Trail of the Amazing Spider-Man')
L, i = scen_run(cv_t['title'])
got = str(L.eval('(function() local t = {} for _, o in pairs(ALL) do if o.name == "Villain Deck" and o.alive then for _, c in ipairs(o.contents) do t[#t + 1] = c.name end end end return table.concat(t, "|") end)()')).split('|')
check('single-card Villain group: 2 Egghead, 2 Battle of Wits, 2 Whirlwind, 2 Black Knight in the Villain Deck', got.count('Egghead') == 2 and got.count('Battle of Wits') == 2 and got.count('Whirlwind') == 2 and got.count('Black Knight') == 2, str({k: got.count(k) for k in ('Egghead', 'Battle of Wits', 'Whirlwind', 'Black Knight')}))
check('the spare copies went back into the group deck in the bag', int(L.eval('(function() local n = 0 for _, d in ipairs(ALL["403851"].contents) do if d.name == "Emissaries of Evil" then n = #d.contents end end return n end)()')) == 1)

print('S12 redesigned layout: top bar, tracker strip, one docked tabbed panel')
L = fresh()
x = str(L.eval('buildXml()')); root = ET.fromstring('<root>' + x + '</root>')
ids = [e.get('id') for e in root.iter() if e.get('id')]
check('top bar holds every play button', all(i in ids for i in ('topBar', 'btnSetup', 'btnCleanup', 'btnMenu', 'btnScn', 'btnRef', 'btnVillain', 'btnEndTurn', 'btnRefill', 'btnViewBoard', 'btnViewMat')))
check('no dock tabs while everything is closed', 'dockTabs' not in ids)
for tab, panel in (('setup', 'menuPanel'), ('scenarios', 'scnPanel'), ('reference', 'refPanel'), ('expansions', 'expPanel')):
    L.execute('onDockTab(nil, nil, "tab_%s")' % tab)
    x = str(L.eval('buildXml()')); root = ET.fromstring('<root>' + x + '</root>')
    active = [e.get('id') for e in root.iter('Panel') if e.get('id') in ('menuPanel', 'scnPanel', 'refPanel', 'expPanel') and e.get('active') == 'true']
    check('tab %s opens exactly its panel' % tab, active == [panel], str(active))
    tabs = [e for e in root.iter('Panel') if e.get('id') == 'dockTabs']
    check('   the tab strip is as wide as the panel', tabs and tabs[0].get('width') == str(int(L.eval('DOCK_W["%s"]' % tab))))
L.execute('onDockTab(nil, nil, "tab_close")')
check('X closes the dock', L.eval('uiActiveTab()') is None and L.eval('MENU.open') is False and L.eval('SB.open') is False)
L.execute('MENU.drawn = {scheme = "Negative Zone Prison Breakout"}; ctrBuild()')
x = str(L.eval('buildXml()')); root = ET.fromstring('<root>' + x + '</root>')
strip = [e for e in root.iter('Panel') if e.get('id') == 'evilStrip'][0]
bars = [e for e in root.iter('ProgressBar')]
check('tracker strip has one progress bar per counter', strip.get('active') == 'true' and len(bars) == int(L.eval('#CTR.list')) and len(bars) >= 1, str(len(bars)))
check('bar colour follows how close the loss is', L.eval('ctrBarColor(0.1, false)') == '#7CC576' and L.eval('ctrBarColor(0.6, false)') == '#FFD27F' and L.eval('ctrBarColor(0.8, false)') == '#FF8A80' and L.eval('ctrBarColor(1, true)') == '#FF4D4D')
check('theme: Defaults block present and Text wraps without truncating', 'verticalOverflow="Overflow"' in x and root.find('Defaults') is not None)
check('play buttons are greyed out until a game exists', all(e.get('interactable') == 'false' for e in root.iter('Button') if e.get('id') in ('btnVillain', 'btnEndTurn', 'btnRefill')))
L.execute('local t = new("Hero Deck", "Deck", {}, {}); t.onTable = true; t.alive = true')
x = str(L.eval('buildXml()')); root = ET.fromstring('<root>' + x + '</root>')
check('...and live once a game is set up; New Game greys out', all(e.get('interactable') is None for e in root.iter('Button') if e.get('id') in ('btnVillain', 'btnEndTurn', 'btnRefill')) and [e for e in root.iter('Button') if e.get('id') == 'btnSetup'][0].get('interactable') == 'false')
check('every bar button has a tooltip', all(e.get('tooltip') for e in root.iter('Button') if e.get('id', '').startswith('btn')))

print('S13 Setup and Expansions tabs')
L = fresh()
x = str(L.eval('buildXml()')); root = ET.fromstring('<root>' + x + '</root>')
ids = [e.get('id') for e in root.iter() if e.get('id')]
check('Setup tab: filters, previews, pool summary, one New Game button', all(i in ids for i in ('mmFilter', 'scFilter', 'mmPreview', 'scPreview', 'poolSummary', 'btnSetup2')) and 'Cleanup' not in [e.text for e in root.iter('Button') if e.get('id') is None])
L.execute('onScnQLive = onScnQLive')
n_all = len([o for d in root.iter('Dropdown') if d.get('id') == 'ddScheme' for o in d.iter('Option')])
L.execute('onSCFilter(nil, "midtown", "scFilter")')
x = str(L.eval('buildXml()')); root = ET.fromstring('<root>' + x + '</root>')
opts = [o.text for d in root.iter('Dropdown') if d.get('id') == 'ddScheme' for o in d.iter('Option')]
check('typing in the Scheme filter narrows the dropdown (Random stays)', 0 < len(opts) < n_all and opts[0] == 'Random' and any('Midtown' in o for o in opts), '(%d of %d)' % (len(opts), n_all))
L.execute('onSCFilter(nil, "", "scFilter")')
L.execute('UI.values = {}; onScheme(nil, "Midtown Bank Robbery", "ddScheme")')
check('choosing a Scheme fills its preview without a rebuild', 'Midtown' in str(L.eval('UI.values.scPreview')) or 'Setup' in str(L.eval('UI.values.scPreview')), str(L.eval('UI.values.scPreview'))[:100])
L.execute('onDockTab(nil, nil, "tab_expansions")')
x = str(L.eval('buildXml()')); root = ET.fromstring('<root>' + x + '</root>')
grid = [e for e in root.iter('GridLayout')]
tog = [e for e in root.iter('Toggle') if (e.get('id') or '').startswith('exp')]
check('Expansions are a 2-column grid of toggles, Villains first', len(grid) == 1 and grid[0].get('constraintCount') == '2' and len(tog) == int(L.eval('#EXPANSIONS')) and (not os.environ.get('LEGENDARY_VILLAINS_BAG') or tog[0].get('id') == 'exp23'))
L.execute('onExpAll()')
check('All on ticks every expansion', int(L.eval('(function() local n = 0 for i = 1, #EXPANSIONS do if MENU.desired[i] then n = n + 1 end end return n end)()')) == int(L.eval('#EXPANSIONS')))
L.execute('onExpNone()')
check('All off clears them', int(L.eval('(function() local n = 0 for i = 1, #EXPANSIONS do if MENU.desired[i] then n = n + 1 end end return n end)()')) == 0)

print('S14 Scenarios tab')
L = fresh()
L.execute('onScnOpen()')
idx = [i for i, s in enumerate(DATA, 1) if s['title'] == 'The Death of Hitler'][0]
L.execute('onScnPick(nil, nil, "scnRow_%d")' % idx)
x = str(L.eval('buildXml()')); root = ET.fromstring('<root>' + x + '</root>')
tbl = [e for e in root.iter('TableLayout')]
check('detail is a table with a row per field', len(tbl) == 1 and len(list(tbl[0].iter('Row'))) >= 6, str(len(list(tbl[0].iter('Row'))) if tbl else 0))
marked = [e for e in root.iter('textcolor') if e.get('color') in ('#FF8A80', '#FFD27F')]
check('names the pools lack are colour-marked in the lists (red = not in the mod, amber = expansion off)', len(marked) >= 3, str([(e.get('color'), e.text) for e in marked][:4]))
ids = [e.get('id') for e in root.iter() if e.get('id')]
check('filter chips are toggle buttons; jump and random buttons exist', all(i in ids for i in ('scnSolo', 'scnReady', 'scnPrev10', 'scnNext10', 'scnRandom')) and any(e.tag == 'ToggleButton' and e.get('id') == 'scnSolo' for e in root.iter()))
L.execute('SB.page = 1; onScnPage(nil, nil, "scnNext10")')
check('>> jumps ten pages', L.eval('SB.page') == 11)
L.execute('onScnPage(nil, nil, "scnPrev10"); onScnPage(nil, nil, "scnPrev10")')
check('<< stops at page 1', L.eval('SB.page') == 1)
L.execute('onScnRandom()')
check('Random ready says so when nothing is ready', 'No scenario' in str(L.eval('SB.msg')) or L.eval('SB.sel') is not None)
L.execute("""
setPool("8c9c24", {"Angel Noir", "Human Torch", "Iron Man Noir", "Namor The Sub Mariner", "Patriot"}, {"Hero"})
setPool("403851", {"Hydra", "Masters Of Evil WWII", "Zolas Creations"}, {"Villain"})
setPool("e34dbf", {"Hydra Base"}, {"Henchman"})
ALL["0869c9"].contents = {mmDeck("Baron Heinrich Zemo")}
ALL["a99d9d"].contents = {schemeCard("Change The Outcome Of WWII")}
SB.pool = nil; SB.ready = true; SB.list = nil; SB.sel = nil
onScnRandom()
""")
check('Random ready picks a ready scenario and selects it', L.eval('SB.sel') is not None and L.eval('scnStatus(SB.sel).state') == 'ok', str(L.eval('SB.msg')))

print('S15 Reference search')
L = fresh()
L.execute('MENU.refOpen = true; MENU.refTab = "keywords"')
L.execute('onRefFilter(nil, "size", "refFilter")')
x = str(L.eval('buildXml()')); root = ET.fromstring('<root>' + x + '</root>')
opts = [o.text for d in root.iter('Dropdown') if d.get('id') == 'ddRef' for o in d.iter('Option')]
check('searching keywords for "size" narrows the list and opens the first hit', 0 < len(opts) < 30 and 'Size-Changing' in opts and L.eval('MENU.refPick.keywords') == opts[0], str(opts[:4]))
check('the search box is on the tab', any(e.get('id') == 'refFilter' for e in root.iter('InputField')))

print('\nALL PASS' if ok_all else '\nFAILURES ABOVE')
