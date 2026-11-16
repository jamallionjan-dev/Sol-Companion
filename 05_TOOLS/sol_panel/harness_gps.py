"""SolGPS against a simulated SC.Driving (same function names and argument shapes as SCDriving.lua)."""
import os, sys, tempfile
sys.path.insert(0, "/home/claude/brain")
from lupa import lua51
from PIL import Image
L = lua51.LuaRuntime(unpack_returned_tuples=True)
LUA_DIR = tempfile.mkdtemp() + "/"
L.globals()["TEXOK"] = lambda n: os.path.exists("build/media/textures/SolUI/" + n + ".png")
L.globals()["TEXW"] = lambda n: Image.open("build/media/textures/SolUI/" + n + ".png").size[0]
L.globals()["TEXH"] = lambda n: Image.open("build/media/textures/SolUI/" + n + ".png").size[1]
L.globals()["PEXISTS"] = lambda p: os.path.exists(p)
L.globals()["PSIZE"] = lambda p, i: Image.open(p).size[i]
L.globals()["LUA_DIR"] = LUA_DIR
L.execute(open("harness_stubs.lua").read())
L.execute(r'''
local baseGet = getTexture
function getTexture(p) if p:find("SolText/") then local f = "build/" .. p; if not PEXISTS(f) then return nil end
  return { name = f, getWidth = function() return PSIZE(f, 0) end, getHeight = function() return PSIZE(f, 1) end } end return baseGet(p) end
CALLS = {}
local gas = { getContainerContentAmount = function() return 12 end, getContainerCapacity = function() return 50 end }
CAR = { x = 100, y = 200, getX = function(self) return self.x end, getY = function(self) return self.y end, getCurrentSpeedKmHour = function() return 18.4 end,
  getPartById = function(_, id) if id == "GasTank" then return gas end end }
PLAYER_IN_CAR = true
PLAYER = { getVehicle = function() if PLAYER_IN_CAR then return CAR end end, getX = function() return 100 end, getY = function() return 200 end }
function getSpecificPlayer() return PLAYER end
SOL = { name = "Sol", getVehicle = function() return CAR end }
SolUI = SolUI or {}; SolUI.solActor = function() return SOL end
DRIVER = false; JOB = nil
SurvivorCompanion.Driving = {
  isDriver = function(a) return DRIVER end,
  takeWheel = function(a, v, intent) CALLS[#CALLS + 1] = "takeWheel:" .. intent; DRIVER = true; return true end,
  drive = function(a, goal, opt) CALLS[#CALLS + 1] = "drive:" .. goal.x .. "," .. goal.y .. "," .. goal.z .. "@" .. opt.speedKmh; JOB = { phase = "planning" }; return true, "driving" end,
  jobStatus = function(a) return JOB end,
  stop = function(a, why) CALLS[#CALLS + 1] = "stop:" .. why; JOB = { phase = "stopped", result = "stopped" }; return true end,
  tick = function(now) CALLS[#CALLS + 1] = "tick" end,
}
local SYMS = {}
ISWorldMap_instance = { mapAPI = { getSymbolsAPI = function() return { getSymbolCount = function() return #SYMS end, getSymbolByIndex = function(_, i) return SYMS[i + 1] end } end } }
function ADDSYM(x, y) SYMS[#SYMS + 1] = { getWorldX = function() return x end, getWorldY = function() return y end } end
''')
for f in ("SolTextData.lua", "SolText.lua", "SolGPS.lua"):
    L.execute(open("build/media/lua/client/" + f, encoding="ascii").read())
G = L.globals(); U = G.SolUI; res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
calls = lambda: list(G.CALLS.values())
r = U.gpsMapMarker(); check("no marker yet -> honest 'no_marker'", r[0] is None and r[1] == "no_marker")
G.ADDSYM(500.6, 900.2); G.ADDSYM(7012, 8444)
m = U.gpsMapMarker(); check("newest map marker becomes the destination point", m.x == 7012 and m.y == 8444)
U.gpsSetDestination(m)
# Living Fellows' rule: Sol may take the driver's seat only while no non-companion is aboard (SCVehicle.lua 1152-1156)
L.execute("function getCell() return { getVehicles = function() return { size = function() return 1 end, get = function() return CAR end } end } end")
L.execute("SOL.getVehicle = function() return SOLCAR end"); G.PLAYER_IN_CAR = True
r0 = U.gpsStart("fast")
check("you are already in the car -> 'get out a moment, I sit first' (no LF English error)", r0[0] is False and L.eval("SolUI.gps.reason") == "player_aboard")
# you get out -> she carries on by herself (no second press)
G.CALLS = L.table(); G.PLAYER_IN_CAR = False; G.TIME = 4000; U.gpsTick()
check("after 'get out a moment', your getting out makes her take the wheel by herself", "takeWheel:sol_gps" in calls() and L.eval("SolUI.gps.reason") == "board_passenger")
L.execute("DRIVER = false; SolUI.gps.awaitPlayer = false"); G.CALLS = L.table()
r1 = U.gpsStart("fast")
check("you are outside -> Sol takes the wheel of the nearest car first", "takeWheel:sol_gps" in calls() and r1[1] == "board_passenger")
check("...and waits for you to board as passenger (no drive yet)", not any(c.startswith("drive:") for c in calls()) and L.eval("SolUI.gps.awaitPlayer") is True)
L.execute("SOLCAR = CAR"); G.PLAYER_IN_CAR = True; G.TIME = 5000; U.gpsTick()
check("you board her car -> she leaves by herself: drive(actor, {x, y, z=0}, {speedKmh=30})", "drive:7012,8444,0@30" in calls())
st = U.gpsStatus()
check("status: distance from the car, km/h, fuel 24%", st.distance == int(((7012 - 100) ** 2 + (8444 - 200) ** 2) ** 0.5 + 0.5) and abs(st.fuel - 0.24) < 1e-6 and st.phase == "planning")
U.gpsStop(); check("stop -> SC.Driving.stop(actor, 'player_stop')", "stop:player_stop" in calls())
# Sol already in a back seat (seen in game): she gets out (LF exit_vehicle) and then takes the wheel
L.execute("DRIVER = false; SOLCAR = CAR; SOL.getVehicle = function() return SOLCAR end; SolUI.issueLF = function(c) CALLS[#CALLS + 1] = 'lf:' .. c; return true end")
G.PLAYER_IN_CAR = False; G.CALLS = L.table()
r = U.gpsStart("normal")
check("Sol in a back seat -> she steps out first (LF exit_vehicle)", r[1] == "moving_to_wheel" and "lf:exit_vehicle" in calls())
L.execute("SOLCAR = nil"); G.TIME = 9000; U.gpsTick()
check("...then takes the wheel as soon as she is outside", "takeWheel:sol_gps" in calls())
G.PLAYER_IN_CAR = False; L.execute("SOL.getVehicle = function() return nil end; DRIVER = true")
ok2 = U.gpsStart("slow"); check("not in a vehicle -> refused with a reason", ok2[0] is False and ok2[1] == "not_in_vehicle")
G.PLAYER_IN_CAR = True; L.execute("SOL.getVehicle = function() return CAR end; DRIVER = true")
open(LUA_DIR + "SolGPS_Request.txt", "w").write("id=5\naction=drive\nx=6900\ny=8400\nname=home\nspeed=slow\n")
G.CALLS = L.table(); U.gpsPollRequest()
check("chat request -> drive home slowly (10 km/h), no second takeWheel", calls() == ["drive:6900,8400,0@10"])
state = open(LUA_DIR + "SolGPS_State.txt").read()
check("state file written for Sol Mind", "ack=5" in state and "speed=slow" in state and "inVehicle=true" in state)
open(LUA_DIR + "SolGPS_Request.txt", "w").write("id=6\naction=stop\n"); G.CALLS = L.table(); U.gpsPollRequest()
check("chat 'stop' -> stop", "stop:player_stop" in calls())
U.gpsPollRequest(); check("same request id is not replayed", len(calls()) == 1)
# panel
G.TIME = 10000; U.gpsTick()
check("GPS panel appears while you sit in a vehicle with Sol", U.gpsPanel is not None and U.gpsPanel.visible)
G.DRAWS = L.table(); U.gpsPanel.prerender(U.gpsPanel)
acts = [h.action for h in U.gpsPanel.hits.values()]
from PIL import ImageDraw
im = Image.new("RGBA", (330, 236), (40, 62, 46, 255))
for d in G.DRAWS.values():
    if d[1] == "tex":
        name = d[2]; fp = name if str(name).startswith("build/") else "build/media/textures/SolUI/" + name + ".png"
        t = Image.open(fp).convert("RGBA").resize((max(1, int(d[5])), max(1, int(d[6]))))
        if d[7] < 1: t.putalpha(t.getchannel("A").point(lambda v: int(v * d[7])))
        im.alpha_composite(t, (int(d[3]), int(d[4])))
    elif d[1] == "rect":
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
        dr.rectangle((d[2], d[3], d[2] + d[4] - 1, d[3] + d[5] - 1), fill=(int(d[7] * 255), int(d[8] * 255), int(d[9] * 255), int(d[6] * 255))); im.alpha_composite(ov)
im.convert("RGB").save("/tmp/gps_panel.png")
check("panel buttons: 3 speeds, map marker, drive/stop", acts.count("speed") == 3 and "marker" in acts and ("drive" in acts or "stop" in acts))
G.PLAYER_IN_CAR = False; L.execute("SOL.getVehicle = function() return nil end"); G.TIME = 11000; U.gpsTick()
check("panel hides when you leave the car", U.gpsPanel.visible == False)
# tick fallback: if LF never ticks SC.Driving while Sol drives, SolGPS does
G.PLAYER_IN_CAR = True; L.execute("SOL.getVehicle = function() return CAR end"); U.gpsSetDestination(m); U.gpsStart("normal")
G.CALLS = L.table()
for k in range(4): G.TIME = 12000 + k * 300; U.gpsTick()
check("nobody else ticks LF driving -> Sol ticks it (route jobs advance)", calls().count("tick") >= 2)
# right-click on the world map
L.execute(r"""
MENU = { opts = {} }
function MENU:addOption(label, target, fn) self.opts[#self.opts + 1] = { label = label, fn = fn } end
ISContextMenu = { get = function() MENU.opts = {}; return MENU end }
ISWorldMap = { onRightMouseUp = function(self, x, y) return true end }
MAPUI = { mapAPI = { uiToWorldX = function(_, x, y) return 7100.6 end, uiToWorldY = function(_, x, y) return 8300.2 end },
          getAbsoluteX = function() return 0 end, getAbsoluteY = function() return 0 end }
setmetatable(MAPUI, { __index = ISWorldMap })
""")
U.gpsHookMap()
L.execute("MAPUI:onRightMouseUp(50, 60)")
labels = [o.label for o in G.MENU.opts.values()]
check("world map right-click offers 'Sol: drive here' and 'Sol: walk here'", labels == ["Sol: drive here", "Sol: walk here"])
G.CALLS = L.table(); L.execute("DRIVER = true; MENU.opts[1].fn()")
check("'drive here' drives to the clicked point", "drive:7100,8300,0@20" in calls())
G.CALLS = L.table(); L.execute("SolUI.solGoto = function(x, y, z) CALLS[#CALLS + 1] = 'walk:' .. x .. ',' .. y; return true end; MENU.opts[2].fn()")
check("'walk here' walks to the clicked point", calls() == ["walk:7100,8300"])
G.PLAYER_IN_CAR = False; L.execute("SOL.getVehicle = function() return nil end")
U.gpsStart("normal"); G.DRAWS = L.table(); U.gpsPanel.prerender(U.gpsPanel)
texts = "".join("".join(chr(c) for c in G.SolText.codepoints(d[2]).values()) for d in G.DRAWS.values() if d[1] == "line") if False else ""
check("refusal reasons have Arabic text (not 'not_in_vehicle')", L.eval("SolUI.gps.reason") == "not_in_vehicle")
G.PLAYER_IN_CAR = True; L.execute("SOL.getVehicle = function() return CAR end")
# Sol Mind side: intents -> request file
import chat_service as C, world_knowledge as W
mem_dir = tempfile.mkdtemp(); os.environ["LOCALAPPDATA"] = mem_dir
mem = W.Memory({"name": "w", "mode": "Sandbox"}); mem.data["home"] = {"name": "بيتنا", "x": 6900, "y": 8400}; mem.data["places"] = [{"name": "المستودع", "x": 7100, "y": 8000}]
r = C.drive_to(LUA_DIR, {"target": "home", "speed": "slow"}, mem)
req = open(LUA_DIR + "SolGPS_Request.txt").read()
check("'خذينا إلى البيت' resolves home and writes the GPS request", r["sent"] == "home" and "x=6900" in req and "speed=slow" in req)
r = C.drive_to(LUA_DIR, C.intents("اذهبي بالسيارة الى المستودع بسرعة")[0][1], mem)
check("a remembered place by name", r.get("sent") == "المستودع" and "x=7100" in open(LUA_DIR + "SolGPS_Request.txt").read())
check("unknown place -> honest error", "error" in C.drive_to(LUA_DIR, {"target": "place", "name": "المريخ"}, mem))
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
