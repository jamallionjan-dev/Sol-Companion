"""s75 one-value: no Lua value list ever reaches Kahlua's tonumber again. Game closed only.
Kahlua's BaseLib.tonumber takes the safe path only with EXACTLY one argument; with two it does (String) arg1
(BaseLib.java:419), so tonumber(call(w, "getMaxAmmo")) crashed when call() returned `a, b` (2026-11-10, twice).
In place and idempotent (every edit is skipped when it is already there; anchors must match exactly, or nothing is written):
  1. SolSecretLoadout.lua: the staged file (call returns one value, its tonumber sites wrapped) is copied in.
  2. Helpers return ONE value where no caller uses a second one:
       call      SolFarWork SolFarmAct SolFarmKeeper SolFarmWork SolSort
       tcall     SolFarWork SolFarmKeeper SolFarmView SolFarmWork
       safeMethod SCUI SCUIBridge
     Kept two-value on purpose (callers read the 2nd value): SolBaseScan/SolGate call, SolWorldScan call,
     SCBaseVisuals safeMethod, SCGameplayUtil U.call, SCDiary guarded, SolFixLook callm, SCCombat medicalPressure.
  3. Every tonumber(X) whose last argument is a call -> tonumber((X)) (s75_onevalue_edits.json, made by build_s75_onevalue.py
     from the unpatched client: 848 sites in 95 files, plus the 5 in SolSecretLoadout.lua = 853).
Afterwards the whole dir must pass 05_TOOLS/sol_kahlua/tonumber_check.py (launch_lab.ps1 refuses with exit 7 otherwise).
usage: apply_s75_onevalue.py <client dir>"""
import json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua"))
import tonumber_check
NL, CRLF = chr(10), chr(13) + chr(10)

CALL_OLD = "    local ok, a, b = pcall(f, o, ...)\n    if ok then return a, b end\n"
CALL_NEW = "    local ok, a = pcall(f, o, ...)\n    if ok then return a end\n"
TCALL_OLD = "local ok, a, b = pcall(f, ...); if ok then return a, b end return nil end"
TCALL_NEW = "local ok, a = pcall(f, ...); if ok then return a end return nil end"
SAFE_OLD = ("    local ok, value, second = pcall(method, object, ...)\n    if not ok then\n        return nil\n    end\n"
            "    return value, second\nend\n")
SAFE_NEW = ("    local ok, value = pcall(method, object, ...)\n    if not ok then\n        return nil\n    end\n"
            "    return value\nend\n")
HELPERS = [(f, CALL_OLD, CALL_NEW) for f in ("SolFarWork.lua", "SolFarmAct.lua", "SolFarmKeeper.lua", "SolFarmWork.lua", "SolSort.lua")] \
        + [(f, TCALL_OLD, TCALL_NEW) for f in ("SolFarWork.lua", "SolFarmKeeper.lua", "SolFarmView.lua", "SolFarmWork.lua")] \
        + [(f, SAFE_OLD, SAFE_NEW) for f in ("SCUI.lua", "SCUIBridge.lua")]


def main(cl):
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")), "not a Sol client dir: " + cl
    texts, changed = {}, set()

    def text(name):
        if name not in texts:
            texts[name] = open(os.path.join(cl, name), encoding="utf-8", newline="").read()
        return texts[name]

    def edit(name, old, new, count=1, raw=False):
        t = text(name)
        if not raw:
            nl = CRLF if CRLF in t else NL
            old, new = old.replace(NL, nl), new.replace(NL, nl)
        if t.count(old) == 0 and t.count(new) >= count:
            return                                                    # already there
        assert t.count(old) == count, (name, "anchor found %d times, expected %d" % (t.count(old), count), old[:90])
        texts[name] = t.replace(old, new)
        changed.add(name)

    # 1 the staged SolSecretLoadout.lua (fixed call + wrapped tonumber); must itself be clean
    staged = os.path.join(HERE, "SolSecretLoadout.lua")
    s = open(staged, encoding="ascii", newline="").read()
    assert "local ok, a = pcall(f, o, ...)" in s and not tonumber_check.sites(staged, s), "staged SolSecretLoadout.lua is not the fixed one"
    # 2 helpers, 3 tonumber sites -- all checked in memory first
    for name, old, new in HELPERS:
        edit(name, old, new)
    edits = json.load(open(os.path.join(HERE, "s75_onevalue_edits.json"), encoding="utf-8"))
    for e in edits:
        if os.path.exists(os.path.join(cl, e["file"])):
            edit(e["file"], e["old"], e["new"], e["count"], raw=True)
        else:
            print("skip (no such file):", e["file"])
    for name in sorted(changed):                                      # every edited file still parses
        tonumber_check.tokenize(texts[name])
    # write
    dst = os.path.join(cl, "SolSecretLoadout.lua")
    if not os.path.exists(dst) or open(dst, encoding="utf-8", newline="").read() != s:
        shutil.copy(staged, dst)
        print("copied SolSecretLoadout.lua")
    for name in sorted(changed):
        with open(os.path.join(cl, name), "w", encoding="utf-8", newline="") as h:
            h.write(texts[name])
    print("s75 one-value: %d files changed" % len(changed))
    left = tonumber_check.check(cl)
    for l in left:
        print("  " + l)
    print("TONUMBER CHECK", "OK" if not left else "FOUND %d" % len(left))
    return 0 if not left else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1]))
