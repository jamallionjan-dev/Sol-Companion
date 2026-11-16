"""Compile every Sol Lua file with the game's own compiler and check what the bytecode uses against what the game has. Usage: scan.py [--quiet]"""
import collections, os, re, sys
from compare import kahlua, GAME, HERE
LUA = os.path.join(HERE, "..", "..", "07_TEST", "SOL_LAB", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua")
r = kahlua("scan", os.path.join(HERE, "scan.tsv"), os.path.abspath(LUA), os.path.join(GAME, "media", "lua"))
print(r.stdout.strip()[-300:], r.stderr[-300:])
api = collections.defaultdict(set); statics = collections.defaultdict(set); globs = set()
for l in open(os.path.join(HERE, "api.tsv"), encoding="utf-8"):
    p = l.rstrip("\n").split("\t")
    if p[0] == "M":
        api[p[2]].add(p[1])
        if p[3] == "s": statics[p[1]].add(p[2])
    elif p[0] == "F": statics[p[1]].add(p[2])
    elif p[0] == "G": globs.add(p[2])
classes = set(statics) | {c for s in api.values() for c in s}
libs = {}
kg = set()
for l in open(os.path.join(HERE, "probe_kahlua.txt"), encoding="utf-8"):
    if l.startswith("LIB "): p = l.split(); libs[p[1]] = set(p[2:])
    elif l.startswith("GLOBAL "):
        p = l.split()
        if p[2] != "nil": kg.add(p[1])
rows = [l.rstrip("\n").split("\t") for l in open(os.path.join(HERE, "scan.tsv"), encoding="utf-8")]
setg = {r[3] for r in rows if r[0] == "S"}
defk = {r[3] for r in rows if r[0] == "K"}
sol = [r for r in rows if not r[1].startswith("V:")]
known = kg | globs | classes | setg | {"_G"}
res = collections.defaultdict(list)
for r in sol:
    k, f, ln, a = r[0], r[1].rsplit("/", 1)[-1], r[2], r[3]
    extra = r[4] if len(r) > 4 else ""
    at = "%s:%s" % (f, ln)
    if k == "G" and a not in known: res["global_unknown"].append((a, at))
    elif k == "F":
        o, fld = a.split(".", 1)
        if o in libs and fld not in libs[o]: res["lib_missing"].append((a, at))
        elif o not in setg and o in statics and fld not in statics[o] and fld not in defk: res["static_missing"].append((a, at))
    elif k == "M" and a not in api and a not in defk: res["method_nowhere"].append((a, at))
    elif k == "X":
        if a in ("tonumber", "tostring", "string.len", "select", "string.sub", "math.floor", "math.ceil", "math.abs", "string.lower", "string.upper", "string.rep", "unpack", "table.insert", "table.remove", "ZombRand"):
            res["multret_into_" + a].append((extra, at))
    elif k == "MOD": res["mod"].append((a, at))
    elif k == "VT": res["vararg_table"].append(("{...}", at))
    elif k == "E": res["compile_error"].append((a, at))
for key in sorted(res):
    c = collections.OrderedDict()
    for a, at in res[key]: c.setdefault(a, []).append(at)
    print("\n== %s: %d sites, %d names" % (key, len(res[key]), len(c)))
    if "--quiet" in sys.argv: continue
    for a, sites in sorted(c.items(), key=lambda kv: kv[0] or ""):
        print("  %s  x%d  %s" % (a, len(sites), " ".join(sites[:4])))
