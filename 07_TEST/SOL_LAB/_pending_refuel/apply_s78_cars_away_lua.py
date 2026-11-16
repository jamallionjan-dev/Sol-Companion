"""s78_cars_away_lua (Jamal 2026-11-10 21:35, 21:36): "سول شو في سيارات حواليكي" while she was at home, ~200 tiles from him, answered
"ما قدرت شوف شو في سيارات حواليّ هلأ". Her body was registered but its square was not loaded (SolFar.bodyGone: no square under her
for 2 s), so the snapshot said sol.away and the scan's cars were the ones around HIM (none). The game's read-only list of the saved
cars around her (solCarsNearRequest, the far_car path) was behind the far_car switch, which is off in the lab.

1. SolFar.lua: U.solFar("cars") answers whatever the far_car switch says (a wrapper around U.solFar; the far_car block itself is
   untouched). It only reads the saved vehicle rows around where she is (Java SolCarsNear, world streamer thread, read only); nothing
   is chosen, moved or started. With the switch off the head says "cars:<n>/own|..." so the Mind does not offer to bring one of them
   (only her own car can come then). A "scanning" answer is asked again at once (twice), in case the list is already in.
2. SolWorldScan.lua: when her body is in the loaded world, snap.solVehicles lists the loaded cars within 60 tiles of HER (same
   fields as snap.vehicles, with s77's locked/key), wherever he is. The Mind's cars_near answers from it (apply_s78_cars_away_mind.py).
Both insertions sit outside every earlier installer's text, so re-running those stays a no-op.
Needs apply_s77_lua.py first (carUse). Kahlua: num((call(...))) everywhere. Game closed only. In place, idempotent.
usage: apply_s78_cars_away_lua.py <client dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)


def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))


FAR_ANCHOR = 'SolBudget.register("far", tick, { everyMs = 1000, priority = 5 })\n'
FAR_BLOCK = r'''-- s78 cars_away: "cars" answers whatever the far_car switch says; it only reads the saved vehicle rows around her (Java, read
-- only). With the switch off the head says "cars:<n>/own|": only her own car may come, so the Mind offers none of these.
local function carsAnswer78()
    if actor() ~= nil then return true, "here" end
    local okA, why = carsAnswer()
    for _ = 1, 2 do                                                             -- carsAnswer reads a list in, then says "scanning" once
        if okA == false and why == "scanning" then okA, why = carsAnswer() end
    end
    if okA == true and not farCarOn() then why = (string.gsub(tostring(why), "^cars:(%d+)|", "cars:%1/own|", 1)) end
    return okA, why
end
local solFar77 = U.solFar
function U.solFar(option)
    if string.lower(tostring(option or "status")) == "cars" then return carsAnswer78() end
    return solFar77(option)
end
-- s78 end
'''
FAR = [(FAR_ANCHOR, FAR_BLOCK + FAR_ANCHOR)]

SWS_ANCHOR = '''    return snap
    end
    -- the same squares in the same order as one loop would read them, but a few at a time
'''
SWS_BLOCK = r'''    -- s78 cars_away: the loaded cars around HER body, wherever he is (the Mind's cars_near). Read only. Absent when her body is not
    -- in the loaded world (sol.away): the Mind then asks sol_far "cars", the saved rows around her.
    local sx78, sy78 = num((call(sol, "getX"))), num((call(sol, "getY")))
    if sol ~= nil and snap.sol ~= nil and snap.sol.away ~= true and sx78 ~= nil and sy78 ~= nil then
        local REACH78 = 60
        snap.solVehicles = {}
        for vi = 1, #vlist do
            local v = vlist[vi]
            local vx, vy = num((call(v, "getX"))), num((call(v, "getY")))
            if vx ~= nil and vy ~= nil and math.abs(vx - sx78) <= REACH78 and math.abs(vy - sy78) <= REACH78 and #snap.solVehicles < 40 then
                local gas = call(v, "getPartById", "GasTank")
                local info = { name = call((call(v, "getScript")), "getName") or "vehicle", x = round(vx, 0), y = round(vy, 0),
                               id = num((call(v, "getSqlId"))) or num((call(v, "getId"))),
                               fuel = gas and round((call(gas, "getContainerContentAmount")), 1) or nil,
                               fuelMax = gas and num((call(gas, "getContainerCapacity"))) or nil }
                info.locked, info.key = carUse(v, sol)
                snap.solVehicles[#snap.solVehicles + 1] = info
            end
        end
    end
    -- s78 end
'''
SWS = [(SWS_ANCHOR, SWS_BLOCK + SWS_ANCHOR)]


def client(cl):
    sws = os.path.join(cl, "SolWorldScan.lua")
    assert "local function carUse(v, sol)" in open(sws, encoding="utf-8").read(), "apply_s77_lua.py first"
    for o, n in FAR: edit(os.path.join(cl, "SolFar.lua"), o, n)
    for o, n in SWS: edit(sws, o, n)


if __name__ == "__main__":
    client(sys.argv[1])
    print("s78_cars_away_lua applied")
