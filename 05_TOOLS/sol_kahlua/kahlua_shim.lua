-- kahlua_shim.lua: run BEFORE the module under test in a lupa (real Lua 5.1) runtime, so offline tests fail where the
-- game's Kahlua would. Kahlua's BaseLib.tonumber (projectzomboid.jar, BaseLib.java:411-439):
--   0 arguments                 -> error "Not enough arguments"
--   exactly 1 argument          -> rawTonumber(x)                (the only safe path)
--   2+ arguments                -> (String) x  (line 419: ClassCastException for a number/boolean/table),
--                                  base = rawTonumber(arg2), nil base -> returns nil silently
-- tonumber(f()) with f returning 2+ values (or none) hits the bad paths. This shim is stricter than Kahlua on purpose:
-- with 2+ arguments it raises unless arg1 is a string AND arg2 is a number, so a silent wrong nil also shows up.
-- Usage (python):  L.execute(open(<sol_kahlua>/kahlua_shim.lua).read())   then load the module.
-- KAHLUA_SHIM_HITS counts every refused call (a module may pcall around the error; a test can assert the count is 0).
do
    local rawTonumber, rawSelect, rawType, rawError, rawTostring = tonumber, select, type, error, tostring
    KAHLUA_SHIM_HITS = 0
    KAHLUA_SHIM_LAST = nil
    local function refuse(msg)
        KAHLUA_SHIM_HITS = KAHLUA_SHIM_HITS + 1
        KAHLUA_SHIM_LAST = msg
        rawError(msg, 3)
    end
    tonumber = function(...)
        local n = rawSelect("#", ...)
        if n == 0 then refuse("kahlua_shim: tonumber() with no argument (Kahlua: Not enough arguments)") end
        local v, base = ...
        if n == 1 then return rawTonumber(v) end
        if rawType(v) ~= "string" then
            refuse("kahlua_shim: tonumber got " .. n .. " arguments, first is a " .. rawType(v)
                .. " (Kahlua: ClassCastException " .. rawType(v) .. " cannot be cast to String at BaseLib.tonumber:419)")
        end
        if rawType(base) ~= "number" or n > 2 then
            refuse("kahlua_shim: tonumber(" .. rawTostring(v) .. ", " .. rawTostring(base) .. ") with " .. n
                .. " arguments: the second is not a number base (Kahlua returns nil or crashes); wrap the call: tonumber((f()))")
        end
        return rawTonumber(v, base)
    end
end
