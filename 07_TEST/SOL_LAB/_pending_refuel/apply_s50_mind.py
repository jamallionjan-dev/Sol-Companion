"""Before going to the pump: a full tank gets an answer, not a trip. usage: apply_s50_mind.py <path to chat_service.py>"""
import sys
P = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)
a1 = """def _hist_placeholder"""
EDITS = [
("""        if action == "refuel_from_can":
            r = run_action(self.dir, "refuel_from_can", None, wait=3.0)
""", """        if action == "refuel_at_station":
            full = car_is_full(snap)
            if full is not None:
                done_line("model", action, "tank_full", full)
                return "السيارة مليانة (%d%%)، ما بدها تعبية." % full
        if action == "refuel_from_can":
            r = run_action(self.dir, "refuel_from_can", None, wait=3.0)
"""),
("""class Chat:
    def __init__(self, lua_dir,""", """def car_is_full(snap):
    \"\"\"The percent, when the car nearest him has a full tank; None otherwise. Any real room left in the tank counts as not full.\"\"\"
    s = snap or {}
    me = s.get("player") or {}
    px, py = me.get("x"), me.get("y")
    if px is None or py is None: return None
    best, bd = None, 30 * 30
    for v in s.get("vehicles") or []:
        if not isinstance(v, dict) or v.get("x") is None or v.get("y") is None: continue
        d = (v["x"] - px) ** 2 + (v["y"] - py) ** 2
        if d < bd: best, bd = v, d
    if best is None: return None
    fuel, cap = best.get("fuel"), best.get("fuelMax")
    if not isinstance(fuel, (int, float)) or not isinstance(cap, (int, float)) or cap <= 0: return None
    return int(round(100.0 * fuel / cap)) if fuel >= cap - 0.01 else None

class Chat:
    def __init__(self, lua_dir,"""),
]
t = open(P, encoding="utf-8", newline="").read()
nl = CRLF if CRLF in t else NL
for a, b in EDITS:
    a2, b2 = a.replace(NL, nl), b.replace(NL, nl)
    assert t.count(a2) == 1, a[:60]
    t = t.replace(a2, b2)
compile(t, P, "exec")
GE = P.replace("chat_service.py", "goal_engine.py")
G_EDITS = [
("""            if reason == "tank_full": return self._after_car(g, now)
            return self._next(g, "pumping_car", now)
""", """            if reason == "tank_full":
                self._speak("السيارة مليانة.")
                return self._after_car(g, now)
            g["tankBefore"] = self._tank_read()
            return self._next(g, "pumping_car", now)
"""),
("""            if not res[0]: return self._fail(g, res[1])
            return self._after_car(g, now)

        if phase == "pump_can":
""", """            if not res[0]: return self._fail(g, res[1])
            self._say_tank(g)
            return self._after_car(g, now)

        if phase == "pump_can":
"""),
("""            self._speak("ماشي، رايحة عالكازية.")
            f = dict(g["destFields"]); f.update(action="drive", solo="1", speed=slots.get("speed") or "normal")
""", """            if self._pump_in_reach(g, slots):
                self._speak("الكازية قدامي، بصف جنب المضخة.")
                return self._next(g, "park_check", now)
            self._speak("ماشي، رايحة عالكازية.")
            f = dict(g["destFields"]); f.update(action="drive", solo="1", speed=slots.get("speed") or "normal")
"""),
("""    def _after_car(self, g, now):
""", """    def _fix_on(self, name):
        try:
            with open(os.path.join(self.e.lua_dir, "SolFixes_LAB.txt"), encoding="utf-8", errors="replace") as f:
                return (name + "=on") in [line.strip() for line in f]
        except OSError:
            return False

    def _pump_in_reach(self, g, slots):
        \"\"\"Already at the station in the car: she parks at the pump from here. The road is for getting to the station.\"\"\"
        if not self._fix_on("refuel_short_hop") or slots.get("target") not in ("car", "both"): return False
        if ((self._perception() or {}).get("sol") or {}).get("currentVehicle") is None: return False
        d = g["destFields"]
        near = self._distance_to(d["x"], d["y"])
        return near is not None and near <= 30

    def _tank_read(self):
        \"\"\"(litres, capacity) of the car nearest her, from the game's own report.\"\"\"
        snap = W.load_snapshot(self.e.lua_dir) or {}
        who = snap.get("sol") or {}
        x, y = who.get("x"), who.get("y")
        if x is None or y is None: return None
        best, bd = None, 15 * 15
        for v in snap.get("vehicles") or []:
            if not isinstance(v, dict) or v.get("x") is None or v.get("y") is None or v.get("fuel") is None: continue
            d = (v["x"] - x) ** 2 + (v["y"] - y) ** 2
            if d < bd: best, bd = v, d
        return (best["fuel"], best.get("fuelMax")) if best else None

    def _say_tank(self, g):
        \"\"\"Real numbers only: a reading that has not moved yet is not reported as a result.\"\"\"
        before, after = g.pop("tankBefore", None), self._tank_read()
        if before and after and after[1] and after[0] > before[0]:
            self._speak("كان فيها %.1f، عبيتها لـ %.1f من %d." % (before[0], after[0], after[1]))
        else:
            self._speak("عبيت السيارة.")

    def _after_car(self, g, now):
"""),
]
g_text = open(GE, encoding="utf-8", newline="").read()
gnl = CRLF if CRLF in g_text else NL
for a, b in G_EDITS:
    a2, b2 = a.replace(NL, gnl), b.replace(NL, gnl)
    assert g_text.count(a2) == 1, a[:60]
    g_text = g_text.replace(a2, b2)
compile(g_text, GE, "exec")
open(P, "w", encoding="utf-8", newline="").write(t)
open(GE, "w", encoding="utf-8", newline="").write(g_text)
print("applied")
