-- s103_fakes.lua: the Java side for the s103 offline tests. EFZ's own TW/Core, TW/Data and TW/Builds are the real ones
-- (loaded read-only from the Workshop folder); HandWeapon's part store follows B42's bytecode (javap -c HandWeapon):
--   attachWeaponPart(chr, part, change): a part of the same PartType already on comes off first, then setWeaponPart
--   setWeaponPart: map[PartType] = part, list.add(part);   clearWeaponPart(part): map.remove(PartType), list.remove(part)
--   detachWeaponPart(chr, part, change): nothing unless the part is in the list AND map[PartType] == part
--   clearAllWeaponParts: map.clear(), list.clear()
-- Every EFZ template has its own PartType (TW_Items.txt: PartType = TW_<tpl>, copies TW_<tpl>_<n>).
-- TWRuntime here keeps EFZ's code for read / installedPath / createDefault (OnCreate) / applyTree (Runtime.lua 51-78,
-- 484-506, 798-839); refresh records md.TW.ready from C.validate + the problem of R.read, as Runtime.lua:451 does.
local C = require("TW/Core")
local D = C.data
EFZC = C
function jl(t) return { size = function() return #t end, get = function(_, i) return t[i + 1] end } end
NEXTID = 0
ONCREATE = true
CALLS = {}
local function note(n) CALLS[n] = (CALLS[n] or 0) + 1 end

local IT = {}
IT.__index = IT
-- any other setter SCPersistence restores (condition, favourite, visual ...) is accepted and ignored
setmetatable(IT, { __index = function(_, k)
    if type(k) == "string" and (string.find(k, "^set") or string.find(k, "^copy")) then return function() return true end end
    return nil
end })
function IT:getFullType() return self.t end
function IT:getType() return (string.match(self.t, "%.(.+)$")) or self.t end
function IT:getModule() return (string.match(self.t, "^(.-)%.")) end
function IT:getDisplayName() return self.name or self.t end
function IT:getName() return self.name or self.t end
function IT:getModData() return self.md end
function IT:getID() return self.id end
function IT:getPartType() return self.ptype end
function IT:getContainer() return self.container end
function IT:setContainer(c) self.container = c end
function IT:getCurrentAmmoCount() return self.ammo or 0 end
function IT:setCurrentAmmoCount(n) self.ammo = n end
function IT:isContainsClip() return self.clip == true end
function IT:setContainsClip(b) self.clip = b end
function IT:isRoundChambered() return self.chambered == true end
function IT:setRoundChambered(b) self.chambered = b end
function IT:getMagazineType() return self.mag end
function IT:setMagazineType(m) self.mag = m end
function IT:getMaxAmmo() return self.maxAmmo or 0 end
function IT:setMaxAmmo(n) self.maxAmmo = n end
function IT:haveChamber() return self.cls == "HandWeapon" end
function IT:getCondition() return 10 end
function IT:isRanged() return self.cls == "HandWeapon" end
function IT:transmitModData() note("transmitModData") end
-- the part store (weapons only)
local function clearPart(w, p)
    if w.map[p.ptype] ~= nil then w.map[p.ptype] = nil end
    for i, q in ipairs(w.list) do if q == p then table.remove(w.list, i); break end end
end
local function detach(w, chr, p, change)
    if p == nil then return end
    local inList = false
    for _, q in ipairs(w.list) do if q == p then inList = true end end
    if not inList or w.map[p.ptype] ~= p then return end
    clearPart(w, p)
end
function IT:getAllWeaponParts() if self.list == nil then error("no such method") end return jl(self.list) end
function IT:clearAllWeaponParts() note("clearAllWeaponParts"); self.map = {}; self.list = {} end
function IT:attachWeaponPart(a, b, c)
    local chr, p, change
    if type(a) == "table" and a.cls == "WeaponPart" then p, change = a, b else chr, p, change = a, b, c end
    if p == nil then return end
    if self.map[p.ptype] ~= nil then detach(self, chr, self.map[p.ptype], change) end
    if self.map[p.ptype] ~= nil then clearPart(self, self.map[p.ptype]) end
    self.map[p.ptype] = p
    self.list[#self.list + 1] = p
end
function IT:detachWeaponPart(a, b, c)
    if type(a) == "table" and a.cls == "WeaponPart" then return detach(self, nil, a, true) end
    return detach(self, a, b, c)
end

function instanceItem(t)
    if t == nil or UNKNOWN and UNKNOWN[t] then return nil end
    NEXTID = NEXTID + 1
    local it = setmetatable({ t = t, md = {}, id = NEXTID }, IT)
    local meta = D.types[t]
    if D.byType[t] then
        it.cls, it.map, it.list = "HandWeapon", {}, {}
        if ONCREATE then TWRuntime.createDefault(it) end         -- EFZ OnCreate = TWRuntime.createDefault
    elseif meta then
        it.cls = "WeaponPart"
        local short = string.match(t, "%.P_(.+)$") or t
        it.ptype = "TW_" .. short
        if C.isClip(meta.tpl) then it.maxAmmo, it.ammo = D.items[meta.tpl].capacity, 0 end
    else
        it.cls = "InventoryItem"
    end
    return it
end
function instanceof(o, cls)
    if type(o) ~= "table" then return false end
    if cls == "InventoryItem" then return o.t ~= nil end
    return o.cls == cls
end

function container(name)
    local c = { items = {}, name = name or "inv" }
    function c:getItems() return jl(self.items) end
    function c:AddItem(x)
        if type(x) == "string" then x = instanceItem(x) end
        if x == nil then return nil end
        self.items[#self.items + 1] = x; x.container = self; return x
    end
    function c:Remove(x) for i, q in ipairs(self.items) do if q == x then table.remove(self.items, i); x.container = nil; return end end end
    function c:DoRemoveItem(x) return self:Remove(x) end
    function c:contains(x) for _, q in ipairs(self.items) do if q == x then return true end end return false end
    function c:containsRecursive(x) return self:contains(x) end
    function c:getCapacityWeight() return 1 end
    return c
end

-- TWRuntime (EFZ's code where it matters)
local R = {}
TWRuntime = R
REPORTS = {}
function R.key(item) return item and item.cls == "HandWeapon" and D.byType[item:getFullType()] or nil end
function R.meta(item) return item and D.types[item:getFullType()] or nil end
function R.isMagazine(tpl) return C.isClip(tpl) end
function R.installedPath(part)
    local meta = R.meta(part)
    if not meta then return nil end
    if R.isMagazine(meta.tpl) then return "mod_magazine" end
    local md = part:getModData()
    return type(md.TWPath) == "string" and md.TWPath or nil
end
function R.read(weapon)
    local tree, entries, parts, problem = {}, {}, {}, nil
    local list = weapon:getAllWeaponParts()
    for i = 0, list:size() - 1 do
        local part = list:get(i)
        local meta = R.meta(part)
        local path = R.installedPath(part)
        if meta and path then
            if tree[path] then problem = "duplicatePath" end
            tree[path] = meta.tpl
            parts[path] = part
            entries[#entries + 1] = { path = path, tpl = meta.tpl }
        elseif meta then
            problem = problem or "missingPath"
        end
    end
    return tree, entries, parts, problem
end
function R.typeFor(tpl, copy) return copy == 0 and D.items[tpl].pz or D.items[tpl].pz .. "_" .. copy end
function R.refresh(weapon, player)
    R.refreshed = (R.refreshed or 0) + 1
    local key = R.key(weapon)
    if not key then return end
    local tree, _, _, problem = R.read(weapon)
    local valid, reason = C.validate(key, tree)
    local okS, s = pcall(C.stats, key, tree)
    local ready = okS and type(s) == "table" and s.ready or false
    if problem or not valid then ready = false; REPORTS[#REPORTS + 1] = tostring(problem or reason) end
    weapon:getModData().TW = { schema = 2, key = key, ready = ready }
    if player then UNEQUIPPED = (UNEQUIPPED or 0) + 1 end
    return s
end
function R.createDefault(weapon)
    local key = R.key(weapon)
    if not key then return end
    local preset = C.presetTree(key)
    assert(C.validate(key, preset))
    local paths = {}
    for path in pairs(preset) do paths[#paths + 1] = path end
    table.sort(paths, function(a, b) if C.depth(a) == C.depth(b) then return a < b end return C.depth(a) < C.depth(b) end)
    local used = {}
    for _, path in ipairs(paths) do
        local tpl = preset[path]
        local copy = used[tpl] or 0
        used[tpl] = copy + 1
        local full = R.isMagazine(tpl) and C.clipType(key, tpl) or R.typeFor(tpl, copy)
        local part = assert(instanceItem(full), "[TW] Missing default item " .. full)
        if not R.isMagazine(tpl) then part:getModData().TWPath = path end
        weapon:attachWeaponPart(part, false)
    end
    weapon:setContainsClip(C.isClip(preset.mod_magazine))
    weapon:setCurrentAmmoCount(0)
    R.refresh(weapon, nil)
end
function R.applyTree(weapon, tree)
    local key = R.key(weapon)
    if not key then return false, "invalidItem" end
    local valid, reason = C.validate(key, tree)
    if not valid then return false, reason end
    local list = weapon:getAllWeaponParts()
    local installed = {}
    for i = 0, list:size() - 1 do installed[#installed + 1] = list:get(i) end
    for _, part in ipairs(installed) do
        local meta = R.meta(part)
        if meta then weapon:detachWeaponPart(part) end
    end
    local paths = {}
    for path, tpl in pairs(tree) do if not R.isMagazine(tpl) then paths[#paths + 1] = path end end
    table.sort(paths, function(a, b) if C.depth(a) == C.depth(b) then return a < b end return C.depth(a) < C.depth(b) end)
    local used = {}
    for _, path in ipairs(paths) do
        local tpl = tree[path]
        local copy = used[tpl] or 0
        used[tpl] = copy + 1
        local part = instanceItem(R.typeFor(tpl, copy))
        if not part then return false, "missingNativeAlias" end
        part:getModData().TWPath = path
        weapon:attachWeaponPart(part, false)
    end
    weapon:setCurrentAmmoCount(0)
    weapon:setRoundChambered(false)
    weapon:getModData().AmmoList = nil
    if C.isClip(tree.mod_magazine) then
        local full = C.clipType(key, tree.mod_magazine)
        weapon:setMagazineType(full)
        weapon:setMaxAmmo(D.items[tree.mod_magazine].capacity)
        weapon:setContainsClip(true)
        -- Gunworks Magazine.manageMagazineAttachment(weapon, full): the inserted magazine shown as a part
        local clip = instanceItem(full)
        weapon:attachWeaponPart(clip, false)
    else
        weapon:setContainsClip(false)
    end
    R.refresh(weapon, nil)
    return true
end
-- EFZ's loose-part rule (Runtime.lua:285): a carried EFZ part without TWPath, by template
function R.looseParts(player)
    local out = {}
    for _, item in ipairs(player:getInventory().items) do
        local meta = R.meta(item)
        if meta and item.cls == "WeaponPart" and not item:getModData().TWPath then
            out[meta.tpl] = out[meta.tpl] or {}
            table.insert(out[meta.tpl], item)
        end
    end
    return out
end

-- a tree and its duplicates, from the part list (what R.read and SolCombatEquipFallback report)
function treeOf(w)
    local tree, _, _, problem = R.read(w)
    local seen, dups = {}, {}
    for _, p in ipairs(w.list) do
        local path = R.installedPath(p)
        if path then if seen[path] then dups[#dups + 1] = path end; seen[path] = true end
    end
    table.sort(dups)
    return tree, problem, dups
end
function sameTree(a, b)
    for k, v in pairs(a) do if b[k] ~= v then return false, k end end
    for k, v in pairs(b) do if a[k] ~= v then return false, k end end
    return true
end
