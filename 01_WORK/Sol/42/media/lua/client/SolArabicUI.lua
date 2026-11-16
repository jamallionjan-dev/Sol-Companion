-- SolArabicUI.lua - Arabic for the Living Fellows screens shown in the Sol window.
-- 1) While the Sol window builds its content, Living Fellows' UI.text() returns the Arabic text (SolLF_AR).
--    Outside that build (right-click menus, other mods, vanilla UI) nothing is translated.
-- 2) The game's own widgets are never patched (see below).
require "SolText"
require "SolLF_AR"
require "SolDialogueArabic"

SolUI = SolUI or {}
local U = SolUI
local T = SolText
U.ARABIC_UI_VERSION = "0.3.0"
local function log(m) print("[SolUI] " .. tostring(m)) end

-- ---------------------------------------------------------------- detection (cached per string)
local arCache, arCount = {}, 0
local function hasArabic(s)
    if type(s) ~= "string" or s == "" then return false end
    local v = arCache[s]
    if v == nil then
        v = false
        for _, cp in ipairs(T.codepoints(s)) do if T.isArabic(cp) then v = true; break end end
        arCount = arCount + 1
        if arCount > 4000 then arCache = {}; arCount = 0 end
        arCache[s] = v
    end
    return v
end
U.hasArabic = hasArabic

local function fontScale(font)
    local h = 16
    local tm = getTextManager and getTextManager()
    if tm then h = tm:MeasureFont(font or UIFont.Small) end
    return math.max(0.42, math.min(0.9, h / 27))
end
-- draw one line of Arabic inside [x, x + w], vertically centred in [y, y + h]; shrinks to fit
local function drawAr(ui, text, x, y, w, h, font, r, g, b, a, align)
    local scale = fontScale(font)
    local tw = T.width(text, scale)
    if tw > w and tw > 0 then scale = math.max(scale * 0.62, scale * w / tw) end
    local lh = T.lineHeight(scale)
    T.drawLine(ui, text, x, y + (h - lh * 0.86) / 2, w, { scale = scale, align = align or "right", r = r or 1, g = g or 1, b = b or 1, a = a or 1 })
end
U.drawArabicLine = drawAr

-- ---------------------------------------------------------------- 1) translation during the Sol window build
U.translateDepth = 0
local function fmt(s, args)
    s = string.gsub(s, "%%(%d)", function(n) local v = args[tonumber(n)]; if v == nil then return "%" .. n end; return tostring(v) end)
    return (string.gsub(s, "%%%%", "%%"))
end
function U.translate(key, ...)
    if (U.lang and U.lang() or "ar") ~= "ar" then return nil end
    local s = SolLF_AR[key]
    if not s then return nil end
    return fmt(s, { ... })
end
function U.withArabic(fn, ...)
    U.translateDepth = U.translateDepth + 1
    local ok, a, b = pcall(fn, ...)
    U.translateDepth = U.translateDepth - 1
    if not ok then error(a) end
    return a, b
end
function U.installTranslation()
    local SC = SurvivorCompanion
    if type(SC) ~= "table" or type(SC.UI) ~= "table" or type(SC.UI.text) ~= "function" then return false end
    if SC.UI.solTextHooked then return true end
    local orig = SC.UI.text
    SC.UI.text = function(key, ...)
        local s = U.translate(key, ...)
        if s then return s end
        return orig(key, ...)
    end
    SC.UI.solTextHooked = true
    SC.UI.solTextOriginal = orig
    return true
end

-- ---------------------------------------------------------------- 2) (removed in 0.2.0)
-- 0.1.x patched ISLabel / ISButton / ISTickBox / ISComboBox for the whole game. Once Arabic detection worked it
-- also redrew the game's main menu (2026-10-24). The Living Fellows window is gone and the Sol pages draw their
-- own text, so the game's widgets are no longer touched at all.

U.installTranslation()
if Events and Events.OnGameStart then Events.OnGameStart.Add(function() U.installTranslation() end) end
if T.selfCheck then pcall(T.selfCheck) end
log("Arabic UI ready v" .. U.ARABIC_UI_VERSION)
