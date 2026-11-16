"""Run only after the game is closed. Walking to the car: when she stalls she is asked again after 1.5 s, not after 5; a car that has left the loaded world is forgotten instead of crashing the boarding.
usage: apply_s38_lua.py <SolGPS.lua>"""
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
PAIRS = [
("local ORDER_WAIT_LAST_ASK = 4000       -- the door walk re-asks 5 s after lastAsk, so this leaves about 1 s",
 "local ORDER_WAIT_LAST_ASK = 500        -- the door walk re-asks 1.5 s after lastAsk, so this leaves about 1 s"),
("elseif t - w.lastAsk > 5000 and t - w.movedAt > 2500 and U.solGoto then",
 "elseif t - w.lastAsk > 1500 and t - w.movedAt > 1200 and U.solGoto then"),
("""    local veh = G.wheelCar or nearestCar()
    if not veh then G.lastResult, G.reason = "failed", "no_vehicle_near"; return false, G.reason end
""",
 """    if G.wheelCar ~= nil and not carStillLoaded(G.wheelCar) then log("the car she was going for is no longer in the loaded world"); G.wheelCar = nil end
    local veh = G.wheelCar or nearestCar()
    if not veh then G.lastResult, G.reason = "failed", "no_vehicle_near"; return false, G.reason end
"""),
("""local function nearestCar()
""",
 """local function carStillLoaded(car)
    local sc = LF()
    local service = sc and sc.Vehicle
    if type(service) ~= "table" or type(service.loadedVehicles) ~= "function" then return true end
    local ok, vehicles = pcall(service.loadedVehicles)
    if not ok or type(vehicles) ~= "table" then return true end
    for _, v in ipairs(vehicles) do if v == car then return true end end
    return false
end
local function nearestCar()
"""),
]
for a, b in PAIRS:
    a, b = a.replace("\n", nl), b.replace("\n", nl)
    assert t.count(a) == 1, (a[:50], t.count(a))
    t = t.replace(a, b)
open(p, "w", encoding="utf-8", newline="").write(t)
print("applied to", p)
