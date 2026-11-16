"""GPS panel: say and show it when a route stops short of the marker, and log where it ends. Game closed only. usage: apply_s53.py <client dir>"""
import os, sys
P = os.path.join(sys.argv[1], "SolGPS.lua")
NL, CRLF = chr(10), chr(13) + chr(10)
E = [
("""    if ok and type(route) == "table" and type(route.points) == "table" and #route.points >= 2 then P.route, P.reason = route, nil
""", """    if ok and type(route) == "table" and type(route.points) == "table" and #route.points >= 2 then
        local last = route.points[#route.points]
        local gap = math.sqrt((last.x - G.dest.x) ^ 2 + (last.y - G.dest.y) ^ 2)
        if P.lastEnd ~= key then P.lastEnd = key; log(string.format("preview %s: from %.0f,%.0f, %d points, ends %.0f,%.0f, %.0f tiles short of the marker", key, o.x, o.y, #route.points, last.x, last.y, gap)) end
    end
    if ok and type(route) == "table" and type(route.points) == "table" and #route.points >= 2 then P.route, P.reason = route, nil
"""),
("""    elseif dest and not pts and o then local ax, ay = self:toUI(o.x, o.y); local bx, by = self:toUI(dest.x, dest.y); self:line(ax, ay, bx, by, 8, 3, YELLOW, 0.8) end
""", """    elseif dest and not pts and o then local ax, ay = self:toUI(o.x, o.y); local bx, by = self:toUI(dest.x, dest.y); self:line(ax, ay, bx, by, 8, 3, YELLOW, 0.8)
    elseif dest and pts and (pts[#pts].x - dest.x) ^ 2 + (pts[#pts].y - dest.y) ^ 2 > 225 then local ax, ay = self:toUI(pts[#pts].x, pts[#pts].y); local bx, by = self:toUI(dest.x, dest.y); self:line(ax, ay, bx, by, 8, 3, YELLOW, 0.9) end
"""),
("""    elseif not driving and dest and pts then
        state, sc = ar("\\\\u0627\\\\u0644\\\\u0637\\\\u0631\\\\u064A\\\\u0642 \\\\u062C\\\\u0627\\\\u0647\\\\u0632\\\\u060C \\\\u0627\\\\u0636\\\\u063A\\\\u0637 \\\\u0642\\\\u0648\\\\u062F\\\\u064A", "Route ready - press Drive"), BLUE
""", """    elseif not driving and dest and pts and (pts[#pts].x - dest.x) ^ 2 + (pts[#pts].y - dest.y) ^ 2 > 225 then
        state, sc = ar("\\\\u0627\\\\u0644\\\\u0637\\\\u0631\\\\u064A\\\\u0642 \\\\u0628\\\\u064A\\\\u0648\\\\u0642\\\\u0641 \\\\u0642\\\\u0628\\\\u0644 \\\\u0627\\\\u0644\\\\u0639\\\\u0644\\\\u0627\\\\u0645\\\\u0629", "The road stops short of the marker"), YELLOW
    elseif not driving and dest and pts then
        state, sc = ar("\\\\u0627\\\\u0644\\\\u0637\\\\u0631\\\\u064A\\\\u0642 \\\\u062C\\\\u0627\\\\u0647\\\\u0632\\\\u060C \\\\u0627\\\\u0636\\\\u063A\\\\u0637 \\\\u0642\\\\u0648\\\\u062F\\\\u064A", "Route ready - press Drive"), BLUE
"""),
]
t = open(P, encoding="utf-8", newline="").read()
nl = CRLF if CRLF in t else NL
for a, b in E:
    a2, b2 = a.replace(NL, nl), b.replace(NL, nl)
    assert t.count(a2) == 1, a[:70]
    t = t.replace(a2, b2)
open(P, "w", encoding="utf-8", newline="").write(t)
print("applied")
