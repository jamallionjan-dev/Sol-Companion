"""s84 compat_vp_harvest: SolCompatVP.lua under the game's Lua rules (kahlua_env), the facts it relies on in the game's and the mods'
own files (read only), the tonumber gate, and the installer (idempotent, on a temporary copy). Nothing live is touched.
Run: set PYTHONIOENCODING=utf-8 & python test_s84_compat_vp_harvest.py [client dir]
Offline PASS is not Runtime PASS: the Kahlua pool fault itself cannot be made offline; the replay throws the same error text."""
import os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media\lua"
WS = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\108600"
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
SRC = open(os.path.join(HERE, "SolCompatVP.lua"), encoding="ascii").read()
NPE = ('java.lang.NullPointerException: Cannot assign field "callFrame" because "a" is null at ReturnValues.put(ReturnValues.java:61)')

# ================================================================ facts in the files we hook (read only)
fm = os.path.join(GAME, "client", "Farming", "ISUI", "ISFarmingMenu.lua")
if os.path.exists(fm):
    t = open(fm, encoding="utf-8", errors="replace").read()
    ck("vanilla: predicateDigPlow is 'not isBroken and hasTag(ItemTag.DIG_PLOW)'",
       re.search(r"local function predicateDigPlow\(item\)\s*return not item:isBroken\(\) and item:hasTag\(ItemTag\.DIG_PLOW\)", t) is not None)
    ck("vanilla: getShovel = hand first, then getFirstEvalRecurse(predicateDigPlow)",
       "ISFarmingMenu.getShovel = function(player)" in t and "playerInv:getFirstEvalRecurse(predicateDigPlow)" in t)
    calls = re.findall(r"ISFarmingMenu\.getShovel\(", t)
    ck("vanilla: every caller goes through the table field (so the wrap reaches doDigMenu and doFarmingMenu2)", len(calls) >= 4 and "local getShovel" not in t, len(calls))
else:
    print("SKIP vanilla ISFarmingMenu.lua not found")
qol = None
for root, _, files in os.walk(WS):
    if "ProjectViewpointQOL.lua" in files and os.path.join("mods", "ProjectViewpointQOL", "42") in root:
        qol = os.path.join(root, "ProjectViewpointQOL.lua"); break
if qol:
    t = open(qol, encoding="utf-8", errors="replace").read()
    ck("PV QOL: harvestFailed asks ProjectViewpointQOL.isKnownHarvestError by table lookup (so the wrap is seen)",
       "if ProjectViewpointQOL.isKnownHarvestError(err) then" in t and "function ProjectViewpointQOL.isKnownHarvestError(err)" in t)
    ck("PV QOL: its own filter does not know the callFrame error (why the gather was re-raised)",
       "callFrame" not in t[t.find("function ProjectViewpointQOL.isKnownHarvestError"):t.find("function ProjectViewpointQOL.isKnownHarvestError") + 600])
else:
    print("SKIP ProjectViewpointQOL.lua not found")

# ================================================================ Lua
ENV = r"""
LOGS = {}
function print(m) LOGS[#LOGS + 1] = tostring(m) end
SWITCH = true
SolAuthority = { on = function(f) if f ~= "compat_vp_harvest" then error("wrong switch " .. tostring(f)) end; return SWITCH end }
ItemTag = { DIG_PLOW = "DIG_PLOW" }
function list(t) return { size = function(self) return #t end, get = function(self, i) return t[i + 1] end } end
function mkitem(name, tags, broken, inner)
    local it = { name = name, tags = tags or {}, broken = broken == true, inner = inner }
    function it:isBroken() return self.broken end
    function it:hasTag(tag) CALLS = CALLS + 1; return self.tags[tag] == true end
    function it:getInventory() return self.inner end
    return it
end
function mkcont(items) local c = { items = items }; function c:getItems() return list(self.items) end; return c end
function instanceof(o, cls) return cls == "InventoryContainer" and type(o) == "table" and o.inner ~= nil end
function mkplayer(hand, inv) return { getPrimaryHandItem = function() return hand end, getInventory = function() return inv end } end
CALLS = 0
VANILLA_MODE = "ok"
VANILLA_CALLS = 0
ISFarmingMenu = {}
ISFarmingMenu.getShovel = function(player)                  -- the stand-in for the vanilla body: hand, then getFirstEvalRecurse
    VANILLA_CALLS = VANILLA_CALLS + 1
    if VANILLA_MODE == "npe" then error("Exception thrown " .. NPE) end
    local h = player:getPrimaryHandItem()
    if h and not h:isBroken() and h:hasTag(ItemTag.DIG_PLOW) then return h end
    return "VANILLA_RESULT"
end
-- the stand-in for PV QOL's guard (ProjectViewpointQOL.lua 5609-5638): its filter, harvestFailed and guardHarvest
ProjectViewpointQOL = {}
function ProjectViewpointQOL.isKnownHarvestError(err)
    local msg = tostring(err or "")
    return msg:find("spriteName", 1, true) ~= nil or msg:find("ISWorldObjectContextMenuLogic", 1, true) ~= nil or msg:find("inventoryPane", 1, true) ~= nil
end
function harvestFailed(err)
    if ProjectViewpointQOL.isKnownHarvestError(err) then return { why = "known vanilla harvest bug" } end
    error(err)
end
function guardHarvest(fn, ...)
    local results = { pcall(fn, ...) }
    if not results[1] then return harvestFailed(results[2]) end
    return unpack(results, 2, #results)
end
HOOKS = {}
Events = { OnGameStart = { Add = function(f) HOOKS[#HOOKS + 1] = f end } }
function require() end
"""
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("NPE = %s" % ('"' + NPE.replace('"', '\\"') + '"'))
L.execute(ENV)
L.execute(SRC)
g = L.globals()
M = g.SolCompatVP
ck("lua: loads, one OnGameStart hook", len(list(g.HOOKS.values())) == 1 and M.VERSION == "0.1.0")
L.execute("for _, f in ipairs(HOOKS) do f() end")
ck("install: getShovel wrapped, PV QOL filter wrapped, one ready line", L.eval("ISFarmingMenu.getShovel == SolCompatVP.getShovel") and L.eval("ProjectViewpointQOL._solCompatVP == true")
   and sum(1 for v in g.LOGS.values() if "ready v0.1.0" in v) == 1)
L.execute("SolCompatVP.install(); SolCompatVP.install()")
ck("install: twice keeps one wrap (the vanilla body is still M._orig)", L.eval("SolCompatVP._orig ~= SolCompatVP.getShovel") and L.eval("ISFarmingMenu.getShovel == SolCompatVP.getShovel"))

def ev(s): return L.eval(s)
L.execute("""
SHOVEL = mkitem("Shovel", { DIG_PLOW = true })
BROKEN = mkitem("Shovel(broken)", { DIG_PLOW = true }, true)
TROWEL = mkitem("Trowel", { DIG_PLOW = true })
AXE = mkitem("Axe", {})
""")
ck("scan: the hand item first", ev("ISFarmingMenu.getShovel(mkplayer(SHOVEL, mkcont({ TROWEL }))) == SHOVEL"))
ck("scan: a broken hand item is passed over, the bag's one is found", ev("ISFarmingMenu.getShovel(mkplayer(BROKEN, mkcont({ AXE, TROWEL }))) == TROWEL"))
ck("scan: inside a backpack inside a bag", ev("ISFarmingMenu.getShovel(mkplayer(nil, mkcont({ AXE, mkitem('Bag', {}, false, mkcont({ mkitem('Pack', {}, false, mkcont({ BROKEN, TROWEL })) })) }))) == TROWEL"))
ck("scan: breadth first: her own items before the bags'", ev("ISFarmingMenu.getShovel(mkplayer(nil, mkcont({ mkitem('Bag', {}, false, mkcont({ SHOVEL })), TROWEL }))) == TROWEL"))
ck("scan: nothing to dig with -> nil, and the vanilla body is not called", ev("(function() VANILLA_CALLS = 0; local r = ISFarmingMenu.getShovel(mkplayer(nil, mkcont({ AXE, BROKEN }))); return r == nil and VANILLA_CALLS == 0 end)()"))
# the live fault: the vanilla body throws the NPE. With the guard it is never reached on a normal walk.
L.execute("VANILLA_MODE = 'npe'")
ck("replay 23:05:59: the vanilla body would throw; the guarded getShovel answers from Lua and never calls it",
   ev("(function() VANILLA_CALLS = 0; local ok, r = pcall(ISFarmingMenu.getShovel, mkplayer(nil, mkcont({ TROWEL }))); return ok and r == TROWEL and VANILLA_CALLS == 0 end)()"))
L.execute("ItemTag = nil")
ck("no ItemTag (older build): the vanilla body under pcall; it throws -> nil, no exception, one log line",
   ev("(function() local ok, r = pcall(ISFarmingMenu.getShovel, mkplayer(nil, mkcont({ TROWEL }))); return ok and r == nil and SolCompatVP.stats.errors == 1 end)()")
   and sum(1 for v in g.LOGS.values() if "vanilla call failed too" in v) == 1)
L.execute("VANILLA_MODE = 'ok'")
ck("no ItemTag, vanilla works: its answer is used", ev("ISFarmingMenu.getShovel(mkplayer(nil, mkcont({ TROWEL }))) == 'VANILLA_RESULT'"))
L.execute("ItemTag = { DIG_PLOW = 'DIG_PLOW' }; SolCompatVP.MAX_ITEMS = 3")
ck("a huge inventory: the walk stops at MAX_ITEMS and the vanilla answer is used",
   ev("ISFarmingMenu.getShovel(mkplayer(nil, mkcont({ AXE, AXE, AXE, AXE, AXE, TROWEL }))) == 'VANILLA_RESULT'"))
L.execute("SolCompatVP.MAX_ITEMS = 4000")
L.execute("ODD = mkitem('Odd', {}); function ODD:hasTag() error('boom') end")
ck("an item whose hasTag throws is skipped, the next one found", ev("ISFarmingMenu.getShovel(mkplayer(nil, mkcont({ ODD, TROWEL }))) == TROWEL"))
# switch off: exactly vanilla
L.execute("SWITCH = false; VANILLA_CALLS = 0")
ck("switch off: the vanilla body, directly", ev("ISFarmingMenu.getShovel(mkplayer(nil, mkcont({ TROWEL }))) == 'VANILLA_RESULT' and VANILLA_CALLS == 1"))
L.execute("VANILLA_MODE = 'npe'")
ck("switch off: its exception passes through as before", ev("(pcall(ISFarmingMenu.getShovel, mkplayer(nil, mkcont({ TROWEL }))))") is False)
L.execute("VANILLA_MODE = 'ok'; SWITCH = true")

# PV QOL's guard with the wrapped filter
L.execute("function GATHER_NPE() error('Exception thrown ' .. NPE) end; function GATHER_OTHER() error('something else entirely') end")
ck("replay: the callFrame error in a gather -> their guard returns 'nothing gathered' (no re-raise)",
   ev("(function() local ok, r = pcall(guardHarvest, GATHER_NPE); return ok and type(r) == 'table' and r.why == 'known vanilla harvest bug' end)()"))
ck("their own known errors still known", ev("ProjectViewpointQOL.isKnownHarvestError('x spriteName y') == true"))
ck("any other error is still raised", ev("(pcall(guardHarvest, GATHER_OTHER))") is False)
L.execute("SWITCH = false")
ck("switch off: the callFrame error is raised as before", ev("(pcall(guardHarvest, GATHER_NPE))") is False)
L.execute("SWITCH = true")
L.execute("ProjectViewpointQOL = nil; ISFarmingMenu = nil; SolCompatVP._logged = nil; LOGS = {}")
ck("neither mod nor vanilla table present: install does nothing and says so", ev("(pcall(SolCompatVP.install))") is True and any("absent" in v for v in g.LOGS.values()))

# ================================================================ the tonumber gate
if os.path.exists(GATE):
    r = subprocess.run([sys.executable, GATE, os.path.join(HERE, "SolCompatVP.lua")], capture_output=True, text=True)
    ck("tonumber gate: SolCompatVP.lua clean", r.returncode == 0, (r.stdout + r.stderr)[-300:])
else:
    print("SKIP tonumber gate not found")
ck("ascii only", all(ord(c) < 128 for c in SRC))

# ================================================================ the installer on a temporary copy
if os.path.isfile(os.path.join(CL, "SolAuthority.lua")):
    tmp = tempfile.mkdtemp(prefix="s84_")
    try:
        cl = os.path.join(tmp, "client")
        os.makedirs(cl)
        for f in ("SolAuthority.lua", "SolActions.lua"): shutil.copy(os.path.join(CL, f), cl)
        run = lambda: subprocess.run([sys.executable, os.path.join(HERE, "apply_s84_compat_vp_harvest.py"), cl], capture_output=True, text=True)
        r1 = run(); a1 = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8", newline="").read()
        r2 = run(); a2 = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8", newline="").read()
        ck("installer: runs, copies SolCompatVP.lua, adds the switch once", r1.returncode == 0 and os.path.exists(os.path.join(cl, "SolCompatVP.lua"))
           and a1.count('"compat_vp_harvest"') == 1, r1.stdout + r1.stderr)
        ck("installer: second run changes nothing", r2.returncode == 0 and a1 == a2 and "kept" in r2.stdout, r2.stdout + r2.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
else:
    print("SKIP installer: no client dir at " + CL)

print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
