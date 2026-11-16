-- SolHeliExaminer.lua - passive, Lab-only flight recorder for manual piloting.
-- It observes Aviation Core's input state; it never changes flight controls.
SolHeliExaminer = SolHeliExaminer or {}
local E = SolHeliExaminer
if E._initialized then return E end
E._initialized = true

local SAMPLE_MS, FLUSH_MS = 100, 1000
local nextSample, nextFlush = 0, 0
local writer, buffer, filename, fileExists = nil, {}, nil, false
local previousZ, previousMs, scratchVector = nil, nil, nil
local reportedWriterFailure = false

local function now()
    if type(getTimestampMs) == "function" then
        local ok, value = pcall(getTimestampMs)
        if ok and tonumber(value) then return tonumber(value) end
    end
    return os and type(os.time) == "function" and os.time() * 1000 or 0
end

local function call(object, name, ...)
    if object == nil then return nil end
    local okMethod, method = pcall(function() return object[name] end)
    if not okMethod or type(method) ~= "function" then return nil end
    local ok, value = pcall(method, object, ...)
    if ok then return value end
    return nil
end

local function enabled()
    if type(rawget(_G, "SolLab")) ~= "table" or SolLab.active ~= true then return false end
    local authority = rawget(_G, "SolAuthority")
    if type(authority) ~= "table" or type(authority.on) ~= "function" then return false end
    local ok, value = pcall(authority.on, "drive_record")
    return ok and value == true
end

local function number(value)
    return type(value) == "number" and string.format("%.4f", value) or ""
end

local function log(message)
    print("[SolHeliExaminer] " .. tostring(message))
end

local function flush()
    if #buffer == 0 then return true end
    if writer == nil then
        if filename == nil or type(getFileWriter) ~= "function" then return false end
        local okOpen, handle = pcall(getFileWriter, filename, true, fileExists)
        if not okOpen or handle == nil then
            if not reportedWriterFailure then
                reportedWriterFailure = true
                log("WRITE_FAILED file_open_failed name=" .. tostring(filename))
            end
            return false
        end
        writer = handle
    end
    local payload = table.concat(buffer)
    local activeWriter = writer
    local ok = pcall(function() activeWriter:write(payload) end)
    pcall(function() activeWriter:close() end)
    writer = nil
    if not ok then
        log("WRITE_FAILED rows=" .. tostring(#buffer))
        return false
    end
    buffer = {}
    fileExists = true
    return true
end

local function close(reason)
    if filename == nil then return end
    flush()
    if writer ~= nil then pcall(function() writer:close() end); writer = nil end
    filename = nil
    previousZ, previousMs = nil, nil
    log("CAPTURE_CLOSED reason=" .. tostring(reason or "state_changed"))
end

local function open(timestamp)
    if filename ~= nil then return true end
    if type(getFileWriter) ~= "function" then
        if not reportedWriterFailure then
            reportedWriterFailure = true
            log("START_FAILED getFileWriter_unavailable")
        end
        return false
    end
    filename = "SolHeliExaminer_" .. string.format("%.0f", timestamp) .. ".txt"
    fileExists = false
    nextFlush = timestamp + FLUSH_MS
    buffer[#buffer + 1] = "ms,vehicle_id,script,seat,controls,x,y,world_altitude_z,ground_z,agl,vertical_z_per_s,kmh,forward_x,forward_y\n"
    if not flush() then close("header_write_failed"); return false end
    log("CAPTURE_STARTED file=" .. filename .. " seat=0 sample_ms=" .. tostring(SAMPLE_MS) .. " durable_flush=true")
    return true
end

local function worldPosition(vehicle)
    local vectorType = rawget(_G, "Vector3f")
    if scratchVector == nil and type(vectorType) == "table" and type(vectorType.new) == "function" then
        local ok, value = pcall(vectorType.new)
        if ok then scratchVector = value end
    end
    if scratchVector ~= nil and type(vehicle.getWorldPos) == "function" then
        local ok, point = pcall(vehicle.getWorldPos, vehicle, 0, 0, 0, scratchVector)
        if ok and point ~= nil then
            local okXYZ, x, y, z = pcall(function() return point:x(), point:y(), point:z() end)
            if okXYZ then return tonumber(x), tonumber(y), tonumber(z) end
        end
    end
    return tonumber((call(vehicle, "getX"))), tonumber((call(vehicle, "getY"))), nil
end

local function heading(vehicle)
    local vectorType = rawget(_G, "Vector3f")
    if type(vectorType) ~= "table" or type(vectorType.new) ~= "function" then return nil, nil end
    local okVector, vector = pcall(vectorType.new)
    if not okVector then return nil, nil end
    local forward = call(vehicle, "getForwardVector", vector)
    return tonumber((call(forward, "x"))), tonumber((call(forward, "z")))
end

function E.observe(player, state, vehicle, seat)
    if player == nil or type(state) ~= "table" or vehicle == nil or tonumber(seat) ~= 0 or not enabled() then
        close("pilot_state_ended")
        return false
    end
    local localPlayer = getSpecificPlayer and getSpecificPlayer(0) or nil
    if player ~= localPlayer then return false end

    local timestamp = now()
    if timestamp < nextSample then return writer ~= nil end
    nextSample = timestamp + SAMPLE_MS
    if not open(timestamp) then return false end

    local x, y, z = worldPosition(vehicle)
    local modData = call(vehicle, "getModData")
    local ground = modData and tonumber(modData.currentGroundZ) or nil
    local agl = z and ground and (z - ground) or nil
    local vertical = z and previousZ and previousMs and timestamp > previousMs
        and ((z - previousZ) / ((timestamp - previousMs) / 1000)) or nil
    previousZ, previousMs = z, timestamp
    local controls = table.concat({
        "W=" .. tostring(state.liftUp == true), "S=" .. tostring(state.liftDown == true),
        "A=" .. tostring(state.yawLeft == true), "D=" .. tostring(state.yawRight == true),
        "UP=" .. tostring(state.pitchUp == true), "DOWN=" .. tostring(state.pitchDown == true),
        "LEFT=" .. tostring(state.rollLeft == true), "RIGHT=" .. tostring(state.rollRight == true),
    }, ";")
    buffer[#buffer + 1] = table.concat({
        tostring(timestamp), tostring(call(vehicle, "getId") or ""), tostring(call(vehicle, "getScriptName") or ""),
        "0", controls, number(x), number(y), number(z), number(ground), number(agl), number(vertical),
        number(call(vehicle, "getCurrentSpeedKmHour")), number((heading(vehicle))),
    }, ",") .. "\n"

    if timestamp >= nextFlush then
        if flush() then
            nextFlush = timestamp + FLUSH_MS
            log("CAPTURE_HEARTBEAT rows=active latest_z=" .. number(z) .. " agl=" .. number(agl))
        else
            close("sample_write_failed")
            return false
        end
    end
    return true
end

function E.stop(reason)
    close(reason or "manual_stop")
end

log("READY lab_only=true file_api=" .. tostring(type(getFileWriter) == "function"))
return E
