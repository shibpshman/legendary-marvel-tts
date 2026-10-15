"""Lua for the Scenario browser: the Marvel History scenarios (data from build_scenarios.py), name matching against the
pools, the browser panel and the hooks that make setup() draw the listed Heroes / Villain groups / Henchmen."""
import json, os, re, time

from scenario_names import norm, ALIASES, CATALOG_SET_ALIASES, MOD_SETS, EXCLUDED_SETS

CANDIDATES = [os.environ.get('LEGENDARY_SCENARIOS', ''), r'E:\Media\Board Games\TTS_work\scenarios.json',
              os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenarios.json'), 'scenarios.json']
CAT_CANDIDATES = [os.environ.get('LEGENDARY_CATALOG', ''), r'E:\Media\Board Games\TTS_work\catalog.json',
                  os.path.join(os.path.dirname(os.path.abspath(__file__)), 'catalog.json'), 'catalog.json']
SPEC_CANDIDATES = [os.environ.get('LEGENDARY_VILLAINS_SPEC', ''), r'E:\\Media\\Board Games\\TTS_work\\villains_set_spec.json',
                   os.path.join(os.path.dirname(os.path.abspath(__file__)), 'villains_set_spec.json'), 'villains_set_spec.json']
BAG_CANDIDATES = [os.environ.get('LEGENDARY_VILLAINS_BAG', ''), r'E:\\Media\\Board Games\\TTS_work\\villains_set\\villains_bag.json',
                  os.path.join(os.path.dirname(os.path.abspath(__file__)), 'villains_bag.json')]
VILLAINS_INDEX = 23          # position of the Villains expansion in menu_lua.EXPANSIONS (1-based)


def villains_spec():
    """The Villains expansion spec when the bag has been built (build_villains_set.py), else None."""
    if not any(p and os.path.isfile(p) for p in BAG_CANDIDATES): return None
    p = next((p for p in SPEC_CANDIDATES if p and os.path.isfile(p)), None)
    return json.load(open(p, encoding='utf-8')) if p else None


XMAP_CANDIDATES = [os.environ.get('LEGENDARY_XMAP', ''), r'E:\Media\Board Games\TTS_work\expansion_names.json',
                   os.path.join(os.path.dirname(os.path.abspath(__file__)), 'expansion_names.json'), 'expansion_names.json']


def q(s):
    s = (s or '').encode('ascii', 'ignore').decode('ascii')
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ') + '"'


def _list(items, key):
    return '{' + ','.join(q(i[key]) for i in items) + '}'


def _opt_list(items, key, names):
    """Parallel list that is only written when some entry differs from the name (empty string = same)."""
    vals = [i[key] if i[key] and i[key] != n else '' for i, n in zip(items, names)]
    return '{' + ','.join(q(v) for v in vals) + '}' if any(vals) else None


def data_lua(path=None):
    path = path or next((p for p in CANDIDATES if p and os.path.isfile(p)), None)
    if path is None:
        print('[%s] WARNING: scenarios.json not found; the Scenario browser will be empty. Run build_scenarios.py first.' % time.strftime('%H:%M:%S'), flush=True)
        return '{}', '{}'
    d = json.load(open(path, encoding='utf-8'))
    rows = []
    for s in d['scenarios']:
        f = ['t=%s' % q(s['title']), 'e=%d' % (s['era'] + 1), 'p=%d' % s['page'], 'src=%s' % q(s['source']), 'sc=%s' % q(s['scheme']),
             'mm=%s' % q(s['mastermind']['name'])]
        if s['mod']: f.append('m=%s' % q(s['mod']))
        if s['mastermind']['qual']: f.append('mmq=%s' % q(s['mastermind']['qual']))
        if s['mastermind']['label'] != s['mastermind']['name']: f.append('mml=%s' % q(s['mastermind']['label']))
        for key, lst in (('v', s['villains']), ('hn', s['henchmen']), ('h', s['heroes'])):
            names = [i['name'] for i in lst]
            f.append('%s={%s}' % (key, ','.join(q(n) for n in names)))
            if key != 'h':
                qs = [i['qual'] or '' for i in lst]
                if any(qs): f.append('%sq={%s}' % (key, ','.join(q(x) for x in qs)))
            ls = _opt_list(lst, 'label', names)
            if ls: f.append('%sl=%s' % (key, ls))
        act = s.get('actions') or {}
        if act.get('vdeck'): f.append('vd={%s}' % ','.join(q(n) for n in act['vdeck']))
        if act.get('ko'):
            f.append('ko={%s}' % ','.join(q(k['name']) for k in act['ko'])); f.append('kol={%s}' % ','.join(q(k['label']) for k in act['ko']))
        if act.get('herodeck'):
            f.append('hd={%s}' % ','.join(q(k['name']) for k in act['herodeck'])); f.append('hdn={%s}' % ','.join(str(k['n']) for k in act['herodeck']))
        cvs = []
        for i, v in enumerate(s['villains'], 1):
            c = v.get('composite')
            if v['custom'] and c and c['ok']:
                parts = ','.join('{g=%s,c={%s}}' % (q(p['group']), ','.join('{%s,%d}' % (q(cd['name']), cd['n']) for cd in p['cards'])) for p in c['parts'])
                cvs.append('[%d]={n=%s,p={%s}}' % (i, q(c['name']), parts))
        if cvs: f.append('cv={%s}' % ','.join(cvs))
        if s['notes']: f.append('nt=%s' % q(s['notes']))
        if s['solo']: f.append('so=true')
        if s['villain_mat']: f.append('vm=true')
        if s['custom']: f.append('cu=true')
        rows.append('{' + ','.join(f) + '}')
    eras = '{' + ','.join(q(e) for e in d['eras']) + '}'
    print('[%s] scenarios: %d from %s' % (time.strftime('%H:%M:%S'), len(rows), path), flush=True)
    return eras, '{\n' + ',\n'.join(rows) + '}'


def _xmap_parts(data):
    kinds = ('heroes', 'villains', 'henchmen', 'masterminds', 'schemes')
    return '{' + ','.join('%s={%s}' % (k, ','.join('[%s]=%d' % (q(a), b) for a, b in sorted(data.get(k, {}).items()))) for k in kinds) + '}'


def xmap_lua(path=None):
    path = path or next((p for p in XMAP_CANDIDATES if p and os.path.isfile(p)), None)
    data = json.load(open(path, encoding='utf-8')) if path else {}
    if not path: print('[%s] WARNING: expansion_names.json not found; scenarios cannot tell which expansion adds a missing card.' % time.strftime('%H:%M:%S'), flush=True)
    kinds = ('heroes', 'villains', 'henchmen', 'masterminds', 'schemes')
    alias = []
    for k in kinds:
        alias.append('%s={%s}' % (k, ','.join('[%s]=%s' % (q(norm(a)), q(norm(b))) for a, b in sorted(ALIASES.get(k, {}).items()))))
    spec = villains_spec()
    if spec:
        for k, key in (('heroes', 'heroes'), ('villains', 'villains'), ('henchmen', 'henchmen'), ('masterminds', 'masterminds'), ('schemes', 'schemes')):
            for e in spec[key]:
                data.setdefault(k, {})[norm(e.get('deck_name') or e['name'])] = VILLAINS_INDEX
        print('[%s] Villains expansion bag found: its cards count as part of expansion %d' % (time.strftime('%H:%M:%S'), VILLAINS_INDEX), flush=True)
    return _xmap_parts(data), '{' + ','.join(alias) + '}', xcat_lua(data)


def xcat_lua(lib):
    """kind -> normalised name -> catalog set, for cards that belong to a set this mod does not hold."""
    path = next((p for p in CAT_CANDIDATES if p and os.path.isfile(p)), None)
    kinds = ('heroes', 'villains', 'henchmen', 'masterminds', 'schemes')
    xc = {k: {} for k in kinds}
    if path is None:
        print('[%s] WARNING: catalog.json not found; missing cards will not say which set they come from. Run build_catalog.py.' % time.strftime('%H:%M:%S'), flush=True)
    else:
        cat = json.load(open(path, encoding='utf-8'))
        for sname, d in cat.items():
            if sname in MOD_SETS or 'Second Edition' in sname or (sname == 'Villains' and villains_spec()): continue
            for k in kinds:
                for n in d.get(k, []):
                    key = norm(n)
                    if key in lib.get(k, {}): continue
                    xc[k].setdefault(key, sname)
        print('[%s] catalog: %d sets, %d cards outside this mod, from %s' % (time.strftime('%H:%M:%S'), len(cat), sum(len(v) for v in xc.values()), path), flush=True)
    for k in kinds:
        for n, sname in CATALOG_SET_ALIASES.get(k, {}).items():
            if sname == 'Villains' and villains_spec(): continue
            xc[k][norm(n)] = sname
    return '{' + ','.join('%s={%s}' % (k, ','.join('[%s]=%s' % (q(a), q(b)) for a, b in sorted(v.items()))) for k, v in xc.items()) + '}'


def scenario_lua(scn_path=None, xmap_path=None):
    eras, data = data_lua(scn_path)
    xmap, alias, xcat = xmap_lua(xmap_path)
    return SCENARIO_LUA.replace('__SCNERAS__', eras).replace('__SCNDATA__', data).replace('__XMAP__', xmap).replace('__ALIAS__', alias).replace('__XCAT__', xcat).replace('__XEXC__', '{' + ','.join('[%s]=true' % q(x) for x in sorted(EXCLUDED_SETS)) + '}')


SCENARIO_LUA = r'''
--[[ ---------- Scenario browser (Marvel History scenarios) ---------- --]]
SCN_ERAS = __SCNERAS__
SCN = __SCNDATA__
XMAP = __XMAP__
ALIAS = __ALIAS__
XCAT = __XCAT__
XEXC = __XEXC__
SB = {open = false, q = "", era = 0, solo = false, ready = false, page = 1, sel = nil, list = nil, msg = "", pool = nil, st = {},
      blocked = false, running = false, anyway = false, audit = nil}
SB_PAGE = 9
POOL_GUIDS = {heroes = "8c9c24", villains = "403851", henchmen = "e34dbf", masterminds = "0869c9", schemes = "a99d9d"}

--[[Same steps as scenario_names.norm in Python--]]
function scnNorm(s)
    s = " " .. string.lower(tostring(s)) .. " "
    s = string.gsub(s, "&", " and ")
    s = string.gsub(s, "[^%w%s]", "")
    s = string.gsub(s, "%s+", " ")
    s = string.gsub(s, " the ", " ")
    s = string.gsub(s, " the ", " ")
    s = string.gsub(s, " doctor ", " dr ")
    return (string.gsub(s, " ", ""))
end

function scnPool()
    if SB.pool ~= nil then return SB.pool end
    local p = {}
    for kind, guid in pairs(POOL_GUIDS) do
        p[kind] = {}
        local bag = getObjectFromGUID(guid)
        if bag ~= nil then
            local ok, entries = pcall(function() return bag.getObjects() end)
            if ok and entries ~= nil then
                for _, e in ipairs(entries) do
                    if e.name ~= nil and e.name ~= "" then p[kind][scnNorm(e.name)] = e.name end
                end
            end
        end
    end
    SB.pool = p
    SB.st = {}
    return p
end

--[[Returns the pool's own spelling when the card is in the pool now, else nil plus the expansion index (0 = base game) that adds it--]]
function scnFind(kind, name, qual)
    local pool = scnPool()[kind] or {}
    local x = XMAP[kind] or {}
    local keys = {}
    if qual ~= nil and qual ~= "" then keys[#keys + 1] = scnNorm(name .. " " .. qual) end
    keys[#keys + 1] = scnNorm(name)
    for _, k in ipairs(keys) do
        if pool[k] ~= nil then return pool[k], nil end
    end
    for _, k in ipairs(keys) do
        local a = (ALIAS[kind] or {})[k]
        if a ~= nil then
            if pool[a] ~= nil then return pool[a], nil end
            if x[a] ~= nil then return nil, x[a] end
        end
    end
    for _, k in ipairs(keys) do
        if x[k] ~= nil then return nil, x[k] end
    end
    return nil, nil
end

function scnCatSet(kind, name, qual)
    local x = XCAT[kind] or {}
    local k1 = scnNorm(name)
    if qual ~= nil and qual ~= "" and x[scnNorm(name .. " " .. qual)] ~= nil then return x[scnNorm(name .. " " .. qual)] end
    if x[k1] ~= nil then return x[k1] end
    local a = (ALIAS[kind] or {})[k1]
    if a ~= nil and x[a] ~= nil then return x[a] end
    return nil
end

function scnReplacePlain(s, a, b)
    local out, pos = "", 1
    while true do
        local i = string.find(s, a, pos, true)
        if i == nil then return out .. string.sub(s, pos) end
        out = out .. string.sub(s, pos, i - 1) .. b
        pos = i + #a
    end
end

--[["Loki with Odin", "Kingpin, with Red Skull", "Dr. Doom with Apocalypse, Galactus, and Ultron" -> separate names. A label that is one Mastermind stays whole.--]]
function scnSplitMM(label, qual)
    local real, xi = scnFind("masterminds", label, qual)
    if real ~= nil or xi ~= nil then return {label} end
    local s = string.gsub(label, "%s+", " ")
    s = scnReplacePlain(s, ", with ", ", ")
    s = scnReplacePlain(s, ", and ", ", ")
    s = scnReplacePlain(s, " with ", ", ")
    s = scnReplacePlain(s, " and ", ", ")
    local out, pos = {}, 1
    while pos <= #s do
        local i = string.find(s, ", ", pos, true)
        local part
        if i == nil then
            part = string.sub(s, pos)
            pos = #s + 1
        else
            part = string.sub(s, pos, i - 1)
            pos = i + 2
        end
        part = trimText(part)
        if part ~= "" then out[#out + 1] = part end
    end
    if #out < 2 then return {label} end
    return out
end

function scnLabel(sc, key, i)
    local l = sc[key .. "l"]
    if l ~= nil and l[i] ~= nil and l[i] ~= "" then return l[i] end
    return sc[key][i]
end

function scnStatus(i)
    scnPool()
    local c = SB.st[i]
    if c ~= nil then return c end
    local sc = SCN[i]
    local r = {missing = {}, miss = {}, needExp = {}, real = {heroes = {}, villains = {}, henchmen = {}}, nunres = {heroes = 0, villains = 0, henchmen = 0}, hard = false}
    local function check(kind, label, name, qual)
        local real, xi = scnFind(kind, name, qual)
        if real ~= nil then return real end
        local cset = nil
        if xi == nil or xi <= 0 then cset = scnCatSet(kind, name, qual) end
        r.miss[#r.miss + 1] = {kind = kind, name = name, xi = xi or -1, set = cset}
        if xi ~= nil and xi > 0 then
            r.needExp[xi] = true
            r.missing[#r.missing + 1] = label .. " [" .. EXPANSIONS[xi].name .. "]"
        elseif cset ~= nil then
            r.hard = true
            r.missing[#r.missing + 1] = label .. " [from " .. cset .. (XEXC[cset] and ", an excluded MCU / What If set]" or ", not in this mod]")
        else
            r.hard = true
            r.missing[#r.missing + 1] = label .. " [not in this mod or the card catalog: spelling?]"
        end
        return nil
    end
    r.mms = {}
    local mmNames = scnSplitMM(sc.mm, sc.mmq)
    for _, nm in ipairs(mmNames) do
        local real = check("masterminds", nm, nm, (#mmNames == 1) and sc.mmq or nil)
        if real ~= nil then r.mms[#r.mms + 1] = real end
    end
    r.mm = r.mms[1]
    r.comp, r.vdeck, r.ko, r.hd = {}, {}, {}, {}
    r.scheme = check("schemes", sc.sc, sc.sc, nil)
    for i2, n in ipairs(sc.h) do
        local real = check("heroes", n, n, nil)
        if real ~= nil then r.real.heroes[#r.real.heroes + 1] = real else r.nunres.heroes = r.nunres.heroes + 1 end
    end
    for i2, n in ipairs(sc.v) do
        local cv = sc.cv and sc.cv[i2] or nil
        if cv ~= nil then
            local parts = {}
            for _, p in ipairs(cv.p) do
                local real = check("villains", p.g .. " (for " .. cv.n .. ")", p.g, nil)
                if real ~= nil then parts[#parts + 1] = {group = real, cards = p.c} end
            end
            r.comp[#r.comp + 1] = {name = cv.n, parts = parts}
        else
            local real = check("villains", scnLabel(sc, "v", i2), n, sc.vq and sc.vq[i2] or nil)
            if real ~= nil then r.real.villains[#r.real.villains + 1] = real else r.nunres.villains = r.nunres.villains + 1 end
        end
    end
    for _, n in ipairs(sc.vd or {}) do
        local real = check("heroes", n .. " (into the Villain Deck)", n, nil)
        if real ~= nil then r.vdeck[#r.vdeck + 1] = real end
    end
    for k, n in ipairs(sc.ko or {}) do
        local real = check("henchmen", n .. " (KO pile)", n, nil)
        if real ~= nil then r.ko[#r.ko + 1] = {name = real, label = sc.kol[k]} end
    end
    for k, n in ipairs(sc.hd or {}) do
        local real = check("henchmen", n .. " (into the Hero Deck)", n, nil)
        if real ~= nil then r.hd[#r.hd + 1] = {name = real, n = sc.hdn[k]} end
    end
    for i2, n in ipairs(sc.hn) do
        local real = check("henchmen", scnLabel(sc, "hn", i2), n, sc.hnq and sc.hnq[i2] or nil)
        if real ~= nil then r.real.henchmen[#r.real.henchmen + 1] = real else r.nunres.henchmen = r.nunres.henchmen + 1 end
    end
    if sc.cu then r.state = "manual"
    elseif #r.missing == 0 then r.state = "ok"
    elseif r.hard then r.state = "miss"
    else r.state = "exp" end
    SB.st[i] = r
    return r
end

function scnPlayers(sc)
    local nh, nv, nn = #sc.h, #sc.v, #sc.hn
    if sc.so or nh <= 3 then return 1 end
    if nv >= 4 then return 5 end
    if nv == 3 then return (nn >= 2) and 4 or 3 end
    return (nn >= 2) and 4 or 2
end

function scnKeyOf(i)
    local sc = SCN[i]
    if sc.k == nil then
        sc.k = string.lower(table.concat({sc.t, sc.sc, sc.mm, sc.src, table.concat(sc.v, " "), table.concat(sc.hn, " "), table.concat(sc.h, " ")}, " | "))
    end
    return sc.k
end

function scnWords(q)
    local words, pos = {}, 1
    q = string.lower(trimText(q or ""))
    while pos <= #q do
        local j = string.find(q, " ", pos, true)
        local w
        if j == nil then
            w = string.sub(q, pos)
            pos = #q + 1
        else
            w = string.sub(q, pos, j - 1)
            pos = j + 1
        end
        if w ~= "" then words[#words + 1] = w end
    end
    return words
end

function scnFilter()
    local words = scnWords(SB.q)
    local out = {}
    for i, sc in ipairs(SCN) do
        local good = true
        if SB.era ~= 0 and sc.e ~= SB.era then good = false end
        if good and SB.solo and not sc.so then good = false end
        if good and #words > 0 then
            local k = scnKeyOf(i)
            for _, w in ipairs(words) do
                if string.find(k, w, 1, true) == nil then good = false break end
            end
        end
        if good and SB.ready and scnStatus(i).state ~= "ok" then good = false end
        if good then out[#out + 1] = i end
    end
    SB.list = out
    local pages = math.max(1, math.ceil(#out / SB_PAGE))
    if SB.page > pages then SB.page = pages end
    if SB.page < 1 then SB.page = 1 end
end

--[[ ---- panel ---- --]]
function scnStateColor(state, selected)
    if selected then return ' colors="#7CC576|#9BE093|#5FA35A|#C8C8C8"' end
    if state == "exp" then return ' colors="#F2E3A0|#FFF1B8|#D9C97F|#C8C8C8"' end
    if state == "miss" or state == "manual" then return ' colors="#E8B4B4|#FFD0D0|#C98F8F|#C8C8C8"' end
    return ''
end

function scnJoin(sc, key)
    local out = {}
    for i = 1, #sc[key] do out[#out + 1] = scnLabel(sc, key, i) end
    return table.concat(out, ", ")
end

--[[Names the scenario needs that the pools cannot supply right now: red when the mod lacks them, amber when an expansion is off--]]
function scnMissingMap(st)
    local mp = {}
    for _, m in ipairs(st.miss) do mp[m.kind .. "|" .. scnNorm(m.name)] = (m.xi > 0) and "#FFD27F" or "#FF8A80" end
    return mp
end

function scnMarkJoin(sc, key, kind, mp)
    local out = {}
    for i = 1, #sc[key] do
        local label = esc(scnLabel(sc, key, i))
        local col = mp[kind .. "|" .. scnNorm(sc[key][i])]
        if col ~= nil then label = '<textcolor color="' .. col .. '">' .. label .. '</textcolor>' end
        out[#out + 1] = label
    end
    return table.concat(out, ", ")
end

function scnDetailXml(add, i)
    local sc = SCN[i]
    local st = scnStatus(i)
    local mp = scnMissingMap(st)
    local function line(text, color, size, bold)
        size = size or 13
        add('<Text fontSize="' .. size .. '"' .. (bold and ' fontStyle="Bold"' or '') .. ' color="' .. (color or "#FFFFFF") .. '" alignment="UpperLeft" preferredHeight="' .. refHeight(text, size) .. '">' .. esc(text) .. '</Text>')
    end
    local tag = ""
    if sc.m == "new" then tag = "  NEW" elseif sc.m == "modified" then tag = "  MODIFIED" end
    line(sc.t .. tag, "#FFFFFF", 17, true)
    line((SCN_ERAS[sc.e] or "") .. "   -   " .. sc.src .. "   -   PDF page " .. sc.p, "#B9C2DA", 12)
    if st.state == "ok" then
        line("Ready: everything this scenario needs is in the pools now.", "#9BE093", 13, true)
    elseif st.state == "exp" then
        local names = {}
        for xi, _ in pairs(st.needExp) do names[#names + 1] = EXPANSIONS[xi].name end
        table.sort(names)
        line("Needs expansions that are off: " .. table.concat(names, ", ") .. ". Set up switches them on first.", "#F2E3A0", 13, true)
    elseif st.state == "manual" then
        line("The Villain Deck of this scenario is a list the PDF text breaks. Assemble it by hand from the lines below.", "#FF8A80", 13, true)
    else
        line("Not possible with this mod: red names below are missing. Set up anyway fills the gaps at random.", "#FF8A80", 13, true)
    end
    local rows = {}
    local function row(label, text, plain)
        rows[#rows + 1] = {label, text, plain}
    end
    row("Scheme", '<textcolor color="#8FD3FF">' .. esc(sc.sc) .. '</textcolor>', sc.sc)
    row("Mastermind", '<textcolor color="#FFB070">' .. esc(sc.mml or sc.mm) .. '</textcolor>', sc.mml or sc.mm)
    row("Villains", scnMarkJoin(sc, "v", "villains", mp), scnJoin(sc, "v"))
    row("Henchmen", scnMarkJoin(sc, "hn", "henchmen", mp), scnJoin(sc, "hn"))
    row("Heroes", scnMarkJoin(sc, "h", "heroes", mp), scnJoin(sc, "h"))
    local players = scnPlayers(sc)
    row("Players", players .. (sc.so and " (Solo scenario)" or "") .. ": " .. #sc.h .. " Heroes, " .. #sc.v .. " Villain groups, " .. #sc.hn .. " Henchmen groups", players .. (sc.so and " (Solo scenario)" or "") .. ": " .. #sc.h .. " Heroes, " .. #sc.v .. " Villain groups, " .. #sc.hn .. " Henchmen groups")
    local does = {}
    if #st.mms > 1 then does[#does + 1] = "Second Mastermind (" .. table.concat(st.mms, ", ", 2) .. ") goes above the Scheme slot." end
    if sc.vd then does[#does + 1] = "Into the Villain Deck: " .. table.concat(sc.vd, ", ") .. " (whole Hero deck)." end
    if sc.ko then does[#does + 1] = "To the KO pile: " .. table.concat(sc.ko, ", ") .. "." end
    if sc.hd then
        local p = {}
        for k, n in ipairs(sc.hd) do p[#p + 1] = n .. " x" .. sc.hdn[k] end
        does[#does + 1] = "Into the Hero Deck: " .. table.concat(p, ", ") .. "."
    end
    if sc.cv then
        local p = {}
        for _, c in pairs(sc.cv) do p[#p + 1] = c.n end
        does[#does + 1] = "Villain group built from single cards: " .. table.concat(p, ", ") .. "."
    end
    if sc.vm then does[#does + 1] = "Villain Mat scenario: set up as normal, play is the same." end
    if #does > 0 then row("Set up also", esc(table.concat(does, " ")), table.concat(does, " ")) end
    if sc.nt ~= nil and sc.nt ~= "" then row("Notes", esc(sc.nt), sc.nt) end
    local total = 0
    local heights = {}
    for k, r in ipairs(rows) do
        heights[k] = refHeight(r[3], 13) + 4
        total = total + heights[k]
    end
    add('<TableLayout columnWidths="86 0" cellBackgroundColor="rgba(1,1,1,0.05)" cellPadding="6 6 3 3" cellSpacing="2" autoCalculateHeight="true" preferredHeight="' .. (total + 2 * #rows) .. '">')
    for k, r in ipairs(rows) do
        add('<Row preferredHeight="' .. heights[k] .. '">')
        add('<Cell><Text class="lbl" fontSize="13" alignment="UpperLeft">' .. r[1] .. '</Text></Cell>')
        add('<Cell><Text fontSize="13" color="#FFFFFF" alignment="UpperLeft">' .. r[2] .. '</Text></Cell>')
        add('</Row>')
    end
    add('</TableLayout>')
    if #st.missing > 0 then
        add('<Text preferredHeight="4"> </Text>')
        line("Missing now: " .. table.concat(st.missing, "; "), "#F2E3A0", 12)
    end
end

function scnPanelXml(add)
    if not SB.open then
        add('<Panel id="scnPanel" active="false"></Panel>')
        return
    end
    if SB.list == nil then scnFilter() end
    local total = #SB.list
    local pages = math.max(1, math.ceil(total / SB_PAGE))
    add('<Panel id="scnPanel" active="true" rectAlignment="UpperRight" offsetXY="-10 -210" width="800" height="628" color="rgba(0.08,0.09,0.14,0.98)">')
    add('<HorizontalLayout padding="12 12 10 10" spacing="10" childForceExpandWidth="false" childForceExpandHeight="true">')
    add('<VerticalLayout preferredWidth="350" spacing="5" childForceExpandHeight="false" childAlignment="UpperLeft">')
    add('<Text fontSize="20" fontStyle="Bold" color="#FFFFFF" alignment="MiddleLeft" preferredHeight="28">Scenarios (' .. total .. ' of ' .. #SCN .. ')</Text>')
    add('<HorizontalLayout spacing="5" preferredHeight="30" childForceExpandWidth="false" childForceExpandHeight="true">')
    add('<InputField id="scnQ" text="' .. esc(SB.q) .. '" placeholder="Search title, hero, villain" onValueChanged="onScnQLive" onEndEdit="onScnQuery" fontSize="13" preferredWidth="270"/>')
    add('<Button id="scnFind" onClick="onScnQuery" preferredWidth="66">Find</Button>')
    add('</HorizontalLayout>')
    local eo = {'<Option' .. ((SB.era == 0) and ' selected="true"' or '') .. '>All eras</Option>'}
    for k, e in ipairs(SCN_ERAS) do eo[#eo + 1] = '<Option' .. ((SB.era == k) and ' selected="true"' or '') .. '>' .. esc(e) .. '</Option>' end
    add('<Dropdown id="scnEra" onValueChanged="onScnEra" preferredHeight="28" dropdownHeight="260" itemHeight="24">' .. table.concat(eo) .. '</Dropdown>')
    add('<HorizontalLayout spacing="6" preferredHeight="28" childForceExpandHeight="true">')
    add('<ToggleButton id="scnSolo" isOn="' .. tostring(SB.solo) .. '" onValueChanged="onScnSolo" fontSize="13" colors="#E1E1E1|#FFFFFF|#C8C8C8|#808080" tooltip="Only scenarios written for one player">Solo only</ToggleButton>')
    add('<ToggleButton id="scnReady" isOn="' .. tostring(SB.ready) .. '" onValueChanged="onScnReady" fontSize="13" colors="#E1E1E1|#FFFFFF|#C8C8C8|#808080" tooltip="Only scenarios whose cards are in the pools right now">Ready now</ToggleButton>')
    add('</HorizontalLayout>')
    local first = (SB.page - 1) * SB_PAGE + 1
    for k = first, math.min(total, first + SB_PAGE - 1) do
        local i = SB.list[k]
        local sc = SCN[i]
        local st = scnStatus(i)
        local label = sc.t .. "\n" .. (sc.so and "Solo  |  " or "") .. sc.mm .. "  /  " .. sc.sc
        add('<Button id="scnRow_' .. i .. '" onClick="onScnPick" fontSize="12" preferredHeight="44"' .. scnStateColor(st.state, SB.sel == i) .. '>' .. esc(label) .. '</Button>')
    end
    if total == 0 then
        add('<Text fontSize="13" color="#E8D9A0" alignment="UpperLeft" preferredHeight="60">No scenario matches. Clear the search or switch a filter off.</Text>')
    end
    add('<HorizontalLayout spacing="5" preferredHeight="30" childForceExpandHeight="true">')
    add('<Button id="scnPrev10" onClick="onScnPage" preferredWidth="40" tooltip="Back 10 pages">&lt;&lt;</Button>')
    add('<Button id="scnPrev" onClick="onScnPage" preferredWidth="40">&lt;</Button>')
    add('<Text fontSize="13" color="#B9C2DA" alignment="MiddleCenter">Page ' .. SB.page .. ' / ' .. pages .. '</Text>')
    add('<Button id="scnNext" onClick="onScnPage" preferredWidth="40">&gt;</Button>')
    add('<Button id="scnNext10" onClick="onScnPage" preferredWidth="40" tooltip="Forward 10 pages">&gt;&gt;</Button>')
    add('</HorizontalLayout>')
    add('<Text fontSize="11" color="#B9C2DA" alignment="UpperLeft" preferredHeight="30">Green row: chosen. Yellow: needs an expansion that is off. Red: a card is not in this library.</Text>')
    add('</VerticalLayout>')
    add('<VerticalLayout preferredWidth="430" spacing="6" childForceExpandHeight="false" childAlignment="UpperLeft">')
    add('<VerticalScrollView preferredHeight="508" scrollSensitivity="20" color="rgba(0,0,0,0.25)">')
    add('<VerticalLayout padding="8 8 6 6" spacing="5" childForceExpandHeight="false">')
    if SB.sel ~= nil then
        scnDetailXml(add, SB.sel)
    elseif SB.audit ~= nil then
        for _, l in ipairs(splitLines(SB.audit)) do
            add('<Text fontSize="12" color="#FFFFFF" alignment="UpperLeft" verticalOverflow="Overflow" preferredHeight="' .. refHeight(l, 12) .. '">' .. esc(l) .. '</Text>')
        end
    else
        add('<Text fontSize="14" color="#B9C2DA" alignment="UpperLeft" preferredHeight="120">Pick a scenario on the left to read it. Set up draws its Mastermind, Scheme, Villain groups, Henchmen and Heroes, switching on any expansion it needs.</Text>')
    end
    add('</VerticalLayout>')
    add('</VerticalScrollView>')
    add('<HorizontalLayout spacing="6" preferredHeight="36" childForceExpandHeight="true">')
    add('<Button id="scnGo" onClick="onScnSetup" colors="#7CC576|#9BE093|#5FA35A|#C8C8C8">Set up scenario</Button>')
    if SB.blocked then add('<Button id="scnGoAny" onClick="onScnSetup" colors="#E8B4B4|#FFD0D0|#C98F8F|#C8C8C8">Set up anyway</Button>') end
    add('<Button id="scnText" onClick="onScnText">Card text</Button>')
    add('</HorizontalLayout>')
    add('<HorizontalLayout spacing="6" preferredHeight="30" childForceExpandHeight="true">')
    add('<Button id="scnRandom" onClick="onScnRandom" tooltip="Pick a random scenario from the current list that is ready now">Random ready</Button>')
    add('<Button id="scnAudit" onClick="onScnAudit" tooltip="Count which scenarios the pools can run and which sets to add">Library audit</Button>')
    add('<Button id="scnClose" onClick="onScnClose">Close</Button>')
    add('</HorizontalLayout>')
    add('<Text id="scnMsg" fontSize="12" color="#FFFFFF" alignment="UpperLeft" preferredHeight="46">' .. esc(SB.msg) .. '</Text>')
    add('</VerticalLayout>')
    add('</HorizontalLayout>')
    add('</Panel>')
end

--[[ ---- events ---- --]]
function onScnOpen()
    uiTab("scenarios")
end

function onScnClose()
    uiTab(nil)
end

function onScnQLive(player, value, id)
    SB.q = tostring(value or "")
end

function onScnQuery(player, value, id)
    if value ~= nil and id == "scnQ" then SB.q = tostring(value) end
    SB.page = 1
    SB.list = nil
    rebuildUILite()
end

function onScnEra(player, value, id)
    SB.era = 0
    for k, e in ipairs(SCN_ERAS) do
        if e == value then SB.era = k end
    end
    SB.page = 1
    SB.list = nil
    rebuildUILite()
end

function onScnSolo(player, value, id)
    SB.solo = (tostring(value) == "True" or tostring(value) == "true")
    SB.page = 1
    SB.list = nil
    rebuildUILite()
end

function onScnReady(player, value, id)
    SB.ready = (tostring(value) == "True" or tostring(value) == "true")
    SB.page = 1
    SB.list = nil
    rebuildUILite()
end

function onScnPage(player, value, id)
    local step = {scnPrev10 = -10, scnPrev = -1, scnNext = 1, scnNext10 = 10}
    SB.page = SB.page + (step[id] or 1)
    local pages = math.max(1, math.ceil(#(SB.list or {}) / SB_PAGE))
    if SB.page < 1 then SB.page = 1 end
    if SB.page > pages then SB.page = pages end
    rebuildUILite()
end

function onScnRandom(player, value, id)
    if SB.list == nil then scnFilter() end
    local ready = {}
    for k, i in ipairs(SB.list) do
        if scnStatus(i).state == "ok" then ready[#ready + 1] = k end
    end
    if #ready == 0 then
        SB.msg = "No scenario in this list is ready right now."
        rebuildUILite()
        return
    end
    local k = ready[math.random(#ready)]
    SB.sel = SB.list[k]
    SB.page = math.ceil(k / SB_PAGE)
    SB.blocked = false
    SB.msg = "Random pick: " .. SCN[SB.sel].t
    rebuildUILite()
end

function onScnPick(player, value, id)
    local i = tonumber(string.sub(id or "", 8))
    if i == nil or SCN[i] == nil then return end
    SB.sel = i
    SB.blocked = false
    SB.msg = ""
    rebuildUILite()
end

function onScnText(player, value, id)
    if SB.sel == nil then return end
    local st = scnStatus(SB.sel)
    local sc = SCN[SB.sel]
    MENU.refTab = "schemes"
    MENU.refPick.schemes = (st.scheme ~= nil and refEntry("schemes", st.scheme) ~= nil) and refEntry("schemes", st.scheme).n or (refEntry("schemes", sc.sc) and refEntry("schemes", sc.sc).n or MENU.refPick.schemes)
    uiTab("reference")
end

function onScnSetup(player, value, id)
    if SB.sel == nil then
        SB.msg = "Pick a scenario first."
        rebuildUILite()
        return
    end
    if SB.running then
        SB.msg = "Still working on the last request."
        rebuildUILite()
        return
    end
    SB.anyway = (id == "scnGoAny")
    startLuaCoroutine(Global, "scnSetupRun")
end

function scnSetupRun()
    local i = SB.sel
    local sc = SCN[i]
    SB.running = true
    local function stop(msg)
        SB.msg = msg
        SB.running = false
        print(msg)
        rebuildUILite()
        return 1
    end
    syncPlayers()
    if gameInProgress() then return stop("A game is already set up. Run Automatic Cleanup first.") end
    if sc.cu then return stop("This scenario builds its Villain Deck from individual cards. Assemble it by hand.") end
    SB.pool = nil
    local st = scnStatus(i)
    local added = 0
    for xi, _ in pairs(st.needExp) do
        if not MENU.state[xi] then
            local ex = EXPANSIONS[xi]
            local bag = getObjectFromGUID(ex.guid)
            if bag ~= nil then
                print("Scenario needs " .. ex.name .. ": adding it to the pools")
                bag.call("unpack")
                for k = 1, 90 do coroutine.yield(0) end
                added = added + 1
            end
        end
    end
    if added > 0 then
        SB.pool = nil
        refreshExpansionState()
        st = scnStatus(i)
    end
    if st.state ~= "ok" and not SB.anyway then
        SB.blocked = true
        return stop("Not everything is in the library: " .. table.concat(st.missing, "; ") .. ". Press Set up anyway to fill the gaps at random.")
    end
    local more = {}
    for k = 2, #st.mms do more[#more + 1] = st.mms[k] end
    MENU.force = {heroes = st.real.heroes, villains = st.real.villains, henchmen = st.real.henchmen, taken = {heroes = {}, villains = {}, henchmen = {}},
                  extra = {heroes = st.nunres.heroes, villains = st.nunres.villains, henchmen = st.nunres.henchmen},
                  composites = st.comp, vdeck = st.vdeck, ko = st.ko, herodeck = st.hd, extraMM = more}
    MENU.mastermind = st.mm or "Random"
    MENU.scheme = st.scheme or "Random"
    local n = scnPlayers(sc)
    local c = getObjectFromGUID("1a65aa")
    if c ~= nil then c.setValue(n) end
    MENU.players = n
    MENU.advanced = false
    MENU.log = {}
    MENU.drawn = {}
    MENU.open = false
    SB.open = false
    SB.blocked = false
    SB.msg = ""
    SB.running = false
    print("Scenario: " .. sc.t .. " (" .. n .. " player" .. (n == 1 and "" or "s") .. ")")
    if sc.vm then print("This scenario uses the Villain Mat: play is the same, nothing extra to set up.") end
    if sc.nt ~= nil and sc.nt ~= "" and sc.nt ~= "Solo" then print("Scenario notes: " .. sc.nt) end
    rebuildUI()
    setupWrapper()
    return 1
end

function onScnAudit(player, value, id)
    SB.pool = nil
    local counts = {ok = 0, exp = 0, miss = 0, manual = 0}
    local unk = {masterminds = {}, schemes = {}, heroes = {}, villains = {}, henchmen = {}}
    local need, allSets, nExcl = {}, {}, 0
    for i, sc in ipairs(SCN) do
        local st = scnStatus(i)
        counts[st.state] = counts[st.state] + 1
        local sets, clean, excl = {}, true, false
        for _, m in ipairs(st.miss) do
            if m.xi > 0 then
                -- an expansion that is in the mod but switched off: not a gap
            elseif m.set ~= nil and XEXC[m.set] then
                excl = true
            elseif m.set ~= nil then
                sets[m.set] = true
                allSets[m.set] = true
            else
                clean = false
                unk[m.kind][m.name] = (unk[m.kind][m.name] or 0) + 1
            end
        end
        if st.state == "miss" and excl then nExcl = nExcl + 1 elseif st.state == "miss" and clean then need[#need + 1] = sets end
    end
    local out = {"Library audit (" .. #SCN .. " scenarios)",
                 "Ready now: " .. counts.ok .. "   Need an expansion switched on: " .. counts.exp .. "   Not possible with this mod: " .. counts.miss .. " (of which " .. nExcl .. " need an excluded MCU / What If set)   Built by hand: " .. counts.manual}
    --[[Which sets to add to the mod, best first: each pick is the set that completes the most remaining scenarios--]]
    out[#out + 1] = "Sets that would unlock the most scenarios if you added them to the mod (cumulative):"
    local chosen, done, total = {}, {}, 0
    for round = 1, 10 do
        local best, bestN = nil, 0
        for s, _ in pairs(allSets) do
            if not chosen[s] then
                local n = 0
                for k, sets in ipairs(need) do
                    if not done[k] then
                        local fits = true
                        for x, _ in pairs(sets) do
                            if x ~= s and not chosen[x] then fits = false break end
                        end
                        if fits then n = n + 1 end
                    end
                end
                if n > bestN then best, bestN = s, n end
            end
        end
        if best == nil then break end
        chosen[best] = true
        for k, sets in ipairs(need) do
            if not done[k] then
                local fits = true
                for x, _ in pairs(sets) do
                    if not chosen[x] then fits = false break end
                end
                if fits then done[k] = true end
            end
        end
        total = total + bestN
        out[#out + 1] = round .. ". " .. best .. "  +" .. bestN .. "  (" .. total .. " in all)"
    end
    local unresolved = 0
    for _, kind in ipairs({"heroes", "villains", "henchmen", "masterminds", "schemes"}) do
        for _ in pairs(unk[kind]) do unresolved = unresolved + 1 end
    end
    out[#out + 1] = "Names in the scenarios that match neither this mod nor the card catalog (" .. unresolved .. "), most used first:"
    for _, kind in ipairs({"heroes", "villains", "henchmen", "masterminds", "schemes"}) do
        local list = {}
        for name, n in pairs(unk[kind]) do list[#list + 1] = {name, n} end
        table.sort(list, function(a, b) if a[2] ~= b[2] then return a[2] > b[2] end return a[1] < b[1] end)
        local parts = {}
        for k = 1, math.min(#list, 25) do parts[#parts + 1] = list[k][1] .. " (" .. list[k][2] .. ")" end
        if #list > 0 then out[#out + 1] = string.upper(kind) .. ": " .. table.concat(parts, ", ") end
    end
    SB.audit = table.concat(out, "\n")
    SB.sel = nil
    SB.msg = "Audit done."
    print(out[2])
    rebuildUILite()
end

--[[ ---- scenario extras inside setup() ---- --]]
function scnFindGuid(bag, name)
    for _, e in ipairs(bag.getObjects()) do
        if e.name == name then return e.guid end
    end
    return nil
end

function scnPlaceExtraMasterminds(mastermindsBag)
    local f = MENU.force
    if f == nil or f.extraMM == nil then return end
    for k, nm in ipairs(f.extraMM) do
        local m = pickFromContainer(mastermindsBag, nm, {position = {SLOTS.mm2.x + 3.2 * (k - 1), 2, SLOTS.mm2.z}, rotation = {0, 180, 0}, smooth = false})
        coroutine.yield(0)
        say("Second Mastermind: ", m.getName())
    end
end

function scnBuildComposite(villainDeck, villainsBag, c)
    for _, part in ipairs(c.parts) do
        local gid = scnFindGuid(villainsBag, part.group)
        if gid == nil then
            say("Scenario: " .. part.group .. " is not in the pool any more, its cards for " .. c.name .. " are skipped.")
        else
            local g = villainsBag.takeObject({guid = gid, position = {0, 3, 0}, smooth = false})
            coroutine.yield(0)
            for _, card in ipairs(part.cards) do
                local want, got, nk = card[2], 0, scnNorm(card[1])
                for _, e in ipairs(g.getObjects()) do
                    if got < want and scnNorm(e.name) == nk then
                        g.takeObject({guid = e.guid, position = {0, 4, 0}, smooth = false})
                        coroutine.yield(0)
                        villainDeck.putObject(getObjectFromGUID(e.guid))
                        got = got + 1
                    end
                end
                if got < want then say("Scenario: " .. card[1] .. " (" .. part.group .. ") x" .. want .. ": only " .. got .. " found.") end
            end
            local ok = pcall(function() villainsBag.putObject(g) end)
            if not ok then say("Scenario: " .. part.group .. " had no cards left to return.") end
        end
    end
    say("Villain group built from single cards: " .. c.name)
end

function scnHeroDeckExtras(heroDeck, henchmenBag)
    local f = MENU.force
    if f == nil or f.herodeck == nil then return end
    for _, e in ipairs(f.herodeck) do
        local gid = scnFindGuid(henchmenBag, e.name)
        if gid == nil then
            say("Scenario: " .. e.name .. " is not in the Henchmen pool; add " .. e.n .. " to the Hero Deck by hand.")
        else
            local d = henchmenBag.takeObject({guid = gid, position = {0, 3, 0}, smooth = false})
            coroutine.yield(0)
            local part = d
            if d.getQuantity() > e.n then
                local cut = d.cut(e.n)
                coroutine.yield(0)
                part = cut[2]
                henchmenBag.putObject(cut[1])
                coroutine.yield(0)
            end
            heroDeck.putObject(part)
            coroutine.yield(0)
            say("Scenario: " .. e.n .. " " .. e.name .. " cards shuffled into the Hero Deck.")
        end
    end
end

function scnVillainDeckExtras(villainDeck, heroesBag, villainsBag, henchmenBag, mastermindsBag)
    local f = MENU.force
    if f == nil then return end
    scnPlaceExtraMasterminds(mastermindsBag)
    for _, c in ipairs(f.composites or {}) do scnBuildComposite(villainDeck, villainsBag, c) end
    for _, nm in ipairs(f.vdeck or {}) do
        local have = false
        for _, e in ipairs(villainDeck.getObjects()) do
            for _, tg in ipairs(e.tags or {}) do
                if tg == nm then have = true end
            end
        end
        if have then
            say("Scenario: " .. nm .. " is already in the Villain Deck (the Scheme put it there).")
        else
            local gid = scnFindGuid(heroesBag, nm)
            if gid == nil then
                say("Scenario: Hero " .. nm .. " is not in the pool; put it in the Villain Deck by hand.")
            else
                local d = heroesBag.takeObject({guid = gid, position = {0, 3, 0}, smooth = false})
                coroutine.yield(0)
                villainDeck.putObject(d)
                coroutine.yield(0)
                say("Scenario: " .. nm .. " shuffled into the Villain Deck.")
            end
        end
    end
    for _, k in ipairs(f.ko or {}) do
        local gid = scnFindGuid(henchmenBag, k.name)
        if gid == nil then
            say("Scenario: " .. k.name .. " is not in the Henchmen pool; put it in the KO pile by hand.")
        else
            local d = henchmenBag.takeObject({guid = gid, position = {SLOTS.ko.x, 2.5, SLOTS.ko.z}, rotation = {0, 180, 0}, smooth = false})
            coroutine.yield(0)
            d.setName(k.label)
            say("Scenario: " .. k.name .. " is in the KO pile as " .. k.label .. ".")
        end
    end
end

--[[ ---- setup() hooks: draw the listed names first, then fall back to random ---- --]]
function forcedPick(kind, bag)
    local f = MENU.force
    if f == nil or f[kind] == nil then return nil end
    local have = {}
    for _, e in ipairs(bag.getObjects()) do
        if have[e.name] == nil then have[e.name] = e.guid end
    end
    for _, n in ipairs(f[kind]) do
        if have[n] ~= nil and not f.taken[kind][n] then return have[n], n end
    end
    return nil
end

function forcedTake(kind, bag, params)
    params = params or {}
    local guid, n = forcedPick(kind, bag)
    if guid ~= nil then
        params.guid = guid
        MENU.force.taken[kind][n] = true
        return bag.takeObject(params)
    end
    if MENU.force ~= nil then
        if (MENU.force.extra[kind] or 0) > 0 then MENU.force.extra[kind] = MENU.force.extra[kind] - 1 end
        say("Scenario: no listed " .. kind .. " left in the pool, drawing at random.")
        bag.shuffle()
    end
    return bag.takeObject(params)
end

--[[How many more to draw: the listed names still in the bag plus those that could not be matched--]]
function forcedCount(kind, bag, default)
    local f = MENU.force
    if f == nil or f[kind] == nil then return default end
    local have = {}
    for _, e in ipairs(bag.getObjects()) do have[e.name] = true end
    local n = f.extra[kind] or 0
    for _, name in ipairs(f[kind]) do
        if have[name] and not f.taken[kind][name] then n = n + 1 end
    end
    return n
end
'''
