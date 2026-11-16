-- SolActions.lua - Sol's body: the list of things the brain may ask her to do, built from the game itself.
--  * Living Fellows actions: every button / choice / tick of Sol's Orders and Loadout pages that issues an LF
--    command (follow, stay, guard, regroup, retreat, board / exit vehicle, move mode walk / sneak / run, combat
--    doctrine, hold fire, scavenging, weapon priority, base job, bandage ...). Executing one calls the same LF
--    callback the button calls, so LF's own availability rules and reasons apply.
--  * Sol actions: drive (SolGPS), read a book (ISReadABook), attack the nearest zombie (LF designate_target).
-- The catalog goes to SolActions_Snapshot.txt; Sol Mind sends SolAct_Request.txt and reads SolAct_State.txt.
require "SolText"
SolUI = SolUI or {}
local U = SolUI
U.ACTIONS_VERSION = "0.4.2"
local SNAP, REQ, STATE = "SolActions_Snapshot.txt", "SolAct_Request.txt", "SolAct_State.txt"
local PAGES = { "orders", "loadout" }
local function log(m) print("[SolActions] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function LF() local sc = SurvivorCompanion; return type(sc) == "table" and sc or nil end

-- ---------------------------------------------------------------- catalog
function U.actionCatalog(pre)       -- s99 perf_slice: pre = the pages already read (one a frame); nil = read them now, as before
    local out, seen = {}, {}
    for _, page in ipairs(PAGES) do
        local items
        if type(pre) == "table" then items = pre[page] else items = U.extractPage and U.extractPage(page) or nil end
        local section = ""
        for _, it in ipairs(items or {}) do
            if it.kind == "section" then section = it.text
            elseif it.command and not seen[it.command .. "|" .. (it.kind == "button" and it.text or "")] then
                seen[it.command .. "|" .. (it.kind == "button" and it.text or "")] = true
                local e = { id = it.command, kind = it.kind, page = page, section = section }
                if it.kind == "button" then e.label = it.text; e.enabled = it.enabled; e.reason = it.tip
                elseif it.kind == "combo" then e.options = it.options; e.selected = it.selected
                elseif it.kind == "tick" then e.options = {}; for i, o in ipairs(it.options) do e.options[i] = o.text end; e.on = it.options[1] and it.options[1].on end
                out[#out + 1] = e
            end
        end
    end
    out[#out + 1] = { id = "sol_drive", kind = "sol", label = "start driving to the destination already selected on Sol GPS; she takes the driver seat first and waits for the player to board when nearby" }
    out[#out + 1] = { id = "sol_headlights", kind = "sol", label = "switch the car's headlights; option: on / off / toggle (her car, else the player's car, else the nearest one)" }
    out[#out + 1] = { id = "sol_engine", kind = "sol", label = "start or stop the car's engine; option: on / off (on needs her in the driver seat)" }
    out[#out + 1] = { id = "sol_car_wait", kind = "sol", label = "turn the engine off and stay seated in the car waiting for the player" }
    out[#out + 1] = { id = "sol_horn", kind = "sol", label = "the car horn; option: once / drive (sounds for the whole trip) / stop" }
    out[#out + 1] = { id = "sol_gps_clear", kind = "sol", label = "take the destination off Sol's GPS" }
    out[#out + 1] = { id = "sol_fuel", kind = "sol", label = "fuel pumps; used by the refuel goals, not called alone" }
    out[#out + 1] = { id = "sol_read", kind = "sol", label = "read a book or magazine from Sol's bag" }
    out[#out + 1] = { id = "sol_attack_nearest", kind = "sol", label = "attack the nearest zombie (designate target)" }
    out[#out + 1] = { id = "sol_eat", kind = "sol", label = "eat now: the food in her bag that spoils first (game eat action)" }
    out[#out + 1] = { id = "sol_drink", kind = "sol", label = "drink now from a bottle of clean water in her bag (game drink action)" }
    out[#out + 1] = { id = "sol_give", kind = "sol", label = "hand the player items from her bag (into the player's inventory or worn bag); option: water / food / all / mine (what the player gave her) / an English item name" }
    out[#out + 1] = { id = "sol_bandage_player", kind = "sol", label = "bandage the player's wound (LF medical care)" }
    out[#out + 1] = { id = "sol_replace_bandage", kind = "sol", label = "replace her own dirty bandage (LF medical care)" }
    out[#out + 1] = { id = "sol_go_inside", kind = "sol", label = "walk inside the nearest building (out of the cold / rain); option: home to prefer the saved home" }
    out[#out + 1] = { id = "sol_goto", kind = "sol", label = "walk to a place; option: x,y (Sol Mind fills it for home or a remembered place)" }
    out[#out + 1] = { id = "sol_fetch", kind = "sol", label = "walk to a nearby container, take an item and come back; option: book, book:read, food, water or an English item name" }
    if U.fetchJob then out[#out].state = U.fetchJob.phase .. (U.fetchJob.reason and (":" .. U.fetchJob.reason) or "") end
    return out
end

local DIRECT
local function hasWord(s, w) return w ~= nil and w ~= "" and string.find(tostring(s), tostring(w), 1, true) ~= nil end

-- run one action; option = option label (exact or contained), or "on"/"off" for ticks
function U.runAction(id, option)
    if (id == "follow" or id == "regroup") and type(SolOrders) == "table" and type(SolOrders.leaveCar) == "function" and type(SolAuthority) == "table" and SolAuthority.on("follow_exits_car") == true then
        local s = U.solActor and U.solActor() or nil
        local car = s and type(s.getVehicle) == "function" and s:getVehicle() or nil
        local me = getSpecificPlayer and getSpecificPlayer(0) or nil
        local mine = me and type(me.getVehicle) == "function" and me:getVehicle() or nil
        if car ~= nil and mine ~= car then
            print("[SolOrders] " .. tostring(id) .. ": she is in a car he is not in, she gets out first")
            if car:getDriver() == s and car:isEngineRunning() and type(U.solEngine) == "function" then pcall(U.solEngine, "off") end
            SolOrders.leaveCar()
            return true, "leaving_car_to_follow"
        end
    end
    if id == "sol_drive" then
        if SolOrders and type(SolOrders.driveDestination) == "function" then
            return SolOrders.driveDestination(option)
        end
        local g = type(U.gps) == "table" and U.gps or nil
        if not g or not g.dest then return false, "no_destination" end
        if type(U.gpsStart) ~= "function" then return false, "gps_unavailable" end
        return U.gpsStart(nil, false)
    end
    if id == "sol_headlights" then return U.solHeadlights(option) end
    if id == "sol_engine" then return U.solEngine(option) end
    if id == "sol_car_wait" then return U.solCarWait() end
    if id == "sol_horn" then return U.solHorn(option) end
    if id == "sol_gps_clear" and type(U.gpsClear) == "function" then return U.gpsClear(option) end
    if id == "sol_fuel" and type(U.solFuel) == "function" then return U.solFuel(option) end
    if id == "sol_far" and type(U.solFar) == "function" then return U.solFar(option) end
    if id == "sol_set_home" and type(SolHome) == "table" and type(SolHome.setHere) == "function" then return SolHome.setHere() end
    if id == "sol_attack_nearest" then return U.attackNearest() end
    if id == "sol_eat" then return U.solEat() end
    if id == "sol_drink" then return U.solDrink() end
    if id == "sol_give" then return U.solGive(option) end
    if id == "sol_bandage_player" then return U.solBandagePlayer() end
    if id == "sol_replace_bandage" then return U.solReplaceBandage() end
    if id == "sol_fetch" then return U.solFetch(option) end
    if id == "sol_go_inside" then return U.solGoInside(option) end
    if id == "sol_goto" then
        local x, y = string.match(tostring(option or ""), "(%-?%d+)%s*,%s*(%-?%d+)")
        if not x then return false, "need_x_y" end
        return U.solGoto(tonumber(x), tonumber(y))
    end
    if id == "sol_read" then
        local books = U.solBooks and U.solBooks() or {}
        for _, b in ipairs(books) do if b.status == "useful" or b.status == "teaches" then return U.solRead(b.item) end end
        for _, b in ipairs(books) do if b.status == "fun" then return U.solRead(b.item) end end
        return false, "no_useful_book"
    end
    for _, page in ipairs(PAGES) do
        local items = U.extractPage and U.extractPage(page) or nil
        for _, it in ipairs(items or {}) do
            if it.command == id then
                if it.kind == "button" then
                    if option and option ~= "" and it.text ~= option and not hasWord(it.text, option) then
                        -- several buttons may share a command (e.g. LF signals); keep looking for the named one
                    else
                        if not it.enabled then return false, it.tip or "unavailable" end
                        return U.pressButton(it.ref), "pressed"
                    end
                elseif it.kind == "combo" then
                    for i, o in ipairs(it.options) do
                        if o == option or (option and hasWord(o, option)) then return U.chooseOption(it.ref, i), "chosen" end
                    end
                    return false, "unknown_option"
                elseif it.kind == "tick" then
                    local want = option ~= "off"
                    local cur = it.options[1] and it.options[1].on
                    if cur == want then return true, "already" end
                    return U.toggleTick(it.ref, 1), "toggled"
                end
            end
        end
    end
    -- not on Sol's pages right now: the plain LF commands (same ids the LF buttons and right-click menu issue)
    if DIRECT[id] then
        if U.extractPage then U.extractPage("orders") end
        local payload = nil
        if id == "board_vehicle" then
            local p = getSpecificPlayer and getSpecificPlayer(0)
            local veh = p and p.getVehicle and p:getVehicle() or U.nearestVehicle and U.nearestVehicle(30)
            if not veh then return false, "no_vehicle_near" end
            -- Keep Sol's vehicle job as the single owner of approach, boarding,
            -- retries, and the truthful completion reply.
            if SolOrders and type(SolOrders.board) == "function" then
                return SolOrders.board(veh)
            end
            payload = { vehicle = veh }
        end
        local ok, why = U.issueLF(id, payload)
        return ok, why or (ok and "issued" or "unavailable")
    end
    return false, "unknown_action"
end
DIRECT = { follow = true, stay = true, guard = true, regroup = true, retreat = true, cautious_follow = true, hold_fire = true,
           fire_at_will = true, bandage = true, board_vehicle = true, exit_vehicle = true }
function U.nearestVehicle(radius)
    -- Build 42.21: cell:getVehicles() is gone; use Living Fellows' Set-safe adapter (same as SolGPS nearestCar)
    local p = U.solActor and U.solActor() or (getSpecificPlayer and getSpecificPlayer(0))
    local SC = LF(); local service = SC and SC.Vehicle
    if not p or type(service) ~= "table" or type(service.loadedVehicles) ~= "function" then return nil end
    local ok, vehicles = pcall(service.loadedVehicles)
    if not ok or type(vehicles) ~= "table" then return nil end
    if type(U.solPickCar) == "function" and U.solCarRulesOn() then return (U.solPickCar(vehicles, p, radius or 30)) end
    local best, bd = nil, (radius or 30) ^ 2
    for _, v in ipairs(vehicles) do
        local okd, d = pcall(function() return (v:getX() - p:getX()) ^ 2 + (v:getY() - p:getY()) ^ 2 end)
        if okd and d < bd then best, bd = v, d end
    end
    return best
end

-- nearest zombie to Sol within 15 tiles -> LF designate_target (the same command the right-click menu issues)
-- The car's headlights: the same switch the vehicle menu flips. Her own car first (she is the one
-- asked), then the player's, then the nearest one. A car with no lights or a flat battery is said
-- plainly, never claimed done.
function U.solHeadlights(option)
    local function m(o, name, ...)
        if o == nil then return nil end
        local f = o[name]; if f == nil then return nil end
        local ok, v = pcall(f, o, ...); if ok then return v end; return nil
    end
    local s = type(U.solActor) == "function" and U.solActor() or nil
    local p = getSpecificPlayer and getSpecificPlayer(0) or nil
    local veh = m(s, "getVehicle") or m(p, "getVehicle") or (U.nearestVehicle and U.nearestVehicle(8)) or nil
    if veh == nil then return false, "no_vehicle_near" end
    if veh.setHeadlightsOn == nil then return false, "headlights_unavailable" end
    if m(veh, "hasHeadlights") == false then return false, "car_has_no_headlights" end
    local cur = m(veh, "getHeadlightsOn") == true
    local opt = string.lower(tostring(option or "on"))
    local want
    if opt == "off" or opt == "0" or opt == "false" then want = false
    elseif opt == "toggle" then want = not cur
    else want = true end
    if cur == want then return true, want and "already_on" or "already_off" end
    m(veh, "setHeadlightsOn", want)
    local now = m(veh, "getHeadlightsOn")
    if now ~= nil and now ~= want then return false, "battery_dead_or_refused" end
    log("headlights " .. (want and "on" or "off"))
    return true, want and "headlights_on" or "headlights_off"
end

-- Car orders by voice. Every game method is looked up before it is called (in debug mode a thrown Java error halts the game).
local function vcall(o, name, ...)
    if o == nil then return nil end
    local f = o[name]
    if f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function solCar()
    local s = type(U.solActor) == "function" and U.solActor() or nil
    return s, vcall(s, "getVehicle")
end
local function batteryEmpty(veh)
    local part = vcall(veh, "getPartById", "Battery")
    if part == nil then return false end                  -- this car reports no battery part: let the game decide
    local item = vcall(part, "getInventoryItem")
    if item == nil then return true, "no_battery" end
    local charge = vcall(item, "getCurrentUsesFloat")
    if type(charge) == "number" and charge <= 0 then return true, "battery_dead" end
    return false
end

-- option on / off
function U.solEngine(option)
    local s, veh = solCar()
    if veh == nil then return false, "not_in_a_car" end
    if string.lower(tostring(option or "on")) == "off" then
        local SC = LF()
        if SC and SC.Driving and type(SC.Driving.stop) == "function" then pcall(SC.Driving.stop, s, "player_order") end
        if vcall(veh, "isEngineRunning") ~= true then return true, "already_off" end
        if veh.shutOff == nil then return false, "engine_control_unavailable" end
        vcall(veh, "shutOff")
        log("engine off")
        return true, "engine_off"
    end
    if vcall(veh, "getDriver") ~= s then return false, "not_in_driver_seat" end
    if vcall(veh, "isEngineRunning") == true then return true, "already_on" end
    if veh.tryStartEngine == nil then return false, "engine_control_unavailable" end
    if vcall(veh, "isEngineWorking") == false then return false, "engine_broken" end
    local fuel = vcall(veh, "getRemainingFuelPercentage")
    if type(fuel) == "number" and fuel <= 0 then return false, "no_fuel" end
    local empty, why = batteryEmpty(veh)
    if empty then return false, why end
    local SC = LF()
    local drivingApi = type(SurvivorCompanion) == "table" and SurvivorCompanion.Driving or nil
    if type(drivingApi) == "table" and type(drivingApi.bringKeyToHand) == "function" then pcall(drivingApi.bringKeyToHand, s, veh) end
    local haveKey = false
    if SC and SC.Driving and type(SC.Driving.hasKey) == "function" then
        local ok, has = pcall(SC.Driving.hasKey, s, veh)
        haveKey = ok and has == true
    end
    if not haveKey and vcall(veh, "isHotwired") ~= true and vcall(veh, "isKeysInIgnition") ~= true then return false, "no_key" end
    vcall(veh, "tryStartEngine", haveKey)
    log("engine start requested key=" .. tostring(haveKey))
    return true, "engine_starting"
end

-- engine off, she keeps her seat and waits: no follow, no getting out, until the next car order
function U.solCarWait()
    local s, veh = solCar()
    if veh == nil then return false, "not_in_a_car" end
    local ok, why = U.solEngine("off")
    if not ok then return false, why end
    local A = rawget(_G, "SolAuthority")
    if type(A) == "table" and type(A.holdVehicle) == "function" then A.holdVehicle(veh, "wait_in_car") end
    local SC = LF()
    if SC and type(SC.Commands) == "table" and type(SC.Commands.issue) == "function" and type(SC.GameplayUtil) == "table"
            and type(SC.GameplayUtil.idOf) == "function" then
        local okId, id = pcall(SC.GameplayUtil.idOf, s)
        if okId and type(id) == "string" and id ~= "" then
            pcall(SC.Commands.issue, id, "stay", nil, getSpecificPlayer and getSpecificPlayer(0) or nil)
        end
    end
    log("waiting in the car")
    return true, "waiting_in_car"
end

local hornOffAt, hornTrip = nil, nil
local function hornOff(veh)
    if veh ~= nil then vcall(veh, "onHornStop") end
end
-- option once / drive / stop
function U.solHorn(option)
    local s, veh = solCar()
    local opt = string.lower(tostring(option or "once"))
    if opt == "stop" then
        if hornTrip then hornOff(hornTrip); hornTrip = nil end
        hornOffAt = nil
        hornOff(veh)
        return true, "horn_off"
    end
    if veh == nil then return false, "not_in_a_car" end
    if veh.onHornStart == nil or veh.onHornStop == nil then return false, "horn_unavailable" end
    local empty, why = batteryEmpty(veh)
    if empty then return false, why end
    vcall(veh, "onHornStart")
    if opt == "drive" then
        hornTrip, hornOffAt = veh, nil
        log("horn on for the trip")
        return true, "horn_on_for_trip"
    end
    hornOffAt = { at = nowMs() + 500, veh = veh }
    return true, "horn_beep"
end
function U.hornTick()
    if hornOffAt and nowMs() >= hornOffAt.at then hornOff(hornOffAt.veh); hornOffAt = nil end
    if hornTrip then
        local s, veh = solCar()
        local SC = LF()
        local D = SC and SC.Driving
        local driving = D and type(D.isDriving) == "function" and s ~= nil and select(2, pcall(D.isDriving, s)) == true
        local arrived = false
        if D and type(D.jobStatus) == "function" and s ~= nil then
            local okJ, js = pcall(D.jobStatus, s)
            arrived = okJ and type(js) == "table" and (js.result == "arrived" or js.result == "failed")
        end
        if veh ~= hornTrip or not driving or arrived then
            hornOff(hornTrip); hornTrip = nil
            log("horn off: the trip is over")
        end
    end
end

function U.attackNearest()
    local sol = U.solActor and U.solActor()
    if not sol or not U.issueLF then return false, "no_sol" end
    local cell = getCell and getCell()
    local zl = cell and cell.getZombieList and cell:getZombieList()
    local best, bd = nil, 15 * 15
    local sx, sy = sol:getX(), sol:getY()
    for i = 0, (zl and zl:size() or 0) - 1 do
        local z = zl:get(i)
        local d = (z:getX() - sx) ^ 2 + (z:getY() - sy) ^ 2
        if d < bd then best, bd = z, d end
    end
    if not best then return false, "no_zombie_near" end
    if U.extractPage then U.extractPage("orders") end
    return U.issueLF("designate_target", { target = best })
end

-- ---------------------------------------------------------------- her own body: eat / drink / give / care
-- The same game timed actions Living Fellows' needs system queues (SCNativeActions.lua 1901-1922):
--   ISEatFoodAction:new(actor, item, percentage) / ISDrinkFromBottle:new(actor, item, uses), then ISTimedActionQueue.add
local function mcall(o, name, ...) if o == nil then return nil end local f = o[name]; if not f then return nil end local ok, v = pcall(f, o, ...); if ok then return v end return nil end
local function bagItems(actor, seen)
    local out = {}
    local function walk(container, depth)
        if seen then seen[#seen + 1] = container end   -- s108 perf_hotspots: the containers this walk read
        local list = mcall(container, "getItems")
        local n = list and (tonumber((mcall(list, "size"))) or 0) or 0
        for i = 0, n - 1 do
            local it = mcall(list, "get", i)
            if it then
                out[#out + 1] = { item = it, container = container }
                local inner = mcall(it, "getInventory")
                if inner and depth < 2 then walk(inner, depth + 1) end
            end
        end
    end
    walk(mcall(actor, "getInventory"), 0)
    return out
end
U.solBagItems = bagItems
local function isFood(it)
    return instanceof and instanceof(it, "Food") and (tonumber((mcall(it, "getHungerChange"))) or 0) < 0
        and not mcall(it, "isRotten") and not mcall(it, "isFrozen") and not mcall(it, "isBurnt")
end
local function isCleanWater(it)
    local fc = mcall(it, "getFluidContainer")
    if not fc or mcall(fc, "isEmpty") then return false end
    local fl = mcall(fc, "getPrimaryFluid")
    local kind = tostring(fl and (mcall(fl, "getFluidTypeString") or mcall(fl, "toString")) or "")
    return string.find(kind, "Water", 1, true) ~= nil and string.find(kind, "Tainted", 1, true) == nil and not mcall(fl, "isPoisonous")
end
local function spoilsIn(it)
    local age, off = tonumber((mcall(it, "getAge"))), tonumber((mcall(it, "getOffAgeMax")))
    if age and off and off < 1e6 then return off - age end
    return 1e9
end
local function toRoot(actor, rec)
    local root = mcall(actor, "getInventory")
    if rec.container ~= root then
        if not pcall(function() rec.container:Remove(rec.item); root:AddItem(rec.item) end) then return false end
    end
    return true
end
local function queue(action) local ok, err = pcall(ISTimedActionQueue.add, action); return ok, ok and "started" or tostring(err) end
function U.solEat()
    local sol = U.solActor and U.solActor()
    if not sol or not ISEatFoodAction then return false, "eat_unavailable" end
    local best
    for _, rec in ipairs(bagItems(sol)) do
        if isFood(rec.item) and (not best or spoilsIn(rec.item) < spoilsIn(best.item)) then best = rec end
    end
    if not best then return false, "no_food_in_her_bag" end
    if not toRoot(sol, best) then return false, "cannot_take_food_out" end
    local ok, a = pcall(ISEatFoodAction.new, ISEatFoodAction, sol, best.item, 1)
    if not ok or not a then return false, "eat_action_failed" end
    local q, why = queue(a)
    return q, q and ("eating " .. tostring(mcall(best.item, "getDisplayName"))) or why
end
function U.solDrink()
    local sol = U.solActor and U.solActor()
    if not sol or not ISDrinkFromBottle then return false, "drink_unavailable" end
    for _, rec in ipairs(bagItems(sol)) do
        if isCleanWater(rec.item) then
            if not toRoot(sol, rec) then return false, "cannot_take_bottle_out" end
            local ok, a = pcall(ISDrinkFromBottle.new, ISDrinkFromBottle, sol, rec.item, 1)
            if not ok or not a then return false, "drink_action_failed" end
            local q, why = queue(a)
            return q, q and "drinking" or why
        end
    end
    return false, "no_clean_water_in_her_bag"
end
-- hand items to the player standing next to her (within 2.5 tiles): into the player's main inventory, or the
-- player's worn bag when the main inventory has no room; never dropped on the floor.
--   option: water / food / all / mine (what the player put in her bag) / an English item name
U.givenByPlayer = U.givenByPlayer or {}
local function roomIn(container, chr, item)
    if not container then return false end
    local f = container.hasRoomFor
    if type(f) ~= "function" then return true end
    local ok, r = pcall(f, container, chr, item)
    return not ok or r == true
end
local function playerDestination(p, item)
    local main = p:getInventory()
    if roomIn(main, p, item) then return main end
    local back = mcall(p, "getClothingItem_Back")
    local bagInv = back and mcall(back, "getInventory")
    if bagInv and roomIn(bagInv, p, item) then return bagInv end
    return nil
end
function U.solGive(what)
    local sol = U.solActor and U.solActor()
    local p = getSpecificPlayer and getSpecificPlayer(0)
    if not sol or not p then return false, "no_sol" end
    local d = math.sqrt((sol:getX() - p:getX()) ^ 2 + (sol:getY() - p:getY()) ^ 2)
    if d > 2.5 then return false, "too_far_to_hand_over" end
    local w = string.lower(tostring(what or ""))
    local picks = {}
    local best
    for _, rec in ipairs(bagItems(sol)) do
        local it = rec.item
        if mcall(it, "isEquipped") ~= true and mcall(it, "getInventory") == nil then
            local name = string.lower(tostring(mcall(it, "getDisplayName") or "") .. " " .. tostring(mcall(it, "getFullType") or ""))
            if w == "all" then picks[#picks + 1] = rec
            elseif w == "mine" then if U.givenByPlayer[it] then picks[#picks + 1] = rec end
            else
                local ok
                if w == "water" then ok = isCleanWater(it)
                elseif w == "food" or w == "" then ok = isFood(it)
                else ok = string.find(name, w, 1, true) ~= nil end
                if ok and (not best or (w == "food" and spoilsIn(it) < spoilsIn(best.item))) then best = rec end
            end
        end
    end
    if best then picks = { best } end
    if #picks == 0 then return false, (w == "mine" and "nothing_from_you" or "she_has_none") end
    local given, full = {}, false
    for _, rec in ipairs(picks) do
        local dest = playerDestination(p, rec.item)
        if not dest then full = true; break end
        if pcall(function() rec.container:Remove(rec.item); dest:AddItem(rec.item) end) then
            given[#given + 1] = tostring(mcall(rec.item, "getDisplayName"))
            U.givenByPlayer[rec.item] = nil
        end
    end
    if #given == 0 then return false, full and "your_bags_are_full" or "hand_over_failed" end
    return true, "gave " .. table.concat(given, ", ") .. (full and " (your bags are full for the rest)" or "")
end

-- what the player puts into her bag is remembered, so "give me back what I gave you" works
local lastSeen = nil
function U.trackGivenItems()
    local sol = U.solActor and U.solActor()
    if not sol then return end
    local H_ = rawget(_G, "SolPerfHotspots")   -- s108 perf_hotspots: her bag unchanged since the last walk = nothing new to remember
    local hot_ = type(H_) == "table" and type(H_.on) == "function" and H_.on() == true
    if hot_ and lastSeen ~= nil and H_.bagSame(sol) then return end
    local seen_ = hot_ and {} or nil
    local now = {}
    for _, rec in ipairs(bagItems(sol, seen_)) do now[rec.item] = true end
    if lastSeen then
        local p = getSpecificPlayer and getSpecificPlayer(0)
        local near = p and math.sqrt((sol:getX() - p:getX()) ^ 2 + (sol:getY() - p:getY()) ^ 2) <= 3
        for it in pairs(now) do if not lastSeen[it] and near then U.givenByPlayer[it] = true end end
    end
    lastSeen = now
    if seen_ then H_.bagMark(sol, seen_) elseif type(H_) == "table" then H_.bag = nil end
end

function U.solBandagePlayer()
    local SC = LF(); local M = SC and SC.Medical
    local sol = U.solActor and U.solActor(); local p = getSpecificPlayer and getSpecificPlayer(0)
    if not M or not sol or not p or type(M.applyPlayerBandage) ~= "function" then return false, "medical_unavailable" end
    if type(M.playerBandagePreflight) == "function" then
        local ok, why = M.playerBandagePreflight(sol, p)
        if not ok then return false, tostring(why or "no_bandage_possible") end
    end
    local ok, why = M.applyPlayerBandage(sol, p)
    return ok == true or ok == nil and true or false, why or "bandaging_you"
end
function U.solReplaceBandage()
    local SC = LF(); local M = SC and SC.Medical
    local sol = U.solActor and U.solActor()
    if not M or not sol or type(M.replaceDirtyBandage) ~= "function" then return false, "medical_unavailable" end
    if type(M.canReplaceDirtyBandage) == "function" and not M.canReplaceDirtyBandage(sol) then return false, "no_dirty_bandage_or_no_clean_one" end
    local ok, why = M.replaceDirtyBandage(sol)
    return ok ~= false, why or "replacing_bandage"
end

-- ---------------------------------------------------------------- fetch: walk to a container, take the item, come back
-- walking = LF's own navigation through the AI tool gateway ("go_to" -> LF command move_to);
-- taking = the game's ISInventoryTransferAction:new(character, item, srcContainer, destContainer, time)
local FETCH_RADIUS, WALK_TIMEOUT, TAKE_TIMEOUT = 18, 60000, 20000
local function bookKind(it)
    local sb = SkillBook and mcall(it, "getSkillTrained") and SkillBook[mcall(it, "getSkillTrained")]
    if sb then return "skill" end
    local lr = mcall(it, "getLearnedRecipes")
    if lr and (tonumber((mcall(lr, "size"))) or 0) > 0 then return "recipes" end
    if mcall(it, "IsLiterature") and not (ItemTag and mcall(it, "hasTag", ItemTag.UNINTERESTING)) then return "fun" end
    return nil
end
U.bookKind = bookKind
local function matches(it, what)
    if what == "book" then return bookKind(it) ~= nil end
    if what == "food" then return isFood(it) end
    if what == "water" then return isCleanWater(it) end
    local name = string.lower(tostring(mcall(it, "getDisplayName") or "") .. " " .. tostring(mcall(it, "getFullType") or ""))
    return string.find(name, string.lower(what), 1, true) ~= nil
end
local BOOK_RANK = { skill = 3, recipes = 2, fun = 1 }
function U.findNearby(what)
    local p = getSpecificPlayer and getSpecificPlayer(0)
    local cell = getCell and getCell()
    if not p or not cell then return nil end
    local px, py, pz = math.floor(p:getX()), math.floor(p:getY()), math.floor(p:getZ())
    local best, bestScore
    for x = px - FETCH_RADIUS, px + FETCH_RADIUS do
        for y = py - FETCH_RADIUS, py + FETCH_RADIUS do
            local sq = cell:getGridSquare(x, y, pz)
            local objs = sq and mcall(sq, "getObjects")
            local n = objs and (tonumber((mcall(objs, "size"))) or 0) or 0
            for i = 0, n - 1 do
                local o = mcall(objs, "get", i)
                local cc = tonumber((mcall(o, "getContainerCount"))) or 0
                for k = 0, cc - 1 do
                    local c = mcall(o, "getContainerByIndex", k)
                    local list = c and mcall(c, "getItems")
                    local m = list and (tonumber((mcall(list, "size"))) or 0) or 0
                    for j = 0, m - 1 do
                        local it = mcall(list, "get", j)
                        if it and matches(it, what) then
                            local dist = math.sqrt((x - px) ^ 2 + (y - py) ^ 2)
                            local score = (what == "book" and (BOOK_RANK[bookKind(it)] or 0) * 100 or 0) - dist
                            if not bestScore or score > bestScore then best, bestScore = { item = it, container = c, x = x, y = y, z = pz }, score end
                        end
                    end
                end
            end
        end
    end
    return best
end
local function gatewayGoTo(sol, x, y, z)
    local SC = LF(); local Gw = SC and SC.AIToolGateway
    if not Gw then return false, "gateway_unavailable" end
    local req = { requestId = "solfetch-" .. tostring(nowMs()), tool = "go_to", arguments = { x = x, y = y, z = z } }
    for _, name in ipairs({ "handle", "execute", "request", "run", "call", "dispatch" }) do
        if type(Gw[name]) == "function" then
            local ok, r = pcall(Gw[name], sol, req)
            if ok and type(r) == "table" then return r.accepted == true or r.ok == true or r.status == "accepted", tostring(r.reason or r.status or "") end
        end
    end
    -- fall back: LF's own command with a square payload
    local sq = getCell and getCell():getGridSquare(x, y, z)
    if U.issueLF and sq then if U.extractPage then U.extractPage("orders") end return U.issueLF("move_to", { square = sq }) end
    return false, "no_walk_path"
end
-- ---------------------------------------------------------------- going somewhere (LF navigation)
function U.solGoto(x, y, z)
    local sol = U.solActor and U.solActor()
    if not sol then return false, "no_sol" end
    z = z or math.floor(sol:getZ())
    local ok, why = gatewayGoTo(sol, math.floor(x), math.floor(y), z)
    if ok ~= true and type(why) == "string" and string.find(why, "action_owned:downtime:", 1, true) == 1 and (type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("order_breaks_rest") == true) then
        local SC0 = LF()
        if SC0 and type(SC0.Downtime) == "table" and type(SC0.Downtime.cancel) == "function" then
            pcall(SC0.Downtime.cancel, sol, "sol_order")
            ok, why = gatewayGoTo(sol, math.floor(x), math.floor(y), z)
        end
    end
    return ok, ok and ("walking_to " .. math.floor(x) .. "," .. math.floor(y)) or why
end
-- nearest walkable square inside a building (a room), searched around Sol; option "home" = around the saved home
function U.solGoInside(option)
    local sol = U.solActor and U.solActor()
    local cell = getCell and getCell()
    if not sol or not cell then return false, "no_sol" end
    local cx, cy = math.floor(sol:getX()), math.floor(sol:getY())
    local hx, hy = string.match(tostring(option or ""), "(%-?%d+)%s*,%s*(%-?%d+)")
    if hx then cx, cy = tonumber(hx), tonumber(hy) end
    local z = math.floor(sol:getZ())
    local best, bd
    for r = 0, 20 do
        for dx = -r, r do
            for dy = -r, r do
                if math.abs(dx) == r or math.abs(dy) == r then
                    local sq = cell:getGridSquare(cx + dx, cy + dy, z)
                    if sq and mcall(sq, "getRoom") and mcall(sq, "isFree", false) ~= false then
                        local d = dx * dx + dy * dy
                        if not bd or d < bd then best, bd = sq, d end
                    end
                end
            end
        end
        if best then break end
    end
    if not best then return false, "no_building_near" end
    local ok, why = gatewayGoTo(sol, best:getX(), best:getY(), z)
    local room = mcall(mcall(best, "getRoom"), "getName")
    return ok, ok and ("going_inside " .. tostring(room or "")) or why
end

function U.solFetch(option)
    local sol = U.solActor and U.solActor()
    if not sol then return false, "no_sol" end
    local what, after = tostring(option or "book"), nil
    local a, b = string.match(what, "^([^:]+):(%a+)$")
    if a then what, after = a, b end
    if what == "book" and after == "read" and U.solBooks then
        for _, b in ipairs(U.solBooks()) do
            if b.status == "useful" or b.status == "teaches" or b.status == "fun" then return U.solRead(b.item) end
        end
    end
    local found = U.findNearby(what)
    if not found then return false, "not_found_nearby" end
    local ok, why = gatewayGoTo(sol, found.x, found.y, found.z)
    if not ok then return false, why end
    U.fetchJob = { item = found.item, container = found.container, x = found.x, y = found.y, z = found.z, after = after, phase = "walking", since = nowMs() }
    return true, "going_for " .. tostring(mcall(found.item, "getDisplayName"))
end
function U.fetchTick()
    local job = U.fetchJob
    local sol = U.solActor and U.solActor()
    if not job or not sol or job.phase == "done" or job.phase == "failed" then return end
    local t = nowMs()
    local inv = sol:getInventory()
    if job.phase == "walking" then
        local d = math.sqrt((sol:getX() - (job.x + 0.5)) ^ 2 + (sol:getY() - (job.y + 0.5)) ^ 2)
        if d <= 1.8 then
            local SC = LF(); local TW = SC and SC.WorkTransport; local ok, why = false, "transport_unavailable"; if type(TW) == "table" and type(TW.transferVerified) == "function" then ok, why = TW.transferVerified(job.container, inv, job.item, sol) end
            if ok ~= true then job.phase, job.reason = "failed", tostring(why or "take_failed"); return end
            -- Sol patch 2026-10-26: an NPC takes with LF verified transfer (ISInventoryTransferAction:perform touches the local player UI and throws for an NPC)
            job.phase, job.since = "taking", t
        elseif t - job.since > WALK_TIMEOUT then job.phase, job.reason = "failed", "could_not_reach" end
    elseif job.phase == "taking" then
        if mcall(inv, "contains", job.item) then
            job.phase = "done"
            if job.after == "read" and U.solRead then U.solRead(job.item) end
            if U.issueLF then pcall(U.issueLF, "follow") end
        elseif t - job.since > TAKE_TIMEOUT then job.phase, job.reason = "failed", "could_not_take" end
    end
end

-- ---------------------------------------------------------------- files
local function writeCatalog()
    local ok, cat = pcall(U.actionCatalog)
    if not ok or not U.jsonEncode then return end
    local okE, text = pcall(U.jsonEncode, { v = 1, t = nowMs(), actions = cat })
    if not okE then return end
    local okw, w = pcall(getFileWriter, SNAP, true, false)
    if okw and w then w:write(text); w:close() end
end
-- s99 perf_slice: the same catalog over several frames: a page a frame, then the list, then the JSON a value at a time
-- (SolWorldScan's U.jsonEncodeJob, the same text as U.jsonEncode), then the file. At most CAT_SLICE_MS a frame plus the unit
-- that crosses it; reading one Living Fellows page is one unit.
local CAT_SLICE_MS = 4
local catJob = nil
local function catSliceOn() local A_ = rawget(_G, "SolAuthority"); return type(A_) == "table" and type(A_.on) == "function" and A_.on("perf_slice") == true end
local function catalogStep(budgetMs)
    local j = catJob
    local stopAt = nowMs() + budgetMs
    while true do
        if j.phase == "pages" then
            local page = PAGES[j.pi]
            if page == nil then j.phase = "build"
            else
                j.pi = j.pi + 1
                local okP, items = pcall(function() return U.extractPage and U.extractPage(page) or nil end)
                if not okP then return true end                                  -- as a failed actionCatalog: nothing written
                j.pre[page] = items
                return false                                                     -- one page a frame
            end
        elseif j.phase == "build" then
            local ok, cat = pcall(U.actionCatalog, j.pre)
            if not ok or not U.jsonEncode then return true end
            local doc = { v = 1, t = nowMs(), actions = cat }
            if type(U.jsonEncodeJob) == "function" then j.enc = U.jsonEncodeJob(doc); j.phase = "encode"
            else
                local okE, text = pcall(U.jsonEncode, doc)
                if not okE then return true end
                j.text, j.phase = text, "write"
            end
        elseif j.phase == "encode" then
            if j.enc.step(math.max(stopAt - nowMs(), 0)) then j.text, j.phase = j.enc.result(), "write" end
        elseif j.phase == "write" then
            local okw, w = pcall(getFileWriter, SNAP, true, false)
            if okw and w then w:write(j.text); w:close() end
            return true
        end
        if nowMs() >= stopAt then return false end
    end
end
U.writeActionCatalog = function() catJob = nil; return writeCatalog() end      -- a reply or a spawn wants it now: written at once, as before
local lastId = 0
local function poll()
    -- Sol patch: prime the request id. A request left in the file by an earlier session is not an order, but the first real request must still run.
    if not U._actPrimed then
        U._actPrimed = true
        local okp, rp = pcall(getFileReader, REQ, false)
        if okp and rp then
            local lp = rp:readLine()
            while lp ~= nil do local k, v = string.match(lp, "^([^=]+)=(.*)$"); if k == "id" then local n = tonumber(v); if n and n > lastId then lastId = n end end; lp = rp:readLine() end
            rp:close()
        end
    end
    local ok, r = pcall(getFileReader, REQ, false)
    if not ok or not r then return end
    local t, line = {}, r:readLine()
    while line ~= nil do local k, v = string.match(line, "^([^=]+)=(.*)$"); if k then t[k] = v end; line = r:readLine() end
    r:close()
    local id = tonumber(t.id) or 0
    if id <= lastId then return end
    lastId = id
    local okR, res, reason = pcall(U.runAction, t.action, t.option)
    if not okR then res, reason = false, tostring(res) end
    local okw, w = pcall(getFileWriter, STATE, true, false)
    U._acks = U._acks or {}
    table.insert(U._acks, 1, "r" .. id .. "=" .. tostring(res == true) .. "|" .. tostring(reason or ""))
    if #U._acks > 8 then table.remove(U._acks) end
    if okw and w then w:write("ack=" .. id .. "\nok=" .. tostring(res == true) .. "\nreason=" .. tostring(reason or "") .. "\n" .. table.concat(U._acks, "\n") .. "\n"); w:close() end
    log(tostring(t.action) .. " " .. tostring(t.option or "") .. " -> " .. tostring(res) .. " " .. tostring(reason or ""))
    U._catalogDue = U._catalogDue or (nowMs() + 3000)                            -- several actions in a row write it once
end
U.pollActions = poll
local lastPoll, lastCat = 0, 0
local function onTick()
    local tt = nowMs()
    if U.hornTick then pcall(U.hornTick) end
    if tt - lastPoll >= 1000 then lastPoll = tt; pcall(poll); pcall(U.fetchTick); pcall(U.trackGivenItems) end
    if catJob ~= nil then                                                         -- s99 perf_slice: a catalog on its way
        local t0 = nowMs()
        local okS, done = pcall(catalogStep, catSliceOn() and CAT_SLICE_MS or 1000000)
        if not okS or done then catJob = nil end
        if U.perfAdd then U.perfAdd("actions_catalog", nowMs() - t0) end
    elseif ((U._catalogDue and tt >= U._catalogDue) or tt - lastCat >= 120000) and U.solActor and U.solActor() then
        lastCat, U._catalogDue = tt, nil
        if catSliceOn() then catJob = { phase = "pages", pi = 1, pre = {} }
        else
        local t0 = nowMs(); pcall(writeCatalog); if U.perfAdd then U.perfAdd("actions_catalog", nowMs() - t0) end
        end
    end
end
if Events and Events.OnTick then Events.OnTick.Add(onTick) end
log("ready v" .. U.ACTIONS_VERSION)
