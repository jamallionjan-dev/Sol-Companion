"""s100 item_stacks offline. Code under test is CUT FROM THE PATCHED FILES of a copy of the lab client after
apply_s99_mag_fill.py, apply_s99_perf_slice.py and apply_s100_item_stacks.py (in that order, each run twice):
SCGameplayUtil (inventoryItems, inventoryItemsDeep, inventoryCount), SCInventoryIndex (whole file), SCCombat
(weaponRecord, inventoryWeapons, hasReloadAmmo and helpers), SolInventory.itemRead, SolWorldScan.itemInfo, SolItemStacks.
Every method call on a fake item is counted (CALLS) to compare the scan cost.
Run: python test_s100_item_stacks.py [client dir]. Offline PASS is not Runtime PASS."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
FILES = ("SCCombat.lua", "SCGameplayUtil.lua", "SCInventoryIndex.lua", "SolAuthority.lua", "SolInventory.lua", "SolWorldScan.lua", "SolActions.lua")
tmp = tempfile.mkdtemp(prefix="s100_")
fixdir = os.path.join(tmp, "Lua"); os.makedirs(fixdir)
cl = os.path.join(tmp, "a", "b", "c", "d", "e", "client"); os.makedirs(cl)
for f in FILES: shutil.copy(os.path.join(CL, f), cl)
fixfile = os.path.join(fixdir, "SolFixes_LAB.txt")
open(fixfile, "w", newline="").write("preferred_weapon=on\r\n")

def run(script):
    return subprocess.run([sys.executable, os.path.join(HERE, script), cl], capture_output=True, text=True)
for s in ("apply_s99_mag_fill.py", "apply_s99_perf_slice.py"):
    r = run(s); ck("prior " + s + " runs on the copy", r.returncode == 0, r.stdout + r.stderr)
before = {f: open(os.path.join(cl, f), encoding="utf-8", newline="").read() for f in FILES}
r = run("apply_s100_item_stacks.py")
ck("s100 installer runs after s99 + perf_slice", r.returncode == 0 and "s100 item_stacks applied" in r.stdout, r.stdout + r.stderr)
ck("s100 edits: GU 2, IX 4, SolInventory 2, SolWorldScan 2, SolAuthority, copy",
   all(x in r.stdout for x in ("edited SCGameplayUtil.lua (2)", "edited SCInventoryIndex.lua (4)", "edited SolInventory.lua (2)",
                                "edited SolWorldScan.lua (2)", "edited SolAuthority.lua", "copied SolItemStacks.lua")), r.stdout)
snap = {f: open(os.path.join(cl, f), encoding="utf-8", newline="").read() for f in FILES + ("SolItemStacks.lua",)}
r2 = run("apply_s100_item_stacks.py")
after2 = {f: open(os.path.join(cl, f), encoding="utf-8", newline="").read() for f in FILES + ("SolItemStacks.lua",)}
ck("s100 installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout and "copied" not in r2.stdout and snap == after2, r2.stdout)
r3 = run("apply_s99_mag_fill.py"); r4 = run("apply_s99_perf_slice.py")
ck("s99 + perf_slice re-run after s100 still clean (kept)", r3.returncode == 0 and r4.returncode == 0 and "edited" not in r3.stdout + r4.stdout, r3.stdout + r3.stderr + r4.stdout + r4.stderr)
ck("SolActions untouched by s100", before["SolActions.lua"] == snap["SolActions.lua"])
fx = open(fixfile, encoding="utf-8").read()
ck("SolFixes_LAB.txt: item_stacks=on once", fx.count("item_stacks=on") == 1, fx)
rd = lambda f: open(os.path.join(cl, f), encoding="utf-8", newline="").read().replace("\r\n", "\n")
CB, GU, IX, AU, SI, WS, ST = rd("SCCombat.lua"), rd("SCGameplayUtil.lua"), rd("SCInventoryIndex.lua"), rd("SolAuthority.lua"), rd("SolInventory.lua"), rd("SolWorldScan.lua"), rd("SolItemStacks.lua")
ck("switch registered in A.FIXES", '"item_stacks"' in AU)

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
         cut(CB, "local function hasReloadAmmo(", "\n    return false\nend\n", "hasReloadAmmo")]
GPARTS = [cut(GU, "function U.inventoryItems(", "\nend\n", "U.inventoryItems"),
          cut(GU, "function U.inventoryItemsDeep(", "\n    return result, containers\nend\n", "U.inventoryItemsDeep"),
          cut(GU, "function U.inventoryCount(", "\nend\n", "U.inventoryCount")]
SIP = [cut(SI, "local function method(", "\nend\n", "SolInventory.method"), "local function num(v) return tonumber(v) end",
       cut(SI, "local function is(", "\n", "SolInventory.is"), cut(SI, "local function itemRead(", "\n    return d\nend\n", "SolInventory.itemRead"),
       "INV_READ = itemRead"]
WSP = [cut(WS, "local function call(", "\nend\n", "SolWorldScan.call"), cut(WS, "local function num(", "\n", "SolWorldScan.num"),
       cut(WS, "local function round(", "\n", "SolWorldScan.round"), cut(WS, "local function itemInfo(", "\n    return d\nend\n", "SolWorldScan.itemInfo"),
       "WS_INFO = itemInfo"]

ENV = r"""
NOW = 10000
function getTimestampMs() return NOW end
LOGS = {}
function print(m) LOGS[#LOGS + 1] = tostring(m) end
SW = { item_stacks = true }
SolAuthority = { on = function(f) return SW[f] == true end }
CALLS = 0
function List(t) return { t = t, size = function(self) return #self.t end, get = function(self, i) return self.t[i + 1] end } end
function Cont(items) local c = { items = items or {} }
    function c:getItems() return List(self.items) end
    function c:getContentsWeight() return #self.items end
    local function walk(cont, fn) for _, it in ipairs(cont.items) do fn(it, cont); if it.inv then walk(it.inv, fn) end end end
    function c:getCountTypeRecurse(t) local n = 0; walk(self, function(it) if it.t == t then n = n + 1 end end); return n end
    function c:AddItem(x) self.items[#self.items + 1] = x; return x end
    return c end
function instanceof(o, cls)
    if type(o) ~= "table" then return false end
    if cls == "HandWeapon" then return o.weapon == true end
    if cls == "InventoryContainer" then return o.inv ~= nil end
    if cls == "Food" then return o.food == true end
    if cls == "DrainableComboItem" then return o.uses ~= nil end
    if cls == "Clothing" then return o.cloth == true end
    return false end
local M = {}
function M:getFullType() CALLS = CALLS + 1; return self.t end
function M:getType() CALLS = CALLS + 1; return string.match(self.t, "([%w_]+)$") end
function M:getDisplayName() CALLS = CALLS + 1; return self.t end
function M:getCategory() CALLS = CALLS + 1; return self.weapon and "Weapon" or (self.food and "Food") or (self.cloth and "Clothing") or (self.inv and "Container") or "Item" end
function M:getDisplayCategory() CALLS = CALLS + 1; return self.dcat or "Item" end
function M:hasModData() CALLS = CALLS + 1; return self.md ~= nil end
function M:getModData() CALLS = CALLS + 1; self.md = self.md or {}; return self.md end
function M:getItemContainer() CALLS = CALLS + 1; return self.inv end
function M:getInventory() CALLS = CALLS + 1; return self.inv end
function M:getCount() CALLS = CALLS + 1; return 1 end
function M:getFluidContainer() CALLS = CALLS + 1; return nil end
function M:getConditionMax() CALLS = CALLS + 1; return 10 end
function M:getCondition() CALLS = CALLS + 1; return self.cond or 10 end
function M:getMaxAmmo() CALLS = CALLS + 1; if self.mag then return self.max end; if self.ranged then return self.max or 10 end; return 0 end
function M:getCurrentAmmoCount() CALLS = CALLS + 1; return self.count or self.cur or 0 end
function M:getAge() CALLS = CALLS + 1; return self.age or 0 end
function M:getCalories() CALLS = CALLS + 1; return 100 end
function M:getHungerChange() CALLS = CALLS + 1; return -0.1 end
function M:isRotten() CALLS = CALLS + 1; return false end
function M:getOffAgeMax() CALLS = CALLS + 1; return 5 end
function M:getCurrentUsesFloat() CALLS = CALLS + 1; return self.uses end
local WM = {}
function WM:getMaxDamage() CALLS = CALLS + 1; return self.dmg or 1 end
function WM:isRanged() CALLS = CALLS + 1; return self.ranged == true end
function WM:isJammed() return false end
function WM:getMaxRange() return self.range or 1.2 end
function WM:getSwingTime() return 3 end
function WM:getWeight() return 1 end
function WM:getEnduranceMod() return 1 end
function WM:getSharpness() return 1 end
function WM:isTwoHandWeapon() return self.two == true end
function WM:getMagazineType() return self.magType end
function WM:getAmmoType() return self.ammoType end
function WM:isContainsClip() return false end
function WM:isRoundChambered() return false end
function WM:getScriptItem() local s = self; return { containsWeaponCategory = function(_, e) return s.cat == e end } end
function Item(full, o) o = o or {}; o.t = full
    return setmetatable(o, { __index = function(t, k) if rawget(t, "weapon") and WM[k] then return WM[k] end; return M[k] end }) end
SurvivorCompanion = {}
SC = SurvivorCompanion
U = {}
function U.call(o, m, ...) if o == nil then return nil, false end; local f = o[m]; if f == nil then return nil, false end; return f(o, ...), true end
function U.each(list, limit, fn) local n = list:size(); for i = 0, math.min(n, limit) - 1 do fn(list:get(i)) end end
function U.config(k) return nil end
function U.nowMs() return NOW end
function U.listSize(l) return l and l:size() or 0 end
function U.itemType(it) local v = it and it:getFullType(); return v end
function U.instanceOf(it, cls) return (cls == "HandWeapon" or cls == "zombie.inventory.types.HandWeapon") and type(it) == "table" and it.weapon == true end
function U.hasMethod(o, m) return type(o) == "table" and o[m] ~= nil end
function U.inventory(a) return a:getInventory() end
function U.clamp(v, a, b) return math.max(a, math.min(b, v)) end
function U.idOf(a) return "sol-1" end
setmetatable(U, { __call = function(self) return self end })
SC.GameplayUtil = U
INV = Cont({})
SOL = { }
function SOL:getInventory() return INV end
function SOL:getPrimaryHandItem() return nil end
function SOL:getSecondaryHandItem() return nil end
"""
SETUP = """
INV.items = {}
for i = 1, 500 do INV.items[#INV.items + 1] = Item('EFZ.Ammo_762x51_M80', { dcat = 'Ammo' }) end
for i = 1, 30 do INV.items[#INV.items + 1] = Item('Base.Nails', { dcat = 'Material' }) end
KATANA = Item('Base.Katana', { weapon = true, dmg = 8, cat = 'LONG_BLADE', two = true })
G28 = Item('EFZ.G28', { weapon = true, ranged = true, two = true, dmg = 3, range = 20, magType = 'EFZ.G28_Mag10', ammoType = 'EFZ.Ammo_762x51_M80', cur = 0, max = 10 })
BEANS1 = Item('Base.TinnedBeans', { food = true, age = 1 }); BEANS2 = Item('Base.TinnedBeans', { food = true, age = 9 })
BANDAGE1 = Item('Base.Bandage', { dcat = 'FirstAid' }); BANDAGE2 = Item('Base.Bandage', { dcat = 'FirstAid', md = { SC_GivenByPlayer = true } })
TAPE1 = Item('Base.DuctTape', { uses = 1.0 }); TAPE2 = Item('Base.DuctTape', { uses = 0.3 })
SHIRT1 = Item('Base.Tshirt', { cloth = true }); SHIRT2 = Item('Base.Tshirt', { cloth = true })
MAG1 = Item('EFZ.G28_Mag10', { mag = true, max = 10, count = 0 }); MAG2 = Item('EFZ.G28_Mag10', { mag = true, max = 10, count = 4 })
for _, x in ipairs({ KATANA, G28, BEANS1, BEANS2, BANDAGE1, BANDAGE2, TAPE1, TAPE2, SHIRT1, SHIRT2, MAG1, MAG2 }) do INV:AddItem(x) end
"""
def fresh():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV); L.execute(ST)
    L.execute("\n".join(GPARTS)); L.execute(IX)
    L.execute("\n".join(PARTS) + "\nINVW = inventoryWeapons\nRELOAD = hasReloadAmmo\n")
    L.execute("\n".join(SIP)); L.execute("\n".join(WSP))
    L.execute(SETUP)
    return L
TOCOUNT = r"""
local items = U.inventoryItemsDeep(INV, 240)
SEEN = {}
for _, it in ipairs(items) do SEEN[it] = true end
NITEMS = #items
"""
# ---- switch on: everything seen, rounds = 500
L = fresh()
L.execute(TOCOUNT)
ck("on: katana, G28 and food are seen", L.eval("SEEN[KATANA] and SEEN[G28] and SEEN[BEANS1] and SEEN[BEANS2] and SEEN[BANDAGE1]") is True)
L.execute("_, _, INFO = U.inventoryItemsDeep(INV, 240)")
ck("on: rounds are one stack of 500", L.eval("INFO.byType['EFZ.Ammo_762x51_M80']") == 500 and L.eval("INFO.count[INV.items[1]]") == 500, L.eval("INFO.byType['EFZ.Ammo_762x51_M80']"))
ck("on: nails one stack of 30", L.eval("INFO.byType['Base.Nails']") == 30)
ck("on: distinct entries = 2 stacks + 12 stateful/single", L.eval("INFO.distinct") == 14, L.eval("INFO.distinct"))
ck("on: list still capped at 240 (stack members fill the rest)", L.eval("NITEMS") == 240, L.eval("NITEMS"))
ck("on: distinct entries come first", L.eval("(function() local r = U.inventoryItemsDeep(INV, 240); return r[3] == KATANA and r[14] == MAG2 end)()") is True)
ck("on: stateful items not merged (two beans, two bandages (one modData), two tapes, two shirts, two magazines)",
   L.eval("SEEN[BEANS2] and SEEN[BANDAGE2] and SEEN[TAPE1] and SEEN[TAPE2] and SEEN[SHIRT1] and SEEN[SHIRT2] and SEEN[MAG1] and SEEN[MAG2]") is True
   and L.eval("INFO.count[BEANS1] == 1 and INFO.count[TAPE1] == 1 and INFO.count[MAG1] == 1 and INFO.count[SHIRT1] == 1") is True)
ck("on: a small cap still lists every distinct thing", L.eval("(function() local r, _, i = U.inventoryItemsDeep(INV, 14); return #r == 14 and i.distinct == 14 end)()") is True)
L.execute("E = SC.InventoryIndex.get(SOL)")
ck("on: index weapons = katana + G28", L.eval("#E.weapons") == 2)
ck("on: index looseAmmoByType counts 500 rounds", L.eval("E.looseAmmoByType['Ammo_762x51_M80']") == 500, L.eval("E.looseAmmoByType['Ammo_762x51_M80']"))
ck("on: index itemCountByType nails 30, magazines 2 (separate)", L.eval("E.itemCountByType['Nails']") == 30 and L.eval("#E.magazinesByType['G28_Mag10']") == 2)
ck("on: index itemSet holds the stack members listed", L.eval("E.itemSet[INV.items[2]] == true and E.itemSet[INV.items[531]] == true"))
ck("on: inventoryWeapons lists katana + G28", L.eval("#(INVW(SOL))") == 2)
ck("on: hasReloadAmmo true (magazine with rounds)", L.eval("RELOAD(INV, (INVW(SOL))[2], E)") is True or L.eval("RELOAD(INV, (INVW(SOL))[1], E)") is True)
ck("U.inventoryCount(actor, rounds) = 500 natively", L.eval("U.inventoryCount(SOL, 'EFZ.Ammo_762x51_M80')") == 500)
ck("U.inventoryCount(inventory, nails) = 30", L.eval("U.inventoryCount(INV, 'Base.Nails')") == 30)
ck("multi-instance callers still get several (5 Nails)", L.eval("(function() local n = 0; for _, it in ipairs(U.inventoryItemsDeep(INV, 240)) do if it.t == 'Base.Nails' then n = n + 1 end end; return n end)()") >= 5)

# ---- scan cost: method calls on items for one index build + weapon list
COST = "SolItemStacks.reset(); SC.InventoryIndex.reset(); CALLS = 0; local e = SC.InventoryIndex.get(SOL); INVW(SOL, e); COSTN = CALLS"
L = fresh(); L.execute(COST); on_cost = L.eval("COSTN"); on_entries = L.eval("#(SC.InventoryIndex.get(SOL).weapons)")
L.execute("_, _, I2 = U.inventoryItemsDeep(INV, 240)"); on_classified = L.eval("I2.distinct")
L = fresh(); L.execute("SW.item_stacks = false"); L.execute(COST); off_cost = L.eval("COSTN")
print("  LF index + weapon list item calls: off=%d on=%d; entries classified off=240 on=%d" % (off_cost, on_cost, on_classified))
ck("scan cost lower: LF index build + weapon list item calls (on < off)", on_cost < off_cost, (off_cost, on_cost))
ck("scan cost lower: LF index classifies %d entries instead of 240" % on_classified, on_classified < 240 // 10)
SCOST = """SolItemStacks.reset(); CALLS = 0; local n = 0
for _, it in ipairs(INV.items) do local d = INV_READ(it); n = n + (d.n or 1) end
for _, it in ipairs(INV.items) do local d = WS_INFO(it) end
SN = n; SCOSTN = CALLS"""
L = fresh(); L.execute(SCOST); s_on, s_n = L.eval("SCOSTN"), L.eval("SN")
L.execute("D1, D2 = INV_READ(INV.items[1]), INV_READ(INV.items[2]); B1, B2 = INV_READ(BEANS1), INV_READ(BEANS2); W1, W2 = WS_INFO(TAPE1), WS_INFO(TAPE2)")
ck("Sol readers on: rounds share one record, food and drainables read per item",
   L.eval("D1 == D2 and B1 ~= B2 and W1 ~= W2 and W1.uses == 1 and W2.uses == 0.3") is True)
L = fresh(); L.execute("SW.item_stacks = false"); L.execute(SCOST); s_off = L.eval("SCOSTN"); s_noff = L.eval("SN")
print("  SolInventory.itemRead + SolWorldScan.itemInfo item calls over 542 items: off=%d on=%d" % (s_off, s_on))
ck("scan cost lower: Sol readers (on < half of off)", s_on * 2 < s_off, (s_off, s_on))
ck("Sol readers: item count unchanged (542 both ways)", s_n == s_noff == 542, (s_n, s_noff))
L = fresh(); L.execute("SW.item_stacks = false; D1, D2 = INV_READ(INV.items[1]), INV_READ(INV.items[2])")
ck("Sol readers off: a record per item (old)", L.eval("D1 ~= D2") is True)

# ---- switch off: the old behaviour
L = fresh()
L.execute("SW.item_stacks = false"); L.execute(TOCOUNT)
ck("off: old capped walk (180-root reserve gone, 240 rounds), no katana", L.eval("NITEMS") == 240 and L.eval("SEEN[KATANA]") is None)
ck("off: no third return value", L.eval("select('#', U.inventoryItemsDeep(INV, 240))") == 2)
L.execute("E = SC.InventoryIndex.get(SOL)")
ck("off: index sees no weapon and counts 240 rounds (old)", L.eval("#E.weapons") == 0 and L.eval("E.looseAmmoByType['Ammo_762x51_M80']") == 240)

# ---- the LF rounds fixture: each round its own item, a bag with the rest
L = fresh()
L.execute("BAGI = Item('Base.Bag_ALICEpack', { inv = Cont({ Item('Base.Katana', { weapon = true, dmg = 8 }), Item('Base.Pills') }) }); INV:AddItem(BAGI)")
L.execute("R, C, I = U.inventoryItemsDeep(INV, 240, 12)")
ck("bag contents reached past 500 rounds", L.eval("#C") == 1 and L.eval("(function() for _, it in ipairs(R) do if it.t == 'Base.Pills' then return true end end; return false end)()") is True)

for nm, src in (("SolItemStacks.lua", ST), ("SCGameplayUtil.lua", GU), ("SCInventoryIndex.lua", IX), ("SolInventory.lua", SI), ("SolWorldScan.lua", WS)):
    ck("ascii only " + nm, all(ord(c) < 128 for c in src))
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
if os.path.exists(GATE):
    for nm in ("SolItemStacks.lua", "SCGameplayUtil.lua", "SCInventoryIndex.lua", "SolInventory.lua", "SolWorldScan.lua"):
        r = subprocess.run([sys.executable, GATE, os.path.join(cl, nm)], capture_output=True, text=True)
        ck("tonumber gate " + nm, r.returncode == 0, r.stdout[-300:])
else:
    ck("tonumber gate present", False, GATE)
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
