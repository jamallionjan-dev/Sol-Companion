"""s87 game side (ledger A1 + A10, council SOL_REVIEW section 45). Pairs with apply_s87_mind.py (smart_park only).

1. smart_park: "park the car" near any place: the nearest free spot the car fits in, blocking no road or door, then a check
   that the whole car is inside (verb sol_smart_park find | settle | status for the Mind).
     copies   SolSmartPark.lua
2. move_check: while she walks an order of his (LF move_to): a "did not move" check every 600 ms -> a fresh path; jog when
   more than 8 tiles to go, walk within 4; a walk to him ends 1.5 tiles from him.
     copies   SolMoveCheck.lua         (wraps SurvivorCompanion.Navigation.request for Sol's ordered_move only)
   edits    SolAuthority.lua          A.FIXES += "smart_park", "move_check"
            <Zomboid>/Lua/SolFixes_LAB.txt  smart_park=on, move_check=on (each only when missing; only when the file exists)
Game closed only. In place, idempotent.
usage: apply_s87_lua.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIXES = ("smart_park", "move_check")
FILES = (("SolSmartPark.lua", 'M.VERSION = "0.1.0"'), ("SolMoveCheck.lua", 'M.VERSION = "0.1.0"'))


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


def client(cl):
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")) and os.path.isfile(os.path.join(cl, "SCNavigation.lua")), "not a Sol client dir: " + cl
    for name, version in FILES:
        src = os.path.join(HERE, name)
        body = open(src, "rb").read()
        body.decode("ascii")                                    # pure ASCII, like every Sol Lua file
        assert version.encode() in body, name
        dst = os.path.join(cl, name)
        if not os.path.exists(dst) or open(dst, "rb").read() != body:
            shutil.copy(src, dst); print("copied " + name)
        else: print("kept " + name)
    for fix in FIXES:
        print("SolAuthority", fix, edit(os.path.join(cl, "SolAuthority.lua"), "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",' % fix + NL, '"%s"' % fix))
    fixfile = os.path.normpath(os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt"))
    if os.path.exists(fixfile):
        for fix in FIXES:
            have = open(fixfile, encoding="utf-8", newline="").read()
            if fix + "=" in have: continue
            with open(fixfile, "a", encoding="utf-8", newline="") as h:
                if have and not have.endswith(NL): h.write(CRLF)
                h.write(fix + "=on" + CRLF)
            print("SolFixes_LAB", fix + "=on")


if __name__ == "__main__":
    client(sys.argv[1])
    print("s87_lua applied")
