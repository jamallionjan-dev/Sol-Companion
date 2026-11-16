"""s101 edge_api offline: the patched files compile, the edge-to-square calls find a door/window both ways, the switch off keeps
the old Boolean calls, the installer is idempotent, tonumber + jarcall gates pass. Run: python test_s101_edge_api.py [client dir]"""
import os, sys, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kahlua_env import lua51
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
FAIL, P = [], []
def ck(n, c, d=""): print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d else "")); (P if c else FAIL).append(n)
tmp = tempfile.mkdtemp(prefix="s101_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
for f in os.listdir(CL):
    if f.endswith(".lua"): shutil.copy(os.path.join(CL, f), cl)
for f in ("SolWeaponPick.lua", "SolMagFill.lua"):
    if os.path.exists(os.path.join(HERE, f)): shutil.copy(os.path.join(HERE, f), cl)   # the staged s99 fix, as it will be installed
r1 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s101_edge_api.py"), cl], capture_output=True, text=True)
r2 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s101_edge_api.py"), cl], capture_output=True, text=True)
ck("installer runs", r1.returncode == 0 and "applied" in r1.stdout, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout, r2.stdout)
L = lua51.LuaRuntime()
for f in ("SolEdgeApi.lua", "SCNavigation.lua", "SCTopology.lua", "SolPlace.lua"):
    src = open(os.path.join(cl, f), encoding="utf-8").read()
    ok = L.eval("function(s) local f, e = loadstring(s); return f ~= nil end")(src)
    ck("compiles " + f, ok)
    ck("s101 present in " + f, f == "SolEdgeApi.lua" or "s101" in src)
L.execute('SolAuthority = { on = function(n) return SW[n] == true end }; SW = { edge_api = true }')
L.execute(open(os.path.join(cl, "SolEdgeApi.lua"), encoding="utf-8").read())
L.execute('''
A, B = {}, {}; DOOR, WIN, FR = {}, {}, {}; CALLS = {}
function cf(o, n, a) CALLS[#CALLS + 1] = n
  if n == "getDoor" or n == "getWindow" or n == "getThumpableWindow" or n == "getWindowFrame" then error("No implementation found for function: " .. n) end
  if n == "getDoorTo" and o == B and a == A then return DOOR, true end
  if n == "getWindowTo" and o == A and a == B then return WIN, true end
  if n == "getWindowFrameTo" and o == B and a == A then return FR, true end
  return nil, true end''')
ck("door found from the other square", L.eval('SolEdgeApi.call(cf, A, B, A, "getDoor", true) == DOOR'))
ck("window found from this square", L.eval('SolEdgeApi.call(cf, A, B, A, "getWindow", false) == WIN'))
ck("frame found", L.eval('SolEdgeApi.call(cf, A, B, A, "getWindowFrame", true) == FR'))
ck("thumpable: none -> nil, ok", L.eval('select(2, SolEdgeApi.call(cf, A, B, A, "getThumpableWindow", true)) == true'))
ck("switch on: no Boolean call made", L.eval('(function() for _, n in ipairs(CALLS) do if n == "getDoor" or n == "getWindow" or n == "getWindowFrame" or n == "getThumpableWindow" then return false end end return true end)()'))
L.execute('SW.edge_api = false')
ck("switch off: the old Boolean call (errors as in the game)", L.eval('(pcall(SolEdgeApi.call, cf, A, B, A, "getDoor", true)) == false'))
G = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua")
r = subprocess.run([sys.executable, "-I", os.path.join(G, "tonumber_check.py"), cl], capture_output=True, text=True); ck("tonumber gate", r.returncode == 0, r.stdout[-200:])
r = subprocess.run([sys.executable, "-I", os.path.join(G, "jarcall_check.py"), cl], capture_output=True, text=True); ck("jarcall gate", r.returncode == 0, r.stdout[-300:])
ck("ascii only", all(ord(c) < 128 for c in open(os.path.join(cl, "SolEdgeApi.lua"), encoding="utf-8").read()))
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(P), len(FAIL))); sys.exit(1 if FAIL else 0)
