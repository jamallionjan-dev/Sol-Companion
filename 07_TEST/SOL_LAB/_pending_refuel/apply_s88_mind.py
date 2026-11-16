"""s88 Mind (open items A6, A11; Jamal's TODO 2026-11-09 #6, #16, #17). Pairs with apply_s88_lua.py (SolFailNote.lua).

1. "ليش" after a failure says the real reason (switch fail_reasons). Was: only a failed GPS drive or the farm's stop line, else
   "ما صار شي غلط هلأ." even right after a refused order. Now the newest of, within WHY_WINDOW_S88:
     - the game's own note (SolFail_State.txt, written by SolFailNote.lua: orders, boarding, the wheel, bridge_failure, no key),
     - an order the game refused to the Mind (run_action ok=false, kept by the Mind with its time),
     - a failed or interrupted GPS drive (as before),
   worded in her own Levantine line (WHY_AR_S88; REASON_AR for the rest), never the code. The farm's stop line stays the answer
   when nothing newer failed. One log line per answer: "chat: why -> source=... reason=... detail=...".
2. Her memory back after a reconnect (Mind restart, game reload, world switch):
   a) the chat panel: the conversation is loaded from the world's chat_history.json once the world is known, and published to the
      game at once (it stayed empty until he typed again: publish() ran only for a new message);
   b) a message that arrives before the world is known joins the world's own history instead of being dropped when it binds;
   c) the model's card: the memory part of the sheet was cached for 5 minutes, so a sheet built while the game was still loading
      ("لسا ما حددنا البيت", no places) stayed after the world came back. It is rebuilt as soon as what she remembers changes
      (world, home, places, deaths, farm zones, parking, her body there or not).
Block appended at the end of chat_service.py (redefinitions, like s78-s85); needs s85. Card unchanged (no new action, no new
words); card_check.py must still PASS. Mind only; a Mind restart applies it. In place, idempotent.
usage: apply_s88_mind.py <sol_mind dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
MARK = "# ---------------------------------------------------------------- s88 why it failed, memory back after a reconnect"
NEED = "# ---------------------------------------------------------------- s85 card budget, two orders in one line, exit first, far report"


def append(path, block):
    t = open(path, encoding="utf-8", newline="").read()
    if MARK in t: return "kept"
    assert NEED in t, "s85 is not installed in " + path
    nl = CRLF if CRLF in t else NL
    sep = "" if t.endswith(nl) else nl
    open(path, "w", encoding="utf-8", newline="").write(t + sep + nl + nl + (MARK + NL + block).replace(NL, nl))
    return "appended"


CS = r'''# 1. "ليش": the newest real failure (the game's note, an order the game refused, a failed drive), in her words. Switch fail_reasons.
# 2. After a reconnect: the world's conversation back in the chat panel at once, a message before the world is known kept, and the
#    card's memory rebuilt as soon as what she remembers changes.
FAIL_FILE_S88 = "SolFail_State.txt"
WHY_WINDOW_S88 = 15 * 60                                                     # seconds: an older failure is not "the last thing"
_LAST_FAIL_S88 = {}
WHY_AR_S88 = {
    "no_path": "ما لقيت طريق يوصلني لهناك، كل ما حاولت رجعت لنفس المحل.",
    "carry_no_path": "ما لقيت طريق أوصل فيه الغراض.",
    "door_unreachable": "ما قدرت أوصل لباب السيارة، كان في شي سادد الطريق عليه.",
    "door_far": "ما وصلت لباب السيارة.",
    "door_locked": "باب السيارة كان مقفول.",
    "board_timeout": "طوّلت وأنا عم حاول إركب وما زبطت.",
    "wheel_timeout": "طوّلت وأنا رايحة عالمقود وما وصلت.",
    "no_wheel": "ما قدرت إقعد ورا المقود.",
    "no_seat": "ما كان في مقعد فاضي إركب فيه.",
    "unavailable_board": "ما كان في مقعد فاضي إركب فيه.",
    "unavailable_exit": "السيارة كانت ماشية وما فيني إنزل.",
    "still_in": "ضليت بالسيارة، ما قدرت إنزل.",
    "stranger": "كان في حدا غريب بالسيارة.",
    "preempted": "كل ما بلّشت، كان في شي تاني يقطعني.",
    "busy": "كنت مشغولة بشي تاني.",
    "threat": "كان في زومبي قريب، وما فيني إتحرك قبل ما نخلص منه.",
    "no_key": "ما كان معي مفتاح هالسيارة.",
    "no_usable_car": "السيارات اللي حوالينا كلها مقفولة وما معنا مفاتيحها.",
    "no_vehicle_near": "ما كان في سيارة قريبة.",
    "bridge_failure": "السيارة ما مشيت عالطريق اللي رسمتو، فوقفت.",
    "no_route": "ما لقيت طريق بالسيارة لهناك.",
    "road_goal_unavailable": "ما لقيت طريق بالسيارة لهناك.",
    "no_way_round": "الطريق كان مسكّر قدامي وما في لفّة حواليه.",
    "leg_stalled": "علقت بنص الطريق وما قدرت كمّل.",
    "native_released": "السيارة وقفت لحالها بنص الطريق.",
    "player_stop": "إنت وقفتني.",
    "no_row": "ما وصلني الأمر منيح، عيدو.",
    "driving_unavailable": "ما كان فيني سوق وقتها.",
    "player_is_driver": "إنت كنت ورا المقود.",
    "exit_failed": "ما قدرت إنزل من السيارة.",
    "base_missing": "ما في قاعدة محددة لهالشغل.",
}
_run_action_s88_base = run_action
QUERY_OPTIONS_S88 = ("status", "poll", "report", "street", "gardens", "list", "cars", "car_where", "interrupt")   # questions, not orders


def run_action(lua_dir, action, option=None, wait=3.0):
    r = _run_action_s88_base(lua_dir, action, option, wait)
    query = str(option or "") in QUERY_OPTIONS_S88 or str(action).endswith("_status")
    if isinstance(r, dict) and r.get("ok") is False and not query:
        _LAST_FAIL_S88.clear()
        _LAST_FAIL_S88.update(t=time.time(), source="action:" + str(action), reason=str(r.get("reason") or r.get("error") or ""), detail=str(option or ""))
    return r


def read_fail_note(lua_dir):
    """The game's newest failure note (SolFailNote.lua), with the file's time as when; None when there is none."""
    path = os.path.join(lua_dir, FAIL_FILE_S88)
    try:
        with open(path, encoding="ascii", errors="replace") as f:
            st = dict(l.split("=", 1) for l in f.read().splitlines() if "=" in l)
        st["when"] = os.path.getmtime(path)
    except (OSError, ValueError): return None
    return st if st.get("reason") else None


def why_line(reason, detail=""):
    """Her own sentence for a failure code; the code itself is never said."""
    r = str(reason or "").strip()
    if re.search(r"[؀-ۿ]", r): return r                              # the game already said it in her words
    for pre in ("drive_cancelled:", "deferred:"):
        if r.startswith(pre): r = r[len(pre):]
    base = r.split(":", 1)[0].strip()
    if base.endswith("no_key"): base = "no_key"
    line = WHY_AR_S88.get(base) or reason_ar(r)
    if line: return line if line.endswith((".", "!", "؟")) else line + "."
    return "ما زبطت معي، وما عرفت شو اللي وقّفها بالضبط."


def _why_answer_s88(self, snap):
    if not fix_on(self.dir, "fail_reasons"): return _why_answer_s87(self, snap)
    now, found = time.time(), []
    note = read_fail_note(self.dir)
    if note: found.append((note["when"], "game:" + str(note.get("source") or ""), note.get("reason"), note.get("detail") or ""))
    if _LAST_FAIL_S88: found.append((_LAST_FAIL_S88["t"], _LAST_FAIL_S88["source"], _LAST_FAIL_S88["reason"], _LAST_FAIL_S88["detail"]))
    g = self.gps_state() or {}
    if str(g.get("result")) in ("failed", "interrupted") and g.get("reason") not in (None, "", "walking_to_door", "moving_to_wheel"):
        try: when = os.path.getmtime(os.path.join(self.dir, GPS_STATE))
        except OSError: when = now
        found.append((when, "gps", g.get("reason"), ""))
    found = [f for f in found if now - f[0] <= WHY_WINDOW_S88]
    if found:
        when, source, reason, detail = max(found, key=lambda f: f[0])
        line = why_line(reason, detail)
        self.log("chat: why -> source=%s reason=%s detail=%s age=%ds -> %s" % (source, reason, str(detail)[:160], int(now - when), line))
        return line
    line = _FT85.stop_line(((snap or {}).get("solFarm") or {}).get("stop")) or "ما صار شي غلط هلأ."      # an old failed drive is not "the last thing"
    self.log("chat: why -> no failure in the last %d min -> %s" % (WHY_WINDOW_S88 // 60, line))
    return line


_why_answer_s87 = Chat._why_answer
Chat._why_answer = _why_answer_s88


def memory_sig_s88(snap, mem):
    """What she remembers, in a few values: the card's memory is rebuilt when one of them changes."""
    if mem is None: return ("no_world",)
    s = snap or {}
    h = mem.data.get("home") or s.get("solHome")
    farm = s.get("solFarm") if isinstance(s.get("solFarm"), dict) else {}
    return (mem.key, isinstance(h, dict) and h.get("x") is not None, len(mem.data.get("places") or []), int(mem.data.get("deaths") or 0),
            isinstance(s.get("sol"), dict), len(farm.get("zones") or []), isinstance(s.get("solParking"), dict))


_session_sheet_s87 = Chat._session_sheet


def _session_sheet_s88(self, snap, mem, acts):
    sig = memory_sig_s88(snap, mem)
    if getattr(self, "_sheet_sig_s88", None) != sig:
        if getattr(self, "_sheet_sig_s88", None) is not None: self.log("chat: her memory changed %s -> %s, card rebuilt" % (self._sheet_sig_s88, sig))
        self._sheet, self._sheet_sig_s88 = None, sig
    return _session_sheet_s87(self, snap, mem, acts)


Chat._session_sheet = _session_sheet_s88
_handle_s87 = Chat.handle


def _handle_s88(self, text):
    if not self._hist_file:                                                      # the world first: his line joins that world's own history
        try: self._world()
        except Exception as e: self.log("chat: world not known before the message: %r" % (e,))
    return _handle_s87(self, text)


Chat.handle = _handle_s88
_poll_once_s87 = Chat.poll_once
BIND_EVERY_S88 = 1.0


def _poll_once_s88(self):
    if not self._hist_file and time.time() - getattr(self, "_bind_try_s88", 0) >= BIND_EVERY_S88:
        self._bind_try_s88 = time.time()
        try: self._world()
        except Exception as e: self.log("chat: world not known yet: %r" % (e,))
    out = _poll_once_s87(self)
    if self._hist_file and self._hist_file != getattr(self, "_published_hist_s88", None):
        self._published_hist_s88 = self._hist_file
        self.publish()
        self.log("chat: conversation of this world back in the game, %d messages (%s)" % (len(self.hist), os.path.basename(os.path.dirname(self._hist_file))))
    return out


Chat.poll_once = _poll_once_s88
'''


def main(d):
    cs = os.path.join(d, "chat_service.py")
    assert os.path.isfile(cs) and os.path.isfile(os.path.join(d, "model_router.py")), "not a sol_mind dir: " + d
    print("chat_service.py", append(cs, CS))


if __name__ == "__main__":
    main(sys.argv[1])
    print("s88_mind applied")
