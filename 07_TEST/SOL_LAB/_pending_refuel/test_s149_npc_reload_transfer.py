"""Exercise the exact s149 reload helper with player, NPC, and nested-magazine fixtures."""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
INTEGRATION = os.path.join(ROOT, "01_WORK", "INTEGRATION", "SOL_2026-11-14_0.28.6_ERRORFIX", "Sol", "42", "media", "lua", "client")
CANDIDATE = os.path.join(ROOT, "01_WORK", "RELEASE", "SOL_2026-11-14_0.28.6", "Sol", "42", "media", "lua", "client")
FAIL = []
PASS = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(detail)) if detail and not ok else ""))
    (PASS if ok else FAIL).append(name)


# Check the idempotent installer against pristine candidate files in a temp directory.
tmp = tempfile.mkdtemp(prefix="s149_reload_")
try:
    client = os.path.join(tmp, "client")
    os.makedirs(client)
    for name in ("SCNativeActions.lua", "SolAuthority.lua"):
        shutil.copy(os.path.join(CANDIDATE, name), os.path.join(client, name))
    switches = os.path.join(tmp, "SolFixes_LAB.txt")
    with open(switches, "w", encoding="ascii", newline="") as output:
        output.write("existing=on\r\n")
    applier = os.path.join(HERE, "apply_s149_npc_reload_transfer.py")
    first = subprocess.run([sys.executable, applier, client, switches], capture_output=True, text=True)
    snap = {name: open(os.path.join(client, name), "rb").read() for name in ("SCNativeActions.lua", "SolAuthority.lua")}
    sw = open(switches, "rb").read()
    second = subprocess.run([sys.executable, applier, client, switches], capture_output=True, text=True)
    snap2 = {name: open(os.path.join(client, name), "rb").read() for name in ("SCNativeActions.lua", "SolAuthority.lua")}
    ck("installer applies to candidate files", first.returncode == 0, first.stdout + first.stderr)
    ck("installer is idempotent", second.returncode == 0 and snap == snap2 and sw == open(switches, "rb").read(), second.stdout + second.stderr)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

source = open(os.path.join(INTEGRATION, "SCNativeActions.lua"), encoding="utf-8").read()
start = source.index("-- s149: NPCs cannot use player-index inventory transfer helpers safely.")
end = source.index("\nlocal function reload(actor, intent, provider)", start)
helper = source[start:end]
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("""
SC = { Call = {
  pack = function(...) return { n = select('#', ...), ... } end,
  unpack = function(t) return unpack(t, 1, t.n) end
} }
function invoke(obj, name, ...)
  local f = obj and obj[name]
  if type(f) ~= 'function' then return false, nil end
  local r = { pcall(f, obj, ...) }
  if not r[1] then return false, r[2] end
  return true, r[2]
end
function instanceof(item, class) return class == 'InventoryItem' and item and item.inventoryItem == true end
SolAuthority = { on = function(name) return name == 'npc_reload_transfer' and SWITCH end }
SWITCH = true
local originalTransfers, queued = 0, {}
ISInventoryPaneContextMenu = { transferIfNeeded = function(actor, item) originalTransfers = originalTransfers + 1; return true end }
ISTimedActionQueue = { add = function(action) queued[#queued + 1] = action; return true end }
ISInventoryTransferAction = { new = function(self, actor, item, src, dst) return { kind='transfer', actor=actor, item=item, src=src, dst=dst } end }
ISReloadWeaponAction = { BeginAutomaticReload = function(actor, weapon)
  local ok = ISInventoryPaneContextMenu.transferIfNeeded(actor, weapon.magazine)
  if ok then queued[#queued + 1] = { kind='insert', actor=actor, item=weapon.magazine } end
end }
function makeActor(index)
  local actor = { inventory = {} }
  function actor:getPlayerNum() return index end
  function actor:getInventory() return self.inventory end
  return actor
end
function makeItem(container)
  return { inventoryItem=true, getContainer=function() return container end }
end
function clearQueue() queued = {}; originalTransfers = 0 end
function queueState() return queued, originalTransfers end
""")
L.execute(helper + "\nfunction invokeReload(actor, weapon) return beginAutomaticReload(actor, weapon) end")

# Player path stays on the original transfer implementation.
L.execute("player = makeActor(0); getSpecificPlayer = function(n) if n == 0 then return player end end; playerWeapon = { magazine = makeItem(player.inventory) }")
r = L.eval("{ invokeReload(player, playerWeapon) }")
ck("player reload keeps the vanilla/Gunworks path", r[1] is True and L.eval("select(2, queueState())") == 1)
ck("player transfer hook is restored", L.eval("ISInventoryPaneContextMenu.transferIfNeeded ~= nil"))

# NPC magazine already in the top-level inventory needs insertion but no transfer action.
L.execute("clearQueue(); sol = makeActor(1); getSpecificPlayer = function(n) return nil end; topWeapon = { magazine = makeItem(sol.inventory) }")
r = L.eval("{ invokeReload(sol, topWeapon) }")
ck("NPC top-level magazine reload completes", r[1] is True)
ck("NPC top-level magazine queues insertion only", L.eval("(function() local q = queueState(); return #q == 1 and q[1].kind == 'insert' end)()"))
ck("NPC transfer hook is restored", L.eval("ISInventoryPaneContextMenu.transferIfNeeded ~= nil"))

# Nested backpack magazine is transferred with the NPC actor, then inserted in order.
L.execute("""
clearQueue()
nested = { isInCharacterInventory = function(self, actor) return actor == sol end }
nestedWeapon = { magazine = makeItem(nested) }
""")
r = L.eval("{ invokeReload(sol, nestedWeapon) }")
ck("nested magazine transfer is queued for Sol", r[1] is True and L.eval("(function() local q = queueState(); return #q == 2 and q[1].kind == 'transfer' and q[1].actor == sol end)()"))
ck("nested transfer precedes magazine insertion", L.eval("(function() local q = queueState(); return q[1].kind == 'transfer' and q[2].kind == 'insert' end)()"))
ck("NPC reload never calls player-index transfer helper", L.eval("select(2, queueState()) == 0"))

print("SUMMARY pass=%d fail=%d" % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
