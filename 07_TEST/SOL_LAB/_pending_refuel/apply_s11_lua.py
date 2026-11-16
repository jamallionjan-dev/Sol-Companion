"""Run only after the game is closed. "Get in" takes the front passenger seat if free, else the first free seat behind; the wheel is only for an order to drive. usage: apply_s11_lua.py <SolOrders.lua>"""
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
a = """        freshFlow()
        log("board target=" .. (targetVehicle and "selected" or "nearest") .. " radius=30")
        job = { kind = "ride", veh = veh, seat = 1, since = nowMs(), deadline = nowMs() + 90000, tries = 0 }
""".replace("\n", nl)
b = """        local function taken(i) local ok, v = pcall(function() return veh:isSeatOccupied(i) end); return ok and v == true end
        local wanted = nil
        local okN, n = pcall(function() return veh:getMaxPassengers() end)
        for i = 1, ((okN and tonumber(n)) or 2) - 1 do          -- seat 0 is the wheel: that takes an order to drive, never "get in"
            if not taken(i) then wanted = i; break end
        end
        if wanted == nil then return say(AR.no_seat) end
        freshFlow()
        log("board target=" .. (targetVehicle and "selected" or "nearest") .. " radius=30 seat=" .. tostring(wanted))
        job = { kind = "ride", veh = veh, seat = wanted, since = nowMs(), deadline = nowMs() + 90000, tries = 0 }
""".replace("\n", nl)
assert t.count(a) == 1, t.count(a)
open(p, "w", encoding="utf-8", newline="").write(t.replace(a, b))
print("applied to", p)
