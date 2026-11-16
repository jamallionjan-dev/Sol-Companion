"""s103 parts_delivery offline. EFZ's real TW/Core + TW/Data + TW/Builds (Workshop, read-only), the real stored loadout
(Zomboid/Lua/Sol_SecretLoadout.txt) through the real SolSecretLoadout, on the B42-faithful HandWeapon fake (s103_fakes.lua,
OnCreate = createDefault). Shows: the player gets 2 bare receivers + every build part loose + 2 empty magazines, once;
EFZ's rules can assemble each build from those loose parts on the bare receiver; second load / switch off give nothing.
Run: python test_s103_parts_delivery.py [client dir]"""
import os, sys, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kahlua_env import lua51
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
SHARED = os.path.join(CL, "..", "shared")
EFZ = r"C:/Program Files (x86)/Steam/steamapps/workshop/content/108600/3824755284/mods/EscapeFromZomboidFirearms/42/media/lua/shared/"
LOADOUT = os.path.join(HERE, "..", "profile", "Zomboid", "Lua", "Sol_SecretLoadout.txt")
FAIL, P = [], []
def ck(n, c, d=""): print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else "")); (P if c else FAIL).append(n)
tmp = tempfile.mkdtemp(prefix="s103pd_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
for f in os.listdir(CL):
    if f.endswith(".lua"): shutil.copy(os.path.join(CL, f), cl)
for f in ("SolWeaponPick.lua", "SolMagFill.lua"):
    if os.path.exists(os.path.join(HERE, f)): shutil.copy(os.path.join(HERE, f), cl)   # the staged s99 fix, as it will be installed
r1 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s103_parts_delivery.py"), cl], capture_output=True, text=True)
r2 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s103_parts_delivery.py"), cl], capture_output=True, text=True)
ck("installer runs", r1.returncode == 0 and "applied" in r1.stdout, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout, r2.stdout + r2.stderr)
L = lua51.LuaRuntime()
comp = L.eval("function(s) local f, e = loadstring(s); return f ~= nil, e end")
for f in ("SolPartsDelivery.lua", "SolKitBare.lua", "SolAuthority.lua"):
    src = open(os.path.join(cl, f), encoding="utf-8").read()
    ok, e = comp(src); ck("compiles " + f, ok, e)
    ck("ascii " + f, all(ord(c) < 128 for c in src))
ck("switch listed in SolAuthority", '"parts_delivery"' in open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read())

def P_(s): return s.replace("\\", "/")
L.execute('package.path = [[%s/?.lua;%s/?.lua;%s?.lua]]' % (P_(cl), P_(os.path.abspath(SHARED)), EFZ))
L.execute('''
TICKS = {}
Events = setmetatable({}, {__index = function(t, k) local e = {Add = function(f) TICKS[#TICKS + 1] = f end, Remove = function(f) REMOVED = (REMOVED or 0) + 1 end}; rawset(t, k, e); return e end})
NOW = 100000; getTimestampMs = function() return NOW end; isClient = function() return false end; isServer = function() return false end
SW = { parts_delivery = true, secret_loadout = true }
SolAuthority = { on = function(n) return SW[n] == true end }
LINES = {}
function getFileReader(name) local i = 0; return { readLine = function() i = i + 1; return LINES[i] end, close = function() end } end
''')
L.execute(open(os.path.join(HERE, "s103_fakes.lua"), encoding="utf-8").read())
for f in ("SolKitBare.lua", "SolSecretLoadout.lua", "SolPartsDelivery.lua"):
    L.execute(open(os.path.join(cl, f), encoding="utf-8").read())
lines = open(LOADOUT, encoding="utf-8").read().splitlines()
for i, l in enumerate(lines): L.eval("function(i, s) LINES[i] = s end")(i + 1, l)
L.execute('''
function newPlayer() local inv = container("jamal"); local md = {}
    return { getInventory = function() return inv end, getModData = function() return md end, getUsername = function() return "Jamal" end,
             getPrimaryHandItem = function() return nil end, getSecondaryHandItem = function() return nil end, inv = inv, md = md } end
PL = newPlayer(); getSpecificPlayer = function() return PL end
RECS = SolSecretLoadout.loadout()
function count(inv, pred) local n = 0; for _, it in ipairs(inv.items) do if pred(it) then n = n + 1 end end return n end
function isWeapon(it) return it.cls == "HandWeapon" end
function isMag(it) return it.cls == "WeaponPart" and TWRuntime.meta(it) ~= nil and EFZC.isClip(TWRuntime.meta(it).tpl) end
function isLoose(it) return it.cls == "WeaponPart" and not isMag(it) end
''')
L.execute('OK1, WHY1 = SolPartsDelivery.deliver()')
ck("first load delivers", L.eval('OK1') is True, L.eval('tostring(WHY1)'))
ck("two weapons: one HK G28, one Colt M4A1", L.eval('''count(PL.inv, function(it) return it.t == "EscapeFromZomboidFirearms.G28" end) == 1
    and count(PL.inv, function(it) return it.t == "EscapeFromZomboidFirearms.M4A1" end) == 1'''))
ck("both weapons BARE: no part, no magazine, no round", L.eval('''count(PL.inv, function(it) return isWeapon(it) and #it.list == 0 and not it:isContainsClip()
    and it:getCurrentAmmoCount() == 0 and not it:isRoundChambered() and it.md.AmmoList == nil end) == 2'''))
ck("EFZ state of the bare weapons: refreshed, not ready (needs assembly), no hands touched", L.eval('''count(PL.inv, function(it) return isWeapon(it) and it.md.TW ~= nil and it.md.TW.ready == false end) == 2 and UNEQUIPPED == nil'''))
# every part of both builds, loose
exp = {}
for i in (1, 2):
    parts = L.eval('RECS[%d].parts' % i).split(","); mag = L.eval('RECS[%d].mag' % i)
    exp[i] = sorted(p for p in parts if p != mag)
got = sorted(L.eval('(function() local t = {}; for _, it in ipairs(PL.inv.items) do if isLoose(it) then t[#t + 1] = it.t end end return table.concat(t, ",") end)()').split(","))
ck("every build part delivered once as a loose item (%d = %d + %d)" % (len(got), len(exp[1]), len(exp[2])), got == sorted(exp[1] + exp[2]), (len(got), len(exp[1] + exp[2])))
ck("loose parts carry no TWPath (EFZ's loose rule, TWRuntime.looseParts)", L.eval('count(PL.inv, function(it) return isLoose(it) and it.md.TWPath ~= nil end)') == 0)
ck("one EMPTY magazine per gun, of the build's type", L.eval('''count(PL.inv, function(it) return it.t == RECS[1].mag and it:getCurrentAmmoCount() == 0 and it.md.AmmoList == nil end) == 1
    and count(PL.inv, function(it) return it.t == RECS[2].mag and it:getCurrentAmmoCount() == 0 and it.md.AmmoList == nil end) == 1'''))
total = L.eval('#PL.inv.items')
ck("total items = 2 weapons + %d parts + 2 magazines" % (len(exp[1]) + len(exp[2])), total == 2 + len(exp[1]) + len(exp[2]) + 2, total)
# EFZ's own rules accept the kit: from an empty tree, each build is installable from the loose parts the player has
assemble = L.eval('''(function()
    local B = require("TW/Builds"); local out = {}
    local loose = TWRuntime.looseParts(PL)
    for i = 1, 2 do
        local key, build = B.decode(RECS[i].code)
        local tree, paths = {}, {}
        for p, tpl in pairs(build) do if not EFZC.isClip(tpl) then paths[#paths + 1] = p end end
        table.sort(paths, function(a, b) if EFZC.depth(a) ~= EFZC.depth(b) then return EFZC.depth(a) < EFZC.depth(b) end return a < b end)
        for _, p in ipairs(paths) do
            local tpl = build[p]
            if not (loose[tpl] and #loose[tpl] > 0) then return "no loose " .. tpl end
            table.remove(loose[tpl], 1)
            local nt, why = EFZC.install(key, tree, p, tpl)
            if not nt then return "refused " .. p .. " " .. tostring(why) end
            tree = nt
        end
        out[#out + 1] = key
    end
    return table.concat(out, ",")
end)()''')
ck("EFZ C.install assembles both builds on the bare receivers from the delivered loose parts", assemble == "G28,M4A1", assemble)
ck("flag in the player's modData", L.eval('type(PL.md.SolPartsDelivery) == "table" and PL.md.SolPartsDelivery.items == #PL.inv.items'))
# second load: nothing
L.execute('N1 = #PL.inv.items; OK2, WHY2 = SolPartsDelivery.deliver()')
ck("second load gives nothing", L.eval('OK2 == false and WHY2 == "done" and #PL.inv.items == N1'))
# switch off: nothing, no flag
L.execute('SW.parts_delivery = false; PL2 = newPlayer(); OK3, WHY3 = SolPartsDelivery.deliver(PL2)')
ck("switch off gives nothing and sets no flag", L.eval('OK3 == false and WHY3 == "off" and #PL2.inv.items == 0 and PL2.md.SolPartsDelivery == nil'))
# the game-start path: OnGameStart -> install -> OnTick delivers once and unhooks
L.execute('SW.parts_delivery = true; PL = newPlayer(); TICKS = {}; REMOVED = 0; SolPartsDelivery._installed = nil; SolPartsDelivery.install()')
L.execute('for k = 1, 5 do NOW = NOW + 2500; for _, f in ipairs(TICKS) do f() end end')
ck("game start: delivered by the tick once, then the tick unhooks", L.eval('PL.md.SolPartsDelivery ~= nil and REMOVED >= 1 and #PL.inv.items == N1'))
L.execute('NOW = NOW + 2500; for _, f in ipairs(TICKS) do f() end')
ck("game start: later ticks give nothing", L.eval('#PL.inv.items == N1'))
# no loadout: no flag (it will try again on a later load)
L.execute('PL3 = newPlayer(); local S = SolSecretLoadout; local keep = S.loadout; S.loadout = function() return nil end; OK4, WHY4 = SolPartsDelivery.deliver(PL3); S.loadout = keep')
ck("no stored loadout: nothing, no flag", L.eval('OK4 == false and WHY4 == "no_loadout" and PL3.md.SolPartsDelivery == nil'))
G = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua")
r = subprocess.run([sys.executable, "-I", os.path.join(G, "tonumber_check.py"), cl], capture_output=True, text=True); ck("tonumber gate", r.returncode == 0, r.stdout[-300:])
r = subprocess.run([sys.executable, "-I", os.path.join(G, "jarcall_check.py"), cl], capture_output=True, text=True); ck("jarcall gate", r.returncode == 0, r.stdout[-400:])
print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(P), len(FAIL))); sys.exit(1 if FAIL else 0)
