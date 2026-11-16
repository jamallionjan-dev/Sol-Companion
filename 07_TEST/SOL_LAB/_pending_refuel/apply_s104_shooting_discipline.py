"""s104 shooting_discipline: Sol fires aimed single shots, standing, inside the weapon's effective range.
Live 2026-11-11 13:09:41-13:09:48 (DebugLog 2026-11-11_12-24): with the EFZ Colt M4A1 (FireMode Auto, AimingTime 40,
MaxSightRange 10, MaxRange 60) she emptied the magazine; FPZombiesHD logged 8 hits (1 Head) 72-114 ms apart, no kill.
The "[TW-SHOT] baseline shot" lines are Jamal's own shots (EFZ ShotOwner.given counts the local player only).
Causes (DOCS/COUNCIL_s104_shooting.md): Auto mode = no recoil delay for a ranged attack (CombatManager.calculateAttackVars), so
LF's recovery gate never holds; LF's aim wait is wall time, not the engine's aimingDelay that the hit chance subtracts; LF
offers "shoot" at any visible distance and scores far shots higher; the move penalty is still high right after stopping.
Fix (SolShootDiscipline.lua): Single mode, an aim gate on getAimingDelay/getBeenMovingFor, effective range = MaxSightRange+2,
5 aimed shots per zombie until it comes 2 tiles nearer, short bursts only for 3+ zombies within 5 tiles, tactical reload,
the last magazine kept for close threats, threats nearest Jamal first. Switch shooting_discipline (off = LF as before).
Lua only: the game may run while this is staged, but install with the game closed (or restart after).
usage: apply_s104_shooting_discipline.py <client>"""
import os, sys, shutil
CL = sys.argv[1]; NL, CRLF = chr(10), chr(13) + chr(10)
HERE = os.path.dirname(os.path.abspath(__file__))
def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old))
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new)); print("edited " + os.path.basename(path))

shutil.copy(os.path.join(HERE, "SolShootDiscipline.lua"), os.path.join(CL, "SolShootDiscipline.lua")); print("copied SolShootDiscipline.lua")
C = os.path.join(CL, "SCCombat.lua")
# 1. rank: with a firearm, threats nearest Jamal first
edit(C, '''    local scored = Combat.scoreTargets(actor, player, snapshot, state.target)
''', '''    local scored = Combat.scoreTargets(actor, player, snapshot, state.target)
    do local sd_ = rawget(_G, "SolShootDiscipline"); if type(sd_) == "table" and sd_.on() then sd_.rank(actor, player, scored) end end   -- s104 shooting_discipline: threats nearest Jamal first
''')
# 2. shape: effective range, last magazine, tactical reload
edit(C, '''    return utility.sortByScoreDescending(actions), distance
end

Combat._actionUtilitiesForTests = actionUtilities''', '''    do local sd_ = rawget(_G, "SolShootDiscipline"); if type(sd_) == "table" and sd_.on() and weapon and weapon.ranged then sd_.shape(actor, player, snapshot, target, weapon, inventory, actions, distance, function() return hasReloadAmmo(inventory, weapon) end) end end   -- s104 shooting_discipline: range, reserve, tactical reload
    return utility.sortByScoreDescending(actions), distance
end

Combat._actionUtilitiesForTests = actionUtilities''')
# 3. gate: stand, settle the engine's aim, single mode, per-target cap
edit(C, '''        local aiming, aimReason = prepareRangedShot(actor, state, snapshot, target,
            weapon, readiness, player, commands, now)
        if aiming then''', '''        local aiming, aimReason = prepareRangedShot(actor, state, snapshot, target,
            weapon, readiness, player, commands, now)
        local sd_ = rawget(_G, "SolShootDiscipline")   -- s104 shooting_discipline: stand, settle the engine aim, single shot
        if not aiming and type(sd_) == "table" and sd_.on() then aiming, aimReason = sd_.gate(actor, player, state, snapshot, target, weapon, aimReason, now) end
        if aiming then''')
# 4. fired: count the shot
edit(C, '''    clearRejection(state, rootRuntime)
    if reason ~= "combat_recovery_wait" and (chosen.kind == "shoot"''', '''    clearRejection(state, rootRuntime)
    if chosen.kind == "shoot" and reason == "shoot" then local sd_ = rawget(_G, "SolShootDiscipline"); if type(sd_) == "table" and sd_.on() then sd_.fired(actor, target, weapon, now) end end   -- s104 shooting_discipline
    if reason ~= "combat_recovery_wait" and (chosen.kind == "shoot"''')
# 5. cover fire while retreating: not past the effective range
edit(C, '''        and distance <= math.max(1, tonumber(weapon.range) or 1)
        and target.visible == true and target.obstructed ~= true
''', '''        and distance <= math.max(1, tonumber(weapon.range) or 1)
        and (type(rawget(_G, "SolShootDiscipline")) ~= "table" or not SolShootDiscipline.on() or SolShootDiscipline.coverFireOk(actor, weapon, distance))   -- s104 shooting_discipline
        and target.visible == true and target.obstructed ~= true
''')
A = os.path.join(CL, "SolAuthority.lua")
if '"shooting_discipline"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "shooting_discipline",   -- s104: aimed single shots, standing, inside the effective range; 5 per zombie; last magazine kept' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "shooting_discipline" not in open(fix, encoding="utf-8").read():
    body = open(fix, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in body else NL
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write(("" if body.endswith(NL) or body == "" else nl) + "shooting_discipline=on" + nl)
print("s104 shooting_discipline applied")
