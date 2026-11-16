import os, sys, tempfile, json
tmp = tempfile.mkdtemp(); os.environ["LOCALAPPDATA"] = tmp
import chat_service as C, providers as P
res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
s = "مرحباً يا سول! 😀 test=1|x \\ end"
check("escape is pure ASCII and round-trips (incl. emoji, = | \\)", C.esc(s).isascii() and C.unesc(C.esc(s)) == s)
lua = tempfile.mkdtemp(); seen = []
def fake_ask(hist):
    seen.append([dict(m) for m in hist]); return "أنا سول، أسمعك جيدًا."
ch = C.Chat(lua, log=lambda m: None, ask=fake_ask)
def send(text=None, action=None, rid=[0]):
    rid[0] += 1
    body = "id=%d\n" % rid[0] + ("text=%s\n" % C.esc(text) if text is not None else "") + ("action=%s\n" % action if action else "")
    open(os.path.join(lua, C.REQ), "w", encoding="ascii").write(body); ch.poll_once()
    return dict(l.split("=", 1) for l in open(os.path.join(lua, C.STATE), encoding="ascii").read().splitlines())
st = send("مرحبا يا سول")
check("message answered: status ok, 2 messages", st["status"] == "ok" and st["count"] == "2")
check("state file is ASCII escaped and decodes back", C.unesc(st["m2"].split("|", 1)[1]) == "أنا سول، أسمعك جيدًا." and st["m1"].startswith("user|"))
st2 = send("كيف حالك؟")
check("history kept and sent as context", len(seen[-1]) == 3 and st2["count"] == "4")
check("history persisted to disk", len(json.load(open(os.path.join(tmp, "SolMind", "chat_history.json"), encoding="utf-8"))) == 4)
ch2 = C.Chat(lua, log=lambda m: None, ask=fake_ask); check("history reloaded after restart", len(ch2.hist) == 4)
def failing(h): raise P.ProviderError("rate_limited", "Groq HTTP 429")
ch.ask = failing; st = send("رسالة"); check("provider error -> status error with code", st["status"] == "error" and st["code"] == "rate_limited")
ch.ask = fake_ask
open(os.path.join(lua, C.REQ), "w").write("id=1\ntext=old\n"); check("old request id ignored", ch.poll_once() is False)
st = send(action="clear"); check("clear wipes history", st["count"] == "0")
# no mind configured -> no_mind
import settings_service as SS
ch3 = C.Chat(lua, log=lambda m: None); st = None
try: ch3._ask_provider([{"role": "user", "text": "x"}]); check("no mind configured -> no_mind", False)
except P.ProviderError as e: check("no mind configured -> no_mind", e.code == "no_mind")
ch.ask = lambda h: "لدينا ٧٥ طلقة"; st = send("كم طلقة؟")
check("reply digits normalized to 0-9", C.unesc(st["m%s" % st["count"]].split("|", 1)[1]) == "لدينا 75 طلقة")
check("replies cleaned: no markdown, no tool names, no kcal", C.clean_reply("**الطعام:** - 12 عنصرا (2904 kcal) عبر find_items") == "الطعام: 12 عنصرا (2904 سعرة) عبر")
check("intent: 'تعرفي ان هذا بيتنا' -> set_home", C.intents("تعرفي ان هذا بيتنا")[0][0] == "set_home")
check("intent: remember with a name", C.intents("تذكري ما هنا باسم المطبخ") == [("remember_place", {"name": "المطبخ", "note": ""})])
check("intent: supplies question", C.intents("ماذا لدينا من موارد")[0][0] == "supplies")
import world_knowledge as W2
lua2 = tempfile.mkdtemp()
snap2 = {"world": {"name": "w1", "mode": "Sandbox"}, "player": {"x": 10, "y": 20, "z": 0, "stats": {}}, "containers": [{"where": "player", "items": [{"type": "Base.Nails", "name": "Nails", "count": 1}]}], "time": {"day": 1}}
open(os.path.join(lua2, W2.SNAP), "w").write(json.dumps(snap2))
ch2 = C.Chat(lua2, log=lambda m: None)
import providers as P2, settings_service as SS2
SS2.load_config = lambda: {"source": "api", "provider": "groq", "model": "m"}
P2.chat_with_tools = lambda *a, **k: "**حسنًا**، حفظته."
ch2.handle("هذا بيتنا")
m2 = W2.Memory(snap2["world"])
check("'هذا بيتنا' really saves home at the player's position (problems 6, 17)", m2.data["home"] and m2.data["home"]["x"] == 10 and m2.data["home"]["y"] == 20)
check("reply stored clean", ch2.hist[-1]["text"] == "حسنًا، حفظته.")
ch2.handle("ماذا لدينا من موارد")
check("supplies question -> a table card follows Sol's sentence", ch2.hist[-1]["role"] == "card" and "مسامير;1;قليل;amber" in ch2.hist[-1]["text"] and "\n" not in ch2.hist[-1]["text"])
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
