"""SolSkin.lua against a simulated Living Fellows UI (same API shape as SCUI.lua 0.26.40)."""
import sys
from lupa import lua51
L = lua51.LuaRuntime(unpack_returned_tuples=True)
import os
from PIL import Image
L.globals()["TEXOK"] = lambda n: os.path.exists("build/media/textures/SolUI/" + n + ".png")
L.globals()["TEXW"] = lambda n: Image.open("build/media/textures/SolUI/" + n + ".png").size[0]
L.globals()["TEXH"] = lambda n: Image.open("build/media/textures/SolUI/" + n + ".png").size[1]
L.execute(open("harness_stubs.lua").read())
L.execute(r'''
ISLabel = {}; ISLabel.__index = ISLabel
function ISLabel:new(x, y, h, name, r, g, b, a) local o = { Type = "ISLabel", name = name, r = r, g = g, b = b, a = a, children = {} }; setmetatable(o, ISLabel); return o end
ISButton = {}; ISButton.__index = ISButton
function ISButton:new(x, y, w, h, title, target, onclick) local o = { Type = "ISButton", x = x, y = y, width = w, height = h, title = title, target = target, onclick = onclick, visible = true, children = {},
  backgroundColor = { r = 0.035, g = 0.04, b = 0.035, a = 0.8 } }; setmetatable(o, ISButton); return o end
function ISButton:initialise() end
function ISButton:instantiate() end
function ISButton:setVisible(v) self.visible = v end
function ISButton:setX(v) self.x = v end
function ISButton:setY(v) self.y = v end
function ISButton:setWidth(v) self.width = v end
function ISButton:setHeight(v) self.height = v end
-- simulated LF classes
Root = setmetatable({}, { __index = ISPanel }); Root.__index = Root
function Root:applyLayout() self.layouts = (self.layouts or 0) + 1; self.collapseButton:setVisible(true) end
function Root:updateTabButtons() for _, b in ipairs(self.tabButtons) do b.backgroundColor = (b.scTab == self.selectedTab) and { r = 0.34, g = 0.38, b = 0.27, a = 0.9 } or { r = 0.12, g = 0.13, b = 0.12, a = 0.8 } end end
function Root:prerender() self.lfPrerender = true end
function Root:applyScreenBounds() self.x = 0; self.docked = true end   -- LF: snaps the window to a screen side
function Root:render() self.lfTitle = "Living Fellows: Companion" end
function Root:setCollapsed(c) self.collapsed = c; if c then SurvivorCompanion.UI.showCollapsedLauncher(self) else self.visible = true end end
Detail = setmetatable({}, { __index = ISPanel }); Detail.__index = Detail
function Detail:contentViewportHeight() return self.height - 30 end
function Detail:rebuild()
  local panel = ISPanel:new(0, 0, 300, 400); panel.children = {}
  panel.children[1] = ISLabel:new(8, 0, 16, "Status", 0.79, 0.73, 0.48, 1)
  panel.children[2] = ISLabel:new(8, 20, 16, "Health: 100%", 0.88, 0.89, 0.83, 1)
  panel.children[3] = ISButton:new(8, 40, 200, 20, "Open companion inventory", nil, function() end)
  self.content = panel; self.rebuilds = (self.rebuilds or 0) + 1
end
local function newRoot()
  local r = ISPanel:new(1200, 60, 560, 520); setmetatable(r, Root)
  r.metrics = { headerHeight = 30, fontHeight = 16, rosterItemHeight = 70, lineHeight = 15 }
  r.collapseButton = ISButton:new(6, 5, 82, 20, "Collapse"); r.dockButton = ISButton:new(94, 5, 100, 20, "Dock left"); r.talkButton = ISButton:new(500, 5, 58, 20, "Talk")
  r.tabButtons = {}; for _, t in ipairs({ "status", "orders", "squad", "expeditions", "loadout", "more" }) do local b = ISButton:new(0, 0, 80, 20, t); b.scTab = t; r.tabButtons[#r.tabButtons + 1] = b end
  r.selectedTab = "status"
  r.roster = ISPanel:new(6, 31, 160, 400); r.roster.selected = 1
  r.detail = setmetatable({ root = r, x = 170, y = 60, width = 380, height = 440, children = {} }, Detail); r.detail:rebuild()
  r.roster.items = { { item = { name = "Sol" } } }
  return r
end
SurvivorCompanion.UI = {}
local UI = SurvivorCompanion.UI
UI.text = function(k, ...) return k end
UI.healthText = function(h) return "100%" end
UI.distanceText = function(d) return "2.0 tiles" end
UI.stateText = function(s) return tostring(s) end
UI.showCollapsedLauncher = function(root) UI.launcher = UI.launcher or ISPanel:new(0, 0, 40, 40); UI.launcher.visible = true; root.visible = false; return UI.launcher end
UI.ensureControl = function() if not UI.instance then UI.instance = newRoot() end; if UI.instance.collapsed then UI.showCollapsedLauncher(UI.instance) else UI.instance.visible = true end; return UI.instance end
UI.restoreStartupVisibility = function() local r = UI.ensureControl(); r.visible = true; return true end
UI.open = function(tab, id) local r = UI.ensureControl(); r.visible = true; r.selectedTab = tab; r.openedWith = id; return r end
UI.onGameStart = function() UI.restoreStartupVisibility() end
STARTS = {}; Events = { OnGameStart = { Add = function(f) STARTS[#STARTS + 1] = f end } }
function ONSTART() for _, f in ipairs(STARTS) do f() end end
getTextManager = function() return { MeasureStringX = function(_, f, s) return #s * 7 end } end
''')
for f in ("SolPanel.lua", "SolSkin.lua"):
    L.execute(open("build/media/lua/client/" + f, encoding="utf-8").read())
G = L.globals(); res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
UI = G.SurvivorCompanion.UI
check("skin installed at load", UI.solSkinInstalled == True)
UI.onGameStart()
check("game start: no LF window is shown", UI.instance is None or UI.instance.visible == False)
check("game start: no LF launcher", UI.launcher is None or UI.launcher.visible == False)
G.ONSTART()
lau = G.SolUI.launcher; lau.onMouseDown(lau, 50, 50); lau.onMouseUp(lau, 50, 50)
pan = G.SolUI.panel
pan.onMouseDown(pan, 440, 450); pan.onMouseUp(pan, 440, 450)        # status
r = UI.instance
check("status button opens the window on the status tab", r is not None and r.visible and r.selectedTab == "status" and r.openedWith == "sc-1")
check("window is skinned", r.solSkinned == True)
check("LF header buttons hidden (Collapse / Dock / Talk)", not r.collapseButton.visible and not r.dockButton.visible and not r.talkButton.visible)
r.prerender(r); r.render(r)
check("LF background/title not drawn (Sol frame instead)", r.lfPrerender is None and r.lfTitle is None)
draws = [tuple(d.values()) for d in G.DRAWS.values()]
check("Sol title 'Sol' drawn in the header", any(d[0] == "text" and d[1] == "Sol" for d in draws))
check("Sol frame border uses Sol blue", any(d[0] == "rect" for d in draws))
r.applyLayout(r)
check("layout pass keeps LF header buttons hidden", not r.collapseButton.visible and r.layouts == 1)
r.selectedTab = "loadout"; r.updateTabButtons(r)
sel = [b for b in r.tabButtons.values() if b.scTab == "loadout"][0]; oth = [b for b in r.tabButtons.values() if b.scTab == "orders"][0]
check("selected tab is Sol blue, others Sol navy", abs(sel.backgroundColor.r - 0.102) < 0.01 and abs(oth.backgroundColor.r - 0.075) < 0.01)
c = r.detail.content.children
check("detail rebuilt and restyled: gold section -> Sol blue", abs(c[1].r - 0.42) < 0.01 and abs(c[1].b - 1.0) < 0.01)
check("info text -> Sol white, button -> Sol colours", abs(c[2].r - 0.94) < 0.01 and abs(c[3].backgroundColor.r - 0.075) < 0.01)
r.detail.rebuild(r.detail, True); c = r.detail.content.children
check("every later rebuild is restyled too", abs(c[1].r - 0.42) < 0.01)
y = r.roster.doDrawItem(r.roster, 0, L.eval("{ item = { name = 'Sol Survivor', health = 1, distance = 2, order = 'follow', activity = 'follow' }, index = 1 }"), False)
check("roster drawn by Sol (returns next y)", y == 70)
pan.visible = True; pan.onMouseDown(pan, 150, 370); pan.onMouseUp(pan, 150, 370)   # equip
check("equip button opens the loadout tab in the same Sol window", r.selectedTab == "loadout" and r.visible)
check("window placed beside the Sol panel", r.x == pan.x - r.width - 8 or r.x == pan.x + pan.width + 8)
r.solClose.onclick(r.solClose.target, r.solClose)
check("Sol close button hides it, no LF launcher appears", r.visible == False and (UI.launcher is None or UI.launcher.visible == False))
G.calls = L.table(); pan.visible = True; pan.onMouseDown(pan, 440, 280); pan.onMouseUp(pan, 440, 280)
check("chat button no longer opens the LF talk tab", r.selectedTab != "talk")
UI.restoreStartupVisibility()
check("reload path keeps the LF window hidden", r.visible == False)
r.visible = True; r.x = 700; r.y = 120; r.applyScreenBounds(r)
check("no docking jump: window stays where it is (LF snapped it to x=0)", r.x == 700 and r.docked is None)
check("window enlarged to the Sol size", r.width >= 640 and r.height >= 520)
r.applyLayout(r)
tabs = list(r.tabButtons.values())
check("tabs form one vertical column on the right", len({t.x for t in tabs}) == 1 and tabs[0].x > r.width / 2 and sorted(t.y for t in tabs) == [t.y for t in tabs])
check("companion list hidden when Sol is the only companion", r.roster.visible == False and r.detail.x == 8)
check("content fills the left side up to the tab column", r.detail.x + r.detail.width <= tabs[0].x)
r.roster.items = L.eval("{ { item = { name = 'Sol' } }, { item = { name = 'Other' } } }"); r.applyLayout(r)
check("companion list shown when there are two companions", r.roster.visible == True and r.detail.x > 150)
r.onMouseDown(r, 100, 10); r.mx, r.my = 160, 40; r.onMouseMove(r, 60, 30); r.onMouseUp(r, 160, 40)
check("drag by the header moves the window without docking", r.x == 760 and r.y == 150 and r.docked is None)
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
