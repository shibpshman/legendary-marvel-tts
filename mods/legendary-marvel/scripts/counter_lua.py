"""Evil Wins tracker: live counters read from scripting zones over the KO and Escape slots and from the decks,
a table of what each scheme's "Evil Wins" needs, snap points on every slot, and the Lua that drives them."""
import json

# ----------------------------------------------------------------------------------------------------------------
# kinds:  twist  = Scheme Twists played so far (Villain Deck started with N; played = N - still in the deck)
#         escv   = Villain/Henchman cards in the Escape zone      escb = Bystanders in the Escape zone
#         kb     = Bystanders in the KO zone + Escape zone        escall = every card in the Escape zone
#         kong   = non-grey Heroes (Hero tag + a class tag) in the KO zone
#         herodeck / wounds / villaindeck = cards left in that deck (Evil wins at 0)
#         manual = counted by hand with the + / - buttons
#                  counts_down=True, start=N: starts at N and goes down; Evil wins when it reaches the target (0)
# target: n = fixed number, pp = per player, plus = players + k
# ----------------------------------------------------------------------------------------------------------------
def T(n): return dict(k='twist', l='Scheme Twist #%d (Evil wins)' % n, n=n)
def ESC(**kw): return dict(k='escv', l='Escaped Villains', **kw)
def KO(**kw): return dict(k='kong', l='non-grey Heroes in the KO pile', **kw)
def M(label, counts_down=False, **kw):
    r = dict(k='manual', l=label, **kw)
    if counts_down:
        assert r.get('start', 0) > r.get('n', 0), 'a counts_down rule needs start above its target, or it would fire at setup: %r' % label
        r['cd'] = 1
    return r
HERO = dict(k='herodeck', l='Hero Deck', n=0)
WOUND = dict(k='wounds', l='Wound Stack', n=0)
VILL = dict(k='villaindeck', l='Villain Deck', n=0)

RULES = {
    # Twist-number endings
    'Portals To The Dark Dimension': [T(7)], 'Unleash The Power Of The Cosmic Cube': [T(8)], 'Invincible Force Field': [T(7)],
    'Pull Reality Into The Negative Zone': [T(7)], 'Weave A Web Of Lies': [T(7)], 'Dark Alliance': [T(7)], 'Secret Wars': [T(8)],
    'The God-Emperor Of Battleworld': [T(8)], 'The Unbreakable Enigma Code': [T(6)], 'Avengers VS. X-Men': [T(8)],
    'Horror Of Horrors': [T(6)], 'Mutating Gamma Rays': [T(7)], 'World War Hulk': [T(9)], 'Paralyzing Venom': [T(6)],
    'Symbiotic Absorption': [T(11)], 'Hail Hydra': [T(10)], 'Tornado of Terrigen Mists': [T(10)],
    # Escaped Villains
    'Negative Zone Prison Breakout': [ESC(n=12)], 'Smash Two Dimensions Together': [ESC(n=10)],
    'Deadlands Hordes Charge The Wall': [ESC(plus=6)], 'The Fountain Of Eternal Life': [ESC(pp=3)],
    'Master The Mysteries Of Kung-Fu': [ESC(pp=2)], 'Everybody Hates Deadpool': [ESC(pp=3)], 'Alien Brood Encounters': [ESC(pp=3)],
    'Pull Earth Into Medieval Times': [ESC(pp=3)], 'Predict Future Crime': [ESC(pp=2)], 'Hypnotize Every Human': [ESC(n=8)],
    'Superhuman Baseball Game': [ESC(pp=4)],
    'Five Families Of Crime': [ESC(n=8), VILL], 'Gladiator Pits Of Sakaar': [ESC(pp=2), VILL], 'Trap Heroes In The Microverse': [ESC(pp=3), VILL],
    'Earthquake Drains The Ocean': [ESC(pp=3), VILL], 'Devolve with Xerogen Crystals': [ESC(pp=3), VILL],
    'Invasion Of The Venom Symbiotes': [dict(k='escall', l='cards in the Escape Pile', pp=3), VILL],
    'Splice Humans With Spider DNA': [M('Sinister Six Villains escaped', n=6), VILL],
    'The Clone Saga': [M('Villains with the same card name escaped (need 2)', n=2), VILL],
    # non-grey Heroes in the KO pile
    'Massive Earthquake Generator': [KO(pp=3)], 'Bathe Earth In Cosmic Rays': [KO(pp=6)], 'Flood The Planet With Melted Glaciers': [KO(n=20)],
    'Intergalactic Kree Nega-Bomb': [KO(n=16)], 'Fragmented Realities': [KO(pp=5)], 'Steal All Oxygen On Earth': [KO(n=20)],
    'Break The Planet Asunder': [KO(n=25)], 'Hydra Helicarriers Hunt Heroes': [KO(n=18)],
    "X-Cutioner's Song": [M("non-grey Heroes KO'd or carried off", n=9)],
    # Bystanders
    'Midtown Bank Robbery': [dict(k='escb', l='Bystanders carried away', n=8)],
    'Save Humanity': [dict(k='kb', l="Bystanders KO'd and/or carried off", pp=4)],
    'Imprison Unregistered Superhumans': [dict(k='kb', l='Bystanders in the KO pile and/or Escape Pile', n=3)],
    'Silence The Witnesses': [dict(k='escb', l='Bystanders in the Escape Pile', n=6)],
    'Maximum Carnage': [dict(k='escb', l='Bystanders in the Escape Pile', n=6), WOUND],
    'Cytoplasm Spike Invasion': [M('Bystanders and Spikes in the KO pile and Escape Pile', n=18)],
    # decks running out
    'Super Hero Civil War': [HERO], 'Epic Super Hero Civil War': [HERO], 'Deadpool Kills The Marvel Universe': [HERO],
    "Go Back In Time To Slay Heroes' Ancestors": [HERO], 'Detonate The Helicarrier': [HERO, M('HQ spaces Destroyed', n=5)],
    'The Legacy Virus': [WOUND], 'Pan-Dimensional Plague': [WOUND], 'Fall Of The Hulks': [WOUND], 'Anti-Mutant Hatred': [WOUND, VILL],
    'Clash Of The Monsters Unleashed': [WOUND, M('Monster Pit cards left', n=0, start=8, counts_down=True)],
    # counted next to the scheme / mastermind or in the city: manual +/-
    'Organized Crime Wave': [M('Goons escaped', n=5)], "Replace Earth's Leaders With Killbots": [M('Killbots escaped', n=5)],
    'Secret Invasion Of The Skrull Shapeshifters': [M('Heroes in the Escaped Villains pile', n=6)],
    'Steal The Weaponized Plutonium': [M('Plutonium carried off', n=4)], 'Capture Baby Hope': [M('Twists next to the Mastermind', n=3)],
    'Transform Citizens Into Demons': [M('Goblin Queen cards escaped', n=4)], 'Invade The Daily Bugle News HQ': [M('Villains in the HQ', n=5)],
    'The Kree-Skrull War': [M('Kree Conquests', n=4), M('Skrull Conquests', n=4)],
    'Forge The Infinity Gauntlet': [M('Infinity Gem Villains in the city and/or Escape Pile', n=6), M('Infinity Gem Artifacts one player controls', n=4)],
    'Unite The Shards': [M('Shards on the Mastermind', n=10)], 'Master Of Tyrants': [M('Tyrant Villains escaped', n=5)],
    'Corrupt The Next Generation Of Heroes': [M('Sidekicks escaped', n=4)], 'Build An Army Of Annihilation': [M('Annihilation Henchmen next to the Mastermind', n=10)],
    'Crush Them With My Bare Hands': [M('Master Strikes that took effect', n=8)], 'Sinister Ambitions': [M('Ambition Villains escaped', n=4)],
    'The Mark Of Khonshu': [M('Khonshu Guardians escaped', n=7)], 'Enthrone The Barons Of Battleworld': [M('Masterminds in play', n=6)],
    'Deadpool Wants A Chimichanga': [M('Chimichangas in the Escape Pile', n=6)], 'Change The Outcome Of WWII': [M('Capitals conquered', n=3)],
    'Brainwash The Military': [M('S.H.I.E.L.D. Officers escaped', n=5)], "Reveal Heroes' Secret Identities": [M('Heroes Unmasked', n=5)],
    'United States Split By Civil War': [M('Western Victories', n=3), M('Eastern Victories', n=3)],
    'Dark Reign Of H.A.M.M.E.R. Officers': [M('Officers next to the Mastermind', n=7)], 'Hidden Heart Of Darkness': [M('Tactics escaped', n=2)],
    'X-Men Danger Room Goes Beserk': [M('Airborne Neurotoxins', n=5)], 'The Dark Phoenix Saga': [M('Jean Grey cards escaped', n=5)],
    'Mutant-Hunting Super Sentinels': [M('Sentinels escaped', n=3)], 'Nuclear Armageddon': [M('City spaces destroyed', n=5)],
    'Subjugate With Obedience Disks': [M('HQ spaces with 2 Obedience Disks', n=5)],
    'Shoot Hulk Into Space': [M('cards in the Prison Ship', n=10), M('Hulk Deck cards left', n=0, start=14, counts_down=True)],
    'Age Of Ultron': [M('Evolved Ultrons in the city and/or Escape Pile', n=7)], 'Transform Commuters Into Giant Ants': [M('Giant Ants next to the Mastermind', n=10)],
    'SHIELD vs Hydra War': [M('Hydra Level', n=11)], 'Secret Empire Of Betrayal': [M('Vicious Betrayals next to the Scheme', n=6)],
    'War Of The Frost Giants': [M('Frost Giant Invaders in the city and/or Escape Pile', n=5)],
    'The Dark World Of Svartalfheim': [M('city spaces covered in Eternal Darkness (or 5 HQ spaces)', n=5)],
    'Ragnarok, Twilight Of The Gods': [M('Guardians Defeated', n=5)], 'Asgardian Test Of Worth': [M('Moral Failings', n=5)],
    'Crash The Moon Into The Sun': [M('Altered Orbits', n=4)], 'Trapped In The Insane Asylum': [M("Psychotic Breaks on one player", n=3)],
    'The Demon Bear Saga': [M('Dream Horrors', n=3)], 'Annihilation: Conquest': [M('Phalanx-Infected in the city and/or Escape Pile', n=6), VILL],
    'The Contest Of Champions': [M('Evil Triumphs', n=6)], 'Destroy The Nova Corps': [M("KO'd Nova Centurions", pp=5)],
    'Turn The Soul Of Adam Warlock': [M("Soul's Corruptions", n=8)], 'Ruin the Perfect Wedding': [M("Wedding Hero Stacks KO'd (either one)", n=1)],
    'War of Kings': [M('Victorious Generals', n=6)], 'Divide And Conquer': [M('Hero Decks gone', n=5)],
}
RULES = {k: v for k, v in RULES.items() if v}


def _lua_rule(t):
    parts = ['k="%s"' % t['k'], 'l="%s"' % t['l'].replace('"', "'")]
    for key in ('n', 'pp', 'plus', 'start', 'cd'):
        if key in t: parts.append('%s=%d' % (key, t[key]))
    return '{' + ','.join(parts) + '}'


def rules_lua():
    return '{\n' + ',\n'.join('["%s"] = {%s}' % (k.replace('"', '\\"'), ','.join(_lua_rule(t) for t in v)) for k, v in sorted(RULES.items())) + '}'


COUNTER_LUA = r'''
--[[ ===== Evil Wins tracker: zones, counters, snap points (generated by the save builder) ===== --]]
CTR_RULES = __CTR_RULES__
CTR = {zones = {}, adj = {}, fired = {}, twistTotal = nil, loop = false, list = {}}
CLASS_TAGS = {"Strength", "Instinct", "Covert", "Tech", "Ranged"}

function newTally() return {cards = 0, hero = 0, herong = 0, villain = 0, bystander = 0, wound = 0, twist = 0, strike = 0, officer = 0} end

function tallyOne(t, name, tags)
    t.cards = t.cards + 1
    local isHero, isClass = false, false
    for _, g in ipairs(tags or {}) do
        if g == "Hero" then isHero = true end
        if g == "Villain" or g == "Henchman" then t.villain = t.villain + 1 end
        if g == "Bystander" then t.bystander = t.bystander + 1 end
        if g == "Wound" then t.wound = t.wound + 1 end
        if g == "SHIELD Officer" then t.officer = t.officer + 1 end
        for _, c in ipairs(CLASS_TAGS) do if g == c then isClass = true end end
    end
    if isHero then t.hero = t.hero + 1 end
    if isHero and isClass then t.herong = t.herong + 1 end
    if name == "Scheme Twist" then t.twist = t.twist + 1 end
    if name == "Master Strike" then t.strike = t.strike + 1 end
end

function tallyObject(t, o)
    local ok, kind = pcall(function() return o.type end)
    if not ok then return end
    if kind == "Deck" then
        local ok2, entries = pcall(function() return o.getObjects() end)
        if ok2 and entries ~= nil then
            for _, e in ipairs(entries) do tallyOne(t, e.name, e.tags) end
        end
    elseif kind == "Card" then
        local okn, n = pcall(function() return o.getName() end)
        local okt, tg = pcall(function() return o.getTags() end)
        tallyOne(t, okn and n or "", okt and tg or {})
    end
end

function zoneTally(zone)
    if zone == nil then return nil end
    local ok, objs = pcall(function() return zone.getObjects() end)
    if not ok or objs == nil then return nil end
    local t = newTally()
    for _, o in ipairs(objs) do tallyObject(t, o) end
    return t
end

function findDeckByName(name)
    for _, o in ipairs(getObjects()) do
        local ok, kind = pcall(function() return o.type end)
        if ok and kind == "Deck" then
            local okn, n = pcall(function() return o.getName() end)
            if okn and n == name then return o end
        end
    end
    return nil
end

function deckTally(name)
    local d = findDeckByName(name)
    if d == nil then return nil end
    local t = newTally()
    tallyObject(t, d)
    return t
end

function ctrTarget(r)
    if r.n ~= nil then return r.n end
    if r.pp ~= nil then return r.pp * MENU.players end
    if r.plus ~= nil then return MENU.players + r.plus end
    return nil
end

--[[Builds the tracker list for the drawn scheme: the Twist counter first, then the rules for that scheme--]]
function ctrBuild()
    local list = {}
    local rules = CTR_RULES[MENU.drawn.scheme or ""] or {}
    local hasTwistRule = false
    for _, r in ipairs(rules) do if r.k == "twist" then hasTwistRule = true end end
    if not hasTwistRule then list[#list + 1] = {k = "twist", l = "Scheme Twists played", info = true} end
    for _, r in ipairs(rules) do list[#list + 1] = r end
    CTR.list = list
end

function ctrValue(i, r)
    local adj = CTR.adj[i] or 0
    local auto = nil
    local ko, esc = zoneTally(CTR.zones.ko), zoneTally(CTR.zones.escape)
    if r.k == "twist" then
        local vd = deckTally("Villain Deck")
        if CTR.twistTotal ~= nil and vd ~= nil then auto = math.max(0, CTR.twistTotal - vd.twist) end
    elseif r.k == "escv" and esc ~= nil then auto = esc.villain
    elseif r.k == "escb" and esc ~= nil then auto = esc.bystander
    elseif r.k == "escall" and esc ~= nil then auto = esc.cards
    elseif r.k == "kb" and ko ~= nil and esc ~= nil then auto = ko.bystander + esc.bystander
    elseif r.k == "kong" and ko ~= nil then auto = ko.herong
    elseif r.k == "herodeck" or r.k == "wounds" or r.k == "villaindeck" then
        local nm = (r.k == "herodeck") and "Hero Deck" or ((r.k == "wounds") and "Wounds" or "Villain Deck")
        local d = deckTally(nm)
        if d ~= nil then auto = d.cards end
        return auto, adj, true
    end
    return auto, adj, false
end

--[[Text for one tracker: its label, value, target; also reports whether Evil has won on it--]]
function ctrLine(i, r)
    local auto, adj, remaining = ctrValue(i, r)
    local tgt = ctrTarget(r)
    if remaining then
        if auto == nil then return r.l .. ": not found", false, 0 end
        local left = auto + adj
        return r.l .. ": " .. left .. " cards left (Evil wins at 0)", (left <= 0), (left <= 0) and 1 or 0
    end
    if r.cd == 1 then
        --[[counts down from start (cards left in a deck kept by hand): Evil wins when it reaches the target--]]
        local start = r.start or 0
        local v = start + adj
        local won = (tgt ~= nil and v <= tgt and not r.info)
        local frac = (tgt ~= nil and start > tgt) and ((start - v) / (start - tgt)) or 0
        return r.l .. ": " .. v .. " (Evil wins at " .. tostring(tgt or 0) .. ")", won, frac
    end
    local manual = (auto == nil)
    local v = (auto or 0) + adj
    local s = r.l .. ": " .. v
    if tgt ~= nil then s = s .. " / " .. tgt end
    if manual and r.k ~= "manual" and r.k ~= "twist" then s = s .. "  (set by hand: zone missing)" end
    local won = (tgt ~= nil and v >= tgt and not r.info)
    local frac = (tgt ~= nil and tgt > 0) and (v / tgt) or 0
    return s, won, frac
end

function ctrMark(frac, won)
    if won then return "!!! " end
    if frac >= 0.75 then return "(!) " end
    return ""
end

function ctrRefresh()
    if MENU.drawn.scheme == nil then
        pcall(function() UI.setAttribute("evilStrip", "active", "false") end)
        return
    end
    for i, r in ipairs(CTR.list) do
        local s, won, frac = ctrLine(i, r)
        pcall(function() UI.setValue("ctr_" .. i, ctrMark(frac, won) .. s) end)
        pcall(function() UI.setValue("ctrt_" .. i, ctrMark(frac, won) .. ctrLabel(s)) end)
        pcall(function() UI.setAttribute("ctrb_" .. i, "percentage", tostring(math.floor(math.min(1, frac) * 100))) end)
        pcall(function() UI.setAttribute("ctrb_" .. i, "fillImageColor", ctrBarColor(frac, won)) end)
        if won and not CTR.fired[i] then
            CTR.fired[i] = true
            pcall(function() broadcastToAll("EVIL WINS: " .. s, {1, 0.3, 0.3}) end)
        end
    end
    pcall(function() UI.setAttribute("evilStrip", "active", "true") end)
end

function ctrLoop()
    if CTR.loop then return end
    CTR.loop = true
    pcall(function() Wait.time(ctrRefresh, 2, -1) end)
end

function onCtrAdj(player, value, id)
    local i, d = string.match(id or "", "^ctra_(%d+)_(%a)$")
    i = tonumber(i)
    if i == nil then return end
    CTR.adj[i] = (CTR.adj[i] or 0) + ((d == "p") and 1 or -1)
    CTR.fired[i] = nil
    ctrRefresh()
end

--[[Called after setup: remembers how many Twists went into the Villain Deck and builds the tracker list--]]
function ctrAfterSetup()
    CTR.adj, CTR.fired = {}, {}
    local vd = deckTally("Villain Deck")
    CTR.twistTotal = (vd ~= nil and vd.twist > 0) and vd.twist or nil
    ctrBuild()
    ctrLoop()
    ctrRefresh()
end

function ctrReset()
    CTR.adj, CTR.fired, CTR.twistTotal, CTR.list = {}, {}, nil, {}
    pcall(function() UI.setAttribute("evilStrip", "active", "false") end)
end

--[[Zones over the KO and Escape slots, and snap points on every slot--]]
function makeZone(name)
    local s = SLOTS and SLOTS[name]
    if s == nil then return end
    pcall(function()
        spawnObject({type = "ScriptingTrigger", position = {s.x, 1.6, s.z}, scale = {3.6, 3, 4.8},
            callback_function = function(o)
                CTR.zones[name] = o
                pcall(function() o.addTag("LegCounterZone") end)
            end})
    end)
end

function initTable()
    pcall(function()
        for _, o in ipairs(getObjectsWithTag("LegCounterZone")) do destroyObject(o) end
    end)
    CTR.zones = {}
    makeZone("ko")
    makeZone("escape")
    if SLOTS ~= nil and SLOTS.escape == nil then
        print("Escape slot is not set in mat_config.py, so escape-based counters are set by hand with + and -.")
    end
    local pts = {}
    for name, s in pairs(SLOTS or {}) do
        local free = (name == "escape" or name == "adversaries")     --[[wide landscape box: cards lie sideways, so do not lock the turn--]]
        pts[#pts + 1] = {position = {s.x, 1.2, s.z}, rotation = {0, free and 270 or 180, 0}, rotation_snap = not free}
    end
    for i = 1, 5 do
        pts[#pts + 1] = {position = {CITYX[i], 1.2, CITYZ}, rotation = {0, 180, 0}, rotation_snap = true}
        pts[#pts + 1] = {position = {HQX[i], 1.2, HQZ}, rotation = {0, 180, 0}, rotation_snap = true}
    end
    --[[snap points for the Draw Deck, Victory and Discard piles of every player mat--]]
    pcall(function()
        for _, g in ipairs(PLAYER_MATS) do
            local mat = getObjectFromGUID(g)
            if mat ~= nil then
                local ry = mat.getRotation().y or 180
                for _, uv in pairs(PILES) do
                    local pt = tfMatPoint(mat, uv)
                    pts[#pts + 1] = {position = {pt.x, 1.2, pt.z}, rotation = {0, ry, 0}, rotation_snap = true}
                end
            end
        end
    end)
    pcall(function() Global.setSnapPoints(pts) end)
end
'''


def counter_lua():
    return COUNTER_LUA.replace('__CTR_RULES__', rules_lua())
