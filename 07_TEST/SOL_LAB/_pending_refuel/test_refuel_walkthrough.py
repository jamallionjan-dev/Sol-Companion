"""The whole refuel errand: the real goal engine talking through the real mailbox to the real SolFuel.lua on a mocked game.
Living Fellows' follow logic is modelled by the one rule that bit us: with the player in a car and nothing holding her out, she is seated again."""
import os, re, sys, tempfile, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind")
import goal_engine as GE, intent_engine as IE
from kahlua_env import lua51
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
src = open(os.path.join(HERE, "test_fuel_lua.py"), encoding="utf-8").read()
WORLD = src.split('WORLD = r"""', 1)[1].split('"""', 1)[0]
LAYOUT = r"""
HERX, HERY = 7320.5, 8180.5
function SOL.getX() return HERX end; function SOL.getY() return HERY end
INCAR = true
SOL.getVehicle = function() if INCAR then return CAR end return nil end
AREA = { getX = function() return 7309.4 end, getY = function() return 8177.3 end }; CAR.getAreaCenter = function() return AREA end
BLOCK = {}
function block(x0, y0, x1, y1) for x = x0, x1 do for y = y0, y1 do BLOCK[x .. "," .. y] = true end end end
block(7306, 8175, 7309, 8178); block(7311, 8175, 7312, 8177); block(7306, 8174, 7306, 8174); block(7311, 8178, 7311, 8178)
CELL.getGridSquare = function(_, x, y, z) return { x = x, y = y, free = not BLOCK[x .. "," .. y], hasGridPower = function() return true end } end
SurvivorCompanion.GameplayUtil.isSquareFree = function(sq) return sq.free end
TRIED = {}
function SolUI.solGoto(x, y, z) TRIED[#TRIED + 1] = x .. "," .. y; GOTO = { x, y }; if WALK_REFUSED then return false, "invalid_destination" end return true, "walking_to" end
GOTOS, WALK_OK = 0, true
TOP = nil
"""
class Mind:
    def __init__(self):
        self.perception = {"sol": {"position": {"x": 7320, "y": 8180, "z": 0}, "currentVehicle": {"id": "car"}}, "player": {"position": {"x": 7320, "y": 8180, "z": 0}, "currentVehicle": None}, "threats": {"count": 0, "immediateCount": 0, "visible": []}}
        self.tools = []; self.said = []; self.results = {}
    def request_tool(self, t, a=None):
        rid = "r%d" % (len(self.tools) + 1); self.tools.append((t, a or {})); self.results[rid] = {"status": "accepted", "accepted": True}; return rid
    def say(self, t): self.said.append(t); return "s"
    def status(self, rid): return self.results.get(rid)
GE.SEND_WAIT = 0
_SEND = GE._write_request
CURRENT = [None]
def _send_after_the_game_read(path, fields):                                      # the real sender waits for the game to take the last request
    if CURRENT[0] is not None: CURRENT[0].game()
    return _SEND(path, fields)
GE._write_request = _send_after_the_game_read

class Run:
    def __init__(self, extra="", he_rides=False, tank=10):
        self.L = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.L.execute(WORLD); self.L.execute(open(os.path.join(HERE, "SolFuel.lua"), encoding="utf-8").read()); self.L.execute(LAYOUT)
        self.L.execute("TANK = %d; %s" % (tank, extra))
        self.g = self.L.globals()
        self.dir = tempfile.mkdtemp(prefix="sol_walk_")
        self.m = Mind()
        self.e = GE.GoalEngine(self.dir, self.m, threading.RLock(), log=lambda x: None)
        r = self.e.submit(IE.make_goal("refuel_errand", {"target": "car", "transport": "car"}, source="test")); assert r.get("ok"), r
        self.he_rides, self.acked, self.reseated, self.options, self.phases = he_rides, None, 0, [], []
        self.gps_reply = "arrived"
        CURRENT[0] = self
    def game(self):
        p = os.path.join(self.dir, "SolAct_Request.txt")
        if os.path.exists(p):
            kv = dict(l.split("=", 1) for l in open(p, encoding="ascii").read().splitlines() if "=" in l)
            if kv.get("id") != self.acked:
                self.acked = kv["id"]
                self.options.append(kv.get("option"))
                ok, reason = self.g.SolUI.solFuel(kv.get("option"))
                with open(os.path.join(self.dir, "SolAct_State.txt"), "w", encoding="ascii") as f: f.write("ack=%s\nok=%s\nreason=%s\n" % (kv["id"], "true" if ok else "false", reason))
        q = os.path.join(self.dir, "SolGPS_Request.txt")
        if os.path.exists(q) and self.e.active and self.e.active.get("gpsRid"):
            with open(os.path.join(self.dir, "SolGPS_State.txt"), "w", encoding="ascii") as f: f.write("ack=%s\nresult=%s\nphase=%s\ndistance=0\nreason=%s\n" % (self.e.active["gpsRid"], self.gps_reply, self.gps_reply, getattr(self, "gps_why", "")))
    def world(self):
        for t, a in self.m.tools:
            if t == "exit_vehicle" and not getattr(self, "out", False):
                self.out = True; self.L.execute("INCAR = false"); self.m.perception["sol"]["currentVehicle"] = None
        if self.he_rides and getattr(self, "out", False) and self.L.eval("INCAR") is False and self.e.active and self.e.active.get("phase") not in ("homeward", "driving_back") and self.g.SolUI.solFuelHeld() is not True:
            self.reseated += 1; self.L.execute("INCAR = true"); self.m.perception["sol"]["currentVehicle"] = {"id": "car"}
        if self.e.active and self.e.active.get("phase") in ("homeward", "driving_back"): self.m.perception["sol"]["currentVehicle"] = {"id": "car"}
    def step(self, n=1):
        for _ in range(n):
            a = self.e.active
            if not a or a.get("status") != "running": return
            self.world(); a["pollAt"] = 0
            self.g.NOW = self.g.NOW + 400; self.g.TICK()
            self.e.tick(); self.game(); self.e.tick(); self.game()
            ph = self.e.active.get("phase") if self.e.active else None
            if not self.phases or self.phases[-1] != ph: self.phases.append(ph)
    def until(self, phase, n=200):
        for _ in range(n):
            if self.e.active and self.e.active.get("phase") == phase: return True
            self.step()
        return False
    def said(self, w): return any(w in s for s in self.m.said)
    def kinds(self): return [self.g.QUEUED[i].kind for i in range(1, len(list(self.g.QUEUED.values())) + 1)]

r = Run()
ck("A reaches the station by the GPS", r.until("park_check"), r.phases)
ck("A the cap is by a pump: gets out", r.until("get_out"), r.phases)
ck("A held out of the car before she gets out", (r.step(), r.g.SolUI.solFuelHeld())[1] is True)
ck("A out of the car, goes to fill", r.until("pumping_car"), r.phases)
ck("A not in the car", r.L.eval("INCAR") is False)
r.step(3)
ck("A walks to a free square", len(list(r.g.TRIED.values())) >= 1 and all(not r.g.BLOCK[t] for t in r.g.TRIED.values()), list(r.g.TRIED.values()))
ck("A says nothing about filling on the way", not r.said("عم عبي"), r.m.said)
x, y = list(r.g.GOTO.values())
r.L.execute("HERX, HERY = %d + 0.5, %d + 0.5" % (x, y)); r.step(2)
ck("A the game's refuel action is queued", r.kinds() == ["refuel"], r.kinds())
r.step(3); ck("A only now says she is filling", sum("عم عبي السيارة" in s for s in r.m.said) == 1, r.m.said)
ck("A the car is off while pumping", r.g.ENGINE is False)
r.L.execute("LUAQUEUE.queue = {}; TANK = 55"); r.step(12)
ck("A tank full: heads back", r.e.active["phase"] in ("homeward", "driving_back") or r.e.active["status"] == "completed", (r.e.active["phase"], r.e.active["status"], r.phases))
s = open(os.path.join(r.dir, "SolGPS_Request.txt"), encoding="ascii").read()
ck("A drives back herself, in the same car", "car=last" in s, s)
r.step(40); ck("A trip completes", r.e.active["status"] == "completed", (r.e.active["status"], r.e.active.get("reason"), r.phases))
ck("A no complaint anywhere", not r.said("ما ") or not any(w in " ".join(r.m.said) for w in ("ما لقيت", "ما قدرت")), r.m.said)

r = Run(he_rides=True)
r.until("pumping_car"); r.step(30)
ck("B he sits in the car: she is never seated back", r.reseated == 0 and r.L.eval("INCAR") is False, r.reseated)

r = Run('', he_rides=True); r.L.execute("HOLD_BROKEN = true")
r.g.SolUI.solFuelHeld = r.L.eval("function() return false end")
r.until("get_out"); r.step(8)
ck("B2 (the model of the bug) without the hold she is seated at once", r.reseated > 0, r.reseated)

r = Run(); r.until("pumping_car"); r.L.execute("HERX, HERY = 7310.5, 8177.5"); r.step(4)
ck("C standing within reach: the action starts without walking anywhere near", r.kinds() == ["refuel"], (r.kinds(), list(r.g.TRIED.values())))

r = Run("WALK_REFUSED = true"); r.until("pumping_car"); r.step(120)
ck("D every square refused: says it, only then", r.e.active["status"] == "failed" and r.said("ما لقيت طريق") and len(set(r.g.TRIED.values())) >= 2, (r.e.active["status"], r.m.said, len(set(r.g.TRIED.values()))))
ck("D never claimed to be filling", not r.said("عم عبي"), r.m.said)

r = Run(tank=55); r.until("homeward", 80)
ck("E tank already full: no pump, goes back", r.e.active["phase"] in ("homeward", "driving_back") and r.kinds() == [] and not r.said("عم عبي"), (r.e.active["phase"], r.kinds(), r.m.said))

r = Run("PUMP_FAR = true"); r.until("park_check"); r.step(6)
ck("F the cap is not by a pump: she draws a stop, she does not get out", r.e.active["phase"] in ("parking", "parking_wait") and "park" in r.options and not r.m.tools, (r.e.active["phase"], r.options, r.m.tools))

r = Run(); r.m.perception["sol"]["position"] = {"x": 6000, "y": 6000, "z": 0}; r.gps_reply = "failed"; r.gps_why = "survival_priority"; r.until("driving_out"); r.step(4)
ck("G danger stops the drive: she says so, no pumping", r.e.active["status"] == "failed" and len(r.m.said) >= 2 and r.kinds() == [], (r.e.active["status"], r.e.active.get("reason"), r.m.said))
r = Run(); r.m.perception["sol"]["position"] = {"x": 6000, "y": 6000, "z": 0}; r.gps_reply = "failed"; r.gps_why = "no_way_round"; r.until("driving_out"); r.step(4)
ck("H no way through: she says exactly that", r.e.active["status"] == "failed" and r.said("ما لقيت طريق من هون"), (r.e.active["status"], r.m.said))
r = Run(); r.gps_reply = "stopped"; r.gps_why = "player_order"; r.until("driving_out"); r.step(4)
ck("I he stops her: ended without a complaint", r.e.active["reason"] == "player_took_over" and not any("ما لقيت" in s or "ما قدرت" in s for s in r.m.said), (r.e.active.get("reason"), r.m.said))
r = Run("POWER = false"); r.L.execute("CELL.getGridSquare = (function(old) return function(a, x, y, z) local s = old(a, x, y, z); s.hasGridPower = function() return false end; return s end end)(CELL.getGridSquare)"); r.until("get_out"); r.step(20)
ck("J the power went off after arriving: says so", r.e.active["status"] == "failed" and r.said("الكهربا"), (r.e.active["status"], r.m.said))
r = Run(); r.until("pumping_car"); r.step(2); r.e.cancel(reason="player_order:follow"); r.game()
ck("K he calls it off mid-walk: the job ends in the game", r.g.SolUI.solFuelHeld() is False and "cancel" in r.options, (r.options, r.g.SolUI.solFuelHeld()))
r = Run("WALK_REFUSED = true"); r.until("pumping_car"); r.step(120); r.game()
ck("L a failure after getting out: she is sent to follow", any(t == "follow" for t, _ in r.m.tools) and r.g.SolUI.solFuelHeld() is False, (r.m.tools, r.g.SolUI.solFuelHeld()))
r = Run(); r.until("resolve", 1); r.step(); rid = r.e.active.get("findRid")
open(os.path.join(r.dir, "SolAct_State.txt"), "w", encoding="ascii").write("ack=999\nok=true\nreason=other\nr%s=true|station:7316,8178,92,gas2go,240,1,216,-100\n" % rid)
import goal_engine as _G
ck("M another sender's answer on top does not lose ours", _G.GoalEngine and (lambda p: (p.goal.update({"k": rid}), _G.RefuelErrand._action_result(p, "k"))[1])(type("X", (), {"goal": {}, "e": r.e, "ACT_STATE": "SolAct_State.txt"})())[0] is True)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
