"""s153: a model on a phone (or another PC at home) connects without fiddling, and stays connected.
usage: apply_s153_phone_model.py <sol_mind dir>
providers.py        - home-network https servers are trusted on first use and recognised by certificate fingerprint; a
                      server whose address changed is found again by that fingerprint; a typed address is tried with
                      https/http and with/without /v1; a short key is accepted for the player's own server
settings_service.py - a pasted text may hold the address and the key together; the address that answered is the one saved;
                      a server without a key is allowed for Custom; the saved address follows the phone when it moves
Exact old->new strings; "kept" when already applied."""
import os, sys
MIND = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)


class File:
    def __init__(self, name):
        self.path = os.path.join(MIND, name); self.name = name
        self.text = open(self.path, encoding="utf-8", newline="").read()
        self.nl = CRLF if CRLF in self.text else NL
        self.changed = False
    def edit(self, old, new):
        old, new = old.replace(NL, self.nl), new.replace(NL, self.nl)
        if new in self.text: print("kept " + self.name); return
        if self.text.count(old) != 1: raise RuntimeError((self.name, "expected one exact source block", self.text.count(old), old[:80]))
        self.text = self.text.replace(old, new); self.changed = True; print("edited " + self.name)
    def save(self):
        if self.changed: open(self.path, "w", encoding="utf-8", newline="").write(self.text)


p = File("providers.py")
p.edit('import json, time, urllib.request, urllib.error, ssl, pathlib, urllib.parse\n',
       'import json, time, urllib.request, urllib.error, ssl, pathlib, urllib.parse\nimport base64, hashlib, http.client, ipaddress, os, re, socket, threading\n')
block = open(os.path.join(HERE, "s153_lan_block.py.txt"), encoding="utf-8").read().replace(CRLF, NL).replace(NL, p.nl)
if block in p.text:
    print("kept providers.py (request block)")
else:
    start = p.text.index("def _http(method, url, headers, body=None, timeout=20):")
    end = p.text.index('def base_url(pid, custom_base=""):')
    if "_http_once" in p.text[start:end] or p.text.count("def _http(") != 1: raise RuntimeError("providers.py: unexpected _http")
    p.text = p.text[:start] + block + p.text[end:]; p.changed = True; print("edited providers.py (request block)")
p.edit('''    b = custom_base.strip().rstrip("/") if pid in ("custom", "ollama") and custom_base.strip() else PROVIDERS[pid]["base"]
''', '''    b = normalize_base(custom_base) if pid in ("custom", "ollama") and custom_base.strip() else PROVIDERS[pid]["base"]
''')
p.edit('''def looks_like_key(text):
    """Shape check done BEFORE any network call, so random clipboard text is never sent anywhere."""
    return bool(_KEY_RE.match((text or "").strip()))
''', '''_KEY_RE_OWN = _re.compile(r"^[A-Za-z0-9_\\-\\.:+/=@!#$%&*~^]{3,300}$")
def looks_like_key(text, pid=""):
    """Shape check done BEFORE any network call, so random clipboard text is never sent anywhere.
    For the player's own server (custom) a short key is fine: phone apps hand out short ones."""
    k = (text or "").strip()
    if pid == "custom": return bool(_KEY_RE_OWN.match(k)) and not k.lower().startswith(("http://", "https://"))
    return bool(_KEY_RE.match(k))
''')
p.edit('''def list_models(pid, key, custom_base="", timeout=20):
    b = base_url(pid, custom_base)
    if not b:
        raise ProviderError("no_base_url")
''', '''def list_models(pid, key, custom_base="", timeout=20):
    b = base_url(pid, custom_base)
    if not b:
        raise ProviderError("no_base_url")
    if pid == "custom":                                    # s153: the typed address is tried in its usual spellings
        b, raw = resolve_base(custom_base, key, timeout=min(timeout, 8))
        out = []
        for m in raw:
            mid = str((m.get("id", m.get("name", "")) if isinstance(m, dict) else m) or "").strip()
            if not mid: continue
            badge, warn, supported = _label(pid, {"id": mid})
            out.append({"id": mid, "badge": badge, "warn": warn, "supported": supported})
        out.sort(key=lambda x: (not x["supported"], x["id"]))
        return out
''')
p.save()

s = File("settings_service.py")
s.edit('''            if not c.get("provider"): return "none:no_provider"
            if not S.get(c["provider"]): return "none:no_key"
''', '''            if not c.get("provider"): return "none:no_provider"
            if not S.get(c["provider"]) and not (c["provider"] == "custom" and c.get("keyless")): return "none:no_key"   # s153: his own server may have no key
''')
s.edit('''        pid = req.get("provider", "") or "auto"
        base = req.get("base", self.cfg.get("base", ""))
        try:
            if act in ("fetch_models", "paste_key"):
                key = read_clipboard() if act == "paste_key" else req.get("key", "").strip()
                if act == "paste_key" and not key:
                    return self._err("clipboard_empty")
                if not key and pid != "auto":
                    key = S.get(pid) or ""
                if not key and pid != "ollama":
                    return self._err("no_key")
                if key and not P.looks_like_key(key):
                    return self._err("not_a_key")
                found, models = P.detect(key, pid, base) if pid != "ollama" else ("ollama", P.list_models("ollama", "", base))
                if found != "ollama":
                    S.put(found, key)
''', '''        pid = req.get("provider", "") or "auto"
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
''')
s.edit('''                if pid == "auto" or not self.cfg.get("provider"):
                    self.cfg["provider"] = found
                if base: self.cfg["base"] = base
                return
''', '''                if pid == "auto" or not self.cfg.get("provider") or found == "custom":
                    self.cfg["provider"] = found
                if base: self.cfg["base"] = base
                if found == "custom":                                           # s153: one press connects: remembered at once, not only after Save
                    self.cfg["source"] = "api"
                    ids = [m["id"] for m in models if m.get("supported")]
                    if self.cfg.get("model") not in ids: self.cfg["model"] = ids[0] if len(ids) == 1 else ""
                    save_config(self.cfg)
                return
''')
s.edit('''                key = S.get(pid) or ""
                if not key: return self._err("no_key")
                models = P.list_models(pid, key, base)
                self.cfg.update(source="api", provider=pid, model="", base=base)
''', '''                key = S.get(pid) or ""
                if not key and not (pid == "custom" and self.cfg.get("keyless")): return self._err("no_key")
                models = P.list_models(pid, key, base)
                if pid == "custom": base = P.normalize_base(base)
                self.cfg.update(source="api", provider=pid, model="", base=base)
''')
s.edit('''                self.cfg.update(source=src, provider=req.get("provider", self.cfg["provider"]), model=req.get("model", self.cfg["model"]),
                                base=base, fallback_provider''', '''                if req.get("provider", self.cfg["provider"]) == "custom":      # s153: the address that answered; an empty model box keeps the chosen model
                    base = P.normalize_base(base) if base else self.cfg.get("base", "")   # a window showing another provider sends no address: the saved one stays
                    if not req.get("model") and self.cfg.get("provider") == "custom" and self.cfg.get("model"): req = dict(req, model=self.cfg["model"])
                self.cfg.update(source=src, provider=req.get("provider", self.cfg["provider"]), model=req.get("model", self.cfg["model"]),
                                base=base, fallback_provider''')
s.edit('''    def publish(self):
        st = {"ack": self.ack,''', '''    def publish(self):
        if self.cfg.get("provider") == "custom" and self.cfg.get("base"):       # s153: the phone moved: the saved address follows it
            now = P.moved_base(self.cfg["base"])
            if now != self.cfg["base"]:
                self.log("settings: the model server moved, address updated")
                self.cfg["base"] = now; save_config(self.cfg)
        st = {"ack": self.ack,''')
s.save()
print("s153 phone model connection applied")

# s153c (Jamal 2026-11-15: "he puts the phone's address and the key, tests, and when it works it is saved"):
# a successful Test of his own server saves what was tested; with one model on the server no model has to be picked first
s3 = File("settings_service.py")
s3.edit('''                key = S.get(c["provider"]) or ""
                if not c["model"]: return self._err("no_model")
                reply, secs = P.test(c["provider"], key, c["model"], c.get("base", ""))
                self.state.update(status="ok" if reply else "error", code="test_ok" if reply else "empty_reply", latency=str(secs)); return
''', '''                key = S.get(c["provider"]) or ""
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
''')
s3.save()
