"""s97 two_hand_grip (2026-11-11 10:38 live): Sol (and later the player) held a rifle in one hand, gripped at the scope.
The pose comes from the hands: WeaponType.getWeaponType gives FIREARM only when primary == secondary (else HANDGUN).
setPrimaryHandItem fires OnEquipPrimary inside the call; a Gunworks/EFZ listener threw (Kahlua callFrame NPE, live
10:36:48), SC.Call.method's pcall came back false although the rifle was already in her hand, and SCNativeActions.equip
returned before setSecondaryHandItem. Then SCCombat.equipWeapon answered "already equipped" for ever (primary == item).
Fix (switch two_hand_grip, read at call time; off = old behaviour): equip goes on when the item is in the hand despite
the error; "already equipped" first puts a one-handed two-hander in both hands; SolTwoHandGrip re-checks every 2 s.
Idempotent. Game closed only. usage: apply_s97_two_hand_grip.py <client dir>"""
import os, shutil, sys
CL = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    print("edited " + os.path.basename(path))

G = 'local G_ = rawget(_G, "SolTwoHandGrip")'
N = os.path.join(CL, "SCNativeActions.lua")
edit(N,
     '    local assigned, assignReason = invoke(actor, "setPrimaryHandItem", intent.item)' + NL +
     '    if not assigned then' + NL +
     '        return false, assignReason' + NL +
     '    end' + NL +
     '    local twoHandedOk, twoHanded = invoke(intent.item, "isTwoHandWeapon")' + NL,
     '    local assigned, assignReason = invoke(actor, "setPrimaryHandItem", intent.item)' + NL +
     '    if not assigned then' + NL +
     '        ' + G + '   -- s97: a listener may throw after the item is in her hand' + NL +
     '        if not (type(G_) == "table" and type(G_.afterThrow) == "function" and G_.afterThrow(actor, intent.item, "primary") == true) then' + NL +
     '            return false, assignReason' + NL +
     '        end' + NL +
     '    end' + NL +
     '    local twoHandedOk, twoHanded = invoke(intent.item, "isTwoHandWeapon")' + NL +
     '    do local G_ = rawget(_G, "SolTwoHandGrip"); if type(G_) == "table" and type(G_.isTwoHanded) == "function" and type(G_.on) == "function" and G_.on() and G_.isTwoHanded(intent.item) then twoHandedOk, twoHanded = true, true end end   -- s97: RequiresEquippedBothHands too' + NL)
edit(N,
     '        local secondaryAssigned, secondaryReason = invoke(actor, "setSecondaryHandItem", intent.item)' + NL +
     '        if not secondaryAssigned then' + NL,
     '        local secondaryAssigned, secondaryReason = invoke(actor, "setSecondaryHandItem", intent.item)' + NL +
     '        if not secondaryAssigned then local G_ = rawget(_G, "SolTwoHandGrip"); if type(G_) == "table" and type(G_.afterThrow) == "function" and G_.afterThrow(actor, intent.item, "secondary") == true then secondaryAssigned = true end end   -- s97' + NL +
     '        if not secondaryAssigned then' + NL)
C = os.path.join(CL, "SCCombat.lua")
edit(C,
     '    if primaryOk and primary == item then return true, "weapon_already_equipped" end' + NL,
     '    if primaryOk and primary == item then' + NL +
     '        ' + G + '; if type(G_) == "table" and type(G_.grip) == "function" then pcall(G_.grip, actor, "already_equipped", true) end   -- s97: one-handed two-hander gets both hands' + NL +
     '        return true, "weapon_already_equipped"' + NL +
     '    end' + NL)
shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "SolTwoHandGrip.lua"), os.path.join(CL, "SolTwoHandGrip.lua"))
A = os.path.join(CL, "SolAuthority.lua")
if '"two_hand_grip"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "two_hand_grip",' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "two_hand_grip" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("two_hand_grip=on" + CRLF)
print("s97 two_hand_grip applied")
