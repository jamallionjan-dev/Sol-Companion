"""Offline tests for farm_night on copies (lab SolFarmWork and the staged spatial_access one). usage: python test_farm_night.py"""
import os, shutil, subprocess, sys, tempfile
from lupa import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
LAB = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid"
ok_n = bad = 0
def check(name, ok):
    global ok_n, bad
    print(("PASS " if ok else "FAIL ") + name); ok_n += bool(ok); bad += (not ok)

for label, src in (("lab", os.path.join(LAB, r"mods\Sol_LAB\42\media\lua\client\SolFarmWork.lua")), ("staged", os.path.join(HERE, "SolFarmWork.lua"))):
    if not os.path.exists(src): continue
    T = tempfile.mkdtemp(prefix="sol_night_")
    cl = os.path.join(T, "1", "2", "3", "4", "5", "6", "client"); os.makedirs(cl); os.makedirs(os.path.join(T, "1", "Lua"))
    shutil.copy(src, os.path.join(cl, "SolFarmWork.lua"))
    shutil.copy(os.path.join(LAB, r"mods\Sol_LAB\42\media\lua\client\SolAuthority.lua"), cl)
    shutil.copy(os.path.join(LAB, r"Lua\SolFixes_LAB.txt"), os.path.join(T, "1", "Lua"))
    r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s73_farm_night.py"), cl], capture_output=True, text=True)
    check(label + ": installer runs", r.returncode == 0)
    check(label + ": installer safe twice", subprocess.run([sys.executable, os.path.join(HERE, "apply_s73_farm_night.py"), cl], capture_output=True, text=True).returncode == 0)
    for f in ("SolFarmWork.lua", "SolFarmNight.lua", "SolAuthority.lua"):
        check(label + ": compiles " + f, not isinstance(lua51.LuaRuntime().eval("loadstring")(open(os.path.join(cl, f), encoding="utf-8").read()), tuple))
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute("SolUI = {}; SolFarmPlan = {}; SolFarmWork = {}; Events = nil; ModData = nil")
    L.execute(open(os.path.join(cl, "SolFarmWork.lua"), encoding="utf-8").read())
    plants = "{ { x = 1, y = 1, z = 0, state = 'seeded', health = 50, water = 10, need = 80, exterior = true, nb = 2, crop = 'Carrots' } }"
    env = "{ raining = false, day = false, nightOk = %s, player = { x = 50, y = 50, z = 0 }, skill = 0 }"
    stock = "{ cans = 2, foodStorage = 1 }"
    L.execute("SolFarmPlan.waterDoses = SolFarmPlan.waterDoses or function() return 1 end")
    t_ok = L.eval("SolFarmPlan.next(%s, %s, %s, {})" % (plants, stock, env % "true"))
    t_no = L.eval("SolFarmPlan.next(%s, %s, %s, {})" % (plants, stock, env % "false"))
    task_ok = t_ok[0] if isinstance(t_ok, tuple) else t_ok
    task_no, blocked = (t_no[0], t_no[1]) if isinstance(t_no, tuple) else (t_no, None)
    check(label + ": night with a light: she waters the outdoor plant", task_ok is not None and task_ok["op"] == "water")
    check(label + ": night, light not ready yet: outdoor plant waits (dark)", task_no is None and blocked is not None and blocked["dark"] is not None)

# the light helper on its own
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("""
SolAuthority = { on = function(n) return n == 'farm_night' end }
NOW = 0; function getTimestampMs() return NOW end
local function jl(t) return { size = function() return #t end, get = function(_, i) return t[i + 1] end } end
function light(on) return { act = false, canBeActivated = function() return true end, getLightStrength = function() return 0.8 end,
  getCurrentUsesFloat = function() return on and 0.5 or 0 end, isActivated = function(s) return s.act end, setActivated = function(s, v) s.act = v end,
  getContainer = function(s) return s.cont end } end
SOL = { inv = { items = {} } }
function SOL.inv:getItems() return jl(self.items) end
function SOL:getInventory() return self.inv end
function SOL:getPrimaryHandItem() return self.p end
function SOL:getSecondaryHandItem() return self.s end
function SOL:setSecondaryHandItem(i) self.s = i end
function SOL:getX() return 1 end function SOL:getY() return 1 end
SolUI = { solActor = function() return SOL end, invLast = function() return { places = {} } end }
SAID = {}
SurvivorCompanion = { GameplayUtil = { say = function(a, t) SAID[#SAID + 1] = t end, transferItemVerified = function() return true end } }
""")
L.execute(open(os.path.join(HERE, "SolFarmNight.lua"), encoding="ascii").read())
check("day: nothing to do", L.eval("SolFarmNight.ensure(SOL, false)") == "day")
check("night, no light anywhere: works anyway, says it once", L.eval("SolFarmNight.ensure(SOL, true)") == "none" and L.eval("#SAID") == 1)
L.execute("SolFarmNight.ensure(SOL, true)")
check("the no-light line is said once only", L.eval("#SAID") == 1)
L.execute("local l = light(true); l.cont = SOL.inv; SOL.inv.items = { l }; ST = SolFarmNight.ensure(SOL, true)")
check("light in her bag: put in her hand and switched on", L.eval("ST") == "ready" and L.eval("SOL.s ~= nil and SOL.s.act == true"))
L.execute("SOL.s = nil; local e = light(false); e.cont = SOL.inv; SOL.inv.items = { e }; ST2 = SolFarmNight.ensure(SOL, true)")
check("a flashlight with a dead battery does not count", L.eval("ST2") == "none")
check("her line has no system words", all(w not in L.eval("SAID[1]") for w in ("java", "switch", "farm_night")))
print("RESULT", ok_n, "/", ok_n + bad)
sys.exit(1 if bad else 0)
