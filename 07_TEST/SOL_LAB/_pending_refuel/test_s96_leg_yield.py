"""s96 leg_yield offline: s85's replays still pass after s96; base_duty with a moving serial no longer ends a leg (live 10:37:31);
his stay during base_duty still ends it. Run: python test_s96_leg_yield.py [client dir]. Offline PASS is not Runtime PASS."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
tmp = tempfile.mkdtemp(prefix="s96_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
for f in ("SolPlace.lua", "SolAuthority.lua", "SolActions.lua"): shutil.copy(os.path.join(CL, f), cl)
for s in ("apply_s85_place_leg_arrive.py", "apply_s96_leg_yield.py"):
    r = subprocess.run([sys.executable, os.path.join(HERE, s), cl], capture_output=True, text=True)
    ck("installer " + s, r.returncode == 0, r.stdout + r.stderr)
r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s96_leg_yield.py"), cl], capture_output=True, text=True)
ck("s96 second run changes nothing", r.returncode == 0 and r.stdout.count("kept") == 2, r.stdout)
P = open(os.path.join(cl, "SolPlace.lua"), encoding="utf-8", newline="").read()
r = subprocess.run([sys.executable, os.path.join(HERE, "test_s85_place_leg_arrive.py"), cl], capture_output=True, text=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
fails85 = [l for l in r.stdout.splitlines() if l.startswith("FAIL") and "installer" not in l]
ck("s85's replays all still pass on the s96 file", not fails85, fails85 or r.stdout[-400:])
ENV = r"""
NOW = 1000
function getTimestampMs() return NOW end
LOGS = {}
function print(m) LOGS[#LOGS + 1] = tostring(m) end
SW = { spatial_access = true, place_leg_arrive = true }
SolAuthority = { on = function(f) return SW[f] == true end }
W = {}
function W.standable(x, y, z) return x > 7380 and x < 7440 and y > 8220 and y < 8280 end
function W.edge(x, y, z, dir)
    if dir == "W" and x == 7420 and y > 8220 and y < 8280 then if y == 8240 then return "door", { open = false } end return "wall" end
    return "open"
end
SOL = { x = 7415.5, y = 8248.5, z = 0 }
function SOL:getX() return self.x end
function SOL:getY() return self.y end
function SOL:getZ() return self.z end
function SOL:getVehicle() return nil end
ST = { order = "base_duty", commandSerial = 70 }
SENT = {}
SurvivorCompanion = { Commands = { peek = function(a) return ST end } }
SolUI = { solActor = function() return SOL end }
-- as live: the sort's walk on base_duty keeps the order name, LF's duty work bumps the serial
SolUI.solGoto = function(x, y, z) SENT[#SENT + 1] = { x = x, y = y }; ST.commandSerial = ST.commandSerial + 1; return true, "walking" end
Events = nil
"""
def fresh(on=True):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV); L.execute(P); L.execute("SolPlace.install(); SolPlace.setWorld(W)")
    L.execute("SW.place_leg_arrive = %s" % ("true" if on else "false"))
    return L
def logs(L): s = L.eval("LOGS"); return [s[i] for i in range(1, len(s) + 1)]
def run_ms(L, ms, step=100):
    for _ in range(ms // step):
        L.execute("NOW = NOW + %d" % step); L.execute("SolPlace.tick(4)")
L = fresh()
L.execute("SolUI.solGoto(7427, 8238, 0)"); run_ms(L, 500)
ck("route through the door built", any("route 7415,8248 -> 7427,8238" in m for m in logs(L)), logs(L))
L.execute("SOL.x, SOL.y = 7416.5, 8247.5"); run_ms(L, 300)
L.execute("ST.commandSerial = ST.commandSerial + 3"); run_ms(L, 300)      # base_duty's own work moves the serial
lg = logs(L)
ck("base_duty, serial moved: the leg does NOT end (live 10:37:31 fault gone)", not any("ended by another order" in m for m in lg) and L.eval("SolPlace.R") is not None, lg)
L.execute("ST.order = 'stay'; ST.commandSerial = ST.commandSerial + 1"); run_ms(L, 300)
ck("his stay during base_duty: the leg ends", any("ended by another order (stay)" in m for m in logs(L)), logs(L))
ck("ascii only", all(ord(c) < 128 for c in P))
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
if os.path.exists(GATE):
    open(os.path.join(tmp, "p.lua"), "w", encoding="utf-8", newline="").write(P)
    r = subprocess.run([sys.executable, GATE, os.path.join(tmp, "p.lua")], capture_output=True, text=True)
    ck("tonumber gate", r.returncode == 0, r.stdout[-200:])
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
