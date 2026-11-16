-- SolCompat.lua - keeps other mods from tripping the game's own debug "LootLog".
-- The game's LootLog (server/Items/LootLog.lua) runs on every container fill when ISLootLog.cheat is true (a debug / admin option, off by default) and
-- reads the filled container with :getItems(). The Viewpoint mod fills containers with a Java wrapper (ItemPickerContainer) that has no getItems(), so with that
-- option on the game logs an error for every loot roll - and a Lua debugger set to "Break On Error" stops the game at each one.
-- While the option is on, this module turns it back off: LootLog's own check (ISLootLog.cheat) then returns before it reads anything. Nothing else is touched.
SolCompat = SolCompat or {}
local C = SolCompat
C.VERSION = "0.1.0"
local function log(m) print("[SolCompat] " .. tostring(m)) end
C.turnedOff = 0
function C.quietLootLog()
    local L = ISLootLog
    if type(L) == "table" and L.cheat == true then
        L.cheat = false
        C.turnedOff = C.turnedOff + 1
        if C.turnedOff == 1 then log("the game's debug LootLog was on: turned off (another mod's loot preview makes it fail)") end
        return true
    end
    return false
end
local ticks = 0
local function onTick()
    ticks = ticks + 1
    if ticks >= 30 then ticks = 0; C.quietLootLog() end
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(function() C.quietLootLog() end) end
if Events and Events.OnTick then Events.OnTick.Add(onTick) end
C._tick = onTick
print("[SolCompat] ready v" .. C.VERSION)
