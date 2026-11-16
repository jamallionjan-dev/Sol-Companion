-- SolOverlay.lua - Sol's Arabic over the game world: the speech bubble above her head and the labels of the base layout.
-- The game's own world text (chat bubbles, the zone names on the ground, the layout legend) is drawn with its font, which cannot show
-- connected Arabic. Sol's font (SolText) draws through a UI element, so this file keeps one tiny invisible element and, every frame,
-- draws what the hooks (apply_hooks_batch7.py) handed it:
--   SolBubble.speak(actor, line, ms)   an Arabic line above the actor's head (an English line is refused, so the game's bubble runs)
--   SolOverlay.label(value, sx, sy, color, alpha)   a label on the ground, centred (refused when there is no Arabic for it)
--   SolOverlay.text(value, x, y, color, alpha)      a legend line (refused when there is no Arabic for it)
-- Every entry point answers false when it cannot draw, and the caller then draws the original text, so nothing ever disappears.
SolUI = SolUI or {}
SolOverlay = SolOverlay or {}
SolBubble = SolBubble or {}
local O, B = SolOverlay, SolBubble
O.VERSION = "0.2.0"
local HEAD_Z = 0.9          -- how far above her feet (in floors) the bubble's tail points
local MAX_W = 300           -- widest bubble text, in pixels
local function log(m) print("[SolOverlay] " .. tostring(m)) end
local function now() return (getTimestampMs and getTimestampMs()) or 0 end
local function isArabic(s) return type(s) == "string" and (string.find(s, "\\u06", 1, true) ~= nil or string.find(s, "\\uFB", 1, true) ~= nil) end
local function fontScale(font)
    local h = 16
    local tm = getTextManager and getTextManager()
    if tm then h = tm:MeasureFont(font or UIFont.Small) end
    return math.max(0.42, math.min(0.9, h / 27))
end
local function width(ar, font) return (SolText and SolText.width and SolText.width(ar, fontScale(font))) or 0 end

-- English text -> Arabic text (\uXXXX escapes); filled by SolLabels.lua
O.dict = O.dict or {}
function O.addMap(t) for k, v in pairs(t) do O.dict[k] = v end end
function O.map(value)
    if type(value) ~= "string" then return nil end
    local ar = O.dict[value]
    if ar then return ar end
    local head, tail = string.match(value, "^(.-)%s*(%b())$")        -- "Base layout (INSERT)": the text, then a key hint
    if head and head ~= "" and O.dict[head] then return O.dict[head] .. " " .. tail end
    return nil
end

local panel, frame, bubbles = nil, {}, {}

function O.label(value, sx, sy, color, alpha)
    local ar = panel and O.map(value)
    if not ar then return false end
    frame[#frame + 1] = { ar = ar, x = sx, y = sy, c = color, a = alpha or 1, centre = true }
    return true
end
function O.text(value, x, y, color, alpha)
    local ar = panel and O.map(value)
    if not ar then return false end
    frame[#frame + 1] = { ar = ar, x = x, y = y, c = color, a = alpha or 1, centre = false }
    return true
end

function B.speak(actor, line, ms)
    if not panel or actor == nil or not isArabic(line) then return false end
    local lines = SolContextAR and SolContextAR.wrapLines and SolContextAR.wrapLines(line, UIFont.Small, MAX_W) or { line }
    local t = now()
    bubbles[tostring(actor)] = { actor = actor, lines = lines, born = t, expire = t + (type(ms) == "number" and ms or 8000) }
    return true
end

local function actorScreen(actor)
    if type(actor.getX) ~= "function" or type(isoToScreenX) ~= "function" or type(isoToScreenY) ~= "function" then return nil end
    local x, y, z = actor:getX(), actor:getY(), actor:getZ()
    if type(x) ~= "number" or type(y) ~= "number" or type(z) ~= "number" then return nil end
    local sx, sy = isoToScreenX(0, x, y, z), isoToScreenY(0, x, y, z + HEAD_Z)
    if type(sx) ~= "number" or type(sy) ~= "number" then return nil end
    return sx, sy
end

local function drawFrame(ui)
    local draw = SolUI.drawArabicLine
    local font = UIFont.Small
    local tm = getTextManager()
    local fh = tm:getFontHeight(font)
    local items = frame
    frame = {}
    for i = 1, #items do
        local it = items[i]
        local w = width(it.ar, font)
        local c = it.c or { r = 1, g = 1, b = 1 }
        local x = it.centre and (it.x - w / 2) or it.x
        draw(ui, it.ar, x + 1, it.y + 1, w, fh, font, 0.02, 0.02, 0.02, math.min(0.94, it.a), it.centre and "center" or "left")
        draw(ui, it.ar, x, it.y, w, fh, font, c.r or 1, c.g or 1, c.b or 1, it.a, it.centre and "center" or "left")
    end
    -- speech bubbles
    local t = now()
    local screenW = (getCore and getCore() and getCore():getScreenWidth()) or 0
    for key, b in pairs(bubbles) do
        if t >= b.expire then
            bubbles[key] = nil
        else
            local sx, sy = actorScreen(b.actor)
            if sx and (screenW == 0 or (sx > -200 and sx < screenW + 200)) then
                local textW = 0
                for _, l in ipairs(b.lines) do textW = math.max(textW, width(l, font)) end
                local boxW, boxH = textW + 16, #b.lines * fh + 10
                local bx, by = sx - boxW / 2, sy - boxH - 6
                local fade = math.min(1, (b.expire - t) / 600, (t - b.born) / 150 + 0.15)
                local tc = SolTheme and SolTheme.c.text or { 1, 0.97, 0.82 }
                if SolTheme then
                    SolTheme.rounded(ui, bx, by, boxW, boxH, 8, SolTheme.c.panel, 0.92 * fade, SolTheme.c.border, 0.9 * fade)
                else
                    ui:drawRect(bx, by, boxW, boxH, 0.62 * fade, 0.03, 0.05, 0.08)
                    ui:drawRectBorder(bx, by, boxW, boxH, 0.9 * fade, 0.55, 0.62, 0.7)
                end
                for i, l in ipairs(b.lines) do
                    draw(ui, l, bx + 8, by + 5 + (i - 1) * fh, textW, fh, font, tc[1], tc[2], tc[3], fade, "center")
                end
            end
        end
    end
end

function O.install()
    if panel then return true end
    if type(ISUIElement) ~= "table" or type(ISUIElement.new) ~= "function" then log("no UI element class: overlay off"); return false end
    local p = ISUIElement:new(0, 0, 1, 1)
    p:initialise(); p:instantiate()
    p.render = function(self)
        if type(SolUI.drawArabicLine) ~= "function" then frame = {}; return end
        drawFrame(self)
    end
    p:addToUIManager()
    if type(p.setAlwaysOnTop) == "function" then p:setAlwaysOnTop(true) end
    panel = p
    log("installed v" .. O.VERSION)
    return true
end
function O.isInstalled() return panel ~= nil end
if Events and Events.OnGameStart then Events.OnGameStart.Add(O.install) end
log("ready v" .. O.VERSION)
