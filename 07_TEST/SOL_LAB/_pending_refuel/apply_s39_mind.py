"""The full review of 2026-11-09, Sol Mind side. All or nothing.
usage: apply_s39_mind.py <sol_mind dir>"""
import os, sys
D = sys.argv[1]
EDITS = {}
def E(f, a, b): EDITS.setdefault(f, []).append((a, b))

# ---------------------------------------------------------------- the gate: only the bad clause goes
E("reply_gate.py", '''def about_the_world(text):
    t = _norm(text).lower()
    return any(w in t for w in WORLD_WORDS)
''', '''_WORLD_ENDS = ("", "نا", "ي", "ك", "ه", "ها", "كم", "هم", "ات", "ين")
_WORLD_FORMS = set()
for _w in WORLD_WORDS:
    for _e in _WORLD_ENDS:
        _WORLD_FORMS.add(_w + _e)
        if _w.endswith("ة") and _e: _WORLD_FORMS.add(_w[:-1] + "ت" + _e)          # مدينة -> مدينتنا


def _is_world_word(w):
    """A whole word, with the letters Arabic glues on: بيتنا and ببيت count, خبيت and طريقة do not."""
    if w in _WORLD_FORMS: return True
    return any(w.startswith(c) and w[len(c):] in _WORLD_FORMS for c in _CLITICS)


def about_the_world(text):
    return any(_is_world_word(w) for w in _TOKEN.findall(_norm(text).lower()))


_NEGATIONS = {"ما", "مو", "مش", "لسا", "لسه", "ماني", "مالي"}


def claims_an_action(s):
    """A word saying she did something, whole-word from the start (فرحت is not رحت) and not negated (ما وصلت is not a claim)."""
    words = _TOKEN.findall(_norm(s).lower())
    for i, w in enumerate(words):
        bare = w[1:] if w.startswith("و") and len(w) > 3 else w
        if any(w.startswith(c) or bare.startswith(c) for c in CLAIM_STEMS) and not (i > 0 and words[i - 1] in _NEGATIONS): return True
    return False
''')
E("reply_gate.py", '''def check_speech(p, ctx, action_ran):
    """(speech, why). why is None when the line stands."""
    s = _norm(p.get("speech")).strip()
    if not s: return random.choice(SAFE_NOTHING), "empty"
    if len(s) > MAX_SPEECH: return random.choice(SAFE_UNKNOWN), "too_long"
    if mojibake(s): return random.choice(SAFE_UNKNOWN), "mojibake"
    if s.startswith("{") or "[" in s or "(" in s or "（" in s: return random.choice(SAFE_UNKNOWN), "not_speech"
    if any(w.lower() in s.lower() for w in BANNED): return random.choice(SAFE_UNKNOWN), "meta_words"
    if speaks_to_herself(s): return random.choice(SAFE_UNKNOWN), "speaks_to_herself"
    known = _norm(ctx.known_text)
    world = about_the_world(s)
    named, invented = False, []
    s, ctx.fixes, named, invented = resolve_names(s, ctx.names, known)
    if not world: named, invented = False, []
    for n in _NUM.findall(s):
        if n not in known: return random.choice(SAFE_UNKNOWN), "number_not_known:" + n
    if world and not named and not grounded(s, known): return random.choice(SAFE_UNKNOWN), "world_claim_not_known"
    if invented: return random.choice(SAFE_UNKNOWN), "invented_name:" + invented[0]
    if not action_ran and any(c in s for c in CLAIM_STEMS): return random.choice(SAFE_NOT_DONE), "claims_an_action"
    return s, None
''', '''_CLAUSE = re.compile(r"((?:[،؛,;!?؟…\\n]|(?<!\\d)\\.|\\.(?!\\d))+)")
ALONE_OK = {"مرحبا", "اهلا", "أهلا", "اهلين", "أهلين", "هلا", "ماشي", "تكرم", "ايه", "إيه", "لأ", "لا", "حاضر", "طيب", "تمام", "اكيد", "أكيد"}
LEANS_ON_WHAT_WENT = ("لأن", "لان", "عشان", "لهيك", "لذلك")
TRIM_FIRST = ("بس", "لكن")


def _clause_fault(c, ctx, known, action_ran, named_in_line):
    """(why, the clause with spellings put right, the safe lines to use if nothing else of the reply survives). why is None when it stands."""
    if "[" in c or "(" in c or "（" in c: return "not_speech", c, SAFE_UNKNOWN
    if any(w.lower() in c.lower() for w in BANNED): return "meta_words", c, SAFE_UNKNOWN
    if speaks_to_herself(c): return "speaks_to_herself", c, SAFE_UNKNOWN
    world = about_the_world(c)
    fixed, fixes, named, invented = resolve_names(c, ctx.names, known)
    ctx.fixes = list(ctx.fixes) + list(fixes)
    if not world: named, invented = False, []
    for n in _NUM.findall(fixed):
        if n not in known: return "number_not_known:" + n, c, SAFE_UNKNOWN
    if world and not (named or named_in_line) and not grounded(fixed, known): return "world_claim_not_known", c, SAFE_UNKNOWN
    if invented: return "invented_name:" + invented[0], c, SAFE_UNKNOWN
    if not action_ran and claims_an_action(fixed): return "claims_an_action", c, SAFE_NOT_DONE
    return None, fixed, None


def check_speech(p, ctx, action_ran):
    """(speech, why). why is None when something of the line stands; ctx.stripped lists the clauses that were taken out."""
    s = _norm(p.get("speech")).strip()
    ctx.stripped = []
    if not s: return random.choice(SAFE_NOTHING), "empty"
    if len(s) > MAX_SPEECH: return random.choice(SAFE_UNKNOWN), "too_long"
    if mojibake(s): return random.choice(SAFE_UNKNOWN), "mojibake"
    if s.startswith("{"): return random.choice(SAFE_UNKNOWN), "not_speech"
    known = _norm(ctx.known_text)
    named_in_line = about_the_world(s) and resolve_names(s, ctx.names, known)[2]     # a real place named anywhere grounds the numbers beside it: "كازية X، 300 متر"
    parts = _CLAUSE.split(s)
    kept, first_fault = [], None
    for i in range(0, len(parts), 2):
        raw, delim = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
        clause = raw.strip()
        if not clause:
            if kept: kept[-1] = (kept[-1][0], kept[-1][1] + raw + delim)
            continue
        why, fixed, safe = _clause_fault(clause, ctx, known, action_ran, named_in_line)
        if why:
            ctx.stripped.append((why, clause))
            first_fault = first_fault or (why, safe)
            continue
        kept.append((raw.replace(clause, fixed), delim))
    if first_fault is None: return "".join(c + d for c, d in kept).strip(), None
    if kept:
        head = kept[0][0].strip().split()
        if head and head[0] in LEANS_ON_WHAT_WENT: kept.pop(0)
        elif head and head[0] in TRIM_FIRST and len(head) > 1: kept[0] = (" ".join(head[1:]), kept[0][1])
    text = "".join(c + d for c, d in kept).rstrip("،,؛; \\n").strip()
    words = re.findall(r"[\\w']+", text)
    bare_ack = all(w in ALONE_OK for w in words)
    if not words or (len(words) == 1 and words[0] not in ALONE_OK) or (bare_ack and is_question(ctx.user_text)):
        return random.choice(first_fault[1]), first_fault[0]
    return text, None
''')
E("chat_service.py", '''        if rejected: self.log("gate: rejected (%s): %s" % (rejected, str(p.get("speech"))[:120]))
''', '''        if rejected: self.log("gate: rejected (%s): %s" % (rejected, str(p.get("speech"))[:120]))
        elif getattr(ctx, "stripped", None): self.log("gate: stripped %s | kept: %s" % ("; ".join("(%s) %s" % x for x in ctx.stripped)[:160], speech[:120]))
''')
E("chat_service.py", '''        return self._through_the_gate(reply, history, acts, mem, snap, sysp + " ".join(tool_notes), names)
''', '''        facts = W.situation_text(snap, mem) + " " + json.dumps(self.gps_state() or {}, ensure_ascii=False) + " " + (known or "") + " " + " ".join(tool_notes)   # what she has been told about the world, not her character sheet
        return self._through_the_gate(reply, history, acts, mem, snap, facts, names)
''')

# ---------------------------------------------------------------- home
E("chat_service.py", '''_HERE_WORD = r"(?:هذا|هنا|هذه|هاد|هادا|هيدا|هاي|هون|هنيك)"''', '''_HERE_WORD = r"(?:هذا|هنا|هذه|هاد|هادا|هيدا|هاي|هون)"''')
E("chat_service.py", '''HOME_RX = re.compile(_HERE_WORD + r"(?:\\s+(?:المكان|المحل|الموقع))?\\s+(?:هو\\s+|هي\\s+)?(?:بيتنا|منزلنا|بيتي|مخيمنا|دارنا)|''',
  '''HOME_NOT_RX = re.compile(r"(?:^|\\s)(?:مو|مش|ما|مانو|ليس|مالي)\\s+(?:بدي\\s+)?" + _HERE_WORD + r"|(?:^|\\s)ما\\s+بدي\\b")
HOME_RX = re.compile(_HERE_WORD + r"(?:\\s+(?:المكان|المحل|الموقع|البيت))?(?:\\s+رح\\s+يكون)?\\s+(?:هو\\s+|هي\\s+)?(?:بيتنا|منزلنا|بيتي|مخيمنا|دارنا|البيت(?=\\s*[.!،]*$))|''')
E("chat_service.py", '''    if HOME_RX.search(t): out.append(("set_home", {"name": "بيتنا"}))''', '''    if HOME_RX.search(t) and not RG.is_question(t) and not HOME_NOT_RX.search(t): out.append(("set_home", {"name": "بيتنا"}))''')
E("chat_service.py", '''            if name == "set_home" and isinstance(r, dict) and r.get("home"): self._forced = "تمام، صار هون بيتنا."
''', '''            if name == "set_home" and isinstance(r, dict) and r.get("home"):
                self._forced = "تمام، صار هون بيتنا."
                self.log("chat: home in the game -> %s" % run_action(self.dir, "sol_set_home", None, wait=2.0))       # the game's own "go home" and the farm read this one
''')
E("chat_service.py", '''            r = W.run_tool(name, args, snap, mem, W.load_recipes(self.dir)); self.log("chat: tool %s -> %s" % (name, str(r)[:120]))
            tool_notes.append(json.dumps(r, ensure_ascii=False))
''', '''            r = W.run_tool(name, args, snap, mem, W.load_recipes(self.dir)); self.log("chat: tool %s -> %s" % (name, str(r)[:120]))
            if name == "set_home" and isinstance(r, dict) and r.get("home"): run_action(self.dir, "sol_set_home", None, wait=2.0)
            tool_notes.append(json.dumps(r, ensure_ascii=False))
''')
E("chat_service.py", '''def drive_to(lua_dir, args, mem):
''', '''def drive_to(lua_dir, args, mem, snap=None):
''')
E("chat_service.py", '''        h = mem.data.get("home")
        if not h: return {"error": "home not set"}
''', '''        h = mem.data.get("home")
        if not h and isinstance((snap or {}).get("solHome"), dict) and snap["solHome"].get("x") is not None: h = snap["solHome"]   # the home or base he set in the game
        if not h: return {"error": "home_not_set"}
''')
E("chat_service.py", '''        return drive_to(lua_dir, args, mem)
''', '''        return drive_to(lua_dir, args, mem, snap)
''')
E("chat_service.py", '''                r = drive_to(self.dir, args, mem); self._turn_action_results.append(r)
''', '''                r = drive_to(self.dir, args, mem, snap); self._turn_action_results.append(r)
''')
E("chat_service.py", '''    "no_vehicle_near": "لا توجد سيارة قريبة",
''', '''    "no_vehicle_near": "ما في سيارة قريبة",
    "vehicle is not in the loaded world": "السيارة بعيدة عني هلأ",
    "hotwiring": "ما في مفتاح، رح شرّطها، وبس خلّص قلي نمشي",
''')
E("chat_service.py", '''    "home_not_set": "لم نحدد بيتنا بعد",
''', '''    "home_not_set": "لسا ما حددنا بيتنا",
''')

# ---------------------------------------------------------------- parking
E("chat_service.py", '''MOVE_ORDERS = frozenset(("drive_take_wheel", ''', '''MOVE_ORDERS = frozenset(("park_car", "drive_take_wheel", ''')
E("chat_service.py", '''            if name in ("action", "drive_take_wheel", "drive_stop", "drive_to"): self._stop_farm_if_running(snap)
''', '''            if name in ("action", "drive_take_wheel", "drive_stop", "drive_to", "park_car"): self._stop_farm_if_running(snap)
''')
E("chat_service.py", '''        self._forced = "رايحة صفها بالكراج." if r.get("ok") or str(r.get("reason")) in ("moving_to_wheel", "walking_to_door") else drive_reply(r)
''', '''        started = r.get("ok") or str(r.get("reason")) in ("moving_to_wheel", "walking_to_door")
        self._forced = "رايحة صفها بالكراج." if started else drive_reply(r)
        self._park_waiting = {"t": time.time()} if started else None

    def _say_later(self, line):
        """A line that comes after the turn that asked for it."""
        with self.lock: self.hist.append({"role": "sol", "text": line, "t": time.time()})
        self._save(); self.publish()

    def _park_watch(self):
        """She promised to park: he hears how it ended, and the car ends up inside the marked area, not some tiles short."""
        w = getattr(self, "_park_waiting", None)
        if not w: return
        if w.get("phase") == "settle":
            r = run_action(self.dir, "sol_errand_park_status", None, wait=2.5)
            if not (isinstance(r, dict) and r.get("ok")) or r.get("reason") == "done" or time.time() - w["since"] > 60:
                self._park_waiting = None
                self._say_later("صفيتها.")
            return
        if time.time() - w["t"] > 600:
            self._park_waiting = None
            return
        g = self.gps_state() or {}
        result, reason = str(g.get("result") or ""), str(g.get("reason") or "")
        if result == "arrived" and reason in ("arrived", ""):
            r = run_action(self.dir, "sol_errand_park", None, wait=2.5)
            if isinstance(r, dict) and r.get("ok"): w.update(phase="settle", since=time.time())
            else:
                self._park_waiting = None
                self._say_later("وصلنا عالكراج.")
        elif result in ("failed", "interrupted") and reason not in ("walking_to_door", "moving_to_wheel", "await_destination", "board_passenger", ""):
            self._park_waiting = None
            if "player" not in reason: self._say_later(drive_reply({"ok": False, "reason": reason}))
''')
E("chat_service.py", '''                try: self._far_watch()
                except Exception as e: self.log("far watch failed: %r" % (e,))
''', '''                try: self._far_watch()
                except Exception as e: self.log("far watch failed: %r" % (e,))
            for watch in (self._park_watch, self._farm_pending_watch):
                try: watch()
                except Exception as e: self.log("%s failed: %r" % (watch.__name__, e))
''')

# ---------------------------------------------------------------- far
E("chat_service.py", '''        if (snap or {}).get("sol"): return None
        r = run_action(self.dir, "sol_far", "status", wait=2.5)
''', '''        if (snap or {}).get("sol") and not snap["sol"].get("away"): return None
        r = run_action(self.dir, "sol_far", "status", wait=2.5)
''')
E("chat_service.py", '''        elif reason == "placed" and mode != "car": self._far_waiting = False
''', '''        elif reason == "placed" and mode != "car": self._far_waiting = False
        elif reason == "idle": self._far_waiting = False                         # a reload ended it: nothing failed
''')

# ---------------------------------------------------------------- an order the paused game has not read yet
E("chat_service.py", '''def run_action(lua_dir, action, option=None, wait=3.0):
    rid = write_request(os.path.join(lua_dir, ACT_REQ), {"action": action, "option": option or None})
    end = time.time() + wait
    while time.time() < end:
        try:
            with open(os.path.join(lua_dir, ACT_STATE), encoding="ascii", errors="replace") as f:
                st = dict(l.split("=", 1) for l in f.read().splitlines() if "=" in l)
            if st.get("ack") == str(rid): return {"ok": st.get("ok") == "true", "reason": unesc(st.get("reason", ""))}
            if ("r%s" % rid) in st:                                              # another sender's answer came after ours
                ok, _, why = st["r%s" % rid].partition("|")
                return {"ok": ok == "true", "reason": unesc(why)}
        except OSError: pass
        time.sleep(0.1)
    return {"ok": None, "reason": "sent; the game did not confirm yet"}
''', '''def action_result(lua_dir, rid):
    """The game's answer to request rid, or None while it has not answered."""
    try:
        with open(os.path.join(lua_dir, ACT_STATE), encoding="ascii", errors="replace") as f:
            st = dict(l.split("=", 1) for l in f.read().splitlines() if "=" in l)
    except OSError: return None
    if st.get("ack") == str(rid): return {"ok": st.get("ok") == "true", "reason": unesc(st.get("reason", ""))}
    if ("r%s" % rid) in st:                                                      # another sender's answer came after ours
        ok, _, why = st["r%s" % rid].partition("|")
        return {"ok": ok == "true", "reason": unesc(why)}
    return None

def run_action(lua_dir, action, option=None, wait=3.0):
    rid = write_request(os.path.join(lua_dir, ACT_REQ), {"action": action, "option": option or None})
    end = time.time() + wait
    while time.time() < end:
        r = action_result(lua_dir, rid)
        if r is not None: return r
        time.sleep(0.1)
    return {"ok": None, "reason": "sent; the game did not confirm yet", "rid": rid}
''')
E("chat_service.py", '''        self.log("chat: farm order %s %s -> %s" % (action, option, r))
''', '''        self.log("chat: farm order %s %s -> %s" % (action, option, r))
        if action == "sol_farm" and isinstance(r, dict) and r.get("ok") is None and r.get("rid"):  # the game is paused: the slot is kept for it and he hears the outcome when it runs
            self._farm_pending = {"rid": r["rid"], "option": option, "t": time.time()}
''')
E("chat_service.py", '''    def _farm_running(self, snap):
''', '''    def _farm_pending_watch(self):
        w = getattr(self, "_farm_pending", None)
        if not w: return
        if time.time() - w["t"] > 900:
            self._farm_pending = None
            return
        r = action_result(self.dir, w["rid"])
        if r is None: return
        self._farm_pending = None
        import farm_talk as FT
        self.log("chat: farm order %s answered late -> %s" % (w["option"], r))
        self._say_later(FT.reply_for(w["option"], r))

    def _farm_running(self, snap):
''')
E("chat_service.py", '''    def _street_now(self):
        r = run_action(''', '''    def _street_now(self):
        if getattr(self, "_farm_pending", None): return None                     # one request slot: a background question must not replace his order
        r = run_action(''')
E("chat_service.py", '''    def _station_list(self):
        r = run_action(''', '''    def _station_list(self):
        if getattr(self, "_farm_pending", None): return None
        r = run_action(''')

# ---------------------------------------------------------------- the farm's words
E("chat_service.py", '''        stop = farm.get("stop") or {}
        seq = stop.get("seq") or 0
        if seq and seq != fm.data.get("stopSeen"):
            fm.data["stopSeen"] = seq
            changed = True
            line = FT.stop_line(stop)
            if line: lines.insert(0, line)
''', '''        rows = [r for r in (farm.get("stops") or [farm.get("stop") or {}]) if isinstance(r, dict) and r.get("seq")]
        top = max([r["seq"] for r in rows] or [0])
        seen = fm.data.get("stopSeen") or 0
        if top and top != seen:
            if top < seen: seen = 0                                              # a new world counts from one again
            fm.data["stopSeen"] = top
            changed = True
            said = []
            for r in sorted(rows, key=lambda x: x["seq"]):
                if r["seq"] <= seen or (r.get("reason") == "waiting" and (r.get("detail") or {}).get("why") == "paused"): continue   # the ending of a job whose real reason is the row before
                line = FT.stop_line(r)
                if line and line not in said: said.append(line)
            lines[:0] = said
''')
E("farm_talk.py", '''(?:هون\\s+)?(?:ب|في\\s+|فال|عل[يا]\\s+)?(?:ال)?(?:بيت|دار|منزل|قاعده)\\b"''', '''(?:هون\\s+|ا?رتاحي\\s+|ريحي\\s+)?(?:ب|في\\s+|فال|عل[يا]\\s+)?(?:ال)?(?:بيت|دار|منزل|قاعده)\\b"''')
E("farm_talk.py", '''(?:ارتاحي|ريحي|استريحي|نامي|اتريحي)\\s+(?:ب|في\\s+|عال?)?''', '''(?:ا?رتاحي|ريحي|استريحي|نامي|اتريحي)\\s+(?:ب|في\\s+|عال?)?''')
E("farm_talk.py", '''HOME_REST_WORD = re.compile(r"(?:ارتاحي|ريحي|''', '''HOME_REST_WORD = re.compile(r"(?:ا?رتاحي|ريحي|''')
E("farm_talk.py", '''WHY_AR = {
''', '''WHY_AR = {
    "body_busy": "كنت مشغولة بشي تاني وما قدرت أوصل", "target_unloaded": "المكان بعيد عنك وما بقدر أوصلو هلأ",
''')
E("farm_talk.py", '''    if cmd == "storage": return storage_line(''', '''    if cmd in ("short", "storage") and why == "not_ready": return "لسا عم اتفقد المخازن، اسألني كمان شوي."
    if cmd == "storage": return storage_line(''')
E("farm_talk.py", '''    if cmd in ACK: return ack(option)
''', '''    if cmd == "home" and "farmhome" in why: return random.choice(ACK["both"])
    if cmd in ACK: return ack(option)
''')
E("farm_talk.py", '''    if not seeds and not fert:
        parts.append(''', '''    if stock.get("ready") is False:
        parts.append("لسا عم اتفقد المخازن.")
    elif not seeds and not fert:
        parts.append(''')
E("farm_talk.py", '''    if report.get("shortages"): parts.append(shortages_text(report["shortages"]))
''', '''    if report.get("shortages") and stock.get("ready") is not False: parts.append(shortages_text(report["shortages"]))
''')
E("farm_talk.py", '''        if r.get("storage"): stores.append("مكان فيه فراغ للأكل" if r["storage"] == "food" else "مكان للمحصول"); continue
''', '''        if r.get("storage"): (unsure if r.get("unsure") else stores).append("مكان فيه فراغ للأكل" if r["storage"] == "food" else "مكان للمحصول"); continue
''')

# ---------------------------------------------------------------- walking to the door is not a failure
E("goal_engine.py", '''    WAITING=("moving_to_wheel","await_destination","board_passenger","")
''', '''    WAITING=("moving_to_wheel","walking_to_door","await_destination","board_passenger","")
''')
E("goal_engine.py", '''            if result=="failed" and reason not in ("moving_to_wheel","await_destination","board_passenger",""):
''', '''            if result=="failed" and reason not in ("moving_to_wheel","walking_to_door","await_destination","board_passenger",""):
''')
E("goal_engine.py", '''            if result=="failed" and reason not in ("board_passenger","moving_to_wheel","await_destination",""):
''', '''            if result=="failed" and reason not in ("board_passenger","moving_to_wheel","walking_to_door","await_destination",""):
''')

if len(sys.argv) > 2 and sys.argv[2] == "--verify":          # every edit is in the deployed files
    missing = 0
    for f, pairs_ in EDITS.items():
        t = open(os.path.join(D, f), encoding="utf-8", newline="").read().replace(chr(13) + chr(10), chr(10))
        for a, b in pairs_:
            if t.count(b) < 1: missing += 1; print("MISSING", f, b[:70])
    print("verified", sum(len(v) for v in EDITS.values()), "edits, missing", missing)
    sys.exit(1 if missing else 0)
out = {}
for f, pairs_ in EDITS.items():
    p = os.path.join(D, f)
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b in pairs_:
        a2, b2 = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a2) == 1, (f, a[:70], t.count(a2))
        t = t.replace(a2, b2)
    compile(t, p, "exec")
    out[p] = t
for p, t in out.items(): open(p, "w", encoding="utf-8", newline="").write(t)
print("applied", sum(len(v) for v in EDITS.values()), "edits to", len(out), "files in", D)
