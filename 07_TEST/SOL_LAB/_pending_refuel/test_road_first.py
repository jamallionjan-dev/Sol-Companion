"""She keeps to the road: real SolRoadFirst.lua on a mocked game. Offline PASS is not Runtime PASS."""
import os, sys
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
WORLD = r"""
print = function() end
FIXES = { road_first = true }
SolAuthority = { on = function(n) return FIXES[n] == true end }
KINDS, CARS = {}, {}
SolBypass = { world = { kind = function(x, y) return KINDS[x .. ":" .. y] or false end, cars = function() return CARS end } }
J = {}
CAR = {}
PTS = {}
function solNavCorridorClear() PTS = {}; CLEARED = true end
function solNavCorridorPoint(x, y) PTS[#PTS + 1] = x .. "," .. y end
function solNavCorridorRadius(r) RAD = r end
"""
def world():
    L = lua51.LuaRuntime(unpack_returned_tuples=True); L.execute(WORLD)
    with open(os.path.join(HERE, "SolRoadFirst.lua"), encoding="utf-8") as h: L.execute(h.read())
    return L
L = world()
ck("one look is not enough", L.eval("SolRoadFirst.seen(J, 10, 10, 1000)") is False)
ck("two looks are not enough", L.eval("SolRoadFirst.seen(J, 10, 10, 1700)") is False)
ck("three looks at the same place: a real obstacle", L.eval("SolRoadFirst.seen(J, 10, 11, 2400)") is True)
L = world(); L.execute("for i = 0, 3 do LAST = SolRoadFirst.seen(J, 10 + i * 8, 10, 1000 + i * 700) end")
ck("something moving down the road never counts", L.eval("LAST") is False)
L = world(); L.execute("SolRoadFirst.seen(J, 10, 10, 1000); SolRoadFirst.seen(J, 10, 10, 1700)")
ck("a long gap starts the count again", L.eval("SolRoadFirst.seen(J, 10, 10, 9000)") is False)
S = "{ blockedX = 20.5, blockedY = 20.5 }"
L = world(); ck("nothing at the stopping point: no other street", L.eval("SolRoadFirst.mayReroute(J, %s, CAR)" % S) is False)
L = world(); L.execute("KINDS['20:21'] = 'solid'"); ck("a wall or wreck there: one other street", L.eval("SolRoadFirst.mayReroute(J, %s, CAR)" % S) is True)
ck("still shut: a second street", L.eval("SolRoadFirst.mayReroute(J, %s, CAR)" % S) is True)
ck("never a third street on one drive", L.eval("SolRoadFirst.mayReroute(J, %s, CAR)" % S) is False)
L = world(); L.execute("KINDS['30:30'] = 'solid'"); ck("a wall further off does not count", L.eval("SolRoadFirst.mayReroute(J, %s, CAR)" % S) is False)
L = world(); L.execute("CARS[1] = { v = {} }"); ck("another car there counts", L.eval("SolRoadFirst.mayReroute(J, %s, CAR)" % S) is True)
L = world(); L.execute("CARS[1] = { v = CAR }"); ck("her own car does not count", L.eval("SolRoadFirst.mayReroute(J, %s, CAR)" % S) is False)
L = world(); L.execute("FIXES.road_first = false"); ck("switch off: as before", L.eval("SolRoadFirst.mayReroute(J, %s, CAR)" % S) is True)
L = world(); L.execute("J.route = { points = { {x=1,y=1}, {x=20,y=1}, {x=500,y=1} } }; SolRoadFirst.sendCorridor(J, 5, 1)")
ck("the corridor is the road near her", L.eval("#PTS") == 2 and L.eval("RAD") == 10, L.eval("#PTS"))
L = world(); L.execute("FIXES.road_first = false; J.route = { points = { {x=1,y=1} } }; SolRoadFirst.sendCorridor(J, 5, 1)")
ck("switch off: no corridor", L.eval("#PTS") == 0 and L.eval("CLEARED") is True)
L = world(); L.execute("J.jnavFails = 1; J.route = { points = { {x=1,y=1}, {x=20,y=1} } }; SolRoadFirst.sendCorridor(J, 5, 1)")
ck("no way round near the road: she may look wider", L.eval("#PTS") == 0 and L.eval("CLEARED") is True)
L = world()
ck("a paved route that ends at the place serves it", L.eval("SolRoadFirst.reaches({ {x=0,y=0}, {x=100,y=100} }, {x=108,y=108})") is True)
ck("a house up a dirt lane: the paved route does not serve it", L.eval("SolRoadFirst.reaches({ {x=0,y=0}, {x=100,y=100} }, {x=130,y=100})") is False)
d = L.eval("SolRoadFirst.routeDetail({ {x=1,y=1,width=5}, {x=1.2,y=1,width=70}, {x=-3,y=1,width=2} })")
ck("the refused route is described", d.startswith("points=3 outside=1 width=2.0..70.0") or d.startswith("points=3 outside=1 width=2..70"), d)
ck("no points", L.eval("SolRoadFirst.routeDetail(nil)") == "no points")
L = world()
L.execute("R = SolRoadFirst.spaced({ {x=10,y=10,width=8}, {x=10.03,y=10,width=8} })")
ck("nothing left to drive: still a route the bridge accepts", L.eval("#R") == 2 and L.eval("math.abs(R[2].x - 11) < 0.01"), L.eval("R[2].x"))
L.execute("R = SolRoadFirst.spaced({ {x=0,y=0}, {x=0.1,y=0}, {x=5,y=0}, {x=5.1,y=0} })")
ck("points too close are dropped, the end is kept", L.eval("#R") == 2 and L.eval("R[2].x") == 5.1, L.eval("#R"))
L.execute("R = SolRoadFirst.spaced({ {x=0,y=0}, {x=5,y=0}, {x=9,y=0} })")
ck("a normal route is untouched", L.eval("#R") == 3)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED: " + str(FAIL[:8]))
sys.exit(1 if FAIL else 0)
