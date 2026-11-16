"""Speed fixes after the 2026-11-09 play session. Each behaviour has its own switch in SolFixes_LAB.txt. Game closed only. All or nothing.
usage: apply_s40_lua.py <client dir> [--verify]"""
import os, sys
D = sys.argv[1]
EDITS = {}
def E(f, a, b): EDITS.setdefault(f, []).append((a, b))
SW = 'local _A = rawget(_G, "SolAuthority"); '
def on(name): return '(type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("%s") == true)' % name


E("SolAuthority.lua", "A.FIXES = {" + chr(10), "A.FIXES = {" + chr(10) + "    \"walk_search_fast\", \"order_jog\", \"walk_no_resend\", \"order_breaks_rest\", \"farm_keep_tools\"," + chr(10))

# walk_search_fast: a walk order's route search keeps her standing still for up to 30 s (12:20:36 to 12:21:07); following is bounded at 5 s
E("SCNavigation.lua", """    return leaseMs, math.max(leaseMs, hardMs)
end
""", """    if type(pending) == "table" and pending.followRouting ~= true and %s then
        leaseMs, hardMs = math.min(leaseMs, 2500), math.min(hardMs, 5000)
    end
    return leaseMs, math.max(leaseMs, hardMs)
end
""" % on("walk_search_fast"))

# order_jog: an order to go somewhere is run, not strolled, unless he is sneaking
E("SCCommands.lua", """    local accepted, status = SC.Navigation.request(actor, square,
        resolvedMoveMode(state, player), {
        action = "ordered_move",
""", """    local orderedMode = resolvedMoveMode(state, player)
    if orderedMode == "walk" and type(SolSpeechAR) == "table" and type(SolSpeechAR.isSol) == "function" and SolSpeechAR.isSol(actor)
        and %s then orderedMode = "jog" end
    local accepted, status = SC.Navigation.request(actor, square,
        orderedMode, {
        action = "ordered_move",
""" % on("order_jog"))

# order_breaks_rest: a chair break holds her body and refused every walk (13:35:27 onwards)
E("SolActions.lua", """    local ok, why = gatewayGoTo(sol, math.floor(x), math.floor(y), z)
    return ok, ok and ("walking_to " .. math.floor(x) .. "," .. math.floor(y)) or why
""", """    local ok, why = gatewayGoTo(sol, math.floor(x), math.floor(y), z)
    if ok ~= true and type(why) == "string" and string.find(why, "action_owned:downtime:", 1, true) == 1 and %s then
        local SC0 = LF()
        if SC0 and type(SC0.Downtime) == "table" and type(SC0.Downtime.cancel) == "function" then
            pcall(SC0.Downtime.cancel, sol, "sol_order")
            ok, why = gatewayGoTo(sol, math.floor(x), math.floor(y), z)
        end
    end
    return ok, ok and ("walking_to " .. math.floor(x) .. "," .. math.floor(y)) or why
""" % on("order_breaks_rest"))
E("SolGPS.lua", """    if type(reason) ~= "string" or string.find(reason, "action_owned:downtime:", 1, true) ~= 1 then return end
""", """    if type(reason) ~= "string" or string.find(reason, "action_owned:downtime:", 1, true) ~= 1 then return end
    if not %s then return end
""" % on("order_breaks_rest"))

# walk_no_resend: every order restarted her step; while she is moving the order stands
E("SolFarmWork.lua", """    if w.sent ~= nil and j.spent - w.sent < RESEND_MS then return "walking" end
    local target = targets[((w.ti - 1) % #targets) + 1]
""", """    if w.sent ~= nil and px ~= nil and %s then
        if w.lx ~= px or w.ly ~= py then w.lx, w.ly, w.sent = px, py, j.spent end                                 -- a new square since the last look: leave her to it
    end
    if w.sent ~= nil and j.spent - w.sent < RESEND_MS then return "walking" end
    local target = targets[((w.ti - 1) %% #targets) + 1]
""" % on("walk_no_resend"))

# why a walk failed, in the log (no switch: it only writes a line)
E("SolFarmWork.lua", """    if j.spent - w.from > w.limit then return "failed" end
    if call(a, "getVehicle") ~= nil then return "walking" end
""", """    if j.spent - w.from > w.limit then j.walkFail = "time_limit"; return "failed" end
    if call(a, "getVehicle") ~= nil then return "walking" end
""")
E("SolFarmWork.lua", """        w.refused = w.refused + 1
        return w.refused >= REFUSED_LIMIT and "failed" or "walking"
""", """        w.refused = w.refused + 1
        if w.refused >= REFUSED_LIMIT then j.walkFail = "no_standing_square" end
        return w.refused >= REFUSED_LIMIT and "failed" or "walking"
""")
E("SolFarmWork.lua", """    w.refused = w.refused + 1
    if w.refused >= REFUSED_LIMIT then return "failed" end
    return "walking"
end
""", """    w.refused = w.refused + 1
    if w.refused >= REFUSED_LIMIT then j.walkFail = "walk_refused:" .. tostring(why); return "failed" end
    return "walking"
end
""")
E("SolFarmWork.lua", """    if j == nil then return end
    if reason == "no_path" or reason == "carry_no_path" then                     -- "no road" only when it is true
""", """    if j == nil then return end
    print("[SolFarmWork] job failed op=" .. tostring(j.op) .. " reason=" .. tostring(reason) .. " walkFail=" .. tostring(j.walkFail) .. " at " .. tostring(j.x) .. "," .. tostring(j.y) .. " walkTo " .. tostring(j.walk and j.walk.x) .. "," .. tostring(j.walk and j.walk.y))
    if reason == "no_path" or reason == "carry_no_path" then                     -- "no road" only when it is true
""")

# farm_keep_tools: she took seeds back to the crate after every plot, because the next job was watering (one plot in 13:38)
E("SolFarmWork.lua", """    if #m.owed > 0 and not usesOwed(m, t) and startReturn(m, a) then return end
""", """    if #m.owed > 0 and not usesOwed(m, t) and not %s and startReturn(m, a) then return end
""" % on("farm_keep_tools"))

# why the driving layer refused a route
E("SCDriving.lua", """    if not followed then
        job.result, job.reason, job.detail = "failed", "bridge_failure", followReason
""", """    if not followed then
        print("[SolDrive] route refused: " .. tostring(followReason))
        job.result, job.reason, job.detail = "failed", "bridge_failure", followReason
""")
E("SCDriving.lua", """    local status, why = Driving.status(actor)
    if not status then
        local stopped = Driving.stop(actor, "bridge_failure")
""", """    local status, why = Driving.status(actor)
    if not status then
        print("[SolDrive] no native status: " .. tostring(why))
        local stopped = Driving.stop(actor, "bridge_failure")
""")

EDITS = {f: [p for p in v if p] for f, v in EDITS.items()}
if len(sys.argv) > 2 and sys.argv[2] == "--verify":
    missing = 0
    for f, pairs_ in EDITS.items():
        t = open(os.path.join(D, f), encoding="utf-8", newline="").read().replace(chr(13) + chr(10), chr(10))
        for a, b in pairs_:
            if t.count(b) < 1: missing += 1; print("MISSING", f, b[:70])
    print("verified", sum(len(v) for v in EDITS.values()), "edits, missing", missing)
    sys.exit(1 if missing else 0)
out = {}
for f, pairs_ in EDITS.items():
    p = os.path.join(D, f)
    t = open(p, encoding="utf-8", newline="").read()
    nl = chr(13) + chr(10) if chr(13) + chr(10) in t else chr(10)
    for a, b in pairs_:
        a2, b2 = a.replace(chr(10), nl), b.replace(chr(10), nl)
        assert t.count(a2) == 1, (f, a[:70], t.count(a2))
        t = t.replace(a2, b2)
    out[p] = t
for p, t in out.items(): open(p, "w", encoding="utf-8", newline="").write(t)
print("applied", sum(len(v) for v in EDITS.values()), "edits to", len(out), "files")
