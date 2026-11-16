"""s151: understand fuel cans at a station and do not restart an active refuel errand.
usage: python apply_s151_refuel_intent.py <sol_mind directory>
Exact-anchor, idempotent patch. This changes only the selected Mind source files.
"""
import os, sys

MD = os.path.abspath(sys.argv[1])
NL = "\n"
CRLF = "\r\n"

def edit(name, old, new):
    path = os.path.join(MD, name)
    text = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in text else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in text:
        return
    count = text.count(old)
    assert count == 1, (name, count, old[:100])
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace(old, new))

edit("intent_engine.py",
     '_CAN_WORDS = ("غالون", "غلون", "جالون", "جلون", "جركن", "جيركن", "بيدون", "تنكة", "تنكه", "gas can", "jerry")',
     '_CAN_WORDS = ("غالون", "غلون", "جالون", "جلون", "جركن", "جيركن", "بيدون", "بدونات", "بدونة", "تنكة", "تنكه", "gas can", "jerry")')

edit("chat_service.py",
     '            self._stop_farm_if_running(snap)                                    # any other order from him ends what she was doing on the farm' + NL +
     '            r = self.goals.submit(goal)' + NL +
     '            if goal.get("intent") == "refuel_errand" and r.get("status") == "already_running":' + NL +
     '                # asked again: she starts over from where she is, and marks the station again' + NL +
     '                self.goals.cancel(reason="player_order:refuel_again")' + NL +
     '                r = self.goals.submit(goal)' + NL +
     '            self._turn_action_results.append(r)' + NL +
     '            done.append("goal %s -> %s" % (goal.get("intent"), json.dumps(r, ensure_ascii=False)))' + NL +
     '            self.log("chat: goal %s -> %s" % (goal.get("intent"), r))' + NL,
     '            self._stop_farm_if_running(snap)                                    # any other order from him ends what she was doing on the farm' + NL +
     '            r = self.goals.submit(goal)' + NL +
     '            self._turn_action_results.append(r)' + NL +
     '            done.append("goal %s -> %s" % (goal.get("intent"), json.dumps(r, ensure_ascii=False)))' + NL +
     '            self.log("chat: goal %s -> %s" % (goal.get("intent"), r))' + NL)

edit("model_router.py",
     '    "refuel_from_can":   ("تعبي السيارة من بدون بنزين", None),' + NL +
     '    "refuel_at_station": ("تروح تعبي السيارة من الكازية", "عبي السيارة بنزين من الكازية"),',
     '    "refuel_from_can":   ("تعبي السيارة من بدونة بنزين", None),' + NL +
     '    "refuel_at_station": ("تعبي السيارة أو بدونات البنزين من الكازية", "عبي السيارة بنزين من الكازية"),')
edit("model_router.py",
     '    "secret_loadout": "نسخة من سلاحه السري مع ذخيرة", "refuel_at_station": "تعبي من الكازية", "farm_keeper": "تهتم بالمزرعة لحالها",',
     '    "secret_loadout": "نسخة من سلاحه السري مع ذخيرة", "refuel_at_station": "تعبي السيارة والبدونات من الكازية", "farm_keeper": "تهتم بالمزرعة لحالها",')
edit("model_router.py",
     'EXAMPLES_S90 = (' + NL,
     'EXAMPLES_S90 = (' + NL +
     '    ("سول عبي بدونات البنزين من الكازية", "refuel_at_station", None),' + NL +
     '    ("عبي السيارة بنزين من الكازية", "refuel_at_station", None),' + NL)

print("s151 refuel intent fix applied")
