-- SolSecretLoadout.lua - switch secret_loadout. Jamal's secret order: Sol puts exact copies of his two firearms into HER inventory,
-- each with every part installed (EFZ build tree or the vanilla WeaponPart list), the magazine in it full, a round chambered,
-- his spare magazines of that type full, and 500 rounds of the weapon's own round.
-- The loadout is NOT per save and NOT per life:
--   1 SolSecretLoadoutData (media/lua/shared/SolSecretLoadoutData.lua, shipped with the mod; fold_secret_loadout.py fills it)
--   2 else Sol_SecretLoadout.txt in the Zomboid/Lua folder (getFileWriter/getFileReader, like SolFixes_LAB.txt)
--   3 else it is captured once, silently, the first time he carries two firearms (hands, then hotbar/attached slots), and the
--     file is written only if it is still missing. After that it stays fixed; only a new shipped data file replaces it.
-- Nothing here lives in ModData, so SolLife.checkIdentity (her death) never touches it: KEEP_ON_DEATH.
-- EFZ (Escape From Zomboid Firearms): the build is kept as EFZ's own build code (TW/Builds B.encode, TWB2|...) and put on a
-- fresh weapon with EFZ's own TWRuntime.applyTree (Runtime.lua:798), which creates every part with its TWPath and inserts
-- the magazine empty; the rounds go in as Gunworks does it (modData.AmmoList, last = next to fire; LootItems.lua:62).
-- Not listed in any panel, menu or help: the only door is U.runAction("sol_secret", "give") from Sol Mind.
-- ASCII only: Sol Mind words every line, nothing here speaks.
SolUI = SolUI or {}
local U = SolUI
SolSecretLoadout = SolSecretLoadout or {}
local M = SolSecretLoadout
M.VERSION = "0.1.0"
M.FILE = "Sol_SecretLoadout.txt"
M.ROUNDS = 500                 -- rounds of its own ammo per weapon
M.MAX_SPARE = 4                -- spare magazines per weapon at most
M.CAPTURE_MS = 3000
M.KEEP_ON_DEATH = true         -- SolLife's death wipe has no forget hook for this, on purpose

local function log(m) print("[SolSecret] " .. tostring(m)) end
local function g(name) return rawget(_G, name) end
local function nowMs() return getTimestampMs and getTimestampMs() or 0 end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function on() local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("secret_loadout") == true end
local function actor() return type(U.solActor) == "function" and U.solActor() or nil end
local function player()
    local f = g("getSpecificPlayer")
    if type(f) == "function" then local ok, p = pcall(f, 0); if ok and p ~= nil then return p end end
    f = g("getPlayer")
    if type(f) == "function" then local ok, p = pcall(f); if ok then return p end end
    return nil
end
local function clean(s) s = tostring(s or ""); s = string.gsub(s, "[\r\n]", " "); return s end
local function isA(o, cls)
    local f = g("instanceof")
    if type(f) ~= "function" or o == nil then return false end
    local ok, r = pcall(f, o, cls)
    return ok and r == true
end
local function newItem(t)
    local f = g("instanceItem")
    if type(f) ~= "function" or t == nil or t == "" then return nil end
    local ok, it = pcall(f, t)
    if ok then return it end
    return nil
end

local function efz()
    local R = g("TWRuntime")
    if type(R) ~= "table" or type(R.applyTree) ~= "function" or type(R.key) ~= "function" then return nil end
    local okB, B = pcall(require, "TW/Builds")
    if not okB or type(B) ~= "table" or type(B.encode) ~= "function" or type(B.decode) ~= "function" then return nil end
    local okD, D = pcall(require, "TW/Data")
    return R, B, (okD and type(D) == "table") and D or nil
end

-- ---------------------------------------------------------------- the stored loadout (lines "k=v", the same in both places)
function M.parse(lines)
    local t = {}
    for _, line in ipairs(lines or {}) do
        local k, v = string.match(tostring(line), "^([%w_%.]+)=(.*)$")
        if k then t[k] = v end
    end
    local out = {}
    for i = 1, 2 do
        local p = "w" .. i .. "."
        if t[p .. "type"] and t[p .. "type"] ~= "" then
            local rec = {}
            for k, v in pairs(t) do if string.sub(k, 1, #p) == p then rec[string.sub(k, #p + 1)] = v end end
            out[#out + 1] = rec
        end
    end
    if #out == 0 then return nil end
    return out
end

function M.readFile()
    local f = g("getFileReader")
    if type(f) ~= "function" then return nil end
    local ok, r = pcall(f, M.FILE, false)
    if not ok or r == nil then return nil end
    local lines = {}
    while true do
        local okL, line = pcall(function() return r:readLine() end)
        if not okL or line == nil then break end
        lines[#lines + 1] = line
    end
    pcall(function() r:close() end)
    return lines
end

function M.writeFile(lines)
    local existing = M.parse(M.readFile())
    if existing ~= nil then return false, "kept" end                      -- written once: never over a loadout already there
    local f = g("getFileWriter")
    if type(f) ~= "function" then return false, "no_writer" end
    local ok, w = pcall(f, M.FILE, true, false)
    if not ok or w == nil then return false, "no_writer" end
    local okW = pcall(function()
        for _, line in ipairs(lines) do w:write(line .. "\n") end
        w:close()
    end)
    return okW, okW and "written" or "write_failed"
end

M._cache = nil
function M.loadout()
    if M._cache then return M._cache, M._source end
    local data = g("SolSecretLoadoutData")
    local shipped = type(data) == "table" and M.parse(data.lines) or nil
    if shipped then M._cache, M._source = shipped, "shipped"; return shipped, "shipped" end
    local filed = M.parse(M.readFile())
    if filed then M._cache, M._source = filed, "file"; return filed, "file" end
    return nil, nil
end

-- ---------------------------------------------------------------- capture
function M.isFirearm(item)
    if item == nil or not isA(item, "HandWeapon") then return false end
    return call(item, "isRanged") == true
end

-- His firearms in the order he holds them: primary hand, secondary hand, then the hotbar / attached slots. Each one once.
function M.heldFirearms(p)
    local out, seen = {}, {}
    local function add(it, where)
        if it == nil or seen[it] or not M.isFirearm(it) then return end
        seen[it] = true
        out[#out + 1] = { item = it, where = where }
    end
    add(call(p, "getPrimaryHandItem"), "hand")
    add(call(p, "getSecondaryHandItem"), "hand")
    local att = call(p, "getAttachedItems")
    local n = tonumber(att and call(att, "size") or 0) or 0
    for i = 0, n - 1 do
        local a = call(att, "get", i)
        if a ~= nil then add(call(a, "getItem"), clean(call(a, "getLocation") or "slot")) end
    end
    return out
end

-- The round a weapon fires: what is in it (Gunworks AmmoList, last = next), else EFZ's own round of the weapon
-- (TW/Data weapons[key].ammo), else the script's AmmoType (getItemKey is the round's item type, TW_Init.lua:60).
function M.roundOf(w, key, D)
    local md = call(w, "getModData")
    local list = type(md) == "table" and md.AmmoList or nil
    if type(list) == "table" and #list > 0 and type(list[#list]) == "string" then return list[#list] end
    if key and D and type(D.weapons) == "table" and type(D.weapons[key]) == "table" and type(D.weapons[key].ammo) == "string" then return D.weapons[key].ammo end
    local at = call(w, "getAmmoType")
    if type(at) == "string" and at ~= "" then return at end
    if at ~= nil then
        local k = call(at, "getItemKey")
        if k ~= nil and tostring(k) ~= "" then return tostring(k) end
    end
    return ""
end

local function countMags(p, magType)
    if magType == nil or magType == "" then return 0 end
    local inv = call(p, "getInventory")
    local items = inv and call(inv, "getItems")
    local n = tonumber(items and call(items, "size") or 0) or 0
    local c = 0
    for i = 0, n - 1 do
        local it = call(items, "get", i)
        if it ~= nil and call(it, "getFullType") == magType then c = c + 1 end
    end
    return c
end

function M.describe(w, where, p, usedMags)
    local R, B, D = efz()
    local rec = { type = clean(call(w, "getFullType")), name = clean(call(w, "getDisplayName")), where = clean(where) }
    local parts, names = {}, {}
    local list = call(w, "getAllWeaponParts")
    local n = tonumber(list and call(list, "size") or 0) or 0
    for i = 0, n - 1 do
        local part = call(list, "get", i)
        if part ~= nil then parts[#parts + 1] = clean(call(part, "getFullType")); names[#names + 1] = clean(call(part, "getDisplayName")) end
    end
    rec.parts, rec.partnames = table.concat(parts, ","), table.concat(names, ";")
    local key = R and R.key(w) or nil
    rec.efz, rec.code = key or "", ""
    if key then
        local okT, tree = pcall(R.read, w)
        if okT and type(tree) == "table" then
            local okC, code = pcall(B.encode, key, tree, "")
            if okC and type(code) == "string" then rec.code = code end
        end
    end
    rec.mag = clean(call(w, "getMagazineType") or "")
    if rec.mag ~= "" then
        local probe = newItem(rec.mag)
        rec.magname = clean(probe and call(probe, "getDisplayName") or "")
    else rec.magname = "" end
    local spare = usedMags[rec.mag] and 0 or countMags(p, rec.mag)
    usedMags[rec.mag] = true
    rec.spare = tostring(math.min(M.MAX_SPARE, spare))
    rec.round = clean(M.roundOf(w, key, D))
    rec.firemode = clean(call(w, "getFireMode") or "")
    return rec
end

function M.lines(recs)
    local out = { "v=1", "at=" .. tostring(nowMs()) }
    local fields = { "type", "name", "where", "efz", "code", "parts", "partnames", "mag", "magname", "spare", "round", "firemode" }
    for i, rec in ipairs(recs) do
        for _, f in ipairs(fields) do out[#out + 1] = "w" .. i .. "." .. f .. "=" .. clean(rec[f]) end
    end
    return out
end

-- Once: two firearms on him, nothing stored yet. Silent (a log line only).
function M.capture(p)
    if M.loadout() ~= nil then return false, "have" end
    p = p or player()
    if p == nil then return false, "no_player" end
    local held = M.heldFirearms(p)
    if #held < 2 then return false, "need_two" end
    local recs, used = {}, {}
    for i = 1, 2 do recs[i] = M.describe(held[i].item, held[i].where, p, used) end
    local lines = M.lines(recs)
    local ok, why = M.writeFile(lines)
    M._cache, M._source = M.parse(lines), "captured"
    for i, rec in ipairs(recs) do log("captured w" .. i .. " " .. rec.type .. " (" .. rec.name .. ") parts: " .. rec.partnames .. " mag: " .. rec.magname .. " round: " .. rec.round) end
    log("file " .. tostring(why))
    return true, why
end

-- ---------------------------------------------------------------- give
local function fillList(item, round, count)
    local md = call(item, "getModData")
    if type(md) ~= "table" then return end
    if count > 0 and round ~= nil and round ~= "" then
        local l = {}
        for i = 1, count do l[i] = round end
        md.AmmoList = l
        local enumFor = g("TWAmmoEnumFor")
        if type(enumFor) == "function" then
            local ok, enum = pcall(enumFor, round)
            if ok and enum ~= nil then call(item, "setAmmoType", enum) end
        end
    else
        md.AmmoList = nil
    end
end

local function addTo(inv, item)
    if item == nil then return false end
    call(inv, "AddItem", item)
    local isC = g("isClient")
    if type(isC) == "function" and isC() and type(g("sendAddItemToContainer")) == "function" then pcall(sendAddItemToContainer, inv, item) end
    return true
end

-- A fresh weapon with the stored build: EFZ's own applyTree from its own build code, or the vanilla parts one by one.
function M.build(rec)
    local w = newItem(rec.type)
    if w == nil then return nil, "no_item" end
    local R, B = efz()
    if rec.code ~= nil and rec.code ~= "" and R then
        local okD, key, tree = pcall(B.decode, rec.code)
        if not okD or type(tree) ~= "table" or R.key(w) ~= key then return nil, "bad_build" end
        local okA, applied, why = pcall(R.applyTree, w, tree)
        if not okA or applied ~= true then return nil, "apply_" .. tostring(why or applied) end
        return w, "efz"
    end
    for t in string.gmatch(rec.parts or "", "[^,]+") do
        local part = newItem(t)
        if part ~= nil then
            local ok = pcall(function() w:attachWeaponPart(part, false) end)
            if not ok then pcall(function() w:attachWeaponPart(part) end) end
        end
    end
    if rec.mag ~= nil and rec.mag ~= "" then call(w, "setContainsClip", true) end
    return w, "vanilla"
end

-- Full: the magazine in it to its capacity and, when it has a chamber, one round in the chamber.
function M.load(w, rec)
    local max = tonumber((call(w, "getMaxAmmo"))) or 0
    local chamber = call(w, "haveChamber") == true
    call(w, "setCurrentAmmoCount", max)
    fillList(w, rec.round, max + (chamber and 1 or 0))
    if chamber then call(w, "setRoundChambered", true) end
    local fm = rec.firemode
    if fm ~= nil and fm ~= "" then call(w, "setFireMode", fm) end
    return max + (chamber and 1 or 0)
end

local function addRounds(inv, round, n)
    if round == nil or round == "" or n <= 0 then return 0 end
    local ok, list = pcall(function() return inv:AddItems(round, n) end)
    local got = ok and list ~= nil and tonumber((call(list, "size"))) or 0
    if got <= 0 then
        got = 0
        for _ = 1, n do if addTo(inv, newItem(round)) then got = got + 1 end end
    end
    return got
end

M.last = nil
function M.give()
    local recs = M.loadout()
    if recs == nil then return false, "none" end
    local a = actor()
    local inv = a and call(a, "getInventory")
    if inv == nil then return false, "no_sol" end
    local given, missed, rounds = 0, 0, 0
    local report = {}
    for _, rec in ipairs(recs) do
        local w, how = M.build(rec)
        if w ~= nil then
            local loaded = M.load(w, rec)
            addTo(inv, w)
            local spares = 0
            for _ = 1, math.min(M.MAX_SPARE, tonumber(rec.spare) or 0) do
                local m = newItem(rec.mag)
                if m ~= nil then
                    local cap = tonumber((call(m, "getMaxAmmo"))) or 0
                    call(m, "setCurrentAmmoCount", cap)
                    fillList(m, rec.round, cap)
                    if addTo(inv, m) then spares = spares + 1 end
                end
            end
            local r = addRounds(inv, rec.round, M.ROUNDS)
            rounds = rounds + r
            given = given + 1
            report[#report + 1] = rec.type .. ":" .. how .. ":loaded=" .. loaded .. ":spare=" .. spares .. ":rounds=" .. r
        else
            missed = missed + 1
            report[#report + 1] = rec.type .. ":" .. tostring(how)
        end
    end
    local cw = tonumber((call(inv, "getCapacityWeight")))
    local mw = tonumber((call(a, "getMaxWeight")))
    local heavy = cw ~= nil and mw ~= nil and cw > mw
    M.last = { given = given, missed = missed, rounds = rounds, heavy = heavy, report = report }
    log("give " .. table.concat(report, " | ") .. " weight " .. tostring(cw) .. "/" .. tostring(mw))
    if given == 0 then return false, "failed" end
    return true, "given:" .. given .. ";missed=" .. missed .. ";heavy=" .. (heavy and "1" or "0") .. ";rounds=" .. rounds
end

function M.order(option)
    if not on() then return false, "none" end                             -- a secret: off looks the same as unknown
    option = tostring(option or "give")
    if option == "give" or option == "" then return M.give() end
    if option == "status" then
        local recs, src = M.loadout()
        return true, "have=" .. tostring(recs ~= nil) .. ";source=" .. tostring(src)
    end
    return false, "unknown_option"
end

local nextCapture = 0
function M.tick()
    if not on() or M._cache ~= nil then return end
    local t = nowMs()
    if t < nextCapture then return end
    nextCapture = t + M.CAPTURE_MS
    pcall(M.capture)
end

function M.install()
    if M._installed then return end
    M._installed = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_secret" then return M.order(option) end
        return base(id, option)
    end
    local budget = g("SolBudget")
    if type(budget) == "table" and type(budget.register) == "function" then
        budget.register("sol_secret", function() pcall(M.tick) end, { everyMs = M.CAPTURE_MS, priority = 9 })
    elseif Events and Events.OnTick then
        Events.OnTick.Add(function() pcall(M.tick) end)
    end
    log("ready v" .. M.VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(M.install) end
return M
