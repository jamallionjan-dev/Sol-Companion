"""Install s119 retreat counterfire and s120 fierce combat refinements in SOL_LAB only."""
import os, shutil, subprocess, time, sys

ROOT = r"C:\Users\JAMAL\Desktop\Sol"
TARGET_CLIENT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else None
if TARGET_CLIENT:
    # Optional candidate mode applies the exact same staged transformation to a
    # disposable or backed-up package tree; the default remains SOL_LAB-only.
    CLIENT = TARGET_CLIENT
    PROFILE = os.path.abspath(os.path.join(CLIENT, "..", "..", "..", "..", "..", ".."))
    LAB = None
    SWITCHES = os.path.join(PROFILE, "Lua", "SolFixes_MAIN.txt")
    if not os.path.isfile(SWITCHES):
        SWITCHES = os.path.join(PROFILE, "Lua", "SolFixes_LAB.txt")
    BACKUP = None
else:
    LAB = os.path.join(ROOT, "07_TEST", "SOL_LAB")
    PROFILE = os.path.join(LAB, "profile", "Zomboid")
    CLIENT = os.path.join(PROFILE, "mods", "Sol_LAB", "42", "media", "lua", "client")
    SWITCHES = os.path.join(PROFILE, "Lua", "SolFixes_LAB.txt")
    BACKUP = os.path.join(LAB, "_backup", "20261112_before_s119_s120_combat")
LOG_DIR = os.path.join(PROFILE, "Logs")

def verify_game_closed():
    result = subprocess.run(["powershell", "-NoProfile", "-Command",
        "@(Get-Process -Name java,javaw,ProjectZomboid64,ProjectZomboid -ErrorAction SilentlyContinue).Count"],
        capture_output=True, text=True, check=True)
    if int(result.stdout.strip() or "0") != 0:
        raise SystemExit("REFUSED: Project Zomboid is running")
    logs = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.endswith("DebugLog.txt")]
    if not logs:
        raise SystemExit("REFUSED: no LAB DebugLog exists")
    log = max(logs, key=os.path.getmtime)
    if time.time() - os.path.getmtime(log) < 60:
        raise SystemExit("REFUSED: LAB log is recent and may still be active")

def read_lua(path):
    raw = open(path, "rb").read()
    crlf = raw.count(b"\r\n") > raw.count(b"\n") / 2
    return raw.decode("utf-8-sig").replace("\r\n", "\n"), crlf

def write_lua(path, text, crlf):
    data = text.replace("\n", "\r\n") if crlf else text
    tmp = path + ".s119s120.tmp"
    with open(tmp, "wb") as f:
        f.write(data.encode("utf-8"))
    os.replace(tmp, path)

def replace_once(text, old, new, name):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"REFUSED: {name} anchor count={n}, expected 1")
    return text.replace(old, new, 1)

if TARGET_CLIENT is None:
    verify_game_closed()
if BACKUP and os.path.exists(BACKUP):
    raise SystemExit("REFUSED: backup already exists: " + BACKUP)

paths = {name: os.path.join(CLIENT, name) for name in
         ("SCCombat.lua", "SolShootDiscipline.lua", "SolAuthority.lua")}
texts, crlfs = {}, {}
for name, path in paths.items():
    texts[name], crlfs[name] = read_lua(path)

# s119: a fierce-plan loaded firearm can counterfire below LF's ordinary 3-tile
# cover-fire threshold. Contact range retains the shove below 0.75 tiles.
sc = texts["SCCombat.lua"]
old = '''    local distance = math.sqrt(target.distanceSq or utility.distanceSq(actor, target.actor))
    local accepted, action
    if distance <= (utility.config("combatShoveDistance") or 1.35)
        and utility.sameFloor(actor, target.actor)
        and not lineBlockedByFriendly(actor, target.actor, player, snapshot, "melee") then
        -- One controlled shove buys the next movement decision room to turn.
        accepted = utility.move(actor, "walk", {
            action = "shove", target = target.actor, retreatCounter = true,
        })
        action = "retreat_shove"
    elseif weapon and weapon.equipped and weapon.ranged and weapon.ammo > 0
        and commands.holdFire ~= true and commands.combatDoctrine ~= "stealth"
        and distance >= (utility.config("combatRetreatCoverFireMinDistance") or 3.0)'''
new = '''    local distance = math.sqrt(target.distanceSq or utility.distanceSq(actor, target.actor))
    local accepted, action
    local shoveDistance = utility.config("combatShoveDistance") or 1.35
    local coverMinDistance = utility.config("combatRetreatCoverFireMinDistance") or 3.0
    local fierceCloseFire = false
    local plans = rawget(_G, "SolCombatPlans")
    local authority = rawget(_G, "SolAuthority")
    if type(plans) == "table" and type(plans.current) == "function"
        and type(authority) == "table" and type(authority.on) == "function"
        and authority.on("retreat_close_fire") == true
        and plans.current(actor) == "fierce"
        and distance >= 0.75 and distance < coverMinDistance
        and weapon and weapon.equipped and weapon.ranged and weapon.ammo > 0
        and commands.holdFire ~= true and commands.combatDoctrine ~= "stealth"
        and distance <= math.max(1, tonumber(weapon.range) or 1)
        and (type(rawget(_G, "SolShootDiscipline")) ~= "table" or not SolShootDiscipline.on() or SolShootDiscipline.coverFireOk(actor, weapon, distance))
        and target.visible == true and target.obstructed ~= true
        and utility.sameFloor(actor, target.actor)
        and not lineBlockedByFriendly(actor, target.actor, player, snapshot) then
        fierceCloseFire = true
    end
    if distance <= shoveDistance and not fierceCloseFire
        and utility.sameFloor(actor, target.actor)
        and not lineBlockedByFriendly(actor, target.actor, player, snapshot, "melee") then
        -- One controlled shove buys the next movement decision room to turn.
        accepted = utility.move(actor, "walk", {
            action = "shove", target = target.actor, retreatCounter = true,
        })
        action = "retreat_shove"
    elseif weapon and weapon.equipped and weapon.ranged and weapon.ammo > 0
        and commands.holdFire ~= true and commands.combatDoctrine ~= "stealth"
        and (distance >= coverMinDistance or fierceCloseFire)'''
sc = replace_once(sc, old, new, "s119 retreat counter")
sc = replace_once(sc, '''    if action == "retreat_cover_fire" then claimTarget(target.actor, actor, now) end''', '''    if action == "retreat_cover_fire" then
        claimTarget(target.actor, actor, now)
        if fierceCloseFire then
            print("[SolRetreatFire] accepted plan=fierce distance=" .. tostring(math.floor(distance * 100 + 0.5) / 100)
                .. " ammo=" .. tostring(weapon.ammo) .. " action=fire_then_resume_retreat")
        end
    end''', "s119 retreat trace")

# s120: fierce may choose a loaded, safe firearm shot for a nearby grounded
# zombie. Other plans keep LF's normal stomp/melee finisher behavior.
needle = '    local grounded = groundedTarget(target.actor)'
insert = '''    local grounded = groundedTarget(target.actor)
    local fierceGroundFire = false
    local combatPlans = rawget(_G, "SolCombatPlans")
    local solAuthority = rawget(_G, "SolAuthority")
    if grounded and weapon and weapon.equipped == true and weapon.ranged == true
        and weapon.jammed ~= true and weapon.ammo > 0
        and commands.holdFire ~= true and commands.combatDoctrine == "weapons_free"
        and type(combatPlans) == "table" and type(combatPlans.current) == "function"
        and combatPlans.current(actor) == "fierce"
        and type(solAuthority) == "table" and type(solAuthority.on) == "function"
        and solAuthority.on("grounded_fire") == true
        and distance <= math.min(3.0, math.max(1, tonumber(weapon.range) or 1))
        and target.visible == true and target.obstructed ~= true
        and utility.sameFloor(actor, target.actor)
        and not lineBlockedByFriendly(actor, target.actor, player, snapshot) then
        fierceGroundFire = true
    end'''
sc = replace_once(sc, needle, insert, "s120 grounded gate")
sc = replace_once(sc, '    if weapon and not grounded then',
                  '    if weapon and (not grounded or fierceGroundFire) then', "s120 firearm offering")
oldscore = '''                    score = 54 + math.min(weapon.range, distance) * 2
                        + readiness.combatSkill * 2.2 + readiness.weaponQuality * 8
                        - pressure * 4 - readiness.panic * 5
                        - readiness.stress * 0.08,'''
newscore = '''                    score = grounded and (124 + readiness.combatSkill * 2.2
                        + readiness.weaponQuality * 8 - pressure * 2)
                        or (54 + math.min(weapon.range, distance) * 2
                            + readiness.combatSkill * 2.2 + readiness.weaponQuality * 8
                            - pressure * 4 - readiness.panic * 5 - readiness.stress * 0.08),
                    solGroundedFire = grounded == true,'''
sc = replace_once(sc, oldscore, newscore, "s120 grounded shot score")
texts["SCCombat.lua"] = sc

sd = texts["SolShootDiscipline.lua"]
sd = replace_once(sd, 'M.RESERVE_RANGE = 5.0', 'M.RESERVE_RANGE = 5.0\nM.GROUNDED_FIRE_RANGE = 3.0', "s120 grounded range")
down_fn = '''local function down(z)
    if z == nil then return true end
    return call(z, "isDead") == true or call(z, "isOnFloor") == true or call(z, "isProne") == true
        or call(z, "isCrawling") == true
end'''
down_helper = down_fn + '''
local function groundedFireAllowed(actor, target, weapon, distance)
    if not M.on() or type(target) ~= "table" or type(weapon) ~= "table"
        or weapon.ranged ~= true or weapon.equipped ~= true or (num(weapon.ammo) or 0) <= 0 then return false end
    local plans, authority = rawget(_G, "SolCombatPlans"), rawget(_G, "SolAuthority")
    if type(plans) ~= "table" or type(plans.current) ~= "function"
        or plans.current(actor) ~= "fierce" or type(authority) ~= "table"
        or type(authority.on) ~= "function" or authority.on("grounded_fire") ~= true then return false end
    local isDown = target.grounded == true or target.fallen == true or down(target.actor)
    local d = num(distance) or targetDistance(actor, target)
    return isDown and d ~= nil and d <= math.min(M.GROUNDED_FIRE_RANGE, M.effectiveRange(weapon.item, weapon.range))
end'''
sd = replace_once(sd, down_fn, down_helper, "s120 grounded-fire policy")
oldgate = '''    -- a zombie that is down is LF's finisher's (stomp / melee), never a round
    if target.grounded == true or target.fallen == true or down(target.actor) then
        holdAim(actor, target, st)
        logEvery("down", "hold: the zombie is down (d=" .. f1(d) .. "), left to a stomp or a blow")
        st.reason = "target_down"
        return true, "aiming"
    end
    local isUrgent = urgent(actor, player, target, d)'''
newgate = '''    -- Normal plans finish grounded targets physically; fierce has a tightly bounded firearm exception.
    local isDown = target.grounded == true or target.fallen == true or down(target.actor)
    local fierceDownShot = isDown and groundedFireAllowed(actor, target, weapon, d)
    if isDown and not fierceDownShot then
        holdAim(actor, target, st)
        logEvery("down", "hold: the zombie is down (d=" .. f1(d) .. "), left to a stomp or a blow")
        st.reason = "target_down"
        return true, "aiming"
    end
    local isUrgent = fierceDownShot or urgent(actor, player, target, d)'''
sd = replace_once(sd, oldgate, newgate, "s120 grounded gate override")
sd = replace_once(sd, '    if aimReason == "aim_not_safe" then',
                  '    if aimReason == "aim_not_safe" and not fierceDownShot then', "s120 downed close shot")
oldwait = '    local maxWait = emergency and M.EMERGENCY_MAX_SETTLE_MS or M.MAX_SETTLE_MS'
newwait = '''    local maxWait = fierceDownShot and 200 or (emergency and M.EMERGENCY_MAX_SETTLE_MS or M.MAX_SETTLE_MS)
    local plans, authority = rawget(_G, "SolCombatPlans"), rawget(_G, "SolAuthority")
    if emergency and not fierceDownShot and type(plans) == "table" and type(plans.current) == "function"
        and plans.current(actor) == "fierce" and type(authority) == "table"
        and type(authority.on) == "function" and authority.on("fierce_fast_react") == true then
        maxWait = math.min(maxWait, 250)
    end'''
sd = replace_once(sd, oldwait, newwait, "s120 fierce urgency cap")
oldshape = '''        if a.kind == "shoot" and isDown then
            actions[i] = { kind = "hold_range", score = math.min(num(a.score) or 0, 40), sdHold = "target_down" }'''
newshape = '''        local allowGroundedFire = a.kind == "shoot" and a.solGroundedFire == true
            and groundedFireAllowed(actor, target, weapon, d)
        if a.kind == "shoot" and isDown and not allowGroundedFire then
            actions[i] = { kind = "hold_range", score = math.min(num(a.score) or 0, 40), sdHold = "target_down" }'''
sd = replace_once(sd, oldshape, newshape, "s120 grounded action shaping")
texts["SolShootDiscipline.lua"] = sd

auth = texts["SolAuthority.lua"]
for fix, comment in (("retreat_close_fire", "s119: fierce cover-fire while retreating"),
                     ("grounded_fire", "s120: fierce firearm finisher for a nearby downed zombie"),
                     ("fierce_fast_react", "s120: shorter aim-settle cap on urgent fierce targets")):
    if f'"{fix}"' not in auth:
        auth = replace_once(auth, 'A.FIXES = {', f'A.FIXES = {{\n    "{fix}", -- {comment}', "register " + fix)
texts["SolAuthority.lua"] = auth

# Finish transformations and validate anchors before making any installed change.
if "fierceCloseFire = true" not in texts["SCCombat.lua"] or "fierceGroundFire = true" not in texts["SCCombat.lua"]:
    raise SystemExit("REFUSED: SCCombat candidate invariant failed")
for token in ("groundedFireAllowed(actor, target, weapon, d)", "maxWait = math.min(maxWait, 250)",
              'a.solGroundedFire == true'):
    if token not in texts["SolShootDiscipline.lua"]:
        raise SystemExit("REFUSED: shooting-discipline candidate invariant failed: " + token)

switch_text = open(SWITCHES, encoding="ascii").read()
for fix in ("retreat_close_fire", "grounded_fire", "fierce_fast_react"):
    import re
    if not re.search(rf"(?m)^{fix}=on\s*$", switch_text):
        switch_text = re.sub(rf"(?m)^{fix}=.*$", "", switch_text).rstrip("\r\n")
        switch_text += f"\r\n{fix}=on\r\n"

if BACKUP:
    os.makedirs(BACKUP)
    for name, path in paths.items():
        shutil.copy2(path, os.path.join(BACKUP, name + ".before"))
    shutil.copy2(SWITCHES, os.path.join(BACKUP, "SolFixes_LAB.txt.before"))
for name, path in paths.items():
    write_lua(path, texts[name], crlfs[name])
tmp = SWITCHES + ".s119s120.tmp"
with open(tmp, "w", encoding="ascii", newline="") as f:
    f.write(switch_text)
os.replace(tmp, SWITCHES)

print("Applied s119 + s120 into " + ("SOL_LAB" if LAB else "candidate tree"))
if BACKUP:
    print("Backup=" + BACKUP)
print("Switches: retreat_close_fire=on grounded_fire=on fierce_fast_react=on")
if LAB:
    print("RELEASE, Steam profile, and player saves untouched")
