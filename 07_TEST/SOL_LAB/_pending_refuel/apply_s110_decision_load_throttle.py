"""s110: throttle only ordinary AI decision evaluations during measured load.
Usage: python apply_s110_decision_load_throttle.py <client lua dir>
"""
import os
import shutil
import sys

CLIENT = os.path.abspath(sys.argv[1])
HERE = os.path.dirname(os.path.abspath(__file__))
NL = "\n"
CRLF = "\r\n"


def edit(path, old, new):
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    newline = CRLF if CRLF in text else NL
    old_text = old.replace(NL, newline)
    new_text = new.replace(NL, newline)
    if new_text in text:
        print("kept " + os.path.basename(path))
        return
    count = text.count(old_text)
    if count != 1:
        raise SystemExit("expected one match in %s, found %d" % (path, count))
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace(old_text, new_text))
    print("edited " + os.path.basename(path))


helper_src = os.path.join(HERE, "SolDecisionBudget.lua")
helper_dst = os.path.join(CLIENT, "SolDecisionBudget.lua")
if os.path.exists(helper_dst):
    with open(helper_dst, "rb") as handle:
        current = handle.read()
    with open(helper_src, "rb") as handle:
        expected = handle.read()
    if current != expected:
        raise SystemExit("refusing to overwrite changed SolDecisionBudget.lua")
    print("kept SolDecisionBudget.lua")
else:
    shutil.copyfile(helper_src, helper_dst)
    print("copied SolDecisionBudget.lua")

authority = os.path.join(CLIENT, "SolAuthority.lua")
edit(authority,
     'A.FIXES = {' + NL,
     'A.FIXES = {' + NL + '    "decision_load_throttle", -- s110: ordinary decision cadence stretches to 150 ms under measured load; safety and fresh commands stay fast' + NL)

runtime = os.path.join(CLIENT, "SCRuntime.lua")
with open(runtime, encoding="utf-8", newline="") as handle:
    runtime_text = handle.read().replace(CRLF, NL)
bare_helper_require = 'require "SCPerformance"' + NL + 'require "SolDecisionBudget"' + NL
assigned_helper_require = 'require "SCPerformance"' + NL + 'local SolDecisionBudget = require "SolDecisionBudget"' + NL
if bare_helper_require in runtime_text:
    edit(runtime, bare_helper_require, assigned_helper_require)
else:
    edit(runtime, 'require "SCPerformance"' + NL, assigned_helper_require)
edit(runtime,
     'local criticalDecisionActive = setmetatable({}, { __mode = "k" })' + NL +
     'local decisionServiceEstimateMs = 0.5' + NL,
     'local criticalDecisionActive = setmetatable({}, { __mode = "k" })' + NL +
     'local decisionServiceEstimateMs = 0.5' + NL +
     'local commandDecisionUrgentUntil = setmetatable({}, { __mode = "k" })' + NL +
     'local lastDecisionThrottleLog = nil' + NL)
edit(runtime,
     'function runtime.frameSerial()' + NL +
     '    return inProductionTick and frameSerial or nil' + NL +
     'end' + NL,
     'function runtime.frameSerial()' + NL +
     '    return inProductionTick and frameSerial or nil' + NL +
     'end' + NL +
     'function runtime.notePlayerCommand(actor, at)' + NL +
     '    if actor == nil then return false end' + NL +
     '    commandDecisionUrgentUntil[actor] = (tonumber(at) or ((getTimestampMs and getTimestampMs()) or 0)) + 1000' + NL +
     '    return true' + NL +
     'end' + NL)
edit(runtime,
     '    local movementInterval = SC.Config.get("movementIntervalMs")' + NL,
     '    local movementInterval = SC.Config.get("movementIntervalMs")' + NL +
     '    local loadLevel = SC.Performance and type(SC.Performance.loadLevel) == "function"' + NL +
     '        and SC.Performance.loadLevel() or 0' + NL +
     '    local throttleEnabled = type(SolAuthority) == "table"' + NL +
     '        and type(SolAuthority.on) == "function"' + NL +
     '        and SolAuthority.on("decision_load_throttle") == true' + NL +
     '    local throttledInterval = movementInterval' + NL +
     '    if throttleEnabled == true and type(SolDecisionBudget) == "table"' + NL +
     '        and type(SolDecisionBudget.ordinaryInterval) == "function" then' + NL +
     '        throttledInterval = SolDecisionBudget.ordinaryInterval(' + NL +
     '            movementInterval, loadLevel, true, current, 0)' + NL +
     '    end' + NL +
     '    local throttleState = tostring(throttleEnabled) .. ":" .. tostring(loadLevel)' + NL +
     '        .. ":" .. tostring(throttledInterval)' + NL +
     '    if throttleState ~= lastDecisionThrottleLog then' + NL +
     '        lastDecisionThrottleLog = throttleState' + NL +
     '        print("[SolDecisionBudget] enabled=" .. tostring(throttleEnabled)' + NL +
     '            .. " load=" .. tostring(loadLevel) .. " ordinary="' + NL +
     '            .. tostring(throttledInterval) .. "ms base=" .. tostring(movementInterval)' + NL +
     '            .. "ms; critical lane unchanged; command grace=1000ms")' + NL +
     '    end' + NL)
edit(runtime,
     '            if isCritical(record) ~= true' + NL +
     '                and SC.Scheduler.dueFor(record.id, "decision", movementInterval, current) then' + NL,
     '            local urgentUntil = commandDecisionUrgentUntil[record.actor] or 0' + NL +
     '            local interval = current < urgentUntil and movementInterval or throttledInterval' + NL +
     '            if isCritical(record) ~= true' + NL +
     '                and SC.Scheduler.dueFor(record.id, "decision", interval, current) then' + NL)

commands = os.path.join(CLIENT, "SCCommands.lua")
edit(commands,
     'local function markCommand(actor, entry, state)' + NL +
     '    state.commandSerial = (state.commandSerial or 0) + 1' + NL +
     '    state.lastCommandAt = U().nowMs()' + NL,
     'local function markCommand(actor, entry, state)' + NL +
     '    state.commandSerial = (state.commandSerial or 0) + 1' + NL +
     '    state.lastCommandAt = U().nowMs()' + NL +
     '    local runtime = SC.Runtime' + NL +
     '    if runtime and type(runtime.notePlayerCommand) == "function" then' + NL +
     '        pcall(runtime.notePlayerCommand, actor, state.lastCommandAt)' + NL +
     '    end' + NL)

profile = os.path.normpath(os.path.join(CLIENT, "..", "..", "..", "..", "..", ".."))
switch_file = os.path.join(profile, "Lua", "SolFixes_LAB.txt")
if os.path.isfile(switch_file):
    with open(switch_file, encoding="utf-8", newline="") as handle:
        body = handle.read()
    if "decision_load_throttle=" not in body:
        newline = CRLF if CRLF in body else NL
        if body and not body.endswith((NL, CRLF)):
            body += newline
        body += "decision_load_throttle=on" + newline
        with open(switch_file, "w", encoding="utf-8", newline="") as handle:
            handle.write(body)
        print("SolFixes_LAB.txt: decision_load_throttle=on")
    else:
        print("kept SolFixes_LAB.txt")

print("s110 decision_load_throttle applied")
