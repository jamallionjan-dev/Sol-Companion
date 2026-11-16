"""road_first: stay on the road. Game closed only. All or nothing.
usage: apply_s48.py <client dir> <sol_nav_java dir> <sol_mind dir>"""
import os, shutil, sys
CLIENT, JAVA, MIND = sys.argv[1], sys.argv[2], sys.argv[3]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
EDITS = {}
def E(p, a, b): EDITS.setdefault(p, []).append((a, b))
C = lambda n: os.path.join(CLIENT, n)

E(C("SolAuthority.lua"), "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "road_first",' + NL)

E(C("SCExpeditionRoute.lua"), """    -- Sol fix (gps_trails): the same planner with dirt roads in its map; the paved map remains the fallback.
""", """    local solA = rawget(_G, "SolAuthority")
    if not pavedOnly and type(solA) == "table" and type(solA.on) == "function" and solA.on("road_first") == true then
        local paved, why, detail = plan(actor, target, continuingMission, avoidance, circlesText, circles, origin, true)
        local RF = rawget(_G, "SolRoadFirst")
        if paved and (type(RF) ~= "table" or RF.reaches(paved.points, target)) then return paved, why, detail end
    end
    -- Sol fix (gps_trails): the same planner with dirt roads in its map; the paved map remains the fallback.
""")

E(C("SolBypass.lua"), """        if k == "solid" then return true end
        if k == "post" and (fx - 0.5) ^ 2 + (fy - 0.5) ^ 2 <= 0.1225 then return true end
        for i = 1, #cars do
            if (cars[i].v == nil or cars[i].v ~= B.measured) and carCovers(cars[i], px, py) then return true end
        end
        return false
""", """        if k == "solid" then return "solid" end
        if k == "post" and (fx - 0.5) ^ 2 + (fy - 0.5) ^ 2 <= 0.1225 then return "post" end
        for i = 1, #cars do
            if (cars[i].v == nil or cars[i].v ~= B.measured) and carCovers(cars[i], px, py) then
                local speed = on("road_first") and math.abs(tonumber(method(cars[i].v, "getCurrentSpeedKmHour")) or 0) or 0
                if speed <= 2 then return "car" end
            end
        end
        return false
""")
E(C("SolBypass.lua"), """                        if hit(cx0 - uy * across, cy0 + ux * across) then return dist, cx0, cy0 end
""", """                        local what = hit(cx0 - uy * across, cy0 + ux * across)
                        if what then return dist, cx0, cy0, what end
""")

E(C("SCDriving.lua"), """    local followed, reason = call("driveFollow", actor, text, tonumber(kmh) or 10)
""", """    local followed, reason = call("driveFollow", actor, text, tonumber(kmh) or 10)
    if not followed then
        local RF = rawget(_G, "SolRoadFirst")
        if type(RF) == "table" then print("[SolDrive] route given: " .. RF.routeDetail(points)) end
    end
""")
E(C("SCDriving.lua"), """    local okS, dist, ox, oy = pcall(planner.scanAhead, job.route.points, x, y, math.min(40, math.max(25, 25 + speed * 0.5)), size.halfLength, size.halfWidth)
    if not okS or not dist or dist > LOOK_MAX_TILES then return end
""", """    local okS, dist, ox, oy, what = pcall(planner.scanAhead, job.route.points, x, y, math.min(40, math.max(25, 25 + speed * 0.5)), size.halfLength, size.halfWidth)
    if not okS or not dist or dist > LOOK_MAX_TILES then return end
    local RF = rawget(_G, "SolRoadFirst")
    if type(RF) == "table" and RF.on() and not RF.seen(job, ox, oy, current) then return end
""")
E(C("SCDriving.lua"), """    ladderLog(job, string.format("seen ahead %.0f tiles on, at %.0f,%.0f", dist, ox, oy))
""", """    ladderLog(job, string.format("seen ahead %.0f tiles on, at %.0f,%.0f what=%s", dist, ox, oy, tostring(what)))
""")
E(C("SCDriving.lua"), """    if job.attempts == nil or job.circles == nil or job.attempts >= 3 or #job.circles >= 8 then return false end
""", """    if job.attempts == nil or job.circles == nil or job.attempts >= 3 or #job.circles >= 8 then return false end
    local RF = rawget(_G, "SolRoadFirst")
    if type(RF) == "table" and not RF.mayReroute(job, status, job.vehicle) then return false end
""")
E(C("SCDriving.lua"), """    for _, b in ipairs(job.jnavBans or {}) do pcall(add, b.x, b.y) end
end
""", """    for _, b in ipairs(job.jnavBans or {}) do pcall(add, b.x, b.y) end
    local RF = rawget(_G, "SolRoadFirst")
    if type(RF) == "table" then
        local _, x = method(job.vehicle, "getX")
        local _, y = method(job.vehicle, "getY")
        RF.sendCorridor(job, finite(x), finite(y))
    end
end
""")

N = os.path.join(JAVA, "localplayerbody", "SolNav.java")
E(N, """    private static final List<double[]> BANS = new ArrayList<>();
""", """    private static final List<double[]> BANS = new ArrayList<>();
    private static final List<double[]> CORRIDOR = new ArrayList<>();
    private static double corridorRadius;
    private static final double CORRIDOR_KEEP = 6;
""")
E(N, """        final List<double[]> bans = new ArrayList<>();
    }
""", """        final List<double[]> bans = new ArrayList<>();
        final List<double[]> corridor = new ArrayList<>(); double corridorRadius;
    }
""")
E(N, """        c.bans.addAll(BANS);
        c.mayTurnBack = turnBackNext; turnBackNext = false;
        capture = c; state = "capturing"; ready = null;
        return true;
    }

    /** One stage of the drive beyond the road""", """        c.bans.addAll(BANS);
        c.corridor.addAll(CORRIDOR); c.corridorRadius = corridorRadius;
        c.mayTurnBack = turnBackNext; turnBackNext = false;
        capture = c; state = "capturing"; ready = null;
        return true;
    }

    /** One stage of the drive beyond the road""")
E(N, """    private static final float SOFT_OFF_ROAD = 0.25f;
""", """    private static final float SOFT_OFF_ROAD = 0.25f, SOFT_OFF_ROAD_NEAR_ROAD = 1.0f;
""")
E(N, """            for (int j = 0; j < 10; j++) java.util.Arrays.fill(soft, (ty * 10 + j) * n + tx * 10, (ty * 10 + j) * n + tx * 10 + 10, SOFT_OFF_ROAD);
""", """            float cost = c.corridor.isEmpty() ? SOFT_OFF_ROAD : SOFT_OFF_ROAD_NEAR_ROAD;                    // going round something on the road: keep to the paving and shoulder while there is room
            for (int j = 0; j < 10; j++) java.util.Arrays.fill(soft, (ty * 10 + j) * n + tx * 10, (ty * 10 + j) * n + tx * 10 + 10, cost);
""")
E(N, """    @LuaMethod(name = "solNavBanClear", global = true)
""", """    @LuaMethod(name = "solNavCorridorClear", global = true)
    public static void corridorClear() { CORRIDOR.clear(); }

    @LuaMethod(name = "solNavCorridorPoint", global = true)
    public static void corridorPoint(double x, double y) { CORRIDOR.add(new double[] { x, y }); }

    @LuaMethod(name = "solNavCorridorRadius", global = true)
    public static void corridorRadius(double r) { corridorRadius = r; }

    @LuaMethod(name = "solNavBanClear", global = true)
""")
E(N, """        for (double[] b : c.bans) SolNavPlanner.ban(occ, n, n, c.originX, c.originY, b[0], b[1], BAN_RADIUS);
        return occ;
    }
""", """        for (double[] b : c.bans) SolNavPlanner.ban(occ, n, n, c.originX, c.originY, b[0], b[1], BAN_RADIUS);
        if (!c.leg && !c.park && !c.corridor.isEmpty()) applyCorridor(occ, c.size, c.originX, c.originY, c.corridor, c.corridorRadius, c.sx, c.sy, c.gx, c.gy);
        return occ;
    }

    /** A way round may only use ground near the road. The car's own start and goal stay open, so she can always leave and rejoin. */
    static void applyCorridor(boolean[] occ, int size, int ox, int oy, List<double[]> pts, double radius, double sx, double sy, double gx, double gy) {
        int n = size * 10;
        double r2 = radius * radius, keep2 = CORRIDOR_KEEP * CORRIDOR_KEEP;
        for (int ty = 0; ty < size; ty++) for (int tx = 0; tx < size; tx++) {
            double cx = ox + tx + 0.5, cy = oy + ty + 0.5;
            if ((cx - sx) * (cx - sx) + (cy - sy) * (cy - sy) <= keep2 || (cx - gx) * (cx - gx) + (cy - gy) * (cy - gy) <= keep2) continue;
            boolean near = false;
            for (int i = 0; i < pts.size() && !near; i++) {
                double[] a = pts.get(i), b = pts.get(Math.min(i + 1, pts.size() - 1));
                double dx = b[0] - a[0], dy = b[1] - a[1], len2 = dx * dx + dy * dy;
                double u = len2 > 0 ? Math.max(0, Math.min(1, ((cx - a[0]) * dx + (cy - a[1]) * dy) / len2)) : 0;
                double px = a[0] + dx * u - cx, py = a[1] + dy * u - cy;
                near = px * px + py * py <= r2;
            }
            if (near) continue;
            for (int j = 0; j < 10; j++) java.util.Arrays.fill(occ, (ty * 10 + j) * n + tx * 10, (ty * 10 + j) * n + tx * 10 + 10, true);
        }
    }
""")

CS = os.path.join(MIND, "chat_service.py")
E(CS, """    "no_usable_car": "السيارات القريبة كلها مقفلة وما معنا مفتاحها",
""", """    "no_usable_car": "السيارات القريبة كلها مقفلة وما معنا مفتاحها",
    "no_way_round": "الطريق مسكر قدامي وما في لف حواليه، وقفت",
""")

out = {}
for p, ps in EDITS.items():
    t = open(p, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    for a, b in ps:
        a2, b2 = a.replace(NL, nl), b.replace(NL, nl)
        assert t.count(a2) == 1, (p[-26:], a[:70], t.count(a2))
        t = t.replace(a2, b2)
    if p.endswith(".py"): compile(t, p, "exec")
    out[p] = t
bk = os.path.join(HERE, "..", "_backup", "20261109_before_road_first")
os.makedirs(bk, exist_ok=True)
for p in out:
    if p.endswith(".lua"): shutil.copy2(p, bk)
for p, t in out.items():
    open(p, "w", encoding="utf-8", newline="").write(t)
shutil.copy(os.path.join(HERE, "SolRoadFirst.lua"), C("SolRoadFirst.lua"))
fix = os.path.join(CLIENT, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
t = open(fix, encoding="utf-8", newline="").read()
assert "road_first=" not in t
t = t.replace("gps_trails=off", "gps_trails=on")
t += "road_first=on" + CRLF
open(fix, "w", encoding="utf-8", newline="").write(t)
print("applied")
