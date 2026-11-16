"""NOT run while the game is open. Installs SolFuel and its two hooks into a Lua client folder.  usage: apply_lua.py <client dir>"""
import os, shutil, sys
d = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
shutil.copyfile(os.path.join(here, "SolFuel.lua"), os.path.join(d, "SolFuel.lua"))
def patch(name, a, b):
    p = os.path.join(d, name)
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    a, b = a.replace("\n", nl), b.replace("\n", nl)
    assert t.count(a) == 1, (name, a[:60], t.count(a))
    open(p, "w", encoding="utf-8", newline="").write(t.replace(a, b))
patch("SolActions.lua", '    if id == "sol_horn" then return U.solHorn(option) end\n', '    if id == "sol_horn" then return U.solHorn(option) end\n    if id == "sol_fuel" and type(U.solFuel) == "function" then return U.solFuel(option) end\n')
patch("SolActions.lua", '    out[#out + 1] = { id = "sol_read", kind = "sol",', '    out[#out + 1] = { id = "sol_fuel", kind = "sol", label = "fuel pumps; used by the refuel goals, not called alone" }\n    out[#out + 1] = { id = "sol_read", kind = "sol",')
patch("SolAuthority.lua", '    "solo_drive",  ', '    "refuel",             -- she remembers fuel pumps and fills a car or a can when told\n    "solo_drive",  ')
print("installed into", d)
