"""Run only after the game is closed. The farmer gate counts what the job can really borrow: Watering Can, fertiliser, food storage; an unloaded storage is not a shortage.
usage: apply_s20_lua.py <SolGate.lua>"""
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
("""    if call(gu.itemHasTag, item, "COMPOST") or string.find(kind, "compostbag", 1, true) then return "compost" end
    if string.find(kind, "wateringcan", 1, true) then return "can" end
""", """    if call(gu.itemHasTag, item, "COMPOST") or call(gu.itemHasTag, item, "FERTILIZER") or string.find(kind, "compostbag", 1, true) or string.find(kind, "fertilizer", 1, true) then return "compost" end
    if string.find(kind, "wateredcan", 1, true) or string.find(kind, "wateringcan", 1, true) then return "can" end
"""),
("""-- take stock: Sol's bag (nested containers included) and every registered base storage that can be opened
""", """-- take stock: only what the farm job can borrow, the categories it withdraws from (a storage not loaded is counted apart, it is unknown rather than empty)
"""),
("""    local inv = call(gu.inventory, sol)
    if inv ~= nil then add(call(gu.inventoryItemsDeep, inv, 180, 12)) end
    local BL = sc.BaseLife
    if type(BL) == "table" and type(BL.storageRows) == "function" then
        local rows = call(BL.storageRows, nil, false)
        if type(rows) == "table" then
            for _, storage in ipairs(rows) do
                local container = call(BL.resolveContainer, storage)
                if container ~= nil then
                    have.stor = have.stor + 1
                    add(call(gu.inventoryItems, container, 80))
                else
                    have.unloaded = have.unloaded + 1
                end
            end
        end
    end
    return have
""", """    local BL = sc.BaseLife
    if type(BL) == "table" and type(BL.storageRows) == "function" then
        for _, cat in ipairs({ "farming", "tools", "water" }) do
            local rows = call(BL.storageRows, cat, true)
            if type(rows) == "table" then
                for _, storage in ipairs(rows) do
                    local container = call(BL.resolveContainer, storage)
                    if container ~= nil then
                        have.stor = have.stor + 1
                        add(call(gu.inventoryItems, container, 80))
                    else
                        have.unloaded = have.unloaded + 1
                    end
                end
            end
        end
    end
    return have
"""),
("""        if have.seed + have.tool + have.can + have.compost + have.spray == 0 then miss[#miss + 1] = "farm_supplies" end
        local out = call(BL.depositStorageRows, "output")
        if type(out) ~= "table" or #out == 0 then miss[#miss + 1] = "out_storage" end
""", """        if have.seed + have.tool + have.can + have.compost + have.spray == 0 and have.unloaded == 0 then miss[#miss + 1] = "farm_supplies" end
        local food = call(BL.depositStorageRows, "food")
        if type(food) ~= "table" or #food == 0 then miss[#miss + 1] = "food_storage" end
"""),
])
