"""s83 veh_shoot_seated: the client file under the game's Lua rules (set / clear of the one animation variable, Sol and KI5 cars left
alone, switch off clears it, throttle), the aim node against every aim node the game and the active mods ship for player-vehicle
(read only: it must outrank all of them, use only AnimNode fields the game parses, and play a clip the game has), the tonumber gate,
and the installer (idempotent, on a temporary copy). Nothing live is touched.
Run: set PYTHONIOENCODING=utf-8 & python test_s83_veh_shoot_seated.py [client dir]
Offline PASS is not Runtime PASS: the seated look itself needs one look in game."""
import os, re, shutil, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media"
WS = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\108600"
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
SRC = open(os.path.join(HERE, "SolVehShootSeated.lua"), encoding="ascii").read()

# ================================================================ Lua
ENV = r"""
NOW = 1000
function getTimestampMs() return NOW end
SETS, CLEARS, LOGS = {}, {}, {}
local _print = print
function print(m) LOGS[#LOGS + 1] = m end
SWITCH = true
SolAuthority = { on = function(f) if f ~= "veh_shoot_seated" then error("wrong switch " .. tostring(f)) end; return SWITCH end }
function mkveh(script) return { getScript = function(self) return { getFullName = function(s) return script end } end } end
function mkplayer(name)
    local p = { name = name, vars = {}, veh = nil, dead = false }
    function p:getVehicle() return self.veh end
    function p:isDead() return self.dead end
    function p:setVariable(k, v) self.vars[k] = v; SETS[#SETS + 1] = self.name .. ":" .. k .. "=" .. tostring(v) end
    function p:clearVariable(k) self.vars[k] = nil; CLEARS[#CLEARS + 1] = self.name .. ":" .. k end
    function p:getVariableString(k) local v = self.vars[k]; if v == nil then return "" end; return tostring(v) end
    return p
end
PLAYERS = { [0] = mkplayer("jamal") }
NUM = 1
function getSpecificPlayer(i) return PLAYERS[i] end
function getNumActivePlayers() return NUM end
HOOKS = {}
Events = { OnTick = { Add = function(f) HOOKS[#HOOKS + 1] = f end } }
SolUI = { solActor = function() return SOL end }
"""
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(ENV)
L.execute(SRC)
g = L.globals()
M = g.SolVehShootSeated
ck("lua: loads, one OnTick hook", len(list(g.HOOKS.values())) == 1 and M.VERSION == "0.1.0")
L.execute(SRC)
ck("lua: loading twice keeps one hook", len(list(g.HOOKS.values())) == 1)
J = g.PLAYERS[0]

def tick(step=150):
    g.NOW = g.NOW + step
    M.tick()

tick()
ck("on foot: nothing set", len(list(g.SETS.values())) == 0 and J.vars["SolSeatAim"] is None)
L.execute('PLAYERS[0].veh = mkveh("Base.Van_Blacksmith")')
tick()
ck("vanilla van: SolSeatAim=true once", list(g.SETS.values()) == ["jamal:SolSeatAim=true"] and J.vars["SolSeatAim"] is True)
tick(); tick()
ck("still seated: not set again", len(list(g.SETS.values())) == 1)
g.NOW = g.NOW + 10
L.execute('PLAYERS[0].veh = nil')
M.tick()
ck("throttle: a tick within 100 ms does nothing", J.vars["SolSeatAim"] is True)
tick()
ck("left the car: cleared", list(g.CLEARS.values()) == ["jamal:SolSeatAim"] and J.vars["SolSeatAim"] is None)
L.execute('PLAYERS[0].veh = mkveh("Base.Van_Blacksmith")'); tick()
ck("back in: set again", J.vars["SolSeatAim"] is True)
g.SWITCH = False; tick()
ck("switch off: cleared", J.vars["SolSeatAim"] is None and len(list(g.CLEARS.values())) == 2)
g.SWITCH = True; tick()
ck("switch on: set", J.vars["SolSeatAim"] is True)
L.execute('PLAYERS[0].dead = true'); tick()
ck("dead: cleared", J.vars["SolSeatAim"] is None)
L.execute('PLAYERS[0].dead = false'); tick()
# KI5 by the DAMN API
L.execute('DAMN = { vehicleIsManaged = function(self, n) return n == "Base.KI5Truck" end }')
L.execute('PLAYERS[0].veh = mkveh("Base.KI5Truck")'); tick()
ck("KI5 car (DAMN api): left to damnlib, cleared", J.vars["SolSeatAim"] is None)
L.execute('DAMN = nil; PLAYERS[0].vars.damnVehicle = "True"'); tick()
ck("KI5 car (damnVehicle=True): still left alone", J.vars["SolSeatAim"] is None)
L.execute('PLAYERS[0].vars.damnVehicle = nil'); tick()
ck("vanilla again: set", J.vars["SolSeatAim"] is True)
L.execute('DAMN = { vehicleIsManaged = function(self, n) error("boom") end }'); tick()
ck("a throwing DAMN api is survived (falls back to the variable)", J.vars["SolSeatAim"] is True)
L.execute('DAMN = nil')
# Sol is never touched
L.execute('SOL = PLAYERS[0]'); tick()
ck("the Sol actor is never given the variable", J.vars["SolSeatAim"] is None)
L.execute('SOL = mkplayer("sol"); SOL.veh = mkveh("Base.Van_Blacksmith")'); tick()
ck("only local human players are looked at", J.vars["SolSeatAim"] is True and not any("sol:" in s for s in g.SETS.values()))
# split screen and a vanished player
L.execute('PLAYERS[1] = mkplayer("p2"); PLAYERS[1].veh = mkveh("Base.CarNormal"); NUM = 2'); tick()
ck("second local player gets it too", g.PLAYERS[1].vars["SolSeatAim"] is True)
L.execute('PLAYERS[1] = nil; NUM = 1'); tick()
ck("a vanished player's slot is released", M.set[1] is None)
# a player object without the methods (a Java error) does not stop the tick
L.execute('PLAYERS[0] = { getVehicle = function() error("java") end }'); tick()
ck("a throwing getVehicle is survived", True)
ck("every write is setVariable/clearVariable of SolSeatAim only",
   all(s.split(":")[1].startswith("SolSeatAim") for s in list(g.SETS.values()) + list(g.CLEARS.values())))
ck("logs are tagged", all(str(m).startswith("[SolVehShootSeated]") for m in g.LOGS.values()))
ck("lua: no game call outside the guarded helper", not re.search(r"\bpl:[a-zA-Z]+\(", SRC) and not re.search(r"\bveh:[a-zA-Z]+\(", SRC))

# ================================================================ the aim node
ANIMNODE_FIELDS = set("m_2DBlendTri m_2DBlends m_AlternateAnims m_AnimName m_AnimReverse m_BlendCurve m_BlendOutTime m_BlendTime "
    "m_ConditionPriority m_Conditions m_DeferredBoneName m_EarlyTransitionOut m_Events m_GrappleOffsetForward m_GrappleOffsetYaw "
    "m_GrappleTweenInTime m_GrapplerOffsetBehaviour m_Looped m_MatchingGrappledAnimNode m_Name m_Priority m_Scalar m_Scalar2 "
    "m_SpeedScale m_SpeedScaleRandomMultiplierMax m_SpeedScaleRandomMultiplierMin m_SpeedScaleVariable m_StopAnimOnExit "
    "m_SubStateBoneWeights m_SyncTrackingEnabled m_TrackTimeToVariable m_Transitions m_chanceToRagdoll m_deferredBoneAxis "
    "m_deferredRotationScale m_isRagdoll m_maxTorsoTwist m_ragdollMaxTime m_ragdollStartTimeMax m_ragdollStartTimeMin "
    "m_randomAdvanceFraction m_useDeferedRotation m_useDeferredMovement".split())   # javap -v AnimNode.class, 42.22.2


def rank(path):
    t = open(path, encoding="utf-8-sig").read()
    r = ET.fromstring(t)
    cp = r.findtext("m_ConditionPriority")
    return (int(cp) if cp else 0, len(r.findall("m_Conditions"))), r


ours_rank, node = rank(os.path.join(HERE, "SolSeatAim.xml"))
ck("node: only AnimNode fields the game parses", all(c.tag in ANIMNODE_FIELDS for c in node), [c.tag for c in node if c.tag not in ANIMNODE_FIELDS])
ck("node: one BOOL condition SolSeatAim == true",
   [(c.findtext("m_Name"), c.findtext("m_Type"), c.findtext("m_Value")) for c in node.findall("m_Conditions")] == [("SolSeatAim", "BOOL", "true")])
ck("node: plays the clip vanilla's seated idle plays",
   node.findtext("m_AnimName") == ET.parse(os.path.join(GAME, "AnimSets", "player-vehicle", "idle", "default.xml")).getroot().findtext("m_AnimName") == "Bob_IdleDriving")
ck("node: the clip exists in the game", os.path.isfile(os.path.join(GAME, "anims_X", "Bob", "Bob_IdleDriving.x")))
others = []
for base in [os.path.join(GAME, "AnimSets", "player-vehicle", "aim")] + [
        os.path.join(WS, wid, "mods", m, sub, "media", "AnimSets", "player-vehicle", "aim")
        for wid, m in (("3171167894", "damnlib"), ("3824755284", "EscapeFromZomboidFirearms"), ("3722064198", "Gunworks_gang_framework"),
                       ("3809306528", "Viewpoint"), ("3812612054", "ProjectViewpointADS"), ("3817413313", "ImmersiveDriving"))
        for sub in ("", "common", "42", "42.13", "42.17", "42.20")]:
    if os.path.isdir(base):
        for f in os.listdir(base):
            if f.endswith(".xml"):
                try: others.append((f, rank(os.path.join(base, f))[0]))
                except ET.ParseError: pass
ck("node: outranks every aim node the game and the checked mods ship (%d)" % len(others),
   len(others) >= 13 and all(ours_rank > r for f, r in others), [o for o in others if not ours_rank > o[1]])

# ================================================================ gates
ck("ascii", all(ord(ch) < 128 for ch in SRC) and all(ord(ch) < 128 for ch in open(os.path.join(HERE, "SolSeatAim.xml"), encoding="utf-8").read()))
e = lua51.LuaRuntime().eval("function(s) local f, e = loadstring(s); return e end")(SRC)
ck("lua: compiles", e is None, e)
gr = subprocess.run([sys.executable, GATE, os.path.join(HERE, "SolVehShootSeated.lua")], capture_output=True, text=True, encoding="utf-8", errors="replace")
ck("tonumber gate clean", gr.returncode == 0, gr.stdout + gr.stderr)

# ================================================================ installer on a temporary copy
tmp = tempfile.mkdtemp(prefix="sol_s83_")
try:
    tcl = os.path.join(tmp, "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
    os.makedirs(tcl)
    os.makedirs(os.path.join(tmp, "Zomboid", "Lua"))
    for n in ("SolAuthority.lua", "SolActions.lua"): shutil.copy(os.path.join(CL, n), tcl)
    fx = os.path.join(tmp, "Zomboid", "Lua", "SolFixes_LAB.txt")
    open(fx, "w", encoding="utf-8", newline="").write("horn_hold=on")
    run = lambda: subprocess.run([sys.executable, os.path.join(HERE, "apply_s83_veh_shoot_seated.py"), tcl], capture_output=True, text=True, encoding="utf-8", errors="replace")
    r1 = run()
    ck("installer: first run", r1.returncode == 0 and "s83_veh_shoot_seated applied" in r1.stdout, r1.stdout + r1.stderr)
    xmlp = os.path.join(tmp, "Zomboid", "mods", "Sol_LAB", "42", "media", "AnimSets", "player-vehicle", "aim", "SolSeatAim.xml")
    ck("installer: node placed under media/AnimSets/player-vehicle/aim", os.path.isfile(xmlp))
    ck("installer: lua placed", open(os.path.join(tcl, "SolVehShootSeated.lua"), encoding="ascii").read() == SRC)
    au = open(os.path.join(tcl, "SolAuthority.lua"), encoding="utf-8").read()
    ck("installer: switch registered once", au.count('"veh_shoot_seated"') == 1)
    ck("installer: switch file gets veh_shoot_seated=on on its own line", open(fx, encoding="utf-8").read().splitlines() == ["horn_hold=on", "veh_shoot_seated=on"])
    snap = {p: open(p, "rb").read() for p in (xmlp, os.path.join(tcl, "SolAuthority.lua"), os.path.join(tcl, "SolVehShootSeated.lua"), fx)}
    r2 = run()
    ck("installer: second run changes nothing", r2.returncode == 0 and all(open(p, "rb").read() == b for p, b in snap.items()) and "kept" in r2.stdout, r2.stdout)
    ck("installer: refuses a non-client dir", subprocess.run([sys.executable, os.path.join(HERE, "apply_s83_veh_shoot_seated.py"), tmp], capture_output=True).returncode != 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d FAIL" % len(FAIL) if FAIL else "\nALL PASS (offline; the seated look needs one look in game)")
sys.exit(1 if FAIL else 0)
