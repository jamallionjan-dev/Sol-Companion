-- SolKahluaGuard.lua - switch kahlua_overload_guard (s96). Stops the "callFrame ... ReturnValues.put" storm at its source.
-- Root cause, measured offline on the game's own projectzomboid.jar (42.22.2, harness in the s96 notes):
--   se.krka.kahlua.integration.expose.MultiLuaJavaInvoker.call (an OVERLOADED Java method called from Lua) releases the same
--   pooled MethodArguments TWICE when no overload fits the arguments: its last loop puts the failed arguments back
--   (MethodArguments.put also sets valid=true), then after the loop assertValid() passes and it puts them back again, and only then
--   throws "No implementation found for function: name(...)". A pcall swallows the error, but MethodArguments.Pools now holds
--   that object twice. Later, any Lua->Java call that calls back into Lua (getFirstEvalRecurse with a Lua predicate,
--   setPrimaryHandItem -> OnEquipPrimary, triggerEvent, ...) can be handed the same object for the outer and an inner call;
--   the inner call releases it (returnValues = nil) and the outer one dies in ReturnValues.put(null): exactly the NPE we see.
--   Each failed overloaded call adds one duplicate; each NPE removes one. The pools are static: only a game restart clears them.
-- With the switch on:
--   1 every pcall that ends in "No implementation found for function" is logged once per signature, with the Lua call site
--     (file:line) and a count, whoever made it (Sol or another mod): the next session names the culprit.
--   2 Sol's own Java calls (SC.Call.value/method/static, used by U.call; and SolKahluaGuard.call for the files that route here)
--     remember a (class, method, argument types) signature that failed this way and do not make that call again this session:
--     they answer the same failure without touching Java, so one bad call site poisons the pool at most once, not once per item.
-- Switch off: the pcall wrapper only passes through; Sol's calls go to Java as before.
SolKahluaGuard = SolKahluaGuard or {}
local M = SolKahluaGuard
M.VERSION = "0.1.0"
M.MAX_SITES = 64                    -- distinct signatures logged; after that only the counter grows
M.stats = M.stats or { seen = 0, blocked = 0, sites = 0 }
M.blocked = M.blocked or {}         -- [class metatable][method name][argument-type key] = message
M.sites = M.sites or {}             -- [message] = count

local G = _G
local rawPcall = M.rawPcall or G.pcall
M.rawPcall = rawPcall
local NEEDLE = "No implementation found for function"

local function log(m) print("[SolKahluaGuard] " .. tostring(m)) end
function M.on()
    local A = rawget(G, "SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, v = rawPcall(A.on, "kahlua_overload_guard")
    return ok and v == true
end

local function isOverloadError(err)
    if err == nil then return false end
    return string.find(tostring(err), NEEDLE, 1, true) ~= nil
end
local function pack(...) return { n = select("#", ...), ... } end   -- unpack(t, 1, t.n): Kahlua's unpack stops at a nil otherwise
M.isOverloadError = isOverloadError

-- where in Lua the failed call came from: the innermost frames that are not this file
local function callSite()
    local gcc, top, frame = rawget(G, "getCurrentCoroutine"), rawget(G, "getCallframeTop"), rawget(G, "getCoroutineCallframeStack")
    local fileOf, lineOf = rawget(G, "getFilenameOfCallframe"), rawget(G, "getLineNumber")
    if type(gcc) ~= "function" or type(top) ~= "function" or type(frame) ~= "function" or type(fileOf) ~= "function" then return "?" end
    local okC, co = rawPcall(gcc)
    if not okC or co == nil then return "?" end
    local okT, n = rawPcall(top, co)
    n = okT and tonumber((n)) or 0
    local out = {}
    for i = n - 1, 0, -1 do
        local okF, cf = rawPcall(frame, co, i)
        if okF and cf ~= nil then
            local okN, file = rawPcall(fileOf, cf)
            file = okN and tostring(file or "?") or "?"
            if not string.find(file, "SolKahluaGuard", 1, true) then
                local okL, line = rawPcall(lineOf, cf)
                out[#out + 1] = file:match("([^/\\]+)$") .. ":" .. tostring(okL and line or "?")
                if #out >= 4 then break end
            end
        end
    end
    return #out > 0 and table.concat(out, " < ") or "?"
end

function M.note(err, how)
    M.stats.seen = M.stats.seen + 1
    local key = tostring(err):sub(1, 200)
    local c = M.sites[key]
    if c == nil then
        if M.stats.sites >= M.MAX_SITES then return end
        M.stats.sites = M.stats.sites + 1
        M.sites[key] = 1
        log("failed overloaded Java call (" .. tostring(how) .. ", poisons the Kahlua pool once): " .. key .. " | at " .. callSite())
    else
        M.sites[key] = c + 1
        if c + 1 == 10 or c + 1 == 100 or c + 1 == 1000 then log("the same failed call " .. (c + 1) .. " times now: " .. key) end
    end
end

-- 1 every pcall: pass-through; a failure that is the overload bug is noted (switch on). No table is built on the way.
local function after(ok, ...)
    if not ok then
        local err = ...
        if isOverloadError(err) and M.on() then M.note(err, "pcall") end
    end
    return ok, ...
end
function M.pcall(f, ...)
    return after(rawPcall(f, ...))
end

-- 2 Sol's own calls: the signature is the class metatable, the method name and every argument's class / Lua type
local function argKey(...)
    local n = select("#", ...)
    if n == 0 then return "" end
    local parts = {}
    for i = 1, n do
        local v = select(i, ...)
        local t = type(v)
        if t == "userdata" then
            local mt = getmetatable(v)
            parts[i] = mt ~= nil and tostring(mt) or "u"
        else parts[i] = t end
    end
    return table.concat(parts, ",")
end
local function blockedFor(obj, name)
    if type(obj) ~= "userdata" then return nil end
    local mt = getmetatable(obj)
    if mt == nil then return nil end
    local byName = M.blocked[mt]
    return byName and byName[name] or nil, mt
end
-- before the call: the error it gave last time when this exact signature is known bad (and the switch is on), else nil
function M.check(obj, name, ...)
    local byArgs = blockedFor(obj, name)
    if byArgs == nil then return nil end
    local msg = byArgs[argKey(...)]
    if msg ~= nil and M.on() then
        M.stats.blocked = M.stats.blocked + 1
        return msg
    end
    return nil
end
-- after a failed call: remember the signature when it was the overload bug
function M.learn(obj, name, err, ...)
    if not isOverloadError(err) or type(obj) ~= "userdata" or not M.on() then return end
    local mt = getmetatable(obj)
    if mt == nil then return end
    local byName = M.blocked[mt]
    if byName == nil then byName = {}; M.blocked[mt] = byName end
    local byArgs = byName[name]
    if byArgs == nil then byArgs = {}; byName[name] = byArgs end
    byArgs[argKey(...)] = tostring(err)
end

-- the file-local call helpers (SolSort, SolInventory, SolCompatVP) route here: ok, value like pcall(o[name], o, ...)
function M.call(obj, name, ...)
    if obj == nil then return false, "nil object" end
    local okF, f = rawPcall(function() return obj[name] end)
    if not okF or f == nil then return false, "no method " .. tostring(name) end
    local known = M.check(obj, name, ...)
    if known ~= nil then return false, known end
    local res = pack(rawPcall(f, obj, ...))
    if res[1] ~= true then M.learn(obj, name, res[2], ...) end
    return unpack(res, 1, res.n)
end

-- SC.Call (shared/SCCall.lua): value/method/static get the same check before and learn after
function M.wrapCall()
    local SC = rawget(G, "SurvivorCompanion")
    local C = type(SC) == "table" and SC.Call or nil
    if type(C) ~= "table" or C._solKahluaGuard then return C ~= nil end
    C._solKahluaGuard = true
    local baseValue, baseMethod, baseStatic = C.value, C.method, C.static
    if type(baseValue) == "function" then
        C.value = function(object, name, ...)
            local known = M.check(object, name, ...)
            if known ~= nil then return nil, false, known end
            local res = pack(baseValue(object, name, ...))
            if res[2] == false and res[3] ~= nil then M.learn(object, name, res[3], ...) end
            return unpack(res, 1, math.max(res.n, 2))
        end
    end
    if type(baseMethod) == "function" then
        C.method = function(object, name, ...)
            local known = M.check(object, name, ...)
            if known ~= nil then return false, known end
            local res = pack(baseMethod(object, name, ...))
            if res[1] == false then M.learn(object, name, res[2], ...) end
            return unpack(res, 1, res.n)
        end
    end
    if type(baseStatic) == "function" then
        C.static = function(object, name, ...)
            local known = M.check(object, name, ...)
            if known ~= nil then return false, known end
            local res = pack(baseStatic(object, name, ...))
            if res[1] == false then M.learn(object, name, res[2], ...) end
            return unpack(res, 1, res.n)
        end
    end
    return true
end

-- the global pcall becomes the pass-through above (once). Files that captured pcall in a local before this ran keep the raw one.
function M.installPcall()
    if rawget(G, "pcall") == M.pcall then return true end
    if M._pcallInstalled then return true end
    M._pcallInstalled = true
    G.pcall = M.pcall
    return true
end

function M.install()
    M.installPcall()
    local c = M.wrapCall()
    if not M._logged then
        M._logged = true
        log("ready v" .. M.VERSION .. " (switch kahlua_overload_guard=" .. tostring(M.on()) .. ", pcall watched, SC.Call "
            .. (c and "guarded" or "absent") .. ")")
    end
end
M.installPcall()                    -- as early as possible: client files loaded after this one are watched from the start
if Events and Events.OnGameStart then Events.OnGameStart.Add(function() rawPcall(M.install) end) end
return M
