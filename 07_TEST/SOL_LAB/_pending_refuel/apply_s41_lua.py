"""Driving speeds +10 per step, Lua side. Switch: drive_fast in SolFixes_LAB.txt. Corner speeds (6 and 12 km/h) are in the jar and are not touched here. Game closed only.
usage: apply_s41_lua.py <client dir> [--verify]"""
import os, sys
D = sys.argv[1]
ON = '(type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("drive_fast") == true)'
NL = chr(10)
EDITS = {
    "SolGPS.lua": [("local ok, why = D.drive(s, goal, { speedKmh = SPEEDS[G.speed], blockWaitMs = 2500 })",
                    "local ok, why = D.drive(s, goal, { speedKmh = (SPEEDS[G.speed] or 10) + (" + ON + " and 10 or 0), blockWaitMs = 2500 })")],
    "SCDriving.lua": [("job.speedKmh = math.max(0, math.min(30, finite(options.speedKmh) or 10))",
                       "job.speedKmh = math.max(0, math.min(" + ON + " and 60 or 30, finite(options.speedKmh) or 10))")],
    "SolAuthority.lua": [("A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "drive_fast",' + NL)],
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
