"""s86 book_memory, game side (card_check WARN "address-book places in her memory"). Her address book (ModData "Sol_AddressBook",
SolAddressBook.lua + s84 SolAddressPlaces.lua) never reached the Mind: the card's memory listed only the Mind's own places, so
"شو في عنا عناوين" / "وين <مكان>" could only run sol_address, and a "none" answer had nothing true to read. Now the world snapshot
carries a compact copy of the book ("solBook": group, name, town, distance in tiles and one of 8 directions from her; no
coordinates), read by apply_s86_book_memory_mind.py. Game closed only. In place and idempotent.

  copies   SolBookMemory.lua   -> <client dir>
  edits    SolWorldScan.lua    one anchor: snap.solBook = SolBookMemory.snapshot() (guarded) before the coverage line
           SolAuthority.lua    A.FIXES += "book_memory"
           <Zomboid>/Lua/SolFixes_LAB.txt  book_memory=on (only when missing)
Needs (installed in the lab): SolAddressBook.lua (address_book), SolWorldScan.lua. Uses SolAddressPlaces (s84) and SolHome when present.
usage: apply_s86_book_memory_lua.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "book_memory"
NAME = "SolBookMemory.lua"
ANCHOR = "    snap.coverage = { radius = RADIUS,"
DONE = "snap.solBook = "
BLOCK = ("    if type(SolBookMemory) == \"table\" and type(SolBookMemory.snapshot) == \"function\" then      -- book_memory: her address book, compact, for the Mind" + NL
         + "        local okBM, bm = pcall(SolBookMemory.snapshot)" + NL
         + "        if okBM then snap.solBook = bm end" + NL
         + "    end" + NL)


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


def client(cl):
    for need in ("SolAuthority.lua", "SolAddressBook.lua", "SolWorldScan.lua"):
        assert os.path.isfile(os.path.join(cl, need)), "not a Sol client dir with %s: %s" % (need, cl)
    src = os.path.join(HERE, NAME)
    body = open(src, encoding="ascii").read()                       # ASCII only (the game keeps the low 8 bits of anything else)
    assert 'M.VERSION = "0.1.0"' in body, NAME
    dst = os.path.join(cl, NAME)
    if os.path.exists(dst) and open(dst, encoding="ascii", errors="replace").read() == body: print("kept", NAME)
    else: shutil.copy(src, dst); print("copied", NAME)
    print("SolWorldScan", edit(os.path.join(cl, "SolWorldScan.lua"), ANCHOR, BLOCK + ANCHOR, DONE))
    print("SolAuthority", edit(os.path.join(cl, "SolAuthority.lua"), "A.FIXES = {" + NL,
          "A.FIXES = {" + NL + '    "%s",     -- her address book, compact, in the world snapshot for the Mind\'s memory' % FIX + NL, '"%s"' % FIX))
    fixfile = os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
    if os.path.exists(fixfile):
        have = open(fixfile, encoding="utf-8").read()
        if FIX + "=" not in have:
            with open(fixfile, "a", encoding="utf-8", newline="") as h:
                if have and not have.endswith(NL): h.write(CRLF)
                h.write(FIX + "=on" + CRLF)
            print("SolFixes_LAB", FIX + "=on")
        else: print("SolFixes_LAB kept")


if __name__ == "__main__":
    if len(sys.argv) != 2: print(__doc__); sys.exit(2)
    client(sys.argv[1])
    print("s86 book_memory (Lua) applied")
