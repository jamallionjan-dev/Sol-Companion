-- SolSkills.lua - what Sol can and cannot do, by the game's own rules (PZ 42.21):
--   * every craft recipe (ScriptManager.instance:getAllCraftRecipes(), mods included)
--   * required skills: recipe:getRequiredSkill(i) -> CraftRecipeManager.hasPlayerRequiredSkill(rs, Sol)
--   * learning: recipe:needToBeLearn() + CraftRecipeManager.hasPlayerLearnedRecipe(recipe, Sol)
--   * reading: books/magazines in Sol's bag, judged like ISInventoryPane / ISReadABook; reading is the
--     game's own ISReadABook timed action on Sol (pages, XP multiplier, learned recipes all by the game).
-- The catalog goes to SolRecipes_Snapshot.txt (JSON, ASCII) for Sol Mind.
require "SolText"
SolUI = SolUI or {}
local U = SolUI
U.SKILLS_VERSION = "0.1.0"
local FILE = "SolRecipes_Snapshot.txt"
local PER_TICK = 30
local REBUILD_MS = 30 * 60 * 1000
local MAX_INPUTS, MAX_ALTS = 8, 6
local function log(m) print("[SolSkills] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function call(o, name, ...)
    if o == nil then return nil end
    local f = o[name]; if f == nil then return nil end
    local ok, v = pcall(f, o, ...); if ok then return v end; return nil
end
local function scall(fn, ...) if type(fn) ~= "function" then return nil end local ok, v = pcall(fn, ...); if ok then return v end return nil end

-- ---------------------------------------------------------------- one recipe, judged for Sol
function U.recipeInfo(recipe, actor)
    local r = { n = call(recipe, "getName"), t = call(recipe, "getTranslationName"), cat = call(recipe, "getCategory") }
    r.learn = call(recipe, "needToBeLearn") == true
    local CRM = CraftRecipeManager
    if r.learn then r.known = actor and CRM and scall(CRM.hasPlayerLearnedRecipe, recipe, actor) == true or false end
    local sc = tonumber((call(recipe, "getRequiredSkillCount"))) or 0
    if sc > 0 then
        r.skills = {}
        for i = 0, sc - 1 do
            local rs = call(recipe, "getRequiredSkill", i)
            local perk = call(rs, "getPerk")
            r.skills[#r.skills + 1] = { tostring(call(perk, "getName") or "?"), tonumber((call(rs, "getLevel"))) or 0,
                actor and CRM and scall(CRM.hasPlayerRequiredSkill, rs, actor) == true or false }
        end
    end
    local inputs = call(recipe, "getInputs")
    local ni = inputs and (tonumber((call(inputs, "size"))) or 0) or 0
    if ni > 0 then
        r["in"] = {}
        for i = 0, math.min(ni, MAX_INPUTS) - 1 do
            local inp = call(inputs, "get", i)
            local items = call(inp, "getPossibleInputItems")
            local na = items and (tonumber((call(items, "size"))) or 0) or 0
            local alts = {}
            for k = 0, math.min(na, MAX_ALTS) - 1 do
                local it = call(items, "get", k)
                local fn = call(it, "getFullName")
                if fn then alts[#alts + 1] = fn end
            end
            if #alts > 0 then r["in"][#r["in"] + 1] = { a = alts, q = tonumber((call(inp, "getAmount"))) } end
        end
    end
    return r
end

-- ---------------------------------------------------------------- catalog, built a little per tick
local job = nil
function U.startRecipeCatalog()
    local sm = ScriptManager and ScriptManager.instance
    local all = sm and call(sm, "getAllCraftRecipes")
    if not all then log("craft recipes not available"); return false end
    job = { all = all, i = 0, n = tonumber((call(all, "size"))) or 0, out = {}, actor = U.solActor and U.solActor() or nil, started = nowMs() }
    return true
end
local function finish()
    local snap = { v = 1, t = nowMs(), sol = job.actor ~= nil, count = #job.out, recipes = job.out }
    if U.jsonEncode then
        local ok, text = pcall(U.jsonEncode, snap)
        if ok then
            local okw, w = pcall(getFileWriter, FILE, true, false)
            if okw and w then w:write(text); w:close() end
        end
    end
    local known, learnable = 0, 0
    for _, r in ipairs(job.out) do if r.learn then learnable = learnable + 1; if r.known then known = known + 1 end end end
    U.recipeStats = { total = #job.out, learnable = learnable, known = known, at = nowMs() }
    log("catalog: " .. #job.out .. " recipes, " .. known .. "/" .. learnable .. " learnable known by Sol")
    job = nil
end
local lastBuild = -REBUILD_MS + 15000
local function onTick()
    if job then
        local t0 = nowMs()
        local stop = math.min(job.n, job.i + PER_TICK)
        for i = job.i, stop - 1 do
            local rec = call(job.all, "get", i)
            if rec then local ok, info = pcall(U.recipeInfo, rec, job.actor); if ok then job.out[#job.out + 1] = info end end
            job.i = i + 1
            if nowMs() - t0 >= 2 then break end
        end
        if job.i >= job.n then finish(); lastBuild = nowMs() end
        if U.perfAdd then U.perfAdd("recipes", nowMs() - t0) end
        return
    end
    if nowMs() - lastBuild > REBUILD_MS and U.solActor and U.solActor() then U.startRecipeCatalog() end
end
function U.refreshRecipes() lastBuild = -REBUILD_MS end
require "SolBudget"
SolBudget.register("recipes", onTick, { everyMs = 0, priority = 8 })

-- ---------------------------------------------------------------- books and magazines in Sol's bag
-- status rules copied from ISInventoryPane (2608-2611) and ISReadABook (38-50)
function U.solBooks(actor)
    actor = actor or (U.solActor and U.solActor())
    local inv = call(actor, "getInventory")
    local items = inv and call(inv, "getItems")
    local n = items and (tonumber((call(items, "size"))) or 0) or 0
    local out = {}
    for i = 0, n - 1 do
        local it = call(items, "get", i)
        local learned = call(it, "getLearnedRecipes")
        local skill = call(it, "getSkillTrained")
        local sb = SkillBook and skill and SkillBook[skill] or nil
        local lit = call(it, "IsLiterature") and not (ItemTag and call(it, "hasTag", ItemTag.UNINTERESTING))
        if (learned and (tonumber((call(learned, "size"))) or 0) > 0) or sb or lit then
            local b = { item = it, name = tostring(call(it, "getDisplayName") or "?"), pages = tonumber((call(it, "getNumberOfPages"))) or 0,
                        read = tonumber((call(it, "getAlreadyReadPages"))) or 0 }
            if sb then
                local lvl = tonumber((call(actor, "getPerkLevel", sb.perk))) or 0
                local minL, maxL = tonumber((call(it, "getLvlSkillTrained"))) or -1, tonumber((call(it, "getMaxLevelTrained"))) or -1
                if minL ~= -1 and minL > lvl + 1 then b.status = "too_hard"
                elseif maxL ~= -1 and maxL < lvl + 1 then b.status = "too_easy"
                else b.status = "useful" end
                b.skill = tostring(call(sb.perk, "getName") or skill)
            elseif learned and (tonumber((call(learned, "size"))) or 0) > 0 then
                local known = call(actor, "getKnownRecipes")
                b.status = (known and call(known, "containsAll", learned)) and "known" or "teaches"
            else
                b.status = "fun"          -- literature: reading lowers boredom and unhappiness
            end
            if call(actor, "hasTrait", CharacterTrait and CharacterTrait.ILLITERATE) then b.status = "illiterate" end
            out[#out + 1] = b
        end
    end
    return out
end

-- Sol reads with the game's own timed action (same rules as the player)
function U.solRead(item)
    local sol = U.solActor and U.solActor()
    if not sol or not item or not ISReadABook or not ISTimedActionQueue then return false, "unavailable" end
    local inv = call(sol, "getInventory")
    if not (inv and call(inv, "contains", item)) then return false, "not_in_bag" end
    local ok, err = pcall(function() ISTimedActionQueue.add(ISReadABook:new(sol, item)) end)
    if not ok then log("read failed: " .. tostring(err)); return false, "error" end
    log("Sol reads " .. tostring(call(item, "getDisplayName")))
    U.refreshRecipes()
    return true
end
log("skills and recipes ready v" .. U.SKILLS_VERSION)
