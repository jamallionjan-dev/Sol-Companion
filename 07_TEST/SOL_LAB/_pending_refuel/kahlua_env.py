"""lupa, made to behave like the game's Kahlua for every built-in we could measure.

Every rule below comes from 05_TOOLS/sol_kahlua/probe.lua run on the game's own classes (compare.py prints the differences).
What cannot be copied here, because the operator never reaches Lua code: `%` takes the sign of the left operand in Kahlua,
`#t` and `unpack` stop at the first nil. Those two are checked on the bytecode by test_kahlua_scan.py instead.

Use:  from kahlua_env import lua51   (instead of: from lupa import lua51)
"""
from lupa import lua51 as _lua51

PRELUDE = r"""
LUA_NEXT = next
next, xpcall, io, debug, dofile, loadfile, load, module, newproxy, gcinfo = nil
string.gfind, string.dump = nil
math.mod, math.random, math.randomseed = nil
table.getn, table.foreach, table.foreachi, table.maxn, table.setn = nil
os.clock, os.execute, os.exit, os.getenv, os.remove, os.rename, os.setlocale, os.tmpname = nil

do
    local rawTonumber, rawType, rawError, rawPcall, rawSelect = tonumber, type, error, pcall, select
    tonumber = function(...)
        local n = rawSelect("#", ...)
        if n == 0 then rawError("Not enough arguments java.lang.RuntimeException", 2) end
        local v, base = ...
        if n == 1 then
            if rawType(v) == "string" and string.find(v, "^%s*[-+]?0[xX]") then return nil end    -- no hex without a base
            return rawTonumber(v)
        end
        if rawType(v) ~= "string" then rawError("class java.lang.Double cannot be cast to class java.lang.String", 2) end
        if base == nil then return nil end
        return rawTonumber(v, base)
    end
    select = function(i, ...)
        if i == "#" then return rawSelect("#", ...) end
        if i == nil then rawError('Cannot invoke "java.lang.Double.doubleValue()" because "o" is null', 2) end
        local k = rawTonumber(i)
        if k == nil or k < 1 then return end
        return rawSelect(k, ...)
    end
    -- a failed pcall hands back more than the message: the stack and the Java exception
    local function shape(ok, ...)
        if ok == false then return false, (...), "at lua", "java.lang.RuntimeException" end
        return ok, ...
    end
    pcall = function(f, ...) return shape(rawPcall(f, ...)) end
end

do
    local rawLen, rawGsub, rawType, rawError, rawConcat, rawTostring, rawFloor = string.len, string.gsub, type, error, table.concat, tostring, math.floor
    string.len = function(s)
        if rawType(s) ~= "string" then rawError("__len not defined for operand java.lang.RuntimeException", 2) end
        return rawLen(s)
    end
    local function captures(p)
        local n, i, set = 0, 1, false
        while i <= rawLen(p) do
            local c = string.sub(p, i, i)
            if c == "%" then i = i + 1
            elseif set then if c == "]" then set = false end
            elseif c == "[" then set = true; if string.sub(p, i + 1, i + 1) == "^" then i = i + 1 end; if string.sub(p, i + 1, i + 1) == "]" then i = i + 1 end
            elseif c == "(" then n = n + 1 end
            i = i + 1
        end
        return n
    end
    string.gsub = function(s, p, r, n)
        local t = rawType(r)
        if t == "string" and rawType(p) == "string" then
            local caps, i = captures(p), 1
            while true do
                local a = string.find(r, "%", i, true)
                if not a then break end
                local d = tonumber(string.sub(r, a + 1, a + 1))
                if d and d > caps and d > 0 then rawError("se.krka.kahlua.vm.KahluaException: invalid capture index java.lang.RuntimeException", 2) end
                i = a + 2
            end
        elseif t == "function" then
            local f = r
            r = function(...) local v = f(...); if v == false or v == true then return "null" end; return v end
        elseif t == "table" then
            local src = r
            r = function(k) local v = src[k]; if v == false or v == true then return "null" end; return v end
        end
        if n == nil then return rawGsub(s, p, r) end
        return rawGsub(s, p, r, n)
    end
    string.contains = function(s, x) return string.find(s, x, 1, true) ~= nil end
    string.trim = function(s) return (rawGsub(s, "^%s*(.-)%s*$", "%1")) end
    string.split = function(s, sep)
        local out, from = {}, 1
        while true do
            local a, b = string.find(s, sep, from)
            if not a then out[#out + 1] = string.sub(s, from); return out end
            out[#out + 1] = string.sub(s, from, a - 1); from = b + 1
        end
    end
    table.wipe = function(t) for k in LUA_NEXT, t do t[k] = nil end end
    table.isempty = function(t) return LUA_NEXT(t) == nil end
    -- stops at the first nil; a boolean becomes the text "null"
    table.concat = function(t, sep, i, j)
        local out = {}
        i = i or 1
        j = j or #t
        for k = i, j do
            local v = t[k]
            if v == nil then break end
            if rawType(v) == "boolean" then v = "null" end
            out[#out + 1] = v
        end
        return rawConcat(out, sep or "")
    end
    math.max = function(max, ...)
        for i = 1, select("#", ...) do local v = select(i, ...); if max < v then max = v end end
        return max
    end
    math.min = function(min, ...)
        for i = 1, select("#", ...) do local v = select(i, ...); if v < min then min = v end end
        return min
    end
    tostring = function(v, ...)
        if rawType(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge then
            if rawFloor(v) == v and v > -1e15 and v < 1e15 then return string.format("%.0f", v) end
            if rawFloor(v) == v then return (string.format("%.15e", v):gsub("0+e", "e"):gsub("%.e", ".0e"):gsub("e%+0*", "E"):gsub("e%-0*", "E-")) end
            for p = 15, 17 do local s = string.format("%." .. p .. "g", v); if tonumber(s) == v then return s end end
        end
        return rawTostring(v)
    end
end
"""

class _KahluaLupa:
    """Stands in for lupa.lua51: every runtime it makes starts with PRELUDE."""
    def __getattr__(self, name):
        return getattr(_lua51, name)
    def LuaRuntime(self, *a, **k):
        r = _lua51.LuaRuntime(*a, **k)
        r.execute(PRELUDE)
        return r

lua51 = _KahluaLupa()
