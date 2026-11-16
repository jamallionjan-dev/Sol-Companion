-- SPDX-License-Identifier: MIT
SurvivorCompanion = SurvivorCompanion or {}
local SC = SurvivorCompanion
SC.AIMailbox = SC.AIMailbox or {}
local M = SC.AIMailbox

M.PROTOCOL = "sol-ai-1"
M.FORMAT = "SOL_AI_FRAME_V1"
M.INBOX = "SolAI_Inbox.txt"
M.OUTBOX = "SolAI_Outbox.txt"
M.MAX_CHARS = 131072
M.MAX_VALUES = 4096
M.MAX_DEPTH = 12

local lastInboundKey = nil

local function finite(v)
    return type(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge
end

local function hexEncode(text)
    text = tostring(text or "")
    return (string.gsub(text, ".", function(c)
        return string.format("%02X", string.byte(c))
    end))
end

local function hexDecode(text)
    if type(text) ~= "string" or (#text % 2) ~= 0 then return nil, "invalid_hex" end
    local out = {}
    for i = 1, #text, 2 do
        local b = tonumber(string.sub(text, i, i + 1), 16)
        if b == nil then return nil, "invalid_hex" end
        out[#out + 1] = string.char(b)
    end
    return table.concat(out)
end

local function classifyTable(value)
    local count, maximum = 0, 0
    local array = true
    for key in pairs(value) do
        count = count + 1
        if type(key) ~= "number" or key < 1 or key ~= math.floor(key) then
            array = false
        elseif key > maximum then
            maximum = key
        end
    end
    if array and maximum == count then return "A", count end
    return "M", count
end

local function sortedMapKeys(value)
    local keys = {}
    for key in pairs(value) do
        local kind = type(key)
        if kind ~= "string" and kind ~= "number" then
            return nil, "unsupported_key_type"
        end
        if kind == "number" and not finite(key) then
            return nil, "non_finite_key"
        end
        keys[#keys + 1] = key
    end
    table.sort(keys, function(a, b)
        local ta, tb = type(a), type(b)
        if ta ~= tb then return ta < tb end
        if ta == "number" then return a < b end
        return a < b
    end)
    return keys
end

local function encodeValue(value, state, depth)
    if depth > M.MAX_DEPTH then return nil, "depth_limit" end
    state.count = state.count + 1
    if state.count > M.MAX_VALUES then return nil, "value_limit" end

    local kind = type(value)
    if kind == "nil" then return "N" end
    if kind == "boolean" then return value and "B1" or "B0" end
    if kind == "number" then
        if not finite(value) then return nil, "non_finite_number" end
        return "D" .. string.format("%.17g", value) .. ";"
    end
    if kind == "string" then
        local hex = hexEncode(value)
        return "S" .. tostring(#hex) .. ":" .. hex
    end
    if kind ~= "table" then return nil, "unsupported_type_" .. kind end
    if state.seen[value] then return nil, "cyclic_or_repeated_table" end
    state.seen[value] = true

    local tableKind, count = classifyTable(value)
    local parts = { tableKind, tostring(count), ":" }
    if tableKind == "A" then
        for i = 1, count do
            local encoded, reason = encodeValue(value[i], state, depth + 1)
            if not encoded then state.seen[value] = nil return nil, reason end
            parts[#parts + 1] = encoded
        end
    else
        local keys, reason = sortedMapKeys(value)
        if not keys then state.seen[value] = nil return nil, reason end
        for _, key in ipairs(keys) do
            local encodedKey, keyReason = encodeValue(key, state, depth + 1)
            if not encodedKey then state.seen[value] = nil return nil, keyReason end
            local encodedValue, valueReason = encodeValue(value[key], state, depth + 1)
            if not encodedValue then state.seen[value] = nil return nil, valueReason end
            parts[#parts + 1] = encodedKey
            parts[#parts + 1] = encodedValue
        end
    end
    state.seen[value] = nil
    return table.concat(parts)
end

local function readCount(body, index, delimiter)
    local stop = string.find(body, delimiter, index, true)
    if not stop then return nil, nil, "delimiter_missing" end
    local raw = string.sub(body, index, stop - 1)
    if raw == "" or not string.match(raw, "^%d+$") then return nil, nil, "invalid_count" end
    return tonumber(raw), stop + 1
end

local function decodeValue(body, index, state, depth)
    if depth > M.MAX_DEPTH then return nil, nil, "depth_limit" end
    state.count = state.count + 1
    if state.count > M.MAX_VALUES then return nil, nil, "value_limit" end
    local tag = string.sub(body, index, index)
    if tag == "" then return nil, nil, "unexpected_end" end
    if tag == "N" then return nil, index + 1 end
    if tag == "B" then
        local v = string.sub(body, index + 1, index + 1)
        if v == "1" then return true, index + 2 end
        if v == "0" then return false, index + 2 end
        return nil, nil, "invalid_boolean"
    end
    if tag == "D" then
        local stop = string.find(body, ";", index + 1, true)
        if not stop then return nil, nil, "number_terminator_missing" end
        local value = tonumber((string.sub(body, index + 1, stop - 1)))
        if not finite(value) then return nil, nil, "invalid_number" end
        return value, stop + 1
    end
    if tag == "S" then
        local length, start, reason = readCount(body, index + 1, ":")
        if not length then return nil, nil, reason end
        if length < 0 or start + length - 1 > #body then return nil, nil, "string_length_invalid" end
        local value, decodeReason = hexDecode(string.sub(body, start, start + length - 1))
        if value == nil then return nil, nil, decodeReason end
        return value, start + length
    end
    if tag ~= "A" and tag ~= "M" then return nil, nil, "invalid_tag" end

    local count, cursor, reason = readCount(body, index + 1, ":")
    if not count then return nil, nil, reason end
    if count > M.MAX_VALUES then return nil, nil, "container_limit" end
    local result = {}
    if tag == "A" then
        for i = 1, count do
            local value
            value, cursor, reason = decodeValue(body, cursor, state, depth + 1)
            if reason then return nil, nil, reason end
            result[i] = value
        end
    else
        for _ = 1, count do
            local key, value
            key, cursor, reason = decodeValue(body, cursor, state, depth + 1)
            if reason then return nil, nil, reason end
            if type(key) ~= "string" and type(key) ~= "number" then
                return nil, nil, "invalid_map_key"
            end
            value, cursor, reason = decodeValue(body, cursor, state, depth + 1)
            if reason then return nil, nil, reason end
            result[key] = value
        end
    end
    return result, cursor
end

function M.encodeFrame(frame)
    if type(frame) ~= "table" then return nil, "frame_not_table" end
    if frame.protocol ~= M.PROTOCOL then return nil, "protocol_mismatch" end
    local encoded, reason = encodeValue(frame, { count = 0, seen = {} }, 0)
    if not encoded then return nil, reason end
    if #encoded > M.MAX_CHARS then return nil, "frame_too_large" end
    return encoded
end

function M.decodeFrame(body)
    if type(body) ~= "string" then return nil, "body_not_string" end
    if #body > M.MAX_CHARS then return nil, "frame_too_large" end
    local frame, cursor, reason = decodeValue(body, 1, { count = 0 }, 0)
    if reason then return nil, reason end
    if cursor ~= #body + 1 then return nil, "trailing_data" end
    if type(frame) ~= "table" then return nil, "frame_not_table" end
    if frame.protocol ~= M.PROTOCOL then return nil, "protocol_mismatch" end
    return frame
end

local function writeFrame(path, frame)
    if type(getFileWriter) ~= "function" then return false, "file_writer_unavailable" end
    local body, reason = M.encodeFrame(frame)
    if not body then return false, reason end
    local writer = getFileWriter(path, true, false)
    if writer == nil then return false, "open_writer_failed" end
    writer:writeln(M.FORMAT)
    writer:writeln(body)
    writer:writeln("END")
    writer:close()
    return true
end

local function readFrame(path)
    if type(getFileReader) ~= "function" then return nil, "file_reader_unavailable" end
    local reader = getFileReader(path, true)
    if reader == nil then return nil, "open_reader_failed" end
    local format = reader:readLine()
    local body = reader:readLine()
    local ending = reader:readLine()
    reader:close()
    if format == nil and body == nil then return nil, "empty" end
    if format ~= M.FORMAT then return nil, "format_mismatch" end
    if ending ~= "END" then return nil, "incomplete_frame" end
    return M.decodeFrame(body)
end

function M.write(frame)
    return writeFrame(M.OUTBOX, frame)
end

local function inboundKey(frame)
    return table.concat({
        hexEncode(tostring(frame.sessionId or "")),
        hexEncode(tostring(frame.sequence or "")),
        hexEncode(tostring(frame.requestId or "")),
        hexEncode(tostring(frame.type or "")),
    }, "|")
end

function M.readNext()
    local frame, reason = readFrame(M.INBOX)
    if frame == nil then return nil, reason end
    local key = inboundKey(frame)
    if key == lastInboundKey then return nil, "duplicate" end
    lastInboundKey = key
    return frame, "ready"
end

function M.health()
    return {
        protocol = M.PROTOCOL,
        format = M.FORMAT,
        inbox = M.INBOX,
        outbox = M.OUTBOX,
        maxChars = M.MAX_CHARS,
        maxValues = M.MAX_VALUES,
        maxDepth = M.MAX_DEPTH,
        reader = type(getFileReader) == "function",
        writer = type(getFileWriter) == "function",
    }
end

return M
