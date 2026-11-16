"""s98 combat_equip_fallback + preferred_weapon (2026-11-11 11:18-11:36 live): Sol held and aimed a rifle but never fired;
"carry this weapon" on the M4A1 said "Could not equip item: retry_exhausted".
Cause chain: EFZ's OnEquipPrimary listener (TW/Runtime.lua R.update -> R.refresh, 451-476 and 1062-1064) finds the M4A1
assembly broken (duplicatePath), writes md.TW.ready=false and clears both hands -> SCNativeActions.equip fails ("native equip
did not retain the requested item") -> after 4 failures LF's ActionSupervisor marks equip_weapon on that weapon exhausted
with no expiry -> every begin is refused (retry_exhausted), combat and player orders alike -> SCCombat.execute drops the
reason ("equip_rejected") and picks the same M4A1 next pulse, for ever.
combat_equip_fallback (read at call time; off = old behaviour):
  - SCCombat.execute keeps the reason, blocks the weapon 60 s and goes on with the usable weapon in her hands;
  - weaponUsableNow: blocked weapons and EFZ weapons with md.TW.ready == false are not usable;
  - chooseWeapon: a usable gun in her hands is kept;
  - an explicit equip order skips the retry ledger (ignoreRetry) and a success clears it; an exhausted equip_weapon
    record expires after 3 minutes.
preferred_weapon: "carry this weapon" sets her preferred weapon even when the equip fails; combat keeps the held or
preferred weapon while it can fire; she says plainly (Shami) why she is not using his pick; no technical halo.
Idempotent. Game closed only. usage: apply_s98_combat_equip_fallback.py <client dir>"""
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

F = 'local F_ = rawget(_G, "SolCombatEquipFallback")'
C = os.path.join(CL, "SCCombat.lua")
# 1. weaponUsableNow
edit(C,
     'local function weaponUsableNow(inventory, weapon, indexEntry)' + NL +
     '    if not weapon or (tonumber(weapon.condition) or 0) <= 0 then return false end' + NL,
     'local function weaponUsableNow(inventory, weapon, indexEntry)' + NL +
     '    if not weapon or (tonumber(weapon.condition) or 0) <= 0 then return false end' + NL +
     '    do ' + F + '; if type(F_) == "table" and type(F_.unusable) == "function" and F_.unusable(weapon.item) then return false end end   -- s98: rejected / EFZ not ready' + NL)
# 2. chooseWeapon: held / preferred first
edit(C,
     '    local preferredAvailable = false' + NL,
     '    do ' + F + '; if type(F_) == "table" and type(F_.choose) == "function" then   -- s98: keep the held / preferred gun' + NL +
     '        local w_ = F_.choose(actor, weapons, function(w) return weaponUsableNow(inventory, w, entry) end, manualId)' + NL +
     '        if w_ ~= nil then return w_, inventory, entry end' + NL +
     '    end end' + NL +
     '    local preferredAvailable = false' + NL)
# 3. explicit order skips the retry ledger
edit(C,
     '        allowedActions = { equip_weapon = true },' + NL,
     '        allowedActions = { equip_weapon = true },' + NL +
     '        ignoreRetry = (function() ' + F + '; return type(F_) == "table" and type(F_.ignoreRetry) == "function" and F_.ignoreRetry(options) == true end)(),   -- s98' + NL)
# 4. equipExactWeapon: preference, plain words, ledger cleared on success
edit(C,
     '    local weapon = weaponRecord(item)' + NL +
     '    if not weapon or not weaponUsableNow(U().inventory(actor), weapon) then' + NL +
     '        return false, "no_usable_weapon"' + NL +
     '    end' + NL +
     '    local equipped, reason = equipWeapon(actor, item, {' + NL +
     '        preference = "manual", immediateCommand = true,' + NL +
     '    })' + NL,
     '    local weapon = weaponRecord(item)' + NL +
     '    local P_ = rawget(_G, "SolCombatEquipFallback"); if type(P_) ~= "table" then P_ = nil end   -- s98 preferred_weapon' + NL +
     '    if P_ and weapon and type(P_.markPreferred) == "function" then P_.markPreferred(actor, item) end' + NL +
     '    if not weapon or not weaponUsableNow(U().inventory(actor), weapon) then' + NL +
     '        if P_ and type(P_.pickFailed) == "function" then P_.pickFailed(actor, item, "no_usable_weapon", weapon) end' + NL +
     '        return false, "no_usable_weapon"' + NL +
     '    end' + NL +
     '    local equipped, reason = equipWeapon(actor, item, {' + NL +
     '        preference = "manual", immediateCommand = true,' + NL +
     '    })' + NL +
     '    if P_ and not equipped and type(P_.pickFailed) == "function" then P_.pickFailed(actor, item, reason, weapon) end' + NL +
     '    if P_ and equipped and type(P_.on) == "function" and P_.on() then' + NL +
     '        local sv_ = actionSupervisor(); if sv_ and type(sv_.resetRetry) == "function" then pcall(sv_.resetRetry, actor, "player_equip_order", "equip_weapon", weaponKey(item)) end' + NL +
     '    end' + NL)
# 5. execute: keep the reason, use the gun in her hands
edit(C,
     '    if weapon and not weapon.equipped and action.kind ~= "shove" and action.kind ~= "stomp" then' + NL +
     '        if not equipWeapon(actor, weapon.item, { nextAction = action.kind }) then' + NL +
     '            return false, "equip_rejected"' + NL +
     '        end' + NL +
     '        return true, "equip"' + NL +
     '    end' + NL,
     '    if weapon and not weapon.equipped and action.kind ~= "shove" and action.kind ~= "stomp" then' + NL +
     '        -- s98 begin: combat_equip_fallback' + NL +
     '        local eqOk_, eqReason_ = equipWeapon(actor, weapon.item, { nextAction = action.kind })' + NL +
     '        if eqOk_ then return true, "equip" end' + NL +
     '        ' + F + NL +
     '        if not (type(F_) == "table" and type(F_.on) == "function" and F_.on()) then return false, "equip_rejected" end' + NL +
     '        state.weaponCache = nil' + NL +
     '        local held_ = weaponRecord(select(1, utility.call(actor, "getPrimaryHandItem")))' + NL +
     '        local heldUsable_ = held_ ~= nil and held_.item ~= weapon.item and held_.ranged == weapon.ranged' + NL +
     '            and weaponUsableNow(utility.inventory(actor), held_)' + NL +
     '        local kind_ = F_.rejected(actor, weapon.item, eqReason_, held_, heldUsable_, action.kind)' + NL +
     '        if kind_ == nil then return false, "equip_rejected:" .. tostring(eqReason_ or "unknown") end' + NL +
     '        held_.equipped = true' + NL +
     '        weapon = held_' + NL +
     '        if kind_ ~= action.kind then action = { kind = kind_ } end' + NL +
     '        -- s98 end' + NL +
     '    end' + NL)

S = os.path.join(CL, "SCActionSupervisor.lua")
edit(S,
     '        retryAt = (not exhausted) and (current + retryDelay(attempts)) or nil,' + NL,
     '        retryAt = (not exhausted) and (current + retryDelay(attempts))' + NL +
     '            or (function() ' + F + '; return type(F_) == "table" and type(F_.exhaustedRetryAt) == "function" and F_.exhaustedRetryAt(token.action, current) or nil end)(),   -- s98: exhausted equip expires' + NL)
edit(S,
     '    local record = ledger[retryKey(action, targetKey, category)]' + NL +
     '    if not record then return nil end' + NL,
     '    local record = ledger[retryKey(action, targetKey, category)]' + NL +
     '    if not record then return nil end' + NL +
     '    do ' + F + '; if type(F_) == "table" and type(F_.retryExpired) == "function" and F_.retryExpired(record, nowMs()) then return nil end end   -- s98' + NL)
edit(S,
     '        if record.action == action and record.targetKey == targetKey' + NL,
     '        if record.action == action and record.targetKey == targetKey' + NL +
     '            and not (type(rawget(_G, "SolCombatEquipFallback")) == "table" and type(SolCombatEquipFallback.retryExpired) == "function" and SolCombatEquipFallback.retryExpired(record, current))   -- s98' + NL)

B = os.path.join(CL, "SCUIBridge.lua")
edit(B,
     '    safeMethod(player, "setHaloNote", message)' + NL,
     '    if not (ok and equipped) then   -- s98 preferred_weapon: she says it, no technical halo' + NL +
     '        local P_ = rawget(_G, "SolCombatEquipFallback")' + NL +
     '        if type(P_) == "table" and type(P_.preferOn) == "function" and P_.preferOn() then' + NL +
     '            if not P_.spokeRecently(actor) then P_.tell(actor, item, "refused", nil) end' + NL +
     '            print("[SolCombatEquipFallback] carry order failed: " .. tostring(ok and reason or equipped))' + NL +
     '            return' + NL +
     '        end' + NL +
     '    end' + NL +
     '    safeMethod(player, "setHaloNote", message)' + NL)

shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "SolCombatEquipFallback.lua"), os.path.join(CL, "SolCombatEquipFallback.lua"))
A = os.path.join(CL, "SolAuthority.lua")
for sw, note in (("combat_equip_fallback", "s98: a refused equip is logged, blocked, expires; she fires the gun in her hands"),
                 ("preferred_weapon", "s98: carry this weapon = her preferred weapon; she says why when she cannot use it")):
    if '"' + sw + '"' not in open(A, encoding="utf-8").read():
        edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "' + sw + '",   -- ' + note + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix):
    for sw in ("combat_equip_fallback", "preferred_weapon"):
        if sw not in open(fix, encoding="utf-8").read():
            with open(fix, "a", encoding="utf-8", newline="") as h: h.write(sw + "=on" + CRLF)
print("s98 combat_equip_fallback + preferred_weapon applied")
