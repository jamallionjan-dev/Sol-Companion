"""SolActions with Sol's LF pages simulated (items as SolPages.readWidgets returns them) + the Sol Mind side."""
import json, os, sys, tempfile
sys.path.insert(0, "/home/claude/brain")
from lupa import lua51
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("package.path = 'build/media/lua/client/?.lua;' .. package.path")
LUA_DIR = tempfile.mkdtemp() + "/"
L.globals()["LUA_DIR"] = LUA_DIR
L.execute(r'''
CALLS = {}
function getFileWriter(n) local f = io.open(LUA_DIR .. n, "w"); return { write = function(_, s) f:write(s) end, close = function() f:close() end } end
function getFileReader(n) local f = io.open(LUA_DIR .. n, "r"); if not f then return nil end
  return { readLine = function() return f:read("*l") end, close = function() f:close() end } end
function getTimestampMs() return 1 end
SolUI = {}
local SNEAK = "\\u062A\\u0633\\u0644\\u0644"
local PAGES = {
  orders = { { kind = "section", text = "Direct orders" },
             { kind = "combo", command = "set_order", options = { "Follow", "Stay" }, selected = 1, ref = "ORDER" },
             { kind = "button", command = "regroup", text = "Regroup", enabled = true, ref = "REGROUP" },
             { kind = "button", command = "retreat", text = "Retreat", enabled = false, tip = "too far", ref = "RETREAT" },
             { kind = "section", text = "Movement" },
             { kind = "combo", command = "set_move_mode", options = { "Copy player", "Walk", SNEAK, "Run" }, selected = 1, ref = "MOVE" },
             { kind = "tick", command = "set_hold_fire", options = { { text = "Hold fire", on = false } }, ref = "HOLD" } },
  loadout = { { kind = "button", command = "open_inventory", text = "Open inventory", enabled = true, ref = "INV" } },
}
SolUI.extractPage = function(p) return PAGES[p] end
SolUI.pressButton = function(r) CALLS[#CALLS + 1] = "press:" .. r; return true end
SolUI.chooseOption = function(r, i) CALLS[#CALLS + 1] = "choose:" .. r .. ":" .. i; return true end
SolUI.toggleTick = function(r, i) CALLS[#CALLS + 1] = "tick:" .. r .. ":" .. i; return true end
SolUI.issueLF = function(c, p) CALLS[#CALLS + 1] = "lf:" .. c .. (p and p.vehicle and ":veh" or ""); return true end
SolUI.solActor = function() return { getX = function() return 10 end, getY = function() return 10 end } end
PLAYER = { getVehicle = function() return nil end, getX = function() return 10 end, getY = function() return 10 end }
function getSpecificPlayer() return PLAYER end
CAR = { getX = function() return 13 end, getY = function() return 11 end }
ZOMBIES = { { getX = function() return 30 end, getY = function() return 30 end }, { getX = function() return 14 end, getY = function() return 12 end } }
function getCell() return { getVehicles = function() return { size = function() return 1 end, get = function() return CAR end } end,
  getZombieList = function() return { size = function() return #ZOMBIES end, get = function(_, i) return ZOMBIES[i + 1] end } end } end
''')
for f in ("SolTextData.lua", "SolText.lua", "SolWorldScan.lua", "SolActions.lua"):
    L.execute(open("build/media/lua/client/" + f, encoding="ascii").read())
G = L.globals(); U = G.SolUI; res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
calls = lambda: list(G.CALLS.values())
cat = [dict(e) for e in U.actionCatalog().values()]
ids = [e["id"] for e in cat]
check("catalog built from Sol's pages (+ drive / read / attack)", ids[:6] == ["set_order", "regroup", "retreat", "set_move_mode", "set_hold_fire", "open_inventory"] and "sol_drive" in ids and "sol_attack_nearest" in ids)
r = U.runAction("regroup"); check("button action -> the LF button's own callback", calls() == ["press:REGROUP"])
r = U.runAction("retreat"); check("unavailable action returns LF's reason", r[0] is False and r[1] == "too far")
G.CALLS = L.table(); r = U.runAction("set_move_mode", "\\u062A\\u0633\\u0644\\u0644")
check("choice by option text (sneak) -> chooseOption(index 3)", calls() == ["choose:MOVE:3"])
G.CALLS = L.table(); U.runAction("set_hold_fire", "on"); check("switch on -> tick", calls() == ["tick:HOLD:1"])
G.CALLS = L.table(); r = U.runAction("set_hold_fire", "off"); check("switch already off -> nothing to do", r[0] is True and calls() == [])
G.CALLS = L.table(); U.runAction("follow"); check("command not on the page -> plain LF command", calls() == ["lf:follow"])
G.CALLS = L.table(); U.runAction("board_vehicle"); check("board vehicle with the nearest car as payload", calls() == ["lf:board_vehicle:veh"])
G.CALLS = L.table(); U.runAction("sol_attack_nearest"); check("attack -> designate the NEAREST zombie (LF command)", calls() == ["lf:designate_target"])
r = U.runAction("fly"); check("unknown action -> honest", r[0] is False and r[1] == "unknown_action")
# ---- her own body
L.execute(r"""
local function list(a) return { size = function() return #a end, get = function(_, i) return a[i + 1] end } end
local function food(name, age, off, rotten) return { __food = true, name = name, getDisplayName = function() return name end, getFullType = function() return "Base." .. name end,
  getHungerChange = function() return -0.2 end, isRotten = function() return rotten end, isFrozen = function() return false end, isBurnt = function() return false end,
  getAge = function() return age end, getOffAgeMax = function() return off end, isEquipped = function() return false end } end
local function bottle(kind) return { name = "Bottle", getDisplayName = function() return "Water Bottle" end, getFullType = function() return "Base.WaterBottle" end,
  isEquipped = function() return false end, getFluidContainer = function() return { isEmpty = function() return false end,
  getPrimaryFluid = function() return { getFluidTypeString = function() return kind end, isPoisonous = function() return kind ~= "Water" end } end } end } end
local hammer = { name = "Hammer", getDisplayName = function() return "Hammer" end, getFullType = function() return "Base.Hammer" end, isEquipped = function() return false end }
local function container(items) local c = { items = items }
  c.getItems = function(self) return list(self.items) end
  c.Remove = function(self, it) for i, v in ipairs(self.items) do if v == it then table.remove(self.items, i) return end end end
  c.AddItem = function(self, it) self.items[#self.items + 1] = it end
  return c end
BACKPACK = container({ food("Apple", 1, 3, false) })
local bag = { name = "Backpack", getDisplayName = function() return "Backpack" end, getFullType = function() return "Base.Bag" end, getInventory = function() return BACKPACK end, isEquipped = function() return true end }
SOLINV = container({ food("CannedTuna", 0, 1e9, false), food("Banana", 2, 2.5, false), food("Old Bread", 9, 5, true), bottle("TaintedWater"), bottle("Water"), hammer, bag })
PLINV = container({})
SOLX = 10
SOL = { getInventory = function() return SOLINV end, getX = function() return SOLX end, getY = function() return 10 end }
SolUI.solActor = function() return SOL end
PLAYER.getInventory = function() return PLINV end
function instanceof(o, c) return c == "Food" and o.__food == true end
QUEUED = {}
ISTimedActionQueue = { add = function(a) QUEUED[#QUEUED + 1] = a end }
ISEatFoodAction = { new = function(self, who, item, pct) return { kind = "eat", who = who, item = item, pct = pct } end }
ISDrinkFromBottle = { new = function(self, who, item, uses) return { kind = "drink", who = who, item = item, uses = uses } end }
SurvivorCompanion = { Medical = { playerBandagePreflight = function(c, p) return true end, applyPlayerBandage = function(c, p) CALLS[#CALLS + 1] = "bandage_player"; return true end,
  canReplaceDirtyBandage = function(a) return false end, replaceDirtyBandage = function(a) CALLS[#CALLS + 1] = "replace"; return true end } }
""")
r = U.runAction("sol_eat")
check("eat: the food that spoils first (banana before apple / tuna), not the rotten bread", r[0] is True and L.eval("QUEUED[1].kind == 'eat' and QUEUED[1].item.name == 'Banana' and QUEUED[1].pct == 1"))
r = U.runAction("sol_drink")
check("drink: clean water only (skips the tainted bottle)", r[0] is True and L.eval("QUEUED[2].kind == 'drink' and QUEUED[2].item.getFullType() == 'Base.WaterBottle' and QUEUED[2].item.getFluidContainer():getPrimaryFluid():getFluidTypeString() == 'Water'"))
L.execute("SOLINV.items = { SOLINV.items[1], SOLINV.items[6], SOLINV.items[7] }")   # tuna, hammer, backpack(apple)
r = U.runAction("sol_eat")
check("food inside her backpack is taken out first, then eaten", r[0] is True and L.eval("QUEUED[3].item.name == 'Apple' and #BACKPACK.items == 0"))
r = U.runAction("sol_give", "water"); check("give water when she has none -> honest", r[0] is False and r[1] == "she_has_none")
r = U.runAction("sol_give", "hammer"); check("give by English name: hammer moves to your bag", r[0] is True and L.eval("#PLINV.items == 1 and PLINV.items[1].name == 'Hammer'"))
G.SOLX = 20; r = U.runAction("sol_give", "food"); check("too far -> she says come closer", r[0] is False and r[1] == "too_far_to_hand_over"); G.SOLX = 10
L.execute("""
PLBAG = { items = {}, hasRoomFor = function(self) return true end }
PLBAG.AddItem = function(self, it) self.items[#self.items + 1] = it end
PLAYER.getClothingItem_Back = function() return { getInventory = function() return PLBAG end } end
PLINV.hasRoomFor = function() return false end
""")
r = U.runAction("sol_give", "tuna")
check("your inventory full -> it goes into your worn bag", r[0] is True and L.eval("#PLBAG.items == 1 and PLBAG.items[1].name == 'CannedTuna'"))
L.execute("PLBAG.hasRoomFor = function() return false end")
r = U.runAction("sol_give", "all"); check("all your bags full -> she keeps it and tells you", r[0] is False and r[1] == "your_bags_are_full")
L.execute("PLINV.hasRoomFor = function() return true end; PLBAG.hasRoomFor = function() return true end")
L.execute("NAILS = { name = 'Nails', getDisplayName = function() return 'Nails' end, getFullType = function() return 'Base.Nails' end, isEquipped = function() return false end }")
U.trackGivenItems(); L.execute("SOLINV:AddItem(NAILS)"); U.trackGivenItems()
r = U.runAction("sol_give", "mine")
check("'give me back what I gave you' returns exactly that (nails)", r[0] is True and L.eval("PLINV.items[#PLINV.items] == NAILS"))
r = U.runAction("sol_give", "mine"); check("nothing more of yours -> honest", r[0] is False and r[1] == "nothing_from_you")
n_before = L.eval("#PLINV.items")
r = U.runAction("sol_give", "all")
check("'give me everything' moves all loose items, not her worn backpack", r[0] is True and L.eval("#PLINV.items") > n_before and L.eval("(function() for _, v in ipairs(PLINV.items) do if v.name == 'Backpack' then return false end end return true end)()"))
G.CALLS = L.table(); r = U.runAction("sol_bandage_player"); check("bandage me -> LF Medical.applyPlayerBandage", calls() == ["bandage_player"] and r[0] is True)
r = U.runAction("sol_replace_bandage"); check("replace bandage refused by LF's own check -> reason", r[0] is False and r[1] == "no_dirty_bandage_or_no_clean_one")
# ---- fetch: walk to a container, take, come back, read
L.execute(r"""
local function list(a) return { size = function() return #a end, get = function(_, i) return a[i + 1] end } end
SkillBook = { Cooking = { perk = {} } }
ItemTag = { UNINTERESTING = "UNINTERESTING" }
local function book(name, skill, lit) return { name = name, getDisplayName = function() return name end, getFullType = function() return "Base." .. name end,
  getSkillTrained = function() return skill end, getLearnedRecipes = function() return nil end, IsLiterature = function() return lit end, hasTag = function() return false end } end
FUNBOOK = book("Administration for Managers", nil, true)
SKILLBOOK = book("Cooking Vol 1", "Cooking", false)
local function cont(items) local c = { items = items }; c.getItems = function(self) return list(self.items) end
  c.Remove = function(self, it) for i, v in ipairs(self.items) do if v == it then table.remove(self.items, i) return end end end; return c end
SHELF = cont({ FUNBOOK }); DESK = cont({ SKILLBOOK })
local shelfObj = { getContainerCount = function() return 1 end, getContainerByIndex = function() return SHELF end }
local deskObj = { getContainerCount = function() return 1 end, getContainerByIndex = function() return DESK end }
function getCell() return { getGridSquare = function(_, x, y, z)
  if x == 13 and y == 10 then return { getObjects = function() return list({ shelfObj }) end } end
  if x == 18 and y == 14 then return { getObjects = function() return list({ deskObj }) end } end
  return nil end, getVehicles = function() return list({}) end, getZombieList = function() return list({}) end } end
PLAYER.getZ = function() return 0 end
SOLY = 10
SOL.getX = function() return SOLX end; SOL.getY = function() return SOLY end
SOLINV.contains = function(self, it) for _, v in ipairs(self.items) do if v == it then return true end end return false end
SurvivorCompanion.AIToolGateway = { handle = function(actor, req) CALLS[#CALLS + 1] = "go_to:" .. req.arguments.x .. "," .. req.arguments.y; return { accepted = true, status = "accepted" } end }
ISInventoryTransferAction = { new = function(self, who, item, src, dst) return { kind = "take", item = item, src = src, dst = dst } end }
READ = nil
SolUI.solRead = function(it) READ = it; return true end
SolUI.solBooks = function() return {} end
""")
G.CALLS = L.table()
r = U.runAction("sol_fetch", "book:read")
check("finds the best book nearby (skill book beats the fun one) and walks there via LF navigation", r[0] is True and calls() == ["go_to:18,14"])
U.fetchTick(); check("still walking: nothing taken yet", G.SolUI.fetchJob.phase == "walking")
G.SOLX, G.SOLY = 18.2, 14.6; U.fetchTick()
check("next to the desk: the game's transfer action is queued", G.SolUI.fetchJob.phase == "taking" and L.eval("QUEUED[#QUEUED].kind == 'take' and QUEUED[#QUEUED].item == SKILLBOOK"))
L.execute("SOLINV:AddItem(SKILLBOOK); DESK:Remove(SKILLBOOK)"); G.CALLS = L.table(); U.fetchTick()
check("item in her bag -> she reads it and comes back (follow)", G.SolUI.fetchJob.phase == "done" and L.eval("READ == SKILLBOOK") and calls() == ["lf:follow"])
check("books for fun are recognised (literature lowers boredom)", U.bookKind(G.FUNBOOK) == "fun" and U.bookKind(G.SKILLBOOK) == "skill")
G.CALLS = L.table(); r = U.runAction("sol_fetch", "chainsaw"); check("nothing like that nearby -> honest", r[0] is False and r[1] == "not_found_nearby")
# ---- going somewhere
L.execute(r"""
ROOMSQ = { getX = function() return 21 end, getY = function() return 12 end, getRoom = function() return { getName = function() return "kitchen" end } end,
  isFree = function() return true end }
local baseCell = getCell
function getCell() local c = baseCell(); c.getGridSquare = function(_, x, y, z) if x == 21 and y == 12 then return ROOMSQ end return nil end; return c end
""")
L.execute("SOL.getZ = function() return 0 end")
G.CALLS = L.table(); G.SOLX, G.SOLY = 18, 12
r = U.runAction("sol_go_inside")
check("'ادخلي' -> walk to the nearest square inside a building (LF navigation)", r[0] is True and calls() == ["go_to:21,12"] and "kitchen" in r[1])
G.CALLS = L.table(); r = U.runAction("sol_goto", "7013,8448"); check("go to x,y", r[0] is True and calls() == ["go_to:7013,8448"])
r = U.runAction("sol_goto", "kitchen"); check("go to without x,y -> asks Sol Mind to resolve", r[0] is False and r[1] == "need_x_y")
# files: Sol Mind request -> game -> state
import chat_service as C
G.CALLS = L.table()
res_wait = C.run_action(LUA_DIR, "set_move_mode", "تسلل", wait=0)
U.pollActions()
st = open(LUA_DIR + "SolAct_State.txt").read()
check("Sol Mind request runs in game and reports back", calls() == ["choose:MOVE:3"] and "ok=true" in st)
snap = json.loads(open(LUA_DIR + "SolActions_Snapshot.txt").read())
acts = C.load_actions(LUA_DIR)
check("catalog file decoded for the brain (Arabic option text)", any(a["id"] == "set_move_mode" and "تسلل" in a["options"] for a in acts))
txt = C.actions_text(acts)
check("catalog shown to the model with options and availability", "set_move_mode: choose one of" in txt and "retreat: Retreat (unavailable now)" in txt)
check("Arabic verbs map to actions", C.intents("اتبعيني")[0] == ("action", {"action": "follow", "option": None}) and C.intents("تسللي")[0][1]["option"] == "تسلل")
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
