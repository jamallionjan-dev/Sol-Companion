"""s82 address_target (Jamal 2026-11-10 22:15: the GPS drove to "625 Dewey Street, Muldraugh", stopped on S Main St behind the house,
15 tiles from the marker, SolNavLeg: no_corridor_wide_enough, and the GPS said arrived).
Game closed only. In place and idempotent. No line of any other file is edited except the switch list: SolAddressTarget.lua wraps
SolAddressBook.go, U.gpsPollRequest, U.gpsStatus and SolGPSWords.panelLine at load and on OnGameStart (see its header).

  copies   SolAddressTarget.lua (generated ASCII from src/SolAddressTarget_src.lua) -> <client dir>
  edits    SolAuthority.lua  A.FIXES += "address_target"
           <Zomboid>/Lua/SolFixes_LAB.txt  address_target=on (only when missing)
Needs (already installed in the lab): SolAddressBook.lua (address_book), SolStaticRoads.lua + SolStaticRoadsData.lua (the road graph,
loaded whether gps_static_roads is on or not), SolGPS.lua; SolGPSWords.lua for the panel line (gps_plain_words).
usage: apply_s82_address_target.py <client dir>
       apply_s82_address_target.py --gen          regenerate SolAddressTarget.lua from src (Arabic -> \\uXXXX)"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "address_target"
NAME = "SolAddressTarget.lua"


def gen():
    src = open(os.path.join(HERE, "src", "SolAddressTarget_src.lua"), encoding="utf-8").read()
    out = "".join(c if ord(c) < 128 else "\\\\u%04X" % ord(c) for c in src)
    open(os.path.join(HERE, NAME), "w", encoding="ascii", newline="\n").write(out)
    print("generated", NAME)


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


def client(cl):
    for need in ("SolAuthority.lua", "SolAddressBook.lua", "SolGPS.lua"):
        assert os.path.isfile(os.path.join(cl, need)), "not a Sol client dir with %s: %s" % (need, cl)
    src = os.path.join(HERE, NAME)
    body = open(src, encoding="ascii").read()
    assert 'M.VERSION = "0.1.0"' in body and "SolAddressTarget" in body
    dst = os.path.join(cl, NAME)
    if os.path.exists(dst) and open(dst, encoding="ascii").read() == body: print("kept", NAME)
    else: shutil.copy(src, dst); print("copied", NAME)
    print("SolAuthority", edit(os.path.join(cl, "SolAuthority.lua"), "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",' % FIX + NL, '"%s"' % FIX))
    fixfile = os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
    if os.path.exists(fixfile):
        have = open(fixfile, encoding="utf-8").read()
        if FIX + "=" not in have:
            with open(fixfile, "a", encoding="utf-8", newline="") as h:
                if have and not have.endswith(NL): h.write(CRLF)
                h.write(FIX + "=on" + CRLF)
            print("SolFixes_LAB", FIX + "=on")


if __name__ == "__main__":
    if sys.argv[1:] == ["--gen"]: gen()
    else:
        client(sys.argv[1])
        print("s82 address_target applied")
