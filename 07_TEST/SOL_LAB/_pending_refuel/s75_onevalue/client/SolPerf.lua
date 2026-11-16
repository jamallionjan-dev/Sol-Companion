-- SolPerf.lua - how much time each part of Sol takes. Every 15 s one line per part in console.txt:
--   [SolPerf] fps=NN | chat 120ms/450 calls max 9 | pages ... | scan ... (ms summed over the 15 s window)
-- Parts report themselves with SolUI.perfAdd(name, ms) / SolUI.perfWrap(name, fn, ...).
SolUI = SolUI or {}
local U = SolUI
U.PERF_VERSION = "0.1.0"
local WINDOW_MS = 15000
local stats, windowStart = {}, nil
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
function U.perfAdd(name, ms)
    local s = stats[name]
    if not s then s = { total = 0, calls = 0, max = 0 }; stats[name] = s end
    s.total = s.total + ms; s.calls = s.calls + 1
    if ms > s.max then s.max = ms end
end
function U.perfWrap(name, fn, ...)
    local t0 = nowMs()
    local r1, r2, r3 = fn(...)
    U.perfAdd(name, nowMs() - t0)
    return r1, r2, r3
end
local function fps()
    if type(getAverageFPS) == "function" then local ok, v = pcall(getAverageFPS); if ok and v then return math.floor(v + 0.5) end end
    if type(getPerformance) == "function" then local ok, p = pcall(getPerformance); if ok and p and p.getFPS then local ok2, v = pcall(p.getFPS, p); if ok2 then return v end end end
    return -1
end
local function report()
    local parts = {}
    for name, s in pairs(stats) do parts[#parts + 1] = { name = name, s = s } end
    table.sort(parts, function(a, b) return a.s.total > b.s.total end)
    local line = "[SolPerf] fps=" .. tostring(fps()) .. " window=" .. WINDOW_MS / 1000 .. "s"
    for _, p in ipairs(parts) do
        line = line .. " | " .. p.name .. " " .. p.s.total .. "ms/" .. p.s.calls .. " max " .. p.s.max
    end
    print(line)
    stats = {}
end
local function onTick()
    local t = nowMs()
    if not windowStart then windowStart = t end
    if t - windowStart >= WINDOW_MS then windowStart = t; pcall(report) end
end
if Events and Events.OnTick then Events.OnTick.Add(onTick) end
print("[SolPerf] ready v" .. U.PERF_VERSION)
