"""A walk order takes the game's own pathfinder at once, as long-range following already does (the Lua search holds her still while it runs).
Switch: order_engine_path in SolFixes_LAB.txt. Game closed only. usage: apply_s42_lua.py <client dir> [--verify]"""
import os, sys
D = sys.argv[1]
NL = chr(10)
ON = '(type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("order_engine_path") == true)'
EDITS = {
    "SCNavigation.lua": [("""function Navigation._followUsesEngine(intent, sourceSquare, goalSquare, followRouting)
""", """function Navigation._followUsesEngine(intent, sourceSquare, goalSquare, followRouting)
    if type(intent) == "table" and intent.action == "ordered_move" and intent.draggingBody ~= true and not intent.stealthAvoidance and %s then
        return true
    end
""" % ON)],
    "SolAuthority.lua": [("A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "order_engine_path",' + NL)],
}
if len(sys.argv) > 2 and sys.argv[2] == "--verify":
    missing = 0
    for f, ps in EDITS.items():
        t = open(os.path.join(D, f), encoding="utf-8", newline="").read().replace(chr(13) + NL, NL)
        for a, b in ps:
            if t.count(b) < 1: missing += 1; print("MISSING", f, b[:60])
    print("verified", sum(len(v) for v in EDITS.values()), "edits, missing", missing)
    sys.exit(1 if missing else 0)
out = {}
for f, ps in EDITS.items():
    p = os.path.join(D, f)
    t = open(p, encoding="utf-8", newline="").read()
    nl = chr(13) + NL if chr(13) + NL in t else NL
    for a, b in ps:
        a2, b2 = a.replace(NL, nl), b.replace(NL, nl)
        assert t.count(a2) == 1, (f, a[:60], t.count(a2))
        t = t.replace(a2, b2)
    out[p] = t
for p, t in out.items(): open(p, "w", encoding="utf-8", newline="").write(t)
print("applied to", len(out), "files")
