"""s104 shooting_discipline offline (kahlua_env). Fakes follow B42 bytecode (javap, projectzomboid.jar 42.22.2):
IsoGameCharacter.updateAimingDelay  aimingDelay -= 0.625 * mult * (1 + 0.05 * Aiming [+0.1 Marksman]) while aiming and
                                    recoilDelay <= 0; not aiming -> resetAimingDelay = weapon AimingTime
CombatManager.setAimingDelay        after a shot: + RecoilDelay * 0.25 + AimingTime * 0.05, clamped to [0, AimingTime]
CombatManager.calculateAttackVars   a ranged weapon in "Auto" sets no recoil delay
Shows: switch off = pass-through; Auto -> Single; the aim gate holds on moving / aimingDelay / minimum wait and lets the
shot go when settled or after the timeout; point blank fires at once; effective range; per-target cap; burst for a group;
reserve magazine; tactical reload; threats nearest Jamal first; a 6 s replay of the live dump (old cadence vs new);
the installed hook lines run with SCCombat's own locals; installer idempotent; gates.
Run: python test_s104_shooting_discipline.py [client dir]"""
import os, sys, shutil, subprocess, tempfile, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kahlua_env import lua51
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
FAIL, P = [], []
def ck(n, c, d=""): print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else "")); (P if c else FAIL).append(n)
tmp = tempfile.mkdtemp(prefix="s104sd_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
for f in os.listdir(CL):
    if f.endswith(".lua"): shutil.copy(os.path.join(CL, f), cl)
r1 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s104_shooting_discipline.py"), cl], capture_output=True, text=True)
r2 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s104_shooting_discipline.py"), cl], capture_output=True, text=True)
ck("installer runs", r1.returncode == 0 and "applied" in r1.stdout, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout, r2.stdout + r2.stderr)
L = lua51.LuaRuntime()
comp = L.eval("function(s) local f, e = loadstring(s); return f ~= nil, e end")
for f in ("SolShootDiscipline.lua", "SCCombat.lua", "SolAuthority.lua"):
    src = open(os.path.join(cl, f), encoding="utf-8").read()
    ok, e = comp(src); ck("compiles " + f, ok, e)
    ck("ascii " + f, all(ord(c) < 128 for c in src))
combat = open(os.path.join(cl, "SCCombat.lua"), encoding="utf-8").read()
ck("SCCombat carries 5 s104 hooks", combat.count("-- s104 shooting_discipline") == 5, combat.count("-- s104 shooting_discipline"))
ck("SolAuthority lists shooting_discipline", '"shooting_discipline"' in open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read())

L.execute('''
SW = { shooting_discipline = true, mag_fill = false }
SolAuthority = { on = function(n) return SW[n] == true end }
NOW = 0; getTimestampMs = function() return NOW end
LOG = {}; local rawPrint = print; print = function(s) LOG[#LOG + 1] = tostring(s) end
MOVES = {}
SurvivorCompanion = { GameplayUtil = { move = function(a, mode, intent) MOVES[#MOVES + 1] = intent.action; a.aiming = true; a.moving = false; return true, "ok" end } }
function jlist(t) return { size = function(self) return #t end, get = function(self, i) return t[i + 1] end } end
function gun(o)
    o = o or {}
    local g = { mode = o.mode or "Auto", modes = o.modes or { "Auto", "Single" }, sight = o.sight or 10, aimTime = o.aimTime or 40,
        recoil = o.recoil or 15, mag = o.mag or "Base.556Clip", full = "EscapeFromZomboidFirearms.M4A1" }
    function g:isRanged() return true end
    function g:getFireMode() return self.mode end
    function g:setFireMode(m) assert(type(m) == "string", "setFireMode(String) only"); self.mode = m end
    function g:getFireModePossibilities() return jlist(self.modes) end
    function g:getMaxSightRange(...) assert(select("#", ...) == 0, "no-arg overload only"); return self.sight end
    function g:getAimingTime() return self.aimTime end
    function g:getMagazineType() return self.mag end
    function g:getFullType() return self.full end
    return g
end
function zed(x, y, o)
    o = o or {}
    local z = { x = x, y = y, dead = false, floor = o.floor or false }
    function z:getX() return self.x end
    function z:getY() return self.y end
    function z:isDead() return self.dead end
    function z:isOnFloor() return self.floor end
    function z:isProne() return false end
    function z:isCrawling() return false end
    return z
end
function inventory(mags)
    local inv = { mags = mags or {} }
    function inv:getAllTypeRecurse(t) assert(type(t) == "string"); local out = {}
        for _, m in ipairs(self.mags) do out[#out + 1] = { n = m, getCurrentAmmoCount = function(s) return s.n end } end
        return jlist(out) end
    return inv
end
function sol(o)
    o = o or {}
    local a = { x = 0, y = 0, aiming = false, moving = o.moving or false, delay = o.delay or 40, moved = o.moved or 0,
        hand = o.hand, inv = o.inv or inventory({ 30, 30 }) }
    function a:getX() return self.x end
    function a:getY() return self.y end
    function a:isAiming() return self.aiming end
    function a:isMoving() return self.moving end
    function a:getAimingDelay() return self.delay end
    function a:getBeenMovingFor() return self.moved end
    function a:getPrimaryHandItem() return self.hand end
    function a:getInventory() return self.inv end
    return a
end
function rec(z, a, extra) local dx, dy = z.x - a.x, z.y - a.y; local r = { actor = z, distanceSq = dx * dx + dy * dy, distance = math.sqrt(dx * dx + dy * dy), score = 50 }
    for k, v in pairs(extra or {}) do r[k] = v end; return r end
function wrec(g, ammo, max) return { item = g, ranged = true, ammo = ammo or 30, maxAmmo = max or 30, range = 60 } end
function snap(...) local t = { threats = {} }; for _, z in ipairs({ ... }) do t.threats[#t.threats + 1] = { actor = z } end; return t end
function try(a, z, g, t, s, why) s = s or snap(z); why = why or "aim_settled"
    local h = SolShootDiscipline.gate(a, nil, {}, s, rec(z, a), wrec(g), why, t)
    if h == false then return false end
    return SolShootDiscipline.gate(a, nil, {}, s, rec(z, a), wrec(g), why, t + 300) end
function reset() SolShootDiscipline.actors = setmetatable({}, { __mode = "k" }); SolShootDiscipline.targets = setmetatable({}, { __mode = "k" })
    SolShootDiscipline.spareCache = setmetatable({}, { __mode = "k" }); SolShootDiscipline.lastLog = {}; MOVES = {}; NOW = 0 end
''')
L.execute(open(os.path.join(cl, "SolShootDiscipline.lua"), encoding="utf-8").read())
ev = L.eval
ck("module loads", ev('type(SolShootDiscipline) == "table" and SolShootDiscipline.VERSION == "0.1.0"'))

# switch off = LF as before
ck("off: gate passes LF's reason through", ev('''(function() SW.shooting_discipline = false; reset()
    local g = gun(); local a = sol({ delay = 40, moving = true }); local z = zed(8, 0)
    local hold, why = SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(g), "aim_settled", 0)
    SW.shooting_discipline = true
    return hold == false and why == "aim_settled" and g.mode == "Auto" end)()'''))
ck("off: shape leaves the actions alone", ev('''(function() SW.shooting_discipline = false
    local a = sol(); local z = zed(25, 0); local acts = { { kind = "shoot", score = 90 } }
    SolShootDiscipline.shape(a, nil, snap(z), rec(z, a), wrec(gun()), a.inv, acts, 25, nil)
    SW.shooting_discipline = true; return #acts == 1 and acts[1].kind == "shoot" end)()'''))

# fire mode
ck("Auto -> Single (the M4A1's own FireModePossibilities Auto/Single)", ev('''(function() reset(); local g = gun(); local a = sol({ delay = 0 })
    local z = zed(6, 0); SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(g), "aim_settled", 0); return g.mode == "Single" end)()'''))
ck("RealAuto (Gunworks) -> Single", ev('''(function() reset(); local g = gun({ mode = "RealAuto" }); local a = sol({ delay = 0 })
    local z = zed(6, 0); SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(g), "aim_settled", 0); return g.mode == "Single" end)()'''))
ck("a weapon without a single mode keeps its mode (gate still holds the cadence)", ev('''(function() reset(); local g = gun({ modes = { "Auto" } }); local a = sol({ delay = 0 })
    local z = zed(6, 0); SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(g), "aim_settled", 0); return g.mode == "Auto" end)()'''))

# aim gate
ck("unsettled engine aim (aimingDelay 40 of 40): hold and keep aiming", ev('''(function() reset(); local g = gun(); local a = sol({ delay = 40 }); local z = zed(8, 0)
    local hold, why = SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(g), "aim_settled", 0)
    return hold == true and why == "aiming" and SolShootDiscipline.actors[a].reason == "settle_aim" and MOVES[1] == "ready_weapon" end)()'''))
ck("moving / just stopped (beenMovingFor 20): hold", ev('''(function() reset(); local a = sol({ delay = 0, moved = 20 }); local z = zed(8, 0)
    local hold = SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(gun()), "aim_settled", 0)
    return hold == true and SolShootDiscipline.actors[a].reason == "settle_move" end)()'''))
ck("settled aim but under the 300 ms minimum: hold, then fire at 300 ms", ev('''(function() reset(); local g = gun(); local a = sol({ delay = 5 }); local z = zed(8, 0)
    local h1 = SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(g), "aim_settled", 0)
    local h2 = SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(g), "aim_settled", 300)
    return h1 == true and h2 == false and SolShootDiscipline.actors[a].reason == "aimed" end)()'''))
ck("engine aim never settles: she fires at the 2500 ms timeout and says so", ev('''(function() reset(); local a = sol({ delay = 40 }); local z = zed(8, 0)
    local h1 = SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(gun()), "aim_settled", 0)
    local h2 = SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(gun()), "aim_settled", 2500)
    local logged = false; for _, l in ipairs(LOG) do if string.find(l, "without a settled aim", 1, true) then logged = true end end
    return h1 == true and h2 == false and logged end)()'''))
ck("point blank (2.5 tiles): fires at once", ev('''(function() reset(); local a = sol({ delay = 40, moved = 30 }); local z = zed(2.5, 0)
    return SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(gun()), "aim_not_safe", 0) == false end)()'''))
ck("an immediate threat elsewhere (aim_not_required): waits at most 600 ms", ev('''(function() reset(); local a = sol({ delay = 40 }); local z = zed(8, 0)
    local h1 = SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(gun()), "aim_not_required", 0)
    local h2 = SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(gun()), "aim_not_required", 600)
    return h1 == true and h2 == false end)()'''))

# range
ck("effective range = MaxSightRange 10 + 2", ev('SolShootDiscipline.effectiveRange(gun(), 60)') == 12)
ck("gate: a zombie at 20 tiles is not shot", ev('''(function() reset(); local a = sol({ delay = 0 }); local z = zed(20, 0)
    local hold = SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(gun()), "aim_settled", 5000)
    return hold == true and SolShootDiscipline.actors[a].reason == "out_of_range" end)()'''))
ck("shape: shoot at 20 tiles -> hold_range (same score)", ev('''(function() reset(); local a = sol(); local z = zed(20, 0); local acts = { { kind = "shoot", score = 94 }, { kind = "retreat", score = 30 } }
    SolShootDiscipline.shape(a, nil, snap(z), rec(z, a), wrec(gun()), a.inv, acts, 20, nil)
    return acts[1].kind == "hold_range" and acts[1].score == 94 and acts[1].sdHold == "out_of_range" end)()'''))
ck("shape: a far zombie within 3 tiles of Jamal is still shot", ev('''(function() reset(); local a = sol(); local z = zed(20, 0); local jamal = zed(21, 1); local acts = { { kind = "shoot", score = 94 } }
    SolShootDiscipline.shape(a, jamal, snap(z), rec(z, a), wrec(gun()), a.inv, acts, 20, nil)
    return acts[1].kind == "shoot" end)()'''))
ck("cover fire while retreating: not past the effective range", ev('SolShootDiscipline.coverFireOk(nil, wrec(gun()), 30) == false and SolShootDiscipline.coverFireOk(nil, wrec(gun()), 8) == true'))

# per-target cap
ck("5 aimed shots at one zombie, the 6th waits", ev('''(function() reset(); local g = gun(); local a = sol({ delay = 0 }); local z = zed(9, 0); local t = 0
    for i = 1, 5 do t = t + 400; assert(try(a, z, g, t) == false); SolShootDiscipline.fired(a, rec(z, a), wrec(g), t + 300) end
    t = t + 400; local hold = SolShootDiscipline.gate(a, nil, {}, snap(z), rec(z, a), wrec(g), "aim_settled", t)
    return hold == true and SolShootDiscipline.actors[a].reason == "per_target_cap" end)()'''))
ck("... and is allowed again once it came 2 tiles nearer", ev('''(function() local a; for k in pairs(SolShootDiscipline.actors) do a = k end
    local z; for k in pairs(SolShootDiscipline.targets) do z = k end; z.x = 6.5
    return try(a, z, gun(), 99999) == false end)()'''))
ck("a different zombie is not capped by the first one's count", ev('''(function() local a; for k in pairs(SolShootDiscipline.actors) do a = k end
    local z2 = zed(0, 8); SolShootDiscipline.fired(a, rec(z2, a), wrec(gun()), 199000); SolShootDiscipline.targets[z2].n = 0; return try(a, z2, gun(), 200000) == false end)()'''))

# burst
ck("3 zombies within 5 tiles: half-settled aim (20 of 40) and 120 ms are enough", ev('''(function() reset(); local a = sol({ delay = 18 }); local z1, z2, z3 = zed(4, 0), zed(4, 1), zed(4.5, -1)
    local h = SolShootDiscipline.gate(a, nil, {}, snap(z1, z2, z3), rec(z1, a), wrec(gun()), "aim_settled", 0)
    local f = SolShootDiscipline.gate(a, nil, {}, snap(z1, z2, z3), rec(z1, a), wrec(gun()), "aim_settled", 120)
    return h == true and f == false and SolShootDiscipline.actors[a].reason == "burst" end)()'''))
ck("a single zombie at 4 tiles: aimingDelay 18 is not settled (needs <= 6)", ev('''(function() reset(); local a = sol({ delay = 18 }); local z1 = zed(4, 0)
    return SolShootDiscipline.gate(a, nil, {}, snap(z1), rec(z1, a), wrec(gun()), "aim_settled", 1000) == true end)()'''))
ck("burst is at most 3 quick shots, then a full settle", ev('''(function() reset(); local g = gun(); local a = sol({ delay = 18 }); local z1, z2, z3 = zed(4, 0), zed(4, 1), zed(4.5, -1); local s = snap(z1, z2, z3); local t = 0
    for i = 1, 3 do t = t + 150; local h = SolShootDiscipline.gate(a, nil, {}, s, rec(z1, a), wrec(g), "aim_settled", t)
        if h then h = SolShootDiscipline.gate(a, nil, {}, s, rec(z1, a), wrec(g), "aim_settled", t + 120) end
        assert(h == false, i); SolShootDiscipline.fired(a, rec(z1, a), wrec(g), t + 120); t = t + 120 end
    t = t + 150; local h1 = SolShootDiscipline.gate(a, nil, {}, s, rec(z1, a), wrec(g), "aim_settled", t)
    local h2 = SolShootDiscipline.gate(a, nil, {}, s, rec(z1, a), wrec(g), "aim_settled", t + 400)
    return h1 == true and h2 == true and SolShootDiscipline.actors[a].reason == "settle_aim" end)()'''))

# reserve and tactical reload
ck("last magazine (no loaded spare): a zombie at 8 tiles -> hold_range", ev('''(function() reset(); local a = sol({ inv = inventory({ 0 }) }); local z = zed(8, 0); local acts = { { kind = "shoot", score = 80 } }
    SolShootDiscipline.shape(a, nil, snap(z), rec(z, a), wrec(gun(), 12), a.inv, acts, 8, nil)
    return acts[1].kind == "hold_range" and acts[1].sdHold == "reserve" end)()'''))
ck("last magazine: a zombie at 4 tiles is shot", ev('''(function() reset(); local a = sol({ inv = inventory({}) }); local z = zed(4, 0); local acts = { { kind = "shoot", score = 80 } }
    SolShootDiscipline.shape(a, nil, snap(z), rec(z, a), wrec(gun(), 12), a.inv, acts, 4, nil)
    return acts[1].kind == "shoot" end)()'''))
ck("with a loaded spare the 8-tile zombie is shot", ev('''(function() reset(); local a = sol({ inv = inventory({ 30 }) }); local z = zed(8, 0); local acts = { { kind = "shoot", score = 80 } }
    SolShootDiscipline.shape(a, nil, snap(z), rec(z, a), wrec(gun(), 12), a.inv, acts, 8, nil)
    return acts[1].kind == "shoot" end)()'''))
ck("tactical reload: 5/30, a loaded spare, nearest zombie 8 tiles", ev('''(function() reset(); local a = sol({ inv = inventory({ 30 }) }); local z = zed(8, 0); local acts = { { kind = "shoot", score = 80 } }
    SolShootDiscipline.shape(a, nil, snap(z), rec(z, a), wrec(gun(), 5), a.inv, acts, 8, nil)
    return #acts == 2 and acts[2].kind == "reload" and acts[2].score > 80 end)()'''))
ck("no tactical reload with a zombie at 4 tiles, or without a spare", ev('''(function() reset(); local a = sol({ inv = inventory({ 30 }) }); local z = zed(4, 0); local acts = { { kind = "shoot", score = 80 } }
    SolShootDiscipline.shape(a, nil, snap(z), rec(z, a), wrec(gun(), 5), a.inv, acts, 4, nil)
    local b = sol({ inv = inventory({ 0 }) }); local z2 = zed(8, 0); local acts2 = { { kind = "shoot", score = 80 } }
    SolShootDiscipline.shape(b, nil, snap(z2), rec(z2, b), wrec(gun(), 5), b.inv, acts2, 8, nil)
    return #acts == 1 and #acts2 == 1 end)()'''))

# rank
ck("rank: with a firearm the zombie 2 tiles from Jamal goes first", ev('''(function() reset(); local g = gun(); local a = sol({ hand = g }); local jamal = zed(-6, 0)
    local near, far = zed(-7, 1), zed(5, 0); local s = { rec(far, a, { score = 70 }), rec(near, a, { score = 60 }) }
    SolShootDiscipline.rank(a, jamal, s); return s[1].actor == near end)()'''))
ck("rank: melee in her hands = LF order unchanged", ev('''(function() reset(); local a = sol({ hand = { isRanged = function() return false end } }); local jamal = zed(-6, 0)
    local near, far = zed(-7, 1), zed(5, 0); local s = { rec(far, a, { score = 70 }), rec(near, a, { score = 60 }) }
    SolShootDiscipline.rank(a, jamal, s); return s[1].actor == far end)()'''))

# replay: 6 s of the live dump, one zombie at 9 tiles, 100 ms decision pulses, engine aim model from the bytecode
L.execute('''
function replay(newGate)
    reset(); local g = gun(); local a = sol({ delay = 40 }); local z = zed(9, 0); local s = snap(z)
    local Aiming, mult, perTick = 10, 1.0, 0.625 * (1 + 0.05 * 10)
    local shots, sumDelay, lfAimUntil, recoil, mode = 0, 0, nil, 0, "Auto"
    for t = 0, 6000, 16 do
        a.aiming = true
        if recoil <= 0 then a.delay = math.max(0, a.delay - perTick * mult) end
        recoil = math.max(0, recoil - mult)
        if t % 96 == 0 then
            lfAimUntil = lfAimUntil or (t + 220)
            if t >= lfAimUntil and recoil <= 0 then
                local fire = true
                if newGate then fire = SolShootDiscipline.gate(a, nil, {}, s, rec(z, a), wrec(g), "aim_settled", t) == false end
                if fire then
                    local auto = g.mode == "Auto"
                    local rounds = auto and 3 or 1
                    for r = 1, rounds do
                        shots = shots + 1; sumDelay = sumDelay + a.delay
                        a.delay = math.min(40, a.delay + (auto and 0 or 15) * 0.25 + 40 * 0.05)
                    end
                    recoil = auto and 0 or 15
                    if newGate then SolShootDiscipline.fired(a, rec(z, a), wrec(g), t) end
                    lfAimUntil = nil
                end
            end
        end
    end
    return shots, sumDelay / math.max(1, shots)
end
''')
old_n, old_d = L.eval('replay(false)')
new_n, new_d = L.eval('replay(true)')
print("replay 6 s: old %d rounds, mean aimingDelay at the trigger %.1f; new %d rounds, mean %.1f" % (old_n, old_d, new_n, new_d))
ck("replay: the old cadence spends a magazine in 6 s (live: 30 rounds)", old_n >= 25, old_n)
ck("replay: the new gate fires at most 5 aimed rounds at the one zombie", 1 <= new_n <= 5, new_n)
ck("replay: the new shots leave with the aim settled (mean aimingDelay <= 6)", new_d <= 6.0, new_d)

# the installed hook lines run with SCCombat's own local names
def hook_line(marker_text):
    for line in combat.splitlines():
        if marker_text in line and "s104" in line: return line
    for i, line in enumerate(combat.splitlines()):
        if marker_text in line: return line
    return None
lines = combat.splitlines()
gi = [i for i, l in enumerate(lines) if "s104 shooting_discipline: stand, settle" in l][0]
gate_chunk = "\n".join(lines[gi:gi + 2])
L.execute('function hookGate(actor, player, state, snapshot, target, weapon, now)\n local aiming, aimReason = false, "aim_settled"\n'
          + gate_chunk + '\n return aiming, aimReason end')
ck("installed gate hook holds an unsettled shot", L.eval('(function() reset(); local a = sol({ delay = 40 }); local z = zed(8, 0); local h, w = hookGate(a, nil, {}, snap(z), rec(z, a), wrec(gun()), 0); return h == true and w == "aiming" end)()'))
fi = [i for i, l in enumerate(lines) if 'chosen.kind == "shoot" and reason == "shoot"' in l][0]
L.execute('function hookFired(actor, target, weapon, now, reason)\n local chosen = { kind = "shoot" }\n' + lines[fi] + '\n end')
ck("installed fired hook counts the shot", L.eval('(function() reset(); local a = sol(); local z = zed(8, 0); hookFired(a, rec(z, a), wrec(gun()), 10, "shoot"); return SolShootDiscipline.targets[z].n == 1 end)()'))
si = [i for i, l in enumerate(lines) if "s104 shooting_discipline: range, reserve" in l][0]
L.execute('function hookShape(actor, player, snapshot, target, weapon, inventory, actions, distance)\n local hasReloadAmmo = function() return true end\n'
          + lines[si] + '\n return actions end')
ck("installed shape hook turns a 20-tile shot into hold_range", L.eval('(function() reset(); local a = sol(); local z = zed(20, 0); local acts = hookShape(a, nil, snap(z), rec(z, a), wrec(gun()), a.inv, { { kind = "shoot", score = 90 } }, 20); return acts[1].kind == "hold_range" end)()'))
ri = [i for i, l in enumerate(lines) if "s104 shooting_discipline: threats nearest Jamal" in l][0]
L.execute('function hookRank(actor, player, scored)\n' + lines[ri] + '\n return scored end')
ck("installed rank hook reorders", L.eval('(function() reset(); local a = sol({ hand = gun() }); local jamal = zed(-6, 0); local near, far = zed(-7, 1), zed(5, 0); local s = hookRank(a, jamal, { rec(far, a, { score = 70 }), rec(near, a, { score = 60 }) }); return s[1].actor == near end)()'))
ci = [i for i, l in enumerate(lines) if "SolShootDiscipline.coverFireOk" in l][0]
L.execute('function hookCover(actor, weapon, distance)\n return true\n' + lines[ci] + '\n end')
ck("installed cover-fire clause refuses 30 tiles", L.eval('(function() reset(); return hookCover(sol(), wrec(gun()), 30) == false and hookCover(sol(), wrec(gun()), 8) == true end)()'))
ck("no Java call with a boolean argument in SolShootDiscipline", re.search(r'(?<![\w.])call\([^)]*,\s*"[A-Za-z]+",[^)]*\b(true|false)\b', open(os.path.join(cl, "SolShootDiscipline.lua"), encoding="utf-8").read()) is None)

G = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua")
r = subprocess.run([sys.executable, "-I", os.path.join(G, "tonumber_check.py"), cl], capture_output=True, text=True); ck("tonumber gate", r.returncode == 0, r.stdout[-300:])
r = subprocess.run([sys.executable, "-I", os.path.join(G, "jarcall_check.py"), cl], capture_output=True, text=True); ck("jarcall gate", r.returncode == 0, r.stdout[-400:])
print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(P), len(FAIL))); sys.exit(1 if FAIL else 0)
