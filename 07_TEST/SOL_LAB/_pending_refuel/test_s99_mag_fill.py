"""s99 mag_fill + weapon_scan + melee_choice offline. Code under test is CUT FROM THE PATCHED FILES: SCCombat (numberCall, boolCall,
weaponRecord, inventoryWeapons, hasReloadAmmo, weaponUsableNow, equipExactWeapon, chooseWeapon), SCGameplayUtil
(inventoryItems, inventoryItemsDeep: LF's capped walk), SCInventoryIndex (whole file), plus SolMagFill, SolWeaponPick and
SolCombatEquipFallback 0.3.0 as staged. The game is faked: containers with the Java recursive lookups, an EFZ-like G28
(vanilla magazine fields, chamber), Gunworks Magazine/Ammo (profile list, reloadMagazine, GetAutomaticReloadAmmoType) and
the timed actions (ISLoadBulletsInMagazine, ISInsertMagazine which queues its rack like ISInsertMagazine.lua:52-53,
ISRackFirearm like ISRackFirearm.lua:62-64, ISEjectMagazine) run from the queue.
Live replay: 500 loose 7.62x51 rounds before her weapons -> LF sees only the wrench (carried=1).
Run: python test_s99_mag_fill.py [client dir]. Offline PASS is not Runtime PASS."""
import os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
tmp = tempfile.mkdtemp(prefix="s99_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
for f in ("SCCombat.lua", "SCGameplayUtil.lua", "SCInventoryIndex.lua", "SolAuthority.lua"): shutil.copy(os.path.join(CL, f), cl)
fixdir = os.path.join(tmp, "Lua"); os.makedirs(fixdir)
# the installer looks for <client>/../../../../../../Lua/SolFixes_LAB.txt; mimic the depth
deep = os.path.join(tmp, "a", "b", "c", "d", "e", "client"); os.makedirs(deep)
for f in os.listdir(cl): shutil.copy(os.path.join(cl, f), deep)
fixfile = os.path.join(fixdir, "SolFixes_LAB.txt")   # <client>/../ x6 /Lua, as in the lab (client -> ... -> Zomboid/Lua)
open(fixfile, "w", newline="").write("preferred_weapon=on\r\n")
cl = deep
r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s99_mag_fill.py"), cl], capture_output=True, text=True)
ck("installer runs (5 SCCombat edits + 3 switches)", r.returncode == 0 and r.stdout.count("edited") == 8, r.stdout + r.stderr)
r2 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s99_mag_fill.py"), cl], capture_output=True, text=True)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout, r2.stdout + r2.stderr)
fx = open(fixfile, encoding="utf-8").read()
ck("SolFixes_LAB.txt: three switches once each", all(fx.count(s + "=on") == 1 for s in ("mag_fill", "weapon_scan", "melee_choice")), fx)
rd = lambda f: open(os.path.join(cl, f), encoding="utf-8", newline="").read()
CB, GU, IX, AU = rd("SCCombat.lua"), rd("SCGameplayUtil.lua"), rd("SCInventoryIndex.lua"), rd("SolAuthority.lua")
MF, WP, FB = rd("SolMagFill.lua"), rd("SolWeaponPick.lua"), rd("SolCombatEquipFallback.lua")
ck("switches registered in A.FIXES", all('"%s"' % s in AU for s in ("mag_fill", "weapon_scan", "melee_choice")))

def cut(src, start, end, nm):
    i = src.find(start); j = src.find(end, i)
    ck("cut " + nm, i >= 0 and j > i)
    return src[i:j + len(end)]
PARTS = [cut(CB, "local function boolCall(", "\nend\n", "boolCall"),
         cut(CB, "local function numberCall(", "\nend\n", "numberCall"),
         cut(CB, "local function weaponRecord(", "\n    }\nend\n", "weaponRecord"),
         cut(CB, "local function inventoryWeapons(", "\n    return result, inventory, entry\nend\n", "inventoryWeapons"),
         cut(CB, "local function ammoTypeMatches(", "\nend\n", "ammoTypeMatches"),
         cut(CB, "local function ammoShortType(", "\nend\n", "ammoShortType"),
         cut(CB, "local function hasReloadAmmo(", "\n    return false\nend\n", "hasReloadAmmo"),
         cut(CB, "local function weaponUsableNow(", "\nend\n", "weaponUsableNow"),
         cut(CB, "function Combat.equipExactWeapon(", "\n    return equipped, reason\nend\n", "equipExactWeapon"),
         cut(CB, "local function chooseWeapon(", "\n    return best, inventory, entry\nend\n", "chooseWeapon")]
GPARTS = [cut(GU, "function U.inventoryItems(", "\nend\n", "U.inventoryItems"),
          cut(GU, "function U.inventoryItemsDeep(", "\n    return result, containers\nend\n", "U.inventoryItemsDeep")]

ENV = r"""
NOW = 10000
function getTimestampMs() return NOW end
LOGS = {}
function print(m) LOGS[#LOGS + 1] = tostring(m) end
SW = { preferred_weapon = true, combat_equip_fallback = true, mag_fill = true, weapon_scan = true, melee_choice = true }
SolAuthority = { on = function(f) return SW[f] == true end }
SAID = {}
SolOverlay = { speak = function(a, line, ms) SAID[#SAID + 1] = line; return true end }
function isClient() return false end
function isServer() return false end
-- java-like list
function List(t) return { t = t, size = function(self) return #self.t end, get = function(self, i) return self.t[i + 1] end, add = function(self, v) self.t[#self.t + 1] = v end } end
ArrayList = { new = function() return List({}) end }   -- B42 Java: getAllCategoryRecurse(String, ArrayList) only
-- containers with the recursive lookups the game's ItemContainer has
function Cont(items) local c = { items = items or {} }
    function c:getItems() return List(self.items) end
    function c:getContentsWeight() return #self.items end
    local function walk(cont, fn) for _, it in ipairs(cont.items) do fn(it, cont); if it.inv then walk(it.inv, fn) end end end
    c.walk = walk
    function c:getAllTypeRecurse(t) local out = {}; walk(self, function(it) if it.t == t then out[#out + 1] = it end end); return List(out) end
    function c:getAllCategoryRecurse(k, res) if res == nil then error('expected 2 arguments, got 1') end; walk(self, function(it) if it:getCategory() == k then res:add(it) end end); return res end
    function c:getCountTypeRecurse(t) local n = 0; walk(self, function(it) if it.t == t then n = n + 1 end end); return n end
    function c:containsWithModule(t) for _, it in ipairs(self.items) do if it.t == t then return true end end; return false end
    function c:contains(x) for _, it in ipairs(self.items) do if it == x then return true end end; return false end
    function c:Remove(x) for i, it in ipairs(self.items) do if it == x then table.remove(self.items, i); return true end end; return false end
    function c:AddItem(x) self.items[#self.items + 1] = x; return x end
    function c:RemoveOneOf(t) local found, from; walk(self, function(it, cont) if found == nil and it.t == t then found, from = it, cont end end)
        if found then from:Remove(found) end; return found end
    return c end
function Item(full, o) o = o or {}; o.t = full
    function o:getFullType() return self.t end
    function o:getType() return string.match(self.t, "([%w_]+)$") end
    function o:getDisplayName() return self.dn or self.t end
    function o:getCategory() return self.weapon and "Weapon" or "Item" end
    function o:getDisplayCategory() return self.dcat or (self.weapon and "Weapon" or "Ammo") end
    function o:isTwoHandWeapon() return self.two == true end
    function o:hasModData() return self.md ~= nil end
    function o:getModData() self.md = self.md or {}; return self.md end
    function o:getItemContainer() return self.inv end
    if o.weapon then
        function o:getMaxDamage() return self.dmg or 1 end
        function o:isRanged() return self.ranged == true end
        function o:isJammed() return self.jammed == true end
        function o:getCondition() return self.cond or 10 end
        function o:getConditionMax() return 10 end
        function o:getMaxRange() return self.range or 1.2 end
        function o:getSwingTime() return self.swing or 3 end
        function o:getWeight() return self.wt or 1 end
        function o:getEnduranceMod() return 1 end
        function o:getSharpness() return 1 end
        function o:getScriptItem() local s = self; return { containsWeaponCategory = function(_, e) return s.cat == e end } end
    end
    if o.ranged then
        function o:getCurrentAmmoCount() return self.cur or 0 end
        function o:setCurrentAmmoCount(n) self.cur = n end
        function o:getMaxAmmo() return self.max or 10 end
        function o:isRoundChambered() return self.chambered == true end
        function o:setRoundChambered(v) self.chambered = v end
        function o:haveChamber() return true end
        function o:isContainsClip() return self.clip == true end
        function o:setContainsClip(v) self.clip = v end
        function o:getMagazineType() return self.magType end
        function o:getAmmoPerShoot() return 1 end
    end
    if o.mag then
        function o:getCurrentAmmoCount() return self.count or 0 end
        function o:setCurrentAmmoCount(n) self.count = n end
        function o:getMaxAmmo() return self.max end
        function o:getAmmoType() local k = self.key; return { getItemKey = function() return k end } end
    end
    return o end
WeaponCategory = { LONG_BLADE = "LONG_BLADE", AXE = "AXE", BLUNT = "BLUNT", SPEAR = "SPEAR", SMALL_BLADE = "SMALL_BLADE", SMALL_BLUNT = "SMALL_BLUNT" }
-- Gunworks fakes (Magazine.lua:154 / 194-210, Ammo.lua:169-194)
FAMILY = { ["EFZ.G28"] = "762", ["EFZ.G28_Mag10"] = "762", ["EFZ.G28_Mag20"] = "762", ["EFZ.M4A1"] = "556", ["EFZ.M4_Mag30"] = "556" }
BULLETS = { ["762"] = { "EFZ.Ammo_762x51_M80", "EFZ.Ammo_762x51_M61" }, ["556"] = { "EFZ.Ammo_556_M855" } }
PROFILE = { ["EFZ.G28"] = { "EFZ.G28_Mag10", "EFZ.G28_Mag20" }, ["EFZ.M4A1"] = { "EFZ.M4_Mag30" } }
GWAmmo = { GetAutomaticReloadAmmoType = function(p, item)
    local fam = FAMILY[item.t]; if not fam then return nil end
    for _, b in ipairs(BULLETS[fam]) do if p:getInventory():getCountTypeRecurse(b) > 0 then return b end end
    return nil end }
TRANSFERS = 0
ISInventoryPaneContextMenu = {
    transferIfNeeded = function(p, item) if item and item.t and not p:getInventory():contains(item) then
        local moved = false
        p:getInventory().walk(p:getInventory(), function(it, cont) if it == item and not moved then cont:Remove(item); moved = true end end)
        if moved then p:getInventory():AddItem(item); TRANSFERS = TRANSFERS + 1 end end end,
    transferBullets = function(p, t, cur, max) return math.min(p:getInventory():getCountTypeRecurse(t), max - cur) end }
GWMagazine = { GetMagazineTypesForGun = function(gun) return PROFILE[gun.t] end,
    reloadMagazine = function(p, mag)
        local key = GWAmmo.GetAutomaticReloadAmmoType(p, mag); if not key then return 0 end
        local n = mag:getCurrentAmmoCount() + ISInventoryPaneContextMenu.transferBullets(p, key, mag:getCurrentAmmoCount(), mag:getMaxAmmo())
        if n > 0 then ISInventoryPaneContextMenu.transferIfNeeded(p, mag); ISTimedActionQueue.add(ISLoadBulletsInMagazine:new(p, mag, n, nil, key)) end
        return n end }
package.loaded["WeaponSystems/Utils/Magazine"] = GWMagazine
package.loaded["WeaponSystems/Utils/Ammo"] = GWAmmo
-- the timed-action queue (vanilla shape: queue.queue[1] is the current action)
QUEUES = {}
ISTimedActionQueue = {}
function ISTimedActionQueue.getTimedActionQueue(a) QUEUES[a] = QUEUES[a] or { queue = {}, current = nil,
    removeFromQueue = function(self, x) for i, y in ipairs(self.queue) do if y == x then table.remove(self.queue, i); break end end; self.current = self.queue[1] end }
    return QUEUES[a] end
function ISTimedActionQueue.add(x) local q = ISTimedActionQueue.getTimedActionQueue(x.character); q.queue[#q.queue + 1] = x; q.current = q.queue[1]; return q end
function ISTimedActionQueue.addAfter(prev, x) local q = ISTimedActionQueue.getTimedActionQueue(x.character)
    for i, y in ipairs(q.queue) do if y == prev then table.insert(q.queue, i + 1, x); return q, x end end; return nil end
RAN = {}
function DRAIN(a, max) local q = ISTimedActionQueue.getTimedActionQueue(a); local n = 0
    while q.queue[1] and n < (max or 20) do local x = q.queue[1]; q.current = x; RAN[#RAN + 1] = x.Type
        if x.isValid == nil or x:isValid() then x:run() end
        q:removeFromQueue(x); n = n + 1 end; return n end
local function class(name) local c = { Type = name }; c.__index = c
    function c:new(character, ...) local o = setmetatable({ character = character, Type = name }, c); o:init(...); return o end
    function c:forceStop() self.stopped = true; local q = ISTimedActionQueue.getTimedActionQueue(self.character); q:removeFromQueue(self) end
    return c end
ISLoadBulletsInMagazine = class("ISLoadBulletsInMagazine")
function ISLoadBulletsInMagazine:init(mag, count, limit, kind) self.magazine, self.ammoCount, self.ammoLimit, self.kind = mag, count, limit, kind end
function ISLoadBulletsInMagazine:isValid() return self.character:getInventory():contains(self.magazine) end
function ISLoadBulletsInMagazine:run() local inv, m = self.character:getInventory(), self.magazine
    local key = self.kind or m:getAmmoType():getItemKey(); local n = 0
    while m.count < m.max and (self.ammoLimit == nil or n < self.ammoLimit) do
        local r = inv:RemoveOneOf(key); if not r then break end; m.count = m.count + 1; n = n + 1
        m:getModData().AmmoList = m:getModData().AmmoList or {}; table.insert(m.md.AmmoList, key) end end
ISInsertMagazine = class("ISInsertMagazine")
function ISInsertMagazine:init(gun, mag) self.gun, self.magazine = gun, mag end
function ISInsertMagazine:isValid() return not self.gun:isContainsClip() and self.character:getInventory():contains(self.magazine) and self.character:getPrimaryHandItem() == self.gun end
function ISInsertMagazine:run() local inv = self.character:getInventory(); inv:Remove(self.magazine)
    self.gun.cur = self.magazine.count; self.gun.clip = true; self.gun.max = self.magazine.max; self.gun.inserted = self.magazine
    if not self.gun.chambered and self.gun.cur >= 1 then ISTimedActionQueue.addAfter(self, ISRackFirearm:new(self.character, self.gun)) end end
ISRackFirearm = class("ISRackFirearm")
function ISRackFirearm:init(gun) self.gun = gun end
function ISRackFirearm:run() local gun = self.gun; gun.chambered = false
    if gun.cur >= 1 then gun.chambered = true; gun.cur = gun.cur - 1 end end
ISEjectMagazine = class("ISEjectMagazine")
function ISEjectMagazine:init(gun) self.gun = gun end
function ISEjectMagazine:run() local gun = self.gun; local m = gun.inserted or Item(gun.magType or "EFZ.G28_Mag10", { mag = true, max = gun.max, key = "EFZ.Ammo_762x51_M80" })
    m.count = gun.cur; gun.cur = 0; gun.clip = false; gun.inserted = nil; self.character:getInventory():AddItem(m) end
ISReloadWeaponAction = { canRack = function(gun) return gun.cur >= 1 or gun.chambered end }
-- zombies
ZOMBIES = {}
function getCell() return { getZombieList = function() return List(ZOMBIES) end } end
function Zombie(x, y) return { getX = function() return x end, getY = function() return y end, getZ = function() return 0 end, isDead = function() return false end } end
-- Sol
INV = Cont({})
SOL = { p = nil, s = nil, x = 100, y = 100 }
function SOL:getInventory() return INV end
function SOL:getPrimaryHandItem() return self.p end
function SOL:getSecondaryHandItem() return self.s end
function SOL:setPrimaryHandItem(i) self.p = i end
function SOL:getX() return self.x end
function SOL:getY() return self.y end
function SOL:getZ() return 0 end
function SOL:getVehicle() return nil end
function SOL:isDead() return false end
function SOL:resetModelNextFrame() end
-- LF utility
SurvivorCompanion = {}
SC = SurvivorCompanion
U = {}
function U.call(o, m, ...) if o == nil then return nil, false end; local f = o[m]; if f == nil then return nil, false end; return f(o, ...), true end
function U.each(list, limit, fn) local n = list:size(); for i = 0, math.min(n, limit) - 1 do fn(list:get(i)) end end
function U.config(k) return nil end
function U.nowMs() return NOW end
function U.listSize(l) return l and l:size() or 0 end
function U.itemType(it) return it and it.t end
function U.instanceOf(it, cls) return (cls == "HandWeapon" or cls == "zombie.inventory.types.HandWeapon") and type(it) == "table" and it.weapon == true end
function U.hasMethod(o, m) return type(o) == "table" and o[m] ~= nil end
function U.clamp(v, a, b) return math.max(a, math.min(b, v)) end
function U.inventory(a) return a:getInventory() end
function U.idOf(a) return "sol-1" end
function U.isValidActor(a) return true end
function U.say(a, t) SAID[#SAID + 1] = t end
setmetatable(U, { __call = function(self) return self end })
SC.GameplayUtil = U
Combat = {}
SC.Combat = Combat
function actionSupervisor() return nil end
function weaponKey(item) return "weapon:" .. tostring(item.t) end
EQUIPS = 0
function equipWeapon(actor, item, options) EQUIPS = EQUIPS + 1; actor.p = item; if item.two then actor.s = item end; return true, "equipped" end
"""

def fresh():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV)
    L.execute("\n".join(GPARTS))
    L.execute(IX)
    L.execute(FB); L.execute(WP); L.execute(MF)
    L.execute("\n".join(PARTS) + "\nREC = weaponRecord\nINVW = inventoryWeapons\nRELOAD = hasReloadAmmo\nUSABLE = weaponUsableNow\nCHOOSE = chooseWeapon\n")
    L.execute("""
WRENCH = Item('Base.Wrench', { weapon = true, dmg = 1.0, swing = 4, cat = 'SMALL_BLUNT', dcat = 'ToolWeapon', cond = 9 })
KATANA = Item('Base.Katana', { weapon = true, dmg = 8.0, swing = 3, cat = 'LONG_BLADE', two = true, range = 1.4 })
AXE = Item('Base.Axe', { weapon = true, dmg = 3.0, swing = 3, cat = 'AXE', two = true })
G28 = Item('EFZ.G28', { weapon = true, ranged = true, two = true, dmg = 3, range = 20, magType = 'EFZ.G28_Mag10', cur = 0, max = 10 })
MAG10 = Item('EFZ.G28_Mag10', { mag = true, max = 10, count = 0, key = 'EFZ.Ammo_762x51_M80' })
MAG20 = Item('EFZ.G28_Mag20', { mag = true, max = 20, count = 5, key = 'EFZ.Ammo_762x51_M80' })
INV.items = {}
for i = 1, 500 do INV.items[#INV.items + 1] = Item('EFZ.Ammo_762x51_M80') end
INV:AddItem(WRENCH); INV:AddItem(KATANA); INV:AddItem(G28)
BAG = Item('Base.Bag_ALICEpack', { inv = Cont({ MAG10, MAG20 }) })
INV:AddItem(BAG)
SOL.p = WRENCH
""")
    return L
def logs(L): s = L.eval("LOGS"); return [s[i] for i in range(1, len(s) + 1)]
def said(L): s = L.eval("SAID"); return [s[i] for i in range(1, len(s) + 1)]
def ran(L): s = L.eval("RAN"); return [s[i] for i in range(1, len(s) + 1)]
AR_FILL = "عم عبّي مخزن الـ"

# ---- the live root cause, with LF's own walk (switches off)
L = fresh()
L.execute("SW.weapon_scan = false; SW.melee_choice = false; SW.mag_fill = false")
ck("LIVE: LF's capped walk sees only the wrench (carried=1)", L.eval("#(INVW(SOL))") == 1 and L.eval("(INVW(SOL))[1].item == WRENCH"), L.eval("#(INVW(SOL))"))
ck("LIVE: LF picks the wrench", L.eval("(CHOOSE(SOL, 'best', 1, 1)).item == WRENCH"))
L.execute("OK1, WHY1 = Combat.equipExactWeapon(SOL, G28)")
ck("LIVE: carry order on the G28 refused no_usable_weapon (empty)", L.eval("OK1 == false and WHY1 == 'no_usable_weapon'") and any("(empty)" in x for x in logs(L)), logs(L))

# ---- weapon_scan alone: all three weapons, but s98 still keeps the held wrench
L = fresh()
L.execute("SW.melee_choice = false; SW.mag_fill = false")
ck("weapon_scan: wrench, katana, G28 listed", L.eval("#(INVW(SOL))") == 3)
ck("weapon_scan: LF's miss is logged with the root count", any("missed 2 weapon(s)" in x and "504 items" in x for x in logs(L)), logs(L)[-3:])
ck("weapon_scan without melee_choice: s98 keeps the held wrench (the second cause)", L.eval("(CHOOSE(SOL, 'best', 1, 1)).item == WRENCH"))

# ---- melee_choice
L = fresh()
L.execute("SW.mag_fill = false")
ck("melee_choice: katana over the held wrench", L.eval("(CHOOSE(SOL, 'best', 1, 1)).item == KATANA"))
L.execute("KATANA.cond = 0")
ck("melee_choice: broken katana -> next melee (the wrench, nothing else)", L.eval("(CHOOSE(SOL, 'best', 1, 1)).item == WRENCH"))
L.execute("KATANA.cond = 10; INV:AddItem(AXE)")
ck("melee_choice: katana (default preferred) over an axe", L.eval("(CHOOSE(SOL, 'best', 1, 1)).item == KATANA"))
L.execute("SW.melee_choice = true; SolWeaponPick.cache = setmetatable({}, { __mode = 'k' })")
L.execute("OKA = Combat.equipExactWeapon(SOL, AXE)")
ck("his carry order on the axe marks her melee weapon", L.eval("OKA == true and AXE.md.SolMeleeFor == 'sol-1'"))
L.execute("SOL.p = WRENCH; SolWeaponPick.cache = setmetatable({}, { __mode = 'k' }); AXE.md.SC_ManualEquipFor = nil")
ck("melee_choice: his axe over the katana", L.eval("(CHOOSE(SOL, 'best', 1, 1)).item == AXE"))
L.execute("NOW = NOW + 2000; SolWeaponPick.cache = setmetatable({}, { __mode = 'k' })")
ck("melee score: tool penalty, damage x condition", L.eval("SolWeaponPick.meleeScore(SOL, REC(WRENCH), 0) < SolWeaponPick.meleeScore(SOL, REC(KATANA), 0) - 60"))

# ---- EFZ ammo counting (mag_fill)
L = fresh()
L.execute("G28.clip = true; G28.cur = 0; G28.chambered = true")
ck("EFZ: chambered round counts (ammo 1)", L.eval("REC(G28).ammo") == 1)
L.execute("SW.mag_fill = false")
ck("switch off: old count (ammo 0)", L.eval("REC(G28).ammo") == 0)
L.execute("SW.mag_fill = true; G28.chambered = false; MAG20.count = 12")
ck("loaded compatible magazine in the bag past LF's walk: reload ready", L.eval("RELOAD(INV, REC(G28))") is True)
L.execute("SW.mag_fill = false; NOW = NOW + 1000")
ck("switch off: LF does not find it (old)", L.eval("RELOAD(INV, REC(G28))") is False)
L.execute("SW.mag_fill = true; MAG20.count = 0; NOW = NOW + 1000")
ck("only loose rounds: not a reload in a fight", L.eval("RELOAD(INV, REC(G28))") is False)

# ---- his order + the fill, insert and rack (live: no loaded magazine at all)
L = fresh()
L.execute("MAG20.count = 0")
L.execute("OK1, WHY1 = Combat.equipExactWeapon(SOL, G28)")
ck("order on the G28 accepted (she can fill a magazine)", L.eval("OK1 == true and SOL.p == G28"), (L.eval("OK1"), L.eval("WHY1")))
ck("a fill request is pending", L.eval("SolMagFill.pending[SOL] ~= nil and SolMagFill.pending[SOL].item == G28"))
L.execute("ZOMBIES = { Zombie(104, 100) }")
ck("zombie at 4 tiles: nothing starts", L.eval("SolMagFill.poll(SOL)") == "zombie_within_6" and L.eval("#ISTimedActionQueue.getTimedActionQueue(SOL).queue") == 0)
L.execute("ZOMBIES = { Zombie(105.5, 100) }")
ck("zombie at 5.5 tiles: still nothing", L.eval("SolMagFill.poll(SOL)") == "zombie_within_6")
L.execute("ZOMBIES = { Zombie(110, 100) }")
k = L.eval("SolMagFill.poll(SOL)")
ck("zombie at 10 tiles: fill + insert queued on her queue", k == "fill_insert" and L.eval("#ISTimedActionQueue.getTimedActionQueue(SOL).queue") == 2, k)
s = said(L)
ck("she says it in Arabic: 'fill the G28 magazine'", len(s) == 1 and s[0].encode("utf-8") == (AR_FILL + "G28").encode("utf-8"), s)
ck("first magazine of the profile filled (10)", L.eval("ISTimedActionQueue.getTimedActionQueue(SOL).queue[1].magazine == MAG10"))
L.execute("DRAIN(SOL)")
ck("ran: load bullets, insert, rack", ran(L) == ["ISLoadBulletsInMagazine", "ISInsertMagazine", "ISRackFirearm"], ran(L))
ck("G28: magazine in, round chambered, 9 + 1", L.eval("G28.clip == true and G28.chambered == true and G28.cur == 9"))
ck("rounds used: 10 of 500, matching kind", L.eval("INV:getCountTypeRecurse('EFZ.Ammo_762x51_M80')") == 490)
ck("the magazine was taken out of the bag first (transfer)", L.eval("TRANSFERS") >= 1)
L.execute("NOW = NOW + 1000")
ck("G28 now usable for LF (ammo 10)", L.eval("REC(G28).ammo") == 10 and L.eval("USABLE(INV, REC(G28))") is True)
k = L.eval("SolMagFill.poll(SOL)")
ck("idle again: fills the empty spare 20", k == "fill")
L.execute("DRAIN(SOL)")
ck("spare filled 20/20", L.eval("MAG20.count") == 20 and L.eval("INV:getCountTypeRecurse('EFZ.Ammo_762x51_M80')") == 470)

# ---- partial magazines: the fullest one she can fill is topped up first, then inserted
L = fresh()
L.execute("SOL.p = G28")
ck("partial 20 (5 in it) chosen first", L.eval("SolMagFill.poll(SOL)") == "fill_insert" and L.eval("ISTimedActionQueue.getTimedActionQueue(SOL).queue[1].magazine == MAG20"))
L.execute("DRAIN(SOL)")
ck("topped up with 15 rounds, inserted, racked (19 + 1)", L.eval("INV:getCountTypeRecurse('EFZ.Ammo_762x51_M80')") == 485 and L.eval("G28.cur == 19 and G28.chambered"))
ck("then the empty spare 10 is filled", L.eval("SolMagFill.poll(SOL)") == "fill")
L.execute("DRAIN(SOL)")
ck("nothing more to do", L.eval("SolMagFill.poll(SOL)") is None)
ck("no second speech within a minute", len(said(L)) == 1, said(L))

# ---- empty gun in her hands, empty magazine inside, only that magazine: eject, fill, insert, rack
L = fresh()
L.execute("INV:Remove(BAG); SOL.p = G28; G28.clip = true; G28.cur = 0; G28.inserted = Item('EFZ.G28_Mag10', { mag = true, max = 10, count = 0, key = 'EFZ.Ammo_762x51_M80' })")
ck("empty mag inside: eject first", L.eval("SolMagFill.poll(SOL)") == "eject")
L.execute("DRAIN(SOL)")
ck("then fill + insert", L.eval("SolMagFill.poll(SOL)") == "fill_insert")
L.execute("DRAIN(SOL)")
ck("loaded 9 + chambered", L.eval("G28.clip and G28.chambered and G28.cur == 9"))

# ---- caliber match
L = fresh()
L.execute("MAG20.count = 0; for i = #INV.items, 1, -1 do if INV.items[i].t == 'EFZ.Ammo_762x51_M80' then table.remove(INV.items, i) end end")
L.execute("for i = 1, 60 do INV:AddItem(Item('EFZ.Ammo_556_M855')) end; SOL.p = G28")
ck("only 5.56 rounds: no fill for the G28", L.eval("SolMagFill.poll(SOL)") is None and L.eval("#ISTimedActionQueue.getTimedActionQueue(SOL).queue") == 0)
L.execute("for i = 1, 3 do INV:AddItem(Item('EFZ.Ammo_762x51_M61')) end")
ck("another 7.62x51 kind of the family is used", L.eval("SolMagFill.poll(SOL)") == "fill_insert" and L.eval("ISTimedActionQueue.getTimedActionQueue(SOL).queue[1].kind") == "EFZ.Ammo_762x51_M61")
L.execute("DRAIN(SOL)")
ck("5.56 untouched", L.eval("INV:getCountTypeRecurse('EFZ.Ammo_556_M855')") == 60)
L.execute("M4MAG = Item('EFZ.M4_Mag30', { mag = true, max = 30, count = 0, key = 'EFZ.Ammo_556_M855' }); INV:AddItem(M4MAG)")
ck("an M4 magazine is never a G28 magazine", L.eval("(function() for _, m in ipairs(SolMagFill.magazines(INV, G28)) do if m.item == M4MAG then return false end end return true end)()") is True)

# ---- a zombie comes close during the fill: her action stops
L = fresh()
L.execute("SOL.p = G28")
ck("fill started", L.eval("SolMagFill.poll(SOL)") == "fill_insert")
L.execute("FIRST = ISTimedActionQueue.getTimedActionQueue(SOL).queue[1]; OTHER = { character = SOL, Type = 'Other' }; ISTimedActionQueue.add(OTHER); ZOMBIES = { Zombie(103, 101) }")
ck("zombie at ~3 tiles: aborted", L.eval("SolMagFill.poll(SOL)") == "aborted")
ck("her fill and insert are gone, the other action stays", L.eval("FIRST.stopped == true and #ISTimedActionQueue.getTimedActionQueue(SOL).queue == 1 and ISTimedActionQueue.getTimedActionQueue(SOL).queue[1] == OTHER"))

# ---- busy: never on top of another action
L = fresh()
L.execute("SOL.p = G28; ISTimedActionQueue.add({ character = SOL, Type = 'Walk' })")
ck("not idle: waits", L.eval("SolMagFill.poll(SOL)") == "busy")

# ---- SolCombatEquipFallback: an empty refusal asks for a fill
L = fresh()
L.execute("SW.mag_fill = true; SolCombatEquipFallback.pickFailed(SOL, G28, 'no_usable_weapon', REC(G28))")
ck("empty refusal -> fill request", L.eval("SolMagFill.pending[SOL] ~= nil and SolMagFill.pending[SOL].why == 'empty_refusal'"))
L = fresh()
L.execute("G28:getModData().SC_ManualEquipFor = 'sol-1'; MAG20.count = 0; MAG10.count = 0")
L.execute("W1 = CHOOSE(SOL, 'best', 12, 0)")
ck("preferred empty G28 in a fight: fallback weapon (katana), fill requested for later", L.eval("W1.item == KATANA and SolMagFill.pending[SOL] ~= nil"))

# ---- switch off
L = fresh()
L.execute("SW.mag_fill = false; SOL.p = G28")
ck("off: poll does nothing", L.eval("SolMagFill.poll(SOL)") is None and L.eval("#ISTimedActionQueue.getTimedActionQueue(SOL).queue") == 0)
ck("off: orderFill false, reloadReady nil", L.eval("SolMagFill.orderFill(SOL, G28)") is False and L.eval("SolMagFill.reloadReady(INV, G28)") is None)
L.execute("SOL.p = WRENCH; OKX = Combat.equipExactWeapon(SOL, G28)")
ck("off: the carry order is refused as before", L.eval("OKX") is False)

for nm, src in (("SolMagFill.lua", MF), ("SolWeaponPick.lua", WP), ("SolCombatEquipFallback.lua", FB), ("SCCombat.lua", CB)):
    ck("ascii only " + nm, all(ord(c) < 128 for c in src))
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
if os.path.exists(GATE):
    for nm in ("SolMagFill.lua", "SolWeaponPick.lua", "SolCombatEquipFallback.lua", "SCCombat.lua"):
        r = subprocess.run([sys.executable, GATE, os.path.join(cl, nm)], capture_output=True, text=True)
        ck("tonumber gate " + nm, r.returncode == 0, r.stdout[-300:])
else:
    ck("tonumber gate present", False, GATE)
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
