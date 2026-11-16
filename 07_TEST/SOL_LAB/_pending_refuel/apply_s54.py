"""A new drive order replaces the trip she is on; "home" means the home's parking spot, not the middle of the house.
Game closed only. usage: apply_s54.py <client dir> <sol_mind dir>"""
import os, sys
CL, MIND = sys.argv[1], sys.argv[2]
NL, CRLF = chr(10), chr(13) + chr(10)
EDITS = {}
def E(p, a, b): EDITS.setdefault(p, []).append((a, b))

E(os.path.join(CL, "SolGPS.lua"), """        if okJ and type(js) == "table" and (js.result == "arrived" or js.result == "failed") then pcall(D.stop, s, "new_destination") end
""", """        local solA = rawget(_G, "SolAuthority")
        local replace = type(solA) == "table" and type(solA.on) == "function" and solA.on("drive_replace") == true      -- a new order replaces the trip she is on
        if okJ and type(js) == "table" and (js.result == "arrived" or js.result == "failed" or replace) then pcall(D.stop, s, "new_destination") end
""")
E(os.path.join(CL, "SolWorldScan.lua"), """                snap.solParking = { x = math.floor((z.x1 + z.x2) / 2), y = math.floor((z.y1 + z.y2) / 2) }
                break
""", """                local spot = { x = math.floor((z.x1 + z.x2) / 2), y = math.floor((z.y1 + z.y2) / 2), x1 = math.min(z.x1, z.x2), x2 = math.max(z.x1, z.x2), y1 = math.min(z.y1, z.y2), y2 = math.max(z.y1, z.y2) }
                snap.solParking = snap.solParking or { x = spot.x, y = spot.y }
                snap.solParkings = snap.solParkings or {}
                snap.solParkings[#snap.solParkings + 1] = spot
""")
A = os.path.join(CL, "SolAuthority.lua")
E(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "drive_replace", "home_parks",' + NL)

CS = os.path.join(MIND, "chat_service.py")
E(CS, """        if not h: return {"error": "home_not_set"}
        rid = gps_request(lua_dir, {"action": "drive", "x": h["x"], "y": h["y"], "name": h.get("name") or "home", "speed": speed})
        return _drive_outcome(lua_dir, rid, {"sent": "home", "x": h["x"], "y": h["y"]})
""", """        if not h: return {"error": "home_not_set"}
        spot = home_parking(snap, h) if fix_on(lua_dir, "home_parks") else None
        if spot:                                                                   # home is where the car stands at home: the marked parking, not the house itself
            rid = gps_request(lua_dir, {"action": "drive", "x": spot["x"], "y": spot["y"], "name": "الكراج", "speed": speed})
            return _drive_outcome(lua_dir, rid, {"sent": "home parking", "x": spot["x"], "y": spot["y"]})
        if fix_on(lua_dir, "home_parks"):                                          # no parking marked: the road beside the house, never into it
            rid = gps_request(lua_dir, {"action": "drive", "x": h["x"], "y": h["y"], "near": "1", "name": "جنب البيت", "speed": speed})
            return _drive_outcome(lua_dir, rid, {"sent": "near home", "x": h["x"], "y": h["y"], "say": "ما في مكان صف محدد، رح وقّف عالطريق جنب البيت."})
        rid = gps_request(lua_dir, {"action": "drive", "x": h["x"], "y": h["y"], "name": h.get("name") or "home", "speed": speed})
        return _drive_outcome(lua_dir, rid, {"sent": "home", "x": h["x"], "y": h["y"]})
""")
E(CS, """    if r.get("result") == "arrived" and reason == "arrived": return "وصلنا."
    return "تمام، انطلقت."
""", """    if r.get("result") == "arrived" and reason == "arrived": return "وصلنا."
    if r.get("say"): return r["say"]
    return "تمام، انطلقت."
""")
E(os.path.join(CL, "SolGPS.lua"), """        elseif r.x and r.y then U.gpsSetDestination({ x = tonumber(r.x), y = tonumber(r.y), name = r.name }) end
""", """        elseif r.x and r.y and r.near == "1" and U.gpsNearestRoad then                                         -- beside the place, on the road: for a home with no parking marked
            local sx, sy = U.gpsNearestRoad(tonumber(r.x), tonumber(r.y))
            if sx then U.gpsSetDestination({ x = sx, y = sy, name = r.name }); log("near " .. tostring(r.x) .. "," .. tostring(r.y) .. ": the road at " .. sx .. "," .. sy)
            else U.gpsSetDestination({ x = tonumber(r.x), y = tonumber(r.y), name = r.name }) end
        elseif r.x and r.y then U.gpsSetDestination({ x = tonumber(r.x), y = tonumber(r.y), name = r.name }) end
""")
E(CS, """def drive_to(lua_dir, args, mem, snap=None):
""", """def fix_on(lua_dir, name):
    try:
        with open(os.path.join(lua_dir, "SolFixes_LAB.txt"), encoding="utf-8", errors="replace") as f:
            return any(line.strip().replace(" ", "") == name + "=on" for line in f)
    except OSError:
        return False

def home_parking(snap, home, reach=60):
    \"\"\"The parking spot he marked for this home: a free one first, the nearest to the house among those. None when there is none near the home.\"\"\"
    s = snap or {}
    spots = [p for p in (s.get("solParkings") or ([s["solParking"]] if isinstance(s.get("solParking"), dict) else [])) if isinstance(p, dict) and p.get("x") is not None]
    spots = [p for p in spots if (p["x"] - home["x"]) ** 2 + (p["y"] - home["y"]) ** 2 <= reach * reach]
    if not spots: return None
    cars = [v for v in s.get("vehicles") or [] if isinstance(v, dict) and v.get("x") is not None]
    me = s.get("sol") or {}
    def taken(p):
        x1, x2, y1, y2 = p.get("x1", p["x"] - 1), p.get("x2", p["x"] + 1), p.get("y1", p["y"] - 1), p.get("y2", p["y"] + 1)
        for v in cars:
            if me.get("x") is not None and abs(v["x"] - me["x"]) < 1.5 and abs(v["y"] - me["y"]) < 1.5: continue     # her own car
            if x1 <= v["x"] <= x2 + 1 and y1 <= v["y"] <= y2 + 1: return True
        return False
    spots.sort(key=lambda p: (taken(p), (p["x"] - home["x"]) ** 2 + (p["y"] - home["y"]) ** 2))
    return spots[0]

def drive_to(lua_dir, args, mem, snap=None):
""")

out = {}
for p, ps in EDITS.items():
    t = open(p, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    for a, b in ps:
        a2, b2 = a.replace(NL, nl), b.replace(NL, nl)
        assert t.count(a2) == 1, (p[-22:], a[:60], t.count(a2))
        t = t.replace(a2, b2)
    if p.endswith(".py"): compile(t, p, "exec")
    out[p] = t
for p, t in out.items():
    open(p, "w", encoding="utf-8", newline="").write(t)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix):
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("drive_replace=on" + CRLF + "home_parks=on" + CRLF)
print("applied")
