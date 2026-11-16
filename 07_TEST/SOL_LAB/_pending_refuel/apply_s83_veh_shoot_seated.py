"""s83 veh_shoot_seated (Jamal 2026-11-10 22:33: firing from inside the car stands his body up through the roof; it should stay
seated and fire). Game side only; no Mind change, no Java.

Cause (game 42.22.2, read-only): media/AnimSets/player-vehicle/aim/*.xml play the standing clips (Bob_IdleAimRifle ...) with no bone
mask, while player-vehicle/idle/default.xml plays Bob_IdleDriving. The car was a vanilla Base.Van_Blacksmith (log 22:27:09), so
neither damnlib's seated aim nodes (KI5 cars only, damnVehicle=True) nor any other active mod covered it.
Fix: one extra aim node in OUR mod (m_ConditionPriority 10, condition SolSeatAim == true) that keeps Bob_IdleDriving, and a small
client file that sets SolSeatAim on the local human player only while he sits in a non-KI5 car and the switch is on. The shot
itself (player-vehicle/ranged, an upper-body sub-state) is untouched, so the gun still comes up for each shot.
  copies   SolVehShootSeated.lua -> <client>/SolVehShootSeated.lua
           SolSeatAim.xml        -> <client>/../../AnimSets/player-vehicle/aim/SolSeatAim.xml
  edits    SolAuthority.lua          A.FIXES += "veh_shoot_seated"
           <Zomboid>/Lua/SolFixes_LAB.txt  veh_shoot_seated=on (only when missing; only when the file exists)
Independent of s75..s82 (touches none of their text). Game closed only (AnimSets load at game start). In place, idempotent.
usage: apply_s83_veh_shoot_seated.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "veh_shoot_seated"


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


def place(src_name, dst):
    body = open(os.path.join(HERE, src_name), "rb").read()
    body.decode("ascii")                                        # pure ASCII, like every Sol file
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst) or open(dst, "rb").read() != body:
        open(dst, "wb").write(body); return "copied"
    return "kept"


def client(cl):
    cl = os.path.abspath(cl)
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")) and os.path.isfile(os.path.join(cl, "SolActions.lua")), "not a Sol client dir: " + cl
    media = os.path.normpath(os.path.join(cl, "..", ".."))
    assert os.path.basename(media) == "media" and os.path.isdir(os.path.join(media, "lua")), "no media dir above " + cl
    lua = open(os.path.join(HERE, "SolVehShootSeated.lua"), "rb").read()
    assert b'M.VERSION = "0.1.0"' in lua and b'M.VAR = "SolSeatAim"' in lua
    xml = open(os.path.join(HERE, "SolSeatAim.xml"), "rb").read()
    assert b"<m_Name>SolSeatAim</m_Name>" in xml and b"<m_ConditionPriority>10</m_ConditionPriority>" in xml
    print("SolVehShootSeated.lua", place("SolVehShootSeated.lua", os.path.join(cl, "SolVehShootSeated.lua")))
    print("AnimSets/player-vehicle/aim/SolSeatAim.xml",
          place("SolSeatAim.xml", os.path.join(media, "AnimSets", "player-vehicle", "aim", "SolSeatAim.xml")))
    print("SolAuthority", FIX, edit(os.path.join(cl, "SolAuthority.lua"), "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",' % FIX + NL, '"%s"' % FIX))
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
    print("s83_veh_shoot_seated applied")
