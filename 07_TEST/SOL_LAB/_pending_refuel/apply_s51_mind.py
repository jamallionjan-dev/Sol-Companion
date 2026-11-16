"""Lights, engine and horn on the entry card, and the refuel actions need a word about fuel.
usage: apply_s51_mind.py <sol_mind dir>"""
import os, sys
M = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)
EDITS = {}
def E(f, a, b): EDITS.setdefault(os.path.join(M, f), []).append((a, b))

E("model_router.py", """ARGS_NOTE = {"sol_cook": "option: شو تطبخ، مثال: طبخي بيض"}
""", """ARGS_NOTE = {"sol_cook": "option: شو تطبخ، مثال: طبخي بيض"}
# game actions the panel does not list as buttons, that he asks for in plain words
CARD_ACTIONS = {
    "sol_headlights": ("ضو السيارة", "شغلي ضو السيارة", "option: on أو off"),
    "sol_toggle_light": ("ضو الغرفة أو البيت، أقرب مفتاح ضو", "ضوي الغرفة", None),
    "sol_engine": ("محرك السيارة", "شغلي السيارة", "option: on أو off"),
    "sol_horn": ("زمور السيارة", "زمري", "option: once أو stop"),
}
""")
E("model_router.py", """- إذا الطلب مش مفهوم أبدًا: action = "unknown".
""", """- إذا الطلب مش مفهوم أبدًا، أو مو موجود بالقائمة: action = "unknown". لا تختاري فعل ما إلو علاقة بالطلب.
""")
E("model_router.py", """    shots = n.join('%s -> {"action":"%s","speech":""}' % e for e in EXAMPLES)
""", """    known = {a.get("id") for a in actions or [] if a.get("enabled", True)}
    for cid, (meaning, phrase, note) in CARD_ACTIONS.items():
        if cid in known or not actions:
            lines.append('%s: %s | مثال: "%s"%s' % (cid, meaning, phrase, " | " + note if note else ""))
    shots = n.join('%s -> {"action":"%s","speech":""}' % e for e in EXAMPLES)
    shots += n + 'شغلي الضو -> {"action":"sol_headlights","args":{"option":"on"},"speech":""}'
    shots += n + 'طفي ضو السيارة -> {"action":"sol_headlights","args":{"option":"off"},"speech":""}'
    shots += n + 'ضوي الغرفة -> {"action":"sol_toggle_light","speech":""}'
    shots += n + 'رقصي -> {"action":"unknown","speech":""}'
""")
E("chat_service.py", """        if action == "unknown" or (action != "none" and action not in MR.COMMANDS and action not in ids):
""", """        if action in ("refuel_from_can", "refuel_at_station") and not any(w in text for w in FUEL_WORDS):
            done_line("model", action, "no_fuel_word", "asked him")
            return "شو قصدك؟ عيدها بكلمة تانية."
        if action == "unknown" or (action != "none" and action not in MR.COMMANDS and action not in ids):
""")
E("chat_service.py", """import model_router as MR
""", """import model_router as MR
FUEL_WORDS = ("بنزين", "بانزين", "بنزن", "وقود", "بدون", "غالون", "جالون", "كاز", "محطة", "عبي", "تعبي", "fuel", "gas")
""")

out = {}
for p, ps in EDITS.items():
    t = open(p, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    for a, b in ps:
        a2, b2 = a.replace(NL, nl), b.replace(NL, nl)
        assert t.count(a2) == 1, (p[-20:], a[:60], t.count(a2))
        t = t.replace(a2, b2)
    compile(t, p, "exec")
    out[p] = t
for p, t in out.items():
    open(p, "w", encoding="utf-8", newline="").write(t)
print("applied")
