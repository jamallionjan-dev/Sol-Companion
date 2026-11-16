-- SolItemStacks 0.3.0 (s100 item_stacks, s105 live fix)
-- 0.3.0: 0.2.0 still merged nothing live (14:54, 752 root items) although the fakes grouped. Items whose modData is
--   the same are now one stack too (key = full type + modData as sorted text; a table that cannot be compared keeps
--   the item apart), and a one-shot diagnostic ("[SolItemStacks] diag ...") logs the Java facts of the first 3 root
--   items and of the first repeated types when a walk merges nothing.
-- s105: 0.1.0 never grouped anything live. Two rules rejected every loose round (verified in projectzomboid.jar 42.22):
--   * "ComboItem" was on the stateful list, but Item.InstanceItem makes EVERY ItemType=normal item a ComboItem
--     (rounds, nails, pills, magazines); Kahlua's instanceof answers true for it (ComboItem is exposed).
--   * getCount ~= 1 was taken as per-item state, but InstanceItem copies the script's Count onto every instance:
--     Base.308Bullets / Base.556Bullets have Count = 5, so each loose round answers getCount() == 5.
--   Now: ComboItem is stackable unless another rule says otherwise, and the count is ignored: it is a script constant
--   copied onto every instance of the type (no per-item call, so the walk costs no more than 0.1.0 meant it to).
--   Cache (s105): the grouped walk is kept per inventory and reused while the inventory is unchanged. Signature =
--   getItems():size() and getContentsWeight() of the root and of every bag the walk opened (Java-side sums, no item
--   call; OnContainerUpdate is not used: vanilla fires it ad hoc, mostly without the container). Also rebuilt after
--   CACHE_MAX_MS, so a change that keeps count and weight (an item gaining modData) is seen within that time.
--   Each rebuild reports its ms to SolPerf as "item_stacks".
-- Identical, stateless items are ONE entry with a count (500 loose 7.62x51 rounds = one stack of 500), so an item walk
-- capped at N entries sees N different things instead of N rounds.
-- Stateless = same full type, no modData, and a type that carries no per-item state: not a weapon, container, clothing,
-- food, drainable, key, radio, literature, map, animal, moveable, fluid container or magazine. Those stay separate.
--   S.deep(U, inv, limit, containerLimit)  LF's inventoryItemsDeep, grouped: returns result, containers, info
--       result = one entry per distinct thing (<= limit), then (budget left) further members of the stacks, so a
--       caller that wants several identical items (pay 3 Money, 10 Nails) still gets them; info.reps = the distinct
--       entries, info.count[rep] = the stack count, info.byType[fullType] = total seen, info.distinct = #reps.
--   S.count(U, actorOrInventory, fullType)   native getCountTypeRecurse: 500 without a walk
--   S.cachedRead(it, call, ns) / S.remember(it, d, ns)   Sol's own readers: a stateless type is read once per type
-- Switch item_stacks (SolAuthority.on, read at call time). Off: callers use their old code.
SolItemStacks = SolItemStacks or {}
local S = SolItemStacks
S.VERSION = "0.3.0"
S.RAW_CAP = 4000          -- items read from one container at most (the old walk read 180)
S.visits = { raw = 0, full = 0, cached = 0 }

function S.enabled()
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("item_stacks") == true
end

local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or type(f) ~= "function" then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function isA(o, cls)
    if type(instanceof) ~= "function" then return false end
    local ok, r = pcall(instanceof, o, cls)
    return ok and r == true
end

-- not "ComboItem": that is the class of every plain (ItemType = normal) item, loose rounds included (s105)
local STATEFUL = { "HandWeapon", "InventoryContainer", "Clothing", "Food", "DrainableComboItem", "Key", "Radio",
                   "Literature", "MapItem", "AnimalInventoryItem", "Moveable" }
local typeClass = {}      -- fullType -> true (stackable type) / false (per-item state)
local typeCount = 0

-- the type rule without the cache: true, or false and the reason
local function typeVerdict(it)
    for _, cls in ipairs(STATEFUL) do if isA(it, cls) then return false, "instanceof " .. cls end end
    local cat = tostring(call(it, "getCategory") or "")
    if cat == "Weapon" or cat == "Food" or cat == "Clothing" or cat == "Container" or cat == "Drainable" or cat == "Key" then
        return false, "category " .. cat
    end
    if call(it, "getFluidContainer") ~= nil then return false, "fluid container" end
    if (tonumber((call(it, "getMaxAmmo"))) or 0) > 0 then return false, "maxAmmo > 0" end   -- a magazine holds its own rounds
    if call(it, "getItemContainer") ~= nil then return false, "item container" end
    return true, "stateless type"
end
S.typeVerdict = typeVerdict

-- type-level: decided once per full type from the first item seen
local function stackableType(it, ft)
    local c = typeClass[ft]
    if c ~= nil then return c end
    c = typeVerdict(it) == true
    if typeCount > 3000 then typeClass, typeCount = {}, 0 end
    typeClass[ft] = c; typeCount = typeCount + 1
    return c
end
S.stackableType = stackableType

-- per item: the stack key (or nil: this item is kept on its own), then the full type
-- modData as text, keys sorted: items whose modData is the same are still interchangeable (other mods tag loose
-- rounds, e.g. a loot mark). nil = cannot be compared (too big, too deep, a Java value): the item stays apart.
S.MD_MAX = 32
local function mdText(v, depth, budget)
    local tv = type(v)
    if tv == "string" then return "s" .. v end
    if tv == "number" or tv == "boolean" then return string.sub(tv, 1, 1) .. tostring(v) end
    if tv ~= "table" or depth > 2 then return nil end
    local keys = {}
    for k in pairs(v) do
        local tk = type(k)
        if tk ~= "string" and tk ~= "number" then return nil end
        budget.n = budget.n + 1
        if budget.n > S.MD_MAX then return nil end
        keys[#keys + 1] = k
    end
    table.sort(keys, function(a, b) return (type(a) .. tostring(a)) < (type(b) .. tostring(b)) end)
    local parts = {}
    for i, k in ipairs(keys) do
        local s = mdText(v[k], depth + 1, budget)
        if s == nil then return nil end
        parts[i] = string.sub(type(k), 1, 1) .. tostring(k) .. "=" .. s
    end
    return "{" .. table.concat(parts, ",") .. "}"
end
S.mdText = function(md) return mdText(md, 1, { n = 0 }) end

function S.key(it)
    local ft = call(it, "getFullType")
    if ft == nil then return nil end
    ft = tostring(ft)
    if not stackableType(it, ft) then return nil, ft end
    if call(it, "hasModData") == true then
        local md = call(it, "getModData")
        local s = type(md) == "table" and mdText(md, 1, { n = 0 }) or nil
        if s == nil then return nil, ft end
        return ft .. s, ft
    end
    return ft, ft
end

-- ---------------------------------------------------------------- temporary diagnostics (s105)
-- One block, once per session, the first time a walk of 2+ root items merges nothing: the first 3 root items and the
-- first item of up to 3 full types that occur more than once in the root yet were not merged. Every Java call is
-- read-only; getModData is only called when hasModData is true (it would create the table otherwise).
S.DIAG_CLASSES = { "InventoryItem", "ComboItem", "HandWeapon", "InventoryContainer", "Clothing", "Food",
                   "DrainableComboItem", "Key", "Radio", "Literature", "MapItem", "AnimalInventoryItem", "Moveable" }
S.loggedDiag = false
local function describe(it)
    local ft = tostring(call(it, "getFullType"))
    local cls = "?"
    local gs = rawget(_G, "getClassSimpleName")
    if type(gs) == "function" then local ok, v = pcall(gs, it); if ok then cls = tostring(v) end end
    local inst = {}
    for _, c in ipairs(S.DIAG_CLASSES) do if isA(it, c) then inst[#inst + 1] = c end end
    local hmd = call(it, "hasModData")
    local mdn, keys = 0, {}
    if hmd == true then
        local md = call(it, "getModData")
        if type(md) == "table" then
            for k, v in pairs(md) do
                mdn = mdn + 1
                if #keys < 6 then keys[#keys + 1] = tostring(k) .. "=" .. tostring(v) end
            end
        end
    end
    local tv, why = typeVerdict(it)
    local cached = typeClass[ft]
    local key = S.key(it)
    local verdict, reason
    if key ~= nil then verdict, reason = "stackable", "key " .. tostring(key)
    elseif cached == false then verdict, reason = "kept apart", "type cached false (first item of the type: " .. tostring(why) .. ")"
    elseif hmd == true then verdict, reason = "kept apart", "modData not comparable"
    else verdict, reason = "kept apart", tostring(why) end
    return ft .. " class=" .. cls .. " getCategory=" .. tostring(call(it, "getCategory"))
        .. " displayCategory=" .. tostring(call(it, "getDisplayCategory"))
        .. " instanceof=[" .. table.concat(inst, ",") .. "] hasModData=" .. tostring(hmd)
        .. " modData=" .. tostring(mdn) .. (#keys > 0 and ("{" .. table.concat(keys, ",") .. "}") or "")
        .. " getCount=" .. tostring(call(it, "getCount")) .. " getMaxAmmo=" .. tostring(call(it, "getMaxAmmo"))
        .. " fluid=" .. tostring(call(it, "getFluidContainer") ~= nil) .. " itemContainer=" .. tostring(call(it, "getItemContainer") ~= nil)
        .. " typeVerdict=" .. tostring(tv) .. "(" .. tostring(why) .. ") cachedType=" .. tostring(cached)
        .. " -> " .. verdict .. ": " .. reason
end
function S.diagnose(rootItems, why)
    if S.loggedDiag then return end
    local n = #rootItems
    -- only a walk that had something to merge (a full type twice in the root) says anything
    local once, repeated = {}, false
    for i = 1, n do
        local ft = tostring(call(rootItems[i], "getFullType"))
        if once[ft] then repeated = true break end
        once[ft] = true
    end
    if not repeated then return end
    S.loggedDiag = true
    print("[SolItemStacks] diag " .. tostring(why) .. ": root " .. tostring(n) .. " items, enabled=" .. tostring(S.enabled())
        .. " instanceof=" .. type(rawget(_G, "instanceof")))
    for i = 1, math.min(3, n) do
        local ok, line = pcall(describe, rootItems[i])
        print("[SolItemStacks] diag root#" .. i .. " " .. (ok and line or ("error " .. tostring(line))))
    end
    local seen, shown = {}, 0
    for i = 1, n do
        local ft = tostring(call(rootItems[i], "getFullType"))
        local first = seen[ft]
        if first == nil then seen[ft] = i
        elseif first ~= true then
            seen[ft] = true
            local ok, line = pcall(describe, rootItems[i])
            print("[SolItemStacks] diag repeat#" .. i .. " " .. (ok and line or ("error " .. tostring(line))))
            shown = shown + 1
            if shown >= 3 then break end
        end
    end
end

S.loggedGroup = false     -- temporary (s105): one line the first time a walk really merges something
local function logGroup(raw, entries)
    if S.loggedGroup then return end
    S.loggedGroup = true
    print("[SolItemStacks] grouped " .. tostring(raw) .. " items into " .. tostring(entries) .. " entries")
end

-- ---------------------------------------------------------------- LF's walk, grouped
local function build(U, inventory, limit, containerLimit)
    if inventory == nil then return {}, {}, { reps = {}, count = {}, byType = {}, distinct = 0 } end
    limit = math.max(1, math.floor(tonumber(limit) or 240))
    containerLimit = math.max(0, math.floor(tonumber(containerLimit) or 12))
    local reps, count, byType, members, order = {}, {}, {}, {}, {}
    local containers, seen = {}, {}
    local groups = {}         -- key -> rep
    local merged = 0          -- items counted into an earlier entry
    local V = S.visits
    -- the old reserve: a quarter of the budget for what is in the bags, unless there are no bags
    local rootLimit = limit
    if containerLimit > 0 then rootLimit = math.max(1, limit - math.floor(limit / 4)) end
    local function take(list, cap, root)
        local cut = false
        for _, item in ipairs(list) do
            V.raw = V.raw + 1
            local key, ft = S.key(item)
            local rep = key and groups[key]
            if rep ~= nil then
                count[rep] = count[rep] + 1
                byType[ft] = (byType[ft] or 0) + 1
                merged = merged + 1
                local m = members[rep]; if #m < limit then m[#m + 1] = item end
            else
                if #reps < cap then
                    V.full = V.full + 1
                    reps[#reps + 1] = item
                    count[item] = 1
                    if key then groups[key] = item; members[item] = {}; order[#order + 1] = item; byType[ft] = (byType[ft] or 0) + 1 end
                else cut = true end
                if root and key == nil and #containers < containerLimit then
                    local nested = U.call(item, "getItemContainer")
                    if nested ~= nil and not seen[nested] then seen[nested] = true; containers[#containers + 1] = nested end
                end
            end
        end
        return cut
    end
    local rootItems = U.inventoryItems(inventory, S.RAW_CAP)
    take(rootItems, rootLimit, true)
    if #containers == 0 and rootLimit < limit and #reps >= rootLimit then
        -- no bags to hold the reserve back for: the root may use the whole budget (as before)
        reps, count, byType, members, order, groups, merged = {}, {}, {}, {}, {}, {}, 0
        take(rootItems, limit, true)
    end
    for _, nested in ipairs(containers) do
        if #reps >= limit then break end
        take(U.inventoryItems(nested, S.RAW_CAP), limit, false)
    end
    if merged > 0 then logGroup(#reps + merged, #reps)
    elseif #rootItems >= 2 then S.diagnose(rootItems, "nothing merged") end
    local result = {}
    for i = 1, #reps do result[i] = reps[i] end
    -- budget left: further members of the stacks, so "give me 3 of these" callers still find 3
    -- round robin over the stacks, so 500 rounds do not take the whole rest from 30 nails
    local k, added = 1, true
    while added and #result < limit do
        added = false
        for _, rep in ipairs(order) do
            local m = members[rep][k]
            if m ~= nil then
                result[#result + 1] = m; added = true
                if #result >= limit then break end
            end
        end
        k = k + 1
    end
    return result, containers, { reps = reps, count = count, byType = byType, distinct = #reps }
end
S.build = build

-- ---------------------------------------------------------------- cache per inventory
S.CACHE_MAX_MS = 10000    -- a cached walk is rebuilt after this long even if the signature still matches
S.CACHE_MAX = 32          -- inventories kept (Kahlua has no working weak tables: the table is dropped when full)
S.stats = { hits = 0, builds = 0, ms = 0 }
local cache, cacheN = {}, 0
local function nowMs()
    local f = rawget(_G, "getTimestampMs")
    if type(f) ~= "function" then return 0 end
    local ok, v = pcall(f)
    return (ok and type(v) == "number") and v or 0
end
local function sigOf(inventory, containers)
    local function one(c)
        return tostring(call(call(c, "getItems"), "size")) .. ":" .. tostring(call(c, "getContentsWeight"))
    end
    local parts = { one(inventory) }
    for i, c in ipairs(containers) do parts[i + 1] = one(c) end
    return table.concat(parts, "|")
end
local function copy(t) local r = {}; for i = 1, #t do r[i] = t[i] end; return r end

-- result and containers are fresh lists on every call; info is shared with the cache: read it, never change it
function S.deep(U, inventory, limit, containerLimit)
    if inventory == nil then return build(U, inventory, limit, containerLimit) end
    limit = math.max(1, math.floor(tonumber(limit) or 240))
    containerLimit = math.max(0, math.floor(tonumber(containerLimit) or 12))
    local now = nowMs()
    local e = cache[inventory]
    if e ~= nil and e.limit == limit and e.containerLimit == containerLimit and now >= e.at and now - e.at < S.CACHE_MAX_MS
        and e.sig == sigOf(inventory, e.containers) then
        S.stats.hits = S.stats.hits + 1
        return copy(e.result), copy(e.containers), e.info
    end
    local result, containers, info = build(U, inventory, limit, containerLimit)
    local ms = nowMs() - now
    S.stats.builds = S.stats.builds + 1
    S.stats.ms = S.stats.ms + ms
    local P = rawget(_G, "SolUI")
    if type(P) == "table" and type(P.perfAdd) == "function" then P.perfAdd("item_stacks", ms) end
    if e == nil then
        if cacheN >= S.CACHE_MAX then cache, cacheN = {}, 0 end
        cacheN = cacheN + 1
    end
    cache[inventory] = { limit = limit, containerLimit = containerLimit, at = now, sig = sigOf(inventory, containers),
                         result = result, containers = containers, info = info }
    return copy(result), copy(containers), info
end
function S.invalidate(inventory)
    if inventory == nil then cache, cacheN = {}, 0 elseif cache[inventory] ~= nil then cache[inventory] = nil; cacheN = cacheN - 1 end
end

-- ---------------------------------------------------------------- count without a walk
function S.count(U, who, fullType)
    if who == nil or fullType == nil then return 0 end
    local inv = who
    if call(who, "getInventory") ~= nil and call(who, "getItems") == nil then inv = call(who, "getInventory") end
    local n = tonumber((call(inv, "getCountTypeRecurse", tostring(fullType))))
    if n ~= nil then return n end
    local _, _, info = S.deep(U, inv, 240, 12)
    return (info and info.byType[tostring(fullType)]) or 0
end

-- ---------------------------------------------------------------- Sol's own readers (SolInventory, SolWorldScan)
local reads = {}          -- ns -> fullType -> d (the record of a stateless type)
function S.cachedRead(it, ns)
    if not S.enabled() then return nil end
    local ft = call(it, "getFullType")
    if ft == nil then return nil end
    local c = reads[ns]
    if c == nil then return nil end
    local d = c[tostring(ft)]
    if d == nil then return nil end
    if call(it, "hasModData") == true then return nil end
    S.visits.cached = S.visits.cached + 1
    return d
end
function S.remember(it, d, ns)
    S.visits.full = S.visits.full + 1
    if type(d) ~= "table" or not S.enabled() then return end
    if d.fluid ~= nil or d.food ~= nil or d.bag ~= nil or d.uses ~= nil then return end
    if d.cond ~= nil and d.cond < 1 then return end
    local ft = call(it, "getFullType")
    if ft == nil then return end
    ft = tostring(ft)
    if not stackableType(it, ft) or call(it, "hasModData") == true then return end
    local c = reads[ns]
    if c == nil or c.n_ == nil or c.n_ > 3000 then c = { n_ = 0 }; reads[ns] = c end
    if c[ft] == nil then c[ft] = d; c.n_ = c.n_ + 1 end
end

function S.reset() typeClass, typeCount, reads = {}, 0, {}; S.visits = { raw = 0, full = 0, cached = 0 }; S.loggedGroup = false; S.loggedDiag = false
    cache, cacheN = {}, 0; S.stats = { hits = 0, builds = 0, ms = 0 } end

return S
