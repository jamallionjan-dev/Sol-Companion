-- Sol fix walk_no_vault (s97). Live 2026-11-11 10:40:46-51 (DebugLog 2026-11-11_10-19): during the sort at home her walk
-- 7402,8262 -> 7406,8251 went out as one plain move_to (no "[SolPlace] route" line, the goal itself in the SolDrive line), she
-- jogged at the porch railing instead of the porch gap, vaulted and fell (IsoFallingClothing at 7406.197,8258.394). The plain walk
-- happens when M.danger says "a zombie within 7 tiles" (any zombie, any floor, seen or not), and the same test also drops the
-- fence price in Living Fellows' A*. With the switch on, while she is calm:
--   calm      M.danger means real danger only: a zombie Living Fellows perceives within FLEE_SEEN tiles, or any zombie on her floor
--             within FLEE_CLOSE tiles. Danger walks stay the old ones (a fence may be her way out).
--   route     SolPlace's own route takes a fence only when nothing else gets there (FENCE_CALM), so gaps, then doors, then windows.
--   legs      a route's legs are placed so that the walk between two legs cannot be shortened over a fence or a window: between
--             each pair a small LF-priced probe (fence 2.5) is run; when it would cross one, a leg is added halfway and both halves
--             are probed again. Such a route is never handed back as "direct".
--   LF        SC.Navigation._handleFenceForRequest (LF's own fence step, every walk: follow, base duty, come) is refused for her when
--             the far side of that fence is reachable within ROUND_MAX steps without a fence or a window; LF then blacklists that
--             fence edge and plans again (through the gap or the door).
--   watch     a vault or window climb that starts while she is calm is logged once ("calm vault seen"), for runtime evidence.
-- Switch off: SolPlace exactly as before.
M.NV = M.NV or {}
local NV = M.NV
NV.FLEE_SEEN, NV.FLEE_CLOSE = 7, 2.5
NV.FENCE_CALM = 500
NV.PROBE_NODES, NV.PROBE_MARGIN, NV.PROBE_BUDGET, NV.PROBE_DEPTH = 300, 4, 2000, 6
NV.ROUND_MAX, NV.ROUND_NODES, NV.ROUND_TTL_MS = 30, 900, 30000
NV.CLIMB_STATES = { climbfence = true, climbwindow = true, climbwall = true, climboverfence = true, climbthroughwindow = true }
NV.round = NV.round or {}
NV.roundN = NV.roundN or 0
NV.stats = NV.stats or { gapLegs = 0, refused = 0, calmVaults = 0, probes = 0 }
local function nvOn()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("walk_no_vault") == true
end
M.noVaultOn = nvOn

-- real danger: what she perceives near, or what is at arm's length on her floor
function M.flee(a)
    if a == nil then return false end
    local t = nowMs()
    if NV.fleeA == a and t - (NV.fleeAt or -1e9) < 500 then return NV.fleeVal end
    local v = false
    local ax, ay, az = tonumber((call(a, "getX"))), tonumber((call(a, "getY"))), tonumber((call(a, "getZ")))
    if ax ~= nil and ay ~= nil then
        local SC = g("SurvivorCompanion")
        local GU = type(SC) == "table" and SC.GameplayUtil or nil
        if type(GU) == "table" and type(GU.peekActorState) == "function" then
            local ok, st = pcall(GU.peekActorState, a)
            local th = ok and type(st) == "table" and type(st.snapshot) == "table" and st.snapshot.threats or nil
            if type(th) == "table" then
                for i = 1, math.min(#th, 32) do
                    local d = type(th[i]) == "table" and tonumber((th[i].distanceSq)) or nil
                    if d ~= nil and d <= NV.FLEE_SEEN * NV.FLEE_SEEN then v = true; break end
                end
            end
        end
        if not v then
            local c = cell()
            local list = c and call(c, "getZombieList")
            local n = tonumber((list and call(list, "size"))) or 0
            local r2 = NV.FLEE_CLOSE * NV.FLEE_CLOSE
            local fz = math.floor(az or 0)
            for i = 0, math.min(n, 400) - 1 do
                local zb = call(list, "get", i)
                local zx, zy, zz = tonumber((call(zb, "getX"))), tonumber((call(zb, "getY"))), tonumber((call(zb, "getZ")))
                if zx ~= nil and zy ~= nil and math.floor(zz or 0) == fz and (zx - ax) * (zx - ax) + (zy - ay) * (zy - ay) <= r2
                        and call(zb, "isDead") ~= true then v = true; break end
            end
        end
    end
    NV.fleeA, NV.fleeAt, NV.fleeVal = a, t, v
    return v
end
NV.baseDanger = M.danger
M.danger = function(a)
    if nvOn() then return M.flee(a) end
    return NV.baseDanger(a)
end

-- prices: calm routes take a fence last; a probe prices like Living Fellows (fence/window 2.5, closed door 2.2, open door 1)
NV.baseCross = M.crossCost
M.crossCost = function(kind, st)
    local c = NV.baseCross(kind, st)
    if c == nil then return nil end
    if NV.probing then
        if kind == "fence" or kind == "window" or kind == "frame" then return NV.probeClimb or 1.5 end
        if kind == "door" then return (type(st) == "table" and st.open) and 0 or 1.2 end
        return c
    end
    if kind == "fence" and nvOn() then return NV.FENCE_CALM end
    return c
end

local function probe(ax, ay, bx, by, z, strict, nodes, margin)
    local j = M.newSearch(ax, ay, z, { { x = bx, y = by } }, { strict = strict, maxNodes = nodes })
    j.probe = true
    if margin ~= nil then
        j.box = { math.min(ax, bx) - margin, math.min(ay, by) - margin, math.max(ax, bx) + margin, math.max(ay, by) + margin }
    end
    NV.probing = not strict
    local ok = pcall(function() while M.resume(j, 100000) == "running" do end end)
    NV.probing = false
    NV.stats.probes = NV.stats.probes + 1
    if not ok then j.state = "failed" end
    return j
end
M.probe = probe
local function crossesClimb(j)
    local c = j.counts or {}
    return (c.fence or 0) + (c.window or 0) + (c.frame or 0) > 0
end

-- extra legs so that no stretch between two legs can be cut short over a fence or through a window
function NV.gapLegs(j)
    local path, legs = j.path, j.legs
    if type(path) ~= "table" or type(legs) ~= "table" or #path < 3 then return 0 end
    local left = NV.PROBE_BUDGET
    local marks, list = {}, {}
    local function tempts(a, b)
        if left <= 0 then return false end
        local A, B = path[a], path[b]
        local p = probe(A.x, A.y, B.x, B.y, j.z, false, NV.PROBE_NODES, NV.PROBE_MARGIN)
        left = left - (p.nodes or 0)
        return p.state == "done" and crossesClimb(p)
    end
    local function split(a, b, depth)
        if b - a < 2 or depth > NV.PROBE_DEPTH then return end         -- one step: the crossing itself, or nothing to cut
        if not tempts(a, b) then return end
        local m = math.floor((a + b) / 2)
        if not marks[m] then marks[m] = true; list[#list + 1] = m end
        split(a, m, depth + 1)
        split(m, b, depth + 1)
    end
    local prev = 1
    for _, L in ipairs(legs) do
        split(prev, L.i, 0)
        prev = L.i
    end
    if #list == 0 then return 0 end
    local have = {}
    for _, L in ipairs(legs) do have[L.i] = true end
    local out = {}
    for _, L in ipairs(legs) do out[#out + 1] = L end
    local added, where = 0, {}
    for _, m in ipairs(list) do
        if not have[m] then
            out[#out + 1] = { i = m, x = path[m].x, y = path[m].y, gap = true }
            added = added + 1
            where[#where + 1] = path[m].x .. "," .. path[m].y
        end
    end
    table.sort(out, function(p, q) return p.i < q.i end)
    j.legs = out
    j.crossings = j.crossings or {}
    for _, m in ipairs(list) do
        j.crossings[#j.crossings + 1] = { i = m, kind = "gap", from = path[m - 1] or path[m], to = path[m] }
    end
    table.sort(j.crossings, function(p, q) return p.i < q.i end)
    j.counts = j.counts or {}
    j.counts.gap = (j.counts.gap or 0) + added
    j.gapLegs = added
    NV.stats.gapLegs = NV.stats.gapLegs + added
    if added > 0 then
        log("no_vault: " .. added .. " extra leg(s) so no stretch is cut over a fence or window: " .. table.concat(where, " "))
    end
    return added
end
NV.baseFinish = M._finish
M._finish = function(j)
    NV.baseFinish(j)
    if j.probe or not nvOn() then return end
    local ok, err = pcall(NV.gapLegs, j)
    if not ok then log("no_vault legs: " .. tostring(err)) end
end

-- Living Fellows' fence step for her, while calm: refused when there is a way round without a fence or a window
function NV.refuseVault(actor, fromSquare, toSquare)
    if not nvOn() or actor == nil or actor ~= solActor() then return false end
    if call(actor, "getVehicle") ~= nil or M.flee(actor) then return false end
    local fx, fy, fz = tonumber((call(fromSquare, "getX"))), tonumber((call(fromSquare, "getY"))), tonumber((call(fromSquare, "getZ")))
    local tx, ty, tz = tonumber((call(toSquare, "getX"))), tonumber((call(toSquare, "getY"))), tonumber((call(toSquare, "getZ")))
    if fx == nil or tx == nil or fy == nil or ty == nil then return false end
    fx, fy, tx, ty = math.floor(fx), math.floor(fy), math.floor(tx), math.floor(ty)
    fz, tz = math.floor(fz or 0), math.floor(tz or 0)
    if fz ~= tz then return false end
    local k = fx .. "," .. fy .. ">" .. tx .. "," .. ty .. "," .. fz
    local t = nowMs()
    local c = NV.round[k]
    if c == nil or t - c.at > NV.ROUND_TTL_MS then
        local j = probe(fx, fy, tx, ty, fz, true, NV.ROUND_NODES, NV.ROUND_MAX)
        local steps = j.state == "done" and type(j.path) == "table" and (#j.path - 1) or nil
        c = { at = t, steps = steps, ok = steps ~= nil and steps <= NV.ROUND_MAX }
        NV.roundN = NV.roundN + 1
        if NV.roundN > 256 then NV.round, NV.roundN = {}, 1 end
        NV.round[k] = c
        if c.ok then
            NV.stats.refused = NV.stats.refused + 1
            log("no_vault: Living Fellows' fence crossing " .. fx .. "," .. fy .. " -> " .. tx .. "," .. ty .. " refused while calm; a way round of "
                .. steps .. " steps (gap or door)")
        else
            log("no_vault: Living Fellows' fence crossing " .. fx .. "," .. fy .. " -> " .. tx .. "," .. ty .. " allowed while calm: no way round within "
                .. NV.ROUND_MAX .. " steps (" .. tostring(steps or j.why) .. ")")
        end
    end
    return c.ok == true, "sol_calm_way_round"
end
function NV.wrapFence()
    local SC = g("SurvivorCompanion")
    local Nav = type(SC) == "table" and SC.Navigation or nil
    if type(Nav) ~= "table" or type(Nav._handleFenceForRequest) ~= "function" then return false end
    if Nav._solNoVault then return true end
    local base = Nav._handleFenceForRequest
    Nav._solNoVault = true
    Nav._handleFenceForRequest = function(actor, object, fromSquare, toSquare, intent, a6, a7)
        local ok, refuse, why = pcall(NV.refuseVault, actor, fromSquare, toSquare)
        if ok and refuse == true then return false, why end
        return base(actor, object, fromSquare, toSquare, intent, a6, a7)
    end
    log("Living Fellows fence steps: refused for Sol while calm when a way round is near (switch walk_no_vault)")
    return true
end

-- s97b (live 2026-11-11 12:06:44 / 12:08:34 / 12:08:55, following him in past the porch): the vaults came with no LF fence step
-- (no "refused"/"allowed" line): Living Fellows' native moves (intent.enginePath: engine_goal after a search ran out of time,
-- native_edge beside a car or tree, multi-level, recovery) hand a target to vanilla PathFindBehavior2 (SCNativeMovementActions
-- .dispatch -> SCNativeActions directPath -> pathToLocationF), and vanilla's own path hops a low fence with no Lua call at all.
-- While she is calm such a target is checked first: when the LF-priced probe from her square to it would cross a fence or a
-- window and a way without one exists within ROUND_MAX extra steps, vanilla gets the furthest square of that way it can reach
-- without a climb (the gap or the door) instead; the next native move from there goes on. Approved single-edge crossings
-- (intent.nativeAffordance: door, stairs, an allowed fence) are left alone.
NV.native, NV.nativeN = NV.native or {}, NV.nativeN or 0
NV.NATIVE_TTL_MS = 1500
NV.stats.nativeWaypoints = NV.stats.nativeWaypoints or 0
function NV.squareAt(x, y, z) return Live.square(x, y, z) end
local function xyzOf(t)
    if type(t) == "table" and tonumber(t.x) ~= nil and tonumber(t.y) ~= nil and type(t.getX) ~= "function" then
        return math.floor(tonumber(t.x)), math.floor(tonumber(t.y)), math.floor(tonumber(t.z) or 0)
    end
    local x, y, z = tonumber((call(t, "getX"))), tonumber((call(t, "getY"))), tonumber((call(t, "getZ")))
    if x == nil or y == nil then return nil end
    return math.floor(x), math.floor(y), math.floor(z or 0)
end
-- vanilla's path is any-angle and prices a low fence about like floor: a stretch is at risk when the straight line crosses a
-- fence or window edge, or when a probe that prices a climb like floor (0 extra) crosses one
local CLIMB = { fence = true, window = true, frame = true }
function NV.lineClimbs(ax, ay, bx, by, z)
    local x0, y0, x1, y1 = ax + 0.5, ay + 0.5, bx + 0.5, by + 0.5
    local n = math.max(1, math.floor(math.max(math.abs(x1 - x0), math.abs(y1 - y0)) * 10))
    local cx, cy = ax, ay
    for i = 1, n do
        local nx, ny = math.floor(x0 + (x1 - x0) * i / n), math.floor(y0 + (y1 - y0) * i / n)
        if nx ~= cx or ny ~= cy then
            if nx ~= cx and ny ~= cy then
                local k1 = M.edgeBetween(cx, cy, nx, cy, z)
                local k2 = M.edgeBetween(nx, cy, nx, ny, z)
                local k3 = M.edgeBetween(cx, cy, cx, ny, z)
                local k4 = M.edgeBetween(cx, ny, nx, ny, z)
                if CLIMB[k1] or CLIMB[k2] or CLIMB[k3] or CLIMB[k4] then return true end
            elseif CLIMB[(M.edgeBetween(cx, cy, nx, ny, z))] then return true end
            cx, cy = nx, ny
        end
    end
    return false
end
function NV.vanillaClimbs(ax, ay, bx, by, z)
    if NV.lineClimbs(ax, ay, bx, by, z) then return true end
    NV.probeClimb = 0
    local okP, p = pcall(probe, ax, ay, bx, by, z, false, NV.PROBE_NODES * 2, NV.PROBE_MARGIN)
    NV.probeClimb = nil
    return okP and p.state == "done" and crossesClimb(p)
end
function NV.nativeWaypoint(actor, intent)
    if not nvOn() or type(intent) ~= "table" or intent.enginePath ~= true or intent.nativeAffordance ~= nil then return nil end
    if actor == nil or actor ~= solActor() or call(actor, "getVehicle") ~= nil or M.flee(actor) then return nil end
    local tx, ty, tz = xyzOf(intent.nextSquare or intent.targetSquare or intent.targetPosition)
    local px, py, pz = posOf(actor)
    if tx == nil or px == nil or tz ~= pz then return nil end
    if math.max(math.abs(tx - px), math.abs(ty - py)) <= 1 then return nil end
    local k = px .. "," .. py .. ">" .. tx .. "," .. ty .. "," .. tz
    local t = nowMs()
    local c = NV.native[k]
    if c ~= nil and t - c.at <= NV.NATIVE_TTL_MS then return c.wp end
    local wp = nil
    if NV.vanillaClimbs(px, py, tx, ty, pz) then
        local s = probe(px, py, tx, ty, pz, true, NV.ROUND_NODES * 2, NV.ROUND_MAX)
        local straight = math.max(math.abs(tx - px), math.abs(ty - py))
        if s.state == "done" and type(s.path) == "table" and #s.path - 1 <= straight + NV.ROUND_MAX then
            local lo, hi = 1, #s.path
            while hi - lo > 1 do
                local mid = math.floor((lo + hi) / 2)
                if NV.vanillaClimbs(px, py, s.path[mid].x, s.path[mid].y, pz) then hi = mid else lo = mid end
            end
            if lo < 2 then lo = 2 end
            wp = { x = s.path[lo].x, y = s.path[lo].y, z = pz }
        end
    end
    NV.nativeN = NV.nativeN + 1
    if NV.nativeN > 256 then NV.native, NV.nativeN = {}, 1 end
    NV.native[k] = { at = t, wp = wp }
    if wp ~= nil then
        NV.stats.nativeWaypoints = NV.stats.nativeWaypoints + 1
        log("no_vault: Living Fellows' engine path " .. px .. "," .. py .. " -> " .. tx .. "," .. ty .. " (" .. tostring(intent.action)
            .. ") would cut over a fence; vanilla walks to " .. wp.x .. "," .. wp.y .. " first (gap or door)")
    end
    return wp
end
function NV.wrapNative()
    local SC = g("SurvivorCompanion")
    local Mv = type(SC) == "table" and SC.NativeMovementActions or nil
    if type(Mv) ~= "table" or type(Mv.dispatch) ~= "function" then return false end
    if Mv._solNoVault then return true end
    local base = Mv.dispatch
    Mv._solNoVault = true
    Mv.dispatch = function(actor, mode, intent, provider)
        local ok, wp = pcall(NV.nativeWaypoint, actor, intent)
        if ok and type(wp) == "table" then
            local sq = NV.squareAt(wp.x, wp.y, wp.z)
            if sq ~= nil then
                local copy = {}
                for key, v in pairs(intent) do copy[key] = v end
                copy.nextSquare, copy.targetSquare, copy.targetPosition, copy.targetKind = sq, sq, nil, "square"
                copy.solNoVaultWaypoint = true
                return base(actor, mode, copy, provider)
            end
        end
        return base(actor, mode, intent, provider)
    end
    log("Living Fellows engine paths: re-aimed through the gap or door for Sol while calm (switch walk_no_vault)")
    return true
end
-- what Living Fellows was doing when a calm climb started (for the runtime check)
function NV.lfMoveNote(a)
    local SC = g("SurvivorCompanion")
    local Nav = type(SC) == "table" and SC.Navigation or nil
    if type(Nav) ~= "table" or type(Nav.peek) ~= "function" then return "" end
    local ok, st = pcall(Nav.peek, a)
    if not ok or type(st) ~= "table" then return "" end
    local lease = type(st.nativeLease) == "table" and st.nativeLease or nil
    local function sq(s) local x, y = xyzOf(s); return x and (x .. "," .. y) or "-" end
    return " | LF goal=" .. tostring(st.goalAction) .. " pathReason=" .. tostring(st.pathReason) .. " lastMove=" .. tostring(st.lastMovementReason)
        .. " native=" .. (lease and (tostring(lease.reason) .. "/" .. tostring(lease.affordance) .. " to " .. sq(lease.toSquare)) or "none")
end

-- a climb that starts while she is calm: one line, for the runtime check
function NV.watch()
    if not nvOn() then return end
    local a = solActor()
    if a == nil then return end
    local s = string.lower(tostring(call(a, "getActionStateName") or ""))
    if s ~= NV.lastState then
        NV.lastState = s
        if NV.CLIMB_STATES[s] and not M.flee(a) then
            NV.stats.calmVaults = NV.stats.calmVaults + 1
            local px, py = posOf(a)
            local okN, note = pcall(NV.lfMoveNote, a)
            log("no_vault: calm vault seen (" .. s .. ") at " .. tostring(px) .. "," .. tostring(py) .. (M.R and (" on the walk to " .. M.R.gx .. "," .. M.R.gy) or "")
                .. (okN and note or ""))
        end
    end
end
function NV.install()
    if NV._installed then return end
    NV._installed = true
    if Events and Events.OnTick and type(Events.OnTick.Add) == "function" then
        local nextAt, wrapTries = 0, 0
        Events.OnTick.Add(function()
            local t = nowMs()
            if t < nextAt then return end
            nextAt = t + 250
            if wrapTries < 40 and not (type(g("SurvivorCompanion")) == "table" and type(g("SurvivorCompanion").Navigation) == "table"
                    and g("SurvivorCompanion").Navigation._solNoVault
                    and type(g("SurvivorCompanion").NativeMovementActions) == "table" and g("SurvivorCompanion").NativeMovementActions._solNoVault) then
                wrapTries = wrapTries + 1
                pcall(NV.wrapFence)
                pcall(NV.wrapNative)
            end
            pcall(NV.watch)
        end)
    end
    pcall(NV.wrapFence)
    pcall(NV.wrapNative)
    log("walk_no_vault ready (switch walk_no_vault=" .. tostring(nvOn()) .. ")")
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(function() pcall(NV.install) end) end
