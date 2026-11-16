"""Sol on ladders: real SolLadders.lua on a mocked game. Offline PASS is not Runtime PASS."""
import os, sys
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
CL = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
WORLD = r"""
print = function() end
FIXES = { sol_ladders = true }
SolAuthority = { on = function(n) return FIXES[n] == true end }
Events = { OnTick = { Add = function() end } }
SAID = {}
SolOverlay = { speak = function(a, line) SAID[#SAID + 1] = line end }
IsoPropertyType = { LADDER_N = "N", LADDER_S = "S", LADDER_E = "E", LADDER_W = "W" }
GRID = {}
function sq(x, y, z, o) o = o or {}
    local s = { x = x, y = y, z = z, o = o }
    function s.getX() return x end; function s.getY() return y end; function s.getZ() return z end
    function s.getLadder() return o.ladder end; function s.getLadderUnder() return o.under end
    GRID[x .. ":" .. y .. ":" .. z] = s; return s end
function getCell() return { getGridSquare = function(_, x, y, z) return GRID[x .. ":" .. y .. ":" .. z] end } end
ACTOR = { attackers = 0 }
function ACTOR.getClimbLadder(_, s) return s.getLadder() end
function ACTOR.getClimbLadderDown(_, s) return s.getLadderUnder() end
function ACTOR.getSurroundingAttackingZombies() return ACTOR.attackers end
function prop(k) return { getProperties = function() return { has = function(_, v) return v == k end } end } end
function W(src, goal, t) return SolLadders.walkGoal(ACTOR, STATE, src, goal, t) end
function C(src, goal, t) return SolLadders.climbHere(ACTOR, STATE, src, goal, t) end
STATE = {}
"""
def world():
    L = lua51.LuaRuntime(unpack_returned_tuples=True); L.execute(WORLD)
    with open(os.path.join(CL, "SolLadders.lua"), encoding="utf-8") as h: L.execute(h.read())
    L.execute("SRC = sq(0, 0, 0); GOAL = sq(5, 5, 1); BASE = sq(4, 4, 0, { ladder = prop('N') }); TOP = sq(4, 3, 1, { under = prop('S') }); ROOF = sq(9, 9, 1); LOW = sq(9, 9, 0)")
    return L
L = world()
ck("same floor: nothing to do", L.eval("W(SRC, LOW, 99999)") is None)
ck("different floor: the normal way gets its chance first", L.eval("W(SRC, GOAL, 1000)") is None)
ck("after the wait: walk to the ladder", L.eval("W(SRC, GOAL, 7000) == BASE"))
ck("not at the ladder yet: no climb", L.eval("C(SRC, GOAL, 7000)") is None)
ck("at the ladder: not walked to again", L.eval("W(BASE, GOAL, 7000)") is None)
ck("at the ladder: climbs up", L.eval("(function() local r = C(BASE, GOAL, 7000); return r ~= nil and r.down == false end)()"))
L = world(); L.execute("W(ROOF, LOW, 1000); TARGET = W(ROOF, LOW, 7000)")
ck("from the roof: walk to the top of the ladder", L.eval("TARGET == TOP"))
L.execute("R = C(TOP, LOW, 7000)")
ck("at the top: climbs down", L.eval("R ~= nil and R.down == true"))
ck("at the top: stands where the game stands for a south ladder", L.eval("R.x == 4.5 and R.y == 3.2"), L.eval("R.x"))
L = world(); L.execute("BASE.o.ladder = nil; W(SRC, GOAL, 1000)")
ck("no ladder near: nothing, the normal way stays", L.eval("W(SRC, GOAL, 7000)") is None)
L = world(); L.execute("ACTOR.attackers = 1; W(SRC, GOAL, 1000)")
ck("zombies on her: no ladder", L.eval("W(SRC, GOAL, 7000)") is None)
L = world(); L.execute("FIXES.sol_ladders = false; W(SRC, GOAL, 1000)")
ck("switch off", L.eval("W(SRC, GOAL, 7000)") is None)
L = world(); L.execute("W(SRC, GOAL, 1000); W(SRC, GOAL, 7000)")
ck("cannot reach it: gives up", L.eval("W(SRC, GOAL, 33000)") is None)
ck("cannot reach it: says so", L.eval("#SAID") == 1 and L.eval("SAID[1]") == "ما قدرت إطلع عالسلم.", L.eval("SAID[1]"))
ck("after giving up: leaves it alone for a while", L.eval("W(SRC, GOAL, 40000)") is None)
ck("after the pause: tries again", L.eval("W(SRC, GOAL, 70000) == BASE"))
L = world(); L.execute("W(SRC, GOAL, 1000); for i = 1, 3 do C(BASE, GOAL, 7000 + i) end; LAST = C(BASE, GOAL, 8000)")
ck("climb keeps failing: stops after three", L.eval("LAST") is None and L.eval("#SAID") == 1)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED: " + str(FAIL[:8]))
sys.exit(1 if FAIL else 0)
