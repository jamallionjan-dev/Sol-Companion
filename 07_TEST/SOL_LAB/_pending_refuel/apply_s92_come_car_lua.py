"""s92 come_by_car, game side (Jamal 2026-11-10: "come to me by car" from home or from ANY place she stands with a car near her).
Pairs with apply_s92_come_car_mind.py.

     copies   SolFarComeCar.lua      (the pieces: see its header; switch come_by_car, and far_car for the far arrival pieces)
     edits    SolFar.lua             usableCar: the 60-tile limit is read through F.carNear (come_by_car: any loaded distance)
                                     end of file: publishes the module as SolUI.solFarF with the locals SolFarComeCar needs (read only use)
              SolAuthority.lua       A.FIXES += "come_by_car"
              <Zomboid>/Lua/SolFixes_LAB.txt  come_by_car=on (only when missing; only when the file exists). far_car is NOT touched.
Game closed only. In place, idempotent. Pure ASCII.
usage: apply_s92_come_car_lua.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "come_by_car"
NEAR_OLD = 'if px == nil or cx == nil or dist(px, py, cx, cy) > CAR_NEAR then return nil, "car_not_near" end'
NEAR_NEW = 'if px == nil or cx == nil or dist(px, py, cx, cy) > ((type(F.carNear) == "function" and F.carNear()) or CAR_NEAR) then return nil, "car_not_near" end   -- s92 come_by_car'
END_OLD = NL + "return F" + NL
END_NEW = (NL + "-- s92 come_by_car: SolFarComeCar.lua reads these (it wraps F.arriveTick / F.arrive and U.solFar; it never writes SolFar's state)" + NL
           + "F.record, F.loadedCar, F.store, F.loadedCanGo, F.fuelIn, F.actor = record, loadedCar, store, loadedCanGo, fuelIn, actor" + NL
           + "U.solFarF = F" + NL + "return F" + NL)


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


def client(cl):
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")) and os.path.isfile(os.path.join(cl, "SolFar.lua")), "not a Sol client dir: " + cl
    src = os.path.join(HERE, "SolFarComeCar.lua")
    body = open(src, "rb").read()
    body.decode("ascii")                                        # pure ASCII, like every Sol Lua file
    assert b'M = { VERSION = "0.1.0" }' in body
    dst = os.path.join(cl, "SolFarComeCar.lua")
    if not os.path.exists(dst) or open(dst, "rb").read() != body:
        shutil.copy(src, dst); print("copied SolFarComeCar.lua")
    else: print("kept SolFarComeCar.lua")
    far = os.path.join(cl, "SolFar.lua")
    print("SolFar carNear", edit(far, NEAR_OLD, NEAR_NEW, NEAR_NEW))
    print("SolFar module", edit(far, END_OLD, END_NEW, "U.solFarF = F"))
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
    print("s92_come_car_lua applied")
