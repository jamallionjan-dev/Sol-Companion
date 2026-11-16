-- SolSkillProbe.lua - read-only diagnostics for Sol's learning. It changes nothing in the game.
-- Verb sol_skill_stats (through the existing SolAct_Request channel; not in the brain's catalog) reports, on one line:
--   skills: every perk with a level, XP or XP multiplier (the game's own getXp():getXP / getMultiplier)
--   ledger: the pages of each book Sol has read (Living Fellows keeps it in her mod data: SC_ReadingPages)
--   books : the literature in her bag with the game's verdict (useful / too_hard / too_easy / teaches / known / fun)
-- Why: a skill book raises an XP multiplier, not a level, so "did she learn" needs XP, multiplier and pages, not levels alone.
-- Nothing here may fail on purpose: debug mode stops the game on any error, even a caught one.
require "SolSkills"
SolUI = SolUI or {}
local U = SolUI
U.SKILLPROBE_VERSION = "0.1.0"
local function log(m) print("[SolSkillProbe] " .. tostring(m)) end

local function call(o, name, ...)
    if o == nil then return nil end
    local f = o[name]
    if type(f) ~= "function" then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function num(v) if type(v) == "number" and v == v then return v end return nil end
local function r1(v) v = num(v); if not v then return "?" end return tostring(math.floor(v * 10 + 0.5) / 10) end

function U.skillStats()
    local sol = U.solActor and U.solActor() or nil
    if sol == nil then return nil, "no_sol" end
    local xp = call(sol, "getXp")
    local list = type(PerkFactory) == "table" and PerkFactory.PerkList or nil
    local n = list and num(call(list, "size")) or 0
    local skills = {}
    for i = 0, n - 1 do
        local perk = call(list, "get", i)
        if perk ~= nil then
            local lv = num(call(sol, "getPerkLevel", perk))
            local x = xp and num(call(xp, "getXP", perk)) or nil
            local m = xp and num(call(xp, "getMultiplier", perk)) or nil
            if (lv and lv > 0) or (x and x > 0) or (m and m > 0) then
                local t = call(perk, "getType")
                local name = tostring(call(t, "name") or call(perk, "getId") or i)
                local s = name .. " L" .. r1(lv) .. " xp=" .. r1(x)
                if m and m > 0 then s = s .. " m=" .. r1(m) end
                skills[#skills + 1] = s
            end
        end
    end
    local ledger = {}
    local data = call(sol, "getModData")
    local pages = type(data) == "table" and data.SC_ReadingPages or nil
    if type(pages) == "table" then
        for k, v in pairs(pages) do
            if type(k) == "string" and num(v) then ledger[#ledger + 1] = (string.match(k, "([^%.]+)$") or k) .. "=" .. r1(v) end
        end
        table.sort(ledger)
    end
    local books = {}
    local list2 = type(U.solBooks) == "function" and U.solBooks(sol) or nil
    if type(list2) == "table" then
        for i, b in ipairs(list2) do
            if i > 6 then break end
            books[#books + 1] = tostring(b.name) .. "[" .. tostring(b.status) .. " " .. r1(b.read) .. "/" .. r1(b.pages) .. "]"
        end
    end
    local text = "skills: " .. (#skills > 0 and table.concat(skills, ", ") or "none")
        .. " | ledger: " .. (#ledger > 0 and table.concat(ledger, ", ") or "none")
        .. " | books: " .. (#books > 0 and table.concat(books, ", ") or "none")
    if string.len(text) > 900 then text = string.sub(text, 1, 900) end
    return true, text
end

local function install()
    if U._skillProbeInstalled then return end
    U._skillProbeInstalled = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_skill_stats" then
            local ok, a, b = pcall(U.skillStats)
            if not ok then return false, "skill_probe_error" end
            return a, b
        end
        return base(id, option)
    end
    log("verb installed v" .. U.SKILLPROBE_VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(install) end
log("ready v" .. U.SKILLPROBE_VERSION)
