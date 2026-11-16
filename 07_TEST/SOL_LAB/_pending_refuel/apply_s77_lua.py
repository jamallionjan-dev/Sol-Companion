"""s77_lua: the world snapshot says, per car, whether Sol could use it, so the Mind's cars_near (apply_s77_mind.py) can say
"مسكّرة" / "ما معي مفتاحها" / "جاهزة" for the cars around her when she is here.
SolWorldScan.lua, each row of snap.vehicles gains two fields (absent = unknown; the Mind then says it does not know, never "ready"):
  locked  true/false   the driver's door (DoorFrontLeft) isLocked
  key     true         a key in the ignition, hotwired with the wires whole, its key in her things (haveThisKeyId) or inside the car
          false        it has a key id and none of those, and her things could be read (or the car has no key id at all)
The same rule as SolFar's loadedCanGo (far_car keys). Read-only: nothing is moved, opened or started.
Kahlua: every call() result that feeds num() is wrapped in its own parentheses. Game closed only. In place, idempotent.
usage: apply_s77_lua.py <client dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)


def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))


CAR_USE = """-- s77 cars_near: could she use this car? Read from the car and her things; the Mind words it, nothing here is spoken.
--   locked: the driver's door (nil when unknown). key: true = key in the ignition, hotwired with the wires whole, its key in her
--   things or inside the car; false = none of those; nil = unknown. The same rule as SolFar's loadedCanGo.
local function carUse(v, sol)
    local locked = nil
    local door = call((call(v, "getPartById", "DoorFrontLeft")), "getDoor")
    if door ~= nil then
        local l = call(door, "isLocked")
        if type(l) == "boolean" then locked = l end
    end
    if call(v, "isKeysInIgnition") == true then return locked, true end
    if call(v, "isHotwired") == true and call(v, "isHotwiredBroken") == false then return locked, true end
    local kid = num((call(v, "getKeyId")))
    if kid == nil then return locked, nil end
    if kid < 0 then return locked, false end
    local inv = nil
    if sol ~= nil then inv = call(sol, "getInventory") end
    if inv ~= nil then
        local h = call(inv, "haveThisKeyId", kid)
        if h ~= nil and h ~= false then return locked, true end
    end
    local n = num((call(v, "getPartCount"))) or 0
    for i = 0, n - 1 do
        local c = call((call(v, "getPartByIndex", i)), "getItemContainer")
        if c ~= nil then
            local h = call(c, "haveThisKeyId", kid)
            if h ~= nil and h ~= false then return locked, true end
        end
    end
    if inv == nil then return locked, nil end
    return locked, false
end
-- s77 end
"""

SWS = [
    ("""-- ---------------------------------------------------------------- scan
local function scanJob()
""", CAR_USE + """-- ---------------------------------------------------------------- scan
local function scanJob()
"""),
    ("""            snap.vehicles[#snap.vehicles + 1] = info
""", """            info.locked, info.key = carUse(v, sol)                                    -- s77 cars_near
            snap.vehicles[#snap.vehicles + 1] = info
"""),
]


def client(cl):
    for o, n in SWS: edit(os.path.join(cl, "SolWorldScan.lua"), o, n)


if __name__ == "__main__":
    client(sys.argv[1])
    print("s77_lua applied")
