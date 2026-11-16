-- SolContextAR.lua - Arabic in the right-click menus of Living Fellows and Sol.
-- The game draws menu text with its own font, which cannot show connected Arabic, and Living Fellows' menu now receives Arabic
-- as \uXXXX escapes (Sol's translation layer). This module makes those entries readable without touching any other menu:
--   addOption   an entry whose name is Arabic (\uXXXX) is stored under a short placeholder token padded to the Arabic width,
--               so the game still sizes the menu correctly and never tries to draw the escapes.
--   render      while the menu draws, the game's drawText is replaced for placeholder tokens only: it draws the Arabic with Sol's
--               font (SolText) in the same row, with the SAME colour the game chose (white on hover, grey when disabled, ...).
-- Every other entry, and every other menu, goes through the game's own code untouched.
-- Dialogs (v0.3): the game's ISModalDialog and ISTextBox draw their message with drawTextCentre and size themselves from the text they
--   are given. An Arabic (\\uXXXX) message is wrapped into lines that fit, each line becomes a padded placeholder, the dialog sizes itself
--   from those, and drawTextCentre / drawText draw the real Arabic lines with Sol's font. The yes / no / ok buttons get Arabic titles
--   the same way. The dialog's logic (what Yes does) is not touched at all.
require "ISUI/ISContextMenu"
require "SolText"
SolContextAR = SolContextAR or {}
local M = SolContextAR
M.VERSION = "0.4.2"
M.enOf = M.enOf or {}   -- Arabic text -> its English original (filled by SolUIShami): a placeholder that leaks into a menu the game draws itself then reads as English, not as "~ar3~"
local function log(m) print("[SolContextAR] " .. tostring(m)) end
local byKey, byToken, counter = {}, {}, 0
local function isArabicEscape(s) return type(s) == "string" and (string.find(s, "\\u06", 1, true) ~= nil or string.find(s, "\\uFB", 1, true) ~= nil) end
M.isArabicEscape = isArabicEscape

-- Sol's name: Living Fellows puts the companion's English name ("Sol Survivor", "Sol") into the menu; here it reads "Sol" in Arabic
local NAME_AR = "\\u0633\\u0648\\u0644"
-- names the game stores in the save in English (the camp and its first zone); only their display changes, the saved name does not
local DATA_NAMES = {
    ["Sol Survivor"] = NAME_AR,
    ["Main Camp"] = "\\u0627\\u0644\\u0645\\u062E\\u064A\\u0645 \\u0627\\u0644\\u0631\\u0626\\u064A\\u0633\\u064A",
    ["Camp area"] = "\\u0645\\u0646\\u0637\\u0642\\u0629 \\u0627\\u0644\\u0645\\u062E\\u064A\\u0645",
}
-- texts the game draws itself in English (its own option names) that read Arabic when drawn, without changing the option's name (Living Fellows looks it up by that name)
M.display = { ["Medical Check"] = "\\u0641\\u062D\\u0635 \\u0637\\u0628\\u064A" }

function M.arabize(name)
    if name == "Sol" then return NAME_AR end
    if type(name) ~= "string" then return name end
    if DATA_NAMES[name] then return DATA_NAMES[name] end
    if isArabicEscape(name) then
        for en, ar in pairs(DATA_NAMES) do
            if string.find(name, en, 1, true) then name = string.gsub(name, en, ar) end
        end
    end
    return name
end

local function fontScale(font)
    local h = 16
    local tm = getTextManager and getTextManager()
    if tm then h = tm:MeasureFont(font or UIFont.Small) end
    return math.max(0.42, math.min(0.9, h / 27))
end

-- a unique ASCII token (never drawn) whose width in the game's font matches the Arabic text
function M.tokenFor(ar, font, plain)
    local key = tostring(font) .. "|" .. ar
    local t = byKey[key]
    if t then return t end
    local en = M.enOf and M.enOf[ar]
    local base
    if type(en) == "string" and en ~= "" then base = en .. " "
    elseif plain then base = "Sol "            -- a menu entry with no English original (a text built at run time): a clean name, never a code
    else counter = counter + 1; base = "~ar" .. counter .. "~" end
    local tm = getTextManager and getTextManager()
    local wAr = (SolText and SolText.width and SolText.width(ar, fontScale(font))) or 0
    if tm and wAr > 0 then
        local sw = math.max(1, tm:MeasureStringX(font, " "))
        local pad = math.ceil((wAr - tm:MeasureStringX(font, base)) / sw)
        if pad > 0 then base = base .. string.rep(" ", pad) end
    end
    -- two different Arabic texts with the same English original must not share a placeholder
    while byToken[base] ~= nil and byToken[base] ~= ar do base = base .. " " end
    byKey[key] = base
    byToken[base] = ar
    return base
end

local dialogs = {}      -- multi-line placeholder text -> { lines = { Arabic line, ... } }
local AR_YES, AR_NO, AR_OK = "\\u0646\\u0639\\u0645", "\\u0644\\u0627", "\\u0645\\u0648\\u0627\\u0641\\u0642"

-- split an Arabic message into lines no wider than maxW (words are never cut; a real newline always breaks)
function M.wrapLines(ar, font, maxW)
    local scale = fontScale(font)
    local function width(t) return (SolText and SolText.width and SolText.width(t, scale)) or 0 end
    local lines = {}
    for para in string.gmatch(ar .. "\n", "(.-)\n") do
        local cur = ""
        for word in string.gmatch(para, "%S+") do
            local try = (cur == "") and word or (cur .. " " .. word)
            if cur ~= "" and width(try) > maxW then lines[#lines + 1] = cur; cur = word else cur = try end
        end
        if cur ~= "" then lines[#lines + 1] = cur end
    end
    if #lines == 0 then lines[1] = ar end
    return lines
end

function M.dialogText(ar, font, maxW)
    local lines = M.wrapLines(M.arabize(ar), font, maxW or 520)
    local tokens = {}
    for i, l in ipairs(lines) do tokens[i] = M.tokenFor(l, font) end
    local text = table.concat(tokens, "\n")
    dialogs[text] = { lines = lines }
    local widest = 0
    for _, l in ipairs(lines) do widest = math.max(widest, (SolText and SolText.width and SolText.width(l, fontScale(font))) or 0) end
    log("dialog text: " .. #lines .. " line(s), widest " .. tostring(math.floor(widest)) .. " px, limit " .. tostring(maxW or 520))
    return text
end

local installed = false
function M.install()
    if installed then return true end
    local C = ISContextMenu
    if type(C) ~= "table" or type(C.addOption) ~= "function" or type(C.render) ~= "function" then log("ISContextMenu not found: not installed"); return false end
    installed = true
    local origAdd, origRender = C.addOption, C.render
    C.addOption = function(self, name, ...)
        name = M.arabize(name)
        -- the name another mod reads from this menu (Viewpoint builds its interaction list from it and its Java code draws it) must be readable English
        if isArabicEscape(name) then name = M.tokenFor(name, self.font, true) end
        return origAdd(self, name, ...)
    end
    C.render = function(self)
        local anyArabic = false
        for _, o in ipairs(self.options or {}) do if byToken[o.name] or M.display[o.name] then anyArabic = true break end end
        if not anyArabic then return origRender(self) end
        -- Sol's panel under the entries: the game's own background and border are made invisible for this one draw
        local bgc, brc = self.backgroundColor, self.borderColor
        local themed = false
        if SolTheme and type(bgc) == "table" and type(brc) == "table" and type(self.width) == "number" and type(self.height) == "number" then
            local scrolls = type(self.getScrollHeight) == "function" and type(self.getScrollAreaHeight) == "function" and self:getScrollHeight() > self:getScrollAreaHeight()
            if not scrolls then SolTheme.panel(self, 0, 0, self.width, self.height); themed = true end
        end
        local savedBg, savedBr
        if themed then savedBg, savedBr = bgc.a, brc.a; bgc.a, brc.a = 0, 0 end
        self.drawText = function(s, str, x, y, r, g, b, a, font)
            local ar = byToken[str] or M.display[str]
            if ar == nil then return ISContextMenu.drawText(s, str, x, y, r, g, b, a, font) end
            local ui = SolUI
            if not (ui and ui.drawArabicLine) then return end
            local rowTop = y - ((s.itemHgt or 0) - (s.fontHgt or 0)) / 2
            local opt = s.getOptionFromName and s:getOptionFromName(str) or nil
            local rightPad = (opt and opt.subOption ~= nil) and 22 or 8
            -- plain white text takes the theme's near-white; the grey of a disabled entry and the highlight colours stay as the game chose them
            if themed and r == 1 and g == 1 and b == 1 then local tc = SolTheme.c.text; r, g, b = tc[1], tc[2], tc[3] end
            ui.drawArabicLine(s, ar, x, rowTop, (s.width or 100) - x - rightPad, s.itemHgt or 20, font or s.font, r, g, b, a, "right")
        end
        origRender(self)
        self.drawText = nil
        if themed then bgc.a, brc.a = savedBg, savedBr end
    end
    -- dialogs and buttons ------------------------------------------------------------------------------------------------------
    local E = ISUIElement
    local origText, origCentre
    local function fh(font) local tm = getTextManager and getTextManager(); return tm and tm:getFontHeight(font or UIFont.Small) or 16 end
    -- draw a single-line placeholder as its Arabic text over the width the placeholder occupies; false when it is not one of ours
    local function drawTokenAt(self, str, x, y, r, g, b, a, font)
        local ar = byToken[str]
        local ui = SolUI
        if ar == nil or not (ui and ui.drawArabicLine) then return false end
        local tw = getTextManager():MeasureStringX(font, str)
        ui.drawArabicLine(self, ar, x, y, tw, fh(font), font, r, g, b, a, "center")
        return true
    end
    if type(E) == "table" and type(E.drawText) == "function" and type(E.drawTextCentre) == "function" then
        origText, origCentre = E.drawText, E.drawTextCentre
        E.drawTextCentre = function(self, str, x, y, r, g, b, a, font)
            local d = dialogs[str]
            local ui = SolUI
            if d ~= nil and ui and ui.drawArabicLine then
                local f, w = font or UIFont.Small, (self.width or 400) - 20
                for i, l in ipairs(d.lines) do ui.drawArabicLine(self, l, x - w / 2, y + (i - 1) * fh(f), w, fh(f), f, r, g, b, a, "center") end
                return
            end
            local ar = byToken[str]
            if ar ~= nil and ui and ui.drawArabicLine then
                local tw = getTextManager():MeasureStringX(font, str)
                ui.drawArabicLine(self, ar, x - tw / 2, y, tw, fh(font), font, r, g, b, a, "center")
                return
            end
            return origCentre(self, str, x, y, r, g, b, a, font)
        end
        E.drawText = function(self, str, x, y, r, g, b, a, font)
            -- not inside a context menu render (it has its own override)
            if rawget(self, "drawText") == nil and drawTokenAt(self, str, x, y, r, g, b, a, font) then return end
            return origText(self, str, x, y, r, g, b, a, font)
        end
    else
        log("ISUIElement text functions not found: dialogs not hooked")
    end
    local function now() return (getTimestampMs and getTimestampMs()) or 0 end
    local noop = setmetatable({}, { __index = function() return function() end end })
    local function hookDialog(C, name)
        if type(C) ~= "table" or type(C.new) ~= "function" then return end
        local origNew = C.new
        local alive = {}      -- placeholder text -> { dialog, at }: a repeated click must not stack another copy of the same question
        C.new = function(self, x, y, width, height, text, ...)
            local arabic = isArabicEscape(text)
            if arabic then
                text = M.dialogText(text, UIFont.Small, 520)
                local a = alive[text]
                if a and now() - a.at < 60000 then return setmetatable({}, getmetatable(noop)) end      -- already open: the caller's initialise / addToUIManager do nothing
            end
            local o = origNew(self, x, y, width, height, text, ...)
            if arabic and type(o) == "table" then o.solArabic = true; o.solText = text; alive[text] = { dialog = o, at = now() } end
            return o
        end
        if type(C.prerender) == "function" then
            local origPre = C.prerender
            C.prerender = function(self, ...)
                local bgc, brc = self.backgroundColor, self.borderColor
                if self.solArabic and SolTheme and type(bgc) == "table" and type(brc) == "table" and type(self.width) == "number" and type(self.height) == "number" then
                    SolTheme.panel(self, 0, 0, self.width, self.height)
                    local sa, sb = bgc.a, brc.a
                    bgc.a, brc.a = 0, 0
                    local r1, r2 = origPre(self, ...)
                    bgc.a, brc.a = sa, sb
                    return r1, r2
                end
                return origPre(self, ...)
            end
        end
        if type(C.destroy) == "function" then
            local origDestroy = C.destroy
            C.destroy = function(self, ...)
                local a = self.solText and alive[self.solText]
                if a and a.dialog == self then alive[self.solText] = nil end
                return origDestroy(self, ...)
            end
        end
        if type(C.initialise) == "function" then
            local origInit = C.initialise
            C.initialise = function(self, ...)
                local r1, r2 = origInit(self, ...)
                if self.solArabic then
                    for field, ar in pairs({ yes = AR_YES, no = AR_NO, ok = AR_OK }) do
                        local b = self[field]
                        if type(b) == "table" and type(b.title) == "string" then
                            b.title = M.tokenFor(ar, b.font or UIFont.Small)
                            if SolTheme then
                                local good = (field == "no") and SolTheme.c.red or SolTheme.c.green
                                b.backgroundColor = { r = SolTheme.c.bg[1], g = SolTheme.c.bg[2], b = SolTheme.c.bg[3], a = 0.95 }
                                b.backgroundColorMouseOver = { r = SolTheme.c.line[1], g = SolTheme.c.line[2], b = SolTheme.c.line[3], a = 1 }
                                b.borderColor = { r = good[1], g = good[2], b = good[3], a = 1 }
                            end
                            -- on the button itself: this wins over any class-level lookup, so the title can never reach the screen as a placeholder
                            if origText then
                                b.drawText = function(btn, str, x, y, r, g, bl, a, font)
                                    if drawTokenAt(btn, str, x, y, r, g, bl, a, font) then return end
                                    return origText(btn, str, x, y, r, g, bl, a, font)
                                end
                            end
                        end
                    end
                end
                return r1, r2
            end
        end
        log("dialog hook: " .. name)
    end
    hookDialog(ISModalDialog, "ISModalDialog")
    hookDialog(ISTextBox, "ISTextBox")
    log("installed v" .. M.VERSION)
    return true
end

M.install()
if Events and Events.OnGameStart then Events.OnGameStart.Add(function() M.install() end) end
log("ready v" .. M.VERSION)
