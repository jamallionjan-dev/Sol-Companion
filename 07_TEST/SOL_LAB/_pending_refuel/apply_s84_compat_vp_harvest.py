"""s84 compat_vp_harvest: a compat guard in OUR mod for Viewpoint's interaction gather. Game side only; no Java, no third-party file.

Live 2026-11-10 23:05:59 / 23:06:01 (DebugLog 2026-11-10_21-26 lines 28345, 28482): "Lua(Vanilla).getShovel> Exception thrown
java.lang.NullPointerException: Cannot assign field callFrame because a is null at ReturnValues.put(ReturnValues.java:61)",
Lua stack getShovel(ISFarmingMenu.lua:134) <- doFarmingMenu2(:222) / doDigMenu(:142) <- createMenu(ISWorldObjectContextMenu.lua:209)
<- Viewpoint unseen(Viewpoint_Interact.lua:236) <- harvest(:256) <- PV QOL guardHarvest(ProjectViewpointQOL.lua:5633), Java
viewpoint.interact.LootActions.call <- InteractActions.gather <- LootMenu.snapshot <- FP.renderWorld <- IsoCell.render.
javap (projectzomboid.jar): LuaJavaInvoker.call(LuaCallFrame,int) line 181 prepareCall -> MethodArguments.get (static pool), 184 the
Java call (here ItemContainer.getFirstEvalRecurse, which calls the Lua predicate per item), 185 ReturnValues.put(args.getReturnValues()).
put(null) means the outer call's pooled MethodArguments was released (returnValues set to null) while still in use: the pool held it
twice. Neither Sol's Lua (cannot reach the pools) nor SolCombined.jar (no LuaCaller / LuaJavaInvoker / MethodArguments use; its
executor hands spawns back with MainThread.queueInvokeOnMainThread) can do that.
  copies   SolCompatVP.lua -> <client>/SolCompatVP.lua
  edits    SolAuthority.lua          A.FIXES += "compat_vp_harvest"
           <Zomboid>/Lua/SolFixes_LAB.txt  compat_vp_harvest=on (only when missing; only when the file exists)
Independent of s75..s83. Game closed only. In place, idempotent.
usage: apply_s84_compat_vp_harvest.py <client dir>"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "compat_vp_harvest"


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


def place(src_name, dst):
    body = open(os.path.join(HERE, src_name), "rb").read()
    body.decode("ascii")                                        # pure ASCII, like every Sol file
    if not os.path.exists(dst) or open(dst, "rb").read() != body:
        open(dst, "wb").write(body); return "copied"
    return "kept"


def client(cl):
    cl = os.path.abspath(cl)
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")) and os.path.isfile(os.path.join(cl, "SolActions.lua")), "not a Sol client dir: " + cl
    lua = open(os.path.join(HERE, "SolCompatVP.lua"), "rb").read()
    assert b'M.VERSION = "0.1.0"' in lua and b'A.on("compat_vp_harvest")' in lua
    print("SolCompatVP.lua", place("SolCompatVP.lua", os.path.join(cl, "SolCompatVP.lua")))
    print("SolAuthority", FIX, edit(os.path.join(cl, "SolAuthority.lua"), "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",' % FIX + NL, '"%s"' % FIX))
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
    print("s84_compat_vp_harvest applied")
