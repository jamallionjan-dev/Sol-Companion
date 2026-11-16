"""s85 place_leg_arrive: SolPlace's leg walk takes Living Fellows' arrival as it is, and lets another order end the walk. Game side only.

Live 2026-11-10 (DebugLog 2026-11-10_21-26 lines 28252-28329, 28644-28650):
  23:05:35.024  [SolPlace] route 7403,8265 -> 7399,8260: 10 steps, doors 1, 3 legs; leg 1 = solGoto(7402,8259) (move_to)
  23:05:36.354  LF navigation-blocker native_path_failed 7403:8264 > 7402:8259, safety-hold "held" (LF's recovery then walks her)
  23:05:43.350  [SolDrive] LF command stay  <- LF itself: SCDecision.lua 1798-1803, move_to + navigationArrived -> switchToStay
                (SCDecision.lua 1195-1211 issues Commands.issue(id, "stay")). Arrival = SCNavigation.lua 6450-6453 / 4574-4599,
                U.arrived (SCGameplayUtil.lua 425-433): within navigationArrivalDistance 0.6 (SCConfig.lua 263) of the square's centre.
                She stood at 7402.500,8260.092 (pos in the 23:05:52.801 line): 0.592 from 7402.5,8259.5 -> "arrived", but her
                square is 7402,8260, not the leg square 7402,8259.
  SolPlace.tick (SolPlace.lua 525-540) only moves to the next leg when she stands ON a path square with index >= the leg's, so
  nothing was sent; 9 s later (LEG_STALL_MS, line 540) "old walk to 7399,8260: leg_stalled" re-sent move_to to the goal through the
  wall (23:05:51.968), LF failed again (native_path_failed 23:05:52.801), tried a climb (cancelled_stuck_climb 23:06:22.781) and
  stopped (stay 23:06:23.657). The stay did not kill the leg walker; the walker did not see that LF had ended the leg.
  The same code also re-walks her 9 s after ANY other order (his "stay", the farm's own stop): the route never looks at the order.
With the switch on (SolPlace.tick, before the leg test):
  reached  within LEG_ARRIVE (0.6, LF's own radius) of the leg square's centre, or on a square next to it with nothing between
           (M.reach) while LF still walks her and she has not moved for LEG_NEAR_MS -> the next leg is sent at once.
  yield    LF's order is no longer move_to and its command serial moved since this leg was sent (someone else ordered her) and the
           leg is not reached -> the route ends quietly (no old walk); the caller's own logic decides what comes next.
Switch off: SolPlace exactly as before.
  edits    SolPlace.lua       helpers before sendLeg; sendLeg remembers LF's command serial; the check in tick
           SolAuthority.lua   A.FIXES += "place_leg_arrive"
           <Zomboid>/Lua/SolFixes_LAB.txt  place_leg_arrive=on (only when missing; only when the file exists)
Independent of s75..s84. Game closed only. In place, idempotent.
usage: apply_s85_place_leg_arrive.py <client dir>"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "place_leg_arrive"
TAG = "-- Sol fix place_leg_arrive"


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


SEND_OLD = '''local function sendLeg(R, i)
    local L = R.legs[i]
    R.li, R.sentAt, R.movedAt = i, nowMs(), nowMs()
    M.stats.legs = M.stats.legs + 1
    return M._orig(L.x, L.y, R.z)
end
'''
SEND_NEW = TAG + ''' (s85): Living Fellows ends a leg up to 0.6 tiles from the leg square's centre (U.arrived), which can
-- be the square next to it; and any other order ends her walk. The route takes both as they are instead of walking her again later.
M.LEG_ARRIVE = 0.6            -- LF navigationArrivalDistance (SCConfig.lua)
M.LEG_NEAR_MS = 1500          -- next to the leg square, nothing between, still for this long: the leg counts
local function plaOn()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("place_leg_arrive") == true
end
M.legArriveOn = plaOn
local function lfOrder(a)
    local SC = g("SurvivorCompanion")
    local C = type(SC) == "table" and SC.Commands or nil
    if a == nil or type(C) ~= "table" or type(C.peek) ~= "function" then return nil, nil end
    local ok, st = pcall(C.peek, a)
    if not ok or type(st) ~= "table" then return nil, nil end
    return st.order, tonumber((st.commandSerial))
end
M.lfOrder = lfOrder
-- "reached" | "yield", order | nil (go on as before). px,py: her square; fx,fy: her exact position; L: the leg; t: now
function M.legCheck(R, a, px, py, pz, fx, fy, L, t)
    if fx ~= nil and fy ~= nil then
        local dx, dy = fx - (L.x + 0.5), fy - (L.y + 0.5)
        if math.sqrt(dx * dx + dy * dy) <= M.LEG_ARRIVE then return "reached" end
    end
    local order, serial = lfOrder(a)
    local foreign = order ~= nil and order ~= "move_to" and R.serial ~= nil and serial ~= nil and serial ~= R.serial
    if foreign then return "yield", order end
    local d = math.max(math.abs(px - L.x), math.abs(py - L.y))
    if d == 1 and t - (R.movedAt or t) >= M.LEG_NEAR_MS and M.reach(px, py, pz, L.x, L.y) then return "reached" end
    return nil
end
local function sendLeg(R, i)
    local L = R.legs[i]
    R.li, R.sentAt, R.movedAt = i, nowMs(), nowMs()
    M.stats.legs = M.stats.legs + 1
    local okW, why = M._orig(L.x, L.y, R.z)
    if plaOn() then local _, serial = lfOrder(solActor()); R.serial = serial end        ''' + TAG + ''': LF's serial after this leg's order
    return okW, why
end
'''
TICK_OLD = '''    if not onPath then log("she left the route (someone else is walking her)"); finish(R); return end
    if idx ~= nil and idx >= L.i then
'''
TICK_NEW = '''    if not onPath then log("she left the route (someone else is walking her)"); finish(R); return end
    if (idx == nil or idx < L.i) and plaOn() then                                         ''' + TAG + '''
        local _, _, _, fx, fy = posOf(a)
        local verdict, order = M.legCheck(R, a, px, py, pz, fx, fy, L, t)
        if verdict == "reached" then
            idx = L.i
            M.stats.nearLegs = (M.stats.nearLegs or 0) + 1
        elseif verdict == "yield" then
            M.stats.yields = (M.stats.yields or 0) + 1
            log("walk to " .. R.gx .. "," .. R.gy .. " ended by another order (" .. tostring(order) .. "): not walked again")
            finish(R)
            return
        end
    end
    if idx ~= nil and idx >= L.i then
'''


def client(cl):
    cl = os.path.abspath(cl)
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")) and os.path.isfile(os.path.join(cl, "SolActions.lua")), "not a Sol client dir: " + cl
    sp = os.path.join(cl, "SolPlace.lua")
    assert os.path.isfile(sp), "no SolPlace.lua (spatial_access, s70) in " + cl
    t = open(sp, encoding="utf-8", newline="").read()
    assert 'M.VERSION = "0.2.0"' in t, "SolPlace.lua is not 0.2.0"
    print("SolPlace.lua sendLeg", edit(sp, SEND_OLD, SEND_NEW, TAG + " (s85)"))
    print("SolPlace.lua tick", edit(sp, TICK_OLD, TICK_NEW, "plaOn() then                                         " + TAG))
    print("SolAuthority", FIX, edit(os.path.join(cl, "SolAuthority.lua"), "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",' % FIX + NL, '"%s"' % FIX))
    fixfile = os.path.normpath(os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt"))
    if os.path.exists(fixfile):
        have = open(fixfile, encoding="utf-8", newline="").read()
        if FIX + "=" not in have:
            with open(fixfile, "a", encoding="utf-8", newline="") as h:
                if have and not have.endswith(NL): h.write(CRLF)
                h.write(FIX + "=on" + CRLF)
            print("SolFixes_LAB", FIX + "=on")


if __name__ == "__main__":
    client(sys.argv[1])
    print("s85_place_leg_arrive applied")
