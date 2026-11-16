"""s97 gear_recover: after a fall, trip, vault-fall or knockdown Sol picks up what came off her and puts it back on.
Live 2026-11-11 10:40:51.213 (DebugLog 2026-11-11_10-19): "IsoFallingClothing added x=7406.197 y=8258.394" - her helmet came off when
she fell vaulting the porch railing; she never took it back. New file SolGearRecover.lua (its header has the rules); switch
gear_recover read at call time (off: nothing read or done). Verb: sol_gear status | take.
Edits: copies SolGearRecover.lua; SolAuthority.lua (A.FIXES += gear_recover); <Zomboid>/Lua/SolFixes_LAB.txt (gear_recover=on when
the file exists and has no line for it). Independent of the other fixes. Game closed only. Idempotent.
usage: apply_s97_gear_recover.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "gear_recover"


def main(cl):
    cl = os.path.abspath(cl)
    ap = os.path.join(cl, "SolAuthority.lua")
    assert os.path.isfile(ap), "not a Sol client dir: " + cl
    src = os.path.join(HERE, "SolGearRecover.lua")
    body = open(src, encoding="utf-8").read()
    assert all(ord(c) < 128 for c in body), "SolGearRecover.lua is not ASCII"
    dst = os.path.join(cl, "SolGearRecover.lua")
    if os.path.exists(dst) and open(dst, encoding="utf-8").read() == body:
        print("SolGearRecover.lua kept")
    else:
        shutil.copy(src, dst)
        print("SolGearRecover.lua copied")
    a = open(ap, encoding="utf-8", newline="").read()
    if '"%s"' % FIX in a:
        print("SolAuthority kept")
    else:
        anl = CRLF if CRLF in a else NL
        old = "A.FIXES = {" + anl
        assert a.count(old) == 1
        a = a.replace(old, old + '    "%s",        -- s97: what came off her in a fall is picked up and put back on' % FIX + anl)
        open(ap, "w", encoding="utf-8", newline="").write(a)
        print("SolAuthority edited")
    fixfile = os.path.normpath(os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt"))
    if os.path.exists(fixfile):
        have = open(fixfile, encoding="utf-8", newline="").read()
        if FIX + "=" not in have:
            with open(fixfile, "a", encoding="utf-8", newline="") as h:
                if have and not have.endswith(NL): h.write(CRLF)
                h.write(FIX + "=on" + CRLF)
            print("SolFixes_LAB", FIX + "=on")


if __name__ == "__main__":
    main(sys.argv[1])
    print("s97 gear_recover applied")
