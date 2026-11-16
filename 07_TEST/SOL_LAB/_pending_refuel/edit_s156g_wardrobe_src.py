"""s156g: SolWardrobe.src.lua 0.4.0 -> 0.5.0. Jamal 2026-11-15: a button that takes ALL her clothes off.
- "take everything off": every worn clothing piece (underwear too) goes to her bag and is set aside so her loadout
  routine does not wear it again. Bags and other containers stay on her (they carry her things), bandages/wounds too.
- the same button then reads "put it back on": what the last strip took off is worn again (nothing is ever deleted).
One-time source edit; "kept" when done. Then run apply_s156_wardrobe.py."""
import io, os
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "SolWardrobe.src.lua")
s = io.open(p, encoding="utf-8", newline="").read()
if 'WD.VERSION = "0.5.0"' in s:
    print("kept SolWardrobe.src.lua"); raise SystemExit(0)
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")


def rep(old, new):
    global s
    if s.count(old) != 1: raise SystemExit("count %d for: %s" % (s.count(old), old[:70]))
    s = s.replace(old, new)


rep('WD.VERSION = "0.4.0"', 'WD.VERSION = "0.5.0"')
rep('''    hint = "اسحب بالماوس لتدوّرها، والعجلة للتقريب",''',
    '''    hint = "اسحب بالماوس لتدوّرها، والعجلة للتقريب",
    strip = "شيلي كل اللبس", dress = "رجّعي اللبس يلي انشال",''')
rep('''    hint = "drag to turn her, wheel to zoom",''',
    '''    hint = "drag to turn her, wheel to zoom",
    strip = "Take everything off", dress = "Put it back on",''')
rep('''-- ---------------------------------------------------------------- the window
local Win = ISPanel:derive("SolWardrobeWindow")''', '''-- ---------------------------------------------------------------- everything off, and back on
local function isContainer(item) return call(item, "getInventory") ~= nil or call(item, "getItemContainer") ~= nil end
-- every worn clothing piece goes to her bag (bags stay on her). Returns how many pieces came off.
function WD.stripAll(who)
    if who == nil then return 0 end
    WD.revertAll(who)
    WD.hookLogistics()
    local off = {}
    for _, w in ipairs(WD.worn(who)) do
        if WD.slotOf(w.loc) ~= nil and not isContainer(w.item) then
            local ok = pcall(function() who:removeWornItem(w.item) end)
            if ok then
                local md = call(w.item, "getModData")
                off[#off + 1] = { item = w.item, loc = w.loc, manual = type(md) == "table" and md.SC_ManualWearFor or nil }
                WD.setAside(who, w.item)
            end
        end
    end
    if #off > 0 then
        WD.lastStrip = off
        local te = g("triggerEvent"); if type(te) == "function" then pcall(te, "OnClothingUpdated", who) end
        refreshLook(who)
        log("everything off: " .. tostring(#off) .. " pieces, all in her bag")
    end
    return #off
end
-- what the last strip took off is worn again (a piece he gave away or she no longer has is skipped)
function WD.dressBack(who)
    local list = WD.lastStrip
    if who == nil or list == nil then return 0 end
    WD.lastStrip = nil
    local inv = call(who, "getInventory")
    local n = 0
    for _, d in ipairs(list) do
        if d.item ~= nil and d.loc ~= nil and call(inv, "contains", d.item) == true and wornSet(who)[d.item] == nil then
            local md = call(d.item, "getModData")
            if type(md) == "table" then md.SolWardrobeOff = nil; md.SC_ManualWearFor = d.manual or idOf(who) end
            if pcall(function() who:setWornItem(d.loc, d.item) end) and wornSet(who)[d.item] ~= nil then n = n + 1 end
        end
    end
    local te = g("triggerEvent"); if type(te) == "function" then pcall(te, "OnClothingUpdated", who) end
    refreshLook(who)
    log("put back on: " .. tostring(n) .. " of " .. tostring(#list) .. " pieces")
    return n
end

-- ---------------------------------------------------------------- the window
local Win = ISPanel:derive("SolWardrobeWindow")''')
# the button under the preview, on the parts page only
rep('''    if self.open then self:drawList(mx, my, over, who) else self:drawParts(mx, my, over, who) end
end''', '''    if self.open then self:drawList(mx, my, over, who)
    else
        self:drawParts(mx, my, over, who)
        local sr = { PV[1], by + 66, PV[3], 34 }
        local back = WD.lastStrip ~= nil
        button(self, sr, word(back and "dress" or "strip"), over and inside(mx, my, sr), true, 0.5)
        self.hits[#self.hits + 1] = { r = sr, kind = back and "dress" or "strip" }
    end
end''')
rep('''            elseif h.kind == "open" then self:openList(h.slot)''', '''            elseif h.kind == "strip" then WD.stripAll(who); self:showSol()
            elseif h.kind == "dress" then WD.dressBack(who); self:showSol()
            elseif h.kind == "open" then self:openList(h.slot)''')
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl))
print("edited SolWardrobe.src.lua")
