    if ((U._catalogDue and tt >= U._catalogDue) or tt - lastCat >= 120000) and U.solActor and U.solActor() then
        lastCat, U._catalogDue = tt, nil
        local t0 = nowMs(); pcall(writeCatalog); if U.perfAdd then U.perfAdd("actions_catalog", nowMs() - t0) end
    end
end
