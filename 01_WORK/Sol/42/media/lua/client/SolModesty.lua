-- SolModesty.lua - switch modest_chest (2026-11-15, s158), 0.3.0.
-- Jamal 2026-11-15: with a T-shirt or a tank top on, Sol's chest shows every detail as if she wore nothing. Those tops are
-- "painted" clothing: a texture on the body mesh itself, so the body's own shape is what he sees.
-- Her body patch (SolCombined.jar, javap) has a mode that nothing in Sol ever turned on:
--   localplayerbody.CensorshipMode.configure(boolean), exposed to Lua as LocalPlayerVSGirlCensorship. The FIRST call of
--   a game session decides. On only for a female character whose PlayerChoice is enabled (Sol).
-- Runtime, his words the same evening: in the world the result is right and without clothes she is back to her natural
-- look; keep it. (0.2.0, a bra under every top, was never installed: he reports a bra changes nothing.)
-- Still open, his words: only the tips are covered; from below the chest still reads as bare under the cloth. The patch
-- has a cloth-bridge feature for painted tops (TextureBridgeModels) that does not show on her. Switch chest_diag turns
-- on the patch's own diagnostics (Physics.configureDiagnostics(boolean), exposed as LocalPlayerVSGirlPhysics) so the
-- log says why. chest_diag is for one test run; it changes nothing she looks like.
require "SolAuthority"
SolModesty = SolModesty or {}
local M = SolModesty
M.VERSION = "0.3.0"
local function log(m) print("[SolModesty] " .. tostring(m)) end
local function fix(name)
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on(name) == true
end
function M.on() return fix("modest_chest") end
function M.apply()
    if M.done ~= nil then return M.done end
    local want = M.on()
    local C = rawget(_G, "LocalPlayerVSGirlCensorship")
    if C == nil then
        if want and not M.said then M.said = true; log("the body patch class is not in this game session yet") end
        return false
    end
    local ok, err = pcall(function() C.configure(want) end)
    M.done = ok
    log(ok and ("covered chest mode " .. (want and "ON" or "OFF")) or ("could not set the mode: " .. tostring(err)))
    return ok
end
function M.diagnostics()
    if M.diagDone then return end
    local P = rawget(_G, "LocalPlayerVSGirlPhysics")
    if P == nil then return end
    M.diagDone = true
    if not fix("chest_diag") then return end
    local ok, err = pcall(function() P.configureDiagnostics(true) end)
    log(ok and "body patch diagnostics ON (one test run)" or ("could not turn diagnostics on: " .. tostring(err)))
end
M.apply()
M.diagnostics()
-- a class was not there yet at load: one more try when a world starts
local ev = rawget(_G, "Events")
if ev and ev.OnGameStart and not M.hooked then
    M.hooked = true
    ev.OnGameStart.Add(function() if M.done ~= true then pcall(M.apply) end; pcall(M.diagnostics) end)
end
return M
