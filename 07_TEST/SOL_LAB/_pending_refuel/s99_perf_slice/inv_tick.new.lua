        local function invTick(remainingMs)
            local t = nowMs()
            if job and job.phase ~= "done" then
                local A99_ = rawget(_G, "SolAuthority")                         -- s99 perf_slice: about 4 ms a frame at most
                if type(A99_) == "table" and type(A99_.on) == "function" and A99_.on("perf_slice") == true then
                    local b = tonumber(remainingMs) or 4
                    if b > 4 then b = 4 end
                    if b < 1 then b = 1 end
                    U.invStepSliced(b)
                else
                    U.invStep()
                end
                if U.perfAdd then U.perfAdd("inventory", nowMs() - t) end
                return
            end
