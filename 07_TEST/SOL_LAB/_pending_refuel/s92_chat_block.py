

# ---------------------------------------------------------------- s92 come_by_car (switch come_by_car; the far arrival pieces also need the game's far_car)
#   1 her far car is a helicopter: once she is down and out of it (the game walks her to him), no drive goal follows (Living Fellows'
#     driving does not fly); she is said to be near, as for a car.
#   2 she came to a loaded car near her (mode "car"): the drive goal takes THAT car (GPS car=last; SolFarComeCar pins it) and is by car.
#   3 she came with the far car, at the wheel (mode "car_far"): the drive goal is by car.
_far_car_spot_s92_base = Chat._far_car_spot
_far_watch_s92_base = Chat._far_watch


def _far_car_spot_s92(self):
    """As before; the kind of vehicle the game chose (car / tracked / heli) is kept for the arrival."""
    self._far_kind_s92 = None
    seen = []
    base_run = globals()["run_action"]

    def spy(d, action, option=None, wait=2.5):
        r = base_run(d, action, option, wait=wait)
        if action == "sol_far" and option == "car_where": seen.append(r)
        return r
    globals()["run_action"] = spy
    try: out = _far_car_spot_s92_base(self)
    finally: globals()["run_action"] = base_run
    for r in seen[-1:]:
        m = re.match(r"^car:-?\d+,-?\d+,-?\d+,-?\d+,\d+,(\w+)", str(r.get("reason")) if isinstance(r, dict) and r.get("ok") else "")
        self._far_kind_s92 = m.group(1) if m else None
    return out


def _far_watch_s92(self):
    mode = getattr(self, "_far_waiting", False)
    if not mode or not fix_on(self.dir, "come_by_car"): return _far_watch_s92_base(self)
    if mode in ("car", "car_far"):
        goal = getattr(self, "_far_drive_goal", None) or IE.make_goal("fetch_player", {"then": "stay_with_player"}, source="deterministic", text="")
        slots = goal.setdefault("slots", {})
        slots["by_car"] = "1"
        if mode == "car": slots["car"] = "last"
        self._far_drive_goal = goal
    if mode == "car_far" and getattr(self, "_far_kind_s92", None) == "heli":
        p = run_action(self.dir, "sol_far", "poll", wait=2.5)
        if isinstance(p, dict) and str(p.get("reason")) == "here":
            self._far_waiting = False
            with self.lock: self.hist.append({"role": "sol", "text": FAR_AT_EDGE, "t": time.time()})
            self._save(); self.publish()
            self.log("chat: far helicopter down, she walks to him (no drive goal)")
            return
    return _far_watch_s92_base(self)


Chat._far_car_spot = _far_car_spot_s92
Chat._far_watch = _far_watch_s92
# ---------------------------------------------------------------- s92 end
