"""s88 game side (open items A6, A7, A8, A9; Jamal's TODO 2026-11-09 #6, #12, #17, #28, #29). Pairs with apply_s88_mind.py.

A6 why it failed: SolFailNote.lua (new) records every failure in one log line "[SolFail] source=... reason=... detail=..." and in
   <Zomboid>/Lua/SolFail_State.txt (newest only), which the Mind's "ليش" answer words.
     SolOrders.lua  failText(): the order's failure code (board / wheel / exit / order / home) -> SolFailNote.note
                    endFail(): the reason (no_path / door_unreachable / board_timeout / busy ...) with how long and how often she
                    tried (secs, tries, no_progress, failed_walks, preemptions) -> SolFailNote.orderEnd
                    busyText(): with fail_reasons on, she says only "I'm busy"; the "(preempted)" code goes to the log (it was
                    spoken: a mechanics leak)
A7 bridge_failure cause: the three places in SCDriving.lua that stop with bridge_failure (driveStart refused, no native status,
   route refused) now put the bridge's own words and the site into the job's detail (so the outcome and SolGPS's state carry it)
   and log "[SolDrive] bridge_failure at=start|status|follow cause=...", with the route's numbers (points, outside the map,
   smallest gap) for a refused route. Log evidence: 2026-11-09 21:52-01:55 "route refused: route must be 2 to 512 points ..."
   with "smallest_gap=0.19 / 0.44" (route points too close; spaced by s49); the 12:41:26 / 13:00:09 cases predate that log line.
A8 keys: "[SolKeys] <where> car=<script> car_key=<id> ignition= hotwired= hers=[id:type,...] his=[...] in_car=[...] match=..."
     SCDriving.lua  startNative: no key and the engine off (before "no_key")
     SolUI.solPickCar (wrapped by SolFailNote.lua, SolCarRules.lua untouched): cars there, none she may use -> the nearest three
A9 "Base duty" / "Move to" in the Sol window: Living Fellows' stateText looks up UI_SC_State_<order>; base_duty, move_to and the
   move_to_* actions had no key, so humanize() printed the English id. SolLF_AR_Orders.lua (new, generated here) adds those keys
   to SolLF_AR (our own table, read only while the Sol window builds). No third-party file is touched.
Switch: fail_reasons (A.FIXES; lab SolFixes_LAB.txt fail_reasons=on when missing). Logging and the Arabic words need none.
Game closed only. In place, idempotent; refuses when an anchor is not found exactly once.
usage: apply_s88_lua.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "fail_reasons"
FN = 'do local FN88 = rawget(_G, "SolFailNote"); if type(FN88) == "table" and type(FN88.%s) == "function" then pcall(FN88.%s, %s) end end'


def fn(name, args): return FN % (name, name, args)


EDITS = {
    "SCDriving.lua": [
        ("bridge start",
         '        print("[SolDrive] driveStart refused: " .. tostring(reason))\n        Driving.stop(job.actor, "bridge_failure")\n',
         '        print("[SolDrive] driveStart refused: " .. tostring(reason))\n        ' + fn("bridge", '"start", reason, job')
         + '   -- Sol s88: the cause behind bridge_failure\n        Driving.stop(job.actor, "bridge_failure")\n'),
        ("bridge status",
         '        print("[SolDrive] no native status: " .. tostring(why))\n        local stopped = Driving.stop(actor, "bridge_failure")\n',
         '        print("[SolDrive] no native status: " .. tostring(why))\n        ' + fn("bridge", '"status", why, job')
         + '   -- Sol s88\n        local stopped = Driving.stop(actor, "bridge_failure")\n'),
        ("bridge follow",
         '        job.result, job.reason, job.detail = "failed", "bridge_failure", followReason\n',
         '        job.result, job.reason, job.detail = "failed", "bridge_failure", followReason\n        ' + fn("bridge", '"follow", followReason, job, route')
         + '   -- Sol s88\n'),
        ("no key",
         '        Driving.stop(job.actor, "no_key")\n        return false, "no_key"\n',
         '        ' + fn("keyLine", '"drive_start", job.actor, job.vehicle') + '   -- Sol s88: her keys against the car\'s\n        '
         + fn("note", '"drive", "no_key", ""') + '\n        Driving.stop(job.actor, "no_key")\n        return false, "no_key"\n'),
    ],
    "SolOrders.lua": [
        ("failText",
         'local function failText(reason, context)\n',
         'local function failText(reason, context)\n    ' + fn("note", '"order_" .. tostring(context), reason, ""') + '   -- Sol s88: the code, in the log and for "why"\n'),
        ("endFail",
         'local function endFail(text)\n',
         'local function endFail(text)\n    ' + fn("orderEnd", 'text, job') + '   -- Sol s88: the reason and how long / how often she tried\n'),
        ("busyText",
         '    return AR.busy .. " (" .. tostring(why) .. ")"\n',
         '    local A88 = rawget(_G, "SolAuthority")\n'
         '    if type(A88) == "table" and type(A88.on) == "function" and A88.on("fail_reasons") == true then log("busy: " .. tostring(why)); return AR.busy end   -- Sol fix fail_reasons: the code goes to the log, never into her words\n'
         '    return AR.busy .. " (" .. tostring(why) .. ")"\n'),
    ],
}

MARKERS = {                                                                         # present once an edit is in (other edits may sit beside it)
    "bridge start": 'pcall(FN88.bridge, "start"', "bridge status": 'pcall(FN88.bridge, "status"', "bridge follow": 'pcall(FN88.bridge, "follow"',
    "no key": 'pcall(FN88.keyLine, "drive_start"', "failText": 'pcall(FN88.note, "order_"', "endFail": "pcall(FN88.orderEnd, text, job)",
    "busyText": 'A88.on("fail_reasons")',
}

# A9: Living Fellows' order and move_to_* states (UI_SC_State_<id>) with no key, in the same words style as SolLF_AR's states
STATES_AR = {
    "base_duty": "مناوبة بالقاعدة", "move_to": "انتقال", "check_room": "تفقّد غرفة", "dismissed": "مسرّحة", "expedition": "رحلة",
    "faction_duty": "مهمة للجماعة", "interact": "استعمال غرض", "wander": "تجوّل",
    "move_to_base_build": "ذهاب إلى البناء", "move_to_base_check_in": "ذهاب إلى نقطة التجمع", "move_to_base_storage": "ذهاب إلى مخزن القاعدة",
    "move_to_camp_storage": "ذهاب إلى مخزن المخيم", "move_to_car_trunk": "ذهاب إلى صندوق السيارة", "move_to_clean_stain": "ذهاب لتنظيف بقعة",
    "move_to_corpse": "ذهاب إلى جثة", "move_to_farm_plot": "ذهاب إلى الحقل", "move_to_fishing_spot": "ذهاب إلى مكان الصيد",
    "move_to_gather_destination": "ذهاب إلى مكان الجمع", "move_to_gather_item": "ذهاب لجمع غرض", "move_to_light_switch": "ذهاب إلى مفتاح الإنارة",
    "move_to_production_body": "ذهاب إلى جثة", "move_to_production_grave": "ذهاب إلى القبر", "move_to_production_tree": "ذهاب إلى شجرة",
    "move_to_pyre_body": "ذهاب بجثة إلى المحرقة", "move_to_pyre_watch": "ذهاب لمراقبة المحرقة", "move_to_quarantine": "ذهاب إلى العزل",
    "move_to_radio": "ذهاب إلى الراديو", "move_to_scavenge": "ذهاب للتفتيش", "move_to_seat": "ذهاب إلى مقعد", "move_to_treat": "ذهاب للعلاج",
    "move_to_tv": "ذهاب إلى التلفزيون", "move_to_water_source": "ذهاب إلى مصدر ماء", "move_to_window": "ذهاب إلى الشباك",
}


def esc(s): return "".join(c if 32 <= ord(c) < 127 else "\\\\u%04X" % ord(c) for c in s)


def orders_lua():
    rows = ["-- SolLF_AR_Orders.lua - s88 (A9): Arabic for Living Fellows' orders and move_to_* states that had no UI_SC_State_ key,",
            "-- so the Sol window printed the English id (\"Base duty\", \"Move to ...\"). Generated by apply_s88_lua.py; same format as SolLF_AR.",
            'require "SolLF_AR"',
            "SolLF_AR = SolLF_AR or {}",
            "local add = {"]
    for k in sorted(STATES_AR):
        rows.append('  ["UI_SC_State_%s"] = "%s",' % (k, esc(STATES_AR[k])))
    rows += ["}", "for k, v in pairs(add) do if SolLF_AR[k] == nil then SolLF_AR[k] = v end end", ""]
    return CRLF.join(rows)


def edit(path, label, old, new, marker):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if marker in t: return "kept"
    assert t.count(old) == 1, (os.path.basename(path), label, t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


def put(dst, body):
    if os.path.exists(dst) and open(dst, "rb").read() == body: return "kept"
    open(dst, "wb").write(body)
    return "written"


def client(cl):
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")) and os.path.isfile(os.path.join(cl, "SolOrders.lua")), "not a Sol client dir: " + cl
    assert os.path.isfile(os.path.join(cl, "SolLF_AR.lua")), "SolLF_AR.lua missing in " + cl
    body = open(os.path.join(HERE, "SolFailNote.lua"), "rb").read()
    body.decode("ascii")                                                            # pure ASCII, like every Sol Lua file
    assert b'M.VERSION = "0.1.0"' in body
    print("SolFailNote.lua", put(os.path.join(cl, "SolFailNote.lua"), body))
    orders = orders_lua().encode("ascii")
    print("SolLF_AR_Orders.lua", put(os.path.join(cl, "SolLF_AR_Orders.lua"), orders))
    for name, edits in EDITS.items():
        for label, old, new in edits:
            print(name, label, edit(os.path.join(cl, name), label, old, new, MARKERS[label]))
    print("SolAuthority", FIX, edit(os.path.join(cl, "SolAuthority.lua"), FIX, "A.FIXES = {" + NL,
                                    "A.FIXES = {" + NL + '    "%s",          -- s88: "why" says the real reason; no code in her words' % FIX + NL,
                                    '"%s"' % FIX))
    fixfile = os.path.normpath(os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt"))
    if os.path.exists(fixfile):
        have = open(fixfile, encoding="utf-8", newline="").read()
        if FIX + "=" not in have:
            with open(fixfile, "a", encoding="utf-8", newline="") as h:
                if have and not have.endswith(NL): h.write(CRLF)
                h.write(FIX + "=on" + CRLF)
            print("SolFixes_LAB", FIX + "=on")


if __name__ == "__main__":
    client(sys.argv[1])
    print("s88_lua applied")
