"""Offline test of the Played count (played_lua.py), run with the real Lua generated for the save, against mock TTS cards.
Needs lupa (pip install --user lupa). Usage: python test_played_lua.py [--save E:\\Documents\\My Games\\Tabletop Simulator\\Saves\\TS_Save_10.json]
Checks: plain / X+ / divided / unknown cards, an unnamed card by CardID, a stacked deck, a face-down deck, the five real starting decks, and that every
Hero card in the save's bags resolves to a printed value. It does not test TTS geometry (tfPlayedOn) or the UI; those need the game."""
import argparse, json, sys
import lupa
import played_lua

ap = argparse.ArgumentParser()
ap.add_argument('--save', default=r'E:\Documents\My Games\Tabletop Simulator\Saves\TS_Save_10.json')
a = ap.parse_args()

lua = lupa.LuaRuntime(unpack_returned_tuples=True)
lua.execute('''
function pcall_ok(f) return pcall(f) end
Wait = {time = function() end}
UI = {setValue = function() end, setAttribute = function() end}
''')
lua.execute(played_lua.played_lua())
G = lua.globals()
fails = []


def check(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + (('  ' + detail) if detail and not cond else ''))
    if not cond: fails.append(name)


def mock_card(name, tags=(), card_id=None, face_down=False):
    return lua.eval('''function(name, tags, cid, down)
        local t = {tags = tags}
        return {type = "Card", is_face_down = down, getName = function() return name end, getTags = function() return tags end,
                getData = function() return {CardID = cid} end}
    end''')(name, lua.table_from(list(tags)), card_id, face_down)


def mock_deck(entries, face_down=False):
    ents = [lua.table_from({'name': n, 'tags': lua.table_from(list(t))}) for n, t in entries]
    return lua.eval('''function(ents, down)
        return {type = "Deck", is_face_down = down, getObjects = function() return ents end}
    end''')(lua.table_from(ents), face_down)


def tally(objs):
    t = G.plTallyObjects(lua.table_from(objs))
    return dict(a=t.a, r=t.r, ap=t.ap, rp=t.rp, cards=t.cards, div=t.div, unknown=t.unknown)


data = json.load(open(played_lua.CANDIDATES[-1], encoding='utf-8'))
cards = data['cards']
plain = next(k for k, v in cards.items() if 'div' not in v and not v.get('ap') and not v.get('rp') and v.get('a') and v.get('r'))
xplus = next(k for k, v in cards.items() if v.get('ap') and 'div' not in v)
divided = next(k for k, v in cards.items() if 'div' in v)

t = tally([mock_card(plain, ['Hero'])])
check('plain card counts its printed numbers', t['a'] == cards[plain]['a'] and t['r'] == cards[plain]['r'] and t['cards'] == 1, str(t))
t = tally([mock_card(xplus, ['Hero'])])
check('X+ card is a minimum', t['ap'] is True, str(t))
t = tally([mock_card(divided, ['Hero'])])
check('divided card is flagged, not counted', t['div'] == 1 and t['a'] == 0 and t['r'] == 0, str(t))
t = tally([mock_card('Not A Real Card', ['Hero'])])
check('unknown hero card is reported', t['unknown'] == 1, str(t))
t = tally([mock_card('', [], card_id=4403)])
check('unnamed starting Agent found by CardID', t['r'] == 1 and t['unknown'] == 0, str(t))
t = tally([mock_card(plain, ['Hero'], face_down=True)])
check('face-down card is ignored', t['cards'] == 0, str(t))

# a stacked deck: the case that used to lose the count
stack = [('S.H.I.E.L.D. Agent', ['Hero'])] * 8 + [('S.H.I.E.L.D. Trooper', ['Hero'])] * 4
t = tally([mock_deck(stack)])
check('stacked deck of 8 Agents + 4 Troopers = Recruit 8, Attack 4', t['a'] == 4 and t['r'] == 8 and t['cards'] == 12 and t['unknown'] == 0, str(t))
t = tally([mock_deck(stack, face_down=True)])
check('face-down deck is ignored', t['cards'] == 0, str(t))
t = tally([mock_deck([(plain, ['Hero']), (plain, ['Hero'])]), mock_card(plain, ['Hero'])])
check('deck plus loose card add up', t['cards'] == 3 and t['a'] == 3 * cards[plain]['a'], str(t))

# the real save: starting decks, and every Hero card in the bags
save = json.load(open(a.save, encoding='utf-8'))
by = {o['GUID']: o for o in save['ObjectStates']}
import mat_config as C
for dg in C.PM_STARTER_DECKS:
    d = by[dg]
    ents = [(c.get('Nickname', ''), c.get('Tags', [])) for c in d.get('ContainedObjects', [])]
    t = tally([mock_deck(ents)])
    check('real starting deck %s: 12 cards, Attack 4, Recruit 8, none unknown' % dg, t['cards'] == 12 and t['a'] == 4 and t['r'] == 8 and t['unknown'] == 0, str(t))


def heroes(o, out):
    for c in o.get('ContainedObjects', []) or []:
        tags = c.get('Tags', []) or []
        if c.get('Name') in ('Card', 'CardCustom') and 'Hero' in tags: out.append(c)
        heroes(c, out)


hc = []
for o in save['ObjectStates']: heroes(o, hc)
unknown = []
for c in hc:
    t = tally([mock_card(c.get('Nickname', ''), c.get('Tags', []), c.get('CardID'))])
    if t['unknown']: unknown.append(c.get('Nickname'))
check('every Hero card in the save resolves (%d cards)' % len(hc), len(hc) > 500 and not unknown, '%d unknown, e.g. %s' % (len(unknown), sorted(set(unknown))[:6]))

print('\n%d failed' % len(fails) if fails else '\nall passed')
sys.exit(1 if fails else 0)
