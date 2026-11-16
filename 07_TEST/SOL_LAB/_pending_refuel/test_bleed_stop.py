"""Bleeding at the wheel: real SolBleedStop.lua on a mocked game. Offline PASS is not Runtime PASS."""
import os, sys
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
W = r"""
print = function() end
FIXES = { bleed_get_out = true }
SolAuthority = { on = function(n) return FIXES[n] == true end }
SAID, EXITS, STARTS = {}, 0, 0
SolOverlay = { speak = function(_, l) SAID[#SAID + 1] = l end }
CAR = { speed = 0 }
function CAR.getCurrentSpeedKmHour() return CAR.speed end
function CAR.getSeat() return 0 end
S = { x = 10, y = 10, bleed = 1, car = CAR }
function S.getX() return S.x end; function S.getY() return S.y end
function S.getVehicle() return S.car end
function S.getBodyDamage() return { getNumPartsBleeding = function() return S.bleed end } end
ZOMBIES = {}
function getCell() return { getZombieList = function() return { size = function() return #ZOMBIES end, get = function(_, i) return ZOMBIES[i + 1] end } end } end
function zombie(x, y) return { getX = function() return x end, getY = function() return y end, isDead = function() return false end } end
SurvivorCompanion = { Vehicle = { exit = function(a) EXITS = EXITS + 1; S.car = nil; return true end } }
SolUI = { solActor = function() return S end, gps = { dest = { x = 50, y = 50 } } }
function SolUI.gpsStart() STARTS = STARTS + 1; return true, "walking_to_door" end
Events = { OnTick = { Add = function() end } }
"""
def world():
    L = lua51.LuaRuntime(unpack_returned_tuples=True); L.execute(W)
    with open(os.path.join(HERE, "SolBleedStop.lua"), encoding="utf-8") as h: L.execute(h.read())
    return L
L = world(); L.execute("SolUI.solBleedTick(1000)")
ck("just started bleeding: waits a moment", L.eval("EXITS") == 0)
L.execute("SolUI.solBleedTick(4500)")
ck("still bleeding, car stopped, no zombies: gets out", L.eval("EXITS") == 1)
ck("she says why", L.eval("SAID[1]") == "عم نزف، بنزل ضمّد حالي.")
L.execute("SolUI.solBleedTick(6000)")
ck("still bleeding on foot: does not drive yet", L.eval("STARTS") == 0)
L.execute("S.bleed = 0; SolUI.solBleedTick(9000)")
ck("bandaged: back to the same trip", L.eval("STARTS") == 1)
L = world(); L.execute("ZOMBIES[1] = zombie(12, 11); SolUI.solBleedTick(1000); SolUI.solBleedTick(5000)")
ck("a zombie close: stays in the car", L.eval("EXITS") == 0)
L = world(); L.execute("CAR.speed = 30; SolUI.solBleedTick(1000); SolUI.solBleedTick(5000)")
ck("the car is moving: does not jump out", L.eval("EXITS") == 0)
L = world(); L.execute("SolUI.solBleedTick(1000); SolUI.solBleedTick(5000); SolUI.gps.dest = { x = 9, y = 9 }; S.bleed = 0; SolUI.solBleedTick(7000)")
ck("he gave another order meanwhile: no resume", L.eval("STARTS") == 0)
L = world(); L.execute("SolUI.solBleedTick(1000); SolUI.solBleedTick(5000); S.bleed = 0; SolUI.solBleedTick(200000)")
ck("too long ago: no resume", L.eval("STARTS") == 0)
L = world(); L.execute("S.bleed = 0; SolUI.solBleedTick(1000); SolUI.solBleedTick(9000)")
ck("not bleeding: nothing", L.eval("EXITS") == 0)
L = world(); L.execute("FIXES.bleed_get_out = false; SolUI.solBleedTick(1000); SolUI.solBleedTick(9000)")
ck("switch off: nothing", L.eval("EXITS") == 0)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED: " + str(FAIL))
sys.exit(1 if FAIL else 0)
