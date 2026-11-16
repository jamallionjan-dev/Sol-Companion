"""s107 gear_page (PLAN_gear_and_combat.md Part 1; COUNCIL_s107_gear_page.md), game side, no Mind change.
Her gear tab (SolPages "loadout") gets Sol's own page: in her hands (the real weapon, rounds in the gun / spare magazines /
loose rounds, ready / empty / jammed / parts / broken, use this one, reload), her preferred firearm and melee weapon, the 8
fighting plans of s105 (replacing LF's weapon-priority selector while combat_plans is on), worn items by slot (take off,
swap), her bag grouped by kind (give to me, use, set preferred), his bag on his click (only what she can use: give to Sol),
what the last SolInventory scan saw in the car and at home, and "like me" (what he has that is better, give her a spare).
One new file, SolGearPage.lua: it wraps SolPages' page class at OnGameStart (refresh, drawLoadoutCard, onMouseUp); no LF or
SolPages edit. Switch gear_page (off = the old card and LF's widgets as before). Game closed only.
usage: apply_s107_gear_page.py <client>"""
import os, sys, shutil, filecmp
CL = sys.argv[1]; NL, CRLF = chr(10), chr(13) + chr(10)
HERE = os.path.dirname(os.path.abspath(__file__))
def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old))
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new)); print("edited " + os.path.basename(path))

src, dst = os.path.join(HERE, "SolGearPage.lua"), os.path.join(CL, "SolGearPage.lua")
assert os.path.exists(os.path.join(CL, "SolPages.lua")), "SolPages.lua missing in the client dir"
if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False): print("kept SolGearPage.lua")
else: shutil.copy(src, dst); print("copied SolGearPage.lua")
A = os.path.join(CL, "SolAuthority.lua")
if '"gear_page"' in open(A, encoding="utf-8").read(): print("kept SolAuthority.lua")
else: edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "gear_page",   -- s107: her gear tab: hands, favourites, fighting plan, worn, her bag, his bag on click, car/home, like me' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix):
    body = open(fix, encoding="utf-8", newline="").read()
    if any(l.strip().startswith("gear_page=") for l in body.splitlines()): print("kept SolFixes_LAB.txt")
    else:
        nl = CRLF if CRLF in body else NL
        with open(fix, "a", encoding="utf-8", newline="") as h: h.write(("" if body.endswith(NL) or body == "" else nl) + "gear_page=on" + nl)
        print("edited SolFixes_LAB.txt")
print("s107 gear_page applied")
