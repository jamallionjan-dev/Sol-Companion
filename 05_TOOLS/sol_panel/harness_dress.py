import sys
from lupa import lua51
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(r'''
local EXIST = { ["Base.Bra_Straps_White"] = true, ["Base.Underpants_White"] = true, ["Base.Socks_Long"] = true, ["Base.Tshirt_White"] = true,
  ["Base.Trousers_Denim"] = true, ["Base.Shoes_Black"] = true }
ScriptManager = { instance = { getItem = function(_, t) return EXIST[t] and {} or nil end } }
function newActor(worn)
  local a = { worn = {}, inv = {}, resets = 0 }
  for _, w in ipairs(worn or {}) do a.worn[#a.worn + 1] = w end
  a.getWornItems = function(self) return { size = function() return #self.worn end } end
  a.getInventory = function(self) return { AddItem = function(_, t) self.inv[#self.inv + 1] = t; return { t = t, getBodyLocation = function() return "loc:" .. t end } end } end
  a.setWornItem = function(self, loc, item) self.worn[#self.worn + 1] = item.t end
  a.resetModelNextFrame = function(self) self.resets = self.resets + 1 end
  return a
end
SOL = newActor()
SolUI = { solActor = function() return SOL end }
TICKS = {}; Events = { OnTick = { Add = function(f) TICKS[#TICKS + 1] = f end } }
local T = 0; function getTimestampMs() return T end; function ADVANCE(ms) T = T + ms end
''')
L.execute(open("build/media/lua/client/SolDress.lua").read())
G = L.globals(); res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
G.ADVANCE(5000); L.execute("TICKS[1]()")
worn = list(G.SOL.worn.values())
check("naked Sol gets one vanilla item per slot (first that exists)", worn == ["Base.Bra_Straps_White", "Base.Underpants_White", "Base.Socks_Long", "Base.Tshirt_White", "Base.Trousers_Denim", "Base.Shoes_Black"])
check("model refreshed once (like LF)", G.SOL.resets == 1)
check("missing items are skipped, not forced", "Base.HoodieDOWN_WhiteTINT" not in list(G.SOL.inv.values()))
G.ADVANCE(5000); L.execute("TICKS[1]()")
check("same actor is not dressed twice", len(list(G.SOL.worn.values())) == 6)
L.execute("SOL = newActor({ 'Base.Dress_Long' })"); G.ADVANCE(5000); L.execute("TICKS[1]()")
check("a Sol who wears anything is left untouched", list(G.SOL.worn.values()) == ["Base.Dress_Long"] and G.SOL.resets == 0)
L.execute("SOL = newActor()"); G.ADVANCE(5000); L.execute("TICKS[1]()")
check("respawned (new) naked Sol is dressed again", len(list(G.SOL.worn.values())) == 6)
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
