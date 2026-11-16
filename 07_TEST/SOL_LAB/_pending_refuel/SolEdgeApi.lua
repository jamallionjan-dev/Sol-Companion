-- SolEdgeApi.lua - switch edge_api (s101, 2026-11-11). B42 has no getDoor/getWindow/getThumpableWindow/getWindowFrame(Boolean):
-- calling them with a Boolean makes Kahlua's MultiLuaJavaInvoker throw "No implementation found" and release one pooled
-- MethodArguments twice, which poisons the Kahlua pool (the game-wide callFrame NPEs). The B42 calls take the other square:
-- getDoorTo / getWindowTo / getWindowThumpableTo / getWindowFrameTo(IsoGridSquare). Used by SolPlace, SCNavigation, SCTopology.
SolEdgeApi = SolEdgeApi or {}
local E = SolEdgeApi
E.TO = { getDoor = "getDoorTo", getWindow = "getWindowTo", getThumpableWindow = "getWindowThumpableTo", getWindowFrame = "getWindowFrameTo" }
function E.on() local A = rawget(_G, "SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("edge_api") == true end
-- callf(obj, name, arg) -> value, ok (LF's utility.call / U().call). Returns value, ok like the old call did.
function E.call(callf, from, to, owner, oldName, north)
    local toName = E.TO[oldName]
    if toName == nil or not E.on() or from == nil or to == nil then return callf(owner, oldName, north) end
    local v, ok = callf(from, toName, to)
    if ok and v ~= nil then return v, true end
    v, ok = callf(to, toName, from)
    if ok and v ~= nil then return v, true end
    return nil, true
end
return E
