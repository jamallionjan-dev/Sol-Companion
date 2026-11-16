"""s156c: SolWardrobe.src.lua 0.2.0 -> 0.3.0 after Jamal's second run (2026-11-15). One-time source edit; "kept" when done.
His words: every time he changed the jacket and went to change the top, the old jacket was back. The log: "applied jacket:
none" 9 times. Cause (confirmed in SCLogistics.lua): selectOwnedClothingUpgrade wears a garment from her bag whenever it
scores 8 points above what the location holds (an empty location = 0), so a piece the wardrobe took off was worn again.
- an applied piece is marked SC_ManualWearFor (the mod's own "he dressed her" mark: Logistics.clothingUpgrade leaves it on)
- pieces an applied choice took off are marked SolWardrobeOff; SC.Logistics.clothingUpgrade is wrapped: never an upgrade
- the armor list is named for the bullet vest too
Then run apply_s156_wardrobe.py."""
import io, os
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "SolWardrobe.src.lua")
s = io.open(p, encoding="utf-8", newline="").read()
if 'WD.VERSION = "0.3.0"' in s:
    print("kept SolWardrobe.src.lua"); raise SystemExit(0)
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")


def rep(old, new):
    global s
    if s.count(old) != 1: raise SystemExit("count %d for: %s" % (s.count(old), old[:70]))
    s = s.replace(old, new)


rep('WD.VERSION = "0.2.0"', 'WD.VERSION = "0.3.0"')
rep('armor = "الدروع والواقيات"', 'armor = "الدروع ومضاد الرصاص"')
rep('armor = "Armor and pads"', 'armor = "Armor and bullet vests"')
rep('''-- keep the trial: the piece is hers now; what it replaced stays in her bag
function WD.apply(who, slot)
    local t = WD.trial[slot]
    if t == nil then return false end
    WD.trial[slot] = nil
''', '''-- Her own loadout routine (SCLogistics selectOwnedClothingUpgrade) wears a garment from her bag when it scores above
-- what the location holds, an empty location included: a piece the wardrobe took off came back by itself.
-- SC_ManualWearFor is the mod's own mark for "he dressed her in this" (clothingUpgrade never replaces it while worn);
-- SolWardrobeOff marks a piece he took off here: never an upgrade until he puts it on her again.
local function idOf(who)
    local SC = g("SurvivorCompanion")
    local gu = SC and SC.GameplayUtil
    if gu and type(gu.idOf) == "function" then local ok, id = pcall(gu.idOf, who); if ok and id ~= nil then return id end end
    local md = call(who, "getModData")
    return type(md) == "table" and md.SC_Id or "sol"
end
WD.idOf = idOf
function WD.keep(who, item)
    local md = call(item, "getModData")
    if type(md) ~= "table" then return end
    md.SC_ManualWearFor = idOf(who); md.SolWardrobeOff = nil
end
function WD.setAside(who, item)
    local md = call(item, "getModData")
    if type(md) ~= "table" then return end
    md.SolWardrobeOff = idOf(who)
    if md.SC_ManualWearFor ~= nil then md.SC_ManualWearFor = nil end
end
function WD.isAside(who, item)
    local md = call(item, "getModData")
    return type(md) == "table" and md.SolWardrobeOff ~= nil and md.SolWardrobeOff == idOf(who)
end
function WD.hookLogistics()
    if WD.logisticsHooked then return true end
    local SC = g("SurvivorCompanion")
    local L = SC and SC.Logistics
    if type(L) ~= "table" or type(L.clothingUpgrade) ~= "function" then return false end
    WD.logisticsHooked = true
    local base = L.clothingUpgrade
    L.clothingUpgrade = function(actor, item)
        local a, b, c, d = base(actor, item)
        if a == true and WD.on() and WD.isAside(actor, item) then return false, 0, c, d end
        return a, b, c, d
    end
    log("her loadout routine leaves alone what the wardrobe took off")
    return true
end
-- keep the trial: the piece is hers now; what it replaced stays in her bag
function WD.apply(who, slot)
    local t = WD.trial[slot]
    if t == nil then return false end
    WD.trial[slot] = nil
    if slot ~= "hair" then
        WD.hookLogistics()
        if t.item ~= nil then WD.keep(who, t.item) end
        for _, d in ipairs(t.displaced or {}) do if d.item ~= nil then WD.setAside(who, d.item) end end
        local te = g("triggerEvent"); if type(te) == "function" then pcall(te, "OnClothingUpdated", who) end
    end
''')
rep('''if not WD.guardHooked then
    WD.guardHooked = true
    local n = 0
    local ev = g("Events")
    if ev and ev.OnTick then ev.OnTick.Add(function() n = n + 1; if n % 15 == 0 then pcall(WD.guard) end end) end''',
    '''if not WD.guardHooked then
    WD.guardHooked = true
    local n = 0
    local ev = g("Events")
    if ev and ev.OnTick then ev.OnTick.Add(function()
        n = n + 1
        if n % 15 == 0 then pcall(WD.guard) end
        if not WD.logisticsHooked and n % 120 == 0 then pcall(WD.hookLogistics) end       -- SCLogistics may load after this file
    end) end''')
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl))
print("edited SolWardrobe.src.lua")
