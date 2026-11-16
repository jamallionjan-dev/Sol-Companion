"""s156 offline: SolWardrobe's logic in the Kahlua stand-in with a faked game: the catalog built in slices, the parts,
sorting and search, and the trial / take back / apply rules on a faked Sol. The window's drawing and the 3D preview are the
game's and are NOT exercised here. Offline PASS is not Runtime PASS.
Run: python test_s156_wardrobe.py [client dir]"""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
tmp = tempfile.mkdtemp(prefix="s156_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
shutil.copy(os.path.join(CL, "SolAuthority.lua"), cl)
sw = os.path.join(tmp, "SolFixes_LAB.txt"); open(sw, "w", newline="").write("x=on\r\n")
ap = os.path.join(HERE, "apply_s156_wardrobe.py")
r1 = subprocess.run([sys.executable, ap, cl, sw], capture_output=True, text=True)
snap = {f: open(os.path.join(cl, f), "rb").read() for f in os.listdir(cl)}
r2 = subprocess.run([sys.executable, ap, cl, sw], capture_output=True, text=True)
ck("installer runs", r1.returncode == 0, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout and "copied" not in r2.stdout and snap == {f: open(os.path.join(cl, f), "rb").read() for f in os.listdir(cl)}, r2.stdout)
src = open(os.path.join(cl, "SolWardrobe.lua"), encoding="utf-8", newline="").read()
ck("SolWardrobe.lua is ASCII", all(ord(c) < 128 for c in src))
ck("Arabic text is \\\\uXXXX escapes", "\\\\u062E" in src and "خ" not in src)
ck("switch registered and enabled once", '"wardrobe"' in open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read() and open(sw).read().count("wardrobe=on") == 1)
tn = subprocess.run([sys.executable, "-I", os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py"), cl], capture_output=True, text=True)
ck("tonumber gate", tn.returncode == 0, tn.stdout + tn.stderr)

FAKES = r"""
CLOCK = 0
getTimestampMs = function() CLOCK = CLOCK + 0.01; return CLOCK end
SWITCH = true
SolAuthority = { on = function(n) return n == "wardrobe" and SWITCH end }
SolText = { drawLine = function() end, width = function(s) return #tostring(s) * 8 end }
SolTheme = { c = {}, panel = function() end, rounded = function() end }
ISPanel = { derive = function(self, name) local c = {}; c.__index = c; return c end, new = function() return {} end }
ISUI3DModel, ISTextEntryBox = {}, {}
local realRequire = require
require = function(n) return true end
PAGE = {}; PAGE.__index = PAGE
function PAGE:refresh(force, follow) self.refreshed = (self.refreshed or 0) + 1 end
SolUI = { lang = function() return LANG or "ar" end, PageClass = PAGE,
          pageTabs = function() return { { id = "status" }, { id = "skills", sol = true }, { id = "orders" } } end,
          solActor = function() return SOL end }
function jlist(t) return { size = function() return #t end, get = function(_, i) return t[i + 1] end } end
function script(full, name, loc, ci, flags)
  flags = flags or {}
  return { getFullName = function() return full end, getDisplayName = function() return name end,
           getBodyLocation = function() return loc end, getClothingItem = function() return ci end,
           getObsolete = function() return flags.obsolete == true end, isHidden = function() return flags.hidden == true end }
end
SCRIPTS = {}
getAllItems = function() return jlist(SCRIPTS) end
HAIR = {}
function style(name, nochoose) return { getName = function() return name end, isNoChoose = function() return nochoose == true end } end
getHairStylesInstance = function() return { getAllFemaleStyles = function() return jlist(HAIR) end } end
-- exclusive locations, like the game's BodyLocationGroup: a dress cannot be worn with a shirt or trousers
EXCL = { ["base:dress"] = { "base:tshirt", "base:pants", "base:skirt" }, ["base:tshirt"] = { "base:dress" }, ["base:pants"] = { "base:dress", "base:skirt" }, ["base:skirt"] = { "base:pants", "base:dress" } }
LOCOF = {}
function mkItem(full, loc) return { full = full, loc = loc, md = {}, getModData = function(self) return self.md end, getBodyLocation = function(self) return self.loc end,
  getDisplayName = function(self) return "N:" .. self.full end, getFullType = function(self) return self.full end } end
function mkSol()
  local a = { worn = {}, hair = "Long", resets = 0 }
  a.inv = { items = {} }
  function a.inv:AddItem(full) if LOCOF[full] == nil then return nil end local it = mkItem(full, LOCOF[full]); self.items[#self.items + 1] = it; return it end
  function a.inv:contains(it) for _, v in ipairs(self.items) do if v == it then return true end end return false end
  function a.inv:Remove(it) for i, v in ipairs(self.items) do if v == it then table.remove(self.items, i); return end end end
  function a:getInventory() return self.inv end
  function a:getWornItems() local w = self.worn
    return { size = function() return #w end, get = function(_, i) local e = w[i + 1]; return { getItem = function() return e.item end, getLocation = function() return e.loc end } end } end
  function a:removeWornItem(it) for i, e in ipairs(self.worn) do if e.item == it then table.remove(self.worn, i); return end end end
  function a:setWornItem(loc, it)
    if it.cursed then error("cannot wear") end
    for i = #self.worn, 1, -1 do
      local e = self.worn[i]; local out = e.loc == loc
      for _, x in ipairs(EXCL[loc] or {}) do if e.loc == x then out = true end end
      if out then table.remove(self.worn, i) end
    end
    self.worn[#self.worn + 1] = { item = it, loc = loc }
  end
  local hv = { getHairModel = function() return a.hair end, setHairModel = function(_, m) a.hair = m end }
  function a:getHumanVisual() return hv end
  function a:resetModelNextFrame() self.resets = self.resets + 1 end
  return a
end
function own(a, full, loc) LOCOF[full] = loc; local it = a.inv:AddItem(full); a:setWornItem(loc, it); return it end
function wornNames(a) local t = {}; for _, e in ipairs(a.worn) do t[#t + 1] = e.item.full end table.sort(t); return table.concat(t, ",") end
function bagCount(a) return #a.inv.items end
"""
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(FAKES)
L.execute(src)
ck("module loads", L.eval("SolWardrobe ~= nil and SolWardrobe.VERSION ~= nil"))

# ---- parts
cases = {"base:tshirt": "top", "base:shirt": "top", "base:shortsleeveshirt": "top", "base:tanktop": "top", "base:sweater": "top", "base:sweaterhat": "top",
         "base:jacket": "jacket", "base:jackethat": "jacket", "base:jacket_bulky": "jacket", "base:pants": "bottom", "base:shortpants": "bottom", "base:shortsshort": "bottom",
         "base:skirt": "bottom", "base:longskirt": "bottom", "base:legs1": "under", "base:torso1legs1": "under", "base:dress": "dress", "base:longdress": "dress", "base:fullsuit": "dress",
         "base:boilersuit": "dress", "base:bathrobe": "dress", "base:shoes": "shoes", "base:hat": "head", "base:fullhat": "head", "base:socks": "under",
         "base:hands": "hands", "base:scarf": "neck", "base:underwear_top": "under", "Base:TShirt": "top",
         "base:underwearbottom": "under", "base:torsoextravestbullet": "armor", "base:cuirass": "armor", "base:gorget": "armor", "base:shoulderpadleft": "armor",
         "base:sportshoulderpadontop": "armor", "base:calf_right": "armor", "base:thigh_left": "armor", "base:forearm_right": "armor", "base:knee_left": "armor",
         "base:elbow_right": "armor", "base:codpiece": "armor", "base:gaiter_left": "armor", "base:leftarm": "armor", "base:calf_left_texture": "armor",
         "base:torsoextravest": "vest", "base:torsoextra": "vest", "base:webbing": "vest", "base:vesttexture": "vest",
         "base:eyes": "face", "base:maskeyes": "face", "base:mask": "face", "base:maskfull": "face", "base:nose": "face", "base:ears": "face", "base:eartop": "face",
         "base:lefteye": "face", "base:scba": "face", "base:necklace": "neck", "base:necklace_long": "neck", "base:neck": "neck", "base:neck_texture": "neck",
         "base:leftwrist": "hands", "base:right_ringfinger": "hands", "base:handsleft": "hands", "base:belt": "belt", "base:beltextra": "belt",
         "base:fannypackfront": "belt", "base:satchel": "belt", "base:back": "belt", "base:bellybutton": "belt", "base:tail": "other", "mod:somethingnew": "other",
         "base:jersey": "top", "base:jacketsuit": "jacket", "base:jackethat_bulky": "jacket", "base:pants_skinny": "bottom", "base:pantsextra": "bottom",
         "base:fullsuithead": "dress", "base:fulltop": "dress", "base:ankleholster": None, "base:ammostrap": None, "base:bandage": None, "base:makeup_lips": None,
         "base:zeddmg": None, "base:wound": None, "": None}
bad = {k: (L.eval("SolWardrobe.slotOf(%r)" % k), v) for k, v in cases.items() if L.eval("SolWardrobe.slotOf(%r)" % k) != v}
ck("body locations go to the right part (%d cases)" % len(cases), not bad, bad)

# ---- catalog: 6000 scripts, sliced
L.execute("""
local locs = { "base:tshirt", "base:jacket", "base:pants", "base:skirt", "base:dress", "base:shoes", "base:hat", "base:socks" }
for i = 1, 6000 do
  local loc = locs[(i % #locs) + 1]
  SCRIPTS[#SCRIPTS + 1] = script("Mod.Item" .. i, string.char(65 + (i * 7) % 26) .. "name " .. i, loc, "CI" .. i)
end
SCRIPTS[#SCRIPTS + 1] = script("Base.Hammer", "Hammer", nil, nil)                       -- not clothing
SCRIPTS[#SCRIPTS + 1] = script("Base.Bag", "Bag", nil, "x")                             -- no body location
SCRIPTS[#SCRIPTS + 1] = script("Base.OldShirt", "Old", "base:tshirt", "x", { obsolete = true })
SCRIPTS[#SCRIPTS + 1] = script("Base.Hidden", "Hid", "base:tshirt", "x", { hidden = true })
SCRIPTS[#SCRIPTS + 1] = script("Base.NoModel", "NoModel", "base:tshirt", "")
SCRIPTS[#SCRIPTS + 1] = script("Base.Lipstick", "Lipstick", "base:makeup_lips", "x")
SCRIPTS[#SCRIPTS + 1] = script("Base.Tshirt_Rock", "Rock T-Shirt", "base:tshirt", "x")
HAIR = { style("Long"), style("Bob"), style("", false), style("HatLong", true), style("Bob") }
steps = 0
CLOCK_STEP = 1
getTimestampMs = function() CLOCK = CLOCK + 0.5; return CLOCK end      -- each look at the clock: half a millisecond of work passed
while not SolWardrobe.catalogStep(3) do steps = steps + 1; if steps > 5000 then break end end
""")
ck("catalog is built over many frames, not one (%d slices)" % L.eval("steps"), 10 < L.eval("steps") < 5000)
ck("catalog: 6001 clothing rows, the rest refused", L.eval("SolWardrobe.cat.count") == 6001 and L.eval("SolWardrobe.cat.state") == "done")
ck("catalog: hair styles without the hat alternates and without doubles", L.eval("#SolWardrobe.cat.rows.hair") == 3)
ck("catalog: second call does nothing", L.eval("SolWardrobe.catalogStep(3)") is True and L.eval("SolWardrobe.cat.count") == 6001)
L.execute("ss = 0; while not SolWardrobe.sortStep('top') do ss = ss + 1; if ss > 200 then break end end")
ck("a part's list is sorted over several frames (%d)" % L.eval("ss"), 1 < L.eval("ss") < 200)
ck("sorted by name", L.eval("(function() local r = SolWardrobe.cat.rows.top; for i = 2, #r do if r[i - 1].key > r[i].key then return false end end return #r > 700 end)()"))
ck("search by name, by id, case-insensitive", L.eval("#SolWardrobe.filter('top', 'ROCK')") == 1 and L.eval("#SolWardrobe.filter('top', 'tshirt_rock')") == 1 and L.eval("#SolWardrobe.filter('top', '  ')") == L.eval("#SolWardrobe.cat.rows.top") and L.eval("#SolWardrobe.filter('top', 'zzzz')") == 0)

# ---- trials on a faked Sol
L.execute("""
SOL = mkSol()
shirt = own(SOL, "Base.Tshirt", "base:tshirt"); pants = own(SOL, "Base.Pants", "base:pants"); shoes = own(SOL, "Base.Shoes", "base:shoes")
LOCOF["Mod.Blouse"] = "base:tshirt"; LOCOF["Mod.Dress"] = "base:dress"; LOCOF["Mod.Skirt"] = "base:skirt"; LOCOF["Mod.Boots"] = "base:shoes"
W0 = wornNames(SOL); B0 = bagCount(SOL)
ok = SolWardrobe.try(SOL, "top", { full = "Mod.Blouse", name = "Blouse" })
""")
ck("trial: the piece is created and on her at once", L.eval("ok") is True and L.eval("wornNames(SOL)") == "Base.Pants,Base.Shoes,Mod.Blouse")
ck("trial: her own shirt is in her bag, not lost", L.eval("SOL.inv:contains(shirt)") and L.eval("bagCount(SOL)") == L.eval("B0") + 1)
L.execute("SolWardrobe.try(SOL, 'top', { full = 'Mod.Blouse', name = 'x' }); SolWardrobe.try(SOL, 'top', { full = 'Mod.Blouse', name = 'x' })")
ck("trying again does not pile up trial pieces", L.eval("bagCount(SOL)") == L.eval("B0") + 1)
L.execute("r = SolWardrobe.revert(SOL, 'top')")
ck("take back: exactly what she wore, trial piece gone", L.eval("r") is True and L.eval("wornNames(SOL)") == L.eval("W0") and L.eval("bagCount(SOL)") == L.eval("B0") and L.eval("SOL.worn[1].item == pants or SOL.worn[2].item == pants"))
L.execute("SolWardrobe.try(SOL, 'top', { full = 'Mod.Blouse', name = 'x' }); a = SolWardrobe.apply(SOL, 'top'); r2 = SolWardrobe.revert(SOL, 'top')")
ck("apply: kept; the old shirt stays in her bag; nothing to take back", L.eval("a") is True and L.eval("r2") is False and L.eval("wornNames(SOL)") == "Base.Pants,Base.Shoes,Mod.Blouse" and L.eval("SOL.inv:contains(shirt)"))
# a dress displaces top and trousers; taking it back returns both
L.execute("W1 = wornNames(SOL); B1 = bagCount(SOL); SolWardrobe.try(SOL, 'dress', { full = 'Mod.Dress', name = 'd' })")
ck("dress trial: the game takes the top and trousers off", L.eval("wornNames(SOL)") == "Base.Shoes,Mod.Dress")
L.execute("SolWardrobe.revert(SOL, 'dress')")
ck("dress taken back: top and trousers on again", L.eval("wornNames(SOL)") == L.eval("W1") and L.eval("bagCount(SOL)") == L.eval("B1"))
# two trials at once, one swallows the other
L.execute("SolWardrobe.try(SOL, 'bottom', { full = 'Mod.Skirt', name = 's' }); SolWardrobe.try(SOL, 'dress', { full = 'Mod.Dress', name = 'd' })")
ck("a dress over a trial skirt: the skirt trial ends, its piece is removed", L.eval("SolWardrobe.trial.bottom == nil") and L.eval("wornNames(SOL)") == "Base.Shoes,Mod.Dress" and L.eval("bagCount(SOL)") == L.eval("B1") + 1)
L.execute("SolWardrobe.revertAll(SOL)")
ck("... and taking the dress back restores the ORIGINAL trousers and top", L.eval("wornNames(SOL)") == L.eval("W1") and L.eval("bagCount(SOL)") == L.eval("B1"))
# none
L.execute("SolWardrobe.try(SOL, 'shoes', nil)")
ck("none: the part is taken off, the piece stays in her bag", L.eval("wornNames(SOL)") == "Base.Pants,Mod.Blouse" and L.eval("SOL.inv:contains(shoes)"))
L.execute("SolWardrobe.revert(SOL, 'shoes')")
ck("none taken back: shoes on again", L.eval("wornNames(SOL)") == L.eval("W1"))
ck("none on an empty part reports it", L.eval("select(2, SolWardrobe.try(SOL, 'head', nil))") == "nothing_worn" or L.eval("({SolWardrobe.try(SOL, 'head', nil)})[2]") == "nothing_worn")
# failures leave nothing behind
L.execute("b = bagCount(SOL); ok1, why1 = SolWardrobe.try(SOL, 'top', { full = 'Mod.Missing', name = 'm' })")
ck("an item the game cannot create: refused, nothing changed", L.eval("ok1") is False and L.eval("why1") == "cannot_create" and L.eval("wornNames(SOL)") == L.eval("W1") and L.eval("bagCount(SOL)") == L.eval("b"))
L.execute("""LOCOF["Mod.Cursed"] = "base:tshirt"
local add = SOL.inv.AddItem
SOL.inv.AddItem = function(self, full) local it = add(self, full); if it and full == "Mod.Cursed" then it.cursed = true end return it end
ok2, why2 = SolWardrobe.try(SOL, 'top', { full = 'Mod.Cursed', name = 'c' })""")
ck("an item she cannot wear: refused, the created piece is removed again", L.eval("ok2") is False and L.eval("why2") == "cannot_wear" and L.eval("wornNames(SOL)") == L.eval("W1") and L.eval("bagCount(SOL)") == L.eval("b"))
# hair
L.execute("SolWardrobe.try(SOL, 'hair', { full = 'Bob', name = 'Bob' })")
ck("hair trial shows at once", L.eval("SOL.hair") == "Bob")
L.execute("SolWardrobe.revert(SOL, 'hair')")
ck("hair taken back", L.eval("SOL.hair") == "Long")
L.execute("SolWardrobe.try(SOL, 'hair', { full = 'Bob', name = 'Bob' }); SolWardrobe.apply(SOL, 'hair'); SolWardrobe.revertAll(SOL)")
ck("hair applied stays", L.eval("SOL.hair") == "Bob")
ck("her model is refreshed after changes", L.eval("SOL.resets") > 10)
ck("what the part shows now", L.eval("SolWardrobe.currentOf(SOL, 'top')") == "N:Mod.Blouse" and L.eval("SolWardrobe.currentOf(SOL, 'head')") is None and L.eval("SolWardrobe.currentOf(SOL, 'hair')") == "Bob")

# ---- v0.2.0: leaving a list without keeping, and a trial never outlives its list
ck("every part has a list name in both languages", L.eval("(function() for _, s in ipairs(SolWardrobe.SLOTS) do if SolWardrobe.word(s) == s then return false end end return #SolWardrobe.SLOTS == 15 end)()"))
L.execute("""WIN = setmetatable({ open = "top" }, SolWardrobe.WindowClass)
Wb = wornNames(SOL); Bb = bagCount(SOL)
SolWardrobe.try(SOL, "top", { full = "Mod.Cursed2", name = "x" })
LOCOF["Mod.Tee"] = "base:tshirt"
SolWardrobe.try(SOL, "top", { full = "Mod.Tee", name = "t" }); mid = wornNames(SOL)
WIN:closeList()""")
ck("back from a list: the trial piece is gone and her own is on again", L.eval("mid") != L.eval("Wb") and L.eval("wornNames(SOL)") == L.eval("Wb") and L.eval("bagCount(SOL)") == L.eval("Bb") and L.eval("WIN.open == nil"))
L.execute("""WIN.open = "top"; SolWardrobe.try(SOL, "top", { full = "Mod.Tee", name = "t" }); SolWardrobe.apply(SOL, "top"); WIN:closeList(); kept = wornNames(SOL)""")
ck("apply then back: the applied piece stays", "Mod.Tee" in L.eval("kept"))
L.execute("""Wc = wornNames(SOL); Bc = bagCount(SOL)
VIS = true
WIN.open = "shoes"; WIN.isVisible = function() return VIS end; WIN.isReallyVisible = function() return VIS end
SolWardrobe.win = WIN
SolWardrobe.try(SOL, "shoes", { full = "Mod.Boots", name = "b" })
g1 = SolWardrobe.guard(); still = wornNames(SOL)
VIS = false; g2 = SolWardrobe.guard(); after = wornNames(SOL)""")
ck("guard: nothing while the list is open and seen", L.eval("g1") is False and "Mod.Boots" in L.eval("still"))
ck("guard: window gone by any way -> the trial is taken back", L.eval("g2") is True and L.eval("after") == L.eval("Wc") and L.eval("bagCount(SOL)") == L.eval("Bc") and L.eval("WIN.open == nil"))
L.execute("""VIS = true; WIN.open = "shoes"; SolWardrobe.try(SOL, "shoes", { full = "Mod.Boots", name = "b" }); g3 = SolWardrobe.guard(true)""")
ck("guard: a save takes the trial back even with the list open", L.eval("g3") is True and L.eval("wornNames(SOL)") == L.eval("Wc"))
ck("guard: no trial, no work", L.eval("SolWardrobe.guard()") is False and L.eval("SolWardrobe.hasTrial()") is False)
L.execute("SolWardrobe.win = nil")

# ---- v0.3: her own loadout routine must not undo the wardrobe
L.execute("""SOL.md = { SC_Id = "sol-1" }; SOL.getModData = function(self) return self.md end
UPG = 0
SurvivorCompanion = { GameplayUtil = { idOf = function(a) return a.md.SC_Id end },
  Logistics = { clothingUpgrade = function(actor, item) UPG = UPG + 1; return true, 20, nil, item.loc end } }
LOCOF["Mod.Coat"] = "base:jacket"; LOCOF["Mod.Coat2"] = "base:jacket"
coat = own(SOL, "Mod.Coat", "base:jacket"); coat.md.SC_ManualWearFor = "sol-1"
SolWardrobe.try(SOL, "jacket", nil)
t_aside = SolWardrobe.isAside(SOL, coat); t_up = SurvivorCompanion.Logistics.clothingUpgrade(SOL, coat)
SolWardrobe.revert(SOL, "jacket")
r_aside = SolWardrobe.isAside(SOL, coat); r_manual = coat.md.SC_ManualWearFor; r_up = SurvivorCompanion.Logistics.clothingUpgrade(SOL, coat)
SolWardrobe.try(SOL, "jacket", nil); SolWardrobe.apply(SOL, "jacket")
a_up = SurvivorCompanion.Logistics.clothingUpgrade(SOL, coat); a_worn = wornNames(SOL)""")
ck("none on trial: the piece taken off is not an upgrade for her routine", L.eval("t_aside") is True and L.eval("t_up") is False)
ck("trial taken back: the piece has its old marks again", L.eval("r_aside") is False and L.eval("r_manual") == "sol-1" and L.eval("r_up") is True)
ck("none applied: her routine never wears it again", L.eval("a_up") is False and "Mod.Coat" not in L.eval("a_worn") and L.eval("SOL.inv:contains(coat)"))
L.execute("""SolWardrobe.try(SOL, "jacket", { full = "Mod.Coat2", name = "c2" }); SolWardrobe.apply(SOL, "jacket")
new = nil; for _, e in ipairs(SOL.worn) do if e.item.full == "Mod.Coat2" then new = e.item end end""")
ck("a piece applied is marked as dressed by him (the mod's own mark)", L.eval("new ~= nil and new.md.SC_ManualWearFor == 'sol-1' and new.md.SolWardrobeOff == nil"))
L.execute("""SolWardrobe.try(SOL, "jacket", { full = "Mod.Coat", name = "c" }); back = nil
for _, e in ipairs(SOL.worn) do if e.item.full == "Mod.Coat" then back = e.item end end
SolWardrobe.apply(SOL, "jacket")""")
ck("replacing it: the replaced piece is set aside, other items are still judged by her routine", L.eval("SolWardrobe.isAside(SOL, new)") is True and L.eval("(SurvivorCompanion.Logistics.clothingUpgrade(SOL, new))") is False and L.eval("(SurvivorCompanion.Logistics.clothingUpgrade(SOL, mkItem('X.Other', 'base:hat')))") is True)
L.execute("SWITCH = false")
ck("switch off: her routine as before", L.eval("(SurvivorCompanion.Logistics.clothingUpgrade(SOL, new))") is True)
L.execute("SWITCH = true")

# ---- v0.4: arrow keys in a list
L.execute("""Keyboard = { KEY_DOWN = 208, KEY_UP = 200, KEY_RETURN = 28 }
SolWardrobe.cat.rows.shoes = { { full = "Mod.Boots", name = "A boots", key = "a boots" }, { full = "Mod.Boots2", name = "B boots", key = "b boots" }, { full = "Mod.Boots3", name = "C boots", key = "c boots" } }
SolWardrobe.cat.sorted.shoes = true
LOCOF["Mod.Boots2"] = "base:shoes"; LOCOF["Mod.Boots3"] = "base:shoes"
KW = setmetatable({ open = "shoes", scroll = 0, query = "", flash = {}, visibleRows = 2, search = { getInternalText = function() return "" end } }, SolWardrobe.WindowClass)
Wk = wornNames(SOL); Bk = bagCount(SOL)
KW:onKeyPress(208); s1 = KW.sel; n1 = SolWardrobe.trial.shoes and SolWardrobe.trial.shoes.full
KW:onKeyPress(208); s2 = KW.sel; f2 = SolWardrobe.trial.shoes.full
KW:onKeyPress(208); KW:onKeyPress(208); s4 = KW.sel; f4 = SolWardrobe.trial.shoes.full; sc4 = KW.scroll
KW:onKeyPress(208); s5 = KW.sel
KW:onKeyPress(200); s6 = KW.sel; f6 = SolWardrobe.trial.shoes.full; bagMid = bagCount(SOL)""")
ck("down: first the 'nothing' row, then each piece is tried at once", L.eval("s1") == 1 and L.eval("n1") is None and L.eval("s2") == 2 and L.eval("f2") == "Mod.Boots")
ck("down to the end: stops at the last row and the list scrolls with it", L.eval("s4") == 4 and L.eval("f4") == "Mod.Boots3" and L.eval("sc4") == 2 and L.eval("s5") == 4)
ck("up: the row above; only one trial piece exists at a time", L.eval("s6") == 3 and L.eval("f6") == "Mod.Boots2" and L.eval("bagMid") == L.eval("Bk") + 1)
ck("the keys are the list's while it is open", L.eval("KW:isKeyConsumed(208)") is True and L.eval("KW:isKeyConsumed(30)") is False)
L.execute("KW:onKeyPress(28); kept = wornNames(SOL); KW.open = nil; KW:onKeyPress(208)")
ck("Enter applies the piece the arrows stand on; no list open: the keys do nothing", "Mod.Boots2" in L.eval("kept") and L.eval("SolWardrobe.trial.shoes == nil") and L.eval("wornNames(SOL)") == L.eval("kept"))

# ---- v0.5: everything off, and back on
L.execute("""LOCOF["Base.Bag_ALICE"] = "base:back"; LOCOF["Base.Bandage"] = "base:bandage"; LOCOF["Base.Bra"] = "base:underweartop"
bag = own(SOL, "Base.Bag_ALICE", "base:back"); bag.getInventory = function() return {} end
band = own(SOL, "Base.Bandage", "base:bandage"); bra = own(SOL, "Base.Bra", "base:underweartop")
SolWardrobe.try(SOL, "head", { full = "Mod.Tee", name = "t" })     -- a trial is open when he presses the button
Ws = wornNames(SOL); Bs = bagCount(SOL) - 1
n_off = SolWardrobe.stripAll(SOL); after = wornNames(SOL); bag_after = bagCount(SOL)
up = (SurvivorCompanion.Logistics.clothingUpgrade(SOL, bra))""")
ck("everything off: only her bag and the bandage stay on", L.eval("after") == "Base.Bag_ALICE,Base.Bandage" and L.eval("n_off") >= 4)
ck("... nothing is lost (all in her bag, the open trial piece removed) and her routine will not re-dress her", L.eval("bag_after") == L.eval("Bs") and L.eval("up") is False and L.eval("SolWardrobe.hasTrial()") is False)
L.execute("n_on = SolWardrobe.dressBack(SOL); again = wornNames(SOL)")
ck("put it back on: exactly what she wore before", L.eval("n_on") == L.eval("n_off") and sorted(L.eval("again").split(",")) == sorted(x for x in L.eval("Ws").split(",") if x != "Mod.Tee" or "Mod.Tee" in L.eval("kept")) and L.eval("SolWardrobe.lastStrip == nil"))
ck("... and the pieces are hers to keep again", L.eval("SolWardrobe.isAside(SOL, bra)") is False and L.eval("bra.md.SC_ManualWearFor") == "sol-1")
ck("nothing to put back: no change", L.eval("SolWardrobe.dressBack(SOL)") == 0)

# ---- her window's tab
ck("tab added right under status", [t["id"] for t in L.eval("SolUI.pageTabs()").values()] == ["status", "wardrobe", "skills", "orders"])
L.execute("SWITCH = false")
ck("switch off: no tab", [t["id"] for t in L.eval("SolUI.pageTabs()").values()] == ["status", "skills", "orders"])
L.execute("SWITCH = true; OPENED = 0; SolWardrobe.open = function() OPENED = OPENED + 1 end; page = setmetatable({ tab = 'wardrobe' }, PAGE); page:refresh(true)")
ck("choosing the tab opens the wardrobe and leaves her window on status", L.eval("OPENED") == 1 and L.eval("page.tab") == "status" and L.eval("page.refreshed") == 1)
L.execute("LANG = 'en'")
ck("English window: English words", L.eval("SolWardrobe.word('apply')") == "Apply")
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
