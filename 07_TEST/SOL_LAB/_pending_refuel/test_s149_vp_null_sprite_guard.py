"""Test the s149 Viewpoint null-sprite guard and its live switch."""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CANDIDATE = os.path.join(ROOT, "01_WORK", "RELEASE", "SOL_2026-11-14_0.28.6", "Sol", "42", "media", "lua", "client")
FAIL = []
PASS = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(detail)) if detail and not ok else ""))
    (PASS if ok else FAIL).append(name)


tmp = tempfile.mkdtemp(prefix="s149_viewpoint_")
patched_source = None
try:
    client = os.path.join(tmp, "client")
    os.makedirs(client)
    shutil.copy(os.path.join(HERE, "SolCompatVP.lua"), os.path.join(client, "SolCompatVP.lua"))
    shutil.copy(os.path.join(CANDIDATE, "SolAuthority.lua"), os.path.join(client, "SolAuthority.lua"))
    switches = os.path.join(tmp, "SolFixes_LAB.txt")
    with open(switches, "w", encoding="ascii", newline="") as output:
        output.write("existing=on\r\n")
    applier = os.path.join(HERE, "apply_s149_vp_null_sprite_guard.py")
    first = subprocess.run([sys.executable, applier, client, switches], capture_output=True, text=True)
    snap = {name: open(os.path.join(client, name), "rb").read() for name in ("SolCompatVP.lua", "SolAuthority.lua")}
    sw = open(switches, "rb").read()
    second = subprocess.run([sys.executable, applier, client, switches], capture_output=True, text=True)
    snap2 = {name: open(os.path.join(client, name), "rb").read() for name in ("SolCompatVP.lua", "SolAuthority.lua")}
    patched_source = open(os.path.join(client, "SolCompatVP.lua"), encoding="utf-8").read()
    ck("installer applies", first.returncode == 0, first.stdout + first.stderr)
    ck("installer is idempotent", second.returncode == 0 and snap == snap2 and sw == open(switches, "rb").read(), second.stdout + second.stderr)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("""
FLAGS = { compat_vp_harvest=true, vp_null_sprite_guard=true }
SolAuthority = { on=function(name) return FLAGS[name] == true end }
ORIGINAL_CALLS = 0
ViewpointInteract = { harvest=function(player, object) ORIGINAL_CALLS=ORIGINAL_CALLS+1; return { original=true } end }
ISFarmingMenu = { getShovel=function() return nil end }
ProjectViewpointQOL = { isKnownHarvestError=function() return false end }
Events = { OnGameStart = { Add=function(fn) START=fn end } }
require = function() return true end
""")
L.execute(patched_source)
L.globals().START()
ck("guard installs once", L.eval("ViewpointInteract._solNullSpriteGuard == true"))
L.execute("nullObject={getSpriteName=function() return nil end}; visibleObject={getSpriteName=function() return 'sprite' end}")
L.execute("SolCompatVP.stats.nullSpriteSkips=0; nullResult=ViewpointInteract.harvest({}, nullObject)")
ck("null sprite skips unsafe vanilla menu", L.eval("type(nullResult) == 'table' and ORIGINAL_CALLS == 0"))
ck("skip has a reason", L.eval("nullResult.why == 'object has no sprite'"))
ck("renderable object keeps original behavior", L.eval("ViewpointInteract.harvest({}, visibleObject).original == true and ORIGINAL_CALLS == 1"))
L.execute("FLAGS.vp_null_sprite_guard=false")
ck("switch off delegates even for null sprite", L.eval("ViewpointInteract.harvest({}, nullObject).original == true and ORIGINAL_CALLS == 2"))
ck("skip counter increments exactly once", L.eval("SolCompatVP.stats.nullSpriteSkips == 1"))

print("SUMMARY pass=%d fail=%d" % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
