"""Voice button: local microphone + Whisper path, and the ChatGPT-dictation path through Sol Link."""
import os, sys, tempfile, time, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["LOCALAPPDATA"] = tempfile.mkdtemp()
import voice_service as V, sol_link, settings_service as SS
res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
lua = tempfile.mkdtemp()
class FakeChat:
    def __init__(self): self.got = []
    def handle(self, t): self.got.append(t)
class FakeRec:
    def __init__(self): self.started = 0
    def start(self): self.started = time.time()
    def stop(self): return b"\x00\x01" * 16000          # 1 s of audio
def req(i, a): open(os.path.join(lua, V.REQ), "w").write("id=%d\naction=%s\n" % (i, a))
def state(): return dict(l.split("=", 1) for l in open(os.path.join(lua, V.STATE)).read().splitlines() if "=" in l)
SS.load_config = lambda: {"source": "api"}
chat = FakeChat()
v = V.Voice(lua, chat, log=lambda m: None, recorder=FakeRec, stt=lambda wav, key: "اتبعيني", key="gsk")
req(1, "start"); v.poll_once(); check("first press: listening", state()["status"] == "listening")
req(2, "stop"); v.poll_once(); time.sleep(0.3)
check("second press: Whisper text goes into Sol's chat", chat.got == ["اتبعيني"] and state()["status"] == "done")
check("the heard text is reported to the game (escaped)", state()["text"].startswith("\\u0627"))
v2 = V.Voice(lua, FakeChat(), log=lambda m: None, recorder=FakeRec, stt=lambda w, k: "x", key="")
req(3, "start"); v2.last_id = 2; v2.poll_once(); req(4, "stop"); v2.poll_once()
check("no Groq key -> clear error, nothing sent", state()["code"] == "no_stt_key")
def broken(): raise RuntimeError("mic_unavailable")
v3 = V.Voice(lua, FakeChat(), log=lambda m: None, recorder=broken, key="k"); v3.last_id = 4
req(5, "start"); v3.poll_once(); check("no microphone -> 'mic_unavailable'", state()["code"] == "mic_unavailable")
check("WAV header is valid 16 kHz mono", V.wav_bytes(b"\x00\x00" * 10)[:4] == b"RIFF" and b"WAVE" in V.wav_bytes(b"\x00\x00")[:12])
# ChatGPT dictation through Sol Link
link = sol_link.Link(log=lambda m: None, port=18795, token="t").start()
SS.load_config = lambda: {"source": "bridge"}
SS.start_link = lambda log=print: link
chat4 = FakeChat()
v4 = V.Voice(lua, chat4, log=lambda m: None, recorder=FakeRec, key="k"); v4.last_id = 5
link.last_seen = time.time()
req(6, "start"); v4.poll_once()
check("bridge as mind: first press asks ChatGPT to dictate (no local mic)", link.commands == ["dictate_start"] and state()["status"] == "listening")
def call(method, path, body=None):
    r = urllib.request.Request("http://127.0.0.1:18795" + path, method=method, data=json.dumps(body).encode() if body else None, headers={"X-Sol-Link-Token": "t", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=5) as x: return json.loads(x.read())
check("the userscript gets the command from /next", call("GET", "/next") == {"id": 0, "cmd": "dictate_start"})
req(7, "stop"); v4.poll_once(); check("second press: 'dictate_stop' queued", link.commands == ["dictate_stop"] and state()["status"] == "transcribing")
call("POST", "/heard", {"text": "ادخلي للداخل"}); time.sleep(0.3)
check("dictated text goes into Sol's chat", chat4.got == ["ادخلي للداخل"] and state()["status"] == "done")
link.last_seen = 0; v4.last_id = 7; req(8, "start"); v4.poll_once()
check("page not connected -> says so (not a silent wait)", state()["code"] == "chatgpt_link_not_connected")
link.stop()
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
