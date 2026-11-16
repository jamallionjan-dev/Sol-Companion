"""Run only after the game is closed. While the refuel errand needs her on foot, the follow logic may not seat her in the player's car. usage: apply_s9_lua.py <SolAuthority.lua>"""
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
a = """    if type(SolOrders) == "table" and type(SolOrders.busy) == "function" then
        local ok, b = pcall(SolOrders.busy)
""".replace("\n", nl)
b = """    if type(SolUI) == "table" and type(SolUI.solFuelHeld) == "function" then
        local ok, held = pcall(SolUI.solFuelHeld)
        if ok and held == true then return true, "sol_fuel_errand" end
    end
""".replace("\n", nl) + a
assert t.count(a) == 1, t.count(a)
open(p, "w", encoding="utf-8", newline="").write(t.replace(a, b))
print("applied to", p)
