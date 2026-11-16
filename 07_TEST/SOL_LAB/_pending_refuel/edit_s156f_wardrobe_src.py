"""s156f: SolWardrobe.src.lua 0.3.2 -> 0.4.0. Jamal 2026-11-15: move through a clothing list with the arrow keys, finer and
easier than the mouse alone.
- Up / Down in an open list: the next / previous row is tried on her at once and the list scrolls to keep it in view
  (ISTextEntryBox:onPressUp / onPressDown while the search box has the keys; the window's own onKeyPress otherwise).
- Enter: apply. A click on a row sets the place the arrows continue from.
One-time source edit; "kept" when done. Then run apply_s156_wardrobe.py."""
import io, os
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "SolWardrobe.src.lua")
s = io.open(p, encoding="utf-8", newline="").read()
if 'WD.VERSION = "0.4.0"' in s:
    print("kept SolWardrobe.src.lua"); raise SystemExit(0)
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")


def rep(old, new):
    global s
    if s.count(old) != 1: raise SystemExit("count %d for: %s" % (s.count(old), old[:70]))
    s = s.replace(old, new)


rep('WD.VERSION = "0.3.2"', 'WD.VERSION = "0.4.0"')
rep('''    pick = "اكبس على قطعة لتشوفها عليها. طبّق بيثبتها، ورجوع بيرجّع يلي كانت لابستو",''',
    '''    pick = "اكبس على قطعة أو تنقّل بالأسهم فوق وتحت. Enter أو طبّق بيثبتها، ورجوع بيرجّع يلي كانت لابستو",''')
rep('''    pick = "Click a piece to see it on her. Apply keeps it, Back puts her own piece on again",''',
    '''    pick = "Click a piece or move with the Up and Down arrows. Enter or Apply keeps it, Back puts her own piece on again",''')
rep('''    o.flash = {}
    return o
end''', '''    o.flash = {}
    o.sel = nil             -- the row the arrow keys stand on (1 = the first row of the open list)
    o.wantKeyEvents = true
    return o
end''')
rep('''    self:addChild(self.search)
    self.search:setVisible(false)
end''', '''    self:addChild(self.search)
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
end''')
rep('''    self.open = slot; self.scroll = 0; self.query = ""; self.filterKey = nil''',
    '''    self.open = slot; self.scroll = 0; self.query = ""; self.filterKey = nil; self.sel = nil''')
rep('''        if q ~= self.query then self.query = q; self.scroll = 0 end''',
    '''        if q ~= self.query then self.query = q; self.scroll = 0; self.sel = nil end''')
rep('''    local visible = math.floor((box[4] - 8) / WD.ROW_H)
    local maxScroll = math.max(0, total - visible)''', '''    local visible = math.floor((box[4] - 8) / WD.ROW_H)
    self.visibleRows = visible
    local maxScroll = math.max(0, total - visible)''')
rep('''        self.hits[#self.hits + 1] = { r = r, kind = "pick", slot = slot, row = row }''',
    '''        self.hits[#self.hits + 1] = { r = r, kind = "pick", slot = slot, row = row, idx = idx }''')
rep('''            elseif h.kind == "pick" then
                local ok, why
                if h.row == false then ok, why = WD.try(who, h.slot, nil) else ok, why = WD.try(who, h.slot, h.row) end
                if not ok then log("could not show " .. tostring(h.row and h.row.full or "none") .. ": " .. tostring(why)) end
                self:showSol()
            end''', '''            elseif h.kind == "pick" then
                self.sel = h.idx
                self:pick(h.row)
                if self.search then pcall(function() self.search:focus() end) end     -- the arrows go on from here
            end''')
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl))
print("edited SolWardrobe.src.lua")
