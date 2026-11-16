"""Run only after the game is closed. What Living Fellows' farm job is missing, for Sol: Watering Can as a supply, the plant read fresh, new furrows, weeds, fertiliser, and a harvest that does not need LF's own scan.
usage: apply_s21_lua.py <SCFarmWork.lua>"""
import sys
def patch(p, pairs):
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b in pairs:
        a, b = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a) == 1, (p, a[:70], t.count(a))
        t = t.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("applied to", p)
patch(sys.argv[1], [
("""    local plant, ok = invoke(system, "getLuaObjectOnSquare", square)
    return ok and plant or nil
""", """    local plant, ok = invoke(system, "getLuaObjectOnSquare", square)
    if ok and plant then invoke(plant, "updateFromIsoObject") end
    return ok and plant or nil
"""),
("""    if string.find(kind, "wateringcan", 1, true)
        or string.find(kind, "compostbag", 1, true)
""", """    if string.find(kind, "wateringcan", 1, true)
        or string.find(kind, "wateredcan", 1, true)
        or string.find(kind, "compostbag", 1, true)
"""),
("""    if plant.hasSeeds == true then return true end
""", """    if plant.hasSeed == true or plant.hasSeeds == true then return true end
"""),
("""function FarmWork.audit(base)
""", """function FarmWork.recoverNow(limit) recoverPending(math.max(1, math.floor(tonumber(limit) or 4))) end

function FarmWork.audit(base)
"""),
("""local function compost(item)
    return U().itemHasTag(item, "COMPOST")
        or string.find(string.lower(U().itemType(item)), "compostbag", 1, true) ~= nil
end
""", """local function compost(item)
    return U().itemHasTag(item, "COMPOST") or U().itemHasTag(item, "FERTILIZER")
        or string.find(string.lower(U().itemType(item)), "compostbag", 1, true) ~= nil
        or string.find(string.lower(U().itemType(item)), "fertilizer", 1, true) ~= nil
end
"""),
("""    if operation == "compost" then return plant.compost == true end
    if operation == "harvest" then return select(1, invoke(plant, "canHarvest")) == true end
""", """    if operation == "compost" then return tonumber(plant.fertilizer) or 0 end
    if operation == "harvest" then return select(1, invoke(plant, "canHarvest")) == true end
"""),
("""    if work.operation == "compost" then return plant and plant.compost == true end
    if work.operation == "cure" then
        return plant and (tonumber(plant[target.diseaseField]) or 0) < (tonumber(work.before) or 0)
    end
""", """    if work.operation == "compost" then
        return plant and (plant.compost == true or (tonumber(plant.fertilizer) or 0) > (tonumber(work.before) or 0))
    end
    if work.operation == "weed" then return plant == nil or plant.hasWeeds ~= true end
    if work.operation == "cure" then
        return plant and (tonumber(plant[target.diseaseField]) or 0) < (tonumber(work.before) or 0)
    end
"""),
("""    else before = plantSnapshot(plant, operation) end
""", """    else before = plant and plantSnapshot(plant, operation) or false end
"""),
("""    if not plant then return false, "farm_plot_missing", true end
    if target.operation == "replant" and operation == "plow" and plant.state == "plow" then
""", """    if not plant and target.operation ~= "plow" then return false, "farm_plot_missing", true end
    if plant and target.operation == "replant" and operation == "plow" and plant.state == "plow" then
"""),
("""    local alreadyDone = target.operation == "sow"
            and plant.state == "seeded" and plant.typeOfSeed == target.cropType
""", """    local alreadyDone = plant and (target.operation == "plow" and plant.state == "plow"
        or target.operation == "sow"
            and plant.state == "seeded" and plant.typeOfSeed == target.cropType
"""),
("""        or target.operation == "compost" and plant.compost == true
        or target.operation == "cure" and target.diseaseField ~= nil
            and (tonumber(plant[target.diseaseField]) or 0) <= 0
    if target.operation == "harvest" and select(1, invoke(plant, "canHarvest")) ~= true then
""", """        or target.operation == "compost" and (plant.compost == true or (tonumber(plant.fertilizer) or 0) > 0)
        or target.operation == "weed" and plant.hasWeeds ~= true
        or target.operation == "cure" and target.diseaseField ~= nil
            and (tonumber(plant[target.diseaseField]) or 0) <= 0)
    if target.operation == "harvest" and select(1, invoke(plant, "canHarvest")) ~= true then
"""),
("""    if operation == "harvest" and not harvestAllowed(plant) then
        return false, "farm_seed_reserve_changed", true
""", """    if operation == "harvest" and target.solPlanned ~= true and not harvestAllowed(plant) then
        return false, "farm_seed_reserve_changed", true
"""),
])
