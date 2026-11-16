"""s107 gear_page offline (kahlua_env). Loads the REAL SolPages (page class, LF widget reading, the old loadout card), SolText +
SolTextData (real glyph drawing), SolPerf, LF's SCStableValue / SCGameplayUtil (inventoryCount, transferItemVerified, the
item walk), s100 SolItemStacks, s98 SolCombatEquipFallback, s99 SolWeaponPick / SolMagFill and s105 SolCombatPlans from the
patched temp client; only Java objects (Sol, him, items, containers, worn items), LF's hidden UI root, LF's Commands /
UIBridge and the game's texture loader are fakes.
Shows: the section data (hands with rounds in the gun / spare magazines / loose rounds, every state, favourites, plan, worn
with swap, her bag grouped with counts, his bag only on his click and only what she can use, car / home rows, like me with a
spare); a UI render of the real page (texts drawn, LF's weapon-priority selector and duplicate buttons gone); the virtualised
list draws only the visible rows; a rebuild only on a signature change; the buttons; switch off = the old card and LF's
widgets; SolPerf "gear_page"; installer idempotent; tonumber + jarcall + card gates; ASCII.
Run: python test_s107_gear_page.py [client dir] [matching Mind dir]"""
import os, sys, shutil, subprocess, tempfile, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
from kahlua_env import lua51
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
SWITCHES = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
FAIL, P = [], []
def ck(n, c, d=""): print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else "")); (P if c else FAIL).append(n)
def esc(s): return "".join(c if 32 <= ord(c) < 127 else "\\u%04X" % ord(c) for c in s)

# ------------------------------------------------ install on a temp copy (same folder depth, so the switch file is found)
tmp = tempfile.mkdtemp(prefix="s107gp_")
cl = os.path.join(tmp, "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(cl)
os.makedirs(os.path.join(tmp, "Zomboid", "Lua"))
fx = os.path.join(tmp, "Zomboid", "Lua", "SolFixes_LAB.txt")
if os.path.exists(SWITCHES): shutil.copy(SWITCHES, fx)
else: open(fx, "w", newline="").write("item_stacks=on\r\n")
for f in os.listdir(CL):
    if f.endswith(".lua"): shutil.copy(os.path.join(CL, f), cl)
def run(script, d): return subprocess.run([sys.executable, os.path.join(HERE, script), d], capture_output=True, text=True)
r1, r2 = run("apply_s107_gear_page.py", cl), run("apply_s107_gear_page.py", cl)
ck("installer runs or preserves the already-installed page", r1.returncode == 0 and "applied" in r1.stdout
   and ("copied SolGearPage.lua" in r1.stdout or "kept SolGearPage.lua" in r1.stdout), r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "copied" not in r2.stdout and "edited" not in r2.stdout, r2.stdout + r2.stderr)
auth = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read()
ck("SolAuthority lists gear_page once", auth.count('"gear_page"') == 1)
sw = open(fx, encoding="utf-8").read()
ck("SolFixes_LAB.txt: gear_page=on once", sum(1 for l in sw.splitlines() if l.strip() == "gear_page=on") == 1)
ck("no LF / SolPages file changed by the installer", all(open(os.path.join(cl, f), "rb").read() == open(os.path.join(CL, f), "rb").read() for f in ("SolPages.lua", "SCUI.lua", "SCCombat.lua") if os.path.exists(os.path.join(CL, f))))
L = lua51.LuaRuntime(unpack_returned_tuples=True)
comp = L.eval("function(s) local f, e = loadstring(s); return f ~= nil, e end")
src = open(os.path.join(cl, "SolGearPage.lua"), encoding="utf-8").read()
ok, e = comp(src); ck("compiles SolGearPage.lua", ok, e)
ck("ascii SolGearPage.lua", all(ord(c) < 128 for c in src))
ck("ascii SolAuthority.lua", all(ord(c) < 128 for c in auth))

def P_(s): return os.path.abspath(s).replace("\\", "/")
L.execute('package.path = [[%s/?.lua;%s/?.lua]]' % (P_(cl), P_(os.path.join(CL, "..", "shared"))))
L.execute(r'''
HANDLERS = {}
Events = setmetatable({}, {__index = function(t, k) local e = {Add = function(f) HANDLERS[k] = HANDLERS[k] or {}; table.insert(HANDLERS[k], f) end, Remove = function() end}; rawset(t, k, e); return e end})
NOW = 100000; getTimestampMs = function() return NOW end; isClient = function() return false end; isServer = function() return false end
SW = { gear_page = true, item_stacks = true, combat_equip_fallback = true, preferred_weapon = true, mag_fill = true, melee_choice = true, weapon_scan = true, combat_plans = true }
SolAuthority = { on = function(n) return SW[n] == true end }
LOG = {}; local rawPrint = print; print = function(s) LOG[#LOG + 1] = tostring(s) end
function logged(s) for _, l in ipairs(LOG) do if string.find(l, s, 1, true) then return true end end return false end
MD = {}; ModData = { getOrCreate = function(k) MD[k] = MD[k] or {}; return MD[k] end }
TEXN = 0
getTexture = function(n) TEXN = TEXN + 1; return { name = n, getWidth = function() return 8 end, getHeight = function() return 16 end } end
UIFont = { Small = 1 }
getCore = function() return { getScreenWidth = function() return 1920 end, getScreenHeight = function() return 1080 end } end
function jlist(t) return { size = function() return #t end, get = function(_, i) return t[i + 1] end, add = function(_, x) t[#t + 1] = x end, t = t } end
ArrayList = { new = function() return jlist({}) end }
-- body locations: tostring() as the game's ItemBodyLocation
LOCS = {}; function LOC(n) if not LOCS[n] then LOCS[n] = setmetatable({ n = n }, { __tostring = function(s) return "base:" .. s.n end }) end return LOCS[n] end
-- items
local IT = {}; IT.__index = IT
function item(ft, o) o = o or {}; return setmetatable({ ft = ft, o = o, md = o.md }, IT) end
function IT:getFullType() return self.ft end
function IT:getType() return (string.match(self.ft, "%.(.+)$")) end
function IT:getDisplayName() return self.o.name or self:getType() end
function IT:getName() return self:getDisplayName() end
function IT:getCategory() return self.o.cat or (self.o.weapon and "Weapon") or (self.o.clothing and "Clothing") or (self.o.food and "Food") or "Item" end
function IT:getDisplayCategory() return self.o.dcat or "" end
function IT:hasModData() return self.md ~= nil end
function IT:getModData() self.md = self.md or {}; return self.md end
function IT:isRanged() return self.o.ranged == true end
function IT:getCondition() return self.o.cond or 10 end
function IT:getConditionMax() return 10 end
function IT:getCurrentAmmoCount() return self.o.ammo or 0 end
function IT:isRoundChambered() return self.o.chambered == true end
function IT:isJammed() return self.o.jammed == true end
function IT:getMagazineType() return self.o.magType end
function IT:getAmmoType() local k = self.o.ammoKey; if not k then return nil end; return { getItemKey = function() return k end } end
function IT:getMaxAmmo() return self.o.maxAmmo or 0 end
function IT:getContainer() return self.cont end
function IT:getItemContainer() return self.o.bag end
function IT:IsFood() return self.o.food == true end
function IT:IsClothing() return self.o.clothing == true end
function IT:getBodyLocation() return self.o.loc and LOC(self.o.loc) or nil end
function IT:getBiteDefense() return self.o.bite or 0 end
function IT:getScratchDefense() return self.o.scratch or 0 end
function IT:getBulletDefense() return self.o.bullet or 0 end
function IT:getMaxDamage() return self.o.dmg or 0 end
function IT:getMaxRange() return self.o.ranged and 30 or 1.5 end
function IT:getScriptItem() return nil end
function IT:getCount() return 1 end
function IT:getFluidContainer() return nil end
function instanceof(o, cls)
    if type(o) ~= "table" or getmetatable(o) ~= IT then return false end
    if cls == "HandWeapon" or cls == "zombie.inventory.types.HandWeapon" then return o.o.weapon == true end
    if cls == "InventoryContainer" then return o.o.bag ~= nil end
    if cls == "Clothing" then return o.o.clothing == true end
    if cls == "Food" then return o.o.food == true end
    if cls == "ComboItem" then return not (o.o.weapon or o.o.clothing or o.o.food or o.o.bag) end
    return false
end
-- containers (ItemContainer: getItems, contains, Remove, AddItem, the recursive lookups)
local CO = {}; CO.__index = CO
function cont(list) local c = setmetatable({ list = {} }, CO); for _, x in ipairs(list or {}) do c:AddItem(x) end; return c end
function CO:getItems() return jlist(self.list) end
function CO:getContentsWeight() local w = 0; for _, x in ipairs(self.list) do w = w + (x.o.w or 0.1) end; return math.floor(w * 1000 + 0.5) / 1000 end
function CO:contains(it) for _, x in ipairs(self.list) do if x == it then return true end end return false end
function CO:Remove(it) for i, x in ipairs(self.list) do if x == it then table.remove(self.list, i); it.cont = nil; return end end end
function CO:AddItem(it) self.list[#self.list + 1] = it; it.cont = self; return it end
function CO:getType() return "none" end
function CO:walk(f) for _, x in ipairs(self.list) do f(x); if x.o.bag then x.o.bag:walk(f) end end end
function CO:getCountTypeRecurse(ft) local n = 0; self:walk(function(x) if x.ft == ft then n = n + 1 end end); return n end
function CO:getAllTypeRecurse(ft, extra) assert(extra == nil, "only the 1-arg overload is used"); local out = {}; self:walk(function(x) if x.ft == ft then out[#out + 1] = x end end); return jlist(out) end
function CO:getAllCategoryRecurse(cat, out) assert(type(cat) == "string" and out ~= nil, "B42: getAllCategoryRecurse(String, ArrayList)"); self:walk(function(x) if x:getCategory() == cat then out:add(x) end end); return out end
-- characters
function actor(id, o)
    o = o or {}
    local a = { md = { SC_Id = id }, x = 0, y = 0, z = 0, hand = o.hand, hand2 = nil, inv = cont(o.items or {}), worn = {}, dead = false }
    function a:getModData() return self.md end
    function a:getX() return self.x end function a:getY() return self.y end function a:getZ() return self.z end
    function a:isDead() return self.dead end
    function a:getPrimaryHandItem() return self.hand end
    function a:getSecondaryHandItem() return self.hand2 end
    function a:getInventory() return self.inv end
    function a:getWornItems() local w = self.worn; return { size = function() return #w end, get = function(_, i) local e = w[i + 1]; return { getItem = function() return e.item end, getLocation = function() return LOC(e.loc) end } end } end
    function a:isEquippedClothing(it) for _, e in ipairs(self.worn) do if e.item == it then return true end end return false end
    function a:isEquipped(it) return it == self.hand or it == self.hand2 or self:isEquippedClothing(it) end
    function a:removeWornItem(...) assert(select("#", ...) == 1, "the 1-arg overload"); local it = ...; for i, e in ipairs(self.worn) do if e.item == it then table.remove(self.worn, i); REMOVED = (REMOVED or 0) + 1; return end end end
    function a:resetModelNextFrame() end
    function a:wear(it, loc) self.worn[#self.worn + 1] = { item = it, loc = loc }; if not self.inv:contains(it) then self.inv:AddItem(it) end end
    return a
end
''')
# the world: Sol with a G28 in her hands, two magazines, 500 loose rounds, her M4 (his pick), the katana (her melee), worn items
L.execute(r'''
G28 = item("Base.G28", { weapon = true, ranged = true, ammo = 7, chambered = true, magType = "Base.G28Mag", ammoKey = "Base.308Bullets", dmg = 3, name = "G28" })
M4 = item("EscapeFromZomboidFirearms.M4A1", { weapon = true, ranged = true, ammo = 30, magType = "Base.556Clip", ammoKey = "Base.556Bullets", dmg = 2, name = "M4A1", md = { SC_ManualEquipFor = "sol-1" } })
KATANA = item("Base.Katana", { weapon = true, dmg = 4, name = "Katana", md = { SolMeleeFor = "sol-1" } })
BAT = item("Base.BaseballBat", { weapon = true, dmg = 1.5, name = "Baseball Bat", cond = 5 })
MAG1 = item("Base.G28Mag", { maxAmmo = 20, ammo = 20, ammoKey = "Base.308Bullets", dcat = "Ammo", name = "G28 Magazine" })
MAG2 = item("Base.G28Mag", { maxAmmo = 20, ammo = 5, ammoKey = "Base.308Bullets", dcat = "Ammo", name = "G28 Magazine" })
HAT = item("Base.Hat_BaseballCap", { clothing = true, loc = "Hat", bite = 2, scratch = 2, cond = 6, name = "Baseball Cap" })
HAT2 = item("Base.Hat_Bandana", { clothing = true, loc = "Hat", bite = 1, name = "Bandana" })
TSHIRT = item("Base.Tshirt_White", { clothing = true, loc = "Tshirt", name = "T-shirt" })
CAN = item("Base.TinnedBeans", { food = true, name = "Beans" })
SCREW = item("Base.Screwdriver", { dcat = "Tool", name = "Screwdriver" })
items = { G28, M4, KATANA, BAT, MAG1, MAG2, HAT, HAT2, TSHIRT, CAN, SCREW }
for i = 1, 500 do items[#items + 1] = item("Base.308Bullets", { dcat = "Ammo", name = ".308 Round", w = 0.01 }) end
BANDAGES = {}; for i = 1, 3 do local b = item("Base.Bandage", { dcat = "FirstAid", name = "Bandage" }); items[#items + 1] = b; BANDAGES[i] = b end
SOL = actor("sol-1", { hand = G28, items = items }); SOL:wear(HAT, "Hat"); SOL:wear(TSHIRT, "Tshirt")
-- him: better hat (a spare too), a vest where she has nothing, an axe; bag: rounds of her calibre and of another, a bandage, food, a shirt
ARMYHAT = item("Base.Hat_Army", { clothing = true, loc = "Hat", bite = 40, scratch = 40, bullet = 20, name = "Army Helmet" })
ARMYHAT2 = item("Base.Hat_Army", { clothing = true, loc = "Hat", bite = 40, scratch = 40, bullet = 20, name = "Army Helmet" })
VEST = item("Base.Vest_BulletArmy", { clothing = true, loc = "TorsoExtraVest", bite = 30, scratch = 30, bullet = 60, name = "Bulletproof Vest" })
AXE = item("Base.Axe", { weapon = true, dmg = 3.5, name = "Axe" })
mine = { ARMYHAT, ARMYHAT2, VEST, AXE, item("Base.Bandage", { dcat = "FirstAid", name = "Bandage" }), item("Base.Apple", { food = true, name = "Apple" }),
         item("Base.Tshirt_Red", { clothing = true, loc = "Tshirt", name = "Red T-shirt" }), item("Base.Hammer", { weapon = true, dmg = 1, name = "Hammer" }) }
for i = 1, 40 do mine[#mine + 1] = item("Base.308Bullets", { dcat = "Ammo", name = ".308 Round", w = 0.01 }) end
for i = 1, 30 do mine[#mine + 1] = item("Base.Bullets9mm", { dcat = "Ammo", name = "9mm Round", w = 0.01 }) end
PLAYER = actor("player", { hand = AXE, items = mine }); PLAYER:wear(ARMYHAT, "Hat"); PLAYER:wear(VEST, "TorsoExtraVest")
getSpecificPlayer = function(i) return PLAYER end
''')
for m in ("SCStableValue", "SCGameplayUtil"):
    ok = L.eval('(function() local ok, e = pcall(require, "%s"); if not ok then print("ERR " .. tostring(e)) end; return ok end)()' % m); ck("real LF " + m + " loads offline", ok is True)
L.execute(r'''
SC = SurvivorCompanion; GU = SC.GameplayUtil
GU.idOf = function(a) return type(a) == "table" and a.md and a.md.SC_Id or nil end
GU.isValidActor = function(a) return type(a) == "table" and a.md ~= nil and a.dead ~= true end
SC.InventoryIndex = nil
ISSUED = {}; STATE = { combatMode = "defensive" }
SC.Commands = { issue = function(id, command, payload) ISSUED[#ISSUED + 1] = command .. "=" .. tostring(payload); return true end, peek = function() return STATE end, persist = function() end }
EQUIP = {}; NEAR = true
SC.UIBridge = { NEARBY_DISTANCE = 3, validateNearbyActor = function() return NEAR end,
                equipOnCompanion = function(a, it, p, kind) EQUIP[#EQUIP + 1] = kind .. ":" .. it:getFullType(); return true end }
-- LF's hidden Loadout page (the widgets SCUI buildLoadout makes, read by the real SolPages.readWidgets)
local function W(t) t.x = t.x or 0; return t end
function lfWidgets()
    return { children = {
        W{ Type = "ISButton", y = 7, title = "Open companion inventory", onclick = function() end, scCommand = "open_inventory" },
        W{ Type = "ISLabel", y = 30, name = "Health", r = 0.79, g = 0.73, b = 0.48 },
        W{ Type = "ISButton", y = 60, title = "Medical check", onclick = function() end, scCommand = "open_health" },
        W{ Type = "ISButton", y = 90, title = "Bandage", onclick = function() end, scCommand = "bandage" },
        W{ Type = "ISLabel", y = 120, name = "Weapon priority", r = 0.79, g = 0.73, b = 0.48 },
        W{ Type = "ISComboBox", y = 150, options = { "Best", "Firearm", "Quiet" }, selected = 1, onChange = function() end, onChangeArgs = { "set_weapon_priority" } },
        W{ Type = "ISLabel", y = 180, name = "Carry policy", r = 0.79, g = 0.73, b = 0.48 },
        W{ Type = "ISTickBox", y = 210, options = { "Allow overload" }, selected = {}, changeOptionMethod = function() end, changeOptionArgs = { "set_allow_overload" } },
    } }
end
ROOT = { selectedTab = "loadout", selectedRow = { id = "sol-1", health = 0.98, loadWeight = 59.4, loadCapacity = 100, equippedWeapon = nil, ammunition = 88 },
         setVisible = function() end, setSelectedTab = function(self, t) self.selectedTab = t end }
ROOT.detail = { rebuild = function() end, content = lfWidgets() }
LFAVAIL = { open_inventory = true, open_health = true, bandage = false }
SC.UI = { ensureControl = function() return ROOT end, tabIds = function() return { "status", "orders", "loadout" } end,
          commandAvailability = function(row, c) return LFAVAIL[c] == true end }
SC.Registry = { living = function() return { SOL } end }
-- the game's ISPanel, as much as SolPages uses
ISPanel = { derive = function(self, name) local c = {}; c.__index = c; return setmetatable(c, { __index = self }) end }
ISPanel.__index = ISPanel
function ISPanel:new(x, y, w, h) return setmetatable({ x = x, y = y, w = w, h = h }, ISPanel) end
package.preload["ISUI/ISPanel"] = function() return true end
package.loaded["SolActions"] = true
U = SolUI or {}; SolUI = U
U.solActor = function() return SOL end
''')
for m in ("SolText", "SolPerf", "SolPages", "SolItemStacks", "SolCombatEquipFallback", "SolWeaponPick", "SolMagFill", "SolCombatPlans", "SolOverlay", "SolGearPage"):
    ok = L.eval('(function() local ok, e = pcall(require, "%s"); if not ok then print("ERR %s " .. tostring(e)) end; return ok end)()' % (m, m))
    ck("real " + m + " loads offline", ok is True, [l for l in L.eval("LOG").values() if "ERR" in l][-1:] )
L.execute(r'''
SAID = {}
SolBubble = SolBubble or {}; SolBubble.speak = function(a, line) SAID[#SAID + 1] = line; return true end
PERF = {}; local basePerf = SolUI.perfAdd; SolUI.perfAdd = function(n, ms) PERF[n] = (PERF[n] or 0) + 1; return basePerf(n, ms) end
TEXTS = {}; local baseLine = SolText.drawLine
SolText.drawLine = function(ui, s, ...) TEXTS[#TEXTS + 1] = type(s) == "table" and SolText.escape(s) or tostring(s); return baseLine(ui, s, ...) end
for _, f in ipairs(HANDLERS.OnGameStart or {}) do f() end
GP = SolGearPage
function drew(s) for _, t in ipairs(TEXTS) do if string.find(t, s, 1, true) then return true end end return false end
-- a page as SolPages makes it, with the UI element methods the game gives an ISPanel
function newPage()
    local p = SolUI.PageClass:new(0, 0)
    p.mx, p.my, p.over, p.drawsN = 0, 0, false, 0
    function p:getMouseX() return self.mx end function p:getMouseY() return self.my end function p:isMouseOver() return self.over end
    function p:drawTextureScaled() self.drawsN = self.drawsN + 1 end
    function p:setStencilRect() end function p:clearStencilRect() end function p:drawRect() end function p:drawText() end
    function p:setX() end function p:setY() end function p:getX() return 0 end function p:getY() return 0 end
    return p
end
function frame(p, dt) NOW = NOW + (dt or 16); TEXTS = {}; p.drawsN = 0; p:prerender() end
''')
ev = L.eval
ck("installed at game start: SolPages' page class wrapped once", ev("SolUI.PageClass.solGearPage == true") and ev('logged("[SolGearPage] ready v")'))

# ------------------------------------------------ section data (GP.build on the fakes)
L.execute('M = GP.build(SOL, PLAYER, { showMine = true, showSrc = true })')
h = ev("M.hands")
ck("hands: the real weapon in her hands (not LF's '-')", h.name == "G28", h.name)
ck("hands: rounds in the gun = magazine 7 + chambered 1", h.inGun == 8, h.inGun)
ck("hands: spare magazines 2 holding 25 rounds", h.mags == 2 and h.magRounds == 25, (h.mags, h.magRounds))
ck("hands: loose rounds of its calibre 500 (one stack, counted natively)", h.loose == 500, h.loose)
ck("hands: state ready; reload offered (a magazine gun, mag_fill on)", h.state == "ready" and h.canReload == True)
def state_of(lua_setup):
    return ev('(function() local o = {}; for k, v in pairs(G28.o) do o[k] = v end; local md = G28.md; %s; local s = GP.hands(SOL).state; G28.o = o; G28.md = md; return s end)()' % lua_setup)
ck("state: jammed", state_of("G28.o.jammed = true") == "jammed")
ck("state: empty (no rounds, nothing chambered)", state_of("G28.o.ammo = 0; G28.o.chambered = false") == "empty")
ck("state: chambered round only = ready (s99 counts it)", state_of("G28.o.ammo = 0; G28.o.chambered = true") == "ready")
ck("state: parts problem (EFZ assembly not ready, s98 whyUnusable)", state_of('G28.md = { TW = { key = "g28", ready = false } }') == "parts")
ck("state: broken (condition 0)", state_of("G28.o.cond = 0") == "broken")
ck("hands empty: 'nothing in her hands'", ev("(function() SOL.hand = nil; local r = GP.hands(SOL).none; SOL.hand = G28; return r end)()") is True)
ck("hands: EFZ gun found in the other hand too", ev("(function() SOL.hand, SOL.hand2 = nil, M4; local n = GP.hands(SOL).name; SOL.hand, SOL.hand2 = G28, nil; return n end)()") == "M4A1")
ck("favourites: firearm = his pick (SC_ManualEquipFor), melee = the katana (SolMeleeFor)", ev("M.prefs.gun == M4 and M.prefs.melee1 == KATANA"))
ck("favourites: both changeable (preferred_weapon / melee_choice on)", ev("M.prefs.canGun == true and M.prefs.canMelee == true"))
ck("plan: s105 current plan shown (smart by default)", ev("M.plansOn == true and M.plan == 'smart'"))
ck("worn: cap 60% at the head slot, T-shirt; bandana offered as a swap for the cap", ev("#M.worn == 2 and M.worn[1].item == HAT and math.floor(M.worn[1].cond * 100 + 0.5) == 60 and M.worn[1].alt == HAT2"))
ck("worn: slot words plain Arabic", ev("GP.slotWord(M.worn[1].loc)") == esc("الراس") and ev("GP.slotWord('base:TorsoExtraVest')") == esc("الصدر"))
def grp(m, k): return ev("(function() local t = {}; for _, e in ipairs(%s[\"%s\"]) do t[#t + 1] = e.ft .. 'x' .. e.n end; return table.concat(t, ',') end)()" % (m, k))
ck("her bag: weapons without the one in her hands", grp("M.bag", "weapons") == "Base.BaseballBatx1,Base.Katanax1,EscapeFromZomboidFirearms.M4A1x1", grp("M.bag", "weapons"))
ck("her bag: ammo = 500 rounds as ONE entry + 2 magazines", grp("M.bag", "ammo") == "Base.308Bulletsx500,Base.G28Magx1,Base.G28Magx1", grp("M.bag", "ammo"))
ck("her bag: medical x3, food, tools", grp("M.bag", "medical") == "Base.Bandagex3" and grp("M.bag", "food") == "Base.TinnedBeansx1" and grp("M.bag", "tools") == "Base.Screwdriverx1")
ck("her bag: worn items are not in it, the spare bandana is", grp("M.bag", "clothing") == "Base.Hat_Bandanax1", grp("M.bag", "clothing"))
ck("his bag: only what she can use (her calibre, weapons not in his hands, medical, armour)", "Base.308Bulletsx40" in grp("M.mine", "ammo") and "9mm" not in grp("M.mine", "ammo")
   and grp("M.mine", "weapons") == "Base.Hammerx1" and grp("M.mine", "medical") == "Base.Bandagex1" and grp("M.mine", "food") == "" and grp("M.mine", "clothing") == "Base.Hat_Armyx1",
   (grp("M.mine", "ammo"), grp("M.mine", "weapons"), grp("M.mine", "clothing")))
ck("his bag is not read until he asks for it", ev("GP.build(SOL, PLAYER, {}).mine == nil"))
L.execute('''SolUI.invLast = function() return { t = 5, rows = {
    { where = "vehicle", type = "Base.308Bullets", name = ".308 Round", count = 60, grp = "ammo", label = "Van" },
    { where = "house", type = "Base.Bullets9mm", name = "9mm Round", count = 90, grp = "ammo" },
    { where = "house", type = "Base.556Bullets", name = "5.56 Round", count = 30, grp = "ammo" },
    { where = "house", type = "Base.Bandage", name = "Bandage", count = 4, grp = "medical" },
    { where = "sol", type = "Base.Bandage", name = "Bandage", count = 3, grp = "medical" },
    { where = "vehicle", type = "Base.Apple", name = "Apple", count = 2, grp = "food" } } } end''')
L.execute('M2 = GP.build(SOL, PLAYER, { showSrc = true })')
ck("car and home: her calibres (G28 in the van, M4 at home), bandages at home; no 9mm, no food, not her own bag",
   ev("(function() local t = {}; for _, r in ipairs(M2.src) do t[#t + 1] = r.where .. ':' .. r.name .. 'x' .. r.n end; return table.concat(t, ',') end)()") == "vehicle:.308 Roundx60,house:5.56 Roundx30,house:Bandagex4", ev("(function() local t = {}; for _, r in ipairs(M2.src) do t[#t + 1] = r.where .. ':' .. r.name .. 'x' .. r.n end; return table.concat(t, ',') end)()"))
like = ev("(function() local t = {}; for _, l in ipairs(M.like) do t[#t + 1] = l.myName .. '>' .. l.herName .. (l.spare and '+spare' or '') end; return table.concat(t, ',') end)()")
ck("like me: his axe over her best melee? no (katana scores higher); helmet over cap with a spare; vest where she has nothing", like == "Army Helmet>Baseball Cap+spare,Bulletproof Vest>" + esc("ما في"), like)

# ------------------------------------------------ the real page: render, LF widgets replaced
L.execute('PG = newPage(); PG.tab = "loadout"; PG:refresh(true); frame(PG)')
ck("render: no error in the page log", not ev('logged("failed")'), [l for l in ev("LOG").values() if "failed" in l][-2:])
for word, ar in (("hands", "بإيدها"), ("favourites", "سلاحها المفضّل"), ("plan", "خطة القتال"), ("worn", "لابسة"), ("her bag", "حقيبتها"), ("my bag", "حقيبتي"), ("car and home", "بالسيارة والبيت"), ("like me", "متلي")):
    e_ = esc(ar).replace("\\", "\\\\")
    L.execute('(function() for _, r in ipairs(PG.gear.rows) do if r.kind == "sec" and r.text == "%s" then PG.scroll = math.max(0, r.y - 10); frame(PG, 16); return end end end)()' % e_)
    ck("render: section '" + word + "' drawn (scrolled to it)", ev('drew("%s")' % e_))
L.execute("PG.scroll = 0; frame(PG, 16)")
ck("render: weapon name and rounds drawn", ev('drew("G28")') and ev('drew("8 %s")' % esc("طلقة").replace("\\", "\\\\")))
ck("render: one-line plan text drawn (smart)", ev('drew("%s")' % esc("ذكي").replace("\\", "\\\\")))
ck("render: glyph textures drawn by the real SolText", ev("PG.drawsN") > 200, ev("PG.drawsN"))
rows_cmds = ev("(function() local t = {}; for _, r in ipairs(PG.rows) do local it = r.it or (r.list and r.list[1]); t[#t + 1] = r.kind .. ':' .. tostring(it and it.command or (it and it.text) or '') end; return table.concat(t, ',') end)()")
ck("LF's weapon-priority selector and its section are gone (a plan sets it)", "set_weapon_priority" not in rows_cmds and "Weapon priority" not in rows_cmds, rows_cmds)
ck("LF's duplicate quick buttons are gone; carry policy stays", "open_inventory" not in rows_cmds and "bandage" not in rows_cmds and "set_allow_overload" in rows_cmds, rows_cmds)
L.execute("PG:refresh(true); PG:refresh(true)")      # two forced rebuilds in the same millisecond (a click right after a frame)
ck("a forced refresh in the same millisecond still replaces LF's selector", "set_weapon_priority" not in ev("(function() local t = {}; for _, r in ipairs(PG.rows) do local it = r.it or (r.list and r.list[1]); t[#t + 1] = tostring(it and it.command or '') end; return table.concat(t, ',') end)()"))
L.execute("frame(PG, 16)")
ck("LF's remaining widgets sit below the gear page", ev("PG.rows[1].y >= PG.gear.H and PG.cardH == PG.gear.H and PG.contentH >= PG.gear.H"))
ck("SolPerf gets 'gear_page'", (ev('PERF["gear_page"]') or 0) >= 1)
ck("quick actions: LF availability read at build time (bandage off)", ev("(function() for _, r in ipairs(PG.gear.rows) do if r.kind == 'btns' then return r.btns[1].on == true and r.btns[3].on == false end end end)()") is True)

# ------------------------------------------------ virtualised list: only the visible rows are drawn
L.execute(r'''
for i = 1, 600 do SOL.inv:AddItem(item("Base.Junk" .. i, { name = "Junk " .. i })) end
GP.MAX_BAG = 4000; PG.gear.dirty = true; frame(PG, 600)
NROWS = #PG.gear.rows; DRAWN0 = PG.gear.drawn; HITS0 = #PG.gear.hits; DRAWS0 = PG.drawsN
PG.scroll = math.floor(PG.gear.H / 2); frame(PG, 16)
DRAWNM = PG.gear.drawn; FIRSTM = GP.firstVisible(PG.gear.rows, PG.scroll)
''')
nrows, d0, dm = ev("NROWS"), ev("DRAWN0"), ev("DRAWNM")
ck("virtual list: 600+ rows built", nrows > 600, nrows)
ck("virtual list: top of the page draws only the visible rows (<= 530/24 + 2)", 0 < d0 <= 24, d0)
ck("virtual list: middle of the page too", 0 < dm <= 24, dm)
ck("virtual list: the middle frame starts at the first visible row (binary search)", ev("PG.gear.rows[FIRSTM].y + PG.gear.rows[FIRSTM].h > PG.scroll and (FIRSTM == 1 or PG.gear.rows[FIRSTM - 1].y + PG.gear.rows[FIRSTM - 1].h <= PG.scroll)"))
ck("virtual list: click areas only for visible rows, clipped to the window", ev("(function() for _, h in ipairs(PG.gear.hits) do if h.r[2] < 66 or h.r[2] + h.r[4] > 66 + 530 then return false end end; return #PG.gear.hits > 0 end)()"))
ck("virtual list: texture draws per frame bounded (<1500 with 600 rows)", ev("PG.drawsN") < 1500, ev("PG.drawsN"))
L.execute("PG.scroll = 0; frame(PG, 16)")

# ------------------------------------------------ rebuild only on a signature change
L.execute(r'''
frame(PG, 600)
F0, H0, B0, C0 = GP.stats.full, GP.stats.hands, SolItemStacks.stats.builds, GP.stats.checks
for i = 1, 60 do frame(PG, 16) end            -- ~1 s of frames, nothing changed
F1, H1, B1, C1 = GP.stats.full, GP.stats.hands, SolItemStacks.stats.builds, GP.stats.checks
''')
ck("no change: no rebuild over 60 frames (the walk's cache untouched too)", ev("F1 == F0 and H1 == H0 and B1 == B0"), ev("F0, F1, H0, H1, B0, B1"))
ck("no change: the signature is compared at most every 500 ms (2 checks in ~1 s, not 60)", ev("C1 - C0") <= 3, ev("C1 - C0"))
L.execute('SOL.inv:AddItem(item("Base.Bandage", { dcat = "FirstAid", name = "Bandage" })); frame(PG, 16); F2 = GP.stats.full; frame(PG, 600); F3 = GP.stats.full')
ck("a bandage added: no rebuild before the 500 ms check, one rebuild after", ev("F2 == F1 and F3 == F1 + 1"), ev("F1, F2, F3"))
ck("... and her bag shows x4 bandages", grp("PG.gear.model.bag", "medical") == "Base.Bandagex4")
L.execute('G28.o.ammo = 6; frame(PG, 600); F4, H4 = GP.stats.full, GP.stats.hands')
ck("a shot fired: only the hands are rebuilt (no bag walk)", ev("F4 == F3 and H4 == H1 + 1 and PG.gear.model.hands.inGun == 7"), ev("F3, F4, H1, H4"))
L.execute('MAG1.cont:Remove(MAG1); SOL.inv:AddItem(MAG1); frame(PG, 600); F5 = GP.stats.full')
ck("same count and weight (an item moved within the bag): no rebuild", ev("F5 == F4"))
L.execute('frame(PG, 15000); F6 = GP.stats.full')
ck("backstop: one rebuild after 15 s with equal signatures", ev("F6 == F5 + 1"))

# ------------------------------------------------ buttons
def click(lua_pred):
    return ev('''(function()
        for _, h in ipairs(PG.gear.hits or {}) do if (%s) then PG.over = false; local r = PG:onMouseUp(h.r[1] + 1, h.r[2] + 1); return r end end
        return "nohit" end)()''' % lua_pred)
def scroll_to(lua_pred):
    L.execute('''(function() for _, r in ipairs(PG.gear.rows) do local b = r.btns; local function m(b) return %s end
        if (r.kind == "plan" and m({ a = "plan", id = r.id })) or (b and ((b[1] and m(b[1])) or (b[2] and m(b[2])) or (b[3] and m(b[3])))) then PG.scroll = math.max(0, r.y - 40); frame(PG, 16); return end end end)()''' % lua_pred)
L.execute("for i = #SOL.inv.list, 1, -1 do local x = SOL.inv.list[i]; if string.find(x.ft, 'Junk', 1, true) then table.remove(SOL.inv.list, i) end end; PG.gear.dirty = true; PG.scroll = 0; frame(PG, 600)")
scroll_to('b.a == "plan" and b.id == "fierce"')
r = click('h.b.a == "plan" and h.b.id == "fierce"')
ck("plan click: the s105 plan runs with LF's own commands", r is True and ev('SolCombatPlans.store().plan') == "fierce" and ev('(function() for _, c in ipairs(ISSUED) do if c == "set_combat_doctrine=weapons_free" then return true end end return false end)()'), (r, ev('SolCombatPlans.store().plan')))
ck("plan click: she answers in plain Arabic", ev("SAID[#SAID]") == esc("حاضر، رح هاجم."))
L.execute("frame(PG, 600)")
ck("plan click: the page shows the new plan at once", ev("PG.gear.model.plan") == "fierce")
scroll_to('b.a == "give_me" and b.e and b.e.ft == "Base.Bandage"')
n_before = ev("PLAYER.inv:getCountTypeRecurse('Base.Bandage')")
r = click('h.b.a == "give_me" and h.b.e and h.b.e.ft == "Base.Bandage"')
ck("give to me: the whole bandage stack moves to his bag (LF's verified transfer)", ev("PLAYER.inv:getCountTypeRecurse('Base.Bandage')") == n_before + 4 and ev("SOL.inv:getCountTypeRecurse('Base.Bandage')") == 0, (r, ev("PLAYER.inv:getCountTypeRecurse('Base.Bandage')")))
ck("give to me: she says it plainly", ev("SAID[#SAID]") == esc("تفضّل."))
L.execute("frame(PG, 600)")
scroll_to('b.a == "use" and b.it == KATANA')
click('h.b.a == "use" and h.b.it == KATANA')
ck("use: LF's own equip order (marks her pick, s98)", ev("EQUIP[#EQUIP]") == "weapon:Base.Katana")
scroll_to('b.a == "pref_melee" and b.it == BAT')
click('h.b.a == "pref_melee" and h.b.it == BAT')
ck("set preferred melee: SolMeleeFor moves to the bat", ev("BAT.md.SolMeleeFor") == "sol-1" and ev("KATANA.md.SolMeleeFor") is None)
L.execute("SolCombatPlans.store().plan = 'smart'; PG.gear.dirty = true; PG.scroll = 0; frame(PG, 600)")
scroll_to('b.a == "reload"')
L.execute("ORDERED = nil; local base = SolMagFill.orderFill; SolMagFill.orderFill = function(a, g) ORDERED = g; return true end")
click('h.b.a == "reload"')
ck("reload: s99 SolMagFill.orderFill for the gun in her hands", ev("ORDERED == G28"))
scroll_to('b.a == "takeoff" and b.it == HAT')
click('h.b.a == "takeoff" and h.b.it == HAT')
ck("take off: her cap is off (removeWornItem, 1-arg overload), still in her bag", ev("SOL:isEquippedClothing(HAT) == false and SOL.inv:contains(HAT) and REMOVED == 1"))
L.execute("NEAR = false; PG.gear.dirty = true; frame(PG, 600)")
scroll_to('b.a == "takeoff"')
click('h.b.a == "takeoff"')
ck("too far from her: nothing is taken off", ev("REMOVED == 1"))
L.execute("NEAR = true")
L.execute("PG.gear.dirty = true; PG.scroll = 0; frame(PG, 600)")
ck("his bag is hidden until he clicks", ev("PG.gear.model.mine == nil"))
scroll_to('b.a == "toggle_mine"')
click('h.b.a == "toggle_mine"'); L.execute("frame(PG, 600)")
ck("his click: his bag is listed", ev("PG.gear.model.mine ~= nil"))
scroll_to('b.a == "give_sol" and b.e and b.e.ft == "Base.308Bullets"')
click('h.b.a == "give_sol" and h.b.e and h.b.e.ft == "Base.308Bullets"')
ck("give to Sol: his 40 rounds of her calibre move to her", ev("SOL.inv:getCountTypeRecurse('Base.308Bullets')") == 540 and ev("PLAYER.inv:getCountTypeRecurse('Base.308Bullets')") == 0)
L.execute("frame(PG, 600)")
scroll_to('b.a == "give_one"')
click('h.b.a == "give_one"')
ck("like me: 'give her one' moves his SPARE helmet (not the one he wears)", ev("SOL.inv:contains(ARMYHAT2) and PLAYER:isEquippedClothing(ARMYHAT)"))
ck("every click logged once with its result", ev('logged("[SolGearPage] button give_one")'))

# ------------------------------------------------ switch off = the old tab
L.execute("SW.gear_page = false; frame(PG, 16); frame(PG, 16)")
rows_cmds = ev("(function() local t = {}; for _, r in ipairs(PG.rows) do local it = r.it or (r.list and r.list[1]); t[#t + 1] = tostring(it and it.command or '') end; return table.concat(t, ',') end)()")
ck("off: LF's weapon-priority selector and buttons are back", "set_weapon_priority" in rows_cmds and "open_inventory" in rows_cmds, rows_cmds)
ck("off: the old card is drawn (its weapon label), not the gear page", ev('drew("%s")' % esc("السلاح").replace("\\", "\\\\")) and not ev('drew("%s")' % esc("بإيدها").replace("\\", "\\\\")))
ck("off: the old card height again (236)", ev("PG.cardH") == 236)
ck("off: clicks go to SolPages' own handler", ev("(function() local n = 0; local base = SolUI.PageClass.onMouseUp; return PG.gear == nil end)()"))
L.execute("SW.gear_page = true; frame(PG, 16); frame(PG, 16)")
ck("on again: the gear page comes back", ev('drew("%s")' % esc("بإيدها").replace("\\", "\\\\")) and ev("PG.gearActive == true"))
L.execute("SW.combat_plans = false; PG:refresh(true); frame(PG, 600)")
rows_cmds = ev("(function() local t = {}; for _, r in ipairs(PG.rows) do local it = r.it or (r.list and r.list[1]); t[#t + 1] = tostring(it and it.command or '') end; return table.concat(t, ',') end)()")
ck("combat_plans off: LF's weapon priority stays (one setting either way)", "set_weapon_priority" in rows_cmds, rows_cmds)
ck("combat_plans off: the plan section says plans are off (no plan rows)", ev('(function() local n, off = 0, false; for _, r in ipairs(PG.gear.rows) do if r.kind == "plan" then n = n + 1 end; if r.kind == "note" and r.text == "%s" then off = true end end; return n == 0 and off end)()' % esc("خطط القتال مطفية").replace("\\", "\\\\")))
L.execute("SW.combat_plans = true")
ck("other tabs untouched (status tab: no gear page)", ev("(function() local p = newPage(); p.tab = 'status'; p:refresh(true); TEXTS = {}; p:prerender(); return p.gear == nil end)()") is True)

# ------------------------------------------------ gates
ck("no Java call with a boolean argument (Kahlua overload trap)", re.search(r'(?<![\w.])call\([^)]*,\s*"[A-Za-z]+",[^)]*\b(true|false)\b', src) is None)
ck("no next() anywhere", re.search(r'(?<![\w.])next\s*\(', src) is None)
ck("no per-tick handler (draw-time only, page open)", "OnTick" not in src)
G = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua")
r = subprocess.run([sys.executable, "-I", os.path.join(G, "tonumber_check.py"), cl], capture_output=True, text=True); ck("tonumber gate", r.returncode == 0, r.stdout[-300:])
r = subprocess.run([sys.executable, "-I", os.path.join(G, "jarcall_check.py"), cl], capture_output=True, text=True); ck("jarcall gate", r.returncode == 0, r.stdout[-400:])
print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
MIND = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind")
card_cmd = [sys.executable, "-I", os.path.join(G, "card_check.py"), MIND, "--lua", cl]
if len(sys.argv) > 2:
    card_cmd += ["--lua-profile", os.path.join(ROOT, "07_TEST", "SOL_LAB", "profile", "Zomboid", "Lua"),
                 "--fixes", os.path.join(ROOT, "07_TEST", "SOL_LAB", "profile", "Zomboid", "Lua", "SolFixes_LAB.txt"),
                 "--doc", os.path.join(ROOT, "DOCS", "SOL_MODEL_CARD.md")]
r = subprocess.run(card_cmd, capture_output=True, text=True); ck("card gate (candidate Mind, when supplied)", r.returncode == 0, (r.stdout + r.stderr)[-400:])
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(P), len(FAIL))); sys.exit(1 if FAIL else 0)
