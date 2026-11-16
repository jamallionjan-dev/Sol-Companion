"""Run only after the game is closed. Sol farms by herself now: stock comes from the whole-base scan, her own hold keeps her on the farm, Living Fellows' farming is shut for her.
usage: apply_s33_lua.py <SolInventory.lua> <SolAuthority.lua> <SolGate.lua> <SolChores.lua> <SCFarmWork.lua> <SCCommands.lua>"""
import sys
def patch(p, pairs):
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b, *n in pairs:
        a, b = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a) == (n[0] if n else 1), (p, a[:70], t.count(a))
        t = t.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("applied to", p)
patch(sys.argv[1], [
("""             sample = { ammo = {}, food = {} }, ammo = {} }
""", """             sample = { ammo = {}, food = {} }, ammo = {}, places = {}, farm = {}, waterSources = {} }
"""),
("""                if o ~= nil and not is(o, "IsoDeadBody") then
""", """                if o ~= nil and not is(o, "IsoDeadBody") then
                    local litres = method(o, "hasWater") == true and num(method(o, "getFluidAmount")) or nil     -- what could fill a watering can, and where: water only
                    if litres ~= nil and litres > 0 and #model.waterSources < 64 then
                        model.waterSources[#model.waterSources + 1] = { x = s[1], y = s[2], z = s[3], oi = i, l = litres, tainted = method(o, "isTaintedWater") == true }
                    end
"""),
("""                        if c ~= nil then job.conts[#job.conts + 1] = { cont = c, where = "house", depth = 0, room = room, x = s[1], y = s[2], z = s[3] } end
""", """                        if c ~= nil then job.conts[#job.conts + 1] = { cont = c, where = "house", depth = 0, room = room, x = s[1], y = s[2], z = s[3], oi = i, ci = k } end
"""),
("""local function stepConts()
    local n = 0
""", """-- so a row can be found again: the square, the object on it and its container. The farm reads this; the table for the Mind is unchanged.
local MAX_PLACES, MAX_FARM = 400, 1500
local function placeFor(e)
    if e.where ~= "house" or e.x == nil or e.depth ~= 0 then return nil end
    if #model.places >= MAX_PLACES then model.trunc = true; return nil end
    local p = { x = e.x, y = e.y, z = e.z, oi = e.oi, ci = e.ci, room = e.room, kind = tostring(method(e.cont, "getType") or ""), food = 0 }
    model.places[#model.places + 1] = p
    return p
end
local function noteFarm(e, it, d, place)
    if place ~= nil and d.food ~= nil then place.food = place.food + 1 end
    if (e.where ~= "house" and e.where ~= "sol") or type(U.invFarmTag) ~= "function" then return end
    local ok, row = pcall(U.invFarmTag, it, d.type)
    if not ok or type(row) ~= "table" then return end
    if #model.farm >= MAX_FARM then model.trunc = true; return end
    row.type, row.name, row.where, row.x, row.y, row.z, row.oi, row.ci, row.depth = d.type, d.name, e.where, e.x, e.y, e.z, e.oi, e.ci, e.depth
    model.farm[#model.farm + 1] = row
end

local function stepConts()
    local n = 0
"""),
("""            local list = method(e.cont, "getItems")
            local cnt = list and num(method(list, "size")) or 0
            for i = 0, cnt - 1 do
                local it = method(list, "get", i)
                if it ~= nil then
                    local d = itemRead(it)
                    addItem(model, e.where, d, e.label or e.room)
                    if d.bag ~= nil and e.depth < MAX_DEPTH then
                        job.conts[#job.conts + 1] = { cont = d.bag, where = e.where, depth = e.depth + 1, label = e.label, room = e.room }
""", """            local list = method(e.cont, "getItems")
            local cnt = list and num(method(list, "size")) or 0
            local place = placeFor(e)
            for i = 0, cnt - 1 do
                local it = method(list, "get", i)
                if it ~= nil then
                    local d = itemRead(it)
                    addItem(model, e.where, d, e.label or e.room)
                    noteFarm(e, it, d, place)
                    if d.bag ~= nil and e.depth < MAX_DEPTH then
                        job.conts[#job.conts + 1] = { cont = d.bag, where = e.where, depth = e.depth + 1, label = e.label, room = e.room, x = e.x, y = e.y, z = e.z, oi = e.oi, ci = e.ci }
"""),
("""function U.invModel() return model end
""", """function U.invModel() return model end
function U.invLast() return last end               -- the last scan that finished; a running one is half a picture
"""),
])
patch(sys.argv[2], [
("""function A.allowsDecision(actor, kind, detail)
""", """-- true while she is working the farm: following him would pull her off it. Her own walks are Living Fellows' go_to (a "tactical" decision), so that one stays.
function A.farmHeld(actor)
    if type(SolUI) ~= "table" or type(SolUI.solFarmHeld) ~= "function" then return false end
    if type(SolUI.solActor) == "function" then
        local okA, s = pcall(SolUI.solActor)
        if okA and s ~= nil and s ~= actor then return false end
    end
    local ok, held = pcall(SolUI.solFarmHeld)
    return ok and held == true
end
function A.allowsDecision(actor, kind, detail)
    if tostring(kind) == "follow" and A.farmHeld(actor) then return false end
"""),
("""    if type(SolOrders) == "table" and type(SolOrders.busy) == "function" then
        local ok, b = pcall(SolOrders.busy)
""", """    if A.farmHeld(actor) then return true, "sol_farm_work" end
    if type(SolOrders) == "table" and type(SolOrders.busy) == "function" then
        local ok, b = pcall(SolOrders.busy)
"""),
])
FARM_ROLE = """    if role == "farmer" then                                                  -- farming is hers now, not a Living Fellows role
        if type(U.solFarmOrder) ~= "function" then return false, "lf:farm_unavailable" end
        local okF, whyF = U.solFarmOrder("keeper")
        if okF then return true, "base_role_farmer" end
        return false, "lf:" .. tostring(whyF)
    end
"""
patch(sys.argv[3], [
("""    if not role then return base(option) end                       -- unknown word: SolChores answers
""", """    if not role then return base(option) end                       -- unknown word: SolChores answers
""" + FARM_ROLE),
])
patch(sys.argv[4], [
("""    if not role then return false, "unknown_role" end
""", """    if not role then return false, "unknown_role" end
""" + FARM_ROLE),
])
patch(sys.argv[5], [
("""function FarmWork.update(actor, baseState, job, runtime)
""", """function FarmWork.update(actor, baseState, job, runtime)
    if type(SolUI) == "table" and type(SolUI.solActor) == "function" then       -- Sol farms by her own runner (SolFarmWork), never through these jobs
        local okSol, sol = pcall(SolUI.solActor)
        if okSol and sol ~= nil and sol == actor then return false, "sol_farm_own", true end
    end
"""),
])
patch(sys.argv[6], [
("""    if type(role) ~= "string" or not SC.BaseLife.ROLES[role] then
        return false, "invalid_base_role"
    end
    -- Selecting a job is the whole assignment.""", """    if type(role) ~= "string" or not SC.BaseLife.ROLES[role] then
        return false, "invalid_base_role"
    end
    if role == "farmer" and type(SolUI) == "table" and type(SolUI.solActor) == "function" then    -- Sol farms by her own runner
        local okSol, sol = pcall(SolUI.solActor)
        if okSol and sol ~= nil and sol == actor then return false, "sol_farm_own" end
    end
    -- Selecting a job is the whole assignment."""),
])
