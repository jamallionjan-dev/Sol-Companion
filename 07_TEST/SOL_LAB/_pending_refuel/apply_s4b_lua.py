"""Run only after the game is closed. Cancelling a GPS destination. usage: apply_s4b_lua.py <lua client dir>"""
import os, sys
d = sys.argv[1]
def edit(name, pairs):
    p = os.path.join(d, name)
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b in pairs:
        a, b = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a) == 1, (name, a[:70], t.count(a))
        t = t.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(t)

edit("SolGPS.lua", [
('''-- ---------------------------------------------------------------- driving
local function sol() return U.solActor and U.solActor() or nil end
''', '''-- Takes the destination off the screen. option "errand": only a target an errand set for itself, never one the player chose.
function U.gpsClear(option)
    if not G.dest then return true, "already_clear" end
    if option == "errand" then
        local name = tostring(G.dest.name or "")
        if string.sub(name, 1, 11) ~= "Gas station" and name ~= "back to the player" then return true, "not_an_errand_target" end
    end
    local st = U.gpsStatus and U.gpsStatus() or {}
    if option ~= "errand" and (st.phase == "following" or st.phase == "planning" or st.phase == "replanning" or st.phase == "blocked" or st.phase == "streaming_wait") then U.gpsStop() end
    G.dest = nil
    if G.preview then G.preview.at, G.preview.route, G.preview.reason, G.preview.snap, G.preview.key = nil, nil, nil, nil, nil end
    if G.lastResult ~= "failed" or option ~= "errand" then G.lastResult, G.reason = nil, nil end
    return true, "destination_cleared"
end
-- A click on the map: the same spot again takes it off, anywhere else sets it.
function U.gpsMapClick(wx, wy, driving)
    local d = G.dest
    if d and not driving and math.abs(d.x - wx) <= 2 and math.abs(d.y - wy) <= 2 then
        U.gpsClear()
        return "cleared"
    end
    return "set"
end

-- ---------------------------------------------------------------- driving
local function sol() return U.solActor and U.solActor() or nil end
'''),
('''    if wx and wy then
        U.gpsSetDestination({ x = math.floor(wx), y = math.floor(wy), name = ar(''', '''    local stClick = wx and wy and U.gpsStatus() or {}
    local clickDriving = stClick.phase == "following" or stClick.phase == "planning" or stClick.phase == "replanning" or stClick.phase == "blocked" or stClick.phase == "streaming_wait"
    if wx and wy and U.gpsMapClick(wx, wy, clickDriving) == "cleared" then return true end
    if wx and wy then
        U.gpsSetDestination({ x = math.floor(wx), y = math.floor(wy), name = ar('''),
('''    self.hits[#self.hits + 1] = { r = { 34, 8, 26, 20 }, action = "collapse" }
''', '''    self.hits[#self.hits + 1] = { r = { 34, 8, 26, 20 }, action = "collapse" }
    if dest then
        self:drawRect(66, 8, 60, 20, 0.9, 0.45, 0.14, 0.12); self:drawRectBorder(66, 8, 60, 20, 0.9, 0.95, 0.6, 0.55)
        txt(self, ar("\\\\u0625\\\\u0644\\\\u063A\\\\u0627\\\\u0621", "Clear"), 66, 8, 60, 0.46, "center")
        self.hits[#self.hits + 1] = { r = { 66, 8, 60, 20 }, action = "clear" }
    end
'''),
('''            elseif h.action == "stop" then U.gpsStop()
            elseif h.action == "collapse" then''', '''            elseif h.action == "stop" then U.gpsStop()
            elseif h.action == "clear" then U.gpsClear()
            elseif h.action == "collapse" then'''),
])
edit("SolActions.lua", [
('''    if id == "sol_horn" then return U.solHorn(option) end
''', '''    if id == "sol_horn" then return U.solHorn(option) end
    if id == "sol_gps_clear" and type(U.gpsClear) == "function" then return U.gpsClear(option) end
'''),
('''    out[#out + 1] = { id = "sol_fuel", kind = "sol",''', '''    out[#out + 1] = { id = "sol_gps_clear", kind = "sol", label = "take the destination off Sol's GPS" }
    out[#out + 1] = { id = "sol_fuel", kind = "sol",'''),
])
print("installed into", d)
