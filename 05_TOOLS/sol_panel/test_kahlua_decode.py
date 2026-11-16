"""Emulates the game's string behaviour seen on 2026-10-23: one char per position, string.byte() = low 8 bits."""
import sys
from lupa import lua51
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("package.path = 'build/media/lua/client/?.lua;' .. package.path")
L.execute(open("build/media/lua/client/SolTextData.lua", encoding="utf-8").read())
L.execute(open("build/media/lua/client/SolText.lua", encoding="utf-8").read())
L.execute(r'''
-- Kahlua emulation: positions are UTF-8 characters, byte() keeps only the low 8 bits of the code point
local function chars(s) local t = {} for ch in string.gmatch(s, "[%z\1-\127\194-\244][\128-\191]*") do t[#t + 1] = ch end return t end
local function cp(ch)
  local c = string.byte(ch, 1); if c < 0x80 then return c end
  local n = (c >= 0xF0 and 3) or (c >= 0xE0 and 2) or 1
  local v = c % (2 ^ (6 - n)); for k = 2, n + 1 do v = v * 64 + (string.byte(ch, k) - 0x80) end; return v
end
SolText._len = function(s) return #chars(s) end
SolText._sub = function(s, i, j) local t = chars(s); return table.concat(t, "", i, j) end
SolText._byte = function(s, i) local t = chars(s); return cp(t[i or 1]) % 256 end
SolText.KAHLUA = true
SolText._resetMap()
''')
T = L.globals().SolText
res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
def cps(s): return list(T.codepoints(s).values())
check("masked byte() alone would be wrong (the bug seen in game)", L.eval("SolText._byte('ب')") == 0x28)
check("Arabic decoded through the lookup", cps("الحالة") == [0x627, 0x644, 0x62D, 0x627, 0x644, 0x629])
check("mixed Arabic / Latin / digits", cps("الصحة: 75%") == [0x627,0x644,0x635,0x62D,0x629,0x3A,0x20,0x37,0x35,0x25])
check("presentation forms and punctuation (، ؟ —)", cps("،؟—") == [0x60C, 0x61F, 0x2014])
check("Latin-1 (é) decoded", cps("é") == [0xE9])
check("self check passes", T.selfCheck() == True)
check("escape for files is pure ASCII", T.escape(T.codepoints("مرحبا")) == "\\u0645\\u0631\\u062D\\u0628\\u0627")
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
