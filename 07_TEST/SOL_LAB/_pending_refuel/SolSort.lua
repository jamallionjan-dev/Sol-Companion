-- SolSort.lua - switch item_sort. "\\u0631\\u062A\\u0651\\u0628\\u064A \\u0627\\u0644\\u0623\\u063A\\u0631\\u0627\\u0636": Sol sorts the home's things, each kind into the container that is for it.
-- v0.2: one scan, one plan, one walk. GENERATED ASCII: Arabic is stored as \\uXXXX escapes (SolText decodes them), as in SolSpeechAR.
--   1 scan      every home container (SolInventory's last scan gives the places; the items are read live), SCAN_PER_TICK a tick
--   2 classify  every item gets a category (SC.Logistics.itemCategory; perishable food is "cold"), ITEMS_PER_TICK a tick
--   3 roles     every container gets a role: the player's own storage label (BaseLife storages) first, then its in-game type
--               and room (types and rooms from the game's Distributions.lua), then the majority of what it already holds
--   4 plan      every misplaced item gets one destination, computed once, with each container's free weight reserved as it goes
--   5 round     the visiting order: each container once; at each stop she puts down what is for here and picks up what goes to a
--               container still ahead, as much as she can carry. What is left (a full bag, an A<->B swap) goes in the next round.
--   6 work      at each stop the items move through the verified transfer, MOVES_PER_TICK a tick, with the loot animation.
-- 0.2.1: where she stands is chosen the way vanilla does it (luautils.walkToContainer -> AdjacentFreeTileFinder.Find): the four
--   sides first, a corner only when no side works; the square must be standable (canStand) and reach the container (canReachTo).
--   A container with no such square is left out of the plan. Walking: one order, re-sent only after 5 s without a new square,
--   two attempts, then it is skipped. 0.2.0 re-sent every 3 s to LF's interactionTargets (corners unchecked) and stalled a minute.
-- 0.2.2 (switch spatial_access, SolPlace): a standing square must be on the container's side of every fence, wall, window and closed
--   door (SolPlace.access), and "arrived" asks the same; her walk there goes through doors first (SolPlace wraps U.solGoto).
-- She says short lines: what she sorts and where, and a summary at the end. Stop or danger: what is in her hands goes back first.
-- Verb: sol_sort run | stop | status.
SolUI = SolUI or {}
local U = SolUI
SolSort = SolSort or {}
local M = SolSort
M.VERSION = "0.2.2"
M.SCAN_PER_TICK = 4            -- containers read per tick
M.ITEMS_PER_TICK = 40          -- items classified per tick
M.PLAN_PER_TICK = 60           -- items given a destination per tick
M.MOVES_PER_TICK = 4           -- items moved per tick at a container
M.TICK_MS = 100
M.MAX_MOVES = 300              -- one order never plans more than this
M.MAX_STOPS = 40               -- containers in one round
M.MAX_ROUNDS = 20             -- a round ends when her hands are full and delivered; a big home takes several
M.STOP_BASE_MS, M.ITEM_MS, M.STOP_MAX_MS = 500, 150, 4000   -- a stop: 0.5 s + 0.15 s per kg (vanilla: ~0.8 s per kg each way)
M.WALK_MS = 60000              -- one container: never longer than this, even while she keeps moving
M.STALL_MS = 5000              -- no new square for this long: that attempt failed
M.WALK_ATTEMPTS = 2            -- failed attempts before the container is skipped (and named in the summary)
M.SAY_GAP_MS = 7000
M.DANGER_TILES, M.DANGER_WAIT_MS = 8, 90000
M.INV_WAIT_MS = 30000
M.MAX_MS = 900000             -- one order never works longer than this (real ms); then what is in her hands goes back
M.CARRY_MIN, M.CARRY_MAX = 4, 25
M.MAJORITY_MIN, M.MAJORITY_SHARE = 4, 0.7

-- what a category is, as a key of the plan (Logistics names -> keys); food that rots is "cold"
M.KEY_OF = { food = "food", water = "water", medicine = "medicine", clothing = "clothing", tools = "tools", construction = "construction",
    crafting = "crafting", weapon = "weapon", ammunition = "ammunition", literature = "literature", farming = "farming" }
-- the player's storage labels (BaseLife.STORAGE_CATEGORIES) -> keys; general and output are staging (emptied, never filled), memorial is never touched
M.LABEL = { food = { "food" }, water = { "water" }, medical = { "medicine" }, tools = { "tools" }, construction = { "construction" },
    crafting = { "crafting" }, literature = { "literature" }, weapons = { "weapon" }, ammunition = { "ammunition" }, clothing = { "clothing" },
    farming = { "farming" } }
M.STAGING = { general = true, output = true }
-- in-game container type -> keys (types from Distributions.lua); a room can say otherwise (below)
M.TYPE = {
    fridge = { "cold" }, freezer = { "cold" },
    medicine = { "medicine" },
    wardrobe = { "clothing" }, dresser = { "clothing" }, clothingrack = { "clothing" },
    toolcabinet = { "tools", "construction", "crafting" },
    militarycrate = { "weapon", "ammunition" }, militarylocker = { "weapon", "ammunition" },
    shelves = { "literature" }, shelvesmag = { "literature" }, bookcase = { "literature" }, filingcabinet = { "literature" }, desk = { "literature" },
    crate = { "farming" },
    dishescabinet = { "food", "water" },
}
local GARAGE = { metal_shelves = { "tools", "construction", "crafting" }, crate = { "construction", "farming" }, locker = { "tools" },
    counter = { "tools", "crafting" }, shelves = { "tools", "crafting" } }
M.ROOM_TYPE = {
    kitchen = { counter = { "food", "water" }, overhead = { "food", "water" }, shelves = { "food", "water" }, metal_shelves = { "food", "water" } },
    bathroom = { counter = { "medicine" }, overhead = { "medicine" }, shelves = { "medicine" } },
    bedroom = { locker = { "clothing" } },
    garage = GARAGE, garagestorage = GARAGE, storageunit = GARAGE, shed = GARAGE,
}
-- never opened: cooking, washing, the bin
M.NO_TOUCH = { bin = true, stove = true, microwave = true, clothingwasher = true, clothingdryer = true, fireplace = true, barbecue = true,
    woodstove = true, toaster = true, coffeemaker = true, campfire = true, composter = true }
-- no container for a key: the next best key
M.FALLBACK = { cold = "food", water = "food", ammunition = "weapon", weapon = "tools", construction = "tools", crafting = "tools", farming = "tools" }

-- ---------------------------------------------------------------- words (Levantine)
M.CAT_AR = { cold = "\\u0627\\u0644\\u0623\\u0643\\u0644 \\u0627\\u0644\\u0637\\u0627\\u0632\\u0629", food = "\\u0627\\u0644\\u0623\\u0643\\u0644", water = "\\u0627\\u0644\\u0645\\u064A", medicine = "\\u0627\\u0644\\u062F\\u0648\\u0627", clothing = "\\u0627\\u0644\\u062A\\u064A\\u0627\\u0628", tools = "\\u0627\\u0644\\u0639\\u062F\\u0651\\u0629",
    construction = "\\u0645\\u0648\\u0627\\u062F \\u0627\\u0644\\u0639\\u0645\\u0627\\u0631", crafting = "\\u0623\\u063A\\u0631\\u0627\\u0636 \\u0627\\u0644\\u0635\\u0646\\u0639\\u0629", weapon = "\\u0627\\u0644\\u0633\\u0644\\u0627\\u062D", ammunition = "\\u0627\\u0644\\u0641\\u0634\\u0643", literature = "\\u0627\\u0644\\u0643\\u062A\\u0628", farming = "\\u0623\\u063A\\u0631\\u0627\\u0636 \\u0627\\u0644\\u0632\\u0631\\u0627\\u0639\\u0629" }
M.CAT_SUM = { cold = "\\u0623\\u0643\\u0644 \\u0637\\u0627\\u0632\\u0629", food = "\\u0623\\u0643\\u0644", water = "\\u0645\\u064A", medicine = "\\u062F\\u0648\\u0627", clothing = "\\u062A\\u064A\\u0627\\u0628", tools = "\\u0639\\u062F\\u0651\\u0629",
    construction = "\\u0645\\u0648\\u0627\\u062F \\u0639\\u0645\\u0627\\u0631", crafting = "\\u0623\\u063A\\u0631\\u0627\\u0636 \\u0635\\u0646\\u0639\\u0629", weapon = "\\u0633\\u0644\\u0627\\u062D", ammunition = "\\u0641\\u0634\\u0643", literature = "\\u0643\\u062A\\u0628", farming = "\\u0623\\u063A\\u0631\\u0627\\u0636 \\u0632\\u0631\\u0627\\u0639\\u0629" }
M.KIND_AR = { fridge = "\\u0627\\u0644\\u0628\\u0631\\u0627\\u062F", freezer = "\\u0627\\u0644\\u0641\\u0631\\u064A\\u0632\\u0631", medicine = "\\u062E\\u0632\\u0627\\u0646\\u0629 \\u0627\\u0644\\u062F\\u0648\\u0627", toolcabinet = "\\u062E\\u0632\\u0627\\u0646\\u0629 \\u0627\\u0644\\u0639\\u062F\\u0651\\u0629", militarycrate = "\\u0635\\u0646\\u062F\\u0648\\u0642 \\u0627\\u0644\\u0633\\u0644\\u0627\\u062D",
    militarylocker = "\\u062E\\u0632\\u0627\\u0646\\u0629 \\u0627\\u0644\\u0633\\u0644\\u0627\\u062D", wardrobe = "\\u0627\\u0644\\u062E\\u0632\\u0627\\u0646\\u0629", dresser = "\\u0627\\u0644\\u0643\\u0648\\u0645\\u0648\\u062F\\u064A\\u0646\\u0629", clothingrack = "\\u0639\\u0644\\u0651\\u0627\\u0642\\u0629 \\u0627\\u0644\\u062A\\u064A\\u0627\\u0628", sidetable = "\\u0627\\u0644\\u0643\\u0648\\u0645\\u0648\\u062F\\u064A\\u0646\\u0629",
    shelves = "\\u0627\\u0644\\u0631\\u0641\\u0648\\u0641", shelvesmag = "\\u0631\\u0641\\u0648\\u0641 \\u0627\\u0644\\u0645\\u062C\\u0644\\u0627\\u062A", bookcase = "\\u0627\\u0644\\u0645\\u0643\\u062A\\u0628\\u0629", metal_shelves = "\\u0627\\u0644\\u0631\\u0641\\u0648\\u0641 \\u0627\\u0644\\u062D\\u062F\\u064A\\u062F", crate = "\\u0627\\u0644\\u0635\\u0646\\u062F\\u0648\\u0642",
    desk = "\\u0627\\u0644\\u0637\\u0627\\u0648\\u0644\\u0629", filingcabinet = "\\u062E\\u0632\\u0627\\u0646\\u0629 \\u0627\\u0644\\u0623\\u0648\\u0631\\u0627\\u0642", locker = "\\u0627\\u0644\\u062E\\u0632\\u0627\\u0646\\u0629 \\u0627\\u0644\\u062D\\u062F\\u064A\\u062F", counter = "\\u0627\\u0644\\u062E\\u0632\\u0627\\u0646\\u0629", overhead = "\\u0627\\u0644\\u062E\\u0632\\u0627\\u064A\\u0646 \\u0627\\u0644\\u0641\\u0648\\u0642",
    dishescabinet = "\\u062E\\u0632\\u0627\\u0646\\u0629 \\u0627\\u0644\\u0635\\u062D\\u0648\\u0646" }
M.ROOM_AR = { kitchen = "\\u0627\\u0644\\u0645\\u0637\\u0628\\u062E", bathroom = "\\u0627\\u0644\\u062D\\u0645\\u0627\\u0645", bedroom = "\\u063A\\u0631\\u0641\\u0629 \\u0627\\u0644\\u0646\\u0648\\u0645", livingroom = "\\u0627\\u0644\\u0635\\u0627\\u0644\\u0648\\u0646", garage = "\\u0627\\u0644\\u0643\\u0631\\u0627\\u062C",
    garagestorage = "\\u0627\\u0644\\u0643\\u0631\\u0627\\u062C", laundry = "\\u063A\\u0631\\u0641\\u0629 \\u0627\\u0644\\u063A\\u0633\\u064A\\u0644", storageunit = "\\u0627\\u0644\\u0645\\u062E\\u0632\\u0646", shed = "\\u0627\\u0644\\u0645\\u062E\\u0632\\u0646", diningroom = "\\u063A\\u0631\\u0641\\u0629 \\u0627\\u0644\\u0633\\u0641\\u0631\\u0629" }
M.NAMED_BY_KIND = { fridge = true, freezer = true, medicine = true, toolcabinet = true, militarycrate = true, militarylocker = true }
local W = {
    ["in"] = "\\u0628", one = "\\u063A\\u0631\\u0636 \\u0648\\u0627\\u062D\\u062F", two = "\\u063A\\u0631\\u0636\\u064A\\u0646", few = "\\u0623\\u063A\\u0631\\u0627\\u0636", many = "\\u063A\\u0631\\u0636", thing = "\\u0634\\u064A",
    start = "\\u0637\\u064A\\u0628\\u060C \\u062E\\u0644\\u064A\\u0646\\u064A \\u0634\\u0648\\u0641 \\u0634\\u0648 \\u0641\\u064A \\u0628\\u0627\\u0644\\u062E\\u0632\\u0627\\u064A\\u0646 \\u0623\\u0648\\u0644.",
    waitInv = "\\u0644\\u062D\\u0638\\u0629\\u060C \\u062E\\u0644\\u064A\\u0646\\u064A \\u0625\\u062A\\u0637\\u0644\\u0651\\u0639 \\u0639\\u0627\\u0644\\u0628\\u064A\\u062A \\u0623\\u0648\\u0644.",
    planOne = "\\u0641\\u064A \\u063A\\u0631\\u0636 \\u0648\\u0627\\u062D\\u062F \\u0645\\u0634 \\u0628\\u0645\\u062D\\u0644\\u0651\\u0647\\u060C \\u064A\\u0644\\u0627.",
    planMany = "\\u0641\\u064A %s \\u0645\\u0634 \\u0628\\u0645\\u062D\\u0644\\u0651\\u0646\\u060C \\u064A\\u0644\\u0627 \\u0631\\u062A\\u0651\\u0628\\u0646.",
    nothing = "\\u0643\\u0644 \\u0634\\u064A \\u0628\\u0645\\u062D\\u0644\\u0651\\u0647\\u060C \\u0645\\u0627 \\u0641\\u064A \\u0634\\u064A \\u0644\\u0631\\u062A\\u0651\\u0628\\u0647.",
    progress = "\\u0639\\u0645 \\u0631\\u062A\\u0651\\u0628 %s %s",
    cannot = "\\u0645\\u0627 \\u0642\\u062F\\u0631\\u062A \\u0648\\u0635\\u0644 %s\\u060C \\u0628\\u0643\\u0645\\u0651\\u0644 \\u0628\\u0627\\u0644\\u0628\\u0627\\u0642\\u064A.",
    summary = "\\u0631\\u062A\\u0651\\u0628\\u062A %s: %s.",
    summaryNone = "\\u0645\\u0627 \\u0642\\u062F\\u0631\\u062A \\u0631\\u062A\\u0651\\u0628 \\u0634\\u064A.",
    left = " \\u0648\\u0641\\u064A %s \\u0645\\u0627 \\u0644\\u0642\\u064A\\u062A\\u0644\\u0646 \\u0645\\u062D\\u0644.",
    more = " \\u0648\\u0628\\u0639\\u062F \\u0641\\u064A %s\\u060C \\u0642\\u0644\\u0651\\u064A \\u0625\\u0630\\u0627 \\u0628\\u062F\\u0651\\u0643 \\u0643\\u0645\\u0651\\u0644.",
    unreach = " \\u0648\\u0645\\u0627 \\u0642\\u062F\\u0631\\u062A \\u0623\\u0648\\u0635\\u0644 %s.", lam = "\\u0644", lamT = "\\u0644\\u0640",
    boxOne = "\\u0635\\u0646\\u062F\\u0648\\u0642 \\u0648\\u0627\\u062D\\u062F", boxTwo = "\\u0635\\u0646\\u062F\\u0648\\u0642\\u064A\\u0646", boxFew = "\\u0635\\u0646\\u0627\\u062F\\u064A\\u0642", boxMany = "\\u0635\\u0646\\u062F\\u0648\\u0642",
    stopped = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0648\\u0642\\u0651\\u0641\\u062A \\u0627\\u0644\\u062A\\u0631\\u062A\\u064A\\u0628.",
    stoppedMoved = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0648\\u0642\\u0651\\u0641\\u062A. \\u0631\\u062A\\u0651\\u0628\\u062A %s \\u0644\\u0647\\u0644\\u0651\\u0642.",
    danger = "\\u0641\\u064A \\u0634\\u064A \\u0642\\u0631\\u064A\\u0628\\u060C \\u0631\\u062D \\u0648\\u0642\\u0651\\u0641 \\u0627\\u0644\\u062A\\u0631\\u062A\\u064A\\u0628.",
    sep = "\\u060C ",
}
M.W = W

local function log(m) print("[SolSort] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or 0 end
local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a, b = pcall(f, o, ...)
    if ok then return a, b end
    return nil
end
local function on() local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("item_sort") == true end
local function actor() return type(U.solActor) == "function" and U.solActor() or nil end
local function SC() local sc = g("SurvivorCompanion"); return type(sc) == "table" and sc or nil end
local function GU() local sc = SC(); return sc and type(sc.GameplayUtil) == "table" and sc.GameplayUtil or nil end
local function num(v) return tonumber(v) end
local function int(n) return tostring(math.floor((tonumber(n) or 0) + 0.5)) end

M.state = M.state or {}
local S = M.state
S.lines = S.lines or {}
S.stats = S.stats or { plans = 0, rounds = 0 }

-- ---------------------------------------------------------------- what things are
function M.perishable(item)
    local off = num(call(item, "getOffAgeMax"))
    return off ~= nil and off > 0 and off < 100000
end

function M.keyOf(item)
    local sc = SC()
    local L = sc and sc.Logistics
    if not (L and type(L.itemCategory) == "function") then return nil end
    local ok, c = pcall(L.itemCategory, item)
    local k = ok and M.KEY_OF[c] or nil
    if k == "food" and M.perishable(item) then return "cold" end
    return k
end

-- never touched: worn, equipped, favourites, keys, bags, things her code protects
function M.movable(item, a)
    if call(item, "isFavorite") == true or call(item, "isEquipped") == true or call(item, "isWorn") == true then return false end
    local ft = tostring(call(item, "getFullType") or "")
    if string.find(ft, "Key", 1, true) or string.find(ft, "Corpse", 1, true) then return false end
    if tostring(call(item, "getCategory") or "") == "Container" then return false end
    local sc = SC()
    local P = sc and sc.PersonalItems
    if P and type(P.isProtected) == "function" then
        local ok, prot = pcall(P.isProtected, item, a, "base_haul")
        if ok and prot == true then return false end
    end
    return true
end

local function weightOf(item)
    return num(call(item, "getUnequippedWeight")) or num(call(item, "getActualWeight")) or num(call(item, "getWeight")) or 1
end

-- ---------------------------------------------------------------- names
local AL = "\\u0627\\u0644"                      -- "\\u0627\\u0644"
function M.nameOf(P)
    if P.room and M.ROOM_AR[P.room] and not M.NAMED_BY_KIND[P.kind] then return M.ROOM_AR[P.room] end
    return M.KIND_AR[P.kind] or M.KIND_AR.crate
end
function M.inName(P) return W["in"] .. M.nameOf(P) end                                       -- "\\u0628\\u0627\\u0644\\u0645\\u0637\\u0628\\u062E"
function M.toName(P)                                                                           -- "\\u0644\\u0644\\u0628\\u0631\\u0627\\u062F", "\\u0644\\u062E\\u0632\\u0627\\u0646\\u0629 \\u0627\\u0644\\u062F\\u0648\\u0627"
    local n = M.nameOf(P)
    if string.sub(n, 1, #AL) == AL then return "\\u0644" .. string.sub(n, 7) end
    return "\\u0644" .. n
end
function M.boxes(n)
    n = math.floor(n)
    if n == 1 then return W.boxOne elseif n == 2 then return W.boxTwo elseif n <= 10 then return int(n) .. " " .. W.boxFew end
    return int(n) .. " " .. W.boxMany
end
function M.toBoxes(n) return (n <= 2 and W.lam or W.lamT) .. M.boxes(n) end      -- "\\u0644\\u0635\\u0646\\u062F\\u0648\\u0642\\u064A\\u0646", "\\u0644\\u06403 \\u0635\\u0646\\u0627\\u062F\\u064A\\u0642"
function M.count(n)
    n = math.floor(n)
    if n == 1 then return W.one elseif n == 2 then return W.two elseif n <= 10 then return int(n) .. " " .. W.few end
    return int(n) .. " " .. W.many
end

local function say(a, text, kind)
    S.lines[#S.lines + 1] = { kind = kind, text = text, at = nowMs() }
    while #S.lines > 24 do table.remove(S.lines, 1) end
    log("say " .. tostring(kind))
    local gu = GU()
    if a ~= nil and gu and type(gu.say) == "function" then pcall(gu.say, a, text) end
end

-- ---------------------------------------------------------------- the home's containers
local function placeContainer(p)
    local gu = GU()
    local sq = gu and type(gu.gridSquare) == "function" and gu.gridSquare(p.x, p.y, p.z) or nil
    local obj = sq and call(call(sq, "getObjects"), "get", p.oi)
    return obj and call(obj, "getContainerByIndex", p.ci or 0) or nil, sq
end

-- where she can stand to use a container, as vanilla picks it (luautils.walkToContainer, AdjacentFreeTileFinder.Find):
-- the four sides first; the corners only when no side works; standable (canStand: floor, not solid, not by a window or a low fence)
-- and nothing between it and the container (canReachTo: walls, doors, windows). Nearest to her first.
local SIDES = { { -1, 0 }, { 1, 0 }, { 0, -1 }, { 0, 1 } }
local CORNERS = { { -1, -1 }, { 1, -1 }, { -1, 1 }, { 1, 1 } }
local function place() local SP = g("SolPlace"); return type(SP) == "table" and type(SP.on) == "function" and SP.on() and SP or nil end
function M.access(P)
    local SP = place()
    if SP then                                                                   -- spatial_access: the container's own side only
        local out = {}
        for _, s in ipairs(SP.access(P.x, P.y, P.z)) do
            local sq = GU() and type(GU().gridSquare) == "function" and GU().gridSquare(s.x, s.y, s.z) or nil
            if sq == nil or P.sq == nil or call(sq, "canReachTo", P.sq) ~= false then out[#out + 1] = s end
        end
        return out
    end
    local gu = GU()
    if not (gu and type(gu.gridSquare) == "function") then return {} end
    local out = {}
    for pass = 1, 2 do
        for _, d in ipairs(pass == 1 and SIDES or CORNERS) do
            local s = gu.gridSquare(P.x + d[1], P.y + d[2], P.z)
            if s ~= nil and call(s, "canStand") ~= false and call(s, "canReachTo", P.sq) ~= false then
                out[#out + 1] = { x = P.x + d[1], y = P.y + d[2], z = P.z }
            end
        end
        if #out > 0 then break end
    end
    return out
end

function M.arrived(a, P)
    local px, py, pz = math.floor(num(call(a, "getX")) or -1e6), math.floor(num(call(a, "getY")) or -1e6), math.floor(num(call(a, "getZ")) or 0)
    if pz ~= P.z then return false end
    for _, s in ipairs(P.access or {}) do if s.x == px and s.y == py then return true end end
    -- vanilla: already within reach (walkToContainer: DistToProper < 2), with no wall, door or window in between
    if math.max(math.abs(px - P.x), math.abs(py - P.y)) <= 1 and not (px == P.x and py == P.y) then
        local SP = place()
        if SP and not SP.reach(px, py, pz, P.x, P.y) then return false end           -- spatial_access: not across a fence or a shut door
        return call(call(a, "getCurrentSquare"), "canReachTo", P.sq) == true
    end
    return false
end

local function labels()
    local out, sc = {}, SC()
    local BL = sc and sc.BaseLife
    if not (BL and type(BL.storageRows) == "function") then return out end
    local ok, rows = pcall(BL.storageRows, nil)
    for _, s in ipairs(ok and type(rows) == "table" and rows or {}) do
        if type(s) == "table" and s.x and s.category then
            out[tostring(s.x) .. "," .. tostring(s.y) .. "," .. tostring(s.z or 0) .. "," .. tostring(s.objectIndex or 0)] = s.category
        end
    end
    return out
end

local function dist(a, b) return math.max(math.abs(a.x - b.x), math.abs(a.y - b.y)) + math.abs((a.z or 0) - (b.z or 0)) * 10 end

-- the roles of every container (one tick: counts only)
function M.roles(places, a)
    local lab = labels()
    for _, P in ipairs(places) do
        P.prefer, P.ok, P.dest, P.source = {}, {}, true, true
        local label = lab[tostring(P.x) .. "," .. tostring(P.y) .. "," .. tostring(P.z or 0) .. "," .. tostring(P.oi or 0)]
        P.label = label
        local cold = P.kind == "fridge" or P.kind == "freezer"
        P.powered = (not cold) or call(P.cont, "isPowered") == true
        if M.NO_TOUCH[P.kind] or label == "memorial" or P.unreach then P.dest, P.source = false, false
        elseif label and M.STAGING[label] then P.dest = false
        elseif label and M.LABEL[label] then
            for _, k in ipairs(M.LABEL[label]) do P.prefer[k] = 1 end
            if label == "food" and cold and P.powered then P.prefer.cold = 1 end
        else
            local byRoom = P.room and M.ROOM_TYPE[P.room] and M.ROOM_TYPE[P.room][P.kind] or nil
            for _, k in ipairs(byRoom or M.TYPE[P.kind] or {}) do
                if k ~= "cold" or P.powered then P.prefer[k] = 2 end
            end
        end
        if cold then P.ok.cold, P.ok.food, P.ok.water = true, true, true end           -- a dead fridge is not emptied either
        -- what it already holds: a box mostly of one kind is for that kind (the player's habit)
        local total, top, topN = 0, nil, 0
        for k, n in pairs(P.counts or {}) do total = total + n; if n > topN or (n == topN and top ~= nil and k < top) then top, topN = k, n end end
        if top and total >= M.MAJORITY_MIN and topN >= total * M.MAJORITY_SHARE and P.dest and P.source then
            P.ok[top] = true
            local any = false
            for _ in pairs(P.prefer) do any = true end
            if not any then P.prefer[top] = 3; P.majority = top end
        end
        for k in pairs(P.prefer) do P.ok[k] = true end
        P.cap = num(call(P.cont, "getEffectiveCapacity", a)) or num(call(P.cont, "getCapacity"))
        P.used = num(call(P.cont, "getCapacityWeight")) or num(call(P.cont, "getContentsWeight")) or 0
        P.reserved = 0
    end
    local has = {}
    for _, P in ipairs(places) do if P.dest then for k in pairs(P.prefer) do has[k] = true end end end
    return has
end

local function effective(key, has)
    local n = 0
    while key and not has[key] and n < 4 do key, n = M.FALLBACK[key], n + 1 end
    return key and has[key] and key or nil
end

-- the order a key's items fill its containers: label, type, majority; then where that kind already is; then the middle of the home
local function candidates(j, eff)
    if j.cands[eff] then return j.cands[eff] end
    local list = {}
    for _, P in ipairs(j.places) do if P.dest and P.prefer[eff] then list[#list + 1] = P end end
    local mid = j.mid
    table.sort(list, function(a, b)
        if a.prefer[eff] ~= b.prefer[eff] then return a.prefer[eff] < b.prefer[eff] end
        local na, nb = (a.counts or {})[eff] or 0, (b.counts or {})[eff] or 0
        if na ~= nb then return na > nb end
        local da, db = dist(a, mid), dist(b, mid)
        if da ~= db then return da < db end
        return a.i < b.i
    end)
    j.cands[eff] = list
    return list
end

local function free(P) if P.cap == nil then return math.huge end return P.cap - P.used - P.reserved end

local function pickDest(j, mv, exclude)
    for _, D in ipairs(candidates(j, mv.eff)) do
        if D ~= mv.src and not D.unreach and not (exclude and exclude[D]) and not (D.full and D.full[mv.eff]) and free(D) >= mv.w
            and call(D.cont, "isItemAllowed", mv.item) ~= false then
            D.reserved = D.reserved + mv.w
            return D
        end
    end
    return nil
end

-- ---------------------------------------------------------------- a round: the order she visits, each container once
local function carryFree(a)
    local inv = call(a, "getInventory")
    local cap = num(call(a, "getMaxWeight")) or num(call(inv, "getEffectiveCapacity", a)) or 15
    local used = num(call(inv, "getCapacityWeight")) or 0
    return math.max(M.CARRY_MIN, math.min(M.CARRY_MAX, cap - used))
end

function M.buildRound(j, a)
    S.stats.rounds = S.stats.rounds + 1
    local here = { x = num(call(a, "getX")) or 0, y = num(call(a, "getY")) or 0, z = num(call(a, "getZ")) or 0 }
    local cap = carryFree(a)
    local load, carried = 0, {}
    for _, mv in ipairs(j.moves) do if mv.state == "carried" then carried[#carried + 1] = mv; load = load + mv.w end end
    local visited, stops, pending = {}, {}, {}
    for _, mv in ipairs(j.moves) do if mv.state == "todo" then pending[#pending + 1] = mv end end
    local picked = {}
    while #stops < M.MAX_STOPS do
        local low = (cap - load) < cap * 0.25
        local best, bestCost = nil, nil
        local nodes = {}
        for _, mv in ipairs(carried) do if not mv.put and not visited[mv.dst] then nodes[mv.dst] = true end end
        if not low then
            for _, mv in ipairs(pending) do
                if not picked[mv] and not visited[mv.src] and not visited[mv.dst] and mv.w <= cap - load then nodes[mv.src] = true end
            end
        end
        for P in pairs(nodes) do
            local cost = dist(here, P)
            if not low then
                for _, mv in ipairs(pending) do
                    if mv.dst == P and not picked[mv] and not visited[mv.src] and mv.src ~= P then cost = cost + 6 end
                end
            end
            if bestCost == nil or cost < bestCost or (cost == bestCost and P.i < best.i) then best, bestCost = P, cost end
        end
        if best == nil then break end
        local stop = { P = best, put = {}, take = {} }
        for _, mv in ipairs(carried) do if mv.dst == best and not mv.put then stop.put[#stop.put + 1] = mv; mv.put = true; load = load - mv.w end end
        visited[best] = true
        for _, mv in ipairs(pending) do
            if mv.src == best and not picked[mv] and not visited[mv.dst] and mv.w <= cap - load then
                stop.take[#stop.take + 1] = mv; picked[mv] = true; carried[#carried + 1] = mv; load = load + mv.w
            end
        end
        stops[#stops + 1] = stop
        here = best
    end
    -- cut by MAX_STOPS: a pick whose container is not in this round waits for the next
    local at = {}
    for i, st in ipairs(stops) do at[st.P] = i end
    for i, st in ipairs(stops) do
        local keep = {}
        for _, mv in ipairs(st.take) do if at[mv.dst] and at[mv.dst] > i then keep[#keep + 1] = mv end end
        st.take = keep
    end
    for _, mv in ipairs(j.moves) do mv.put = nil end
    j.stops, j.si = stops, 1
    return #stops
end

-- ---------------------------------------------------------------- walking (as the farm: arrived when she stands where it can be reached)
function M.walk(j, a, P)
    local w = j.w
    if w == nil or w.P ~= P then w = { P = P, attempt = 0, tried = {} }; j.w = w end
    if M.arrived(a, P) then j.w = nil; return "arrived" end
    if type(U.solGoto) ~= "function" or #(P.access or {}) == 0 then j.w = nil; return "failed" end
    local t = nowMs()
    local here = tostring(math.floor(num(call(a, "getX")) or 0)) .. "," .. tostring(math.floor(num(call(a, "getY")) or 0))
    if w.sent ~= nil then
        if here ~= w.here then w.here, w.movedAt = here, t end                              -- a new square: she is getting there
        if t - w.movedAt < M.STALL_MS and t - w.started < M.WALK_MS then return "walking" end
        if w.attempt >= M.WALK_ATTEMPTS or t - w.started >= M.WALK_MS then
            log("cannot reach " .. P.kind .. " " .. tostring(P.x) .. "," .. tostring(P.y) .. " after " .. tostring(w.attempt) .. " attempts")
            j.w = nil
            return "failed"
        end
    end
    -- one order: the nearest standing square not tried yet (vanilla: the closest one)
    local px, py = num(call(a, "getX")) or 0, num(call(a, "getY")) or 0
    local best, bd
    for _, s in ipairs(P.access) do
        local d = (s.x + 0.5 - px) * (s.x + 0.5 - px) + (s.y + 0.5 - py) * (s.y + 0.5 - py) + (w.tried[s] and 1e6 or 0)
        if bd == nil or d < bd then best, bd = s, d end
    end
    w.attempt, w.tried[best] = w.attempt + 1, true
    w.started = w.started or t
    w.sent, w.movedAt, w.here = t, t, here
    pcall(U.solGoto, best.x, best.y, best.z)
    return "walking"
end

local LOOT_POS = { overhead = "High", shelves = "Mid", metal_shelves = "Mid", fridge = "Mid", freezer = "Low", counter = "Mid", wardrobe = "Mid",
    crate = "Low", militarycrate = "Low", dresser = "Low", sidetable = "Low", desk = "Mid", toolcabinet = "Mid", medicine = "High" }
local function animate(a, P)
    call(a, "faceLocation", P.x + 0.5, P.y + 0.5)
    call(a, "SetVariable", "LootPosition", LOOT_POS[P.kind] or "Mid")
    call(a, "reportEvent", "EventLootItem")
end

local function danger(a)
    local gu = GU()
    local okS, st = false, nil
    if gu and type(gu.peekActorState) == "function" then okS, st = pcall(gu.peekActorState, a) end
    local threats = okS and type(st) == "table" and type(st.snapshot) == "table" and st.snapshot.threats or nil
    if type(threats) ~= "table" then return false end
    for i = 1, math.min(#threats, 32) do
        if (num(threats[i].distanceSq) or 1e12) <= M.DANGER_TILES * M.DANGER_TILES then return true end
    end
    return false
end

-- ---------------------------------------------------------------- the runner
function M.held() return S.job ~= nil end
U.solSortHeld = M.held
function M.carrying()
    local n = 0
    for _, mv in ipairs(S.job and S.job.moves or {}) do if mv.state == "carried" then n = n + 1 end end
    return n
end

local work                                                                          -- this tick's allowance, counted
local function spend(kind, n) work[kind] = (work[kind] or 0) + (n or 1); S.stats.max = S.stats.max or {}; if work[kind] > (S.stats.max[kind] or 0) then S.stats.max[kind] = work[kind] end end

local function summaryText()
    local j = S.job
    local total, byKey = 0, {}
    for _, mv in ipairs(j.moves or {}) do
        if mv.state == "done" then
            total = total + 1
            local b = byKey[mv.eff] or { n = 0, dst = {} }
            byKey[mv.eff] = b
            b.n = b.n + 1
            b.dst[mv.dst] = (b.dst[mv.dst] or 0) + 1
        end
    end
    local left = (j.unplaced or 0)
    for _, mv in ipairs(j.moves or {}) do if mv.state == "todo" or mv.state == "failed" or mv.state == "back" then left = left + 1 end end
    local more = (j.capped or 0) > 0 and string.format(W.more, M.count(j.capped)) or ""
    if j.unreach and #j.unreach > 0 then more = more .. string.format(W.unreach, M.toBoxes(#j.unreach)) end
    if total == 0 then return W.summaryNone .. (left > 0 and string.format(W.left, M.count(left)) or "") .. more, 0 end
    local keys = {}
    for k in pairs(byKey) do keys[#keys + 1] = k end
    table.sort(keys, function(a, b) if byKey[a].n ~= byKey[b].n then return byKey[a].n > byKey[b].n end return a < b end)
    local parts = {}
    for i = 1, math.min(3, #keys) do
        local b, bestP, bestN = byKey[keys[i]], nil, 0
        for P, n in pairs(b.dst) do if n > bestN or (n == bestN and bestP and P.i < bestP.i) then bestP, bestN = P, n end end
        parts[#parts + 1] = M.CAT_SUM[keys[i]] .. " " .. M.toName(bestP)
    end
    return string.format(W.summary, M.count(total), table.concat(parts, W.sep)) .. (left > 0 and string.format(W.left, M.count(left)) or "") .. more, total
end

local function finish(a, why)
    local j = S.job
    local text, total = summaryText()
    S.summary, S.moved = text, total
    if why == "nothing" then say(a, W.nothing .. ((j.unreach and #j.unreach > 0) and string.format(W.unreach, M.toBoxes(#j.unreach)) or ""), "summary")
    elseif why == "stopped" or why == "danger" then
        if total > 0 then say(a, string.format(W.stoppedMoved, M.count(total)), "summary")
        elseif not j.acked then say(a, W.stopped, "summary") end
    else say(a, text, "summary") end
    log("done " .. why .. " moved=" .. tostring(total) .. " rounds=" .. tostring(j.round or 0))
    S.last = { key = "done", text = why .. " moved=" .. tostring(total) }
    S.job = nil
end

-- the last resort for one item in her hands: back into its own container, else on the floor where she stands. Never kept.
local function letGo(a, mv, gu, inv)
    if gu and gu.transferItemVerified(inv, mv.src.cont, mv.item) == true then mv.state = "back"; return end
    local sq = call(a, "getCurrentSquare") or call(a, "getSquare")
    call(inv, "Remove", mv.item)
    if sq then call(sq, "AddWorldInventoryItem", mv.item, 0.5, 0.5, 0) end
    mv.state = "floor"
    log("put on the floor " .. tostring(call(mv.item, "getFullType")))
end

-- everything in her hands goes back, now (switch off, an error, a container she cannot reach any more)
local function returnNow(a)
    local j = S.job
    local gu, inv = GU(), call(a, "getInventory")
    for _, mv in ipairs(j and j.moves or {}) do
        if mv.state == "carried" then letGo(a, mv, gu, inv) end
    end
end

local PHASE = {}

function PHASE.wait_inv(j, a)
    if type(U.invLast) == "function" and U.invLast() ~= nil then j.phase = "scan"; return end
    if nowMs() - j.at > M.INV_WAIT_MS then return finish(a, "no_scan") end
end

function PHASE.scan(j, a)
    if j.places == nil then
        j.raw = U.invLast().places or {}
        j.places, j.ri, j.items, j.ii = {}, 1, {}, 1
    end
    local n = 0
    while j.ri <= #j.raw and n < M.SCAN_PER_TICK do
        local p = j.raw[j.ri]; j.ri = j.ri + 1; n = n + 1
        spend("scan")
        local cont, sq = placeContainer(p)
        if cont and sq and (p.kind == nil or tostring(call(cont, "getType") or p.kind) == p.kind) then
            local P = { i = #j.places + 1, x = p.x, y = p.y, z = p.z or 0, oi = p.oi, ci = p.ci, kind = tostring(p.kind or ""), room = p.room,
                cont = cont, sq = sq, counts = {} }
            j.places[#j.places + 1] = P
            if not M.NO_TOUCH[P.kind] then
                P.access = M.access(P)
                if #P.access == 0 then
                    P.unreach = true
                    j.unreach = j.unreach or {}
                    j.unreach[#j.unreach + 1] = P
                    log("no standing square " .. P.kind .. " " .. tostring(P.x) .. "," .. tostring(P.y))
                end
            end
            if not M.NO_TOUCH[P.kind] then
                local list = call(cont, "getItems")
                local cnt = num(list and call(list, "size")) or 0
                for i = 0, cnt - 1 do
                    local it = call(list, "get", i)
                    if it ~= nil then j.items[#j.items + 1] = { item = it, src = P } end
                end
            end
        end
    end
    if j.ri > #j.raw then j.phase = "classify" end
end

function PHASE.classify(j, a)
    local n = 0
    while j.ii <= #j.items and n < M.ITEMS_PER_TICK do
        local r = j.items[j.ii]; j.ii = j.ii + 1; n = n + 1
        spend("items")
        r.key = M.keyOf(r.item)
        if r.key then
            r.src.counts[r.key] = (r.src.counts[r.key] or 0) + 1
            r.movable = M.movable(r.item, a)
        end
    end
    if j.ii > #j.items then j.phase = "roles" end
end

function PHASE.roles(j, a)
    j.has = M.roles(j.places, a)
    local sx, sy, sz, n = 0, 0, 0, 0
    for _, P in ipairs(j.places) do sx, sy, sz, n = sx + P.x, sy + P.y, sz + P.z, n + 1 end
    j.mid = n > 0 and { x = sx / n, y = sy / n, z = math.floor(sz / n + 0.5) } or { x = 0, y = 0, z = 0 }
    j.cands, j.moves, j.pi, j.unplaced = {}, {}, 1, 0
    S.stats.plans = S.stats.plans + 1
    j.phase = "plan"
end

function PHASE.plan(j, a)
    local n = 0
    while j.pi <= #j.items and n < M.PLAN_PER_TICK do
        local r = j.items[j.pi]; j.pi = j.pi + 1; n = n + 1
        spend("plan")
        if r.key and r.movable and r.src.source then
            local eff = effective(r.key, j.has)
            if eff and not r.src.ok[r.key] and not r.src.ok[eff] then
                if #j.moves >= M.MAX_MOVES then j.capped = (j.capped or 0) + 1
                else
                    local mv = { item = r.item, src = r.src, key = r.key, eff = eff, w = weightOf(r.item), state = "todo" }
                    mv.dst = pickDest(j, mv)
                    if mv.dst then j.moves[#j.moves + 1] = mv else j.unplaced = j.unplaced + 1 end
                end
            end
        end
    end
    if j.pi > #j.items then
        j.items = nil                                                                   -- the plan holds what it needs
        if #j.moves == 0 then return finish(a, "nothing") end
        say(a, #j.moves == 1 and W.planOne or string.format(W.planMany, M.count(#j.moves)), "plan")
        j.round, j.phase = 0, "round"
    end
end

function PHASE.round(j, a)
    -- what she could not put down last round: another container of its kind, else back where it came from
    for _, mv in ipairs(j.moves) do
        if mv.state == "carried" and mv.retry then
            local d = pickDest(j, mv, mv.tried)
            mv.dst, mv.retry = d or mv.src, nil
            if d == nil then mv.home = true end
        end
    end
    local pending = 0
    for _, mv in ipairs(j.moves) do if mv.state == "todo" or mv.state == "carried" then pending = pending + 1 end end
    if pending == 0 then return finish(a, "all_in_place") end
    if j.round >= M.MAX_ROUNDS then
        if M.carrying() > 0 then j.phase, j.why = "unload", "rounds"; return end
        return finish(a, "rounds")
    end
    j.round = j.round + 1
    if M.buildRound(j, a) == 0 then
        if M.carrying() > 0 then j.phase, j.why = "unload", "stuck"; return end
        return finish(a, "stuck")
    end
    j.phase = "go"
end

function PHASE.go(j, a)
    local st = j.stops[j.si]
    if st == nil then j.phase = "round"; return end
    local w = M.walk(j, a, st.P)
    if w == "walking" then return end
    if w == "failed" then                                                                -- skipped for the rest of this order, named in the summary
        local P = st.P
        if not P.unreach then P.unreach = true; j.unreach = j.unreach or {}; j.unreach[#j.unreach + 1] = P end
        if not j.saidCannot then say(a, string.format(W.cannot, M.toName(P)), "cannot"); j.saidCannot = true end
        for _, mv in ipairs(st.put) do mv.retry = true; mv.tried = mv.tried or {}; mv.tried[P] = true end
        for _, mv in ipairs(j.moves) do
            if mv.state == "todo" and mv.src == P then mv.state = "failed"
            elseif mv.state == "todo" and mv.dst == P then
                mv.dst = pickDest(j, mv, { [P] = true })
                if mv.dst == nil then mv.state = "failed" end
            end
        end
        j.si = j.si + 1
        return
    end
    S.visits = S.visits or {}
    S.visits[#S.visits + 1] = { place = st.P.i, round = j.round, put = #st.put, take = #st.take }
    j.queue, j.qi, j.stopAt, j.animAt = {}, 1, nowMs(), 0
    for _, mv in ipairs(st.put) do j.queue[#j.queue + 1] = { mv = mv, put = true } end
    for _, mv in ipairs(st.take) do j.queue[#j.queue + 1] = { mv = mv } end
    local kg = 0                                                                         -- vanilla's shape (50 ticks x weight, capped at 3 kg), much shorter
    for _, q in ipairs(j.queue) do kg = kg + math.max(0.3, math.min(3, q.mv.w)) end
    j.stopMs = math.min(M.STOP_MAX_MS, M.STOP_BASE_MS + M.ITEM_MS * kg)
    if #st.put > 0 then                                                                  -- "\\u0639\\u0645 \\u0631\\u062A\\u0651\\u0628 \\u0627\\u0644\\u0623\\u0643\\u0644 \\u0628\\u0627\\u0644\\u0645\\u0637\\u0628\\u062E": what most of it is, and where
        local byKey, top, topN = {}, nil, 0
        for _, mv in ipairs(st.put) do byKey[mv.eff] = (byKey[mv.eff] or 0) + 1 end
        for k, c in pairs(byKey) do if c > topN or (c == topN and k < top) then top, topN = k, c end end
        local line = string.format(W.progress, M.CAT_AR[top], M.inName(st.P))
        if line ~= j.lastLine and nowMs() - (j.saidAt or -1e9) >= M.SAY_GAP_MS then say(a, line, "progress"); j.lastLine, j.saidAt = line, nowMs() end
    end
    j.phase = "work"
end

function PHASE.work(j, a)
    local st = j.stops[j.si]
    local P, gu, inv = st.P, GU(), call(a, "getInventory")
    if nowMs() - j.animAt >= 1200 and j.qi <= #j.queue then animate(a, P); j.animAt = nowMs() end
    local n = 0
    while j.qi <= #j.queue and n < M.MOVES_PER_TICK do
        local q = j.queue[j.qi]; j.qi = j.qi + 1; n = n + 1
        spend("moves")
        local mv = q.mv
        if q.put then
            if mv.state == "carried" then
                local room = call(P.cont, "hasRoomFor", a, mv.item) ~= false and call(P.cont, "isItemAllowed", mv.item) ~= false
                if room and gu.transferItemVerified(inv, P.cont, mv.item) == true then
                    mv.state = mv.home and "back" or "done"
                else
                    mv.retry = true; mv.tried = mv.tried or {}; mv.tried[P] = true
                    P.full = P.full or {}; P.full[mv.eff] = true
                end
            end
        elseif mv.state == "todo" then
            local holder = call(mv.item, "getContainer")
            if holder ~= nil and holder ~= P.cont then mv.state = "failed"                -- someone took it meanwhile
            elseif call(inv, "hasRoomFor", a, mv.item) == false then                       -- her hands are full: next round
            elseif gu.transferItemVerified(P.cont, inv, mv.item) == true then mv.state = "carried"
            else mv.state = "failed" end
        end
    end
    if j.qi > #j.queue and nowMs() - j.stopAt >= j.stopMs then
        call(P.cont, "setDrawDirty", true)
        j.si = j.si + 1
        j.phase = "go"
    end
end

-- stop, danger or the last round: what is in her hands goes back where it came from, walking
function PHASE.unload(j, a)
    local mv
    for _, m in ipairs(j.moves) do if m.state == "carried" then mv = m; break end end
    if mv == nil then return finish(a, j.why or "stopped") end
    local w = M.walk(j, a, mv.src)
    if w == "walking" then return end
    if w == "failed" then log("unload: cannot reach, put back directly"); return returnNow(a) end
    animate(a, mv.src)
    local gu, inv = GU(), call(a, "getInventory")
    for _, m in ipairs(j.moves) do
        if m.state == "carried" and m.src == mv.src then letGo(a, m, gu, inv) end
    end
end

function M.step(a)
    local j = S.job
    if (j.phase == "go" or j.phase == "work") and danger(a) then
        j.dangerAt = j.dangerAt or nowMs()
        if nowMs() - j.dangerAt > M.DANGER_WAIT_MS then say(a, W.danger, "danger"); j.phase, j.why, j.acked, j.dangerAt = "unload", "danger", true, nil end
        return
    end
    j.dangerAt = nil
    if (j.phase == "go" or j.phase == "work" or j.phase == "round") and nowMs() - j.at > M.MAX_MS then
        if M.carrying() > 0 then j.phase, j.why = "unload", "time" else return finish(a, "time") end
    end
    local f = PHASE[j.phase]
    if f then f(j, a) end
end

function M.tick()
    if not S.job then return end
    local a = actor()
    if not on() then
        if a then pcall(returnNow, a) end
        log("switch off")
        S.job = nil
        return
    end
    if not a then return end
    work = {}
    local ok, err = pcall(M.step, a)
    if not ok then
        log("error " .. tostring(err))
        pcall(returnNow, a)
        S.job = nil
    end
end

function M.order(option)
    if not on() then return false, "switch_off" end
    option = tostring(option or "")
    local a = actor()
    if option == "stop" then
        local j = S.job
        if j == nil then return true, "idle" end
        if M.carrying() > 0 then
            j.phase, j.why, j.acked = "unload", "stopped", true
            say(a, W.stopped, "stopped")
            return true, "stopping"
        end
        finish(a, "stopped")
        return true, "stopped"
    end
    if option == "status" then
        local j = S.job
        return true, string.format("job=%s round=%s moves=%s carried=%d last=%s", j and j.phase or "none", tostring(j and j.round or 0),
            tostring(j and j.moves and #j.moves or 0), M.carrying(), S.last and (S.last.key .. " " .. tostring(S.last.text or "")) or "-")
    end
    if option == "run" or option == "" then
        if S.job then return true, "already" end
        S.visits, S.summary = {}, nil
        S.job = { phase = "scan", at = nowMs() }
        if type(U.invLast) ~= "function" or U.invLast() == nil then
            if type(U.invStart) == "function" then pcall(U.invStart) end
            S.job.phase = "wait_inv"
            say(a, W.waitInv, "wait")
            return true, "scanning_home"
        end
        say(a, W.start, "start")
        return true, "started"
    end
    return false, "unknown_option"
end

function M.install()
    if M._installed then return end
    M._installed = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_sort" then return M.order(option) end
        return base(id, option)
    end
    local budget = g("SolBudget")
    if type(budget) == "table" and type(budget.register) == "function" then
        budget.register("sol_sort", function() pcall(M.tick) end, { everyMs = M.TICK_MS, priority = 6 })
    elseif Events and Events.OnTick then
        local nextAt = 0
        Events.OnTick.Add(function() local t = nowMs(); if t < nextAt then return end; nextAt = t + M.TICK_MS; pcall(M.tick) end)
    end
    log("ready v" .. M.VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(M.install) end
return M
