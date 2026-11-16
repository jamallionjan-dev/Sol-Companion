    -- s99 perf_slice: her and his inventories are read by the first step (first, as before), not when the job is made
    local pre = { function() addContainer(snap, "player", call(player, "getInventory")) end }
    if sol then pre[#pre + 1] = function() addContainer(snap, "sol", call(sol, "getInventory")) end end
