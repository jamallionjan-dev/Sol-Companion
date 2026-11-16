"""spatial_access (DOCS/PLAN_spatial_awareness.md): Sol knows which side of a fence, wall, window or door each square is on, and walks
through doors first, a window only when no door will do, a fence only as the last resort. Game closed only. In place and idempotent:
every edit is skipped when it is already there.
  Lua  SolPlace.lua      new module: edges (cached per chunk, door/window state live), access squares, a time-sliced door-first route,
                         U.solGoto walked leg by leg along it, Living Fellows' fence/window edge cost raised for Sol while calm,
                         verb sol_place (status | dump [r] | route x,y | access x,y)
       SolSort.lua       0.2.2 (needs apply_s67.py first: the item_sort switch and its hold): standing squares on the container's side
       SolFarmWork.lua   walkTo: her standing squares come from SolPlace.standSquares when the switch is on (LF's list otherwise)
       SolAnimalCare.lua walk: the same
       SolAuthority.lua  switch spatial_access in A.FIXES
       SolFixes_LAB.txt  spatial_access=on
usage: apply_s70_spatial_access.py <client dir>"""
import os, shutil, sys
CL = sys.argv[1] if len(sys.argv) > 1 else None
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:70])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

FARM_OLD = """    local targets = tcall(n.interactionTargets, a, square, { maximum = 8 })
"""
FARM_NEW = """    local targets = tcall(n.interactionTargets, a, square, { maximum = 8 })
    local SP = g("SolPlace")                                                   -- spatial_access: only squares on the plant's own side
    if type(SP) == "table" and type(SP.on) == "function" and SP.on() then
        local okS, own = pcall(SP.standSquares, square)
        if okS and type(own) == "table" and #own > 0 then targets = own end
    end
"""
ANIMAL_OLD = """    local ok, targets = pcall(n.interactionTargets, a, sq, { maximum = 8 })
"""
ANIMAL_NEW = """    local ok, targets = pcall(n.interactionTargets, a, sq, { maximum = 8 })
    local SP = g("SolPlace")                                                   -- spatial_access: only squares on the animal's own side
    if ok and type(SP) == "table" and type(SP.on) == "function" and SP.on() then
        local okS, own = pcall(SP.standSquares, sq)
        if okS and type(own) == "table" and #own > 0 then targets = own end
    end
"""

def walkers(cl):
    edit(os.path.join(cl, "SolFarmWork.lua"), FARM_OLD, FARM_NEW)
    edit(os.path.join(cl, "SolAnimalCare.lua"), ANIMAL_OLD, ANIMAL_NEW)

if __name__ == "__main__":
    A = os.path.join(CL, "SolAuthority.lua")
    t = open(A, encoding="utf-8").read()
    assert '"item_sort"' in t and "SolUI.solSortHeld" in t, "run apply_s67.py first (SolSort 0.2.1 and its switch)"
    src = open(os.path.join(HERE, "SolSort.lua"), encoding="ascii").read()
    assert 'M.VERSION = "0.2.2"' in src
    shutil.copy(os.path.join(HERE, "SolSort.lua"), os.path.join(CL, "SolSort.lua"))
    shutil.copy(os.path.join(HERE, "SolPlace.lua"), os.path.join(CL, "SolPlace.lua"))
    walkers(CL)
    if '"spatial_access"' not in t:
        edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "spatial_access",     -- doors first, a window only when no door will do, a fence last; access squares on the thing\'s side' + NL)
    fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
    if os.path.exists(fix) and "spatial_access=" not in open(fix, encoding="utf-8").read():
        with open(fix, "a", encoding="utf-8", newline="") as h: h.write("spatial_access=on" + CRLF)
    print("spatial_access applied to", CL)
