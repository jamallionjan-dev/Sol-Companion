"""Far-away Sol and the car. Confirmed from sol_mind.log 2026-11-10 17:39-17:40:
- "ركبي السيارة": the model chose board_car, the Mind ran its card line "اركبي معي"; boarding was not a call, so she refused: "أنا بعيدة ...".
- "ركبي السيارة الاقرب عليكي": the model chose follow; the car test ran on the card line, which has no car word, so she came on foot.
Fix (Mind only): the car test reads what he really wrote, and the car words include "السيارة"/"سيارة"; an order to get in a car while she is far is a call to come by car.
usage: apply_s63_mind.py <sol_mind dir>"""
import os, sys
MIND = sys.argv[1]
p = os.path.join(MIND, "chat_service.py")
t = open(p, encoding="utf-8", newline="").read()
NL = "\r\n" if "\r\n" in t else "\n"

def rep(old, new):
    global t
    if new in t: return
    assert t.count(old) == 1, old[:70]
    t = t.replace(old, new)

rep('_CAR_RX = re.compile(r"(بالسيار|بالعربي|بالمركب|سيارتك|سيارتي)")',
    '_CAR_RX = re.compile(r"(بالسيار|بالعربي|بالمركب|سيارتك|سيارتي|السيار|سيار[ةه]|العربي[ةه]|المدرع)")')
rep("            routed = list(history[:-1]) + [dict(history[-1], text=MR.COMMANDS[action][1])]",
    "            routed = list(history[:-1]) + [dict(history[-1], text=MR.COMMANDS[action][1], said=text)]      # what he really wrote rides along")
rep("        if self._far_order(text, snap, done): return done",
    "        if self._far_order(text, snap, done, (history[-1].get(\"said\") if history else None) or text): return done")
rep("    def _far_order(self, text, snap, done):",
    "    def _far_order(self, text, snap, done, said=None):")
rep("        called = come_words or (goal or {}).get(\"intent\") == \"fetch_player\" or any(n == \"action\" and a.get(\"action\") in (\"regroup\", \"follow\") for n, a in found)",
    "        said = said or text" + NL +
    "        board = any(n == \"action\" and a.get(\"action\") == \"board_vehicle\" for n, a in found)          # far away, \"get in the car\" means: come by car" + NL +
    "        called = board or come_words or (goal or {}).get(\"intent\") == \"fetch_player\" or any(n == \"action\" and a.get(\"action\") in (\"regroup\", \"follow\") for n, a in found)")
rep("            self._far_come(goal, _CAR_RX.search(text or \"\") is not None)",
    "            self._far_come(goal, board or _CAR_RX.search(said or \"\") is not None)")
# Until her car can be brought from far (far_car), a car order never ends in "I can't": she comes on foot and says so naturally.
rep("            if option is None:" + NL +
    "                self._forced = FAR_CAR_NO.get(why, FAR_NO_CAR)" + NL +
    "                return" + NL +
    "            r = run_action(self.dir, \"sol_far\", option, wait=2.5)" + NL +
    "            self.log(\"chat: far car -> %s\" % r)" + NL +
    "            reason = str(r.get(\"reason\")) if isinstance(r, dict) else \"\"" + NL +
    "            far_car = True" + NL,
    "            if option is None:                                                  # no spot or no way to bring it: on foot, below" + NL +
    "                r, reason = {\"ok\": False, \"reason\": why}, why" + NL +
    "            else:" + NL +
    "                r = run_action(self.dir, \"sol_far\", option, wait=2.5)" + NL +
    "                self.log(\"chat: far car -> %s\" % r)" + NL +
    "                reason = str(r.get(\"reason\")) if isinstance(r, dict) else \"\"" + NL +
    "                far_car = True" + NL)
rep("        if not isinstance(r, dict) or not r.get(\"ok\") or not reason.startswith(\"waiting:\"):" + NL +
    "            self._forced = FAR_CAR_NO.get(reason, FAR_NO_CAR) if by_car else \"ما بقدر أتحرك من مكاني هلأ.\"" + NL +
    "            return",
    "        if by_car and (not isinstance(r, dict) or not r.get(\"ok\") or not reason.startswith(\"waiting:\")):      # no car she can bring: on foot, said plainly" + NL +
    "            self.log(\"chat: far car not possible (%s), coming on foot\" % reason)" + NL +
    "            r = run_action(self.dir, \"sol_far\", \"come\", wait=2.5)" + NL +
    "            reason = str(r.get(\"reason\")) if isinstance(r, dict) else \"\"" + NL +
    "            if isinstance(r, dict) and r.get(\"ok\") and reason.startswith(\"waiting:\"):" + NL +
    "                self._forced = far_wait_line(reason, \"ما في سيارة بتمشي جنبي هلأ، جاية مشي، بدي %s.\")" + NL +
    "                self._far_waiting, self._far_told_edge = \"foot\", False" + NL +
    "                return" + NL +
    "            by_car = False" + NL +
    "        if not isinstance(r, dict) or not r.get(\"ok\") or not reason.startswith(\"waiting:\"):" + NL +
    "            self._forced = FAR_CAR_NO.get(reason, FAR_NO_CAR) if by_car else \"ما بقدر أتحرك من مكاني هلأ.\"" + NL +
    "            return")
open(p, "w", encoding="utf-8", newline="").write(t)
print("applied")
