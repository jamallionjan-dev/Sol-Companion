"""s85 place_leg_arrive: an offline replay of 2026-11-10 23:05:35-23:06:23 (route 7403,8265 -> 7399,8260 through one door, leg 1
7402,8259; she stops at 7402.500,8260.092; Living Fellows calls that "arrived" and issues its own stay) on SolPlace.lua as the
installer leaves it (a temporary copy of the live client file, read only), with a stand-in for Living Fellows' order state
(Commands.issue / peek / serial, arrival radius 0.6 as in SCGameplayUtil.U.arrived). Also: his stay mid-leg, stuck next to a leg,
the exact-square path unchanged, the switch off = the old behaviour, the tonumber gate and the installer (idempotent).
Run: set PYTHONIOENCODING=utf-8 & python test_s85_place_leg_arrive.py [client dir]
Offline PASS is not Runtime PASS: Living Fellows' walking is a stub here."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)

CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
if not os.path.isfile(os.path.join(CL, "SolPlace.lua")):
    CL = None
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
tmp = tempfile.mkdtemp(prefix="s85_")
cl = os.path.join(tmp, "client"); os.makedirs(cl)
src_dir = CL or HERE
for f in ("SolPlace.lua", "SolAuthority.lua", "SolActions.lua"):
    p = os.path.join(src_dir, f)
    if not os.path.exists(p): p = os.path.join(HERE, f)
    if os.path.exists(p): shutil.copy(p, cl)
    else: open(os.path.join(cl, f), "w").write("A.FIXES = {\n}\n")
ORIG = open(os.path.join(cl, "SolPlace.lua"), encoding="utf-8", newline="").read()
run = lambda: subprocess.run([sys.executable, os.path.join(HERE, "apply_s85_place_leg_arrive.py"), cl], capture_output=True, text=True)
r1 = run(); P1 = open(os.path.join(cl, "SolPlace.lua"), encoding="utf-8", newline="").read()
r2 = run(); P2 = open(os.path.join(cl, "SolPlace.lua"), encoding="utf-8", newline="").read()
A1 = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8", newline="").read()
ck("installer: runs on %s SolPlace.lua, edits sendLeg and tick" % ("the live" if CL else "the pending"), r1.returncode == 0 and P1.count("-- Sol fix place_leg_arrive") == 3, r1.stdout + r1.stderr)
ck("installer: second run changes nothing", r2.returncode == 0 and P1 == P2 and r2.stdout.count("kept") >= 3, r2.stdout + r2.stderr)
ck("installer: the switch is listed once", A1.count('"place_leg_arrive"') == 1)
ck("installer: nothing outside the two places changed (the old file's lines all kept, in order)",
   all(line in P1 for line in ORIG.splitlines() if "return M._orig(L.x, L.y, R.z)" not in line))

ENV = r"""
NOW = 1000
function getTimestampMs() return NOW end
LOGS = {}
function print(m) LOGS[#LOGS + 1] = tostring(m) end
SW = { spatial_access = true, place_leg_arrive = true }
SolAuthority = { on = function(f) return SW[f] == true end }
-- the replay map: a wall on the west side of x=7402 (7401|7402) from y=8240 to 8280, one door in it at 7402,8259 (closed, not locked)
OPEN = {}
W = {}
function W.standable(x, y, z) return x > 7380 and x < 7420 and y > 8240 and y < 8280 end
function W.edge(x, y, z, dir)
    if dir == "W" and x == 7402 and y > 8240 and y < 8280 then
        if y == 8259 then return "door", { open = OPEN.door == true } end
        return "wall"
    end
    return "open"
end
-- Sol and a stand-in for Living Fellows' orders: issue bumps the serial (SCCommands markCommand), arrival within 0.6 -> its own stay
SOL = { x = 7403.5, y = 8265.5, z = 0 }
function SOL:getX() return self.x end
function SOL:getY() return self.y end
function SOL:getZ() return self.z end
function SOL:getVehicle() return nil end
ST = { order = "stay", commandSerial = 40 }
SENT, ISSUED = {}, {}
function issue(cmd, x, y)
    ST.commandSerial = ST.commandSerial + 1
    ST.order = cmd
    ST.target = x and { x = x, y = y } or nil
    ISSUED[#ISSUED + 1] = cmd
end
SurvivorCompanion = { Commands = { peek = function(a) return ST end } }
SolUI = { solActor = function() return SOL end }
SolUI.solGoto = function(x, y, z) SENT[#SENT + 1] = { x = x, y = y }; issue("move_to", x, y); return true, "walking_to " .. x .. "," .. y end
function lfArrival()                        -- SCDecision move_to: navigationArrived -> switchToStay (Commands.issue "stay")
    if ST.order ~= "move_to" or ST.target == nil then return end
    local dx, dy = SOL.x - (ST.target.x + 0.5), SOL.y - (ST.target.y + 0.5)
    if math.sqrt(dx * dx + dy * dy) <= 0.6 or (math.floor(SOL.x) == ST.target.x and math.floor(SOL.y) == ST.target.y) then issue("stay") end
end
Events = nil
"""
def fresh():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV)
    L.execute(P1)
    L.execute("SolPlace.install(); SolPlace.setWorld(W)")
    return L
def sent(L): s = L.eval("SENT"); return [(s[i].x, s[i].y) for i in range(1, len(s) + 1)]
def issued(L): s = L.eval("ISSUED"); return [s[i] for i in range(1, len(s) + 1)]
def logs(L): s = L.eval("LOGS"); return [s[i] for i in range(1, len(s) + 1)]
def run_ms(L, ms, step=100, lf=True):
    for _ in range(ms // step):
        L.execute("NOW = NOW + %d" % step)
        if lf: L.execute("lfArrival()")
        L.execute("SolPlace.tick(4)")

def replay(L):
    L.execute("SolUI.solGoto(7399, 8260, 0)")                          # 23:05:35.024 the route; leg 1 sent
    run_ms(L, 1300)                                                    # 23:05:36.354 LF native_path_failed, held (order stays move_to)
    L.execute("SOL.x, SOL.y = 7403.5, 8263.5"); run_ms(L, 3000)        # LF's recovery walks her
    L.execute("SOL.x, SOL.y = 7402.5, 8261.5"); run_ms(L, 2500)
    L.execute("SOL.x, SOL.y = 7402.500, 8260.092")                     # ~23:05:42.9 where the 23:05:52.801 line has her
    run_ms(L, 1000)                                                    # 23:05:43.350 LF's stay

# ---------------------------------------------------------------- the replay, switch on
L = fresh()
L.execute("SW.place_leg_arrive = true")
replay(L)
s, lg = sent(L), logs(L)
route = [m for m in lg if m.startswith("[SolPlace] route ")]
ck("replay: the same route as live (7403,8265 -> 7399,8260, 1 door, 3 legs, 10 steps)", route and "10 steps, doors 1" in route[0] and "3 legs" in route[0], route)
ck("replay: leg 1 is 7402,8259, the square before the door", s[:1] == [(7402, 8259)], s)
ck("replay: LF calls 7402.500,8260.092 arrived (0.592 <= 0.6) and issues its own stay (as at 23:05:43.350)", "stay" in issued(L), issued(L))
ck("replay, switch on: the next leg (7401,8259, through the door) is sent at once, no leg_stalled, no old walk",
   (7401, 8259) in s and not any("leg_stalled" in m for m in lg) and (7399, 8260) not in s[:2], (s, [m for m in lg if "SolPlace" in m]))
ck("replay, switch on: counted as a near leg", L.eval("SolPlace.stats.nearLegs") == 1)
L.execute("SOL.x, SOL.y = 7401.5, 8259.5"); run_ms(L, 500)
ck("replay, switch on: through the door, the last leg goes to the goal", s and sent(L)[-1] == (7399, 8260), sent(L))
L.execute("SOL.x, SOL.y = 7399.5, 8260.5"); run_ms(L, 500)
ck("replay, switch on: at the goal the route is done", L.eval("SolPlace.R") is None)

# ---------------------------------------------------------------- the same replay, switch off: the live behaviour
L = fresh()
L.execute("SW.place_leg_arrive = false")
replay(L)
run_ms(L, 8500)                                                        # ... 23:05:51.968
s, lg = sent(L), logs(L)
ck("replay, switch off: exactly the live log: leg_stalled, then the old walk to 7399,8260 (no door leg ever sent)",
   any("old walk to 7399,8260: leg_stalled" in m for m in lg) and s == [(7402, 8259), (7399, 8260)], (s, [m for m in lg if "SolPlace" in m]))

# ---------------------------------------------------------------- his stay in the middle of a leg
for on in (True, False):
    L = fresh()
    L.execute("SW.place_leg_arrive = %s" % ("true" if on else "false"))
    L.execute("SolUI.solGoto(7399, 8260, 0)"); run_ms(L, 500)
    L.execute("SOL.x, SOL.y = 7403.5, 8262.5"); run_ms(L, 500)
    L.execute("issue('stay')")                                         # the player: "stay" (or the farm's own stop)
    run_ms(L, 20000)
    s, lg = sent(L), logs(L)
    if on:
        ck("his stay mid-leg, switch on: the route ends, she is not walked again (20 s)", s == [(7402, 8259)] and L.eval("SolPlace.R") is None
           and any("ended by another order (stay)" in m for m in lg), (s, [m for m in lg if "SolPlace" in m]))
    else:
        ck("his stay mid-leg, switch off: (the old fault) 9 s later she is walked again", (7399, 8260) in s, s)

# ---------------------------------------------------------------- stuck next to a leg, LF still walking her
L = fresh()
L.execute("SolUI.solGoto(7399, 8260, 0)"); run_ms(L, 300)
L.execute("SOL.x, SOL.y = 7403.5, 8259.5")                             # east of the leg square, open between, 1.0 from its centre
run_ms(L, 1000, lf=False)
ck("stuck next to the leg: not yet at 1.0 s", sent(L) == [(7402, 8259)], sent(L))
run_ms(L, 800, lf=False)
ck("stuck next to the leg: after LEG_NEAR_MS the next leg is sent", sent(L)[-1] == (7401, 8259), sent(L))

# ---------------------------------------------------------------- next to a leg but a wall between: not reached
L = fresh()
L.execute("SolUI.solGoto(7399, 8260, 0)"); run_ms(L, 300)
leg1 = sent(L)[0]
L.execute("SOL.x, SOL.y = 7401.5, 8260.5")                             # west of the wall, diagonal to 7402,8259: not clear
run_ms(L, 3000, lf=False)
ck("next to the leg across the wall: not counted (no door leg skipped)", (7401, 8259) not in sent(L)[1:] or sent(L) == [leg1], sent(L))

# ---------------------------------------------------------------- the exact-square path is unchanged
L = fresh()
L.execute("SolUI.solGoto(7399, 8260, 0)"); run_ms(L, 300)
L.execute("SOL.x, SOL.y = 7402.5, 8259.5"); run_ms(L, 300)
ck("on the leg square: the next leg as before", sent(L)[-1] == (7401, 8259) and L.eval("SolPlace.stats.nearLegs") is None, sent(L))

# ---------------------------------------------------------------- no Living Fellows order state: never yields
L = fresh()
L.execute("SurvivorCompanion = nil; SolUI.solGoto(7399, 8260, 0)"); run_ms(L, 300)
L.execute("SOL.x, SOL.y = 7403.5, 8262.5"); run_ms(L, 10000, lf=False)
ck("no LF order state: no yield, the old stall rule still applies", any("leg_stalled" in m for m in logs(L)), [m for m in logs(L) if "SolPlace" in m])

# ---------------------------------------------------------------- gates
if os.path.exists(GATE):
    open(os.path.join(tmp, "SolPlace_patched.lua"), "w", encoding="utf-8", newline="").write(P1)
    r = subprocess.run([sys.executable, GATE, os.path.join(tmp, "SolPlace_patched.lua")], capture_output=True, text=True)
    ck("tonumber gate: the patched SolPlace.lua is clean", r.returncode == 0, (r.stdout + r.stderr)[-300:])
else:
    print("SKIP tonumber gate not found")
ck("ascii only", all(ord(c) < 128 for c in P1))
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
