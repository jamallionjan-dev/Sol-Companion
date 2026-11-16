"""SolSkills.lua with the game's rule functions simulated (CraftRecipeManager, SkillBook, ISReadABook)."""
import json, os, sys
sys.path.insert(0, "/home/claude/brain")
from lupa import lua51
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("package.path = 'build/media/lua/client/?.lua;' .. package.path")
L.execute(r'''
local function list(a) return { size = function() return #a end, get = function(_, i) return a[i + 1] end, contains = function(_, x) for _, v in ipairs(a) do if v == x then return true end end return false end,
  containsAll = function(_, o) for i = 0, o:size() - 1 do local f = false for _, v in ipairs(a) do if v == o:get(i) then f = true end end if not f then return false end end return true end } end
local cooking = { getName = function() return "Cooking" end }
local carpentry = { getName = function() return "Carpentry" end }
local function item(fn) return { getFullName = function() return fn end } end
local function input(alts, q) local a = {} for _, f in ipairs(alts) do a[#a + 1] = item(f) end; return { getPossibleInputItems = function() return list(a) end, getAmount = function() return q end } end
local function rs(perk, lvl, has) return { getPerk = function() return perk end, getLevel = function() return lvl end, has = has } end
local function recipe(n, t, learn, known, skills, inputs)
  return { getName = function() return n end, getTranslationName = function() return t end, needToBeLearn = function() return learn end, known = known,
    getRequiredSkillCount = function() return #skills end, getRequiredSkill = function(_, i) return skills[i + 1] end, getInputs = function() return list(inputs) end }
end
local R = { recipe("MakeStew", "Make Stew", true, false, { rs(cooking, 3, false) }, { input({ "Base.Pot" }), input({ "Base.Carrots", "Base.Potato" }, 2) }),
  recipe("BuildDoor", "Build Wooden Door", false, nil, { rs(carpentry, 3, true) }, { input({ "Base.Plank" }, 4), input({ "Base.Nails" }, 4), input({ "Base.Hammer" }) }),
  recipe("MakeSalad", "Make Salad", false, nil, {}, { input({ "Base.Lettuce" }) }) }
for i = 4, 300 do R[i] = recipe("R" .. i, "Recipe " .. i, i % 2 == 0, i % 4 == 0, {}, {}) end
ScriptManager = { instance = { getAllCraftRecipes = function() return list(R) end } }
CraftRecipeManager = { hasPlayerLearnedRecipe = function(r, a) return r.known == true end, hasPlayerRequiredSkill = function(s, a) return s.has end }
SkillBook = { Cooking = { perk = cooking } }
local function book(name, skill, lo, hi) return { getDisplayName = function() return name end, getSkillTrained = function() return skill end, getLvlSkillTrained = function() return lo end,
  getMaxLevelTrained = function() return hi end, getNumberOfPages = function() return 220 end, getAlreadyReadPages = function() return 40 end, getLearnedRecipes = function() return nil end } end
local mag = { getDisplayName = function() return "Cooking Magazine" end, getSkillTrained = function() return nil end, getNumberOfPages = function() return 0 end,
  getAlreadyReadPages = function() return 0 end, getLearnedRecipes = function() return list({ "MakeStew" }) end }
local knownMag = { getDisplayName = function() return "Old Magazine" end, getSkillTrained = function() return nil end, getNumberOfPages = function() return 0 end,
  getAlreadyReadPages = function() return 0 end, getLearnedRecipes = function() return list({ "MakeSalad" }) end }
BAG = { book("Cooking Vol 1", "Cooking", 1, 2), book("Cooking Vol 3", "Cooking", 5, 6), book("Cooking Vol 0", "Cooking", 1, 0), mag, knownMag, { getDisplayName = function() return "Apple" end } }
SOL = { getPerkLevel = function(_, p) return 1 end, getInventory = function() return { getItems = function() return list(BAG) end, contains = function(_, x) for _, v in ipairs(BAG) do if v == x then return true end end return false end } end,
  getKnownRecipes = function() return list({ "MakeSalad" }) end, hasTrait = function() return false end }
SolUI = { solActor = function() return SOL end }
QUEUED = {}
ISReadABook = { new = function(self, who, it) return { who = who, item = it } end }
ISTimedActionQueue = { add = function(a) QUEUED[#QUEUED + 1] = a end }
TICKS = {}; Events = { OnTick = { Add = function(f) TICKS[#TICKS + 1] = f end } }
local T = 0; function getTimestampMs() return T end; function ADVANCE(ms) T = T + ms end
WRITTEN = nil; function getFileWriter() return { write = function(_, s) WRITTEN = s end, close = function() end } end
''')
for f in ("SolTextData.lua", "SolText.lua", "SolWorldScan.lua", "SolSkills.lua"):
    L.execute(open("build/media/lua/client/" + f, encoding="utf-8").read())
G = L.globals(); U = G.SolUI; res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
G.ADVANCE(20000)
ticks = 0
while G.WRITTEN is None and ticks < 50:
    for f in G.TICKS.values():
        if f is not None: pass
    L.execute("for _, f in ipairs(TICKS) do f() end"); ticks += 1
check("catalog built over several ticks (no frame spike)", G.WRITTEN is not None and ticks >= 3)
d = json.loads(G.WRITTEN)
check("all 300 recipes exported, ASCII JSON", d["count"] == 300 and G.WRITTEN.isascii())
stew = [r for r in d["recipes"] if r["n"] == "MakeStew"][0]; door = [r for r in d["recipes"] if r["n"] == "BuildDoor"][0]
check("stew: needs learning, not known by Sol, Cooking 3 not met (game functions)", stew["learn"] and stew["known"] is False and stew["skills"] == [["Cooking", 3, False]])
check("door: no learning needed, Carpentry 3 met, inputs with alternatives", door["learn"] is False and door["skills"][0][2] is True and door["in"][1]["a"] == ["Base.Nails"] and door["in"][1]["q"] == 4)
check("stats: learnable known count", U.recipeStats.learnable == 150 and U.recipeStats.known == 75)
books = {b.name: b.status for b in U.solBooks(G.SOL).values()}
check("books judged like the game: useful / too hard / too easy / teaches / known", books == {"Cooking Vol 1": "useful", "Cooking Vol 3": "too_hard", "Cooking Vol 0": "too_easy", "Cooking Magazine": "teaches", "Old Magazine": "known"})
mag = [b for b in U.solBooks(G.SOL).values() if b.name == "Cooking Magazine"][0]
ok = U.solRead(mag.item)
check("read = the game's ISReadABook timed action on Sol", ok is True and L.eval("QUEUED[1].who == SOL and QUEUED[1].item:getDisplayName() == 'Cooking Magazine'"))
r2 = U.solRead(L.eval("{ getDisplayName = function() return 'x' end }"))
check("cannot read an item that is not in her bag", r2[0] is False and r2[1] == "not_in_bag")
# ---- Sol Mind can_make with this catalog and a stock snapshot
import world_knowledge as W
snap = {"containers": [{"where": "player", "items": [{"type": "Base.Plank", "count": 6, "name": "Plank"}, {"type": "Base.Hammer", "count": 1}]}]}
r = W.can_make("door", d, snap)["matches"][0]
check("can_make door: missing nails reported", r["verdict"] == "missing_items" and r["missing_items"] == [["Base.Nails"]])
r = W.can_make("stew", d, snap)["matches"][0]
check("can_make stew: 'not learned' comes first (needs the magazine)", r["verdict"] == "not_learned" and r["missing_skills"] == [{"skill": "Cooking", "needs": 3}])
snap["containers"][0]["items"].append({"type": "Base.Nails", "count": 10})
check("with nails in stock the door can be made", W.can_make("door", d, snap)["matches"][0]["verdict"] == "can_make")
check("no catalog yet -> honest error", "error" in W.can_make("door", None, snap))
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
