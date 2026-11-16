

# ---------------------------------------------------------------- s92 come_by_car (switch come_by_car in SolFixes_LAB.txt; off: FetchPlayer as before)
# "تعالي لعندي بالسيارة": she takes a car and drives to where he is NOW.
#   1 by car (car words in his order, or slots by_car=1): standing near him on foot is not "arrived"; she gets in first
#     (was: within 12 tiles of him the goal ended at once, exit_vehicle + follow, and she never boarded).
#   2 driving: arrived is the GPS's own "arrived" (its parking), or within 3 tiles, or within 12 tiles and the GPS has not moved on for 20 s
#     (was: within 12 tiles = exit_vehicle at once, short of where the GPS parks).
#   3 he moves: re-aimed when he is further from the target than a quarter of her distance to him (12 to 60 tiles), measured live
#     (was: every 12 tiles, a stop and a new route each time even when she was 200 tiles out).
#   4 no car she can take, or the car could not be reached: she says so in one line and comes on foot (was: silent).
#   5 slots car=last: the drive takes the car the far trip chose (SolFarComeCar pins it as gps.lastDriveCar).
_CAR_WORDS_92 = ("سيار", "عربي", "المدرع", "مدرع", "car", "truck")
FOOT_LINES_92 = (("no_usable_car", "ما في سيارة بقدر سوقها جنبي، جاية مشي."), ("no_vehicle_near", "ما في سيارة جنبي، جاية مشي."),
                 ("lock", "السيارة مسكّرة، جاية مشي."), ("key", "ما معي مفتاح السيارة، جاية مشي."), ("fuel", "السيارة ما فيها بنزين، جاية مشي."),
                 ("gas", "السيارة ما فيها بنزين، جاية مشي."), ("could_not_reach_door", "ما قدرت وصل للسيارة، جاية مشي."),
                 ("cannot_take_wheel", "ما قدرت قعد ورا المقود، جاية مشي."))
FOOT_DEFAULT_92 = "ما قدرت جيب السيارة، جاية مشي."
STUCK_LINE_92 = "علقت بالسيارة، كملت مشي."


def _fix_on_92(lua_dir, name):
    try:
        with open(os.path.join(lua_dir, "SolFixes_LAB.txt"), encoding="utf-8", errors="replace") as f:
            return any(line.strip().replace(" ", "") == name + "=on" for line in f)
    except OSError:
        return False


def foot_line_92(why, drove):
    if drove: return STUCK_LINE_92
    w = str(why or "")
    for key, line in FOOT_LINES_92:
        if key in w: return line
    return FOOT_DEFAULT_92


@register
class FetchPlayer92(FetchPlayer):
    intent = "fetch_player"
    NEAR_TILES, STILL_SECONDS = 3.0, 20.0

    def _on(self): return _fix_on_92(self.e.lua_dir, "come_by_car")

    def _by_car(self):
        g = self.goal; s = g.get("slots") or {}
        if str(s.get("by_car") or "") == "1": return True
        t = str(g.get("text") or "").lower()
        return any(w in t for w in _CAR_WORDS_92)

    def _in_vehicle(self):
        per = self._perception() or {}
        return (per.get("sol") or {}).get("currentVehicle") is not None

    def _arrived92(self, g, st, live, now):
        """Measured to where he is now. None: not yet; True: arrived; "retarget": the GPS stopped short of where he is now."""
        inside = self._in_vehicle()
        if inside: g["boarded"] = True
        if self._by_car() and not inside and not g.get("boarded"): return None        # the walk to the car is not the trip
        d = self._distance_to(live.get("x"), live.get("y"))
        gps_done = (st.get("result") or "") == "arrived" or (st.get("phase") or "") == "arrived"
        if gps_done:
            return True if d is None or d <= self.ARRIVE_TILES else "retarget"
        if d is None: return None
        if not inside: return True if d <= self.ARRIVE_TILES else None               # on foot (no car words): as before
        if d <= self.NEAR_TILES: return True
        if d <= self.ARRIVE_TILES:
            key = (round(d), st.get("distance"))
            if g.get("nearKey") != key: g["nearKey"], g["nearSince"] = key, now
            if now - g.get("nearSince", now) >= self.STILL_SECONDS: return True
        return None

    def tick(self, now):
        if not self._on(): return FetchPlayer.tick(self, now)
        g = self.goal; slots = g.get("slots") or {}
        phase = g.get("phase") or "resolve"
        if phase not in ("resolve", "driving_to_player"): return FetchPlayer.tick(self, now)
        if not self._perception(): return self.e.wait(g, "waiting_perception")

        if phase == "resolve":
            xy = self._player_xy()
            if xy is None: return self.e.wait(g, "player_position_unavailable")
            g["toPlayer"] = {"x": xy[0], "y": xy[1]}
            f = {"action": "drive", "x": xy[0], "y": xy[1], "name": "to the player", "solo": "1", "speed": slots.get("speed") or "fast"}
            if slots.get("car") == "last": f["car"] = "last"
            self._gps(f)
            g["phase"] = "driving_to_player"; g["reason"] = "driving_to_player"
            g["aims"] = int(g.get("aims") or 0) + 1
            if not g.get("spoke") and not slots.get("quiet"): self._speak("جايتك، استناني.")
            g["spoke"] = True
            return

        st = self._gps_state()
        if st is None:
            if now - g.get("phaseSince", now) > 8: return self.e.fail(g, "gps_unconfirmed")
            return
        why = self._gps_failed(st)
        if why == "player_took_over": return self.e.fail(g, "player_took_over")
        if why:
            if why == "no_sol": return self.e.fail(g, "no_sol")
            self._once_tool("followRid", "follow")
            self._speak(foot_line_92(why, g.get("boarded")))
            return self.e.complete(g, "coming_on_foot:%s" % why)
        xy = self._player_xy()
        to = g.get("toPlayer") or {}
        live = {"x": xy[0], "y": xy[1]} if xy else to
        arrived = self._arrived92(g, st, live, now)
        if arrived is True:
            if (slots.get("then") or "stay_with_player") == "take_player_home":
                home = self.e.home()
                if not home: return self.e.fail(g, "home_not_set")
                self._gps({"action": "drive", "x": int(home["x"]), "y": int(home["y"]),
                           "name": home.get("name") or "home", "solo": "0", "car": "last", "speed": "normal"})
                g["phase"] = "taking_home"; g["reason"] = "waiting_for_player_then_home"; return
            if not self._once_tool("exitRid", "exit_vehicle"): return
            self._once_tool("followRid", "follow")
            return self.e.complete(g, "arrived_at_player")
        if arrived == "retarget":
            g["phase"] = "resolve"; g["phaseSince"] = now; return
        if xy and to.get("x") is not None:
            her = self._distance_to(xy[0], xy[1])
            limit = 12.0 if her is None else max(12.0, min(60.0, 0.25 * her))
            if math.hypot(xy[0] - to["x"], xy[1] - to["y"]) > limit:                # he moved: to where he is now
                g["phase"] = "resolve"; g["phaseSince"] = now; return
        if now - g.get("phaseSince", now) > self.DRIVE_TIMEOUT:
            if not g.get("boarded"):                                              # never got into the car: on foot, said once
                self._once_tool("followRid", "follow")
                self._speak(foot_line_92("could_not_reach_door", False))
                return self.e.complete(g, "coming_on_foot:board_timeout")
            return self.e.fail(g, "drive_to_player_timeout")
        return
# ---------------------------------------------------------------- s92 end
