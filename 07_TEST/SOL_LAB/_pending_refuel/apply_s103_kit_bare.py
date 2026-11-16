"""s103 kit_bare: a weapon Sol builds or restores starts bare, so no EFZ default part stays next to its real parts.
Live 2026-11-11 (00:22 .. 11:59, every load): "[TW] Assembly needs attention: EscapeFromZomboidFirearms.M4A1 duplicatePath",
SolCombatEquipFallback: duplicatePath mod_pistol_grip, mod_barrel, mod_gas_block, mod_muzzle, mod_handguard, mod_handguard/
mod_handguard, mod_stock_000. The give at 21:29 was clean (EFZ's applyTree, Runtime.lua:798, detaches every EFZ part first);
the doubling comes on LOAD: SCPersistence.addInventoryNode re-creates Sol's M4A1 with AddItem(type) -> EFZ OnCreate =
TWRuntime.createDefault (TW_Items.txt:79, Runtime.lua:484) installs the M4A1_Std preset, then the saved parts are attached on
top; a saved part of another template than the preset's lands beside it on the same path (exactly those 7 paths; the G28
build IS its default preset, so it never doubled). Fix (SolKitBare.lua): clearAllWeaponParts() on the new item before the
saved parts, one part per path afterwards (last wins, for snapshots already doubled), EFZ's C.validate prunes orphans;
SolSecretLoadout.build strips before applyTree too. Switch kit_bare (off = the old code). Game closed only.
usage: apply_s103_kit_bare.py <client>"""
import os, sys, shutil
CL = sys.argv[1]; NL, CRLF = chr(10), chr(13) + chr(10)
HERE = os.path.dirname(os.path.abspath(__file__))
def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old))
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new)); print("edited " + os.path.basename(path))

shutil.copy(os.path.join(HERE, "SolKitBare.lua"), os.path.join(CL, "SolKitBare.lua")); print("copied SolKitBare.lua")
P = os.path.join(CL, "SCPersistence.lua")
edit(P, '''    for _, partEntry in ipairs(entry.weaponParts) do
        local partOk, part = addCreatedItem(''', '''    local kb_ = rawget(_G, "SolKitBare"); if type(kb_) == "table" and kb_.on() then kb_.beforeParts(item, entry) end   -- s103 kit_bare: EFZ OnCreate defaults off
    for _, partEntry in ipairs(entry.weaponParts) do
        local partOk, part = addCreatedItem(''')
edit(P, '''            return false, "weapon part could not be attached: " .. partEntry.type
        end
    end
    return true, item
end''', '''            return false, "weapon part could not be attached: " .. partEntry.type
        end
    end
    if type(kb_) == "table" and kb_.on() then kb_.afterParts(item) end   -- s103 kit_bare: one part per EFZ path
    return true, item
end''')
S = os.path.join(CL, "SolSecretLoadout.lua")
edit(S, '''        local okA, applied, why = pcall(R.applyTree, w, tree)''', '''        local kb_ = g("SolKitBare"); if type(kb_) == "table" and kb_.on() then kb_.strip(w) end   -- s103 kit_bare: applyTree on a bare gun
        local okA, applied, why = pcall(R.applyTree, w, tree)''')
A = os.path.join(CL, "SolAuthority.lua")
if '"kit_bare"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "kit_bare",   -- s103: a weapon Sol builds or restores starts bare (no EFZ default part beside its own)' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "kit_bare" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("kit_bare=on" + CRLF)
print("s103 kit_bare applied")
