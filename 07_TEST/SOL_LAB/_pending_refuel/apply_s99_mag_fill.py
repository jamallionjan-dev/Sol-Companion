"""s99 mag_fill + weapon_scan + melee_choice (2026-11-11 11:59-12:04 live).
  - "carry this weapon" on the G28: "no_usable_weapon (empty)" (LF's own check, SCCombat equipExactWeapon ->
    weaponUsableNow: weapon.ammo <= 0 and hasReloadAmmo false); she has ~500 loose 7.62x51 rounds, no loaded magazine.
  - she fought with a wrench, not her katana: "weapon=Wrench carried=1 usable=1" (DebugLog 17488/17502): LF's weapon list
    comes from an item walk capped at 240 items (SCGameplayUtil.inventoryItemsDeep), and the loose rounds use it up.
mag_fill (SolMagFill.lua):
  - weaponRecord: ammo = magazine count + the chambered round (ISRackFirearm moves one round into the chamber);
  - hasReloadAmmo: a magazine gun is reloadable when a COMPATIBLE magazine (Gunworks profile) holds rounds, found with
    getAllTypeRecurse (no scan cap); loose rounds alone are not a reload in a fight;
  - equipExactWeapon: his order on a magazine gun she can load is accepted; the fill waits until she is safe;
  - when idle and no zombie within 6 tiles she fills empty/partial magazines (matching calibre), inserts and racks.
weapon_scan (SolWeaponPick.lua): inventoryWeapons also lists the weapons the capped walk missed.
melee_choice (SolWeaponPick.lua): melee scored by damage x condition and kind (long blade/blunt over tools); her melee
  weapon (his pick, else the katana) first; a held melee weapon is not kept for being held.
SolCombatEquipFallback 0.3.0: an "empty" reason asks SolMagFill; melee pick marks her melee weapon.
Idempotent. Game closed only. usage: apply_s99_mag_fill.py <client dir>"""
import os, shutil, sys
CL = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)
HERE = os.path.dirname(os.path.abspath(__file__))

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    print("edited " + os.path.basename(path))

M = 'local M_ = rawget(_G, "SolMagFill")'
W = 'local W_ = rawget(_G, "SolWeaponPick")'
C = os.path.join(CL, "SCCombat.lua")
# 1. weaponRecord: the chambered round counts
edit(C,
     '    if ammo < 0 then ammo = numberCall(item, "getAmmoCount", ranged and 0 or 1) end' + NL,
     '    if ammo < 0 then ammo = numberCall(item, "getAmmoCount", ranged and 0 or 1) end' + NL +
     '    do ' + M + '; if ranged and type(M_) == "table" and type(M_.loadedRounds) == "function" then ammo = M_.loadedRounds(item, ammo) end end   -- s99 mag_fill: + chambered round' + NL)
# 2. hasReloadAmmo: compatible loaded magazine, no scan cap
edit(C,
     '    if not inventory or not weapon or not weapon.ranged then return false end' + NL,
     '    if not inventory or not weapon or not weapon.ranged then return false end' + NL +
     '    do ' + M + '; if type(M_) == "table" and type(M_.reloadReady) == "function" then local r_ = M_.reloadReady(inventory, weapon.item); if r_ ~= nil then return r_ end end end   -- s99 mag_fill' + NL)
# 3. inventoryWeapons: what the capped walk missed
edit(C,
     '    return result, inventory, entry' + NL + 'end' + NL,
     '    do ' + W + '; if type(W_) == "table" and type(W_.missing) == "function" then   -- s99 weapon_scan' + NL +
     '        for _, item_ in ipairs(W_.missing(actor, inventory, result)) do local r_ = weaponRecord(item_); if r_ then result[#result + 1] = r_ end end' + NL +
     '    end end' + NL +
     '    return result, inventory, entry' + NL + 'end' + NL)
# 4. chooseWeapon: melee score
edit(C,
     '            local score = weapon.score' + NL,
     '            local score = weapon.score' + NL +
     '            do ' + W + '; if type(W_) == "table" and type(W_.meleeScore) == "function" and not weapon.ranged then score = W_.meleeScore(actor, weapon, score) end end   -- s99 melee_choice' + NL)
# 5. equipExactWeapon: his order on a gun she can load
edit(C,
     '    if not weapon or not weaponUsableNow(U().inventory(actor), weapon) then' + NL +
     '        if P_ and type(P_.pickFailed) == "function" then P_.pickFailed(actor, item, "no_usable_weapon", weapon) end' + NL,
     '    if not weapon or (not weaponUsableNow(U().inventory(actor), weapon)' + NL +
     '        and not (function() ' + M + '; return type(M_) == "table" and type(M_.orderFill) == "function" and M_.orderFill(actor, item) == true end)()) then   -- s99 mag_fill' + NL +
     '        if P_ and type(P_.pickFailed) == "function" then P_.pickFailed(actor, item, "no_usable_weapon", weapon) end' + NL)

for f in ("SolMagFill.lua", "SolWeaponPick.lua", "SolCombatEquipFallback.lua"):
    shutil.copy(os.path.join(HERE, f), os.path.join(CL, f))
A = os.path.join(CL, "SolAuthority.lua")
SW = (("mag_fill", "s99: she fills magazines with loose rounds when safe; EFZ chamber counted; loaded magazines found past the scan cap"),
      ("weapon_scan", "s99: LF's weapon list also takes weapons its 240-item walk missed"),
      ("melee_choice", "s99: melee by damage x condition and kind; her melee weapon (his pick, else katana) first"))
for sw, note in SW:
    if '"' + sw + '"' not in open(A, encoding="utf-8").read():
        edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "' + sw + '",   -- ' + note + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix):
    for sw, _ in SW:
        if sw + "=" not in open(fix, encoding="utf-8").read():
            with open(fix, "a", encoding="utf-8", newline="") as h: h.write(sw + "=on" + CRLF)
print("s99 mag_fill + weapon_scan + melee_choice applied")
