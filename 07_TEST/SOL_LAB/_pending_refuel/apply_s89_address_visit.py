"""s89 address_visit (ledger A3 A4 A5, PLAN_address_book.md s6/s7 "not done"). Game closed only. In place and idempotent.

  A3 book_visited    a stash row is marked "انزار" by itself when she gets there (10 tiles, 6 s, any floor); once per row
  A4 book_hint       a paper or map with a place he opened while she was far: when she is next beside him she asks once
                     "شو هالورقة؟ فرجيني ياها وأنا حدك" (the book's rule then learns it when he opens it again beside her)
  A5 address_target  (the s82 switch, no new one) an area row drives to the nearest entrance of the area on a paved road;
                     already inside: the paved road nearest the area's centre

  copies   SolAddressVisit.lua (generated ASCII from src/SolAddressVisit_src.lua) -> <client dir>
  edits    SolAuthority.lua  A.FIXES += "book_visited", "book_hint"
           <Zomboid>/Lua/SolFixes_LAB.txt  book_visited=on, book_hint=on (only when missing)
No line of any other file is edited: SolAddressVisit.lua wraps SolAddressBook.sees, ISReadABook.displayPrintMedia, ISMap.initMapData
and SolAddressTarget.target at runtime, each once (see its header). It loads after SolAddressBook / SolAddressPlaces / SolAddressTarget
(file name order) and works with or without s84; with s82 absent A5 is simply not there.
Needs (installed in the lab): SolAddressBook.lua (address_book). Uses SolAddressTarget.lua (s82) + SolStaticRoads.lua for A5.
usage: apply_s89_address_visit.py <client dir>
       apply_s89_address_visit.py --gen          regenerate SolAddressVisit.lua from src (Arabic -> \\uXXXX)"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIXES = (("book_visited", "a stash row is marked visited by itself when she gets there"),
         ("book_hint", "a paper he opened while she was far: she asks to see it when she is beside him"))
NAME = "SolAddressVisit.lua"


def gen():
    src = open(os.path.join(HERE, "src", "SolAddressVisit_src.lua"), encoding="utf-8").read()
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
    for need in ("SolAuthority.lua", "SolAddressBook.lua"):
        assert os.path.isfile(os.path.join(cl, need)), "not a Sol client dir with %s: %s" % (need, cl)
    src = os.path.join(HERE, NAME)
    body = open(src, encoding="ascii").read()
    assert 'M.VERSION = "0.1.0"' in body and "SolAddressVisit" in body
    dst = os.path.join(cl, NAME)
    if os.path.exists(dst) and open(dst, encoding="ascii").read() == body: print("kept", NAME)
    else: shutil.copy(src, dst); print("copied", NAME)
    auth = os.path.join(cl, "SolAuthority.lua")
    for fix, why in FIXES:
        print("SolAuthority", fix, edit(auth, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",     -- %s' % (fix, why) + NL, '"%s"' % fix))
    fixfile = os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
    if os.path.exists(fixfile):
        for fix, _ in FIXES:
            have = open(fixfile, encoding="utf-8").read()
            if fix + "=" not in have:
                with open(fixfile, "a", encoding="utf-8", newline="") as h:
                    if have and not have.endswith(NL): h.write(CRLF)
                    h.write(fix + "=on" + CRLF)
                print("SolFixes_LAB", fix + "=on")


if __name__ == "__main__":
    if sys.argv[1:] == ["--gen"]: gen()
    else:
        client(sys.argv[1])
        print("s89 address_visit applied")
