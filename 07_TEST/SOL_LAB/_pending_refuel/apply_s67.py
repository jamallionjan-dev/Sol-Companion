"""Item sorting v0.2 (switch item_sort, unchanged): one scan, one plan, each container visited once per round, batches, her own
progress lines and a summary; 0.2.1: she stands where vanilla would (sides first, corners only if no side; canStand + canReachTo),
containers with no such square stay out of the plan, a container she cannot get to is skipped after 2 attempts (5 s each). Game closed only. In place and idempotent: every edit is skipped when it is already there, so it can run
on a lab that has apply_s61.py (v0.1) or on one that does not.
  Lua : SolSort.lua replaced; the switch line, the hold (A.farmHeld) and item_sort=on are added only when missing (as apply_s61.py).
  Mind: chat_service.py sort words get synonyms only (same actions sol_sort run/stop, same card lines sort_items/sort_stop, nothing new).
        Run apply_s66_mind.py too: without it the goal parser still turns "رتبي الاغراض" into the old errand.
usage: apply_s67.py <client dir> <sol_mind dir>      (either may be '-' to skip that side)"""
import os, shutil, sys
CL, MIND = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:70])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

if CL != "-":
    src = open(os.path.join(HERE, "SolSort.lua"), encoding="ascii").read()
    assert 'M.VERSION = "0.2.1"' in src or 'M.VERSION = "0.2.2"' in src      # 0.2.2: spatial_access (apply_s70) adds only an optional SolPlace use
    A = os.path.join(CL, "SolAuthority.lua")
    t = open(A, encoding="utf-8").read()
    if '"item_sort"' not in t:
        edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "item_sort",' + NL)
    if "SolUI.solSortHeld" not in t:
        edit(A, "function A.farmHeld(actor)" + NL,
             "function A.farmHeld(actor)" + NL +
             "    if type(SolUI) == \"table\" and type(SolUI.solSortHeld) == \"function\" then                   -- item_sort: same hold as farm work" + NL +
             "        local okS, s = pcall(SolUI.solActor)" + NL +
             "        local okH, h = pcall(SolUI.solSortHeld)" + NL +
             "        if okH and h == true and (not okS or s == nil or s == actor) then return true end" + NL +
             "    end" + NL)
    shutil.copy(os.path.join(HERE, "SolSort.lua"), os.path.join(CL, "SolSort.lua"))
    fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
    if os.path.exists(fix) and "item_sort=" not in open(fix, encoding="utf-8").read():
        with open(fix, "a", encoding="utf-8", newline="") as h: h.write("item_sort=on" + CRLF)

if MIND != "-":
    CS = os.path.join(MIND, "chat_service.py")
    run_old = '    (r"(?:رتّ?بي|نظّ?مي|فرّ?زي|رتب)\\s+(?:ال)?(?:اغراض|أغراض|غراض|البيت|المخزن|الصناديق|الخزاين)", ("sol_sort", "run")),' + NL
    run_new = ('    (r"(?:رتّ?بي(?:لي|لنا)?|نظّ?مي(?:لي|لنا)?|فرّ?زي|رتب)\\s+(?:ال)?(?:اغراض|أغراض|غراض|اشياء|أشياء|البيت|المخزن|الصناديق|الخزاين|الخزانات)'
               '|(?:حطي|حطّي|رجعي|رجّعي)\\s+كل\\s+(?:شي|شغلة|غرض)\\s+(?:ب|في\\s+|ع|ل)?(?:محل|مكان)", ("sol_sort", "run")),' + NL)
    stop_old = '    (r"(?:وقفي|خلص(?:ي)?|بطلي)\\s+(?:ال)?(?:ترتيب|فرز)", ("sol_sort", "stop")),' + NL
    stop_new = '    (r"(?:وقفي|وقّفي|خلص(?:ي)?|بطلي|كفي|بكفي)\\s+(?:ال)?(?:ترتيب|فرز)", ("sol_sort", "stop")),' + NL
    edit(CS, run_old, run_new)
    edit(CS, stop_old, stop_new)
print("applied")
