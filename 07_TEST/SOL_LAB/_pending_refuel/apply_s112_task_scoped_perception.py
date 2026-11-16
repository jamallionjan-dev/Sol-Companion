"""Serialize Sol-owned world and inventory scans; slice on-demand world refreshes in the lab."""
import os
import shutil
import sys

CLIENT = os.path.abspath(sys.argv[1])
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = "\n", "\r\n"


def edit(path, old, new):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    nl = CRLF if CRLF in text else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in text:
        print("kept " + os.path.basename(path))
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit("expected one exact match in %s, found %d" % (path, count))
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace(old, new, 1))
    print("edited " + os.path.basename(path))


def install_file(source, target):
    if os.path.exists(target):
        with open(source, "rb") as a, open(target, "rb") as b:
            if a.read() != b.read():
                raise SystemExit("refusing to overwrite changed " + os.path.basename(target))
        print("kept " + os.path.basename(target))
    else:
        shutil.copyfile(source, target)
        print("copied " + os.path.basename(target))


install_file(os.path.join(HERE, "SolScanCoordinator.lua"), os.path.join(CLIENT, "SolScanCoordinator.lua"))

authority = os.path.join(CLIENT, "SolAuthority.lua")
with open(authority, "r", encoding="utf-8", newline="") as handle:
    auth_text = handle.read()
if '"task_scoped_perception"' not in auth_text:
    edit(authority, "A.FIXES = {" + NL,
         'A.FIXES = {' + NL + '    "task_scoped_perception", -- s112: one Sol scan lease; urgent LF perception remains independent' + NL)
else:
    print("kept task_scoped_perception in SolAuthority.lua")

world = os.path.join(CLIENT, "SolWorldScan.lua")
with open(world, "r", encoding="utf-8") as handle:
    world_text = handle.read()
if "PASSIVE_NEAR_TILES" in world_text:
    print("kept lab task-scoped performance policy in SolWorldScan.lua")
else:
    edit(world, 'require "SolText"' + NL,
         'require "SolText"' + NL + 'local SolScanCoordinator = require "SolScanCoordinator"' + NL)
    edit(world,
         'local function sliceOn() local A_ = rawget(_G, "SolAuthority"); return type(A_) == "table" and type(A_.on) == "function" and A_.on("perf_slice") == true end',
         'local function sliceOn() local A_ = rawget(_G, "SolAuthority"); return type(A_) == "table" and type(A_.on) == "function" and (A_.on("perf_slice") == true or A_.on("task_scoped_perception") == true) end')
    edit(world, 'local sliced, slicedMs = nil, 0' + NL,
         'local sliced, slicedMs = nil, 0' + NL + 'local scanRequested, worldLease = false, nil' + NL)
    edit(world,
         '        sliced = nil' + NL + '        U.worldScanTuned(job.tuneMs)' + NL,
         '        sliced = nil' + NL + '        U.worldScanTuned(job.tuneMs)' + NL + '        if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "done"); worldLease = nil end' + NL)
old_tick = '''local function onTick(remainingMs)
    local t = nowMs()
    if sliced == nil then
        if t - lastTick < INTERVAL_MS then return end
        lastTick = t
        local ok, job = pcall(scanJob)
        if not ok or job == nil then return end
        sliced, slicedMs = job, 0
        if sliceOn() then                                                      -- s99 perf_slice: making the job is this frame's work
            local ms = nowMs() - t
            slicedMs = ms
            job.phase, job.tuneMs, job.di = "squares", ms, 1
            if U.perfAdd then U.perfAdd("world_scan", ms) end
            return
        end
    end
    if sliced.phase ~= nil or sliceOn() then                                   -- s99 perf_slice
        local okS, err = pcall(slicedTick, t, remainingMs)
        if not okS then log("scan failed: " .. tostring(err)); sliced = nil end
        return
    end
    local ok, done = pcall(sliced.step, remainingMs or 2)
    slicedMs = slicedMs + (nowMs() - t)
    if not ok then log("scan failed: " .. tostring(done)); sliced = nil; return end
    if done then
        local job = sliced
        sliced = nil
        local okF, snap = pcall(job.finish)
        if not okF then log("scan failed: " .. tostring(snap)); return end
        local t1 = nowMs()
        U.writeWorldRaw(snap)
        U.worldScanTuned(slicedMs + (nowMs() - t1))
        if U.perfAdd then U.perfAdd("world_scan", slicedMs + (nowMs() - t1)) end
    end
end
U.scanNow = function() sliced = nil; lastTick = nowMs(); return U.writeWorld() end'''
new_tick = '''local function onTick(remainingMs)
    local t = nowMs()
    if sliced ~= nil and worldLease ~= nil and not SolScanCoordinator.owns("world_scan", worldLease) then
        sliced, slicedMs, worldLease = nil, 0, nil
        log("cancelled superseded scan")
    end
    if sliced == nil then
        if not scanRequested and t - lastTick < INTERVAL_MS then return end
        local profile = scanRequested and "requested" or "background"
        local acquired, generation = SolScanCoordinator.tryAcquire("world_scan", profile)
        if not acquired then return end
        worldLease = generation
        scanRequested = false
        lastTick = t
        local ok, job = pcall(scanJob)
        if not ok or job == nil then
            log("scan start failed: " .. tostring(job))
            SolScanCoordinator.release("world_scan", worldLease, "start_failed")
            worldLease = nil
            return
        end
        sliced, slicedMs = job, 0
        if sliceOn() then
            local ms = nowMs() - t
            slicedMs = ms
            job.phase, job.tuneMs, job.di = "squares", ms, 1
            if U.perfAdd then U.perfAdd("world_scan", ms) end
            return
        end
    end
    if sliced.phase ~= nil or sliceOn() then
        local okS, err = pcall(slicedTick, t, remainingMs)
        if not okS then
            log("scan failed: " .. tostring(err))
            sliced = nil
            if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "failed"); worldLease = nil end
        end
        return
    end
    local ok, done = pcall(sliced.step, remainingMs or 2)
    slicedMs = slicedMs + (nowMs() - t)
    if not ok then
        log("scan failed: " .. tostring(done)); sliced = nil
        if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "failed"); worldLease = nil end
        return
    end
    if done then
        local job = sliced
        sliced = nil
        local okF, snap = pcall(job.finish)
        if not okF then
            log("scan failed: " .. tostring(snap))
            if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "finish_failed"); worldLease = nil end
            return
        end
        local t1 = nowMs()
        U.writeWorldRaw(snap)
        U.worldScanTuned(slicedMs + (nowMs() - t1))
        if U.perfAdd then U.perfAdd("world_scan", slicedMs + (nowMs() - t1)) end
        if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "done"); worldLease = nil end
    end
end
U.requestWorldScan = function() scanRequested = true; return true, "queued" end
U.scanNow = function()
    local A_ = rawget(_G, "SolAuthority")
    if type(A_) == "table" and type(A_.on) == "function" and A_.on("task_scoped_perception") == true then
        return U.requestWorldScan()
    end
    if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "sync_override"); worldLease = nil end
    sliced = nil; lastTick = nowMs(); return U.writeWorld()
end'''
if "PASSIVE_NEAR_TILES" not in world_text:
    edit(world, old_tick, new_tick)

base_scan = os.path.join(CLIENT, "SolBaseScan.lua")
edit(base_scan, 'local U = SolUI' + NL,
     'local U = SolUI' + NL + 'local SolScanCoordinator = require "SolScanCoordinator"' + NL)
edit(base_scan, 'function U.baseScan()' + NL, 'local function baseScanImpl()' + NL)
anchor = '    return true, text' + NL + 'end' + NL + NL + 'function U.baseApply()'
edit(base_scan, anchor,
     '    return true, text' + NL + 'end' + NL + NL +
     'function U.baseScan()' + NL +
     '    local acquired, lease, why = SolScanCoordinator.tryAcquire("base_scan", "explicit_base_discovery")' + NL +
     '    if not acquired then return false, "scan_busy;" .. tostring(why) end' + NL +
     '    local ok, a, b = pcall(baseScanImpl)' + NL +
     '    SolScanCoordinator.release("base_scan", lease, ok and "done" or "failed")' + NL +
     '    if not ok then log("scan failed: " .. tostring(a)); return false, "scan_error" end' + NL +
     '    return a, b' + NL +
     'end' + NL + NL + 'function U.baseApply()')

inventory = os.path.join(CLIENT, "SolInventory.lua")
edit(inventory, '-- Debug mode stops the game on any error, even a caught one, so every game call is checked first.' + NL,
     '-- Debug mode stops the game on any error, even a caught one, so every game call is checked first.' + NL + 'local SolScanCoordinator = require "SolScanCoordinator"' + NL)
edit(inventory,
     '    local player = getSpecificPlayer and getSpecificPlayer(0) or nil' + NL + '    if player == nil then return false, "no_player" end' + NL + '    model = newModel()' + NL + '    job = { phase = "squares", squares = {}, si = 1, conts = {}, ci = 1, rects = rects, seenVeh = {}, px = num(method(player, "getX")), py = num(method(player, "getY")) }',
     '    local player = getSpecificPlayer and getSpecificPlayer(0) or nil' + NL + '    if player == nil then return false, "no_player" end' + NL + '    local acquired, lease, why = SolScanCoordinator.tryAcquire("inventory", "inventory")' + NL + '    if not acquired then return false, why or "scan_busy" end' + NL + '    model = newModel()' + NL + '    job = { phase = "squares", squares = {}, si = 1, conts = {}, ci = 1, rects = rects, seenVeh = {}, px = num(method(player, "getX")), py = num(method(player, "getY")), lease = lease }')
edit(inventory,
     'if type(A99_) == "table" and type(A99_.on) == "function" and A99_.on("perf_slice") == true then' + NL + '        job.phase, job.plan',
     'if type(A99_) == "table" and type(A99_.on) == "function" and (A99_.on("perf_slice") == true or A99_.on("task_scoped_perception") == true) then' + NL + '        job.phase, job.plan')
edit(inventory,
     '    model.state = "done"; model.ms = nowMs() - model.t; model.byKey = nil' + NL + '    last = model' + NL + '    job.phase = "done"' + NL,
     '    model.state = "done"; model.ms = nowMs() - model.t; model.byKey = nil' + NL + '    last = model' + NL + '    job.phase = "done"' + NL + '    SolScanCoordinator.release("inventory", job.lease, "done")' + NL)
edit(inventory,
     '                if type(A99_) == "table" and type(A99_.on) == "function" and A99_.on("perf_slice") == true then' + NL + '                    local b = tonumber(remainingMs) or 4' + NL + '                    if b > 4 then b = 4 end' + NL + '                    if b < 1 then b = 1 end' + NL + '                    U.invStepSliced(b)' + NL + '                else' + NL + '                    U.invStep()' + NL + '                end' + NL,
     '                if job and not SolScanCoordinator.owns("inventory", job.lease) then' + NL + '                    if model then model.state = "cancelled" end' + NL + '                    job = nil' + NL + '                    log("cancelled superseded scan")' + NL + '                    return' + NL + '                end' + NL + '                local slicedOn = type(A99_) == "table" and type(A99_.on) == "function" and (A99_.on("perf_slice") == true or A99_.on("task_scoped_perception") == true)' + NL + '                local okStep, errStep = pcall(function()' + NL + '                    if slicedOn then' + NL + '                        local b = tonumber(remainingMs) or 4' + NL + '                        if b > 4 then b = 4 end' + NL + '                        if b < 1 then b = 1 end' + NL + '                        U.invStepSliced(b)' + NL + '                    else' + NL + '                        U.invStep()' + NL + '                    end' + NL + '                end)' + NL + '                if not okStep then' + NL + '                    log("scan failed: " .. tostring(errStep))' + NL + '                    if model then model.state = "failed" end' + NL + '                    local lease = job and job.lease' + NL + '                    job = nil' + NL + '                    SolScanCoordinator.release("inventory", lease, "failed")' + NL + '                end' + NL)
edit(inventory,
     '            if t - lastAuto >= AUTO_MS and getSpecificPlayer and getSpecificPlayer(0) ~= nil then lastAuto = t; pcall(U.invStart) end',
     '            if t - lastAuto >= AUTO_MS and getSpecificPlayer and getSpecificPlayer(0) ~= nil then' + NL + '                local okStart, started, whyStart = pcall(U.invStart)' + NL + '                if okStart and started then lastAuto = t' + NL + '                elseif okStart and string.find(tostring(whyStart or ""), "busy", 1, true) then lastAuto = t - AUTO_MS + 5000' + NL + '                else lastAuto = t end' + NL + '            end')

for filename, old, new in [
    ("SolChat.lua", '    if U.scanNow then pcall(U.scanNow) end          -- fresh world data for this reply', '    local A_ = rawget(_G, "SolAuthority")' + NL + '    local scoped = type(A_) == "table" and type(A_.on) == "function" and A_.on("task_scoped_perception") == true' + NL + '    if U.scanNow and not scoped then pcall(U.scanNow) end'),
    ("SolOrders.lua", '    if U.scanNow then pcall(U.scanNow) end', '    local A_ = rawget(_G, "SolAuthority")' + NL + '    local scoped = type(A_) == "table" and type(A_.on) == "function" and A_.on("task_scoped_perception") == true' + NL + '    if U.scanNow and not scoped then pcall(U.scanNow) end'),
]:
    edit(os.path.join(CLIENT, filename), old, new)

orders = os.path.join(CLIENT, "SolOrders.lua")
edit(orders, 'local U = SolUI' + NL,
     'local U = SolUI' + NL + 'local SolScanCoordinator = require "SolScanCoordinator"' + NL)
edit(orders, 'local function fixedOrder(command, line)' + NL,
     'local function fixedOrder(command, line)' + NL + '    SolScanCoordinator.cancelAll("new_direct_order:" .. tostring(command))' + NL)
edit(orders, 'function O.forget()' + NL,
     'function O.forget()' + NL + '    SolScanCoordinator.cancelAll("sol_forget")' + NL)

switch_file = os.path.normpath(os.path.join(CLIENT, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt"))
if os.path.isfile(switch_file):
    with open(switch_file, "r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    if "task_scoped_perception=" not in text:
        nl = CRLF if CRLF in text else NL
        if text and not text.endswith((NL, CRLF)):
            text += nl
        text += "task_scoped_perception=on" + nl
        with open(switch_file, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        print("enabled task_scoped_perception in lab only")
    else:
        print("kept task_scoped_perception lab switch")
print("s112 task-scoped perception applied to SOL_LAB")
