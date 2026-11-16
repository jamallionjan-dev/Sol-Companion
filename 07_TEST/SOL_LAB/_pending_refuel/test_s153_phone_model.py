"""s153 offline: a model on a phone. A real HTTPS server with a self-signed certificate runs on loopback addresses
(127.0.0.x stands in for the home network), and the patched Mind talks to it.
Nothing of the player's is touched: LOCALAPPDATA points to a temp folder for this process (config, secrets, lan_hosts).
Run: python test_s153_phone_model.py [sol_mind dir]. Offline PASS is not Runtime PASS."""
import http.server, json, os, shutil, socket, ssl, subprocess, sys, tempfile, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
MIND = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind")
FIX = os.path.join(HERE, "s153_fixture")
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)

tmp = tempfile.mkdtemp(prefix="s153_")
os.environ["LOCALAPPDATA"] = os.path.join(tmp, "appdata"); os.makedirs(os.environ["LOCALAPPDATA"])
mind = os.path.join(tmp, "mind"); os.makedirs(mind)
for f in os.listdir(MIND):
    if f.endswith((".py", ".pyw")): shutil.copy(os.path.join(MIND, f), mind)
ap = os.path.join(HERE, "apply_s153_phone_model.py")
r1 = subprocess.run([sys.executable, ap, mind], capture_output=True, text=True)
snap = {f: open(os.path.join(mind, f), "rb").read() for f in ("providers.py", "settings_service.py")}
r2 = subprocess.run([sys.executable, ap, mind], capture_output=True, text=True)
ck("installer runs", r1.returncode == 0, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout and snap == {f: open(os.path.join(mind, f), "rb").read() for f in snap}, r2.stdout + r2.stderr)
sys.path.insert(0, mind)
import providers as P, settings_service as SS, secret_store as S
P._FOLLOW_EVERY = 0.0

KEY, HITS = "ph0ne-key", []
class Phone(http.server.BaseHTTPRequestHandler):
    need_key = True
    def log_message(self, *a): pass
    def _send(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _auth(self):
        HITS.append((self.server.server_address[0], self.path, self.headers.get("Authorization")))
        if self.server.need_key and self.headers.get("Authorization") != "Bearer " + KEY: self._send(401, {"error": "bad key"}); return False
        return True
    def do_GET(self):
        if not self._auth(): return
        if self.path == "/v1/models": self._send(200, {"data": [{"id": m} for m in self.server.models]})
        else: self._send(404, {"error": "nope"})
    def do_POST(self):
        if not self._auth(): return
        n = int(self.headers.get("Content-Length") or 0); body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/v1/chat/completions": self._send(200, {"choices": [{"message": {"content": "ready " + body.get("model", "")}}]})
        else: self._send(404, {"error": "nope"})

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def start(host, port, cert=None, models=("qwen3-4b",), need_key=True):
    srv = http.server.ThreadingHTTPServer((host, port), Phone)
    srv.models, srv.need_key = list(models), need_key
    if cert:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(os.path.join(FIX, cert + ".crt"), os.path.join(FIX, cert + ".key"))
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv
def stop(srv): srv.shutdown(); srv.server_close()
def code_of(fn):
    try: fn(); return "ok"
    except P.ProviderError as e: return e.code

# ---- 1. pasted text
sp = P.split_address_and_key
ck("paste: address then key", sp("https://192.168.1.20:8080/v1 abc123") == ("abc123", "https://192.168.1.20:8080/v1"))
ck("paste: labels and bare host", sp("URL: 192.168.1.20:8080\nAPI Key: sk-phone-xyz") == ("sk-phone-xyz", "192.168.1.20:8080"))
ck("paste: only a key stays a key", sp("gsk_abcdefghijklmnopqrstuvwxyz") == ("gsk_abcdefghijklmnopqrstuvwxyz", ""))
ck("paste: only an address", sp("http://192.168.1.20:1234") == ("", "http://192.168.1.20:1234"))
ck("home addresses", P.is_lan_host("192.168.1.140") and P.is_lan_host("10.0.0.5") and P.is_lan_host("phone.local") and not P.is_lan_host("api.groq.com") and not P.is_lan_host("8.8.8.8"))
ck("short key accepted for his own server only", P.looks_like_key("abc123", "custom") and not P.looks_like_key("abc123") and not P.looks_like_key("https://x", "custom"))

# ---- 2. first connection: bare ip:port, self-signed https
port = free_port()
a = start("127.0.0.7", port, "a")
typed = "127.0.0.7:%d" % port
models = P.list_models("custom", KEY, typed)
ck("bare address resolved, models listed", [m["id"] for m in models] == ["qwen3-4b"], models)
ck("the spelling that answered is remembered", P.normalize_base(typed) == "https://127.0.0.7:%d/v1" % port, P.normalize_base(typed))
ck("certificate remembered on first use", len(P._lan_load()["pins"].get("127.0.0.7:%d" % port, "")) == 64)
ck("chat works with the typed text as the address", P.chat("custom", KEY, "qwen3-4b", [{"role": "user", "content": "hi"}], custom_base=typed) == "ready qwen3-4b")
ck("wrong key says invalid_key", code_of(lambda: P.list_models("custom", "wrong-key", typed)) == "invalid_key")
ck("bad address says unreachable (no crash)", code_of(lambda: P.list_models("custom", KEY, "127.0.0.7:1")) == "unreachable")

# ---- 3. the phone gets a new address: found by its certificate, key not sent while searching
stop(a); HITS.clear(); P._alive_at.clear()
a2 = start("127.0.0.9", port, "a")
other = start("127.0.0.8", port, "b")                               # another device on the same port with another certificate
reply = P.chat("custom", KEY, "qwen3-4b", [{"role": "user", "content": "hi"}], custom_base=typed)
ck("moved server found and used", reply == "ready qwen3-4b")
ck("new address remembered", P.moved_base("https://127.0.0.7:%d/v1" % port) == "https://127.0.0.9:%d/v1" % port, P._lan_load()["moved"])
ck("the other device never saw the key or a request", not [h for h in HITS if h[0] == "127.0.0.8"], HITS)
stop(other)

# ---- 4. a different certificate on a known address is refused, until he presses Test
stop(a2); P._alive_at.clear(); P._repin_until[0] = 0
b = start("127.0.0.9", port, "b")
ck("changed certificate refused in the background", code_of(lambda: P.chat("custom", KEY, "qwen3-4b", [{"role": "user", "content": "hi"}], custom_base=typed)) == "unreachable")
P.allow_repin()
ck("accepted after his own press", P.chat("custom", KEY, "qwen3-4b", [{"role": "user", "content": "hi"}], custom_base=typed) == "ready qwen3-4b")
P._repin_until[0] = 0
ck("and remembered", P.chat("custom", KEY, "qwen3-4b", [{"role": "user", "content": "hi"}], custom_base=typed) == "ready qwen3-4b")
stop(b)

# ---- 5. the settings channel: one paste connects and everything is remembered after a restart
port2 = free_port()
c = start("127.0.0.11", port2, "a")
lua = os.path.join(tmp, "lua"); os.makedirs(lua)
logs = []
svc = SS.Service(lua, log=logs.append)
SS.read_clipboard = lambda: "Address: 127.0.0.11:%d   Key: %s" % (port2, KEY)
svc.handle({"action": "paste_key", "provider": "auto"})
ck("paste: connected", svc.state["code"] == "models_ok" and svc.state["detected"] == "custom", (svc.state, logs))
ck("paste: saved at once (source, provider, address, the only model)", (svc.cfg["source"], svc.cfg["provider"], svc.cfg["base"], svc.cfg["model"]) == ("api", "custom", "https://127.0.0.11:%d/v1" % port2, "qwen3-4b"), svc.cfg)
ck("key stored encrypted, not in the config", S.get("custom") == KEY and KEY not in open(SS._cfg_path()).read() and KEY not in open(S._path()).read())
svc2 = SS.Service(lua, log=logs.append)                             # the Mind restarted
ck("after a restart: still connected, no key typed", svc2.active_source() == "api:custom/qwen3-4b", svc2.active_source())
svc2.handle({"action": "test", "source": "api", "provider": "custom", "model": "qwen3-4b", "base": "127.0.0.11:%d" % port2})
ck("Test with the address as typed", svc2.state["code"] == "test_ok", svc2.state)
svc2.handle({"action": "save", "source": "api", "provider": "custom", "model": "", "base": "127.0.0.11:%d" % port2})
ck("Save keeps the working address and the model", svc2.cfg["base"] == "https://127.0.0.11:%d/v1" % port2 and svc2.cfg["model"] == "qwen3-4b", svc2.cfg)
svc2.handle({"action": "fetch_models", "provider": "custom", "key": "", "base": "127.0.0.11:%d" % port2})
ck("Apply with an empty key box uses the stored key", svc2.state["code"] == "models_ok", svc2.state)
# the phone moves while the game is running
stop(c); P._alive_at.clear()
c2 = start("127.0.0.12", port2, "a")
P.chat("custom", S.get("custom"), "qwen3-4b", [{"role": "user", "content": "hi"}], custom_base=svc2.cfg["base"])
svc2.publish()
ck("settings: the saved address followed the phone", svc2.cfg["base"] == "https://127.0.0.12:%d/v1" % port2 and SS.load_config()["base"] == svc2.cfg["base"], svc2.cfg)
stop(c2)

# ---- 6. a server with no key, plain http
port3 = free_port()
d = start("127.0.0.13", port3, None, models=("m1", "m2"), need_key=False)
S.forget("custom")                                                 # he has no key for this one
svc3 = SS.Service(lua, log=logs.append)
svc3.handle({"action": "fetch_models", "provider": "custom", "key": "", "base": "http://127.0.0.13:%d" % port3})
ck("keyless http server connects", svc3.state["code"] == "models_ok" and svc3.cfg["base"] == "http://127.0.0.13:%d/v1" % port3 and svc3.cfg.get("keyless") is True, (svc3.state, svc3.cfg))
ck("two models: he chooses (none picked for him)", svc3.cfg["model"] == "")
svc3.handle({"action": "save", "source": "api", "provider": "custom", "model": "m2", "base": "http://127.0.0.13:%d" % port3})
ck("keyless: counts as connected", svc3.active_source() == "api:custom/m2", svc3.active_source())
stop(d)

# ---- 6b. another player's PC: address + key typed, Test pressed, nothing else: saved for next time
port4 = free_port()
e = start("127.0.0.14", port4, "b")
shutil.rmtree(os.environ["LOCALAPPDATA"]); os.makedirs(os.environ["LOCALAPPDATA"])     # a PC that never ran Sol
svc4 = SS.Service(lua, log=logs.append)
svc4.handle({"action": "fetch_models", "provider": "custom", "key": KEY, "base": "127.0.0.14:%d" % port4})
svc4.handle({"action": "test", "source": "api", "provider": "custom", "model": "", "base": "127.0.0.14:%d" % port4})
ck("new PC: Test works without picking the only model", svc4.state["code"] == "test_ok", svc4.state)
svc5 = SS.Service(lua, log=logs.append)                             # next day, game and Mind started again
ck("new PC: next start is connected with nothing typed", svc5.active_source() == "api:custom/qwen3-4b" and svc5.cfg["base"] == "https://127.0.0.14:%d/v1" % port4 and S.get("custom") == KEY, (svc5.active_source(), svc5.cfg))
ck("new PC: chat works from the saved settings", P.chat("custom", S.get("custom"), svc5.cfg["model"], [{"role": "user", "content": "hi"}], custom_base=svc5.cfg["base"]) == "ready qwen3-4b")
stop(e)

# ---- 6c. the phone app's own screen pasted whole: address, TLS pin and key (the pin is never taken for the key)
PIN_A, PIN_B = "H94tcE8Q3/3CjV4ZEmng5Uv8wiA6VQxCAr4SFn/kTDc=", "Q+95INCtL7z1L9AUlxHBo3P24uFvsAcGqpFO3HMDxB4="
ck("TLS pin computed like the app prints it", P.spki_pin(ssl.PEM_cert_to_DER_cert(open(os.path.join(FIX, "a.crt")).read())) == PIN_A)
screen = "Base URL https://127.0.0.15:%d/v1" + chr(10) + "TLS public key pin sha256//" + PIN_A + chr(10) + "API key " + KEY
ck("paste: pin separated from address and key", P.split_address_and_key(screen % 1234) == (KEY, "https://127.0.0.15:1234/v1") and P.find_tls_pin(screen % 1234) == PIN_A)
port5 = free_port()
f = start("127.0.0.15", port5, "a")
shutil.rmtree(os.environ["LOCALAPPDATA"]); os.makedirs(os.environ["LOCALAPPDATA"])
svc6 = SS.Service(lua, log=logs.append)
SS.read_clipboard = lambda: screen % port5
svc6.handle({"action": "paste_key", "provider": "auto"})
ck("whole screen pasted: connected, pin matched", svc6.state["code"] == "models_ok" and svc6.cfg["base"] == "https://127.0.0.15:%d/v1" % port5 and S.get("custom") == KEY, (svc6.state, svc6.cfg))
stop(f); P._alive_at.clear()
g = start("127.0.0.15", port5, "b")                                  # an impostor on the same address with another key pair
P.allow_repin()
ck("a server with another TLS key is refused even on his press", code_of(lambda: P.list_models("custom", KEY, "https://127.0.0.15:%d/v1" % port5)) == "unreachable")
P._repin_until[0] = 0
stop(g)

# ---- 7. other providers untouched
ck("public providers keep their own address and the strict key shape", P.base_url("groq") == "https://api.groq.com/openai/v1" and P.candidates("gsk_x" * 5) == ["groq"])
ck("a public https address is not treated as home", not P.is_lan_host(P._origin("https://api.groq.com/openai/v1")[0]))

shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
