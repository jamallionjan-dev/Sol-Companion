"""Offline tests for SolTracked.lua, and a smoke test of the real Trucksmith TrackSteer.step on a stub Sol-driven vehicle (read-only).
usage: python test_tracked.py"""
import math, os, sys
from lupa import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
TSF = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\108600\3812497744\mods\Trucksmith\common\media\lua\client\Trucksmith_TrackSteer.lua"
ok_n = bad = 0
def check(name, ok):
    global ok_n, bad
    print(("PASS " if ok else "FAIL ") + name); ok_n += ok; bad += (not ok)

STUBS = r"""
calls = {}
FIX = { tracked_mode = true }
SolAuthority = { on = function(n) return FIX[n] == true end }
NOW = 1000
function getTimestampMs() return NOW end
function instanceof(o, c) return o.kind == c end
local function mkdriver(kind, localp) return { kind = kind, isLocalPlayer = function() return localp end } end
function mkveh(id, driver, tracked)
  return { id = id, driver = driver, tracked = tracked,
    getDriver = function(s) return s.driver end, getId = function(s) return s.id end,
    getScriptName = function(s) return "Base.T" .. s.id end }
end
SOL = mkdriver("IsoPlayer", false)
ME = mkdriver("IsoPlayer", true)
VS = {}
function getCell() return { getVehicles = function() return { iterator = function() local i = 0; return { hasNext = function() return i < #VS end, next = function() i = i + 1; return VS[i] end } end } end } end
Trucksmith = { TrackSteer = {}, Stabilizer = {} }
Trucksmith.TrackSteer.config = function(v) return v.tracked and {} or nil end
Trucksmith.TrackSteer.step = function(tc, v, now) calls[#calls + 1] = "ts" .. v.id; return 0, 5, 0, 1, 2, 3 end
Trucksmith.Stabilizer.config = function(v) return true end
Trucksmith.Stabilizer.numbers = function(c, v) return { n = true } end
Trucksmith.Stabilizer.step = function(n, v, now, cx, cy, cz, yx, yy, yz, ext)
  calls[#calls + 1] = "s" .. v.id .. ":" .. tostring(n and n.n) .. ":" .. cx .. cy .. cz .. ":" .. yx .. yy .. yz .. ":" .. tostring(ext)
end
Events = nil
"""

def fresh():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(STUBS)
    L.execute(open(os.path.join(HERE, "SolTracked.lua"), encoding="utf-8").read())
    return L

L = fresh()
L.execute("VS = { mkveh(1, SOL, true), mkveh(2, ME, true), mkveh(3, SOL, false), mkveh(4, nil, true) }; SolTracked.tick()")
calls = list(L.eval("calls").values())
check("Sol's tracked vehicle is turned", "ts1" in calls)
check("same order and arguments as Trucksmith's own loop (turn, then push with force and torque)", "s1:true:123:050:nil" in calls)
check("a vehicle the player drives is left to Trucksmith", "ts2" not in calls)
check("an ordinary vehicle is never touched", "ts3" not in calls)
check("an empty vehicle is never touched", "ts4" not in calls)

L = fresh()
L.execute("FIX.tracked_mode = false; VS = { mkveh(1, SOL, true) }; SolTracked.tick()")
check("switch off: nothing", len(list(L.eval("calls").values())) == 0)

L = fresh()
L.execute("Trucksmith = nil; VS = { mkveh(1, SOL, true) }; SolTracked.tick()")
check("Trucksmith not loaded: nothing, no error", len(list(L.eval("calls").values())) == 0)

L = fresh()
L.execute("Trucksmith.TrackSteer.step = function() error('boom') end; VS = { mkveh(1, SOL, true) }; SolTracked.tick(); NOW = NOW + 2000; SolTracked.tick()")
check("an error stops it once, with no error thrown into the game", L.eval("SolTracked.failed") is True)

L = fresh()
L.execute("Trucksmith.TrackSteer.step = function() calls[#calls+1]='ts'; return nil end; VS = { mkveh(1, SOL, true) }; SolTracked.tick()")
check("no turn this frame: no push", list(L.eval("calls").values()) == ["ts"])

L = fresh()
L.execute("VS = { mkveh(1, SOL, true) }; SolTracked.tick(); VS[1].driver = ME; NOW = NOW + 10; SolTracked.tick()")
check("the player takes the wheel: Sol's loop lets go at once", list(L.eval("calls").values()).count("ts1") == 1)

# The real TrackSteer.step on a stub vehicle with nobody but Sol: does it turn when the steering is held?
R = lua51.LuaRuntime(unpack_returned_tuples=True)
R.execute(r"""
package = package or {}; package.loaded = package.loaded or {}
function require() end
Trucksmith = { log = function() end, config = function() return { trackSteer = {} } end, Stabilizer = { geometry = function() return { iy = 10, lever = 1.5 } end } }
SandboxVars = {}
local V = {}
V.__index = V
function V.new() return setmetatable({ x_ = 0, y_ = 0, z_ = 0 }, V) end
function V:x() return self.x_ end function V:y() return self.y_ end function V:z() return self.z_ end
function V:set(a, b, c) self.x_, self.y_, self.z_ = a, b, c end
Vector3f = V
STEER = 0.6
veh = { th = 0 }
function veh:getForwardVector(v) v:set(math.cos(self.th), 0, math.sin(self.th)) return v end
function veh:getUpVector(v) v:set(0, 1, 0) return v end
function veh:getId() return 7 end
function veh:getScriptName() return "Base.RKCBradleyM3" end
function veh:getCurrentSteering() return STEER end
function veh:getLinearVelocity(v) v:set(math.cos(self.th) * 3, 0, math.sin(self.th) * 3) return v end
function veh:getScript() return { getSteeringClamp = function() return 0.6 end, getExtents = function() return { x = function() return 3 end, z = function() return 6 end } end } end
function veh:getCurrentSpeedKmHour() return 10.8 end
function veh:isEngineRunning() return true end
function veh:getPartCount() return 0 end
function veh:getMass() return 25000 end
""")
R.execute(open(TSF, encoding="utf-8").read())
first = R.eval("{Trucksmith.TrackSteer.step({}, veh, 1000)}")
out = R.eval("{Trucksmith.TrackSteer.step({}, veh, 1033)}")
vals = [out[i] for i in range(1, 7)] if out and len(out) >= 6 else []
check("real TrackSteer.step gives a turning push for a vehicle no player drives (held steering)", len(vals) == 6 and abs(vals[1]) > 0)
R.execute("STEER = 0")
R.eval("Trucksmith.TrackSteer.step({}, veh, 1066)")
zero = R.eval("{Trucksmith.TrackSteer.step({}, veh, 1099)}")
zy = zero[2] if zero and len(zero) >= 2 else 0
check("real TrackSteer.step: no steering, no turn", zy == 0 or zy is None)
print("RESULT", ok_n, "/", ok_n + bad)
sys.exit(1 if bad else 0)
