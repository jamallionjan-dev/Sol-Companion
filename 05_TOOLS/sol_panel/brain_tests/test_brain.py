import json, os, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
tmp = tempfile.mkdtemp(); os.environ["LOCALAPPDATA"] = tmp
import providers as P, secret_store as S, settings_service as SS

KEYS = {"/anthropic": "sk-ant-api03-GOODKEY1234567890", "/openrouter": "sk-or-v1-GOODKEY99993f9a", "/groq": "gsk_GOODKEY5555555555555",
        "/opencode": "ocz-GOODKEY7777777777777", "/deepseek": "sk-GOODDEEPSEEK0001"}
LOG = []
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
    def _key(self):
        a = self.headers.get("Authorization", ""); return self.headers.get("x-api-key") or (a[7:] if a.startswith("Bearer ") else "")
    def _prov(self): return "/" + self.path.split("/")[1]
    def do_GET(self):
        pv = self._prov(); LOG.append(("GET", self.path))
        if pv == "/ollama":
            return self._send(200, {"models": [{"name": "qwen3:8b"}, {"name": "llama3.2:3b"}]})
        if self._key() != KEYS.get(pv): return self._send(401, {"error": "bad key"})
        data = {"/anthropic": [{"id": "claude-haiku-4-5"}, {"id": "claude-sonnet-4-6"}],
                "/openrouter": [{"id": "deepseek/deepseek-v4-flash:free", "pricing": {"prompt": "0", "completion": "0"}},
                                {"id": "anthropic/claude-haiku-4.5", "pricing": {"prompt": "0.000001", "completion": "0.000005"}}],
                "/groq": [{"id": "llama-3.3-70b-versatile"}, {"id": "openai/gpt-oss-120b"}, {"id": "whisper-large-v3-turbo"}, {"id": "canopylabs/orpheus-arabic-saudi"}, {"id": "meta-llama/llama-prompt-guard-2-22m"}],
                "/opencode": [{"id": "gpt-5.5"}, {"id": "mimo-v2.5-free"}, {"id": "big-pickle"}, {"id": "glm-5.1"}, {"id": "claude-sonnet-4-6"}],
                "/deepseek": [{"id": "deepseek-chat"}]}[pv]
        self._send(200, {"data": data})
    def do_POST(self):
        pv = self._prov(); n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}"); LOG.append(("POST", self.path, body.get("model")))
        if pv == "/ollama": return self._send(200, {"message": {"content": "ready"}})
        if self._key() != KEYS.get(pv): return self._send(401, {})
        if pv == "/anthropic": return self._send(200, {"content": [{"type": "text", "text": "ready"}]})
        if "gpt-oss" in str(body.get("model")) and (body.get("reasoning_effort") != "low" or body.get("max_tokens", 0) < 1024):
            return self._send(200, {"choices": [{"finish_reason": "length", "message": {"content": "", "reasoning": "thinking..."}}]})
        self._send(200, {"choices": [{"message": {"content": "ready"}}]})
srv = ThreadingHTTPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = "http://127.0.0.1:%d" % port
for pid, path in (("anthropic", "/anthropic"), ("openrouter", "/openrouter"), ("groq", "/groq"), ("opencode", "/opencode"),
                  ("deepseek", "/deepseek"), ("openai", "/openai"), ("ollama", "/ollama")):
    P.PROVIDERS[pid]["base"] = B + path

res = []
def check(name, cond): res.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name)

check("detect by prefix: sk-ant- -> anthropic", P.candidates("sk-ant-api03-x") == ["anthropic"])
check("detect by prefix: sk-or- -> openrouter", P.candidates("sk-or-v1-x") == ["openrouter"])
check("generic sk- tries openai, deepseek, opencode", P.candidates("sk-abc") == ["openai", "deepseek", "opencode"])
pid, ms = P.detect(KEYS["/deepseek"]); check("generic sk- key found at deepseek after openai rejects it", pid == "deepseek" and ms[0]["id"] == "deepseek-chat")
pid, ms = P.detect(KEYS["/opencode"]); ids = [m["id"] for m in ms]
check("OpenCode key without prefix is detected", pid == "opencode")
check("OpenCode free models first and labelled free", ms[0]["badge"] == "free" and set(ids[:2]) == {"big-pickle", "mimo-v2.5-free"})
check("OpenCode free models carry data warning", all(m["warn"] for m in ms if m["badge"] == "free"))
check("OpenCode gpt-/claude- models marked not supported yet", not next(m for m in ms if m["id"] == "gpt-5.5")["supported"] and not next(m for m in ms if m["id"] == "claude-sonnet-4-6")["supported"])
pid, ms = P.detect(KEYS["/openrouter"])
check("OpenRouter pricing -> free/paid", [m["badge"] for m in ms] == ["free", "paid"])
pid, ms = P.detect(KEYS["/groq"]); check("Groq -> free tier label", ms[0]["badge"] == "tier")
nc = {m["id"]: m for m in ms}
check("Groq whisper/orpheus/guard marked nochat and not selectable", all(nc[i]["badge"] == "nochat" and not nc[i]["supported"] for i in ("whisper-large-v3-turbo", "canopylabs/orpheus-arabic-saudi", "meta-llama/llama-prompt-guard-2-22m")))
check("chat models listed before non-chat models", [m["supported"] for m in ms] == sorted([m["supported"] for m in ms], reverse=True))
check("gpt-oss gets reasoning_effort=low + 1024 -> non-empty reply (was empty before fix)", P.chat("groq", KEYS["/groq"], "openai/gpt-oss-120b", [{"role": "user", "content": "x"}], max_tokens=120) == "ready")
reply, secs = P.test("groq", KEYS["/groq"], "openai/gpt-oss-120b"); check("test button on gpt-oss returns a reply", reply == "ready")
pid, ms = P.detect(KEYS["/anthropic"]); check("Anthropic -> paid", all(m["badge"] == "paid" for m in ms))
try: P.detect("sk-ant-api03-WRONGWRONGWRONG"); check("bad key rejected", False)
except P.ProviderError as e: check("bad key rejected with invalid_key", e.code == "invalid_key")
check("chat anthropic", P.chat("anthropic", KEYS["/anthropic"], "claude-haiku-4-5", [{"role": "user", "content": "hi"}]) == "ready")
check("chat openai-compatible (opencode free)", P.chat("opencode", KEYS["/opencode"], "mimo-v2.5-free", [{"role": "user", "content": "hi"}]) == "ready")
check("ollama models + chat", [m["id"] for m in P.list_models("ollama", "")][0] in ("llama3.2:3b", "qwen3:8b") and P.chat("ollama", "", "qwen3:8b", [{"role": "user", "content": "x"}]) == "ready")
check("key hint hides the key", P.key_hint(KEYS["/openrouter"]) == "sk-or-v1-****3f9a")
try: P.detect("sk-ant-x", custom_base=""); 
except P.ProviderError: pass
P.PROVIDERS["custom"]["base"] = ""
try: P.list_models("custom", "k"); check("custom without URL refused", False)
except P.ProviderError as e: check("custom without URL refused", e.code == "no_base_url")

# ---------- settings channel end-to-end
lua = tempfile.mkdtemp(); opened = []
svc = SS.Service(lua, log=LOG.append, opener=opened.append)
def request(**kw):
    request.n = getattr(request, "n", 0) + 1
    with open(os.path.join(lua, SS.REQ), "w", encoding="utf-8") as f: f.write(SS.dump(dict(id=request.n, **kw)))
    svc.poll_once()
    return SS.parse(open(os.path.join(lua, SS.STATE), encoding="utf-8").read())
st = request(action="fetch_models", provider="auto", key=KEYS["/openrouter"])
check("fetch via typed key -> ok, detected openrouter", st["status"] == "ok" and st["detected"] == "openrouter" and st["count"] == "2")
check("state carries hint, never the key", KEYS["/openrouter"] not in open(os.path.join(lua, SS.STATE)).read() and st["hint"] == "sk-or-v1-****3f9a")
check("typed key scrubbed from request file", KEYS["/openrouter"] not in open(os.path.join(lua, SS.REQ)).read())
check("key stored encrypted-at-rest file, not plaintext", KEYS["/openrouter"] not in open(os.path.join(tmp, "SolMind", "secrets.json")).read() and S.get("openrouter") == KEYS["/openrouter"])
check("model line format id|badge|warn|supported", st["m1"] == "deepseek/deepseek-v4-flash:free|free|1|1")
os.environ["SOLMIND_TEST_CLIPBOARD"] = KEYS["/opencode"]
st = request(action="paste_key", provider="auto")
check("paste button: key read from clipboard by Sol Mind, never via game files", st["detected"] == "opencode" and KEYS["/opencode"] not in open(os.path.join(lua, SS.REQ)).read())
os.environ["SOLMIND_TEST_CLIPBOARD"] = ""
st = request(action="paste_key", provider="auto"); check("empty clipboard -> clipboard_empty", st["code"] == "clipboard_empty")
st = request(action="save", source="api", provider="opencode", model="mimo-v2.5-free", fallback_provider="ollama", fallback_model="qwen3:8b")
check("save -> config persisted", st["code"] == "saved" and SS.load_config()["model"] == "mimo-v2.5-free" and st["fallback"] == "ollama:qwen3:8b")
st = request(action="test"); check("test uses stored key -> test_ok with latency", st["code"] == "test_ok" and st["latency"] != "")
st = request(action="fetch_models", provider="openrouter"); check("re-fetch with stored key (no key resent)", st["code"] == "models_ok")
st = request(action="open_key_page", provider="anthropic"); check("open key page", opened == ["https://platform.claude.com/settings/keys"])
st = request(action="fetch_models", provider="auto", key="sk-ant-api03-WRONGWRONGWRONG"); check("wrong key -> invalid_key error state", st["status"] == "error" and st["code"] == "invalid_key")
st = request(action="forget_key", provider="opencode"); check("forget key", S.get("opencode") is None and "opencode" not in st["stored"].split(","))
old = request.n; svc.poll_once(); check("same request id is not handled twice", SS.parse(open(os.path.join(lua, SS.STATE)).read())["ack"] == str(old))
check("escaping round-trip", SS.parse(SS.dump({"a": "x=1\n%y"}))["a"] == "x=1\n%y")
check("no key ever written to Sol Mind log", not any(any(k in str(l) for k in KEYS.values()) for l in LOG if isinstance(l, str)))
lua2 = tempfile.mkdtemp(); opened2 = []
with open(os.path.join(lua2, SS.REQ), "w", encoding="utf-8") as f: f.write(SS.dump({"id": 99, "action": "open_key_page", "provider": "openai"}))
svc2 = SS.Service(lua2, log=LOG.append, opener=opened2.append); t = svc2.start(interval=0.05)
import time as _t; _t.sleep(0.3); svc2.stop()
check("stale request present at startup is ignored (no browser opens)", opened2 == [] and SS.parse(open(os.path.join(lua2, SS.STATE)).read())["ack"] == "99")
os.environ["SOLMIND_TEST_CLIPBOARD"] = "Living Fellows"
before = len([l for l in LOG if isinstance(l, tuple)])
st = request(action="paste_key", provider="auto")
check("non-key clipboard text refused with not_a_key and NO network call", st["code"] == "not_a_key" and len([l for l in LOG if isinstance(l, tuple)]) == before)
st = request(action="fetch_models", provider="auto", key="sk-WRONGWRONGWRONGWRONG1")
check("error detail names every provider that rejected the key", st["code"] == "invalid_key" and "OpenAI" in st["detail"] and "DeepSeek" in st["detail"] and "OpenCode" in st["detail"])
srv.shutdown()
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
