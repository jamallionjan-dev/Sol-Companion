"""jarcall_check.py - launch gate: every Java method Sol's Lua calls BY NAME must exist in the game jar with that many arguments.

Why: 2026-11-11 12:26, SolMagFill / SolWeaponPick called getAllCategoryRecurse("Weapon"), but B42 only has
getAllCategoryRecurse(String, ArrayList), so the call failed every 2 s ("expected 2 arguments, got 1"). The offline fakes accepted it.

What it checks: string-named calls in Sol*.lua (the helpers call / invoke / U.call / U().call / SC.Call.method / G.call(o, "name", args...)).
- FAIL: the name exists in the game jar (or in our jars), but no public method of that name takes that many arguments.
- WARN: the name is in no jar at all (it may be a Lua table method; check by hand).
It never sees colon calls (obj:method()), which Lua tables share; those stay the reviewer's job.

usage: jarcall_check.py <client dir> [--jar projectzomboid.jar] [--extra-jar x.jar ...]   exit 0 ok, 1 FAIL."""
import os, re, sys, struct, zipfile, json, hashlib

GAME_JAR = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\projectzomboid.jar"
# java.util / java.lang methods reached through Kahlua on ArrayList, HashMap, String, ... (name: arities)
JAVA_BASE = {"size": {0}, "get": {1}, "add": {1, 2}, "isEmpty": {0}, "contains": {1}, "remove": {1}, "clear": {0},
             "iterator": {0}, "hasNext": {0}, "next": {0}, "toString": {0}, "equals": {1}, "hashCode": {0},
             "put": {2}, "containsKey": {1}, "keySet": {0}, "values": {0}, "addAll": {1}, "indexOf": {1}, "set": {2},
             "length": {0}, "name": {0}, "ordinal": {0}, "intValue": {0}, "doubleValue": {0}, "floatValue": {0}}


def class_methods(data):
    """public method name -> set of argument counts, from one .class file."""
    def u2(o): return struct.unpack(">H", data[o:o + 2])[0]
    n = u2(8); o = 10; pool = [None] * n; i = 1
    while i < n:
        tag = data[o]
        if tag == 1:
            ln = u2(o + 1); pool[i] = data[o + 3:o + 3 + ln].decode("utf-8", "replace"); o += 3 + ln
        elif tag in (3, 4): o += 5
        elif tag in (5, 6): o += 9; i += 1
        elif tag in (7, 8, 16, 19, 20): o += 3
        elif tag in (9, 10, 11, 12, 17, 18): o += 5
        elif tag == 15: o += 4
        else: return {}
        i += 1
    o += 6; o += 2 + 2 * u2(o)
    for _ in range(u2(o - 0) if False else 0): pass
    fc = u2(o); o += 2
    for _ in range(fc):
        o += 6; ac = u2(o); o += 2
        for _ in range(ac): o += 6 + struct.unpack(">I", data[o + 2:o + 6])[0]
    mc = u2(o); o += 2; out = {}
    for _ in range(mc):
        flags, ni, di = u2(o), u2(o + 2), u2(o + 4); o += 6; ac = u2(o); o += 2
        for _ in range(ac): o += 6 + struct.unpack(">I", data[o + 2:o + 6])[0]
        if not flags & 0x0001: continue
        name, desc = pool[ni], pool[di]
        args = desc[1:desc.index(")")]; k = 0; j = 0
        while j < len(args):
            while args[j] == "[": j += 1
            if args[j] == "L": j = args.index(";", j)
            j += 1; k += 1
        out.setdefault(name, set()).add(k)
    return out


def jar_methods(path, cache_dir):
    st = os.stat(path); key = hashlib.sha1(("%s|%d|%d" % (path, st.st_size, int(st.st_mtime))).encode()).hexdigest()[:16]
    cache = os.path.join(cache_dir, "jarcall_%s.json" % key)
    if os.path.exists(cache):
        return {k: set(v) for k, v in json.load(open(cache)).items()}
    out = {}
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if not n.endswith(".class"): continue
            try:
                for m, ks in class_methods(z.read(n)).items(): out.setdefault(m, set()).update(ks)
            except Exception:
                pass
    json.dump({k: sorted(v) for k, v in out.items()}, open(cache, "w"))
    return out


CALL_RX = re.compile(r'(?<![\w.:])(?:call|invoke|U\.call|U\(\)\.call|SC\.Call\.method|G\.call)\(([^"()]*(?:\([^()]*\))?[^"()]*?),\s*"(\w+)"')


def args_after(text, start):
    """count the arguments after the method name until the call's closing parenthesis."""
    depth, k, i, seen = 0, 0, start, False
    while i < len(text):
        c = text[i]
        if c in "([{": depth += 1
        elif c in ")]}":
            if depth == 0: return k
            depth -= 1
        elif c == "," and depth == 0: k += 1
        elif c == '"' or c == "'":
            q = c; i += 1
            while i < len(text) and text[i] != q: i += 2 if text[i] == "\\" else 1
        i += 1
    return k


def main(argv):
    client = argv[1]
    jars = [GAME_JAR]
    if "--jar" in argv: jars = [argv[argv.index("--jar") + 1]]
    jars += [argv[i + 1] for i, a in enumerate(argv) if a == "--extra-jar"]
    java = os.path.join(client, "..", "..", "java")
    jars += [os.path.join(java, f) for f in os.listdir(java) if f.endswith(".jar")] if os.path.isdir(java) else []
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache"); os.makedirs(cache_dir, exist_ok=True)
    api = {k: set(v) for k, v in JAVA_BASE.items()}
    for j in jars:
        for m, ks in jar_methods(j, cache_dir).items(): api.setdefault(m, set()).update(ks)
    fails, warns = [], []
    for f in sorted(os.listdir(client)):
        if not (f.startswith("Sol") and f.endswith(".lua")): continue
        text = open(os.path.join(client, f), encoding="utf-8", errors="replace").read()
        for m in CALL_RX.finditer(text):
            name = m.group(2); n = args_after(text, m.end())
            seg = text[m.end():m.end() + 400]
            if re.match(r'\s*,\s*function\W', seg): n = None          # an inline Lua function: its body's commas are not arguments
            line = text.count("\n", 0, m.start()) + 1
            if name not in api: warns.append("%s:%d %s (not in any jar)" % (f, line, name))
            elif n is None:
                if not (api[name] & {1, 2}): fails.append("%s:%d %s takes a function but the jar has %s" % (f, line, name, sorted(api[name])))
            elif n not in api[name]: fails.append("%s:%d %s called with %d argument(s); the jar has %s" % (f, line, name, n, sorted(api[name])))
    for w in warns[:15]: print("WARN " + w)
    if len(warns) > 15: print("WARN ... %d more" % (len(warns) - 15))
    for x in fails: print("FAIL " + x)
    print("JARCALL CHECK %s (%d fail, %d warn)" % ("OK" if not fails else "FAILED", len(fails), len(warns)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
