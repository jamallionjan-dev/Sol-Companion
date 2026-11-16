"""s156e: SolWardrobe.src.lua 0.3.1 -> 0.3.2. Jamal 2026-11-15 (screenshot): with modest_chest on, Sol in the world is
right, Sol in the wardrobe's preview still shows the uncovered chest.
Cause (javap, inference on the effect): the body patch treats a UI3DModel as "a preview of this player" only after
PlayerChoice.bindPlayerPreview(UI3DModel, SurvivorDesc, IsoPlayer) (exposed to Lua as LocalPlayerVSGirlChoice); its
preview code (PreviewSupport / CensorshipMode.previewPacket) works from that binding. The wardrobe only called
UI3DModel.setCharacter. Now it also binds the preview to her. Not overloaded, no boolean argument; inside pcall.
One-time source edit; "kept" when done. Then run apply_s156_wardrobe.py."""
import io, os
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "SolWardrobe.src.lua")
s = io.open(p, encoding="utf-8", newline="").read()
if 'WD.VERSION = "0.3.2"' in s:
    print("kept SolWardrobe.src.lua"); raise SystemExit(0)
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")


def rep(old, new):
    global s
    if s.count(old) != 1: raise SystemExit("count %d for: %s" % (s.count(old), old[:70]))
    s = s.replace(old, new)


rep('WD.VERSION = "0.3.1"', 'WD.VERSION = "0.3.2"')
rep('''    if a ~= nil and self.avatar then pcall(function() self.avatar:setCharacter(a) end) end
    self:applyView()''', '''    if a ~= nil and self.avatar then
        pcall(function() self.avatar:setCharacter(a) end)
        -- tell her body patch whose preview this is, so the preview gets what she gets in the world (covered chest)
        local choice = g("LocalPlayerVSGirlChoice")
        local view = self.avatar.javaObject
        if choice ~= nil and view ~= nil then
            local ok, err = pcall(function() choice.bindPlayerPreview(view, a:getDescriptor(), a) end)
            if not ok and not WD.bindWarned then WD.bindWarned = true; log("preview not bound to her body patch: " .. tostring(err)) end
            if ok and not WD.bindSaid then WD.bindSaid = true; log("preview bound to her body patch") end
        end
    end
    self:applyView()''')
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl))
print("edited SolWardrobe.src.lua")
