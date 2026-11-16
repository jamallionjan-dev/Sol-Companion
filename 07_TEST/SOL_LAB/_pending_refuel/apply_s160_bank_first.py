"""s160 bank_first (Mind switch): words that ARE one of the example bank's phrases are not sent to the model.
usage: apply_s160_bank_first.py <sol_mind dir> [switch file ...]

Jamal's play 2026-11-16 (sol_mind.log, the phone model, full s155 card):
  "قعدي ريحي شوي"            -> sol_take_wheel   (the bank's own phrase for sol_rest)
  "سول عطيني الدركسيون"      -> sol_horn         (13:26; the same words gave sol_let_player_drive at 12:32)
The small model is not steady on phrases it has an exact example for. When his words, her name dropped, are an example
(similarity >= EXACT_MIN_S160) the bank's answer is used at once: the same checks and receipts as a model answer, no
5 second wait, the same result every time. Plain-talk examples (action none) still go to the model: she has to speak.
Needs s157 (offline_answer_s157 and the _offline_raw_s157 slot). "kept" when already applied."""
import os, re, sys
MIND = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)


def load(name):
    p = os.path.join(MIND, name)
    t = open(p, encoding="utf-8", newline="").read()
    return p, t, (CRLF if CRLF in t else NL)


p, t, nl = load("model_router.py")
if "offline_answer_s157" not in t: raise RuntimeError("s157 is not applied to this Mind")
if "exact_answer_s160" in t:
    print("kept model_router.py")
else:
    block = '''

# ---------------------------------------------------------------- s160 bank_first
EXACT_MIN_S160 = 0.97               # his words are the example itself (her name and small spelling marks aside)


def exact_answer_s160(said, actions):
    """The bank's answer when his words are one of its examples; None otherwise (the model decides)."""
    global OFFLINE_MIN_S157
    keep = OFFLINE_MIN_S157
    OFFLINE_MIN_S157 = EXACT_MIN_S160
    try: return offline_answer_s157(said, actions)
    finally: OFFLINE_MIN_S157 = keep
# ---------------------------------------------------------------- s160 end
'''.replace(NL, nl)
    open(p, "w", encoding="utf-8", newline="").write(t.rstrip(chr(13) + NL) + nl + block)
    print("edited model_router.py")

p, t, nl = load("chat_service.py")
if "exact_answer_s160" in t:
    print("kept chat_service.py")
else:
    old = '        raw = getattr(self, "_offline_raw_s157", None); self._offline_raw_s157 = None'
    if t.count(old) != 1: raise RuntimeError(("chat_service.py", "expected the s157 line once", t.count(old)))
    k = t.index(old); e = t.index(nl, k)
    add = (nl + '        if raw is None and fix_on(self.dir, "bank_first") and hasattr(MR, "exact_answer_s160"):       # s160' + nl
           + '            raw = MR.exact_answer_s160(text, acts)' + nl
           + '            if raw: self.log("chat: his words are a known order, the model is not asked: %s" % raw[:80])')
    t = t[:e] + add + t[e:]
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("edited chat_service.py")

for sw in sys.argv[2:]:
    if not os.path.isfile(sw): print("no switch file " + sw); continue
    s = open(sw, encoding="utf-8", newline="").read()
    if re.search(r"(?m)^bank_first=", s): print("kept bank_first in " + os.path.basename(sw)); continue
    with open(sw, "a", encoding="utf-8", newline="") as f:
        f.write(("" if s.endswith((NL, CRLF)) else CRLF) + "bank_first=on" + CRLF)
    print("enabled bank_first in " + os.path.basename(sw))
print("s160 bank_first applied")
