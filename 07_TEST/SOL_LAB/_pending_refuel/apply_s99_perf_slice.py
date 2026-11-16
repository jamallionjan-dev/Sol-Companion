"""s99 perf_slice: Sol's three single-frame spikes are spread over frames (about 4 ms a frame), same results.
Live 2026-11-11 (DebugLog 2026-11-11_11-13, SolPerf windows 11:44-11:50):
  world_scan 98-111ms/1 every 60 s  - that number is the SUM of the square slices plus the write; the one heavy frame is the
                                      finish + writeWorldRaw frame (vehicles, invCompact, encode of the whole snapshot, file):
                                      budget max 25-35 ms in the windows where world_scan ran alone.
  inventory ... max 39-40 ms        - one invStep = 150 squares or 8 whole containers; invStart also lists every base square at once.
  actions_catalog 62-72ms/1         - its own OnTick: two Living Fellows pages + the catalog + the JSON + the file in one frame.
perf_slice (read at call time; off = the old code paths):
  SolWorldScan.lua  the job is made in a frame of its own and both inventories are read by the first step; squares checked after every square; finish is a stepper (a vehicle a unit); writeWorldRaw's additions are
                    DECOR pieces (one unit each, same order); U.jsonEncodeJob encodes a value at a time (same text as encode);
                    the file last. perfAdd("world_scan") once a frame (max = the real frame cost); radius tuning keeps the old count.
  SolInventory.lua  invStart lists squares a column per unit ("plan" phase); squares one at a time; a container's items are listed
                    once when it is opened and read one at a time. U.invLast() still changes only when a scan finishes.
  SolActions.lua    a page a frame, then actionCatalog(pre), then U.jsonEncodeJob, then the file. U.writeActionCatalog (chat, spawn)
                    still writes at once and cancels a sliced one.
Edits: the three files (old/new blocks in s99_perf_slice/), SolAuthority.lua (A.FIXES += perf_slice),
<Zomboid>/Lua/SolFixes_LAB.txt (perf_slice=on when the file exists and has no line for it). Game closed only. Idempotent.
usage: apply_s99_perf_slice.py <client dir>"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
FRAG = os.path.join(HERE, "s99_perf_slice")
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "perf_slice"
EDITS = [
    ("SolWorldScan.lua", "ws_pre"), ("SolWorldScan.lua", "ws_finish"), ("SolWorldScan.lua", "ws_write"),
    ("SolInventory.lua", "inv_plan"), ("SolInventory.lua", "inv_squares"), ("SolInventory.lua", "inv_conts"),
    ("SolInventory.lua", "inv_step"), ("SolInventory.lua", "inv_tick"),
    ("SolActions.lua", "act_cat"), ("SolActions.lua", "act_write"), ("SolActions.lua", "act_tick"),
]


def frag(name, kind):
    t = open(os.path.join(FRAG, name + "." + kind + ".lua"), encoding="utf-8", newline="").read().replace(CRLF, NL)
    assert all(ord(c) < 128 for c in t), name + " is not ASCII"
    return t


def main(cl):
    cl = os.path.abspath(cl)
    ap = os.path.join(cl, "SolAuthority.lua")
    assert os.path.isfile(ap), "not a Sol client dir: " + cl
    # check every edit first, write nothing unless all of them fit
    texts, plan = {}, []
    for fn, name in EDITS:
        p = os.path.join(cl, fn)
        if p not in texts: texts[p] = open(p, encoding="utf-8", newline="").read()
        t = texts[p]
        nl = CRLF if CRLF in t else NL
        old, new = frag(name, "old").replace(NL, nl), frag(name, "new").replace(NL, nl)
        if new in t:
            plan.append((p, name, None, None))
            continue
        assert t.count(old) == 1, (fn, name, t.count(old))
        texts[p] = t.replace(old, new)
        plan.append((p, name, old, new))
    for p in sorted(set(x[0] for x in plan)):
        names = [x[1] for x in plan if x[0] == p]
        changed = [x[1] for x in plan if x[0] == p and x[2] is not None]
        if changed:
            open(p, "w", encoding="utf-8", newline="").write(texts[p])
            print("edited %s (%s)" % (os.path.basename(p), ",".join(changed)))
        else:
            print("kept " + os.path.basename(p))
    a = open(ap, encoding="utf-8", newline="").read()
    if '"%s"' % FIX in a:
        print("kept SolAuthority.lua")
    else:
        anl = CRLF if CRLF in a else NL
        old = "A.FIXES = {" + anl
        assert a.count(old) == 1
        a = a.replace(old, old + '    "%s",          -- s99: world scan, base inventory and action catalog work about 4 ms a frame' % FIX + anl)
        open(ap, "w", encoding="utf-8", newline="").write(a)
        print("edited SolAuthority.lua")
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
    print("s99 perf_slice applied")
