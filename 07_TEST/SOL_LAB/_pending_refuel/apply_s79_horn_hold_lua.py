"""s79_horn_hold_lua (Jamal 2026-11-10 20:48 "خلي ايدك عالزمور"), game side. Pairs with apply_s79_horn_hold_mind.py.

Sol keeps her hand on the car horn while she drives: one long held horn (the vanilla horn key's hold: BaseVehicle.onHornStart
once, onHornStop at the end), until he says stop, she leaves the driver seat, the engine stops, the car is gone, or the safety
cap (2 game minutes) runs out. One new verb horn_hold start | stop; the existing sol_horn single beep is untouched.
  copies   SolHornHold.lua           (wraps U.runAction / U.actionCatalog; the catalog entry says state=holding|idle)
  edits    SolAuthority.lua          A.FIXES += "horn_hold"
           <Zomboid>/Lua/SolFixes_LAB.txt  horn_hold=on (only when missing; only when the file exists)
Independent of s75/s77/s78 (touches none of their text). Game closed only. In place, idempotent.
usage: apply_s79_horn_hold_lua.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "horn_hold"


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


def client(cl):
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")) and os.path.isfile(os.path.join(cl, "SolActions.lua")), "not a Sol client dir: " + cl
    src = os.path.join(HERE, "SolHornHold.lua")
    body = open(src, "rb").read()
    body.decode("ascii")                                        # pure ASCII, like every Sol Lua file
    assert b'M.VERSION = "0.1.0"' in body
    dst = os.path.join(cl, "SolHornHold.lua")
    if not os.path.exists(dst) or open(dst, "rb").read() != body:
        shutil.copy(src, dst); print("copied SolHornHold.lua")
    else: print("kept SolHornHold.lua")
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
    print("s79_horn_hold_lua applied")
