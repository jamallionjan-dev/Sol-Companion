"""s156d: SolWardrobe.src.lua 0.3.0 -> 0.3.1. The same loadout routine must not undo a TRIAL either: while a piece is on
trial it is marked like an applied one and what it displaced is set aside; taking the trial back restores the marks.
One-time source edit; "kept" when done. Then run apply_s156_wardrobe.py."""
import io, os
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "SolWardrobe.src.lua")
s = io.open(p, encoding="utf-8", newline="").read()
if 'WD.VERSION = "0.3.1"' in s:
    print("kept SolWardrobe.src.lua"); raise SystemExit(0)
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")


def rep(old, new):
    global s
    if s.count(old) != 1: raise SystemExit("count %d for: %s" % (s.count(old), old[:70]))
    s = s.replace(old, new)


rep('WD.VERSION = "0.3.0"', 'WD.VERSION = "0.3.1"')
# the mark helpers must exist before try/revert use them: forward declarations at the trial section
rep('''WD.trial = WD.trial or {}
local function rewear(who, list)
    local inv = call(who, "getInventory")
    for _, d in ipairs(list or {}) do
''', '''WD.trial = WD.trial or {}
-- marks while a piece is on trial (see WD.keep / WD.setAside below): what it displaced must not be worn again by her
-- loadout routine during the preview; taking the trial back gives each piece the mark it had.
local function markTrial(who, t)
    if WD.hookLogistics then WD.hookLogistics() end
    if t.item ~= nil and WD.keep then WD.keep(who, t.item) end
    for _, d in ipairs(t.displaced or {}) do
        local md = call(d.item, "getModData")
        if type(md) == "table" then
            if d.marks == nil then d.marks = { manual = md.SC_ManualWearFor or false, off = md.SolWardrobeOff or false } end
            if WD.setAside then WD.setAside(who, d.item) end
        end
    end
end
local function unmark(list)
    for _, d in ipairs(list or {}) do
        local md = call(d.item, "getModData")
        if type(md) == "table" and d.marks ~= nil then
            md.SC_ManualWearFor = d.marks.manual or nil
            md.SolWardrobeOff = d.marks.off or nil
        end
    end
end
local function rewear(who, list)
    local inv = call(who, "getInventory")
    unmark(list)
    for _, d in ipairs(list or {}) do
''')
rep('''    WD.trial[slot] = t
    refreshLook(who)
    return true
end''', '''    WD.trial[slot] = t
    markTrial(who, t)
    refreshLook(who)
    return true
end''')
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl))
print("edited SolWardrobe.src.lua")
