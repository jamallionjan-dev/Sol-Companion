"""s87 Mind (ledger A1, council SOL_REVIEW section 45). Pairs with apply_s87_lua.py (SolSmartPark.lua, switch smart_park).

smart_park: "صفي السيارة" (the existing park action; no new action, no new keyword route) parks near wherever she is, not only
in the home garage:
  - he names the garage ("بالكراج", "بالموقف" ...) or her car is within 40 tiles of the parking area he marked: the garage park
    exactly as before (home_parks / the marked area);
  - otherwise the game picks the nearest free spot that fits the car and blocks no road or door (sol_smart_park find), she
    drives there (GPS, slow, like the garage park), LF's precise last metres take the car in (sol_smart_park settle), and the
    game checks the whole car is inside (sol_smart_park status). He hears where it ended: inside, partly outside, or why not.
  - smart_park off (SolFixes_LAB.txt): the garage park exactly as before.
The card: "park" means the garage or the nearest free spot (one short phrase on the existing line; no new example).
Blocks appended at the end of model_router.py and chat_service.py (redefinitions); needs s85 installed first. Mind only; needs a
Mind restart. In place, idempotent. Afterwards: card_check.py <mind> --write-doc.
usage: apply_s87_mind.py <sol_mind dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
MARK = "# ---------------------------------------------------------------- s87 smart_park: park near any place"
NEED = "# ---------------------------------------------------------------- s85 card budget, two orders in one line, exit first, far report"


def append(path, block):
    t = open(path, encoding="utf-8", newline="").read()
    if MARK in t: return "kept"
    assert NEED in t, "s85 is not installed in " + path
    nl = CRLF if CRLF in t else NL
    sep = "" if t.endswith(nl) else nl
    open(path, "w", encoding="utf-8", newline="").write(t + sep + nl + nl + (MARK + NL + block).replace(NL, nl))
    return "appended"


MR = r'''# park: the garage, or the nearest free spot when he is not at home (the game decides which; the model only picks "park")
COMMANDS["park"] = ("تصف السيارة بالكراج أو أقرب مكان فاضي", COMMANDS["park"][1])
'''

CS = r'''# smart_park: "صفي السيارة" away from the marked garage -> the game's nearest free spot (SolSmartPark.lua), then a check that the
# whole car is inside. At the garage, or when he names it, the garage park exactly as before.
import farm_talk as _FT87
SMART_PARK_HOME_REACH = 40              # tiles: her car this close to his marked parking area -> that area (the garage park)
SMART_PARK_SETTLE_S = 60                # the last metres and the check, at most
SMART_PARK_DRIVE_S = 600
_GARAGE_WORD_S87 = re.compile(r"(?:كراج|جراج|موقف|مصف|باركينج)")
SMART_PARK_LINES = {
    "start": "رايحة صفها بأقرب مكان فاضي.",
    "already": "هي مصفوفة بمكان صف.",
    "no_spot": "ما لقيت مكان فاضي قريب بتساع السيارة.",
    "no_car": "ما في سيارة جنبي لصفها.",
    "not_loaded": "ما بشوف المكان حوالي منيح هلأ.",
    "near_only": "وقفت جنب المكان، بس ما قدرت فوتها جواته.",
    "inside": "صفيتها جوا المكان.",
    "outside": "صفيتها، بس مش كلها جوا المكان.",
    "failed": "ما قدرت صفها جوا المكان.",
    "no_answer": "ما قدرت لاقي مكان هلأ.",
}
_park_car_s86 = Chat._park_car
_park_watch_s86 = Chat._park_watch
_pre_intents_s86 = Chat._pre_intents


def _pre_intents_s87(self, history, snap, mem):
    last = history[-1] if history else {}
    self._park_said_s87 = str(last.get("said") or last.get("text") or "") if isinstance(last, dict) else ""
    return _pre_intents_s86(self, history, snap, mem)


def smart_park_wanted(snap, said):
    """False: the garage park (he named the garage, or her car is near the area he marked). True: the nearest free spot."""
    s = snap or {}
    marked = s.get("solParking")
    if not isinstance(marked, dict) or marked.get("x") is None: return True
    if _GARAGE_WORD_S87.search(_FT87.norm(said or "")): return False
    sol = s.get("sol") or {}
    if sol.get("x") is None or sol.get("y") is None: return False
    return (sol["x"] - marked["x"]) ** 2 + (sol["y"] - marked["y"]) ** 2 > SMART_PARK_HOME_REACH ** 2


_SPOT_S87 = re.compile(r"^spot:(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(\w+),(\d+)$")


def _park_car_s87(self, snap):
    if not fix_on(self.dir, "smart_park") or not smart_park_wanted(snap, getattr(self, "_park_said_s87", "")):
        self._smart_park_waiting = None
        return _park_car_s86(self, snap)
    self._park_waiting = None
    r = run_action(self.dir, "sol_smart_park", "find", wait=4.0)
    self.log("chat: smart park find -> %s" % r)
    reason = str(r.get("reason") or "") if isinstance(r, dict) else ""
    ok = isinstance(r, dict) and r.get("ok") is True
    if ok and reason.startswith("already:"):
        self._smart_park_waiting = None
        self._forced = SMART_PARK_LINES["already"]
        return
    m = _SPOT_S87.match(reason) if ok else None
    if not m:
        self._smart_park_waiting = None
        self._forced = SMART_PARK_LINES.get(reason) or (SMART_PARK_LINES["no_answer"] if not ok else SMART_PARK_LINES["no_spot"])
        return
    x, y = int(float(m.group(1))), int(float(m.group(2)))
    rid = gps_request(self.dir, {"action": "drive", "x": x, "y": y, "name": "مكان الصف", "speed": "slow"})
    out = _drive_outcome(self.dir, rid, {"sent": "smart parking", "x": x, "y": y})
    self.log("chat: smart park %s %s,%s -> %s" % (m.group(7), x, y, out))
    started = out.get("ok") or str(out.get("reason")) in ("moving_to_wheel", "walking_to_door")
    self._forced = SMART_PARK_LINES["start"] if started else drive_reply(out)
    self._smart_park_waiting = {"t": time.time(), "phase": "drive", "spot": reason} if started else None


def _smart_park_watch(self):
    """Her drive to the spot: the last metres when the GPS arrived, then whether the whole car is inside, said once."""
    w = getattr(self, "_smart_park_waiting", None)
    if not w: return
    now = time.time()
    if w.get("phase") == "settle":
        r = run_action(self.dir, "sol_smart_park", "status", wait=2.5)
        reason = str(r.get("reason") or "") if isinstance(r, dict) else ""
        answered = isinstance(r, dict) and r.get("ok") is not None
        if not answered or (r.get("ok") and reason == "working"):
            if now - w["since"] > SMART_PARK_SETTLE_S:
                self._smart_park_waiting = None
                self._say_later(SMART_PARK_LINES["failed"])
            return
        self._smart_park_waiting = None
        self.log("chat: smart park status -> %s" % r)
        if r.get("ok") and reason == "inside": self._say_later(SMART_PARK_LINES["inside"])
        elif r.get("ok") and reason.startswith("outside"): self._say_later(SMART_PARK_LINES["outside"])
        else: self._say_later(SMART_PARK_LINES["failed"])
        return
    if now - w["t"] > SMART_PARK_DRIVE_S:
        self._smart_park_waiting = None
        return
    g = self.gps_state() or {}
    result, reason = str(g.get("result") or ""), str(g.get("reason") or "")
    if result == "arrived" and reason in ("arrived", ""):
        r = run_action(self.dir, "sol_smart_park", "settle", wait=2.5)
        self.log("chat: smart park settle -> %s" % r)
        if isinstance(r, dict) and r.get("ok"): w.update(phase="settle", since=now)
        else:
            self._smart_park_waiting = None
            self._say_later(SMART_PARK_LINES["near_only"])
    elif result in ("failed", "interrupted") and reason not in ("walking_to_door", "moving_to_wheel", "await_destination", "board_passenger", ""):
        self._smart_park_waiting = None
        if "player" not in reason: self._say_later(drive_reply({"ok": False, "reason": reason}))


def _park_watch_s87(self):
    _park_watch_s86(self)
    _smart_park_watch(self)


Chat._pre_intents = _pre_intents_s87
Chat._park_car = _park_car_s87
Chat._park_watch = _park_watch_s87
'''

if __name__ == "__main__":
    d = sys.argv[1]
    assert os.path.isfile(os.path.join(d, "chat_service.py")) and os.path.isfile(os.path.join(d, "model_router.py")), "not a sol_mind dir: " + d
    print("model_router.py", append(os.path.join(d, "model_router.py"), MR))
    print("chat_service.py", append(os.path.join(d, "chat_service.py"), CS))
    print("s87_mind applied")
