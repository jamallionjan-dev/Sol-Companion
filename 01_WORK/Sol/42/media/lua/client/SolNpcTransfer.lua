-- SolNpcTransfer.lua - switch npc_reload_transfer (2026-11-15, s152). Her own items reach her main inventory without the
-- player-only helpers.
-- Live 2026-11-14 02:43:03 f:13990 and 03:18:32 f:80416 (LAB DebugLog): NullPointerException "chr is null" at
-- ItemContainer.isInCharacterInventory, raised from luautils.walkToContainer (luautils.lua:311-316:
-- getSpecificPlayer(playerNum) is nil for her) <- luautils.haveToBeTransfered <- ISInventoryPaneContextMenu.transferIfNeeded
-- (CleanUI's copy included) <- SolMagFill.queueInsert (SolMagFill.lua:350) and Gunworks Magazine.reloadMagazine
-- (Magazine.lua:206) called by SolMagFill.queueFill. s149 covered only SCNativeActions' BeginAutomaticReload.
-- The vanilla reload actions need the magazine and the rounds in the MAIN inventory (ISLoadBulletsInMagazine.lua:9/15/128,
-- ISInsertMagazine.lua:11/44), so a magazine or rounds inside one of her bags must be moved first.
-- What this file does (switch read at call time, off = nothing changes):
--   moveToMain(actor, item)  an item inside a container that belongs to HER (bag on her) goes to her main inventory with
--                            Living Fellows' verified move (SCGameplayUtil U.transferItemVerified: remove, add, check, roll
--                            back), else the same steps here. Nothing is ever taken from a container that is not hers.
--                            No timed action and no inventory UI (SolPlanner.lua:172: the transfer action's UI part is for
--                            the local player only).
--   transfer(actor, item)    one InventoryItem or a Java list of them (transferBullets passes an ArrayList).
--   guard(actor, fn, ...)    runs fn with ISInventoryPaneContextMenu.transferIfNeeded answering through transfer() for this
--                            actor only (every other character keeps the function that was there), then puts the previous
--                            function back. Returns pcall's results. For the local player or with the switch off: plain pcall.
SolNpcTransfer = SolNpcTransfer or {}
local T = SolNpcTransfer
T.VERSION = "0.1.0"
T.LIST_CAP = 256
T.moved = T.moved or 0

local function g(name) return rawget(_G, name) end
local function log(m) print("[SolNpcTransfer] " .. tostring(m)) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local rawTonumber = tonumber
local function num(v) return rawTonumber(v) end

function T.on()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("npc_reload_transfer") == true
end

-- true only for a character the game knows by player index (the player-only helpers are safe for it)
function T.isLocalPlayer(actor)
    if actor == nil then return false end
    local f = g("getSpecificPlayer")
    if type(f) ~= "function" then return false end
    local n = call(actor, "getPlayerNum")
    if n == nil then return false end
    local ok, p = pcall(f, n)
    return ok and p == actor
end

local function isItem(o)
    local f = g("instanceof")
    if type(f) ~= "function" then return false end
    local ok, r = pcall(f, o, "InventoryItem")
    return ok and r == true
end
local function isList(o)
    local f = g("instanceof")
    if type(f) ~= "function" then return false end
    local ok, r = pcall(f, o, "ArrayList")
    return ok and r == true
end

function T.moveToMain(actor, item)
    local inv = call(actor, "getInventory")
    if inv == nil or item == nil then return false, "no_inventory" end
    local src = call(item, "getContainer")
    if src == nil then return false, "no_container" end
    if src == inv then return true, "already_main" end
    if call(src, "isInCharacterInventory", actor) ~= true then return false, "not_hers" end
    local SC = g("SurvivorCompanion")
    local U = type(SC) == "table" and SC.GameplayUtil or nil
    if type(U) == "table" and type(U.transferItemVerified) == "function" then
        local ok, moved, why = pcall(U.transferItemVerified, src, inv, item)
        if ok then
            if moved == true then T.moved = T.moved + 1 end
            return moved == true, why
        end
    end
    call(src, "Remove", item)
    if call(src, "contains", item) == true then return false, "source_remove_failed" end
    call(inv, "AddItem", item)
    if call(inv, "contains", item) == true then T.moved = T.moved + 1; return true, "moved" end
    call(src, "AddItem", item)                      -- put it back where it was: nothing of hers is lost
    return false, "add_failed_rolled_back"
end

-- one item or a Java list; true when everything asked for is now in her main inventory
function T.transfer(actor, item)
    if item == nil then return false end
    if isItem(item) then
        local ok = T.moveToMain(actor, item)
        return ok == true
    end
    if isList(item) then
        local n = num((call(item, "size"))) or 0
        local all = true
        for i = 0, math.min(n, T.LIST_CAP) - 1 do
            local it = call(item, "get", i)
            if it ~= nil and T.moveToMain(actor, it) ~= true then all = false end
        end
        return all
    end
    return false                                    -- a world object: she does not walk to it from here
end

function T.guard(actor, fn, ...)
    if type(fn) ~= "function" then return false, "not_a_function" end
    local CM = g("ISInventoryPaneContextMenu")
    if actor == nil or not T.on() or T.isLocalPlayer(actor)
        or type(CM) ~= "table" or type(CM.transferIfNeeded) ~= "function" then
        return pcall(fn, ...)
    end
    local previous = CM.transferIfNeeded
    local function forActor(playerObj, item, ...)
        if playerObj ~= actor then return previous(playerObj, item, ...) end
        return T.transfer(actor, item)
    end
    CM.transferIfNeeded = forActor
    local results = { pcall(fn, ...) }
    if CM.transferIfNeeded == forActor then CM.transferIfNeeded = previous end
    return results[1], results[2], results[3], results[4]
end

log("loaded v" .. T.VERSION)
return T
