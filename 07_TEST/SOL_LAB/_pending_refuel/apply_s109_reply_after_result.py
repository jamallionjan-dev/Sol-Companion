"""s109 reply_after_result, game side: registers the switch only (no Lua behaviour changes). Pairs with
apply_s109_reply_after_result_mind.py, where the behaviour is (the Mind reads SolFixes_LAB.txt each time; a missing line = off there).
  SolAuthority.lua                   A.FIXES += "reply_after_result" (so the release lists and SolFixes_MAIN carry it)
  <Zomboid>/Lua/SolFixes_LAB.txt     reply_after_result=on (only when missing; only when the file exists)
Game closed only. Idempotent.
usage: apply_s109_reply_after_result.py <client>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "reply_after_result"


def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old))
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new)); print("edited " + os.path.basename(path))


def main(cl):
    A = os.path.join(cl, "SolAuthority.lua")
    if '"%s"' % FIX in open(A, encoding="utf-8").read(): print("kept SolAuthority.lua")
    else: edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",   -- s109: she speaks what the game confirmed (the Mind reads it); never a success line on a failure' % FIX + NL)
    fix = os.path.normpath(os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt"))
    if os.path.exists(fix):
        body = open(fix, encoding="utf-8", newline="").read()
        if any(l.strip().split("=", 1)[0] == FIX for l in body.splitlines()): print("kept SolFixes_LAB.txt")
        else:
            nl = CRLF if CRLF in body else NL
            with open(fix, "a", encoding="utf-8", newline="") as h: h.write(("" if body.endswith(NL) or body == "" else nl) + FIX + "=on" + nl)
            print("SolFixes_LAB.txt " + FIX + "=on")
    print("s109 reply_after_result applied")


if __name__ == "__main__":
    main(sys.argv[1])
