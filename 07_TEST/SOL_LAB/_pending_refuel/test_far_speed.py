"""Offline test for far_wait_speed on a copy of SolFar.lua: the walk-in wait at 1x, 5x, 20x, 40x and paused. usage: python test_far_speed.py"""
import os, shutil, subprocess, sys, tempfile, re
from lupa import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
LAB = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid"
T = tempfile.mkdtemp(prefix="sol_farspeed_")
cl = os.path.join(T, "1", "2", "3", "4", "5", "6", "client"); os.makedirs(cl); os.makedirs(os.path.join(T, "1", "Lua"))
for f in ("SolFar.lua", "SolAuthority.lua"): shutil.copy(os.path.join(LAB, r"mods\Sol_LAB\42\media\lua\client", f), cl)
shutil.copy(os.path.join(LAB, r"Lua\SolFixes_LAB.txt"), os.path.join(T, "1", "Lua"))
ok_n = bad = 0
def check(name, ok):
    global ok_n, bad
    print(("PASS " if ok else "FAIL ") + name); ok_n += bool(ok); bad += (not ok)
r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s64.py"), cl], capture_output=True, text=True)
check("installer runs", r.returncode == 0)
check("installer is safe twice", subprocess.run([sys.executable, os.path.join(HERE, "apply_s64.py"), cl], capture_output=True, text=True).returncode == 0)
src = open(os.path.join(cl, "SolFar.lua"), encoding="utf-8").read()
check("SolFar compiles", not isinstance(lua51.LuaRuntime().eval("loadstring")(src), tuple))
check("SolAuthority compiles", not isinstance(lua51.LuaRuntime().eval("loadstring")(open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read()), tuple))
# pull the two functions out and run them on a fake wait
body = src[src.index("local SPEED_STEPS"):]
body = body[:body.index("    local tries, mode = wait.tries, wait.mode")] + "end\n"
def wait_after(step, on=True, paused=False, real_ms=10000):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute("SolAuthority = { on = function(n) return n == 'far_wait_speed' and %s end }" % ("true" if on else "false"))
    L.execute("function getGameSpeed() return %d end" % step)
    L.execute("MAX_TICK_MS = 1000; wait = { left = 300000, last = 0 }; function paused() return %s end" % ("true" if paused else "false"))
    L.execute("local MAX_TICK_MS, wait_ = MAX_TICK_MS\n" + body.replace("local function waitTick", "function waitTick"))
    L.execute("for t = 100, %d, 100 do waitTick(t) end" % real_ms)
    return L.eval("wait.left")
check("1x: 10 s real = 10 s off the wait", wait_after(1) == 290000)
check("fast forward 5x: 10 s real = 50 s", wait_after(2) == 250000)
check("fast forward 20x: 10 s real = 200 s", wait_after(3) == 100000)
check("fast forward 40x: 10 s real finishes 5 min", wait_after(4) <= 0)
check("paused: nothing passes", wait_after(4, paused=True) == 300000)
check("switch off: real time as before even at 40x", wait_after(4, on=False) == 290000)
print("RESULT", ok_n, "/", ok_n + bad)
sys.exit(1 if bad else 0)
