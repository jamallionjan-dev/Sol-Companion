-- SolDamageProbe.lua - exact hit attribution for comparing Sol and the local player.
-- This is diagnostic only: it never changes weapon stats, zombie health, or hit handling.
SolDamageProbe = SolDamageProbe or {}
local P = SolDamageProbe
P.VERSION = "0.1.0"
P.pending = P.pending or {}
P.tickSerial = P.tickSerial or 0
P.installed = P.installed or false

local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, value = pcall(f, o, ...)
    if ok then return value end
    return nil
end
local function number(v) local n = tonumber(v); return n end
local function precise(v)
    v = number(v)
    if v == nil then return "?" end
    return string.format("%.5f", v)
end
local function log(message) print("[SolDamageProbe] " .. tostring(message)) end
function P.on()
    local authority = g("SolAuthority")
    return type(authority) == "table" and type(authority.on) == "function"
        and authority.on("shooting_damage_probe") == true
end
local function sourceOf(attacker)
    local discipline = g("SolShootDiscipline")
    if type(discipline) == "table" and type(discipline._isSol) == "function" then
        local ok, result = pcall(discipline._isSol, attacker)
        if ok and result then return "Sol" end
    end
    local UI = g("SolUI")
    if type(UI) == "table" and type(UI.solActor) == "function" then
        local ok, actor = pcall(UI.solActor)
        if ok and actor == attacker then return "Sol" end
    end
    if call(attacker, "isLocalPlayer") == true then return "Jamal" end
    return nil
end
local function weaponName(weapon)
    return tostring(call(weapon, "getFullType") or call(weapon, "getType") or "?")
end
function P.onHit(zombie, attacker, bodyPart, weapon)
    if not P.on() or zombie == nil or attacker == nil or weapon == nil then return false end
    if call(weapon, "isRanged") ~= true then return false end
    local source = sourceOf(attacker)
    if source == nil then return false end
    local hp = number(call(zombie, "getHealth"))
    if hp == nil then return false end
    P.pending[#P.pending + 1] = {
        zombie = zombie, source = source, weapon = weaponName(weapon), body = tostring(bodyPart or "?"),
        pre = hp, hitTick = P.tickSerial, flushTick = P.tickSerial + 1
    }
    return true
end
function P.flush()
    P.tickSerial = P.tickSerial + 1
    if #P.pending == 0 then return 0 end
    local keep, flushed = {}, 0
    for i = 1, #P.pending do
        local row = P.pending[i]
        if row.flushTick <= P.tickSerial then
            local post = number(call(row.zombie, "getHealth"))
            if post ~= nil then
                local delta = row.pre - post
                log("source=" .. row.source .. " weapon=" .. row.weapon .. " body=" .. row.body
                    .. " pre=" .. precise(row.pre) .. " post=" .. precise(post)
                    .. " damage=" .. precise(delta) .. " ticks=" .. tostring(P.tickSerial - row.hitTick))
            else
                log("source=" .. row.source .. " weapon=" .. row.weapon .. " body=" .. row.body .. " post=unavailable")
            end
            flushed = flushed + 1
        else
            keep[#keep + 1] = row
        end
    end
    P.pending = keep
    return flushed
end

if not P.installed and Events ~= nil then
    P.installed = true
    if Events.OnHitZombie and type(Events.OnHitZombie.Add) == "function" then
        Events.OnHitZombie.Add(function(zombie, attacker, bodyPart, weapon)
            pcall(P.onHit, zombie, attacker, bodyPart, weapon)
        end)
    end
    if Events.OnTick and type(Events.OnTick.Add) == "function" then
        Events.OnTick.Add(function() pcall(P.flush) end)
    end
    log("ready v" .. P.VERSION .. " (read-only; switch shooting_damage_probe)")
end
