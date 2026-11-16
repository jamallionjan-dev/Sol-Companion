"""s98 combat_equip_fallback + preferred_weapon offline. Code under test is CUT FROM THE PATCHED FILES (SCCombat weaponUsableNow,
chooseWeapon, equipExactWeapon, the execute s98 block; SCNativeActions equip with s97; SCActionSupervisor retry ledger;
SCUIBridge onEquipmentOption) plus SolCombatEquipFallback and SolTwoHandGrip. EFZ is a fake of TW/Runtime R.update: an
assembly with duplicatePath gets md.TW.ready=false and is cleared from both hands inside setPrimaryHandItem.
Live replay: Sol holds a G28 in both hands; LF picks the (broken) M4A1; equip fails -> she shoots with the G28, both hands
stay on it (SolTwoHandGrip has nothing to mend), the M4A1 is not picked again. Run: python test_s98_combat_equip_fallback.py
[client dir]. Offline PASS is not Runtime PASS."""
import os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
tmp = tempfile.mkdtemp(prefix="s98_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
for f in ("SCNativeActions.lua", "SCCombat.lua", "SCActionSupervisor.lua", "SCUIBridge.lua", "SolAuthority.lua"): shutil.copy(os.path.join(CL, f), cl)
shutil.copy(os.path.join(HERE, "SolTwoHandGrip.lua"), cl)
r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s98_combat_equip_fallback.py"), cl], capture_output=True, text=True)
ck("installer runs (10 edits + 2 switches)", r.returncode == 0 and r.stdout.count("edited") == 11, r.stdout + r.stderr)
r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s98_combat_equip_fallback.py"), cl], capture_output=True, text=True)
ck("second run changes nothing", r.returncode == 0 and "edited" not in r.stdout, r.stdout + r.stderr)
rd = lambda f: open(os.path.join(cl, f), encoding="utf-8", newline="").read()
NA, CB, SV, UB, FB, GR = rd("SCNativeActions.lua"), rd("SCCombat.lua"), rd("SCActionSupervisor.lua"), rd("SCUIBridge.lua"), rd("SolCombatEquipFallback.lua"), rd("SolTwoHandGrip.lua")
AU = rd("SolAuthority.lua")
ck("switches registered", '"combat_equip_fallback"' in AU and '"preferred_weapon"' in AU)

def cut(src, start, end, nm):
    i = src.find(start); j = src.find(end, i)
    ck("cut " + nm, i >= 0 and j > i)
    return src[i:j + len(end)]
EQUIP = re.search(r"\nlocal function equip\(actor, intent, provider\)\r?\n.*?\r?\nend\r?\n", NA, re.S).group(0)
USABLE = cut(CB, "local function weaponUsableNow(", "\nend\n", "weaponUsableNow")
CHOOSE = cut(CB, "local function chooseWeapon(", "\n    return best, inventory, entry\nend\n", "chooseWeapon")
EXACT = cut(CB, "function Combat.equipExactWeapon(", "\n    return equipped, reason\nend\n", "equipExactWeapon")
BLOCK = cut(CB, '    if weapon and not weapon.equipped and action.kind ~= "shove" and action.kind ~= "stomp" then\n        -- s98 begin', "        -- s98 end\n    end\n", "execute block")
LEDGER1 = cut(SV, "local function retryKey(", "\n    return ledger[key]\nend\n", "noteFailure")
LEDGER2 = cut(SV, "function Supervisor.retryStatus(", "\n    return false, status\nend\n", "canRetry")
ONEQUIP = cut(UB, "local function onEquipmentOption(", '    safeMethod(player, "setHaloNote", message)\nend\n', "onEquipmentOption")
ck("equipWeapon passes ignoreRetry", "ignoreRetry = (function() local F_" in CB)

ENV = r"""
NOW = 10000
function getTimestampMs() return NOW end
LOGS = {}
function print(m) LOGS[#LOGS + 1] = tostring(m) end
SW = { two_hand_grip = true, combat_equip_fallback = true, preferred_weapon = true }
SolAuthority = { on = function(f) return SW[f] == true end }
SAID = {}
SolOverlay = { speak = function(a, line, ms) SAID[#SAID + 1] = line; return true end }
function Item(full, o) o = o or {}; o.t = full
    function o:getFullType() return self.t end
    function o:getType() return string.match(self.t, "([%w_]+)$") end
    function o:getDisplayName() return self.dn or self.t end
    function o:isTwoHandWeapon() return self.two == true end
    function o:isRequiresEquippedBothHands() return self.two == true end
    function o:hasModData() return self.md ~= nil end
    function o:getModData() self.md = self.md or {}; return self.md end
    function o:isRoundChambered() return self.chambered == true end
    return o end
-- fake EFZ TW/Runtime: R.update inside OnEquipPrimary/Secondary
TWRuntime = { isWeapon = function(i) return type(i) == "table" and i.efz == true end,
    read = function(i)
        local e = { { path = "mod_sight_rear", fullType = "EFZ.RearSight" } }
        if i.broken then e[2] = { path = "mod_sight_rear", fullType = "EFZ.RearSight2" } end
        return {}, e, {}, i.broken and "duplicatePath" or nil end }
TWLOG = 0
local function efzUpdate(p, w)
    if not (type(w) == "table" and w.efz) then return end
    w.md = w.md or {}
    w.md.TW = { key = w.t, ready = not w.broken }
    if w.broken then TWLOG = TWLOG + 1
        if p.p == w then p.p = nil end
        if p.s == w then p.s = nil end
    end
end
SOL = { p = nil, s = nil, resets = 0 }
function SOL:getPrimaryHandItem() return self.p end
function SOL:getSecondaryHandItem() return self.s end
function SOL:setPrimaryHandItem(i) self.p = i; efzUpdate(self, i) end
function SOL:setSecondaryHandItem(i) self.s = i; efzUpdate(self, i) end
function SOL:resetEquippedHandsModels() self.resets = self.resets + 1 end
function SOL:getVehicle() return nil end
function SOL:getCharacterActions() return { isEmpty = function() return true end } end
ISTimedActionQueue = { getTimedActionQueue = function(a) return { queue = {} } end }
SolUI = { solActor = function() return SOL end }
ITEMS = {}
U_ = { call = function(o, m, ...) if o == nil or o[m] == nil then return nil, false end; return o[m](o, ...), true end,
    inventory = function(a) return "INV" end, idOf = function(a) return "sol-1" end, isValidActor = function() return true end,
    inventoryItemsDeep = function() return ITEMS end, say = function(a, t) SAID[#SAID + 1] = t end, config = function() return nil end }
SurvivorCompanion = { GameplayUtil = U_ }
function U() return U_ end
Combat = {}
function weaponRecord(i) if i == nil then return nil end
    return { item = i, type = i.t, ranged = i.ranged == true, jammed = i.jammed == true, condition = i.cond or 10,
        ammo = i.ammo or 0, score = i.score or 0, twoHanded = i.two == true } end
function hasReloadAmmo(inv, w) return w.item.reload == true end
function inventoryWeapons(actor)
    local out, p = {}, actor.p
    if p then local r = weaponRecord(p); r.equipped = true; out[#out + 1] = r end
    for _, i in ipairs(ITEMS) do if i ~= p and i.weapon then out[#out + 1] = weaponRecord(i) end end
    return out, "INV", nil end
local function invoke(object, name, ...) local f = object[name]; if f == nil then return false, "no method" end; return pcall(f, object, ...) end
local function useProvider() return nil end
EQUIPS = 0
function equipWeapon(actor, item, options)
    EQUIPS = EQUIPS + 1
    if actor.p == item then return true, "weapon_already_equipped" end
    return NATIVE_EQUIP(actor, { item = item }, { directNative = true })
end
function actionSupervisor() return SUP end
function weaponKey(item) return "weapon:" .. tostring(item.t) end
"""
HARNESS = ("\nlocal function invoke(object, name, ...) local f = object[name]; if f == nil then return false, 'no method' end; return pcall(f, object, ...) end\n"
           "local function useProvider() return nil end\n" + EQUIP + "\nNATIVE_EQUIP = equip\n"
           + USABLE + "\nUSABLE = weaponUsableNow\n" + CHOOSE + "\nCHOOSE = chooseWeapon\n" + EXACT +
           "\nfunction EXEC(actor, weapon, action, state)\n    local utility = U_\n" + BLOCK +
           "    return 'proceed', weapon, action\nend\n")

def fresh():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV); L.execute(GR); L.execute(FB); L.execute(HARNESS)
    L.execute("""
G28 = Item('EscapeFromZomboidFirearms.G28', { weapon = true, ranged = true, two = true, efz = true, ammo = 10, chambered = true, score = 50 })
M4 = Item('EscapeFromZomboidFirearms.M4A1', { weapon = true, ranged = true, two = true, efz = true, broken = true, ammo = 30, score = 60, dn = 'Colt M4A1' })
PISTOL = Item('Base.Pistol', { weapon = true, ranged = true, two = false, ammo = 8, score = 30 })
AXE = Item('Base.Axe', { weapon = true, ranged = false, two = true, score = 20 })
ITEMS = { G28, M4, PISTOL, AXE }
SOL.p, SOL.s = G28, G28
""")
    return L
def logs(L): s = L.eval("LOGS"); return [s[i] for i in range(1, len(s) + 1)]
def said(L): s = L.eval("SAID"); return [s[i] for i in range(1, len(s) + 1)]
def esc(s): return s.encode("utf-8")
AR_PARTS = "فيها مشكلة بالقطع"; AR_STAY = "رح ضل عالـ"

# ---- live replay: M4A1 chosen by LF (preferred marker, assembly not refreshed yet)
L = fresh()
L.execute("M4:getModData().SC_ManualEquipFor = 'sol-1'")
w = L.eval("(CHOOSE(SOL, 'best', 12, 0))")
ck("LF picks the preferred M4A1 first (manual marker, not yet known broken)", L.eval("(CHOOSE(SOL, 'best', 12, 0)).item == M4"))
L.execute("ST = {}; R1, W1, A1 = EXEC(SOL, (CHOOSE(SOL, 'best', 12, 0)), { kind = 'shoot' }, ST)")
ck("EFZ cleared the M4A1 (duplicatePath)", L.eval("TWLOG") >= 1)
ck("execute goes on with the gun in her hands: shoot with the G28", L.eval("R1 == 'proceed' and W1.item == G28 and A1.kind == 'shoot'"), (L.eval("R1"), L.eval("W1")))
ck("two-handed grip correct: G28 in both hands", L.eval("SOL.p == G28 and SOL.s == G28"))
ck("SolTwoHandGrip stays happy (nothing to mend)", L.eval("select(2, SolTwoHandGrip.grip(SOL, 'check', true))") == "fine")
ck("log names the real reason and the EFZ problem", any("rejected: native equip did not retain" in x and "duplicatePath mod_sight_rear" in x for x in logs(L)), logs(L))
s = said(L)
ck("she says it plainly (M4A1 parts problem, staying on the G28)", len(s) == 1 and esc(AR_PARTS) in esc(s[0]) and esc(AR_STAY + "G28") in esc(s[0]), s)
ck("next pulse: M4A1 no longer chosen, G28 kept", L.eval("(CHOOSE(SOL, 'best', 12, 0)).item == G28"))
L.execute("NOW = NOW + 61000")
ck("after the 60 s block: EFZ not-ready keeps the M4A1 out", L.eval("(CHOOSE(SOL, 'best', 12, 0)).item == G28") and L.eval("USABLE('INV', weaponRecord(M4))") is False)
ck("no second speech for the same thing", len(said(L)) == 1, said(L))

# ---- switch off: the old behaviour (equip_rejected, the M4A1 chosen again)
L = fresh()
L.execute("SW.combat_equip_fallback = false; SW.preferred_weapon = false; M4:getModData().SC_ManualEquipFor = 'sol-1'")
L.execute("R1, W1 = EXEC(SOL, (CHOOSE(SOL, 'best', 12, 0)), { kind = 'shoot' }, {})")
ck("switch off: old reply equip_rejected", L.eval("R1 == false and W1 == 'equip_rejected'"), (L.eval("R1"), L.eval("W1")))
ck("switch off: M4A1 chosen again (the live loop)", L.eval("(CHOOSE(SOL, 'best', 12, 0)).item == M4"))

# ---- held gun empty, mags in the bag: reload instead of a dry shot
L = fresh()
L.execute("G28.ammo = 0; G28.chambered = false; G28.reload = true")
L.execute("R1, W1, A1 = EXEC(SOL, weaponRecord(M4), { kind = 'shoot' }, {})")
ck("held G28 empty with mags: reload it", L.eval("R1 == 'proceed' and W1.item == G28 and A1.kind == 'reload'"))
L = fresh()
L.execute("G28.jammed = true")
L.execute("R1, W1, A1 = EXEC(SOL, weaponRecord(M4), { kind = 'shoot' }, {})")
ck("held G28 jammed: unjam it", L.eval("R1 == 'proceed' and A1.kind == 'unjam'"))

# ---- nothing in her hands: reason kept, next pulse picks the next usable weapon, melee last
L = fresh()
L.execute("SOL.p, SOL.s = nil, nil")
L.execute("R1, W1 = EXEC(SOL, weaponRecord(M4), { kind = 'shoot' }, {})")
ck("empty hands: reason in the reply", L.eval("R1 == false") and str(L.eval("W1")).startswith("equip_rejected:native equip"), L.eval("W1"))
ck("next pulse picks the next usable gun (G28)", L.eval("(CHOOSE(SOL, 'best', 12, 0)).item == G28"))
L.execute("G28.cond = 0; PISTOL.cond = 0")
ck("all guns out: the axe (melee last)", L.eval("(CHOOSE(SOL, 'best', 12, 0)).item == AXE"))

# ---- no swap mid-fight: held usable G28 kept against a higher-scoring usable gun
L = fresh()
L.execute("M4.broken = false; M4.score = 90")
ck("held usable G28 kept against a better-scoring M4A1", L.eval("(CHOOSE(SOL, 'best', 12, 0)).item == G28"))
L.execute("M4:getModData().SC_ManualEquipFor = 'sol-1'")
ck("his preferred working M4A1 is taken (his pick)", L.eval("(CHOOSE(SOL, 'best', 12, 0)).item == M4"))
L.execute("R1, W1 = EXEC(SOL, (CHOOSE(SOL, 'best', 12, 0)), { kind = 'shoot' }, {})")
ck("a working M4A1 equips in both hands", L.eval("R1 == true and SOL.p == M4 and SOL.s == M4"))

# ---- the player's order: carry this weapon
L = fresh()
L.execute("G28:getModData().SC_ManualEquipFor = 'sol-1'; M4.md = { TW = { key = 'M4A1', ready = false } }")
L.execute("OK1, WHY1 = Combat.equipExactWeapon(SOL, M4)")
ck("order on the broken M4A1: refused, preference moves to it", L.eval("OK1 == false and M4.md.SC_ManualEquipFor == 'sol-1' and G28.md.SC_ManualEquipFor == nil"))
s = said(L)
ck("she says why (parts), staying on the G28", len(s) == 1 and esc(AR_PARTS) in esc(s[0]) and esc(AR_STAY + "G28") in esc(s[0]), s)
ck("combat keeps the G28 (no new speech)", L.eval("(CHOOSE(SOL, 'best', 12, 0)).item == G28") and len(said(L)) == 1)
L.execute("SUP = { resets = 0, resetRetry = function(a, why, act, key) SUP.resets = SUP.resets + 1; SUP.key = key end }")
L.execute("OK2 = Combat.equipExactWeapon(SOL, PISTOL)")
ck("order on the pistol: equipped, preference moves, retry ledger cleared", L.eval("OK2 == true and PISTOL.md.SC_ManualEquipFor == 'sol-1' and M4.md.SC_ManualEquipFor == nil and SUP.resets == 1"))

# ---- onEquipmentOption: no technical halo
for on in (True, False):
    L = fresh()
    if not on: L.execute("SW.preferred_weapon = false")
    L.execute("HALO = nil; PLAYER = { setHaloNote = function(self, m) HALO = m end }\n"
              "Bridge = { equipOnCompanion = function() return false, 'retry_exhausted' end, borrowedInventoryLabel = function() return 'Sol' end }\n"
              "function safeMethod(o, m, ...) if o == nil or o[m] == nil then return nil end; return o[m](o, ...) end\n" + ONEQUIP +
              "\nonEquipmentOption(M4, SOL, PLAYER, 'weapon')")
    if on:
        ck("halo replaced by her words", L.eval("HALO == nil") and len(said(L)) == 1, (L.eval("HALO"), said(L)))
    else:
        ck("switch off: the old halo", L.eval("HALO") == "Could not equip item: retry_exhausted")

# ---- LF ActionSupervisor: exhausted equip expires
SUPH = r"""
Supervisor = {}
local retryByActor, retryResetByActor = {}, {}
local function config(k, d) return d end
local function clean(v) return v end
local function nowMs() return NOW end
local function safeDetail(r) local c = {}; for k, v in pairs(r) do c[k] = v end; return c end
""" + LEDGER1 + LEDGER2 + "\nNOTE = noteFailure\n"
for on in (True, False):
    L = fresh()
    if not on: L.execute("SW.combat_equip_fallback = false")
    L.execute(SUPH)
    L.execute("TOK = { action = 'equip_weapon', targetKey = 'weapon:M4' }; for i = 1, 4 do NOTE(SOL, TOK, 'native equip did not retain', 'control') end")
    ck(("on" if on else "off") + ": 4 failures -> retry_exhausted", L.eval("Supervisor.retryStatusAny(SOL, 'equip_weapon', 'weapon:M4').exhausted == true and select(1, Supervisor.canRetry(SOL, 'equip_weapon', 'weapon:M4', 'control')) == false"))
    L.execute("NOW = NOW + 181000")
    exp = L.eval("Supervisor.retryStatusAny(SOL, 'equip_weapon', 'weapon:M4') == nil and select(1, Supervisor.canRetry(SOL, 'equip_weapon', 'weapon:M4', 'control')) == true")
    ck(("on: expires after 3 min" if on else "off: never expires (old)"), exp is (True if on else False))
    L.execute("TOK2 = { action = 'board_vehicle', targetKey = 'veh' }; for i = 1, 4 do NOTE(SOL, TOK2, 'x', 'control') end; NOW = NOW + 181000")
    ck(("on" if on else "off") + ": other actions unchanged (still exhausted)", L.eval("Supervisor.retryStatusAny(SOL, 'board_vehicle', 'veh').exhausted == true"))
L = fresh()
ck("ignoreRetry for an explicit order only", L.eval("SolCombatEquipFallback.ignoreRetry({ immediateCommand = true }) == true and SolCombatEquipFallback.ignoreRetry({ nextAction = 'shoot' }) == false"))

for nm, src in (("SolCombatEquipFallback.lua", FB), ("SCCombat.lua", CB), ("SCActionSupervisor.lua", SV), ("SCUIBridge.lua", UB)):
    ck("ascii only " + nm, all(ord(c) < 128 for c in src))
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
if os.path.exists(GATE):
    for nm in ("SolCombatEquipFallback.lua", "SCCombat.lua", "SCActionSupervisor.lua", "SCUIBridge.lua"):
        r = subprocess.run([sys.executable, GATE, os.path.join(cl, nm)], capture_output=True, text=True)
        ck("tonumber gate " + nm, r.returncode == 0, r.stdout[-300:])
else:
    ck("tonumber gate present", False, GATE)
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
