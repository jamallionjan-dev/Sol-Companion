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

