-- SolBudget.lua - one allowance per frame for Sol's background work.
--   Work registers here instead of hanging on OnTick. Each frame the due tasks run, most important first, until the allowance is spent;
--   the rest wait for the next frame. A task that has waited far too long runs anyway, so nothing starves.
--   fn(remainingMs) does a bounded slice and returns.
SolBudget = SolBudget or {}
local B = SolBudget
local FRAME_MS = 2
B.tasks = B.tasks or {}
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end

function B.register(name, fn, options)
    local o = options or {}
    local every = tonumber(o.everyMs) or 0
    for _, t in ipairs(B.tasks) do
        if t.name == name then t.fn, t.every, t.priority = fn, every, tonumber(o.priority) or 5; return end
    end
    B.tasks[#B.tasks + 1] = { name = name, fn = fn, every = every, priority = tonumber(o.priority) or 5, due = nowMs(), seq = #B.tasks }
    table.sort(B.tasks, function(a, b) if a.priority ~= b.priority then return a.priority < b.priority end return a.seq < b.seq end)
end

function B.step()
    local tasks = B.tasks
    local t0 = nowMs()
    for i = 1, #tasks do
        local k = tasks[i]
        if t0 >= k.due then
            local left = FRAME_MS - (nowMs() - t0)
            local starving = t0 - k.due > math.max(k.every * 3, 3000)
            if left > 0 or starving then
                k.due = t0 + k.every
                local ok, err = pcall(k.fn, math.max(left, 1))
                if not ok then print("[SolBudget] " .. k.name .. " failed: " .. tostring(err)) end
            end
        end
    end
    local SolU = rawget(_G, "SolUI")
    if type(SolU) == "table" and type(SolU.perfAdd) == "function" then SolU.perfAdd("budget", nowMs() - t0) end
end

if not B._hooked and Events and Events.OnTick then
    B._hooked = true
    Events.OnTick.Add(B.step)
end
return B
