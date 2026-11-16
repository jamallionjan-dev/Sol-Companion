        local function invTick()
            local t = nowMs()
            if job and job.phase ~= "done" then
                U.invStep()
                if U.perfAdd then U.perfAdd("inventory", nowMs() - t) end
                return
            end
