function U.invStep()
    if not job or job.phase == "done" then return true end
    local cell = getCell and getCell() or nil
    if cell == nil then return false end
    if job.phase == "squares" then stepSquares(cell)
    elseif job.phase == "vehicles" then stepVehicles(cell)
    elseif job.phase == "conts" then stepConts()
    elseif job.phase == "finish" then finish() end
    return job.phase == "done"
end
