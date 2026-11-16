"""s91 game side (Jamal 2026-11-10: every time she gets out of the car she turns the engine off, unless he asked her directly to
leave it running). Pairs with apply_s91_engine_off_exit_mind.py.

   copies   SolExitEngine.lua          (wraps SurvivorCompanion.Vehicle.exit, the one native exit every path ends in, and
                                        SolUI.runAction for exit_vehicle's option keep_engine; both at the first tick)
   edits    SolAuthority.lua           A.FIXES += "exit_engine_off"
            <Zomboid>/Lua/SolFixes_LAB.txt  exit_engine_off=on (only when missing; only when the file exists)
Independent of every other stage's text. Game closed only. In place, idempotent.
usage: apply_s91_engine_off_exit_lua.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "exit_engine_off"


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
    src = os.path.join(HERE, "SolExitEngine.lua")
    body = open(src, "rb").read()
    body.decode("ascii")                                        # pure ASCII, like every Sol Lua file
    assert b'M.VERSION = "0.1.0"' in body
    dst = os.path.join(cl, "SolExitEngine.lua")
    if not os.path.exists(dst) or open(dst, "rb").read() != body:
        shutil.copy(src, dst); print("copied SolExitEngine.lua")
    else: print("kept SolExitEngine.lua")
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
    print("s91_engine_off_exit_lua applied")
