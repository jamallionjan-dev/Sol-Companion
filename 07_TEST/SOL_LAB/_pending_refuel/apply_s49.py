"""scanAhead slid the route sideways by her distance from it, so a car not yet on the road saw walls that are nowhere near her path.
Game closed only. usage: apply_s49.py <client dir>"""
import os, shutil, sys
P =os.path.join(sys.argv[1], "SolBypass.lua")
NL, CRLF = chr(10), chr(13) + chr(10)
a = """    local okC, cars = pcall(B.world.cars, x, y, reach + 6)
    if not okC or type(cars) ~= "table" then cars = {} end
    local cache = {}
"""
b = """    if on("road_first") and math.abs(side) > SCAN_MAX_SIDE then return nil end      -- not on the road yet: nothing on the road's line says anything about where she is
    local okC, cars = pcall(B.world.cars, x, y, reach + 6)
    if not okC or type(cars) ~= "table" then cars = {} end
    local cache = {}
"""
a0 = "function B.scanAhead(path, x, y, reach, halfLength, halfWidth)" + NL
b0 = "local SCAN_MAX_SIDE = 4" + NL + a0
a1 = """    local walked, i, sx, sy, start = 0, at, x, y, (halfLength or 2.8) + 1.0
"""
b1 = a1 + """    if on("road_first") then                                                        -- the sideways shift is added below: start from the road's line, or the first stretch counts it twice
        local p, q = path[at], path[at + 1]
        local ex, ey = q.x - p.x, q.y - p.y
        local l2 = ex * ex + ey * ey
        local u = l2 > 0 and math.max(0, math.min(1, ((x - p.x) * ex + (y - p.y) * ey) / l2)) or 0
        sx, sy = p.x + ex * u, p.y + ey * u
    end
"""
t = open(P, encoding="utf-8", newline="").read()
nl = CRLF if CRLF in t else NL
for x, y in ((a, b), (a0, b0), (a1, b1)):
    x2, y2 = x.replace(NL, nl), y.replace(NL, nl)
    assert t.count(x2) == 1, x[:50]
    t = t.replace(x2, y2)
open(P, "w", encoding="utf-8", newline="").write(t)
D = os.path.join(sys.argv[1], "SCDriving.lua")
if os.path.exists(D):
    a2 = "function Driving.routeText(points)" + NL + '    if type(points) ~= "table" then return nil, "route has no points" end' + NL
    b2 = a2 + '    local RF = rawget(_G, "SolRoadFirst")' + NL + '    if type(RF) == "table" and RF.on() then points = RF.spaced(points) end' + NL
    d = open(D, encoding="utf-8", newline="").read()
    dn = CRLF if CRLF in d else NL
    assert d.count(a2.replace(NL, dn)) == 1, "routeText"
    open(D, "w", encoding="utf-8", newline="").write(d.replace(a2.replace(NL, dn), b2.replace(NL, dn)))
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "SolRoadFirst.lua"), os.path.join(sys.argv[1], "SolRoadFirst.lua"))
F = os.path.join(sys.argv[1], "SolFuel.lua")
if os.path.exists(F):
    a3 = '    if cur >= cap - 0.5 then return true, "tank_full" end' + NL
    b3 = '    local solA = rawget(_G, "SolAuthority")' + NL + '    local topUp = type(solA) == "table" and type(solA.on) == "function" and solA.on("refuel_top_up") == true' + NL + '    if cur >= cap - (topUp and 0.01 or 0.5) then return true, "tank_full" end' + NL
    f = open(F, encoding="utf-8", newline="").read()
    fn = CRLF if CRLF in f else NL
    assert f.count(a3.replace(NL, fn)) == 1, "tank_full"
    open(F, "w", encoding="utf-8", newline="").write(f.replace(a3.replace(NL, fn), b3.replace(NL, fn)))
    A = os.path.join(sys.argv[1], "SolAuthority.lua")
    t2 = open(A, encoding="utf-8", newline="").read()
    an = CRLF if CRLF in t2 else NL
    k = "A.FIXES = {" + an
    assert t2.count(k) == 1
    open(A, "w", encoding="utf-8", newline="").write(t2.replace(k, k + '    "refuel_top_up", "refuel_short_hop",' + an))
    fix = os.path.join(sys.argv[1], "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("refuel_top_up=on" + CRLF + "refuel_short_hop=on" + CRLF)
print("applied")
