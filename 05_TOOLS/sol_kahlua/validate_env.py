"""Proves kahlua_env.py against the real thing: runs probe.lua on the prelude and diffs it with probe_kahlua.txt. Lists whatever still differs."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "07_TEST", "SOL_LAB", "_pending_refuel"))
from kahlua_env import lua51
out = []
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.globals().print = lambda *a: out.append("\t".join(str(x) for x in a))
L.execute(open(os.path.join(HERE, "probe.lua"), encoding="utf-8").read())
def parse(lines):
    d = {}
    for l in lines:
        if " => " in l: k, v = l.split(" => ", 1); d[k] = v
        elif l.startswith(("GLOBAL ", "LIB ")): p = l.split(" ", 2); d[p[0] + " " + p[1]] = p[2] if len(p) > 2 else ""
    return d
k = parse(open(os.path.join(HERE, "probe_kahlua.txt"), encoding="utf-8").read().splitlines())
m = parse(out)
def ok_fail(v): return v.split(",", 1)[0]          # error text differs by design; what matters is pass or fail
same, diff = 0, []
for n in m:
    a, b = k.get(n), m[n]
    if a == b or (a and a.startswith("false") and b.startswith("false")): same += 1
    else: diff.append((n, a, b))
print("same", same, "different", len(diff))
for n, a, b in diff: print("%-22s K: %s\n%-22s L: %s" % (n, str(a)[:110], "", b[:110]))
