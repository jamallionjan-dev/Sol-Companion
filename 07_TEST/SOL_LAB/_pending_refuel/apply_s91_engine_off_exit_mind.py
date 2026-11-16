"""s91 Mind side (Jamal 2026-11-10: every time she gets out of the car she turns the engine off, unless he asked her directly to
leave it running: "سول نزلي من السيارة وخلي المحرك شغال"). Pairs with apply_s91_engine_off_exit_lua.py (switch exit_engine_off).

Model first, no keyword override: the model maps the explicit phrase to exit_car with option keep_engine (one variant of exit_car,
taught by an example); the Mind sends the game exit_vehicle with option keep_engine; the game keeps the engine running for that
exit only. A plain "انزلي" is exit_car as before (and the game turns her engine off).
  model_router.py  s91 block: the example "نزلي من السيارة وخلي المحرك شغال / خلي الموتور شغال -> exit_car keep_engine".
                   s90's example bank (a module list/dict whose name holds BANK) when the copy has one: added there, in the
                   bank's own entry shape. Otherwise one line on the card, within CARD_BUDGET (two intro lines say the same in
                   fewer words to make room). parse() notes KEEP_ENGINE_S91 when the reply is exit_car keep_engine.
  chat_service.py  s91 block: run_action("exit_vehicle") inside that route carries option keep_engine; the route clears it.
The block stays the last one in each file: run again after a later stage appended its own, it moves itself to the end.
Needs s85 (several actions, the card budget). Game closed only. In place, idempotent.
usage: apply_s91_engine_off_exit_mind.py <sol_mind dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
BEGIN = "# ---------------------------------------------------------------- s91 engine off on exit, unless he says keep it running"
END = "# ---------------------------------------------------------------- s91 end"

MR_BLOCK = BEGIN + r'''
# exit_car keep_engine: his explicit "get out and leave the engine running". One variant of exit_car, taught by an example.
KEEP_ENGINE_SAID_S91 = ("نزلي من السيارة وخلي المحرك شغال", "خلي الموتور شغال")
KEEP_ENGINE_ANSWER_S91 = '{"action":"exit_car","args":{"option":"keep_engine"}}'
KEEP_ENGINE_LINE_S91 = " / ".join(KEEP_ENGINE_SAID_S91) + " -> " + KEEP_ENGINE_ANSWER_S91
KEEP_ENGINE_S91 = False                                                      # set by parse(), read and cleared by the chat
_TRIM_S91 = (('الجواب سطر JSON واحد فقط، بدون أي كلام تاني:' + chr(10) + '{"action":"معرف من القائمة","speech":""}' + chr(10) + chr(10)
              + '- action: معرف القائمة حرفيًا.' + chr(10),
              'الجواب سطر JSON واحد بس:' + chr(10) + '{"action":"معرف من القائمة حرفيًا","speech":""}' + chr(10) + chr(10)),
             ('- option: أضيفيها بس للأفعال المكتوب جنبها option.', '- option: بس للأفعال اللي جنبها option.'))


def _bank_add_s91():
    """s90's example bank, when this Mind has one: the keep_engine example goes there in the bank's own shape. The bank's name, or None."""
    names = [k for k, v in list(globals().items()) if "BANK" in k and not k.endswith("_S91") and isinstance(v, (list, dict))]
    if not names: return None
    name = names[-1]
    bank = globals()[name]
    answer = json.loads(KEEP_ENGINE_ANSWER_S91)
    if isinstance(bank, dict):
        sample = next(iter(bank.values()), KEEP_ENGINE_ANSWER_S91)
        for said in KEEP_ENGINE_SAID_S91: bank.setdefault(said, answer if isinstance(sample, dict) else KEEP_ENGINE_ANSWER_S91)
        return name
    sample = bank[0] if bank else KEEP_ENGINE_LINE_S91
    if isinstance(sample, str):
        if KEEP_ENGINE_LINE_S91 not in bank: bank.append(KEEP_ENGINE_LINE_S91)
        return name
    if isinstance(sample, (tuple, list)) and len(sample) == 2 and isinstance(sample[0], str):
        for said in KEEP_ENGINE_SAID_S91:
            if not any(e[0] == said for e in bank):
                e = (said, answer if isinstance(sample[1], dict) else KEEP_ENGINE_ANSWER_S91)
                bank.append(e if isinstance(sample, tuple) else list(e))
        return name
    return None


BANK_S91 = _bank_add_s91()
if BANK_S91 is None:
    for _old, _new in _TRIM_S91:
        if _old in CARD: CARD = CARD.replace(_old, _new)
_sheet_s91_base = sheet


def sheet(actions, memory, *more, **kw):
    """The card as before; with no example bank, the keep_engine example as one line after the others."""
    text = _sheet_s91_base(actions, memory, *more, **kw)
    if BANK_S91 is not None or KEEP_ENGINE_LINE_S91 in text: return text
    tail = chr(10) + chr(10) + "ذاكرتك الآن:"
    return text.replace(tail, chr(10) + KEEP_ENGINE_LINE_S91 + tail, 1) if tail in text else text + chr(10) + KEEP_ENGINE_LINE_S91


_parse_s91_base = parse


def parse(raw):
    """As before; KEEP_ENGINE_S91 says whether this reply is exit_car with option keep_engine."""
    global KEEP_ENGINE_S91
    p = _parse_s91_base(raw)
    KEEP_ENGINE_S91 = bool(p and p.get("action") == "exit_car" and str((p.get("args") or {}).get("option") or "").strip().lower() == "keep_engine")
    return p
''' + END + NL

CS_BLOCK = BEGIN + r'''
# exit_car keep_engine (the model's answer, model_router.KEEP_ENGINE_S91): the exit order the Mind sends in that route carries
# option keep_engine; the game (SolExitEngine.lua, switch exit_engine_off) leaves the engine running for that exit only.
_run_action_s91_base = run_action


EXIT_VERB_S91 = "exit_vehicle"                                                # the game's exit order (SolOrders.leaveCar)


def run_action(lua_dir, action, option=None, wait=3.0):
    if option is None and action == EXIT_VERB_S91 and getattr(MR, "KEEP_ENGINE_S91", False):
        MR.KEEP_ENGINE_S91 = False
        option = "keep_engine"
    return _run_action_s91_base(lua_dir, action, option, wait)


_route_by_model_s91_base = Chat._route_by_model


def _route_by_model_s91(self, history, c, key, snap, mem):
    MR.KEEP_ENGINE_S91 = False
    try: return _route_by_model_s91_base(self, history, c, key, snap, mem)
    finally: MR.KEEP_ENGINE_S91 = False


Chat._route_by_model = _route_by_model_s91
''' + END + NL


def place(path, block, need):
    raw = open(path, "rb").read()
    t = raw.decode("utf-8")
    nl = CRLF if CRLF in t else NL
    blk = block.replace(NL, nl)
    if BEGIN in t:
        a = t.index(BEGIN)
        b = t.index(END, a) + len(END)
        while b < len(t) and t[b] in "\r\n": b += 1
        old = t[a:b]
        rest = (t[:a] + t[b:]).rstrip("\r\n") + nl
        if not rest[a:].strip() and old.rstrip("\r\n") == blk.rstrip("\r\n"): return "kept"
        new = rest + nl + blk
        verdict = "moved to the end" if rest[a:].strip() else "updated"
    else:
        assert need in t, "%s: s85 is not installed (%s missing)" % (os.path.basename(path), need)
        new = t.rstrip("\r\n") + nl + nl + blk
        verdict = "edited"
    open(path, "wb").write(new.encode("utf-8"))
    return verdict


def mind(d):
    mr, cs = os.path.join(d, "model_router.py"), os.path.join(d, "chat_service.py")
    assert os.path.isfile(mr) and os.path.isfile(cs), "not a sol_mind dir: " + d
    print("model_router", place(mr, MR_BLOCK, "MAX_STEPS_S85"))
    print("chat_service", place(cs, CS_BLOCK, "_route_by_model_s85"))


if __name__ == "__main__":
    mind(sys.argv[1])
    print("s91_engine_off_exit_mind applied")
