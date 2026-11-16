"""SolWorldScan.lua on a simulated world -> JSON parsed by Python."""
import json, sys
from lupa import lua51
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("package.path = '/home/claude/solpanel/build/media/lua/client/?.lua;' .. package.path")
L.execute(r'''
local function obj(t) return setmetatable(t, { __index = function(_, k) return nil end }) end
local function list(arr) return { size = function() return #arr end, get = function(_, i) return arr[i + 1] end } end
CharacterStat = { HUNGER = "HUNGER", THIRST = "THIRST", WETNESS = "WETNESS", FATIGUE = "FATIGUE" }
MoodleType = { HYPOTHERMIA = "HYPOTHERMIA", TIRED = "TIRED" }
local function char(stats, moodles, x, y, inv)
  return { getX = function() return x end, getY = function() return y end, getZ = function() return 0 end,
    getStats = function() return { get = function(_, e) return stats[e] or 0 end } end,
    getMoodles = function() return { getMoodleLevel = function(_, e) return moodles[e] or 0 end } end,
    getBodyDamage = function() return { getOverallBodyHealth = function() return 80 end, IsInfected = function() return false end,
      getBodyParts = function() return list({ { getType = function() return { toString = function() return "Hand_L" end } end, bleeding = function() return true end, bandaged = function() return false end } }) end } end,
    getCurrentSquare = function() return { getRoom = function() return { getName = function() return "kitchen" end } end } end,
    getVehicle = function() return nil end, getPrimaryHandItem = function() return { getDisplayName = function() return "Katana" end } end,
    getInventory = function() return inv end }
end
local function food(name, hunger, age, offMax, rotten)
  return { __food = true, getFullType = function() return "Base." .. name end, getDisplayName = function() return name end, getDisplayCategory = function() return "Food" end,
    getHungerChange = function() return hunger end, isFresh = function() return age < 1 end, isRotten = function() return rotten end, isCooked = function() return false end,
    isBurnt = function() return false end, isFrozen = function() return false end, getAge = function() return age end, getOffAge = function() return offMax - 2 end,
    getOffAgeMax = function() return offMax end, getCalories = function() return 300 end }
end
local function item(name, cat) return { getFullType = function() return "Base." .. name end, getDisplayName = function() return name end, getDisplayCategory = function() return cat end } end
local function bottle(liters, kind, poison) return { getFullType = function() return "Base.Bottle" end, getDisplayName = function() return "زجاجة ماء" end, getDisplayCategory = function() return "Water" end,
  getFluidContainer = function() return { isEmpty = function() return false end, getAmount = function() return liters end,
    getPrimaryFluid = function() return { getFluidTypeString = function() return kind end, isPoisonous = function() return poison end } end } end } end
local function container(items) return { getItems = function() return list(items) end, getType = function() return "crate" end } end
function instanceof(o, cls) return (cls == "Food" and o.__food) or (cls == "IsoAnimal" and o.__animal) or false end
local playerInv = container({ food("Apple", -0.1, 3, 4, false), item("Nails", "Material"), item("Nails", "Material") })
local solInv = container({ food("Rice", -0.4, 1, 10000000, false) })
PLAYER = char({ HUNGER = 0.3, THIRST = 0.1, WETNESS = 30 }, { HYPOTHERMIA = 2 }, 100.4, 200.6, playerInv)
SOL = char({ HUNGER = 0.05 }, {}, 101, 201, solInv)
function getSpecificPlayer() return PLAYER end
SolUI = { solActor = function() return SOL end }
local crate = obj({ getContainerCount = function() return 1 end, getContainerByIndex = function() return container({ bottle(1.5, "Water", false), bottle(2, "TaintedWater", true), item("Seeds Carrot", "Gardening") }) end,
  getSprite = function() return { getName = function() return "crate_01" end } end })
local hen = { __animal = true, getAnimalType = function() return "hen" end, getThirst = function() return 0.6 end, getStats = function() return { get = function() return 0.4 end } end }
local trunk = container({ item("Plank", "Material") })
local car = { getX = function() return 110 end, getY = function() return 205 end, getScript = function() return { getName = function() return "Pickup" end } end,
  getSqlId = function() return 7 end, getPartById = function(_, id) if id == "GasTank" then return { getContainerContentAmount = function() return 12 end, getContainerCapacity = function() return 50 end } end end,
  getPartCount = function() return 1 end, getPartByIndex = function() return { getItemContainer = function() return trunk end, getId = function() return "TruckBed" end } end }
function getCell() return {
  getGridSquare = function(_, x, y, z) if z ~= 0 then return nil end
    if x == 102 and y == 203 then return { getObjects = function() return list({ crate }) end, getRoom = function() return { getName = function() return "kitchen" end } end, getMovingObjects = function() return list({}) end } end
    if x == 99 and y == 199 then return { getObjects = function() return list({}) end, getRoom = function() return nil end, getMovingObjects = function() return list({ hen }) end } end
    return nil end,
  getVehicles = function() return list({ car }) end } end
function getWorld() return { getWorld = function() return "2026-10-23_14-43-18" end, getGameMode = function() return "Sandbox" end } end
function getGameTime() return { getWorldAgeHours = function() return 48 end, getHour = function() return 9 end } end
function getSandboxOptions() return { getTimeSinceApo = function() return 1 end } end
function getClimateManager() return { getSeasonName = function() return "Autumn" end, getAirTemperatureForCharacter = function() return 4.5 end, getPrecipitationIntensity = function() return 0.3 end } end
SandboxVars = { WaterShutModifier = 5, ElecShutModifier = 14 }
CFarmingSystem = { instance = { getLuaObjectOnSquare = function(_, sq) if sq.getRoom and sq:getRoom() == nil then return { typeOfSeed = "Carrots", waterLvl = 10, nbOfGrow = 2, state = "plow" } end end } }
function getTimestampMs() return 1 end
WRITTEN = nil
function getFileWriter() return { write = function(_, s) WRITTEN = s end, close = function() end } end
Events = nil
''')
for f in ("SolTextData.lua", "SolText.lua", "SolWorldScan.lua"):
    L.execute(open("/home/claude/solpanel/build/media/lua/client/" + f, encoding="utf-8").read())
G = L.globals(); res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
check("scan + write succeeds", G.SolUI.writeWorld() == True)
txt = G.WRITTEN
check("output is pure ASCII", txt.isascii())
d = json.loads(txt)
check("Python parses the JSON", isinstance(d, dict) and d["v"] == 1)
check("world identity", d["world"] == {"name": "2026-10-23_14-43-18", "mode": "Sandbox"})
check("time: day from world age", d["time"]["day"] == 2 and d["time"]["hour"] == 9)
check("weather and utilities", d["weather"]["season"] == "Autumn" and d["weather"]["air"] == 4.5 and d["utilities"]["waterShutDay"] == 5)
check("player stats via CharacterStat + moodles", d["player"]["stats"]["HUNGER"] == 0.3 and d["player"]["moodles"]["HYPOTHERMIA"] == 2 and d["player"]["room"] == "kitchen")
check("wounds: bleeding hand", d["player"]["wounds"][0]["state"] == ["bleeding"])
wh = [c["where"] for c in d["containers"]]
check("containers: player, Sol, square, vehicle", set(wh) == {"player", "sol", "square", "vehicle"})
pc = [c for c in d["containers"] if c["where"] == "player"][0]
check("items aggregated (2 nails -> count 2), food listed separately", pc["items"][0]["count"] == 2 and pc["foods"][0]["food"]["offAgeMax"] == 4)
sq = [c for c in d["containers"] if c["where"] == "square"][0]
check("fluids: clean and tainted, Arabic name escaped and decoded", sq["fluids"][1]["fluid"]["poison"] is True and sq["fluids"][0]["name"] == "زجاجة ماء")
check("vehicle trunk + fuel", d["vehicles"][0]["fuel"] == 12 and [c for c in d["containers"] if c["where"] == "vehicle"][0]["part"] == "TruckBed")
check("plants and animals", d["plants"][0]["seed"] == "Carrots" and d["animals"][0]["kind"] == "hen" and d["animals"][0]["thirst"] == 0.6)
open("/tmp/snapshot_sample.json", "w").write(txt)
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
