-- SolChat.lua - Sol text chat window. Messages go to Sol Mind through SolChat_Request.txt and the
-- conversation comes back in SolChat_State.txt (ASCII with \uXXXX escapes). Arabic is drawn by SolText.
require "ISUI/ISPanel"
require "ISUI/ISTextEntryBox"
require "SolText"

SolUI = SolUI or {}
local U = SolUI
local T = SolText
U.CHAT_VERSION = "0.2.8"
local REQ, STATE = "SolChat_Request.txt", "SolChat_State.txt"
local W, H = 560, 640
local HEAD, INPUT_H, PAD = 60, 44, 16
local MIC = nil            -- microphone button rect, set in createChildren
local OFFLINE_MS = 8000
local REPLY_TIMEOUT_MS = 120000
local SCALE, SMALL = 0.6, 0.48      -- IBM Plex glyphs at 30 px: 18 px messages, 14 px status

local C = {
    frame = { 0.043, 0.102, 0.149, 0.97 }, header = { 0.059, 0.129, 0.188, 1 }, border = { 0.165, 0.561, 0.847, 1 },
    line = { 0.122, 0.251, 0.345, 1 }, sol = { 0.075, 0.153, 0.220, 1 }, solLine = { 0.173, 0.290, 0.384, 1 },
    me = { 0.102, 0.400, 0.690, 1 }, text = { 0.94, 0.96, 0.98 }, muted = { 0.62, 0.71, 0.78 }, green = { 0.18, 0.83, 0.39 },
    amber = { 0.93, 0.74, 0.19 }, red = { 0.94, 0.47, 0.43 },
}
local MSG = {
    title = "\\u0645\\u0631\\u0627\\u0633\\u0644\\u0629 \\u0633\\u0648\\u0644", send = "\\u0625\\u0631\\u0633\\u0627\\u0644", ready = "\\u0645\\u062A\\u0627\\u062D\\u0629", thinking = "\\u0633\\u0648\\u0644 \\u062A\\u0643\\u062A\\u0628...",
    empty = "\\u0627\\u0643\\u062A\\u0628 \\u0631\\u0633\\u0627\\u0644\\u062A\\u0643 \\u0644\\u0633\\u0648\\u0644 \\u0628\\u0627\\u0644\\u0623\\u0633\\u0641\\u0644. \\u062A\\u064F\\u0631\\u0633\\u0644 \\u0639\\u0628\\u0631 \\u0639\\u0642\\u0644 \\u0633\\u0648\\u0644 \\u0627\\u0644\\u0645\\u062E\\u062A\\u0627\\u0631 \\u0641\\u064A \\u0627\\u0644\\u0625\\u0639\\u062F\\u0627\\u062F\\u0627\\u062A.",
    no_mind = "\\u0644\\u0645 \\u064A\\u064F\\u062E\\u062A\\u0631 \\u0639\\u0642\\u0644 \\u0644\\u0633\\u0648\\u0644 \\u0628\\u0639\\u062F. \\u0627\\u0641\\u062A\\u062D \\u0627\\u0644\\u0625\\u0639\\u062F\\u0627\\u062F\\u0627\\u062A \\u0648\\u0627\\u062E\\u062A\\u0631 \\u0645\\u0635\\u062F\\u0631\\u064B\\u0627 \\u0648\\u0646\\u0645\\u0648\\u0630\\u062C\\u064B\\u0627.",
    mind_offline = "Sol Mind \\u063A\\u064A\\u0631 \\u0645\\u0634\\u063A\\u0651\\u0644. \\u064A\\u0628\\u062F\\u0623 \\u062A\\u0644\\u0642\\u0627\\u0626\\u064A\\u064B\\u0627 \\u0645\\u0639 \\u0627\\u0644\\u0644\\u0639\\u0628\\u0629\\u061B \\u0623\\u0639\\u062F \\u062A\\u0634\\u063A\\u064A\\u0644 \\u0627\\u0644\\u0644\\u0639\\u0628\\u0629 \\u0625\\u0646 \\u0627\\u0633\\u062A\\u0645\\u0631 \\u0630\\u0644\\u0643.",
    rate_limited = "\\u062A\\u062C\\u0627\\u0648\\u0632\\u062A \\u062D\\u062F \\u0627\\u0644\\u0637\\u0644\\u0628\\u0627\\u062A \\u0627\\u0644\\u0645\\u062C\\u0627\\u0646\\u064A\\u0629. \\u062D\\u0627\\u0648\\u0644 \\u0628\\u0639\\u062F \\u0642\\u0644\\u064A\\u0644.",
    invalid_key = "\\u0627\\u0644\\u0645\\u0641\\u062A\\u0627\\u062D \\u0645\\u0631\\u0641\\u0648\\u0636. \\u0627\\u0641\\u062A\\u062D \\u0627\\u0644\\u0625\\u0639\\u062F\\u0627\\u062F\\u0627\\u062A \\u0648\\u0637\\u0628\\u0651\\u0642 \\u0627\\u0644\\u0645\\u0641\\u062A\\u0627\\u062D \\u0645\\u0646 \\u062C\\u062F\\u064A\\u062F.",
    no_credit = "\\u0644\\u0627 \\u064A\\u0648\\u062C\\u062F \\u0631\\u0635\\u064A\\u062F \\u0641\\u064A \\u062D\\u0633\\u0627\\u0628 \\u0627\\u0644\\u0645\\u0632\\u0648\\u0651\\u062F.", unreachable = "\\u062A\\u0639\\u0630\\u0651\\u0631 \\u0627\\u0644\\u0648\\u0635\\u0648\\u0644 \\u0625\\u0644\\u0649 \\u0627\\u0644\\u0645\\u0632\\u0648\\u0651\\u062F. \\u062A\\u062D\\u0642\\u0642 \\u0645\\u0646 \\u0627\\u0644\\u0625\\u0646\\u062A\\u0631\\u0646\\u062A.",
    timeout = "\\u0627\\u0646\\u062A\\u0647\\u062A \\u0645\\u0647\\u0644\\u0629 \\u0627\\u0644\\u0631\\u062F. \\u062D\\u0627\\u0648\\u0644 \\u0645\\u0631\\u0629 \\u0623\\u062E\\u0631\\u0649.", empty_reply = "\\u0639\\u0627\\u062F \\u0627\\u0644\\u0631\\u062F \\u0641\\u0627\\u0631\\u063A\\u064B\\u0627. \\u062D\\u0627\\u0648\\u0644 \\u0645\\u0631\\u0629 \\u0623\\u062E\\u0631\\u0649.",
    chatgpt_link_not_connected = "Sol Link \\u063A\\u064A\\u0631 \\u0645\\u062A\\u0635\\u0644. \\u0627\\u0641\\u062A\\u062D \\u0645\\u062D\\u0627\\u062F\\u062B\\u0629 \\u0633\\u0648\\u0644 \\u0641\\u064A \\u0627\\u0644\\u0645\\u062A\\u0635\\u0641\\u062D\\u060C \\u0623\\u0648 \\u0627\\u062E\\u062A\\u0631 \\u0645\\u0635\\u062F\\u0631\\u064B\\u0627 \\u0622\\u062E\\u0631 \\u0641\\u064A \\u0627\\u0644\\u0625\\u0639\\u062F\\u0627\\u062F\\u0627\\u062A.",
    chatgpt_link_timeout = "\\u0644\\u0645 \\u064A\\u0635\\u0644 \\u0631\\u062F ChatGPT \\u0641\\u064A \\u0627\\u0644\\u0648\\u0642\\u062A. \\u062A\\u0623\\u0643\\u062F \\u0623\\u0646 \\u0645\\u062D\\u0627\\u062F\\u062B\\u0629 \\u0633\\u0648\\u0644 \\u0645\\u0641\\u062A\\u0648\\u062D\\u0629.",
    free_tier_app_only = "\\u0646\\u0645\\u0627\\u0630\\u062C OpenCode \\u0627\\u0644\\u0645\\u062C\\u0627\\u0646\\u064A\\u0629 \\u062A\\u0639\\u0645\\u0644 \\u062F\\u0627\\u062E\\u0644 \\u062A\\u0637\\u0628\\u064A\\u0642\\u0647 \\u0641\\u0642\\u0637. \\u0627\\u062E\\u062A\\u0631 \\u0645\\u0635\\u062F\\u0631\\u064B\\u0627 \\u0622\\u062E\\u0631.",
    voice_listening = "\\u0623\\u0633\\u062A\\u0645\\u0639... \\u062A\\u0643\\u0644\\u0651\\u0645\\u060C \\u062B\\u0645 \\u0627\\u0636\\u063A\\u0637 \\u0632\\u0631 \\u0627\\u0644\\u0635\\u0648\\u062A \\u0645\\u0631\\u0629 \\u0623\\u062E\\u0631\\u0649",
    voice_transcribing = "\\u0623\\u062D\\u0648\\u0651\\u0644 \\u0635\\u0648\\u062A\\u0643 \\u0625\\u0644\\u0649 \\u0646\\u0635...",
    mic_unavailable = "\\u0644\\u0627 \\u064A\\u0648\\u062C\\u062F \\u0645\\u064A\\u0643\\u0631\\u0648\\u0641\\u0648\\u0646 \\u0645\\u062A\\u0627\\u062D \\u0644\\u0640 Sol Mind",
    no_stt_key = "\\u062A\\u062D\\u0648\\u064A\\u0644 \\u0627\\u0644\\u0635\\u0648\\u062A \\u064A\\u062D\\u062A\\u0627\\u062C \\u0645\\u0641\\u062A\\u0627\\u062D Groq \\u0641\\u064A \\u0627\\u0644\\u0625\\u0639\\u062F\\u0627\\u062F\\u0627\\u062A\\u060C \\u0623\\u0648 \\u0627\\u062E\\u062A\\u0631 \\u0627\\u0644\\u062C\\u0633\\u0631",
    stt_failed = "\\u062A\\u0639\\u0630\\u0651\\u0631 \\u062A\\u062D\\u0648\\u064A\\u0644 \\u0627\\u0644\\u0635\\u0648\\u062A \\u0625\\u0644\\u0649 \\u0646\\u0635\\u060C \\u062D\\u0627\\u0648\\u0644 \\u0645\\u0631\\u0629 \\u0623\\u062E\\u0631\\u0649",
    stt_invalid_key = "\\u0645\\u0641\\u062A\\u0627\\u062D Groq \\u0645\\u0631\\u0641\\u0648\\u0636 \\u0641\\u064A \\u062A\\u062D\\u0648\\u064A\\u0644 \\u0627\\u0644\\u0635\\u0648\\u062A",
    stt_rate_limited = "\\u062A\\u062C\\u0627\\u0648\\u0632\\u062A \\u062D\\u062F \\u062A\\u062D\\u0648\\u064A\\u0644 \\u0627\\u0644\\u0635\\u0648\\u062A\\u060C \\u0627\\u0646\\u062A\\u0638\\u0631 \\u0642\\u0644\\u064A\\u0644\\u064B\\u0627",
    too_short = "\\u0627\\u0644\\u062A\\u0633\\u062C\\u064A\\u0644 \\u0642\\u0635\\u064A\\u0631 \\u062C\\u062F\\u064B\\u0627",
    nothing_heard = "\\u0644\\u0645 \\u0623\\u0633\\u0645\\u0639 \\u0643\\u0644\\u0627\\u0645\\u064B\\u0627",
    clear = "\\u0645\\u0633\\u062D",
    unknown_error = "\\u062D\\u062F\\u062B \\u062E\\u0637\\u0623 \\u0623\\u062B\\u0646\\u0627\\u0621 \\u0627\\u0644\\u0631\\u062F.",
}
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function rect(ui, x, y, w, h, c, a) ui:drawRect(x, y, w, h, a or c[4] or 1, c[1], c[2], c[3]) end
local function border(ui, x, y, w, h, c) ui:drawRectBorder(x, y, w, h, c[4] or 1, c[1], c[2], c[3]) end
local function inside(x, y, r) return x >= r[1] and y >= r[2] and x < r[1] + r[3] and y < r[2] + r[4] end

-- ---------------------------------------------------------------- channel
function U.readChatState()
    local ok, reader = pcall(getFileReader, STATE, false)
    if not ok or not reader then return nil end
    local st, line = {}, reader:readLine()
    while line ~= nil do
        local k, v = string.match(line, "^([^=]+)=(.*)$")
        if k then st[k] = v end
        line = reader:readLine()
    end
    reader:close()
    if st.ack == nil then return nil end
    return st
end
local lastId = 0
function U.sendChat(fields)
    local id = math.max(lastId + 1, math.floor(nowMs())); lastId = id
    local parts = { "id=" .. tostring(id) .. "\n" }
    for k, v in pairs(fields) do parts[#parts + 1] = k .. "=" .. v .. "\n" end
    local ok, w = pcall(getFileWriter, REQ, true, false)
    if not ok or not w then return nil end
    w:write(table.concat(parts)); w:close()
    return id
end

-- ---------------------------------------------------------------- window
local Chat = ISPanel:derive("SolChat")
U.ChatClass = Chat

function Chat:new(x, y)
    local o = ISPanel:new(x, y, W, H)
    setmetatable(o, self); self.__index = self
    o.background = false
    o.msgs = {}; o.status = "idle"; o.code = ""; o.scroll = 0; o.contentH = 0
    o.pending = nil; o.pendingAt = 0; o.lastPoll = 0; o.lastCount = -1; o.stickBottom = true
    o.thinkingSince = nil; o.timeoutAck = nil
    return o
end

function Chat:createChildren()
    local w, h = self:getWidth(), self:getHeight()
    MIC = { 112, h - PAD - INPUT_H, 44, INPUT_H }
    self.entry = ISTextEntryBox:new("", 162, h - PAD - INPUT_H, w - 162 - PAD, INPUT_H)      -- 112..156: microphone
    self.entry:initialise(); self.entry:instantiate()
    self.entry.backgroundColor = { r = 0.03, g = 0.07, b = 0.11, a = 1 }
    self.entry.borderColor = { r = 0.21, g = 0.35, b = 0.43, a = 1 }
    local panel = self
    self.entry.onCommandEntered = function() panel:sendCurrent() end
    self:addChild(self.entry)
end

-- Sol patch 2026-10-26: Clear Chat. Sol Mind already handles action=clear; memory is never touched.
local CLEAR = { 54, 14, 64, 32 }
local RESIZE_GRIP = 18
function Chat:solBusy() return self.pending ~= nil or self.status == "thinking" or self.status == "sending" end
function Chat:clearNow()
    if self:solBusy() then return false end
    local id = U.sendChat({ action = "clear" })
    if not id then return false end
    self.msgs = {}; self.lastCount = 0; self.lastSig = nil; self.scroll = 0; self.layoutDirty = true; self.stickBottom = true
    self.clearId = id; self.clearAt = nowMs()
    return true
end
function Chat:sendCurrent()
    -- one message at a time: while Sol is still answering, Send does nothing (the text stays in the box)
    if self.pending ~= nil or self.status == "thinking" or self.status == "sending" then return end
    local text = self.entry:getText() or ""
    local cps = T.codepoints(text)
    local any = false
    for _, cp in ipairs(cps) do if cp ~= 32 then any = true; break end end
    if not any or self.pending then return false end
    local A_ = rawget(_G, "SolAuthority")
    local scoped = type(A_) == "table" and type(A_.on) == "function" and A_.on("task_scoped_perception") == true
    if U.scanNow and not scoped then pcall(U.scanNow) end
    local id = U.sendChat({ text = T.escape(cps) })
    if id then
        self.pending = id; self.pendingAt = nowMs(); self.status = "sending"; self.code = ""
        self.thinkingSince = self.pendingAt; self.timeoutAck = nil; self.offlineAck = nil
        self.msgs[#self.msgs + 1] = { role = "user", cps = cps, local_ = true }
        self.layoutDirty = true
        if U.writeActionCatalog then pcall(U.writeActionCatalog) end      -- fresh action list for this reply
        self.stickBottom = true
        self.entry:setText("")
    end
    return id ~= nil
end

function Chat:mergeMind(st)
    local n = tonumber(st.count) or 0
    local sig = tostring(st.count) .. "|" .. tostring(st["m" .. tostring(st.count)] or "")
    if sig == self.mergeSig then return end
    self.mergeSig = sig; self.lastMindChange = nowMs()
    local msgs = {}
    for i = 1, n do
        local v = st["m" .. i]
        if v then
            local role, txt = string.match(v, "^(%a+)|(.*)$")
            if role then msgs[#msgs + 1] = { role = role, cps = T.unescape(txt) } end
        end
    end
    local mine = nil
    for i = #self.msgs, 1, -1 do if self.msgs[i].local_ then mine = self.msgs[i]; break end end
    if mine then msgs[#msgs + 1] = mine end
    self.msgs = msgs; self.layoutDirty = true
end

function Chat:applyState(st)
    if st == nil then
        if self.pending and nowMs() - self.pendingAt > OFFLINE_MS then self.pending = nil; self.status = "error"; self.code = "mind_offline" end
        if not self.pending and self.lastCount < 0 then self.status = "error"; self.code = "mind_offline" end
        return
    end
    if self.clearId ~= nil then
        if (tonumber(st.ack) or 0) < self.clearId and nowMs() - self.clearAt < 5000 then return end
        self.clearId = nil
    end
    local ack = tonumber(st.ack) or 0
    if self.pending and ack < self.pending then
        -- Sol Mind is still on an earlier message: still SHOW what it has (a reply must never be dropped),
        -- and keep our not-yet-taken message at the end. (2026-10-24: a ChatGPT reply was hidden this way.)
        self:mergeMind(st)
        if nowMs() - self.pendingAt > REPLY_TIMEOUT_MS then
            self.pending = nil; self.status = "error"; self.code = "timeout"; self.timeoutAck = ack
            return
        end
        local alive = st.status == "thinking" or (nowMs() - (self.lastMindChange or 0)) < OFFLINE_MS
        if not alive and nowMs() - self.pendingAt > OFFLINE_MS then
            self.pending = nil; self.status = "error"; self.code = "mind_offline"; self.offlineAck = ack
        end
        return
    end
    -- Ignore only the old thinking state. A final answer with the same ack must still appear.
    if self.offlineAck ~= nil then
        if ack == self.offlineAck and st.status == "thinking" and self.pending == nil then return end
        self.offlineAck = nil
    end
    if self.timeoutAck ~= nil then
        if ack == self.timeoutAck and st.status == "thinking" and self.pending == nil then return end
        self.timeoutAck = nil
    end
    if st.status == "thinking" then
        self.thinkingSince = self.thinkingSince or (self.pending and self.pendingAt or nowMs())
        if nowMs() - self.thinkingSince > REPLY_TIMEOUT_MS then
            self.pending = nil; self.status = "error"; self.code = "timeout"; self.timeoutAck = ack
            return
        end
    else
        self.thinkingSince = nil
    end
    self.status = st.status or "idle"; self.code = st.code or ""
    if self.pending and self.status ~= "thinking" then self.pending = nil end
    local n = tonumber(st.count) or 0
    local msgs = {}
    for i = 1, n do
        local v = st["m" .. i]
        if v then
            local role, txt = string.match(v, "^(%a+)|(.*)$")
            if role then msgs[#msgs + 1] = { role = role, cps = T.unescape(txt) } end
        end
    end
    local sig = tostring(st.count) .. "|" .. tostring(st["m" .. tostring(st.count)] or "")
    if sig == self.lastSig and self.pending == nil then return end
    self.lastSig = sig
    if self.pending == nil or #msgs >= #self.msgs then
        if #msgs ~= self.lastCount then self.stickBottom = true end
        self.msgs = msgs; self.lastCount = #msgs; self.layoutDirty = true
    end
end

function Chat:poll()
    local t = nowMs()
    if t - self.lastPoll < 300 then return end
    self.lastPoll = t
    self:applyState(U.readChatState())
end

local function utf8FromCodepoints(cps)
    local out = {}
    for _, cp in ipairs(cps or {}) do
        if cp < 0x80 then out[#out + 1] = string.char(cp)
        elseif cp < 0x800 then
            out[#out + 1] = string.char(0xC0 + math.floor(cp / 64), 0x80 + cp % 64)
        elseif cp < 0x10000 then
            out[#out + 1] = string.char(0xE0 + math.floor(cp / 4096), 0x80 + math.floor(cp / 64) % 64, 0x80 + cp % 64)
        elseif cp <= 0x10FFFF then
            out[#out + 1] = string.char(0xF0 + math.floor(cp / 262144), 0x80 + math.floor(cp / 4096) % 64,
                0x80 + math.floor(cp / 64) % 64, 0x80 + cp % 64)
        end
    end
    return table.concat(out)
end

function Chat:updateGeometry()
    local w, h = self:getWidth(), self:getHeight()
    MIC = { 112, h - PAD - INPUT_H, 44, INPUT_H }
    if self.entry then
        self.entry:setX(162); self.entry:setY(h - PAD - INPUT_H)
        self.entry:setWidth(math.max(180, w - 162 - PAD))
    end
    self.layoutDirty = true
end

function Chat:resizeTo(w, h)
    local core = getCore()
    local sw, sh = core:getScreenWidth(), core:getScreenHeight()
    local minW, minH = math.min(420, sw - 24), math.min(420, sh - 24)
    w = math.max(minW, math.min(math.floor(w), sw - 24))
    h = math.max(minH, math.min(math.floor(h), sh - 24))
    if w ~= self:getWidth() or h ~= self:getHeight() then
        self:setWidth(w); self:setHeight(h); self:updateGeometry()
        self:setX(math.max(0, math.min(self:getX(), sw - w)))
        self:setY(math.max(0, math.min(self:getY(), sh - h)))
        self.stickBottom = false
    end
end

function Chat:messageAt(x, y)
    local L = self:listRect()
    if not inside(x, y, L) then return nil end
    if not self.layoutCache or self.layoutDirty then self.layoutCache = { self:layout() }; self.layoutDirty = false end
    local items = self.layoutCache[1] or {}
    local contentY = y - L[2] - 8 + (self.scroll or 0)
    for i, item in ipairs(items) do
        if contentY >= item.y and contentY <= item.y + item.h and not item.card then return i end
    end
    return nil
end

function Chat:copySelection()
    if not self.selectionFirst or not self.selectionLast or Clipboard == nil
        or type(Clipboard.setClipboard) ~= "function" then return false end
    local first, last = math.min(self.selectionFirst, self.selectionLast), math.max(self.selectionFirst, self.selectionLast)
    local chunks = {}
    for i = first, last do
        local message = self.msgs[i]
        if message and type(message.cps) == "table" then chunks[#chunks + 1] = utf8FromCodepoints(message.cps) end
    end
    if #chunks == 0 then return false end
    return pcall(Clipboard.setClipboard, table.concat(chunks, "\n"))
end

function U.chatKeyPressed(key)
    local chat = U.chat
    if not chat or not chat:isVisible() or not chat.selectionFirst then return end
    local entryFocused = chat.inputFocused == true
    if chat.entry and type(chat.entry.isFocused) == "function" then
        local ok, focused = pcall(chat.entry.isFocused, chat.entry)
        if ok and focused == true then entryFocused = true end
    end
    if entryFocused then return end
    local control = Keyboard and (Keyboard.KEY_LCONTROL or Keyboard.KEY_RCONTROL)
    local function held(code)
        if code == nil or type(isKeyDown) ~= "function" then return false end
        local ok, down = pcall(isKeyDown, code)
        return ok and down == true
    end
    local controlHeld = held(control) or held(Keyboard and Keyboard.KEY_RCONTROL)
    if not controlHeld then return end
    if key == Keyboard.KEY_A then
        chat.selectionFirst, chat.selectionLast = 1, #chat.msgs
        return
    end
    if key == Keyboard.KEY_C then chat:copySelection() end
end

-- layout of the message list (heights computed with SolText wrapping)
local BUBBLE_W, BUBBLE_PAD, GAP = 380, 12, 10
function Chat:layout()
    local W = self:getWidth()
    local bubbleLimit = math.min(W - 2 * PAD - 20, BUBBLE_W + math.max(0, W - 560))
    local items, y = {}, 0
    for _, m in ipairs(self.msgs) do
        if m.role == "card" then
            -- Itemized supplies table built from game data: item ; quantity ; category/location ; neutral colour.
            local sum = #m.cps
            for i = 1, math.min(#m.cps, 256) do sum = (sum * 31 + m.cps[i]) % 1000000007 end
            local cacheKey = tostring(W) .. ":" .. tostring(#m.cps) .. ":" .. tostring(sum)
            self.cardCache = self.cardCache or {}
            local known = self.cardCache[cacheKey]
            if known then
                items[#items + 1] = { m = m, card = known.rows, y = y, w = known.w, h = known.h }
                y = y + known.h + GAP
            else
            local rows, cur = {}, {}
            local field = {}
            for _, cp in ipairs(m.cps) do
                if cp == 94 then field[#field + 1] = cur; rows[#rows + 1] = field; field = {}; cur = {}      -- '^' between rows
                elseif cp == 59 then field[#field + 1] = cur; cur = {}
                else cur[#cur + 1] = cp end
            end
            if #cur > 0 or #field > 0 then field[#field + 1] = cur; rows[#rows + 1] = field end
            local w, cardRows, h = W - 2 * PAD - 20, {}, 16
            local nameW, countW = 200, 52
            local detailW = w - nameW - countW - 48
            for _, row in ipairs(rows) do
                local name = row[1] or {}
                local count = row[2] or {}
                local detail = row[3] or {}
                local color = row[4] or {}
                local nameLines = T.wrap(name, nameW, 0.44)
                local detailLines = T.wrap(detail, detailW, 0.44)
                local lineCount = math.max(1, #nameLines, #detailLines)
                local rowH = math.max(28, lineCount * 17 + 11)
                local colName = ""
                for _, cp in ipairs(color) do colName = colName .. string.char(cp) end
                cardRows[#cardRows + 1] = { name = nameLines, count = count, detail = detailLines, colName = colName, h = rowH, top = h - 16 }
                h = h + rowH
            end
            self.cardCache[cacheKey] = { rows = cardRows, w = w, h = h }
            items[#items + 1] = { m = m, card = cardRows, y = y, w = w, h = h }
            y = y + h + GAP
            end
        else
        local lines = T.wrap(m.cps, bubbleLimit - 2 * BUBBLE_PAD, SCALE)
        local lh = T.lineHeight(SCALE) * 0.82
        local wmax = 0
        for _, l in ipairs(lines) do wmax = math.max(wmax, T.width(l, SCALE)) end
        local bw = math.min(bubbleLimit, wmax + 2 * BUBBLE_PAD + 4)
        local bh = #lines * lh + 2 * BUBBLE_PAD - 4
        items[#items + 1] = { m = m, lines = lines, y = y, w = bw, h = bh, lh = lh }
        y = y + bh + GAP
        end
    end
    return items, y
end

function Chat:listRect()
    local w, h = self:getWidth(), self:getHeight()
    return { PAD, HEAD + 8, w - 2 * PAD, h - HEAD - 8 - INPUT_H - PAD - 40 }
end

function Chat:prerender()
    if U.perfAdd then local t0 = nowMs(); self:prerenderBody(); U.perfAdd("chat", nowMs() - t0); return end
    self:prerenderBody()
end
function Chat:prerenderBody()
    self:poll()
    local W, H = self:getWidth(), self:getHeight()
    rect(self, 0, 0, W, H, C.frame)
    rect(self, 0, 0, W, HEAD, C.header)
    rect(self, 0, HEAD, W, 1, C.line)
    border(self, 0, 0, W, H, C.border)
    local tex = getTexture("media/textures/SolUI/portrait_ring.png")
    if tex then self:drawTextureScaled(tex, W - 58, 4, 52, 52, 1, 1, 1, 1) end
    T.drawLine(self, MSG.title, W - 280, 6, 214, { scale = 0.68, align = "right", r = C.text[1], g = C.text[2], b = C.text[3] })
    local thinking = self.pending ~= nil or self.status == "thinking"
    local sc = thinking and C.amber or (self.status == "error" and C.red or C.green)
    self:drawRect(W - 76, 40, 8, 8, 1, sc[1], sc[2], sc[3])
    local stext = thinking and MSG.thinking or (self.status == "error" and (MSG[self.code] or MSG.unknown_error) or MSG.ready)
    local vc = U.voice
    if vc and (vc.listening or vc.status == "transcribing") then stext = vc.listening and MSG.voice_listening or MSG.voice_transcribing; sc = C.amber
    elseif vc and vc.status == "error" and vc.code ~= "" and nowMs() - (vc.since or 0) < 60000 then stext = MSG[vc.code] or MSG.unknown_error; sc = C.red end
    if not (self.status == "error") then T.drawLine(self, stext, W - 400, 30, 316, { scale = SMALL, align = "right", r = sc[1], g = sc[2], b = sc[3] }) end
    -- close button
    rect(self, 12, 14, 32, 32, C.sol); border(self, 12, 14, 32, 32, C.solLine)
    self:drawText("X", 23, 20, C.text[1], C.text[2], C.text[3], 1, UIFont.Medium)
    -- message list (clipped)
    local L = self:listRect()
    rect(self, L[1], L[2], L[3], L[4], { 0.035, 0.08, 0.12, 1 }); border(self, L[1], L[2], L[3], L[4], C.solLine)
    if not self.layoutCache or self.layoutDirty then self.layoutCache = { self:layout() }; self.layoutDirty = false end
    local items, total = self.layoutCache[1], self.layoutCache[2]
    self.contentH = total
    local maxScroll = math.max(0, total - (L[4] - 16))
    if self.stickBottom then self.scroll = maxScroll; self.stickBottom = false end
    if self.scroll > maxScroll then self.scroll = maxScroll end
    self:setStencilRect(L[1] + 1, L[2] + 1, L[3] - 2, L[4] - 2)
    if #items == 0 then
        T.draw(self, MSG.empty, L[1] + 20, L[2] + 20, L[3] - 40, { scale = SMALL, align = "center", r = C.muted[1], g = C.muted[2], b = C.muted[3] })
    end
    for itemIndex, it in ipairs(items) do
        local y = L[2] + 8 + it.y - self.scroll
        if it.card and y + it.h >= L[2] and y <= L[2] + L[4] then
            local x = L[1] + 10
            rect(self, x, y, it.w, it.h, C.sol); border(self, x, y, it.w, it.h, C.border)
            local COL = { red = C.red, amber = C.amber, green = C.green }
            local nameW, countW = 200, 52
            local nameX = x + it.w - 8 - nameW
            local countX = nameX - 60
            local dotX = countX - 17
            -- only the rows inside the window: a table of hundreds costs the same as a table of twenty
            local card, low, high, listBottom = it.card, 1, #it.card, L[2] + L[4]
            while low < high do
                local mid = math.floor((low + high) / 2)
                if y + 8 + card[mid].top + card[mid].h < L[2] then low = mid + 1 else high = mid end
            end
            for i = low, #card do
                local row = card[i]
                local ry = y + 8 + row.top
                if ry > listBottom then break end
                if i > 1 then rect(self, x + 8, ry - 2, it.w - 16, 1, C.solLine) end
                local nameLines, count, detail = row.name or {}, row.count or {}, row.detail or {}
                local cc = COL[row.colName] or C.muted
                local textY = ry + math.max(3, (row.h - #nameLines * 17) / 2)
                for lineNo, line in ipairs(nameLines) do
                    T.drawLine(self, line, nameX, textY + (lineNo - 1) * 17, nameW, { scale = 0.44, align = "right", r = C.text[1], g = C.text[2], b = C.text[3] })
                end
                T.drawLine(self, count, countX, ry + (row.h - 18) / 2, countW, { scale = 0.48, align = "center", r = 0.42, g = 0.72, b = 1.0 })
                self:drawRect(dotX, ry + (row.h - 8) / 2, 6, 6, 1, cc[1], cc[2], cc[3])
                local detailX, detailW = x + 8, dotX - (x + 8) - 8
                local detailY = ry + math.max(3, (row.h - #detail * 17) / 2)
                for lineNo, line in ipairs(detail) do
                    T.drawLine(self, line, detailX, detailY + (lineNo - 1) * 17, detailW, { scale = 0.44, align = "right", r = cc[1], g = cc[2], b = cc[3] })
                end
            end
        elseif y + it.h >= L[2] and y <= L[2] + L[4] then
            local mine = it.m.role == "user"
            local x = mine and (L[1] + 10) or (L[1] + L[3] - 10 - it.w)
            local bg = mine and C.me or C.sol
            rect(self, x, y, it.w, it.h, bg); border(self, x, y, it.w, it.h, mine and C.border or C.solLine)
            if self.selectionFirst and self.selectionLast
                and itemIndex >= math.min(self.selectionFirst, self.selectionLast)
                and itemIndex <= math.max(self.selectionFirst, self.selectionLast) then
                self:drawRect(x + 1, y + 1, it.w - 2, it.h - 2, 0.18, 1, 0.78, 0.22)
                border(self, x, y, it.w, it.h, C.amber)
            end
            for i, line in ipairs(it.lines) do
                T.drawLine(self, line, x + BUBBLE_PAD, y + BUBBLE_PAD - 6 + (i - 1) * it.lh, it.w - 2 * BUBBLE_PAD,
                    { scale = SCALE, r = C.text[1], g = C.text[2], b = C.text[3] })
            end
        end
    end
    self:clearStencilRect()
    if maxScroll > 0 then
        local track = L[4] - 8
        local hh = math.max(24, track * (L[4] - 16) / total)
        self:drawRect(L[1] + L[3] - 6, L[2] + 4 + (track - hh) * (self.scroll / maxScroll), 3, hh, 0.8, 0.18, 0.64, 1)
    end
    for i = 0, 2 do
        self:drawRect(W - 5 - i * 4, H - 3, 2, 2, 0.9, C.muted[1], C.muted[2], C.muted[3])
        self:drawRect(W - 3, H - 5 - i * 4, 2, 2, 0.9, C.muted[1], C.muted[2], C.muted[3])
    end
    -- error line under the list
    if self.status == "error" then
        T.drawLine(self, MSG[self.code] or MSG.unknown_error, PAD, L[2] + L[4] + 6, W - 2 * PAD, { scale = SMALL, align = "right", r = C.red[1], g = C.red[2], b = C.red[3] })
    end
    -- send button
    local B = { PAD, H - PAD - INPUT_H, 88, INPUT_H }
    rect(self, B[1], B[2], B[3], B[4], { 0.102, 0.471, 0.800, self.pending and 0.5 or 1 }); border(self, B[1], B[2], B[3], B[4], C.border)
    T.drawLine(self, MSG.send, B[1], B[2] + 6, B[3], { scale = SMALL + 0.06, align = "center" })
end

-- microphone button next to Send: press to talk, press again to send (red while listening)
function Chat:drawMic()
    local r = MIC
    if not r then return end
    local vc = U.voice or {}
    local col = C.me
    if vc.listening then
        local a = 0.6 + 0.4 * math.abs(math.sin(nowMs() / 250))
        col = { 0.94 * a, 0.25 * a, 0.22 * a, 1 }
    elseif vc.status == "transcribing" then col = { 0.93, 0.74, 0.19, 1 } end
    rect(self, r[1], r[2], r[3], r[4], col); border(self, r[1], r[2], r[3], r[4], C.border)
    local cx = r[1] + r[3] / 2
    self:drawRect(cx - 5, r[2] + 9, 10, 15, 1, 1, 1, 1)
    self:drawRect(cx - 4, r[2] + 7, 8, 2, 1, 1, 1, 1); self:drawRect(cx - 4, r[2] + 24, 8, 2, 1, 1, 1, 1)
    self:drawRect(cx - 9, r[2] + 19, 2, 9, 1, 1, 1, 1); self:drawRect(cx + 7, r[2] + 19, 2, 9, 1, 1, 1, 1)
    self:drawRect(cx - 9, r[2] + 28, 18, 2, 1, 1, 1, 1)
    self:drawRect(cx - 1, r[2] + 30, 2, 5, 1, 1, 1, 1); self:drawRect(cx - 6, r[2] + 35, 12, 2, 1, 1, 1, 1)
end

function Chat:drawClear()
    local r, sc = CLEAR, SMALL
    local tc = self:solBusy() and C.muted or C.text
    rect(self, r[1], r[2], r[3], r[4], C.sol); border(self, r[1], r[2], r[3], r[4], C.solLine)
    T.drawLine(self, MSG.clear, r[1] + 4, r[2] + (r[4] - T.lineHeight(sc) * 0.86) / 2, r[3] - 8, { scale = sc, align = "center", r = tc[1], g = tc[2], b = tc[3] })
end
function Chat:render()
    self:drawMic()
    self:drawClear()
    -- the game's entry box cannot draw Arabic: Sol draws the typed text INSIDE the box (right-aligned) with a caret,
    -- on top of the box (render runs after the children), so the text appears where it is typed.
    if not self.entry then return end
    local ex, ey, ew, eh = self.entry:getX(), self.entry:getY(), self.entry:getWidth(), self.entry:getHeight()
    rect(self, ex + 1, ey + 1, ew - 2, eh - 2, { 0.03, 0.07, 0.11, 1 })
    local text = self.entry:getText() or ""      -- keyed by the string: shaping is cached, not redone per frame
    local tw = 0
    if text ~= "" then
        local scale = SCALE
        tw = T.width(text, scale)
        if tw > ew - 24 then scale = scale * (ew - 24) / tw; tw = ew - 24 end
        T.drawLine(self, text, ex + 10, ey + (eh - T.lineHeight(scale) * 0.86) / 2, ew - 20, { scale = scale, align = "right", r = C.text[1], g = C.text[2], b = C.text[3] })
    end
    if math.floor(nowMs() / 500) % 2 == 0 then
        local cx = ex + ew - 10 - tw - 3
        self:drawRect(cx, ey + 9, 2, eh - 18, 1, C.text[1], C.text[2], C.text[3])
    end
end

function Chat:onMouseWheel(del)
    self.scroll = math.max(0, self.scroll + (del > 0 and 40 or -40))
    return true
end
function Chat:onMouseDown(x, y)
    local w, h = self:getWidth(), self:getHeight()
    if inside(x, y, { w - RESIZE_GRIP, h - RESIZE_GRIP, RESIZE_GRIP, RESIZE_GRIP }) then
        self.resizing = true; self.resizeW, self.resizeH = w, h
        self.resizeMX, self.resizeMY = self:getX() + self:getMouseX(), self:getY() + self:getMouseY()
        self.selecting = false
    elseif inside(x, y, self:listRect()) then
        local index = self:messageAt(x, y)
        if index then
            self.selectionFirst, self.selectionLast = index, index
            self.selecting = true
            self.inputFocused = false
        else
            self.selectionFirst, self.selectionLast, self.selecting = nil, nil, false
        end
    elseif inside(x, y, { 162, h - PAD - INPUT_H, w - 162 - PAD, INPUT_H }) then
        self.selectionFirst, self.selectionLast, self.selecting = nil, nil, false
        self.inputFocused = true
    elseif y < HEAD and not inside(x, y, { 12, 14, 32, 32 }) and not inside(x, y, CLEAR) then
        self.dragging = true; self.dx, self.dy = x, y
    end
    return true
end
function Chat:onMouseMove(dx, dy)
    if self.resizing then
        local mx, my = self:getX() + self:getMouseX(), self:getY() + self:getMouseY()
        self:resizeTo(self.resizeW + mx - self.resizeMX, self.resizeH + my - self.resizeMY)
    elseif self.selecting then
        local index = self:messageAt(self:getMouseX(), self:getMouseY())
        if index then self.selectionLast = index end
    elseif self.dragging then
        self:setX(self:getX() + self:getMouseX() - self.dx); self:setY(self:getY() + self:getMouseY() - self.dy)
    end
end
function Chat:onMouseMoveOutside(dx, dy) self:onMouseMove(dx, dy) end
function Chat:onMouseUpOutside() self.dragging = false; self.resizing = false; self.selecting = false end
function Chat:onMouseUp(x, y)
    if self.dragging or self.resizing or self.selecting then
        self.dragging = false; self.resizing = false; self.selecting = false
        return true
    end
    if inside(x, y, { 12, 14, 32, 32 }) then U.closeChat(); return true end
    if inside(x, y, CLEAR) then self:clearNow(); return true end
    if inside(x, y, { PAD, self:getHeight() - PAD - INPUT_H, 88, INPUT_H }) then self:sendCurrent(); return true end
    if MIC and inside(x, y, MIC) then if U.voiceToggle then U.voiceToggle() end; return true end
    return true
end

function U.openChat()
    if not U.chat then
        local sw = getCore():getScreenWidth(); local sh = getCore():getScreenHeight()
        local x, y = math.floor((sw - W) / 2), math.floor((sh - H) / 2)
        if U.panel then x = U.panel:getX(); y = math.max(0, math.min(U.panel:getY(), sh - H)) end
        U.chat = Chat:new(x, y)
        U.chat:initialise(); U.chat:instantiate(); U.chat:addToUIManager()
    end
    if U.hidePanel then U.hidePanel() end
    U.chat.selectionFirst, U.chat.selectionLast, U.chat.selecting = nil, nil, false
    U.chat.lastCount = -1; U.chat.stickBottom = true
    U.chat:setVisible(true); U.chat:bringToTop()
    if U.chat.entry and U.chat.entry.focus then pcall(function() U.chat.entry:focus() end) end
end
function U.closeChat()
    if U.chat then U.chat:setVisible(false) end
    if U.showPanel then U.showPanel() end
end

if Events and Events.OnKeyPressed and not U._chatKeyboardHook then
    Events.OnKeyPressed.Add(U.chatKeyPressed)
    U._chatKeyboardHook = true
end
