"""s157 phone_patience (Mind switch): the phone model gets the time the full card needs, and a known order still runs when
the model does not answer.
usage: apply_s157_phone_patience.py <sol_mind dir> [SolFixes_LAB.txt]

Jamal's run 2026-11-15 (sol_mind.log): with the s155 card (6650 chars, was 4600) the phone answered in about 5 s, the chat
call waited 4 s: 28 of 31 lines ended as ProviderError('timeout') and fell to the word lists, which do not know the newer
actions ("شربي مي", "غسلي حالك", "افتحي الباب", "عطيني الدركسيون", "فيكي تجيبي هليكوبتر"). Before s155: 0-2 timeouts a day.
- chat_service.py: the phone call waits PHONE_WAIT_S157 seconds (switch on), 4 as before (switch off)
- chat_service.py: model down and the word lists found nothing -> his words against the example bank (near-exact only);
  a match goes through the same checks and receipts as a model answer
- chat_service.py: "فيكي تجيبي هليكوبتر" without her name is the same explicit order
- model_router.py: offline_answer_s157
"kept" when already applied."""
import os, re, sys
MIND = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)


def load(name):
    p = os.path.join(MIND, name)
    t = open(p, encoding="utf-8", newline="").read()
    return p, t, (CRLF if CRLF in t else NL)


def one(text, old, new, what):
    if text.count(old) != 1: raise RuntimeError((what, "expected once", text.count(old)))
    return text.replace(old, new)


# ---------------------------------------------------------------- model_router.py
p, t, nl = load("model_router.py")
if "offline_answer_s157" in t:
    print("kept model_router.py")
else:
    block = '''

# ---------------------------------------------------------------- s157 phone_patience
# When the model does not answer: his words against the example bank. Near-exact only (OFFLINE_MIN_S157): a guess here
# would run an order he did not give. Short forms he typed on 2026-11-15 that the bank does not hold are listed beside it.
OFFLINE_MIN_S157 = 0.85
OFFLINE_SAID_S157 = (
    ("شربي", '{"action":"sol_drink"}'), ("اشربي", '{"action":"sol_drink"}'), ("شربي شي", '{"action":"sol_drink"}'),
    ("غسلي", '{"action":"sol_wash"}'), ("تغسلي", '{"action":"sol_wash"}'),
    ("عطيني الدركسيون", '{"action":"sol_let_player_drive"}'), ("عطيني سوق", '{"action":"sol_let_player_drive"}'),
    ("خليني سوق", '{"action":"sol_let_player_drive"}'), ("خليني انا سوق", '{"action":"sol_let_player_drive"}'),
    ("زمري", '{"action":"sol_horn","args":{"option":"once"}}'), ("زمري بالسيارة", '{"action":"sol_horn","args":{"option":"once"}}'),
    ("طفي المحرك ونزلي", '{"action":"exit_car"}'), ("طفي المحرك وانزلي", '{"action":"exit_car"}'),
)
_NAME_S157 = re.compile("^\\\\s*(?:يا\\\\s+)?سول[\\\\s،,]+")


def offline_answer_s157(said, actions):
    """The bank's answer for words that are (nearly) one of its examples, as the JSON text a model would have sent. None otherwise."""
    said = _NAME_S157.sub("", str(said or "")).strip()
    if not said: return None
    possible = {a.get("id") for a in actions or [] if a.get("enabled") is not False} | set(COMMANDS)
    q = _feats_s90(said)
    pairs = list(OFFLINE_SAID_S157)
    for line in EXAMPLE_BANK_S90:
        k = line.find(" -> {")
        if k > 0: pairs.extend((ph.strip(), line[k + 4:]) for ph in line[:k].split(" / "))
    best, answer = 0.0, None
    for phrase, ans in pairs:
        s = similarity_s90(q, _feats_s90(_NAME_S157.sub("", phrase)))
        if s > best: best, answer = s, ans
    if answer is None or best < OFFLINE_MIN_S157: return None
    ids = answer_actions_s90(answer)
    if not ids or any(i in ("none", "unknown") or i not in possible for i in ids): return None
    return answer
# ---------------------------------------------------------------- s157 end
'''.replace(NL, nl)
    open(p, "w", encoding="utf-8", newline="").write(t.rstrip(chr(13) + NL) + nl + block)
    print("edited model_router.py")

# ---------------------------------------------------------------- chat_service.py
p, t, nl = load("chat_service.py")
if "PHONE_WAIT_S157" in t:
    print("kept chat_service.py")
else:
    t = one(t, 'timeout=(4 if c.get("provider") == "custom" else 15))',
            'timeout=((PHONE_WAIT_S157 if fix_on(self.dir, "phone_patience") else 4) if c.get("provider") == "custom" else 15))', "phone timeout")
    old = '        try:' + nl + '            raw = P.chat(c["provider"], key, c["model"], MR.message(text, c["model"])'
    t = one(t, old, '        raw = getattr(self, "_offline_raw_s157", None); self._offline_raw_s157 = None      # s157: the bank\'s answer, the model is down' + nl
            + '        try:' + nl + '            if raw is None: raw = P.chat(c["provider"], key, c["model"], MR.message(text, c["model"])', "chat call")
    old = '        if ("سول" in summon_words and "فيكي" in summon_words and "تجيبي" in summon_words'
    t = one(t, old, '        if (("سول" in summon_words or fix_on(self.dir, "phone_patience")) and "فيكي" in summon_words and "تجيبي" in summon_words', "helicopter words")
    old = '            self.log("chat: model down, word lists found no order")' + nl
    new = ('            raw = MR.offline_answer_s157(history[-1]["text"], load_actions(self.dir)) if fix_on(self.dir, "phone_patience") and hasattr(MR, "offline_answer_s157") else None' + nl
           + '            if raw:                                                               # s157: his words are one of the known orders' + nl
           + '                self.log("chat: model down, his words match a known order: %s" % raw[:80])' + nl
           + '                self._offline_raw_s157 = raw' + nl
           + '                routed = self._route_by_model(history, c, key, snap, mem)' + nl
           + '                if routed is not None: return routed' + nl
           + old)
    t = one(t, old, new, "model down")
    old = 'def fix_on(lua_dir, name):' + nl
    t = one(t, old, 'PHONE_WAIT_S157 = 12       # seconds for the phone model; it answered the full card in about 5 (sol_mind.log 2026-11-15)' + nl + nl + old, "constant")
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("edited chat_service.py")

if len(sys.argv) > 2:
    sw = sys.argv[2]
    s = open(sw, encoding="utf-8", newline="").read()
    if not re.search(r"(?m)^phone_patience=", s):
        with open(sw, "a", encoding="utf-8", newline="") as f:
            f.write(("" if s.endswith((NL, CRLF)) else CRLF) + "phone_patience=on" + CRLF)
        print("enabled phone_patience in the switch file")
    else:
        print("kept phone_patience switch")
print("s157 phone_patience applied")
