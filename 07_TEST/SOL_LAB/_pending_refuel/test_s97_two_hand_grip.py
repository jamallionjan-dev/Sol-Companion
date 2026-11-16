"""s97 two_hand_grip offline: installer idempotent; the patched SCNativeActions.equip (cut from the real file) puts a rifle in
both hands when the OnEquipPrimary listener throws after the set (live 10:36:48); switch off = old early return; SCCombat's
"already equipped" mends a one-handed rifle; SolTwoHandGrip.grip / tick mend primary-only and secondary-only, skip while busy,
leave one-handed items and a pistol+torch alone. Run: python test_s97_two_hand_grip.py [client dir]. Offline PASS is not Runtime PASS."""
import os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
tmp = tempfile.mkdtemp(prefix="s97_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
for f in ("SCNativeActions.lua", "SCCombat.lua", "SolAuthority.lua"): shutil.copy(os.path.join(CL, f), cl)
r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s97_two_hand_grip.py"), cl], capture_output=True, text=True)
ck("installer runs", r.returncode == 0 and r.stdout.count("edited") == 4, r.stdout + r.stderr)
r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s97_two_hand_grip.py"), cl], capture_output=True, text=True)
ck("second run changes nothing", r.returncode == 0 and "edited" not in r.stdout, r.stdout + r.stderr)
NA = open(os.path.join(cl, "SCNativeActions.lua"), encoding="utf-8", newline="").read()
CB = open(os.path.join(cl, "SCCombat.lua"), encoding="utf-8", newline="").read()
GR = open(os.path.join(cl, "SolTwoHandGrip.lua"), encoding="utf-8", newline="").read()
ck("switch registered", '"two_hand_grip"' in open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read())
m = re.search(r"\nlocal function equip\(actor, intent, provider\)\r?\n.*?\r?\nend\r?\n", NA, re.S)
ck("equip() found in the patched file", m is not None)
EQUIP = m.group(0)

ENV = r"""
NOW = 10000
function getTimestampMs() return NOW end
LOGS = {}
function print(m) LOGS[#LOGS + 1] = tostring(m) end
SW = { two_hand_grip = true }
SolAuthority = { on = function(f) return SW[f] == true end }
THROW = { primary = false, secondary = false }
function Item(t, two, both) local o = { t = t, two = two, both = both }
    function o:getFullType() return self.t end
    function o:isTwoHandWeapon() return self.two == true end
    function o:isRequiresEquippedBothHands() return self.both == true end
    return o end
SOL = { p = nil, s = nil, resets = 0, acts = 0 }
function SOL:getPrimaryHandItem() return self.p end
function SOL:getSecondaryHandItem() return self.s end
function SOL:setPrimaryHandItem(i) self.p = i; if THROW.primary then error("NPE callFrame (OnEquipPrimary listener)") end end
function SOL:setSecondaryHandItem(i) self.s = i; if THROW.secondary then error("NPE callFrame (OnEquipSecondary listener)") end end
function SOL:resetEquippedHandsModels() self.resets = self.resets + 1 end
function SOL:getVehicle() return nil end
function SOL:getCharacterActions() local n = self.acts; return { isEmpty = function() return n == 0 end } end
QUEUE = {}
ISTimedActionQueue = { getTimedActionQueue = function(a) return { queue = QUEUE } end }
SolUI = { solActor = function() return SOL end }
Events = nil
"""
def fresh():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV); L.execute(GR)
    return L
def logs(L): s = L.eval("LOGS"); return [s[i] for i in range(1, len(s) + 1)]

# ---- the patched equip, with LF's invoke (SC.Call.method = pcall) and no provider
EQ = r"""
local function invoke(object, name, ...) local f = object[name]; if f == nil then return false, "no method" end; return pcall(f, object, ...) end
local function useProvider() return nil end
""" + EQUIP + "\nEQUIP = equip\n"
L = fresh(); L.execute(EQ)
L.execute("M4 = Item('EscapeFromZomboidFirearms.M4A1', true, true); THROW.primary = true")
ok, why = L.eval("EQUIP(SOL, { item = M4 }, { directNative = true })")
ck("live replay: listener throws in setPrimaryHandItem -> equip goes on, both hands", ok is True and L.eval("SOL.p == M4 and SOL.s == M4"), (ok, why))
ck("it says so in the log", any("an equip listener threw" in x for x in logs(L)), logs(L))
L = fresh(); L.execute(EQ)
L.execute("M4 = Item('M4', true, true); THROW.primary = true; THROW.secondary = true")
ok, why = L.eval("EQUIP(SOL, { item = M4 }, { directNative = true })")
ck("both listeners throw -> still both hands", ok is True and L.eval("SOL.p == M4 and SOL.s == M4"), (ok, why))
L = fresh(); L.execute(EQ)
L.execute("SW.two_hand_grip = false; M4 = Item('M4', true, true); THROW.primary = true")
ok, why = L.eval("EQUIP(SOL, { item = M4 }, { directNative = true })")
ck("switch off: the old early return (primary only, as live)", ok is False and L.eval("SOL.p == M4 and SOL.s == nil"), (ok, why))
L = fresh(); L.execute(EQ)
L.execute("KN = Item('Base.KitchenKnife', false, false); TORCH = Item('Base.Torch', false, false); SOL.s = TORCH; THROW.primary = true")
ok, why = L.eval("EQUIP(SOL, { item = KN }, { directNative = true })")
ck("one-handed item with a throwing listener: primary only, torch kept", ok is True and L.eval("SOL.p == KN and SOL.s == TORCH"), (ok, why))
L = fresh(); L.execute(EQ)
L.execute("DUMMY = Item('X', false, false); SOL.setPrimaryHandItem = function(self, i) error('refused') end")
ok, why = L.eval("EQUIP(SOL, { item = DUMMY }, { directNative = true })")
ck("a real refusal (item not in hand) still fails", ok is False and L.eval("SOL.p == nil"), (ok, why))

# ---- SCCombat 'already equipped'
ck("SCCombat already-equipped calls grip", 'pcall(G_.grip, actor, "already_equipped", true)' in CB)

# ---- grip / tick
L = fresh()
L.execute("M4 = Item('M4', true, true); SOL.p = M4; SOL.s = nil")
L.execute("NOW = NOW + 2500; SolTwoHandGrip.tick()")
ck("tick mends primary-only rifle", L.eval("SOL.p == M4 and SOL.s == M4 and SOL.resets == 1"), logs(L))
L.execute("NOW = NOW + 2500; SolTwoHandGrip.tick()")
ck("then quiet (no second log, no reset)", L.eval("SOL.resets") == 1 and sum("both hands" in x for x in logs(L)) == 1, logs(L))
L = fresh()
L.execute("M4 = Item('M4', true, false); SOL.p = nil; SOL.s = M4; THROW.primary = true; THROW.secondary = true")
L.execute("NOW = NOW + 2500; SolTwoHandGrip.tick()")
ck("secondary-only rifle, throwing listeners: both hands", L.eval("SOL.p == M4 and SOL.s == M4"), logs(L))
L = fresh()
L.execute("M4 = Item('M4', true, true); SOL.p = M4; SOL.s = nil; QUEUE[1] = {}")
L.execute("NOW = NOW + 2500; SolTwoHandGrip.tick()")
ck("busy in a timed action: left alone", L.eval("SOL.s == nil"))
ok = L.eval("SolTwoHandGrip.grip(SOL, 'combat', true)")[0]
ck("force (combat path) mends even while busy", ok is True and L.eval("SOL.s == M4"))
L = fresh()
L.execute("M4 = Item('M4', true, true); SOL.p = M4; SOL.s = nil; SW.two_hand_grip = false")
L.execute("NOW = NOW + 2500; SolTwoHandGrip.tick()")
ck("switch off: tick does nothing", L.eval("SOL.s == nil"))
L = fresh()
L.execute("PI = Item('Base.Pistol', false, false); TORCH = Item('Base.Torch', false, false); SOL.p = PI; SOL.s = TORCH")
L.execute("NOW = NOW + 2500; SolTwoHandGrip.tick()")
ck("pistol + torch untouched", L.eval("SOL.p == PI and SOL.s == TORCH"))
L = fresh()
L.execute("AXE = Item('Base.Axe', true, false); TORCH = Item('Base.Torch', false, false); SOL.p = AXE; SOL.s = TORCH")
L.execute("NOW = NOW + 2500; SolTwoHandGrip.tick()")
ck("two-handed axe with a torch in the off hand: both hands on the axe (as vanilla equip)", L.eval("SOL.p == AXE and SOL.s == AXE"))
L = fresh()
L.execute("M4 = Item('M4', true, true); SOL.p = M4; SOL.s = nil; SOL.setSecondaryHandItem = function(self, i) error('refused') end")
L.execute("NOW = NOW + 2500; SolTwoHandGrip.tick(); NOW = NOW + 2500; SolTwoHandGrip.tick()")
ck("cannot set: one log line, no spam", sum("could not put both hands" in x for x in logs(L)) == 1, logs(L))

for nm, src in (("SolTwoHandGrip.lua", GR), ("SCNativeActions.lua", NA), ("SCCombat.lua", CB)):
    ck("ascii only " + nm, all(ord(c) < 128 for c in src))
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
if os.path.exists(GATE):
    for nm in ("SolTwoHandGrip.lua", "SCNativeActions.lua", "SCCombat.lua"):
        r = subprocess.run([sys.executable, GATE, os.path.join(cl, nm)], capture_output=True, text=True)
        ck("tonumber gate " + nm, r.returncode == 0, r.stdout[-300:])
else:
    ck("tonumber gate present", False, GATE)
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
