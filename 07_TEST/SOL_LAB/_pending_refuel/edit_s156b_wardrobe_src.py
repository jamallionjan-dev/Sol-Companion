"""s156b: SolWardrobe.src.lua 0.1.0 -> 0.2.0 after Jamal's first run (2026-11-15). One-time source edit; "kept" when done.
- a list can be left without keeping a piece ("back, no change"); the header's back leaves the list first
- a list for every wearable part (armor, vest, face, neck, hands, waist/bags, underwear), nothing without a list
- a piece on trial is taken back whatever way the window went (tick guard, save)
Then run apply_s156_wardrobe.py to build and install SolWardrobe.lua."""
import io, os
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "SolWardrobe.src.lua")
s = io.open(p, encoding="utf-8", newline="").read()
if 'WD.VERSION = "0.2.0"' in s:
    print("kept SolWardrobe.src.lua"); raise SystemExit(0)
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")


def rep(old, new):
    global s
    if s.count(old) != 1: raise SystemExit("count %d for: %s" % (s.count(old), old[:70]))
    s = s.replace(old, new)


rep('WD.VERSION = "0.1.0"', 'WD.VERSION = "0.2.0"')
rep('local W, H, HEAD = 880, 640, 56', 'local W, H, HEAD = 880, 664, 56')
rep('local ROW_Y, ROW_GAP = 70, 60', 'local ROW_Y, ROW_GAP = 70, 38')
rep('''    apply = "طبّق", applied = "تم", none = "بلا (شيلي القطعة)", done = "تم الاختيار",''',
    '''    apply = "طبّق", applied = "تم", none = "بدون شي (شيلي يلي لابستو هون)", cancel = "رجوع بدون تغيير",
    pick = "اكبس على قطعة لتشوفها عليها. طبّق بيثبتها، ورجوع بيرجّع يلي كانت لابستو",''')
rep('''    shoes = "الحذاء", head = "القبعة", other = "إكسسوارات وغيرها", hair = "الشعر",''',
    '''    shoes = "الحذاء", head = "القبعة أو الخوذة", armor = "الدروع والواقيات", vest = "الصدرية والجعبة",
    face = "الوجه: نضارات وأقنعة", neck = "الرقبة: شال وعقد", hands = "الإيدين: كفوف وساعات",
    belt = "الخصر والشنط", under = "داخلي وجرابات", other = "غير شي", hair = "الشعر",''')
rep('''    apply = "Apply", applied = "Done", none = "None (take it off)", done = "Close list",''',
    '''    apply = "Apply", applied = "Done", none = "Nothing (take off what she wears here)", cancel = "Back, no change",
    pick = "Click a piece to see it on her. Apply keeps it, Back puts her own piece on again",''')
rep('''    shoes = "Shoes", head = "Hat", other = "Accessories and more", hair = "Hair",''',
    '''    shoes = "Shoes", head = "Hat or helmet", armor = "Armor and pads", vest = "Vest and webbing",
    face = "Face: glasses and masks", neck = "Neck: scarf and necklace", hands = "Hands: gloves and watches",
    belt = "Waist and bags", under = "Underwear and socks", other = "Other", hair = "Hair",''')
rep('WD.SLOTS = { "top", "jacket", "bottom", "dress", "shoes", "head", "other", "hair" }',
    'WD.SLOTS = { "top", "jacket", "bottom", "dress", "shoes", "head", "armor", "vest", "face", "neck", "hands", "belt", "under", "other", "hair" }')

a = s.index('    local function has(w) return string.find(s, w, 1, true) ~= nil end')
b = s.index('    return "other"\nend', a)
s = s[:a] + '''    local function has(w) return string.find(s, w, 1, true) ~= nil end
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
''' + s[b:]

rep('''function Win:closeList()
    self.open = nil
''', '''-- leave the open list. keep ~= true: the piece she is trying in this part is taken back (her own is on again).
function Win:closeList(keep)
    local slot = self.open
    if slot ~= nil and keep ~= true then
        local who = actor()
        if who ~= nil and WD.revert(who, slot) then self:showSol() end
    end
    self.open = nil
''')
rep('''    self.hits[#self.hits + 1] = { r = back, kind = "close" }''',
    '''    self.hits[#self.hits + 1] = { r = back, kind = self.open and "closeList" or "close" }''')

a = s.index('function Win:drawParts(mx, my, over, who)')
b = s.index('function Win:drawList(mx, my, over, who)')
s = s[:a] + '''function Win:drawParts(mx, my, over, who)
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

''' + s[b:]

rep('''    local doneR = { RX, top, 136, 32 }
    button(self, doneR, word("done"), over and inside(mx, my, doneR), true, 0.48)
    self.hits[#self.hits + 1] = { r = doneR, kind = "closeList" }
    local apR = { RX + 144, top, 88, 32 }''', '''    local doneR = { RX, top, 170, 32 }
    button(self, doneR, word("cancel"), over and inside(mx, my, doneR), true, 0.46)
    self.hits[#self.hits + 1] = { r = doneR, kind = "closeList" }
    local apR = { RX + 178, top, 96, 32 }''')
rep('''    text(self, word(slot), RX + 150, top - 2, RW - 150, 0.56, "right", { 0.42, 0.72, 1.0 })''',
    '''    text(self, word(slot), RX + 282, top + 2, RW - 282, 0.5, "right", { 0.42, 0.72, 1.0 })''')
rep('''    text(self, status, RX, H - 36, RW, 0.46, "right", { 0.62, 0.72, 0.8 })''',
    '''    text(self, status, RX, H - 36, 150, 0.44, "left", { 0.62, 0.72, 0.8 })
    text(self, word("pick"), RX + 150, H - 36, RW - 150, 0.4, "right", t and c.yellow or { 0.62, 0.72, 0.8 })''')

rep('''function WD.close()
    local who = actor()
    if who ~= nil and WD.revertAll(who) then log("trials taken back on close") end
    if WD.win then WD.win:closeList(); WD.win:setVisible(false) end
end''', '''function WD.close()
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
    if ev and ev.OnTick then ev.OnTick.Add(function() n = n + 1; if n % 15 == 0 then pcall(WD.guard) end end) end
    if ev and ev.OnSave then ev.OnSave.Add(function() pcall(WD.guard, true) end) end
end''')
rep('''    WD.win:closeList()
    WD.win:setVisible(true); WD.win:bringToTop()''', '''    WD.win:closeList(true)
    WD.win:setVisible(true); WD.win:bringToTop()''')
rep('''-- chosen piece is on her at once; one "apply" button per part (top, jacket, trousers/skirt, dress, shoes, head, other, hair);''',
    '''-- chosen piece is on her at once; a list per part, each with its own "apply" and "back, no change" (v0.2.0, after his first
-- run: he could not leave a list without keeping a piece, armor had no list, a piece on trial stayed after closing);''')
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl))
print("edited SolWardrobe.src.lua")
