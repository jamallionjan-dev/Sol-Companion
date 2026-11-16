"""Offline tests for secret_loadout (SolSecretLoadout.lua + apply_s74_secret_loadout.py + fold_secret_loadout.py).
EFZ's own Builds/Core/Data are loaded READ-ONLY from the Workshop folder (real build codes, real presets, real magazine capacities);
only the Java side (items, containers, TWRuntime.read/applyTree) is stubbed, the stub doing what Runtime.lua:798 does.
usage: python test_secret_loadout.py"""
import glob, os, shutil, subprocess, sys, tempfile
from lupa import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
LAB = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid"
CLIENT = LAB + r"\mods\Sol_LAB\42\media\lua\client"
EFZ = r"C:/Program Files (x86)/Steam/steamapps/workshop/content/108600/3824755284/mods/EscapeFromZomboidFirearms/42/media/lua/shared/"
ok_n = bad = 0
def check(name, ok, info=""):
    global ok_n, bad
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  " + str(info)[:400])); ok_n += bool(ok); bad += (not ok)

STUBS = r"""
NOW = 1000; function getTimestampMs() return NOW end
SWITCH = true
SolAuthority = { on = function(n) return n == "secret_loadout" and SWITCH end }
FILES = {}
function jl(t) return { size = function() return #t end, get = function(_, i) return t[i + 1] end } end
function getFileReader(name, create)
    local text = FILES[name]; if text == nil then return nil end
    local lines = {}; for l in string.gmatch(text, "([^\n]*)\n") do lines[#lines + 1] = l end
    local i = 0
    return { readLine = function() i = i + 1; return lines[i] end, close = function() end }
end
WRITES = 0
function getFileWriter(name, create, append)
    local buf = {}
    return { write = function(_, s) buf[#buf + 1] = s end, close = function() FILES[name] = table.concat(buf); WRITES = WRITES + 1 end }
end
TWAmmoEnumFor = function(r) return "ENUM:" .. r end
package.path = EFZ_DIR .. "?.lua"
local C = require("TW/Core"); local D = C.data
EFZC, EFZD = C, D
-- item stubs
META = {}
local IM = {}
IM.__index = IM
function IM:getFullType() return self.t end
function IM:getDisplayName() return self.name or self.t end
function IM:getModData() return self.md end
function IM:isRanged() return self.ranged == true end
function IM:getMaxAmmo() return self.maxAmmo or 0 end
function IM:setMaxAmmo(n) self.maxAmmo = n end
function IM:getCurrentAmmoCount() return self.ammo or 0 end
function IM:setCurrentAmmoCount(n) self.ammo = n end
function IM:haveChamber() return self.chamber == true end
function IM:setRoundChambered(b) self.chambered = b end
function IM:isRoundChambered() return self.chambered == true end
function IM:getMagazineType() return self.mag end
function IM:setMagazineType(m) self.mag = m end
function IM:setContainsClip(b) self.clip = b end
function IM:isContainsClip() return self.clip == true end
function IM:getAllWeaponParts() return jl(self.parts) end
function IM:attachWeaponPart(p, b) self.parts[#self.parts + 1] = p end
function IM:getFireMode() return self.fire end
function IM:setFireMode(m) self.fire = m end
function IM:setAmmoType(e) self.ammoType = e end
function IM:getAmmoType() return self.ammoTypeObj end
function IM:getWeight() return self.w or 0.1 end
UNKNOWN = {}
function instanceItem(t)
    if UNKNOWN[t] then return nil end
    local m = META[t] or {}
    local it = setmetatable({ t = t, md = {}, parts = {}, cls = m.cls, ranged = m.ranged, maxAmmo = m.maxAmmo, chamber = m.chamber, name = m.name, w = m.w, mag = m.mag }, IM)
    local key = D.byType[t]
    if key then it.cls, it.ranged, it.chamber, it.w = "HandWeapon", true, true, 3.0 end
    local meta = D.types[t]
    if meta and C.isClip(meta.tpl) then it.maxAmmo, it.w = D.items[meta.tpl].capacity, 0.2 end
    if string.find(t, "%.A_") or string.find(t, "Bullets") then it.w = 0.012 end
    return it
end
function instanceof(o, cls) return type(o) == "table" and (o.cls == cls or (cls == "InventoryItem" and o.t ~= nil)) end
function container()
    local c = { items = {} }
    function c:getItems() return jl(self.items) end
    function c:AddItem(x) if type(x) == "string" then x = instanceItem(x) end; self.items[#self.items + 1] = x; return x end
    function c:AddItems(t, n) local out = {}; for i = 1, n do out[i] = self:AddItem(t) end; return jl(out) end
    function c:getCapacityWeight() local s = 0; for _, it in ipairs(self.items) do s = s + (it.w or 0.1) end; return s end
    return c
end
function count(c, t) local n = 0; for _, it in ipairs(c.items) do if it.t == t then n = n + 1 end end; return n end
-- TWRuntime stub: R.key / R.read / R.applyTree as Runtime.lua:21, :60, :798 (parts by TWPath, the magazine inserted empty)
TWRuntime = {}
function TWRuntime.key(w) return D.byType[w:getFullType()] end
function TWRuntime.read(w) return C.copy and C.copy(w.tree or {}) or w.tree end
function TWRuntime.applyTree(w, tree)
    local key = TWRuntime.key(w); if not key then return false, "invalidItem" end
    local ok, why = C.validate(key, tree); if not ok then return false, why end
    w.parts, w.tree = {}, {}
    for path, tpl in pairs(tree) do
        w.tree[path] = tpl
        if not C.isClip(tpl) then local p = instanceItem(D.items[tpl].pz); p.md.TWPath = path; p.name = D.items[tpl].pz; w.parts[#w.parts + 1] = p end
    end
    table.sort(w.parts, function(a, b) return a.md.TWPath < b.md.TWPath end)
    w.ammo, w.chambered, w.md.AmmoList = 0, false, nil
    if C.isClip(tree.mod_magazine) then w.mag = C.clipType(key, tree.mod_magazine); w.maxAmmo = D.items[tree.mod_magazine].capacity; w.clip = true
    else w.clip = false end
    return true
end
-- people
function person(maxW) local p = { inv = container(), att = {}, maxW = maxW or 50 }
    function p:getInventory() return self.inv end
    function p:getPrimaryHandItem() return self.p end
    function p:getSecondaryHandItem() return self.s end
    function p:getAttachedItems() return jl(self.att) end
    function p:getMaxWeight() return self.maxW end
    return p end
function attached(item, loc) return { getItem = function() return item end, getLocation = function() return loc end } end
JAMAL = person(); SOL = person(50)
function getSpecificPlayer(i) return JAMAL end
SolUI = { solActor = function() return SOL end, runAction = function(id, o) return false, "base" end }
Events = nil
-- his two weapons: an EFZ M4A1 (SpecOps preset, loaded with a non-default round) and a M1911A1 on the back
function efzWeapon(key, preset)
    local w = instanceItem(D.weapons[key].pz)
    assert(TWRuntime.applyTree(w, C.presetTree(key, preset)))
    return w
end
"""

# Kahlua-faithful tonumber (05_TOOLS/sol_kahlua/kahlua_shim.lua): tonumber(f()) with f returning 2 values raises here as in the game
SHIM = open(os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "kahlua_shim.lua"), encoding="ascii").read()
RUNTIMES = []

def runtime(extra="", module_src=None):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(SHIM)
    RUNTIMES.append(L)
    L.execute('EFZ_DIR = [[%s]]' % EFZ)
    L.execute(STUBS)
    L.execute(open(os.path.join(HERE, "SolSecretLoadoutData.lua"), encoding="ascii").read())
    L.execute(module_src if module_src is not None else open(os.path.join(HERE, "SolSecretLoadout.lua"), encoding="ascii").read())
    L.execute("SolSecretLoadout.install()")
    if extra: L.execute(extra)
    return L

src = open(os.path.join(HERE, "SolSecretLoadout.lua"), encoding="ascii").read()
check("SolSecretLoadout.lua is ASCII only and compiles", all(ord(c) < 128 for c in src) and not isinstance(lua51.LuaRuntime().eval("loadstring")(src), tuple))
check("no ModData anywhere in it (her death wipe works on ModData and forget hooks)", "ModData." not in src and "getOrCreate" not in src)

L = runtime()
presets = L.eval("(function() local t = {} for n in pairs(EFZD.weapons.M4A1.presets or {}) do t[#t+1] = n end table.sort(t) return table.concat(t, ',') end)()")
L.execute("""
PRESET = nil
for _, n in ipairs({ "M4A1_SpecOps", "M4A1_LVOA" }) do if pcall(EFZC.presetTree, "M4A1", n) and EFZC.presetTree("M4A1", n) then PRESET = n break end end
M4 = efzWeapon("M4A1", PRESET); M4.md.AmmoList = { "EscapeFromZomboidFirearms.A_54527ac44bdc2d36668b4567" }; M4.fire = "Auto"
COLT = efzWeapon("M1911A1")
""")
check("EFZ data loaded read-only, an M4A1 preset with parts", L.eval("#M4.parts") >= 8, (presets, L.eval("PRESET")))

# 1 nothing captured yet
r = L.eval("{ SolUI.runAction('sol_secret', 'give') }")
check("no capture yet: she answers 'none' and puts nothing in her bag", r[1] is False and r[2] == "none" and L.eval("#SOL.inv.items") == 0, (r[1], r[2]))
check("other actions still reach the base bridge", L.eval("select(2, SolUI.runAction('sol_sort', 'run'))") == "base")
# 2 one firearm only: no capture
L.execute("JAMAL.p = M4; NOW = 5000; SolSecretLoadout.tick()")
check("one firearm in hand: nothing captured", L.eval("FILES['Sol_SecretLoadout.txt'] == nil and SolSecretLoadout._cache == nil"))
# 3 two: hand + back slot, three spare M4 magazines in his bag
L.execute("""
JAMAL.att = { attached(COLT, "Holster Right") }
for i = 1, 3 do JAMAL.inv:AddItem(M4.mag) end
NOW = 9000; SolSecretLoadout.tick()
""")
txt = L.eval("FILES['Sol_SecretLoadout.txt']") or ""
check("two firearms (hand + holster): captured once, silently, to Sol_SecretLoadout.txt", "w1.type=EscapeFromZomboidFirearms.M4A1" in txt and "w2.type=EscapeFromZomboidFirearms.M1911A1" in txt and L.eval("WRITES") == 1, txt[:300])
check("the EFZ build code is EFZ's own (TWB2) and round-trips to the same tree", "w1.code=TWB2|M4A1|" in txt and
      L.eval("(function() local _, t = require('TW/Builds').decode(SolSecretLoadout._cache[1].code) return EFZC.equalTrees(t, M4.tree) end)()") is True)
check("round captured from what is in the gun (AmmoList), spare mags counted (3)", "w1.round=EscapeFromZomboidFirearms.A_54527ac44bdc2d36668b4567" in txt and "w1.spare=3" in txt)
check("the colt's round comes from EFZ's weapon data when the gun is empty", "w2.round=" + L.eval("EFZD.weapons.M1911A1.ammo") in txt)
check("where each was: hand / Holster Right", "w1.where=hand" in txt and "w2.where=Holster Right" in txt)
L.execute("NOW = 20000; SolSecretLoadout.tick()")
check("captured once: no second write", L.eval("WRITES") == 1)

# 4 give
r = L.eval("{ SolUI.runAction('sol_secret', 'give') }")
check("give: ok, two weapons, not heavy", r[1] is True and r[2].startswith("given:2;missed=0;heavy=0"), r[2])
ws = L.eval("(function() local o = {} for _, it in ipairs(SOL.inv.items) do if it.cls == 'HandWeapon' then o[#o+1] = it end end return o end)()")
check("her bag: one M4A1 and one M1911A1 (exact types)", L.eval("count(SOL.inv, 'EscapeFromZomboidFirearms.M4A1')") == 1 and L.eval("count(SOL.inv, 'EscapeFromZomboidFirearms.M1911A1')") == 1)
L.execute("for _, it in ipairs(SOL.inv.items) do if it.t == M4.t then GM4 = it elseif it.t == COLT.t then GCOLT = it end end")
check("copies carry the same build tree as his (every part, same slot)", L.eval("EFZC.equalTrees(GM4.tree, M4.tree) and EFZC.equalTrees(GCOLT.tree, COLT.tree)") is True)
check("same parts by item type", L.eval("(function() local a, b = {}, {} for _, p in ipairs(GM4.parts) do a[#a+1] = p.t end for _, p in ipairs(M4.parts) do b[#b+1] = p.t end table.sort(a) table.sort(b) return table.concat(a, ',') == table.concat(b, ',') end)()") is True)
cap = L.eval("GM4.maxAmmo")
check("magazine full and a round chambered (M4: %s + 1)" % cap, cap and L.eval("GM4.ammo") == cap and L.eval("GM4.chambered") is True and L.eval("#GM4.md.AmmoList") == cap + 1)
check("the rounds in it are his round, AmmoType set (TWAmmoEnumFor)", L.eval("GM4.md.AmmoList[1]") == "EscapeFromZomboidFirearms.A_54527ac44bdc2d36668b4567" and L.eval("GM4.ammoType") == "ENUM:EscapeFromZomboidFirearms.A_54527ac44bdc2d36668b4567")
check("fire mode copied", L.eval("GM4.fire") == "Auto")
check("3 spare M4 magazines, each full", L.eval("count(SOL.inv, M4.mag)") == 3 and L.eval("(function() for _, it in ipairs(SOL.inv.items) do if it.t == M4.mag and it.ammo ~= it.maxAmmo then return false end end return true end)()") is True)
r556 = L.eval("count(SOL.inv, 'EscapeFromZomboidFirearms.A_54527ac44bdc2d36668b4567')")
r45 = L.eval("count(SOL.inv, EFZD.weapons.M1911A1.ammo)")
check("500 rounds per weapon of its own round (M4: %d, colt: %d)" % (r556, r45), r556 == 500 and r45 == 500)
check("his own weapons untouched", L.eval("JAMAL.p == M4 and M4.ammo == 0 and #JAMAL.inv.items == 3") is True)

# 5 overweight
L.execute("SOL.inv = container(); SOL.maxW = 5")
r = L.eval("{ SolUI.runAction('sol_secret', 'give') }")
check("overweight: still added, the answer says heavy=1", r[1] is True and "heavy=1" in r[2] and L.eval("count(SOL.inv, 'EscapeFromZomboidFirearms.M4A1')") == 1, r[2])
HEAVY_REASON = r[2]
# 6 kept fixed: a new pair in his hands changes nothing
L.execute("""
SolSecretLoadout._cache = nil
local mp5 = efzWeapon("MP5"); JAMAL.p = mp5; JAMAL.att = { attached(efzWeapon("M590A1"), "Back") }
NOW = 40000; SolSecretLoadout.tick(); KEEP = { SolSecretLoadout.capture() }
""")
check("fixed once captured: the file is never rewritten, the old pair stays", L.eval("WRITES") == 1 and L.eval("SolSecretLoadout.loadout()[1].type") == "EscapeFromZomboidFirearms.M4A1")
# 7 shipped data comes first
L.execute("""
SolSecretLoadoutData.lines = { "v=1", "w1.type=EscapeFromZomboidFirearms.MP5", "w1.code=" .. require('TW/Builds').encode("MP5", EFZC.presetTree("MP5"), ""), "w1.round=Base.Bullets9mm",
  "w2.type=EscapeFromZomboidFirearms.M590A1", "w2.code=" .. require('TW/Builds').encode("M590A1", EFZC.presetTree("M590A1"), ""), "w2.round=Base.ShotgunShells" }
SolSecretLoadout._cache = nil
""")
check("the shipped data file wins over the captured file", L.eval("select(2, SolSecretLoadout.loadout())") == "shipped" and L.eval("SolSecretLoadout.loadout()[1].type") == "EscapeFromZomboidFirearms.MP5")
L.execute("SolSecretLoadoutData.lines = {}; SolSecretLoadout._cache = nil")
# 8 switch off: looks like nothing
L.execute("SWITCH = false")
check("switch off: 'none', nothing given", L.eval("select(2, SolUI.runAction('sol_secret', 'give'))") == "none")
L.execute("SWITCH = true")
# 9 a vanilla gun (not EFZ): parts one by one through attachWeaponPart
L2 = runtime("""
META["Base.AssaultRifle"] = { cls = "HandWeapon", ranged = true, maxAmmo = 30, chamber = true, mag = "Base.556Clip", name = "M16 Assault Rifle" }
META["Base.Pistol"] = { cls = "HandWeapon", ranged = true, maxAmmo = 15, chamber = true, mag = "Base.9mmClip", name = "M9 Pistol" }
META["Base.556Clip"] = { maxAmmo = 30, name = "5.56 Magazine" }
local ar = instanceItem("Base.AssaultRifle"); ar:attachWeaponPart(instanceItem("Base.x4Scope")); ar:attachWeaponPart(instanceItem("Base.Laser"))
ar.ammoTypeObj = { getItemKey = function() return "Base.556Bullets" end }
local pi = instanceItem("Base.Pistol"); pi.ammoTypeObj = { getItemKey = function() return "Base.Bullets9mm" end }
JAMAL.p, JAMAL.s = ar, pi
NOW = 9000; SolSecretLoadout.tick()
G = { SolUI.runAction('sol_secret', 'give') }
for _, it in ipairs(SOL.inv.items) do if it.t == "Base.AssaultRifle" then GAR = it end end
""")
check("vanilla gun: captured with its parts and round (AmmoType item key)", "w1.parts=Base.x4Scope,Base.Laser" in (L2.eval("FILES['Sol_SecretLoadout.txt']") or "") and "w1.round=Base.556Bullets" in L2.eval("FILES['Sol_SecretLoadout.txt']"))
check("vanilla gun: copy has scope + laser, clip in, 30 + 1, 500 rounds", L2.eval("G[1]") is True and L2.eval("#GAR.parts") == 2 and L2.eval("GAR.clip") is True and L2.eval("GAR.ammo") == 30 and L2.eval("GAR.chambered") is True and L2.eval("count(SOL.inv, 'Base.556Bullets')") == 500)
# 10 an item type gone from the game: the other one still comes, reason says missed=1
L3 = runtime("""
FILES['Sol_SecretLoadout.txt'] = "v=1\\nw1.type=Gone.Gun\\nw1.round=Base.Bullets9mm\\nw2.type=EscapeFromZomboidFirearms.M1911A1\\nw2.code=" .. require('TW/Builds').encode("M1911A1", EFZC.presetTree("M1911A1"), "") .. "\\nw2.round=Base.Bullets45\\n"
UNKNOWN["Gone.Gun"] = true
G = { SolUI.runAction('sol_secret', 'give') }
""")
check("a weapon type missing: one given, missed=1", L3.eval("G[1]") is True and L3.eval("G[2]").startswith("given:1;missed=1"), L3.eval("G[2]"))
ONE_REASON = L3.eval("G[2]")

# 11 survives her death: the lab's real SolLife.checkIdentity with a new id (respawn)
T = tempfile.mkdtemp(prefix="sol_secret_")
cl, mind = os.path.join(T, "1", "2", "3", "4", "5", "6", "client"), os.path.join(T, "mind")
os.makedirs(cl); os.makedirs(mind); os.makedirs(os.path.join(T, "1", "Lua"))
for f in ("SolAuthority.lua", "SolLife.lua"): shutil.copy(os.path.join(CLIENT, f), cl)                  # read only: copied, never written
shutil.copy(LAB + r"\Lua\SolFixes_LAB.txt", os.path.join(T, "1", "Lua"))
for f in glob.glob(r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind\*.py"): shutil.copy(f, mind)
def apply(*args): return subprocess.run([sys.executable, os.path.join(HERE, "apply_s74_secret_loadout.py")] + list(args), capture_output=True, text=True)
L.execute("""
STORES = {}
ModData = { getOrCreate = function(k) STORES[k] = STORES[k] or {}; return STORES[k] end, transmit = function() end }
SolBudget = { register = function() end }
package.loaded["SolBudget"] = true
SurvivorCompanion = { GameplayUtil = { idOf = function(a) return a.id end } }
FORGOT = 0; solAddressBookForget = function() FORGOT = FORGOT + 1 end; solFarmForget = solAddressBookForget; solStationsForget = solAddressBookForget
""")
r1 = apply(cl, mind)
L.execute(open(os.path.join(cl, "SolLife.lua"), encoding="utf-8").read())
before = L.eval("FILES['Sol_SecretLoadout.txt']")
L.execute("SOL.id = 'sol-1'; SolLife.checkIdentity(); SOL = person(50); SOL.id = 'sol-2'; DIED = SolLife.checkIdentity()")
check("respawn seen by SolLife (death 1, her places forgotten)", L.eval("DIED") is True and L.eval("STORES.Sol_Life.deaths") == 1 and L.eval("FORGOT") == 3)
r = L.eval("{ SolUI.runAction('sol_secret', 'give') }")
check("after her death the new Sol still knows it: file unchanged, both weapons in her new bag", L.eval("FILES['Sol_SecretLoadout.txt']") == before and r[1] is True and r[2].startswith("given:2")
      and L.eval("count(SOL.inv, 'EscapeFromZomboidFirearms.M4A1')") == 1, r[2])

# 12 installer, twice, on copies
r2 = apply(cl, mind)
check("installer runs, twice, on copies", r1.returncode == 0 and r2.returncode == 0, (r1.stderr[-400:], r2.stderr[-400:]))
auth = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read()
life = open(os.path.join(cl, "SolLife.lua"), encoding="utf-8").read()
check("switch once, keep note in the death wipe once, secret_loadout=on once", auth.count('"secret_loadout"') == 1 and life.count("secret_loadout is kept on purpose") == 1
      and open(os.path.join(T, "1", "Lua", "SolFixes_LAB.txt"), encoding="utf-8").read().count("secret_loadout=") == 1)
shared = os.path.join(T, "1", "2", "3", "4", "5", "6", "shared", "SolSecretLoadoutData.lua")
check("data file installed into media/lua/shared", os.path.exists(shared))
for f in ("SolSecretLoadout.lua", "SolAuthority.lua", "SolLife.lua"):
    check("compiles " + f, not isinstance(lua51.LuaRuntime().eval("loadstring")(open(os.path.join(cl, f), encoding="utf-8").read()), tuple))
# fold: captured file -> shipped data, and an empty staged file never overwrites it
cap = os.path.join(T, "Sol_SecretLoadout.txt")
open(cap, "w", encoding="utf-8").write(before)
stage = os.path.join(T, "stage"); shutil.copytree(HERE, stage, ignore=shutil.ignore_patterns("__pycache__", "place_fixtures", "src", "speech_tr", "*.png"))
rf = subprocess.run([sys.executable, os.path.join(stage, "fold_secret_loadout.py"), cap, cl], capture_output=True, text=True, encoding="utf-8")
check("fold: prints both weapons with their parts and writes the shipped file", rf.returncode == 0 and "M4A1" in rf.stdout and "M1911A1" in rf.stdout and '"w1.type=' in open(shared, encoding="ascii").read(), rf.stdout[-300:] + rf.stderr[-300:])
L4 = runtime()
L4.execute(open(shared, encoding="ascii").read())
L4.execute("SolSecretLoadout._cache = nil")
check("folded data loads in Lua and is the shipped source", L4.eval("select(2, SolSecretLoadout.loadout())") == "shipped" and L4.eval("SolSecretLoadout.loadout()[2].type") == "EscapeFromZomboidFirearms.M1911A1")
r3 = apply(cl, mind)
check("re-running the installer with the empty staged data file keeps the folded one", r3.returncode == 0 and '"w1.type=' in open(shared, encoding="ascii").read())

# 13 the Mind
code = r"""
import sys, json; sys.path.insert(0, sys.argv[1]); import chat_service as CS, farm_talk as FT, model_router as MR, intent_engine as IE
cases = {"عطيني سلاحي السري": 1, "اعطيني سلاحي السري": 1, "أعطيني سلاحي السرّي": 1, "جيبيلي سلاحي السري": 1, "هاتي أسلحتي السرية": 1,
         "بدي السلاحين السريين": 1, "سول عطيني سلاحي السري هلأ": 1, "عطيني سلاحي": 0, "عطيني كل شي": 0, "رتبي الاغراض": 0, "السر بيناتنا": 0}
for t, want in cases.items():
    got = [x for x in CS.action_intents(CS._shami(t)) if x[0] == "sol_secret"]
    ok = (got == [("sol_secret", "give")]) if want else got == []
    if want and (FT.order(t) is not None or IE.parse_high_confidence(t) is not None): ok = False
    if want and [n for n, a in CS.intents(t) if n != "action"]: ok = False
    print(("OK " if ok else "BAD ") + t, got)
print("CARD", "secret_loadout" in MR.COMMANDS and MR.COMMANDS["secret_loadout"][1] == "عطيني سلاحي السري" and not any("احفظ" in str(v) for v in MR.COMMANDS.values())
      and sum(1 for k in MR.COMMANDS if "secret" in k) == 1)
sheet = MR.sheet([], "")
print("SHEET", "secret_loadout" in sheet and sheet.count("سلاحي السري") >= 2)
print("ROUTE", [CS.action_intents(CS._shami(MR.COMMANDS["secret_loadout"][1]))])
for r in ({"ok": True, "reason": "given:2;missed=0;heavy=0;rounds=1000"}, {"ok": True, "reason": sys.argv[2]}, {"ok": True, "reason": sys.argv[3]},
          {"ok": False, "reason": "none"}, {"ok": False, "reason": "no_sol"}, {"ok": False, "reason": "failed"}, {"ok": None, "reason": "sent"}):
    print("LINE", json.dumps(CS.secret_reply(r), ensure_ascii=False))
"""
rm = subprocess.run([sys.executable, "-c", code, mind, HEAVY_REASON, ONE_REASON], capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
out = rm.stdout
check("Mind: the secret phrase and its synonyms -> sol_secret give, nothing else grabs them", rm.returncode == 0 and "BAD" not in out and out.count("OK ") == 11, out + rm.stderr[-600:])
check("Mind: one card action secret_loadout, no save phrase anywhere", "CARD True" in out and "SHEET True" in out)
check("Mind: the card's phrase routes to the game action", "('sol_secret', 'give')" in out)
lines = [l[5:].strip().strip('"') for l in out.splitlines() if l.startswith("LINE ")]
print("  lines:", *lines, sep="\n    ")
check("Mind: given -> 'تكرم، السلاحين معي.'", lines and lines[0] == "تكرم، السلاحين معي.")
check("Mind: overweight -> said once in the same line", len(lines) > 1 and lines[1].startswith("تكرم، السلاحين معي.") and lines[1].count("تقيل") == 1)
check("Mind: one of two -> says so", len(lines) > 2 and "واحد" in lines[2])
check("Mind: nothing captured yet -> 'مش لاقية شي بهالاسم هلأ.'", len(lines) > 3 and lines[3] == "مش لاقية شي بهالاسم هلأ.")
check("Mind: no system words in her lines", all(not any(w in l.lower() for w in ("loadout", "efz", "sol_", "switch", "mod", "file", "capture", "ملف", "سويتش")) for l in lines))
r4 = apply("-", mind)
check("Mind side idempotent (third run)", r4.returncode == 0 and open(os.path.join(mind, "chat_service.py"), encoding="utf-8").read().count("def secret_reply") == 1
      and open(os.path.join(mind, "model_router.py"), encoding="utf-8").read().count('"secret_loadout": (') == 1)
shutil.rmtree(T, ignore_errors=True)
# Kahlua shim: no tonumber call in any runtime above was refused (a pcall inside the module would hide the error otherwise)
hits = sum(int(R.eval("KAHLUA_SHIM_HITS")) for R in RUNTIMES)
check("kahlua shim: no Kahlua-unsafe tonumber call in any run (%d runtimes)" % len(RUNTIMES), hits == 0, [R.eval("KAHLUA_SHIM_LAST") for R in RUNTIMES if R.eval("KAHLUA_SHIM_HITS")][:2])
# and the shim does catch the 2026-11-10 crash: the two-value call() + tonumber(call(w, "getMaxAmmo")) of the first install
import re as _re
old_src = _re.sub(r"tonumber\(\((call\([^()]*\))\)\)", lambda m: "tonumber(" + m.group(1) + ")", src)
old_src = old_src.replace("local ok, a = pcall(f, o, ...)", "local ok, a, b = pcall(f, o, ...)").replace("if ok then return a end", "if ok then return a, b end", 1)
LO = runtime(module_src=old_src)
LO.execute("""
M4 = efzWeapon("M4A1"); COLT = efzWeapon("M1911A1")
JAMAL.p = M4; JAMAL.att = { attached(COLT, "Holster Right") }
NOW = 9000; SolSecretLoadout.tick()
""")
okOld, why = LO.eval("(function() local r = { pcall(SolUI.runAction, 'sol_secret', 'give') } return r[1] and r[2] == true, tostring(r[3] or r[2]) end)()")
check("kahlua shim catches the old two-value call(): give fails or a tonumber call is refused", old_src != src and (not okOld or int(LO.eval("KAHLUA_SHIM_HITS")) > 0),
      (okOld, why, LO.eval("KAHLUA_SHIM_HITS")))
RUNTIMES.remove(LO)
print("RESULT", ok_n, "/", ok_n + bad)
sys.exit(1 if bad else 0)
