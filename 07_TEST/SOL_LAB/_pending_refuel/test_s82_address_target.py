"""s82 address_target + preview_calm, offline: both installers on copies (idempotent, switch file), SolAddressTarget.lua under the
game's Lua rules (kahlua_env) with the lab's own SolStaticRoads.lua + SolStaticRoadsData.lua (read only), the game's
PrintMediaDefinitions.lua + Print_Text.json (read only) and a metagrid stub built from the gazetteer's building boxes; then the
go / status / panel / speech wrappers with stubs, and the tonumber gate. Offline PASS is not Runtime PASS.
Run: set PYTHONIOENCODING=utf-8 & python test_s82_address_target.py"""
import gzip, hashlib, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, HERE)
from kahlua_env import lua51
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LAB_CL = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media\lua"
GATE = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "tonumber_check.py")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def read(p): return open(p, encoding="utf-8", newline="").read()
def run(*a): return subprocess.run([sys.executable] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
def digest(d, names): return {n: hashlib.md5(open(os.path.join(d, n), "rb").read()).hexdigest() for n in names if os.path.exists(os.path.join(d, n))}

# ---------------------------------------------------------------- 1. installers on copies
r = run(os.path.join(HERE, "apply_s82_address_target.py"), "--gen")
ck("generator runs; module is ASCII", r.returncode == 0 and all(ord(c) < 128 for c in read(os.path.join(HERE, "SolAddressTarget.lua"))), r.stderr[-300:])
T = tempfile.mkdtemp(prefix="sol_s82t_")
ZB = os.path.join(T, "Zomboid"); CL = os.path.join(ZB, "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(CL); os.makedirs(os.path.join(ZB, "Lua"))
FIXF = os.path.join(ZB, "Lua", "SolFixes_LAB.txt")
open(FIXF, "w", encoding="utf-8", newline="").write("address_book=on\r\nmodel_first=on")
FILES = ["SolAuthority.lua", "SolAddressBook.lua", "SolGPS.lua"]
live = digest(LAB_CL, FILES + ["SolAddressTarget.lua"])
for f in FILES: shutil.copy(os.path.join(LAB_CL, f), CL)
q1 = run(os.path.join(HERE, "apply_s82_address_target.py"), CL); a1 = digest(CL, FILES + ["SolAddressTarget.lua"]); f1 = read(FIXF)
p1 = run(os.path.join(HERE, "apply_s82_preview_calm.py"), CL); b1 = digest(CL, FILES); g1 = read(FIXF)
q2 = run(os.path.join(HERE, "apply_s82_address_target.py"), CL); p2 = run(os.path.join(HERE, "apply_s82_preview_calm.py"), CL)
ck("address_target installer applies", q1.returncode == 0 and "applied" in q1.stdout, q1.stderr[-400:])
ck("preview_calm installer applies", p1.returncode == 0 and "applied" in p1.stdout, p1.stderr[-400:])
ck("both idempotent", q2.returncode == 0 and p2.returncode == 0 and digest(CL, FILES + ["SolAddressTarget.lua"]) == dict(b1, **{"SolAddressTarget.lua": a1["SolAddressTarget.lua"]}) and read(FIXF) == g1, (q2.stderr[-300:], p2.stderr[-300:]))
ck("switch file: both on once, own lines", g1 == "address_book=on\r\nmodel_first=on\r\naddress_target=on\r\npreview_calm=on\r\n", repr(g1))
auth = read(os.path.join(CL, "SolAuthority.lua"))
ck("A.FIXES: address_target and preview_calm once each", auth.count('"address_target"') == 1 and auth.count('"preview_calm"') == 1)
ck("address_target edits no other file", digest(CL, ["SolAddressBook.lua"]) == digest(LAB_CL, ["SolAddressBook.lua"]))
gps = read(os.path.join(CL, "SolGPS.lua"))
ck("SolGPS: preview gap 12 s only while moving, the 4 s line kept", "t - P.at < 4000 then return end" in gps and "t - P.at < 12000" in gps and '"getCurrentSpeedKmHour"' in gps)
ck("SolGPS: gps_preview and drive_tick timers", '"gps_preview"' in gps and '"drive_tick"' in gps)
lr = lua51.LuaRuntime()
ck("SolGPS.lua still compiles", lr.eval("loadstring")(gps.replace("\r\n", "\n"))[0] is not None if isinstance(lr.eval("loadstring")(gps), tuple) else True)
ck("live lab files untouched", digest(LAB_CL, FILES + ["SolAddressTarget.lua"]) == live)
g = run(GATE, os.path.join(HERE, "SolAddressTarget.lua"))
ck("tonumber gate: SolAddressTarget.lua", g.returncode == 0, g.stdout[-400:])
g = run(GATE, os.path.join(CL, "SolGPS.lua"))
ck("tonumber gate: patched SolGPS.lua", g.returncode == 0, g.stdout[-400:])

# ---------------------------------------------------------------- 2. the target, real road graph, real flyers
gz = json.load(gzip.open(os.path.join(ROOT, "05_TOOLS", "sol_mind", "gazetteer.json.gz"), "rt", encoding="utf-8"))
blds = [b for b in gz["buildings"] if gz["kinds"][b[4]] != "farmland"]
defs = open(os.path.join(GAME, "shared", "PrintMedia", "PrintMediaDefinitions.lua"), encoding="utf-8").read()
texts = json.load(open(os.path.join(GAME, "shared", "Translate", "EN", "Print_Text.json"), encoding="utf-8"))
flyers = []
for m in re.finditer(r"(houseforsale\d+|premisesforlease\d+|premiseswithapartmentsforleaselistingno\d+)\s*=\s*\{\s*location1\s*=\s*\{\s*\{\s*x1\s*=\s*(\d+),\s*y1\s*=\s*(\d+),\s*x2\s*=\s*(\d+),\s*y2\s*=\s*(\d+)", defs.replace(" ", " ")):
    fid, x1, y1, x2, y2 = m.group(1), *map(int, m.groups()[1:])
    txt = next((v for k, v in texts.items() if k.lower() == ("print_text_%s_info" % fid).lower()), "")
    last = [l.strip() for l in txt.replace("\\n", "\n").split("\n") if ", KY" in l]
    name = re.sub(r",\s*KY.*$", "", last[-1]) if last else fid
    flyers.append({"id": fid, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "name": name})
ck("game data: the flyers with a place (house for sale / lease)", len(flyers) >= 15 and any(f["id"] == "houseforsale903" for f in flyers), len(flyers))

L = lua51.LuaRuntime()
L.execute("SW = { address_target = true }; SolAuthority = { on = function(n) return SW[n] == true end }")
L.execute("BL = {}")
add = L.eval("function(i, a, b, c, d) BL[i] = { a, b, c, d } end")
for i, b in enumerate(blds, 1): add(i, b[0], b[1], b[2], b[3])
L.execute(r'''
NOW = 0
function getTimestampMs() return NOW end
METAGRID = true
local function def(b) local o = { b = b }
  function o:getX() return self.b[1] end function o:getY() return self.b[2] end function o:getX2() return self.b[3] end function o:getY2() return self.b[4] end
  return o end
local GRID = { calls = 0 }
function GRID:getBuildingAt(x, y)
  self.calls = self.calls + 1
  for i = 1, #BL do local b = BL[i]; if x >= b[1] and x <= b[3] and y >= b[2] and y <= b[4] then return def(b) end end
  return nil end
function getWorld() return { getMetaGrid = function(self) if METAGRID then return GRID end return nil end } end
SAID, LOGS = {}, {}
local rawprint = print
function print(s) LOGS[#LOGS + 1] = tostring(s) end
''')
for f in ("SolStaticRoadsData.lua", "SolStaticRoads.lua"): L.execute(read(os.path.join(LAB_CL, f)))
L.execute(read(os.path.join(HERE, "SolAddressTarget.lua")))
M = L.globals().SolAddressTarget
sk = L.eval("function(s) return SolAddressTarget.streetKey(s) end")
for a, b in (("625 Dewey Street, Muldraugh", "dewey st"), ("Dewey St", "dewey st"), ("12 Arkansas Avenue, X", "arkansas ave"), ("Arkansas Av", "arkansas ave"),
             ("7 Adam Road", "adam rd"), ("Abraham Lane", "abraham ln"), ("1st St", "1st st")):
    ck("streetKey('%s') = '%s'" % (a, b), sk(a) == b, sk(a))
tgt = L.eval("function(k, x, y, name, x1, y1, x2, y2) local t = SolAddressTarget.target({ key = k, kind = 'house', x = x, y = y, name = name, x1 = x1, y1 = y1, x2 = x2, y2 = y2 }); if not t then return nil end return t.x, t.y, t.street, t.how, t.house.how, t.house.x1, t.house.y1, t.house.x2, t.house.y2 end")
x, y, st, how, fh, hx1, hy1, hx2, hy2 = tgt("house:10840,10120", 10840, 10120, "625 Dewey Street, Muldraugh", 10816, 10096, 10863, 10143)
ck("625 Dewey Street: the house is the building at the flyer's centre (10836..10846 x 10108..10123)", fh == "building" and (hx1, hy1, hx2, hy2) == (10836, 10108, 10846, 10123), (fh, hx1, hy1, hx2, hy2))
ck("625 Dewey Street: target on Dewey St, in front of the house (x 10856-10857, y within the house)", st == "Dewey St" and how == "named_street" and 10855 <= x <= 10858 and 10108 <= y <= 10123, (x, y, st, how))
ck("  ... not on S Main St (where the car stopped, behind the garden)", st != "S Main St")
L.execute("METAGRID = false; SolAddressTarget.cache = {}")
x2_, y2_, st2, how2, fh2 = tgt("house:10840,10120", 10840, 10120, "625 Dewey Street, Muldraugh", 10816, 10096, 10863, 10143)[:5]
ck("no metagrid: the lot box, still Dewey St", fh2 == "lot" and st2 == "Dewey St" and 10855 <= x2_ <= 10858, (x2_, y2_, st2, fh2))
L.execute("METAGRID = true; SolAddressTarget.cache = {}")
named = 0
for f in flyers:
    cx, cy = (f["x1"] + f["x2"]) / 2.0, (f["y1"] + f["y2"]) / 2.0
    res = tgt(f["id"], int(cx + 0.5), int(cy + 0.5), f["name"], f["x1"], f["y1"], f["x2"], f["y2"])
    if not res: print("     ", f["id"], f["name"], "-> no road"); continue
    tx, ty, tst, thow = res[:4]
    named += thow == "named_street"
    print("      %-44s %-34s -> %s %s at %d,%d" % (f["id"], f["name"][:34], thow, tst, tx, ty))
ck("most flyers: the target is on the street their address names (%d of %d)" % (named, len(flyers)), named >= len(flyers) * 0.6)

# ---------------------------------------------------------------- 3. wrappers
L.execute(r'''
SolUI = { gps = { dest = nil } }
local U = SolUI
GO = {}
SolAddressBook = { go = function(e) GO[#GO + 1] = { e.x, e.y, e.name }; return true, "driving", "line" end }
ST = { result = "arrived", reason = "arrived", distance = 15 }
function U.gpsStatus() local t = {}; for k, v in pairs(ST) do t[k] = v end; return t end
function U.gpsPollRequest() U.gps.dest = { x = 1, y = 2, name = "mind" }; return true end
SolGPSWords = { TONE = { wait = { 1, 1, 0 } }, panelLine = function() return "orig" end }
CAR = { x = 10825, y = 10121 }
function CAR:getX() return self.x end function CAR:getY() return self.y end
SOL = { getVehicle = function() return CAR end }
function U.solActor() return SOL end
SurvivorCompanion = { GameplayUtil = { say = function(a, line) SAID[#SAID + 1] = line end } }
NAV = "idle"; solNavState = function() return NAV end
SolAddressTarget.wrap()
''')
L.execute("SolAddressTarget.cache = {}; E = { key = 'house:10840,10120', kind = 'house', x = 10840, y = 10120, name = '625 Dewey Street, Muldraugh', x1 = 10816, y1 = 10096, x2 = 10863, y2 = 10143 }")
L.execute("SolAddressBook.go(E)")
go = L.eval("GO[1]")
ck("go: the GPS gets the road point (Dewey St, y in the house)", 10855 <= go[1] <= 10858 and 10108 <= go[2] <= 10123 and go[3] == "625 Dewey Street, Muldraugh", (go[1], go[2], go[3]))
ck("go: the book's entry is not changed", L.eval("E.x == 10840 and E.y == 10120"))
L.execute("SW.address_target = false; SolAddressBook.go(E); SW.address_target = true")
ck("go, switch off: the entry's own point, as before", L.eval("GO[2][1] == 10840 and GO[2][2] == 10120"))
L.execute("SolUI.gps.dest = { x = 10840, y = 10120, name = 'x' }")
stat = L.eval("function() local s = SolUI.gpsStatus(); return s.result, s.reason, s.gap end")
ck("status: arrived 15 tiles from the marker -> arrived / road_end, gap 15", tuple(stat()) == ("arrived", "road_end", 15), stat())
L.execute("ST.distance = 4")
ck("status: 4 tiles -> arrived / arrived", tuple(stat())[:2] == ("arrived", "arrived"), stat())
L.execute("ST.distance = 15; SW.address_target = false")
ck("status: switch off -> arrived / arrived", tuple(stat())[:2] == ("arrived", "arrived"))
L.execute("SW.address_target = true; SolUI.gpsPollRequest()")
ck("status: a destination the Mind sent keeps arrived / arrived", tuple(stat())[:2] == ("arrived", "arrived"), stat())
L.execute("SolUI.gps.dest = { x = 10840, y = 10120, name = 'x' }")
ck("status: a new destination from the panel / book -> road_end again", stat()[1] == "road_end")
ck("status: interrupted and failed untouched", L.eval("(function() ST.result = 'failed'; ST.reason = 'x'; local s = SolUI.gpsStatus(); ST.result, ST.reason = 'arrived', 'arrived'; return s.reason == 'x' end)()"))
pl = L.eval("function(drv) return SolGPSWords.panelLine({ result = 'arrived', reason = 'road_end', gap = 15 }, {}, {}, nil, drv, false, true, 'x') end")
line = pl(False)[0]
ck("panel: road_end -> 'end of the road, N m' (escaped Arabic, no code)", isinstance(line, str) and "15" in line and "\\u0622\\u062E\\u0631" in line and "road_end" not in line, line)
ck("panel: other states go to the original", L.eval("SolGPSWords.panelLine({ result = 'driving' }, {}, {}, nil, true, false, true, 'x')") == "orig")
# speech: once, after SAY_MS still, not while an off-road leg runs
L.execute("SolUI.gps.dest = { x = 10840, y = 10120, name = '625 Dewey Street, Muldraugh' }; NOW = 100000; SolAddressTarget.tick()")
L.execute("NAV = 'planning'; for i = 1, 40 do NOW = NOW + 500; SolAddressTarget.tick() end")
ck("speech: nothing while SolNavLeg is planning the off-road leg", L.eval("#SAID") == 0)
L.execute("NAV = 'failed:no_corridor_wide_enough'; for i = 1, 20 do NOW = NOW + 500; SolAddressTarget.tick() end")
ck("speech: nothing before 15 s still", L.eval("#SAID") == 0)
L.execute("for i = 1, 30 do NOW = NOW + 500; SolAddressTarget.tick() end")
said = L.eval("SAID[1]")
ck("speech: once after 15 s still, with the place and the distance", L.eval("#SAID") == 1 and "625 Dewey Street" in str(said) and "15" in str(said) and "\\u0648\\u0642\\u0641\\u062A" in str(said), said)
L.execute("for i = 1, 60 do NOW = NOW + 500; SolAddressTarget.tick() end")
ck("speech: not again for the same destination", L.eval("#SAID") == 1)
L.execute("SAID = {}; SolUI.gps.dest = { x = 500, y = 500, name = 'Map point' }; for i = 1, 40 do NOW = NOW + 500; SolAddressTarget.tick() end")
ck("speech: a bare map point is 'the marker'", L.eval("#SAID") == 1 and "\\u0627\\u0644\\u0639\\u0644\\u0627\\u0645\\u0629" in str(L.eval("SAID[1]")), L.eval("SAID[1]"))
print("RESULT", "ALL PASS" if not FAIL else "%d FAILED: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
