"""s78_cars_away_mind (Jamal 2026-11-10, 21:35 to 21:38), Mind side. Pairs with apply_s78_cars_away_lua.py.

1. cars_near in the third state, "her body is registered but away from him" (21:35, 21:36: "ما قدرت شوف شو في سيارات حواليّ").
   chat_service Chat._cars_near_answer, three states; the cars around HIM are never her answer:
     away  (sol.away: her square is not loaded): sol_far "cars", the game's saved rows around where she is. The Lua side now answers
           it with the far_car switch off too (read only). Head "cars:<n>/own|...": the switch is off, so far_cars_line does not offer
           to bring one of those cars (only her own car can come then).
     here  (her body is loaded, at any distance from him): snap.solVehicles, the loaded cars around HER.
     here, an older game side with no solVehicles: snap.vehicles (the cars around him) only when she stands within 10 tiles of him;
           otherwise the honest "I could not see" line.
2. come_car on the card (21:38:40 "سول هاتي السيارة وتعي لعندي" -> unknown): the canonical phrase is now "تعالي لعندي بالسيارة"
   (the Mind's own words parse it as fetch_player, so with her body near him she walks to him, as before); "تعالي بالسيارة" and
   "هاتي السيارة وتعي لعندي" are synonym examples. No new action; come_foot unchanged. When come_car is what the model chose, the
   far order is read as by car even if his own words had no car word; with no car to bring, the existing fallback brings her on
   foot and says so.
3. reply_gate (21:37:44: "سول هنصحك على بقية اللاعب" reached the chat): a model line holding meta words (اللاعب, player, NPC, mod,
   Lua, switch, script, ...), a code (Base.SmallCar, far_car, sol_far) or starting with her own name (his "سول ..." echoed back) is
   not speech: the whole line becomes "شو قصدك؟ عيدها بكلمة تانية." ("تكرم."-style after an action ran) and the route log names why.
   Coordinates stay s77's (the clause goes). The card also tells the model to talk to him as a person, never "اللاعب".
Every change is a block appended at the end of its file (redefinitions), so no earlier installer's text is touched and re-running
those stays a no-op. Mind only; needs a Mind restart. Needs apply_s77_mind.py first. In place, idempotent.
usage: apply_s78_cars_away_mind.py <sol_mind dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
MARK = "# ---------------------------------------------------------------- s78 cars_away"


def append(path, block):
    t = open(path, encoding="utf-8", newline="").read()
    if MARK in t: return
    nl = CRLF if CRLF in t else NL
    sep = "" if t.endswith(nl) else nl
    open(path, "w", encoding="utf-8", newline="").write(t + sep + nl + nl + (MARK + NL + block).replace(NL, nl))


MR = r'''# come_car: "تعالي لعندي بالسيارة" is its phrase; synonyms only, no new action. Talking to him as a person.
COMMANDS["come_car"] = (COMMANDS["come_car"][0], "تعالي لعندي بالسيارة")
EXAMPLES += (("تعالي بالسيارة", "come_car"), ("هاتي السيارة وتعي لعندي", "come_car"))
CARD += "\n- احكي معه متل إنسان لإنسان: لا تقولي \"اللاعب\" ولا أي كلمة تقنية، ولا تبلشي كلامك باسمك."
'''

RG = r'''# A line with these is the model talking about the game, not Sol talking to him: the whole line goes.
ASK_AGAIN = "شو قصدك؟ عيدها بكلمة تانية."
META_RX = re.compile(r"(?<![\w])(?:و|ف)?(?:ال|لل|بال|ل|ب)?لاعب(?:ين)?(?![\w])|(?<![\w])(?:ال)?(?:مود|سكربت|سكريبت|سويتش)(?![\w])"
                     r"|\b(?:player|players|npc|npcs|mod|mods|lua|switch|script|kahlua|snapshot|mailbox)\b", re.I)
CODE_RX = re.compile(r"\b[A-Za-z]+\.[A-Za-z][A-Za-z0-9]+\b|\b[a-z]+_[a-z0-9_]+\b")
OWN_NAME_RX = re.compile(r"^\W*(?:يا\s*)?سول(?![\w])")                          # his address echoed back; "أنا سول" stands


def not_speech(s):
    """Why a whole model line cannot be said (meta_line, code_line, names_herself), or None."""
    t = _norm(s)
    if META_RX.search(t): return "meta_line"
    if CODE_RX.search(t): return "code_line"
    if OWN_NAME_RX.search(t.strip()): return "names_herself"
    return None


_check_speech_s77 = check_speech


def check_speech(p, ctx, action_ran):
    """s78: the whole line is refused first when it is not speech; everything else as before (s77 and earlier)."""
    s = _norm(p.get("speech")).strip()
    bad = not_speech(s) if s else None
    if bad:
        ctx.stripped = [(bad, s)]
        return (random.choice(SAFE_NOTHING) if action_ran else ASK_AGAIN), bad
    return _check_speech_s77(p, ctx, action_ran)
'''

CS = r'''# The cars around HIM are never her answer. away -> sol_far "cars" (the game's saved rows, read only); here -> solVehicles.
HER_CARS_SAME_SPOT = 10
CARS_NOT_SEEN = "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي."
_far_cars_line_s77 = far_cars_line


def far_cars_line(reason):
    """s77's line; head "cars:<n>/own" (the far_car switch is off): no offer to bring one of those cars."""
    line = _far_cars_line_s77(reason)
    if "/own" in str(reason).partition("|")[0]: line = line.replace(" إذا بدك بجيك بوحدة منهن، قلي تعالي بالسيارة.", "")
    return line


def her_cars_snap(snap):
    """The snapshot with the cars around HER as its vehicles, or None when there is no true list of them.
    solVehicles (apply_s78_cars_away_lua.py) is around her body wherever he is; without it, the cars around him count only
    when she stands beside him."""
    s = snap or {}
    sol = s.get("sol") if isinstance(s.get("sol"), dict) else {}
    if sol.get("away") or sol.get("x") is None or sol.get("y") is None: return None
    if isinstance(s.get("solVehicles"), list): return dict(s, vehicles=s["solVehicles"])
    me = s.get("player") or {}
    if me.get("x") is None or me.get("y") is None: return None
    if math.hypot(sol["x"] - me["x"], sol["y"] - me["y"]) > HER_CARS_SAME_SPOT: return None
    return s


def _cars_near_answer_s78(self, snap):
    """cars_near, three states. away: the far list (sol_far cars). here: the loaded cars around her. Numbers go to the log only."""
    far_done = []
    if self._far_cars(snap, far_done):
        r = getattr(self, "_forced", None); self._forced = None
        return r or CARS_NOT_SEEN
    sol = (snap or {}).get("sol")
    if not snap or not isinstance(sol, dict):
        self.log("chat: cars near her -> no snapshot of her surroundings")
        return CARS_NOT_SEEN
    if sol.get("away"):
        self.log("chat: cars near her -> away, the game gave no list of the cars around her")
        return CARS_NOT_SEEN
    hers = her_cars_snap(snap)
    if hers is None:
        self.log("chat: cars near her -> she is away from him and the snapshot has no cars around her (solVehicles)")
        return CARS_NOT_SEEN
    self.log("chat: cars near her -> %s%s" % ("" if "solVehicles" in snap else "(beside him) ", near_cars_detail(hers)[:600]))
    return near_cars_line(hers)


Chat._cars_near_answer = _cars_near_answer_s78
_far_order_s77 = Chat._far_order


def _far_order_s78(self, text, snap, done, said=None):
    """come_car chosen by the model: his words ride along as `said`; the car is what he asked for even when they hold no car word."""
    if text == MR.COMMANDS["come_car"][1] and not _CAR_RX.search(said or ""): said = text + " " + (said or "")
    return _far_order_s77(self, text, snap, done, said)


Chat._far_order = _far_order_s78
'''


def mind(d):
    assert "def _cars_near_answer" in open(os.path.join(d, "chat_service.py"), encoding="utf-8").read(), "apply_s77_mind.py first"
    append(os.path.join(d, "model_router.py"), MR)
    append(os.path.join(d, "reply_gate.py"), RG)
    append(os.path.join(d, "chat_service.py"), CS)


if __name__ == "__main__":
    mind(sys.argv[1])
    print("s78_cars_away_mind applied")
