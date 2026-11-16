"""Settings channel between the in-game Sol settings window and Sol Mind.
Files in the Zomboid Lua folder (same folder as the mailbox):
  SolSettings_Request.txt  written by the game   (one request, id increases)
  SolSettings_State.txt    written by Sol Mind   (full state, ack = last handled id)
Line format: key=value, values escaped (%25 %, %0A newline, %3D =).
API keys never travel back to the game: only a hint (sk-or-v1****3f9a)."""
import json, os, subprocess, sys, threading, time, webbrowser
import providers as P
import secret_store as S

REQ, STATE = "SolSettings_Request.txt", "SolSettings_State.txt"
SOURCES = ("api", "local", "bridge", "manual", "none")
LINK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sol_link")

def start_link(log=print):
    """Sol Link (ChatGPT in the browser) runs for as long as 'bridge' is the chosen source."""
    try:
        import sol_link
        return sol_link.get(log=log, script_dir=LINK_DIR)
    except OSError as e:
        log("sol link: could not start: %s" % e); return None

def esc(v): return str(v).replace("%", "%25").replace("\n", "%0A").replace("\r", "").replace("=", "%3D")
def unesc(v): return v.replace("%0A", "\n").replace("%3D", "=").replace("%25", "%")

def parse(text):
    d = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1); d[k.strip()] = unesc(v)
    return d

def dump(d):
    return "".join("%s=%s\n" % (k, esc(v)) for k, v in d.items())

def _cfg_path():
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    p = os.path.join(root, "SolMind"); os.makedirs(p, exist_ok=True)
    return os.path.join(p, "config.json")

def load_config():
    try:
        with open(_cfg_path(), encoding="utf-8") as f: c = json.load(f)
    except (OSError, ValueError): c = {}
    c.setdefault("source", "none"); c.setdefault("provider", ""); c.setdefault("model", "")
    c.setdefault("base", ""); c.setdefault("fallback_provider", ""); c.setdefault("fallback_model", "")
    return c

def save_config(c):
    with open(_cfg_path(), "w", encoding="utf-8") as f: json.dump(c, f, indent=1)

def read_clipboard():
    if sys.platform != "win32": return os.environ.get("SOLMIND_TEST_CLIPBOARD", "")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"], capture_output=True, text=True, timeout=10)
    return (r.stdout or "").strip()

class Service:
    def __init__(self, lua_dir, log=print, opener=webbrowser.open):
        self.dir = lua_dir; self.log = log; self.open = opener
        self.ack = 0; self.cfg = load_config()
        self.state = {"status": "idle", "code": "", "models": [], "detected": "", "latency": "", "hint": "", "detail": ""}

    # ---------- state file
    def publish(self):
        if self.cfg.get("provider") == "custom" and self.cfg.get("base"):       # s153: the phone moved: the saved address follows it
            now = P.moved_base(self.cfg["base"])
            if now != self.cfg["base"]:
                self.log("settings: the model server moved, address updated")
                self.cfg["base"] = now; save_config(self.cfg)
        st = {"ack": self.ack, "status": self.state["status"], "code": self.state["code"],
              "source": self.cfg["source"], "provider": self.cfg["provider"], "model": self.cfg["model"],
              "base": self.cfg["base"], "fallback": (self.cfg["fallback_provider"] + ":" + self.cfg["fallback_model"]).strip(":"),
              "detected": self.state["detected"], "hint": self.state["hint"], "latency": self.state["latency"], "detail": self.state["detail"],
              "protected": "1" if S.PROTECTED else "0",
              "stored": ",".join(pid for pid in P.ORDER if S.get(pid)),
              "providers": ",".join(P.ORDER), "count": len(self.state["models"]),
              "active": self.active_source()}
        for i, m in enumerate(self.state["models"][:200], 1):
            st["m%d" % i] = "%s|%s|%d|%d" % (m["id"], m["badge"], 1 if m["warn"] else 0, 1 if m["supported"] else 0)
        tmp = os.path.join(self.dir, STATE + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f: f.write(dump(st))
        os.replace(tmp, os.path.join(self.dir, STATE))

    def active_source(self):
        """What is actually driving Sol right now, not merely what is selected.
        An API source with no key or no model cannot answer, so the state says
        so plainly instead of letting the window claim a working brain."""
        c = self.cfg
        src = c.get("source", "none")
        if src == "api":
            if not c.get("provider"): return "none:no_provider"
            if not S.get(c["provider"]) and not (c["provider"] == "custom" and c.get("keyless")): return "none:no_key"   # s153: his own server may have no key
            if not c.get("model"): return "none:no_model"
            return "api:" + c["provider"] + "/" + c["model"]
        if src == "local":
            return "local:" + (c.get("model") or "no_model")
        if src == "bridge":
            return "bridge"
        return src

    def _scrub_key(self, path, req):
        """Remove a typed key from the request file once it has been read."""
        if req.get("key"):
            req = dict(req); req.pop("key")
            try:
                with open(path, "w", encoding="utf-8", newline="\n") as f: f.write(dump(req))
            except OSError: pass

    # ---------- actions
    def handle(self, req):
        act = req.get("action", "")
        pid = req.get("provider", "") or "auto"
        base = req.get("base", self.cfg.get("base", ""))
        try:
            if act in ("fetch_models", "paste_key", "use_provider", "test"):
                P.allow_repin()                                                 # s153: his own press accepts a renewed certificate at home
            if act in ("fetch_models", "paste_key"):
                key = read_clipboard() if act == "paste_key" else req.get("key", "").strip()
                if act == "paste_key" and not key:
                    return self._err("clipboard_empty")
                # s153: the text may hold the phone's address and its key together, or only the address
                tls_pin = P.find_tls_pin(key)
                rest, address = P.split_address_and_key(key)
                if address and pid in ("auto", "custom"):
                    key, base, pid = rest, address, "custom"
                elif tls_pin:
                    key = rest
                if tls_pin and pid == "custom" and base: P.set_tls_pin(base, tls_pin)      # the app's own pin checks the first connection
                if not key and pid != "auto":
                    key = S.get(pid) or ""
                if not key and pid not in ("ollama", "custom"):
                    return self._err("no_key")
                if key and not P.looks_like_key(key, pid):
                    return self._err("not_a_key")
                found, models = P.detect(key, pid, base) if pid != "ollama" else ("ollama", P.list_models("ollama", "", base))
                if found == "custom":
                    base = P.normalize_base(base)                               # the spelling that answered
                    self.cfg["keyless"] = not key
                    if not key: S.forget("custom")
                if found != "ollama" and key:
                    S.put(found, key)
                self.state.update(status="ok", code="models_ok", models=models, detected=found, hint=P.key_hint(key) if key else "")
                # Detection only fills in the provider when the player asked for
                # "auto". An explicit choice is never overwritten by whatever the
                # key happens to look like.
                if pid == "auto" or not self.cfg.get("provider") or found == "custom":
                    self.cfg["provider"] = found
                if base: self.cfg["base"] = base
                if found == "custom":                                           # s153: one press connects: remembered at once, not only after Save
                    self.cfg["source"] = "api"
                    ids = [m["id"] for m in models if m.get("supported")]
                    if self.cfg.get("model") not in ids: self.cfg["model"] = ids[0] if len(ids) == 1 else ""
                    save_config(self.cfg)
                return
            if act == "disconnect":
                # Let go of the current provider without losing its key, so the
                # player can pick another one and come back later.
                previous = self.cfg.get("provider", "")
                self.cfg.update(source="none", provider="", model="", base="")
                save_config(self.cfg)
                self.state.update(status="ok", code="disconnected", models=[],
                                  detected="", hint="", latency="",
                                  detail=previous and ("was: " + previous) or "")
                return
            if act == "use_provider":
                # Activate a provider that already has a stored key, in one step.
                if pid in ("", "auto"): return self._err("no_provider")
                if pid == "ollama":
                    self.cfg.update(source="local", provider="ollama", model="", base=base)
                    save_config(self.cfg)
                    models = P.list_models("ollama", "", base)
                    self.state.update(status="ok", code="models_ok", models=models,
                                      detected="ollama", hint="")
                    return
                key = S.get(pid) or ""
                if not key and not (pid == "custom" and self.cfg.get("keyless")): return self._err("no_key")
                models = P.list_models(pid, key, base)
                if pid == "custom": base = P.normalize_base(base)
                self.cfg.update(source="api", provider=pid, model="", base=base)
                save_config(self.cfg)
                self.state.update(status="ok", code="models_ok", models=models,
                                  detected=pid, hint=P.key_hint(key))
                return
            if act == "save":
                src = req.get("source", self.cfg["source"])
                if src not in SOURCES: return self._err("bad_source")
                if req.get("provider", self.cfg["provider"]) == "custom":      # s153: the address that answered; an empty model box keeps the chosen model
                    base = P.normalize_base(base) if base else self.cfg.get("base", "")   # a window showing another provider sends no address: the saved one stays
                    if not req.get("model") and self.cfg.get("provider") == "custom" and self.cfg.get("model"): req = dict(req, model=self.cfg["model"])
                self.cfg.update(source=src, provider=req.get("provider", self.cfg["provider"]), model=req.get("model", self.cfg["model"]),
                                base=base, fallback_provider=req.get("fallback_provider", self.cfg["fallback_provider"]),
                                fallback_model=req.get("fallback_model", self.cfg["fallback_model"]))
                save_config(self.cfg)
                if src == "bridge": start_link(self.log)
                self.state.update(status="ok", code="saved"); return
            if act == "test":
                # test what the window shows now, even before it is saved
                c = dict(self.cfg)
                for k in ("source", "provider", "model", "base"):
                    if req.get(k): c[k] = req[k]
                if c["source"] == "bridge":
                    link = start_link(self.log)
                    if link and link.connected(10): self.state.update(status="ok", code="bridge_ok"); return
                    return self._err("bridge_not_connected")
                if c["source"] not in ("api", "local"): return self._err("source_has_no_test")
                key = S.get(c["provider"]) or ""
                if c["provider"] == "custom" and not c["model"]:
                    ids = [m["id"] for m in P.list_models("custom", key, c.get("base", "")) if m.get("supported")]
                    if len(ids) == 1: c["model"] = ids[0]
                if not c["model"]: return self._err("no_model")
                reply, secs = P.test(c["provider"], key, c["model"], c.get("base", ""))
                if reply and c["provider"] == "custom":
                    self.cfg.update(source="api", provider="custom", model=c["model"], base=P.normalize_base(c.get("base", "")))
                    self.cfg["keyless"] = not key
                    save_config(self.cfg)
                self.state.update(status="ok" if reply else "error", code="test_ok" if reply else "empty_reply", latency=str(secs)); return
            if act == "open_key_page":
                url = P.PROVIDERS.get(pid, {}).get("key_page", "")
                if not url: return self._err("no_key_page")
                self.open(url); self.state.update(status="ok", code="opened"); return
            if act == "forget_key":
                S.forget(pid); self.state.update(status="ok", code="key_removed", hint=""); return
            return self._err("unknown_action")
        except P.ProviderError as e:
            self.log("settings: %s failed: %s %s" % (act, e.code, e.detail))
            return self._err(e.code, e.detail)

    def _err(self, code, detail=""):
        self.state.update(status="error", code=code, detail=detail)

    # ---------- loop
    def poll_once(self):
        path = os.path.join(self.dir, REQ)
        try:
            with open(path, encoding="utf-8") as f: req = parse(f.read())
        except OSError:
            return False
        try: rid = int(req.get("id", "0"))
        except ValueError: return False
        if rid <= self.ack: return False
        self._scrub_key(path, req)
        self.state.update(status="working", code="", detail=""); self.ack = rid - 1; self.publish()
        self.handle(req)
        self.ack = rid; self.publish()
        self.log("settings: request %d %s -> %s %s" % (rid, req.get("action"), self.state["status"], self.state["code"]))
        return True

    def start(self, interval=0.25):
        # ignore a request that was already in the file before Sol Mind started
        try:
            with open(os.path.join(self.dir, REQ), encoding="utf-8") as f:
                self.ack = max(self.ack, int(parse(f.read()).get("id", "0") or 0))
        except (OSError, ValueError):
            pass
        self.publish()
        self._stop = threading.Event()
        def loop():
            while not self._stop.is_set():
                try: self.poll_once()
                except Exception as e: self.log("settings: loop error %r" % (e,))
                self._stop.wait(interval)
        t = threading.Thread(target=loop, name="sol-settings", daemon=True); t.start(); return t

    def stop(self): self._stop.set()
