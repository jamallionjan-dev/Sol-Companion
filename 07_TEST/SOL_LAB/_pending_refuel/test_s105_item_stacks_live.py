"""s105 item_stacks live fix, offline against the REAL LF files.
Loaded whole, unchanged, from a copy of the lab mod (after apply_s105_item_stacks_live.py on the copy):
  shared/SCCall.lua, shared/SCNativeList.lua, shared/SCConfig.lua, client/SolAuthority.lua, client/SCGameplayUtil.lua,
  client/SCInventoryIndex.lua, client/SolItemStacks.lua, client/SolWeaponPick.lua
and cut from client/SCCombat.lua: boolCall, numberCall, weaponRecord, inventoryWeapons (the chain W.missing sees).
Only the Java side is faked, after projectzomboid.jar 42.22 (javap):
  * Item.InstanceItem: ItemType=normal -> ComboItem (extends InventoryItem), copies the script Count (setCount):
    Base.308Bullets / Base.556Bullets have Count = 5, so a loose round answers getCount() == 5.
  * getCategory: InventoryItem "Item" (mainCategory null), HandWeapon "Weapon", InventoryContainer "Container",
    Food "Food", Clothing "Clothing". getMaxAmmo 0 unless the script has MaxAmmo (M14Clip 20).
  * hasModData: table ~= null and not empty; getModData allocates an empty table.
  * instanceof (LuaManager.GlobalObject.instof): exposed simple name -> Class.isInstance (ComboItem is exposed).
  * getItemContainer only on InventoryContainer; getFluidContainer (GameEntity) nil for these items.
  * ItemContainer.getAllCategoryRecurse(String, ArrayList), getCountTypeRecurse(String), getItems() ArrayList.
Fixture = the 13:29:28 live state: root holds 782 items, 500 + 240 loose rounds before the G28, garden hoe and pencil.
Run: python test_s105_item_stacks_live.py [client dir]. Offline PASS is not Runtime PASS."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
CL = os.path.abspath(CL)
SH = os.path.join(os.path.dirname(CL), "shared")
CFILES = ("SCGameplayUtil.lua", "SCInventoryIndex.lua", "SCCombat.lua", "SolAuthority.lua", "SolItemStacks.lua", "SolWeaponPick.lua")
SFILES = ("SCCall.lua", "SCNativeList.lua", "SCConfig.lua")
tmp = tempfile.mkdtemp(prefix="s105_")
cl = os.path.join(tmp, "lua", "client"); sh = os.path.join(tmp, "lua", "shared"); os.makedirs(cl); os.makedirs(sh)
for f in CFILES: shutil.copy(os.path.join(CL, f), cl)
for f in SFILES: shutil.copy(os.path.join(SH, f), sh)
rd = lambda p: open(p, encoding="utf-8", newline="").read()
LAB_ST = rd(os.path.join(cl, "SolItemStacks.lua"))
ck("lab copy has s100 installed (SolItemStacks present)", "S.VERSION = " in LAB_ST)
def from_git(version):
    """the staged SolItemStacks.lua as it was at the given version, from the repo history (None without git)"""
    rel = "07_TEST/SOL_LAB/_pending_refuel/SolItemStacks.lua"
    root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    try:
        revs = subprocess.run(["git", "-C", root, "log", "--format=%H", "--", rel], capture_output=True, text=True).stdout.split()
        for h in revs:
            src = subprocess.run(["git", "-C", root, "show", h + ":" + rel], capture_output=True, text=True, encoding="utf-8").stdout
            if 'S.VERSION = "%s"' % version in src: return src
    except Exception: pass
    return None
OLD_ST = from_git("0.1.0")
V020_ST = from_git("0.2.0")
ck("history: 0.1.0 and 0.2.0 of SolItemStacks.lua found in git", OLD_ST is not None and V020_ST is not None)

def run(*a):
    return subprocess.run([sys.executable, os.path.join(HERE, "apply_s105_item_stacks_live.py")] + list(a), capture_output=True, text=True)
before = {f: rd(os.path.join(cl, f)) for f in CFILES if f != "SolItemStacks.lua"}
r = run(cl)
ck("s105 installer runs", r.returncode == 0 and "s105 item_stacks_live applied" in r.stdout, r.stdout + r.stderr)
snap = rd(os.path.join(cl, "SolItemStacks.lua"))
r2 = run(cl)
ck("s105 installer second run changes nothing", r2.returncode == 0 and "kept SolItemStacks.lua" in r2.stdout and rd(os.path.join(cl, "SolItemStacks.lua")) == snap, r2.stdout)
ck("s105 touches no LF file", all(rd(os.path.join(cl, f)) == before[f] for f in before))
nos = os.path.join(tmp, "nos100"); os.makedirs(nos)
for f in ("SCGameplayUtil.lua", "SCInventoryIndex.lua", "SolAuthority.lua"):
    open(os.path.join(nos, f), "w").write("-- no s100\n")
r3 = run(nos)
ck("s105 installer refuses a client dir without s100", r3.returncode != 0 and not os.path.exists(os.path.join(nos, "SolItemStacks.lua")))
NEW_ST = rd(os.path.join(cl, "SolItemStacks.lua"))
ck("installed copy is 0.3.0", 'S.VERSION = "0.3.0"' in NEW_ST)

CB = rd(os.path.join(cl, "SCCombat.lua")).replace("\r\n", "\n")
def cut(src, start, end, nm):
    i = src.find(start); j = src.find(end, i)
    ck("cut " + nm, i >= 0 and j > i)
    return src[i:j + len(end)]
COMBAT = "\n".join([
    "local SC = SurvivorCompanion",
    "local function U() return SC.GameplayUtil end",
    cut(CB, "local function boolCall(", "\nend\n", "SCCombat.boolCall"),
    cut(CB, "local function numberCall(", "\nend\n", "SCCombat.numberCall"),
    cut(CB, "local function weaponRecord(", "\n    }\nend\n", "SCCombat.weaponRecord"),
    cut(CB, "local function inventoryWeapons(", "\n    return result, inventory, entry\nend\n", "SCCombat.inventoryWeapons"),
    "INVW = inventoryWeapons"])

JAVA = r"""
NOW = 100000
function require(name) return nil end   -- the files are loaded below, in the game's order
SurvivorCompanion = {}
SC = SurvivorCompanion
function getTimestampMs() return NOW end
LOGS = {}
function print(...) local p = {}; for i = 1, select("#", ...) do p[#p + 1] = tostring((select(i, ...))) end; LOGS[#LOGS + 1] = table.concat(p, " ") end
SolLab = { active = true }
FIXES = { "item_stacks=on", "weapon_scan=on", "melee_choice=off" }
-- java.io.BufferedReader from getFileReader(name, false)
function getFileReader(name, create)
    if name ~= "SolFixes_LAB.txt" then return nil end
    local i = 0
    return { readLine = function(self) i = i + 1; return FIXES[i] end, close = function(self) end }
end
-- java.util.ArrayList
local AL = {}
AL.__index = AL
function AL:size() return #self.t end
function AL:get(i) return self.t[i + 1] end
function AL:add(x) self.t[#self.t + 1] = x; return true end
ArrayList = { new = function() return setmetatable({ t = {} }, AL) end }
local function jlist(t) return setmetatable({ t = t }, AL) end
-- class hierarchy (javap): simple name -> parent
PARENT = { InventoryItem = "GameEntity", ComboItem = "InventoryItem", HandWeapon = "InventoryItem",
           InventoryContainer = "InventoryItem", Food = "InventoryItem", Clothing = "InventoryItem",
           DrainableComboItem = "InventoryItem" }
EXPOSED = { InventoryItem = true, ComboItem = true, HandWeapon = true, InventoryContainer = true, Food = true,
            Clothing = true, DrainableComboItem = true, Key = true, Radio = true, Literature = true, MapItem = true,
            AnimalInventoryItem = true, Moveable = true, ItemContainer = true }
-- LuaManager.GlobalObject.getClassSimpleName (global): o.getClass().getSimpleName()
function getClassSimpleName(o) return type(o) == "table" and rawget(o, "_cls") or "?" end
function instanceof(o, name)
    if o == nil then return false end
    if not EXPOSED[name] then return false end
    local c = type(o) == "table" and rawget(o, "_cls") or nil
    while c ~= nil do if c == name then return true end; c = PARENT[c] end
    return false
end
CALLS = 0
local function m(f) return function(...) CALLS = CALLS + 1; return f(...) end end
-- InventoryItem (and GameEntity) public methods used here
local II = {}
II.getFullType = m(function(self) return self._ft end)
II.getType = m(function(self) return string.match(self._ft, "%.([%w_]+)$") end)
II.getDisplayName = m(function(self) return self._ft end)
II.getCategory = m(function(self) return "Item" end)                -- mainCategory is null for these
II.getDisplayCategory = m(function(self) return self._dcat or "Item" end)
II.hasModData = m(function(self) if self._md == nil then return false end; for _ in pairs(self._md) do return true end; return false end)
II.getModData = m(function(self) if self._md == nil then self._md = {} end; return self._md end)
II.getCount = m(function(self) return self._count end)
II.getMaxAmmo = m(function(self) return self._maxAmmo or 0 end)
II.getCurrentAmmoCount = m(function(self) return self._cur or 0 end)
II.getFluidContainer = m(function(self) return nil end)
II.getCondition = m(function(self) return 10 end)
II.getConditionMax = m(function(self) return 10 end)
II.getWeight = m(function(self) return 0.04 end)
II.getActualWeight = m(function(self) return 0.04 end)
local CLS = {}
local function class(name, parent, extra)
    local t = {}
    for k, v in pairs(CLS[parent] or {}) do t[k] = v end
    for k, v in pairs(extra or {}) do t[k] = v end
    CLS[name] = t
end
CLS.InventoryItem = II
class("ComboItem", "InventoryItem")
class("Food", "InventoryItem", { getCategory = m(function() return "Food" end), getAge = m(function(s) return s._age or 0 end) })
class("Clothing", "InventoryItem", { getCategory = m(function() return "Clothing" end) })
class("DrainableComboItem", "InventoryItem", { getCurrentUsesFloat = m(function(s) return s._uses end) })
class("HandWeapon", "InventoryItem", {
    getCategory = m(function() return "Weapon" end),
    getMaxDamage = m(function(s) return s._dmg or 1 end), isRanged = m(function(s) return s._ranged == true end),
    isJammed = m(function() return false end), getMaxRange = m(function(s) return s._range or 1.2 end),
    getMinRange = m(function() return 0 end), getSwingTime = m(function() return 2 end),
    getEnduranceMod = m(function() return 1 end), getSharpness = m(function() return 1 end),
    isTwoHandWeapon = m(function(s) return s._two == true end), getMagazineType = m(function(s) return s._magType end),
    getAmmoType = m(function(s) return s._ammoType end), getMaxAmmo = m(function(s) return s._maxAmmo or 0 end) })
class("InventoryContainer", "InventoryItem", {
    getCategory = m(function() return "Container" end),
    getItemContainer = m(function(s) return s._inv end), getInventory = m(function(s) return s._inv end) })
function Java(cls, ft, o)
    o = o or {}; o._cls = cls; o._ft = ft; o._count = o._count or 1
    return setmetatable(o, { __index = CLS[cls] })
end
-- zombie.inventory.ItemContainer
local IC = {}
IC.__index = IC
CCALLS = 0   -- calls on containers / lists (not item calls)
function IC:getItems() CCALLS = CCALLS + 1; return jlist(self.items) end
-- javap: sum of getUnequippedWeight over the root list, Java side (no Lua item call)
function IC:getContentsWeight() CCALLS = CCALLS + 1; local w = 0; for _, it in ipairs(self.items) do w = w + (rawget(it, "_w") or 0.1) end; return w end
local function walk(c, fn) for _, it in ipairs(c.items) do fn(it); local n = rawget(it, "_inv"); if n then walk(n, fn) end end end
function IC:getCountTypeRecurse(t) local n = 0; walk(self, function(it) if it._ft == t then n = n + 1 end end); return n end
function IC:getAllCategoryRecurse(cat, list) walk(self, function(it) if it:getCategory() == cat then list:add(it) end end); return list end
function Container(items) return setmetatable({ items = items or {} }, IC) end
-- IsoGameCharacter (only what this path reads)
INV = Container({})
SOL = { getInventory = function(self) return INV end, getPrimaryHandItem = function(self) return PRIMARY end,
        getSecondaryHandItem = function(self) return nil end }
"""
FIXTURE = r"""
INV.items = {}
local function add(x) INV.items[#INV.items + 1] = x; return x end
-- in front of the rounds: a knife and a few plain items
KNIFE = add(Java("HandWeapon", "Base.HuntingKnife", { _dmg = 2 }))
for i = 1, 6 do add(Java("ComboItem", "Base.Nails", { _count = 5, _dcat = "Material" })) end
-- 500 loose 7.62x51 (Base.308Bullets) and 240 loose 5.56x45 (Base.556Bullets): ComboItem, Count = 5, category "Item"
for i = 1, 500 do add(Java("ComboItem", "Base.308Bullets", { _count = 5, _dcat = "Ammo", _w = 0.04 })) end
for i = 1, 240 do add(Java("ComboItem", "Base.556Bullets", { _count = 5, _dcat = "Ammo", _w = 0.035 })) end
-- after them, what the live log said LF missed
G28 = add(Java("HandWeapon", "EscapeFromZomboidFirearms.G28", { _ranged = true, _two = true, _dmg = 3, _range = 20, _maxAmmo = 20,
    _ammoType = "Base.308Bullets", _magType = "Base.M14Clip" }))
HOE = add(Java("HandWeapon", "Base.GardenHoe", { _dmg = 1.2, _two = true }))
PENCIL = add(Java("HandWeapon", "Base.Pencil", { _dmg = 0.1 }))
MAG1 = add(Java("ComboItem", "Base.M14Clip", { _maxAmmo = 20, _cur = 0 }))
MAG2 = add(Java("ComboItem", "Base.M14Clip", { _maxAmmo = 20, _cur = 12 }))
BEANS1 = add(Java("Food", "Base.TinnedBeans", { _age = 1 })); BEANS2 = add(Java("Food", "Base.TinnedBeans", { _age = 9 }))
TAPE1 = add(Java("DrainableComboItem", "Base.DuctTape", { _uses = 1 })); TAPE2 = add(Java("DrainableComboItem", "Base.DuctTape", { _uses = 0.3 }))
SHIRT1 = add(Java("Clothing", "Base.Tshirt_DefaultTEXTURE")); SHIRT2 = add(Java("Clothing", "Base.Tshirt_DefaultTEXTURE"))
BAND1 = add(Java("ComboItem", "Base.Bandage")); BAND2 = add(Java("ComboItem", "Base.Bandage", { _md = { SC_GivenByPlayer = true } }))
PILLS5 = add(Java("ComboItem", "Base.PillsBeta")); PILLS6 = add(Java("ComboItem", "Base.PillsBeta"))
BAG = add(Java("InventoryContainer", "Base.Bag_ALICEpack", { _inv = Container({ Java("HandWeapon", "Base.Katana", { _dmg = 8, _two = true }),
    Java("ComboItem", "Base.Pills") }) }))
local misc = 1
while #INV.items < 782 do add(Java("ComboItem", "Base.Misc" .. misc)); misc = misc + 1 end
"""
def fresh(st, switch_on=True, primary=None):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(JAVA)
    if not switch_on: L.execute('FIXES[1] = "item_stacks=off"')
    for f in SFILES: L.execute(rd(os.path.join(sh, f)))
    L.execute(rd(os.path.join(cl, "SolAuthority.lua")))
    L.execute(rd(os.path.join(cl, "SCGameplayUtil.lua")))
    L.execute(rd(os.path.join(cl, "SCInventoryIndex.lua")))
    L.execute(st)
    L.execute(rd(os.path.join(cl, "SolWeaponPick.lua")))
    L.execute(COMBAT)
    L.execute(FIXTURE)
    if primary: L.execute("PRIMARY = " + primary)
    return L
WEAPONS = """(function()
  local w = INVW(SOL); local s = {}
  for _, r in ipairs(w) do s[r.item:getFullType()] = (s[r.item:getFullType()] or 0) + 1 end
  return s end)()"""
def missed_line(L):
    return [l for l in L.eval("LOGS").values() if "[SolWeaponPick]" in l and "missed" in l]
def stack_lines(L):
    return [l for l in L.eval("LOGS").values() if l.startswith("[SolItemStacks]")]

ck("fixture: root holds 782 items (live 13:29:28)", fresh(NEW_ST).eval("#INV.items") == 782)
ck("fake ComboItem facts: instanceof ComboItem/InventoryItem, category Item, count 5, no modData",
   fresh(NEW_ST).eval("instanceof(INV.items[10], 'ComboItem') and instanceof(INV.items[10], 'InventoryItem') and not instanceof(INV.items[10], 'HandWeapon')"
                      " and INV.items[10]:getCategory() == 'Item' and INV.items[10]:getCount() == 5 and INV.items[10]:hasModData() == false") is True)

# ---- 1. 0.1.0 (installed): reproduces the live line
L = fresh(OLD_ST)
ck("0.1.0: SolAuthority.on('item_stacks') true, S.enabled() true", L.eval("SolAuthority.on('item_stacks') == true and SolItemStacks.enabled() == true") is True)
ck("0.1.0: S.key(round) is nil (ComboItem on the stateful list, count 5)", L.eval("SolItemStacks.key(INV.items[10]) == nil") is True)
L.execute("E0 = SC.InventoryIndex.get(SOL); _, _, I0 = SC.GameplayUtil.inventoryItemsDeep(INV, 240)")
ck("0.1.0: hook taken (third return value) but nothing grouped: distinct == 180 root + 2 in the bag", L.eval("I0 ~= nil and I0.distinct") == 182 and L.eval("I0.byType['Base.308Bullets']") is None, L.eval("I0 and I0.distinct"))
w0 = L.eval(WEAPONS)
ml = missed_line(L)
ck("0.1.0: reproduces the live log: LF's walk misses G28, garden hoe and pencil", len(ml) == 1 and "EscapeFromZomboidFirearms.G28" in ml[0] and "Base.GardenHoe" in ml[0] and "Base.Pencil" in ml[0] and "782 items" in ml[0], ml)
ck("0.1.0: SolItemStacks logs nothing", stack_lines(L) == [])
print("  0.1.0 live repro:", ml[0] if ml else None)

# ---- 2. 0.2.0: grouped
L = fresh(NEW_ST)
ck("0.2.0: S.key(round) = 'Base.308Bullets' (ComboItem with Count 5 is stackable)", L.eval("(SolItemStacks.key(INV.items[10]))") == "Base.308Bullets")
L.execute("E = SC.InventoryIndex.get(SOL)")
sl = stack_lines(L)
ck("0.2.0: logs '[SolItemStacks] grouped N items into M entries' once", len(sl) == 1 and sl[0].startswith("[SolItemStacks] grouped ") and sl[0].endswith(" entries"), sl)
print("  " + (sl[0] if sl else "no line"))
L.execute("_, _, I = SC.GameplayUtil.inventoryItemsDeep(INV, 240)")
ck("0.2.0: still one line after more walks", len(stack_lines(L)) == 1)
ck("0.2.0: rounds are two stacks (500 + 240)", L.eval("I.byType['Base.308Bullets']") == 500 and L.eval("I.byType['Base.556Bullets']") == 240
   and L.eval("I.count[INV.items[8]]") == 500, (L.eval("I.byType['Base.308Bullets']"), L.eval("I.byType['Base.556Bullets']")))
ck("0.2.0: distinct entries far below the cap", L.eval("I.distinct") < 100, L.eval("I.distinct"))
ck("0.2.0: index: G28, garden hoe, pencil, knife, katana (bag) are LF weapons",
   L.eval("(function() local s = {}; for _, w in ipairs(E.weapons) do s[w] = true end; return s[G28] and s[HOE] and s[PENCIL] and s[KNIFE] and true or false end)()") is True
   and L.eval("#E.weapons") == 5, L.eval("#E.weapons"))
ck("0.2.0: index looseAmmoByType 308Bullets 500, 556Bullets 240", L.eval("E.looseAmmoByType['308Bullets']") == 500 and L.eval("E.looseAmmoByType['556Bullets']") == 240,
   (L.eval("E.looseAmmoByType['308Bullets']"), L.eval("E.looseAmmoByType['556Bullets']")))
ck("0.2.0: index magazines stay two (M14Clip, MaxAmmo 20)", L.eval("#E.magazinesByType['M14Clip']") == 2)
w = L.eval(WEAPONS)
ck("0.2.0: inventoryWeapons lists G28, hoe, pencil from LF's own walk", w["EscapeFromZomboidFirearms.G28"] == 1 and w["Base.GardenHoe"] == 1 and w["Base.Pencil"] == 1 and w["Base.Katana"] == 1, dict(w))
ck("0.2.0: W.missing finds nothing, no 'missed' line", missed_line(L) == [], missed_line(L))
ck("0.2.0: stateful kept apart (beans, tapes, shirts, mags, bandage with modData); plain pills stack",
   L.eval("I.count[BEANS1] == 1 and I.count[BEANS2] == 1 and I.count[TAPE1] == 1 and I.count[TAPE2] == 1 and I.count[SHIRT1] == 1 and I.count[SHIRT2] == 1"
          " and I.count[MAG1] == 1 and I.count[MAG2] == 1 and I.count[BAND1] == 1 and I.count[BAND2] == 1 and I.count[PILLS5] == 2") is True)
ck("0.2.0: getModData() on a round (empty table) does not split the stack",
   L.eval("(function() INV.items[20]:getModData(); SC.InventoryIndex.touch(SOL); local _, _, i = SC.GameplayUtil.inventoryItemsDeep(INV, 240); return i.byType['Base.308Bullets'] end)()") == 500)
ck("0.3.0: a round with its own modData is its own entry, still counted as that type (cache max age passed)",
   L.eval("(function() INV.items[21]:getModData().x = 1; NOW = NOW + SolItemStacks.CACHE_MAX_MS + 1; local _, _, i = SC.GameplayUtil.inventoryItemsDeep(INV, 240); return i.count[INV.items[21]] == 1 and i.byType['Base.308Bullets'] == 500 end)()") is True)
ck("0.2.0: U.inventoryCount(SOL, 'Base.308Bullets') = 500", L.eval("SC.GameplayUtil.inventoryCount(SOL, 'Base.308Bullets')") == 500)
ck("0.2.0: callers that want several still get stack members (list fills to 240)", L.eval("#(SC.GameplayUtil.inventoryItemsDeep(INV, 240))") == 240)



# ---- 2c. the live state 14:54 (0.2.0 merged nothing): rounds that carry modData
def tagged(L, how):
    L.execute("for _, it in ipairs(INV.items) do local ft = rawget(it, '_ft'); if ft == 'Base.308Bullets' or ft == 'Base.556Bullets' then " + how + " end end")
def diag_lines(L): return [l for l in L.eval("LOGS").values() if l.startswith("[SolItemStacks] diag")]
if V020_ST:
    L = fresh(V020_ST); tagged(L, "it._md = { TWLoot = 1 }")
    L.eval(WEAPONS); L.execute("_, _, I = SC.GameplayUtil.inventoryItemsDeep(INV, 240)")
    ck("0.2.0 with tagged rounds: rounds not merged and the live 'missed' line (one hypothesis for 14:54)",
       len(missed_line(L)) == 1 and L.eval("I.byType['Base.308Bullets']") is None, (missed_line(L), stack_lines(L)))
L = fresh(NEW_ST); tagged(L, "it._md = { TWLoot = 1 }")
w = L.eval(WEAPONS)
ck("0.3.0 with identically tagged rounds: grouped, G28/hoe/pencil found, no missed line, no diag",
   any("grouped" in l for l in stack_lines(L)) and missed_line(L) == [] and diag_lines(L) == [] and w["EscapeFromZomboidFirearms.G28"] == 1, stack_lines(L))
L.execute("_, _, I = SC.GameplayUtil.inventoryItemsDeep(INV, 240)")
ck("0.3.0 tagged: one stack of 500 and one of 240", L.eval("I.byType['Base.308Bullets']") == 500 and L.eval("I.count[INV.items[8]]") == 500)
L = fresh(NEW_ST); tagged(L, "it._md = { a = 1, b = { 'x', 2 } }"); L.execute("INV.items[9]._md = { b = { 'x', 2 }, a = 1 }")
L.execute("_, _, I = SC.GameplayUtil.inventoryItemsDeep(INV, 240)")
ck("0.3.0: modData compared by content, not key order or table identity", L.eval("I.count[INV.items[8]]") == 500)
L = fresh(NEW_ST); L.execute("SERIAL = 0"); tagged(L, "SERIAL = SERIAL + 1; it._md = { id = SERIAL }")
L.execute("for _, it in ipairs(INV.items) do if rawget(it, '_ft') == 'Base.Nails' then it._md = { id = tostring(it) } end end")
L.execute("for i, it in ipairs(INV.items) do if rawget(it, '_ft'):find('Misc') then it._md = { id = i } end end")
L.execute("PILLS6._md = { id = 'p' }")
L.execute("_, _, I = SC.GameplayUtil.inventoryItemsDeep(INV, 240); _, _, I2 = SolItemStacks.build(SC.GameplayUtil, INV, 240, 12)")
dl = diag_lines(L)
print("  diag sample (every round with its own modData id):"); [print("    " + l) for l in dl]
ck("diag: logged once when nothing merges: header + 3 root items + repeated types", len(dl) == 7 and "nothing merged" in dl[0]
   and sum("diag root#" in l for l in dl) == 3 and sum("diag repeat#" in l for l in dl) == 3, dl)
ck("diag: no error, each line has class, instanceof, modData, getCount, verdict and reason",
   all("error" not in l for l in dl) and all(x in dl[5] for x in ("Base.308Bullets class=ComboItem", "instanceof=[InventoryItem,ComboItem]", "hasModData=true", "modData=1{id=", "getCount=5", "getMaxAmmo=0", "typeVerdict=true", "-> stackable: key Base.308Bullets{"))
   and "class=HandWeapon" in dl[1] and "-> kept apart: type cached false (first item of the type: instanceof HandWeapon)" in dl[1], dl[1:6])
ck("diag: getModData never called on an item without modData", L.eval("rawget(KNIFE, '_md') == nil and rawget(BEANS1, '_md') == nil") is True)
L = fresh(NEW_ST); L.execute("SC.GameplayUtil.inventoryItemsDeep(INV, 240)")
ck("diag: silent when the walk merges", diag_lines(L) == [])
L = fresh(NEW_ST); L.execute("SC.GameplayUtil.inventoryItemsDeep(Container({ Java('ComboItem', 'Base.Nails'), Java('ComboItem', 'Base.Rope') }), 240)")
ck("diag: silent (and still armed) for a walk with nothing to merge (no type twice)", diag_lines(L) == [] and L.eval("SolItemStacks.loggedDiag") is False)

# ---- 2b. cache per inventory
import time
PERF = """SolUI = { perfAdd = function(n, ms) PERFN = PERFN or {}; PERFN[n] = (PERFN[n] or 0) + 1 end }"""
L = fresh(NEW_ST); L.execute(PERF)
L.execute("CALLS, CCALLS = 0, 0; R1, C1, I1 = SC.GameplayUtil.inventoryItemsDeep(INV, 240); B_CALLS, B_CC = CALLS, CCALLS")
L.execute("CALLS, CCALLS = 0, 0; R2, C2, I2 = SC.GameplayUtil.inventoryItemsDeep(INV, 240); H_CALLS, H_CC = CALLS, CCALLS")
b_calls, b_cc, h_calls, h_cc = L.eval("B_CALLS"), L.eval("B_CC"), L.eval("H_CALLS"), L.eval("H_CC")
print("  deep walk: rebuild %d item calls (+%d container calls); hit %d item calls (+%d container calls)" % (b_calls, b_cc, h_calls, h_cc))
ck("cache: a hit makes 0 item calls", h_calls == 0 and L.eval("SolItemStacks.stats.hits") == 1 and L.eval("SolItemStacks.stats.builds") == 1)
ck("cache: rebuild reported to SolPerf as item_stacks (once)", L.eval("PERFN and PERFN.item_stacks") == 1)
SAME = """(function(a, ca, b, cb) if #a ~= #b or #ca ~= #cb then return false end
  for i = 1, #a do if a[i] ~= b[i] then return false end end
  for i = 1, #ca do if ca[i] ~= cb[i] then return false end end return true end)"""
L.execute("RU, CU, IU = SolItemStacks.build(SC.GameplayUtil, INV, 240, 12)")
ck("cache: hit result == uncached build (same items, same order, same bags, same counts)",
   L.eval(SAME + "(R2, C2, RU, CU)") is True and L.eval("I2.distinct == IU.distinct and I2.byType['Base.308Bullets'] == IU.byType['Base.308Bullets']") is True)
ck("cache: callers get fresh lists (changing one does not touch the cache)",
   L.eval("(function() R2[1] = nil; table.remove(C2); local r, c = SC.GameplayUtil.inventoryItemsDeep(INV, 240); return r[1] == RU[1] and #c == #CU end)()") is True)
def change(desc, lua, check):
    L.execute("BUILDS0 = SolItemStacks.stats.builds")
    L.execute(lua)
    L.execute("RC, CC, IC_ = SC.GameplayUtil.inventoryItemsDeep(INV, 240); RU, CU, IU = SolItemStacks.build(SC.GameplayUtil, INV, 240, 12)")
    ck("cache: " + desc + " rebuilds", L.eval("SolItemStacks.stats.builds == BUILDS0 + 1") is True)
    ck("cache: " + desc + " result == uncached", L.eval(SAME + "(RC, CC, RU, CU)") is True and L.eval(check) is True, L.eval(check))
change("remove a round", "table.remove(INV.items, 30)", "IC_.byType['Base.308Bullets'] == 499")
change("add a round", "table.insert(INV.items, 30, Java('ComboItem', 'Base.308Bullets', { _count = 5, _w = 0.04 }))", "IC_.byType['Base.308Bullets'] == 500")
change("add a weapon", "AXE = Java('HandWeapon', 'Base.Axe', { _dmg = 3, _w = 3 }); INV.items[#INV.items + 1] = AXE", "(function() for _, x in ipairs(RC) do if x == AXE then return true end end return false end)()")
change("remove a weapon", "table.remove(INV.items)", "(function() for _, x in ipairs(RC) do if x == AXE then return false end end return true end)()")
change("add a bag", "BAG2 = Java('InventoryContainer', 'Base.Bag_Schoolbag', { _w = 1, _inv = Container({ Java('ComboItem', 'Base.Lighter') }) }); INV.items[#INV.items + 1] = BAG2", "#CC == 2")
change("put an item into a bag", "BAG2._inv.items[#BAG2._inv.items + 1] = Java('ComboItem', 'Base.Matches')", "(function() for _, x in ipairs(RC) do if x:getFullType() == 'Base.Matches' then return true end end return false end)()")
change("cache max age", "NOW = NOW + SolItemStacks.CACHE_MAX_MS", "true")
L.execute("BUILDS0 = SolItemStacks.stats.builds; SC.GameplayUtil.inventoryItemsDeep(INV, 120)")
ck("cache: another limit is not served from the cache", L.eval("SolItemStacks.stats.builds == BUILDS0 + 1") is True)
# the index (MAX_AGE 250 ms) every 300 ms with an unchanged inventory: walk served from the cache
L = fresh(NEW_ST)
L.execute("CALLS = 0; E = SC.InventoryIndex.get(SOL); INVW(SOL, E); IX_B = CALLS")
L.execute("NOW = NOW + 300; CALLS = 0; E = SC.InventoryIndex.get(SOL); INVW(SOL, E); IX_H = CALLS")
ix_b, ix_h = L.eval("IX_B"), L.eval("IX_H")
print("  LF index rebuild + weapon list: walk rebuilt %d item calls; walk from cache %d item calls (LF classifies %d entries)" % (ix_b, ix_h, L.eval("#E.weapons") and L.eval("#(select(3, SC.GameplayUtil.inventoryItemsDeep(INV, 240))).reps")))
ck("cache: index rebuild with the walk cached costs far less than the old capped walk", ix_h * 3 < ix_b, (ix_b, ix_h))
ck("cache: index from cache still lists the 5 weapons", L.eval("#E.weapons") == 5)
# offline wall time (lupa, not Kahlua: only the ratio means something)
L = fresh(NEW_ST)
t0 = time.perf_counter(); L.execute("SC.GameplayUtil.inventoryItemsDeep(INV, 240)"); tb = (time.perf_counter() - t0) * 1000
t0 = time.perf_counter()
for _ in range(20): L.execute("SC.GameplayUtil.inventoryItemsDeep(INV, 240)")
th = (time.perf_counter() - t0) * 1000 / 20
print("  offline lupa wall time: rebuild %.2f ms, hit %.3f ms" % (tb, th))

# ---- 3. switch off: old walk
L = fresh(NEW_ST, switch_on=False)
ck("off: S.enabled() false, no third return", L.eval("SolItemStacks.enabled()") is False and L.eval("select('#', SC.GameplayUtil.inventoryItemsDeep(INV, 240))") == 2)
L.eval(WEAPONS)
ck("off: old behaviour (G28 missed by LF, weapon_scan reports it)", len(missed_line(L)) == 1)
ck("off: SolItemStacks logs nothing", stack_lines(L) == [])

# ---- 4. scan cost on the live fixture (Java calls on items for one index build + weapon list)
def cost(st, on):
    L = fresh(st, switch_on=on)
    L.execute("CALLS = 0; local e = SC.InventoryIndex.get(SOL); INVW(SOL, e); COSTN = CALLS")   # first build: the walk is not cached yet
    return L.eval("COSTN")
c_off, c_new = cost(NEW_ST, False), cost(NEW_ST, True)
print("  item calls, index build + weapon list on the 782-item root: off=%d on(0.2.0)=%d" % (c_off, c_new))
ck("cost: 0.2.0 reads every root item (782, not 180) but stays within 2x the old capped walk", c_new < 2 * c_off, (c_off, c_new))

for nm, src in (("SolItemStacks.lua", NEW_ST),):
    ck("ascii only " + nm, all(ord(c) < 128 for c in src))
TOOLS = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua")
r = subprocess.run([sys.executable, os.path.join(TOOLS, "tonumber_check.py"), os.path.join(cl, "SolItemStacks.lua")], capture_output=True, text=True)
ck("tonumber gate SolItemStacks.lua", r.returncode == 0, r.stdout[-400:] + r.stderr[-400:])
r = subprocess.run([sys.executable, os.path.join(TOOLS, "jarcall_check.py"), cl], capture_output=True, text=True)
ck("jarcall gate (client copy)", r.returncode == 0, r.stdout[-600:] + r.stderr[-400:])
print("  jarcall: " + " | ".join(l for l in r.stdout.splitlines() if "SolItemStacks" in l or "FAIL" in l or "summary" in l.lower())[:600])
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
