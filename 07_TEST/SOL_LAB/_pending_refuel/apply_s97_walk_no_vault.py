"""s97 walk_no_vault: calm walks take gaps, then doors, then windows; a fence only to flee danger (or when nothing else gets there).
Live 2026-11-11 (DebugLog 2026-11-11_10-19), the item sort at home:
  10:40:33.918 [SolPlace] route 7406,8249 -> 7402,8262: 21 steps, doors 2 windows 0 fences 0, 6 legs   (out through the porch gap)
  10:40:44.948 [SolDrive] LF command stay                                                             (she is at 7402,8262)
  10:40:46.735 [SolMoveCheck] jog, 12.0 tiles to go
  10:40:46.744 [SolDrive] solGoto(7406,8251) ... -> true walking_to 7406,8251   <- the goal itself, no "[SolPlace] route" line:
               SolPlace handed the whole walk to LF (M.go: M.danger(a) true -> M._orig; "direct" is ruled out, see the report)
  10:40:51.213 IsoFallingClothing added x=7406.197 y=8258.394                  <- she vaulted the railing jogging and fell
M.danger = any zombie within 7 tiles (any floor, seen or not); the same test switches off LF's fence surcharge (wrapTopology),
so LF's A* priced the railing at 2.5 and took it over the walk round through the gap.
The switch (read at call time) changes, in SolPlace.lua only, one block appended before "return M":
  M.danger -> M.flee while on (perceived zombie <= 7 tiles, or any zombie on her floor <= 2.5 tiles);
  M.crossCost: fence 500 while calm; M._finish: extra legs where an LF-priced probe would cut a stretch over a fence/window
  (never "direct" then); SC.Navigation._handleFenceForRequest refused for her while calm when a way round <= 30 steps exists
  (LF blacklists that fence edge and plans again); a calm climb start is logged.
Edits: SolPlace.lua (block), SolAuthority.lua (A.FIXES += walk_no_vault), <Zomboid>/Lua/SolFixes_LAB.txt (walk_no_vault=on when
the file exists and has no line for it). Applies on 0.2.0 with or without s85 and s96. Game closed only. In place, idempotent.
s97b (12:06-12:08 live, following him in past the porch): vanilla PathFindBehavior2 paths that LF starts itself
(SCNativeMovementActions.dispatch, intent.enginePath) are re-aimed at the gap or door while calm; an earlier s97 block is upgraded.
usage: apply_s97_walk_no_vault.py <client dir>"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "walk_no_vault"
MARK = "-- Sol fix walk_no_vault (s97)"
ANCHOR = "if Events and Events.OnGameStart then Events.OnGameStart.Add(function() pcall(M.install) end) end" + NL + "return M"


def main(cl):
    cl = os.path.abspath(cl)
    sp = os.path.join(cl, "SolPlace.lua")
    assert os.path.isfile(sp) and os.path.isfile(os.path.join(cl, "SolAuthority.lua")), "not a Sol client dir with SolPlace: " + cl
    t = open(sp, encoding="utf-8", newline="").read()
    assert 'M.VERSION = "0.2.0"' in t, "SolPlace.lua is not 0.2.0"
    nl = CRLF if CRLF in t else NL
    block = open(os.path.join(HERE, "s97_walk_no_vault_block.lua"), encoding="utf-8").read().replace(CRLF, NL)
    assert all(ord(c) < 128 for c in block), "block is not ASCII"
    assert block.startswith(MARK)
    if MARK in t:
        # an earlier s97 block (the 11:13 lab install): replaced by this one (s97b), from its first line to the final "return M"
        start = t.index(MARK)
        end = t.rindex(nl + "return M")
        new_block = block.rstrip(NL).replace(NL, nl)
        if t[start:end] == new_block:
            print("SolPlace.lua kept")
        else:
            t = t[:start] + new_block + t[end:]
            open(sp, "w", encoding="utf-8", newline="").write(t)
            print("SolPlace.lua block upgraded (s97b)")
    else:
        anchor = ANCHOR.replace(NL, nl)
        assert t.count(anchor) == 1, ("anchor", t.count(anchor))
        head, tail = anchor.split(nl)[0], "return M"
        new = head + nl + block.rstrip(NL).replace(NL, nl) + nl + tail
        t = t.replace(anchor, new)
        open(sp, "w", encoding="utf-8", newline="").write(t)
        print("SolPlace.lua edited")
    ap = os.path.join(cl, "SolAuthority.lua")
    a = open(ap, encoding="utf-8", newline="").read()
    if '"%s"' % FIX in a:
        print("SolAuthority kept")
    else:
        anl = CRLF if CRLF in a else NL
        old = "A.FIXES = {" + anl
        assert a.count(old) == 1
        a = a.replace(old, old + '    "%s",        -- s97: calm walks take gaps, doors, windows; a fence only to flee' % FIX + anl)
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
    print("s97 walk_no_vault applied")
