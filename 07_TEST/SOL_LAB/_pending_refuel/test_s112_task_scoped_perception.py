"""s112 offline checks: one Sol scan lease and no synchronous chat-triggered world refresh."""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CLIENT = os.path.join(ROOT, "07_TEST", "SOL_LAB", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
BASELINE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "07_TEST", "SOL_LAB", "_backup", "20261111_221659_before_s112_task_scoped_perception")
FILES = ("SolAuthority.lua", "SolWorldScan.lua", "SolInventory.lua", "SolBaseScan.lua", "SolChat.lua", "SolOrders.lua")
FAIL = []
PASS = 0


def ck(name, ok, detail=""):
    global PASS
    print(("PASS " if ok else "FAIL ") + name + ((" -- " + str(detail)[:500]) if detail and not ok else ""))
    if not ok:
        FAIL.append(name)
    else:
        PASS += 1


def main():
    with tempfile.TemporaryDirectory(prefix="sol_s112_scan_") as temp:
        cl = os.path.join(temp, "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
        os.makedirs(cl)
        os.makedirs(os.path.join(temp, "profile", "Zomboid", "Lua"))
        for name in os.listdir(BASELINE):
            if name.endswith(".lua"):
                shutil.copyfile(os.path.join(BASELINE, name), os.path.join(cl, name))
        switches = os.path.join(temp, "profile", "Zomboid", "Lua", "SolFixes_LAB.txt")
        with open(switches, "w", encoding="ascii", newline="\n") as handle:
            handle.write("perf_slice=on\n")

        # s112 was authored on top of s99's frame-sliced scanners. Prepare that
        # prerequisite on this disposable candidate-derived fixture first.
        perf_slice = os.path.join(HERE, "apply_s99_perf_slice.py")
        if not os.path.isfile(os.path.join(cl, "SolScanCoordinator.lua")):
            perf = subprocess.run([sys.executable, perf_slice, cl], capture_output=True, text=True)
            ck("s99 prerequisite applies to candidate snapshot", perf.returncode == 0, perf.stdout + perf.stderr)
        else:
            ck("s99 prerequisite already present in candidate snapshot", "local sliced" in open(os.path.join(cl, "SolWorldScan.lua"), encoding="utf-8").read())

        apply = os.path.join(HERE, "apply_s112_task_scoped_perception.py")
        first = subprocess.run([sys.executable, apply, cl], capture_output=True, text=True)
        second = subprocess.run([sys.executable, apply, cl], capture_output=True, text=True)
        ck("installer first run", first.returncode == 0, first.stdout + first.stderr)
        ck("installer is idempotent", second.returncode == 0 and "edited " not in second.stdout and "copied " not in second.stdout,
           second.stdout + second.stderr)
        ck("scan switch listed once", open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read().count('"task_scoped_perception"') == 1)
        ck("lab switch enabled once", open(switches, encoding="ascii").read().count("task_scoped_perception=on") == 1)
        for name in FILES + ("SolScanCoordinator.lua",):
            path = os.path.join(cl, name)
            source = open(path, encoding="utf-8").read()
            ck("ASCII only " + name, all(ord(c) < 128 for c in source))
            syntax = lua51.LuaRuntime(unpack_returned_tuples=True)
            syntax.globals().source = source
            ok, err = syntax.eval("function(s) local f,e=loadstring(s); return f~=nil, e end")(source)
            ck("Lua 5.1 syntax " + name, ok, err)

        c = lua51.LuaRuntime(unpack_returned_tuples=True)
        c.execute(open(os.path.join(cl, "SolScanCoordinator.lua"), encoding="utf-8").read())
        # The module assigns a global and returns the same table.
        c.execute("local ok,g,r=SolScanCoordinator.tryAcquire('world_scan','background'); assert(ok and g==1 and r=='acquired'); local ok2,g2,r2=SolScanCoordinator.tryAcquire('inventory','task'); assert(not ok2 and g2==nil and r2=='busy:world_scan'); local ok3,g3=SolScanCoordinator.tryAcquire('world_scan','background'); assert(ok3 and g3==1); assert(SolScanCoordinator.release('world_scan',1,'done')); local ok4,g4=SolScanCoordinator.tryAcquire('inventory','task'); assert(ok4 and g4==2); assert(not SolScanCoordinator.release('inventory',1,'stale')); assert(SolScanCoordinator.status().owner=='inventory')")
        ck("one active mission scan and stale lease cannot release successor", True)

        # Load the actual patched world scanner under a tiny Kahlua-like fixture; a scoped refresh queues work.
        fixture = r'''
NOW=100000; WRITES=0; OUT={}
function getTimestampMs() return NOW end
function print(_) end
function require(name) if name=="SolScanCoordinator" then return SolScanCoordinator end return nil end
SolText={}
SolAuthority={on=function(name) return name=="task_scoped_perception" or name=="perf_slice" end}
SolBudget={register=function(name,fn) OUT[name]=fn end}
SolUI={}
'''
        w = lua51.LuaRuntime(unpack_returned_tuples=True)
        w.execute(fixture)
        w.execute(open(os.path.join(cl, "SolScanCoordinator.lua"), encoding="utf-8").read())
        w.execute(open(os.path.join(cl, "SolWorldScan.lua"), encoding="utf-8").read())
        w.execute("SolUI.writeWorld=function() WRITES=WRITES+1; return true end; local ok,why=SolUI.scanNow(); assert(ok==true and why=='queued' and WRITES==0)")
        ck("task-scoped scanNow queues without synchronous world write", True)

        off = lua51.LuaRuntime(unpack_returned_tuples=True)
        off.execute(fixture.replace('return name=="task_scoped_perception" or name=="perf_slice"', 'return false'))
        off.execute(open(os.path.join(cl, "SolScanCoordinator.lua"), encoding="utf-8").read())
        off.execute(open(os.path.join(cl, "SolWorldScan.lua"), encoding="utf-8").read())
        off.execute("SolUI.writeWorld=function() WRITES=WRITES+1; return true end; assert(SolUI.scanNow()==true and WRITES==1)")
        ck("switch-off retains prior immediate scan path", True)

        chat = open(os.path.join(cl, "SolChat.lua"), encoding="utf-8").read()
        orders = open(os.path.join(cl, "SolOrders.lua"), encoding="utf-8").read()
        ck("ordinary chat skips eager world scan in scoped mode", 'if U.scanNow and not scoped then pcall(U.scanNow) end' in chat and 'fresh world data for this reply' not in chat)
        ck("rescue does not spend time on an unrelated world scan", 'if U.scanNow and not scoped then pcall(U.scanNow) end' in orders)
        ck("world and inventory jobs share the lease", 'tryAcquire("world_scan"' in open(os.path.join(cl, "SolWorldScan.lua"), encoding="utf-8").read() and 'tryAcquire("inventory"' in open(os.path.join(cl, "SolInventory.lua"), encoding="utf-8").read())
        world = open(os.path.join(cl, "SolWorldScan.lua"), encoding="utf-8").read()
        inventory = open(os.path.join(cl, "SolInventory.lua"), encoding="utf-8").read()
        base = open(os.path.join(cl, "SolBaseScan.lua"), encoding="utf-8").read()
        orders = open(os.path.join(cl, "SolOrders.lua"), encoding="utf-8").read()
        ck("superseded world scans stop before writing stale results", 'not SolScanCoordinator.owns("world_scan", worldLease)' in world)
        ck("superseded inventory scans stop on next budget tick", 'not SolScanCoordinator.owns("inventory", job.lease)' in inventory)
        ck("explicit base discovery shares the same mission lease", 'tryAcquire("base_scan", "explicit_base_discovery")' in base)
        ck("direct order and forget cancel the active mission scan", 'cancelAll("new_direct_order:"' in orders and 'cancelAll("sol_forget")' in orders)

    print("s112 task-scoped perception: %d passed, %d failed" % (PASS, len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
