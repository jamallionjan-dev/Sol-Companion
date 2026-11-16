"""s109 reply_after_result, Mind side: she speaks only what the game confirmed. Pairs with apply_s109_reply_after_result.py
(switch registration only; no Lua behaviour changes). Switch reply_after_result (SolFixes_LAB.txt, read each time; missing = off).

Live 2026-11-11 15:03-15:04 (DebugLog 14-48, sol_mind.log 5125-5133):
  15:03:03 "سوقي السيارة وتعي لعندي" -> come_car: the game said car_not_near (her car ~2977 tiles from him, CAR_NEAR is 60); the Mind
           then moved her car from far (car_where -> car_far -> waiting:180) and said "جاية بالسيارة، بدي 3 دقايق".
           far_car is OFF, so that move is the old one: the car stops on a road just OUTSIDE his loaded area (here ~90 tiles away) and
           she appears at it only when he goes close. Placed at 15:03:22; the "she is at the road" line is disabled (`and False`), so
           he was never told. The promise "I'm coming by car" was not what the game does.
  15:04:22 "اديش بدك لتوصلي" -> model none "أنا هنا معك": untrue (sol_far status at 15:04:41 = placed, no body near him).
  15:04:41 "تعي لعندي مشي" -> "جاية، اصبر شوي.": untrue, nothing moves while she is placed.
What changes with the switch on (chat_service.py, one block appended at the end):
  1 every action whose result the game reports (resolve_and_run: the model's action, the word-list action): an answer not in yet
    gets 2 s more; still nothing -> "ثانية، عم شوف." and the real answer is said when it comes (failure in s88's words, why_line;
    success "تمام."; nothing in 30 s -> "ما زبطت معي هلأ، جرب كمان مرة."). A failure is said with s88's why_line, never "تكرم".
  2 far, by car: the old far move (no ",in": far_car off) is said as it is ("سيارتي بعيدة كتير عنك... بجيبها لأقرب طريق منك...
    وبقلك وين تلاقيني"); once the car is there he is told where (distance and direction from him) and to come closer.
    Her car not possible and she walks: the reason first ("سيارتي ما فيها بنزين كفاية، فجاية مشي، بدي 5 دقايق").
  3 far and the model's plain talk says she is here / arriving / how long: the line is replaced by her real state from the game.
  4 far, placed at the road, called again (on foot or by car): the road line, not "جاية، اصبر شوي".
  5 she is here: "come by car" (the fetch_player drive) waits up to 4 s for the game's first drive answer: started -> "رايحة
    عالسيارة وجايتك."; no car -> s88's reason + "فجاية مشي."; no answer -> "ثانية، عم شوف." and the answer later. The goal's own
    "جايتك، استناني." is not said on top (quiet).
Switch off: every function is the old one. No card change (no action, no example). In place, idempotent.
usage: apply_s109_reply_after_result_mind.py <sol_mind dir>"""
import os, py_compile, sys
NL, CRLF = chr(10), chr(13) + chr(10)
MARK = "# ---------------------------------------------------------------- s109 reply_after_result"


def append(path, block):
    t = open(path, encoding="utf-8", newline="").read()
    if MARK in t: return "kept"
    nl = CRLF if CRLF in t else NL
    sep = "" if t.endswith(nl) else nl
    open(path, "w", encoding="utf-8", newline="").write(t + sep + nl + nl + (MARK + NL + block).replace(NL, nl))
    py_compile.compile(path, doraise=True)
    return "appended"


CS = r'''# Switch reply_after_result: she says what the game confirmed, never a success line before (or against) its answer.
SW_S109 = "reply_after_result"
EXTRA_WAIT_S109, LATE_GIVE_UP_S109, HERE_WAIT_S109 = 2.0, 30.0, 4.0           # seconds
NEUTRAL_S109 = "ثانية، عم شوف."
LATE_OK_S109 = "تمام."
LATE_NONE_S109 = "ما زبطت معي هلأ، جرب كمان مرة."
EDGE_START_S109 = "سيارتي بعيدة كتير عنك، وما بقدر وصل فيها لعندك. بجيبها لأقرب طريق منك، بدي %s، وبقلك وين تلاقيني."
EDGE_THERE_S109 = "صرت بالسيارة عالطريق، %s. قرّب لصوبي شوي، وأول ما تقرب بجي لعندك."
EDGE_ON_WAY_S109 = "لسا بالطريق مع السيارة، باقي %s، وبعدين بقلك وين تلاقيني."
EDGE_MOVING_S109 = "لسا بالطريق مع السيارة، شوي وبقلك وين تلاقيني."
FAR_COMING_S109 = "لسا جاية، باقي %s."
FAR_NEAR_S109 = "صرت قريبة، اصبر شوي."
FAR_AWAY_S109 = "أنا بعيدة عنك هلأ. إذا بدك قلي تعالي."
HERE_GO_S109 = "رايحة عالسيارة وجايتك."
HERE_AT_S109 = "أنا عندك."
FOOT_S109 = "%s، فجاية مشي، بدي %s."
CAR_WHY_S109 = {
    "car_not_near": "سيارتي بعيدة عنك", "no_fuel": "سيارتي ما فيها بنزين كفاية", "picked_no_fuel": "السيارة اللي لقيتها ما فيها بنزين كفاية",
    "car_taken": "أنت راكب سيارتي", "car_locked": "سيارتي مقفولة", "car_no_key": "ما معي مفتاح سيارتي", "car_lock_unknown": "ما عرفت إذا سيارتي مقفولة",
    "towing": "سيارتي عم تجر شي", "no_car": "ما بعرف وين سيارتي", "no_route": "ما لقيت طريق للسيارة لعندك",
    "car_too_close": "سيارتي مو بعيدة عنك بس ما بقدر جيبها من هون", "no_car_near": "ما في سيارة حدي بقدر سوقها",
    "locked_near": "السيارات اللي حدي مقفولة", "no_key_near": "ما معي مفاتيح للسيارات اللي حدي", "no_fuel_near": "السيارات اللي حدي ما فيها بنزين كفاية",
}
CAR_WHY_ANY_S109 = "ما قدرت جيب السيارة"
_COMPASS_S109 = ("بالشرق", "بالجنوب الشرقي", "بالجنوب", "بالجنوب الغربي", "بالغرب", "بالشمال الغربي", "بالشمال", "بالشمال الشرقي")
_PRESENCE_S109 = re.compile(r"هنا|هون|جنبك|حدك|معك|عندك|وصلت|بوصل|دقيق|دقايق|ثواني|باقي|قريب|جاي[ةه]")
_GPS_WAITING_S109 = ("board_passenger", "moving_to_wheel", "walking_to_door", "await_destination", "")
_PENDING_S109 = []                                                           # actions the game had not answered when she spoke


def _s109_on(lua_dir): return fix_on(lua_dir, SW_S109)


_action_receipt_note_s109_base = action_receipt_note


def action_receipt_note(result):
    """Switch on (the result carries s109): not confirmed yet -> the neutral line; a refusal -> s88's words for its reason."""
    if isinstance(result, dict) and result.get("s109"):
        if result.get("ok") is None and not result.get("error"): return NEUTRAL_S109
        if result.get("error") or result.get("ok") is False: return why_line(result.get("reason") or result.get("error") or "")
    return _action_receipt_note_s109_base(result)


_resolve_and_run_s109_base = resolve_and_run


def resolve_and_run(lua_dir, aid, opt, mem, snap, log=print):
    r = _resolve_and_run_s109_base(lua_dir, aid, opt, mem, snap, log)
    if not isinstance(r, dict) or not _s109_on(lua_dir): return r
    rid = r.get("rid")
    if r.get("ok") is None and rid is not None and not r.get("error"):
        end, got = time.time() + EXTRA_WAIT_S109, None
        while time.time() < end:
            got = action_result(lua_dir, rid)
            if got is not None: break
            time.sleep(0.1)
        if got is not None:
            r.clear(); r.update(got)                                            # in place: s105's record of this run sees the answer too
        else:
            _PENDING_S109.append({"dir": lua_dir, "rid": rid, "action": aid, "option": opt, "t": time.time()})
    r["s109"] = True
    return r


def _spy_s109(fn, *a):
    """fn(*a) with every run_action it makes recorded as (action, option, result)."""
    seen, base = [], globals()["run_action"]

    def spy(d, action, option=None, wait=3.0):
        r = base(d, action, option, wait=wait)
        seen.append((action, option, r))
        return r
    globals()["run_action"] = spy
    try: out = fn(*a)
    finally: globals()["run_action"] = base
    return out, seen


def _why_s109(r): return str(r.get("reason") or r.get("error") or "") if isinstance(r, dict) else ""


def _foot_after_car_s109(seen):
    """Why her car could not come, from the game's own answers in this turn (the first refusal on the car's way)."""
    calls = [(str(o or ""), r) for a, o, r in seen if a == "sol_far"]
    where_ok = False
    for o, r in calls:
        why = _why_s109(r)
        ok = isinstance(r, dict) and r.get("ok")
        if o == "come_car" and not ok and why != "car_not_near": return why
        if o == "car_where":
            if not ok: return why
            where_ok = True
        if o.startswith("car_far:") and (not ok or not why.startswith("waiting:")): return why
    if where_ok and not any(o.startswith("car_far:") for o, _ in calls): return "no_route"   # no road spot for it
    return "car_not_near"


def _edge_place_s109(self):
    """Where the car waits, from him now: "شي 90 متر بالشمال منك" (no numbers but metres)."""
    edge = getattr(self, "_s109_edge", None) or {}
    try: snap = self._world()[0] or {}
    except Exception: snap = {}
    me = snap.get("player") or {}
    if edge.get("x") is None or me.get("x") is None: return "قريب منك"
    dx, dy = edge["x"] - float(me["x"]), edge["y"] - float(me["y"])
    d = max(10, int(round(math.hypot(dx, dy) / 10.0)) * 10)
    side = _COMPASS_S109[int(round(math.atan2(dy, dx) / (math.pi / 4))) % 8]   # y grows to the south
    return "شي %d متر %s منك" % (d, side)


def _s109_far_line(self, far):
    """Her real state while she is not here, in her words."""
    edge = getattr(self, "_s109_edge", None) if getattr(self, "_far_waiting", False) == "car_far" else None
    if edge:
        if far == "placed": return EDGE_THERE_S109 % _edge_place_s109(self)
        if far.startswith("waiting:"): return far_wait_line(far, EDGE_ON_WAY_S109)
        return EDGE_MOVING_S109
    if far.startswith("waiting:"): return far_wait_line(far, FAR_COMING_S109)
    if far in ("seeking", "placed"): return FAR_NEAR_S109
    return FAR_AWAY_S109


_far_come_s109_base = Chat._far_come


def _far_come_s109(self, goal=None, by_car=False):
    if not _s109_on(self.dir): return _far_come_s109_base(self, goal, by_car)
    self._s109_edge = None
    _, seen = _spy_s109(_far_come_s109_base, self, goal, by_car)
    mode = getattr(self, "_far_waiting", False)
    started = lambda r: isinstance(r, dict) and r.get("ok") and _why_s109(r).startswith("waiting:")
    moved = next(((str(o), r) for a, o, r in seen if a == "sol_far" and str(o or "").startswith("car_far:")), None)
    foot = next((r for a, o, r in reversed(seen) if a == "sol_far" and o == "come"), None)
    if mode == "car_far" and moved is not None and started(moved[1]) and not moved[0].endswith(",in"):   # the old far move: the car stops outside his area
        try: x, y = (float(v) for v in moved[0][8:].split(",")[:2])
        except ValueError: x = y = None
        self._s109_edge = {"x": x, "y": y, "told": False}
        self._forced = far_wait_line(_why_s109(moved[1]), EDGE_START_S109)
    elif by_car and started(foot):                                              # her car could not come, she walks: why first
        why = _foot_after_car_s109(seen)
        self._forced = FOOT_S109 % (CAR_WHY_S109.get(why, CAR_WHY_ANY_S109), far_wait_line(_why_s109(foot), "%s"))
    self.log("chat: s109 far come by_car=%s mode=%s -> %s" % (by_car, mode, self._forced))


_far_watch_s109_base = Chat._far_watch


def _far_watch_s109(self):
    edge = getattr(self, "_s109_edge", None)
    if not edge or edge.get("told") or getattr(self, "_far_waiting", False) != "car_far" or not _s109_on(self.dir): return _far_watch_s109_base(self)
    p = run_action(self.dir, "sol_far", "poll", wait=2.5)
    if isinstance(p, dict) and p.get("ok") and str(p.get("reason")) == "placed":    # the car is at the road: he hears where, once
        edge["told"] = True
        line = EDGE_THERE_S109 % _edge_place_s109(self)
        self.log("chat: s109 far car at the road -> %s" % line)
        self._say_later(line)
        return
    return _far_watch_s109_base(self)


_far_order_s109_base = Chat._far_order


def _far_order_s109(self, text, snap, done, said=None):
    if not _s109_on(self.dir): return _far_order_s109_base(self, text, snap, done, said)
    out, seen = _spy_s109(_far_order_s109_base, self, text, snap, done, said)
    forced = getattr(self, "_forced", None)
    status = next((_why_s109(r) for a, o, r in reversed(seen) if a == "sol_far" and o == "status"), "")
    coming_line = forced == FAR_ON_WAY or (isinstance(forced, str) and forced.startswith("جاية، باقي"))
    if out and coming_line and status and getattr(self, "_far_waiting", False) == "car_far" and getattr(self, "_s109_edge", None):
        self._forced = _s109_far_line(self, status)
        self.log("chat: s109 far called again while %s -> %s" % (status, self._forced))
    return out


_route_by_model_s109_base = Chat._route_by_model


def _route_by_model_s109(self, history, c, key, snap, mem):
    """As before; her plain talk may not say she is here (or arriving, or how long) while the game says she is not."""
    if not _s109_on(self.dir): return _route_by_model_s109_base(self, history, c, key, snap, mem)
    lines, log0 = [], self.log
    self.log = lambda m: (lines.append(str(m)), log0(m))[1]
    try: reply = _route_by_model_s109_base(self, history, c, key, snap, mem)
    finally: self.log = log0
    route = [l for l in lines if l.startswith("chat: route text=")]
    if not isinstance(reply, str) or not route or " path=model " not in route[-1] or " action=none " not in route[-1]: return reply
    if not _PRESENCE_S109.search(reply): return reply
    sol = (snap or {}).get("sol")
    if isinstance(sol, dict) and sol and not sol.get("away"): return reply
    far = self._far_state(snap)
    if far is None: return reply
    line = _s109_far_line(self, far)
    self.log("chat: s109 her talk said she was here while %s: %s -> %s" % (far, reply[:60], line))
    return line


def _s109_goal(self, gid):
    eng = self.goals
    lock = getattr(eng, "lock", None)
    if lock is not None: lock.acquire()
    try:
        for g in [getattr(eng, "active", None)] + list(reversed(list(getattr(eng, "history", None) or []))):
            if isinstance(g, dict) and g.get("id") == gid: return dict(g)
    finally:
        if lock is not None: lock.release()
    return None


def _foot_line_s109(why):
    return why_line(why).rstrip(".!؟ ") + "، فجاية مشي."


def _s109_here_line(self, gid):
    """The game's first answer to her drive to him: a line, "" (nothing to say), or None (not in yet)."""
    g = _s109_goal(self, gid)
    if g is None: return ""
    st, reason = g.get("status"), str(g.get("reason") or "")
    if st == "completed":
        if reason.startswith("coming_on_foot:"): return _foot_line_s109(reason.split(":", 1)[1])
        if reason == "arrived_at_player": return HERE_AT_S109
        return ""
    if st == "failed":
        if reason == "player_took_over": return ""
        if reason == "no_sol": return "ما فيني هلأ."
        if reason == "gps_unconfirmed": return LATE_NONE_S109
        return why_line(reason)
    if st != "running": return ""
    rid = g.get("gpsRid")
    if not rid: return None
    gs = self.gps_state() or {}
    if str(gs.get("ack") or "") != str(rid): return None
    if (gs.get("result") or "") == "failed" and (gs.get("reason") or "") not in _GPS_WAITING_S109: return None   # the goal turns it into on foot next
    if (gs.get("result") or "") == "stopped": return ""
    return HERE_GO_S109


_pre_intents_s109_base = Chat._pre_intents


def _pre_intents_s109(self, history, snap, mem):
    """As before; "come to me by car" while she is here is answered from the game's first answer to the drive."""
    if not _s109_on(self.dir) or getattr(self, "goals", None) is None: return _pre_intents_s109_base(self, history, snap, mem)
    eng, sub = self.goals, []
    had = "submit" in vars(eng)
    real = eng.submit

    def submit(goal):
        if isinstance(goal, dict) and goal.get("intent") == "fetch_player":
            goal = dict(goal, slots=dict(goal.get("slots") or {}, quiet="1"))       # her line comes from the game's answer, not twice
            r = real(goal)
            sub.append(r)
            return r
        return real(goal)
    eng.submit = submit
    try: done = _pre_intents_s109_base(self, history, snap, mem)
    finally:
        if had: eng.submit = real
        else:
            try: del eng.submit
            except AttributeError: pass
    r = sub[-1] if sub else None
    if isinstance(r, dict) and r.get("ok") and r.get("status") == "running" and r.get("goalId"):
        end, line = time.time() + HERE_WAIT_S109, None
        while time.time() < end:
            line = _s109_here_line(self, r["goalId"])
            if line is not None: break
            time.sleep(0.15)
        if not line:
            self._s109_here = {"goalId": r["goalId"], "t": time.time()}
            line = NEUTRAL_S109
        self._forced = line
        self.log("chat: s109 come by car while here -> %s" % line)
    return done


def _s109_watch(self):
    """The answers that came after she spoke: said once, in her words."""
    if not _s109_on(self.dir): return
    now = time.time()
    for p in list(_PENDING_S109):
        if p["dir"] != self.dir: continue
        got = action_result(self.dir, p["rid"])
        if got is None and now - p["t"] < LATE_GIVE_UP_S109: continue
        _PENDING_S109.remove(p)
        if got is None: line = LATE_NONE_S109
        elif got.get("ok") is False:
            line = why_line(got.get("reason"))
            _LAST_FAIL_S88.clear()
            _LAST_FAIL_S88.update(t=now, source="action:" + str(p["action"]), reason=str(got.get("reason") or ""), detail=str(p.get("option") or ""))
        else: line = LATE_OK_S109
        self.log("chat: s109 late answer %s %s -> %s -> %s" % (p["action"], p.get("option"), got, line))
        self._say_later(line)
    here = getattr(self, "_s109_here", None)
    if here:
        line = _s109_here_line(self, here["goalId"])
        if line is None and now - here["t"] < LATE_GIVE_UP_S109: return
        self._s109_here = None
        if line is None: line = LATE_NONE_S109
        self.log("chat: s109 late drive answer -> %s" % (line or "(nothing to say)"))
        if line: self._say_later(line)


_poll_once_s109_base = Chat.poll_once


def _poll_once_s109(self):
    now = time.time()
    if now - getattr(self, "_s109_at", 0) >= 1.0:
        self._s109_at = now
        try: _s109_watch(self)
        except Exception as e: self.log("s109 watch failed: %r" % (e,))
    return _poll_once_s109_base(self)


Chat._far_come = _far_come_s109
Chat._far_watch = _far_watch_s109
Chat._far_order = _far_order_s109
Chat._route_by_model = _route_by_model_s109
Chat._pre_intents = _pre_intents_s109
Chat.poll_once = _poll_once_s109
# ---------------------------------------------------------------- s109 end
'''


def mind(d):
    cs = os.path.join(d, "chat_service.py")
    t = open(cs, encoding="utf-8").read()
    for need in ("def why_line", "_LAST_FAIL_S88", "def _far_come", "def action_receipt_note", "def resolve_and_run", "def fix_on"):
        assert need in t, "chat_service.py lacks %s (s88 / far pieces): %s" % (need, d)
    print("chat_service.py", append(cs, CS))


if __name__ == "__main__":
    mind(sys.argv[1])
    print("s109_reply_after_result_mind applied")
