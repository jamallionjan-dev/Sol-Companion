-- SolDriveRecorder.lua - lab only: records how the player drives, so Sol's turning, speeds and lines can be set from real driving.
--   While the player is in a vehicle, whoever drives it, ten samples a second go to ~/Zomboid/Lua/SolDrive_Record_<time>.txt.
--   While he drives, the Java perception dumps the ground around him (it keeps its own 20 s gap and costs the frame next to nothing).
--   Switch: SolAuthority "drive_record". Every game method is looked up before it is called.
SolDriveRecorder = SolDriveRecorder or {}
local R = SolDriveRecorder

local SAMPLE_MS, FLUSH_MS, SCAN_MS = 100, 2000, 1000
local nextSample, nextFlush, nextScan = 0, 0, 0
local writer, buffer = nil, {}

local function now() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)           -- reading a method off an object the game has not exposed throws
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function enabled()
    if type(rawget(_G, "SolLab")) ~= "table" or SolLab.active ~= true then return false end
    local A = rawget(_G, "SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, on = pcall(A.on, "drive_record")
    return ok and on == true
end
local function num(v) return type(v) == "number" and string.format("%.4f", v) or "" end

local function heading(v)
    local Vec = rawget(_G, "Vector3f")
    if Vec == nil then return nil end
    local f = call(v, "getForwardVector", Vec.new())
    return call(f, "x"), call(f, "z")
end

local function flush()
    if writer == nil or #buffer == 0 then return end
    pcall(function()
        writer:write(table.concat(buffer))
    end)
    buffer = {}
end
local function open()
    if writer ~= nil or type(getFileWriter) ~= "function" then return end
    local name = "SolDrive_Record_" .. string.format("%.0f", now()) .. ".txt"       -- the game refuses to write a .csv
    local ok, w = pcall(getFileWriter, name, true, false)
    if ok and w ~= nil then
        writer = w
        buffer[#buffer + 1] = "ms,x,y,hx,hy,kmh,steering,client_steer,throttle,braking,gear,engine_rpm,driver,floor\n"
        print("[SolRecorder] recording to " .. name)
    elseif not R.openFailed then
        R.openFailed = true
        print("[SolRecorder] could not open " .. name)
    end
end
local function close()
    if writer == nil then return end
    flush()
    pcall(function() writer:close() end)
    writer = nil
    print("[SolRecorder] recording closed")
end

local function floorName(x, y)
    if x == nil or y == nil or type(getCell) ~= "function" then return "" end
    local sq = call(getCell(), "getGridSquare", math.floor(x), math.floor(y), 0)
    local name = call(call(call(sq, "getFloor"), "getSprite"), "getName")
    return type(name) == "string" and name or ""
end

local announced = false
local function tick()
    local stepFn = rawget(_G, "solPerceptionStep")
    if type(stepFn) == "function" then pcall(stepFn) end
    if not announced then
        announced = true
        print("[SolRecorder] Java perception available: " .. tostring(type(stepFn) == "function"))
    end
    local t = now()
    if t < nextSample then return end
    nextSample = t + SAMPLE_MS
    local player = getSpecificPlayer and getSpecificPlayer(0) or nil
    local v = call(player, "getVehicle")
    if v == nil or not enabled() then
        if writer ~= nil then close() end
        return
    end
    open()
    local d = call(v, "getDriver")
    local who = "none"
    if d ~= nil then
        local sol = type(SolUI) == "table" and type(SolUI.solActor) == "function" and SolUI.solActor() or nil
        if d == player or call(d, "isLocalPlayer") == true then who = "player"
        elseif sol ~= nil and d == sol then who = "sol"
        else who = "other" end
    end
    local x, y = call(v, "getX"), call(v, "getY")
    local hx, hy = heading(v)
    buffer[#buffer + 1] = table.concat({
        tostring(t), num(x), num(y), num(hx), num(hy), num(call(v, "getCurrentSpeedKmHour")), num(call(v, "getCurrentSteering")),
        "", num(call(v, "getThrottle")), tostring(call(v, "isBraking")),
        tostring(call(v, "getTransmissionNumber")), num(call(v, "getEngineSpeed")), who, floorName(x, y),
    }, ",") .. "\n"
    if t >= nextFlush then nextFlush = t + FLUSH_MS; flush() end
    if t >= nextScan then
        nextScan = t + SCAN_MS
        local start = rawget(_G, "solPerceptionStart")
        if type(start) == "function" and x and y then pcall(start, x, y, 30, "player_driving") end      -- Java keeps its own 20 s gap
    end
end

if Events and Events.OnTick then Events.OnTick.Add(function() pcall(tick) end) end
print("[SolRecorder] ready")
return R
