DRAWS = {}; LOGS = {}; OPENED = {}; TIME = 1000000
print = function(s) LOGS[#LOGS + 1] = tostring(s) end
require = function() end
UIFont = { Small = "S", Medium = "M", Large = "L" }
local function rec(t) DRAWS[#DRAWS + 1] = t end
ISPanel = {}; ISPanel.__index = ISPanel
function ISPanel:derive(name) local c = {}; setmetatable(c, { __index = self }); c.Type = name; c.__index = c; return c end
function ISPanel:new(x, y, w, h) local o = { x = x, y = y, width = w, height = h, visible = true, mx = 0, my = 0, over = false, children = {} }; setmetatable(o, ISPanel); return o end
function ISPanel:initialise() end
function ISPanel:instantiate() if self.createChildren then self:createChildren() end end
function ISPanel:addToUIManager() self.inUI = true end
function ISPanel:setAlwaysOnTop() end
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
function ISPanel:addChild(c) self.children[#self.children + 1] = c end
function ISPanel:getWidth() return self.width end
function ISPanel:setWidth(v) self.width = v end
function ISPanel:setHeight(v) self.height = v end
function ISPanel:getHeight() return self.height end
function ISPanel:drawRectBorder(x, y, w, h, a, r, g, b) rec({ "border", x, y, w, h, a, r, g, b }) end
function ISPanel:drawTextureScaled(t, x, y, w, h, a) rec({ "tex", t.name, x, y, w, h, a }) end
function ISPanel:drawText(s, x, y, r, g, b, a, f) rec({ "text", s, x, y, false, r, g, b, a }) end
function ISPanel:drawTextRight(s, x, y, r, g, b, a, f) rec({ "text", s, x, y, true, r, g, b, a }) end
function ISPanel:drawRect(x, y, w, h, a, r, g, b) rec({ "rect", x, y, w, h, a, r, g, b }) end
ISTextEntryBox = {}; ISTextEntryBox.__index = ISTextEntryBox
function ISTextEntryBox:new(t, x, y, w, h) local o = { text = t, x = x, y = y, w = w, h = h, visible = true }; setmetatable(o, ISTextEntryBox); return o end
function ISTextEntryBox:initialise() end
function ISTextEntryBox:instantiate() end
function ISTextEntryBox:setMasked(v) self.masked = v end
function ISTextEntryBox:getText() return self.text end
function ISTextEntryBox:setText(t) self.text = t end
function ISTextEntryBox:setVisible(v) self.visible = v end
function ISTextEntryBox:isVisible() return self.visible end
function ISTextEntryBox:getX() return self.x end
function ISTextEntryBox:getY() return self.y end
function ISTextEntryBox:getWidth() return self.w end
function ISTextEntryBox:getHeight() return self.h end
function getTexture(p)
  local n = p:match("SolUI/(.+)%.png$")
  if not TEXOK(n) then return nil end
  return { name = n, getWidth = function() return TEXW(n) end, getHeight = function() return TEXH(n) end }
end
function getFileReader(name, create)
  local f = io.open(LUA_DIR .. name, "r"); if not f then return nil end
  return { readLine = function() return f:read("*l") end, close = function() f:close() end }
end
function getFileWriter(name, create, append)
  local f = io.open(LUA_DIR .. name, append and "a" or "w")
  return { write = function(_, s) f:write(s) end, close = function() f:close() end }
end
function getTimestampMs() return TIME end
local md = {}
local P = { getModData = function() return md end }
function getSpecificPlayer() return P end
function getCore() return { getScreenWidth = function() return 1920 end, getScreenHeight = function() return 1080 end } end
Events = { OnGameStart = { Add = function(f) ONSTART = f end } }
SOL = { name = "sol" }; LIVING = { SOL }
SurvivorCompanion = { Registry = { living = function() return LIVING end, idOf = function() return "sc-1" end }, UI = {
  open = function() end, openInventory = function() end, openHealth = function() end } }
SC_READS = 0
setmetatable(_G, { __index = function(t, k) if k == "SC" then SC_READS = SC_READS + 1 end return nil end })
