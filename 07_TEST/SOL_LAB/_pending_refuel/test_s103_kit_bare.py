"""s103 kit_bare offline. EFZ's real TW/Core + TW/Data + TW/Builds (Workshop, read-only), the real SCPersistence capture/restore
(addInventoryNode) and SolSecretLoadout.build, on a HandWeapon fake that follows B42's bytecode (s103_fakes.lua).
Shows: the OLD restore reproduces the live duplicatePath on exactly the 7 M4A1 paths; the NEW one gives the stored build and
nothing else; a snapshot that is already doubled comes back single; applyTree on a bare gun; installer idempotent; gates.
Run: python test_s103_kit_bare.py [client dir]"""
import os, sys, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kahlua_env import lua51
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
SHARED = os.path.join(CL, "..", "shared")
EFZ = r"C:/Program Files (x86)/Steam/steamapps/workshop/content/108600/3824755284/mods/EscapeFromZomboidFirearms/42/media/lua/shared/"
LOADOUT = os.path.join(HERE, "..", "profile", "Zomboid", "Lua", "Sol_SecretLoadout.txt")
FAIL, P = [], []
def ck(n, c, d=""): print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else "")); (P if c else FAIL).append(n)
tmp = tempfile.mkdtemp(prefix="s103kb_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
for f in os.listdir(CL):
    if f.endswith(".lua"): shutil.copy(os.path.join(CL, f), cl)
for f in ("SolWeaponPick.lua", "SolMagFill.lua"):
    if os.path.exists(os.path.join(HERE, f)): shutil.copy(os.path.join(HERE, f), cl)   # the staged s99 fix, as it will be installed
r1 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s103_kit_bare.py"), cl], capture_output=True, text=True)
r2 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s103_kit_bare.py"), cl], capture_output=True, text=True)
ck("installer runs", r1.returncode == 0 and "applied" in r1.stdout, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout, r2.stdout + r2.stderr)
L = lua51.LuaRuntime()
comp = L.eval("function(s) local f, e = loadstring(s); return f ~= nil, e end")
for f in ("SolKitBare.lua", "SCPersistence.lua", "SolSecretLoadout.lua", "SolAuthority.lua"):
    src = open(os.path.join(cl, f), encoding="utf-8").read()
    ok, e = comp(src); ck("compiles " + f, ok, e)
    ck("ascii " + f, all(ord(c) < 128 for c in src))
    if f != "SolKitBare.lua": ck("s103 present in " + f, "kit_bare" in src)

def P_(s): return s.replace("\\", "/")
L.execute('package.path = [[%s/?.lua;%s/?.lua;%s?.lua]]' % (P_(cl), P_(os.path.abspath(SHARED)), EFZ))
L.execute('''
Events = setmetatable({}, {__index = function(t, k) local e = {Add = function() end, Remove = function() end}; rawset(t, k, e); return e end})
getTimestampMs = function() return 0 end; isClient = function() return false end; isServer = function() return false end
SW = { kit_bare = false, secret_loadout = true }
SolAuthority = { on = function(n) return SW[n] == true end }
LINES = {}
function getFileReader(name) local i = 0; return { readLine = function() i = i + 1; return LINES[i] end, close = function() end } end
''')
L.execute(open(os.path.join(HERE, "s103_fakes.lua"), encoding="utf-8").read())
ok, e = L.eval('pcall(require, "SCPersistence")'); ck("SCPersistence loads offline", ok, e)
L.execute(open(os.path.join(cl, "SolKitBare.lua"), encoding="utf-8").read())
L.execute(open(os.path.join(cl, "SolSecretLoadout.lua"), encoding="utf-8").read())
lines = open(LOADOUT, encoding="utf-8").read().splitlines()
for i, l in enumerate(lines): L.eval("function(i, s) LINES[i] = s end")(i + 1, l)
L.execute('''
B = require("TW/Builds"); Pers = SurvivorCompanion.Persistence
RECS = SolSecretLoadout.loadout()
function rec(i) return RECS[i] end
function built(i) local k, t = B.decode(RECS[i].code); local w = instanceItem(RECS[i].type); assert(TWRuntime.applyTree(w, t)); return w, t, k end
function restore(w)
    local snap = assert(Pers.captureDetachedItem(w))
    local inv = container("sol"); local actor = { getInventory = function() return inv end }
    local item, why = Pers.restoreDetachedItem(actor, snap)
    return inv.items[1], item ~= nil, why, #snap.roots[1].weaponParts
end
function dupsOf(w) local _, p, d = treeOf(w); return table.concat(d, ","), p end
''')
LIVE = ("mod_pistol_grip,mod_reciever/mod_barrel,mod_reciever/mod_barrel/mod_gas_block,mod_reciever/mod_barrel/mod_muzzle,"
        "mod_reciever/mod_handguard,mod_reciever/mod_handguard/mod_handguard,mod_stock/mod_stock_000")
ck("loadout read: G28 + M4A1", L.eval('RECS ~= nil and #RECS == 2 and RECS[1].efz == "G28" and RECS[2].efz == "M4A1"'))
ck("fresh EFZ weapon already carries the default preset (OnCreate)", L.eval('#instanceItem("EscapeFromZomboidFirearms.M4A1").list') > 0)
# M.build: applyTree
L.execute('SW.kit_bare = false; M4old = SolSecretLoadout.build(rec(2)); SW.kit_bare = true; CALLS.clearAllWeaponParts = 0; M4new = SolSecretLoadout.build(rec(2))')
ck("build (old): EFZ applyTree itself detaches the defaults - no duplicate at give time (live 21:29 give was clean)", L.eval('(dupsOf(M4old))') == "")
ck("build (kit_bare): stripped before applyTree", L.eval('CALLS.clearAllWeaponParts') >= 1)
ck("build (kit_bare): no duplicate, tree == stored build", L.eval('(function() local d = dupsOf(M4new); local _, t = B.decode(rec(2).code); return d == "" and sameTree((treeOf(M4new)), t) end)()'))
# restore: old path reproduces the live doubling
L.execute('SW.kit_bare = false; W, T = built(2); OLD, OLDOK, OLDWHY, N = restore(W)')
ck("restore (old) reproduces the live duplicatePath on exactly the 7 M4A1 paths", L.eval('(dupsOf(OLD))') == LIVE, L.eval('(dupsOf(OLD))'))
ck("restore (old): EFZ's R.read says duplicatePath", L.eval('select(2, dupsOf(OLD))') == "duplicatePath")
ck("restore (old): the detached verify sees the extra parts", L.eval('OLDOK') is False)
L.execute('SW.kit_bare = false; G, GT = built(1); GOLD = restore(G)')
ck("restore (old) of the G28 does not double (its build IS EFZ's default preset)", L.eval('(dupsOf(GOLD))') == "")
# restore: new path
L.execute('SW.kit_bare = true; NEW, NEWOK, NEWWHY, N2 = restore(W)')
ck("restore (kit_bare): no duplicate", L.eval('(dupsOf(NEW))') == "", L.eval('(dupsOf(NEW))'))
ck("restore (kit_bare): the parts are exactly the saved ones", L.eval('#NEW.list == N2'), L.eval('#NEW.list .. " vs " .. N2'))
ck("restore (kit_bare): tree == stored build", L.eval('(sameTree((treeOf(NEW)), T))'))
ck("restore (kit_bare): the detached verify passes", L.eval('NEWOK') is True, L.eval('tostring(NEWWHY)'))
# a snapshot taken from an already doubled weapon (the save on disk now)
L.execute('SW.kit_bare = true; REP = restore(OLD)')
ck("doubled snapshot (kit_bare): comes back with one part per path", L.eval('(dupsOf(REP))') == "", L.eval('(dupsOf(REP))'))
ck("doubled snapshot (kit_bare): every build path holds the build's part", L.eval('(function() local t = treeOf(REP); for k, v in pairs(T) do if t[k] ~= v then return false end end return true end)()'))
extra = L.eval('(function() local t = treeOf(REP); local x = {}; for k in pairs(t) do if T[k] == nil then x[#x + 1] = k end end table.sort(x); return table.concat(x, ",") end)()')
ck("doubled snapshot (kit_bare): only a preset-only part can remain (" + extra + ")", extra in ("", "mod_reciever/mod_sight_rear"), extra)
ck("doubled snapshot (kit_bare): EFZ C.validate accepts the result", L.eval('(EFZC.validate("M4A1", (treeOf(REP))))'))
ck("doubled snapshot (kit_bare): EFZ refresh says ready (no duplicatePath)", L.eval('REP:getModData().TW ~= nil and REP:getModData().TW.ready == true'))
# not a weapon / a vanilla item without parts: untouched
L.execute('CALLS.clearAllWeaponParts = 0; local it = instanceItem("Base.Hammer"); BP = SolKitBare.beforeParts(it, { type = "Base.Hammer", weaponParts = {} })')
ck("an item without saved parts that is not EFZ: untouched", L.eval('BP == 0 and CALLS.clearAllWeaponParts == 0'))
ck("pruning: a part on a path whose parent is gone comes off", L.eval('''(function()
    local w = instanceItem("EscapeFromZomboidFirearms.M4A1"); w:clearAllWeaponParts()
    local p = instanceItem("EscapeFromZomboidFirearms.P_57dbb57e2459774673234890"); p:getModData().TWPath = "mod_reciever/mod_barrel/mod_muzzle/mod_muzzle"
    w:attachWeaponPart(p, false); local d = SolKitBare.prune(w); return #d == 1 and #w.list == 0 end)()'''))
G = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua")
r = subprocess.run([sys.executable, "-I", os.path.join(G, "tonumber_check.py"), cl], capture_output=True, text=True); ck("tonumber gate", r.returncode == 0, r.stdout[-300:])
r = subprocess.run([sys.executable, "-I", os.path.join(G, "jarcall_check.py"), cl], capture_output=True, text=True); ck("jarcall gate", r.returncode == 0, r.stdout[-400:])
print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(P), len(FAIL))); sys.exit(1 if FAIL else 0)
