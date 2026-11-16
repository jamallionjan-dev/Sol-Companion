-- SolVoice.lua - the voice button: press to talk, press again to send.
-- Sol Mind does the listening: with the ChatGPT bridge as Sol's mind through ChatGPT's own dictation, otherwise
-- with the microphone + Whisper. The heard text arrives in Sol's chat like a typed message.
--   game -> SolVoice_Request.txt  id / action=start|stop        Sol Mind -> SolVoice_State.txt  ack / status / code / text
SolUI = SolUI or {}
local U = SolUI
U.VOICE_VERSION = "0.1.0"
local REQ, STATE, MAX_MS = "SolVoice_Request.txt", "SolVoice_State.txt", 31000
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
U.voice = U.voice or { listening = false, status = "idle", code = "", since = 0 }
local Vc = U.voice
local lastId = 0
local function send(action)
    lastId = math.max(lastId + 1, nowMs())
    local ok, w = pcall(getFileWriter, REQ, true, false)
    if ok and w then w:write("id=" .. string.format("%.0f", lastId) .. "\naction=" .. action .. "\n"); w:close() end
end
function U.voiceToggle()
    if Vc.listening then
        Vc.listening = false; Vc.status = "transcribing"; send("stop")
    else
        Vc.listening = true; Vc.status = "listening"; Vc.code = ""; Vc.since = nowMs(); send("start")
        if U.openChat then pcall(U.openChat) end
    end
    return true
end
local function readState()
    local ok, r = pcall(getFileReader, STATE, false)
    if not ok or not r then return nil end
    local t, line = {}, r:readLine()
    while line ~= nil do local k, v = string.match(line, "^([^=]+)=(.*)$"); if k then t[k] = v end; line = r:readLine() end
    r:close()
    return t
end
local last = 0
local function onTick()
    local t = nowMs()
    if Vc.listening and t - Vc.since > MAX_MS then Vc.listening = false; Vc.status = "transcribing" end   -- Sol Mind stops at 30 s
    if t - last < 300 then return end
    last = t
    local st = readState()
    if st and tonumber(st.ack) and tonumber(st.ack) >= lastId - 1 and lastId > 0 then
        Vc.status, Vc.code = st.status or Vc.status, st.code or ""
        if Vc.status == "error" or Vc.status == "done" then Vc.listening = false end
    end
end
if Events and Events.OnTick then Events.OnTick.Add(onTick) end
print("[SolVoice] ready v" .. U.VOICE_VERSION)
