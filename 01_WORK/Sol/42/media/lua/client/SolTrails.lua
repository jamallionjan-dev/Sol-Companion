-- SolTrails.lua - lets the road planner see dirt roads.
--   The game's street data lists paved streets only. media/maps/Sol_Trails/streets.xml holds the dirt roads, generated from
--   the game's own world map by 05_TOOLS/sol_trails/gen_trails.py. They are loaded into a street source of our own, next
--   to the game's streets, so street names and Living Fellows' own lookups stay exactly as they were.
--   The planner asks here first and falls back to the paved network when a route cannot be made. Switch: "gps_trails".
SolTrails = SolTrails or {}
local T = SolTrails
T.FILE = "media/maps/Sol_Trails/streets.xml"
local cached, failed = nil, false

local function enabled()
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("gps_trails") == true
end

local function build()
    local uiType = rawget(_G, "UIWorldMap")
    if uiType == nil or type(uiType.new) ~= "function" then return nil end
    local mapUtils = rawget(_G, "MapUtils")
    if type(mapUtils) ~= "table" or type(mapUtils.initDefaultStreetData) ~= "function" then
        if type(require) == "function" then require "ISUI/Maps/ISMapDefinitions" end
        mapUtils = rawget(_G, "MapUtils")
    end
    if type(mapUtils) ~= "table" or type(mapUtils.initDefaultStreetData) ~= "function" then return nil end
    local owner = {}
    local javaObject = uiType.new(owner)
    if javaObject == nil then return nil end
    local ui = { owner = owner, javaObject = javaObject }
    mapUtils.initDefaultStreetData(ui)
    local api = javaObject:getAPIv3():getStreetsAPI()
    local paved = api:getStreetDataCount()
    api:addStreetData(T.FILE)
    print("[SolTrails] dirt roads added to a street source of " .. tostring(paved) .. " paved files")
    T.ui = ui        -- the map object must stay alive while its street source is used
    return api
end

function T.api()
    if cached ~= nil then return enabled() and cached or nil end
    if failed or not enabled() then return nil end
    local ok, api = pcall(build)
    if ok and api ~= nil then cached = api; return api end
    failed = true
    print("[SolTrails] could not load dirt roads: " .. tostring(api))
    return nil
end
