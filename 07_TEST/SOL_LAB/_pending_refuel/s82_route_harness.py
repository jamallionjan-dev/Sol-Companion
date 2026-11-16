"""s82: one Mind copy's model routing (Chat._route_by_model) with a mocked model, run in its own interpreter so each copy imports
its own chat_service / model_router. Used by test_s82_mind.py and test_s82_route_eval.py. Nothing live is touched: the game's
side (run_action, the GPS) is a stub, the Lua folder is a temp dir, the world is a fixed snapshot in Muldraugh on S Main St.

  child:  s82_route_harness.py --child <mind dir> <cases.json>   -> one JSON line per case on stdout
  case:   {"text": ..., "model": "card" | "nearest" | "unknown" | {"action": ..., "args": {...}}, "actions": [ids] (optional)}
  result: {"text", "reply", "path", "action", "gate", "game": [[action, option]], "pre": [routed text], "seq": both in run order, "card_chars"}
Model mocks
  card     the card's examples only: his exact words (a leading "سول " and a trailing "?" dropped) on an example line -> that answer,
           else plain talk (none). Grouped lines "a / b -> {...}" count for each of a, b.
  card_near  s90: the example on the card this message got (two-tier card: its own examples) closest to his words (the harness's
           own light Arabic normalisation, word overlap, char 3-grams to break ties) -> its answer; nothing in common -> none.
  nearest  the example whose words overlap his most (Jaccard), whatever it is: how a small model misreads a near miss.
  unknown  always {"action":"unknown"}.
  a dict   that exact reply (a recorded model answer).
  live     the connected model itself (settings_service config, the stored key): only test_s82_route_eval.py --live uses it."""
import json, os, re, sys, tempfile

SNAP = {"player": {"x": 10825, "y": 10121, "z": 0}, "sol": {"x": 10826, "y": 10121, "z": 0}, "knownStreets": ["S Main St"],
        "vehicles": [{"x": 10826, "y": 10121, "name": "car"}]}
LIVE_IDS = ["sol_headlights", "sol_engine", "sol_horn", "sol_toggle_light", "regroup", "retreat", "set_combat_doctrine", "open_inventory", "open_health", "bandage", "exit_vehicle"]
BUTTONS = ("regroup", "retreat", "set_combat_doctrine", "open_inventory", "open_health", "bandage", "exit_vehicle")   # s85: every game button on the card
# s90: the game actions the old card never showed (the two-tier card lists every one and has examples for each)
LIVE_IDS += ["board_vehicle", "set_allow_overload", "set_follow_fan_out", "set_hold_fire", "set_ride_with_player", "set_scavenge",
             "sol_attack_nearest", "sol_bandage_player", "sol_car_wait", "sol_close_door", "sol_cook", "sol_cook_and_serve", "sol_drink",
             "sol_drive", "sol_eat", "sol_equip_best", "sol_fetch", "sol_fill_water", "sol_fuel", "sol_give", "sol_go_inside", "sol_goto",
             "sol_gps_clear", "sol_open_door", "sol_open_window", "sol_plan_cancel", "sol_plan_status", "sol_read", "sol_reload",
             "sol_replace_bandage", "sol_rest", "sol_sit_beside", "sol_stove_off", "sol_stove_on", "sol_take_pill", "sol_take_wheel", "sol_wash"]
TICKS = ("set_allow_overload", "set_follow_fan_out", "set_hold_fire", "set_ride_with_player", "set_scavenge")   # the game's tick boxes


def examples(card):
    """{his words: answer json text} from the card's example lines."""
    out = {}
    body = card.split("\nأمثلة:\n", 1)[-1].split("\n\nذاكرتك الآن:", 1)[0]
    for line in body.splitlines():
        k = line.find(" -> {")
        if k <= 0: continue
        for said in line[:k].split(" / "): out.setdefault(said.strip(), line[k + 4:])
    return out


def _words(s): return set(re.sub(r"[؟?.!،,]", " ", s).split()) - {"سول"}


_AR = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})


def _near_feats(s):
    """The mock's own reading of a phrase (independent of the Mind's retrieval): folded letters, light prefixes off."""
    words = re.sub(r"[^\w\s]", " ", re.sub("[\u064B-\u065F\u0640]", "", s).translate(_AR)).split()
    out = set()
    for w in words:
        if w in ("سول", "لو", "سمحتي", "يا", "هلأ", "هلا"): continue
        for p in ("هال", "وال", "بال", "عال", "ال", "و"):
            if w.startswith(p) and len(w) - len(p) >= 3: w = w[len(p):]; break
        out.add(w)
    flat = " ".join(sorted(out))
    return out, {flat[i:i + 3] for i in range(max(0, len(flat) - 2))}


def nearest_on_card(text, ex):
    """card_near: the example closest to his words, or None when no word is shared."""
    w, g = _near_feats(text)
    best, key = None, (0.0, 0.0)
    for e in ex:
        we, ge = _near_feats(e)
        k = (len(w & we) / float(len(w | we) or 1), len(g & ge) / float(len(g | ge) or 1))
        if k > key: best, key = e, k
    return best if key[0] > 0 else None


def child(mind, cases_path):
    sys.path.insert(0, mind)
    import chat_service as CS, model_router as MR, reply_gate as RG, providers as P, settings_service as SS, world_knowledge as W
    assert os.path.dirname(os.path.abspath(CS.__file__)) == os.path.abspath(mind), CS.__file__
    cases = json.load(open(cases_path, encoding="utf-8"))
    TMPD = tempfile.mkdtemp(prefix="sol_s82_route_")
    W.situation_text = lambda s, m: "world"
    CS.time.sleep = lambda s: None
    GAME, LOG, PRE, CUR = [], [], [], {}
    SEQ = []
    CMD_OF = {v[1]: k for k, v in MR.COMMANDS.items() if v[1]}             # the phrase a COMMANDS action is routed as -> its id
    def run_action(d, action, option=None, wait=3.0):
        GAME.append([action, option]); SEQ.append(["game", action, option]); return {"ok": True, "reason": ""}
    CS.run_action = run_action
    CS.gps_request = lambda d, f: (GAME.append(["gps", f.get("action")]) or 1)
    CS._drive_outcome = lambda d, rid, base: dict(base, ok=True, confirmed=True, result="driving", reason="")
    real_chat = P.chat
    def model(pid, key, mdl, msgs, system="", custom_base="", max_tokens=0, timeout=0):
        CUR["card"] = system
        if CUR["model"] == "live":
            CUR["raw"] = real_chat(pid, key, mdl, msgs, system=system, custom_base=custom_base, max_tokens=max_tokens, timeout=max(timeout, 20))
            return CUR["raw"]
        text = msgs[-1]["content"].replace(" /no_think", "").strip()
        m = CUR["model"]
        if isinstance(m, dict): return json.dumps(m, ensure_ascii=False)
        if m == "unknown": return '{"action":"unknown","speech":""}'
        ex = examples(system)
        bare = re.sub(r"^سول\s+", "", text).rstrip("؟? ")
        if m == "card":
            return ex.get(text) or ex.get(bare) or '{"action":"none","speech":"أهلين"}'
        if m == "card_near":
            hit = nearest_on_card(bare, ex)
            return ex[hit] if hit else '{"action":"none","speech":"أهلين"}'
        if m == "nearest":
            w = _words(bare)
            best = max(ex, key=lambda e: (len(w & _words(e)) / float(len(w | _words(e)) or 1), -len(e)))
            return ex[best]
        raise ValueError(m)
    P.chat = model
    cfg, key = {"source": "local", "provider": "custom", "model": "test", "base": ""}, ""
    if any(c.get("model") == "live" for c in cases):
        cfg = SS.load_config()
        key = (CS.S.get(cfg["provider"]) or "") if cfg.get("source") == "api" else ""
    SS.load_config = lambda: cfg
    for case in cases:
        ids = case.get("actions", LIVE_IDS)
        CS.load_actions = lambda d, ids=ids: [{"id": i, "kind": "button" if i in BUTTONS else "tick" if i in TICKS else "sol", "label": i} for i in ids]
        c = CS.Chat.__new__(CS.Chat)
        c.dir, c.log, c._forced, c._sheet = TMPD, LOG.append, None, None
        c._world = lambda: (SNAP, None)
        c.gps_state = lambda: {}
        c._pre_intents = lambda h, s, m: (PRE.append(h[-1]["text"]) or SEQ.append(["pre", CMD_OF.get(h[-1]["text"]), h[-1]["text"]]) or ["ran"])
        c._receipt = lambda: "تكرم."
        c._player_takes_over = lambda a: None
        c._remember_action = lambda a, o: None
        c._memory_text = lambda s, m: "لا شيء."
        c._gate_context = lambda h, a, k, n=(): RG.Context(h[-1]["text"], [], [], k, False, (), [])
        c._model_first = lambda: True
        c._station_list = lambda: []
        c._street_now = lambda: "S Main St"
        c._gardens = lambda: []
        c._why_answer = lambda s: "why"
        c._survey_answer = lambda s: "survey"
        c._cars_near_answer = lambda s: "cars"
        del GAME[:], LOG[:], PRE[:], SEQ[:]
        CUR["model"] = case.get("model", "card")
        reply = c._route_by_model([{"role": "user", "text": case["text"]}], cfg, key, SNAP, None)
        route = [l for l in LOG if l.startswith("chat: route text=")]
        last = route[-1] if route else ""
        g = lambda k: (re.search(r" %s=(\S+)" % k, last) or [None, None])[1]
        card = CUR.get("card") or ""
        print(json.dumps({"text": case["text"], "reply": reply, "path": g("path"), "action": g("action"), "gate": g("gate"), "game": GAME[:], "pre": PRE[:], "seq": SEQ[:],
                          "card_chars": len(card.split("\n\nذاكرتك الآن:", 1)[0]), "log": LOG[-4:], "raw": CUR.pop("raw", None),
                          "card": card if case.get("want_card") else "", "commands": sorted(MR.COMMANDS),
                          "bank": ["%s -> %s" % e for e in MR.example_bank(CS.load_actions(TMPD))] if case.get("want_card") and getattr(MR, "CARD_TIERS", False) and hasattr(MR, "example_bank") else [],
                          "budget": getattr(MR, "CARD_BUDGET", None), "tiers": bool(getattr(MR, "CARD_TIERS", False))}, ensure_ascii=False))


def run(mind, cases):
    """Parent side: the results for these cases on this Mind copy."""
    import subprocess
    fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd)
    json.dump(cases, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--child", mind, p], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1"))
    out = [json.loads(l) for l in r.stdout.splitlines() if l.startswith("{")]
    if r.returncode or len(out) != len(cases): raise RuntimeError("route child failed:\n" + r.stdout[-1500:] + r.stderr[-2500:])
    return out


if __name__ == "__main__" and len(sys.argv) > 3 and sys.argv[1] == "--child":
    child(sys.argv[2], sys.argv[3])
