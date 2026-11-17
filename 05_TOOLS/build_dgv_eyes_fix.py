"""Builds a small LOCAL fix mod for "Viewpoint Eyes: HUD Interface & UI [B42.22 PATCH] byDGV" (DGVViewpointEyes4222Patch).
Jamal 2026-11-16: with Viewpoint alpha 0.1.7 the HUD mod throws, 4 times in his session:
    DGVE_Blocks.lua:314 coverRead: Object tried to call nil
Line 314 calls o:getAbsoluteX() / o:getAbsoluteY() on every element of UIManager.getUI(). One of the elements on the
screen now (inference: one of the new Viewpoint 0.1.7 screens) answers getWidth / isVisible but has no getAbsoluteX, so
the call is a call of nil and the whole HUD update for that block is lost for that frame.
The Workshop file is not touched (Steam would overwrite it, and it is not ours). Instead a local mod, loaded after the
HUD mod, carries a copy of that one file in which an element that cannot say where it is is skipped. The game takes the
later mod's file of the same path.
usage: build_dgv_eyes_fix.py          builds C:\\Users\\JAMAL\\Zomboid\\mods\\SolFixDGVEyes
If the author's file no longer has the line (he fixed it or rewrote it), nothing is built and the fix mod should be
switched off. Rebuild after every update of the HUD mod, otherwise the copy shadows the author's newer file."""
import hashlib, os, sys
SRC = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\108600\3838246684\mods\DGVViewpointEyes\42\media\lua\client\DGVE_Blocks.lua"
OUT = r"C:\Users\JAMAL\Zomboid\mods\SolFixDGVEyes"
OLD = "                r.i, r.x, r.y, r.w, r.h, r.o = i, o:getAbsoluteX(), o:getAbsoluteY(), w, h, o"
NEW = ("                -- SolFixDGVEyes: an element that cannot say where it is (no getAbsoluteX) is not counted as cover\n"
       "                -- (asked first: a pcall'd error is still written to the log with its whole stack, every frame)\n"
       "                local okAbs, ax, ay = false, nil, nil\n"
       "                if o.getAbsoluteX ~= nil and o.getAbsoluteY ~= nil then\n"
       "                    okAbs, ax, ay = pcall(function() return o:getAbsoluteX(), o:getAbsoluteY() end)\n"
       "                end\n"
       "                if okAbs and ax ~= nil and ay ~= nil then\n"
       "                    r.i, r.x, r.y, r.w, r.h, r.o = i, ax, ay, w, h, o\n"
       "                else\n"
       "                    n = n - 1\n"
       "                end")
raw = open(SRC, "rb").read()
text = raw.decode("utf-8")
nl = "\r\n" if "\r\n" in text else "\n"
body = text.replace("\r\n", "\n")
if body.count(OLD) != 1:
    sys.exit("the author's file no longer has that line (%d found): he changed it. Switch SolFixDGVEyes off and test without it." % body.count(OLD))
fixed = body.replace(OLD, NEW).replace("\n", nl)
lua_dir = os.path.join(OUT, "42", "media", "lua", "client")
os.makedirs(lua_dir, exist_ok=True)
open(os.path.join(lua_dir, "DGVE_Blocks.lua"), "w", encoding="utf-8", newline="").write(fixed)
info = "\n".join([
    "name=Sol fix: Viewpoint Eyes HUD with Viewpoint 0.1.7",
    "id=SolFixDGVEyes",
    "modversion=1",
    "versionMin=42.22",
    "require=\\DGVViewpointEyes4222Patch",
    "loadModAfter=\\DGVViewpointEyes4222Patch",
    "author=Jamal (local)",
    "description=Local fix. One file of the HUD mod (DGVE_Blocks.lua) with one guarded call, so a screen element without a position no longer throws in coverRead. Built from the author's file " + hashlib.sha256(raw).hexdigest()[:12] + ". Rebuild or switch off after the HUD mod updates.",
    ""])
open(os.path.join(OUT, "42", "mod.info"), "w", encoding="utf-8", newline="\n").write(info)
print("built", OUT)
print("from the author's file sha256", hashlib.sha256(raw).hexdigest()[:12], "| lines:", body.count("\n"), "->", fixed.replace("\r\n", "\n").count("\n"))
