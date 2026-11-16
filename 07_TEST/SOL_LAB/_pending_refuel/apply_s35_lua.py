"""Run only after the game is closed. The base he marked in the game is her home when no other home has been named, and the parking area he marked is known.
usage: apply_s35_lua.py <SolWorldScan.lua>"""
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
a = """    if type(SolHome) == "table" and type(SolHome.get) == "function" then snap.solHome = SolHome.get() end   -- Sol Mind adopts it when its memory has no home
""".replace("\n", nl)
b = """    if type(SolHome) == "table" and type(SolHome.get) == "function" then snap.solHome = SolHome.get() end   -- Sol Mind adopts it when its memory has no home
    if snap.solHome == nil and type(SurvivorCompanion) == "table" and type(SurvivorCompanion.BaseLife) == "table" and type(SurvivorCompanion.BaseLife.active) == "function" then
        local okB, base = pcall(SurvivorCompanion.BaseLife.active)                -- the area he marked as the base is home
        local x1, y1, x2, y2, floor = nil, nil, nil, nil, 0
        for _, z in ipairs(okB and type(base) == "table" and type(base.zones) == "table" and base.zones or {}) do
            if type(z) == "table" and z.kind == "area" and tonumber(z.x1) and tonumber(z.x2) and tonumber(z.y1) and tonumber(z.y2) then
                local ax, bx, ay, by = math.min(z.x1, z.x2), math.max(z.x1, z.x2), math.min(z.y1, z.y2), math.max(z.y1, z.y2)
                x1, x2, y1, y2 = x1 and math.min(x1, ax) or ax, x2 and math.max(x2, bx) or bx, y1 and math.min(y1, ay) or ay, y2 and math.max(y2, by) or by
                floor = tonumber(z.z) or floor
            end
        end
        if x1 ~= nil then snap.solHome = { x = math.floor((x1 + x2) / 2), y = math.floor((y1 + y2) / 2), z = floor, fromBase = true } end
    end
    if type(SurvivorCompanion) == "table" and type(SurvivorCompanion.BaseLife) == "table" and type(SurvivorCompanion.BaseLife.active) == "function" then
        local okP, parkBase = pcall(SurvivorCompanion.BaseLife.active)
        for _, z in ipairs(okP and type(parkBase) == "table" and type(parkBase.zones) == "table" and parkBase.zones or {}) do
            if type(z) == "table" and z.kind == "parking" and tonumber(z.x1) and tonumber(z.x2) and tonumber(z.y1) and tonumber(z.y2) then
                snap.solParking = { x = math.floor((z.x1 + z.x2) / 2), y = math.floor((z.y1 + z.y2) / 2) }
                break
            end
        end
    end
""".replace("\n", nl)
assert t.count(a) == 1, t.count(a)
open(p, "w", encoding="utf-8", newline="").write(t.replace(a, b))
print("applied to", p)
