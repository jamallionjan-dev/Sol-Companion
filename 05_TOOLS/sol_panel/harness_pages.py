"""Sol pages against a simulated Living Fellows UI: LF window never shown, its widgets read as data,
Sol controls call the same LF callbacks (ISButton.onclick / ISComboBox.onChange / ISTickBox.changeOptionMethod
with the argument order of PZ 42.21)."""
import os, sys
from lupa import lua51
from PIL import Image, ImageDraw
L = lua51.LuaRuntime(unpack_returned_tuples=True)
TEX = "build/media/textures/SolUI/"
L.globals()["TEXOK"] = lambda n: os.path.exists(TEX + n + ".png")
L.globals()["TEXW"] = lambda n: Image.open(TEX + n + ".png").size[0]
L.globals()["TEXH"] = lambda n: Image.open(TEX + n + ".png").size[1]
L.globals()["PEXISTS"] = lambda p: os.path.exists(p)
L.globals()["PSIZE"] = lambda p, i: Image.open(p).size[i]
L.globals()["LUA_DIR"] = "/tmp/"
L.execute(open("harness_stubs.lua").read())
L.execute(r'''
local baseGet = getTexture
function getTexture(p) if p:find("SolText/") then local f = "build/" .. p; if not PEXISTS(f) then return nil end
  return { name = f, getWidth = function() return PSIZE(f, 0) end, getHeight = function() return PSIZE(f, 1) end } end return baseGet(p) end
function ISPanel:setStencilRect() end
function ISPanel:clearStencilRect() end
function ISPanel:onMouseWheel() end
UI_BORDER_SPACING = 4
CALLS = {}
local function W(t) t.children = t.children or {}; return t end
local function btn(y, title, fn, args, enable) return W({ Type = "ISButton", y = y, x = 8, title = title, onclick = fn, target = "TGT", onClickArgs = args or {}, enable = enable ~= false }) end
local function lab(y, text, gold) local r, g, b = 0.88, 0.89, 0.83; if gold then r, g, b = 0.79, 0.73, 0.48 end; return W({ Type = "ISLabel", y = y, name = text, r = r, g = g, b = b }) end
local UI = {}
SurvivorCompanion.UI = UI
function UI.text(k, ...) local a = {...}; return "EN:" .. k .. (a[1] and ("|" .. tostring(a[1])) or "") end
function UI.tabIds() return { "talk", "status", "orders", "squad", "expeditions", "loadout", "more", "base", "journal", "debug" } end
function UI.commandAvailability(row, cmd) return cmd ~= "dismiss" end
SurvivorCompanion.Commands = { issue = function(id, cmd, payload, player) CALLS[#CALLS + 1] = "issue:" .. tostring(id) .. ":" .. cmd; return true end }
function UI.normalizeTab(t) return t end
local function build(root)
  local c = W({})
  local tab = root.selectedTab
  local T = SurvivorCompanion.UI.text
  if tab == "status" then
    c.children = { lab(7, T("UI_SC_Section_Status"), true), lab(27, T("UI_SC_Info_Health", "75%")), lab(47, T("UI_SC_Info_Hunger", "0%")) }
  elseif tab == "orders" then
    local combo = W({ Type = "ISComboBox", y = 30, options = { { text = T("UI_SC_Select_OrderFollow") }, { text = T("UI_SC_Select_OrderStay") } }, selected = 1, target = "TGT",
      onChange = function(target, combo, a1, a2) CALLS[#CALLS + 1] = "combo:" .. combo.selected .. ":" .. tostring(a1) end, onChangeArgs = { "main" } })
    local tick = W({ Type = "ISTickBox", y = 120, options = { T("UI_SC_Toggle_HoldFire") }, selected = { false }, changeOptionTarget = "TGT", changeOptionArgs = { "hold" },
      changeOptionMethod = function(target, i, sel, a1) CALLS[#CALLS + 1] = "tick:" .. i .. ":" .. tostring(sel) .. ":" .. tostring(a1) end,
      setSelected = function(self, i, v) self.selected[i] = v end })
    c.children = { lab(7, T("UI_SC_Section_DirectOrders"), true), combo,
      btn(70, T("UI_SC_Action_Regroup"), function(t, b, a1) CALLS[#CALLS + 1] = "regroup:" .. tostring(t) .. ":" .. tostring(a1) end, { "x1" }),
      btn(96, T("UI_SC_Action_Retreat"), function() CALLS[#CALLS + 1] = "retreat" end, {}, false), tick }
  elseif tab == "more" then
    c.children = { btn(10, T("UI_SC_Tab_Base"), function() root:setSelectedTab("base") end), btn(36, T("UI_SC_Tab_Journal"), function() root:setSelectedTab("journal") end) }
  else
    c.children = { lab(7, T("UI_SC_Tab_" .. tab), true) }
  end
  return c
end
local function newRoot()
  local r = ISPanel:new(1200, 60, 560, 520); r.selectedTab = "status"
  r.detail = { rebuild = function(self) self.content = build(r); r.builds = (r.builds or 0) + 1 end }
  function r:setSelectedTab(t) self.selectedTab = t; self.detail:rebuild() end
  function r:refreshRoster(id) self.companion = id; self.selectedRow = { id = id or "sc-1", name = "Sol", health = 0.75, equippedWeapon = "Katana", ammunition = 90,
    loadWeight = 33.3, loadCapacity = 50, loadRatio = 0.67, wounds = {}, supplies = "Bandages/rags: 0", relationshipTier = "trusted", trust = 0.6, bond = 0.5,
    mood = "calm", morale = "steady", timeTogetherHours = 41, currentNeed = "bandages", recentMemory = "We got out together." } end
  r.detail:rebuild()
  r:refreshRoster("sc-1")
  return r
end
function UI.ensureControl() if not UI.instance then UI.instance = newRoot() end; UI.instance.visible = true; return UI.instance end
function UI.restoreStartupVisibility() local r = UI.ensureControl(); r.visible = true end
function UI.open(tab, id) local r = UI.ensureControl(); r:setSelectedTab(tab); return r end
function UI.showCollapsedLauncher() UI.launcher = ISPanel:new(0, 0, 10, 10); return UI.launcher end
STARTS = {}; Events = { OnGameStart = { Add = function(f) STARTS[#STARTS + 1] = f end } }
function ONSTART() for _, f in ipairs(STARTS) do f() end end
getTextManager = function() return { MeasureFont = function() return 16 end, MeasureStringX = function(_, f, s) return #s * 7 end, MeasureStringY = function() return 16 end } end
''')
for f in ("SolTextData.lua", "SolText.lua", "SolLF_AR.lua"):
    L.execute(open("build/media/lua/client/" + f, encoding="utf-8").read())
L.execute("ISLabel = ISPanel; ISButton = ISPanel; ISTickBox = ISPanel; ISComboBox = ISPanel; ISComboBoxPopup = nil")
for f in ("SolArabicUI.lua", "SolPanel.lua", "SolPages.lua", "SolSkin.lua"):
    L.execute(open("build/media/lua/client/" + f, encoding="utf-8").read())
G = L.globals(); UI = G.SurvivorCompanion.UI; U = G.SolUI; res = []
def dec(x): return "".join(chr(c) for c in G.SolText.codepoints(x).values())
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
G.ONSTART(); UI.restoreStartupVisibility()
check("game start: no LF window", UI.instance is None or UI.instance.visible == False)
lau = U.launcher; lau.onMouseDown(lau, 50, 50); lau.onMouseUp(lau, 50, 50); pan = U.panel
pan.onMouseDown(pan, 440, 450); pan.onMouseUp(pan, 440, 450)
pg = U.page
check("status button opens the Sol page, LF root stays hidden", pg is not None and pg.visible and UI.instance.visible == False and pg.tab == "status")
items = [ (it.kind, dec(it.text)) for it in pg["items"].values() ]
check("LF status content read as data, in Arabic", items[0] == ("section", "الحالة") and items[1] == ("label", "الصحة: 75%"))
UI.open("orders", "sc-1")
check("LF entry points (right-click 'orders') open the Sol page instead", pg.tab == "orders" and UI.instance.visible == False and UI.instance.companion == "sc-1")
kinds = [it.kind for it in pg["items"].values()]
check("orders: section, combo, 2 buttons, tick read in order", kinds == ["section", "combo", "button", "button", "tick"])
combo = pg["items"][2]
check("combo options translated", [dec(o) for o in combo.options.values()] == ["متابعة", "بقاء"])
G.DRAWS = L.table(); pg.prerender(pg); pg.render(pg)
hits = list(pg.hits.values())
bt = [h for h in hits if h.kind == "button"]
check("buttons laid out as rounded Sol rows; disabled one marked", len(bt) == 2 and bt[1].it.enabled == False)
r = bt[0].r; pg.onMouseUp(pg, r[1] + 5, r[2] + 5)
check("Sol button -> LF onclick(target, button, args...)", "regroup:TGT:x1" in list(G.CALLS.values()))
r = bt[1].r; n0 = len(G.CALLS); pg.onMouseUp(pg, r[1] + 5, r[2] + 5)
check("disabled LF button is not called", len(G.CALLS) == n0)
ch = [h for h in pg.hits.values() if h.kind == "combo"][0]
pg.onMouseUp(pg, ch.r[1] + 5, ch.r[2] + 5); check("combo opens a Sol dropdown", pg.dd is not None)
G.DRAWS = L.table(); pg.render(pg); rr = pg.dd.rects[2]
pg.onMouseUp(pg, rr[1] + 5, rr[2] + 5)
check("dropdown choice -> LF onChange(target, combo, args) with selected=2", "combo:2:main" in list(G.CALLS.values()))
G.DRAWS = L.table(); pg.prerender(pg)
tk = [h for h in pg.hits.values() if h.kind == "tick"][0]; pg.onMouseUp(pg, tk.r[1] + 5, tk.r[2] + 5)
check("tick -> LF changeOptionMethod(target, index, selected, args)", "tick:1:true:hold" in list(G.CALLS.values()))
G.DRAWS = L.table(); pg.prerender(pg)
ld = [t for t in pg.tabRects.values() if t.id == "loadout"][0]; pg.onMouseUp(pg, ld.r[1] + 5, ld.r[2] + 5)
check("tab column switches tabs", pg.tab == "loadout")
ids = [t.id for t in U.pageTabs().values()]
check("Sol tab set: status, skills, orders, loadout, family (no groups / expeditions / more / debug / talk)", ids == ["status", "skills", "orders", "loadout", "family"])
G.DRAWS = L.table(); pg.prerender(pg)
lf = [h for h in pg.hits.values() if h.kind == "lf"]
check("loadout card: quick actions available from the LF row", [h.command for h in lf] == ["open_inventory", "open_health", "bandage"])
pg.onMouseUp(pg, lf[0].r[1] + 5, lf[0].r[2] + 5)
check("card button -> SC.Commands.issue(row.id, command, payload, player) like LF", "issue:sc-1:open_inventory" in list(G.CALLS.values()))
texts = "".join(dec(d[2]) if False else "" for d in [])
pg.tab = "family"; pg.refresh(pg, True); G.DRAWS = L.table(); pg.prerender(pg)
tabs_drawn = [d for d in G.DRAWS.values() if d[1] == "tex" and d[2] in ("pg_tab_on", "pg_tab_off")]
check("family page: 7-step relationship ladder drawn (5 + romance + married)", len(tabs_drawn) >= 7 + 5)
# LF measures text with the game font: escaped Arabic must not be cut while LF builds
L.execute(r"""
function getTextManager() return { MeasureFont = function() return 16 end, MeasureStringY = function() return 16 end,
  MeasureStringX = function(_, f, s) return #s * 7 end } end
""")
w_escaped = L.eval("function() local r; SolUI.withMeasure(function() r = getTextManager():MeasureStringX(UIFont.Small, SolUI.translate('UI_SC_Info_Health', '75%')) end); return r end")()
w_plain = L.eval("function() return getTextManager():MeasureStringX(UIFont.Small, SolUI.translate('UI_SC_Info_Health', '75%')) end")()
check("LF measures Arabic with its real width while building (problem 1: %d px instead of %d)" % (w_escaped, w_plain), w_escaped < w_plain / 2)
w_en = L.eval("function() local r; SolUI.withMeasure(function() r = getTextManager():MeasureStringX(UIFont.Small, 'Health: 75%') end); return r end")()
check("English text keeps the game's own measurement", w_en == len("Health: 75%") * 7)
UI.toggle(); check("LF hotkey toggle closes the Sol page", pg.visible == False)
UI.showStatus(L.eval("{ id = 'sc-1' }")); check("LF showStatus opens the Sol status page", pg.visible and pg.tab == "status")
pg.onMouseUp(pg, 30, 20); check("back returns to the Sol panel", not pg.visible and pan.visible)
check("LF root never became visible", UI.instance.visible == False)
L.execute(r'''
local function perk(id, parent) return { getType = function() return { name = function() return id end } end, getParent = function() return parent end,
  getName = function() return id end, getTotalXpForLevel = function(_, lv) return lv * 75 end } end
local none = perk("None", nil)
local passive, combat = perk("Passiv", none), perk("Combat", none)
local P = { perk("Fitness", passive), perk("Strength", passive), perk("Axe", combat), perk("Spear", combat) }
PerkFactory = { PerkList = { size = function() return #P + 3 end, get = function(_, i) return ({ passive, combat, none, P[1], P[2], P[3], P[4] })[i + 1] end } }
SOL.getPerkLevel = function(self, p) local id = p.getType().name(); return ({ Fitness = 5, Strength = 5, Axe = 2 })[id] or 0 end
SOL.getXp = function() return { getXP = function(_, p) return 0.5 end } end
''')
U.openPage("skills"); G.DRAWS = L.table(); pg.mx, pg.my, pg.over = 300, 66 + 34 + 5, True; pg.prerender(pg)
d = [x for x in G.DRAWS.values() if x[1] == "tex"]
on = sum(1 for x in d if x[2] == "pg_skill_on"); off = sum(1 for x in d if x[2] == "pg_skill_off")
check("skills tab listed right after Status", [t.id for t in U.pageTabs().values()][:2] == ["status", "skills"])
check("skills read from the game's perk list: 2 categories, 4 skills, 10 boxes each (12 filled)", on == 12 and off == 28 and len(pg.skills) == 2)
check("Arabic skill and category names", dec(pg.skills[1].label) == "سلبية" and dec(pg.skills[1].skills[1].label) == "اللياقة")
check("hover shows level and XP like the player's panel", pg.tip is not None and "5" in pg.tip and "0.5 / 450" in pg.tip)
pg.skills[1].skills[1].label = "%9'/) 'D*DBJE"   # the exact label that crashed gsub in game (v0.5.1)
G.DRAWS = L.table(); ok_hover = L.eval("function(p) return pcall(p.prerender, p) end")(pg)
check("skill hover with '%' in the name does not crash (game crash 2026-10-24)", (ok_hover is True or (isinstance(ok_hover, tuple) and ok_hover[0] is True)) and pg.tip is not None)
L.execute(r'''
READ = nil
SolUI.solBooks = function() return { { item = "BOOK1", name = "Cooking Vol 1", status = "useful", pages = 220, read = 40 }, { item = "BOOK3", name = "Cooking Vol 3", status = "too_hard", pages = 220, read = 0 } } end
SolUI.solRead = function(it) READ = it; return true end
SolUI.recipeStats = { total = 1200, learnable = 300, known = 12 }
''')
pg.refresh(pg, True); G.DRAWS = L.table(); pg.prerender(pg)
rd = [h for h in pg.hits.values() if h.kind == "read"]
check("books: only the useful one gets a Read button", len(rd) == 1 and rd[0].it.name == "Cooking Vol 1")
pg.onMouseUp(pg, rd[0].r[1] + 5, rd[0].r[2] + 5)
check("Read button -> Sol reads that book", G.READ == "BOOK1")
# previews of the pages as the Lua code draws them
def preview(tab, path):
    U.openPage(tab); pg.refresh(pg, True); G.DRAWS = L.table(); pg.prerender(pg)
    im = Image.new("RGBA", (600, 640), (40, 62, 46, 255))
    for d in G.DRAWS.values():
        if d[1] == "tex":
            name = d[2]; fp = name if str(name).startswith("build/") else TEX + name + ".png"
            t = Image.open(fp).convert("RGBA").resize((max(1, int(d[5])), max(1, int(d[6]))))
            if d[7] < 1: t.putalpha(t.getchannel("A").point(lambda v: int(v * d[7])))
            im.alpha_composite(t, (int(d[3]), int(d[4])))
        elif d[1] == "rect":
            ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
            dr.rectangle((d[2], d[3], d[2] + d[4] - 1, d[3] + d[5] - 1), fill=(int(d[7] * 255), int(d[8] * 255), int(d[9] * 255), int(d[6] * 255))); im.alpha_composite(ov)
        elif d[1] == "text":
            ImageDraw.Draw(im).text((d[3], d[4]), d[2], fill=(200, 210, 220, 255))
    im.convert("RGB").save(path)
for tab in ("status", "orders", "loadout", "family"):
    preview(tab, "/tmp/page_%s.png" % tab)
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
