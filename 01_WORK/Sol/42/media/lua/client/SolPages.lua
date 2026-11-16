-- SolPages.lua - every Living Fellows screen, shown inside a Sol window (rounded Sol theme, SolText Arabic).
-- The Living Fellows window is never displayed. Its builders still run (hidden) to produce their widgets;
-- this file reads those widgets as data (sections, lines, buttons, choices, ticks) and draws them the Sol way.
-- Pressing a Sol control calls the very same Living Fellows callback, exactly as the game would.
require "ISUI/ISPanel"
require "SolText"

SolUI = SolUI or {}
local U = SolUI
local T = SolText
U.PAGES_VERSION = "0.2.0"
local TEX = "media/textures/SolUI/"
local W, H, HEAD = 600, 640, 56
local TAB_X, TAB_W, TAB_H, TAB_GAP = 440, 148, 38, 6
local CX, CW, CY = 14, 418, 66
local CH = H - CY - 44
local SCALE_TXT, SCALE_SEC = 0.57, 0.67      -- IBM Plex Sans Arabic glyphs at 30 px: about 17 px and 20 px
local REFRESH_MS = 5000          -- each refresh rebuilds a hidden LF page (many widgets): keep it rare
-- Sol pages: only what makes sense for one companion. Groups / Expeditions / More come back redesigned later.
local SHOWN_TABS = { status = true, orders = true, loadout = true }
local GOLD = { 0.79, 0.73, 0.48 }

local function log(m) print("[SolUI] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function LF() local sc = SurvivorCompanion; return type(sc) == "table" and sc or nil end
local texCache = {}
local function tex(n) local t = texCache[n]; if t == nil then t = getTexture(TEX .. n .. ".png") or false; texCache[n] = t end; return t or nil end
local function inside(x, y, r) return x >= r[1] and y >= r[2] and x < r[1] + r[3] and y < r[2] + r[4] end
local function near(r, g, b, t) return r and math.abs(r - t[1]) < 0.03 and math.abs(g - t[2]) < 0.03 and math.abs(b - t[3]) < 0.03 end

-- ---------------------------------------------------------------- hidden Living Fellows root
local function hiddenRoot()
    local SC = LF(); if not SC or not SC.UI then return nil end
    local ensure = SC.UI.solOrigEnsure or SC.UI.ensureControl
    if type(ensure) ~= "function" then return nil end
    local ok, root = pcall(ensure)
    if not ok or not root then return nil end
    root:setVisible(false)
    if SC.UI.launcher then SC.UI.launcher:setVisible(false) end
    return root
end

local function tabLabel(id)
    local key = "UI_SC_Tab_" .. string.upper(string.sub(id, 1, 1)) .. string.sub(id, 2)
    if id == "sheet" then key = "UI_SC_Tab_Sheet" end
    local SC = LF()
    local s = U.translate and U.translate(key) or nil
    if s then return s end
    return SC and SC.UI and SC.UI.text and SC.UI.text(key) or id
end
local function isAr() return not (U.lang and U.lang() == "en") end
function U.pageTabs()
    local SC = LF(); local out = {}
    local ids = SC and SC.UI and SC.UI.tabIds and SC.UI.tabIds() or { "status", "orders", "loadout", "more" }
    for _, id in ipairs(ids) do
        if SHOWN_TABS[id] then out[#out + 1] = { id = id, label = tabLabel(id) } end
        if id == "status" then out[#out + 1] = { id = "skills", label = isAr() and "\\u0627\\u0644\\u0645\\u0647\\u0627\\u0631\\u0627\\u062A" or "Skills", sol = true } end
    end
    out[#out + 1] = { id = "family", label = isAr() and "\\u0627\\u0644\\u0639\\u0627\\u0626\\u0644\\u0629" or "Family", sol = true }
    return out
end

-- ---------------------------------------------------------------- Sol's skills (same list as the player's panel)
local AR_PERK = {
    Fitness = "\\u0627\\u0644\\u0644\\u064A\\u0627\\u0642\\u0629", Strength = "\\u0627\\u0644\\u0642\\u0648\\u0629", Sprinting = "\\u0627\\u0644\\u0631\\u0643\\u0636 \\u0627\\u0644\\u0633\\u0631\\u064A\\u0639", Lightfoot = "\\u062E\\u0641\\u0629 \\u0627\\u0644\\u0642\\u062F\\u0645", Nimble = "\\u0627\\u0644\\u0631\\u0634\\u0627\\u0642\\u0629", Sneak = "\\u0627\\u0644\\u062A\\u0633\\u0644\\u0644",
    Axe = "\\u0627\\u0644\\u0641\\u0623\\u0633", Blunt = "\\u0627\\u0644\\u0647\\u0631\\u0627\\u0648\\u0629 \\u0627\\u0644\\u0637\\u0648\\u064A\\u0644\\u0629", SmallBlunt = "\\u0627\\u0644\\u0647\\u0631\\u0627\\u0648\\u0629 \\u0627\\u0644\\u0642\\u0635\\u064A\\u0631\\u0629", LongBlade = "\\u0627\\u0644\\u0646\\u0635\\u0644 \\u0627\\u0644\\u0637\\u0648\\u064A\\u0644", SmallBlade = "\\u0627\\u0644\\u0646\\u0635\\u0644 \\u0627\\u0644\\u0642\\u0635\\u064A\\u0631",
    Spear = "\\u0627\\u0644\\u0631\\u0645\\u062D", Maintenance = "\\u0635\\u064A\\u0627\\u0646\\u0629 \\u0627\\u0644\\u0623\\u0633\\u0644\\u062D\\u0629", Woodwork = "\\u0627\\u0644\\u0646\\u062C\\u0627\\u0631\\u0629", Cooking = "\\u0627\\u0644\\u0637\\u0628\\u062E", Farming = "\\u0627\\u0644\\u0632\\u0631\\u0627\\u0639\\u0629", Doctor = "\\u0627\\u0644\\u0625\\u0633\\u0639\\u0627\\u0641",
    Electricity = "\\u0627\\u0644\\u0643\\u0647\\u0631\\u0628\\u0627\\u0621", MetalWelding = "\\u0627\\u0644\\u0644\\u062D\\u0627\\u0645", Mechanics = "\\u0627\\u0644\\u0645\\u064A\\u0643\\u0627\\u0646\\u064A\\u0643", Tailoring = "\\u0627\\u0644\\u062E\\u064A\\u0627\\u0637\\u0629", Aiming = "\\u0627\\u0644\\u062A\\u0635\\u0648\\u064A\\u0628",
    Reloading = "\\u0625\\u0639\\u0627\\u062F\\u0629 \\u0627\\u0644\\u062A\\u0644\\u0642\\u064A\\u0645", Fishing = "\\u0635\\u064A\\u062F \\u0627\\u0644\\u0633\\u0645\\u0643", Trapping = "\\u0646\\u0635\\u0628 \\u0627\\u0644\\u0641\\u062E\\u0627\\u062E", PlantScavenging = "\\u0627\\u0644\\u0628\\u062D\\u062B \\u0641\\u064A \\u0627\\u0644\\u0637\\u0628\\u064A\\u0639\\u0629",
    Masonry = "\\u0627\\u0644\\u0628\\u0646\\u0627\\u0621 \\u0628\\u0627\\u0644\\u062D\\u062C\\u0631", Pottery = "\\u0627\\u0644\\u0641\\u062E\\u0627\\u0631", Carving = "\\u0627\\u0644\\u0646\\u062D\\u062A", Blacksmith = "\\u0627\\u0644\\u062D\\u062F\\u0627\\u062F\\u0629", Husbandry = "\\u0631\\u0639\\u0627\\u064A\\u0629 \\u0627\\u0644\\u062D\\u064A\\u0648\\u0627\\u0646\\u0627\\u062A",
    Butchering = "\\u0627\\u0644\\u0630\\u0628\\u062D \\u0648\\u0627\\u0644\\u0633\\u0644\\u062E", Tracking = "\\u062A\\u062A\\u0628\\u0639 \\u0627\\u0644\\u0623\\u062B\\u0631", Glassmaking = "\\u0635\\u0646\\u0627\\u0639\\u0629 \\u0627\\u0644\\u0632\\u062C\\u0627\\u062C", FlintKnapping = "\\u062A\\u0634\\u0638\\u064A\\u0629 \\u0627\\u0644\\u0635\\u0648\\u0627\\u0646",
}
local AR_CAT = { Passiv = "\\u0633\\u0644\\u0628\\u064A\\u0629", Passive = "\\u0633\\u0644\\u0628\\u064A\\u0629", Agility = "\\u0627\\u0644\\u0631\\u0634\\u0627\\u0642\\u0629", Combat = "\\u0627\\u0644\\u0642\\u062A\\u0627\\u0644", Crafting = "\\u0627\\u0644\\u062D\\u0650\\u0631\\u064E\\u0641", Firearm = "\\u0627\\u0644\\u0623\\u0633\\u0644\\u062D\\u0629 \\u0627\\u0644\\u0646\\u0627\\u0631\\u064A\\u0629",
                 Survivalist = "\\u0627\\u0644\\u0646\\u062C\\u0627\\u0629", Farming = "\\u0627\\u0644\\u0632\\u0631\\u0627\\u0639\\u0629" }
local function call(o, name, ...)
    if o == nil then return nil end
    local f = o[name]; if f == nil then return nil end
    local ok, v = pcall(f, o, ...); if ok then return v end; return nil
end
local function perkId(p) local t = call(p, "getType"); return tostring(call(t, "name") or call(t, "toString") or call(p, "getId") or tostring(p)) end
function U.readSkills(actor)
    if not actor or not PerkFactory or not PerkFactory.PerkList then return nil, "no perk list" end
    local list = PerkFactory.PerkList
    local n = call(list, "size") or 0
    local cats, order = {}, {}
    local xpObj = call(actor, "getXp")
    for i = 0, n - 1 do
        local perk = call(list, "get", i)
        local parent = call(perk, "getParent")
        local parentId = parent and perkId(parent) or "None"
        if perk and parentId ~= "None" then
            local id = perkId(perk)
            local level = tonumber((call(actor, "getPerkLevel", perk))) or 0
            local xp = xpObj and tonumber((call(xpObj, "getXP", perk))) or nil
            local nextXp = level < 10 and tonumber((call(perk, "getTotalXpForLevel", level + 1))) or nil
            local c = cats[parentId]
            if not c then
                c = { id = parentId, label = (isAr() and AR_CAT[parentId]) or tostring(call(parent, "getName") or parentId), skills = {} }
                cats[parentId] = c; order[#order + 1] = c
            end
            c.skills[#c.skills + 1] = { id = id, label = (isAr() and AR_PERK[id]) or tostring(call(perk, "getName") or id), level = level, xp = xp, nextXp = nextXp }
        end
    end
    return order
end

-- ---------------------------------------------------------------- read the widgets as data
local function children(el)
    local list = {}
    for _, c in pairs(el.children or {}) do list[#list + 1] = c end
    table.sort(list, function(a, b) local ay, by = a.y or 0, b.y or 0; if ay ~= by then return ay < by end return (a.x or 0) > (b.x or 0) end)
    return list
end
local function optionText(o) if type(o) == "table" then return tostring(o.text or "") end return tostring(o or "") end
local function optionData(o) if type(o) == "table" then return o.data end return nil end
-- which LF command a widget issues: buttons keep scCommand; ticks / selectors pass it as their first callback argument
local function commandOf(c)
    if type(c.scCommand) == "string" then return c.scCommand end
    local a = c.changeOptionArgs or c.onChangeArgs
    if type(a) == "table" and type(a[1]) == "string" then return a[1] end
    return nil
end
U.widgetCommand = commandOf
function U.readWidgets(content)
    local items = {}
    local function walk(el, depth)
        for _, c in ipairs(children(el)) do
            if c.Type == "ISButton" or (c.onclick ~= nil and c.title ~= nil) then
                items[#items + 1] = { kind = "button", y = c.y or 0, text = tostring(c.title or ""), enabled = c.enable ~= false, ref = c, tip = c.tooltip, command = commandOf(c) }
            elseif c.Type == "ISComboBox" or (c.options ~= nil and c.onChange ~= nil) then
                local opts, data = {}, {}
                for i, o in ipairs(c.options or {}) do opts[i] = optionText(o); data[i] = optionData(o) end
                items[#items + 1] = { kind = "combo", y = c.y or 0, options = opts, data = data, selected = c.selected or 1, ref = c, command = commandOf(c) }
            elseif c.Type == "ISTickBox" or c.changeOptionMethod ~= nil then
                local opts = {}
                for i, o in ipairs(c.options or {}) do opts[i] = { text = tostring(o), on = c.selected and c.selected[i] == true } end
                items[#items + 1] = { kind = "tick", y = c.y or 0, options = opts, ref = c, command = commandOf(c) }
            elseif c.Type == "ISLabel" or (c.name ~= nil and c.r ~= nil) then
                local txt = tostring(c.translation or c.name or "") if SolDialogueLines and SolDialogueLines.display then txt = SolDialogueLines.display(txt) end
                if txt ~= "" then items[#items + 1] = { kind = near(c.r, c.g, c.b, GOLD) and "section" or "label", y = c.y or 0, text = txt } end
            elseif depth < 4 and c.children then
                walk(c, depth + 1)
            end
        end
    end
    if content then walk(content, 0) end
    return items
end

-- Living Fellows fits and wraps text with the game font. Arabic is stored as \uXXXX escapes (6 ASCII chars per
-- letter), so LF thought every Arabic word was 6x wider and cut / wrapped word by word (seen 2026-10-24).
-- While LF builds a hidden page, the text manager it measures with answers with SolText's real width.
local function escaped(s) return type(s) == "string" and string.find(s, "\\u", 1, true) ~= nil end
function U.measureProxy(real)
    local proxy = {}
    setmetatable(proxy, { __index = function(_, k)
        return function(_, ...) local f = real[k]; return f(real, ...) end
    end })
    proxy.MeasureStringX = function(_, font, text)
        if escaped(text) then return math.ceil(T.width(text, SCALE_TXT)) end
        return real:MeasureStringX(font, text)
    end
    return proxy
end
local function withMeasure(fn)
    local orig = getTextManager
    if type(orig) ~= "function" then return fn() end
    local real = orig()
    local proxy = U.measureProxy(real)
    getTextManager = function() return proxy end
    local ok, err = pcall(fn)
    getTextManager = orig
    if not ok then error(err) end
end
U.withMeasure = withMeasure

function U.extractPage(tab, companionId)
    if U.perfAdd then local t0 = nowMs(); local a, b = U.extractPageRaw(tab, companionId); U.perfAdd("lf_page_build", nowMs() - t0); return a, b end
    return U.extractPageRaw(tab, companionId)
end
function U.extractPageRaw(tab, companionId)
    local root = hiddenRoot()
    if not root then return nil, "Living Fellows UI not available" end
    local function build()
        if companionId and root.refreshRoster then pcall(root.refreshRoster, root, companionId, nil, true) end
        if tab and root.selectedTab ~= tab and root.setSelectedTab then root:setSelectedTab(tab)
        elseif root.detail and root.detail.rebuild then root.detail:rebuild(true) end
    end
    local ok, err = pcall(function() withMeasure(function() if U.withArabic then U.withArabic(build) else build() end end) end)
    root:setVisible(false)
    if not ok then return nil, tostring(err) end
    U.pageRow = root.selectedRow
    return U.readWidgets(root.detail and root.detail.content), root.selectedTab or tab
end

-- ---------------------------------------------------------------- actions (same calls the game makes)
function U.pressButton(b)
    if not b or b.enable == false or type(b.onclick) ~= "function" then return false end
    local a = b.onClickArgs or {}
    local ok, err = pcall(b.onclick, b.target, b, a[1], a[2], a[3], a[4])
    if not ok then log("button failed: " .. tostring(err)) end
    return ok
end
function U.chooseOption(c, index)
    if not c or not c.options or not c.options[index] then return false end
    c.selected = index
    if type(c.onChange) ~= "function" then return true end
    local a = c.onChangeArgs or {}
    local ok, err = pcall(c.onChange, c.target, c, a[1], a[2])
    if not ok then log("choice failed: " .. tostring(err)) end
    return ok
end
function U.toggleTick(tb, index)
    if not tb then return false end
    local new = not (tb.selected and tb.selected[index] == true)
    if tb.setSelected then pcall(tb.setSelected, tb, index, new) else tb.selected = tb.selected or {}; tb.selected[index] = new end
    if type(tb.changeOptionMethod) == "function" then
        local a = tb.changeOptionArgs or {}
        local ok, err = pcall(tb.changeOptionMethod, tb.changeOptionTarget, index, new, a[1], a[2], tb)
        if not ok then log("tick failed: " .. tostring(err)) end
    end
    return true
end

-- ---------------------------------------------------------------- the Sol page window
local Page = ISPanel:derive("SolPage")
U.PageClass = Page
function Page:new(x, y)
    local o = ISPanel:new(x, y, W, H)
    setmetatable(o, self); self.__index = self
    o.background = false; o.tab = "status"; o.items = {}; o.scroll = 0; o.lastBuild = 0; o.rows = {}; o.dd = nil
    return o
end

-- layout: turns items into rows with heights (several buttons on one LF line share the width)
function Page:layout()
    local rows, y = {}, 0
    local i = 1
    local items = self.items
    while i <= #items do
        local it = items[i]
        if it.kind == "button" then
            local group = { it }
            while items[i + 1] and items[i + 1].kind == "button" and math.abs((items[i + 1].y or 0) - (it.y or 0)) < 4 do i = i + 1; group[#group + 1] = items[i] end
            rows[#rows + 1] = { kind = "buttons", list = group, y = y, h = 40 }; y = y + 40
        elseif it.kind == "combo" then rows[#rows + 1] = { kind = "combo", it = it, y = y, h = 40 }; y = y + 40
        elseif it.kind == "tick" then local h = #it.options * 28 + 6; rows[#rows + 1] = { kind = "tick", it = it, y = y, h = h }; y = y + h
        elseif it.kind == "section" then rows[#rows + 1] = { kind = "section", it = it, y = y + 6, h = 30 }; y = y + 36
        else local h = math.max(22, T.height(it.text, CW - 8, { scale = SCALE_TXT })); rows[#rows + 1] = { kind = "label", it = it, y = y, h = h }; y = y + h + 2 end
        i = i + 1
    end
    self.rows = rows; self.contentH = y
end

-- follow = true after a Sol control was used: LF may have moved to another tab (e.g. More > Base)
function Page:refresh(force, follow)
    if not force and nowMs() - self.lastBuild < REFRESH_MS then return end
    self.lastBuild = nowMs()
    local tStart = nowMs()
    if self.tab == "skills" and not follow then
        self.skills = U.readSkills(U.solActor and U.solActor() or nil)
        self.books = U.solBooks and U.solBooks() or {}
        self.items = {}; self.rows = {}
        local h = 0
        for _, c in ipairs(self.skills or {}) do h = h + 34 + #c.skills * 26 end
        h = h + 34 + 28 + math.max(1, #self.books) * 44
        self.contentH = h
        return
    end
    if self.tab == "family" and not follow then
        U.extractPage("status", U.pageCompanionId)            -- refreshes the LF row only
        self.items = {}; self.rows = {}; self.contentH = 640
        return
    end
    local items, tab = U.extractPage(not follow and self.tab or nil, U.pageCompanionId)
    if items then
        if (tab or self.tab) == "loadout" then
            local keep = {}
            for _, it in ipairs(items) do if it.kind ~= "label" then keep[#keep + 1] = it end end
            items = keep
        end
        self.items = items; if tab then self.tab = tab end; self:layout()
        if self.tab == "loadout" then
            self.cardH = 236
            for _, r in ipairs(self.rows) do r.y = r.y + self.cardH end
            self.contentH = (self.contentH or 0) + self.cardH
        else self.cardH = 0 end
    end
end

local function text(ui, s, x, y, w, scale, align, c, a)
    T.drawLine(ui, s, x, y, w, { scale = scale, align = align or "right", r = c and c[1] or 0.94, g = c and c[2] or 0.96, b = c and c[3] or 0.98, a = a or 1 })
end
function Page:prerender()
    if U.perfAdd then local t0 = nowMs(); self:prerenderBody(); U.perfAdd("pages", nowMs() - t0); return end
    self:prerenderBody()
end
function Page:prerenderBody()
    self:refresh(false)
    local function draw(n, x, y, w, h, a) local t = tex(n); if t then self:drawTextureScaled(t, x, y, w, h, a or 1, 1, 1, 1) end end
    draw("pg_bg", 0, 0, W, H)
    draw("pg_back", 16, 12, 110, 32)
    text(self, (U.lang and U.lang() == "en" and "Back" or "\\u0631\\u062C\\u0648\\u0639"), 16, 13, 110, 0.5, "center")
    local title = "Sol"
    for _, tb in ipairs(U.pageTabs()) do if tb.id == self.tab then title = tb.label end end
    text(self, title, 140, 8, 440, 0.72, "right")
    -- tabs (right column)
    self.tabRects = {}
    for i, tb in ipairs(U.pageTabs()) do
        local y = CY + (i - 1) * (TAB_H + TAB_GAP)
        local r = { TAB_X, y, TAB_W, TAB_H }; self.tabRects[#self.tabRects + 1] = { r = r, id = tb.id }
        local on = tb.id == self.tab or (tb.id == "more" and self.tab ~= nil and not self:isTopTab(self.tab))
        draw(on and "pg_tab_on" or "pg_tab_off", r[1], r[2], r[3], r[4])
        text(self, tb.label, r[1] + 6, r[2] + 2, r[3] - 12, 0.55, "center")
    end
    -- content
    self:setStencilRect(CX, CY, CW, CH)
    local mx, my = self:getMouseX(), self:getMouseY()
    self.hits = {}
    self.tip = nil
    for _, row in ipairs(self.rows or {}) do
        local y = CY + row.y - self.scroll
        if y + row.h >= CY and y <= CY + CH then
            if row.kind == "section" then
                text(self, row.it.text, CX, y, CW - 6, SCALE_SEC, "right", { 0.42, 0.72, 1.0 })
            elseif row.kind == "label" then
                row.lines = row.lines or T.wrap(row.it.text, CW - 8, SCALE_TXT)
                local lh = T.lineHeight(SCALE_TXT) * 0.82
                for li, ln in ipairs(row.lines) do
                    T.drawLine(self, ln, CX, y + (li - 1) * lh, CW - 8, { scale = SCALE_TXT, align = "right", r = 0.9, g = 0.94, b = 0.97 })
                end
            elseif row.kind == "buttons" then
                local n = #row.list; local gap = 6; local bw = (CW - gap * (n - 1)) / n
                for k, it in ipairs(row.list) do
                    local bx = CX + CW - k * bw - (k - 1) * gap
                    local r = { bx, y + 2, bw, 34 }
                    local hover = inside(mx, my, r) and self:isMouseOver()
                    draw("pg_btn", r[1], r[2], r[3], r[4], it.enabled and 1 or 0.5)
                    if hover and it.enabled then draw("pg_btn_hover", r[1], r[2], r[3], r[4]) end
                    text(self, it.text, r[1] + 6, r[2] + 4, r[3] - 12, SCALE_TXT, "center", nil, it.enabled and 1 or 0.45)
                    if hover and it.tip and it.tip ~= "" then self.tip = it.tip end
                    self.hits[#self.hits + 1] = { r = r, kind = "button", it = it }
                end
            elseif row.kind == "combo" then
                local it = row.it
                local r = { CX, y + 2, CW, 34 }
                draw("pg_combo", r[1], r[2], r[3], r[4])
                text(self, it.options[it.selected] or "", r[1] + 30, r[2] + 4, r[3] - 40, SCALE_TXT, "right")
                self:drawText("v", r[1] + 12, r[2] + 9, 0.7, 0.78, 0.84, 1, UIFont.Small)
                self.hits[#self.hits + 1] = { r = r, kind = "combo", it = it }
            elseif row.kind == "tick" then
                for k, o in ipairs(row.it.options) do
                    local ty = y + 3 + (k - 1) * 28
                    local box = { CX + CW - 26, ty, 22, 22 }
                    draw(o.on and "pg_tick_on" or "pg_tick_off", box[1], box[2], 22, 22)
                    text(self, o.text, CX, ty - 4, CW - 34, SCALE_TXT, "right")
                    self.hits[#self.hits + 1] = { r = { CX, ty, CW, 24 }, kind = "tick", it = row.it, index = k }
                end
            end
        end
    end
    if self.tab == "skills" then self:drawSkills(mx, my) end
    if self.tab == "family" then self:drawFamily() end
    if self.tab == "loadout" then self:drawLoadoutCard(mx, my) end
    self:clearStencilRect()
    local maxScroll = math.max(0, (self.contentH or 0) - CH)
    if self.scroll > maxScroll then self.scroll = maxScroll end
    if maxScroll > 0 then
        local hh = math.max(24, CH * CH / (self.contentH or CH))
        self:drawRect(CX - 8, CY + (CH - hh) * self.scroll / maxScroll, 3, hh, 0.8, 0.18, 0.64, 1)
    end
    if self.tip then T.drawLine(self, self.tip, CX, H - 38, W - 2 * CX, { scale = 0.48, align = "right", r = 0.93, g = 0.74, b = 0.19 }) end
end

function Page:drawSkills(mx, my)
    local y = CY - self.scroll
    if not self.skills then
        text(self, isAr() and "\\u062A\\u0639\\u0630\\u0651\\u0631\\u062A \\u0642\\u0631\\u0627\\u0621\\u0629 \\u0645\\u0647\\u0627\\u0631\\u0627\\u062A \\u0633\\u0648\\u0644 \\u0627\\u0644\\u0622\\u0646." or "Sol's skills cannot be read right now.", CX, y + 10, CW, SCALE_TXT, "right", { 0.93, 0.74, 0.19 })
        return
    end
    for _, c in ipairs(self.skills) do
        text(self, c.label, CX, y + 6, CW - 6, SCALE_SEC, "right", { 0.42, 0.72, 1.0 }); y = y + 34
        for _, sk in ipairs(c.skills) do
            text(self, sk.label, CX + 222, y, CW - 228, SCALE_TXT, "right", sk.level > 0 and { 1.0, 0.86, 0.45 } or nil)
            for b = 1, 10 do
                local bx = CX + 4 + (b - 1) * 21
                local t = tex(b <= sk.level and "pg_skill_on" or "pg_skill_off")
                if t then self:drawTextureScaled(t, bx, y + 4, 19, 15, 1, 1, 1, 1) end
            end
            if self:isMouseOver() and mx >= CX and mx < CX + CW and my >= y and my < y + 24 then
                local lv = isAr() and (sk.label .. ": \\u0627\\u0644\\u0645\\u0633\\u062A\\u0648\\u0649 " .. tostring(sk.level)) or (sk.label .. ": level " .. tostring(sk.level))
                if sk.xp then lv = lv .. "   XP " .. tostring(math.floor(sk.xp * 10 + 0.5) / 10) .. (sk.nextXp and (" / " .. tostring(math.floor(sk.nextXp))) or "") end
                self.tip = lv
            end
            y = y + 26
        end
    end
    self:drawBooks(y)
end


-- ---------------------------------------------------------------- values from the Living Fellows row
local function rowVal(k) local r = U.pageRow; return r and r[k] or nil end
local function stateText(v)
    if type(v) ~= "string" then return nil end
    local t = U.translate and U.translate("UI_SC_State_" .. v)
    if t then return t end
    return v
end
local function fmtPct(v)
    if type(v) == "number" then
        if v <= 1.0001 then return tostring(math.floor(v * 100 + 0.5)) .. "%" end
        return tostring(math.floor(v + 0.5)) .. "%"
    end
    if type(v) == "string" then return stateText(v) end
    return "-"
end
local function fmt(v)
    if v == nil then return "-" end
    if type(v) == "number" then return tostring(math.floor(v * 10 + 0.5) / 10) end
    if type(v) == "boolean" then return v and "\\u0646\\u0639\\u0645" or "\\u0644\\u0627" end
    if type(v) == "string" then return stateText(v) end
    if type(v) == "table" then
        if v.name then return tostring(v.name) end
        if v.text then return tostring(v.text) end
        local n = 0; for _ in pairs(v) do n = n + 1 end; return tostring(n)
    end
    return tostring(v)
end
U.pageFmt = { pct = fmtPct, val = fmt }

-- the same call path the LF buttons use (SCUI.lua issueCommandButton)
function U.issueLF(command, payload)
    local SC = LF(); local row = U.pageRow
    if not SC or not row then return false, "no_row" end
    local okA, available = pcall(SC.UI.commandAvailability, row, command, payload)
    if not okA or not available then return false, "unavailable" end
    local player = getSpecificPlayer and getSpecificPlayer(0)
    local ok, accepted, reason
    if SC.Interaction and SC.Interaction.descriptor and SC.Interaction.descriptor(command) and type(payload) ~= "table" then
        ok, accepted, reason = pcall(SC.Interaction.issue, row, command, player)
    else
        ok, accepted, reason = pcall(SC.Commands.issue, row.id, command, payload, player)
    end
    return ok and accepted == true, reason
end
function U.lfAvailable(command, payload)
    local SC = LF(); local row = U.pageRow
    if not SC or not row or not SC.UI or not SC.UI.commandAvailability then return false end
    local ok, a = pcall(SC.UI.commandAvailability, row, command, payload)
    return ok and a == true
end

local GOOD, WARN, BAD, MUTED, BLUE = { 0.18, 0.83, 0.39 }, { 0.93, 0.74, 0.19 }, { 0.94, 0.47, 0.43 }, { 0.62, 0.71, 0.78 }, { 0.42, 0.72, 1.0 }
local function panelBox(self, x, y, w, h)
    local t = tex("pg_btn"); if t then self:drawTextureScaled(t, x, y, w, h, 1, 1, 1, 1) end
end
function Page:drawLoadoutCard(mx, my)
    local y = CY - self.scroll
    local ar = isAr()
    -- weapon
    panelBox(self, CX, y, CW, 70)
    text(self, ar and "\\u0627\\u0644\\u0633\\u0644\\u0627\\u062D" or "Weapon", CX + 10, y + 4, CW - 20, 0.48, "right", MUTED)
    text(self, fmt(rowVal("equippedWeapon")), CX + 120, y + 28, CW - 130, 0.64, "right")
    text(self, ar and "\\u0627\\u0644\\u0630\\u062E\\u064A\\u0631\\u0629" or "Ammo", CX + 10, y + 4, 100, 0.48, "left", MUTED)
    local ammo = rowVal("ammunition")
    text(self, type(ammo) == "number" and tostring(ammo) or fmt(ammo), CX + 10, y + 26, 100, 0.78, "left", BLUE)
    -- carry load bar
    y = y + 78
    panelBox(self, CX, y, CW, 58)
    local w, cap, ratio = tonumber((rowVal("loadWeight"))), tonumber((rowVal("loadCapacity"))), tonumber((rowVal("loadRatio")))
    if not ratio and w and cap and cap > 0 then ratio = w / cap end
    local c = (ratio or 0) >= 0.9 and BAD or ((ratio or 0) >= 0.7 and WARN or GOOD)
    text(self, (ar and "\\u0627\\u0644\\u062D\\u0645\\u0644" or "Carry") .. "   " .. (w and (tostring(math.floor(w * 10 + 0.5) / 10) .. " / " .. tostring(math.floor((cap or 0) * 10 + 0.5) / 10)) or "-"), CX + 10, y + 4, CW - 20, 0.52, "right")
    self:drawRect(CX + 12, y + 36, CW - 24, 10, 1, 0.05, 0.12, 0.18)
    if ratio then self:drawRect(CX + 12 + (CW - 24) * (1 - math.min(1, ratio)), y + 36, (CW - 24) * math.min(1, ratio), 10, 1, c[1], c[2], c[3]) end
    -- health + supplies
    y = y + 66
    panelBox(self, CX, y, CW, 50)
    local wounds = rowVal("wounds")
    local wtxt = type(wounds) == "string" and wounds or (type(wounds) == "table" and tostring(#wounds) or fmt(wounds))
    text(self, (ar and "\\u0627\\u0644\\u0635\\u062D\\u0629 " or "Health ") .. fmtPct(rowVal("health")) .. "    " .. (ar and "\\u0627\\u0644\\u062C\\u0631\\u0648\\u062D: " or "Wounds: ") .. wtxt, CX + 10, y + 3, CW - 20, 0.5, "right")
    text(self, (ar and "\\u0627\\u0644\\u0645\\u0624\\u0646: " or "Supplies: ") .. fmt(rowVal("supplies")), CX + 10, y + 25, CW - 20, 0.46, "right", MUTED)
    -- quick actions
    y = y + 58
    local acts = { { "open_inventory", ar and "\\u062D\\u0642\\u064A\\u0628\\u062A\\u0647\\u0627" or "Her bag" }, { "open_health", ar and "\\u0641\\u062D\\u0635 \\u0637\\u0628\\u064A" or "Medical" }, { "bandage", ar and "\\u062A\\u0636\\u0645\\u064A\\u062F" or "Bandage" } }
    local bw = (CW - 12) / 3
    for i, a in ipairs(acts) do
        local r = { CX + CW - i * bw - (i - 1) * 6, y, bw, 32 }
        local on = U.lfAvailable(a[1])
        local t = tex("pg_btn"); if t then self:drawTextureScaled(t, r[1], r[2], r[3], r[4], on and 1 or 0.5, 1, 1, 1) end
        text(self, a[2], r[1], r[2] + 2, r[3], 0.52, "center", nil, on and 1 or 0.45)
        if on then self.hits[#self.hits + 1] = { r = r, kind = "lf", command = a[1] } end
    end
end

local TIERS = { "cautious", "ally", "trusted", "close", "family", "romance", "married" }
local TIER_AR = { cautious = "\\u062D\\u0630\\u0631\\u0629", ally = "\\u062D\\u0644\\u064A\\u0641\\u0629", trusted = "\\u0645\\u0648\\u062B\\u0648\\u0642\\u0629", close = "\\u0645\\u0642\\u0631\\u0651\\u0628\\u0629", family = "\\u0639\\u0627\\u0626\\u0644\\u0629", romance = "\\u0639\\u0644\\u0627\\u0642\\u0629 \\u0639\\u0627\\u0637\\u0641\\u064A\\u0629", married = "\\u0632\\u0648\\u062C\\u0627\\u0646" }
function Page:drawFamily()
    local y = CY - self.scroll
    local ar = isAr()
    text(self, ar and "\\u0639\\u0644\\u0627\\u0642\\u062A\\u0643\\u0645\\u0627" or "Your relationship", CX, y + 4, CW - 6, SCALE_SEC, "right", BLUE); y = y + 38
    local tier = rowVal("relationshipTier")
    local cur = 0
    for i, t in ipairs(TIERS) do if t == tier then cur = i end end
    for i, t in ipairs(TIERS) do
        local locked = i > 5
        local on = i <= cur
        local r = { CX + CW - 150, y, 150, 30 }
        local tx = tex(i == cur and "pg_tab_on" or "pg_tab_off")
        if tx then self:drawTextureScaled(tx, r[1], r[2], r[3], r[4], locked and 0.55 or 1, 1, 1, 1) end
        text(self, ar and TIER_AR[t] or t, r[1] + 4, r[2] + 1, r[3] - 8, 0.5, "center", nil, locked and 0.55 or 1)
        if locked then text(self, ar and "\\u0642\\u0631\\u064A\\u0628\\u064B\\u0627" or "soon", CX, y + 3, CW - 160, 0.44, "right", MUTED)
        elseif on and i < cur then local tk = tex("pg_tick_on"); if tk then self:drawTextureScaled(tk, CX + CW - 178, y + 4, 22, 22, 1, 1, 1, 1) end end
        y = y + 36
    end
    y = y + 8
    local lines = {
        { ar and "\\u0627\\u0644\\u062B\\u0642\\u0629" or "Trust", fmtPct(rowVal("trust")) }, { ar and "\\u0627\\u0644\\u0631\\u0627\\u0628\\u0637\\u0629" or "Bond", fmtPct(rowVal("bond")) },
        { ar and "\\u0627\\u0644\\u0645\\u0632\\u0627\\u062C" or "Mood", fmt(rowVal("mood")) }, { ar and "\\u0627\\u0644\\u0645\\u0639\\u0646\\u0648\\u064A\\u0627\\u062A" or "Morale", fmt(rowVal("morale")) },
        { ar and "\\u0627\\u0644\\u0648\\u0642\\u062A \\u0645\\u0639\\u064B\\u0627" or "Time together", (tonumber((rowVal("timeTogetherHours"))) and (tostring(math.floor(rowVal("timeTogetherHours"))) .. (ar and " \\u0633\\u0627\\u0639\\u0629" or " h")) or "-") },
        { ar and "\\u0645\\u0627 \\u062A\\u062D\\u062A\\u0627\\u062C\\u0647 \\u0627\\u0644\\u0622\\u0646" or "Current need", fmt(rowVal("currentNeed")) },
        { ar and "\\u0622\\u062E\\u0631 \\u0630\\u0643\\u0631\\u0649" or "Recent memory", fmt(rowVal("recentMemory")) },
    }
    for _, l in ipairs(lines) do
        T.draw(self, l[1] .. ": " .. l[2], CX, y, CW - 8, { scale = SCALE_TXT, align = "right", r = 0.9, g = 0.94, b = 0.97 })
        y = y + math.max(28, T.height(l[1] .. ": " .. l[2], CW - 8, { scale = SCALE_TXT }))
    end
end

local BOOK_STATUS = {
    useful = { "\\u0645\\u0641\\u064A\\u062F \\u0644\\u0645\\u0633\\u062A\\u0648\\u0627\\u0647\\u0627 \\u0627\\u0644\\u0622\\u0646", "Useful at her level", { 0.18, 0.83, 0.39 } },
    teaches = { "\\u064A\\u0639\\u0644\\u0651\\u0645\\u0647\\u0627 \\u0648\\u0635\\u0641\\u0627\\u062A \\u062C\\u062F\\u064A\\u062F\\u0629", "Teaches new recipes", { 0.18, 0.83, 0.39 } },
    too_hard = { "\\u0635\\u0639\\u0628 \\u0639\\u0644\\u064A\\u0647\\u0627 \\u0627\\u0644\\u0622\\u0646", "Too advanced for now", { 0.93, 0.74, 0.19 } },
    too_easy = { "\\u062A\\u062C\\u0627\\u0648\\u0632\\u062A \\u0645\\u0633\\u062A\\u0648\\u0627\\u0647", "Below her level", { 0.62, 0.71, 0.78 } },
    known = { "\\u062A\\u0639\\u0631\\u0641 \\u0648\\u0635\\u0641\\u0627\\u062A\\u0647", "Recipes already known", { 0.62, 0.71, 0.78 } },
    fun = { "\\u064A\\u0633\\u0644\\u0651\\u064A\\u0647\\u0627\\u0020\\u0648\\u064A\\u062E\\u0641\\u0641\\u0020\\u0627\\u0644\\u0645\\u0644\\u0644", "Fun: lowers boredom", { 0.42, 0.72, 1.0 } },
    illiterate = { "\\u0644\\u0627 \\u062A\\u0633\\u062A\\u0637\\u064A\\u0639 \\u0627\\u0644\\u0642\\u0631\\u0627\\u0621\\u0629", "Cannot read", { 0.94, 0.47, 0.43 } },
}
function Page:drawBooks(y)
    local ar = isAr()
    text(self, ar and "\\u0627\\u0644\\u0643\\u062A\\u0628 \\u0648\\u0627\\u0644\\u0645\\u062C\\u0644\\u0627\\u062A \\u0641\\u064A \\u062D\\u0642\\u064A\\u0628\\u0629 \\u0633\\u0648\\u0644" or "Books and magazines in Sol's bag", CX, y + 6, CW - 6, SCALE_SEC, "right", { 0.42, 0.72, 1.0 }); y = y + 34
    local st = U.recipeStats
    local line = st and (ar and ("\\u0648\\u0635\\u0641\\u0627\\u062A \\u062A\\u062D\\u062A\\u0627\\u062C \\u062A\\u0639\\u0644\\u0651\\u0645\\u064B\\u0627: \\u062A\\u0639\\u0631\\u0641 " .. st.known .. " \\u0645\\u0646 " .. st.learnable .. "   (\\u0643\\u0644 \\u0627\\u0644\\u0648\\u0635\\u0641\\u0627\\u062A: " .. st.total .. ")")
        or ("Learnable recipes known: " .. st.known .. " / " .. st.learnable .. "   (all recipes: " .. st.total .. ")"))
        or (ar and "\\u064A\\u064F\\u062D\\u0633\\u0628 \\u0645\\u0627 \\u062A\\u0639\\u0631\\u0641\\u0647 \\u0645\\u0646 \\u0627\\u0644\\u0648\\u0635\\u0641\\u0627\\u062A..." or "Checking known recipes...")
    text(self, line, CX, y, CW - 6, SCALE_TXT, "right", { 0.62, 0.71, 0.78 }); y = y + 28
    if #(self.books or {}) == 0 then
        text(self, ar and "\\u0644\\u0627 \\u062A\\u0648\\u062C\\u062F \\u0643\\u062A\\u0628 \\u0623\\u0648 \\u0645\\u062C\\u0644\\u0627\\u062A \\u0641\\u064A \\u062D\\u0642\\u064A\\u0628\\u062A\\u0647\\u0627. \\u0636\\u0639\\u0647\\u0627 \\u0641\\u064A \\u062D\\u0642\\u064A\\u0628\\u062A\\u0647\\u0627 \\u0644\\u062A\\u062A\\u0639\\u0644\\u0645 \\u0645\\u0646\\u0647\\u0627." or "No books or magazines in her bag. Put one there so she can learn.", CX, y, CW - 6, SCALE_TXT, "right")
        return y + 44
    end
    for _, b in ipairs(self.books) do
        local stx = BOOK_STATUS[b.status] or BOOK_STATUS.known
        text(self, b.name, CX + 120, y, CW - 126, SCALE_TXT, "right")
        local sub = (ar and stx[1] or stx[2]) .. (b.pages > 0 and ("   " .. b.read .. "/" .. b.pages) or "")
        text(self, sub, CX + 120, y + 18, CW - 126, 0.44, "right", stx[3])
        if b.status == "useful" or b.status == "teaches" or b.status == "fun" then
            local r = { CX, y + 4, 110, 32 }
            local t = tex("pg_btn"); if t then self:drawTextureScaled(t, r[1], r[2], r[3], r[4], 1, 1, 1, 1) end
            text(self, ar and "\\u0627\\u0642\\u0631\\u0626\\u064A" or "Read", r[1], r[2] + 3, r[3], SCALE_TXT, "center")
            self.hits[#self.hits + 1] = { r = r, kind = "read", it = b }
        end
        y = y + 44
    end
    return y
end

function Page:render()
    if not self.dd then return end
    local dd = self.dd
    local n = #dd.it.options
    local h = math.min(300, n * 30 + 8)
    local y = math.min(dd.y, H - h - 8)
    self:drawTextureScaled(tex("pg_list"), CX, y, CW, h, 1, 1, 1, 1)
    dd.rects = {}
    for i = 1, n do
        local ry = y + 4 + (i - 1) * 30
        if ry + 30 > y + h then break end
        if i == dd.it.selected then self:drawTextureScaled(tex("pg_list_sel"), CX, ry, CW, 30, 1, 1, 1, 1) end
        text(self, dd.it.options[i], CX + 8, ry + 2, CW - 16, SCALE_TXT, "right")
        dd.rects[i] = { CX, ry, CW, 30 }
    end
end

function Page:isTopTab(id) for _, tb in ipairs(U.pageTabs()) do if tb.id == id then return true end end return false end
function Page:onMouseWheel(del) self.scroll = math.max(0, self.scroll + (del > 0 and 48 or -48)); return true end
function Page:onMouseDown(x, y)
    if y < HEAD and x > 130 then self.dragging = true; self.dx, self.dy = x, y end
    return true
end
function Page:onMouseMove() if self.dragging then self:setX(self:getX() + self:getMouseX() - self.dx); self:setY(self:getY() + self:getMouseY() - self.dy) end end
function Page:onMouseMoveOutside() self:onMouseMove() end
function Page:onMouseUpOutside() self.dragging = false end
function Page:onMouseUp(x, y)
    if self.dragging then self.dragging = false; return true end
    if self.dd then
        for i, r in pairs(self.dd.rects or {}) do
            if inside(x, y, r) then U.chooseOption(self.dd.it.ref, i); break end
        end
        self.dd = nil; self:refresh(true, true); return true
    end
    if inside(x, y, { 16, 12, 110, 32 }) then U.closePage(); return true end
    for _, t in ipairs(self.tabRects or {}) do
        if inside(x, y, t.r) then self.tab = t.id; self.scroll = 0; self:refresh(true); return true end
    end
    for _, h in ipairs(self.hits or {}) do
        if inside(x, y, h.r) then
            if h.kind == "button" then U.pressButton(h.it.ref)
            elseif h.kind == "combo" then self.dd = { it = h.it, y = h.r[2] + 36 }; return true
            elseif h.kind == "tick" then U.toggleTick(h.it.ref, h.index)
            elseif h.kind == "read" then if U.solRead then U.solRead(h.it.item) end; self:refresh(true); return true
            elseif h.kind == "lf" then U.issueLF(h.command); self:refresh(true); return true end
            self:refresh(true, true); return true
        end
    end
    return true
end

function U.openPage(tab, companionId)
    U.pageCompanionId = companionId
    if not U.page then
        local sw, sh = getCore():getScreenWidth(), getCore():getScreenHeight()
        local x, y = math.floor((sw - W) / 2), math.max(0, math.floor((sh - H) / 2))
        if U.panel then x = U.panel:getX(); y = math.max(0, math.min(U.panel:getY(), sh - H)) end
        U.page = Page:new(x, y)
        U.page:initialise(); U.page:instantiate(); U.page:addToUIManager()
    end
    if U.hidePanel then U.hidePanel() end
    U.page.tab = tab or "status"; U.page.scroll = 0; U.page.dd = nil
    U.page:refresh(true)
    U.page:setVisible(true); U.page:bringToTop()
    return true
end
function U.closePage()
    if U.page then U.page:setVisible(false) end
    if U.showPanel then U.showPanel() end
end
