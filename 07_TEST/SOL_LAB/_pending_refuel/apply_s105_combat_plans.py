"""s105 combat_plans (PLAN_gear_and_combat.md step 1; COUNCIL_s105_combat_plans.md), game side.
One plan name sets Living Fellows' own combat knobs (weapon priority, doctrine -> combat mode, hold fire; follow distance and
move mode for support / stealth) through LF's own commands, plus the plan rules in SolCombatPlans.lua: smart switches melee
(1-2 zombies) / firearm (3+ near her or one near him); fierce stays within 25 tiles of him; stealth fires only an EFZ-silenced
gun; every plan: never across him, retreat under 30% health, back to smart after her death. Verb sol_combat_plan <plan>.
SCCombat hooks (3): Combat.update weapon preference, chooseWeapon (top), actionUtilities (end). Combat.friendlyFireBlocked and
Combat.scoreTargets are wrapped from SolCombatPlans at OnGameStart (no edit). Works before or after s104 shooting_discipline.
Switch combat_plans (off = LF as before). Game closed only. Pairs with apply_s105_combat_plans_mind.py (Mind restart).
usage: apply_s105_combat_plans.py <client>"""
import os, sys, shutil
CL = sys.argv[1]; NL, CRLF = chr(10), chr(13) + chr(10)
HERE = os.path.dirname(os.path.abspath(__file__))
def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old))
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new)); print("edited " + os.path.basename(path))
def insert_before(path, hook, anchor, skip_tag):
    """hook (one line) goes right above anchor, and above any lines tagged skip_tag that sit directly over it (another stage's
    hook keeps its own anchor whole, so its installer stays idempotent). Kept when the hook line is already there."""
    t = open(path, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in t else NL
    anchor = anchor.replace(NL, nl)
    if hook in t: print("kept " + os.path.basename(path)); return
    assert t.count(anchor) == 1, (os.path.basename(path), t.count(anchor))
    at = t.index(anchor)
    while True:
        prev = t.rfind(nl, 0, at - len(nl)) + len(nl) if at > 0 else 0
        if prev < at and skip_tag in t[prev:at]: at = prev
        else: break
    open(path, "w", encoding="utf-8", newline="").write(t[:at] + hook + nl + t[at:]); print("edited " + os.path.basename(path))

shutil.copy(os.path.join(HERE, "SolCombatPlans.lua"), os.path.join(CL, "SolCombatPlans.lua")); print("copied SolCombatPlans.lua")
C = os.path.join(CL, "SCCombat.lua")
# 1. the weapon kind for this pulse (smart: melee / firearm by count; stealth: quiet; hold: melee)
edit(C, '''    local preference = commands.weaponPriority or "best"
    if seated and commands.combatDoctrine == "weapons_free" then
        preference = "firearm"
    end
''', '''    local preference = commands.weaponPriority or "best"
    if seated and commands.combatDoctrine == "weapons_free" then
        preference = "firearm"
    end
    do local cp_ = rawget(_G, "SolCombatPlans"); if type(cp_) == "table" and cp_.on() then preference = cp_.preference(actor, player, snapshot, scored, commands, preference, seated) end end   -- s105 combat_plans
''')
# 2. the weapon itself: the plan's kind before LF's manual marker / s98 keep-held
edit(C, '''local function chooseWeapon(actor, preference, distance, pressure, indexEntry)
    local weapons, inventory, entry = inventoryWeapons(actor, indexEntry)
''', '''local function chooseWeapon(actor, preference, distance, pressure, indexEntry)
    local weapons, inventory, entry = inventoryWeapons(actor, indexEntry)
    do local cp_ = rawget(_G, "SolCombatPlans"); if type(cp_) == "table" and cp_.on() then local w_ = cp_.choose(actor, weapons, function(w) return weaponUsableNow(inventory, w, entry) end, preference); if w_ ~= nil then return w_, inventory, entry end end end   -- s105 combat_plans
''')
# 3. the actions: retreat under 30% health; stealth never fires an unsilenced gun (above s104's shape line when it is there)
insert_before(C, '''    do local cp_ = rawget(_G, "SolCombatPlans"); if type(cp_) == "table" and cp_.on() then cp_.shape(actor, player, target, weapon, readiness, actions) end end   -- s105 combat_plans''',
              """    return utility.sortByScoreDescending(actions), distance
end

Combat._actionUtilitiesForTests = actionUtilities""", "-- s104 shooting_discipline")
A = os.path.join(CL, "SolAuthority.lua")
if '"combat_plans"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "combat_plans",   -- s105: one plan name sets her fighting knobs; never across him, retreat under 30%, smart after death' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "combat_plans" not in open(fix, encoding="utf-8").read():
    body = open(fix, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in body else NL
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write(("" if body.endswith(NL) or body == "" else nl) + "combat_plans=on" + nl)
print("s105 combat_plans applied")
