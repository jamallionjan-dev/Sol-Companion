"""Builds s75_onevalue_edits.json for apply_s75_onevalue.py from an UNPATCHED client dir (read-only).
Every tonumber(X) whose last argument X is a call (or ...) becomes tonumber((X)): Kahlua's tonumber casts its first
argument to String as soon as it gets a 2nd one (BaseLib.java:419), so a call that returns two values crashes it.
SolSecretLoadout.lua is left out: the installer copies the staged, already fixed file.
usage: build_s75_onevalue.py <unpatched client dir>"""
import collections, glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua"))
from tonumber_check import sites

SKIP = {"SolSecretLoadout.lua"}

def build(cl):
    edits = []
    for f in sorted(glob.glob(os.path.join(cl, "*.lua"))):
        name = os.path.basename(f)
        if name in SKIP:
            continue
        src = open(f, encoding="utf-8", newline="").read()
        found = [s for s in sites(f, src) if s["issue"] == "multi"]
        assert not [s for s in sites(f, src) if s["issue"] == "base"], name           # none today; would need a hand fix
        groups = collections.OrderedDict()
        for s in found:
            old = s["text"]
            a, b = s["arg_start"] - s["start"], s["arg_end"] - s["start"]
            new = old[:a] + "(" + old[a:b] + ")" + old[b:]
            groups.setdefault((old, new), []).append(s["line"])
        for (old, new), lines in groups.items():
            assert src.count(old) == len(lines), (name, old, src.count(old), lines)     # the anchor is exact
            edits.append({"file": name, "old": old, "new": new, "count": len(lines), "lines": lines})
    return edits

if __name__ == "__main__":
    edits = build(sys.argv[1])
    out = os.path.join(HERE, "s75_onevalue_edits.json")
    with open(out, "w", encoding="utf-8", newline="\n") as h:
        json.dump(edits, h, ensure_ascii=False, indent=0)
    print("edits", len(edits), "sites", sum(e["count"] for e in edits), "files", len({e["file"] for e in edits}), "->", out)
