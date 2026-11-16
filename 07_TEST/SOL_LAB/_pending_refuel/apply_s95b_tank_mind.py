"""s95b tank check (2026-11-11): "عبي السيارة من الكازية" must read the tank of THE car she would fill.
Lab 10:27:38: the model branch answered "السيارة مليانة (100%)" while Jamal's Dart had 57.121 / 59 (96.8%, the GPS panel's 96%).
car_is_full took the car nearest HIM (he was at the station's own parked car, perception dump 10:27:03 centred on it), and
only a tank at the brim counted. SolFuel fills her car: her last car within 15, the car she sits in, the nearest to her.
Now (goal_engine.her_tank / tank_gate, used by both routes):
  - the car she sits in (within 3 of her), else the nearest to her within 15; litres / capacity of its GasTank part
  - >= 99%: she refuses at once, no drive: "السيارة مليانة (99%)، ما بدها تعبية."
  - 90..99%: she goes and says so: "فيها 96%، رح كمّلها."   - below 90%: she just goes
  - the percentage is floored like the game's panel (96.8 -> 96)
Model branch (chat_service, refuel_at_station) and the goal path (RefuelErrand, phase leave, before any drive) both use it.
Idempotent; refuses when an anchor is not found exactly once. usage: apply_s95b_tank_mind.py <sol_mind dir>"""
import os, sys
D = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

GE = os.path.join(D, "goal_engine.py")
edit(GE,
     '@register' + NL + 'class RefuelErrand(ErrandRoundTrip):' + NL,
     '# s95b tank check: the car SHE would fill (SolFuel: her last car within 15, her seat, the nearest to her), from the snapshot' + NL +
     'TANK_FULL_PCT, TANK_TOP_UP_PCT = 99.0, 90.0' + NL +
     'def her_tank(snap):' + NL +
     '    """(litres, capacity, percent) of the car she would fill, or None. The car she sits in, else the nearest to her within 15."""' + NL +
     '    s = snap or {}' + NL +
     '    me = s.get("sol") or {}' + NL +
     '    x, y = me.get("x"), me.get("y")' + NL +
     '    if x is None or y is None: return None' + NL +
     '    reach = 3.0 if me.get("inVehicle") else 15.0' + NL +
     '    best, bd = None, reach * reach' + NL +
     '    for v in list(s.get("vehicles") or []) + list(s.get("solVehicles") or []):' + NL +
     '        if not isinstance(v, dict) or v.get("x") is None or v.get("y") is None: continue' + NL +
     '        d = (v["x"] - x) ** 2 + (v["y"] - y) ** 2' + NL +
     '        if d < bd: best, bd = v, d' + NL +
     '    if best is None: return None' + NL +
     '    fuel, cap = best.get("fuel"), best.get("fuelMax")' + NL +
     '    if not isinstance(fuel, (int, float)) or not isinstance(cap, (int, float)) or cap <= 0: return None' + NL +
     '    return (fuel, cap, 100.0 * fuel / cap)' + NL +
     'def tank_gate(snap):' + NL +
     '    """("full" | "top_up" | "go", percent as the game\'s panel shows it), or (None, None) when her car\'s tank is not known."""' + NL +
     '    t = her_tank(snap)' + NL +
     '    if t is None: return None, None' + NL +
     '    shown = int(math.floor(t[2] + 1e-9))' + NL +
     '    if t[2] >= TANK_FULL_PCT: return "full", shown' + NL +
     '    if t[2] >= TANK_TOP_UP_PCT: return "top_up", shown' + NL +
     '    return "go", shown' + NL +
     'TANK_FULL_SAY = "السيارة مليانة (%d%%)، ما بدها تعبية."' + NL +
     'TANK_TOP_UP_SAY = "فيها %d%%، رح كمّلها."' + NL + NL +
     '@register' + NL + 'class RefuelErrand(ErrandRoundTrip):' + NL)
edit(GE,
     '        if phase == "leave":' + NL +
     '            if slots.get("transport") == "foot":' + NL,
     '        if phase == "leave":' + NL +
     '            topUp = None' + NL +
     '            if slots.get("transport") != "foot" and slots.get("target") in ("car", "both"):          # s95b: her car\'s real tank, before any drive' + NL +
     '                gate, pct = tank_gate(W.load_snapshot(self.e.lua_dir) or {})' + NL +
     '                if gate == "full" and slots.get("target") == "car":' + NL +
     '                    self._speak(TANK_FULL_SAY % pct)' + NL +
     '                    return self.e.complete(g, "tank_full")' + NL +
     '                if gate == "full":' + NL +
     '                    slots["target"] = "can"' + NL +
     '                    self._speak("السيارة مليانة (%d%%)، بعبي الغالون بس." % pct)' + NL +
     '                elif gate == "top_up": topUp = pct' + NL +
     '            if slots.get("transport") == "foot":' + NL)
edit(GE,
     '            self._speak("ماشي، رايحة عالكازية.")' + NL +
     '            f = dict(g["destFields"]); f.update(action="drive", solo="1", speed=slots.get("speed") or "normal")' + NL,
     '            self._speak(TANK_TOP_UP_SAY % topUp if topUp is not None else "ماشي، رايحة عالكازية.")' + NL +
     '            f = dict(g["destFields"]); f.update(action="drive", solo="1", speed=slots.get("speed") or "normal")' + NL)
edit(GE,
     '            if self._pump_in_reach(g, slots):' + NL +
     '                self._speak("الكازية قدامي، بصف جنب المضخة.")' + NL,
     '            if self._pump_in_reach(g, slots):' + NL +
     '                if topUp is not None: self._speak(TANK_TOP_UP_SAY % topUp)' + NL +
     '                self._speak("الكازية قدامي، بصف جنب المضخة.")' + NL)

CS = os.path.join(D, "chat_service.py")
edit(CS,
     'from goal_engine import GoalEngine, next_request_id, _write_request as write_request' + NL,
     'from goal_engine import GoalEngine, next_request_id, _write_request as write_request' + NL +
     'from goal_engine import tank_gate, TANK_FULL_SAY                               # s95b: the tank of the car she would fill' + NL)
edit(CS,
     'def car_is_full(snap):' + NL +
     '    """The percent, when the car nearest him has a full tank; None otherwise. Any real room left in the tank counts as not full."""' + NL,
     'def car_is_full(snap):' + NL +
     '    """s95b: the percent when the car SHE would fill is at 99% or more (goal_engine.tank_gate); None otherwise."""' + NL +
     '    gate, pct = tank_gate(snap)' + NL +
     '    return pct if gate == "full" else None' + NL + NL +
     'def car_is_full_s95(snap):' + NL +
     '    """Before s95b: the car nearest HIM, and only a tank at the brim. Kept for the replay test."""' + NL)
edit(CS,
     '                return "السيارة مليانة (%d%%)، ما بدها تعبية." % full' + NL,
     '                return TANK_FULL_SAY % full' + NL)
print("s95b tank check applied to the Mind (restart the Mind to load it)")
