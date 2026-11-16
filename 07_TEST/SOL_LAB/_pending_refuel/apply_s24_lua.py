"""Run only after the game is closed. The snapshot Sol Mind reads carries the farm, and a death wipes what she planted with the rest.
usage: apply_s24_lua.py <SolWorldScan.lua> <SolLife.lua>"""
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
("""    if type(SolHome) == "table" and type(SolHome.get) == "function" then snap.solHome = SolHome.get() end   -- Sol Mind adopts it when its memory has no home
""", """    if type(SolHome) == "table" and type(SolHome.get) == "function" then snap.solHome = SolHome.get() end   -- Sol Mind adopts it when its memory has no home
    if type(SolFarmWork) == "table" and type(SolFarmWork.snapshot) == "function" then
        local okF, farm = pcall(SolFarmWork.snapshot)
        if okF then snap.solFarm = farm end
    end
"""),
])
patch(sys.argv[2], [
("""    local forget = rawget(_G, "solStationsForget")
    if type(forget) == "function" then pcall(forget) end
""", """    local forget = rawget(_G, "solStationsForget")
    if type(forget) == "function" then pcall(forget) end
    local forgetFarm = rawget(_G, "solFarmForget")
    if type(forgetFarm) == "function" then pcall(forgetFarm) end
"""),
])
