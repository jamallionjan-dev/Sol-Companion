"""Which keys let her drive, and that she never drops her things. The code is cut from patched copies of the real files."""
import os, shutil, subprocess, sys, tempfile
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
BK = os.path.join(HERE, "..", "_backup", "20261109_043225_night_before_apply", "Sol_LAB", "42", "media", "lua", "client")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
d = tempfile.mkdtemp(prefix="sol_keys_")
for n in ("SolGPS.lua", "SCDriving.lua", "SCLogistics.lua", "SolActions.lua"): shutil.copy(os.path.join(BK, n), d)
subprocess.check_call([sys.executable, os.path.join(HERE, "apply_s36_lua.py"), os.path.join(d, "SolGPS.lua"), os.path.join(d, "SCDriving.lua")], stdout=subprocess.DEVNULL)
subprocess.check_call([sys.executable, os.path.join(HERE, "apply_s37_lua.py"), os.path.join(d, "SCLogistics.lua"), os.path.join(d, "SolActions.lua")], stdout=subprocess.DEVNULL)
read = lambda n: open(os.path.join(d, n), encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
for n in ("SolGPS.lua", "SCDriving.lua", "SCLogistics.lua", "SolActions.lua"):
    ck("compiles: " + n, not isinstance(lua51.LuaRuntime().globals().loadstring(read(n)), tuple))
s = read("SCDriving.lua")
def cut(start):
    a = s.index(start); return s[a:s.index("\nend\n", a) + 5]
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(r"""
print = function() end
function method(o, name, ...) if o == nil or o[name] == nil then return false, nil end return true, o[name](o, ...) end
Driving = {}
function vehicleOf() return CAR end
function bag(items)
    local b = { items = items }
    b.getItems = function() return { size = function() return #b.items end, get = function(_, i) return b.items[i + 1] end } end
    b.haveThisKeyId = function(_, id) for _, it in ipairs(b.items) do if it.keyId == id then return it end end return nil end
    b.Remove = function(_, it) for i, x in ipairs(b.items) do if x == it then table.remove(b.items, i); return end end end
    b.AddItem = function(_, it) b.items[#b.items + 1] = it end
    return b
end
function car(opts)
    local parts = {}
    for _, box in ipairs(opts.boxes or {}) do parts[#parts + 1] = { getItemContainer = function() return box end } end
    return { getKeyId = function() return 7 end, isKeysInIgnition = function() return opts.ignition == true end, isHotwired = function() return opts.wired == true end,
             getPartCount = function() return #parts end, getPartByIndex = function(_, i) return parts[i + 1] end }
end
function actor(items) local inv = bag(items); return { getInventory = function() return inv end } end
function key(id) return { keyId = id } end
function pack(items) local inv = bag(items); return { getInventory = function() return inv end } end
""")
L.execute(cut("local function keyInBags(container, keyId, depth)").replace("local function keyInBags", "function keyInBags", 1))
L.execute(cut("local function takeKeyFromCar(actor, vehicle)").replace("local function takeKeyFromCar", "function takeKeyFromCar", 1))
L.execute(cut("function Driving.hasKey(actor, vehicle)"))
g = L.globals()
def run(code): return L.eval("(function() " + code + " end)()")
ck("key in her pocket", run("CAR = car({}); return Driving.hasKey(actor({ key(7) }), CAR)") is True)
ck("no key at all", run("CAR = car({}); return Driving.hasKey(actor({ key(9) }), CAR)") is False)
ck("hotwired", run("CAR = car({ wired = true }); return Driving.hasKey(actor({}), CAR)") is True)
ck("key in the ignition", run("CAR = car({ ignition = true }); return Driving.hasKey(actor({}), CAR)") is True)
ck("key in a bag she carries", run("CAR = car({}); A = actor({ pack({ key(7) }) }); return takeKeyFromCar(A, CAR) == true and Driving.hasKey(A, CAR) == true") is True)
ck("key in a bag inside a bag", run("CAR = car({}); A = actor({ pack({ pack({ key(7) }) }) }); return takeKeyFromCar(A, CAR) == true and Driving.hasKey(A, CAR) == true") is True)
ck("someone else's key in the bag stays", run("CAR = car({}); A = actor({ pack({ key(9) }) }); return takeKeyFromCar(A, CAR)") is False)
ck("key in the glove box", run("B = bag({ key(7) }); CAR = car({ boxes = { B } }); A = actor({}); local ok = takeKeyFromCar(A, CAR); return ok == true and #B.items == 0 and Driving.hasKey(A, CAR) == true") is True)
l = read("SCLogistics.lua")
a = l.index("-- Sol empties her bag"); b = l.index('kind = "drop", item = state.item', a)
ck("she never drops: her check comes before the drop", 'return false, "sol_keeps_her_things"' in l[a:b] and "SolUI.solActor() == actor" in l[a:b])
ck("the engine action uses her bag too", "bringKeyToHand" in read("SolActions.lua"))
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
