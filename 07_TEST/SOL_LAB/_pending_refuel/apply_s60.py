"""Animal care: Lua module, switch, the hold that keeps her at the job, and the Mind's words. Game closed only.
usage: apply_s60.py <client dir> <sol_mind dir>"""
import os, shutil, sys
CL, MIND = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new, once=True):
    t = open(path, encoding="utf-8", newline="").read()
    if new in t: return
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (path, old[:60])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

A = os.path.join(CL, "SolAuthority.lua")
edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "animal_care",' + NL)
# while she is on an animal job, the same hold as farm work keeps follow and the other base chores off her
edit(A, "function A.farmHeld(actor)" + NL,
     "function A.farmHeld(actor)" + NL +
     "    if type(SolUI) == \"table\" and type(SolUI.solAnimalsHeld) == \"function\" then                 -- animal_care: same hold as farm work" + NL +
     "        local okS, s = pcall(SolUI.solActor)" + NL +
     "        local okH, h = pcall(SolUI.solAnimalsHeld)" + NL +
     "        if okH and h == true and (not okS or s == nil or s == actor) then return true end" + NL +
     "    end" + NL)
shutil.copy(os.path.join(HERE, "SolAnimalCare.lua"), os.path.join(CL, "SolAnimalCare.lua"))
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "animal_care" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("animal_care=on" + CRLF)

CS = os.path.join(MIND, "chat_service.py")
edit(CS, '    (r"اقرئي|اقري", ("sol_read", None)),' + NL,
     '    (r"(?:وقفي|خلص(?:ي)?|بطلي)\\s+(?:شغل\\s+)?(?:ال)?(?:دجاج|جاج|حيوانات)", ("sol_animals", "stop")),' + NL +
     '    (r"(?:اجمعي|لمي|جيبي|شيلي)\\s+(?:ال)?بيض", ("sol_animals", "eggs")),' + NL +
     '    (r"(?:اهتمي|اعتني|دبري|رعي|طعمي|اطعمي|اسقي)\\s+(?:ب)?(?:ال)?(?:دجاج|جاج|حيوانات)", ("sol_animals", "care")),' + NL +
     '    (r"اقرئي|اقري", ("sol_read", None)),' + NL)
MR = os.path.join(MIND, "model_router.py")
edit(MR, '    "farm_report":   ("تقرير عن حالة الزرع", "شوفي عنا بالمزرعة"),' + NL,
     '    "farm_report":   ("تقرير عن حالة الزرع", "شوفي عنا بالمزرعة"),' + NL +
     '    "animal_care":   ("تهتم بالدجاج: مي وأكل بالمعالف وبيض للمطبخ", "اهتمي بالدجاج"),' + NL +
     '    "eggs":          ("تجمع البيض وتحطو بالمطبخ", "اجمعي البيض"),' + NL +
     '    "animal_stop":   ("توقف شغل الدجاج", "وقفي شغل الدجاج"),' + NL)
print("applied")
