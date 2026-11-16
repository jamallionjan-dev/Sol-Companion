"""Offline tests for the Kahlua tonumber gate (05_TOOLS/sol_kahlua/tonumber_check.py), the shim (kahlua_shim.lua)
and the s75 one-value installer (apply_s75_onevalue.py). Read-only on the lab; the installer runs on a temp copy.
usage: python test_tonumber_gate.py"""
import glob, os, re, shutil, subprocess, sys, tempfile
from lupa import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua")
sys.path.insert(0, TOOLS)
import tonumber_check as G
CLIENT = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
ok_n = bad = 0
def check(name, ok, info=""):
    global ok_n, bad
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  " + str(info)[:400])); ok_n += bool(ok); bad += (not ok)

def issues(src):
    return [(s["line"], s["issue"]) for s in G.sites("t.lua", src)]

# the 2026-11-10 miss: a one-line function before call() swallowed it in the old regex gate
MISS = '''local function log(m) print("[x] " .. tostring(m)) end
local function call(o, name, ...)
    local ok, a, b = pcall(o[name], o, ...)
    if ok then return a, b end
    return nil
end
local max = tonumber(call(w, "getMaxAmmo")) or 0
'''
old_re = r"local function (\w+)\([^)]*\)(.*?)\nend"
check("the old regex never isolates call() after a one-line function (why the gate missed it)",
      [m.group(1) for m in re.finditer(old_re, MISS, re.S)] == ["log"])
check("new gate: flags tonumber(call(...)) there", issues(MISS) == [(7, "multi")], issues(MISS))

check("multi: f(), o:m(), a.b.c(), f\"s\", f{...}, ... , chained call",
      [i for _, i in issues('tonumber(f())\ntonumber(o:m(1))\ntonumber(a.b.c(x, y))\ntonumber(f"5")\ntonumber(f{1})\ntonumber(...)\ntonumber(U().config("k"))\n')] == ["multi"] * 7)
check("single: (f()), a and f() or 0, x .. f(), -f(), #t, name, t.x, t[f()], literal, table, not f()",
      issues('tonumber((f()))\ntonumber(a and f() or 0)\ntonumber(x .. f())\ntonumber(-f())\ntonumber(#t)\ntonumber(x)\n'
             'tonumber(t.x)\ntonumber(t[f()])\ntonumber("5")\ntonumber({})\ntonumber(not f())\ntonumber(f() + 1)\n') == [])
check("base: literal ok, variable / call / nil flagged", [i for _, i in issues('tonumber(s, 16)\ntonumber(s, b)\ntonumber(s, f())\ntonumber(s, nil)\ntonumber(f(), 10)\n')] == ["base"] * 3)
check("comments, strings and long strings are not code",
      issues('-- tonumber(f())\n--[[ tonumber(f())\n]] local s = "tonumber(f())" .. [==[\ntonumber(f())]==] .. \'tonumber(g())\'\n') == [])
check("fields and definitions are not the global: M.tonumber(f()), o:tonumber(f()), local function tonumber(v)",
      issues('M.tonumber(f())\no:tonumber(f())\nlocal function tonumber(v) return v end\n') == [])
check("multi-line call and line numbers", issues('local x = 1\nlocal y = tonumber(\n  call(a,\n "b"))\n') == [(2, "multi")])
check("nested: both wrapped correctly", G.wrapped('tonumber(f(tonumber(g())))') == 'tonumber((f(tonumber((g())))))')
check("wrapped() leaves safe sites alone and is idempotent", G.wrapped(G.wrapped('a = tonumber(f()) + tonumber((g())) + tonumber(x)')) == 'a = tonumber((f())) + tonumber((g())) + tonumber(x)')
check("escaped quotes inside strings", issues('local s = "a\\"tonumber(f())" x = tonumber(f())\n') == [(1, "multi")])
check("a function literal argument is one value", issues('tonumber(function() return 1, 2 end)\n') == [])

# shim: behaves like Kahlua's BaseLib.tonumber on the bad paths
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(open(os.path.join(TOOLS, "kahlua_shim.lua"), encoding="ascii").read())
L.execute("function two() return 5, nil end function none() end function one() return '7' end")
def refused(expr):
    return L.eval("(function() return pcall(function() return " + expr + " end) end)()")[0] is False
check("shim: tonumber(two()) refused (Kahlua: Double cannot be cast to String)", refused("tonumber(two())"))
check("shim: tonumber(none()) refused (Kahlua: Not enough arguments)", refused("tonumber(none())"))
check("shim: tonumber('ff', nil) refused (Kahlua returns nil silently)", refused("tonumber('ff', nil)"))
check("shim: one value and string+number base still work",
      L.eval("tonumber((two()))") == 5 and L.eval("tonumber(one())") == 7 and L.eval("tonumber('ff', 16)") == 255 and L.eval("tonumber((none()))") is None)
check("shim counts refusals", int(L.eval("KAHLUA_SHIM_HITS")) == 3)

# the lab as installed: the gate fails; after the installer on a copy it passes, a second run changes nothing
if os.path.isdir(CLIENT):
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "tonumber_check.py"), CLIENT], capture_output=True, text=True)
    installed_clean = r.returncode == 0
    print("  installed lab client:", r.stdout.strip().splitlines()[-1])
    T = tempfile.mkdtemp(prefix="sol_s75_")
    cl = os.path.join(T, "client")
    os.makedirs(cl)
    for f in glob.glob(os.path.join(CLIENT, "*.lua")):
        shutil.copy(f, cl)
    a1 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s75_onevalue.py"), cl], capture_output=True, text=True)
    check("installer on a copy of the lab client: exit 0, gate OK", a1.returncode == 0 and "TONUMBER CHECK OK" in a1.stdout, a1.stdout[-600:] + a1.stderr[-600:])
    snap = {f: open(f, encoding="utf-8", newline="").read() for f in glob.glob(os.path.join(cl, "*.lua"))}
    a2 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s75_onevalue.py"), cl], capture_output=True, text=True)
    check("installer twice: nothing changes", a2.returncode == 0 and "0 files changed" in a2.stdout and
          all(open(f, encoding="utf-8", newline="").read() == t for f, t in snap.items()), a2.stdout[-400:] + a2.stderr[-400:])
    if not installed_clean:
        check("installed lab client (before s75) fails the gate", r.returncode == 1 and "FOUND" in r.stdout)
    staged = os.path.join(HERE, "s75_onevalue", "client")
    if os.path.isdir(staged) and not installed_clean:
        same = all(open(os.path.join(staged, os.path.basename(f)), encoding="utf-8", newline="").read() == t for f, t in snap.items()
                   if os.path.exists(os.path.join(staged, os.path.basename(f))))
        check("s75_onevalue/client equals the installer's output on the current lab", same)
    LC = lua51.LuaRuntime().eval("loadstring")
    broken = [os.path.basename(f) for f, t in snap.items() if isinstance(LC(t), tuple) and LC(t)[0] is None]
    check("every Lua file still compiles after the installer", not broken, broken[:5])
    shutil.rmtree(T, ignore_errors=True)
print("RESULT", ok_n, "/", ok_n + bad)
sys.exit(1 if bad else 0)
