"""s85 game side (Jamal 2026-11-10). Pairs with apply_s85_mind.py.

1. exit_first: an on-foot order (rest at home, farm work, sort, chickens, walk, fetch, guard) while she sits in a car: she gets out
   by herself first, then does it (live 21:32:36 "rest at home" from the car -> refused in_vehicle). She stops her own drive
   first, or waits for his car to stand. Verb sol_exit_first status for the Mind.
     copies   SolExitFirst.lua          (wraps SolUI.runAction at the first tick, outside every other wrapper)
     edits    SolAuthority.lua          A.FIXES += "exit_first"
              <Zomboid>/Lua/SolFixes_LAB.txt  exit_first=on (only when missing; only when the file exists)
2. GPS panel words match the button: the ready line said "press qudi" while the button reads "suqi".
     edits    SolGPS.lua                "\\u0627\\u0636\\u063A\\u0637 \\u0642\\u0648\\u062F\\u064A" -> "... \\u0633\\u0648\\u0642\\u064A"
              (the line is in SolGPS.lua's panel draw, not in SolGPSWords.lua; no generator holds it)
Game closed only. In place, idempotent.
usage: apply_s85_lua.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "exit_first"
GPS_OLD = '\\\\u0627\\\\u0636\\\\u063A\\\\u0637 \\\\u0642\\\\u0648\\\\u062F\\\\u064A", "Route ready - press Drive"'
GPS_NEW = '\\\\u0627\\\\u0636\\\\u063A\\\\u0637 \\\\u0633\\\\u0648\\\\u0642\\\\u064A", "Route ready - press Drive"'


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


def client(cl):
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")) and os.path.isfile(os.path.join(cl, "SolOrders.lua")), "not a Sol client dir: " + cl
    src = os.path.join(HERE, "SolExitFirst.lua")
    body = open(src, "rb").read()
    body.decode("ascii")                                        # pure ASCII, like every Sol Lua file
    assert b'M.VERSION = "0.1.0"' in body
    dst = os.path.join(cl, "SolExitFirst.lua")
    if not os.path.exists(dst) or open(dst, "rb").read() != body:
        shutil.copy(src, dst); print("copied SolExitFirst.lua")
    else: print("kept SolExitFirst.lua")
    print("SolAuthority", FIX, edit(os.path.join(cl, "SolAuthority.lua"), "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",' % FIX + NL, '"%s"' % FIX))
    print("SolGPS press_suqi", edit(os.path.join(cl, "SolGPS.lua"), GPS_OLD, GPS_NEW, GPS_NEW))
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
    print("s85_lua applied")
