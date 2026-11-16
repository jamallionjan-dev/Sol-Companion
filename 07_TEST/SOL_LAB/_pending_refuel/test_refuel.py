"""Refuel: order wording, the planner step by step, and that nothing Sol says is technical."""
import os, shutil, sys, tempfile, threading, time
M = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind"
sys.path.insert(0, M)
import intent_engine as IE
import goal_engine as GE
from goal_engine import GoalEngine
import chat_service as CS

FAIL = []
def ck(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ((" -- " + str(detail)) if not cond and detail != "" else ""))
    if not cond: FAIL.append(name)

def intent(text):
    g = IE.parse_high_confidence(text)
    return (g or {}).get("intent"), (g or {}).get("slots") or {}

for text, target, transport in [
    ("سول روحي عبي السيارة بنزين", "car", "car"), ("عبيلي السيارة", "car", "car"), ("روحي عبي البنزين", "car", "car"), ("عبّي الفان بنزين وارجعي", "car", "car"),
    ("سول عبي بدونات البنزين من الكازية", "can", "car"), ("عبي بدونة البنزين من الكازية", "can", "car"),
    ("عبي السيارة والغالون", "both", "car"), ("عبي الغالون مع السيارة", "both", "car"), ("روحي عبي الغالون", "can", "car"),
    ("روحي مشي عبي الغالون", "can", "foot"), ("عبي الغلون بدون سيارة وارجعي", "can", "foot"), ("امشي عالكازية وعبي البنزين", "can", "foot"),
    ("املي السيارة بنزين", "car", "car"),
]:
    i, s = intent(text)
    ck("order: " + text, i == "refuel_errand" and s.get("target") == target and s.get("transport") == transport, (i, s))
for text in ["وين اقرب كازية؟", "سول وين في كازية", "بتعرفي كازية قريبة", "شو اقرب محطة بنزين", "where is the nearest gas station"]:
    ck("question: " + text, intent(text)[0] == "station_query", intent(text))
for text, target in [("روحي عالمظخة من جهة المضخة حاولي", "car"), ("روحي عالمضخة", "car"), ("حاولي مرة تانية من المضخة", "car"), ("كملي عالمظخة", "car")]:
    i, s = intent(text)
    ck("retry at the pump: " + text, i == "refuel_errand" and s.get("target") == target, (i, s))
for text in ["وين المضخة", "المضخة حلوة"]:
    ck("not an order: " + text, intent(text)[0] != "refuel_errand", intent(text))
for text in ["عبي السيارة اغراض", "شو في بنزين بالسيارة", "الكازية حلوة", "سول تعالي هنا", "صعبي الموضوع", "ماشي عبي السيارة"]:
    i, s = intent(text)
    want = "refuel_errand" if text.startswith("ماشي") else None
    ck("not misread: " + text, i == want and s.get("transport", "car") == "car", (i, s))
ck("every goal has a planner", all(i in GE.PLANNERS for i in IE.SUPPORTED), IE.SUPPORTED)
ck("the model is told about both", "refuel_errand" in IE.capabilities_text() and "station_query" in IE.capabilities_text())
import model_router as MR
ck("the model card covers fuel cans at a station", "البدونات من الكازية" in MR.COMMANDS["refuel_at_station"][0] and any(x[0] == "سول عبي بدونات البنزين من الكازية" and x[1] == "refuel_at_station" for x in MR.EXAMPLES_S90))
ck("provider target allows car", "car" in IE.provider_tool()["function"]["parameters"]["properties"]["target"]["enum"])
ck("bridge tag, positional foot", IE.make_goal("refuel_errand", {"target": "can", "extract": "foot"})["slots"] == {"target": "can", "transport": "foot"})
ck("bridge defaults are safe", IE.make_goal("refuel_errand", {"target": "player", "extract": "home_if_known"})["slots"] == {"target": "car", "transport": "car"})

class Mind:
    def __init__(self):
        self.perception = {"sol": {"position": {"x": 0, "y": 0, "z": 0}, "currentVehicle": None}, "player": {"position": {"x": 100, "y": 100, "z": 0}}, "threats": {"count": 0, "immediateCount": 0, "visible": []}}
        self.tools = []; self.said = []; self.results = {}
    def request_tool(self, t, a=None):
        rid = "r%d" % (len(self.tools) + 1); self.tools.append((t, a or {})); self.results[rid] = {"status": "queued"}; return rid
    def say(self, t): self.said.append(t); return "s"
    def status(self, rid): return self.results.get(rid)
    def finish(self, rid): self.results[rid] = {"status": "accepted", "accepted": True}

scratch = tempfile.mkdtemp(prefix="sol_refuel_")
lock = threading.RLock()
def fresh(intent_, slots):
    m = Mind(); e = GoalEngine(scratch, m, lock, log=lambda x: None)
    r = e.submit(IE.make_goal(intent_, slots, source="test")); assert r.get("ok"), r
    return m, e
def req(name): return open(os.path.join(scratch, name), encoding="ascii").read()
def answer(e, key, ok, reason):
    with open(os.path.join(scratch, "SolAct_State.txt"), "w", encoding="ascii") as f: f.write("ack=%s\nok=%s\nreason=%s\n" % (e.active[key], "true" if ok else "false", reason))
def gps(e, result="arrived"):
    with open(os.path.join(scratch, "SolGPS_State.txt"), "w", encoding="ascii") as f: f.write("ack=%s\nresult=%s\nphase=%s\ndistance=0\n" % (e.active["gpsRid"], result, result))
ST = "station:7316,8178,92,gas2go,240,1,216,-100"
NOPOWER = "station:7316,8178,92,gas2go,240,0,216,-100"
ALLSAID = []
def done(m): ALLSAID.extend(m.said)

# the question
m, e = fresh("station_query", {}); e.tick()
ck("Q asks the game to mark", "sol_fuel" in req("SolAct_Request.txt") and "option=mark" in req("SolAct_Request.txt"))
answer(e, "markRid", True, ST); e.tick()
ck("Q answered and finished", e.active["status"] == "completed" and e.active["reason"] == "station_marked", e.active)
ck("Q says name, distance, side and GPS", any("غاز تو غو" in s and "240" in s and "GPS" in s and "الشرق" in s for s in m.said), m.said); done(m)
ck("Q does not drive", not os.path.exists(os.path.join(scratch, "SolGPS_Request.txt")))
m, e = fresh("station_query", {}); e.tick(); answer(e, "markRid", False, "no_station_known"); e.tick()
ck("Q knows none: says so, no failure", e.active["status"] == "completed" and any("كازية" in s for s in m.said), m.said); done(m)
m, e = fresh("station_query", {}); e.tick(); answer(e, "markRid", True, NOPOWER); e.tick()
ck("Q warns about power", any("الكهربا" in s for s in m.said), m.said); done(m)
m, e = fresh("station_query", {}); e.tick(); e.active["phaseSince"] = time.time() - 30; e.tick()
ck("Q unanswered ends", e.active["status"] == "failed", e.active); done(m)

# measuring by road takes a few frames
m, e = fresh("station_query", {}); e.tick(); answer(e, "markRid", True, "ranking"); e.tick()
ck("Q measuring: keeps asking", e.active["status"] == "running" and e.active.get("markOption") == "rank" and not m.said, e.active)
e.tick(); ck("Q asks how the measuring goes", "option=rank" in req("SolAct_Request.txt"))
answer(e, "markRid", True, ST); e.tick(); ck("Q then answers", e.active["status"] == "completed" and any("GPS" in s for s in m.said), e.active); done(m)
m, e = fresh("refuel_errand", {"target": "car", "transport": "car"}); e.tick(); answer(e, "findRid", True, "ranking"); e.tick()
ck("R measuring: does not fail or leave", e.active["status"] == "running" and e.active.get("findOption") == "rank", e.active)
e.tick(); answer(e, "findRid", True, ST); e.tick(); ck("R then sets off", e.active["phase"] == "leave", e.active); done(m)
m, e = fresh("station_query", {}); e.tick(); answer(e, "markRid", True, "ranking"); e.tick(); e.active["phaseSince"] = time.time() - 30; e.tick(); e.tick()
ck("Q measuring never ends: gives up aloud", e.active["status"] == "failed" and m.said, e.active); done(m)

# how many she remembers
for text in ["كم كازية انتي حافظة مكانها", "قديش كازية بتعرفي", "كم محطة بنزين حافظة"]:
    i, s = intent(text); ck("about her memory: " + text, i == "station_query" and s.get("ask") == "count", (i, s))
ck("about the map, not her: not this", intent("كم كازية في بالخريطة")[1].get("ask") != "count", intent("كم كازية في بالخريطة"))
for reason, want in [("count:0:", "ولا كازية"), ("count:1:gas2go", "وحدة"), ("count:2:gas2go,fossoil", "كازيتين"), ("count:5:gas2go,gas2go,fossoil,,", "5 كازيات")]:
    m, e = fresh("station_query", {"ask": "count"}); e.tick(); ck("asks to count", "option=count" in req("SolAct_Request.txt")); answer(e, "markRid", True, reason); e.tick()
    ck("says: " + want, e.active["status"] == "completed" and any(want in s for s in m.said), m.said); done(m)

# the answer is kept for the chat, where he asked
m, e = fresh("station_query", {}); gid = e.active["id"]; e.tick(); answer(e, "markRid", True, ST); e.tick()
got = e.wait_answer(gid, 0.5)
ck("Q the chat gets the same words as the bubble", got and got in m.said and "GPS" in got, got); done(m)
m, e = fresh("station_query", {}); gid = e.active["id"]; e.tick()
ck("Q still thinking: the chat is not left hanging", e.wait_answer(gid, 0.2) is None); done(m)
m, e = fresh("station_query", {}); gid = e.active["id"]; e.tick(); answer(e, "markRid", False, "no_station_known"); e.tick()
ck("Q none known: the chat says so", "كازية" in (e.wait_answer(gid, 0.2) or ""), e.active); done(m)

# the whole trip: car and can
m, e = fresh("refuel_errand", {"target": "both", "transport": "car"}); e.tick()
ck("R1 finds a station first", "option=find" in req("SolAct_Request.txt"))
answer(e, "findRid", True, ST); e.tick(); ck("R2 checks the can before leaving", e.active["phase"] == "check_can", e.active)
e.tick(); answer(e, "canRid", True, "can_ok"); e.tick(); ck("R3 leaves", e.active["phase"] == "leave", e.active)
e.tick(); r = req("SolGPS_Request.txt"); ck("R4 drives alone to the pump, shown on the GPS", "x=7316" in r and "y=8178" in r and "solo=1" in r and "Gas station gas2go" in r, r)
ck("R5 waiting for the drive", e.active["phase"] == "driving_out", e.active)
m.perception["sol"]["currentVehicle"] = {"id": "car"}; m.perception["sol"]["position"] = {"x": 7316, "y": 8180, "z": 0}
with open(os.path.join(scratch, "SolGPS_State.txt"), "w", encoding="ascii") as f: f.write("ack=%s\nresult=driving\nphase=following\ndistance=3\n" % e.active["gpsRid"])
e.tick(); ck("R5b close is not stopped: still driving", e.active["phase"] == "driving_out", e.active)
gps(e); e.tick(); ck("R6 stopped: is the cap within reach?", e.active["phase"] == "park_check", e.active)
e.tick(); ck("R6b asks the game's rule", "option=car_near" in req("SolAct_Request.txt")); answer(e, "parkRid", True, "near"); e.tick(); ck("R6c within reach", e.active["phase"] == "get_out", e.active)
e.tick(); ck("R7 gets out", any(t == "exit_vehicle" for t, _ in m.tools), m.tools)
ck("R8 no pumping while seated", e.active["phase"] == "get_out", e.active)
m.perception["sol"]["currentVehicle"] = None; e.tick(); ck("R9 at the car", e.active["phase"] == "pump_car", e.active)
e.tick(); ck("R10 asks to fill the car", "option=car" in req("SolAct_Request.txt"))
ck("R10b held out of the car before getting out", any(a == "sol_fuel" or "hold" in str(a) for a in [x[0] for x in getattr(m, "actions", [])]) or e.active.get("holdRid") is not None, e.active)
answer(e, "carRid", True, "walking"); e.tick(); ck("R11 walking to the cap", e.active["phase"] == "pumping_car", e.active)
ck("R11b says nothing about filling while she walks", not any("عم عبي" in s for s in m.said), m.said)
e.active["pollAt"] = 0; e.tick(); answer(e, "pollRid", True, "walking"); e.tick(); ck("R11c still walking: still silent", not any("عم عبي" in s for s in m.said) and e.active["phase"] == "pumping_car", m.said)
e.active["pollAt"] = 0; e.tick(); answer(e, "pollRid", True, "starting"); e.tick(); ck("R11d action being set up: still silent", not any("عم عبي" in s for s in m.said), m.said)
e.active["pollAt"] = 0; e.tick()
e.tick(); ck("R12 asks how it goes", e.active.get("pollRid") and "option=status" in req("SolAct_Request.txt"), e.active)
answer(e, "pollRid", True, "pumping"); e.tick(); ck("R13 keeps waiting while pumping", e.active["phase"] == "pumping_car", e.active)
ck("R13b only now says she is filling, once", sum("عم عبي السيارة" in s for s in m.said) == 1, m.said)
e.active["pollAt"] = 0; e.tick(); answer(e, "pollRid", True, "done:30"); e.tick(); ck("R14 then the can", e.active["phase"] == "pump_can", e.active)
e.tick(); ck("R15 asks to fill the can", "option=can" in req("SolAct_Request.txt"))
answer(e, "fillRid", True, "pumping"); e.tick(); e.active["pollAt"] = 0; e.tick(); answer(e, "pollRid", True, "done:9.5"); e.tick()
ck("R16 finished pumping", e.active["phase"] == "finish", e.active)
e.tick(); ck("R17 going back", e.active["phase"] == "homeward", e.active)
m.perception["sol"]["currentVehicle"] = {"id": "car"}; e.tick(); r = req("SolGPS_Request.txt"); ck("R18 back to the live player in the same car", "x=100" in r and "car=last" in r, r)
m.perception["sol"]["position"] = {"x": 100, "y": 100, "z": 0}; gps(e); e.tick(); m.finish(e.active["exitBackRid"]); e.tick()
ck("R19 trip completes", e.active["status"] == "completed", e.active)
ck("R20 follows again", any(t == "follow" for t, _ in m.tools), m.tools); done(m)
r = req("SolAct_Request.txt"); ck("R21 takes its own target off the GPS, and only its own", "action=sol_gps_clear" in r and "option=errand" in r, r)

# on foot
m, e = fresh("refuel_errand", {"target": "can", "transport": "foot"}); e.tick(); answer(e, "findRid", True, ST); e.tick(); e.tick(); answer(e, "canRid", True, "can_ok"); e.tick(); e.tick()
ck("F1 on foot does not drive", e.active["phase"] == "walk", e.active)
e.tick(); ck("F2 asks to walk", "option=walk" in req("SolAct_Request.txt")); answer(e, "walkRid", True, "walking_to 7316,8179"); e.tick(); ck("F3 walking", e.active["phase"] == "walking", e.active)
e.tick(); ck("F4 not yet there", e.active["phase"] == "walking", e.active)
m.perception["sol"]["position"] = {"x": 7316, "y": 8180, "z": 0}; e.tick(); ck("F5 there: fills the can", e.active["phase"] == "pump_can", e.active)
e.tick(); answer(e, "fillRid", True, "pumping"); e.tick(); e.active["pollAt"] = 0; e.tick(); answer(e, "pollRid", True, "done:9.5"); e.tick(); e.tick()
ck("F6 done on foot, follows", e.active["status"] == "completed" and any(t == "follow" for t, _ in m.tools), e.active); done(m)

# every refusal is spoken as a person would
def stops_at(name, slots, steps, key, reason, phrase=None):
    m, e = fresh("refuel_errand", slots)
    for f in steps: f(m, e)
    e.tick()
    if key: e.tick() if not e.active.get(key) else None; answer(e, key, False, reason); e.tick()
    ck("X " + name, e.active["status"] == "failed" and m.said and (phrase is None or any(phrase in s for s in m.said)), (e.active.get("status"), e.active.get("reason"), m.said)); done(m)
def s_find(m, e): e.tick(); answer(e, "findRid", True, ST); e.tick()
def s_leave(m, e): e.tick(); e.active["phase"] = "pump_car"; e.active["phaseSince"] = time.time()
CAR = {"target": "car", "transport": "car"}
stops_at("no station known", CAR, [], "findRid", "no_station_known", "كازية")
m, e = fresh("refuel_errand", CAR); e.tick(); answer(e, "findRid", True, NOPOWER); e.tick(); ck("X no power before leaving", e.active["status"] == "failed" and any("الكهربا" in s for s in m.said), m.said); done(m)
stops_at("no can, can only", {"target": "can", "transport": "car"}, [s_find], "canRid", "no_can", "غالون")
for why, word in [("no_car", "سيارة"), ("no_pump_near", "المضخة"), ("no_power", "الكهربا"), ("refuel_unavailable", "أعبي"), ("no_gas_tank", "السيارة")]:
    stops_at("at the pump: " + why, CAR, [s_leave], "carRid", why, word)
m, e = fresh("refuel_errand", {"target": "both", "transport": "car"}); e.tick(); answer(e, "findRid", True, ST); e.tick(); e.tick(); answer(e, "canRid", False, "no_can"); e.tick()
ck("X both without a can: fills the car only", e.active["slots"]["target"] == "car" and e.active["status"] == "running" and any("غالون" in s for s in m.said), e.active); done(m)
m, e = fresh("refuel_errand", {"target": "both", "transport": "car"}); e.tick(); answer(e, "findRid", True, ST); e.tick(); e.tick(); answer(e, "canRid", True, "can_ok"); e.tick(); e.tick(); gps(e, "failed")
with open(os.path.join(scratch, "SolGPS_State.txt"), "w", encoding="ascii") as f: f.write("ack=%s\nresult=failed\nreason=no_vehicle_near\n" % e.active["gpsRid"])
e.tick(); ck("X no car found: walks for the can", e.active["slots"] == {"target": "can", "transport": "foot"} and e.active["phase"] == "walk", e.active); done(m)
m, e = fresh("refuel_errand", CAR); e.tick(); answer(e, "findRid", True, ST); e.tick(); e.tick()
with open(os.path.join(scratch, "SolGPS_State.txt"), "w", encoding="ascii") as f: f.write("ack=%s\nresult=failed\nreason=no_vehicle_near\n" % e.active["gpsRid"])
e.tick(); ck("X car order, no car: fails aloud", e.active["status"] == "failed" and any("سيارة" in s for s in m.said), m.said); done(m)
m, e = fresh("refuel_errand", CAR); s_leave(m, e); e.tick(); answer(e, "carRid", True, "tank_full"); e.tick(); ck("X tank already full: goes back", e.active["phase"] == "finish", e.active); done(m)
m, e = fresh("refuel_errand", CAR); s_leave(m, e); e.tick(); answer(e, "carRid", True, "pumping"); e.tick(); e.active["phaseSince"] = time.time() - 900; e.active["pollAt"] = time.time(); e.tick(); ck("X pump never finishes", e.active["status"] == "failed", e.active); done(m)
m, e = fresh("refuel_errand", CAR); e.tick(); e.active["phaseSince"] = time.time() - 30; e.tick(); ck("X game never answers", e.active["status"] == "failed" and m.said, e.active); done(m)
m, e = fresh("refuel_errand", CAR); e.tick(); answer(e, "findRid", True, ST); e.tick(); e.tick()
with open(os.path.join(scratch, "SolGPS_State.txt"), "w", encoding="ascii") as f: f.write("ack=%s\nresult=stopped\nreason=player_stop\n" % e.active["gpsRid"])
e.tick(); ck("X he stops her: no complaint", e.active["status"] == "failed" and e.active["reason"] == "player_took_over" and not any("ما قدرت" in s for s in m.said), (e.active, m.said)); done(m)

# parked too far: she tries each side, then says so
m, e = fresh("refuel_errand", CAR); e.tick(); answer(e, "findRid", True, ST); e.tick(); e.tick()
seen = []
gps(e); e.tick(); ck("P first checks the reach", e.active["phase"] == "park_check", e.active)
for d in range(2):
    e.tick(); answer(e, "parkRid", False, "pump_too_far"); e.tick(); ck("D%d too far: draws a stop beside the pump" % d, e.active["phase"] == "parking", e.active)
    e.tick(); ck("D%d asks to park" % d, "option=park" in req("SolAct_Request.txt"))
    answer(e, "parkAskRid", True, "parking"); e.tick(); ck("D%d waiting for the car to park" % d, e.active["phase"] == "parking_wait", e.active)
    e.active["parkPollAt"] = 0; e.tick(); ck("D%d asks how it goes" % d, "option=park_status" in req("SolAct_Request.txt"))
    answer(e, "parkPollRid", True, "parking"); e.tick(); ck("D%d still parking" % d, e.active["phase"] == "parking_wait", e.active)
    e.active["parkPollAt"] = 0; e.tick(); answer(e, "parkPollRid", False, "pump_too_far"); e.tick(); ck("D%d failed: looks again" % d, e.active["phase"] == "park_check", e.active)
for i in range(4):
    if i:
        e.tick(); ck("P%d a fresh arrived is not trusted yet" % i, e.active["phase"] == "driving_out", e.active)
        e.active["phaseSince"] -= 5; gps(e); e.tick(); ck("P%d checks the reach" % i, e.active["phase"] == "park_check", e.active)
    e.tick(); answer(e, "parkRid", False, "pump_too_far"); e.tick()
    ck("P%d repositions" % i, e.active["phase"] == "driving_out" and e.active["status"] == "running", e.active)
    r = req("SolGPS_Request.txt"); seen.append(r.split("x=")[1].split("\n")[0] + "," + r.split("y=")[1].split("\n")[0])
    ck("P%d same car, slowly" % i, "car=last" in r and "speed=slow" in r, r)
ck("P all four sides differ", len(set(seen)) == 4, seen)
e.active["phaseSince"] -= 5; gps(e); e.tick(); e.tick(); answer(e, "parkRid", False, "pump_too_far"); e.tick()
ck("P after every side: says it plainly", e.active["status"] == "failed" and e.active["reason"] == "pump_too_far" and any("أصف" in s for s in m.said), (e.active, m.said)); done(m)
ck("P never got out to pump from afar", not any(t == "exit_vehicle" for t, _ in m.tools), m.tools)
m, e = fresh("refuel_errand", {"target": "can", "transport": "car"}); e.tick(); answer(e, "findRid", True, ST); e.tick(); e.tick(); answer(e, "canRid", True, "can_ok"); e.tick(); e.tick(); gps(e); e.tick()
ck("P a can alone does not need the car by the pump", e.active["phase"] == "get_out", e.active); done(m)
m, e = fresh("refuel_errand", CAR); e.tick(); answer(e, "findRid", True, ST); e.tick(); e.tick(); gps(e); e.tick(); e.tick(); answer(e, "parkRid", False, "pump_too_far"); e.tick(); e.tick(); answer(e, "parkAskRid", True, "parking"); e.tick(); e.active["parkPollAt"] = 0; e.tick(); answer(e, "parkPollRid", True, "parked"); e.tick()
ck("P parked: checks the game's own rule again", e.active["phase"] == "park_check", e.active)
e.tick(); answer(e, "parkRid", True, "near"); e.tick(); ck("P then gets out", e.active["phase"] == "get_out", e.active); done(m)
m, e = fresh("refuel_errand", CAR); e.tick(); answer(e, "findRid", True, ST); e.tick(); e.tick(); gps(e); e.tick(); e.tick(); answer(e, "parkRid", False, "pump_too_far"); e.tick(); e.tick(); answer(e, "parkAskRid", False, "park_unavailable"); e.tick()
ck("P no drawn-path parking: falls back to trying each side", e.active["phase"] == "park_check" and e.active["parkDrawn"] == 9, e.active); done(m)

# a spoken cancel
for text in ["الغي التحديد", "سول الغي الوجهة", "امسحي العلامة", "شيلي النقطة", "ألغي الهدف", "بطلي الوجهة"]:
    ck("cancel: " + text, CS.action_intents(text) == [("sol_gps_clear", None)], CS.action_intents(text))
for text in ["الغي الاوامر", "شيلي الاغراض", "الوجهة وين"]:
    ck("not a cancel: " + text, CS.action_intents(text) != [("sol_gps_clear", None)], CS.action_intents(text))
m, e = fresh("refuel_errand", CAR); e.tick(); answer(e, "findRid", False, "no_station_known"); e.tick()
r = req("SolAct_Request.txt"); ck("a failed errand clears only its own target too", "action=sol_gps_clear" in r and "option=errand" in r, r); done(m)

# asked again while she is still on it
class _G:
    def __init__(self): self.n, self.canc = 0, []
    def submit(self, g):
        self.n += 1; return {"ok": True, "goalId": "g", "status": "already_running" if self.n == 1 else "running"}
    def cancel(self, reason=""): self.canc.append(reason); return True
_c = CS.Chat.__new__(CS.Chat); _c.goals, _c.log, _c._forced, _c.dir = _G(), (lambda x: None), None, scratch
_d = _c._pre_intents([{"role": "user", "text": "سول روحي عبي السيارة بنزين"}], {}, None)
ck("asked again: keeps the running errand", _c.goals.canc == [] and _c.goals.n == 1, (_c.goals.canc, _c.goals.n))
ck("the answer confirms the existing errand", _c._forced == "لسا عم حاول، لحظة.", _c._forced)

# what she says on taking an order
for goal in [IE.parse_high_confidence(x) for x in ("سول عبي السيارة بنزين من الكازية", "عبي السيارة والغالون", "روحي عبي الغالون", "روحي مشي عبي الغالون", "تعي لعندي", "روحي فضي الاغراض بالبيت وارجعي", "سول انقذيني")]:
    seen = {CS.order_line(goal) for _ in range(60)}
    ck("order line fits, not a receipt: %s %s" % (goal["intent"], goal["slots"].get("target", "")), seen and not any("بدأت" in s for s in seen) and all(s in [v for vs in CS.ORDER_LINES.values() for v in vs] for s in seen), seen)
ck("refuel by car speaks of the car, not the can", all("غالون" not in CS.order_line(IE.make_goal("refuel_errand", {"target": "car", "transport": "car"})) for _ in range(40)))
ck("the robotic line is gone from the code", "تمام، بدأت." not in open(CS.__file__, encoding="utf-8").read())
ALLSAID.extend(v for vs in CS.ORDER_LINES.values() for v in vs)

# told to refuel while already at the pump: the GPS has no road to draw
m, e = fresh("refuel_errand", CAR); e.tick(); answer(e, "findRid", True, ST); e.tick(); m.perception["sol"]["position"] = {"x": 7308, "y": 8176, "z": 0}; m.perception["sol"]["currentVehicle"] = {"id": 1}; e.tick()
with open(os.path.join(scratch, "SolGPS_State.txt"), "w", encoding="ascii") as f: f.write("ack=%s\nresult=failed\nreason=bridge_failure\ndistance=2\n" % e.active["gpsRid"])
e.tick(); ck("already at the station: carries on", e.active["status"] == "running" and e.active["phase"] == "park_check", (e.active.get("status"), e.active.get("phase"), e.active.get("reason"))); done(m)
m, e = fresh("refuel_errand", CAR); e.tick(); answer(e, "findRid", True, ST); e.tick(); e.tick()
with open(os.path.join(scratch, "SolGPS_State.txt"), "w", encoding="ascii") as f: f.write("ack=%s\nresult=failed\nreason=bridge_failure\n" % e.active["gpsRid"])
e.tick(); ck("far away, the same refusal is a failure", e.active["status"] == "failed", e.active.get("status")); done(m)

# speech
every = set(ALLSAID) | set(GE.RefuelErrand.TELL.values()) | {GE.RefuelErrand.GENERIC}
bad = [s for s in every if any(w in s for w in CS.BANNED_IN_SPEECH) or any(ch.isascii() and ch.isalpha() for ch in s.replace("GPS", ""))]
ck("no line is technical or has foreign text (%d lines)" % len(every), not bad, bad)
ck("no raw reason reaches speech", not any("_" in s for s in every), [s for s in every if "_" in s])
# every line must reach the bubble as Arabic, never as one Latin-1 character per byte
import re as _re
import mind_core as MC
from kahlua_env import lua51
CLIENT = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\lua\client"
ST_SRC = open(CLIENT + r"\SolText.lua", encoding="utf-8").read()
OV_SRC = open(CLIENT + r"\SolOverlay.lua", encoding="utf-8").read()
L = lua51.LuaRuntime()
L.execute("T = {}\n" + ST_SRC[ST_SRC.index("local HEXV"):ST_SRC.index("-- one-time self check")])
L.execute(OV_SRC[OV_SRC.index("local function isArabic"):OV_SRC.index("local function fontScale")] + "\nIS_ARABIC = isArabic")
def mojibake(s): return _re.search("[\u00c0-\u00ff][\u0080-\u00bf]|\u00d8|\u00d9", s) is not None
ck("the mojibake check catches a real sample", mojibake("\u0623\u0642\u0631\u0628".encode("utf-8").decode("latin-1")))
ck("the mojibake check passes real Arabic", not mojibake("\u0623\u0642\u0631\u0628 30 GPS"))
wrong = []
for s in sorted(every | set(CS.REASON_AR.values())):
    if mojibake(s): wrong.append(("in source", s))
    e = MC.speech_ascii(s)
    if not e.isascii(): wrong.append(("not ascii", s))
    if any("\u0600" <= c <= "\u06ff" for c in s) and not L.globals().IS_ARABIC(e): wrong.append(("bubble would refuse it", s))
    cps = L.globals().T.codepoints(e)
    back = "".join(chr(int(cps[i + 1])) for i in range(len(cps)))
    if mojibake(back) or back != s.translate({0x660 + d: 48 + d for d in range(10)}): wrong.append(("decodes differently", s, back))
ck("every spoken line reaches the bubble as Arabic (%d lines)" % len(every | set(CS.REASON_AR.values())), not wrong, wrong[:3])
broken = "\u0623\u0642\u0631\u0628".encode("utf-8").decode("latin-1")
ck("what went wrong in the game is what this catches: raw bytes are refused by the bubble", not L.globals().IS_ARABIC(broken))
shutil.rmtree(scratch, ignore_errors=True)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
