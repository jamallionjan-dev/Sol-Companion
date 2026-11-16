-- SolWardrobe.lua - switch wardrobe (2026-11-15, s156). Sol's dressing room: clothes and hair, with a live preview.
-- GENERATED from SolWardrobe.src.lua by build_s156_wardrobe.py (Arabic text -> \u escapes; the game keeps only ASCII).
-- Jamal 2026-11-15: a box in her window (status) to change her clothes to ANY clothing in the game (vanilla or a clothing
-- mod) and her hair; a drop-down that does not stutter however many items there are; she is shown in the window and a
-- chosen piece is on her at once; a list per part, each with its own "apply" and "back, no change" (v0.2.0, after his first
-- run: he could not leave a list without keeping a piece, armor had no list, a piece on trial stayed after closing);
-- zoom in and out; Sol's theme. Clothes are created when she does not have them; what she takes off stays in her bag.
--
-- How it works
--   catalog   every item script with a body location and a clothing item (ScriptManager getAllItems), sorted into the
--             parts by its body location; built ONCE per game session, a few milliseconds per frame (CAT_SLICE_MS) while
--             the window is open, then each part's list is sorted by name the first time it is opened, a bucket a frame.
--             Hair: HairStyles getAllFemaleStyles (her own styles from the mod's hairStyles.xml are among them).
--   list      one virtual list: only the rows inside the box are drawn; the search box filters by name or item id.
--   preview   the game's own character view (ISUI3DModel -> UI3DModel.setCharacter) shows the REAL Sol, so her own body
--             and the fitting done by the body patch are what he sees. That view reads the character live, so a preview
--             is worn by her for real, as a TRIAL: closing the window or choosing another piece puts back what she wore.
--             Apply keeps it. Nothing of hers is ever deleted: only trial pieces this window created are removed again.
--   wearing   inventory:AddItem(fullType) -> character:setWornItem(item:getBodyLocation(), item) (SolDress.lua:59-78);
--             the game takes off what cannot be worn with it; those pieces stay in her bag and are worn again when a trial
--             is taken back. Hair: HumanVisual:setHairModel; resetModelNextFrame after every change.
-- Java calls (javap 42.22.2): ScriptManager getAllItems; Item getBodyLocation/getClothingItem/getDisplayName/getFullName/
-- getObsolete/isHidden; IsoGameCharacter getWornItems/setWornItem(ItemBodyLocation, InventoryItem)/removeWornItem(
-- InventoryItem)/getInventory/getHumanVisual/resetModelNextFrame; WornItems size/get(int); WornItem getItem/getLocation;
-- ItemContainer AddItem(String)/Remove(InventoryItem)/contains(InventoryItem); HairStyles getAllFemaleStyles; HairStyle
-- getName/isNoChoose; HumanVisual getHairModel/setHairModel(String); UI3DModel setCharacter/setState/setDirection/
-- setIsometric/setZoom/setYOffset. No boolean argument to any overloaded Java call.
-- Switch wardrobe read at call time (SolAuthority.on). Off: no tab, no window.
require "ISUI/ISPanel"
require "ISUI/ISUI3DModel"
require "ISUI/ISTextEntryBox"
require "SolText"
require "SolTheme"
require "SolPages"

SolUI = SolUI or {}
local U = SolUI
local T = SolText
SolWardrobe = SolWardrobe or {}
local WD = SolWardrobe
WD.VERSION = "0.5.0"
WD.CAT_SLICE_MS = 3
WD.SORT_BUCKET = 400
WD.ROW_H = 30
WD.ZOOM_MIN, WD.ZOOM_MAX, WD.ZOOM_STEP = 0, 30, 3
WD.PAN_STEP = 0.08

local W, H, HEAD = 880, 664, 56
local PV = { 16, 66, 300, 470 }                 -- the preview box
local RX, RW = 332, 532                         -- the right column
local ROW_Y, ROW_GAP = 70, 38
local TEX = "media/textures/SolUI/"

-- ---------------------------------------------------------------- words (Arabic first, English when her window is English)
local AR = {
    title = "\\u062E\\u0632\\u0627\\u0646\\u0629 \\u0633\\u0648\\u0644", back = "\\u0631\\u062C\\u0648\\u0639", tab = "\\u0627\\u0644\\u0644\\u0628\\u0633 \\u0648\\u0627\\u0644\\u0634\\u0639\\u0631",
    apply = "\\u0637\\u0628\\u0651\\u0642", applied = "\\u062A\\u0645", none = "\\u0628\\u062F\\u0648\\u0646 \\u0634\\u064A (\\u0634\\u064A\\u0644\\u064A \\u064A\\u0644\\u064A \\u0644\\u0627\\u0628\\u0633\\u062A\\u0648 \\u0647\\u0648\\u0646)", cancel = "\\u0631\\u062C\\u0648\\u0639 \\u0628\\u062F\\u0648\\u0646 \\u062A\\u063A\\u064A\\u064A\\u0631",
    pick = "\\u0627\\u0643\\u0628\\u0633 \\u0639\\u0644\\u0649 \\u0642\\u0637\\u0639\\u0629 \\u0623\\u0648 \\u062A\\u0646\\u0642\\u0651\\u0644 \\u0628\\u0627\\u0644\\u0623\\u0633\\u0647\\u0645 \\u0641\\u0648\\u0642 \\u0648\\u062A\\u062D\\u062A. Enter \\u0623\\u0648 \\u0637\\u0628\\u0651\\u0642 \\u0628\\u064A\\u062B\\u0628\\u062A\\u0647\\u0627\\u060C \\u0648\\u0631\\u062C\\u0648\\u0639 \\u0628\\u064A\\u0631\\u062C\\u0651\\u0639 \\u064A\\u0644\\u064A \\u0643\\u0627\\u0646\\u062A \\u0644\\u0627\\u0628\\u0633\\u062A\\u0648",
    search = "\\u0627\\u0643\\u062A\\u0628 \\u0644\\u0644\\u0628\\u062D\\u062B \\u0628\\u0627\\u0644\\u0627\\u0633\\u0645", loading = "\\u0639\\u0645 \\u062D\\u0636\\u0651\\u0631 \\u0642\\u0627\\u0626\\u0645\\u0629 \\u0627\\u0644\\u0644\\u0628\\u0633", count = "\\u0642\\u0637\\u0639\\u0629",
    nothing = "\\u0645\\u0627 \\u0641\\u064A \\u0634\\u064A", worn = "\\u0644\\u0627\\u0628\\u0633\\u0629 \\u0647\\u0644\\u0642", trial = "\\u062A\\u062C\\u0631\\u0628\\u0629\\u060C \\u0644\\u0633\\u0627 \\u0645\\u0627 \\u0627\\u0646\\u0637\\u0628\\u0642\\u062A",
    hint = "\\u0627\\u0633\\u062D\\u0628 \\u0628\\u0627\\u0644\\u0645\\u0627\\u0648\\u0633 \\u0644\\u062A\\u062F\\u0648\\u0651\\u0631\\u0647\\u0627\\u060C \\u0648\\u0627\\u0644\\u0639\\u062C\\u0644\\u0629 \\u0644\\u0644\\u062A\\u0642\\u0631\\u064A\\u0628",
    strip = "\\u0634\\u064A\\u0644\\u064A \\u0643\\u0644 \\u0627\\u0644\\u0644\\u0628\\u0633", dress = "\\u0631\\u062C\\u0651\\u0639\\u064A \\u0627\\u0644\\u0644\\u0628\\u0633 \\u064A\\u0644\\u064A \\u0627\\u0646\\u0634\\u0627\\u0644",
    no_sol = "\\u0633\\u0648\\u0644 \\u0645\\u0634 \\u0645\\u0648\\u062C\\u0648\\u062F\\u0629 \\u0647\\u0644\\u0642",
    top = "\\u0627\\u0644\\u0643\\u0646\\u0632\\u0629 \\u0623\\u0648 \\u0627\\u0644\\u0642\\u0645\\u064A\\u0635", jacket = "\\u0627\\u0644\\u062C\\u0627\\u0643\\u064A\\u062A", bottom = "\\u0627\\u0644\\u0628\\u0646\\u0637\\u0627\\u0644 \\u0623\\u0648 \\u0627\\u0644\\u062A\\u0646\\u0648\\u0631\\u0629", dress = "\\u0627\\u0644\\u0641\\u0633\\u062A\\u0627\\u0646 \\u0623\\u0648 \\u0627\\u0644\\u0637\\u0642\\u0645",
    shoes = "\\u0627\\u0644\\u062D\\u0630\\u0627\\u0621", head = "\\u0627\\u0644\\u0642\\u0628\\u0639\\u0629 \\u0623\\u0648 \\u0627\\u0644\\u062E\\u0648\\u0630\\u0629", armor = "\\u0627\\u0644\\u062F\\u0631\\u0648\\u0639 \\u0648\\u0645\\u0636\\u0627\\u062F \\u0627\\u0644\\u0631\\u0635\\u0627\\u0635", vest = "\\u0627\\u0644\\u0635\\u062F\\u0631\\u064A\\u0629 \\u0648\\u0627\\u0644\\u062C\\u0639\\u0628\\u0629",
    face = "\\u0627\\u0644\\u0648\\u062C\\u0647: \\u0646\\u0636\\u0627\\u0631\\u0627\\u062A \\u0648\\u0623\\u0642\\u0646\\u0639\\u0629", neck = "\\u0627\\u0644\\u0631\\u0642\\u0628\\u0629: \\u0634\\u0627\\u0644 \\u0648\\u0639\\u0642\\u062F", hands = "\\u0627\\u0644\\u0625\\u064A\\u062F\\u064A\\u0646: \\u0643\\u0641\\u0648\\u0641 \\u0648\\u0633\\u0627\\u0639\\u0627\\u062A",
    belt = "\\u0627\\u0644\\u062E\\u0635\\u0631 \\u0648\\u0627\\u0644\\u0634\\u0646\\u0637", under = "\\u062F\\u0627\\u062E\\u0644\\u064A \\u0648\\u062C\\u0631\\u0627\\u0628\\u0627\\u062A", other = "\\u063A\\u064A\\u0631 \\u0634\\u064A", hair = "\\u0627\\u0644\\u0634\\u0639\\u0631",
}
local EN = {
    title = "Sol's wardrobe", back = "Back", tab = "Clothes & hair",
    apply = "Apply", applied = "Done", none = "Nothing (take off what she wears here)", cancel = "Back, no change",
    pick = "Click a piece or move with the Up and Down arrows. Enter or Apply keeps it, Back puts her own piece on again",
    search = "type to search by name", loading = "preparing the clothing list", count = "items",
    nothing = "nothing", worn = "wearing now", trial = "trial, not applied yet",
    hint = "drag to turn her, wheel to zoom",
    strip = "Take everything off", dress = "Put it back on",
    no_sol = "Sol is not here now",
    top = "Top or shirt", jacket = "Jacket", bottom = "Trousers or skirt", dress = "Dress or suit",
    shoes = "Shoes", head = "Hat or helmet", armor = "Armor and bullet vests", vest = "Vest and webbing",
    face = "Face: glasses and masks", neck = "Neck: scarf and necklace", hands = "Hands: gloves and watches",
    belt = "Waist and bags", under = "Underwear and socks", other = "Other", hair = "Hair",
}
local function isAr() return not (U.lang and U.lang() == "en") end
local function word(k) local t = isAr() and AR or EN; return t[k] or EN[k] or k end
WD.word = word
WD.SLOTS = { "top", "jacket", "bottom", "dress", "shoes", "head", "armor", "vest", "face", "neck", "hands", "belt", "under", "other", "hair" }

-- ---------------------------------------------------------------- small helpers
local rawTonumber = tonumber
local function num(v) return rawTonumber(v) end
local function g(name) return rawget(_G, name) end
local function log(m) print("[SolWardrobe] " .. tostring(m)) end
local function nowMs() local f = g("getTimestampMs"); return f and f() or 0 end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function inside(x, y, r) return x >= r[1] and y >= r[2] and x < r[1] + r[3] and y < r[2] + r[4] end
local texCache = {}
local function tex(n)
    local t = texCache[n]
    if t == nil then local f = g("getTexture"); t = f and f(TEX .. n .. ".png") or false; texCache[n] = t end
    return t or nil
end
function WD.on()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("wardrobe") == true
end
local function actor() return U.solActor and U.solActor() or nil end

-- ---------------------------------------------------------------- which part of her a body location belongs to
local SKIP_LOC = { "bandage", "wound", "makeup", "tattoo", "zeddmg", "bloat", "ammostrap", "holster" }
function WD.slotOf(loc)
    local s = string.lower(tostring(loc or ""))
    s = string.gsub(s, "^.*:", ""); s = string.gsub(s, "[_%s]", "")
    if s == "" then return nil end
    for _, w in ipairs(SKIP_LOC) do if string.find(s, w, 1, true) then return nil end end
    local function has(w) return string.find(s, w, 1, true) ~= nil end
    local function any(list) for _, w in ipairs(list) do if has(w) then return true end end return false end
    -- every body location lands in a list; one nobody knows (a mod's) lands in "other". Order matters: "underwear" has
    -- "ear" in it, "shortsleeveshirt" has "short", "sweaterhat" has "hat".
    if any({ "underwear", "sock", "legs1", "torso1", "panties", "stocking", "tights" }) then return "under" end
    if any({ "cuirass", "gorget", "shoulderpad", "calf", "thigh", "forearm", "knee", "elbow", "codpiece", "gaiter", "vestbullet",
             "leftarm", "rightarm", "armor", "armour", "greave", "vambrace", "bracer", "shin" }) then return "armor" end
    if has("shoe") or has("boot") then return "shoes" end
    if any({ "dress", "fullsuit", "boilersuit", "robe", "fulltop", "onesie", "jumpsuit" }) then return "dress" end
    if has("jacket") or has("coat") then return "jacket" end
    if any({ "shirt", "tanktop", "sweater", "jersey", "blouse", "hoodie" }) then return "top" end
    if any({ "pants", "skirt", "short", "trouser", "legging" }) then return "bottom" end
    if any({ "torsoextra", "vest", "webbing", "apron" }) then return "vest" end
    if any({ "eye", "mask", "nose", "ear", "scba", "glasses", "face" }) then return "face" end
    if has("hat") or has("helmet") or has("head") then return "head" end
    if any({ "neck", "scarf" }) then return "neck" end
    if any({ "hand", "wrist", "finger", "glove", "bracelet", "watch" }) then return "hands" end
    if any({ "belt", "fannypack", "satchel", "back", "belly", "bag", "waist" }) then return "belt" end
    return "other"
end

-- ---------------------------------------------------------------- the catalog (built once, a slice a frame)
WD.cat = WD.cat or { state = "new", i = 0, n = 0, rows = {}, sorted = {}, count = 0 }
local function catReset()
    WD.cat = { state = "new", i = 0, n = 0, rows = {}, sorted = {}, count = 0 }
    for _, s in ipairs(WD.SLOTS) do WD.cat.rows[s] = {} end
end
local function addHair(c)
    local hs = g("getHairStylesInstance")
    local styles = hs and call(hs(), "getAllFemaleStyles") or nil
    local n = num((call(styles, "size"))) or 0
    local seen = {}
    for i = 0, n - 1 do
        local st = call(styles, "get", i)
        local name = st and call(st, "getName") or nil
        if type(name) == "string" and not seen[name] and call(st, "isNoChoose") ~= true then
            seen[name] = true
            local shown = name == "" and "Bald" or name
            c.rows.hair[#c.rows.hair + 1] = { full = name, name = shown, key = string.lower(shown) }
        end
    end
end
-- one item script -> a row, or nil
function WD.rowOf(it)
    if it == nil or call(it, "getObsolete") == true or call(it, "isHidden") == true then return nil end
    local loc = call(it, "getBodyLocation")
    if loc == nil then return nil end
    local ci = call(it, "getClothingItem")
    if ci == nil or tostring(ci) == "" then return nil end
    local slot = WD.slotOf(loc)
    if slot == nil then return nil end
    local full = call(it, "getFullName")
    if type(full) ~= "string" or full == "" then return nil end
    local name = call(it, "getDisplayName")
    if type(name) ~= "string" or name == "" then name = full end
    return { full = full, name = name, key = string.lower(name .. " " .. full) }, slot
end
function WD.catalogStep(budgetMs)
    local c = WD.cat
    if c.state == "done" then return true end
    if c.state == "new" then
        catReset(); c = WD.cat
        local f = g("getAllItems")
        c.items = f and f() or nil
        c.n = num((call(c.items, "size"))) or 0
        c.state = "items"
        pcall(addHair, c)
    end
    local stopAt = nowMs() + (budgetMs or WD.CAT_SLICE_MS)
    while c.i < c.n do
        local row, slot = WD.rowOf(call(c.items, "get", c.i))
        c.i = c.i + 1
        if row then c.rows[slot][#c.rows[slot] + 1] = row; c.count = c.count + 1 end
        if c.i % 40 == 0 and nowMs() >= stopAt then return false end
    end
    c.items = nil; c.state = "done"
    log("catalog ready: " .. tostring(c.count) .. " clothing items, " .. tostring(#c.rows.hair) .. " hair styles")
    return true
end
-- sort one part's list by name without a long frame: buckets by first letter, one bucket (or SORT_BUCKET rows) a frame
function WD.sortStep(slot)
    local c = WD.cat
    if c.sorted[slot] == true then return true end
    local job = c.sorted[slot]
    if job == nil then
        job = { buckets = {}, keys = {}, k = 1, out = {} }
        for _, r in ipairs(c.rows[slot]) do
            local b = string.sub(r.key, 1, 1)
            if job.buckets[b] == nil then job.buckets[b] = {}; job.keys[#job.keys + 1] = b end
            local t = job.buckets[b]; t[#t + 1] = r
        end
        table.sort(job.keys)
        c.sorted[slot] = job
        return false
    end
    local done = 0
    while job.k <= #job.keys and done < WD.SORT_BUCKET do
        local t = job.buckets[job.keys[job.k]]
        table.sort(t, function(a, b) return a.key < b.key end)
        for _, r in ipairs(t) do job.out[#job.out + 1] = r end
        done = done + #t; job.k = job.k + 1
    end
    if job.k > #job.keys then c.rows[slot] = job.out; c.sorted[slot] = true; return true end
    return false
end
function WD.filter(slot, query)
    local rows = WD.cat.rows[slot] or {}
    local q = string.lower(tostring(query or ""))
    q = string.gsub(q, "^%s+", ""); q = string.gsub(q, "%s+$", "")
    if q == "" then return rows end
    local out = {}
    for _, r in ipairs(rows) do if string.find(r.key, q, 1, true) then out[#out + 1] = r end end
    return out
end

-- ---------------------------------------------------------------- what she wears
function WD.worn(who)
    local out = {}
    local wi = call(who, "getWornItems")
    local n = num((call(wi, "size"))) or 0
    for i = 0, n - 1 do
        local w = call(wi, "get", i)
        local it = w and call(w, "getItem") or nil
        if it ~= nil then out[#out + 1] = { item = it, loc = call(w, "getLocation") } end
    end
    return out
end
local function wornSet(who)
    local set = {}
    for _, w in ipairs(WD.worn(who)) do set[w.item] = w.loc end
    return set
end
function WD.currentOf(who, slot)
    if slot == "hair" then return call(call(who, "getHumanVisual"), "getHairModel") end
    local names = {}
    for _, w in ipairs(WD.worn(who)) do
        if WD.slotOf(w.loc) == slot then names[#names + 1] = tostring(call(w.item, "getDisplayName") or call(w.item, "getFullType") or "?") end
    end
    if #names == 0 then return nil end
    return table.concat(names, " + ")
end
local function refreshLook(who)
    call(who, "resetModelNextFrame")
end

-- ---------------------------------------------------------------- trials: worn for the preview, taken back unless applied
-- WD.trial[slot] = { full, item (a piece this window created, nil for "none"), displaced = { { item, loc } ... } } or
-- for hair { hair = previous model }
WD.trial = WD.trial or {}
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
        if d.item ~= nil and d.loc ~= nil and call(inv, "contains", d.item) == true then
            pcall(function() who:setWornItem(d.loc, d.item) end)
        end
    end
end
-- take the trial of this part back: her own pieces return, the trial piece is removed
function WD.revert(who, slot)
    local t = WD.trial[slot]
    if t == nil then return false end
    WD.trial[slot] = nil
    if slot == "hair" then
        local hv = call(who, "getHumanVisual")
        if hv ~= nil and t.hair ~= nil then pcall(function() hv:setHairModel(t.hair) end) end
        refreshLook(who); return true
    end
    if t.item ~= nil then
        pcall(function() who:removeWornItem(t.item) end)
        local inv = call(who, "getInventory")
        if call(inv, "contains", t.item) == true then pcall(function() inv:Remove(t.item) end) end
    end
    rewear(who, t.displaced)
    refreshLook(who)
    return true
end
function WD.revertAll(who)
    local any = false
    for _, s in ipairs(WD.SLOTS) do if WD.revert(who, s) then any = true end end
    return any
end
-- try a piece on (row = nil: take the part off). Returns true when she now shows it.
function WD.try(who, slot, row)
    if who == nil then return false, "no_sol" end
    WD.revert(who, slot)
    if slot == "hair" then
        local hv = call(who, "getHumanVisual")
        if hv == nil or row == nil then return false, "no_visual" end
        local before = call(hv, "getHairModel")
        local ok = pcall(function() hv:setHairModel(row.full) end)
        if not ok then return false, "hair_failed" end
        WD.trial.hair = { full = row.full, hair = before }
        refreshLook(who); return true
    end
    local before = wornSet(who)
    local t = { full = row and row.full or nil, displaced = {} }
    if row == nil then
        for _, w in ipairs(WD.worn(who)) do
            if WD.slotOf(w.loc) == slot then
                pcall(function() who:removeWornItem(w.item) end)
                t.displaced[#t.displaced + 1] = { item = w.item, loc = w.loc }
            end
        end
        if #t.displaced == 0 then return false, "nothing_worn" end
    else
        local inv = call(who, "getInventory")
        local item = inv and call(inv, "AddItem", row.full) or nil
        if item == nil then return false, "cannot_create" end
        local loc = call(item, "getBodyLocation")
        local ok = loc ~= nil and pcall(function() who:setWornItem(loc, item) end)
        if not ok or wornSet(who)[item] == nil then
            pcall(function() inv:Remove(item) end)
            return false, "cannot_wear"
        end
        t.item = item
        local after = wornSet(who)
        for it, loc0 in pairs(before) do
            if after[it] == nil then
                -- a piece that left because of this one. A trial piece of another part: that trial ends, what it had
                -- displaced becomes this trial's to give back.
                local owner = nil
                for s, tr in pairs(WD.trial) do if tr.item == it then owner = s end end
                if owner ~= nil then
                    for _, d in ipairs(WD.trial[owner].displaced or {}) do t.displaced[#t.displaced + 1] = d end
                    WD.trial[owner] = nil
                    if call(inv, "contains", it) == true then pcall(function() inv:Remove(it) end) end
                else
                    t.displaced[#t.displaced + 1] = { item = it, loc = loc0 }
                end
            end
        end
    end
    WD.trial[slot] = t
    markTrial(who, t)
    refreshLook(who)
    return true
end
-- Her own loadout routine (SCLogistics selectOwnedClothingUpgrade) wears a garment from her bag when it scores above
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
    log("applied " .. slot .. ": " .. tostring(t.full or "none"))
    return true
end

-- ---------------------------------------------------------------- everything off, and back on
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
local Win = ISPanel:derive("SolWardrobeWindow")
WD.WindowClass = Win
function Win:new(x, y)
    local o = ISPanel:new(x, y, W, H)
    setmetatable(o, self); self.__index = self
    o.background = false
    o.open = nil            -- the part whose list is open
    o.scroll = 0; o.query = ""; o.rows = {}; o.hits = {}
    o.zoom = 0; o.pan = 0
    o.flash = {}
    o.sel = nil             -- the row the arrow keys stand on (1 = the first row of the open list)
    o.wantKeyEvents = true
    return o
end
function Win:createChildren()
    self.avatar = ISUI3DModel:new(PV[1] + 2, PV[2] + 2, PV[3] - 4, PV[4] - 4)
    self.avatar:initialise(); self.avatar:instantiate()
    self:addChild(self.avatar)
    pcall(function()
        self.avatar:setState("idle"); self.avatar:setDirection(IsoDirections.S); self.avatar:setIsometric(false)
    end)
    self.search = ISTextEntryBox:new("", RX + 8, ROW_Y + 44, RW - 16, 28)
    self.search:initialise(); self.search:instantiate()
    self.search.backgroundColor = { r = 0.03, g = 0.07, b = 0.11, a = 1 }
    self.search.borderColor = { r = 0.21, g = 0.35, b = 0.43, a = 1 }
    self:addChild(self.search)
    self.search:setVisible(false)
    -- the search box holds the keys while a list is open: its arrows walk the list, its Enter applies
    local win = self
    self.search.onPressDown = function() win:moveSel(1) end
    self.search.onPressUp = function() win:moveSel(-1) end
    self.search.onCommandEntered = function() win:applyOpen() end
end
-- the row at a place in the open list: false = the "nothing" row, a table = a piece, nil = outside
function Win:rowAt(idx)
    local slot = self.open
    if slot == nil then return nil end
    local rows = self:listRows()
    local extra = slot ~= "hair" and 1 or 0
    if idx < 1 or idx > #rows + extra then return nil end
    if extra == 1 and idx == 1 then return false end
    return rows[idx - extra]
end
function Win:pick(row)
    local who = actor()
    local slot = self.open
    if who == nil or slot == nil or row == nil then return false end
    local ok, why
    if row == false then ok, why = WD.try(who, slot, nil) else ok, why = WD.try(who, slot, row) end
    if not ok then log("could not show " .. tostring(row and row.full or "none") .. ": " .. tostring(why)) end
    self:showSol()
    return ok
end
-- arrow keys: d = 1 down, -1 up
function Win:moveSel(d)
    local slot = self.open
    if slot == nil then return false end
    local rows = self:listRows()
    local extra = slot ~= "hair" and 1 or 0
    local total = #rows + extra
    if total == 0 then return false end
    local at = self.sel
    if at == nil then
        -- start from the piece on trial when it is in this list, else from above the first row
        local t = WD.trial[slot]
        at = 0
        if t ~= nil and t.full ~= nil then
            for i, r in ipairs(rows) do if r.full == t.full then at = i + extra; break end end
        end
        if at == 0 and d < 0 then at = 2 end
    end
    at = math.max(1, math.min(total, at + d))
    self.sel = at
    local visible = self.visibleRows or 1
    local first = math.floor(self.scroll) + 1
    if at < first then self.scroll = at - 1
    elseif at > first + visible - 1 then self.scroll = at - visible end
    self:pick(self:rowAt(at))
    return true
end
function Win:applyOpen()
    local slot = self.open
    if slot == nil then return false end
    local who = actor()
    if WD.apply(who, slot) then self.flash[slot] = nowMs(); return true end
    return false
end
function Win:onKeyPress(key)
    if not self.open then return end
    local K = g("Keyboard")
    if K == nil then return end
    if key == K.KEY_DOWN then self:moveSel(1)
    elseif key == K.KEY_UP then self:moveSel(-1)
    elseif key == K.KEY_RETURN then self:applyOpen() end
end
function Win:isKeyConsumed(key)
    local K = g("Keyboard")
    return self.open ~= nil and K ~= nil and (key == K.KEY_DOWN or key == K.KEY_UP or key == K.KEY_RETURN)
end
function Win:showSol()
    local a = actor()
    if a ~= nil and self.avatar then
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
    self:applyView()
end
function Win:applyView()
    if not (self.avatar and self.avatar.javaObject) then return end
    pcall(function() self.avatar.javaObject:setZoom(self.zoom) end)
    pcall(function() self.avatar.javaObject:setYOffset(self.pan) end)
end
function Win:zoomBy(d)
    self.zoom = math.max(WD.ZOOM_MIN, math.min(WD.ZOOM_MAX, self.zoom + d)); self:applyView()
end
function Win:panBy(d) self.pan = math.max(-1.6, math.min(1.6, self.pan + d)); self:applyView() end
function Win:turn(step)
    pcall(function() self.avatar:setDirection(IsoDirectionSet.rotate(self.avatar:getDirection(), step)) end)
end

local function text(ui, s, x, y, w, scale, align, c, a)
    T.drawLine(ui, s, x, y, w, { scale = scale, align = align or "right", r = c and c[1] or 0.94, g = c and c[2] or 0.96, b = c and c[3] or 0.98, a = a or 1 })
end
-- a name cut to the width (kept per row and width)
local function fit(row, w, scale)
    local key = "fit" .. tostring(w)
    if row[key] then return row[key] end
    local s = tostring(row.name)
    if T.width(s, scale) > w then
        while string.len(s) > 4 and T.width(s .. "..", scale) > w do s = string.sub(s, 1, string.len(s) - 3) end
        s = s .. ".."
    end
    row[key] = s
    return s
end
local function button(ui, r, label, hover, enabled, scale)
    local t = tex("pg_btn")
    if t then ui:drawTextureScaled(t, r[1], r[2], r[3], r[4], enabled and 1 or 0.45, 1, 1, 1) end
    if hover and enabled then local h = tex("pg_btn_hover"); if h then ui:drawTextureScaled(h, r[1], r[2], r[3], r[4], 1, 1, 1, 1) end end
    text(ui, label, r[1] + 4, r[2] + math.floor((r[4] - 26) / 2), r[3] - 8, scale or 0.55, "center", nil, enabled and 1 or 0.5)
end

function Win:openList(slot)
    self.open = slot; self.scroll = 0; self.query = ""; self.filterKey = nil; self.sel = nil
    if self.search then self.search:setText(""); self.search:setVisible(true); pcall(function() self.search:focus() end) end
end
-- leave the open list. keep ~= true: the piece she is trying in this part is taken back (her own is on again).
function Win:closeList(keep)
    local slot = self.open
    if slot ~= nil and keep ~= true then
        local who = actor()
        if who ~= nil and WD.revert(who, slot) then self:showSol() end
    end
    self.open = nil
    if self.search then self.search:setVisible(false); pcall(function() self.search:unfocus() end) end
end
function Win:listRows()
    local slot = self.open
    if slot == nil then return {} end
    local q = self.search and self.search:getInternalText() or ""
    local key = slot .. "|" .. tostring(q) .. "|" .. tostring(WD.cat.state) .. "|" .. tostring(WD.cat.sorted[slot] == true) .. "|" .. tostring(#(WD.cat.rows[slot] or {}))
    if key ~= self.filterKey then
        self.filterKey = key; self.rows = WD.filter(slot, q)
        if q ~= self.query then self.query = q; self.scroll = 0; self.sel = nil end
    end
    return self.rows
end

function Win:prerender()
    if U.perfAdd then local t0 = nowMs(); self:prerenderBody(); U.perfAdd("wardrobe", nowMs() - t0); return end
    self:prerenderBody()
end
function Win:prerenderBody()
    -- the catalog and the open list's sort advance a little each frame
    if WD.cat.state ~= "done" then WD.catalogStep(WD.CAT_SLICE_MS)
    elseif self.open and self.open ~= "hair" and WD.cat.sorted[self.open] ~= true then WD.sortStep(self.open)
    elseif self.open == "hair" and WD.cat.sorted.hair ~= true then WD.sortStep("hair") end
    local c = SolTheme.c
    SolTheme.panel(self, 0, 0, W, H)
    local mx, my = self:getMouseX(), self:getMouseY()
    local over = self:isMouseOver()
    self.hits = {}
    -- header
    local back = { 16, 12, 110, 32 }
    local tb = tex("pg_back"); if tb then self:drawTextureScaled(tb, back[1], back[2], back[3], back[4], 1, 1, 1, 1) end
    text(self, word("back"), back[1], back[2] + 1, back[3], 0.5, "center")
    self.hits[#self.hits + 1] = { r = back, kind = self.open and "closeList" or "close" }
    text(self, word("title"), 140, 8, W - 160, 0.72, "right")
    -- preview box and its controls
    SolTheme.rounded(self, PV[1], PV[2], PV[3], PV[4], 8, c.bg, 1, c.line, 1)
    local by = PV[2] + PV[4] + 8
    local bw = 44
    local ctl = { { "-", "zoom", -WD.ZOOM_STEP }, { "+", "zoom", WD.ZOOM_STEP }, { "^", "pan", -WD.PAN_STEP }, { "v", "pan", WD.PAN_STEP }, { "<", "turn", -1 }, { ">", "turn", 1 } }
    for i, b in ipairs(ctl) do
        local r = { PV[1] + (i - 1) * (bw + 7), by, bw, 34 }
        button(self, r, b[1], over and inside(mx, my, r), true, 0.6)
        self.hits[#self.hits + 1] = { r = r, kind = b[2], d = b[3] }
    end
    text(self, word("hint"), PV[1], by + 40, PV[3], 0.42, "center", { 0.62, 0.72, 0.8 })
    local who = actor()
    if who == nil then text(self, word("no_sol"), RX, 200, RW, 0.6, "center", c.yellow); return end
    if self.open then self:drawList(mx, my, over, who)
    else
        self:drawParts(mx, my, over, who)
        local sr = { PV[1], by + 66, PV[3], 34 }
        local back = WD.lastStrip ~= nil
        button(self, sr, word(back and "dress" or "strip"), over and inside(mx, my, sr), true, 0.5)
        self.hits[#self.hits + 1] = { r = sr, kind = back and "dress" or "strip" }
    end
end

function Win:drawParts(mx, my, over, who)
    local LW = 196                                             -- the part's name, right of its box
    for i, slot in ipairs(WD.SLOTS) do
        local y = ROW_Y + (i - 1) * ROW_GAP
        local combo = { RX, y, RW - LW - 8, 32 }
        local hover = over and inside(mx, my, combo)
        text(self, word(slot), RX + RW - LW, y + 3, LW, 0.46, "right", { 0.42, 0.72, 1.0 })
        local tc = tex("pg_combo"); if tc then self:drawTextureScaled(tc, combo[1], combo[2], combo[3], combo[4], 1, 1, 1, 1) end
        if hover then local h = tex("pg_list_sel"); if h then self:drawTextureScaled(h, combo[1], combo[2], combo[3], combo[4], 0.35, 1, 1, 1) end end
        local shown = WD.currentOf(who, slot)
        if slot == "hair" and shown == "" then shown = "Bald" end
        if shown ~= nil then
            self.partFit = self.partFit or {}
            local cut = self.partFit[slot]
            if cut == nil or cut.name ~= shown then cut = { name = shown }; self.partFit[slot] = cut end
            shown = fit(cut, combo[3] - 52, 0.46)
        end
        text(self, shown or word("nothing"), combo[1] + 30, combo[2] + 4, combo[3] - 40, 0.46, "right", nil, shown and 1 or 0.5)
        self:drawText("v", combo[1] + 12, combo[2] + 8, 0.7, 0.78, 0.84, 1, UIFont.Small)
        self.hits[#self.hits + 1] = { r = combo, kind = "open", slot = slot }
    end
end

function Win:drawList(mx, my, over, who)
    local c = SolTheme.c
    local slot = self.open
    local top = ROW_Y
    text(self, word(slot), RX + 282, top + 2, RW - 282, 0.5, "right", { 0.42, 0.72, 1.0 })
    local doneR = { RX, top, 170, 32 }
    button(self, doneR, word("cancel"), over and inside(mx, my, doneR), true, 0.46)
    self.hits[#self.hits + 1] = { r = doneR, kind = "closeList" }
    local apR = { RX + 178, top, 96, 32 }
    local t = WD.trial[slot]
    local flash = self.flash[slot] and nowMs() - self.flash[slot] < 1500
    button(self, apR, flash and word("applied") or word("apply"), over and inside(mx, my, apR), t ~= nil, 0.52)
    if t ~= nil then self.hits[#self.hits + 1] = { r = apR, kind = "apply", slot = slot } end
    -- the list box under the search box
    local box = { RX, top + 80, RW, H - (top + 80) - 44 }
    self.listBox = box
    SolTheme.rounded(self, box[1], box[2], box[3], box[4], 6, c.bg, 1, c.line, 1)
    local rows = self:listRows()
    local extra = slot ~= "hair" and 1 or 0                    -- the "none" row
    local total = #rows + extra
    local visible = math.floor((box[4] - 8) / WD.ROW_H)
    self.visibleRows = visible
    local maxScroll = math.max(0, total - visible)
    if self.scroll > maxScroll then self.scroll = maxScroll end
    local first = math.floor(self.scroll) + 1
    local selTex = tex("pg_list_sel")
    for k = 0, visible - 1 do
        local idx = first + k
        if idx > total then break end
        local ry = box[2] + 4 + k * WD.ROW_H
        local r = { box[1] + 4, ry, box[3] - 14, WD.ROW_H }
        local row = nil
        if extra == 1 and idx == 1 then row = false else row = rows[idx - extra] end
        local isTrial = t ~= nil and ((row == false and t.full == nil) or (row and t.full == row.full))
        local hover = over and inside(mx, my, r)
        if (isTrial or hover) and selTex then self:drawTextureScaled(selTex, r[1], r[2], r[3], r[4], isTrial and 1 or 0.45, 1, 1, 1) end
        if row == false then text(self, word("none"), r[1] + 6, ry + 2, r[3] - 12, 0.5, "right", c.yellow)
        elseif row then text(self, fit(row, r[3] - 16, 0.5), r[1] + 6, ry + 2, r[3] - 12, 0.5, "left", isTrial and c.yellow or nil) end
        self.hits[#self.hits + 1] = { r = r, kind = "pick", slot = slot, row = row, idx = idx }
    end
    if maxScroll > 0 then
        local hh = math.max(24, box[4] * visible / total)
        self:drawRect(box[1] + box[3] - 6, box[2] + (box[4] - hh) * self.scroll / maxScroll, 3, hh, 0.8, 0.18, 0.64, 1)
    end
    local status
    if WD.cat.state ~= "done" then
        status = word("loading") .. " " .. tostring(math.floor(100 * WD.cat.i / math.max(1, WD.cat.n))) .. "%"
    else
        status = tostring(#rows) .. " " .. word("count")
    end
    text(self, status, RX, H - 36, 150, 0.44, "left", { 0.62, 0.72, 0.8 })
    text(self, word("pick"), RX + 150, H - 36, RW - 150, 0.4, "right", t and c.yellow or { 0.62, 0.72, 0.8 })
    if self.search and self.search:getInternalText() == "" then
        text(self, word("search"), RX + 12, top + 46, RW - 28, 0.44, "right", { 0.45, 0.55, 0.62 })
    end
end

function Win:onMouseWheel(del)
    local mx, my = self:getMouseX(), self:getMouseY()
    if inside(mx, my, PV) then self:zoomBy(del > 0 and -WD.ZOOM_STEP or WD.ZOOM_STEP); return true end
    if self.open and self.listBox and inside(mx, my, self.listBox) then
        self.scroll = math.max(0, self.scroll + (del > 0 and 3 or -3)); return true
    end
    return true
end
function Win:onMouseDown(x, y)
    if y < HEAD and x > 130 then self.dragging = true; self.dx, self.dy = x, y end
    return true
end
function Win:onMouseMove() if self.dragging then self:setX(self:getX() + self:getMouseX() - self.dx); self:setY(self:getY() + self:getMouseY() - self.dy) end end
function Win:onMouseMoveOutside() self:onMouseMove() end
function Win:onMouseUpOutside() self.dragging = false end
function Win:onMouseUp(x, y)
    if self.dragging then self.dragging = false; return true end
    local who = actor()
    for _, h in ipairs(self.hits or {}) do
        if inside(x, y, h.r) then
            if h.kind == "close" then WD.close(); return true
            elseif h.kind == "zoom" then self:zoomBy(h.d)
            elseif h.kind == "pan" then self:panBy(h.d)
            elseif h.kind == "turn" then self:turn(h.d)
            elseif h.kind == "strip" then WD.stripAll(who); self:showSol()
            elseif h.kind == "dress" then WD.dressBack(who); self:showSol()
            elseif h.kind == "open" then self:openList(h.slot)
            elseif h.kind == "closeList" then self:closeList()
            elseif h.kind == "apply" then
                if WD.apply(who, h.slot) then self.flash[h.slot] = nowMs() end
            elseif h.kind == "pick" then
                self.sel = h.idx
                self:pick(h.row)
                if self.search then pcall(function() self.search:focus() end) end     -- the arrows go on from here
            end
            return true
        end
    end
    return true
end

function WD.open()
    if not WD.on() then return false end
    if not WD.win then
        local core = getCore()
        local sw, sh = core:getScreenWidth(), core:getScreenHeight()
        WD.win = Win:new(math.max(0, math.floor((sw - W) / 2)), math.max(0, math.floor((sh - H) / 2)))
        WD.win:initialise(); WD.win:instantiate(); WD.win:addToUIManager()
    end
    WD.win:closeList(true)
    WD.win:setVisible(true); WD.win:bringToTop()
    WD.win:showSol()
    return true
end
function WD.close()
    local who = actor()
    if who ~= nil and WD.revertAll(who) then log("trials taken back on close") end
    if WD.win then WD.win:closeList(true); WD.win:setVisible(false) end
end
-- A trial lives only while its list is open in a visible window. Whatever way the window went (Escape, her window
-- closed, the UI hidden, a save), the trial is taken back. Jamal 2026-11-15: closed with a piece on trial, she kept it.
function WD.hasTrial()
    for _, s in ipairs(WD.SLOTS) do if WD.trial[s] ~= nil then return true end end
    return false
end
function WD.guard(force)
    if not WD.hasTrial() then return false end
    local w = WD.win
    local shown = w ~= nil and w.open ~= nil and call(w, "isVisible") == true and call(w, "isReallyVisible") ~= false
    if shown and force ~= true then return false end
    local who = actor()
    if who == nil then return false end
    WD.revertAll(who)
    if w ~= nil then w.open = nil; if w.search then pcall(function() w.search:setVisible(false) end) end end
    log("trial taken back (" .. (force == true and "save" or "window gone") .. ")")
    return true
end
if not WD.guardHooked then
    WD.guardHooked = true
    local n = 0
    local ev = g("Events")
    if ev and ev.OnTick then ev.OnTick.Add(function()
        n = n + 1
        if n % 15 == 0 then pcall(WD.guard) end
        if not WD.logisticsHooked and n % 120 == 0 then pcall(WD.hookLogistics) end       -- SCLogistics may load after this file
    end) end
    if ev and ev.OnSave then ev.OnSave.Add(function() pcall(WD.guard, true) end) end
end

-- ---------------------------------------------------------------- her window: one more tab under "status"
if not WD.hooked and type(U.pageTabs) == "function" and U.PageClass then
    WD.hooked = true
    local baseTabs = U.pageTabs
    function U.pageTabs()
        local out = baseTabs()
        if not WD.on() then return out end
        local at = #out + 1
        for i, tb in ipairs(out) do if tb.id == "status" then at = i + 1 end end
        table.insert(out, at, { id = "wardrobe", label = word("tab"), sol = true })
        return out
    end
    local baseRefresh = U.PageClass.refresh
    function U.PageClass:refresh(force, follow)
        if self.tab == "wardrobe" then
            self.tab = "status"
            if WD.on() then pcall(WD.open) end
        end
        return baseRefresh(self, force, follow)
    end
end
log("loaded v" .. WD.VERSION)
return WD
