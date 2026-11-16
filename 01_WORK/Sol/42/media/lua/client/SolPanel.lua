-- SolPanel.lua - Sol companion panel (design v5.2).
-- A separate UI layer on top of Living Fellows: it does not edit SCUI.lua.
-- Every button calls an existing, proven Living Fellows entry point.
-- Arabic text is pre-rendered into textures (PZ fonts do not shape Arabic).

SolUI = SolUI or {}
local U = SolUI
U.VERSION = "0.2.0"
local TEX = "media/textures/SolUI/"

-- Living Fellows publishes its namespace as the global SurvivorCompanion;
-- its own files use "local SC = SurvivorCompanion". Resolve it at call time.
local function LF()
    local sc = SurvivorCompanion
    if type(sc) == "table" then return sc end
    return nil
end

-- Layout (mirrors layout.json used to generate the textures)
local PW, PH, HEADER = 600, 598, 56
local BTN_W, BTN_H = 270, 74
local COL_RIGHT, COL_LEFT = 310, 20
local ROWS = { 246, 332, 418, 504 }
local R = {
    gear = { 18, 10, 36, 36 }, lang = { 400, 10, 128, 36 }, close = { 556, 12, 32, 32 },
    ring = { 418, 60, 174, 174 }, dot = { 546, 82, 24, 24 },
    status = { 44, 92, 342, 26 }, speech = { 44, 122, 342, 84 },
}
local LAUNCH_W, LAUNCH_H = 134, 166
local LAUNCH_DOT = { 94, 16, 24, 24 }

-- key, column, row, primary, enabled
local BUTTONS = {
    { key = "chat",     col = COL_RIGHT, row = 1, primary = true,  enabled = true, noSol = true },
    { key = "voice",    col = COL_LEFT,  row = 1, primary = true,  enabled = true, noSol = true },
    { key = "bag",      col = COL_RIGHT, row = 2, enabled = true },
    { key = "equip",    col = COL_LEFT,  row = 2, enabled = true },
    { key = "status",   col = COL_RIGHT, row = 3, enabled = true },
    { key = "orders",   col = COL_LEFT,  row = 3, enabled = true },
    { key = "tasks",    col = COL_RIGHT, row = 4, enabled = true },
    { key = "settings", col = COL_LEFT,  row = 4, enabled = true, noSol = true },
}

local texCache = {}
local function tex(name)
    local t = texCache[name]
    if t == nil then
        t = getTexture(TEX .. name .. ".png") or false
        if t == false then print("[SolUI] missing texture " .. name) end
        texCache[name] = t
    end
    return t or nil
end

local function log(msg) print("[SolUI] " .. tostring(msg)) end

local function player()
    if type(getSpecificPlayer) ~= "function" then return nil end
    local ok, p = pcall(getSpecificPlayer, 0)
    return ok and p or nil
end

-- Same rule as SCAIRuntime.actor(): exactly one living companion = Sol.
function U.solActor()
    local SC = LF()
    if SC == nil or type(SC.Registry) ~= "table" or type(SC.Registry.living) ~= "function" then return nil end
    local ok, list = pcall(SC.Registry.living)
    if not ok or type(list) ~= "table" or #list ~= 1 then return nil end
    return list[1]
end

local function solId(actor)
    local SC = LF()
    if actor == nil or SC == nil then return nil end
    if SC.Registry and type(SC.Registry.idOf) == "function" then
        local ok, id = pcall(SC.Registry.idOf, actor)
        if ok and id then return id end
    end
    if SC.GameplayUtil and type(SC.GameplayUtil.idOf) == "function" then
        local ok, id = pcall(SC.GameplayUtil.idOf, actor)
        if ok and id then return id end
    end
    return nil
end

-- ---------------------------------------------------------------- settings
local function store()
    local p = player()
    if not p then return {} end
    local ok, md = pcall(function() return p:getModData() end)
    if not ok or type(md) ~= "table" then return {} end
    md.SolUI = type(md.SolUI) == "table" and md.SolUI or {}
    return md.SolUI
end
function U.lang() local s = store(); return (s.lang == "en") and "en" or "ar" end
function U.setLang(l)
    local new = (l == "en") and "en" or "ar"
    local changed = store().lang ~= new and not (store().lang == nil and new == "ar")
    store().lang = new
    if changed and U.onLangChanged then pcall(U.onLangChanged) end
end

local function screenW() return getCore and getCore():getScreenWidth() or 1920 end
local function screenH() return getCore and getCore():getScreenHeight() or 1080 end
local function clamp(v, lo, hi) if v < lo then return lo elseif v > hi then return hi end return v end

-- ---------------------------------------------------------------- actions
local function needSol(key)
    local a = U.solActor()
    if a == nil then log("action " .. key .. " ignored: Sol not found (needs exactly one living companion)") end
    return a
end

-- Status, Loadout and Orders open inside the Sol-themed window (SolSkin.lua), never the LF look.
-- Chat opens the Sol chat window (SolChat.lua, through Sol Mind), never the old LF talk tab.
local function openTab(tab)
    return function(a, SC)
        if U.openTab then return U.openTab(tab, solId(a)) end
        return SC.UI.open(tab, solId(a))
    end
end
local ACTIONS = {
    bag = function(a, SC) return SC.UI.openInventory(a, player()) end,
    equip = openTab("loadout"),
    status = openTab("status"),
    orders = openTab("orders"),
    tasks = openTab("more"),
}

function U.run(key)
    local fn = ACTIONS[key]
    if not fn then log("action " .. key .. " is not available yet"); return false, "not_available" end
    local SC = LF()
    if SC == nil or type(SC.UI) ~= "table" then log("Living Fellows UI not loaded"); return false, "ui_missing" end
    local a = needSol(key)
    if a == nil then return false, "sol_missing" end
    local ok, err = pcall(fn, a, SC)
    if not ok then log("action " .. key .. " failed: " .. tostring(err)); return false, "exception" end
    return true
end

local function inside(x, y, r) return x >= r[1] and y >= r[2] and x < r[1] + r[3] and y < r[2] + r[4] end
-- green near or awake, yellow dormant far away, grey only when there is no Sol or her systems are not up
local function dotName(sol)
    if type(U.solDotState) == "function" then
        local ok, state = pcall(U.solDotState)
        if ok and state then return "dot_" .. state end
    end
    return sol and "dot_on" or "dot_off"
end
local function buttonRect(b) return { b.col, ROWS[b.row], BTN_W, BTN_H } end

-- ---------------------------------------------------------------- panel
local Panel = ISPanel:derive("SolPanel")
U.PanelClass = Panel

function Panel:new(x, y)
    local o = ISPanel:new(x, y, PW, PH)
    setmetatable(o, self); self.__index = self
    o.background = false
    o.moveWithMouse = false
    o.dragging = false
    return o
end

function Panel:hitButton(x, y)
    for _, b in ipairs(BUTTONS) do
        if inside(x, y, buttonRect(b)) then return b end
    end
    return nil
end

function Panel:prerender()
    local function draw(name, x, y, w, h, a)
        local t = tex(name); if t then self:drawTextureScaled(t, x, y, w, h, a or 1, 1, 1, 1) end
    end
    local lang = U.lang()
    local sol = U.solActor()
    local mx, my = self:getMouseX(), self:getMouseY()
    local over = self:isMouseOver()
    draw("panel_bg", 0, 0, PW, PH)
    draw("lang_" .. lang, R.lang[1], R.lang[2], R.lang[3], R.lang[4])
    draw("portrait_ring", R.ring[1], R.ring[2], R.ring[3], R.ring[4])
    draw(dotName(sol), R.dot[1], R.dot[2], R.dot[3], R.dot[4])
    local far = sol == nil and type(U.solFarState) == "function" and U.solFarState() or nil
    if far and SolText then
        local label = lang == "en" and (far == "coming" and "On her way" or far == "awake" and "Awake" or "Far away") or (far == "coming" and "\\u062C\\u0627\\u064A\\u0629" or far == "awake" and "\\u0641\\u0627\\u064A\\u0642\\u0629" or "\\u0628\\u0639\\u064A\\u062F\\u0629")
        SolText.drawLine(self, SolText.codepoints(label), R.status[1], R.status[2], R.status[3], { scale = 0.5, align = "right", r = 0.95, g = 0.72, b = 0.25 })
    else
        draw("status_" .. (sol and "on" or "off") .. "_" .. lang, R.status[1], R.status[2], R.status[3], R.status[4])
    end
    if far and SolText then
        -- far away: this box is the way to wake her, then what comes next
        self:drawRect(R.speech[1], R.speech[2], R.speech[3], R.speech[4], 0.92, 0.07, 0.16, 0.26)
        local eta = type(U.solFarEta) == "function" and U.solFarEta() or nil
        local left = eta and (" " .. math.floor(eta / 60) .. ":" .. ((eta % 60) < 10 and "0" or "") .. (eta % 60)) or ""
        local text = far == "coming" and ((lang == "en" and "On her way to you" or "\\u062C\\u0627\\u064A\\u0629 \\u0644\\u0639\\u0646\\u062F\\u0643") .. left)
            or far == "awake" and (lang == "en" and "Tell her: come on foot" or "\\u0642\\u0644\\u0647\\u0627 \\u062A\\u0639\\u0627\\u0644\\u064A \\u0645\\u0634\\u064A")
            or (lang == "en" and "Sol, are you awake?" or "\\u0633\\u0648\\u0644 \\u0641\\u0627\\u064A\\u0642\\u0629\\u061F")
        SolText.drawLine(self, SolText.codepoints(text), R.speech[1] + 8, R.speech[2] + 28, R.speech[3] - 16, { scale = 0.62, align = "center", r = 0.95, g = 0.95, b = 0.95 })
        if far == "far" and over and inside(mx, my, R.speech) then self:drawRect(R.speech[1], R.speech[2], R.speech[3], R.speech[4], 0.12, 1, 1, 1) end
    else
        draw("speech_" .. lang, R.speech[1], R.speech[2], R.speech[3], R.speech[4])
    end
    for _, b in ipairs(BUTTONS) do
        local r = buttonRect(b)
        local usable = b.enabled and (sol ~= nil or b.noSol == true)
        draw(b.primary and "btn_primary" or "btn_normal", r[1], r[2], r[3], r[4])
        draw("btn_" .. b.key .. "_" .. lang, r[1], r[2], r[3], r[4], usable and 1 or 0.45)
        if not b.enabled then draw("soon_" .. lang, r[1] + 10, r[2] + 8, lang == "ar" and 54 or 46, 20) end
        if b.key == "voice" and U.voice and U.voice.listening then       -- recording: pulsing red dot
            local a = 0.55 + 0.45 * math.abs(math.sin((getTimestampMs and getTimestampMs() or 0) / 250))
            self:drawRect(r[1] + 12, r[2] + 12, 12, 12, a, 0.94, 0.25, 0.22)
        end
        if over and usable and inside(mx, my, r) then draw("btn_hover", r[1], r[2], r[3], r[4]) end
    end
end

function Panel:onMouseDown(x, y)
    if y < HEADER and not inside(x, y, R.lang) and not inside(x, y, R.close) and not inside(x, y, R.gear) then
        self.dragging = true
        self.dragX, self.dragY = x, y
    end
    return true
end

function Panel:onMouseMove(dx, dy)
    if self.dragging then
        local nx = clamp(self:getX() + self:getMouseX() - self.dragX, 0, screenW() - PW)
        local ny = clamp(self:getY() + self:getMouseY() - self.dragY, 0, screenH() - PH)
        self:setX(nx); self:setY(ny)
    end
end
function Panel:onMouseMoveOutside(dx, dy) self:onMouseMove(dx, dy) end

function Panel:onMouseUp(x, y)
    if self.dragging then
        self.dragging = false
        local s = store(); s.panelX, s.panelY = self:getX(), self:getY()
        return true
    end
    if inside(x, y, R.close) then U.hidePanel(); return true end
    if inside(x, y, R.lang) then
        U.setLang((x < R.lang[1] + R.lang[3] / 2) and "ar" or "en"); return true
    end
    if inside(x, y, R.gear) then if U.openSettings then U.openSettings() end; return true end
    if inside(x, y, R.speech) and type(U.solFarState) == "function" and U.solFarState() == "far" and type(U.sendChat) == "function" then
        local t = getTimestampMs and getTimestampMs() or 0                       -- the button is the same question as typing it in the chat
        if t - (self.farAskedAt or 0) > 5000 then self.farAskedAt = t; U.sendChat({ text = "\\u0633\\u0648\\u0644 \\u0641\\u0627\\u064A\\u0642\\u0629\\u061F" }) end
        return true
    end
    local b = self:hitButton(x, y)
    if b then
        if not b.enabled then log(b.key .. " is not available yet"); return true end
        if b.key == "settings" then if U.openSettings then U.openSettings() end; return true end
        if b.key == "chat" then if U.openChat then U.openChat() end; return true end
        if b.key == "voice" then if U.voiceToggle then U.voiceToggle() end; return true end
        U.run(b.key)
    end
    return true
end
function Panel:onMouseUpOutside(x, y) self.dragging = false end

-- ---------------------------------------------------------------- launcher
local Launcher = ISPanel:derive("SolLauncher")
U.LauncherClass = Launcher

function Launcher:new(x, y)
    local o = ISPanel:new(x, y, LAUNCH_W, LAUNCH_H)
    setmetatable(o, self); self.__index = self
    o.background = false
    o.pressed = false
    o.moved = false
    return o
end

function Launcher:prerender()
    local t = tex("launcher"); if t then self:drawTextureScaled(t, 0, 0, LAUNCH_W, LAUNCH_H, 1, 1, 1, 1) end
    local d = tex(dotName(U.solActor()))
    if d then self:drawTextureScaled(d, LAUNCH_DOT[1], LAUNCH_DOT[2], LAUNCH_DOT[3], LAUNCH_DOT[4], 1, 1, 1, 1) end
end

function Launcher:onMouseDown(x, y)
    self.pressed = true; self.moved = false
    self.downX, self.downY = x, y
    return true
end
function Launcher:onMouseMove(dx, dy)
    if not self.pressed then return end
    local mx, my = self:getMouseX(), self:getMouseY()
    if not self.moved and math.abs(mx - self.downX) + math.abs(my - self.downY) < 5 then return end
    self.moved = true
    self:setX(clamp(self:getX() + mx - self.downX, 0, screenW() - LAUNCH_W))
    self:setY(clamp(self:getY() + my - self.downY, 0, screenH() - LAUNCH_H))
end
function Launcher:onMouseMoveOutside(dx, dy) self:onMouseMove(dx, dy) end
function Launcher:onMouseUp(x, y)
    if not self.pressed then return true end
    self.pressed = false
    if self.moved then
        local s = store(); s.launcherX, s.launcherY = self:getX(), self:getY()
    else
        U.togglePanel()
    end
    return true
end
function Launcher:onMouseUpOutside(x, y) self:onMouseUp(x, y) end

-- ---------------------------------------------------------------- lifecycle
function U.showPanel()
    if not U.panel then
        local s = store()
        local x = tonumber(s.panelX) or math.floor((screenW() - PW) / 2)
        local y = tonumber(s.panelY) or math.floor((screenH() - PH) / 2)
        U.panel = Panel:new(clamp(x, 0, screenW() - PW), clamp(y, 0, screenH() - PH))
        U.panel:initialise(); U.panel:instantiate(); U.panel:addToUIManager()
    end
    U.panel:setVisible(true); U.panel:bringToTop()
end
function U.hidePanel() if U.panel then U.panel:setVisible(false) end end
function U.togglePanel()
    if U.panel and U.panel:isVisible() then U.hidePanel() else U.showPanel() end
end

function U.create()
    if U.launcher then return end
    local s = store()
    local x = clamp(tonumber(s.launcherX) or 70, 0, screenW() - LAUNCH_W)
    local y = clamp(tonumber(s.launcherY) or 20, 0, screenH() - LAUNCH_H)
    U.launcher = Launcher:new(x, y)
    U.launcher:initialise(); U.launcher:instantiate(); U.launcher:addToUIManager()
    U.launcher:setAlwaysOnTop(true)
    log("ready v" .. U.VERSION)
end

if Events and Events.OnGameStart then Events.OnGameStart.Add(U.create) end
