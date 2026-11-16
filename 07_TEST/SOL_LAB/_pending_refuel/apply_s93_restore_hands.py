"""s93 restore_hands (2026-11-11 00:26 live): Sol's saved record was QUARANTINED on load with
"actor initialization failed: primary hand item could not be equipped" (SCPersistence.applyEquipment), so she never came back
and every far order answered cannot_travel. A hand item that cannot be equipped must not cost the whole companion: the item
stays in her inventory (the existing reportEquipmentFallback logs it) and the restore goes on. Switch restore_hands
(read at call time; off = the old strict behaviour). Game closed only. usage: apply_s93_restore_hands.py <client dir>"""
import os, sys
CL = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

P = os.path.join(CL, "SCPersistence.lua")
GATE = ('local A_ = rawget(_G, "SolAuthority"); local soft_ = type(A_) == "table" and type(A_.on) == "function" and A_.on("restore_hands") == true   -- s93' + NL)
for hand in ("primary", "secondary"):
    H = hand.capitalize()
    edit(P,
         '        if not set or not readOk or readItem ~= item then' + NL +
         '            return false, "' + hand + ' hand item could not be equipped"' + NL,
         '        if not set or not readOk or readItem ~= item then' + NL +
         '            ' + GATE +
         '            if soft_ then reportEquipmentFallback(companionId, "' + hand + ' hand", "' + hand + '", "could not be equipped")   -- s93: keep it in her bag, go on' + NL +
         '                local RQ_ = rawget(_G, "SolRestoreHands"); if type(RQ_) == "table" and type(RQ_.later) == "function" then pcall(RQ_.later, actor, item, "' + hand + '") end   -- s93: back in her hand once she stands' + NL +
         '            else return false, "' + hand + ' hand item could not be equipped" end' + NL)
import shutil
shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "SolRestoreHands.lua"), os.path.join(CL, "SolRestoreHands.lua"))
A = os.path.join(CL, "SolAuthority.lua")
if '"restore_hands"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "restore_hands",' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "restore_hands" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("restore_hands=on" + CRLF)
print("s93 restore_hands applied")
