"""Calibration overlay (build_save.py --calibrate): draws, with TTS vector lines in the plane of the art, where the build THINKS the board and
mat features are, so a top-down screenshot shows the real offset between the computed positions and the printed art.
Yellow rectangle = the printed area the build assumes; red crosses = slot centres; green rectangle = the Played box. Lines sit in the same plane as
the art, so there is no perspective error. Off unless LEGENDARY_CAL=1."""
import os
import mat_config as C

CAL_LUA = r'''
--[[ ===== Calibration overlay (generated with --calibrate; remove by rebuilding without it) ===== --]]
CAL_BOARD = {cx = __CX__, cz = __CZ__, w = __W__, h = __H__}
CAL_BOARD_SLOTS = {__BSLOTS__}
CAL_MAT_UVS = {__MUVS__}
CAL_PLAYED = {__PLAYED__}
CAL_DECKS = {__DECKS__}
CAL_STARTERS = {__STARTERS__}
CAL_Y = 1.75   -- above the board (top 1.49) and mat (top 1.37) surfaces, or the lines are hidden inside them

function calCol(c) return {r = c[1], g = c[2], b = c[3]} end

function calCross(L, x, z, col)
    L[#L + 1] = {points = {{x = x - 0.6, y = CAL_Y, z = z}, {x = x + 0.6, y = CAL_Y, z = z}}, color = calCol(col), thickness = 0.16}
    L[#L + 1] = {points = {{x = x, y = CAL_Y, z = z - 0.6}, {x = x, y = CAL_Y, z = z + 0.6}}, color = calCol(col), thickness = 0.16}
end

function calPoly(L, pts, col)
    local p = {}
    for _, q in ipairs(pts) do p[#p + 1] = {x = q[1], y = CAL_Y, z = q[2]} end
    p[#p + 1] = p[1]
    L[#L + 1] = {points = p, color = calCol(col), thickness = 0.2}
end

function calDecks()
    --[[where each deck is against where the build meant it to be (slot centre), and where its bounding box is centred]]
    local function report(label, guid, ex, ez)
        local o = getObjectFromGUID(guid)
        if o == nil then print('CAL ' .. label .. ': not found') return end
        local p = o.getPosition()
        local ok, bc = pcall(function() return o.getBounds().center end)
        local bs = ok and bc or p
        print(string.format('CAL %-10s intended (%.2f, %.2f)  position (%.2f, %.2f) diff (%+.2f, %+.2f)  bounds centre (%.2f, %.2f) y %.2f', label, ex, ez, p.x, p.z, p.x - ex, p.z - ez, bs.x, bs.z, p.y))
    end
    for _, d in ipairs(CAL_DECKS) do report(d[1], d[2], d[3], d[4]) end
    for i, g in ipairs(PLAYER_MATS) do
        local mat = getObjectFromGUID(g)
        local deckg = CAL_STARTERS[i]
        if mat ~= nil and deckg ~= nil then
            local pt = tfMatPoint(mat, PILES.draw)
            report('draw ' .. i, deckg, pt.x, pt.z)
        end
    end
end

function calDraw()
    local L = {}
    local b = CAL_BOARD
    calPoly(L, {{b.cx - b.w / 2, b.cz - b.h / 2}, {b.cx + b.w / 2, b.cz - b.h / 2}, {b.cx + b.w / 2, b.cz + b.h / 2}, {b.cx - b.w / 2, b.cz + b.h / 2}}, {1, 1, 0})
    for _, s in ipairs(CAL_BOARD_SLOTS) do calCross(L, s[1], s[2], {1, 0.1, 0.1}) end
    for _, g in ipairs(PLAYER_MATS) do
        local mat = getObjectFromGUID(g)
        if mat ~= nil then
            local pts = {}
            for _, uv in ipairs({{0, 0}, {1, 0}, {1, 1}, {0, 1}}) do local p = tfMatPoint(mat, uv); pts[#pts + 1] = {p.x, p.z} end
            calPoly(L, pts, {1, 1, 0})
            local q = {}
            for _, uv in ipairs({{CAL_PLAYED[1], CAL_PLAYED[2]}, {CAL_PLAYED[3], CAL_PLAYED[2]}, {CAL_PLAYED[3], CAL_PLAYED[4]}, {CAL_PLAYED[1], CAL_PLAYED[4]}}) do local p = tfMatPoint(mat, uv); q[#q + 1] = {p.x, p.z} end
            calPoly(L, q, {0.2, 1, 0.3})
            for _, uv in ipairs(CAL_MAT_UVS) do local p = tfMatPoint(mat, uv); calCross(L, p.x, p.z, {1, 0.1, 0.1}) end
        end
    end
    local okv, errv = pcall(function() Global.setVectorLines(L) end)
    if not okv then print('CAL setVectorLines failed: ' .. tostring(errv)) end
    print('CAL lines drawn: ' .. #L)
    local board = getObjectFromGUID('083da5')
    if board ~= nil then
        local bb = board.getBounds()
        print(string.format('CAL board bounds: size %.2f x %.2f x %.2f, centre %.2f, %.2f, %.2f, scale %.4f', bb.size.x, bb.size.y, bb.size.z, bb.center.x, bb.center.y, bb.center.z, board.getScale().x))
    end
    local m1 = getObjectFromGUID(PLAYER_MATS[2])
    if m1 ~= nil then
        local mb = m1.getBounds()
        print(string.format('CAL mat bounds: size %.2f x %.2f x %.2f, centre %.2f, %.2f, %.2f, scale %.4f', mb.size.x, mb.size.y, mb.size.z, mb.center.x, mb.center.y, mb.center.z, m1.getScale().x))
    end
    for _, p in ipairs(Player.getPlayers()) do
        pcall(function() p.lookAt({position = {x = b.cx, y = 1, z = b.cz}, pitch = 90, yaw = 0, distance = 30}) end)
    end
    print("Calibration overlay on: yellow = assumed printed area, red crosses = computed slot centres, green = Played box.")
end

Wait.time(calDraw, 4)
Wait.time(calDecks, 6)
'''


def cal_lua():
    if os.environ.get('LEGENDARY_CAL') != '1': return ''
    W = C.IMG_W; H = W / C.ASPECT
    bs = [(C.CX + (u - .5) * W, C.CZ - (v - .5) * H) for u, v in C.SLOT_UV.values()]
    bs += [(C.CX + (u - .5) * W, C.CZ - (C.CITY_V - .5) * H) for u in C.CITY_U]
    bs += [(C.CX + (u - .5) * W, C.CZ - (C.HQ_V - .5) * H) for u in C.CITY_U]
    muv = [C.PM_VICTORY_UV, C.PM_DRAW_UV, C.PM_ARTIFACTS_UV, C.PM_DISCARD_UV, C.PM_ATTACK_UV, C.PM_RECRUIT_UV, C.PM_SHARDS_UV]
    dk = []
    for name, guid, key in (('Bystanders', '15841b', 'bystanders'), ('Wounds', 'dab70e', 'wounds'), ('Officers', '22f0d7', 'shield')):
        u, v = C.SLOT_UV[key]
        dk.append('{"%s", "%s", %.3f, %.3f}' % (name, guid, C.CX + (u - .5) * W, C.CZ - (v - .5) * H))
    starters = ', '.join('"%s"' % g for g in C.PM_STARTER_DECKS)
    f = lambda pts: ', '.join('{%.3f, %.3f}' % p for p in pts)
    return (CAL_LUA.replace('__CX__', '%g' % C.CX).replace('__CZ__', '%g' % C.CZ).replace('__W__', '%g' % W).replace('__H__', '%g' % H)
            .replace('__BSLOTS__', f(bs)).replace('__MUVS__', f(muv)).replace('__DECKS__', ', '.join(dk)).replace('__STARTERS__', starters).replace('__PLAYED__', ', '.join('%g' % v for v in C.PM_PLAYED_BOX)))
