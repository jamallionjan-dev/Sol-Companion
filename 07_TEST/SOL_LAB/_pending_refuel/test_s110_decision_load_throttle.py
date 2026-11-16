"""s110 regression tests for the measured load-aware ordinary decision interval."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PENDING = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "05_TOOLS" / "sol_kahlua"))
import kahlua_env

checks = []


def check(name, actual, expected=True):
    ok = actual == expected
    checks.append(ok)
    print(("PASS" if ok else "FAIL") + " " + name + " -> " + str(actual))


lua = kahlua_env.lua51.LuaRuntime(unpack_returned_tuples=True)
helper_source = (PENDING / "SolDecisionBudget.lua").read_text(encoding="utf-8")
lua.globals().SolDecisionBudget = lua.execute(helper_source)
cases = [
    ("switch off preserves original cadence", 100, 3, False, 1000, 0, 100),
    ("low load preserves original cadence", 100, 1, True, 1000, 0, 100),
    ("load level two caps routine cadence", 100, 2, True, 1000, 0, 150),
    ("load level three caps routine cadence", 100, 3, True, 1000, 0, 150),
    ("new player command retains fast cadence", 100, 3, True, 1000, 1500, 100),
    ("command grace expires cleanly", 100, 3, True, 1500, 1500, 150),
    ("base cadence is never shortened", 180, 3, True, 1000, 0, 180),
    ("base cadence above cap is preserved", 225, 3, True, 1000, 0, 225),
    ("invalid base is clamped safely", 0, 3, True, 1000, 0, 1),
]
for name, base, level, enabled, now, urgent, expected in cases:
    result = lua.eval('SolDecisionBudget.ordinaryInterval(%r,%r,%s,%r,%r)' %
                      (base, level, "true" if enabled else "false", now, urgent))
    check(name, result, expected)

with tempfile.TemporaryDirectory(prefix="s110_apply_") as tmp:
    client = Path(tmp) / "client"
    client.mkdir()
    for name in ("SolAuthority.lua", "SCRuntime.lua", "SCCommands.lua"):
        source_file = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client" / name
        (client / name).write_bytes(source_file.read_bytes())
    apply = str(PENDING / "apply_s110_decision_load_throttle.py")
    first = subprocess.run([sys.executable, apply, str(client)], capture_output=True, text=True)
    check("installer applies cleanly to a temporary copy", first.returncode, 0)
    source = (client / "SCRuntime.lua").read_text(encoding="utf-8")
    commands = (client / "SCCommands.lua").read_text(encoding="utf-8")
    check("critical lane still uses configured 50 ms interval", '"decision-critical", criticalInterval, current' in source)
    check("throttle is behind its own authority switch", 'SolAuthority.on("decision_load_throttle") == true' in source)
    check("fresh command gets a one-second fast-lane grace", 'commandDecisionUrgentUntil[actor]' in source and 'runtime.notePlayerCommand, actor, state.lastCommandAt' in commands)
    check("ordinary path uses the adaptive helper", 'SolDecisionBudget.ordinaryInterval(' in source and 'current < urgentUntil and movementInterval or throttledInterval' in source)
    check("returned helper is assigned to the runtime local", 'local SolDecisionBudget = require "SolDecisionBudget"' in source)
    check("helper call is guarded and switch-off keeps base interval", 'local throttledInterval = movementInterval' in source and 'if throttleEnabled == true and type(SolDecisionBudget) == "table"' in source and 'throttledInterval = SolDecisionBudget.ordinaryInterval(' in source)
    digests = {p.name: p.read_bytes() for p in client.iterdir()}
    second = subprocess.run([sys.executable, apply, str(client)], capture_output=True, text=True)
    check("installer is idempotent", second.returncode, 0)
    check("idempotent rerun does not change bytes",
          all(p.read_bytes() == digests[p.name] for p in client.iterdir()), True)

check("switch-off behavior remains the original interval", 'if enabled ~= true or level < 2 then return base end' in (PENDING / "SolDecisionBudget.lua").read_text(encoding="utf-8"))

guard_cases = lua.execute('''
local function effectiveInterval(base, enabled, helper)
    local throttledInterval = base
    if enabled == true and type(helper) == "table"
        and type(helper.ordinaryInterval) == "function" then
        throttledInterval = helper.ordinaryInterval(base, 3, true, 1000, 0)
    end
    return throttledInterval
end
return effectiveInterval
''')
check("disabled switch never calls a missing helper", guard_cases(100, False, None), 100)
check("enabled switch uses the returned helper table", guard_cases(100, True, lua.globals().SolDecisionBudget), 150)

for name, path in (("Lua helper", PENDING / "SolDecisionBudget.lua"),
                   ("apply script", PENDING / "apply_s110_decision_load_throttle.py")):
    data = path.read_bytes()
    check(name + " stays ASCII", all(byte < 128 for byte in data))

print("\n%d/%d checks passed" % (sum(checks), len(checks)))
raise SystemExit(0 if all(checks) else 1)
