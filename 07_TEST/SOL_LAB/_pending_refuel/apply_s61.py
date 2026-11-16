"""Item sorting: Lua module, switch, the hold, and the Mind's words. Game closed only. Run after apply_s60.py.
usage: apply_s61.py <client dir> <sol_mind dir>"""
import os, shutil, sys
CL, MIND = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (path, old[:60])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

A = os.path.join(CL, "SolAuthority.lua")
edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "item_sort",' + NL)
edit(A, "function A.farmHeld(actor)" + NL,
     "function A.farmHeld(actor)" + NL +
     "    if type(SolUI) == \"table\" and type(SolUI.solSortHeld) == \"function\" then                   -- item_sort: same hold as farm work" + NL +
     "        local okS, s = pcall(SolUI.solActor)" + NL +
     "        local okH, h = pcall(SolUI.solSortHeld)" + NL +
     "        if okH and h == true and (not okS or s == nil or s == actor) then return true end" + NL +
     "    end" + NL)
shutil.copy(os.path.join(HERE, "SolSort.lua"), os.path.join(CL, "SolSort.lua"))
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "item_sort" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("item_sort=on" + CRLF)

CS = os.path.join(MIND, "chat_service.py")
edit(CS, '    (r"اقرئي|اقري", ("sol_read", None)),' + NL,
     '    (r"(?:وقفي|خلص(?:ي)?|بطلي)\\s+(?:ال)?(?:ترتيب|فرز)", ("sol_sort", "stop")),' + NL +
     '    (r"(?:رتّ?بي|نظّ?مي|فرّ?زي|رتب)\\s+(?:ال)?(?:اغراض|أغراض|غراض|البيت|المخزن|الصناديق|الخزاين)", ("sol_sort", "run")),' + NL +
     '    (r"اقرئي|اقري", ("sol_read", None)),' + NL)
MR = os.path.join(MIND, "model_router.py")
edit(MR, '    "farm_report":   ("تقرير عن حالة الزرع", "شوفي عنا بالمزرعة"),' + NL,
     '    "farm_report":   ("تقرير عن حالة الزرع", "شوفي عنا بالمزرعة"),' + NL +
     '    "sort_items":    ("ترتب أغراض البيت كل شي بمكانو", "رتبي الاغراض"),' + NL +
     '    "sort_stop":     ("توقف الترتيب", "وقفي الترتيب"),' + NL)
print("applied")
