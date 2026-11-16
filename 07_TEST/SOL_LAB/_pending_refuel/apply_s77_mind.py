"""s77_mind (Jamal 2026-11-10 20:41): "شوفي سيارات حوليكي" went to survey, which answered "البيت محدد عند 7411,8258. مكان صف السيارات عند 7413,8264. ..."
(coordinates in chat, and not what he asked).

1. model_router: ONE new card action cars_near ("which cars are around HER"), with its own examples; survey ("scan the place") keeps its own and
   no longer lists cars in its meaning. The card tells the model never to speak coordinates. No keyword override: the old far_car word match
   that overrode the model's "none" is gone (the word lists still answer when no model is connected, as before).
2. chat_service: cars_near works in both states.
     far  : the existing far_car scan (_far_cars -> sol_far cars -> far_cars_line).
     here : the live world snapshot (SolWorld_Snapshot.txt 'vehicles': name, x, y, fuel, fuelMax, and with apply_s77_lua.py also locked, key),
            distance measured from HER. near_cars_line words it: car names (vehicle_ar), how far in words (جنبي / قريبة / بآخر الشارع),
            and whether usable (مسكّرة / ما معي مفتاحها / ما فيها بنزين / جاهزة). No tiles, litres, coordinates or ids: those go to the log.
   far_cars_line shares the same names, distance words and the words جاهزة / مسكّرة (redefined after the s65/s72 one, whose text is left
   as it was, so re-running earlier installers stays a no-op).
3. No coordinates in anything that reaches chat: survey (also no tile counts), the memory line the model reads ("بيتنا عند x,y"),
   reply_gate.check_speech strips any clause holding a coordinate pair, and clean_reply (the last step before every chat reply) drops
   any sentence still holding one. Internal options for game actions (resolve_and_run, car_far:...) keep their numbers.
4. sol_templates.vehicle_ar knows the common vanilla car types; an unknown type is "سيارة", never an English script id.
Mind only; needs a Mind restart. In place, idempotent (edit by anchor).
usage: apply_s77_mind.py <sol_mind dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)


def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))


# ---------------------------------------------------------------- model_router.py: the card
MR = [
    ('    "survey":        ("تفحص البيت والمكان: زراعة، كراج، سيارات، أماكن شغل", None),\n',
     '    "survey":        ("تفحص البيت والمكان كلو: البيت، الزراعة، الكراج، أماكن الشغل", None),\n'
     '    "cars_near":     ("تقلو شو في سيارات حواليها هي: أساميها، قديش بعيدة، وإذا بتمشي", None),     # s77: her surroundings, far or here\n'),
    ('EXTRA_EXAMPLE = {"survey": "فحصي المكان", ',
     'EXTRA_EXAMPLE = {"survey": "فحصي المكان", "cars_near": "شوفي سيارات حواليكي", '),
    ('            ("جيبيلي سلاحي السري", "secret_loadout"), ("بدي أسلحتي السرية", "secret_loadout"))\n',
     '            ("جيبيلي سلاحي السري", "secret_loadout"), ("بدي أسلحتي السرية", "secret_loadout"))\n'
     'EXAMPLES += (("شوفي سيارات حواليكي", "cars_near"), ("شو في سيارات حواليكي", "cars_near"), ("في سيارة قريبة؟", "cars_near"),   # s77\n'
     '             ("في شي سيارة جنبك؟", "cars_near"), ("شو السيارات اللي حولك", "cars_near"))\n'),
    ('من الذاكرة بس. لا تذكري مكان أو رقم مو مكتوب تحت."""',
     'من الذاكرة بس. لا تذكري مكان أو رقم مو مكتوب تحت.\n- لا تكتبي إحداثيات أو أرقام مواقع بالكلام أبدًا."""'),
]

# ---------------------------------------------------------------- sol_templates.py: car names
TPL = [
    ('VEHICLES = [("trooper", "التروبر"), ("ford", "الفورد"), ("trailer", "المقطورة"), ("astrodome", "المقطورة"), ("van", "الفان"), ("pickup", "البيك أب"), ("truck", "الشاحنة")]\n',
     'VEHICLES = [("ambulance", "سيارة الإسعاف"), ("police", "سيارة الشرطة"), ("fire", "سيارة الإطفاء"), ("taxi", "التاكسي"), ("bradley", "البرادلي"), ("heli", "الهليكوبتر"),   # s77\n'
     '            ("trooper", "التروبر"), ("ford", "الفورد"), ("trailer", "المقطورة"), ("astrodome", "المقطورة"), ("van", "الفان"), ("pickup", "البيك أب"), ("truck", "الشاحنة"),\n'
     '            ("sportscar", "السيارة الرياضية"), ("luxury", "السيارة الفخمة"), ("offroad", "الجيب"), ("suv", "الجيب"), ("stationwagon", "الستيشن"),\n'
     '            ("smallcar", "السيارة الصغيرة"), ("moderncar", "السيارة الحديثة"), ("carnormal", "السيارة العادية")]\n'),
]

# ---------------------------------------------------------------- reply_gate.py: no coordinates in model speech
RG = [
    ('_NUM = re.compile(r"\\d+")\n',
     '_NUM = re.compile(r"\\d+")\n'
     '# s77: a map position ("7411,8258", "x 7411 y 8258") is never speech, whatever the model was shown\n'
     'COORD_RX = re.compile(r"(?<![\\d.])\\d{3,5}(?:\\.\\d+)?\\s*[,،]\\s*\\d{3,5}(?:\\.\\d+)?(?:\\s*[,،]\\s*-?\\d{1,2})?(?![\\d])|\\b[xX]\\s*[=:]?\\s*\\d{3,5}\\D{0,6}?\\b[yY]\\s*[=:]?\\s*\\d{3,5}")\n'
     '_COORD_MARK = "\\ue000"\n'
     '_SENTENCE = re.compile(r"((?:[!?؟…\\n]|(?<!\\d)\\.|\\.(?!\\d))+)")\n'
     '\n'
     '\n'
     'def drop_coordinates(text):\n'
     '    """Any sentence holding a map position is taken out. If nothing would be left, only the position (and the word before it) goes."""\n'
     '    t = str(text or "")\n'
     '    if not COORD_RX.search(_norm(t)): return t\n'
     '    parts = _SENTENCE.split(t)\n'
     '    kept = "".join(parts[i] + (parts[i + 1] if i + 1 < len(parts) else "") for i in range(0, len(parts), 2) if not COORD_RX.search(_norm(parts[i])))\n'
     '    kept = kept.strip()\n'
     '    if kept: return kept\n'
     '    bare = re.sub(r"(?:\\s+(?:عند|على|عل|ب|في|بـ|at))?\\s*" + COORD_RX.pattern, "", _norm(t))\n'
     '    return re.sub(r"\\s+([.،,؟?!])", r"\\1", re.sub(r"[ \\t]{2,}", " ", bare)).strip()\n'),
    ('def _clause_fault(c, ctx, known, action_ran, named_in_line):\n'
     '    """(why, the clause with spellings put right, the safe lines to use if nothing else of the reply survives). why is None when it stands."""\n',
     'def _clause_fault(c, ctx, known, action_ran, named_in_line):\n'
     '    """(why, the clause with spellings put right, the safe lines to use if nothing else of the reply survives). why is None when it stands."""\n'
     '    if _COORD_MARK in c: return "coordinates", c.replace(_COORD_MARK, "x,y"), SAFE_UNKNOWN     # s77\n'),
    ('    if s.startswith("{"): return random.choice(SAFE_UNKNOWN), "not_speech"\n',
     '    if s.startswith("{"): return random.choice(SAFE_UNKNOWN), "not_speech"\n'
     '    s = COORD_RX.sub(_COORD_MARK, s)                                            # s77: the clause holding it is stripped below\n'),
]

# ---------------------------------------------------------------- chat_service.py
CS = [
    # after far_cars_line (left as s65/s72 wrote it, so re-running those stays a no-op): the s77 block, which redefines it with the shared words
    ('    if any(v == "ok" for _i, _s, _d, _f, v, _m in rows): out.append("إذا بدك بجيك بوحدة منهن، قلي تعالي بالسيارة.")\n'
     '    return " ".join(out)\n',
     '    if any(v == "ok" for _i, _s, _d, _f, v, _m in rows): out.append("إذا بدك بجيك بوحدة منهن، قلي تعالي بالسيارة.")\n'
     '    return " ".join(out)\n'
     '\n'
     '\n'
     '# ---------------------------------------------------------------- s77 cars_near: the cars around HER, in her words (numbers stay in the log)\n'
     '# far (far_cars_line, redefined here) and here (near_cars_line) share the names, the distance words and the state words.\n'
     'NEAR_CARS_REACH = 60\n'
     'FAR_CARS_STATE.update({"ok": "جاهزة", "locked": "مسكّرة"})\n'
     '\n'
     '\n'
     'def cars_head(n):\n'
     '    return "حواليّ في " + ("سيارة وحدة" if n == 1 else "سيارتين" if n == 2 else "%d سيارات" % n) + ":"\n'
     '\n'
     '\n'
     'def car_name_ar(script):\n'
     '    """Base.SmallCar -> السيارة الصغيرة. An unknown type is just a car: no English id in her mouth."""\n'
     '    import sol_templates as STPL\n'
     '    raw = str(script or "").split(".", 1)[-1]\n'
     '    ar = STPL.vehicle_ar(raw)\n'
     '    return ar if ar and ar != raw else "سيارة"\n'
     '\n'
     '\n'
     'def car_dist_word(d):\n'
     '    d = _num(d)\n'
     '    return "جنبي" if d < 6 else "قريبة" if d < 25 else "بآخر الشارع" if d < NEAR_CARS_REACH else "بعيدة شوي"\n'
     '\n'
     '\n'
     'def near_car_state(v):\n'
     '    """Whether she could use it, from what the snapshot says. Unknown is said as unknown, never as ready."""\n'
     '    if "trailer" in str(v.get("name") or "").lower(): return FAR_CARS_STATE["trailer"]\n'
     '    f, m = v.get("fuel"), v.get("fuelMax")\n'
     '    fuel_known = isinstance(f, (int, float)) and isinstance(m, (int, float)) and m > 0\n'
     '    bad = []\n'
     '    if v.get("locked") is True: bad.append("مسكّرة")\n'
     '    if v.get("key") is False: bad.append("ما معي مفتاحها")\n'
     '    if fuel_known and f < max(1.0, 0.02 * m): bad.append("ما فيها بنزين")\n'
     '    if bad: return " و".join(bad)\n'
     '    if v.get("locked") is False and v.get("key") is True and fuel_known:\n'
     '        return "جاهزة" + ("، بس بنزينها قليل" if f < 0.25 * m else "")\n'
     '    good = ([] if v.get("locked") is not False else ["مفتوحة"]) + ([] if v.get("key") is not True else ["معي مفتاحها"]) + (["فيها بنزين"] if fuel_known else [])\n'
     '    return (" و".join(good) + "، بس ما جرّبتها") if good else "ما بعرف وضعها"\n'
     '\n'
     '\n'
     'def near_cars_rows(snap):\n'
     '    """[(distance from her, vehicle row)] nearest first, from the snapshot. She is the centre (him when she has no position)."""\n'
     '    s = snap or {}\n'
     '    me = s.get("sol") if isinstance(s.get("sol"), dict) and s["sol"].get("x") is not None else (s.get("player") or {})\n'
     '    mx, my = me.get("x"), me.get("y")\n'
     '    rows = []\n'
     '    for v in s.get("vehicles") or []:\n'
     '        if not isinstance(v, dict) or v.get("x") is None or v.get("y") is None: continue\n'
     '        d = math.hypot(v["x"] - mx, v["y"] - my) if mx is not None and my is not None else 99.0\n'
     '        if d <= NEAR_CARS_REACH: rows.append((d, v))\n'
     '    return sorted(rows, key=lambda r: r[0])\n'
     '\n'
     '\n'
     'def near_cars_line(snap):\n'
     '    rows = near_cars_rows(snap)\n'
     '    if not rows: return "ما في ولا سيارة حواليّ."\n'
     '    out = [cars_head(len(rows))]\n'
     '    for d, v in rows[:5]:\n'
     '        out.append("%s %s، %s." % (car_name_ar(v.get("name")), car_dist_word(d), near_car_state(v)))\n'
     '    if len(rows) > 5: out.append("وفي غيرهن أبعد.")\n'
     '    return " ".join(out)\n'
     '\n'
     '\n'
     'def far_cars_line(reason):\n'
     '    """far_car: the game\'s list (cars:<n>|id,script,dist,fuel,verdict,mine;...) in her words, as near_cars_line words the near ones."""\n'
     '    head, _, body = str(reason).partition("|")\n'
     '    rows = [r.split(",") for r in body.split(";") if r.count(",") == 5]\n'
     '    if not rows: return "ما في ولا سيارة حواليّ."\n'
     '    out = [cars_head(len(rows))]\n'
     '    for _id, script, d, fuel, verdict, mine in rows[:5]:\n'
     '        name = car_name_ar(script) if script != "?" else "سيارة ما عرفت نوعها"\n'
     '        out.append("%s%s %s، %s." % (name, " (سيارتي)" if mine == "1" else "", car_dist_word(d), FAR_CARS_STATE.get(verdict, "ما بعرف وضعها")))\n'
     '    if len(rows) > 5: out.append("وفي غيرهن أبعد.")\n'
     '    if any(v == "ok" for _i, _s, _d, _f, v, _m in rows): out.append("إذا بدك بجيك بوحدة منهن، قلي تعالي بالسيارة.")\n'
     '    return " ".join(out)\n'
     '\n'
     '\n'
     'def near_cars_detail(snap):\n'
     '    """The same list with its numbers, for the log only."""\n'
     '    return "; ".join("%s id=%s d=%.0f fuel=%s/%s locked=%s key=%s" % (v.get("name"), v.get("id"), d, v.get("fuel"), v.get("fuelMax"), v.get("locked"), v.get("key"))\n'
     '                     for d, v in near_cars_rows(snap)) or "none"\n'),
    # the reply gate's last step for every chat reply
    ('    t = re.sub(r"\\(\\s*\\)", "", t)\n'
     '    t = re.sub(r"[ \\t]{2,}", " ", t)\n'
     '    return t.strip()\n',
     '    t = re.sub(r"\\(\\s*\\)", "", t)\n'
     '    t = RG.drop_coordinates(t)                                                  # s77: no map position ever reaches the chat\n'
     '    t = re.sub(r"[ \\t]{2,}", " ", t)\n'
     '    return t.strip()\n'),
    # the model's choice
    ('        if action == "survey":\n'
     '            r = self._survey_answer(snap); done_line("model", action, "-", r); return r\n',
     '        if action == "survey":\n'
     '            r = self._survey_answer(snap); done_line("model", action, "-", r); return r\n'
     '        if action == "cars_near":                                                   # s77: the cars around her, far or here\n'
     '            r = self._cars_near_answer(snap); done_line("model", action, "-", r); return r\n'),
    # no keyword override of the model's "none"
    ('        if _CARS_Q_RX.search(text or "") and _CARS_ASK_RX.search(text or "") and not _CARS_ORDER_RX.search(text or ""):   # far_car: her surroundings, not his\n'
     '            far_done = []\n'
     '            if self._far_cars(snap, far_done):\n'
     '                said = getattr(self, "_forced", None); self._forced = None\n'
     '                done_line("far_cars", "none", "-", said)\n'
     '                return said\n',
     '        # s77: a question about the cars around her is the model\'s cars_near; no word match overrides its "none"\n'
     '        #      (s71\'s far_cars", "none" word match was here; this note keeps apply_s71_mind.py from putting it back)\n'),
    # survey: no coordinates, no tile counts
    ('        parts.append("البيت محدد عند %d,%d." % (h["x"], h["y"]) if isinstance(h, dict) and h.get("x") is not None else "لسا ما حددنا البيت.")\n',
     '        parts.append("البيت محدد." if isinstance(h, dict) and h.get("x") is not None else "لسا ما حددنا البيت.")      # s77: no coordinates\n'),
    ('        parts.append("مكان صف السيارات عند %d,%d." % (p["x"], p["y"]) if isinstance(p, dict) and p.get("x") is not None else "ما في مكان محدد لصف السيارات.")\n',
     '        parts.append("في مكان محدد لصف السيارات." if isinstance(p, dict) and p.get("x") is not None else "ما في مكان محدد لصف السيارات.")\n'),
    ('            parts.append("عنا %d منطقة زراعة: %d خانة، عايش منها %d، وفاضي %d." % (len(zones), sum(z.get("n") or 0 for z in zones), sum(z.get("alive") or 0 for z in zones), sum(z.get("empty") or 0 for z in zones)))\n',
     '            nz, alive, empty = len(zones), sum(z.get("alive") or 0 for z in zones), sum(z.get("empty") or 0 for z in zones)     # s77: no tile counts\n'
     '            parts.append("عنا %s للزراعة، فيها %s%s." % ("منطقة وحدة" if nz == 1 else "منطقتين" if nz == 2 else "%d مناطق" % nz,\n'
     '                                                    "نبتة وحدة عايشة" if alive == 1 else "نبتتين عايشين" if alive == 2 else "%d نبتات عايشة" % alive if 3 <= alive <= 10 else "%d نبتة عايشة" % alive if alive else "ولا نبتة عايشة", "، وفي محل فاضي للزرع" if empty else ""))\n'),
    ('        parts.append("شايفة %d سيارة قريبة." % len(s.get("vehicles") or []))\n'
     '        return " ".join(parts)\n'
     '\n'
     '    def _ask_provider(self, history):\n',
     '        nv = len(s.get("vehicles") or [])\n'
     '        parts.append("ما شايفة سيارات قريبة." if nv == 0 else "شايفة سيارة وحدة قريبة." if nv == 1 else "شايفة سيارتين قراب." if nv == 2 else "شايفة %d سيارات قريبة." % nv)\n'
     '        return " ".join(parts)\n'
     '\n'
     '    def _cars_near_answer(self, snap):\n'
     '        """s77 cars_near. Far: the far_car scan of her surroundings. Here: the cars the live snapshot shows around her. The numbers go to the log."""\n'
     '        far_done = []\n'
     '        if self._far_cars(snap, far_done):\n'
     '            r = getattr(self, "_forced", None); self._forced = None\n'
     '            return r or "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي."\n'
     '        sol = (snap or {}).get("sol")\n'
     '        if not snap or not isinstance(sol, dict) or sol.get("away"):               # no body here and no far list: nothing true to say\n'
     '            self.log("chat: cars near her -> no snapshot of her surroundings")\n'
     '            return "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي."\n'
     '        self.log("chat: cars near her -> %s" % near_cars_detail(snap)[:600])\n'
     '        return near_cars_line(snap)\n'
     '\n'
     '    def _ask_provider(self, history):\n'),
    # what the model reads about home: no coordinates (it must not learn to say them)
    ('            if isinstance(h, dict) and h.get("x") is not None: parts.append("بيتنا عند %d,%d." % (h["x"], h["y"]))\n',
     '            if isinstance(h, dict) and h.get("x") is not None: parts.append("بيتنا محدد.")      # s77: no coordinates\n'),
]


def mind(d):
    for o, n in MR: edit(os.path.join(d, "model_router.py"), o, n)
    for o, n in TPL: edit(os.path.join(d, "sol_templates.py"), o, n)
    for o, n in RG: edit(os.path.join(d, "reply_gate.py"), o, n)
    for o, n in CS: edit(os.path.join(d, "chat_service.py"), o, n)


if __name__ == "__main__":
    mind(sys.argv[1])
    print("s77_mind applied")
