"""s85 Mind (Jamal 2026-11-10/11). Pairs with apply_s85_lua.py (SolExitFirst.lua, switch exit_first; GPS "اضغط سوقي").

1. The card within model_router.CARD_BUDGET (4600) with every switch on (05_TOOLS/sol_kahlua/card_check.py builds it from the full
   catalog, horn_hold listed, her hand on the horn or not): was 4999 / 5054. horn_hold: a short meaning, one example line per
   answer ("ضلك زمري / زرمي طول الطريق" start, "وقفي الزمور" stop, "بس" only while held), the duplicate "زمري" line and the held
   sentence gone; shorter intro and words; lines whose phrase says it all keep only the phrase ("water: | "اسقي الزرع"").
   Every game button on the card gets a short example (regroup, retreat, set_combat_doctrine, open_inventory, open_health,
   bandage). cars_near says it also works while she is far. "شوفي عنا بالمخزون" -> farm_report (live eval miss).
2. Two or three orders in one line, model first: the model may answer {"actions":[{...},{...}],"speech":""} (the one-action
   form stays valid). The Mind runs them in order through the same route, each one done before the next (exit_car: until the
   game's snapshot shows her out of the car, at most 15 s); a refusal ends the chain. Two examples on the card:
   "طفي المحرك ونزلي" -> sol_engine off, exit_car; "نزلي من السيارة وتعالي لعندي" -> exit_car, come_foot.
3. An on-foot order while she sits in a car (live 21:32:36 "رتاحي بالبيت" -> "ما قدرت: أنا بالسيارة، لازم انزل أول."): the
   game gets her out first and runs it after (SolExitFirst.lua); she says one line now ("ماشي، بنزل من السيارة أول." / stopping
   her drive first / waiting for his car to stand) and, when the game ran it, the order's own line (farm, role) or why not.
4. far_report: when a new far_report row appears in the farm's stop list (seq and time, once), one line in the chat
   ("وإنت برّا، سقيت الزرع وحطيت سماد.") instead of the in-game bubble only; it stays in her memory on the card for 6 hours.
Blocks appended at the end of model_router.py and chat_service.py (redefinitions); needs s82 installed first (it wraps s82's
sheet and route). Mind only; needs a Mind restart. In place, idempotent. Afterwards: card_check.py <mind> --write-doc.
usage: apply_s85_mind.py <sol_mind dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
MARK = "# ---------------------------------------------------------------- s85 card budget, two orders in one line, exit first, far report"
NEED = "# ---------------------------------------------------------------- s82 engine words, place questions, compact card"


def append(path, block):
    t = open(path, encoding="utf-8", newline="").read()
    if MARK in t: return "kept"
    assert NEED in t, "s82 is not installed in " + path
    nl = CRLF if CRLF in t else NL
    sep = "" if t.endswith(nl) else nl
    open(path, "w", encoding="utf-8", newline="").write(t + sep + nl + nl + (MARK + NL + block).replace(NL, nl))
    return "appended"


MR = r'''# The card within CARD_BUDGET with every switch on (horn_hold listed, her hand on it or not): shorter words, one example per
# horn answer, a short example for each game button, two orders in one line ("actions", in order), "شوفي عنا بالمخزون".
_INTRO_S85 = (("أنتِ سول: مرافقة حقيقية للاعب داخل لعبة Project Zomboid، امرأة، بتحكي بالشامي عن حالك بصيغة المؤنث، ومو بوت دردشة.",
               "أنتِ سول: رفيقته بلعبة Project Zomboid، امرأة، بتحكي شامي بصيغة المؤنث، ومو بوت دردشة."),
              ("مهمتك: اقرئي جملة اللاعب، حتى لو فيها أخطاء كتابة، واختاري فعل واحد من القائمة، الأقرب لقصدو. العقل بينفذ الفعل ويتأكد منه باللعبة، وهو اللي بيقول النتيجة، فلا تقولي إنك عملتِ شي.",
               "مهمتك: اقرئي جملته، حتى لو فيها أخطاء، واختاري من القائمة الأقرب لقصدو. العقل بينفذ وبيقول النتيجة، فلا تقولي إنك عملتِ شي."),
              ("- لا تكتبي إحداثيات أو أرقام مواقع بالكلام أبدًا." + chr(10) + "- احكي معه متل إنسان لإنسان: لا تقولي \"اللاعب\" ولا أي كلمة تقنية، ولا تبلشي كلامك باسمك.",
               "- احكي معه متل إنسان: بلا \"اللاعب\" ولا كلام تقني ولا أرقام مواقع، ولا تبلشي باسمك." + chr(10)
               + "- طلبين ورا بعض: \"actions\" بالترتيب، متل الأمثلة."))
for _old, _new in _INTRO_S85:
    if _old in CARD: CARD = CARD.replace(_old, _new)
_MEANING_S85 = {
    "follow": "تمشي وراه", "board_car": "تركب جنبه كراكبة",
    "animal_care": "تهتم بالدجاج: مي وأكل وبيض", "address_book": "دفتر عناوينها: بيوت ومخابئ شافتها، شو فيه أو تاخدو لعنوان",
    "survey": "تفحص البيت والزراعة والكراج وأماكن الشغل", "cars_near": "شو في سيارات حواليها، حتى لو بعيدة عنو",
    "secret_loadout": "نسخة من سلاحه السري مع ذخيرة", "refuel_at_station": "تعبي من الكازية", "farm_keeper": "تهتم بالمزرعة لحالها",
}
for _k, _v in _MEANING_S85.items():
    if _k in COMMANDS: COMMANDS[_k] = (_v, COMMANDS[_k][1])
# the phrase says it all: the line keeps the id and the phrase ("water: | \"اسقي الزرع\"")
PHRASE_ONLY_S85 = ("stay", "drive_stop", "exit_car", "set_home", "farm_stop", "harvest", "water", "cure", "weed", "fertilize", "plow",
                   "sort_stop", "animal_stop", "drive_home", "farm_short", "farm_status", "awake", "drive", "drive_marker", "go_home_rest",
                   "sort_items", "eggs", "plant")
# horn_hold: one example per answer; "زمري" is the list's own sol_horn example; "بس" only while her hand is on the horn (s79)
CARD_ACTIONS["horn_hold"] = ("إيدك عالزمور طول ما عم تسوقي", "خلي ايدك عالزمور", "option: start أو stop")
HORN_START = ("ضلك زمري", "زرمي طول الطريق")
HORN_STOP = ("وقفي الزمور",)
_HORN_DROP_S85 = ('زمري -> {"action":"sol_horn","args":{"option":"once"}}', "إيدك عالزمور هلأ: \"بس\" لحالها يعني شيلي إيدك عنه.")
# the game's own buttons: a short example each (the label stays as the game wrote it)
ARGS_NOTE.update({"regroup": '"تجمعي حدي"', "retreat": '"انسحبي"', "set_combat_doctrine": '"طبقي الخطة عالكل"',
                  "open_inventory": '"فرجيني شنتتك"', "open_health": '"افحصي صحتك"', "bandage": '"ضمدي جرحك"'})
SHOTS_S85 = ('شوفي عنا بالمخزون -> {"action":"farm_report"}',
             'طفي المحرك ونزلي -> {"actions":[{"action":"sol_engine","args":{"option":"off"}},{"action":"exit_car"}]}',
             'نزلي من السيارة وتعالي لعندي -> {"actions":[{"action":"exit_car"},{"action":"come_foot"}]}')
MAX_STEPS_S85 = 3
_sheet_s82 = sheet


def sheet(actions, memory):
    """The card as before, within the budget: horn lines as one answer each, phrase-only lines, the s85 examples."""
    text = _sheet_s82(actions, memory)
    n = chr(10)
    lines = []
    for line in text.split(n):
        if line in _HORN_DROP_S85: continue
        cid = line.split(": ", 1)[0]
        if cid in PHRASE_ONLY_S85 and cid in COMMANDS and ' | "' in line: line = '%s: | "%s"' % (cid, line.split(' | "', 1)[1].rstrip('"'))
        lines.append(line)
    text = n.join(lines)
    known = {a.get("id") for a in actions or [] if a.get("enabled", True)}
    shots = [s for s in SHOTS_S85 if not ("sol_engine" in s and actions and "sol_engine" not in known)]
    tail = n + n + "ذاكرتك الآن:"
    return text.replace(tail, n + n.join(shots) + tail, 1) if tail in text else text + n + n.join(shots)


def card_size(actions):
    return len(sheet(actions, "").rsplit(chr(10) + chr(10) + "ذاكرتك الآن:", 1)[0])


# "actions": two or three orders in one line, in order. The first is what parse() returns (every older path reads it);
# the whole list waits in LAST_STEPS for the chat, which runs the rest after the first has finished.
LAST_STEPS = []
_parse_s85_base = parse


def _one_step(d):
    if not isinstance(d, dict) or not isinstance(d.get("action"), str) or not d["action"].strip(): return None
    return {"action": d["action"].strip(), "args": d.get("args") if isinstance(d.get("args"), dict) else {}}


def parse(raw):
    """As before; a reply with "actions" (a list) reads as its first action, the rest go to LAST_STEPS."""
    del LAST_STEPS[:]
    text = re.sub(r"<think>.*?</think>", "", str(raw or ""), flags=re.S).strip()
    m = _JSON.search(text)
    d = None
    if m:
        try: d = json.loads(m.group(0))
        except ValueError: d = None
    if isinstance(d, dict) and isinstance(d.get("actions"), list) and not isinstance(d.get("action"), str):
        steps = [s for s in (_one_step(x) for x in d["actions"][:MAX_STEPS_S85]) if s]
        if not steps: return None
        LAST_STEPS.extend(steps)
        return {"action": steps[0]["action"], "args": steps[0]["args"], "speech": str(d.get("speech") or "").strip()}
    return _parse_s85_base(raw)
'''

CS = r'''# 1. Two or three orders in one line (the model's "actions"): run in order, each one finished before the next (her out of the car
#    before she walks); a refusal ends the chain and is what he hears.
# 2. An on-foot order while she sits in a car: the game gets her out first (SolExitFirst.lua, switch exit_first) and runs the
#    order after; she says so in one line now and the order's own line when it ran (or why it could not).
# 3. far_report (what she did while he was away): one line in the chat when a new report appears, and it stays in her memory.
import farm_talk as _FT85
STEP_WAIT_S85 = {"exit_car": 15.0}                                            # seconds the next step waits for this one at most
STEP_POLL_S85 = 0.5
_STEP_RESULTS = []
_EXIT_RUN = []
EXIT_FIRST_REASONS = ("leaving_car_first", "stopping_car_first", "waiting_car_stop")
EXIT_LINES = {
    "leaving_car_first": "ماشي، بنزل من السيارة أول.",
    "stopping_car_first": "ماشي، بوقف السيارة وبنزل أول.",
    "waiting_car_stop": "ماشي، بس توقف السيارة بنزل.",
}
EXIT_FAILED_LINE = "ما قدرت انزل من السيارة."
EXIT_WATCH_SECONDS = 180
FAR_BACK_PREFIX = "وإنت برّا، "
FAR_MEMORY_SECONDS = 6 * 3600
_run_action_s85_base = run_action


def run_action(lua_dir, action, option=None, wait=3.0):
    r = _run_action_s85_base(lua_dir, action, option, wait)
    _STEP_RESULTS.append(r)
    if isinstance(r, dict) and r.get("ok") and str(r.get("reason") or "") in EXIT_FIRST_REASONS:
        _EXIT_RUN.append((action, option, str(r.get("reason"))))
    return r


def _she_is_out(snap):
    sol = (snap or {}).get("sol")
    return isinstance(sol, dict) and sol.get("currentVehicle") is None


def _wait_step(self, step):
    """The next order waits until this one is done in the game (exit_car: she is out), at most STEP_WAIT_S85 seconds."""
    limit = STEP_WAIT_S85.get(step["action"])
    if not limit: return True
    end = time.time() + limit
    while True:
        try: snap = self._world()[0]
        except Exception: snap = None
        if _she_is_out(snap): return True
        if time.time() >= end: return False
        time.sleep(STEP_POLL_S85)


def _run_steps(self, history, c, key, snap, mem, steps, reply, route):
    """steps[0] has run (reply is its line); the rest run one by one through the same model route, as if the model chose each."""
    real = P.chat
    for i, step in enumerate(steps[1:], 1):
        if any(isinstance(r, dict) and (r.get("ok") is False or r.get("error")) for r in _STEP_RESULTS):
            self.log("chat: steps stop after %s (refused)" % steps[i - 1]["action"]); break
        if not _wait_step(self, steps[i - 1]):
            self.log("chat: step %s not seen done in time, %s goes on" % (steps[i - 1]["action"], step["action"]))
        del _STEP_RESULTS[:]
        answer = json.dumps(dict({"action": step["action"], "speech": ""}, **({"args": step["args"]} if step.get("args") else {})), ensure_ascii=False)
        P.chat = lambda *a, **k: answer
        try:
            try: now = self._world()[0] or snap
            except Exception: now = snap
            got = route(self, history, c, key, now, mem)
        finally:
            P.chat = real
        self.log("chat: step %d/%d %s -> %s" % (i + 1, len(steps), step["action"], str(got)[:60]))
        if got is None or got == ASK_AGAIN_S82: break
        reply = got
    return reply


_route_by_model_s84 = Chat._route_by_model


def _route_by_model_s85(self, history, c, key, snap, mem):
    """As before; several actions from the model run in order; an on-foot order she must leave the car for says so."""
    del MR.LAST_STEPS[:], _STEP_RESULTS[:], _EXIT_RUN[:]
    reply = _route_by_model_s84(self, history, c, key, snap, mem)
    steps = list(MR.LAST_STEPS)
    del MR.LAST_STEPS[:]
    if len(steps) > 1 and reply is not None and reply != ASK_AGAIN_S82:
        self.log("chat: %d steps: %s" % (len(steps), " then ".join(s["action"] for s in steps)))
        reply = _run_steps(self, history, c, key, snap, mem, steps, reply, _route_by_model_s84)
    if _EXIT_RUN:
        action, option, why = _EXIT_RUN[-1]
        self._exit_waiting = {"action": action, "option": option, "t": time.time(), "at": 0.0}
        self.log("chat: %s %s -> she gets out of the car first (%s)" % (action, option, why))
        reply = EXIT_LINES.get(why, EXIT_LINES["leaving_car_first"])
    del _EXIT_RUN[:]
    return reply


def exit_done_line(action, option, ok, why):
    """Her line once the game ran the order she left the car for; None when the order has nothing to add."""
    if why == "exit_failed": return EXIT_FAILED_LINE
    r = {"ok": ok, "reason": why}
    own = {"sol_farm": _FT85.reply_for, "sol_role": role_reply}.get(action)      # the orders with their own lines
    if own is not None: return own(option, r)
    if not ok: return reason_ar(why) or "ما قدرت عليها هلأ."
    return None


def _exit_watch(self):
    w = getattr(self, "_exit_waiting", None)
    if not w: return
    now = time.time()
    if now - w["t"] > EXIT_WATCH_SECONDS:
        self._exit_waiting = None; return
    if now - w["at"] < 2.0: return
    w["at"] = now
    r = _run_action_s85_base(self.dir, "sol_exit_first", "status", wait=2.0)
    why = str(r.get("reason") or "") if isinstance(r, dict) else ""
    if why == "pending" or not why.startswith(("done:", "idle")): return
    self._exit_waiting = None
    if why == "idle": return
    _, ok, rest = why.split(":", 2) if why.count(":") >= 2 else (why, "false", "")
    line = exit_done_line(w["action"], w["option"], ok == "true", rest)
    self.log("chat: exit_first %s %s done -> %s %s" % (w["action"], w["option"], ok, rest[:60]))
    if line: self._say_later(line)


_poll_once_s84 = Chat.poll_once


def _poll_once_s85(self):
    try: _exit_watch(self)
    except Exception as e: self.log("exit watch failed: %r" % (e,))
    return _poll_once_s84(self)


# far_report: the stop list's far_report row is said here, in the chat, once (its seq and its time); _farm_watch keeps the rest
_stop_line_s84 = _FT85.stop_line
_FAR_QUIET = []


def _stop_line_s85(stop):
    if _FAR_QUIET and isinstance(stop, dict) and stop.get("reason") == "far_report": return None
    return _stop_line_s84(stop)


_FT85.stop_line = _stop_line_s85
_farm_watch_s84 = Chat._farm_watch


def _farm_watch_s85(self, snap, mem):
    farm = (snap or {}).get("solFarm")
    news, fm = [], None
    if mem is not None and isinstance(farm, dict):
        fm = _FT85.FarmMemory(mem)
        rows = [r for r in (farm.get("stops") or [farm.get("stop") or {}]) if isinstance(r, dict) and r.get("seq")]
        seen = fm.data.get("stopSeen") or 0
        if rows and max(r["seq"] for r in rows) < seen: seen = 0                   # a new world counts from one again
        news = [r for r in rows if r.get("reason") == "far_report" and r["seq"] > seen and r.get("at") != fm.data.get("farReportAt")]
    _FAR_QUIET.append(1)
    try: out = _farm_watch_s84(self, snap, mem)
    finally: _FAR_QUIET.pop()
    if news:
        r = max(news, key=lambda x: x["seq"])
        line = _FT85.far_report_line(r.get("detail"))
        fm.data["farReportAt"] = r.get("at")
        fm.data["farReport"] = {"t": time.time(), "line": line} if line else None
        mem.save()
        self._sheet = None                                                     # her memory on the card changed
        self.log("chat: far_report seq=%s -> %s" % (r.get("seq"), line))
        if line: self._say_later(FAR_BACK_PREFIX + line)
    return out


_memory_text_s84 = Chat._memory_text


def _memory_text_s85(self, snap, mem):
    """As before, plus what she did while he was away (far_report), for a few hours after he is back."""
    text = _memory_text_s84(self, snap, mem)
    fr = ((mem.data.get("farm") or {}).get("farReport") if mem is not None else None) or {}
    if fr.get("line") and time.time() - float(fr.get("t") or 0) < FAR_MEMORY_SECONDS:
        text += " بغيابك: " + fr["line"]
    return text


Chat._route_by_model = _route_by_model_s85
Chat.poll_once = _poll_once_s85
Chat._farm_watch = _farm_watch_s85
Chat._memory_text = _memory_text_s85
'''


def mind(d):
    cs = os.path.join(d, "chat_service.py")
    assert "def _route_by_model" in open(cs, encoding="utf-8").read(), "not the Sol Mind: " + d
    print("model_router.py", append(os.path.join(d, "model_router.py"), MR))
    print("chat_service.py", append(cs, CS))


if __name__ == "__main__":
    mind(sys.argv[1])
    print("s85_mind applied")
