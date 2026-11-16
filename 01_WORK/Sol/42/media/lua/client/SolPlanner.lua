-- SolPlanner.lua - Layer 3: compound actions as plans of atomic steps, run one step at a time by the body.
-- A plan is built only from what Sol can see or carry right now (no invented items, no unknown recipes); when a
-- precondition fails the plan is refused with a precise reason that the brain can say out loud.
-- First plans: sol_cook (any cookable food -> nearest working stove -> wait until cooked, out before it burns) and
-- sol_cook_and_serve (then hand it to the player). Mirrors what a human player does: fetch, carry, place, switch
-- on, watch, take out, switch off, come back.
-- Evidence (installed Build 42.21 scripts, 2026-10-25): Egg IsCookable, MinutesToCook=4, MinutesToBurn=20;
-- stove = IsoStove with getContainer()/isActivated()/ISToggleStoveAction; moving items = ISInventoryTransferAction.
require "SolActions"
require "SolActionRegistry"
SolUI = SolUI or {}
local U = SolUI
U.PLANNER_VERSION = "0.1.6"
local function log(m) print("[SolPlanner] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function mcall(o, name, ...) if o == nil then return nil end local f = o[name]; if type(f) ~= "function" then return nil end local ok, v = pcall(f, o, ...); if ok then return v end return nil end
local function sol() return U.solActor and U.solActor() or nil end
local function player() return getSpecificPlayer and getSpecificPlayer(0) or nil end
local function near(a, x, y, r) return a and ((a:getX() - x) ^ 2 + (a:getY() - y) ^ 2) <= r * r end
local function objXY(o) return (tonumber((mcall(o, "getX"))) or 0) + 0.5, (tonumber((mcall(o, "getY"))) or 0) + 0.5 end

-- ---------------------------------------------------------------- job runner (generalises SolActions' fetchJob)
U.job = nil
local function inDanger(s)
    local SC = SurvivorCompanion
    local C = type(SC) == "table" and SC.Combat
    if C and type(C.peek) == "function" then
        local ok, v = pcall(C.peek, s)
        if ok and v and (v.target or v.engaged) then return true end
    end
    return false
end
function U.startJob(name, steps)
    if U.job and U.job.phase == "running" then return false, "busy:" .. U.job.name end
    U.job = { name = name, steps = steps, i = 1, phase = "running", since = nowMs(), started = false, log = {} }
    return true, "plan_started:" .. name .. " (" .. #steps .. " steps)"
end
function U.cancelJob(reason)
    if U.job and U.job.phase == "running" then U.job.phase, U.job.reason = "cancelled", reason or "cancelled" end
end
local function finish(job, phase, reason)
    job.phase, job.reason = phase, reason
    log(job.name .. " " .. phase .. " " .. tostring(reason or ""))
    if U.issueLF then pcall(U.issueLF, "follow") end
end
function U.jobTick()
    local job = U.job
    local s = sol()
    if not job or job.phase ~= "running" or not s then return end
    if inDanger(s) then return finish(job, "cancelled", "danger_near_sol") end
    local step = job.steps[job.i]
    if not step then return finish(job, "done", "all_steps_done") end
    local t = nowMs()
    if not job.started then
        local ok, r1, r2 = pcall(step.run, s)
        if not ok then return finish(job, "failed", step.name .. ":error:" .. tostring(r1)) end
        if r1 == false then return finish(job, "failed", step.name .. ":" .. tostring(r2)) end
        job.started, job.stepSince = true, t
        job.log[#job.log + 1] = step.name
        return
    end
    local ok, d, why = pcall(step.done, s)
    if not ok then return finish(job, "failed", step.name .. ":error:" .. tostring(d)) end
    if d == "failed" then return finish(job, "failed", step.name .. ":" .. tostring(why)) end
    if d == true then job.i, job.started = job.i + 1, false; return end
    if t - job.stepSince > (step.timeout or 60000) then return finish(job, "failed", step.name .. ":timeout") end
end
function U.jobStatus()
    local j = U.job
    if not j then return "idle" end
    local step = j.steps[j.i]
    return j.phase .. ":" .. j.name .. (j.phase == "running" and step and (":" .. step.name) or "") .. (j.reason and (":" .. j.reason) or "")
end

-- ---------------------------------------------------------------- step factories (atomic, checkable)
-- Living Fellows clears the companion's own work on every player order (SCCommands.lua:700-701); a plan is such an order.
local function yieldWork(s)
    local SC = SurvivorCompanion
    if type(SC) == "table" and SC.Decision and type(SC.Decision.cancelWork) == "function" then pcall(SC.Decision.cancelWork, s, "sol_plan") end
end
local function stepWalkTo(x, y, label)
    local accepted, tries, lastTry, lastWhy = false, 0, 0, nil
    local function ask(s) local ok, why = U.solGoto(x, y); accepted = ok == true; lastWhy = why; tries = tries + 1; lastTry = nowMs(); return ok end
    return { name = label or "walk", timeout = 60000,
        run = function(s) yieldWork(s); ask(s); return true, accepted and "walking" or ("retrying:" .. tostring(lastWhy)) end,
        done = function(s)
            if near(s, x, y, 1.8) then return true end
            if not accepted and nowMs() - lastTry >= 1500 then
                if tries >= 8 then return "failed", tostring(lastWhy) end
                yieldWork(s); ask(s)
            end
            return false
        end }
end
-- stove switch: game timed action first; if the state has not changed after 4 s, stove:Toggle() directly (vanilla IsoStove API).
local function stepStove(stove, on)
    local since, tried = 0, false
    local function state() return mcall(stove, "Activated") == true end
    return { name = on and "stove_on" or "stove_off", timeout = 15000,
        run = function(s) since = nowMs(); if state() == on then return true, "already" end U.timed("ISToggleStoveAction", s, stove); return true, "toggling" end,
        done = function(s)
            if state() == on then return true end
            if not tried and nowMs() - since > 4000 then
                tried = true; pcall(function() stove:Toggle() end)
                if state() == on then log((on and "stove_on" or "stove_off") .. ": direct_toggle"); return true end
                return "failed", "toggle_failed"
            end
            return false
        end }
end
local function stepFetch(what)
    return { name = "fetch:" .. tostring(what), timeout = 90000,
        run = function(s) return U.solFetch(what) end,
        done = function(s)
            local j = U.fetchJob
            if not j then return "failed", "fetch_lost" end
            if j.phase == "failed" then return "failed", j.reason or "fetch_failed" end
            return j.phase == "done"
        end }
end
local function stepGive(what)
    return { name = "hand_over", timeout = 120000,
        run = function(s) return true, "waiting_for_player" end,
        done = function(s)
            local p = player()
            if not p or not near(s, p:getX(), p:getY(), 2.4) then
                if p and not U._giveWalk then U._giveWalk = true; U.solGoto(p:getX(), p:getY()) end
                return false
            end
            U._giveWalk = nil
            local ok, why = U.solGive(what)
            if ok then return true end
            return "failed", why
        end }
end

-- ---------------------------------------------------------------- cook plan
local function isCookableRaw(it)
    return instanceof and instanceof(it, "Food") and mcall(it, "isCookable") == true and mcall(it, "isCooked") ~= true
        and mcall(it, "isBurnt") ~= true and mcall(it, "isRotten") ~= true
end
local ALIAS = { egg = "Egg", eggs = "Egg", ["??????"] = "Egg", ["????????"] = "Egg", ["????????"] = "Egg" }
local function wanted(opt)
    local w = string.lower(tostring(opt or ""))
    w = string.gsub(w, "%s*|.*$", "")
    return ALIAS[w] or (w ~= "" and w or nil)
end
local function matchesName(it, w)
    if not w then return true end
    local n = string.lower(tostring(mcall(it, "getDisplayName") or "") .. " " .. tostring(mcall(it, "getFullType") or ""))
    return string.find(n, string.lower(w), 1, true) ~= nil
end
-- dry run: what would the plan use? returns ok, reason, ctx (no movement, no world change)
function U.planCookCheck(opt)
    local s = sol()
    if not s then return false, "no_sol" end
    if U.job and U.job.phase == "running" then return false, "busy:" .. U.job.name end
    local w = wanted(opt)
    local inBag
    for _, rec in ipairs(U.solBagItems and U.solBagItems(s) or {}) do
        if isCookableRaw(rec.item) and matchesName(rec.item, w) then inBag = rec; break end
    end
    local nearby = (not inBag) and U.findNearby and U.findNearby(w or "food") or nil
    if nearby and not (isCookableRaw(nearby.item) and matchesName(nearby.item, w)) then nearby = nil end
    if not inBag and not nearby then return false, "no_" .. tostring(w or "cookable_food") .. "_seen" end
    local stove, d = U.nearestStove(s, 25)
    if not stove then return false, "no_stove_seen" end
    local ok, why = U.stoveUsable(stove)
    if not ok then return false, why end
    return true, "ok", { inBag = inBag, nearby = nearby, stove = stove, what = w }
end
-- NPC item move: direct container move only. ISInventoryTransferAction:perform (line 490) touches the local player inventory UI and throws for an NPC, so it must never be queued for Sol (console proof 2026-10-25 04:12 session).
local function stepMove(label, getItem, getSrc, getDst)
    local since = 0
    return { name = label, timeout = 20000,
        run = function(a) local it = getItem(); if not it then return false, "nothing_to_move" end
            since = nowMs() - 4000; return true, "moving" end,
        done = function(a)
            local it, dst = getItem(), getDst(a)
            if mcall(dst, "contains", it) == true then return true end
            if nowMs() - since > 4000 then
                local src = getSrc(a)
                local ok = pcall(function() src:Remove(it); dst:AddItem(it) end)
                if ok and mcall(dst, "contains", it) == true then log(label .. ": direct_move"); return true end
                return "failed", "move_failed"
            end
            return false
        end }
end
function U.planCook(opt, serve)
    local ok, why, c = U.planCookCheck(opt)
    if not ok then return false, why end
    local s = sol()
    local steps = {}
    local item
    if c.inBag then item = c.inBag.item
    else steps[#steps + 1] = stepFetch(c.what or "food"); steps[#steps + 1] = { name = "pick_fetched", timeout = 1000,
            run = function(a) item = U.fetchJob and U.fetchJob.item; if not item then return false, "fetched_item_lost" end return true end,
            done = function() return true end } end
    local sx, sy = objXY(c.stove)
    -- stand on a free square next to the stove, never on the stove tile itself (Build 42.21 AdjacentFreeTileFinder.Find)
    local stSq = mcall(c.stove, "getSquare")
    local adj = stSq and AdjacentFreeTileFinder and AdjacentFreeTileFinder.Find and AdjacentFreeTileFinder.Find(stSq, s)
    if not adj then return false, "stove_not_reachable" end
    sx, sy = adj:getX() + 0.5, adj:getY() + 0.5
    local wasOff = mcall(c.stove, "Activated") ~= true
    steps[#steps + 1] = stepWalkTo(sx, sy, "walk_to_stove")
    steps[#steps + 1] = stepMove("put_on_stove",
        function() item = item or (c.inBag and c.inBag.item); return item end,
        function(a) local src = a:getInventory(); for _, rec in ipairs(U.solBagItems and U.solBagItems(a) or {}) do if rec.item == item then src = rec.container end end return src end,
        function(a) return c.stove:getContainer() end)
    steps[#steps + 1] = stepStove(c.stove, true)
    steps[#steps + 1] = { name = "wait_cooked", timeout = 900000, run = function() return true, "watching" end,
        done = function() if mcall(item, "isBurnt") == true then return "failed", "it_burnt" end
            if mcall(c.stove, "Activated") ~= true then return "failed", "stove_went_off" end
            return mcall(item, "isCooked") == true end }
    steps[#steps + 1] = stepMove("take_out", function() return item end, function(a) return c.stove:getContainer() end, function(a) return a:getInventory() end)
    if wasOff then steps[#steps + 1] = stepStove(c.stove, false) end
    if serve then steps[#steps + 1] = stepGive(c.what or "food") end
    return U.startJob(serve and "cook_and_serve" or "cook", steps)
end

-- ---------------------------------------------------------------- registration into SolActions' channel
U.planIds = { sol_cook = true, sol_cook_and_serve = true, sol_plan_status = true, sol_plan_cancel = true }
function U.planRun(id, option)
    if id == "sol_cook" then return U.planCook(option, false) end
    if id == "sol_cook_and_serve" then return U.planCook(option, true) end
    if id == "sol_plan_status" then return true, U.jobStatus() end
    if id == "sol_plan_cancel" then U.cancelJob("asked"); return true, "cancelled" end
    return false, "unknown_plan"
end
function U.planCatalog()
    local ok, why = U.planCookCheck(nil)
    return {
        { id = "sol_cook", kind = "plan", label = "cook a raw food on the nearest working stove and take it out before it burns; option: English item name (egg) or empty for the first spoiling food", enabled = ok, reason = why },
        { id = "sol_cook_and_serve", kind = "plan", label = "same as sol_cook, then hand the cooked food to the player", enabled = ok, reason = why },
        { id = "sol_plan_status", kind = "plan", label = "current compound plan status", enabled = true, reason = U.jobStatus() },
        { id = "sol_plan_cancel", kind = "plan", label = "cancel the running compound plan", enabled = U.job ~= nil and U.job.phase == "running", reason = "" },
    }
end
local lastTick = 0
local function onTick()
    local t = nowMs()
    if t - lastTick >= 500 then lastTick = t; pcall(U.jobTick) end
    if not U._catalogOnSpawn and sol() and U.writeActionCatalog then U._catalogOnSpawn = true; pcall(U.writeActionCatalog) end
end
if Events and Events.OnTick then Events.OnTick.Add(onTick) end
log("ready v" .. U.PLANNER_VERSION)
