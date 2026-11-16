"""s101 edge_api: SolPlace's live edge read asks B42 for the door / window on an edge with the right calls.
Live 2026-11-11 12:33:47 ([SolKahluaGuard], 10 lines): SolPlace.liveStruct (SolPlace.lua 107-113) called square:getDoor(north),
getWindow(north), getThumpableWindow(north), getWindowFrame(north) with a Boolean. B42 has no Boolean overload (javap: getDoor(
GridSquareEdgeFacingDirection | GridSquareEdge [, GetSquare]) ...), so Kahlua's MultiLuaJavaInvoker threw "No implementation found"
and released one pooled MethodArguments twice: each such call poisons the Kahlua pool once (the game-wide callFrame NPEs, the sort
storm at 10:35, the 12:34:18 NPE). Fix: the edge-to-square calls B42 does have (getDoorTo / getWindowTo / getWindowThumpableTo /
getWindowFrameTo(other square)), both ways. Switch edge_api (off = the old calls). Game closed only. usage: apply_s101_edge_api.py <client>"""
import os, sys
CL = sys.argv[1]; NL, CRLF = chr(10), chr(13) + chr(10)
def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old))
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new)); print("edited " + os.path.basename(path))
P = os.path.join(CL, "SolPlace.lua")
edit(P, '''        return "door", call(owner, "getDoor", north) or call(other, "getDoor", north)
    end''', '''        if eaOn() then return "door", call(owner, "getDoorTo", other) or call(other, "getDoorTo", owner) end   -- s101 edge_api
        return "door", call(owner, "getDoor", north) or call(other, "getDoor", north)
    end''')
edit(P, '''        local w = call(owner, "getWindow", north) or call(owner, "getThumpableWindow", north)
        if w ~= nil then return "window", w end
        local fr = call(owner, "getWindowFrame", north)''', '''        local w, fr
        if eaOn() then   -- s101 edge_api: the B42 edge-to-square calls (no Boolean overloads exist)
            w = call(owner, "getWindowTo", other) or call(other, "getWindowTo", owner)
                or call(owner, "getWindowThumpableTo", other) or call(other, "getWindowThumpableTo", owner)
            if w ~= nil then return "window", w end
            fr = call(owner, "getWindowFrameTo", other) or call(other, "getWindowFrameTo", owner)
            if fr ~= nil then return "frame", fr end
            return "wall", nil
        end
        w = call(owner, "getWindow", north) or call(owner, "getThumpableWindow", north)
        if w ~= nil then return "window", w end
        fr = call(owner, "getWindowFrame", north)''')
edit(P, "local function liveStruct(x, y, z, dir)", '''local function eaOn() local A = rawget(_G, "SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("edge_api") == true end   -- s101
local function liveStruct(x, y, z, dir)''')

import shutil
shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "SolEdgeApi.lua"), os.path.join(CL, "SolEdgeApi.lua"))
N = os.path.join(CL, "SCNavigation.lua")
for old in ("getDoor", "getWindow", "getThumpableWindow", "getWindowFrame"):
    pass
edit(N, 'local door, doorOk = utility.call(owner, "getDoor", north)', 'local door, doorOk = SolEdgeApi.call(utility.call, fromSquare, toSquare, owner, "getDoor", north)   -- s101')
edit(N, 'local window, windowOk = utility.call(owner, "getWindow", north)', 'local window, windowOk = SolEdgeApi.call(utility.call, fromSquare, toSquare, owner, "getWindow", north)   -- s101')
edit(N, 'window, windowOk = utility.call(owner, "getThumpableWindow", north)', 'window, windowOk = SolEdgeApi.call(utility.call, fromSquare, toSquare, owner, "getThumpableWindow", north)   -- s101')
edit(N, 'local frame, frameOk = utility.call(owner, "getWindowFrame", north)', 'local frame, frameOk = SolEdgeApi.call(utility.call, fromSquare, toSquare, owner, "getWindowFrame", north)   -- s101')
T = os.path.join(CL, "SCTopology.lua")
UC = 'function(o, n, a) return U().call(o, n, a) end'
edit(T, 'door, doorOk = U().call(owner, "getDoor", north)', 'door, doorOk = SolEdgeApi.call(' + UC + ', fromSquare, toSquare, owner, "getDoor", north)   -- s101')
edit(T, 'window, windowOk = U().call(owner, "getWindow", north)', 'window, windowOk = SolEdgeApi.call(' + UC + ', fromSquare, toSquare, owner, "getWindow", north)   -- s101')
edit(T, 'window, windowOk = U().call(owner, "getThumpableWindow", north)', 'window, windowOk = SolEdgeApi.call(' + UC + ', fromSquare, toSquare, owner, "getThumpableWindow", north)   -- s101')
edit(T, 'frame, frameOk = U().call(owner, "getWindowFrame", north)', 'frame, frameOk = SolEdgeApi.call(' + UC + ', fromSquare, toSquare, owner, "getWindowFrame", north)   -- s101')
A = os.path.join(CL, "SolAuthority.lua")
if '"edge_api"' not in open(A, encoding="utf-8").read(): edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "edge_api",' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "edge_api" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("edge_api=on" + CRLF)
print("s101 edge_api applied")
