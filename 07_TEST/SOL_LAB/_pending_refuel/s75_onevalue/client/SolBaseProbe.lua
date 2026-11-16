-- SolBaseProbe.lua - read-only verb sol_base_stats: zones, storages, jobs by state and the reason-like fields of farm jobs. Changes nothing.
SolUI = SolUI or {}
local U = SolUI
U.BASEPROBE_VERSION = "0.1.0"
local function log(m) print("[SolBaseProbe] " .. m) end
local function call(fn, ...)
    if type(fn) ~= "function" then return nil end
    local ok, a = pcall(fn, ...)
    if ok then return a end
    return nil
end
local function counts(list, field)
    local c, order = {}, {}
    if type(list) ~= "table" then return "" end
    for _, e in ipairs(list) do
        local k = type(e) == "table" and tostring(e[field] or "?") or "?"
        if not c[k] then c[k] = 0; order[#order + 1] = k end
        c[k] = c[k] + 1
    end
    table.sort(order)
    local out = {}
    for _, k in ipairs(order) do out[#out + 1] = k .. ":" .. c[k] end
    return table.concat(out, ",")
end

function U.baseStats()
    local sc = SurvivorCompanion
    local BL = type(sc) == "table" and sc.BaseLife or nil
    if type(BL) ~= "table" then return false, "no_baselife" end
    local base = call(BL.active)
    if type(base) ~= "table" then return true, "base=none" end
    local storages = type(base.storages) == "table" and base.storages or {}
    local unloaded = 0
    for _, s in ipairs(storages) do
        if call(BL.resolveContainer, s) == nil then unloaded = unloaded + 1 end
    end
    local jobs = type(base.jobs) == "table" and base.jobs or {}
    local byType, order = {}, {}
    for _, j in ipairs(jobs) do
        if type(j) == "table" then
            local t, st = tostring(j.type or "?"), tostring(j.state or "?")
            if not byType[t] then byType[t] = {}; order[#order + 1] = t end
            byType[t][st] = (byType[t][st] or 0) + 1
        end
    end
    table.sort(order)
    local jt = {}
    for _, t in ipairs(order) do
        local parts = {}
        for st, n in pairs(byType[t]) do parts[#parts + 1] = st .. n end
        table.sort(parts)
        jt[#jt + 1] = t .. "=" .. table.concat(parts, "/")
    end
    local why, WORDS = {}, { "reason", "block", "why", "error", "last" }
    for _, j in ipairs(jobs) do
        if type(j) == "table" and j.type == "farm" and #why < 2 then
            local fields, keys = {}, {}
            for k, v in pairs(j) do
                local lk = string.lower(tostring(k))
                keys[#keys + 1] = tostring(k)
                if type(v) == "string" or type(v) == "number" then
                    for _, w in ipairs(WORDS) do
                        if string.find(lk, w, 1, true) then fields[#fields + 1] = tostring(k) .. "=" .. string.sub(tostring(v), 1, 40); break end
                    end
                end
            end
            table.sort(fields); table.sort(keys)
            why[#why + 1] = "state=" .. tostring(j.state) .. (#fields > 0 and (" " .. table.concat(fields, " ")) or "") .. " keys=" .. table.concat(keys, ",")
        end
    end
    local text = "base=yes zones[" .. counts(base.zones, "kind") .. "] storages[" .. counts(storages, "category") .. "] unloaded=" .. unloaded
        .. " jobs[" .. table.concat(jt, " ") .. "]" .. (#why > 0 and (" farmjob{" .. table.concat(why, " | ") .. "}") or "")
    if string.len(text) > 900 then text = string.sub(text, 1, 900) end
    return true, text
end

local function install()
    if U._baseProbeInstalled then return end
    U._baseProbeInstalled = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_base_stats" then
            local ok, a, b = pcall(U.baseStats)
            if not ok then return false, "base_probe_error" end
            return a, b
        end
        return base(id, option)
    end
    log("verb installed v" .. U.BASEPROBE_VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(install) end
log("ready v" .. U.BASEPROBE_VERSION)
