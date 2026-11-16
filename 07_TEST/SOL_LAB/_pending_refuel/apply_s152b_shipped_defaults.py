"""s152b: the main copy falls back to switch defaults shipped inside the mod (media/lua/shared/SolFixesDefault.lua, written
by build_release.py) when SolFixes_MAIN.txt is missing or does not name a switch. The lab copy is unchanged (missing = on).
usage: apply_s152b_shipped_defaults.py <client dir>. Exact old->new; "kept" when already applied."""
import os, sys
CLIENT = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)
def edit(path, old, new):
    text = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in text else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in text: print("kept " + os.path.basename(path)); return
    if text.count(old) != 1: raise RuntimeError((os.path.basename(path), "expected one exact source block", text.count(old)))
    open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new)); print("edited " + os.path.basename(path))
p = os.path.join(CLIENT, "SolAuthority.lua")
edit(p, '''local function isLab() return type(rawget(_G, "SolLab")) == "table" and SolLab.active == true end
''', '''local function isLab() return type(rawget(_G, "SolLab")) == "table" and SolLab.active == true end
-- s152b: a switch no file names: on in the lab; in the main copy the default shipped with the mod (SolFixesDefault), else off
local function unnamed(fix)
    if isLab() then return true end
    local d = rawget(_G, "SolFixesDefault")
    return type(d) == "table" and d[fix] == true
end
''')
edit(p, '''parts[#parts + 1] = f .. "=" .. (t[f] == nil and (isLab() and "on" or "off") or (t[f] and "on" or "off")) end''',
        '''parts[#parts + 1] = f .. "=" .. (t[f] == nil and (unnamed(f) and "on" or "off") or (t[f] and "on" or "off")) end''')
edit(p, '''    if v == nil then return isLab() end      -- lab: untested fixes on; main: off until switched on''',
        '''    if v == nil then return unnamed(fix) end -- lab: untested fixes on; main: the shipped default, else off''')
print("s152b shipped defaults applied")
