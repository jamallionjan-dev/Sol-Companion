"""Sol Mind brain providers: key detection, model listing, free/paid labels, chat.
Standard library only (urllib). Every network call has a timeout and never logs the key."""
import json, time, urllib.request, urllib.error, ssl, pathlib, urllib.parse
import base64, hashlib, http.client, ipaddress, os, re, socket, threading

# kind: anthropic | openai (OpenAI-compatible chat/completions) | ollama
# tier: label used when the provider does not publish per-model prices
PROVIDERS = {
    "anthropic":  {"name": "Anthropic (Claude)", "kind": "anthropic", "base": "https://api.anthropic.com/v1",
                   "prefixes": ["sk-ant-"], "tier": "paid", "key_page": "https://platform.claude.com/settings/keys"},
    "openai":     {"name": "OpenAI", "kind": "openai", "base": "https://api.openai.com/v1",
                   "prefixes": ["sk-proj-", "sk-svcacct-"], "tier": "paid", "key_page": "https://platform.openai.com/api-keys"},
    "gemini":     {"name": "Google Gemini", "kind": "openai", "base": "https://generativelanguage.googleapis.com/v1beta/openai",
                   "prefixes": ["AIza"], "tier": "tier", "key_page": "https://aistudio.google.com/apikey"},
    "openrouter": {"name": "OpenRouter", "kind": "openai", "base": "https://openrouter.ai/api/v1",
                   "prefixes": ["sk-or-"], "tier": "priced", "key_page": "https://openrouter.ai/settings/keys"},
    "groq":       {"name": "Groq", "kind": "openai", "base": "https://api.groq.com/openai/v1",
                   "prefixes": ["gsk_"], "tier": "tier", "key_page": "https://console.groq.com/keys"},
    "xai":        {"name": "xAI (Grok)", "kind": "openai", "base": "https://api.x.ai/v1",
                   "prefixes": ["xai-"], "tier": "paid", "key_page": "https://console.x.ai"},
    "deepseek":   {"name": "DeepSeek", "kind": "openai", "base": "https://api.deepseek.com",
                   "prefixes": [], "tier": "paid", "key_page": "https://platform.deepseek.com/api_keys"},
    "mistral":    {"name": "Mistral", "kind": "openai", "base": "https://api.mistral.ai/v1",
                   "prefixes": [], "tier": "tier", "key_page": "https://console.mistral.ai/api-keys"},
    "opencode":   {"name": "OpenCode Zen", "kind": "openai", "base": "https://opencode.ai/zen/v1",
                   "prefixes": [], "tier": "priced", "key_page": "https://opencode.ai/zen"},
    "custom":     {"name": "Custom URL", "kind": "openai", "base": "", "prefixes": [], "tier": "unknown", "key_page": ""},
    "ollama":     {"name": "Local (Ollama)", "kind": "ollama", "base": "http://localhost:11434", "prefixes": [], "tier": "local", "key_page": ""},
}
ORDER = ["anthropic", "openai", "gemini", "openrouter", "groq", "xai", "deepseek", "mistral", "opencode", "custom", "ollama"]
# keys without a distinctive prefix: providers tried in this order
GENERIC_SK = ["openai", "deepseek", "opencode"]
GENERIC_OTHER = ["opencode", "mistral"]
# OpenCode Zen: free models known from its docs; ids ending in -free are free too
OPENCODE_FREE = {"big-pickle"}

class ProviderError(Exception):
    def __init__(self, code, detail=""):
        super().__init__(code); self.code = code; self.detail = detail

def _headers(pid, key):
    p = PROVIDERS[pid]
    h = {"Content-Type": "application/json", "User-Agent": "SolMind/0.2.2"}
    if p["kind"] == "anthropic":
        h["x-api-key"] = key; h["anthropic-version"] = "2023-06-01"
    elif key:
        h["Authorization"] = "Bearer " + key
    return h

def _iphone_context(url):
    target = urllib.parse.urlsplit(url)
    if target.scheme == 'https' and target.hostname == '192.168.1.140' and target.port == 11434:
        cert_path = pathlib.Path(__file__).with_name('iphone_localcoder.pem')
        context = ssl.create_default_context(cafile=str(cert_path))
        context.check_hostname = False  # This exact self-signed certificate has no IP SAN.
        return context
    return None
# ---------------------------------------------------------------- s153: a model on a phone or another PC in the house
# The phone app shows an address and a key. Three things made that fiddly: (1) its https certificate is self-signed, so
# Python refused it unless a .pem was copied by hand for one fixed address; (2) the phone's address changes when the
# router hands it a new one; (3) the address had to be typed exactly (scheme, port, /v1).
# Here: (1) a server on the home network is trusted on first use and recognised afterwards by its certificate fingerprint
# (kept in %LOCALAPPDATA%\SolMind\lan_hosts.json; public addresses keep the normal checks); (2) when the saved address stops
# answering, the same network is searched once a minute for the server with THAT fingerprint and the new address is
# remembered; the key is never sent during the search; (3) resolve_base() tries the usual spellings of a typed address.
_LAN_LOCK = threading.Lock()
_FOLLOW_EVERY, _follow_at, _alive_at, _repin_until = 60.0, {}, {}, [0.0]

def _lan_path():
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    d = os.path.join(root, "SolMind"); os.makedirs(d, exist_ok=True)
    return os.path.join(d, "lan_hosts.json")

def _lan_load():
    try:
        with open(_lan_path(), encoding="utf-8") as f: d = json.load(f)
    except (OSError, ValueError): d = {}
    if not isinstance(d, dict): d = {}
    for k in ("pins", "moved", "alias", "spki"):
        if not isinstance(d.get(k), dict): d[k] = {}
    return d

def _lan_update(fn):
    with _LAN_LOCK:
        d = _lan_load(); fn(d)
        tmp = _lan_path() + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f: json.dump(d, f, indent=1)
            os.replace(tmp, _lan_path())
        except OSError: pass

def is_lan_host(host):
    h = (host or "").strip("[]").lower()
    if not h: return False
    try:
        ip = ipaddress.ip_address(h)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return h == "localhost" or h.endswith(".local") or "." not in h

def _origin(url):
    t = urllib.parse.urlsplit(url)
    return (t.hostname or ""), (t.port or (443 if t.scheme == "https" else 80)), t.scheme

def _with_host(url, host):
    t = urllib.parse.urlsplit(url)
    netloc = host + ((":%d" % t.port) if t.port else "")
    return urllib.parse.urlunsplit((t.scheme, netloc, t.path, t.query, t.fragment))

def _moved(url):
    """The address this server answers on now, when it was found on another one."""
    host, port, _ = _origin(url)
    new = _lan_load()["moved"].get("%s:%d" % (host, port))
    return _with_host(url, new) if new else url

def moved_base(base):
    return _moved(base) if base else base

def _pin_of(host, port):
    pin = _lan_load()["pins"].get("%s:%d" % (host, port))
    if pin: return pin
    ctx_file = pathlib.Path(__file__).with_name('iphone_localcoder.pem')         # the certificate copied by hand before s153
    if port == 11434 and ctx_file.exists() and _iphone_context("https://%s:%d" % (host, port)) is not None:
        try: return hashlib.sha256(ssl.PEM_cert_to_DER_cert(ctx_file.read_text())).hexdigest()
        except (OSError, ValueError): return None
    return None

# The phone app may show a "TLS public key pin" (sha256//<base64>): the SHA-256 of the certificate's public key. When he
# pastes it with the address, the first connection is checked against it instead of being trusted blindly.
_SPKI_RE = re.compile(r"sha256//([A-Za-z0-9+/]{43}=)")

def _tlv(b, i):
    """One DER element at i: (tag, value start, end)."""
    tag, n = b[i], b[i + 1]; i += 2
    if n & 0x80:
        k = n & 0x7F; n = int.from_bytes(b[i:i + k], "big"); i += k
    return tag, i, i + n

def spki_pin(der):
    """base64(SHA-256(SubjectPublicKeyInfo)) of a certificate, as the phone app prints it. None when it cannot be read."""
    try:
        _, s, _ = _tlv(der, 0)                      # Certificate
        _, i, _ = _tlv(der, s)                      # tbsCertificate
        tag, _, e = _tlv(der, i)
        if tag == 0xA0: i = e                       # version
        for _ in range(5): i = _tlv(der, i)[2]      # serial, signature, issuer, validity, subject
        return base64.b64encode(hashlib.sha256(der[i:_tlv(der, i)[2]]).digest()).decode("ascii")
    except (IndexError, ValueError):
        return None

def find_tls_pin(text):
    m = _SPKI_RE.search(text or "")
    return m.group(1) if m else ""

def set_tls_pin(address, pin):
    """Remember the app's pin for this address (typed with or without https://). An earlier certificate memory is dropped."""
    a = (address or "").strip()
    if not a or not pin: return
    host, port, _ = _origin(a if re.match(r"^https?://", a, re.I) else "https://" + a)
    key = "%s:%d" % (host, port)
    def note(d):
        d["spki"][key] = pin; d["pins"].pop(key, None)
    _lan_update(note)

def allow_repin(seconds=45):
    """The player pressed Apply/Test in the settings: a new certificate on a known home address is accepted for a moment."""
    _repin_until[0] = time.time() + seconds

def _loose_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    return ctx

def _open_pinned(req, timeout, host, port):
    key, pin, seen = "%s:%d" % (host, port), _pin_of(host, port), {}
    want = _lan_load()["spki"].get(key)
    repin = time.time() < _repin_until[0]
    class Conn(http.client.HTTPSConnection):
        def connect(self):
            super().connect()
            der = self.sock.getpeercert(True)
            seen["fp"] = hashlib.sha256(der).hexdigest()
            if want and spki_pin(der) != want:
                self.close(); raise ssl.SSLError("the server's TLS key is not the one the phone app shows (TLS pin)")
            if pin and seen["fp"] != pin and not repin:
                self.close(); raise ssl.SSLError("this address now shows a different certificate; press Test in Sol's settings to accept it")
    ctx = _loose_context()
    class Handler(urllib.request.HTTPSHandler):
        def https_open(self, r): return self.do_open(lambda h, **k: Conn(h, context=ctx, **k), r)
    resp = urllib.request.build_opener(Handler()).open(req, timeout=timeout)
    if seen.get("fp") and seen["fp"] != pin:
        _lan_update(lambda d: d["pins"].__setitem__(key, seen["fp"]))
    return resp

def _find_moved(host, port, pin, connect_timeout=0.4):
    """Search the same /24 for the server with this certificate fingerprint. No request and no key is sent."""
    try: ip = ipaddress.ip_address(host)
    except ValueError: return None
    if ip.version != 4 or not pin: return None
    def probe(addr):
        a = str(addr)
        if a == host: return None
        try:
            with socket.create_connection((a, port), connect_timeout) as s:
                s.settimeout(2.5)
                with _loose_context().wrap_socket(s) as tls:
                    if hashlib.sha256(tls.getpeercert(True)).hexdigest() == pin: return a
        except OSError:
            return None
        return None
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(64) as ex:
        for found in ex.map(probe, ipaddress.ip_network(host + "/24", strict=False).hosts()):
            if found: return found
    return None

def _follow(url):
    """The saved home address does not answer: look for the same server once a minute. Returns the new URL or None."""
    host, port, scheme = _origin(url)
    key = "%s:%d" % (host, port)
    if scheme != "https" or not is_lan_host(host) or time.time() - _follow_at.get(key, 0) < _FOLLOW_EVERY: return None
    _follow_at[key] = time.time()
    pin = _pin_of(host, port)
    new = _find_moved(host, port, pin)
    if not new: return None
    def note(d):
        d["pins"]["%s:%d" % (new, port)] = pin
        if d["spki"].get(key): d["spki"]["%s:%d" % (new, port)] = d["spki"][key]
        for old, cur in list(d["moved"].items()):                   # earlier addresses of the same server follow too
            if cur == host: d["moved"][old] = new
        d["moved"][key] = new
        d["moved"].pop("%s:%d" % (new, port), None)
    _lan_update(note)
    return _with_host(url, new)

def _reachable(host, port, wait=1.5):
    key = "%s:%d" % (host, port)
    if time.time() - _alive_at.get(key, 0) < 30: return True
    try:
        with socket.create_connection((host, port), wait): pass
    except OSError:
        return False
    _alive_at[key] = time.time(); return True

def _http(method, url, headers, body=None, timeout=20):
    if not str(url).lower().startswith(("http://", "https://")):   # s152: a pasted key or a bare host as the address is "unreachable", not a crash loop
        raise ProviderError("unreachable", "address must start with http:// or https://")
    url = _moved(url)
    host, port, scheme = _origin(url)
    lan_https = scheme == "https" and is_lan_host(host)
    if lan_https and not _reachable(host, port):                    # a dead home address: do not wait the whole timeout
        new = _follow(url)
        if not new: raise ProviderError("unreachable", "no answer from %s:%d" % (host, port))
        url = new
    try:
        return _http_once(method, url, headers, body, timeout, lan_https and _iphone_context(url) is None)
    except ProviderError as e:
        if e.code not in ("unreachable", "timeout") or not lan_https: raise
        new = _follow(url)
        if not new: raise
        return _http_once(method, new, headers, body, timeout, _iphone_context(new) is None)

def _http_once(method, url, headers, body, timeout, lan_tls):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    host, port, _ = _origin(url)
    try:
        opened = _open_pinned(req, timeout, host, port) if lan_tls else urllib.request.urlopen(req, timeout=timeout, context=_iphone_context(url))
        with opened as r:
            out = json.loads(r.read().decode("utf-8") or "{}")
        _alive_at["%s:%d" % (host, port)] = time.time()
        return out
    except urllib.error.HTTPError as e:
        code = {401: "invalid_key", 403: "forbidden", 404: "not_found", 429: "rate_limited", 402: "no_credit"}.get(e.code, "http_%d" % e.code)
        try: text = e.read(600).decode("utf-8", "replace")
        except Exception: text = ""
        if "FreeTierError" in text: code = "free_tier_app_only"          # OpenCode: free models only inside the OpenCode app
        elif "error code: 1010" in text: code = "blocked_by_firewall"     # Cloudflare refused the client
        raise ProviderError(code, ("HTTP %d " % e.code) + " ".join(text.split())[:300])
    except urllib.error.URLError as e:
        raise ProviderError("unreachable", str(getattr(e, "reason", e))[:120])
    except (TimeoutError, socket.timeout):
        raise ProviderError("timeout")
    except (ssl.SSLError, ConnectionError, http.client.HTTPException) as e:
        raise ProviderError("unreachable", str(e)[:120])
    except (ValueError, json.JSONDecodeError):
        raise ProviderError("bad_response")

# ---- a typed or pasted address
_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
_HOSTPORT_RE = re.compile(r"(?<![\w.])((?:\d{1,3}\.){3}\d{1,3}|localhost|[\w-]+\.local)(:\d{2,5})?(/[^\s\"'<>]*)?", re.I)
_LABELS = re.compile(r"(?i)^(api|key|apikey|api_key|api-key|token|url|address|base|server|host|bearer|authorization|and|the|model|tls|pin|public|openai|ollama|anthropic)$")

def split_address_and_key(text):
    """Pasted text may hold the address, the key, or both (in any order, with labels). Returns (key, address)."""
    s = _SPKI_RE.sub(" ", (text or "")).strip()                      # the TLS pin is neither the address nor the key
    m = _URL_RE.search(s) or _HOSTPORT_RE.search(s)
    if not m: return s, ""
    addr = m.group(0).rstrip(".,;)")
    rest = s[:m.start()] + " " + s[m.end():]
    words = [w.strip(".,;:()[]\"'") for w in re.split(r"[\s=]+", rest)]
    words = [w for w in words if len(w) >= 3 and not _LABELS.match(w)]
    return (max(words, key=len) if words else ""), addr

def normalize_base(raw):
    """The address as it is used: what resolve_base() found for this typed text, else http:// in front of a bare host."""
    b = (raw or "").strip().rstrip("/")
    if not b: return ""
    known = _lan_load()["alias"].get(b)
    if known: return known
    if not re.match(r"^https?://", b, re.I): b = "http://" + b
    return b

def resolve_base(raw, key, timeout=6):
    """Find the spelling of a typed address that answers /models: with https or http, with or without /v1.
    Returns (base, raw model list). Raises the most useful ProviderError when none answers."""
    typed = (raw or "").strip().rstrip("/")
    if not typed: raise ProviderError("no_base_url")
    roots = [typed] if re.match(r"^https?://", typed, re.I) else ["https://" + typed, "http://" + typed]
    cands = []
    for r in roots:
        if urllib.parse.urlsplit(r).path in ("", "/"): cands += [r + "/v1", r]
        else: cands += [r] + ([r + "/v1"] if not r.endswith("/v1") else [])
    last, rank = ProviderError("unreachable"), {"invalid_key": 3, "forbidden": 3, "timeout": 1, "unreachable": 0}
    for c in cands:
        try:
            data = _http("GET", c + "/models", _headers("custom", key), timeout=timeout)
        except ProviderError as e:
            if rank.get(e.code, 2) >= rank.get(last.code, 2): last = e
            if e.code in ("invalid_key", "forbidden"): break            # the server answered: the address is right, the key is not
            continue
        models = data.get("data", data.get("models", None)) if isinstance(data, dict) else None
        if not isinstance(models, list): last = ProviderError("bad_response"); continue
        if c != typed: _lan_update(lambda d: d["alias"].__setitem__(typed, c))
        return c, models
    raise last

def base_url(pid, custom_base=""):
    b = normalize_base(custom_base) if pid in ("custom", "ollama") and custom_base.strip() else PROVIDERS[pid]["base"]
    return b.rstrip("/")

def candidates(key):
    """Providers to try for a key, most likely first."""
    k = (key or "").strip()
    for pid in ORDER:
        if any(k.startswith(px) for px in PROVIDERS[pid]["prefixes"]):
            return [pid]
    return list(GENERIC_SK) if k.startswith("sk-") else list(GENERIC_OTHER)

# models that are not chat models (speech, TTS, guards, embeddings)
NON_CHAT = ("whisper", "orpheus", "tts", "guard", "safeguard", "embed", "moderation", "transcribe", "playai", "rerank", "dall-e", "image")
# models that think before answering: give them room and keep the thinking short
REASONING = ("gpt-oss", "deepseek-r1", "-reasoner", "qwq", "o1-", "o3-", "o4-")

def is_chat_model(mid):
    low = mid.lower()
    return not any(w in low for w in NON_CHAT)

def is_reasoning_model(mid):
    low = mid.lower()
    return any(w in low for w in REASONING)

def _label(pid, m):
    """Return (badge, data_warning, supported) for one model entry."""
    mid = m.get("id", "")
    if not is_chat_model(mid):
        return "nochat", False, False
    tier = PROVIDERS[pid]["tier"]
    if pid == "openrouter":
        pr = m.get("pricing") or {}
        free = str(pr.get("prompt", "1")) in ("0", "0.0") and str(pr.get("completion", "1")) in ("0", "0.0")
        return ("free" if free else "paid"), free, True
    if pid == "opencode":
        free = mid.endswith("-free") or mid in OPENCODE_FREE
        # Zen GPT models use /responses, Claude /messages, Gemini its own route: chat/completions only for now
        supported = not (mid.startswith("gpt-") or mid.startswith("claude-") or mid.startswith("gemini-"))
        return ("free" if free else "paid"), free, supported
    if tier == "local":
        return "local", False, True
    return {"paid": "paid", "tier": "tier"}.get(tier, "unknown"), False, True

def list_models(pid, key, custom_base="", timeout=20):
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
    if PROVIDERS[pid]["kind"] == "ollama":
        data = _http("GET", b + "/api/tags", _headers(pid, ""), timeout=timeout)
        raw = [{"id": m.get("name", "")} for m in data.get("models", [])]
    else:
        url = b + "/models"
        if pid == "anthropic":
            url += "?limit=100"
        data = _http("GET", url, _headers(pid, key), timeout=timeout)
        raw = data.get("data", data.get("models", []))
        if pid == "gemini":  # ids come as "models/gemini-..." on the compat route
            raw = [dict(m, id=str(m.get("id", m.get("name", ""))).replace("models/", "")) for m in raw]
    out = []
    for m in raw:
        mid = str(m.get("id", "")).strip()
        if not mid:
            continue
        badge, warn, supported = _label(pid, m)
        out.append({"id": mid, "badge": badge, "warn": warn, "supported": supported})
    # free first, then supported, then name
    out.sort(key=lambda x: (x["badge"] != "free", not x["supported"], x["id"]))
    return out

def detect(key, preferred="auto", custom_base="", timeout=15):
    """Find which provider accepts the key. Returns (pid, models). Raises ProviderError with the last failure."""
    order = [preferred] if preferred and preferred != "auto" else candidates(key)
    last = ProviderError("invalid_key")
    tried = []
    for pid in order:
        try:
            return pid, list_models(pid, key, custom_base, timeout)
        except ProviderError as e:
            tried.append("%s %s" % (PROVIDERS[pid]["name"], e.detail or e.code))
            last = e
            if e.code not in ("invalid_key", "forbidden", "not_found", "unreachable"):
                break
    last.detail = "; ".join(tried)
    raise last

def chat(pid, key, model, messages, system="", custom_base="", max_tokens=400, timeout=60):
    """messages: [{"role": "user"|"assistant", "content": str}] -> reply text."""
    b = base_url(pid, custom_base)
    kind = PROVIDERS[pid]["kind"]
    if kind == "anthropic":
        body = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system:
            body["system"] = system
        data = _http("POST", b + "/messages", _headers(pid, key), body, timeout)
        return "".join(c.get("text", "") for c in data.get("content", []) if c.get("type") == "text").strip()
    if kind == "ollama":
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        data = _http("POST", b + "/api/chat", _headers(pid, ""), {"model": model, "messages": msgs, "stream": False}, timeout)
        return (data.get("message") or {}).get("content", "").strip()
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    body = {"model": model, "messages": msgs, "max_tokens": max_tokens}
    if is_reasoning_model(model):
        # proven 2026-10-23 on Groq gpt-oss-120b: with max_tokens=120 the thinking used the whole budget (finish=length,
        # empty reply); reasoning_effort=low + 1024 answered in 35 tokens.
        body["max_tokens"] = max(max_tokens, 1024)
        if pid in ("groq", "openrouter", "openai", "opencode", "custom"):
            body["reasoning_effort"] = "low"
    data = _http("POST", b + "/chat/completions", _headers(pid, key), body, timeout)
    ch = data.get("choices") or [{}]
    return ((ch[0].get("message") or {}).get("content") or "").strip()

def chat_with_tools(pid, key, model, messages, tools, run_tool, system="", custom_base="", max_tokens=600, timeout=60, rounds=4):
    """OpenAI-compatible tool calling: the model may call tools (run_tool(name, args) -> dict) before answering.
    Anthropic / Ollama fall back to plain chat (no tools)."""
    if PROVIDERS[pid]["kind"] != "openai":
        return chat(pid, key, model, messages, system=system, custom_base=custom_base, max_tokens=max_tokens, timeout=timeout)
    b = base_url(pid, custom_base)
    msgs = ([{"role": "system", "content": system}] if system else []) + list(messages)
    for _ in range(rounds):
        body = {"model": model, "messages": msgs, "max_tokens": max_tokens, "tools": tools, "tool_choice": "auto"}
        if is_reasoning_model(model):
            body["max_tokens"] = max(max_tokens, 1024)
            if pid in ("groq", "openrouter", "openai", "opencode", "custom"): body["reasoning_effort"] = "low"
        data = _http("POST", b + "/chat/completions", _headers(pid, key), body, timeout)
        msg = ((data.get("choices") or [{}])[0].get("message") or {})
        calls = msg.get("tool_calls") or []
        if not calls:
            return (msg.get("content") or "").strip()
        msgs.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for c in calls:
            fn = c.get("function") or {}
            try: args = json.loads(fn.get("arguments") or "{}")
            except ValueError: args = {}
            try: result = run_tool(fn.get("name"), args)
            except Exception as e: result = {"error": str(e)[:200]}
            msgs.append({"role": "tool", "tool_call_id": c.get("id"), "content": json.dumps(result, ensure_ascii=False)})
    return ""

def test(pid, key, model, custom_base=""):
    t0 = time.time()
    reply = chat(pid, key, model, [{"role": "user", "content": "Reply with the single word: ready"}],
                 custom_base=custom_base, max_tokens=64, timeout=30)
    return reply, round(time.time() - t0, 2)

import re as _re
_KEY_RE = _re.compile(r"^[A-Za-z0-9_\-\.:+/=]{20,300}$")
_KEY_RE_OWN = _re.compile(r"^[A-Za-z0-9_\-\.:+/=@!#$%&*~^]{3,300}$")
def looks_like_key(text, pid=""):
    """Shape check done BEFORE any network call, so random clipboard text is never sent anywhere.
    For the player's own server (custom) a short key is fine: phone apps hand out short ones."""
    k = (text or "").strip()
    if pid == "custom": return bool(_KEY_RE_OWN.match(k)) and not k.lower().startswith(("http://", "https://"))
    return bool(_KEY_RE.match(k))

def key_hint(key):
    k = (key or "").strip()
    if len(k) < 10:
        return "****"
    head = k[:6] if not k.startswith("sk-or-v1-") else k[:9]
    return head + "****" + k[-4:]
