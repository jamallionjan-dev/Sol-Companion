"""Arabic in the game, as it really behaves (proven 2026-10-24):
 - the game keeps only the low 8 bits of non-ASCII characters in Lua files -> Sol's Lua files must be ASCII,
   Arabic is written as \\uXXXX escapes and decoded by SolText;
 - Sol never patches the game's own widgets (the main menu was redrawn by 0.1.x patches);
 - Living Fellows texts are translated only while the Sol pages read them."""
import glob, sys
from lupa import lua51
res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
files = sorted(glob.glob("build/media/lua/client/Sol*.lua"))
bad = [f for f in files if any(ord(ch) > 127 for ch in open(f, encoding="utf-8").read())]
check("every Sol Lua file is pure ASCII (%d files)" % len(files), not bad)
import re as _re
single = [f for f in files if _re.search(r"(?<!\\)\\u[0-9A-Fa-f]{4}", open(f, encoding="ascii").read())]
check("Arabic escapes are written \\\\uXXXX (a Lua '\\u' would be lost)", not single)
def game_load(src):   # what Project Zomboid does to a Lua file: each character keeps its low 8 bits
    return "".join(chr(ord(ch) & 0xFF) if ord(ch) > 127 else ch for ch in src)
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("package.path = 'build/media/lua/client/?.lua;' .. package.path")
L.execute(r'''
UIFont = { Small = "S" }
PATCHED = {}
ISLabel = { prerender = function() end }; ISButton = { render = function() end }; ISTickBox = { render = function() end }; ISComboBox = { render = function() end }
ORIG = { ISLabel.prerender, ISButton.render, ISTickBox.render, ISComboBox.render }
SolUI = { lang = function() return LANG end }; LANG = "ar"
SurvivorCompanion = { UI = { text = function(key, ...) local a = {...}; return "EN:" .. key .. (a[1] and ("|" .. tostring(a[1])) or "") end } }
''')
for f in ("SolTextData.lua", "SolText.lua", "SolLF_AR.lua", "SolArabicUI.lua"):
    L.execute(game_load(open("build/media/lua/client/" + f, encoding="utf-8").read()))
G = L.globals(); T = G.SolText; U = G.SolUI
dec = lambda s: "".join(chr(c) for c in T.codepoints(s).values())
check("self check (escapes) passes after the game's loading", T.selfCheck() == True)
check("main-menu regression: English text stays English (no Arabic code points)", all(c < 128 for c in T.codepoints("NEW GAME  Continue  Options  (c) The Indie Stone").values()))
check("game widgets are not patched at all", L.eval("ISLabel.prerender == ORIG[1] and ISButton.render == ORIG[2] and ISTickBox.render == ORIG[3] and ISComboBox.render == ORIG[4]"))
UIt = G.SurvivorCompanion.UI.text
check("outside the Sol pages: English (menus untouched)", UIt("UI_SC_Action_Follow") == "EN:UI_SC_Action_Follow")
r = U.withArabic(L.eval("function() return SurvivorCompanion.UI.text('UI_SC_Info_Health', '100%') end"))[0]
check("inside the Sol pages: Arabic with %1 filled", dec(r) == "الصحة: 100%")
r2 = U.withArabic(L.eval("function() return SurvivorCompanion.UI.text('UI_SC_Base_Readiness', 80) end"))[0]
check("%% becomes a literal %", dec(r2) == "الجاهزية: 80%")
r3 = U.withArabic(L.eval("function() return SurvivorCompanion.UI.text('UI_SC_Debug_Trace') end"))[0]
check("untranslated key falls back to the original", r3 == "EN:UI_SC_Debug_Trace")
G.LANG = "en"; check("Sol language EN: no translation", U.withArabic(L.eval("function() return SurvivorCompanion.UI.text('UI_SC_Info_Health', 1) end"))[0].startswith("EN:")); G.LANG = "ar"
check("shaping still works on escaped text", list(T.shape(T.codepoints("\\u0633\\u0648\\u0644")).values()) == [0xFEB3, 0xFEEE, 0xFEDD])
check("real Java chars > 255 (typed text) still decode", list(T.codepoints(L.eval("{0x633}")).values()) == [0x633])
check("digits always 0-9: Arabic-Indic and Persian digits become 0-9", list(T.codepoints("\\u0667\\u0665% \\u06F1\\u06F2").values()) == [55, 53, 37, 32, 49, 50])
vis = list(T.visual(T.shape(T.codepoints("\\u0627\\u0644\\u0635\\u062D\\u0629: \\u0667\\u0665%")), "R").values())
check("number stays left-to-right inside Arabic: '75' not '57'", "".join(chr(c) for c in vis if 48 <= c <= 57) == "75")
# proof of the cause: an Arabic literal loaded the game's way becomes ASCII garbage
broken = game_load("سول")
check("cause reproduced: 'سول' loads as '3HD' in game", broken == "3HD")
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
