"""s95 station_survey, the Mind side (goal_engine.RefuelErrand). No new action, no new wording, no card change:
  - TELL: a plain line for each reason the station survey can end with (only the survey sends these codes);
  - parking_wait: "parking:<why>" (she moves to the other side or another pump) is still parking, and she says why once;
    a "survey_*" failure ends the errand with its line at once, instead of the old four blind drives round the pump.
Idempotent; refuses when an anchor is not found exactly once. A Python-only Mind restart is enough.
usage: apply_s95_station_refuel_mind.py <sol_mind dir>"""
import os, sys
MD = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

P = os.path.join(MD, "goal_engine.py")
edit(P,
     '    GENERIC = "ما قدرت أكمل المشوار."' + NL + '    ALREADY_THERE = 14.0' + NL,
     '    GENERIC = "ما قدرت أكمل المشوار."' + NL +
     '    TELL = dict(TELL, **{                                         # s95 station_survey: why, from the game\'s own checks' + NL +
     '        "survey_no_pump": "ما في ولا مضخة فيها بنزين وعليها كهربا بهالكازية.",' + NL +
     '        "survey_no_pose": "ما في محل فاضي جنب المضخات، ما رح جرّب صف.",' + NL +
     '        "survey_no_stand": "صفّيت، بس ما في محل وقّف فيه جنب غطا البنزين.",' + NL +
     '        "survey_drive_failed": "ما قدرت وصّل السيارة لجنب المضخة، الطريق مسكّر.",' + NL +
     '        "survey_no_cap": "ما عرفت وين غطا البنزين بهالسيارة.",' + NL +
     '        "wrong_fuel": "هالسيارة ما بتمشي على بنزين.",' + NL +
     '    })' + NL +
     '    PARK_SAY = {                                                  # s95: said once each, while she moves the car' + NL +
     '        "other_pump": "الخرطوم ما بيوصل من هالجهة، عم غيّر المضخة.",' + NL +
     '        "other_side": "غطا البنزين مو جهة المضخة، عم صف من الجهة التانية.",' + NL +
     '        "blocked": "في شي سادد الطريق، عم جرّب محل تاني.",' + NL +
     '    }' + NL +
     '    ALREADY_THERE = 14.0' + NL)
edit(P,
     '        if phase == "parking_wait":' + NL +
     '            res = self._park_status(g, now)' + NL +
     '            if res is None or res == (True, "parking"):' + NL,
     '        if phase == "parking_wait":' + NL +
     '            res = self._park_status(g, now)' + NL +
     '            if res is not None and res[0] and str(res[1]).startswith("parking:"):     # s95 station_survey: another side or pump, said once' + NL +
     '                why = str(res[1]).split(":", 1)[1]' + NL +
     '                said = g.setdefault("parkSaid", [])' + NL +
     '                if why not in said:' + NL +
     '                    said.append(why)' + NL +
     '                    if self.PARK_SAY.get(why): self._speak(self.PARK_SAY[why])' + NL +
     '                res = (True, "parking")' + NL +
     '            if res is not None and not res[0] and str(res[1]).startswith("survey_"): return self._fail(g, res[1])' + NL +
     '            if res is None or res == (True, "parking"):' + NL)
print("s95 station_survey Mind side applied")
