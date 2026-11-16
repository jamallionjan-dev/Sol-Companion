"""Finds method names our Lua calls by string (invoke(x, "name")) that this game build no longer has anywhere.
Read-only. usage: lua_method_check.py <game jar> <game media/lua> <mod lua dir>  (exit 0 = none, 1 = some)"""
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from linkcheck import parse

CALL = re.compile(r'\b(?:invoke|invokeMethod|call|safeCall|callIf|tryCall|callMethod|method)\(\s*[^,()"]+(?:\([^()]*\))?\s*,\s*"([A-Za-z_]\w*)"')
DEF = re.compile(r'function\s+[\w.:]*[.:](\w+)\s*\(|\b(\w+)\s*=\s*function\b|["\'](\w+)["\']\s*\]?\s*=\s*function')


def lua_files(root):
    for d, _, fs in os.walk(root):
        for f in fs:
            if f.endswith(".lua"):
                yield os.path.join(d, f)


def main(argv):
    game, vanilla, mod = argv[1:4]
    known = set()
    with zipfile.ZipFile(game) as z:
        for n in z.namelist():
            if n.endswith(".class") and "META-INF" not in n:
                known.update(m for m, _ in parse(z.read(n))[4])
    for root in (vanilla, mod):
        for p in lua_files(root):
            with open(p, encoding="utf-8", errors="replace") as h:
                for m in DEF.finditer(h.read()):
                    known.update(x for x in m.groups() if x)
    missing = {}
    total = 0
    for p in lua_files(mod):
        with open(p, encoding="utf-8", errors="replace") as h:
            for i, line in enumerate(h, 1):
                if line.lstrip().startswith("--"):
                    continue
                for name in CALL.findall(line):
                    total += 1
                    if name not in known:
                        missing.setdefault(name, []).append("%s:%d" % (os.path.basename(p), i))
    for name in sorted(missing):
        print("%s  <- %s" % (name, ", ".join(missing[name][:4])))
    print("LUA METHODS", "OK" if not missing else "MISSING", "calls=%d names_missing=%d" % (total, len(missing)))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
