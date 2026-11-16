"""s105 combat_plans offline (kahlua_env), game side. Loads the REAL Living Fellows SCGameplayUtil / SCStableValue / SCCommands /
SCCombat (patched by the installer on a temp copy) and EFZ's real TW/Core (Workshop, read-only) for the silencer check; only the
Java objects (Sol, him, zombies, weapons, inventory) are fakes. Knobs are read back from LF's own state (Commands.peek) after LF's
own Commands.issue ran. Weapon choice runs through the real chooseWeapon (Combat.equipPreferred); actions through the real
actionUtilities (Combat._actionUtilitiesForTests); lanes through the real Combat.friendlyFireBlocked (wrapped).
Shows: every plan sets the right knobs (and restores follow distance / move mode); smart switches melee / firearm by count and
for a zombie near him; fierce leaves zombies beyond 25 tiles of him; stealth with an unsilenced gun uses melee and never shoots,
a silenced one may; never across him; retreat under 30%; reset to smart on death / a new Sol; switch off = as before;
installer idempotent, either order with s104 gives the same file; tonumber + jarcall gates; ASCII.
Run: python test_s105_combat_plans.py [client dir]"""
import os, sys, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kahlua_env import lua51
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
SHARED = os.path.join(CL, "..", "shared")
EFZ = r"C:/Program Files (x86)/Steam/steamapps/workshop/content/108600/3824755284/mods/EscapeFromZomboidFirearms/42/media/lua/shared/"
FAIL, P = [], []
def ck(n, c, d=""): print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else "")); (P if c else FAIL).append(n)
def run(script, d): return subprocess.run([sys.executable, os.path.join(HERE, script), d], capture_output=True, text=True)
tmp = tempfile.mkdtemp(prefix="s105cp_")
def copy_client(name):
    d = os.path.join(tmp, name); os.makedirs(d)
    for f in os.listdir(CL):
        if f.endswith(".lua"): shutil.copy(os.path.join(CL, f), d)
    return d
cl = copy_client("client")
r1, r2 = run("apply_s105_combat_plans.py", cl), run("apply_s105_combat_plans.py", cl)
ck("installer runs", r1.returncode == 0 and "applied" in r1.stdout, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout, r2.stdout + r2.stderr)
if os.path.exists(os.path.join(HERE, "apply_s104_shooting_discipline.py")):
    a, b = copy_client("a"), copy_client("b")
    ra = [run(s, a) for s in ("apply_s105_combat_plans.py", "apply_s104_shooting_discipline.py", "apply_s105_combat_plans.py", "apply_s104_shooting_discipline.py")]
    rb = [run(s, b) for s in ("apply_s104_shooting_discipline.py", "apply_s105_combat_plans.py", "apply_s104_shooting_discipline.py", "apply_s105_combat_plans.py")]
    ck("with s104: both install orders run", all(r.returncode == 0 for r in ra + rb), "".join(r.stdout + r.stderr for r in ra + rb)[-600:])
    ck("with s104: re-runs change nothing (either order)", all("edited" not in r.stdout for r in ra[2:] + rb[2:]))
    ck("with s104: either order gives the same SCCombat", open(os.path.join(a, "SCCombat.lua"), encoding="utf-8").read() == open(os.path.join(b, "SCCombat.lua"), encoding="utf-8").read())
L = lua51.LuaRuntime()
comp = L.eval("function(s) local f, e = loadstring(s); return f ~= nil, e end")
for f in ("SolCombatPlans.lua", "SCCombat.lua", "SolAuthority.lua"):
    src = open(os.path.join(cl, f), encoding="utf-8").read()
    ok, e = comp(src); ck("compiles " + f, ok, e)
    ck("ascii " + f, all(ord(c) < 128 for c in src))
combat = open(os.path.join(cl, "SCCombat.lua"), encoding="utf-8").read()
ck("SCCombat carries 3 s105 hooks", combat.count("-- s105 combat_plans") == 3, combat.count("-- s105 combat_plans"))
ck("SolAuthority lists combat_plans", '"combat_plans"' in open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read())

def P_(s): return os.path.abspath(s).replace("\\", "/")
L.execute('package.path = [[%s/?.lua;%s/?.lua;%s?.lua]]' % (P_(cl), P_(SHARED), EFZ))
L.execute(r'''
HANDLERS = {}
Events = setmetatable({}, {__index = function(t, k) local e = {Add = function(f) HANDLERS[k] = HANDLERS[k] or {}; table.insert(HANDLERS[k], f) end, Remove = function() end}; rawset(t, k, e); return e end})
NOW = 100000; getTimestampMs = function() return NOW end; isClient = function() return false end; isServer = function() return false end
SW = { combat_plans = true }
SolAuthority = { on = function(n) return SW[n] == true end }
LOG = {}; local rawPrint = print; print = function(s) LOG[#LOG + 1] = tostring(s) end
function logged(s) for _, l in ipairs(LOG) do if string.find(l, s, 1, true) then return true end end return false end
MD = {}; ModData = { getOrCreate = function(k) MD[k] = MD[k] or {}; return MD[k] end }
function instanceof(o, cls) return type(o) == "table" and (o.cls == cls or (cls == "zombie.inventory.types.HandWeapon" and o.cls == "HandWeapon")) end
-- weapons (InventoryItem / HandWeapon, the methods SCCombat.weaponRecord reads)
local IT = {}; IT.__index = IT
function item(t, o) o = o or {}; local i = setmetatable({ t = t, cls = "HandWeapon", ranged = o.ranged == true, md = {}, dmg = o.dmg or 2, range = o.range or (o.ranged and 30 or 1.5) }, IT); return i end
function IT:getFullType() return self.t end
function IT:getType() return (string.match(self.t, "%.(.+)$")) end
function IT:getDisplayName() return self:getType() end
function IT:getName() return self:getType() end
function IT:getCategory() return "Weapon" end
function IT:hasModData() return true end
function IT:getModData() return self.md end
function IT:isRanged() return self.ranged end
function IT:isJammed() return false end
function IT:getCondition() return 10 end
function IT:getConditionMax() return 10 end
function IT:getCurrentAmmoCount() return self.ranged and 20 or 0 end
function IT:getMaxAmmo() return self.ranged and 20 or 0 end
function IT:getMaxDamage() return self.dmg end
function IT:getMaxRange() return self.range end
function IT:getMinRange() return 0 end
function IT:getSwingTime() return 1 end
function IT:getActualWeight() return 2 end
function IT:getEnduranceMod() return 1 end
function IT:getSharpness() return 1 end
function IT:isTwoHandWeapon() return true end
function IT:getContainer() return nil end
KATANA = item("Base.Katana"); M4 = item("EscapeFromZomboidFirearms.M4A1", { ranged = true, dmg = 3 })
function inventory(list) local inv = { list = list }
    function inv:contains(i) for _, x in ipairs(self.list) do if x == i then return true end end return false end
    function inv:getItems() local l = self.list; return { size = function() return #l end, get = function(_, i) return l[i + 1] end } end
    function inv:getAllCategoryRecurse(cat, out) assert(type(cat) == "string" and out ~= nil, "B42: getAllCategoryRecurse(String, ArrayList)"); for _, x in ipairs(self.list) do out:add(x) end; return out end
    return inv end
function mkActor(id, o) o = o or {}
    local a = { md = { SC_Id = id, SC_Recruited = true }, x = o.x or 0, y = o.y or 0, z = 0, hand = o.hand, inv = inventory(o.items or {}), dead = false }
    function a:getModData() return self.md end
    function a:getX() return self.x end function a:getY() return self.y end function a:getZ() return self.z end
    function a:isDead() return self.dead end
    function a:getPrimaryHandItem() return self.hand end
    function a:getSecondaryHandItem() return nil end
    function a:getInventory() return self.inv end
    return a end
function zed(x, y) local z = { x = x, y = y, z = 0 }
    function z:getX() return self.x end function z:getY() return self.y end function z:getZ() return self.z end
    return z end
ArrayList = { new = function() local l = { n = {} }; function l:add(x) self.n[#self.n + 1] = x end; function l:size() return #self.n end; function l:get(i) return self.n[i + 1] end; return l end }
PLAYER = mkActor("player", { x = 0, y = 0 }); getSpecificPlayer = function(i) return PLAYER end
SOL = mkActor("sol-1", { x = 2, y = 0, hand = M4, items = { KATANA, M4 } })
''')
for m in ("SCStableValue", "SCGameplayUtil", "SCCommands", "SCCombat"):
    ok = L.eval('(function() local ok, e = pcall(require, "%s"); return ok end)()' % m); ck("real LF " + m + " loads offline", ok is True)
L.execute(r'''
SC = SurvivorCompanion; GU = SC.GameplayUtil
ACTORS = { ["sol-1"] = SOL }
GU.resolveActor = function(id) local a = ACTORS[id]; if a then return a, { id = id, recruited = true } end return nil end
GU.idOf = function(a) return type(a) == "table" and a.md and a.md.SC_Id or nil end
GU.isDead = function(a) return type(a) == "table" and a.dead == true end
GU.isValidActor = function(a) return type(a) == "table" and a.md ~= nil and a.dead ~= true end
EQUIPS = {}
GU.move = function(a, mode, intent) if type(intent) == "table" and intent.action == "equip_weapon" then EQUIPS[#EQUIPS + 1] = intent.item; a.hand = intent.item end; return true, "ok" end
SC.ActionSupervisor = nil
SC.InventoryIndex = nil
package.loaded["SolActions"] = true
SW.combat_equip_fallback, SW.preferred_weapon = true, true                   -- s98 and s99 (real files, as installed in the lab)
SolUI = { solActor = function() return SOL end, runAction = function(id, o) return false, "unknown_action" end, actionCatalog = function() return { { id = "follow" } } end }
''')
for f in ("SolWeaponPick.lua", "SolCombatEquipFallback.lua"):
    if os.path.exists(os.path.join(cl, f)): L.execute(open(os.path.join(cl, f), encoding="utf-8").read())
L.execute(open(os.path.join(cl, "SolCombatPlans.lua"), encoding="utf-8").read())
ev = L.eval
ck("s98 / s99 real files loaded beside it", ev('type(SolWeaponPick) == "table" and type(SolCombatEquipFallback) == "table"'))
ck("module loads and registers its install at OnGameStart", ev('type(SolCombatPlans) == "table" and HANDLERS.OnGameStart ~= nil and #HANDLERS.OnGameStart == 1'))
L.execute('for _, f in ipairs(HANDLERS.OnGameStart) do f() end')
ck("install wraps LF's friendlyFireBlocked and scoreTargets, ticks, hears deaths", ev('SolCombatPlans._ffWrapped == true and SolCombatPlans._stWrapped == true and HANDLERS.OnTick ~= nil and HANDLERS.OnCharacterDeath ~= nil'))
L.execute(r'''
function knobs() local s = SC.Commands.peek(SOL); return string.format("%s/%s/%s/%s", tostring(s.combatMode), tostring(s.combatDoctrine), tostring(s.weaponPriority), tostring(s.holdFire)) end
function lf() return SC.Commands.peek(SOL) end
function setPlan(p) SolCombatPlans.forgetSol(); return SolUI.runAction("sol_combat_plan", p) end
''')

# ------------------------------------------------ every plan sets LF's knobs (LF's own Commands.issue, read back from LF's state)
EXPECT = {   # M4A1 in her hands: "kind" plans take firearm
    "smart":   "defensive/close_defense/best/false",
    "normal":  "defensive/close_defense/firearm/false",
    "fierce":  "aggressive/weapons_free/firearm/false",
    "support": "defensive/ranged_support/firearm/false",
    "careful": "passive/close_defense/best/false",
    "stealth": "passive/stealth/quiet/false",
    "avoid":   "passive/stealth/best/false",
    "hold":    "defensive/close_defense/melee/true",
}
L.execute('lf().followDistance = 3; lf().moveMode = "walk"')
for plan, want in EXPECT.items():
    ok, why = ev('(function() local ok, why = setPlan("%s"); return {ok, why} end)()' % plan).values()
    got = ev('knobs()')
    ck("plan %s sets %s" % (plan, want), ok is True and got == want and why == "plan_" + plan, "%s %s -> %s" % (ok, why, got))
    ck("plan %s is stored as the current plan" % plan, ev('SolCombatPlans.current(SOL)') == plan)
ck("careful: LF's passive mode is persisted with close_defense (SC_CombatMode)", ev('(function() setPlan("careful"); return SOL.md.SC_CombatMode == "passive" and SOL.md.SC_CombatDoctrine == "close_defense" end)()'))
ck("support: follow distance 5 (LF's 4-8 band behind him)", ev('(function() setPlan("support"); return lf().followDistance == 5 end)()'))
ck("leaving support: his follow distance comes back (3)", ev('(function() setPlan("smart"); return lf().followDistance == 3 end)()'))
ck("stealth: she sneaks", ev('(function() setPlan("stealth"); return lf().moveMode == "sneak" end)()'))
ck("leaving stealth: her move mode comes back (walk)", ev('(function() setPlan("normal"); return lf().moveMode == "walk" end)()'))
ck("normal / fierce with no gun on her: priority best", ev('(function() SOL.hand = KATANA; SOL.inv.list = { KATANA }; SolWeaponPick.cache = setmetatable({}, { __mode = "k" }); setPlan("fierce"); local k = knobs(); setPlan("normal"); local k2 = knobs(); SOL.inv.list = { KATANA, M4 }; SolWeaponPick.cache = setmetatable({}, { __mode = "k" }); SOL.hand = M4; return k == "aggressive/weapons_free/best/false" and k2 == "defensive/close_defense/best/false" end)()'))
ck("normal with a gun in her bag, katana in hand, no pick: firearm (s99 weapon list)", ev('(function() SOL.hand = KATANA; SolWeaponPick.cache = setmetatable({}, { __mode = "k" }); setPlan("normal"); local k = knobs(); SOL.hand = M4; return k == "defensive/close_defense/firearm/false" end)()'))
ck("his pick (s98 marker) on the katana decides the kind: best", ev('(function() KATANA.md.SC_ManualEquipFor = "sol-1"; setPlan("normal"); local k = knobs(); KATANA.md.SC_ManualEquipFor = nil; return k == "defensive/close_defense/best/false" end)()'))
ck("aliases: aggressive -> fierce, hold_fire -> hold", ev('(function() local a = select(2, setPlan("aggressive")); local b = select(2, setPlan("Hold Fire")); return a == "plan_fierce" and b == "plan_hold" end)()'))
ck("an unknown plan is refused and changes nothing", ev('(function() setPlan("smart"); local before = knobs(); local ok, why = setPlan("banana"); return ok == false and why == "unknown_option" and knobs() == before and SolCombatPlans.current(SOL) == "smart" end)()'))
ck("no Sol: refused (no_sol)", ev('(function() local s = SolUI.solActor; SolUI.solActor = function() return nil end; local ok, why = setPlan("careful"); SolUI.solActor = s; return ok == false and why == "no_sol" end)()'))
ck("LF refuses (not recruited): the plan is not stored", ev('(function() setPlan("smart"); SOL.md.SC_Recruited = false; local st = lf(); st.recruited = false; local ok, why = setPlan("fierce"); st.recruited = true; SOL.md.SC_Recruited = true; return ok == false and why == "not_recruited" and SolCombatPlans.current(SOL) == "smart" end)()'))
ck("catalog lists sol_combat_plan with the plan as its state", ev('(function() setPlan("careful"); for _, e in ipairs(SolUI.actionCatalog()) do if e.id == "sol_combat_plan" then return e.state == "careful" and e.enabled == true end end return false end)()'))

# ------------------------------------------------ smart: melee for 1-2, firearm for 3+ or one near him (back after 4 s)
L.execute(r'''
function rec(z) local dx, dy = z.x - SOL.x, z.y - SOL.y; return { actor = z, distanceSq = dx * dx + dy * dy, score = 50 } end
function scoredOf(pts) local t = {}; for _, p in ipairs(pts) do t[#t + 1] = rec(zed(p[1], p[2])) end; return t end
function pref(pts, p0) return SolCombatPlans.preference(SOL, PLAYER, {}, scoredOf(pts), lf(), p0 or "best", false) end
''')
L.execute('setPlan("smart"); SOL.x, SOL.y = 2, 0; PLAYER.x, PLAYER.y = 0, 0; SolCombatPlans.group = setmetatable({}, { __mode = "k" })')
ck("smart: 1 zombie -> melee", ev('pref({ { 8, 0 } })') == "melee")
ck("smart: 2 zombies -> melee", ev('pref({ { 8, 0 }, { 9, 1 } })') == "melee")
ck("smart: 3 zombies within 10 tiles -> firearm", ev('pref({ { 8, 0 }, { 9, 1 }, { 10, -1 } })') == "firearm")
ck("smart: right after, 1 left -> firearm still (4 s hold)", ev('(function() NOW = NOW + 1000; return pref({ { 8, 0 } }) end)()') == "firearm")
ck("smart: 4 s later with 1-2 left -> back to melee", ev('(function() NOW = NOW + 4001; return pref({ { 8, 0 }, { 9, 0 } }) end)()') == "melee")
ck("smart: 3 zombies but 2 beyond 10 tiles -> melee", ev('(function() NOW = NOW + 5000; return pref({ { 8, 0 }, { 20, 0 }, { 25, 0 } }) end)()') == "melee")
ck("smart: one zombie 2 tiles from him -> firearm (a threat to him)", ev('(function() NOW = NOW + 5000; return pref({ { -2, 0 } }) end)()') == "firearm")
ck("smart: seated (car) -> LF's own rule", ev('(function() NOW = NOW + 5000; return SolCombatPlans.preference(SOL, PLAYER, {}, scoredOf({ { 8, 0 }, { 9, 0 }, { 9, 1 } }), lf(), "firearm", true) end)()') == "firearm")
# the real chooseWeapon (Combat.equipPreferred): smart picks by kind even with the M4A1 marked as his pick (s98) and in her hands
L.execute('M4.md.SC_ManualEquipFor = "sol-1"')
ck("real chooseWeapon, smart at rest (1 zombie): the katana, though the M4A1 is his pick and in her hands", ev('(function() NOW = NOW + 5000; pref({ { 8, 0 } }); SOL.hand = M4; EQUIPS = {}; local ok, why, d = SC.Combat.equipPreferred(SOL, "melee"); return EQUIPS[1] == KATANA and SOL.hand == KATANA end)()'))
ck("real chooseWeapon, smart with a group: the M4A1", ev('(function() pref({ { 8, 0 }, { 9, 0 }, { 9, 1 } }); EQUIPS = {}; local ok, why = SC.Combat.equipPreferred(SOL, "firearm"); return SOL.hand == M4 and (EQUIPS[1] == M4 or why == "weapon_already_equipped") end)()'))
ck("real chooseWeapon, plan normal: LF + s98 as before (his pick, the M4A1)", ev('(function() setPlan("normal"); SOL.hand = KATANA; EQUIPS = {}; SC.Combat.equipPreferred(SOL, "best"); return SOL.hand == M4 end)()'))
ck("real chooseWeapon, plan hold: melee (the katana)", ev('(function() setPlan("hold"); SOL.hand = M4; EQUIPS = {}; SC.Combat.equipPreferred(SOL, "melee"); return SOL.hand == KATANA end)()'))
ck("smart without a usable melee weapon: LF chooses (no forced kind)", ev('(function() setPlan("smart"); local w = SolCombatPlans.choose(SOL, { { item = M4, ranged = true, equipped = true, score = 10 } }, function() return true end, "best"); return w == nil end)()'))
L.execute('M4.md.SC_ManualEquipFor = nil')

# ------------------------------------------------ stealth: EFZ silencer (real TW/Core C.stats), melee otherwise, never a loud shot
L.execute(r'''
EFZC = require("TW/Core")
SILENCER = nil; for k, v in pairs(EFZC.data.items) do if v.category == "Silencer" then SILENCER = k; break end end
TREES = {}
TWRuntime = { key = function(it) return it == M4 and "M4A1" or nil end, read = function(it) return TREES[it] or {}, {}, {}, nil end }
function resetSil() SolCombatPlans.silencedCache = setmetatable({}, { __mode = "k" }) end
''')
ck("EFZ's real TW/Core: an M4A1 without a silencer is not silenced", ev('(function() resetSil(); TREES[M4] = {}; return SolCombatPlans.silenced(M4) == false end)()'))
ck("EFZ's real TW/Core: with a Silencer part on the muzzle it is", ev('(function() resetSil(); TREES[M4] = { ["mod_reciever/mod_barrel/mod_muzzle"] = SILENCER }; return SILENCER ~= nil and SolCombatPlans.silenced(M4) == true end)()'))
L.execute('setPlan("stealth"); resetSil(); TREES[M4] = {}; M4.md.SC_ManualEquipFor = "sol-1"')
ck("stealth + unsilenced gun (his pick, in her hands): the real chooseWeapon gives melee", ev('(function() SOL.hand = M4; EQUIPS = {}; SC.Combat.equipPreferred(SOL, "quiet"); return SOL.hand == KATANA end)()'))
ck("stealth + silenced gun (his pick): she may keep the gun", ev('(function() resetSil(); TREES[M4] = { ["mod_reciever/mod_barrel/mod_muzzle"] = SILENCER }; SOL.hand = M4; EQUIPS = {}; SC.Combat.equipPreferred(SOL, "quiet"); return SOL.hand == M4 end)()'))
L.execute(r'''
function utilities(weapon, health)
    local z = zed(SOL.x + 8, SOL.y)
    local target = { actor = z, distanceSq = 64, visible = true, obstructed = false, bearing = "front" }
    local readiness = { health = health or 100, close = 0, occupiedSectors = 0, endurance = 1, strength = 5, nimble = 0, fitness = 5,
        combatSkill = 3, weaponQuality = 1, panic = 0, stress = 0, immediate = 0, woundPressure = 0, pain = 0, heavyLoad = 0,
        escapeDanger = 0, staminaCritical = false, support = 0, footing = { crowd = 0 } }
    local acts = SC.Combat._actionUtilitiesForTests(SOL, PLAYER, { threats = {}, escapeSquares = { {} } }, target, weapon, SOL.inv, lf(), readiness)
    local kinds = {}; for _, a in ipairs(acts) do kinds[#kinds + 1] = a.kind end
    return acts, table.concat(kinds, ",")
end
function gunRec() return { item = M4, ranged = true, ammo = 20, maxAmmo = 20, range = 30, jammed = false, equipped = true, condition = 10, conditionRatio = 1 } end
''')
L.execute('PLAYER.x, PLAYER.y = -5, 5')
ok, kinds = ev('(function() resetSil(); TREES[M4] = {}; local ok, acts, k = pcall(utilities, gunRec()); return {ok, k or acts} end)()').values()
ck("real actionUtilities runs offline with the hooks", ok is True, kinds)
ck("stealth + unsilenced gun: no shoot action (real actionUtilities)", ok is True and "shoot" not in str(kinds).split(","), kinds)
ok2, kinds2 = ev('(function() resetSil(); TREES[M4] = { ["mod_reciever/mod_barrel/mod_muzzle"] = SILENCER }; local ok, acts, k = pcall(utilities, gunRec()); return {ok, k or acts} end)()').values()
ck("stealth + silenced gun: the shot stays", ok2 is True and "shoot" in str(kinds2).split(","), kinds2)
ok3, kinds3 = ev('(function() setPlan("normal"); resetSil(); TREES[M4] = {}; local ok, acts, k = pcall(utilities, gunRec()); return {ok, k or acts} end)()').values()
ck("normal + unsilenced gun: the shot stays", ok3 is True and "shoot" in str(kinds3).split(","), kinds3)
L.execute('M4.md.SC_ManualEquipFor = nil')

# ------------------------------------------------ every plan: retreat under 30% health
for plan in ("fierce", "smart"):
    r = ev('(function() setPlan("%s"); local ok, acts = pcall(utilities, gunRec(), 25); if not ok then return tostring(acts) end; return acts[1].kind .. ":" .. tostring(acts[1].score) end)()' % plan)
    ck("%s at 25%% health: retreat comes first (real actionUtilities)" % plan, str(r).startswith("retreat:500"), r)
r = ev('(function() setPlan("fierce"); local ok, acts = pcall(utilities, gunRec(), 80); if not ok then return tostring(acts) end; return acts[1].kind end)()')
ck("fierce at 80% health: not forced to retreat", r != "retreat", r)

# ------------------------------------------------ never across him (the real Combat.friendlyFireBlocked, wrapped)
L.execute(r'''
function blocked(sx, sy, tx, ty, px, py, kind) SOL.x, SOL.y = sx, sy; PLAYER.x, PLAYER.y = px, py
    local b, who = SC.Combat.friendlyFireBlocked(SOL, zed(tx, ty), { player = PLAYER, kind = kind or "ranged" }); return b == true end
''')
ck("him 1.0 tile off the lane, halfway: blocked", ev('blocked(0, 0, 10, 0, 5, 1.0)'))
ck("LF alone allows it (corridor 0.8): the new rule is what blocks", ev('(function() SW.combat_plans = false; local b = blocked(0, 0, 10, 0, 5, 1.0); SW.combat_plans = true; return b == false end)()'))
ck("him behind the zombie in the line of fire (4 tiles past it): blocked", ev('blocked(0, 0, 10, 0, 14, 0.5)'))
ck("him 3 tiles off the lane: the shot is fine", ev('blocked(0, 0, 10, 0, 5, 3) == false'))
ck("him right beside her (she shoots away from him): fine", ev('blocked(0, 0, 10, 0, 0, 1) == false'))
ck("him behind HER: fine", ev('blocked(0, 0, 10, 0, -3, 0) == false'))
ck("melee lane: LF's own rule only", ev('blocked(0, 0, 10, 0, 5, 1.0, "melee") == false'))
ck("another survivor (not Sol): LF's own rule only", ev('(function() local s = SolUI.solActor; SolUI.solActor = function() return nil end; SolCombatPlans.forgetSol(); local b = blocked(0, 0, 10, 0, 5, 1.0); SolUI.solActor = s; SolCombatPlans.forgetSol(); return b == false end)()'))

# ------------------------------------------------ fierce: 25 tiles from him (the real scoreTargets wrapped; leash on its result)
L.execute(r'''
function leashRun(pts) local base = function() return scoredOf(pts) end; local out = SolCombatPlans.scoreTargets(base, SOL, PLAYER, {}, nil); return #out end
''')
L.execute('SolCombatPlans.forgetSol(); PLAYER.x, PLAYER.y = 0, 0; SOL.x, SOL.y = 15, 0')
ck("fierce: zombies 20 and 24 tiles from him are hers; 26 and 40 are not", ev('(function() setPlan("fierce"); return leashRun({ { 20, 0 }, { 24, 0 }, { 26, 0 }, { 40, 0 } }) end)()') == 2)
ck("fierce: one beyond 25 that is attacking her is still hers", ev('(function() local base = function() local t = scoredOf({ { 30, 0 } }); t[1].attacking = true; return t end; return #SolCombatPlans.scoreTargets(base, SOL, PLAYER, {}, nil) end)()') == 1)
ck("normal: no leash", ev('(function() setPlan("normal"); return leashRun({ { 20, 0 }, { 40, 0 } }) end)()') == 2)
ck("the wrapped Combat.scoreTargets still runs LF's own scoring (empty snapshot -> empty list)", ev('(function() setPlan("fierce"); local ok, t = pcall(SC.Combat.scoreTargets, SOL, PLAYER, { threats = {} }, nil); return ok and type(t) == "table" and #t == 0 end)()'))

# ------------------------------------------------ her death: back to smart; a new Sol gets smart's knobs
L.execute('setPlan("fierce")')
ck("before her death: fierce", ev('SolCombatPlans.current(SOL)') == "fierce" and ev('knobs()') == "aggressive/weapons_free/firearm/false")
L.execute(r'''
SOL.dead = true; for _, f in ipairs(HANDLERS.OnCharacterDeath) do f(SOL) end
SOL2 = mkActor("sol-2", { x = 2, y = 0, hand = M4, items = { KATANA, M4 } }); ACTORS["sol-2"] = SOL2
SolUI.solActor = function() return SOL2 end; SolCombatPlans.forgetSol()
''')
ck("her death: the plan is back to smart", ev('SolCombatPlans.store().plan') == "smart" and ev('logged("she died: the plan goes back to smart")'))
L.execute('NOW = NOW + 3000; for _, f in ipairs(HANDLERS.OnTick) do f() end')
ck("the next Sol: plan smart and smart's knobs on her (LF state)", ev('(function() local s = SC.Commands.peek(SOL2); return SolCombatPlans.current(SOL2) == "smart" and s.combatDoctrine == "close_defense" and s.combatMode == "defensive" and s.weaponPriority == "best" and s.holdFire == false end)()'))
ck("the pending reset is done (not applied again)", ev('SolCombatPlans.store().pending == nil'))
L.execute(r'''
SolUI.runAction("sol_combat_plan", "careful")
SOL3 = mkActor("sol-3", { x = 2, y = 0 }); ACTORS["sol-3"] = SOL3; SolUI.solActor = function() return SOL3 end; SolCombatPlans.forgetSol()
''')
ck("a new Sol without a death event (respawn seen by id): current plan smart at once", ev('SolCombatPlans.current(SOL3)') == "smart")
L.execute('NOW = NOW + 3000; for _, f in ipairs(HANDLERS.OnTick) do f() end')
ck("... and the tick gives her smart's knobs", ev('(function() local s = SC.Commands.peek(SOL3); return SolCombatPlans.store().id == "sol-3" and s.combatDoctrine == "close_defense" and s.weaponPriority == "best" end)()'))
L.execute('SolUI.solActor = function() return SOL end; ACTORS["sol-1"] = SOL; SOL.dead = false; SolCombatPlans.forgetSol(); SolCombatPlans.store().id = "sol-1"')

# ------------------------------------------------ switch off = as before
L.execute('SolUI.runAction("sol_combat_plan", "stealth"); SW.combat_plans = false')
ck("off: sol_combat_plan is not in the catalog", ev('(function() for _, e in ipairs(SolUI.actionCatalog()) do if e.id == "sol_combat_plan" then return false end end return true end)()'))
ck("off: the verb falls through to the old runAction", ev('(function() local ok, why = SolUI.runAction("sol_combat_plan", "fierce"); return ok == false and why == "unknown_action" end)()'))
ck("off: preference passes LF's through", ev('pref({ { 8, 0 }, { 9, 0 }, { 9, 1 } }, "best")') == "best")
ck("off: choose leaves the weapon to LF / s98", ev('SolCombatPlans.choose(SOL, { { item = KATANA, ranged = false, score = 1 } }, function() return true end, "best") == nil'))
ck("off: shape changes nothing (stealth, loud gun, 20% health)", ev('(function() local a = { { kind = "retreat", score = 10 }, { kind = "shoot", score = 90 } }; SolCombatPlans.shape(SOL, PLAYER, {}, gunRec(), { health = 20 }, a); return #a == 2 and a[1].score == 10 end)()'))
ck("off: lanes are LF's own (corridor 0.8)", ev('blocked(0, 0, 10, 0, 5, 1.0) == false'))
ck("off: no leash", ev('(function() SolCombatPlans.store().plan = "fierce"; return leashRun({ { 20, 0 }, { 40, 0 } }) end)()') == 2)
ck("off: a death leaves the stored plan alone", ev('(function() SolCombatPlans.store().plan = "stealth"; for _, f in ipairs(HANDLERS.OnCharacterDeath) do f(SOL) end; return SolCombatPlans.store().plan == "stealth" end)()'))
L.execute('SW.combat_plans = true')

# ------------------------------------------------ gates
import re
src = open(os.path.join(cl, "SolCombatPlans.lua"), encoding="utf-8").read()
ck("no Java call with a boolean argument in SolCombatPlans (Kahlua overload trap)", re.search(r'(?<![\w.])call\([^)]*,\s*"[A-Za-z]+",[^)]*\b(true|false)\b', src) is None)
ck("no next() on anything in SolCombatPlans", re.search(r'(?<![\w.])next\s*\(', src) is None)
G = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua")
r = subprocess.run([sys.executable, "-I", os.path.join(G, "tonumber_check.py"), cl], capture_output=True, text=True); ck("tonumber gate", r.returncode == 0, r.stdout[-300:])
r = subprocess.run([sys.executable, "-I", os.path.join(G, "jarcall_check.py"), cl], capture_output=True, text=True); ck("jarcall gate", r.returncode == 0, r.stdout[-400:])
print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(P), len(FAIL))); sys.exit(1 if FAIL else 0)
