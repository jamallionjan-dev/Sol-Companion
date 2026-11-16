-- SolMemStore.lua - Sol World Memory, phase 1: the data layer.
-- One store per save (global ModData under <worldSaveKey>_SolMem), one namespace per Sol incarnation (SC_Id).
-- A new Sol never inherits the memory of a dead one: the old namespace is archived, never deleted.
-- Pure data: no game perception here (phase 3) and no behaviour change. Kill switch: SolUI.Mem.enabled = false.
-- Only plain data is stored (strings, numbers, booleans, tables with string keys or dense arrays).
-- Nothing here is allowed to fail on purpose: debug mode stops the game on any error, even a caught one.
require "SolActionRegistry"
SolUI = SolUI or {}
local U = SolUI
U.Mem = U.Mem or {}
local M = U.Mem
M.VERSION = "0.1.0"
M.SCHEMA = 1
if M.enabled == nil then M.enabled = true end
M.CAP_CONTAINERS = 300
M.CAP_ROWS = 6000
M.RECENT_HOURS = 1
M.TTL_HOURS = { perishable = 12, normal = 72 }
M.ANCHOR_KINDS = { PrimaryVehicle = true, VehicleHome = true, BuildingHome = true }

local function log(m) print("[SolMem] " .. tostring(m)) end

-- world age in game hours (sleeping skips hours, so ages are measured here and not in real time)
function M.worldHours()
    if type(getGameTime) ~= "function" then return nil end
    local gt = getGameTime()
    if gt == nil then return nil end
    local f = gt["getWorldAgeHours"]
    if type(f) ~= "function" then return nil end
    local ok, v = pcall(f, gt)
    if ok and type(v) == "number" and v == v then return v end
    return nil
end

local function mindIdOf(actor)
    if actor == nil then return nil, "no_actor" end
    local SC = SurvivorCompanion
    local G = type(SC) == "table" and SC.GameplayUtil or nil
    if type(G) ~= "table" or type(G.idOf) ~= "function" then return nil, "idOf_unavailable" end
    local ok, id = pcall(G.idOf, actor)
    if not ok or type(id) ~= "string" or id == "" then return nil, "no_id" end
    if string.sub(id, 1, 8) == "runtime-" or string.find(id, "@", 1, true)
        or string.find(id, "table:", 1, true) or string.find(id, "userdata", 1, true) then
        return nil, "id_not_persistent"
    end
    return id
end

local function storeKey()
    local SC = SurvivorCompanion
    local I = type(SC) == "table" and SC.Identity or nil
    local k = type(I) == "table" and I.worldSaveKey or nil
    if type(k) ~= "string" or k == "" then return nil end
    return k .. "_SolMem"
end

-- opens (or creates) the namespace of the current Sol incarnation; returns mind or nil, reason
function M.open()
    if M.enabled ~= true then return nil, "disabled" end
    if type(ModData) ~= "table" or type(ModData.getOrCreate) ~= "function" then return nil, "moddata_unavailable" end
    local key = storeKey()
    if not key then return nil, "world_key_unavailable" end
    local actor = U.solActor and U.solActor() or nil
    local id, why = mindIdOf(actor)
    if not id then return nil, why end
    if M._mind and M._id == id and M._key == key then return M._mind end
    local ok, root = pcall(ModData.getOrCreate, key)
    if not ok or type(root) ~= "table" then return nil, "moddata_failed" end
    if root.schema == nil then
        root.schema = M.SCHEMA
        root.minds = {}
        root.created = M.worldHours() or 0
    end
    if root.schema ~= M.SCHEMA then return nil, "schema_mismatch" end
    if type(root.minds) ~= "table" then return nil, "corrupt_minds" end
    local mind = root.minds[id]
    if mind == nil then
        if root.active ~= nil and root.minds[root.active] ~= nil then root.minds[root.active].archived = true end
        mind = { created = M.worldHours() or 0, containers = {}, vehicles = {}, anchors = {}, probe = { n = 0 } }
        root.minds[id] = mind
        log("new incarnation " .. id .. " (previous one archived, not inherited)")
    end
    mind.archived = nil
    root.active = id
    M._root, M._mind, M._key, M._id = root, mind, key, id
    return mind
end

function M.mind()
    local m = M.open()
    return m
end

-- knowledge state is computed, never stored: visible / recent / remembered / stale / unknown
function M.knowledge(lastVerified, perishable, visibleNow, nowHours)
    if visibleNow == true then return "visible" end
    if type(lastVerified) ~= "number" then return "unknown" end
    local now = nowHours or M.worldHours()
    if type(now) ~= "number" then return "unknown" end
    local age = now - lastVerified
    if age < -0.01 then return "unknown" end
    if age < 0 then age = 0 end
    if age <= M.RECENT_HOURS then return "recent" end
    local ttl = perishable and M.TTL_HOURS.perishable or M.TTL_HOURS.normal
    if age <= ttl then return "remembered" end
    return "stale"
end

-- keeps the store inside its caps: drops the containers visited longest ago, never a pinned one
function M.evict()
    local mind = M.mind()
    if not mind then return 0 end
    local n, rows = 0, 0
    for _, c in pairs(mind.containers) do n = n + 1; rows = rows + #(c.rows or {}) end
    if n <= M.CAP_CONTAINERS and rows <= M.CAP_ROWS then return 0 end
    local list = {}
    for k, c in pairs(mind.containers) do list[#list + 1] = { k = k, t = c.lastVisit or c.lastVerified or 0 } end
    table.sort(list, function(a, b) if a.t == b.t then return a.k < b.k end return a.t < b.t end)
    local removed, i = 0, 1
    while (n > M.CAP_CONTAINERS or rows > M.CAP_ROWS) and i <= #list do
        local c = mind.containers[list[i].k]
        if c ~= nil and c.pinned ~= true then
            rows = rows - #(c.rows or {})
            n = n - 1
            mind.containers[list[i].k] = nil
            removed = removed + 1
        end
        i = i + 1
    end
    return removed
end

-- replaces the rows of one container with a fresh snapshot: rowsNew = { { t = fullType, n = name, c = count, q = worst condition 0..1, p = perishable } }
-- returns { added, removed, changed, rows } or nil, reason
function M.reconcile(key, meta, rowsNew, nowHours)
    local mind = M.mind()
    if not mind then return nil, "no_mind" end
    if type(key) ~= "string" or key == "" then return nil, "bad_key" end
    if type(rowsNew) ~= "table" then return nil, "bad_rows" end
    local rec = mind.containers[key]
    local old = {}
    if rec ~= nil and type(rec.rows) == "table" then
        for _, r in ipairs(rec.rows) do old[r.t] = r end
    end
    local seen, clean = {}, {}
    for _, r in ipairs(rowsNew) do
        if type(r) == "table" and type(r.t) == "string" then
            local row = { t = r.t, n = tostring(r.n or r.t), c = tonumber(r.c) or 1, q = tonumber(r.q) }
            if r.p == true then row.p = true end
            local s = seen[row.t]
            if s ~= nil then
                s.c = s.c + row.c
                if row.q ~= nil and (s.q == nil or row.q < s.q) then s.q = row.q end
                if row.p then s.p = true end
            else
                seen[row.t] = row
                clean[#clean + 1] = row
            end
        end
    end
    local added, removed, changed = 0, 0, 0
    for _, row in ipairs(clean) do
        local o = old[row.t]
        if o == nil then added = added + 1
        elseif o.c ~= row.c or o.q ~= row.q then changed = changed + 1 end
    end
    for t in pairs(old) do if seen[t] == nil then removed = removed + 1 end end
    local nowH = nowHours or M.worldHours() or 0
    if rec == nil then rec = { first = nowH }; mind.containers[key] = rec end
    rec.rows = clean
    rec.lastVerified = nowH
    rec.lastVisit = nowH
    if type(meta) == "table" then
        if meta.room ~= nil then rec.room = tostring(meta.room) end
        if meta.kind ~= nil then rec.kind = tostring(meta.kind) end
        if type(meta.x) == "number" and type(meta.y) == "number" then
            rec.x, rec.y, rec.z = meta.x, meta.y, tonumber(meta.z) or 0
        end
        if meta.pinned == true then rec.pinned = true end
    end
    M.evict()
    return { added = added, removed = removed, changed = changed, rows = #clean }
end

function M.getContainer(key)
    local mind = M.mind()
    if not mind then return nil end
    return mind.containers[key]
end

-- only called after a verification returned GONE (the square is loaded and the container is really absent)
function M.dropContainer(key)
    local mind = M.mind()
    if not mind or mind.containers[key] == nil then return false end
    mind.containers[key] = nil
    return true
end

function M.setAnchor(kind, ref)
    local mind = M.mind()
    if not mind then return false, "no_mind" end
    if M.ANCHOR_KINDS[kind] ~= true then return false, "bad_kind" end
    if type(ref) ~= "table" then return false, "bad_ref" end
    local a = {}
    for k, v in pairs(ref) do
        local tv = type(v)
        if type(k) == "string" and (tv == "number" or tv == "string" or tv == "boolean") then a[k] = v end
    end
    a.setAt = M.worldHours() or 0
    mind.anchors[kind] = a
    return true
end

function M.getAnchor(kind)
    local mind = M.mind()
    if not mind then return nil end
    return mind.anchors[kind]
end

-- vehicles are keyed by the database id as a string (ModData-safe)
function M.noteVehicle(sqlId, info)
    local mind = M.mind()
    if not mind then return false, "no_mind" end
    if type(sqlId) ~= "number" or sqlId < 0 or sqlId % 1 ~= 0 then return false, "bad_sql_id" end
    if type(info) ~= "table" then return false, "bad_info" end
    local key = tostring(math.floor(sqlId))
    local v = mind.vehicles[key] or {}
    for _, f in ipairs({ "x", "y", "z" }) do
        if type(info[f]) == "number" then v[f] = info[f] end
    end
    if type(info.script) == "string" then v.script = info.script end
    if info.loaded ~= nil then v.loaded = info.loaded == true end
    if info.primary == true then v.primary = true elseif info.primary == false then v.primary = nil end
    v.lastSeen = M.worldHours() or v.lastSeen or 0
    mind.vehicles[key] = v
    return true
end

function M.getVehicle(sqlId)
    local mind = M.mind()
    if not mind or type(sqlId) ~= "number" then return nil end
    return mind.vehicles[tostring(math.floor(sqlId))]
end

function M.probe()
    local mind = M.mind()
    if not mind then return nil, "no_mind" end
    mind.probe.n = (mind.probe.n or 0) + 1
    mind.probe.at = M.worldHours() or 0
    return mind.probe.n
end

function M.stats()
    local mind, why = M.open()
    if not mind then return nil, why end
    local n, rows, v, minds = 0, 0, 0, 0
    for _, c in pairs(mind.containers) do n = n + 1; rows = rows + #(c.rows or {}) end
    for _ in pairs(mind.vehicles) do v = v + 1 end
    for _ in pairs(M._root.minds) do minds = minds + 1 end
    return { version = M.VERSION, schema = M._root.schema, id = M._id, minds = minds, containers = n, rows = rows,
             vehicles = v, probe = mind.probe.n or 0, probeAt = mind.probe.at, hours = M.worldHours() }
end

-- two internal verbs for the runtime proof, reachable through the existing SolAct_Request channel; not in the brain's catalog
local function verb(id)
    if id == "sol_mem_stats" then
        local s, why = M.stats()
        if not s then return false, "mem_unavailable:" .. tostring(why) end
        return true, "mem v" .. s.version .. " mind=" .. tostring(s.id) .. " minds=" .. s.minds .. " containers=" .. s.containers
            .. " rows=" .. s.rows .. " vehicles=" .. s.vehicles .. " probe=" .. s.probe .. " at=" .. tostring(s.probeAt) .. " hours=" .. tostring(s.hours)
    end
    if id == "sol_mem_probe" then
        local n, why = M.probe()
        if not n then return false, "mem_unavailable:" .. tostring(why) end
        return true, "probe=" .. n .. " at=" .. tostring(M.worldHours())
    end
    return nil
end
local function install()
    if U._memInstalled then return end
    U._memInstalled = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_mem_stats" or id == "sol_mem_probe" then
            local ok, a, b = pcall(verb, id)
            if not ok then return false, "mem_error" end
            return a, b
        end
        return base(id, option)
    end
    log("verbs installed v" .. M.VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(install) end
log("ready v" .. M.VERSION)
