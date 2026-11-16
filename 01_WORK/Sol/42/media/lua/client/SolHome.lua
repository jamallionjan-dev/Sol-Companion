-- SolHome.lua - Sol's own home, set by the player ("this is home"), without Living Fellows' base registration.
--   Stored in the save's global ModData, so it survives reloads. Used when Living Fellows has no active base:
--   SolInventory scans this area (her knowledge of the store room), SolOrders drives here for "go home",
--   and the world snapshot carries it so Sol Mind's memory can take it over.
SolUI = SolUI or {}
SolHome = SolHome or {}
local H = SolHome
H.VERSION = "0.1.0"
H.DEFAULT_RADIUS = 20
local KEY = "SolHome"
local function log(m) print("[SolHome] " .. tostring(m)) end

local function store()
    if type(ModData) ~= "table" or type(ModData.getOrCreate) ~= "function" then return nil end
    local ok, t = pcall(ModData.getOrCreate, KEY)
    if ok and type(t) == "table" then return t end
    return nil
end

local function enabled() return type(SolAuthority) ~= "table" or type(SolAuthority.on) ~= "function" or SolAuthority.on("sol_home") end   -- Sol fix 7
H.enabled = enabled

function H.get()
    if not enabled() then return nil end
    local t = store()
    if t and type(t.x) == "number" and type(t.y) == "number" then
        return { x = t.x, y = t.y, z = t.z or 0, radius = t.radius or H.DEFAULT_RADIUS }
    end
    return nil
end

-- "this is home": the player's square, a square area of `radius` tiles around it
function H.setHere(radius)
    local p = getSpecificPlayer and getSpecificPlayer(0) or nil
    if not p then return false, "no_player" end
    if not enabled() then return false, "fix_off" end
    local t = store()
    if not t then return false, "no_moddata" end
    t.x, t.y, t.z = math.floor(p:getX()), math.floor(p:getY()), math.floor(p:getZ())
    t.radius = tonumber(radius) or H.DEFAULT_RADIUS
    t.setAt = getTimestampMs and getTimestampMs() or 0
    log("home set at " .. t.x .. "," .. t.y .. "," .. t.z .. " radius=" .. t.radius)
    if SolUI.invStart then pcall(SolUI.invStart) end          -- learn what is stored there right away
    return true, "home_set"
end

-- the area as SolInventory's rectangles
function H.rects()
    local h = H.get()
    if not h then return {} end
    local r = h.radius
    return { { x1 = h.x - r, x2 = h.x + r, y1 = h.y - r, y2 = h.y + r, z = h.z } }
end
