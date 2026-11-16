"""model_first as specified, and follow_exits_car. Replaces what apply_s43 put in. Game closed only.
usage: apply_s44.py <sol_mind dir> <client dir>"""
import os, sys
MIND, CLIENT = sys.argv[1], sys.argv[2]
NL = chr(10); CRLF = chr(13) + NL

def read(p): return open(p, encoding="utf-8", newline="").read()
cs_p = os.path.join(MIND, "chat_service.py")
t = read(cs_p)
crlf = CRLF in t
t = t.replace(CRLF, NL)

a = t.index("    def _route_by_model(self, history, c, key, snap, mem):")
b = t.index("    def _why_answer(self, snap):")
NEW = '''    def _memory_text(self, snap, mem):
        """What this Sol remembers, from the Mind's memory and the game. Rebuilt after a reconnect; her death empties it."""
        parts = [self._survey_answer(snap)]
        if mem is not None:
            places = [p.get("name") for p in (mem.data.get("places") or []) if isinstance(p, dict) and p.get("name")]
            if places: parts.append("أماكن بتعرفيها: " + "، ".join(places[-12:]) + ".")
            h = mem.data.get("home")
            if isinstance(h, dict) and h.get("x") is not None: parts.append("بيتنا عند %d,%d." % (h["x"], h["y"]))
        return " ".join(parts)

    def _session_sheet(self, snap, mem, acts):
        deaths = int(mem.data.get("deaths") or 0) if mem is not None else 0
        got = getattr(self, "_sheet", None)
        if got is None or got["deaths"] != deaths or time.time() - got["t"] > 300:
            got = {"text": MR.sheet(acts, self._memory_text(snap, mem)), "deaths": deaths, "t": time.time()}
            self._sheet = got
            self.log("chat: briefing sheet sent to the model, %d chars" % len(got["text"]))
        return got["text"]

    def _route_by_model(self, history, c, key, snap, mem):
        """The model picks the nearest action, the Mind checks and runs it and the game's result is what he hears. Returns the reply, or None for the word lists.
        self._model_failed is set when the model did not answer, so the slow talk path is not tried on top of it."""
        self._model_failed = False
        if not self._model_first() or not history: return None
        text = history[-1]["text"]
        acts = load_actions(self.dir)
        t0 = time.time()
        def done_line(path, action, gate, result):
            self.log("chat: route text=%s path=%s ms=%d action=%s gate=%s result=%s" % (text[:60], path, int((time.time() - t0) * 1000), action, gate, str(result)[:90]))
        try:
            raw = P.chat(c["provider"], key, c["model"], MR.message(text), system=self._session_sheet(snap, mem, acts), custom_base=c.get("base", ""), max_tokens=80, timeout=4)
        except Exception as e:
            self._model_failed = True
            done_line("fallback", None, "-", "model failed: %r" % (e,))
            return None
        p = MR.parse(raw)
        if p is None:
            done_line("fallback", None, "-", "reply not readable")
            return None
        action = p["action"]
        ids = {a.get("id") for a in acts if a.get("enabled", True)}
        if action == "unknown" or (action != "none" and action not in MR.COMMANDS and action not in ids):
            done_line("model", action, "not_an_action", "asked him")
            return "شو قصدك؟ عيدها بكلمة تانية."
        if action == "why":
            r = self._why_answer(snap); done_line("model", action, "-", r); return r
        if action == "survey":
            r = self._survey_answer(snap); done_line("model", action, "-", r); return r
        if action in MR.COMMANDS:
            routed = list(history[:-1]) + [dict(history[-1], text=MR.COMMANDS[action][1])]
            done = self._pre_intents(routed, snap, mem)
            forced = getattr(self, "_forced", None); self._forced = None
            reply = forced or (self._receipt() if done else None)
            done_line("model", action, "accepted", reply)
            return reply
        if action != "none":
            self._player_takes_over(action)
            r = resolve_and_run(self.dir, action, (p.get("args") or {}).get("option"), mem, snap)
            self._remember_action(action, (p.get("args") or {}).get("option"))
            done_line("model", action, "accepted", r)
            return action_receipt_note(r) or random.choice(("تكرم.", "ماشي."))
        facts = W.situation_text(snap, mem) + " " + self._memory_text(snap, mem)
        ctx = self._gate_context(history, acts, facts, MA.known_names(snap, mem, [], GZ.load()))
        speech, rejected = RG.check_speech({"speech": p["speech"]}, ctx, False)
        done_line("model", "none", rejected or ("stripped" if getattr(ctx, "stripped", None) else "kept"), speech)
        return clean_speech(speech)

'''
t = t[:a] + NEW + t[b:]

old = """        routed = self._route_by_model(history, c, key, snap, mem)
        if routed is not None: return routed
        done = self._pre_intents(history, snap, mem)
        forced = getattr(self, "_forced", None); self._forced = None
        if forced: return forced
        if done: return self._receipt()                                         # the Mind understood it and did it: nothing for a model to add
"""
new = """        routed = self._route_by_model(history, c, key, snap, mem)
        if routed is not None: return routed
        done = self._pre_intents(history, snap, mem)
        forced = getattr(self, "_forced", None); self._forced = None
        if forced: return forced
        if done: return self._receipt()                                         # the Mind understood it and did it: nothing for a model to add
        if getattr(self, "_model_failed", False):                                # the model is down: no minute-long wait on a second call to it
            self.log("chat: model down, word lists found no order")
            return "ما قدرت افهم هلأ، قولها بكلمة تانية."
"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """        return RG.Context(history[-1]["text"] if history else "", ids, IE.SUPPORTED, known_text, in_car, self._note_actions(), names)
"""
new = """        ctx = RG.Context(history[-1]["text"] if history else "", ids, IE.SUPPORTED, known_text, in_car, self._note_actions(), names)
        ctx.strict = self._model_first()                                         # switch off: the gate is as it was
        return ctx
"""
assert t.count(old) == 1
t = t.replace(old, new)
compile(t, cs_p, "exec")

rg_p = os.path.join(MIND, "reply_gate.py")
g = read(rg_p); gcrlf = CRLF in g; g = g.replace(CRLF, NL)
old = 'if not words or (len(words) == 1 and words[0] not in ALONE_OK) or is_question(ctx.user_text):'
new = 'if not words or (len(words) == 1 and words[0] not in ALONE_OK) or (bare_ack and is_question(ctx.user_text)) or (getattr(ctx, "strict", False) and is_question(ctx.user_text)):'
assert g.count(old) == 1
g = g.replace(old, new)
compile(g, rg_p, "exec")

sa_p = os.path.join(CLIENT, "SolActions.lua")
s = read(sa_p); scrlf = CRLF in s; s = s.replace(CRLF, NL)
a = s.index('    if id == "follow" and type(SolOrders) == "table"')
b = s.index('    if id == "sol_drive" then', a)
LUA = '''    if (id == "follow" or id == "regroup") and type(SolOrders) == "table" and type(SolOrders.leaveCar) == "function" and type(SolAuthority) == "table" and SolAuthority.on("follow_exits_car") == true then
        local s = U.solActor and U.solActor() or nil
        local car = s and type(s.getVehicle) == "function" and s:getVehicle() or nil
        local me = getSpecificPlayer and getSpecificPlayer(0) or nil
        local mine = me and type(me.getVehicle) == "function" and me:getVehicle() or nil
        if car ~= nil and mine ~= car then
            print("[SolOrders] " .. tostring(id) .. ": she is in a car he is not in, she gets out first")
            if car:getDriver() == s and car:isEngineRunning() and type(U.solEngine) == "function" then pcall(U.solEngine, "off") end
            SolOrders.leaveCar()
            return true, "leaving_car_to_follow"
        end
    end
'''
s = s[:a] + LUA + s[b:]

au_p = os.path.join(CLIENT, "SolAuthority.lua")
u = read(au_p); ucrlf = CRLF in u; u = u.replace(CRLF, NL)
assert u.count('"follow_leaves_car"') == 1
u = u.replace('"follow_leaves_car"', '"follow_exits_car"')

fix = os.path.join(CLIENT, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
f = open(fix, encoding="utf-8", newline="").read()
assert "follow_leaves_car=" in f
f = f.replace("follow_leaves_car=", "follow_exits_car=")

for p, text, cr in ((cs_p, t, crlf), (rg_p, g, gcrlf), (sa_p, s, scrlf), (au_p, u, ucrlf)):
    open(p, "w", encoding="utf-8", newline="").write(text.replace(NL, CRLF) if cr else text)
open(fix, "w", encoding="utf-8", newline="").write(f)
print("applied")
