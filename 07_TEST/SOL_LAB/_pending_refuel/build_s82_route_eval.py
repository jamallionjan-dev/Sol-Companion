"""Builds s82_route_eval.json: the phrases Jamal typed that the routing got right before (05_TOOLS/sol_mind/sol_mind.log "chat: route"
lines: path=memory, or path=model with gate accepted or "-" and an action other than unknown/none), with the answer each must
still get. Read only on the log. A few logged routes were wrong at the time; they are corrected or left out here, by hand, below.
Plus the street / town / station questions that passed by path=memory before the card grew (2026-11-10 01:23) or failed tonight.
usage: build_s82_route_eval.py [sol_mind.log]  (writes s82_route_eval.json next to this file; re-run to refresh from a newer log)"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind", "sol_mind.log")
LINE = re.compile(r"^(\S+ \S+) chat: route text=(.*) path=(\S+) ms=\d+ action=(\S+) gate=(\S+) result=(.*)$")
# the logged answer was wrong at the time: what it should have been (action, option)
CORRECT = {"سول طفي متور السيارة": ("sol_engine", "off"),               # 22:15:41 live: headlights off, already_off
           "شغلي ضو السيارة": ("sol_headlights", "on"),                 # went to refuel_from_can
           "سول لو سمحتي احرثي الارض": ("plow", None),                  # model reply unreadable that time
           "شو في سيارات حواليكي؟": ("cars_near", None),               # memory path before s77 made it an action
           "شوفي سيارات حوليكي": ("cars_near", None)}                   # went to survey
EXCLUDE = {"ركبي السيارة الاقرب عليكي",                                   # went to follow; what he meant is not clear from the log
           "شوبتعرفي عن هي المدينة"}                                       # went to survey; a town question at best
OPTION = {"sol_headlights": {"شغلي": "on", "طفي": "off"}, "sol_engine": {"شغلي": "on", "طفي": "off"}, "sol_horn": {"": "once"}}
# Jamal's rules after the recording (s85, 2026-11-10): the answer each phrase must get now. "steps": several actions in one reply, in order.
RULES = {"تعالي لعندي": {"action": "come_car", "note": "Jamal 2026-11-10: bare \"تعالي لعندي\" is come_car"},
         "سول نزرلي من السيارة وتعالي لعندي بسرعة": {"action": "come_foot", "steps": [{"action": "exit_car", "option": None}, {"action": "come_foot", "option": None}],
                                                    "note": "s85: two actions, out of the car then come"},
         "طيب خلص طفي محرك السيارة ونزلي منها": {"steps": [{"action": "sol_engine", "option": "off"}, {"action": "exit_car", "option": None}],
                                                "note": "s85: two actions, engine off then out"}}
MEMORY = ["شو اسم المدينة", "شو اسم هالشارع", "شو اسم هالمدينة", "شو اسم هي المدينة", "شو اسم هاد الشارع",
          "بأي شارع نحنا", "وين نحنا هلأ", "بأي ضيعة نحنا", "شو هالكازية"]


def option_for(action, text):
    for w, o in OPTION.get(action, {}).items():
        if w in text: return o
    return None


def build(log):
    seen, out = set(), []
    for raw in open(log, encoding="utf-8", errors="replace"):
        m = LINE.match(raw.rstrip("\n"))
        if not m: continue
        when, text, path, action, gate = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        if text in seen or text in EXCLUDE: continue
        if text in CORRECT:
            a, o = CORRECT[text]
            seen.add(text); out.append({"text": text, "kind": "action", "action": a, "option": o, "source": "log %s (corrected)" % when}); continue
        if path == "memory" or text in MEMORY: continue                   # the memory list below
        if path != "model" or action in ("unknown", "none", "None") or gate not in ("accepted", "-"): continue
        seen.add(text)
        out.append({"text": text, "kind": "action", "action": action, "option": option_for(action, text), "source": "log " + when})
    for c in out:
        r = RULES.get(c["text"])
        if r:
            c.update({k: v for k, v in r.items() if k != "note"}); c["source"] += " (%s)" % r["note"]
    for t in MEMORY: out.append({"text": t, "kind": "memory", "action": "none", "option": None, "source": "map answer (path=memory before 2026-11-10 22:22)"})
    return out


if __name__ == "__main__":
    cases = build(LOG)
    p = os.path.join(HERE, "s82_route_eval.json")
    json.dump(cases, open(p, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print("wrote", p, len(cases), "phrases")
