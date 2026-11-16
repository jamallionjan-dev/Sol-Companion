"""Run only after the game is closed. Street memory, what dying costs, the first-spawn katana, her map marker. usage: apply_s6_lua.py <lua client dir>"""
import os, shutil, sys
d = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
shutil.copyfile(os.path.join(here, "SolLife.lua"), os.path.join(d, "SolLife.lua"))
def edit(name, pairs):
    p = os.path.join(d, name)
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b in pairs:
        a, b = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a) == 1, (name, a[:60], t.count(a))
        t = t.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(t)
edit("SolFixLook.lua", [('''function M.onSolSpawned()
    local SC = SurvivorCompanion
''', '''function M.onSolSpawned()
    if type(rawget(_G, "SolLife")) == "table" and type(SolLife.onSpawned) == "function" then pcall(SolLife.onSpawned) end
    local SC = SurvivorCompanion
''')])
edit("SolDress.lua", [
('''    { "Base.BaseballBat_Metal", "primary" },
''', '''    { "Base.Katana", "primary" },
'''),
('''first Sol spawn received desert military kit and metal baseball bat''', '''first Sol spawn received desert military kit and a katana'''),
])
edit("SolWorldScan.lua", [('''    if type(SolHome) == "table" and type(SolHome.get) == "function" then snap.solHome = SolHome.get() end''', '''    if type(SolLife) == "table" and type(SolLife.snapshot) == "function" then
        local okL, life, streets, current = pcall(SolLife.snapshot)
        if okL then snap.solLife, snap.knownStreets, snap.currentStreet = life, streets, current end
    end
    if type(SolHome) == "table" and type(SolHome.get) == "function" then snap.solHome = SolHome.get() end''')])
edit("SolGPS.lua", [
('''    -- Sol v2: the vehicle's arrow only while someone sits in a vehicle (it points''', '''    if U.solMapDraw then pcall(U.solMapDraw, self, self.mapAPI) end
    -- Sol v2: the vehicle's arrow only while someone sits in a vehicle (it points'''),
('''    local orig = ISWorldMap.onRightMouseUp
''', '''    if type(ISWorldMap.render) == "function" then
        local origRender = ISWorldMap.render
        ISWorldMap.render = function(self, ...)
            local r = origRender(self, ...)
            if U.solMapDraw and self.mapAPI then pcall(U.solMapDraw, self, self.mapAPI) end
            return r
        end
    end
    local orig = ISWorldMap.onRightMouseUp
'''),
])
print("installed into", d)
