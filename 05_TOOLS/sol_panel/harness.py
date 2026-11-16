import os, sys
from lupa import lua51
from PIL import Image
L = lua51.LuaRuntime(unpack_returned_tuples=True)
STUB = r'''
calls = {}; draws = {}; logs = {}
local _print = print
print = function(s) logs[#logs+1] = tostring(s) end
ISUIElement = {}
ISPanel = {}
ISPanel.__index = ISPanel
function ISPanel:derive(name) local c = {}; setmetatable(c, {__index = self}); c.Type = name; c.__index = c; return c end
function ISPanel:new(x, y, w, h) local o = {x=x, y=y, width=w, height=h, visible=true, mx=0, my=0, over=false}; setmetatable(o, ISPanel); return o end
function ISPanel:initialise() end
function ISPanel:instantiate() end
function ISPanel:addToUIManager() self.inUI = true end
function ISPanel:setAlwaysOnTop(v) end
function ISPanel:bringToTop() end
function ISPanel:setVisible(v) self.visible = v end
function ISPanel:isVisible() return self.visible end
function ISPanel:getX() return self.x end
function ISPanel:getY() return self.y end
function ISPanel:setX(v) self.x = v end
function ISPanel:setY(v) self.y = v end
function ISPanel:getMouseX() return self.mx end
function ISPanel:getMouseY() return self.my end
function ISPanel:isMouseOver() return self.over end
function ISPanel:drawTextureScaled(t, x, y, w, h, a) draws[#draws+1] = {t.name, x, y, w, h, a} end
TEXDIR = ""
function getTexture(p) local name = p:match("SolUI/(.+)%.png$"); if TEXOK(name) then return {name=name} end return nil end
local md = {}
local P = {getModData = function() return md end}
function getSpecificPlayer(i) return P end
function getCore() return {getScreenWidth=function() return 1920 end, getScreenHeight=function() return 1080 end} end
Events = {OnGameStart = {Add = function(f) ONSTART = f end}}
SOL = {name="sol-actor"}
LIVING = {SOL}
SurvivorCompanion = {Registry = {living = function() return LIVING end, idOf = function(a) return "sc-1" end},
      UI = {}}
for _, n in ipairs({"open", "openInventory", "openHealth"}) do
  SurvivorCompanion.UI[n] = function(...) local a = {...}; local s = n; for i=1,#a do s = s .. "|" .. tostring(type(a[i])=="table" and (a[i].name or "tbl") or a[i]) end; calls[#calls+1] = s; return true end
end
'''
L.globals()['TEXOK'] = lambda n: os.path.exists(f"build/media/textures/SolUI/{n}.png")
L.execute(STUB)
# strict: the real game has NO global SC (LF uses local SC = SurvivorCompanion)
L.execute("SC_READS = 0; setmetatable(_G, {__index = function(t, k) if k == 'SC' then SC_READS = SC_READS + 1 end return nil end})")
src = open("build/media/lua/client/SolPanel.lua", encoding="utf-8").read()
L.execute(src)
G = L.globals()
results = []
def check(name, cond): results.append((name, bool(cond))); print(("PASS " if cond else "FAIL ") + name)

G.ONSTART()
lau = G.SolUI.launcher
check("launcher created on game start", lau is not None and lau.inUI)
# click (no movement) toggles panel
lau.onMouseDown(lau, 60, 60); lau.onMouseUp(lau, 60, 60)
pan = G.SolUI.panel
check("click on launcher opens panel", pan is not None and pan.visible)

def render(obj):
    G.draws = L.table(); obj.prerender(obj); return [tuple(d.values()) for d in G.draws.values()]

def composite(dlist, w, h, path, bg=(52,77,58,255)):
    im = Image.new("RGBA", (w, h), bg)
    for name, x, y, ww, hh, a in dlist:
        t = Image.open(f"build/media/textures/SolUI/{name}.png").convert("RGBA").resize((int(ww), int(hh)))
        if a < 1: t.putalpha(t.getchannel("A").point(lambda v: int(v*a)))
        im.alpha_composite(t, (int(x), int(y)))
    im.save(path)

dl = render(pan)
missing = [d[0] for d in dl if not os.path.exists(f"build/media/textures/SolUI/{d[0]}.png")]
check("panel draws only existing textures", not missing)
check("no missing-texture log", not any("missing texture" in v for v in G.logs.values()))
# screen preview: launcher + panel at its position
screen = Image.new("RGBA", (1920, 1080), (52,77,58,255))
composite(render(lau), 134, 166, "/tmp/lau.png"); composite(dl, 600, 598, "/tmp/pan.png")
# hover preview over "bag"
pan.over = True; pan.mx, pan.my = 400, 360
composite(render(pan), 600, 598, "/tmp/pan_hover.png")
check("hover draws highlight on bag", any(d[0] == "btn_hover" and d[1] == 310 and d[2] == 332 for d in render(pan)))
pan.over = False

def click(x, y): pan.onMouseDown(pan, x, y); pan.onMouseUp(pan, x, y)
expect = {"more (was tasks)": (440, 540, "open|more|sc-1"), "bag": (440, 370, "open"+"Inventory|sol-actor|tbl"),
          "status": (440, 450, "open|status|sc-1"), "orders": (150, 450, "open|orders|sc-1"),
          "equip": (150, 370, "open|loadout|sc-1")}
for k, (x, y, want) in expect.items():
    G.calls = L.table(); click(x, y); got = list(G.calls.values())
    check(f"button {k} -> {want}", got == [want])
for k, (x, y) in {"chat (opens Sol chat, never LF talk)": (440, 280), "voice": (150, 280), "settings": (150, 540), "gear": (30, 25)}.items():
    G.calls = L.table(); click(x, y)
    check(f"{k} disabled: no call", len(G.calls) == 0)
click(500, 28); check("EN toggle", G.SolUI.lang() == "en")
composite(render(pan), 600, 598, "/tmp/pan_en.png")
click(420, 28); check("AR toggle", G.SolUI.lang() == "ar")
# no Sol: buttons ignored, status off
L.execute("LIVING = {}")
G.calls = L.table(); click(440, 370)
check("no Sol: bag ignored", len(G.calls) == 0)
dl2 = render(pan); check("no Sol: grey status + dimmed buttons", any(d[0]=="status_off_ar" for d in dl2) and any(d[0]=="btn_bag_ar" and d[5] < 1 for d in dl2) and any(d[0]=="btn_chat_ar" and d[5] == 1 for d in dl2))
composite(dl2, 600, 598, "/tmp/pan_nosol.png")
L.execute("LIVING = {SOL, {name='other'}}")
G.calls = L.table(); click(440, 370); check("two companions: ignored (same rule as SCAIRuntime)", len(G.calls) == 0)
L.execute("LIVING = {SOL}")
# action exception is contained
L.execute("SurvivorCompanion.UI.open = function() error('boom') end")
click(440, 450); check("exception in action is caught and logged", any("failed" in v for v in G.logs.values()))
# header drag moves panel, then click on close hides
pan.onMouseDown(pan, 200, 20); pan.mx, pan.my = 260, 60; pan.onMouseMove(pan, 60, 40); pan.onMouseUp(pan, 260, 60)
check("header drag moves panel", pan.x != 660 or pan.y != 241)
click(570, 28); check("close hides panel", not pan.visible)
# launcher drag does not toggle
lau.onMouseDown(lau, 60, 60); lau.mx, lau.my = 90, 80; lau.onMouseMove(lau, 30, 20); lau.onMouseUp(lau, 90, 80)
check("launcher drag does not open panel", not pan.visible)
lau.mx, lau.my = 0, 0
lau.onMouseDown(lau, 60, 60); lau.onMouseUp(lau, 60, 60); check("launcher click reopens", pan.visible)
s = Image.new("RGBA", (1920,1080), (52,77,58,255)); s.alpha_composite(Image.open("/tmp/lau.png"), (70,20)); s.alpha_composite(Image.open("/tmp/pan.png"), (660,241)); s.convert("RGB").save("/tmp/preview_screen.png")
check("panel never reads an undefined global SC", L.eval("rawget(_G, 'SC_READS')") == 0)
print("logs:", list(G.logs.values()))
fails = [n for n, ok in results if not ok]; print(f"{len(results)-len(fails)}/{len(results)} PASS")
sys.exit(1 if fails else 0)
