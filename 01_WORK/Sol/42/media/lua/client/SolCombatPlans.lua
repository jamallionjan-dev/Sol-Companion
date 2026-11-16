-- SolCombatPlans.lua - switch combat_plans (s105, PLAN_gear_and_combat.md step 1).
-- One plan name sets Living Fellows' own combat knobs (SCCommands: set_weapon_priority, set_combat_doctrine, set_hold_fire,
-- set_follow_distance, set_move_mode, the same commands its Loadout page issues; combatMode follows the doctrine through LF's
-- applyDoctrine, SCCommands.lua:111-123, and is set on LF's own state only where a plan needs another one) plus a few rules:
--   smart   (default) defensive / close_defense / best: melee for 1-2 zombies, a firearm for a group (3+ within 10 tiles of her)
--           or anything within 3 tiles of him; back to melee 4 s after the group thins out.
--   normal  defensive / close_defense / firearm when his pick for her is a gun (or, with no pick, she carries one), else best.
--   fierce  aggressive / weapons_free / firearm or best; never engages a zombie more than 25 tiles from him (unless it is on her).
--   support defensive / ranged_support / firearm, follow distance 5 (LF's 4-8 tile band behind him).
--   careful passive / close_defense / best.
--   stealth passive / stealth / quiet, sneaking: melee, or a gun only when EFZ says it is silenced
--           (TW/Core C.stats(key, TWRuntime.read(w)).silenced); an unsilenced gun never fires.
--   avoid   passive / stealth / best.
--   hold    defensive / close_defense / melee, hold fire.
-- Every plan: she never fires across him (his body near her line of fire, or him behind the target in it); under 30% health
-- retreat wins; after her death the plan goes back to smart (and the next Sol gets smart's knobs).
-- Hooks (SCCombat, apply_s105_combat_plans.py): M.preference in Combat.update, M.choose at the top of chooseWeapon, M.shape at
-- the end of actionUtilities. Wrapped here at OnGameStart: Combat.friendlyFireBlocked (every ranged lane check goes through
-- it, vehicle shots too), Combat.scoreTargets (the fierce leash). Works with s98 (preferred weapon marker SC_ManualEquipFor,
-- G.choose), s99 (SolWeaponPick.preferredMelee / meleeScore) and s104 (SolShootDiscipline) in either install order.
-- Switch read at call time; off = LF and the other fixes exactly as before (the knobs a plan already set stay, they are LF's).
-- ASCII only. Every Java method is looked up before it is called (javap 42.22.2: IsoMovingObject getX/getY/getZ,
-- IsoGameCharacter getPrimaryHandItem/isDead, InventoryItem hasModData/getModData/getFullType, HandWeapon isRanged).
require "SolActions"
SolUI = SolUI or {}
local U = SolUI
SolCombatPlans = SolCombatPlans or {}
local M = SolCombatPlans
M.VERSION = "0.1.0"
M.DEFAULT = "smart"
M.STORE = "Sol_CombatPlan"
M.GROUP = 3                 -- smart: this many zombies near her = a group (firearm)
M.GROUP_RADIUS = 10
M.HIM_RADIUS = 3            -- smart: a zombie this close to him = a threat to him (firearm)
M.KIND_HOLD_MS = 4000       -- smart: the firearm stays this long after the group thinned out
M.LEASH = 25                -- fierce: tiles from him
M.RETREAT_HEALTH = 30
M.RETREAT_SCORE = 500       -- above every LF / s104 action score
M.LANE_SIDE = 1.2           -- him this close to her line of fire, between her and the target
M.LANE_START = 0.8          -- ... and at least this far along it (he may stand right beside her)
M.BEYOND_SIDE = 1.5         -- him behind the target in the line of fire
M.BEYOND_TILES = 15
M.SUPPORT_FOLLOW = 5
M.TICK_MS = 2000
M.SILENCED_MS = 3000
M.SOL_MS = 1000
M.ORDER = { "smart", "normal", "fierce", "support", "careful", "stealth", "avoid", "hold" }
M.PLANS = {
    smart   = { mode = "defensive",  doctrine = "close_defense",  priority = "best",    hold = false },
    normal  = { mode = "defensive",  doctrine = "close_defense",  priority = "kind",    hold = false },
    fierce  = { mode = "aggressive", doctrine = "weapons_free",   priority = "kind",    hold = false, leash = true },
    support = { mode = "defensive",  doctrine = "ranged_support", priority = "firearm", hold = false, follow = 5 },
    careful = { mode = "passive",    doctrine = "close_defense",  priority = "best",    hold = false },
    stealth = { mode = "passive",    doctrine = "stealth",        priority = "quiet",   hold = false, move = "sneak", want = "quiet" },
    avoid   = { mode = "passive",    doctrine = "stealth",        priority = "best",    hold = false },
    hold    = { mode = "defensive",  doctrine = "close_defense",  priority = "melee",   hold = true, want = "melee" },
}
M.ALIAS = { default = "smart", mixed = "smart", auto = "smart", aggressive = "fierce", attack = "fierce", ranged = "support",
            cover = "support", cautious = "careful", passive = "careful", quiet = "stealth", silent = "stealth", sneak = "stealth",
            evade = "avoid", hold_fire = "hold", holdfire = "hold", dont_shoot = "hold", no_shoot = "hold" }
M.want = M.want or setmetatable({}, { __mode = "k" })
M.group = M.group or setmetatable({}, { __mode = "k" })
M.silencedCache = M.silencedCache or setmetatable({}, { __mode = "k" })
M.said = M.said or {}

local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); if f then return f() end; return 0 end
local function log(m) print("[SolCombatPlans] " .. tostring(m)) end
local function num(v) return tonumber(v) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function sw(fix) local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on(fix) == true end
function M.on() local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("combat_plans") == true end
local function LF() local sc = g("SurvivorCompanion"); return type(sc) == "table" and sc or nil end
local function player() local f = g("getSpecificPlayer"); if not f then return nil end; local ok, p = pcall(f, 0); return ok and p or nil end
local function idOf(actor)
    local SC = LF()
    local GU = SC and SC.GameplayUtil
    if actor == nil or type(GU) ~= "table" or type(GU.idOf) ~= "function" then return nil end
    local ok, id = pcall(GU.idOf, actor)
    if ok and type(id) == "string" and id ~= "" then return id end
    return nil
end
-- Sol (exactly one living companion, U.solActor), cached SOL_MS: the wrappers run on every lane check
local solAt, solRef = -1, nil
local function sol()
    local t = nowMs()
    if solAt >= 0 and t - solAt < M.SOL_MS then return solRef end
    solAt = t
    solRef = type(U.solActor) == "function" and U.solActor() or nil
    if solRef ~= nil then M.lastSol = solRef end
    return solRef
end
function M.forgetSol() solAt, solRef = -1, nil end
local function once(key, line)
    if M.said[key] == line then return end
    M.said[key] = line
    log(line)
end
local function pos(o)
    local x, y = num((call(o, "getX"))), num((call(o, "getY")))
    if x == nil or y == nil then return nil end
    return x, y, num((call(o, "getZ"))) or 0
end

-- ---------------------------------------------------------------- the plan (ModData, one per save, tied to her id)
local function store()
    local MD = g("ModData")
    if type(MD) ~= "table" or type(MD.getOrCreate) ~= "function" then M._mem = M._mem or {}; return M._mem end
    local ok, d = pcall(MD.getOrCreate, M.STORE)
    if ok and type(d) == "table" then return d end
    M._mem = M._mem or {}
    return M._mem
end
M.store = store
function M.normalize(option)
    local o = string.lower(tostring(option or ""))
    o = string.gsub(o, "^%s+", ""); o = string.gsub(o, "%s+$", ""); o = string.gsub(o, "[%s%-]+", "_")
    if o == "" then return nil end
    if M.PLANS[o] then return o end
    return M.ALIAS[o]
end
-- the plan in force for this Sol: smart for a Sol the plan was not set for (a new one after a death)
function M.current(actor)
    local s = store()
    local plan = M.PLANS[s.plan] and s.plan or M.DEFAULT
    if actor ~= nil and s.id ~= nil then
        local id = idOf(actor)
        if id ~= nil and id ~= s.id then return M.DEFAULT end
    end
    return plan
end

-- ---------------------------------------------------------------- her weapons
local function marked(item, id)
    if item == nil or id == nil or call(item, "hasModData") ~= true then return false end
    local md = call(item, "getModData")
    return type(md) == "table" and md.SC_ManualEquipFor == id
end
local function isGun(item) return item ~= nil and call(item, "isRanged") == true end
-- the weapon kind for normal / fierce: the kind of the weapon he picked for her (s98 marker SC_ManualEquipFor), else "firearm"
-- when she carries a gun (her hands, or her bags through s99's SolWeaponPick.weapons), else "melee"; nil with no weapon at all
function M.weaponKind(actor)
    local id = idOf(actor)
    local held = call(actor, "getPrimaryHandItem")
    local all = {}
    if held ~= nil then all[1] = held end
    local WP = g("SolWeaponPick")
    if type(WP) == "table" and type(WP.weapons) == "function" then
        local ok, list = pcall(WP.weapons, call(actor, "getInventory"))
        if ok and type(list) == "table" then for _, it in ipairs(list) do if it ~= held then all[#all + 1] = it end end end
    end
    local gun = false
    for _, it in ipairs(all) do
        if marked(it, id) then return isGun(it) and "firearm" or "melee" end
        if isGun(it) then gun = true end
    end
    if gun then return "firearm" end
    if #all > 0 then return "melee" end
    return nil
end
-- EFZ: is this gun silenced? (TW/Core C.stats(key, tree).silenced, tree = TWRuntime.read(w)); cached SILENCED_MS per item
function M.silenced(item)
    if item == nil then return false end
    local t = nowMs()
    local c = M.silencedCache[item]
    if type(c) == "table" and t < c.at then return c.v end
    local v = false
    local R = g("TWRuntime")
    if type(R) == "table" and type(R.key) == "function" and type(R.read) == "function" then
        local okK, key = pcall(R.key, item)
        if okK and key ~= nil then
            local okC, C = pcall(require, "TW/Core")
            if okC and type(C) == "table" and type(C.stats) == "function" then
                local okR, tree = pcall(R.read, item)
                if okR and type(tree) == "table" then
                    local okS, st = pcall(C.stats, key, tree)
                    v = okS and type(st) == "table" and st.silenced == true
                end
            end
        end
    end
    M.silencedCache[item] = { v = v, at = t + M.SILENCED_MS }
    return v
end

-- ---------------------------------------------------------------- applying a plan: LF's own commands
local function issue(id, command, payload, p)
    local SC = LF()
    local C = SC and SC.Commands
    if type(C) ~= "table" or type(C.issue) ~= "function" then return false, "lf_unavailable" end
    local ok, a, b = pcall(C.issue, id, command, payload, p)
    if not ok then return false, "lf_error:" .. tostring(a) end
    return a == true, b
end
local function lfState(actor)
    local SC = LF()
    local C = SC and SC.Commands
    if type(C) ~= "table" or type(C.peek) ~= "function" then return nil end
    local ok, st = pcall(C.peek, actor)
    return ok and type(st) == "table" and st or nil
end
function M.knobs(plan, actor)
    local P = M.PLANS[plan]
    if P == nil then return nil end
    local priority = P.priority
    if priority == "kind" then priority = (M.weaponKind(actor) == "firearm") and "firearm" or "best" end
    return { mode = P.mode, doctrine = P.doctrine, priority = priority, hold = P.hold, follow = P.follow, move = P.move }
end
-- sets every knob of the plan on this Sol; returns ok, reason (the first LF refusal)
function M.apply(actor, plan)
    local K = M.knobs(plan, actor)
    if K == nil then return false, "unknown_option" end
    local id = idOf(actor)
    if id == nil then return false, "no_sol" end
    local p = player()
    local s = store()
    local before = lfState(actor) or {}
    local okW, whyW = issue(id, "set_weapon_priority", K.priority, p)
    if not okW then return false, whyW or "weapon_priority_refused" end
    local okD, whyD = issue(id, "set_combat_doctrine", K.doctrine, p)
    if not okD then return false, whyD or "doctrine_refused" end
    local okH, whyH = issue(id, "set_hold_fire", K.hold == true, p)
    if not okH then return false, whyH or "hold_fire_refused" end
    local st = lfState(actor)
    if st ~= nil and st.combatMode ~= K.mode then                     -- careful: passive with close_defense (no LF command sets it alone)
        st.combatMode = K.mode
        local SC = LF()
        if SC and SC.Commands and type(SC.Commands.persist) == "function" then pcall(SC.Commands.persist, actor) end
    end
    s.prev = type(s.prev) == "table" and s.prev or {}
    if K.follow ~= nil then
        if s.prev.followDistance == nil then s.prev.followDistance = before.followDistance or 3 end
        issue(id, "set_follow_distance", K.follow, p)
    elseif s.prev.followDistance ~= nil then
        issue(id, "set_follow_distance", s.prev.followDistance, p)
        s.prev.followDistance = nil
    end
    if K.move ~= nil then
        if s.prev.moveMode == nil then s.prev.moveMode = before.moveMode or "copy" end
        issue(id, "set_move_mode", K.move, p)
    elseif s.prev.moveMode ~= nil then
        issue(id, "set_move_mode", s.prev.moveMode, p)
        s.prev.moveMode = nil
    end
    s.plan, s.id, s.pending = plan, id, nil
    M.want[actor] = nil
    log("plan " .. plan .. ": " .. K.mode .. " / " .. K.doctrine .. " / " .. K.priority .. (K.hold and " / hold fire" or "")
        .. (K.follow and (" / follow " .. tostring(K.follow)) or "") .. (K.move and (" / " .. K.move) or ""))
    return true, "plan_" .. plan
end
local function catalogSoon()
    local t = nowMs() + 300
    if U._catalogDue == nil or U._catalogDue > t then U._catalogDue = t end
end
function M.run(option)
    if not M.on() then return false, "switch_off" end
    local plan = M.normalize(option)
    if plan == nil then return false, "unknown_option" end
    local s = sol()
    if s == nil then M.forgetSol(); s = sol() end
    if s == nil then return false, "no_sol" end
    local ok, why = M.apply(s, plan)
    if ok then catalogSoon() end
    return ok, why
end

-- ---------------------------------------------------------------- combat hooks
local function distSq(ax, ay, bx, by) local dx, dy = ax - bx, ay - by; return dx * dx + dy * dy end
-- smart: "firearm" for a group or a threat to him, else "melee"; the firearm stays KIND_HOLD_MS after the group
function M.smartKind(actor, p, scored, t)
    local n, him = 0, false
    local px, py, pz = pos(p)
    for _, r in ipairs(scored or {}) do
        if type(r) == "table" then
            local d2 = num(r.distanceSq)
            if d2 ~= nil and d2 <= M.GROUP_RADIUS * M.GROUP_RADIUS then n = n + 1 end
            if px ~= nil and not him then
                local zx, zy, zz = pos(r.actor)
                if zx ~= nil and math.floor(zz) == math.floor(pz) and distSq(zx, zy, px, py) <= M.HIM_RADIUS * M.HIM_RADIUS then him = true end
            end
        end
    end
    if n >= M.GROUP or him then M.group[actor] = t; return "firearm", n, him end
    local last = M.group[actor]
    if last ~= nil and t - last < M.KIND_HOLD_MS then return "firearm", n, him end
    return "melee", n, him
end
local PREF = { melee = "melee", firearm = "firearm", quiet = "quiet" }
-- Combat.update: the weapon preference for this pulse (seated: LF's own rule)
function M.preference(actor, p, snapshot, scored, commands, preference, seated)
    if not M.on() or seated then return preference end
    if actor ~= sol() then return preference end
    local plan = M.current(actor)
    local want = M.PLANS[plan].want
    if plan == "smart" then
        local n, him
        want, n, him = M.smartKind(actor, p, scored, nowMs())
        once("kind", "smart: " .. want .. " (" .. tostring(n) .. " near her" .. (him and ", one near him" or "") .. ")")
    end
    M.want[actor] = want and { kind = want, at = nowMs() } or nil
    return PREF[want] or preference
end
local function wanted(actor)
    local w = M.want[actor]
    local plan = M.current(actor)
    if type(w) == "table" and nowMs() - (w.at or 0) < M.KIND_HOLD_MS then return w.kind end
    if plan == "smart" then return "melee" end                       -- at rest: the melee weapon for the first one or two
    return M.PLANS[plan].want
end
-- chooseWeapon (top): the weapon record this plan wants, or nil for LF / s98 / s99 as before
function M.choose(actor, weapons, usable, preference)
    if not M.on() or type(weapons) ~= "table" or actor ~= sol() then return nil end
    local want = wanted(actor)
    if want == nil then return nil end
    local id = idOf(actor)
    local fit = {}
    for _, w in ipairs(weapons) do
        if type(w) == "table" and w.item ~= nil then
            local ok = false
            if want == "firearm" then ok = w.ranged == true
            elseif want == "melee" then ok = w.ranged ~= true
            else ok = w.ranged ~= true or M.silenced(w.item) end            -- quiet: melee, or a silenced gun
            if ok and usable(w) == true then fit[#fit + 1] = w end
        end
    end
    if #fit == 0 then once("choose", "no usable weapon for " .. want .. ": LF chooses"); return nil end
    for _, w in ipairs(fit) do if marked(w.item, id) then return w end end           -- his pick (s98), when it fits the plan
    local WP = g("SolWeaponPick")
    if want ~= "firearm" and type(WP) == "table" and type(WP.preferredMelee) == "function" and type(WP.meleeOn) == "function" and WP.meleeOn() then
        local okP, pm = pcall(WP.preferredMelee, actor)
        if okP and pm ~= nil then for _, w in ipairs(fit) do if w.item == pm then return w end end end
    end
    for _, w in ipairs(fit) do if w.equipped == true and (want ~= "quiet" or w.ranged ~= true) then return w end end
    local best, bestScore
    for _, w in ipairs(fit) do
        local sc = num(w.score) or 0
        if w.ranged ~= true and type(WP) == "table" and type(WP.meleeScore) == "function" then
            local okS, v = pcall(WP.meleeScore, actor, w, sc); if okS and num(v) then sc = num(v) end
        end
        if want == "quiet" and w.ranged == true then sc = sc - 1000 end       -- melee first, the silenced gun when there is none
        if best == nil or sc > bestScore then best, bestScore = w, sc end
    end
    return best
end
-- actionUtilities (end): under 30% health retreat wins; stealth never fires an unsilenced gun
function M.shape(actor, p, target, weapon, readiness, actions)
    if not M.on() or type(actions) ~= "table" or actor ~= sol() then return end
    local health = type(readiness) == "table" and num(readiness.health) or nil
    if health ~= nil and health < M.RETREAT_HEALTH then
        for _, a in ipairs(actions) do
            if a.kind == "retreat" then
                a.score = math.max(num(a.score) or 0, M.RETREAT_SCORE)
                once("retreat", "health " .. string.format("%.0f", health) .. "% < " .. M.RETREAT_HEALTH .. "%: she falls back")
            end
        end
    end
    if M.current(actor) == "stealth" and type(weapon) == "table" and weapon.ranged == true and not M.silenced(weapon.item) then
        for i = #actions, 1, -1 do if actions[i].kind == "shoot" then table.remove(actions, i) end end
        once("stealth", "stealth: no shot with an unsilenced gun")
    end
end
-- never across him: he is near her line of fire on the way to the target, or behind the target in it
function M.acrossHim(actor, target, p)
    local ax, ay, az = pos(actor)
    local tx, ty = pos(target)
    local px, py, pz = pos(p)
    if ax == nil or tx == nil or px == nil then return false end
    if math.floor(az) ~= math.floor(pz) then return false end
    local dx, dy = tx - ax, ty - ay
    local L2 = dx * dx + dy * dy
    if L2 < 0.0001 then return false end
    local L = math.sqrt(L2)
    local along = ((px - ax) * dx + (py - ay) * dy) / L                -- tiles from her along the line
    local side = math.abs((px - ax) * dy - (py - ay) * dx) / L         -- tiles off the line
    if along >= M.LANE_START and along <= L and side <= M.LANE_SIDE then return true, "lane" end
    if along > L and along - L <= M.BEYOND_TILES and side <= M.BEYOND_SIDE then return true, "behind_target" end
    return false
end
function M.friendlyFire(base, actor, target, context)
    local b, who = base(actor, target, context)
    if b or not M.on() then return b, who end
    if type(context) == "table" and context.kind == "melee" then return b, who end
    if actor == nil or actor ~= sol() then return b, who end
    local p = (type(context) == "table" and context.player) or player()
    if p == nil then return b, who end
    local hit, why = M.acrossHim(actor, target, p)
    if hit then once("lane", "no shot across him (" .. tostring(why) .. ")"); return true, p end
    return b, who
end
-- fierce: a zombie more than LEASH tiles from him is not hers (unless it is on her or holding an ally)
function M.leash(actor, p, scored)
    if type(scored) ~= "table" then return scored end
    local px, py = pos(p)
    if px == nil then return scored end
    local dropped = 0
    for i = #scored, 1, -1 do
        local r = scored[i]
        if type(r) == "table" and r.attacking ~= true and r.rescue ~= true then
            local zx, zy = pos(r.actor)
            if zx ~= nil and distSq(zx, zy, px, py) > M.LEASH * M.LEASH then table.remove(scored, i); dropped = dropped + 1 end
        end
    end
    if dropped > 0 then once("leash", "fierce: " .. dropped .. " zombie(s) beyond " .. M.LEASH .. " tiles of him left alone") end
    return scored
end
function M.scoreTargets(base, actor, p, snapshot, previous)
    local scored = base(actor, p, snapshot, previous)
    if not M.on() or actor == nil or actor ~= sol() then return scored end
    if M.PLANS[M.current(actor)].leash then M.leash(actor, p or player(), scored) end
    return scored
end

-- ---------------------------------------------------------------- her death: the plan goes back to smart
function M.onDeath(character)
    if character == nil or not M.on() then return end
    if character ~= M.lastSol and character ~= solRef then return end
    local s = store()
    if s.plan ~= M.DEFAULT then log("she died: the plan goes back to " .. M.DEFAULT) end
    s.plan, s.pending, s.prev = M.DEFAULT, true, nil
    M.want[character] = nil
    M.forgetSol()
end
function M.tick()
    if not M.on() then return end
    local a = sol()
    if a == nil then return end
    local id = idOf(a)
    if id == nil then return end
    local s = store()
    if s.id == nil then s.id = id
    elseif s.id ~= id then                                             -- a new Sol (respawn): her plan is smart
        if s.plan ~= M.DEFAULT then log("a new Sol: the plan goes back to " .. M.DEFAULT) end
        s.plan, s.id, s.prev, s.pending = M.DEFAULT, id, nil, true
    end
    if s.pending then
        s.tries = (num(s.tries) or 0) + 1
        local ok, why = M.apply(a, M.DEFAULT)
        if ok or s.tries >= 10 then s.pending, s.tries = nil, nil end
        if not ok then once("pending", "smart knobs not set yet: " .. tostring(why)) end
    end
end

-- ---------------------------------------------------------------- install
function M.install()
    if M._installed then return end
    M._installed = true
    local baseRun, baseCat = U.runAction, U.actionCatalog
    U.runAction = function(id, option)
        if id == "sol_combat_plan" and M.on() then return M.run(option) end
        return baseRun(id, option)
    end
    U.actionCatalog = function()
        local out = baseCat()
        if M.on() and type(out) == "table" then
            out[#out + 1] = { id = "sol_combat_plan", kind = "sol", enabled = true, state = M.current(sol()),
                              label = "her fighting plan; option: smart / normal / fierce / support / careful / stealth / avoid / hold" }
        end
        return out
    end
    local SC = LF()
    local C = SC and SC.Combat
    if type(C) == "table" and type(C.friendlyFireBlocked) == "function" and not M._ffWrapped then
        M._ffWrapped = true
        local baseFF = C.friendlyFireBlocked
        C.friendlyFireBlocked = function(actor, target, context) return M.friendlyFire(baseFF, actor, target, context) end
    end
    if type(C) == "table" and type(C.scoreTargets) == "function" and not M._stWrapped then
        M._stWrapped = true
        local baseST = C.scoreTargets
        C.scoreTargets = function(actor, p, snapshot, previous) return M.scoreTargets(baseST, actor, p, snapshot, previous) end
    end
    if Events and Events.OnCharacterDeath then Events.OnCharacterDeath.Add(M.onDeath) end
    if Events and Events.OnTick then
        local nextAt = 0
        Events.OnTick.Add(function() local t = nowMs(); if t < nextAt then return end; nextAt = t + M.TICK_MS; pcall(M.tick) end)
    end
    log("installed v" .. M.VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(M.install) end
log("ready v" .. M.VERSION)
return M
