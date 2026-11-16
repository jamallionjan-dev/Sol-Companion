function U.invStep()
    if not job or job.phase == "done" then return true end
    local cell = getCell and getCell() or nil
    if cell == nil then return false end
    if job.phase == "plan" then while job.phase == "plan" do planColumn() end      -- s99: a plan begun while perf_slice was on
    elseif job.phase == "squares" then stepSquares(cell)
    elseif job.phase == "vehicles" then stepVehicles(cell)
    elseif job.phase == "conts" then stepConts()
    elseif job.phase == "finish" then finish() end
    return job.phase == "done"
end
-- s99 perf_slice: the same phases a unit at a time until budgetMs is spent (the unit that crosses it finishes)
function U.invStepSliced(budgetMs)
    if not job or job.phase == "done" then return true end
    local cell = getCell and getCell() or nil
    if cell == nil then return false end
    local stopAt = nowMs() + budgetMs
    while job.phase ~= "done" do
        local ph = job.phase
        if ph == "plan" then planColumn()
        elseif ph == "squares" then
            if job.si <= #job.squares then squareOne(cell) end
            if job.si > #job.squares then job.phase = "vehicles" end
        elseif ph == "vehicles" then stepVehicles(cell)
        elseif ph == "conts" then contUnit()
        elseif ph == "finish" then finish() end
        if nowMs() >= stopAt then break end
    end
    return job.phase == "done"
end
