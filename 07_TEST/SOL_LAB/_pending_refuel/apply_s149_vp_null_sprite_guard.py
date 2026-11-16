"""s149 Viewpoint null-sprite guard, gated independently in SolAuthority."""
import os
import re
import sys

CLIENT = sys.argv[1]
NL = chr(10)
CRLF = chr(13) + chr(10)


def edit(path, old, new):
    text = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in text else NL
    old = old.replace(NL, nl)
    new = new.replace(NL, nl)
    if new in text:
        print("kept " + os.path.basename(path))
        return
    if text.count(old) != 1:
        raise RuntimeError((os.path.basename(path), "expected one exact source block", text.count(old)))
    open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new))
    print("edited " + os.path.basename(path))


compat = os.path.join(CLIENT, "SolCompatVP.lua")
edit(compat,
     'M.stats = M.stats or { scans = 0, found = 0, fallbacks = 0, errors = 0, vpKnown = 0 }',
     'M.stats = M.stats or { scans = 0, found = 0, fallbacks = 0, errors = 0, vpKnown = 0, nullSpriteSkips = 0 }')
edit(compat, 'function M.install()' + NL,
     '''function M.installNullSpriteGuard()
    local V = g("ViewpointInteract")
    if type(V) ~= "table" or type(V.harvest) ~= "function" then return false end
    if V._solNullSpriteGuard then return true end
    local original = V.harvest
    V.harvest = function(player, object, ...)
        local authority = g("SolAuthority")
        if type(authority) == "table" and type(authority.on) == "function"
            and authority.on("vp_null_sprite_guard") == true and object ~= nil then
            local ok, spriteName = pcall(function() return object:getSpriteName() end)
            if ok and spriteName == nil then
                M.stats.nullSpriteSkips = M.stats.nullSpriteSkips + 1
                once("null_sprite", "skipped Viewpoint harvest for an object with no sprite")
                return { why = "object has no sprite" }
            end
        end
        return original(player, object, ...)
    end
    V._solNullSpriteGuard = true
    return true
end

function M.install()
''' )
edit(compat,
     '    local k = M.installKnown()' + NL + '    if not M._logged then',
     '    local k = M.installKnown()' + NL + '    local v = M.installNullSpriteGuard()' + NL + '    if not M._logged then')
edit(compat,
     '            .. ", Viewpoint QOL filter " .. (k and "wrapped" or "absent") .. ")")',
     '            .. ", Viewpoint QOL filter " .. (k and "wrapped" or "absent")' + NL +
     '            .. ", null-sprite guard " .. (v and "wrapped" or "absent") .. ")")')
edit(compat,
     '    local ok, r = pcall(f, o, ...)' + NL + '    if ok then return r end' + NL + '    return nil',
     '    local guard = g("SolKahluaGuard")' + NL +
     '    if type(guard) == "table" and type(guard.call) == "function" then' + NL +
     '        local guarded, value = guard.call(o, name, ...)' + NL +
     '        if guarded then return value end' + NL +
     '        return nil' + NL +
     '    end' + NL +
     '    local ok, r = pcall(f, o, ...)' + NL + '    if ok then return r end' + NL + '    return nil')

authority = os.path.join(CLIENT, "SolAuthority.lua")
text = open(authority, encoding="utf-8", newline="").read()
if '"vp_null_sprite_guard"' not in text:
    edit(authority, 'A.FIXES = {' + NL,
         'A.FIXES = {' + NL + '    "vp_null_sprite_guard", -- s149: skip Viewpoint menu construction on objects without sprites' + NL)
else:
    print("kept vp_null_sprite_guard switch in SolAuthority.lua")

if len(sys.argv) > 2:
    switches = sys.argv[2]
    text = open(switches, encoding="utf-8", newline="").read()
    if not re.search(r"(?m)^vp_null_sprite_guard=", text):
        with open(switches, "a", encoding="utf-8", newline="") as output:
            output.write(("" if text.endswith((NL, CRLF)) else CRLF) + "vp_null_sprite_guard=on" + CRLF)
        print("enabled vp_null_sprite_guard in LAB switches")
    else:
        print("kept vp_null_sprite_guard LAB switch")

print("s149 Viewpoint null-sprite guard applied")
