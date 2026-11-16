"""What Sol has on her: first spawn, reload, death, a save from before this existed, and items the game refuses."""
import os, sys
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(r"""
print = function() end
NOW = 100000
function getTimestampMs() return NOW end
TICK = nil
Events = { OnTick = { Add = function(f) TICK = f end } }
STORE = {}
ModData = { getOrCreate = function(k) STORE[k] = STORE[k] or {}; return STORE[k] end, transmit = function() end }
NOITEM = {}
ScriptManager = { instance = { getItem = function(_, t) if NOITEM[t] then return nil end return t end } }
BADEQUIP = {}
function newActor(id, carried)
    local items = {}
    local a = { id = id, worn = {}, hand = nil }
    a.list = { size = function() return #items end, get = function(_, i) return items[i + 1] end }
    a.inv = { getItems = function() return a.list end,
        AddItem = function(_, t) local bag = t:find("ALICE") ~= nil; local it = { t = t }
            it.getBodyLocation = function() if bag then return nil end return "loc:" .. t end
            it.getCanBeEquipped = function() if bag then return "Back" end return nil end
            items[#items + 1] = it; return it end,
        DoRemoveItem = function(_, it) for i, x in ipairs(items) do if x == it then table.remove(items, i); return end end end }
    a.items = items
    a.getInventory = function() return a.inv end
    a.wornList = { size = function() local n = 0; for _ in pairs(a.worn) do n = n + 1 end return n end, clear = function() a.worn = {} end }
    a.getWornItems = function() return a.wornList end
    a.setPrimaryHandItem = function(_, it) a.hand = it end
    a.setSecondaryHandItem = function(_, it) a.off = it end
    a.setClothingItem_Back = function(_, it) a.back = it end
    a.setWornItem = function(_, loc, it) if BADEQUIP[it.t] or loc == "Back" then error("no such location") end a.worn[it.t] = true end
    a.resetModelNextFrame = function() end
    for _, t in ipairs(carried or {}) do a.inv:AddItem(t) end
    return a
end
SOL = nil
SolUI = { solActor = function() return SOL end }
SurvivorCompanion = { GameplayUtil = { idOf = function(a) return a.id end } }
function has(a, t) for _, it in ipairs(a.items) do if it.t == t then return true end end return false end
function nitems(a) return #a.items end
""")
L.execute(open(os.path.join(HERE, "SolDress.lua"), encoding="utf-8").read())
g = L.globals()
def step(): g.NOW = g.NOW + 3100; g.TICK()
def spawn(id, carried="{}"): L.execute('SOL = newActor("%s", %s)' % (id, carried)); step()
spawn("sol-1", '{ "Base.BaseballBat" }')
ck("first spawn: the katana in her hand", L.eval('SOL.hand ~= nil and SOL.hand.t == "Base.Katana"'))
for t in ["Hat_ArmyDesertNew", "Jacket_ArmyCamoDesertNew", "Trousers_CamoDesertNew", "Vest_BulletDesertNew", "Shoes_ArmyBootsDesert"]:
    ck("first spawn wears " + t, L.eval('SOL.worn["Base.%s"] == true' % t))
ck("first spawn: the bag is on her back", L.eval('SOL.back ~= nil and SOL.back.t == "Base.Bag_ALICEpack_DesertCamo"'))
ck("first spawn: what she came with stays", L.eval('has(SOL, "Base.BaseballBat")'))
n = L.eval("nitems(SOL)"); h = L.eval("SOL.hand")
L.execute('RELOADED = newActor("sol-1", { "Base.Katana", "Base.Hat_ArmyDesertNew", "Base.Medkit" }); RELOADED.worn["Base.Hat_ArmyDesertNew"] = true; SOL = RELOADED'); step()
ck("reload: nothing taken", L.eval("nitems(SOL)") == 3 and L.eval('has(SOL, "Base.Medkit")'))
ck("reload: nothing added", L.eval("SOL.hand") is None and L.eval("SOL.wornList:size()") == 1)
L.execute('STRIPPED = newActor("sol-1", {}); SOL = STRIPPED'); step(); ck("reload after he undressed her: left undressed", L.eval("nitems(SOL)") == 0)
spawn("sol-2", '{ "Base.Katana", "Base.Bag_ALICEpack_DesertCamo", "Base.Vest_BulletDesertNew", "Base.Shotgun" }')
for t in ["Katana", "Bag_ALICEpack_DesertCamo", "Vest_BulletDesertNew", "Shotgun"]: ck("after a death she does not have " + t, not L.eval('has(SOL, "Base.%s")' % t))
ck("after a death: nothing in her hands or on her back", L.eval("SOL.hand == nil and SOL.back == nil"))
ck("after a death: dressed", L.eval("SOL.wornList:size()") >= 6, L.eval("SOL.wornList:size()"))
ck("after a death: a closed jacket", L.eval('SOL.worn["Base.Jacket_WhiteTINT"] == true'))
ck("after a death: only what she wears", L.eval("nitems(SOL)") == L.eval("SOL.wornList:size()"), (L.eval("nitems(SOL)"), L.eval("SOL.wornList:size()")))
ck("after a death: never the kit again", not L.eval('SOL.worn["Base.Jacket_ArmyCamoDesertNew"] == true'))
c = L.eval("nitems(SOL)"); step(); ck("looked at once only", L.eval("nitems(SOL)") == c)
L.execute('STORE = {}; STORE.Sol_InitialDesertLoadout = { initialDesertKitGranted = true }'); spawn("old-1", '{ "Base.Katana" }')
ck("a save from before this: she is left alone", L.eval('has(SOL, "Base.Katana")') and L.eval("STORE.Sol_InitialDesertLoadout.dressedId") == "old-1")
L.execute("STORE = {}; BADEQUIP = {}; BADEQUIP['Base.Vest_BulletDesertNew'] = true"); spawn("sol-9")
ck("an item the game refuses does not cost her the rest", L.eval('SOL.hand ~= nil and SOL.hand.t == "Base.Katana" and SOL.worn["Base.Shoes_ArmyBootsDesert"] == true'))
ck("and the kit is spent", L.eval("STORE.Sol_InitialDesertLoadout.initialDesertKitGranted") is True)
L.execute("BADEQUIP = {}; STORE = {}; NOITEM = {}; NOITEM['Base.Jacket_WhiteTINT'] = true; STORE.Sol_InitialDesertLoadout = { initialDesertKitGranted = true, dressedId = 'a' }"); spawn("b")
ck("no such jacket in this version: the next one", L.eval('SOL.worn["Base.Jacket_Padded"] == true'))
L.execute("NOITEM = {}; STORE = {}; SAVEID = SurvivorCompanion.GameplayUtil.idOf; SurvivorCompanion.GameplayUtil.idOf = function() return nil end; SOL = newActor('x', {})"); step()
ck("not registered yet: she is not touched", L.eval("nitems(SOL)") == 0 and L.eval("STORE.Sol_InitialDesertLoadout.initialDesertKitGranted") is None)
L.execute("SurvivorCompanion.GameplayUtil.idOf = SAVEID"); step(); ck("and is dressed once she is", L.eval("SOL.hand ~= nil"))
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
