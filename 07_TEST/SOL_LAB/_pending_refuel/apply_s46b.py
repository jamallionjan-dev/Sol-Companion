"""No rope climbing: the methods are gone from the game, so her old rope path must never reach them. Game closed only.
usage: apply_s46b.py <client dir>"""
import os, sys
CLIENT = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)
EDITS = {}
def E(p, a, b): EDITS.setdefault(os.path.join(CLIENT, p), []).append((a, b))
E("SolAuthority.lua", '    "rope_climb_4222", "sol_ladders", "ladder_fast_slide",' + NL, '    "sol_ladders", "ladder_fast_slide",' + NL)
E("SCNativeTraversalActions.lua", """    else
        local check = down and "canClimbDownSheetRope" or "canClimbSheetRope"
        local checked, climbable = invoke(actor, check, square)
        if not checked then return false, "native sheet-rope climb check is unavailable" end
        if climbable ~= true then return false, "native sheet rope is not climbable" end
    end
    local A = rawget(_G, "SolAuthority")
    local newNames = isLadder or (type(A) == "table" and type(A.on) == "function" and A.on("rope_climb_4222") == true)
    local methodName = newNames and (down and "climbDown" or "climb") or (down and "climbDownSheetRope" or "climbSheetRope")
    local invoked, failure = invoke(actor, methodName)
""", """    else
        -- Game 42.22 removed climbSheetRope and climbDownSheetRope. She does not climb ropes.
        return false, "sheet_rope_not_supported"
    end
    local invoked, failure = invoke(actor, down and "climbDown" or "climb")
""")
E("SCNavigation.lua", """    if requestIntent.workCampOnly ~= true
        and SC.Topology and type(SC.Topology.squareHasSheetRope) == "function"
""", """    -- Game 42.22 removed the rope climb methods she used: she does not climb ropes.
    if false and requestIntent.workCampOnly ~= true
        and SC.Topology and type(SC.Topology.squareHasSheetRope) == "function"
""")
out = {}
for p, ps in EDITS.items():
    t = open(p, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    for a, b in ps:
        a2, b2 = a.replace(NL, nl), b.replace(NL, nl)
        assert t.count(a2) == 1, (p[-24:], a[:60], t.count(a2))
        t = t.replace(a2, b2)
    out[p] = t
for p, t in out.items():
    open(p, "w", encoding="utf-8", newline="").write(t)
fix = os.path.join(CLIENT, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
t = open(fix, encoding="utf-8", newline="").read()
a = "rope_climb_4222=on" + CRLF
assert t.count(a) == 1
open(fix, "w", encoding="utf-8", newline="").write(t.replace(a, ""))
print("applied")
