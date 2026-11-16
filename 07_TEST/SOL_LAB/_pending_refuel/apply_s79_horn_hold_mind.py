"""s79_horn_hold_mind (Jamal 2026-11-10 20:48 "خلي ايدك عالزمور"; 21:47:46 "زرمي طول الطريق" went to unknown), Mind side.
Pairs with apply_s79_horn_hold_lua.py (verb horn_hold start | stop, behind the horn_hold switch).

1. The card: horn_hold is a card action (shown only when the game lists it, i.e. the switch is on), with examples
   start: "خلي ايدك عالزمور", "ضلك زمري", "ضلي زمري", "زمري طول الطريق", "زرمي طول الطريق";
   stop:  "وقفي الزمور", "شيلي ايدك عن الزمور", "خلص بلا زمور";  and "زمري" stays the single beep (sol_horn once, unchanged).
2. Bare "بس": only while her hand is on the horn does the card say so and show "بس" -> horn_hold stop. No word override: the
   model decides. Whether she holds it comes from the game's action list (horn_hold state=holding|idle) or, when the Mind's own
   start/stop is newer than that list, from what the Mind just did. The sheet is rebuilt when that changes.
3. Her lines: start "تكرم."; stop a short line; a refusal in her words (not in a car, not at the wheel, engine off, battery).
   Nothing technical. A result the game has not confirmed yet keeps the usual reply.
Every change is a block appended at the end of its file (redefinitions), so no earlier installer's text is touched; works with or
without apply_s78_cars_away_mind.py, before or after it. Mind only; needs a Mind restart. In place, idempotent.
usage: apply_s79_horn_hold_mind.py <sol_mind dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
MARK = "# ---------------------------------------------------------------- s79 horn_hold"


def append(path, block):
    t = open(path, encoding="utf-8", newline="").read()
    if MARK in t: return "kept"
    nl = CRLF if CRLF in t else NL
    sep = "" if t.endswith(nl) else nl
    open(path, "w", encoding="utf-8", newline="").write(t + sep + nl + nl + (MARK + NL + block).replace(NL, nl))
    return "appended"


MR = r'''# horn_hold: her hand stays on the horn while she drives, until he says stop. sol_horn (one beep) is unchanged.
HORN_HELD = False                                                             # set by the chat for each sheet it builds
CARD_ACTIONS["horn_hold"] = ("تضلي حاطة إيدك عالزمور وإنتِ عم تسوقي، لحتى يقلك وقفي", "خلي ايدك عالزمور", "option: start أو stop")
HORN_START = ("خلي ايدك عالزمور", "ضلك زمري", "ضلي زمري", "زمري طول الطريق", "زرمي طول الطريق")
HORN_STOP = ("وقفي الزمور", "شيلي ايدك عن الزمور", "خلص بلا زمور")
HORN_HELD_STOP = ("بس",)                                                      # only while her hand is on the horn
_sheet_s78 = sheet


def _horn_shot(text, action, option):
    return '%s -> {"action":"%s","args":{"option":"%s"},"speech":""}' % (text, action, option)


def sheet(actions, memory):
    """The card as before; with horn_hold on it, its examples, and "بس" as a stop only while she holds the horn."""
    text = _sheet_s78(actions, memory)
    known = {a.get("id") for a in actions or [] if a.get("enabled", True)}
    if actions and "horn_hold" not in known: return text
    n = chr(10)
    shots = [_horn_shot(t, "horn_hold", "start") for t in HORN_START] + [_horn_shot(t, "horn_hold", "stop") for t in HORN_STOP]
    if not actions or "sol_horn" in known: shots.append(_horn_shot("زمري", "sol_horn", "once"))
    if HORN_HELD:
        shots += [_horn_shot(t, "horn_hold", "stop") for t in HORN_HELD_STOP]
        shots.append("إيدك عالزمور هلأ: \"بس\" لحالها يعني شيلي إيدك عنه.")
    tail = n + n + "ذاكرتك الآن:"
    if tail not in text: return text + n + n.join(shots)
    return text.replace(tail, n + n.join(shots) + tail, 1)
'''

CS = r'''# horn_hold: whether her hand is on the horn goes into the card; her own short lines for it.
HORN_MIND_SECONDS = 300                                                       # the Mind's own start counts this long at most
HORN_LINES = {
    "not_in_a_car": "أنا مو بسيارة هلأ.",
    "no_sol": "ما فيني هلأ.",
    "horn_needs_driver_seat": "لازم كون ورا المقود لزمّر.",
    "horn_engine_off": "السيارة طافية هلأ.",
    "horn_unavailable": "ما بقدر زمّر بهالسيارة.",
    "battery_dead": "البطارية فاضية.",
    "no_battery": "ما في بطارية بالسيارة.",
    "unknown_option": "شو قصدك؟ عيدها بكلمة تانية.",
}
HORN_STOP_OPTIONS = ("stop", "off", "release")
_HORN_RUN = []


def horn_catalog_time(lua_dir):
    """When the game last wrote its action list (ms), 0 when unknown."""
    try:
        with open(os.path.join(lua_dir, ACT_SNAP), encoding="ascii", errors="replace") as f: d = json.loads(f.read())
        return float(d.get("t") or 0)
    except (OSError, ValueError, TypeError, AttributeError): return 0.0


def horn_line(option, result):
    """Her line for a horn_hold result, or None to keep the usual reply (the game did not confirm yet)."""
    r = result if isinstance(result, dict) else {}
    if r.get("ok") is None and not r.get("error"): return None
    why = str(r.get("reason") or r.get("error") or "")
    if r.get("error") or r.get("ok") is False:
        return HORN_LINES.get(why) or reason_ar(why) or "ما قدرت هلأ."
    if str(option or "start").lower() in HORN_STOP_OPTIONS:
        if why == "horn_not_held": return "ما كنت عم زمّر."
        return random.choice(("خلص، شلت إيدي.", "ماشي، خلص."))
    return "تكرم."


_resolve_and_run_s78 = resolve_and_run


def resolve_and_run(lua_dir, aid, opt, mem, snap, log=print):
    r = _resolve_and_run_s78(lua_dir, aid, opt, mem, snap, log)
    if aid == "horn_hold": _HORN_RUN.append((str(opt or "start").strip().lower(), r))
    return r


def _horn_held(self, acts):
    """True while her hand is on the horn: the game's list says so, unless the Mind's own start/stop is newer than that list."""
    entry = next((a for a in acts or [] if isinstance(a, dict) and a.get("id") == "horn_hold"), None)
    if entry is None: return False
    mine = getattr(self, "_horn_mine", None)
    if mine is not None and mine[0] * 1000.0 > horn_catalog_time(self.dir):
        return mine[1] == "start" and time.time() - mine[0] < HORN_MIND_SECONDS
    return entry.get("state") == "holding"


_session_sheet_s78 = Chat._session_sheet


def _session_sheet_s79(self, snap, mem, acts):
    """The briefing sheet, rebuilt when whether she holds the horn changes."""
    held = self._horn_held(acts)
    got = getattr(self, "_sheet", None)
    if isinstance(got, dict) and got.get("horn") != held: self._sheet = None
    MR.HORN_HELD = held
    text = _session_sheet_s78(self, snap, mem, acts)
    if isinstance(getattr(self, "_sheet", None), dict): self._sheet["horn"] = held
    return text


_route_by_model_s78 = Chat._route_by_model


def _route_by_model_s79(self, history, c, key, snap, mem):
    """As before; a horn_hold the model chose gets her own line, and the Mind remembers whether her hand is on the horn."""
    del _HORN_RUN[:]
    reply = _route_by_model_s78(self, history, c, key, snap, mem)
    if not _HORN_RUN: return reply
    option, r = _HORN_RUN[-1]
    del _HORN_RUN[:]
    if isinstance(r, dict) and r.get("ok") is True:
        self._horn_mine = (time.time(), "stop" if option in HORN_STOP_OPTIONS else "start")
    line = horn_line(option, r)
    self.log("chat: horn_hold %s -> %s" % (option, str(r)[:90]))
    return reply if line is None else line


Chat._horn_held = _horn_held
Chat._session_sheet = _session_sheet_s79
Chat._route_by_model = _route_by_model_s79
'''


def mind(d):
    cs = os.path.join(d, "chat_service.py")
    t = open(cs, encoding="utf-8").read()
    assert "def _session_sheet" in t and "def _route_by_model" in t and "def resolve_and_run" in t, "not the Sol Mind: " + d
    print("model_router.py", append(os.path.join(d, "model_router.py"), MR))
    print("chat_service.py", append(cs, CS))


if __name__ == "__main__":
    mind(sys.argv[1])
    print("s79_horn_hold_mind applied")
