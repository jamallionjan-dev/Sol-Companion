"""s154 card_extra_actions (Mind switch, read through sol_fixes): the game actions the card does not list reach the model
only for the message that asks for them.
The one-tier card is full (CARD_BUDGET) and card_check warns that ~37 game actions the Mind can run are never shown to the
model (eat, drink, wash, cook, read, reload, give, open door, bandage ...). The two-tier card (s90) that lists everything
regressed on the phone model and stays off. Here the card is NOT changed: when his line is close (similarity_s90 >=
EXTRA_MIN_S154) to an s90 bank example of an action that is not on the card, that example (at most EXTRA_MAX_S154) is added
under the examples for this one message. Card duplicates (exit_vehicle, board_vehicle, set_combat_doctrine) and helper
actions are never added; an action the game reports as not possible now (enabled = false) is not added.
usage: apply_s154_card_extra_actions.py <sol_mind dir> [SolFixes_LAB.txt]. Exact old->new; "kept" when already applied."""
import os, re, sys
MIND = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)

BLOCK = '''

# ---------------------------------------------------------------- s154 card_extra_actions
# Game actions that are not on the one-tier card, shown to the model only with the message that asks for one of them.
EXTRA_MIN_S154 = 0.6                # eval 2026-11-15 (s82_route_eval.json): none of the 76 lines for card actions reaches it
EXTRA_MAX_S154 = 2
EXTRA_SKIP_S154 = {"sol_fuel"}      # the pump helper: used by the refuel goals, not called alone


def extra_action_lines(card, said, actions):
    """Bank examples for this line whose action the card does not list, best first. [] when nothing is close enough."""
    if not said: return []
    visible = set(re.findall(r"(?m)^([a-z_0-9]+):", card)) | {"none", "unknown"}
    possible = {a.get("id") for a in actions or [] if a.get("enabled") is not False}
    skip = set(CARD_DUPLICATES) | EXTRA_SKIP_S154
    q = _feats_s90(said)
    best = {}
    for line in EXAMPLE_BANK_S90:
        k = line.find(" -> {")
        if k <= 0: continue
        answer = line[k + 4:]
        ids = answer_actions_s90(answer)
        new = [i for i in ids if i not in visible]
        if not new or any(i in skip or i not in possible for i in new): continue
        for phrase in line[:k].split(" / "):
            s = similarity_s90(q, _feats_s90(phrase))
            if s >= EXTRA_MIN_S154 and s > best.get(answer, (0.0, ""))[0]: best[answer] = (s, phrase.strip())
    ranked = sorted(best.items(), key=lambda kv: -kv[1][0])[:EXTRA_MAX_S154]
    return ["%s -> %s" % (phrase, answer) for answer, (_, phrase) in ranked]


def add_extra_actions(card, said, actions):
    """The card as it is, plus this message's examples of actions it does not list (before her memory)."""
    lines = extra_action_lines(card, said, actions)
    if not lines: return card
    n = chr(10)
    tail = n + n + "\\u0630\\u0627\\u0643\\u0631\\u062a\\u0643 \\u0627\\u0644\\u0622\\u0646:"
    body, sep, rest = card.partition(tail)
    return body + n + n.join(lines) + sep + rest
# ---------------------------------------------------------------- s154 end
'''


def patch(name, fn):
    path = os.path.join(MIND, name)
    text = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in text else NL
    new = fn(text, nl)
    if new == text: print("kept " + name); return
    open(path, "w", encoding="utf-8", newline="").write(new); print("edited " + name)


def router(text, nl):
    if "def add_extra_actions(" in text: return text
    return text.rstrip(CRLF) + nl + BLOCK.replace(NL, nl)


def chat(text, nl):
    new = '''    text = _session_sheet_pre_s90(self, snap, mem, acts)
    if not getattr(MR, "CARD_TIERS", False):
        # s154: the card unchanged; an action it does not list is shown with the line that asks for it
        if _SAID_S90 and hasattr(MR, "add_extra_actions") and fix_on(self.dir, "card_extra_actions"):
            card = MR.add_extra_actions(text, _SAID_S90[-1], acts)
            if card != text: self.log("chat: card +%d chars (an action for this line)" % (len(card) - len(text)))
            return card
        return text
    if not _SAID_S90: return text
'''.replace(NL, nl)
    if new in text: return text
    old = '''    text = _session_sheet_pre_s90(self, snap, mem, acts)
    if not getattr(MR, "CARD_TIERS", False) or not _SAID_S90: return text
'''.replace(NL, nl)
    if text.count(old) != 1: raise RuntimeError(("chat_service.py", "expected one exact source block", text.count(old)))
    return text.replace(old, new)


patch("model_router.py", router)
patch("chat_service.py", chat)
if len(sys.argv) > 2:
    sw = sys.argv[2]
    t = open(sw, encoding="utf-8", newline="").read()
    if not re.search(r"(?m)^card_extra_actions=", t):
        with open(sw, "a", encoding="utf-8", newline="") as f:
            f.write(("" if t.endswith((NL, CRLF)) else CRLF) + "card_extra_actions=on" + CRLF)
        print("enabled card_extra_actions in the switch file")
    else:
        print("kept card_extra_actions switch")
print("s154 card extra actions applied")
