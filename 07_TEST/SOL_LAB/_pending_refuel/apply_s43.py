"""The model reads every line first; she gets out of the car when told to follow; a question never gets half an answer.
Switches: model_first, follow_leaves_car (SolFixes_LAB.txt). Game closed only. All or nothing.
usage: apply_s43.py <sol_mind dir> <client dir> [--verify]"""
import os, sys
MIND, CLIENT = sys.argv[1], sys.argv[2]
NL = chr(10)
EDITS = {}
def E(path, a, b): EDITS.setdefault(path, []).append((a, b))
CS = os.path.join(MIND, "chat_service.py"); RG = os.path.join(MIND, "reply_gate.py"); SA = os.path.join(CLIENT, "SolActions.lua"); AU = os.path.join(CLIENT, "SolAuthority.lua")

E(CS, """        snap, mem = self._world()
        done = self._pre_intents(history, snap, mem)
        forced = getattr(self, "_forced", None); self._forced = None
        if forced: return forced
        if done: return self._receipt()                                         # the Mind understood it and did it: nothing for a model to add
        acts = load_actions(self.dir)
        tool_notes = []
""", """        snap, mem = self._world()
        routed = self._route_by_model(history, c, key, snap, mem)
        if routed is not None: return routed
        done = self._pre_intents(history, snap, mem)
        forced = getattr(self, "_forced", None); self._forced = None
        if forced: return forced
        if done: return self._receipt()                                         # the Mind understood it and did it: nothing for a model to add
        acts = load_actions(self.dir)
        tool_notes = []
""")
E(CS, """    def _ask_provider(self, history):
        c = SS.load_config()
""", """    def _model_first(self):
        \"\"\"His switch in SolFixes_LAB.txt; missing means on, like every lab fix.\"\"\"
        try:
            with open(os.path.join(self.dir, "SolFixes_LAB.txt"), encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.strip().replace(" ", "") == "model_first=off": return False
        except OSError: pass
        return True

    def _route_by_model(self, history, c, key, snap, mem):
        \"\"\"The model picks the nearest command, the Mind runs and checks it. None: the Mind's own word lists take the line (model off, slow, unreadable, or plain talk).\"\"\"
        if not self._model_first() or not history: return None
        text = history[-1]["text"]
        t0 = time.time()
        try:
            raw = P.chat(c["provider"], key, c["model"], MR.message(text), system=MR.SHEET, custom_base=c.get("base", ""), max_tokens=48, timeout=6)
        except Exception as e:
            self.log("chat: model router failed after %.1fs: %r" % (time.time() - t0, e))
            return None
        cid = MR.parse(raw)
        self.log("chat: model chose %s in %.1fs" % (cid, time.time() - t0))
        if cid is None or cid == "chat": return None
        if cid == "why": return self._why_answer(snap)
        if cid == "survey": return self._survey_answer(snap)
        routed = list(history[:-1]) + [dict(history[-1], text=MR.COMMANDS[cid][1])]
        done = self._pre_intents(routed, snap, mem)
        forced = getattr(self, "_forced", None); self._forced = None
        if forced: return forced
        return self._receipt() if done else None

    def _why_answer(self, snap):
        \"\"\"Why the last thing failed, from what the game reported, never from the model.\"\"\"
        import farm_talk as FT
        g = self.gps_state() or {}
        if str(g.get("result")) in ("failed", "interrupted") and g.get("reason") not in (None, "", "walking_to_door", "moving_to_wheel"):
            return drive_reply({"ok": False, "reason": g.get("reason")})
        line = FT.stop_line(((snap or {}).get("solFarm") or {}).get("stop"))
        return line or "ما صار شي غلط هلأ."

    def _survey_answer(self, snap):
        \"\"\"What the game knows about the place, in one answer.\"\"\"
        s = snap or {}
        parts = []
        h = s.get("solHome")
        parts.append("البيت محدد عند %d,%d." % (h["x"], h["y"]) if isinstance(h, dict) and h.get("x") is not None else "لسا ما حددنا البيت.")
        p = s.get("solParking")
        parts.append("مكان صف السيارات عند %d,%d." % (p["x"], p["y"]) if isinstance(p, dict) and p.get("x") is not None else "ما في مكان محدد لصف السيارات.")
        zones = ((s.get("solFarm") or {}).get("zones")) or []
        if zones:
            parts.append("عنا %d منطقة زراعة: %d خانة، عايش منها %d، وفاضي %d." % (len(zones), sum(z.get("n") or 0 for z in zones), sum(z.get("alive") or 0 for z in zones), sum(z.get("empty") or 0 for z in zones)))
        else:
            parts.append("ما في منطقة زراعة محددة.")
        parts.append("شايفة %d سيارة قريبة." % len(s.get("vehicles") or []))
        return " ".join(parts)

    def _ask_provider(self, history):
        c = SS.load_config()
""")
E(CS, """REQ, STATE = "SolChat_Request.txt", "SolChat_State.txt\"""", """import model_router as MR
REQ, STATE = "SolChat_Request.txt", "SolChat_State.txt\"""")

# half an answer to a question is worse than saying she does not know
E(RG, """    if not words or (len(words) == 1 and words[0] not in ALONE_OK) or (bare_ack and is_question(ctx.user_text)):""",
      """    if not words or (len(words) == 1 and words[0] not in ALONE_OK) or is_question(ctx.user_text):""")

# follow_leaves_car: "follow" left her sitting in the driver's seat (14:08:28 to 14:13:20)
E(SA, "function U.runAction(id, option)" + NL, """function U.runAction(id, option)
    if id == "follow" and type(SolOrders) == "table" and type(SolOrders.leaveCar) == "function" and type(SolAuthority) == "table" and SolAuthority.on("follow_leaves_car") == true then
        local s = U.solActor and U.solActor() or nil
        local car = s and mcall(s, "getVehicle") or nil
        local me = getSpecificPlayer and getSpecificPlayer(0) or nil
        if car ~= nil and (me == nil or mcall(me, "getVehicle") ~= car) then SolOrders.leaveCar(); return true, "leaving_car_to_follow" end
    end
""")
E(AU, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "follow_leaves_car",' + NL)

if len(sys.argv) > 3 and sys.argv[3] == "--verify":
    missing = 0
    for p, ps in EDITS.items():
        t = open(p, encoding="utf-8", newline="").read().replace(chr(13) + NL, NL)
        for a, b in ps:
            if t.count(b) < 1: missing += 1; print("MISSING", p[-22:], b[:60])
    print("verified", sum(len(v) for v in EDITS.values()), "edits, missing", missing)
    sys.exit(1 if missing else 0)
out = {}
for p, ps in EDITS.items():
    t = open(p, encoding="utf-8", newline="").read()
    nl = chr(13) + NL if chr(13) + NL in t else NL
    for a, b in ps:
        a2, b2 = a.replace(NL, nl), b.replace(NL, nl)
        assert t.count(a2) == 1, (p[-22:], a[:60], t.count(a2))
        t = t.replace(a2, b2)
    if p.endswith(".py"): compile(t, p, "exec")
    out[p] = t
for p, t in out.items(): open(p, "w", encoding="utf-8", newline="").write(t)
print("applied", sum(len(v) for v in EDITS.values()), "edits to", len(out), "files")
