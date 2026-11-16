# s102: the s97 porch suite with reaim_hold (and edge_api) ON, run on a copy with s101 + s102 applied.
"""s97 walk_no_vault offline: a synthetic porch (house wall with a door, a porch railing with a 1-tile gap 3 tiles from the door,
side railings) on SolPlace.lua after s85 -> s96 -> s97 (a temp copy of the live client file; nothing live is touched).
Checks: the route uses the gap; no stretch between two legs can be cut over the railing (LF-priced probe, fence 2.5); a short
no-door walk round the railing is no longer handed back "direct"; an unseen zombie 6 tiles away no longer turns her walk into the
old one, a perceived one or one at arm's length does; LF's fence step is refused while calm only when a way round exists; the
switch off = the old behaviour; s85's and s96's tests still pass; installer idempotent; ASCII; tonumber gate.
Run: python test_s97_walk_no_vault.py [client dir]. Offline PASS is not Runtime PASS: Living Fellows' walking is a stub here."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
tmp = tempfile.mkdtemp(prefix="s97_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
for f in ("SolPlace.lua", "SolAuthority.lua", "SolActions.lua"): shutil.copy(os.path.join(CL, f), cl)
ORIG = open(os.path.join(cl, "SolPlace.lua"), encoding="utf-8", newline="").read()
for s in ("apply_s85_place_leg_arrive.py", "apply_s96_leg_yield.py", "apply_s97_walk_no_vault.py"):
    r = subprocess.run([sys.executable, os.path.join(HERE, s), cl], capture_output=True, text=True)
    ck("installer " + s + " (in order s85 -> s96 -> s97)", r.returncode == 0, r.stdout + r.stderr)
P96 = None
r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s97_walk_no_vault.py"), cl], capture_output=True, text=True)
ck("s97 second run changes nothing", r.returncode == 0 and r.stdout.count("kept") == 2, r.stdout)
P = open(os.path.join(cl, "SolPlace.lua"), encoding="utf-8", newline="").read()
A = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8", newline="").read()
ck("switch listed once in A.FIXES", A.count('"walk_no_vault"') == 1)
BASE_ORIG = ORIG.split("-- Sol fix walk_no_vault (s97)")[0]
ck("s97 only appends a block: every line of the s85+s96 file (before any older s97 block) kept, in order",
   all(line in P for line in BASE_ORIG.splitlines()) and P.rstrip().endswith("return M") and P.count("-- Sol fix walk_no_vault (s97)") == 1)
ck("s97b block present (native engine paths re-aimed)", "function NV.wrapNative()" in P)
for t in ("test_s85_place_leg_arrive.py", "test_s96_leg_yield.py"):
    r = subprocess.run([sys.executable, os.path.join(HERE, t), cl], capture_output=True, text=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    fails = [l for l in r.stdout.splitlines() if l.startswith("FAIL") and "installer" not in l and "second run" not in l]
    ck(t + " replays all still pass on the s97 file", not fails and "SUMMARY" in r.stdout or ("pass=" in r.stdout and not fails), fails or r.stdout[-400:])

ENV = r"""
NOW = 1000
function getTimestampMs() return NOW end
LOGS = {}
function print(m) LOGS[#LOGS + 1] = tostring(m) end
SW = { spatial_access = true, place_leg_arrive = true, walk_no_vault = true, reaim_hold = true, edge_api = true }
SolAuthority = { on = function(f) return SW[f] == true end }
-- the porch: house rows y 0..9 (x 0..12), its south wall on the N edge of row 10 with a door at x=5; porch rows 10..11, x 2..8;
-- railing on the N edge of row 12 for x 2..8 except a gap at x=8; side railings W of x=2 and W of x=9 for rows 10..11.
GAPX = 8
ENCLOSED = false
DOOR = { open = false }
W = {}
function W.standable(x, y, z) return x >= -6 and x <= 20 and y >= 0 and y <= 26 end
function W.edge(x, y, z, dir)
    if dir == "N" and y == 10 and x >= 0 and x <= 12 then if x == 5 then return "door", DOOR end return "wall" end
    if dir == "W" and (x == 0 or x == 13) and y >= 0 and y <= 9 then return "wall" end
    if dir == "N" and y == 12 and x >= 2 and x <= 8 then if x == GAPX and not ENCLOSED then return "open" end return "fence" end
    if dir == "W" and (x == 2 or x == 9) and y >= 10 and y <= 11 then return "fence" end
    return "open"
end
SOL = { x = 5.5, y = 7.5, z = 0 }
function SOL:getX() return self.x end
function SOL:getY() return self.y end
function SOL:getZ() return self.z end
function SOL:getVehicle() return nil end
function SOL:getActionStateName() return STATE or "idle" end
ST = { order = "follow", commandSerial = 10 }
SENT = {}
THREATS = {}
ZOMBIES = {}
local zl = {}
function zl:size() return #ZOMBIES end
function zl:get(i) return ZOMBIES[i + 1] end
local function zombie(x, y, z) local zb = { x = x, y = y, z = z or 0 }
    function zb:getX() return self.x end; function zb:getY() return self.y end; function zb:getZ() return self.z end
    function zb:isDead() return false end; return zb end
ZOMBIE = zombie
CELL = { getZombieList = function(self) return zl end }
function getCell() return CELL end
BASECALLS = {}
SurvivorCompanion = {
    Commands = { peek = function(a) return ST end },
    GameplayUtil = { peekActorState = function(a) return { snapshot = { threats = THREATS } } end },
    Navigation = { _handleFenceForRequest = function(actor, obj, f, t, intent) BASECALLS[#BASECALLS + 1] = f:getX() .. "," .. f:getY() .. ">" .. t:getX() .. "," .. t:getY(); return true, "climbing" end },
    Topology = { classifyEdge = function(actor, f, t, o) return FENCE_EDGE end },
}
FENCE_EDGE = { traversable = true, affordance = "fence", cost = 2.5 }
SolUI = { solActor = function() return SOL end }
SolUI.solGoto = function(x, y, z) SENT[#SENT + 1] = { x = x, y = y }; ST.order = "move_to"; ST.commandSerial = ST.commandSerial + 1; return true, "walking" end
function SQ(x, y, z) return { getX = function() return x end, getY = function() return y end, getZ = function() return z or 0 end } end
Events = nil
"""
def fresh(on=True):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV); L.execute(P); L.execute("SolPlace.install(); SolPlace.setWorld(W); SolPlace.NV.wrapFence()")
    L.execute("SW.walk_no_vault = %s" % ("true" if on else "false"))
    return L
def logs(L): s = L.eval("LOGS"); return [s[i] for i in range(1, len(s) + 1)]
def lst(t): return [t[i] for i in range(1, len(t) + 1)] if t is not None else []

PROBE_LEGS = r"""
function LEGPROBE(j)
    local bad = {}
    local prev = j.path[1]
    for _, L in ipairs(j.legs) do
        local p = SolPlace.probe(prev.x, prev.y, L.x, L.y, 0, false, 2000, 6)
        local c = p.counts or {}
        if p.state == "done" and ((c.fence or 0) + (c.window or 0) + (c.frame or 0)) > 0 then bad[#bad + 1] = prev.x .. "," .. prev.y .. ">" .. L.x .. "," .. L.y end
        prev = { x = L.x, y = L.y }
    end
    return table.concat(bad, " ")
end
function PATHUSES(j, ax, ay, bx, by)
    for i = 2, #j.path do local p, q = j.path[i - 1], j.path[i]
        if p.x == ax and p.y == ay and q.x == bx and q.y == by then return true end end
    return false
end
"""
# 1. inside -> outside past the porch: the route goes through the gap, and no leg stretch can be cut over the railing
for on in (True, False):
    L = fresh(on); L.execute(PROBE_LEGS)
    L.execute("J = SolPlace.route(5, 7, 0, { { x = 3, y = 15 } })")
    st, fence, gapuse = L.eval("J.state"), L.eval("J.counts.fence or 0"), L.eval("PATHUSES(J, 8, 11, 8, 12)")
    bad = L.eval("LEGPROBE(J)")
    legs = L.eval("(function() local t = {} for _, l in ipairs(J.legs) do t[#t + 1] = l.x .. ',' .. l.y end return table.concat(t, ' ') end)()")
    if on:
        ck("on: route 5,7 -> 3,15 found, no fence crossed, through the gap 8,11 -> 8,12", st == "done" and fence == 0 and gapuse, (st, fence, gapuse, legs))
        ck("on: no stretch between two legs can be cut over the railing (LF-priced probe)", bad == "", (bad, legs))
        ck("on: an extra leg was added at the porch", (L.eval("J.gapLegs") or 0) >= 1 and any("extra leg" in m for m in logs(L)), (legs, logs(L)))
    else:
        ck("off: the same route (gap, door), as before", st == "done" and fence == 0 and gapuse, (st, fence, legs))
        ck("off: the old legs leave a stretch the LF walk can cut over the railing (the live fault, reproduced)", bad != "", legs)
        ck("off: no extra legs, no s97 leg line", L.eval("J.gapLegs") is None and not any("extra leg" in m for m in logs(L)), logs(L))

# 2. a short walk round the railing with no door: before = "direct" (LF's own walk, which vaults); now legs through the gap
for on in (True, False):
    L = fresh(on)
    L.execute("SOL.x, SOL.y = 3.5, 14.5; SolUI.solGoto(4, 11, 0)")
    sent = [(s.x, s.y) for s in lst(L.eval("SENT"))]
    if on:
        ck("on: outside 3,14 -> porch 4,11 is walked in legs, not handed back direct", len(sent) >= 1 and sent[0] != (4, 11) and L.eval("SolPlace.R") is not None
           and L.eval("SolPlace.stats.direct") == 0, (sent, logs(L)))
        L.execute(PROBE_LEGS)
        ck("on: those legs cannot be cut over the railing", L.eval("LEGPROBE(SolPlace.R.job)") == "", L.eval("LEGPROBE(SolPlace.R.job)"))
    else:
        ck("off: the same walk is handed back direct (the goal itself to LF)", sent == [(4, 11)] and L.eval("SolPlace.stats.direct") == 1, sent)

# 3. danger: an unseen zombie 6 tiles away (same floor) - before: the old walk; now: routed. Perceived at 5, or one at 2: the old walk.
def walk_with(on, setup):
    L = fresh(on); L.execute(setup); L.execute("SolUI.solGoto(3, 15, 0)")
    return L, [(s.x, s.y) for s in lst(L.eval("SENT"))]
L, sent = walk_with(True, "ZOMBIES[1] = ZOMBIE(11.5, 7.5, 0)")
ck("on: unseen zombie 6 tiles away (behind the wall): still routed door-first (calm)", sent and sent[0] != (3, 15) and L.eval("SolPlace.R") is not None, sent)
L, sent = walk_with(False, "ZOMBIES[1] = ZOMBIE(11.5, 7.5, 0)")
ck("off: the same zombie -> the old walk (the goal to LF), as before", sent == [(3, 15)], sent)
L, sent = walk_with(True, "ZOMBIES[1] = ZOMBIE(5.5, 7.5, 1)")
ck("on: a zombie upstairs right above her does not count", sent and sent[0] != (3, 15), sent)
L, sent = walk_with(True, "THREATS[1] = { distanceSq = 25 }")
ck("on: a zombie she perceives 5 tiles away -> the old walk (a fence may be her way out)", sent == [(3, 15)], sent)
L, sent = walk_with(True, "ZOMBIES[1] = ZOMBIE(6.5, 8.5, 0)")
ck("on: a zombie at arm's length (1.4 tiles), unseen -> the old walk", sent == [(3, 15)], sent)

# 4. Living Fellows' fence step: refused for her while calm when a way round exists
L = fresh(True)
r = L.execute("OKF, WHY = SurvivorCompanion.Navigation._handleFenceForRequest(SOL, nil, SQ(4, 11), SQ(4, 12), {})")
ck("on, calm, gap 4 tiles away: LF's fence step over the railing is refused (LF blacklists the edge and plans again)",
   L.eval("OKF") is False and L.eval("WHY") == "sol_calm_way_round" and L.eval("#BASECALLS") == 0, (L.eval("OKF"), L.eval("WHY")))
ck("  ... and logged once", sum("refused while calm" in m for m in logs(L)) == 1, logs(L))
L.execute("SurvivorCompanion.Navigation._handleFenceForRequest(SOL, nil, SQ(4, 11), SQ(4, 12), {})")
ck("  ... the answer is remembered (no second search, no second line)", sum("refused while calm" in m for m in logs(L)) == 1 and L.eval("#BASECALLS") == 0)
L.execute("NOW = NOW + 60000; THREATS[1] = { distanceSq = 9 }; SurvivorCompanion.Navigation._handleFenceForRequest(SOL, nil, SQ(3, 11), SQ(3, 12), {})")
ck("on, a perceived zombie 3 tiles away: the vault is allowed (fleeing)", L.eval("#BASECALLS") == 1)
L = fresh(True); L.execute("ENCLOSED = true; DOOR.open = false")
L.execute("NOW = NOW + 60000; SurvivorCompanion.Navigation._handleFenceForRequest(SOL, nil, SQ(4, 11), SQ(4, 12), {})")
ck("on, no gap (the railing closed) and only a far way round: the vault is allowed", L.eval("#BASECALLS") == 1, logs(L))
L = fresh(False)
L.execute("SurvivorCompanion.Navigation._handleFenceForRequest(SOL, nil, SQ(4, 11), SQ(4, 12), {})")
ck("off: LF's fence step untouched", L.eval("#BASECALLS") == 1)
L = fresh(True)
L.execute("OTHER = { getVehicle = function() return nil end }; SurvivorCompanion.Navigation._handleFenceForRequest(OTHER, nil, SQ(4, 11), SQ(4, 12), {})")
ck("on: another companion's fence step untouched", L.eval("#BASECALLS") == 1)

# 5. LF edge prices: the fence surcharge stays on with an unseen zombie 6 tiles away (calm), as the old test dropped it
for on in (True, False):
    L = fresh(on); L.execute("ZOMBIES[1] = ZOMBIE(11.5, 7.5, 0); R5 = SurvivorCompanion.Topology.classifyEdge(SOL, nil, nil, {})")
    c = L.eval("R5.cost")
    if on: ck("on: LF fence price for her with an unseen zombie 6 tiles away = 2.5 + 40", abs(c - 42.5) < 1e-6, c)
    else: ck("off: the same = 2.5 (surcharge dropped, as before)", abs(c - 2.5) < 1e-6, c)

# 6. only a fence gets there (no gap, door locked): her own route still finds the way (fence last) or hands back to LF
L = fresh(True); L.execute("ENCLOSED = true; J6 = SolPlace.route(4, 11, 0, { { x = 4, y = 14 } })")
ck("on, porch closed all round: route over the railing as the last resort", L.eval("J6.state") == "done" and L.eval("J6.counts.fence") == 1,
   (L.eval("J6.state"), L.eval("J6.why")))
L = fresh(True); L.execute(PROBE_LEGS); L.execute("J7 = SolPlace.route(4, 11, 0, { { x = 4, y = 14 } })")
ck("on, gap open: route round through the gap, no fence", L.eval("J7.state") == "done" and (L.eval("J7.counts.fence") or 0) == 0 and L.eval("PATHUSES(J7, 8, 11, 8, 12)"))
ck("on: probe work per route stays small (nodes for the probes of route 4,11 -> 4,14)", L.eval("SolPlace.NV.stats.probes") <= 40, L.eval("SolPlace.NV.stats.probes"))

# 7. a calm climb start is logged once
L = fresh(True); L.execute("STATE = 'climbfence'; SolPlace.NV.watch(); SolPlace.NV.watch()")
ck("on: a calm vault start is logged once", sum("calm vault seen" in m for m in logs(L)) == 1, logs(L))

# 8. s97b: LF's own engine path (vanilla PathFindBehavior2) while following him in past the porch
NATIVE = r"""
NATIVE_SENT = {}
SurvivorCompanion.NativeMovementActions = { dispatch = function(actor, mode, intent, provider)
    local t = intent.nextSquare or intent.targetSquare
    NATIVE_SENT[#NATIVE_SENT + 1] = t:getX() .. "," .. t:getY(); return true, "path_started" end }
SolPlace.NV.squareAt = function(x, y, z) return SQ(x, y, z) end
SolPlace.NV.wrapNative()
function FOLLOW(tx, ty, extra)
    local intent = { action = "follow_formation", enginePath = true, nextSquare = SQ(tx, ty, 0), targetSquare = SQ(tx, ty, 0) }
    for k, v in pairs(extra or {}) do intent[k] = v end
    return SurvivorCompanion.NativeMovementActions.dispatch(SOL, "jog", intent, {})
end
"""
def native(on=True, gapx=8, sx=4.5, sy=14.5):
    L = fresh(on); L.execute(PROBE_LEGS); L.execute(NATIVE)
    L.execute("GAPX = %d; SOL.x, SOL.y = %s, %s" % (gapx, sx, sy))
    return L
def nsent(L): return lst(L.eval("NATIVE_SENT"))
for gapx in (8, 6):
    L = native(True, gapx)
    L.execute("FOLLOW(5, 8)")
    s = nsent(L)
    wx, wy = (int(v) for v in s[0].split(",")) if s else (None, None)
    bad = L.eval("(function() local p = SolPlace.probe(4, 14, %s, %s, 0, false, 2000, 6); local c = p.counts or {}; return (c.fence or 0) + (c.window or 0) end)()" % (wx, wy)) if s else 1
    ck("s97b on, gap at x=%d: follow engine path 4,14 -> 5,8 (in past the railing) re-aimed at a square vanilla reaches without a climb" % gapx,
       len(s) == 1 and s[0] != "5,8" and bad == 0 and any("engine path" in m for m in logs(L)), (s, logs(L)))
    L.execute("SOL.x, SOL.y = %s, %s; NOW = NOW + 2000; FOLLOW(5, 8)" % (wx + 0.5, wy + 0.5))
    s2 = nsent(L)
    ck("s97b on, gap at x=%d: from that square the next engine path goes on (closer to him, still no climb)" % gapx,
       len(s2) == 2 and (s2[1] == "5,8" or s2[1] != s2[0]), s2)
L = native(False); L.execute("FOLLOW(5, 8)")
ck("s97b off: the engine path goes to his square as before", nsent(L) == ["5,8"], nsent(L))
L = native(True); L.execute("THREATS[1] = { distanceSq = 16 }; FOLLOW(5, 8)")
ck("s97b on, a zombie she perceives 4 tiles away: untouched (a vault may be her way out)", nsent(L) == ["5,8"], nsent(L))
L = native(True); L.execute("FOLLOW(5, 8, { nativeAffordance = 'door' })")
ck("s97b on: an approved single crossing (nativeAffordance) is untouched", nsent(L) == ["5,8"], nsent(L))
L = native(True, 8, 7.5, 14.5); L.execute("FOLLOW(7, 16)")
ck("s97b on: an engine path with no fence to cut is untouched", nsent(L) == ["7,16"], nsent(L))
L = native(True); L.execute("ENCLOSED = true; FOLLOW(5, 8)")
ck("s97b on, no gap at all: untouched (vault is the only way)", nsent(L) == ["5,8"], nsent(L))
L = native(True); L.execute("SurvivorCompanion.Navigation.peek = function(a) return { goalAction = 'follow_formation', pathReason = 'budget', lastMovementReason = 'engine_path', nativeLease = { reason = 'engine_goal', toSquare = SQ(5, 8, 0) } } end; STATE = 'climbfence'; SolPlace.NV.watch()")
ck("calm vault line carries what LF was doing (goal, pathReason, native lease)", any("calm vault seen" in m and "native=engine_goal/nil to 5,8" in m for m in logs(L)), logs(L))

ck("ascii only (SolPlace after s97)", all(ord(c) < 128 for c in P))
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
if os.path.exists(GATE):
    r = subprocess.run([sys.executable, GATE, os.path.join(cl, "SolPlace.lua")], capture_output=True, text=True)
    ck("tonumber gate (SolPlace after s97)", r.returncode == 0, r.stdout[-300:])
else:
    ck("tonumber gate present", False, GATE)
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
