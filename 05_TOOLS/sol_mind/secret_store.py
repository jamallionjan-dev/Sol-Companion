"""Store API keys encrypted with Windows DPAPI (bound to the current Windows user).
Off Windows (tests only) it falls back to an obfuscated file and says so."""
import base64, json, os, sys, ctypes

def _path():
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    d = os.path.join(root, "SolMind"); os.makedirs(d, exist_ok=True)
    return os.path.join(d, "secrets.json")

if sys.platform == "win32":
    from ctypes import wintypes
    class _BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]
    def _blob(b):
        buf = ctypes.create_string_buffer(b, len(b))
        return _BLOB(len(b), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf
    def _protect(data: bytes) -> bytes:
        inp, _keep = _blob(data); out = _BLOB()
        if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(inp), "SolMind", None, None, None, 0x1, ctypes.byref(out)):
            raise OSError("CryptProtectData failed")
        try: return ctypes.string_at(out.pbData, out.cbData)
        finally: ctypes.windll.kernel32.LocalFree(out.pbData)
    def _unprotect(data: bytes) -> bytes:
        inp, _keep = _blob(data); out = _BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(inp), None, None, None, None, 0x1, ctypes.byref(out)):
            raise OSError("CryptUnprotectData failed")
        try: return ctypes.string_at(out.pbData, out.cbData)
        finally: ctypes.windll.kernel32.LocalFree(out.pbData)
    PROTECTED = True
else:
    _protect = lambda b: b[::-1]
    _unprotect = lambda b: b[::-1]
    PROTECTED = False

def _load():
    try:
        with open(_path(), encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError): return {}

def put(pid, key):
    d = _load(); d[pid] = base64.b64encode(_protect(key.encode("utf-8"))).decode("ascii")
    with open(_path(), "w", encoding="utf-8") as f: json.dump(d, f)

def get(pid):
    v = _load().get(pid)
    if not v: return None
    try: return _unprotect(base64.b64decode(v)).decode("utf-8")
    except Exception: return None

def forget(pid):
    d = _load(); d.pop(pid, None)
    with open(_path(), "w", encoding="utf-8") as f: json.dump(d, f)
