    if catJob ~= nil then                                                         -- s99 perf_slice: a catalog on its way
        local t0 = nowMs()
        local okS, done = pcall(catalogStep, catSliceOn() and CAT_SLICE_MS or 1000000)
        if not okS or done then catJob = nil end
        if U.perfAdd then U.perfAdd("actions_catalog", nowMs() - t0) end
    elseif ((U._catalogDue and tt >= U._catalogDue) or tt - lastCat >= 120000) and U.solActor and U.solActor() then
        lastCat, U._catalogDue = tt, nil
        if catSliceOn() then catJob = { phase = "pages", pi = 1, pre = {} }
        else
        local t0 = nowMs(); pcall(writeCatalog); if U.perfAdd then U.perfAdd("actions_catalog", nowMs() - t0) end
        end
    end
end
