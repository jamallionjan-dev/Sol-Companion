"""s152 offline: SolNpcTransfer + the patched SolMagFill / SCNativeActions helper, run in the Kahlua stand-in.
The game is faked: containers (Remove/AddItem/contains/isInCharacterInventory), a vanilla
ISInventoryPaneContextMenu.transferIfNeeded that THROWS for a character without a player index (the live NPE of
2026-11-14 02:43:03 / 03:18:32), Gunworks Magazine.reloadMagazine (Magazine.lua:194-210) and the vanilla load/insert
actions, which need the magazine and rounds in the MAIN inventory.
Run: python test_s152_npc_transfer.py [client dir]. Offline PASS is not Runtime PASS."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
BASE = sys.argv[2] if len(sys.argv) > 2 else CL       # pristine (pre-s152) files for the installer test, when given
tmp = tempfile.mkdtemp(prefix="s152_"); cl = os.path.join(tmp, "client"); os.makedirs(cl)
for f in ("SolMagFill.lua", "SCNativeActions.lua", "SolAuthority.lua"): shutil.copy(os.path.join(BASE, f), cl)
ap = os.path.join(HERE, "apply_s152_npc_transfer.py")
r1 = subprocess.run([sys.executable, ap, cl], capture_output=True, text=True)
snap = {f: open(os.path.join(cl, f), "rb").read() for f in os.listdir(cl)}
r2 = subprocess.run([sys.executable, ap, cl], capture_output=True, text=True)
snap2 = {f: open(os.path.join(cl, f), "rb").read() for f in os.listdir(cl)}
ck("installer runs", r1.returncode == 0, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and snap == snap2 and "edited" not in r2.stdout and "copied" not in r2.stdout, r2.stdout + r2.stderr)
rd = lambda f: open(os.path.join(cl, f), encoding="utf-8", newline="").read()
NT, MF, NA, AU = rd("SolNpcTransfer.lua"), rd("SolMagFill.lua"), rd("SCNativeActions.lua"), rd("SolAuthority.lua")
ck("switch npc_reload_transfer registered (s149)", '"npc_reload_transfer"' in AU)
for nm, src in (("SolNpcTransfer.lua", NT), ("SolMagFill.lua", MF)):
    ck(nm + " is ASCII", all(ord(c) < 128 for c in src))
tn = subprocess.run([sys.executable, "-I", os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py"), cl], capture_output=True, text=True)
ck("tonumber gate", tn.returncode == 0, tn.stdout + tn.stderr)
ck("SolMagFill no longer calls the player-only helper directly for her",
   MF.count("guarded(actor, MG.reloadMagazine, actor, mag)") == 1 and MF.count("guarded(actor, CM.transferBullets, actor, kind, cur, max)") == 1)
ck("SCNativeActions uses SolNpcTransfer.guard", NA.count("npcTransfer.guard(actor, ISReloadWeaponAction.BeginAutomaticReload, actor, weapon)") == 1)

FAKES = r"""
SWITCH = { npc_reload_transfer = true, mag_fill = true }
SolAuthority = { on = function(n) return SWITCH[n] == true end }
getTimestampMs = function() return 1000 end
NPE, VANILLA, QUEUE = 0, 0, {}
function mkContainer(owner)
  local c = { items = {}, owner = owner }
  function c:contains(it) for _, v in ipairs(self.items) do if v == it then return true end end return false end
  function c:Remove(it) for i, v in ipairs(self.items) do if v == it then table.remove(self.items, i); it.container = nil; return end end end
  function c:AddItem(it) if REJECT_ADD == self then return end self.items[#self.items + 1] = it; it.container = self; return it end
  function c:isInCharacterInventory(chr) if chr == nil then NPE = NPE + 1; error("NullPointerException: chr is null") end return self.owner == chr end
  function c:getAllTypeRecurse(t) local out = {}
    local function walk(k) for _, v in ipairs(k.items) do if v.type == t then out[#out + 1] = v end if v.bag then walk(v.bag) end end end
    walk(self); return out end
  function c:getCountTypeRecurse(t) return #self:getAllTypeRecurse(t) end
  return c
end
function mkItem(t, container) local it = { type = t, inventoryItem = true, ammo = 0, max = 0 }
  function it:getContainer() return self.container end
  function it:getType() return self.type end
  function it:getFullType() return "Base." .. self.type end
  function it:getCurrentAmmoCount() return self.ammo end
  function it:getMaxAmmo() return self.max end
  if container then container:AddItem(it) end
  return it end
function mkList(t) local l = { javaList = true, t = t }
  function l:size() return #self.t end
  function l:get(i) return self.t[i + 1] end
  return l end
function instanceof(o, cls)
  if type(o) ~= "table" then return false end
  if cls == "InventoryItem" then return o.inventoryItem == true end
  if cls == "ArrayList" then return o.javaList == true end
  return false end
function mkActor(index) local a = { index = index }
  a.inv = mkContainer(a)
  function a:getInventory() return self.inv end
  function a:getPlayerNum() return self.index end
  return a end
function mkBag(actor) local bagItem = mkItem("Bag", actor.inv); bagItem.bag = mkContainer(actor); return bagItem.bag end
PLAYERS = {}
getSpecificPlayer = function(n) return PLAYERS[n] end
-- vanilla: luautils.haveToBeTransfered -> walkToContainer(getSpecificPlayer(playerNum)) -> container:isInCharacterInventory(playerObj)
local function vanillaOne(playerObj, it)
  local c = it:getContainer()
  if c ~= nil and c ~= playerObj:getInventory() then
    c:isInCharacterInventory(getSpecificPlayer(playerObj:getPlayerNum()))
    QUEUE[#QUEUE + 1] = { kind = "transfer_action", item = it }
  end
end
ISInventoryPaneContextMenu = {}
function ISInventoryPaneContextMenu.transferIfNeeded(playerObj, item)
  VANILLA = VANILLA + 1
  if instanceof(item, "InventoryItem") then vanillaOne(playerObj, item)
  elseif instanceof(item, "ArrayList") then for i = 1, item:size() do vanillaOne(playerObj, item:get(i - 1)) end end
end
ORIGINAL = ISInventoryPaneContextMenu.transferIfNeeded
function ISInventoryPaneContextMenu.transferBullets(playerObj, kind, cur, max)
  local found = playerObj:getInventory():getAllTypeRecurse(kind)
  local n = math.min(#found, max - cur)
  if n <= 0 then return 0 end
  local some = {}; for i = 1, n do some[i] = found[i] end
  ISInventoryPaneContextMenu.transferIfNeeded(playerObj, mkList(some))
  return n
end
ISTimedActionQueue = { add = function(a) QUEUE[#QUEUE + 1] = a; return a end, getTimedActionQueue = function() return { queue = QUEUE } end }
ISLoadBulletsInMagazine = { new = function(self, chr, mag, n) return { kind = "load", chr = chr, mag = mag, n = n,
  valid = chr:getInventory():contains(mag) } end }
ISInsertMagazine = { new = function(self, chr, gun, mag) return { kind = "insert", chr = chr, mag = mag, valid = chr:getInventory():contains(mag) } end }
package.loaded["WeaponSystems/Utils/Ammo"] = { GetAutomaticReloadAmmoType = function(p, m) return "Round" end }
package.loaded["WeaponSystems/Utils/Magazine"] = {
  reloadMagazine = function(playerObj, magazine)
    local n = magazine:getCurrentAmmoCount() + ISInventoryPaneContextMenu.transferBullets(playerObj, "Round", magazine:getCurrentAmmoCount(), magazine:getMaxAmmo())
    if n > 0 then
      ISInventoryPaneContextMenu.transferIfNeeded(playerObj, magazine)
      ISTimedActionQueue.add(ISLoadBulletsInMagazine:new(playerObj, magazine, n))
    end
    return n
  end }
Events = {}
function reset() NPE, VANILLA, QUEUE = 0, 0, {}; REJECT_ADD = nil end
function scene(index)
  reset()
  local a = mkActor(index)
  local bag = mkBag(a)
  local mag = mkItem("Mag", bag); mag.ammo, mag.max = 4, 20
  local rounds = {}
  for i = 1, 30 do rounds[i] = mkItem("Round", bag) end
  return a, bag, mag, rounds
end
function inMain(a, items) for _, it in ipairs(items) do if not a.inv:contains(it) then return false end end return true end
function countIn(c, t) local n = 0; for _, v in ipairs(c.items) do if v.type == t then n = n + 1 end end return n end
"""
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(FAKES)
L.execute(NT)
L.execute(MF)

# 1. live replay: she (no player index) fills a 4/20 magazine that sits in her bag with rounds from the bag
L.execute("sol, bag, mag, rounds = scene(1); ok = SolMagFill.queueFill(sol, mag, 'Round')")
ck("replay: fill is queued", L.eval("ok") is True)
ck("replay: no NullPointerException path", L.eval("NPE") == 0)
ck("replay: magazine moved to her main inventory", L.eval("sol.inv:contains(mag) and not bag:contains(mag)"))
ck("replay: exactly the 16 needed rounds moved, 14 stay in the bag", L.eval("countIn(sol.inv, 'Round')") == 16 and L.eval("countIn(bag, 'Round')") == 14)
ck("replay: one load action, valid, no transfer action queued", L.eval("#QUEUE == 1 and QUEUE[1].kind == 'load' and QUEUE[1].valid == true and QUEUE[1].n == 20"))
ck("replay: the game's transfer function is back", L.eval("ISInventoryPaneContextMenu.transferIfNeeded == ORIGINAL"))
ck("replay: nothing lost (31 items of hers)", L.eval("#sol.inv.items + #bag.items") == 32)   # bag item + mag + 30 rounds

# 2. insert: the magazine in the bag goes to the main inventory before ISInsertMagazine
L.execute("sol, bag, mag = scene(1); gun = mkItem('Gun', sol.inv); ok = SolMagFill.queueInsert(sol, gun, mag)")
ck("insert: queued and valid", L.eval("ok == true and #QUEUE == 1 and QUEUE[1].kind == 'insert' and QUEUE[1].valid == true"))
ck("insert: no NPE, vanilla helper not used for her", L.eval("NPE") == 0 and L.eval("VANILLA") == 0)

# 3. switch off = the old behaviour (the vanilla helper is called and throws inside pcall)
L.execute("SWITCH.npc_reload_transfer = false; sol, bag, mag = scene(1); gun = mkItem('Gun', sol.inv); SolMagFill.queueInsert(sol, gun, mag)")
ck("switch off: old path (vanilla helper called, NPE counted)", L.eval("VANILLA") == 1 and L.eval("NPE") == 1 and L.eval("bag:contains(mag)"))
L.execute("SWITCH.npc_reload_transfer = true")

# 4. the local player keeps the game's own path (timed transfer action), nothing moved directly
L.execute("me, bag, mag = scene(0); PLAYERS[0] = me; ok = SolMagFill.queueFill(me, mag, 'Round')")
ck("local player: vanilla path, transfer actions queued, no direct move", L.eval("VANILLA") == 2 and L.eval("NPE") == 0 and L.eval("bag:contains(mag)") and L.eval("SolNpcTransfer.isLocalPlayer(me)"))
L.execute("PLAYERS[0] = nil")

# 5. a container that is not hers is never touched
L.execute("sol = scene(1); other = mkContainer(nil); foreign = mkItem('Mag', other); r, why = SolNpcTransfer.moveToMain(sol, foreign)")
ck("foreign container: refused, item stays", L.eval("r == false and why == 'not_hers' and other:contains(foreign)"))

# 6. a failed add rolls back: the item returns to the bag
L.execute("sol, bag, mag = scene(1); REJECT_ADD = sol.inv; r, why = SolNpcTransfer.moveToMain(sol, mag); REJECT_ADD = nil")
ck("rollback: item back in the bag, reported", L.eval("r == false and bag:contains(mag) and not sol.inv:contains(mag)"), L.eval("why"))

# 7. guard: restores after an error; other characters keep the previous function while it runs
L.execute("""sol, bag, mag = scene(1); me = mkActor(0); PLAYERS[0] = me; mine = mkItem('Mag', me.inv)
okErr = SolNpcTransfer.guard(sol, function() error('boom') end)
restored = ISInventoryPaneContextMenu.transferIfNeeded == ORIGINAL
okIn = SolNpcTransfer.guard(sol, function() ISInventoryPaneContextMenu.transferIfNeeded(me, mine); ISInventoryPaneContextMenu.transferIfNeeded(sol, mag); return 7 end)""")
ck("guard: error reported, function restored", L.eval("okErr == false and restored"))
ck("guard: other character went to the previous function, she did not", L.eval("VANILLA") == 1 and L.eval("NPE") == 0 and L.eval("sol.inv:contains(mag)"))
ck("guard: returns the function's result", L.eval("(select(2, SolNpcTransfer.guard(sol, function() return 7 end)))") == 7)
L.execute("PLAYERS[0] = nil")

# 8. Living Fellows' verified move is used when present
L.execute("""sol, bag, mag = scene(1); LFCALLS = 0
SurvivorCompanion = { GameplayUtil = { transferItemVerified = function(src, dst, it) LFCALLS = LFCALLS + 1; src:Remove(it); dst:AddItem(it); return true, 'transferred' end } }
r = SolNpcTransfer.moveToMain(sol, mag); SurvivorCompanion = nil""")
ck("LF verified move used", L.eval("r == true and LFCALLS == 1 and sol.inv:contains(mag)"))

# 9. SCNativeActions helper (cut from the patched file): nested magazine, NPC
start = NA.index("-- s149: NPCs cannot use player-index inventory transfer helpers safely.")
end = NA.index("\nlocal function reload(actor, intent, provider)", start)
L.execute("""
SC = { Call = { pack = function(...) return { n = select('#', ...), ... } end, unpack = function(t) return unpack(t, 1, t.n) end } }
function invoke(obj, name, ...) local f = obj and obj[name]; if type(f) ~= 'function' then return false, nil end
  local r = { pcall(f, obj, ...) }; if not r[1] then return false, r[2] end return true, r[2] end
ISInventoryTransferAction = { new = function() return { kind = 'transfer_action' } end }
ISReloadWeaponAction = { BeginAutomaticReload = function(actor, weapon)
  ISInventoryPaneContextMenu.transferIfNeeded(actor, weapon.magazine)
  ISTimedActionQueue.add(ISInsertMagazine:new(actor, weapon, weapon.magazine)) end }
""" + NA[start:end].replace("\r\n", "\n") + "\nfunction invokeReload(a, w) return beginAutomaticReload(a, w) end")
L.execute("sol, bag, mag = scene(1); ok = invokeReload(sol, { magazine = mag })")
ck("BeginAutomaticReload for her: magazine moved directly, insert valid, no NPE, no transfer action",
   L.eval("ok == true and NPE == 0 and #QUEUE == 1 and QUEUE[1].kind == 'insert' and QUEUE[1].valid == true"))
L.execute("me, bag, mag = scene(0); PLAYERS[0] = me; ok = invokeReload(me, { magazine = mag })")
ck("BeginAutomaticReload for the player: unchanged vanilla path", L.eval("ok == true and VANILLA == 1 and bag:contains(mag)"))

shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
