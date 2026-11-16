"""Sol Link: ChatGPT in the browser as Sol's mind. A fake userscript talks to the real server over HTTP."""
import json, os, subprocess, sys, tempfile, threading, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["LOCALAPPDATA"] = tempfile.mkdtemp()
import sol_link, chat_service as C, settings_service as SS
res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
PORT = 18790
script_dir = tempfile.mkdtemp()
link = sol_link.Link(log=lambda m: None, port=PORT, token="tok-123", script_dir=script_dir).start()
def call(method, path, body=None, token="tok-123"):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"X-Sol-Link-Token": token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r: return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e: return e.code, {}
check("wrong token -> 401 (nothing passes without Sol Link's own token)", call("GET", "/ping", token="nope")[0] == 401)
check("nothing waiting -> /next id 0", call("GET", "/next") == (200, {"id": 0}))
js = open(os.path.join(script_dir, "Sol_Link.user.js"), encoding="utf-8").read()
check("userscript written with port and token filled in", "127.0.0.1:18790" in js and '"tok-123"' in js and "__TOKEN__" not in js)
open("/tmp/sl2.js", "w").write(js)
ok_syntax = subprocess.run(["node", "--check", "/tmp/sl2.js"], capture_output=True).returncode == 0
check("userscript is valid JavaScript", ok_syntax)
check("userscript has no way to run anything (no eval / Function / bridge /run)", not any(w in js for w in ("eval(", "new Function", "/run", "child_process", "8765")))
check("userscript drops code blocks from replies", 'querySelectorAll("pre, code' in js)
# chat through the link
lua = tempfile.mkdtemp()
SS.load_config = lambda: {"source": "bridge"}
SS.start_link = lambda log=print: link
calls = []
C.run_action = lambda d, a, o=None, wait=3.0: (calls.append((a, o)) or {"ok": True, "reason": "issued"})
json.dump({"v": 1, "actions": [{"id": "follow", "kind": "button", "label": "Follow", "enabled": True}, {"id": "sol_eat", "kind": "sol", "label": "eat"}]}, open(os.path.join(lua, C.ACT_SNAP), "w"))
ch = C.Chat(lua, log=lambda m: None)
t = threading.Thread(target=ch.handle, args=("اتبعيني ثم كلي شيئًا",)); t.start()
got = None
for _ in range(50):
    st, d = call("GET", "/next")
    if d.get("id"): got = d; break
    time.sleep(0.1)
check("the player's message reaches the userscript", got is not None and "اتبعيني ثم كلي شيئًا" in got["text"])
check("first message carries Sol's persona and rules", got and "أنتِ سول" in got["text"] and "[فعل:" in got["text"])
check("it carries the live action list", got and "follow: Follow" in got["text"] and "sol_eat" in got["text"])
check("clear intents ran before ChatGPT was asked (follow)", ("follow", None) in calls)
check("voice requested (ChatGPT reads the reply aloud)", got and got["speak"] is True)
call("POST", "/reply", {"id": got["id"], "text": "حاضر، سأتبعك وآكل شيئًا الآن. [فعل: sol_eat] [فعل: format_disk]"})
t.join(5)
check("ChatGPT's [فعل: sol_eat] runs in the game", ("sol_eat", None) in calls)
check("an action that is not in the list is ignored", not any(a == "format_disk" for a, _ in calls))
check("Sol's reply shown without the tags", ch.hist[-1]["role"] == "sol" and ch.hist[-1]["text"] == "حاضر، سأتبعك وآكل شيئًا الآن.")
t = threading.Thread(target=ch.handle, args=("كيف حالك؟",)); t.start()
for _ in range(50):
    st, d = call("GET", "/next")
    if d.get("id"): got2 = d; break
    time.sleep(0.1)
check("second message has no persona again (only every 25 messages)", "أنتِ سول" not in got2["text"])
call("POST", "/reply", {"id": got2["id"], "text": "بخير ما دمنا معًا."}); t.join(5)
check("stale or wrong reply id is refused", call("POST", "/reply", {"id": 999, "text": "x"})[0] == 409)
# not connected -> clear error
link2 = sol_link.Link(log=lambda m: None, port=PORT + 1, token="t2").start()
orig = link2.ask
link2.ask = lambda text, speak=True, timeout=150: orig(text, speak, timeout=1)
SS.start_link = lambda log=print: link2
ch2 = C.Chat(lua, log=lambda m: None); ch2.handle("مرحبا")
check("no userscript running -> 'chatgpt_link_not_connected' (not a silent hang)", ch2.status == "error" and ch2.code == "chatgpt_link_not_connected")
# Sol's chat is remembered from the userscript and opened by itself when nothing is connected
req = urllib.request.Request("http://127.0.0.1:%d/ping" % PORT, headers={"X-Sol-Link-Token": "tok-123", "X-Sol-Link-Chat": "/c/abc-123"})
urllib.request.urlopen(req, timeout=5).read()
check("the chat address is learned from the userscript and kept on disk", link.chat_path == "/c/abc-123" and open(os.path.join(script_dir, "sol_chat.txt")).read() == "/c/abc-123")
opened = []
link.firefox = staticmethod(lambda: "C:/fake/firefox.exe")
sol_link.subprocess.Popen = lambda args, **k: opened.append(args)
check("open_chat starts Firefox with the Sol profile and Sol's chat", link.open_chat() and opened[-1] == ["C:/fake/firefox.exe", "-no-remote", "-P", "Sol", "https://chatgpt.com/c/abc-123"])
# walking / inside / driving resolved from memory
import world_knowledge as W
mem = W.Memory({"name": "wl", "mode": "Sandbox"}); mem.data["home"] = {"name": "بيتنا", "x": 7013, "y": 8448}; mem.data["places"] = [{"name": "المطبخ", "x": 7020, "y": 8440}]
runs = []
C.run_action = lambda d, a, o=None, wait=3.0: (runs.append((a, o)) or {"ok": True})
snap = {"player": {"x": 7000, "y": 8450}}
C.resolve_and_run(lua, "sol_go_inside", "home", mem, snap)
check("'ادخلي' near home -> walk inside the home (its coordinates)", runs[-1] == ("sol_go_inside", "7013,8448"))
C.resolve_and_run(lua, "sol_go_inside", "home", mem, {"player": {"x": 9000, "y": 9000}})
check("far from home -> the nearest building instead", runs[-1] == ("sol_go_inside", None))
C.resolve_and_run(lua, "sol_goto", "home", mem, snap); check("'اذهبي إلى البيت' -> walk to home x,y", runs[-1] == ("sol_goto", "7013,8448"))
C.resolve_and_run(lua, "sol_goto", "المطبخ", mem, snap); check("walk to a remembered place by name", runs[-1] == ("sol_goto", "7020,8440"))
check("unknown place -> honest", C.resolve_and_run(lua, "sol_goto", "المريخ", mem, snap)["ok"] is False)
r = C.resolve_and_run(lua, "sol_drive", "drive to home", mem, snap)
check("sol_drive from the model goes to the GPS (was 'unknown_action' in game)", r.get("sent") == "home" and "x=7013" in open(os.path.join(lua, C.GPS_REQ)).read())
check("'اركبي السيارة وقودي' = sit behind the wheel (not passenger, not a place called 'the car')", C.intents("اركبي السيارة وقودي") == [("drive_take_wheel", {})])
r = C.resolve_and_run(lua, "sol_drive", "السيارة", mem, snap)
check("the model asking to drive to 'السيارة' -> take the wheel, ask where", r["ok"] is True and "action=take_wheel" in open(os.path.join(lua, C.GPS_REQ)).read())
# ChatGPT claimed "I am behind the wheel" while the game refused: the real reason is now added to her reply
open(os.path.join(lua, C.GPS_STATE), "w").write("ack=%d\nresult=failed\nreason=player_aboard\n" % 0)
orig_req = C.gps_request
def fake_req(d, fields):
    rid = orig_req(d, fields); open(os.path.join(d, C.GPS_STATE), "w").write("ack=%d\nresult=failed\nreason=player_aboard\n" % rid); return rid
C.gps_request = fake_req
r = C.drive_to(lua, {"target": "home"}, mem)
check("drive result comes from the game (refused: player aboard)", r.get("ok") is False and r.get("reason") == "player_aboard")
check("Arabic line for that refusal", C.reason_ar("player_aboard").startswith("انزل لحظة"))
C.gps_request = orig_req
link.stop(); link2.stop()
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
