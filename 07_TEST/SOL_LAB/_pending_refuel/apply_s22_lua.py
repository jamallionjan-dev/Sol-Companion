"""Run only after the game is closed. While she is keeping the farm or home, Living Fellows may also wash and sleep her; the switch for the farm work.
usage: apply_s22_lua.py <SolAuthority.lua> <SCDecision.lua>"""
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
("""    "order_arbiter",      -- 14 an order that meets a short action of hers waits for it instead of hammering it
}
""", """    "order_arbiter",      -- 14 an order that meets a short action of hers waits for it instead of hammering it
    "sol_farm",           -- 15 her own order of work on the farm, and staying home to rest
}
"""),
("""function A.allowsDecision(actor, kind, detail)
    if A.instinctOnly ~= true or not A.on("instinct_only") then return true end
""", """-- true while a standing order lets her wash, sleep and rest (SolFarmKeeper decides)
function A.restWanted(actor)
    local K = rawget(_G, "SolFarmKeeper")
    if type(K) ~= "table" or type(K.restWanted) ~= "function" then return false end
    local ok, wanted = pcall(K.restWanted, actor)
    return ok and wanted == true
end
function A.allowsDecision(actor, kind, detail)
    if A.instinctOnly ~= true or not A.on("instinct_only") then return true end
    if tostring(kind) == "downtime" and A.restWanted(actor) then
        local ok, s = true, nil
        if type(SolUI) == "table" and type(SolUI.solActor) == "function" then ok, s = pcall(SolUI.solActor) end
        if ok and (s == nil or s == actor) then return true end
    end
"""),
])
patch(sys.argv[2], [
("""        elseif commands.order == "base_duty" then
            if not bleeding then add("base_work", 58, false) end
        end
""", """        elseif commands.order == "base_duty" then
            if not bleeding then add("base_work", 58, false) end
            -- Sol, on a standing order: washing and sleep ahead of waiting for farm work, after treating and feeding herself
            if not bleeding and type(SolAuthority) == "table" and type(SolAuthority.restWanted) == "function"
                and SolAuthority.restWanted(actor) then
                add("downtime", 72, false)
            end
        end
"""),
])
