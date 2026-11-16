"""Chat history per world, emptied when she dies. usage: apply_s47_mind.py <path to chat_service.py>"""
import sys
P = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)
EDITS = [
("""        try:
            with open(_hist_path(), encoding="utf-8") as f: self.hist = json.load(f)[-KEEP:]
        except (OSError, ValueError): self.hist = []
""", """        self.hist, self._hist_file = [], None                                   # filled from this world's own file once the world is known
"""),
("""    def _save(self):
        try:
            with open(_hist_path(), "w", encoding="utf-8") as f: json.dump(self.hist[-KEEP:], f, ensure_ascii=False)
        except OSError: pass
""", """    def _bind_history(self, mem):
        \"\"\"Each world has its own conversation, kept with the rest of that world's memory.\"\"\"
        if mem is None: return
        path = os.path.join(mem.dir, "chat_history.json")
        if path == self._hist_file: return
        try:
            with open(path, encoding="utf-8") as f: loaded = json.load(f)[-KEEP:]
        except (OSError, ValueError): loaded = []
        self.hist, self._hist_file = loaded, path

    def _save(self):
        if not self._hist_file: return
        try:
            with open(self._hist_file, "w", encoding="utf-8") as f: json.dump(self.hist[-KEEP:], f, ensure_ascii=False)
        except OSError: pass
"""),
("""        mem = W.Memory(snap["world"]) if snap and snap.get("world") and snap["world"].get("name") else None
        return snap, mem
""", """        mem = W.Memory(snap["world"]) if snap and snap.get("world") and snap["world"].get("name") else None
        self._bind_history(mem)
        return snap, mem
"""),
("""        self._last_at = None
        mem.save()
        self.log("life: death %d, her learned places forgotten" % deaths)
""", """        self._last_at = None
        mem.save()
        self.hist = []
        self._save()
        self.log("life: death %d, her learned places forgotten" % deaths)
"""),
("""def _hist_path():
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    d = os.path.join(root, "SolMind"); os.makedirs(d, exist_ok=True)
    return os.path.join(d, "chat_history.json")

""", ""),
]
t = open(P, encoding="utf-8", newline="").read()
nl = CRLF if CRLF in t else NL
for a, b in EDITS:
    a2, b2 = a.replace(NL, nl), b.replace(NL, nl)
    assert t.count(a2) == 1, a[:60]
    t = t.replace(a2, b2)
assert "_hist_path" not in t
compile(t, P, "exec")
open(P, "w", encoding="utf-8", newline="").write(t)
print("applied")
