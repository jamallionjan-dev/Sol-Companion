"""Offline test for dot_paused_fix on a copy of SolFar.lua. usage: python test_dot.py"""
import os, shutil, subprocess, sys, tempfile
from lupa import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
LAB = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid"
T = tempfile.mkdtemp(prefix="sol_dot_")
cl = os.path.join(T, "1", "2", "3", "4", "5", "6", "client"); os.makedirs(cl); os.makedirs(os.path.join(T, "1", "Lua"))
for f in ("SolFar.lua", "SolAuthority.lua"): shutil.copy(os.path.join(LAB, r"mods\Sol_LAB\42\media\lua\client", f), cl)
shutil.copy(os.path.join(LAB, r"Lua\SolFixes_LAB.txt"), os.path.join(T, "1", "Lua"))
ok_n = bad = 0
def check(name, ok):
    global ok_n, bad
    print(("PASS " if ok else "FAIL ") + name); ok_n += bool(ok); bad += (not ok)
r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s68_dot.py"), cl], capture_output=True, text=True)
check("installer runs", r.returncode == 0)
check("installer safe twice", subprocess.run([sys.executable, os.path.join(HERE, "apply_s68_dot.py"), cl], capture_output=True, text=True).returncode == 0)
src = open(os.path.join(cl, "SolFar.lua"), encoding="utf-8").read()
check("SolFar compiles", not isinstance(lua51.LuaRuntime().eval("loadstring")(src), tuple))
check("SolAuthority compiles", not isinstance(lua51.LuaRuntime().eval("loadstring")(open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read()), tuple))
def run(on, paused_ms, sol=True):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute("""
    NOW = 1000000
    function getTimestampMs() return NOW end
    SolAuthority = { on = function(n) return n == 'dot_paused_fix' and %s end }
    ALIVE = 1000000
    function getFileReader() return { readLine = function() return 't=' .. ALIVE end, close = function() end } end
    SolUI = { solActor = function() return %s end }
    Events = nil
    """ % ("true" if on else "false", "{ getCurrentSquare = function() return {} end }" if sol else "nil"))
    L.execute(src)
    # game running: tick reads the heartbeat; then the game pauses: no tick, the Mind keeps writing
    L.execute("NOW = NOW + 1000; ALIVE = NOW")
    L.execute("for i = 1, %d do NOW = NOW + 1000; ALIVE = NOW end" % (paused_ms // 1000))
    return L.eval("SolUI.solDotState()")
check("game paused 60 s, Mind alive, fix on: dot stays green", run(True, 60000) == "on")
check("game paused 60 s, fix off: grey as before (shows the bug)", run(False, 60000) == "off")
check("no Sol and no far record: grey", run(True, 1000, sol=False) == "off")
print("RESULT", ok_n, "/", ok_n + bad)
sys.exit(1 if bad else 0)
