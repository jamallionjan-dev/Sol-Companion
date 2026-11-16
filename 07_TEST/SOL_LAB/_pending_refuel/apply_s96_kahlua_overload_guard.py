"""s96 kahlua_overload_guard (2026-11-11 10:35 live: 251+ "Cannot assign field callFrame because a is null at ReturnValues.put").
Root cause (reproduced offline on the game's own jar): Kahlua's MultiLuaJavaInvoker releases the pooled MethodArguments twice when
an overloaded Java method is called from Lua with arguments no overload accepts ("No implementation found for function"). The
pcall'd error is silent; the duplicate in the static pool later breaks any Lua->Java->Lua call. Only a restart clears the pool.
This installs SolKahluaGuard.lua (watches every pcall for that error and logs the call site once; Sol's own calls skip a signature
that already failed that way) and routes SolSort's and SolInventory's local call helpers through it.
Switch kahlua_overload_guard (read at call time; off = pass-through). Game closed only. usage: apply_s96_kahlua_overload_guard.py <client dir>"""
import os, shutil, sys
CL = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

# 1 the guard itself
shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "SolKahluaGuard.lua"), os.path.join(CL, "SolKahluaGuard.lua"))

# 2 SolSort's call helper (the item sort reads every item of the home through it)
edit(os.path.join(CL, "SolSort.lua"),
     'local function call(o, name, ...)' + NL +
     '    if o == nil then return nil end' + NL +
     '    local okF, f = pcall(function() return o[name] end)' + NL +
     '    if not okF or f == nil then return nil end' + NL +
     '    local ok, a = pcall(f, o, ...)' + NL +
     '    if ok then return a end' + NL +
     '    return nil' + NL +
     'end' + NL,
     'local function call(o, name, ...)' + NL +
     '    if o == nil then return nil end' + NL +
     '    local okF, f = pcall(function() return o[name] end)' + NL +
     '    if not okF or f == nil then return nil end' + NL +
     '    local KG_ = rawget(_G, "SolKahluaGuard")   -- s96 kahlua_overload_guard: a signature that already failed as no-overload is not called again' + NL +
     '    if type(KG_) == "table" and type(KG_.check) == "function" and KG_.check(o, name, ...) ~= nil then return nil end' + NL +
     '    local ok, a = pcall(f, o, ...)' + NL +
     '    if ok then return a end' + NL +
     '    if type(KG_) == "table" and type(KG_.learn) == "function" then KG_.learn(o, name, a, ...) end' + NL +
     '    return nil' + NL +
     'end' + NL)

# 3 SolInventory's method helper (the home scan that the sort starts)
edit(os.path.join(CL, "SolInventory.lua"),
     'local function method(o, name, ...)' + NL +
     '    if o == nil then return nil end' + NL +
     '    local f = o[name]' + NL +
     '    if type(f) ~= "function" then return nil end' + NL +
     '    local ok, v = pcall(f, o, ...)' + NL +
     '    if ok then return v end' + NL +
     '    return nil' + NL +
     'end' + NL,
     'local function method(o, name, ...)' + NL +
     '    if o == nil then return nil end' + NL +
     '    local f = o[name]' + NL +
     '    if type(f) ~= "function" then return nil end' + NL +
     '    local KG_ = rawget(_G, "SolKahluaGuard")   -- s96 kahlua_overload_guard' + NL +
     '    if type(KG_) == "table" and type(KG_.check) == "function" and KG_.check(o, name, ...) ~= nil then return nil end' + NL +
     '    local ok, v = pcall(f, o, ...)' + NL +
     '    if ok then return v end' + NL +
     '    if type(KG_) == "table" and type(KG_.learn) == "function" then KG_.learn(o, name, v, ...) end' + NL +
     '    return nil' + NL +
     'end' + NL)

# 4 the switch
A = os.path.join(CL, "SolAuthority.lua")
if '"kahlua_overload_guard"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "kahlua_overload_guard",' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "kahlua_overload_guard" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("kahlua_overload_guard=on" + CRLF)
print("s96 kahlua_overload_guard applied")
