"""s97 gear_recover offline: SolGearRecover.lua with stand-ins for her body (worn items, hands, inventory, action state), the floor
(squares with world items), Living Fellows (orders, threats, takeWorldItemVerified) and ModData.
Replays the live case: helmet worn, she falls vaulting (falldown), the helmet leaves her (in the air first), lands 2 tiles away;
calm -> she walks there, picks it up and wears it again. Also: danger / sorting -> she waits; a jacket given away (no fall) is not
"lost"; a weapon dropped in a knockdown on her square -> back in her hand; after a reload a remembered item lying near her is taken
back; the switch off = nothing; ModData holds plain values only; installer idempotent; ASCII; tonumber gate.
Run: python test_s97_gear_recover.py [client dir]. Offline PASS is not Runtime PASS."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
tmp = tempfile.mkdtemp(prefix="s97g_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
shutil.copy(os.path.join(CL, "SolAuthority.lua"), cl)
for i in (1, 2):
    r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s97_gear_recover.py"), cl], capture_output=True, text=True)
    ck("installer run %d" % i, r.returncode == 0 and (i == 1 or r.stdout.count("kept") == 2), r.stdout + r.stderr)
A = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8", newline="").read()
ck("switch listed once in A.FIXES", A.count('"gear_recover"') == 1)
G = open(os.path.join(cl, "SolGearRecover.lua"), encoding="utf-8", newline="").read()

ENV = r"""
NOW = 1000
function getTimestampMs() return NOW end
LOGS = {}
function print(m) LOGS[#LOGS + 1] = tostring(m) end
SW = { gear_recover = true }
SolAuthority = { on = function(f) return SW[f] == true end }
local MDS = {}
ModData = { getOrCreate = function(k) MDS[k] = MDS[k] or {}; return MDS[k] end }
MODDATA = MDS
NEXTID = 100
function ITEM(ft, loc, two) NEXTID = NEXTID + 1; local it = { id = NEXTID, ft = ft, loc = loc, two = two }
    function it:getID() return self.id end; function it:getFullType() return self.ft end
    function it:getBodyLocation() return self.loc end; function it:isTwoHandWeapon() return self.two == true end
    function it:isBroken() return false end; return it end
INV = { items = {} }
function INV:contains(it) for _, x in ipairs(self.items) do if x == it then return true end end return false end
function INV:containsRecursive(it) return self:contains(it) end
function INV:containsID(id) for _, x in ipairs(self.items) do if x.id == id then return true end end return false end
function INV:add(it) self.items[#self.items + 1] = it end
function INV:remove(it) for i, x in ipairs(self.items) do if x == it then table.remove(self.items, i) return end end end
WORN = {}
local wornList = {}
function wornList:size() return #WORN end
function wornList:get(i) local w = WORN[i + 1]; return { getItem = function() return w.item end, getLocation = function() return w.loc end } end
SOL = { x = 10.5, y = 10.5, z = 0, inv = INV }
function SOL:getX() return self.x end; function SOL:getY() return self.y end; function SOL:getZ() return self.z end
function SOL:getVehicle() return nil end
function SOL:getInventory() return self.inv end
function SOL:getWornItems() return wornList end
function SOL:getWornItem(loc) for _, w in ipairs(WORN) do if w.loc == loc then return w.item end end return nil end
function SOL:setWornItem(loc, it) for i = #WORN, 1, -1 do if WORN[i].loc == loc then table.remove(WORN, i) end end
    if it then WORN[#WORN + 1] = { loc = loc, item = it } end end
function SOL:getPrimaryHandItem() return self.p end; function SOL:getSecondaryHandItem() return self.s end
function SOL:setPrimaryHandItem(it) self.p = it end; function SOL:setSecondaryHandItem(it) self.s = it end
function SOL:getActionStateName() return STATE or "idle" end
function SOL:resetModelNextFrame() end
-- the floor
FLOOR = {}
local function sqkey(x, y, z) return x .. "," .. y .. "," .. z end
function DROP(it, x, y, z) local k = sqkey(x, y, z or 0); FLOOR[k] = FLOOR[k] or {}; local wo = { item = it, sq = k }
    function wo:getItem() return self.item end; table.insert(FLOOR[k], wo) end
function getCell() return { getGridSquare = function(self, x, y, z)
    local k = sqkey(x, y, z); return { k = k, getWorldObjects = function()
        local l = FLOOR[k] or {}; return { size = function() return #l end, get = function(_, i) return l[i + 1] end } end } end,
    getZombieList = function() return { size = function() return #ZOMBIES end, get = function(_, i) return ZOMBIES[i + 1] end } end } end
ZOMBIES = {}
THREATS = {}
ST = { order = "follow" }
ISSUED = {}
SENT = {}
SORTING = false
SurvivorCompanion = {
    Commands = { peek = function(a) return ST end },
    GameplayUtil = {
        idOf = function(a) return "sc-test-1" end,
        peekActorState = function(a) return { snapshot = { threats = THREATS } } end,
        takeWorldItemVerified = function(wo, inv, item)
            local l = FLOOR[wo.sq] or {}
            for i, x in ipairs(l) do if x == wo then table.remove(l, i); inv:add(item); return true, "taken" end end
            return false, "gone" end,
    },
}
SolUI = { solActor = function() return SOL end, solSortHeld = function() return SORTING end,
    solGoto = function(x, y, z) SENT[#SENT + 1] = x .. "," .. y; ST.order = "move_to"; return true end,
    issueLF = function(o) ISSUED[#ISSUED + 1] = o; ST.order = o end }
Events = nil
"""
def fresh(on=True, pre=""):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV); L.execute(pre); L.execute(G)
    L.execute("SW.gear_recover = %s" % ("true" if on else "false"))
    return L
def logs(L): s = L.eval("LOGS"); return [s[i] for i in range(1, len(s) + 1)]
def run_ms(L, ms, step=250):
    for _ in range(ms // step):
        L.execute("NOW = NOW + %d; SolGearRecover.tick()" % step)
def lst(t): return [t[i] for i in range(1, len(t) + 1)]
WEAR = "HELM = ITEM('Base.Hat_ArmyDesertNew', 'Hat'); INV:add(HELM); SOL:setWornItem('Hat', HELM); JACKET = ITEM('Base.Jacket_ArmyCamoDesertNew', 'Jacket'); INV:add(JACKET); SOL:setWornItem('Jacket', JACKET)"
FALL = "STATE = 'falldown'; SOL:setWornItem('Hat', nil); INV:remove(HELM)"

# 1. the live case: fall, helmet in the air, lands 2 tiles away; calm, following -> walk, pick up, wear, follow again
L = fresh(); L.execute(WEAR); run_ms(L, 1500)
L.execute(FALL); run_ms(L, 1000)
ck("fall: helmet noted lost (after falldown)", any("lost Base.Hat_ArmyDesertNew" in m and "falldown" in m for m in logs(L)), logs(L))
ck("helmet still in the air: no walk yet", lst(L.eval("SENT")) == [])
L.execute("STATE = 'getup'"); run_ms(L, 1000)
L.execute("STATE = 'idle'; DROP(HELM, 11, 12, 0)"); run_ms(L, 2500)
ck("helmet on the floor 2 tiles away, calm, following: she walks to it", lst(L.eval("SENT"))[:1] == ["11,12"], (lst(L.eval("SENT")), logs(L)))
L.execute("SOL.x, SOL.y = 11.5, 11.6"); run_ms(L, 500)
ck("next to it: picked up and worn again", L.eval("SOL:getWornItem('Hat') == HELM") and L.eval("INV:contains(HELM)") and any("picked up" in m and "worn" in m for m in logs(L)), logs(L))
ck("following before -> follows again", lst(L.eval("ISSUED")) == ["follow"], lst(L.eval("ISSUED")))
ck("nothing pending after", L.eval("(function() local n=0 for _ in pairs(SolGearRecover.store(SOL).pending) do n=n+1 end return n end)()") == 0)

# 2. danger or sorting: she waits; when it passes she goes
L = fresh(); L.execute(WEAR); run_ms(L, 1500); L.execute(FALL); run_ms(L, 500); L.execute("STATE = 'idle'; DROP(HELM, 11, 12, 0); THREATS[1] = { distanceSq = 16 }"); run_ms(L, 3000)
ck("a zombie she perceives 4 tiles away: no walk for the helmet", lst(L.eval("SENT")) == [])
L.execute("THREATS[1] = nil; SORTING = true"); run_ms(L, 3000)
ck("sorting: no walk either", lst(L.eval("SENT")) == [])
L.execute("SORTING = false; NOW = NOW + 31000"); run_ms(L, 1000)
ck("calm and free: she goes for it", lst(L.eval("SENT"))[:1] == ["11,12"], lst(L.eval("SENT")))
L = fresh(); L.execute(WEAR); run_ms(L, 1500); L.execute("ST.order = 'base_duty'; " + FALL); run_ms(L, 500); L.execute("STATE = 'idle'; DROP(HELM, 11, 12, 0)"); run_ms(L, 3000)
ck("on base duty: no walk (she would be left standing); next to it she would take it", lst(L.eval("SENT")) == [])

# 3. a jacket that leaves her without a fall (given to him) is not lost
L = fresh(); L.execute(WEAR); run_ms(L, 1500); L.execute("SOL:setWornItem('Jacket', nil); INV:remove(JACKET); DROP(JACKET, 10, 10, 0)"); run_ms(L, 3000)
ck("jacket gone without a fall: not lost, not taken", not any("lost" in m for m in logs(L)) and lst(L.eval("SENT")) == [] and not L.eval("INV:contains(JACKET)"))
L.execute("SOL:setWornItem('Jacket', JACKET)"); run_ms(L, 1500)
# 4. weapon dropped in a knockdown, lying on her square -> back in her hand at once (no walk)
L = fresh(); L.execute("KAT = ITEM('Base.Katana', nil, true); INV:add(KAT); SOL:setPrimaryHandItem(KAT); SOL:setSecondaryHandItem(KAT)"); run_ms(L, 1500)
L.execute("STATE = 'knockeddown'; SOL:setPrimaryHandItem(nil); SOL:setSecondaryHandItem(nil); INV:remove(KAT)"); run_ms(L, 500)
L.execute("STATE = 'idle'; DROP(KAT, 10, 10, 0)"); run_ms(L, 1500)
ck("katana dropped in a knockdown on her square: back in both hands, no walk", L.eval("SOL:getPrimaryHandItem() == KAT and SOL:getSecondaryHandItem() == KAT") and lst(L.eval("SENT")) == [], logs(L))

# 5. after a reload: the store remembers the helmet id; it lies 2 tiles away; she takes it back
PRE = "HELM = ITEM('Base.Hat_ArmyDesertNew', 'Hat'); DROP(HELM, 12, 10, 0); ModData.getOrCreate('SolGearRecover')['sc-test-1'] = { worn = { [tostring(HELM.id)] = { ft = 'Base.Hat_ArmyDesertNew', loc = 'Hat', kind = 'worn' } }, pending = {} }"
L = fresh(pre=PRE); run_ms(L, 2000)
ck("load pass: a remembered helmet of hers lying near her is found", any("load pass: 1 remembered" in m for m in logs(L)), logs(L))
ck("  ... she walks to it", lst(L.eval("SENT"))[:1] == ["12,10"], lst(L.eval("SENT")))
L.execute("SOL.x = 11.5"); run_ms(L, 500)
ck("  ... and wears it again", L.eval("SOL:getWornItem('Hat') == HELM"), logs(L))
L = fresh(pre="OTHER = ITEM('Base.Hat_Beret', 'Hat'); DROP(OTHER, 11, 10, 0)"); run_ms(L, 3000)
ck("load pass: a hat that was never hers is left alone", lst(L.eval("SENT")) == [] and not L.eval("INV:contains(OTHER)"))
# 6. switch off
L = fresh(on=False); L.execute(WEAR); run_ms(L, 1500); L.execute(FALL); run_ms(L, 500); L.execute("STATE = 'idle'; DROP(HELM, 11, 12, 0)"); run_ms(L, 3000)
ck("off: nothing noted, nothing walked", logs(L) == [] and lst(L.eval("SENT")) == [], logs(L))
# 7. ModData plain values only; verb
L = fresh(); L.execute(WEAR); run_ms(L, 1500); L.execute(FALL); run_ms(L, 1500)
bad = L.eval("""(function() local bad = {}
  local function walk(t, path) for k, v in pairs(t) do local tv = type(v)
    if tv == 'table' then walk(v, path .. '.' .. tostring(k)) elseif tv ~= 'string' and tv ~= 'number' and tv ~= 'boolean' then bad[#bad + 1] = path .. '.' .. tostring(k) .. '=' .. tv end end end
  walk(MODDATA, 'MD'); return table.concat(bad, ' ') end)()""")
ck("ModData holds plain values only (no items, no Java objects)", bad == "", bad)
ok, msg = L.eval("SolGearRecover.order('status')")
ck("verb sol_gear status", ok is True and "pending=1" in msg, msg)
L.execute("OTHER = ITEM('Base.Glasses_Normal', 'Eyes'); DROP(OTHER, 10, 11, 0)")
ok, msg = L.eval("SolGearRecover.order('take')")
ck("verb sol_gear take: wearables near her with a free place on her become pending (his order)", ok is True and "pending 1" in msg, msg)

ck("ascii only", all(ord(c) < 128 for c in G))
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
if os.path.exists(GATE):
    r = subprocess.run([sys.executable, GATE, os.path.join(cl, "SolGearRecover.lua")], capture_output=True, text=True)
    ck("tonumber gate", r.returncode == 0, r.stdout[-300:])
else:
    ck("tonumber gate present", False, GATE)
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
