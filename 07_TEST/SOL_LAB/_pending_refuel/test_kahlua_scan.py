"""Every Lua file of the lab mod, compiled by the game's own compiler; what the bytecode uses, checked against what the game has.
A new global, a missing library function or a new {...} fails here until someone has looked at it."""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SCAN = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "scan.py")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
r = subprocess.run([sys.executable, SCAN], capture_output=True, encoding="utf-8", errors="replace", cwd=os.path.dirname(SCAN), env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=400)
out = r.stdout
ck("scan ran", r.returncode == 0 and "files=" in out, r.stderr[-300:])
m = re.search(r"compile_errors=(\d+)", out)
ck("every file compiles on the game's compiler", m and m.group(1) == "0", out[:300])
def section(name):
    a = out.find("== %s:" % name)
    if a < 0: return {}
    b = out.find("\n== ", a + 5)
    d = {}
    for l in out[a:b if b > 0 else None].splitlines()[1:]:
        p = l.split()
        if len(p) >= 2: d[p[0]] = l
    return d
# Each one looked at by hand; the reason is why it cannot fail in the game.
GLOBALS = {"Events": "the game's event table", "MapItem": "exposed by the game outside the scanned list", "UIWorldMap": "same", "SCBridge": "our own jar", "SCSplitScreenProbe": "our own jar", "passableEdge": "a hook only tests call"}
LIBS = {"os.clock": "only after getTimestampMs is missing, which the game always has", "math.random": "only after ZombRand is missing", "table.unpack": "written as table.unpack or unpack"}
g = section("global_unknown")
ck("no unknown global", set(g) <= set(GLOBALS), {k: g[k] for k in set(g) - set(GLOBALS)})
ck("next() is not called anywhere", "next" not in g)
l = section("lib_missing")
ck("no missing library function", set(l) <= set(LIBS), {k: l[k] for k in set(l) - set(LIBS)})
VT = 7
v = section("vararg_table")
n = sum(int(re.search(r"x(\d+)", s).group(1)) for s in v.values())
ck("the {...} sites are the %d reviewed" % VT, n == VT, n)
ck("no gsub result goes into tonumber", not section("multret_into_tonumber").get("string.gsub") and not section("multret_into_tonumber").get(":gsub"))
LIVE = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED")
sys.exit(1 if FAIL else 0)
