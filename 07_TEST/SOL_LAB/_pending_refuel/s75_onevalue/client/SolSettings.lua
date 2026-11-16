-- SolSettings.lua - Sol settings window, section "Sol mind connection system".
-- Talks to Sol Mind through two files in the Zomboid Lua folder:
--   SolSettings_Request.txt (written here)  /  SolSettings_State.txt (written by Sol Mind)
-- API keys typed here go to Sol Mind once and are scrubbed there; only a hint comes back.
require "ISUI/ISPanel"
require "ISUI/ISTextEntryBox"

SolUI = SolUI or {}
local U = SolUI
U.SETTINGS_VERSION = "0.2.4"
local TEX = "media/textures/SolUI/"
local REQ, STATE = "SolSettings_Request.txt", "SolSettings_State.txt"
local W, H = 600, 800
local CHIP_W, CHIP_H, CHIP_Y, CHIP_GAP = 104, 38, 136, 9
local CHIPS = { "api", "local", "bridge", "manual", "none" }
local RC = {
    back = { 24, 8, 100, 40 },
    lblProvider = { 22, 190, 556, 24 }, keyPageBtn = { 22, 216, 128, 42 }, providerField = { 158, 216, 420, 42 },
    lblKey = { 22, 262, 556, 24 }, fetchBtn = { 22, 288, 120, 42 }, pasteBtn = { 150, 288, 64, 42 }, keyField = { 222, 288, 356, 42 },
    lblModels = { 22, 336, 556, 24 }, list = { 22, 362, 556, 230 },
    customBaseLabel = { 22, 336, 556, 24 }, customBaseField = { 22, 362, 556, 42 },
    customModelsLabel = { 22, 408, 556, 24 }, customList = { 22, 434, 556, 158 },
    warnLine = { 22, 598, 556, 22 }, lblFallback = { 22, 622, 556, 24 }, fallbackField = { 22, 648, 556, 42 },
    info = { 22, 200, 556, 120 }, statusText = { 22, 704, 520, 30 }, statusDot = { 564, 712, 14, 14 },
    saveBtn = { 22, 754, 110, 40 }, testBtn = { 140, 754, 110, 40 }, dropdown = { 22, 258, 556, 510 },
    disconnectBtn = { 258, 754, 150, 40 },
}
local ROW_H, ROWS, DD_ROW_H = 44, 5, 44
local PROVIDERS = {
    { id = "auto", name = "Auto (detect from key)" },
    { id = "custom", name = "Custom URL (iPhone)" },
    { id = "anthropic", name = "Anthropic (Claude)", page = "https://platform.claude.com/settings/keys" },
    { id = "openai", name = "OpenAI", page = "https://platform.openai.com/api-keys" },
    { id = "gemini", name = "Google Gemini", page = "https://aistudio.google.com/apikey" },
    { id = "openrouter", name = "OpenRouter", page = "https://openrouter.ai/settings/keys" },
    { id = "groq", name = "Groq", page = "https://console.groq.com/keys" },
    { id = "xai", name = "xAI (Grok)", page = "https://console.x.ai" },
    { id = "deepseek", name = "DeepSeek", page = "https://platform.deepseek.com/api_keys" },
    { id = "mistral", name = "Mistral", page = "https://console.mistral.ai/api-keys" },
    { id = "opencode", name = "OpenCode Zen", page = "https://opencode.ai/zen" },
}
local FALLBACKS = { "none", "manual", "ollama" }
local STATUS_CODES = {
    idle = 1, working = 1, models_ok = 1, saved = 1, test_ok = 1, opened = 1, key_removed = 1, invalid_key = 1, forbidden = 1,
    not_found = 1, rate_limited = 1, no_credit = 1, unreachable = 1, timeout = 1, bad_response = 1, no_key = 1, clipboard_empty = 1,
    no_model = 1, empty_reply = 1, not_a_key = 1, not_chat_model = 1, source_has_no_test = 1, no_base_url = 1, mind_offline = 1, unknown_error = 1, unsupported_model = 1,
    bridge_ok = 1, bridge_not_connected = 1, free_tier_app_only = 1, blocked_by_firewall = 1,
}
local GOOD = { test_ok = 1, models_ok = 1, saved = 1, opened = 1, key_removed = 1, bridge_ok = 1 }
local OFFLINE_MS = 30000  -- model discovery can take up to 20 seconds over the iPhone connection

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
local function log(m) print("[SolUI] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function inside(x, y, r) return x >= r[1] and y >= r[2] and x < r[1] + r[3] and y < r[2] + r[4] end
local function lang() return (U.lang and U.lang()) or "ar" end
local function providerById(id)
    for _, p in ipairs(PROVIDERS) do if p.id == id then return p end end
    return nil
end
local function modelLayout(s)
    if s.source == "api" and s.provider == "custom" then
        return RC.customModelsLabel, RC.customList, 3
    end
    return RC.lblModels, RC.list, ROWS
end
local function chipRect(i) return { 22 + (#CHIPS - i) * (CHIP_W + CHIP_GAP), CHIP_Y, CHIP_W, CHIP_H } end

-- ---------------------------------------------------------------- file channel
local function esc(v) return (tostring(v):gsub("%%", "%%25"):gsub("\r", ""):gsub("\n", "%%0A"):gsub("=", "%%3D")) end
local function unesc(v) return (v:gsub("%%0A", "\n"):gsub("%%3D", "="):gsub("%%25", "%%")) end

function U.readSettingsState()
    local ok, reader = pcall(getFileReader, STATE, false)
    if not ok or not reader then return nil end
    local st = {}
    local line = reader:readLine()
    while line ~= nil do
        local k, v = string.match(line, "^([^=]+)=(.*)$")
        if k then st[k] = unesc(v) end
        line = reader:readLine()
    end
    reader:close()
    if st.ack == nil then return nil end
    return st
end

local lastId = 0
function U.sendSettingsRequest(fields)
    local id = math.max(lastId + 1, math.floor(nowMs()))
    lastId = id
    local parts = { "id=" .. tostring(id) .. "\n" }
    for k, v in pairs(fields) do parts[#parts + 1] = k .. "=" .. esc(v) .. "\n" end
    local ok, writer = pcall(getFileWriter, REQ, true, false)
    if not ok or not writer then log("cannot write settings request"); return nil end
    writer:write(table.concat(parts))
    writer:close()
    return id
end

-- ---------------------------------------------------------------- window
local Settings = ISPanel:derive("SolSettings")
U.SettingsClass = Settings

function Settings:new(x, y)
    local o = ISPanel:new(x, y, W, H)
    setmetatable(o, self); self.__index = self
    o.background = false
    o.s = { source = "api", provider = "auto", model = "", fallback = "none", base = "http://localhost:11434",
            models = {}, status = "idle", code = "idle", hint = "", detected = "", latency = "", detail = "", scroll = 0,
            pending = nil, pendingAt = 0, lastPoll = 0, adopted = false, ddOpen = false }
    return o
end

local function styleBox(b)
    b.backgroundColor = { r = 0.03, g = 0.07, b = 0.11, a = 1 }
    b.borderColor = { r = 0.21, g = 0.35, b = 0.43, a = 1 }
end

function Settings:createChildren()
    local r = RC.keyField
    self.keyBox = ISTextEntryBox:new("", r[1], r[2], r[3], r[4])
    self.keyBox:initialise(); self.keyBox:instantiate(); styleBox(self.keyBox)
    self:addChild(self.keyBox)
    self.keyBox:setMasked(true)
    local b = RC.providerField
    self.baseBox = ISTextEntryBox:new(self.s.base, b[1], b[2], b[3], b[4])
    self.baseBox:initialise(); self.baseBox:instantiate(); styleBox(self.baseBox)
    self:addChild(self.baseBox)
    local c = RC.customBaseField
    self.customBaseBox = ISTextEntryBox:new(self.s.base, c[1], c[2], c[3], c[4])
    self.customBaseBox:initialise(); self.customBaseBox:instantiate(); styleBox(self.customBaseBox)
    self:addChild(self.customBaseBox)
    self:updateWidgets()
end

function Settings:updateWidgets()
    local s = self.s
    if self.keyBox then self.keyBox:setVisible(s.source == "api" and not s.ddOpen) end
    if self.baseBox then self.baseBox:setVisible(s.source == "local") end
    if self.customBaseBox then self.customBaseBox:setVisible(s.source == "api" and s.provider == "custom" and not s.ddOpen) end
end

function Settings:baseValue()
    if self.s.source == "local" then return self.baseBox:getText() end
    if self.s.source == "api" and self.s.provider == "custom" then return self.customBaseBox:getText() end
    return ""
end

function Settings:send(fields)
    local id = U.sendSettingsRequest(fields)
    if id then
        self.s.pending = id; self.s.pendingAt = nowMs(); self.s.code = "working"; self.s.status = "working"
    end
    return id
end

function Settings:adoptConfig(st)
    local s = self.s
    if st.source and st.source ~= "" then s.source = st.source end
    if st.provider and st.provider ~= "" then s.provider = st.provider end
    if st.model then s.model = st.model end
    if st.base and st.base ~= "" then
        s.base = st.base
        if self.baseBox then self.baseBox:setText(st.base) end
        if self.customBaseBox then self.customBaseBox:setText(st.base) end
    end
    local fb = st.fallback or ""
    s.fallback = (fb:match("^ollama") and "ollama") or (fb:match("^manual") and "manual") or "none"
    if s.source == "local" then s.provider = "ollama" end
    self:updateWidgets()
end

function Settings:applyState(st)
    local s = self.s
    if st == nil then
        if s.pending == nil and not s.adopted then s.code = "mind_offline"; s.status = "error" end
        return
    end
    local ack = tonumber(st.ack) or 0
    if not s.adopted then self:adoptConfig(st); s.adopted = true end
    if s.pending and ack < s.pending then return end
    if s.pending then
        s.pending = nil
        s.status = st.status or "error"
        s.code = (st.code ~= nil and st.code ~= "") and st.code or (s.status == "ok" and "saved" or "unknown_error")
    end
    s.hint = st.hint or ""
    s.detail = st.detail or ""
    s.detected = st.detected or ""
    s.active = st.active or ""
    s.latency = st.latency or ""
    local models = {}
    for i = 1, tonumber(st.count) or 0 do
        local line = st["m" .. i]
        if line then
            local id, badge, warn, sup = string.match(line, "^(.*)|([%w_]+)|(%d)|(%d)$")
            if id then models[#models + 1] = { id = id, badge = badge, warn = warn == "1", supported = sup == "1" } end
        end
    end
    s.models = models
    local _, _, rows = modelLayout(s)
    if s.scroll > math.max(0, #models - rows) then s.scroll = math.max(0, #models - rows) end
end

function Settings:poll()
    local s = self.s
    local t = nowMs()
    if t - s.lastPoll < 250 then return end
    s.lastPoll = t
    self:applyState(U.readSettingsState())
    if s.pending and t - s.pendingAt > OFFLINE_MS then
        s.pending = nil; s.code = "mind_offline"; s.status = "error"
    end
end

function Settings:draw(name, r, a)
    local t = tex(name); if t then self:drawTextureScaled(t, r[1], r[2], r[3], r[4], a or 1, 1, 1, 1) end
end
function Settings:drawTex(name, x, y, a)
    local t = tex(name); if t then self:drawTextureScaled(t, x, y, t:getWidth(), t:getHeight(), a or 1, 1, 1, 1) end
    return t
end

local function clip(text, n) text = tostring(text or ""); if #text > n then return string.sub(text, 1, n - 2) .. ".." end return text end

function Settings:prerender()
    self:poll()
    local s, l = self.s, lang()
    self:draw("st_bg", { 0, 0, W, H })
    self:draw("st_head_" .. l, { 0, 0, W, 130 })
    for i, key in ipairs(CHIPS) do
        self:draw("st_chip_" .. key .. "_" .. (s.source == key and "on" or "off") .. "_" .. l, chipRect(i))
    end
    if s.source == "api" or s.source == "local" then
        if s.source == "api" then
            self:draw("st_lbl_provider_" .. l, RC.lblProvider)
            self:draw("st_btn_keypage_" .. l, RC.keyPageBtn)
            self:draw("st_field_420", RC.providerField)
            local p = providerById(s.provider)
            local label = p and p.name or s.provider
            if s.provider == "auto" and s.detected ~= "" then
                local d = providerById(s.detected); label = "Auto  -  " .. (d and d.name or s.detected)
            end
            self:drawText(clip(label, 40), RC.providerField[1] + 12, RC.providerField[2] + 11, 0.94, 0.96, 0.98, 1, UIFont.Medium)
            self:drawTex("st_caret", RC.providerField[1] + RC.providerField[3] - 34, RC.providerField[2] + 9)
            self:draw("st_lbl_key_" .. l, RC.lblKey)
            self:draw("st_btn_fetch_" .. l, RC.fetchBtn)
            self:draw("st_btn_paste_" .. l, RC.pasteBtn)
        else
            self:draw("st_lbl_base_" .. l, RC.lblProvider)
            self:draw("st_btn_fetch_" .. l, { RC.keyPageBtn[1], RC.keyPageBtn[2], 120, 42 })
        end
        if s.source == "api" and s.provider == "custom" then
            self:drawText("Custom API URL", RC.customBaseLabel[1], RC.customBaseLabel[2], 0.94, 0.96, 0.98, 1, UIFont.Small)
        end
        local modelsLabel, list = modelLayout(s)
        self:draw("st_lbl_models_" .. l, modelsLabel)
        self:draw("st_list", list)
        self:drawModels()
        self:draw("st_warnline_" .. l, RC.warnLine)
        self:draw("st_lbl_fallback_" .. l, RC.lblFallback)
        self:draw("st_field_556", RC.fallbackField)
        self:draw("st_fb_" .. s.fallback .. "_" .. l, { RC.fallbackField[1] + (l == "ar" and 20 or 14), RC.fallbackField[2], 500, 42 })
        self:drawTex("st_caret", RC.fallbackField[1] + (l == "ar" and 12 or RC.fallbackField[3] - 34), RC.fallbackField[2] + 9)
    else
        self:draw("st_info_" .. s.source .. "_" .. l, RC.info)
    end
    -- status
    local dot = (s.status == "working" or s.pending) and "work" or (GOOD[s.code] and "ok") or (s.code == "idle" and "idle") or "err"
    self:draw("st_dot_" .. dot, RC.statusDot)
    local code = STATUS_CODES[s.code] and s.code or "unknown_error"
    self:draw("st_status_" .. code .. "_" .. l, RC.statusText)
    self:draw("st_btn_save_" .. l, RC.saveBtn)
    if s.source == "api" or s.source == "local" then self:draw("st_btn_test_" .. l, RC.testBtn) end
    -- Disconnect: drawn with plain shapes so it needs no new texture. Lets the
    -- player release the current provider (the key stays stored) and choose
    -- another one, which the settings channel had no way to express before.
    if s.source ~= "none" then
        local d = RC.disconnectBtn
        self:drawRect(d[1], d[2], d[3], d[4], 1, 0.10, 0.05, 0.06)
        self:drawRectBorder(d[1], d[2], d[3], d[4], 1, 0.55, 0.25, 0.25)
        local label = lang() == "ar" and "Disconnect" or "Disconnect"
        self:drawText(label, d[1] + 18, d[2] + 11, 0.92, 0.72, 0.72, 1, UIFont.Small)
    end
    local info = s.status == "error" and (s.detail ~= "" and s.detail or s.code) or (s.active and s.active ~= "" and "active: " .. s.active or "")
    if info ~= "" then self:drawText(clip(info, 68), 22, 736, 0.57, 0.66, 0.72, 1, UIFont.Small) end
end

function Settings:drawModels()
    local s, l = self.s, lang()
    local _, list, rows = modelLayout(s)
    for i = 1, rows do
        local m = s.models[s.scroll + i]
        if not m then break end
        local y = list[2] + 8 + (i - 1) * ROW_H
        if m.id == s.model then self:draw("st_rowsel", { 30, y, 540, 40 }) end
        local a = m.supported and 1 or 0.45
        self:drawText(clip(m.id, 44), 42, y + 11, 0.94, 0.96, 0.98, a, UIFont.Small)
        local bkind = m.supported and m.badge or (m.badge == "nochat" and "nochat" or "unsup")
        local bname = "st_badge_" .. bkind .. "_" .. l
        local badge = tex(bname)
        local bw = badge and badge:getWidth() or 60
        self:drawTex(bname, 560 - bw, y + 8)
        if m.warn then self:drawTex("st_warn", 560 - bw - 28, y + 8) end
    end
    if #s.models > rows then
        local track = list[4] - 16
        local h = math.max(20, track * rows / #s.models)
        local y = list[2] + 8 + (track - h) * s.scroll / (#s.models - rows)
        self:drawRect(list[1] + list[3] - 8, y, 4, h, 0.8, 0.18, 0.64, 1)
    end
end

function Settings:render()
    local s = self.s
    if s.source == "api" and self.keyBox and self.keyBox:isVisible() and self.keyBox:getText() == "" and s.hint ~= "" then
        self:drawText(s.hint, RC.keyField[1] + 10, RC.keyField[2] + 12, 0.45, 0.55, 0.62, 1, UIFont.Small)
    end
    if not s.ddOpen then return end
    local d = RC.dropdown
    self:drawRect(0, 0, W, H, 0.35, 0, 0, 0)
    self:draw("st_dropdown", d)
    for i, p in ipairs(PROVIDERS) do
        local y = d[2] + 9 + (i - 1) * DD_ROW_H
        if p.id == s.provider then self:draw("st_rowsel", { d[1] + 8, y, 540, 40 }) end
        self:drawText(p.name, d[1] + 20, y + 11, 0.94, 0.96, 0.98, 1, UIFont.Small)
        if p.page then self:draw("st_btn_getkey_" .. lang(), { d[1] + 392, y + 4, 150, 32 }) end
    end
end

function Settings:onMouseWheel(del)
    local s = self.s
    local _, list, rows = modelLayout(s)
    if inside(self:getMouseX(), self:getMouseY(), list) then
        s.scroll = math.max(0, math.min(math.max(0, #s.models - rows), s.scroll + (del > 0 and 1 or -1)))
    end
    return true
end

function Settings:onMouseDown(x, y)
    if y < 56 and not inside(x, y, RC.back) then self.dragging = true; self.dragX, self.dragY = x, y end
    return true
end
function Settings:onMouseMove(dx, dy)
    if self.dragging then
        self:setX(self:getX() + self:getMouseX() - self.dragX); self:setY(self:getY() + self:getMouseY() - self.dragY)
    end
end
function Settings:onMouseMoveOutside(dx, dy) self:onMouseMove(dx, dy) end
function Settings:onMouseUpOutside(x, y) self.dragging = false end

-- Key pages open through Sol Mind (default browser). If Sol Mind is not running, fall back to the
-- game's openUrl. No type() check: Java-exposed functions are not plain Lua functions.
function Settings:openPage(p)
    local s = self.s
    if not p or not p.page then return end
    if U.readSettingsState() ~= nil then
        self:send({ action = "open_key_page", provider = p.id })
        return
    end
    local ok = pcall(function() openUrl(p.page) end)
    s.code = ok and "opened" or "mind_offline"; s.status = ok and "ok" or "error"
end

function Settings:onMouseUp(x, y)
    local s = self.s
    if self.dragging then self.dragging = false; return true end
    if s.ddOpen then
        local d = RC.dropdown
        if inside(x, y, d) then
            local i = math.floor((y - d[2] - 9) / DD_ROW_H) + 1
            local p = PROVIDERS[i]
            if p then
                if p.page and inside(x, y, { d[1] + 392, d[2] + 9 + (i - 1) * DD_ROW_H + 4, 150, 32 }) then
                    self:openPage(p)
                else
                    s.provider = p.id; s.detected = ""; s.models = {}; s.model = ""; s.scroll = 0
                end
            end
        end
        s.ddOpen = false; self:updateWidgets(); return true
    end
    if inside(x, y, RC.back) then U.closeSettings(); if U.showPanel then U.showPanel() end; return true end
    for i, key in ipairs(CHIPS) do
        if inside(x, y, chipRect(i)) then
            s.source = key
            if key == "local" then s.provider = "ollama"; s.models = {}; s.model = ""
            elseif key == "api" and s.provider == "ollama" then s.provider = "auto"; s.models = {}; s.model = "" end
            self:updateWidgets(); return true
        end
    end
    if s.source ~= "none" and inside(x, y, RC.disconnectBtn) then
        self:send({ action = "disconnect" })
        s.model = ""; s.models = {}; s.detected = ""; s.hint = ""; s.source = "none"
        s.provider = "auto"; s.scroll = 0
        self:updateWidgets()
        return true
    end
    if inside(x, y, RC.saveBtn) then
        local prov = s.source == "local" and "ollama" or (s.detected ~= "" and s.detected or s.provider)
        self:send({ action = "save", source = s.source, provider = prov, model = s.model,
                    base = self:baseValue(),
                    fallback_provider = s.fallback == "none" and "" or s.fallback, fallback_model = "" })
        return true
    end
    if s.source ~= "api" and s.source ~= "local" then return true end
    if inside(x, y, RC.testBtn) then
        if s.model == "" then s.code = "no_model"; s.status = "error"; return true end
        local prov = s.source == "local" and "ollama" or (s.detected ~= "" and s.detected or s.provider)
        self:send({ action = "test", source = s.source, provider = prov, model = s.model,
                    base = self:baseValue() })
        return true
    end
    if inside(x, y, RC.fallbackField) then
        for i, f in ipairs(FALLBACKS) do
            if f == s.fallback then s.fallback = FALLBACKS[i % #FALLBACKS + 1]; break end
        end
        return true
    end
    local _, list, rows = modelLayout(s)
    if inside(x, y, list) then
        local i = math.floor((y - list[2] - 8) / ROW_H) + 1
        local m = (i >= 1 and i <= rows) and s.models[s.scroll + i] or nil
        if m then
            if m.supported then s.model = m.id
            else s.code = (m.badge == "nochat") and "not_chat_model" or "unsupported_model"; s.status = "error" end
        end
        return true
    end
    if s.source == "local" then
        if inside(x, y, { RC.keyPageBtn[1], RC.keyPageBtn[2], 120, 42 }) then
            self:send({ action = "fetch_models", provider = "ollama", base = self.baseBox:getText() })
        end
        return true
    end
    if inside(x, y, RC.keyPageBtn) then
        local p = providerById(s.detected ~= "" and s.detected or s.provider)
        if p and p.page then self:openPage(p) else s.ddOpen = true; self:updateWidgets() end
        return true
    end
    if inside(x, y, RC.providerField) then s.ddOpen = true; self:updateWidgets(); return true end
    if inside(x, y, RC.fetchBtn) then
        local key = self.keyBox:getText() or ""
        self.keyBox:setText("")
        self:send({ action = "fetch_models", provider = s.provider, key = key, base = self:baseValue() })
        return true
    end
    if inside(x, y, RC.pasteBtn) then
        self.keyBox:setText("")
        self:send({ action = "paste_key", provider = s.provider, base = self:baseValue() })
        return true
    end
    return true
end

-- ---------------------------------------------------------------- lifecycle
function U.openSettings()
    if U.hidePanel then U.hidePanel() end
    if not U.settings then
        local sw = getCore and getCore():getScreenWidth() or 1920
        local sh = getCore and getCore():getScreenHeight() or 1080
        local x, y = math.floor((sw - W) / 2), math.max(0, math.floor((sh - H) / 2))
        if U.panel then x, y = U.panel:getX(), math.max(0, math.min(U.panel:getY(), sh - H)) end
        U.settings = Settings:new(x, y)
        U.settings:initialise(); U.settings:instantiate(); U.settings:addToUIManager()
    end
    U.settings.s.adopted = false
    U.settings:setVisible(true); U.settings:bringToTop()
    log("settings opened v" .. U.SETTINGS_VERSION)
end
function U.closeSettings() if U.settings then U.settings.s.ddOpen = false; U.settings:setVisible(false) end end
