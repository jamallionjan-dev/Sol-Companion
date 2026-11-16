-- SolCombatEquipFallback.lua - switches combat_equip_fallback and preferred_weapon (2026-11-11, s98).
-- Live 11:18-11:36: Sol held and aimed a rifle but never fired; "carry this weapon" on the M4A1 said
-- "Could not equip item: retry_exhausted".
--   1. EFZ: setPrimaryHandItem(M4A1) fires OnEquipPrimary; TW/Runtime R.update -> R.refresh finds the assembly broken
--      (duplicatePath: two installed parts on one tree path), writes md.TW.ready=false and clears both hands. Equip reads
--      the hand back, restores the old gun and fails ("[TW] Assembly needs attention ... duplicatePath" in the same frame).
--   2. LF ActionSupervisor: after 4 failures of equip_weapon on that weapon the retry record is exhausted with no expiry;
--      every later begin is refused (retry_exhausted), combat and the player's order alike.
--   3. SCCombat.execute dropped the reason ("equip_rejected") and chose the same M4A1 next pulse, for ever; stomps and
--      shoves need no equip, so she only stomped.
-- combat_equip_fallback:
--   G.unusable(item): a weapon whose equip was rejected is not usable for BLOCK_MS; an EFZ weapon whose assembly is not
--     ready (md.TW.ready == false, EFZ's own record) is not usable (EFZ clears it from any hands).
--   G.rejected(...): logs the real reason, blocks the weapon, and says what to do with the weapon in her hands.
--   G.choose(...): a usable gun already in her hands is kept (no swap for nothing).
--   G.ignoreRetry(opts) / G.retryExpired(record): an explicit equip order skips the retry ledger; an exhausted equip
--     record expires after EXHAUSTED_MS.
-- preferred_weapon:
--   "carry this weapon" marks her preferred weapon (item mod data SC_ManualEquipFor = her id, LF's own marker) even when
--   the equip fails; combat keeps the held or preferred weapon while it can fire; when it cannot, she says why plainly.
--   The preference changes only when he picks another weapon; a new Sol (after death) has a new id, so it is gone.
-- s99 (0.3.0): an "empty" reason asks SolMagFill to load the gun when she is safe (mag_fill); with melee_choice a melee
-- weapon is no longer kept only because it is in her hands, and "carry this weapon" on a melee weapon marks her melee
-- weapon (SolWeaponPick.markMelee).
-- Switches read at call time. Off: nothing changes. Logs and speaks on change only. ASCII (Arabic as decimal escapes).
SolCombatEquipFallback = SolCombatEquipFallback or {}
local G = SolCombatEquipFallback
G.VERSION = "0.3.0"
G.BLOCK_MS = 60000
G.EXHAUSTED_MS = 180000
G.SPEAK_MS = 5000
G.blocked = G.blocked or setmetatable({}, { __mode = "k" })
G.said = G.said or setmetatable({}, { __mode = "k" })
G.spoke = G.spoke or setmetatable({}, { __mode = "k" })

-- Shami lines (UTF-8 as decimal escapes)
local AR = {
    AL = "\216\167\217\132\217\128",
    PARTS = "\217\129\217\138\217\135\216\167 \217\133\216\180\217\131\217\132\216\169 \216\168\216\167\217\132\217\130\216\183\216\185",
    EMPTY = "\217\129\216\167\216\182\217\138\216\169 \217\136\217\133\216\167 \216\182\217\132 \216\165\217\132\217\135\216\167 \217\129\216\180\217\131",
    BROKEN = "\217\133\217\131\216\179\217\136\216\177\216\169",
    REFUSED = "\217\133\216\167 \216\185\217\133 \216\170\216\177\217\131\216\168 \217\133\216\185\217\138",
    STAY = "\216\140 \216\177\216\173 \216\182\217\132 \216\185\216\167\217\132\217\128",
    OTHER = "\216\140 \216\177\216\173 \216\175\216\168\217\145\216\177 \216\173\216\167\217\132\217\138 \216\168\216\186\217\138\216\177\217\135\216\167.",
    NOW = "\216\140 \217\133\216\167 \216\168\217\130\216\175\216\177 \216\163\216\173\217\133\217\132\217\135\216\167 \217\135\217\132\217\130.",
}
G.AR = AR

local function log(m) print("[SolCombatEquipFallback] " .. tostring(m)) end
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
local function name(it) return tostring(call(it, "getDisplayName") or call(it, "getFullType") or it) end
-- short name for speech: "M4A1", "G28"
local function short(it)
    local t = tostring(call(it, "getType") or call(it, "getFullType") or "")
    t = string.match(t, "([%w_]+)$") or t
    if t == "" then t = name(it) end
    return t
end
local function sw(fix) local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on(fix) == true end
function G.on() return sw("combat_equip_fallback") end
function G.preferOn() return sw("preferred_weapon") end
-- s99: an empty gun is a job for SolMagFill (it waits until no zombie is within its safe distance)
local function fillIfEmpty(actor, item, why)
    if why ~= "empty" then return end
    local M = g("SolMagFill")
    if type(M) == "table" and type(M.request) == "function" then pcall(M.request, actor, item, "empty_refusal") end
end
G.fillIfEmpty = fillIfEmpty

-- ---------------------------------------------------------------- EFZ
-- md.TW is EFZ's own record (TW/Runtime R.refresh): ready=false means EFZ takes it out of any hands.
function G.efzNotReady(item)
    if item == nil or call(item, "hasModData") ~= true then return false end
    local md = call(item, "getModData")
    local tw = type(md) == "table" and md.TW or nil
    return type(tw) == "table" and tw.key ~= nil and tw.ready == false
end

-- The EFZ problem in words: duplicatePath with the paths, missingPath, or notReady.
function G.efzProblem(item)
    local R = g("TWRuntime")
    if type(R) == "table" and type(R.read) == "function" and type(R.isWeapon) == "function" then
        local okW, isW = pcall(R.isWeapon, item)
        if okW and isW == true then
            local ok, _, entries, _, problem = pcall(R.read, item)
            if ok and problem == "duplicatePath" and type(entries) == "table" then
                local seen, dups = {}, {}
                for _, e in ipairs(entries) do
                    if type(e) == "table" and e.path ~= nil then
                        if seen[e.path] then dups[#dups + 1] = tostring(e.path) .. "(" .. tostring(e.fullType) .. ")" end
                        seen[e.path] = true
                    end
                end
                return "duplicatePath " .. table.concat(dups, ",")
            end
            if ok and problem ~= nil then return tostring(problem) end
        end
    end
    if G.efzNotReady(item) then return "notReady" end
    return nil
end

-- ---------------------------------------------------------------- usability
function G.unusable(item)
    if item == nil or not G.on() then return false end
    local untilMs = G.blocked[item]
    if untilMs ~= nil then
        if nowMs() < untilMs then return true end
        G.blocked[item] = nil
    end
    if G.efzNotReady(item) then
        if G.said[item] ~= "efz" then
            G.said[item] = "efz"
            log(name(item) .. ": EFZ assembly not ready (" .. tostring(G.efzProblem(item) or "notReady") .. "); not used until it is fixed")
        end
        return true
    end
    return false
end

-- plain reason for a weapon record that cannot be used: parts / broken / empty / refused
function G.whyUnusable(weapon, reason)
    local item = type(weapon) == "table" and weapon.item or weapon
    if item ~= nil and (G.efzNotReady(item) or G.efzProblem(item) ~= nil) then return "parts" end
    if type(weapon) == "table" and (tonumber(weapon.condition) or 1) <= 0 then return "broken" end
    if type(weapon) == "table" and weapon.ranged == true and (tonumber(weapon.ammo) or 0) <= 0 and reason == "no_usable_weapon" then return "empty" end
    return "refused"
end

-- ---------------------------------------------------------------- speech
local function speak(actor, line, key)
    if actor == nil then return false end
    local t = nowMs()
    local last = G.spoke[actor]
    if type(last) == "table" and last.key == key and t - (last.at or 0) < 300000 then return false end
    if type(last) == "table" and t - (last.at or 0) < G.SPEAK_MS and last.key ~= key then return false end
    G.spoke[actor] = { key = key, at = t }
    local O = g("SolOverlay")
    local shown = false
    if type(O) == "table" and type(O.speak) == "function" then
        local ok, r = pcall(O.speak, actor, line, 6000); shown = ok and r == true
    end
    if not shown then
        local SC = g("SurvivorCompanion")
        local U = type(SC) == "table" and SC.GameplayUtil or nil
        if type(U) == "table" and type(U.say) == "function" then pcall(U.say, actor, line) end
    end
    log("say " .. tostring(key))
    return true
end

function G.spokeRecently(actor)
    local last = actor ~= nil and G.spoke[actor] or nil
    return type(last) == "table" and nowMs() - (last.at or 0) < 1500
end

function G.line(item, why, held)
    local r = AR.REFUSED
    if why == "parts" then r = AR.PARTS elseif why == "broken" then r = AR.BROKEN elseif why == "empty" then r = AR.EMPTY end
    local tail = AR.NOW
    if held == false then tail = AR.OTHER
    elseif held ~= nil then tail = AR.STAY .. short(held) .. "." end
    return AR.AL .. short(item) .. " " .. r .. tail
end

-- she tells him she is not using his pick (held: the item she stays on, false: another one, nil: "not now")
function G.tell(actor, item, why, held)
    if not G.preferOn() or item == nil then return false end
    return speak(actor, G.line(item, why, held), tostring(item) .. "|" .. tostring(why))
end

-- ---------------------------------------------------------------- preference (LF's marker SC_ManualEquipFor)
local function GU() local SC = g("SurvivorCompanion"); return type(SC) == "table" and SC.GameplayUtil or nil end
function G.markPreferred(actor, item)
    if not G.preferOn() or actor == nil or item == nil then return false end
    local U = GU()
    if type(U) ~= "table" then return false end
    local id = U.idOf(actor)
    local inv = U.inventory(actor)
    if inv ~= nil then
        for _, c in ipairs(U.inventoryItemsDeep(inv, 240) or {}) do
            if c ~= item and call(c, "hasModData") == true then
                local d = call(c, "getModData")
                if type(d) == "table" and d.SC_ManualEquipFor == id then d.SC_ManualEquipFor = nil end
            end
        end
    end
    local data = call(item, "getModData")
    if type(data) == "table" then data.SC_ManualEquipFor = id end
    local WP = g("SolWeaponPick")
    if type(WP) == "table" and type(WP.markMelee) == "function" then pcall(WP.markMelee, actor, item) end   -- s99 melee_choice
    log("preferred weapon: " .. name(item))
    return true
end

-- ---------------------------------------------------------------- choice
-- weapons: SCCombat records (one has equipped = true); usable(w): weaponUsableNow; manualId: her id.
-- Returns the record to use, or nil for LF's own scoring. LF's manual loop already returned a usable preferred weapon.
function G.choose(actor, weapons, usable, manualId)
    local fb, pr = G.on(), G.preferOn()
    if not fb and not pr then return nil end
    local held, pref
    for _, w in ipairs(weapons or {}) do
        if w.equipped == true then held = w end
        if pr and pref == nil and call(w.item, "hasModData") == true then
            local d = call(w.item, "getModData")
            if type(d) == "table" and manualId ~= nil and d.SC_ManualEquipFor == manualId then pref = w end
        end
    end
    local heldOk = held ~= nil and usable(held) == true
    if pref ~= nil and held ~= nil and pref.item == held.item and heldOk then return held end
    if pref ~= nil and (held == nil or pref.item ~= held.item) and not usable(pref) then
        local why_ = G.whyUnusable(pref, "no_usable_weapon")
        G.tell(actor, pref.item, why_, heldOk and held.item or false)
        fillIfEmpty(actor, pref.item, why_)
    end
    if heldOk and held.ranged ~= true and sw("melee_choice") then return nil end   -- s99: melee is scored (SolWeaponPick)
    if heldOk and (pr or held.ranged == true) then return held end
    return nil
end

-- ---------------------------------------------------------------- a rejected equip in combat
-- held: weaponRecord of her primary hand (or nil); heldUsable: weaponUsableNow for it, same class as the rejected choice.
-- Returns the action kind to do with the held weapon, or nil.
function G.rejected(actor, item, reason, held, heldUsable, kind)
    local why = tostring(reason or "unknown")
    G.blocked[item] = nowMs() + G.BLOCK_MS
    local efz = G.efzProblem(item)
    local useKind
    -- a reload/unjam planned for the rejected gun is not a plan for another one: the next pulse decides afresh
    if heldUsable == true and type(held) == "table" and held.item ~= nil and held.item ~= item
        and kind ~= "reload" and kind ~= "unjam" then
        if held.ranged == true then
            local chambered = call(held.item, "isRoundChambered") == true
            if held.jammed == true then useKind = "unjam"
            elseif kind == "shoot" and (tonumber(held.ammo) or 0) <= 0 and not chambered then useKind = "reload"
            else useKind = kind end
        else
            useKind = kind
        end
    end
    local m = "equip of " .. name(item) .. " rejected: " .. why
        .. (efz and ("; EFZ assembly: " .. efz) or "")
        .. "; not used for " .. tostring(math.floor(G.BLOCK_MS / 1000)) .. " s; "
        .. (useKind and ("using the " .. name(held.item) .. " in her hands (" .. tostring(useKind) .. ")")
            or "nothing usable in her hands, next pulse picks the next usable weapon (melee last)")
    if G.said[item] ~= m then G.said[item] = m; log(m) end
    G.tell(actor, item, efz and "parts" or "refused", useKind and held.item or false)
    return useKind
end

-- ---------------------------------------------------------------- the player's order failed
function G.pickFailed(actor, item, reason, weapon)
    if not G.preferOn() then return false end
    local why = G.whyUnusable(weapon or item, reason)
    log("carry order for " .. name(item) .. " failed: " .. tostring(reason) .. " (" .. why .. ")")
    fillIfEmpty(actor, item, why)
    local U = GU()
    local held = U and select(1, U.call(actor, "getPrimaryHandItem")) or nil
    if held == item then held = nil end
    return G.tell(actor, item, why, held)
end

-- ---------------------------------------------------------------- LF ActionSupervisor retry ledger
function G.ignoreRetry(options)
    return type(options) == "table" and options.immediateCommand == true and G.on()
end
function G.exhaustedRetryAt(action, current)
    if action ~= "equip_weapon" or not G.on() then return nil end
    return current + G.EXHAUSTED_MS
end
function G.retryExpired(record, current)
    return type(record) == "table" and record.exhausted == true and record.action == "equip_weapon"
        and tonumber(record.retryAt) ~= nil and (tonumber(current) or 0) >= tonumber(record.retryAt)
end

log("ready v" .. G.VERSION)
return G
