"""s152b offline: SolAuthority.on with and without the lab marker, the switch file and the shipped defaults.
Run: python test_s152b_shipped_defaults.py [client dir]. Offline PASS is not Runtime PASS."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kahlua_env import lua51
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
src = open(os.path.join(CL, "SolAuthority.lua"), encoding="utf-8").read()
FAIL = []
def run(lab, file_lines, defaults):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute('getTimestampMs=function() return 1 end')
    if file_lines is None: L.execute('getFileReader=function() return nil end')
    else:
        L.globals().LINES = L.table_from(file_lines)
        L.execute('getFileReader=function(name) local i=0 return {readLine=function() i=i+1; return LINES[i] end, close=function() end} end')
    if lab: L.execute('SolLab={active=true}')
    if defaults: L.execute('SolFixesDefault={edge_api=true, far_car=false}')
    L.execute(src)
    return tuple(L.eval('SolAuthority.on("%s")' % n) for n in ('edge_api', 'far_car', 'unknown_x'))
for name, got, want in (
    ("lab, no file: everything on", run(True, None, False), (True, True, True)),
    ("lab ignores shipped defaults", run(True, None, True), (True, True, True)),
    ("lab file decides", run(True, ['far_car=off'], True), (True, False, True)),
    ("main, no file, no defaults: all off (as before)", run(False, None, False), (False, False, False)),
    ("main, no file: shipped defaults", run(False, None, True), (True, False, False)),
    ("main, file overrides defaults", run(False, ['edge_api=off', 'far_car=on'], True), (False, True, False)),
):
    ok = got == want; print(("PASS " if ok else "FAIL ") + name + ("" if ok else " : %r" % (got,)))
    if not ok: FAIL.append(name)
print("SUMMARY fail=%d" % len(FAIL)); sys.exit(1 if FAIL else 0)
