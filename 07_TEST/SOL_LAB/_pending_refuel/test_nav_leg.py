"""SolNavLeg.lua on mocks: when it starts, each stage, and every way it ends."""
import os, sys
from kahlua_env import lua51
C = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SolNavLeg.lua")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("""
NOW = 1000; print = function() end; TICK = nil
function getTimestampMs() return NOW end
Events = { OnTick = { Add = function(f) TICK = f end } }
ON = true; SolAuthority = { on = function(n) return ON and n == "java_nav" end }
SOL = {}; CX, CY = 100, 100; ENGINE = true; ENGINEON = 0
FV = { x = function() return 1 end, z = function() return 0 end }
Vector3f = { new = function() return FV end }
CAR = { getX = function() return CX end, getY = function() return CY end, getDriver = function() return DRIVER end, getForwardVector = function(s, v) return v end, isEngineRunning = function() return ENGINE end }
DRIVER = SOL
function SOL.getVehicle() return SEATED end
SEATED = CAR
SolBypass = { measure = function() return { wheelbase = 2.5, kmax = 0.45 } end }
ST = { result = "arrived", phase = "arrived" }
SolUI = { solActor = function() return SOL end, gps = {}, gpsStatus = function() return ST end, solEngine = function() ENGINEON = ENGINEON + 1 end }
PLANS, FOLLOWS, STOPS, BEATS, STATE, PLAN_OK = 0, 0, 0, 0, "idle", true
function solNavLeg(v, x, y, hx, hy, dx, dy, wb, k) PLANS = PLANS + 1; LAST = { x, y, dx, dy, wb, k }; return PLAN_OK end
function solNavState() return STATE end
function solNavFollow() FOLLOWS = FOLLOWS + 1; return FOLLOW_OK ~= false end
function solNavStop() STOPS = STOPS + 1 end
function solNavBeat() BEATS = BEATS + 1 end
function DEST(x, y, name) SolUI.gps.dest = { x = x, y = y, name = name or "Map point" } end
""")
L.execute(open(C, encoding="utf-8").read()); g = L.globals()
def step(ms=300): g.NOW = g.NOW + ms; g.TICK()
def fresh(x=129, y=100, name=None):
    L.execute('PLANS, FOLLOWS, STOPS, BEATS, STATE, PLAN_OK, FOLLOW_OK = 0, 0, 0, 0, "idle", true, nil; CX, CY = 100, 100; ST = { result = "arrived", phase = "arrived" }; ON = true; ENGINE = true; ENGINEON = 0; SEATED = CAR; DRIVER = SOL')
    if x is not None: L.execute('DEST(%d, %d%s)' % (x, y, ', "%s"' % name if name else ''))
    step()
def clean():
    """Ends any trip the last test left running, so tests do not depend on one another."""
    L.execute('SolUI.gps.dest = nil; ST = { result = "stopped" }'); step(); L.execute('ST = { result = "arrived", phase = "arrived" }'); step()

fresh(); ck("road stopped 29 short: starts a stage", g.PLANS == 1 and list(g.LAST.values()) == [100, 100, 129, 100, 2.5, 0.45], list(g.LAST.values()) if g.LAST else None)
L.execute('STATE = "capturing"'); step(); ck("waits while it draws", g.FOLLOWS == 0)
L.execute('STATE = "ready"'); step(); ck("follows when drawn", g.FOLLOWS == 1)
L.execute('STATE = "following"'); b0 = g.BEATS; step(16); step(16); step(16); ck("heartbeat every frame", g.BEATS == b0 + 3, g.BEATS - b0)
L.execute('STATE = "done"; CX = 115'); step(); ck("stage done, still far: next stage from here", g.PLANS == 2 and g.LAST[1] == 115, g.PLANS)
L.execute('STATE = "ready"'); step(); L.execute('STATE = "done"; CX = 127.5'); step(); ck("close enough: finished", g.PLANS == 2 and g.STOPS >= 1, g.PLANS)
p0 = g.PLANS; step(); step(); ck("once done, it stays done", g.PLANS == p0)
clean(); fresh(101, 101); ck("already there: nothing", g.PLANS == 0, g.PLANS)
clean(); fresh(129, 100, "Gas station gas2go"); ck("a fuel stop is left to the errand", g.PLANS == 0, g.PLANS)
clean(); L.execute('SolAuthority.on = function() return false end'); fresh(); ck("switched off: nothing", g.PLANS == 0, g.PLANS); L.execute('SolAuthority.on = function(n) return ON and n == "java_nav" end'); clean()
L.execute('ST = { result = "failed", reason = "x" }; DEST(140, 100)'); L.execute('PLANS = 0'); step(); ck("road route failed: not started here", g.PLANS == 0, g.PLANS); clean()
L.execute('ST = { phase = "following" }; DEST(150, 100); PLANS = 0'); step(); ck("still driving: nothing", g.PLANS == 0); clean()
L.execute('PLANS = 0; SEATED = nil; DEST(160, 100)'); step(); ck("not in a car: nothing", g.PLANS == 0, g.PLANS); L.execute('SEATED = CAR'); clean()
L.execute('PLANS = 0; DRIVER = {}; DEST(161, 100)'); step(); ck("not driving it: nothing", g.PLANS == 0, g.PLANS); L.execute('DRIVER = SOL'); clean()
fresh(170, 100); L.execute('STATE = "failed:out_of_time"'); s0 = g.STOPS; step(); ck("a failed stage tries once more", g.PLANS == 2 and g.STOPS == s0 + 1, g.PLANS); step(); ck("second failure: gives up", g.PLANS == 2, g.PLANS)
p0 = g.PLANS; step(); ck("given up: stays quiet for this destination", g.PLANS == p0); clean()
fresh(171, 100); L.execute('STATE = "capturing"'); g.NOW = g.NOW + 7000; g.TICK(); ck("plan too slow: tries again", g.PLANS == 2, g.PLANS); clean()
fresh(172, 100); L.execute('PLAN_OK = false; STATE = "done"; CX = 110'); step(); p0 = g.PLANS; step(); ck("cannot plan: ends", g.PLANS == p0); clean()
fresh(173, 100); L.execute('STATE = "ready"; FOLLOW_OK = false'); step(); p0 = g.PLANS; step(); ck("follower refused: ends", g.PLANS == p0); clean()
fresh(180, 100); L.execute('STATE = "following"; DEST(190, 100)'); s0 = g.STOPS; step(); ck("new destination: drops the old stage", g.STOPS >= s0, g.STOPS); clean()
fresh(181, 100); L.execute('STATE = "following"; SEATED = nil'); step(); p0 = g.PLANS; step(); ck("she got out: ends", g.PLANS == p0); L.execute("SEATED = CAR"); clean()
fresh(182, 100); L.execute('STATE = "following"; ST = { result = "stopped" }'); step(); p0 = g.PLANS; step(); ck("he pressed stop: ends", g.PLANS == p0); clean()
L.execute('ENGINE = false; PLANS = 0; ENGINEON = 0; DEST(184, 100)'); step(); ck("engine off: started", g.ENGINEON == 1, g.ENGINEON); L.execute('ENGINE = true'); clean()
L.execute('solNavLegS = solNavLeg; solNavLeg = nil; PLANS = 0; DEST(185, 100)'); step(); ck("Java missing: nothing", g.PLANS == 0); L.execute('solNavLeg = solNavLegS'); clean()
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %s" % FAIL)
sys.exit(1 if FAIL else 0)
