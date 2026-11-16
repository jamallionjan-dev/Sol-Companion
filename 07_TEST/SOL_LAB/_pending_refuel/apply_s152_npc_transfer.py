"""s152 NPC-safe transfers for SolMagFill and SCNativeActions (switch npc_reload_transfer, already registered by s149).
usage: apply_s152_npc_transfer.py <client dir>
- copies SolNpcTransfer.lua next to this script into the client dir
- SolMagFill.lua: transferIfNeeded / queueFill go through SolNpcTransfer for an actor that is not the local player
- SCNativeActions.lua: beginAutomaticReload uses SolNpcTransfer.guard (direct verified move, lists of rounds included)
Exact old->new strings; refuses when a string is not found exactly once; prints "kept" when already applied."""
import os
import shutil
import sys

CLIENT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
NL = chr(10)
CRLF = chr(13) + chr(10)


def edit(path, old, new):
    text = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in text else NL
    old = old.replace(NL, nl)
    new = new.replace(NL, nl)
    if new in text:
        print("kept " + os.path.basename(path))
        return
    if text.count(old) != 1:
        raise RuntimeError((os.path.basename(path), "expected one exact source block", text.count(old)))
    open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new))
    print("edited " + os.path.basename(path))


src = os.path.join(HERE, "SolNpcTransfer.lua")
dst = os.path.join(CLIENT, "SolNpcTransfer.lua")
if os.path.exists(dst) and open(dst, "rb").read() == open(src, "rb").read():
    print("kept SolNpcTransfer.lua")
else:
    shutil.copyfile(src, dst)
    print("copied SolNpcTransfer.lua")

mag = os.path.join(CLIENT, "SolMagFill.lua")
edit(mag,
     '''local function transferIfNeeded(actor, item)
    local CM = g("ISInventoryPaneContextMenu")
    if type(CM) == "table" and type(CM.transferIfNeeded) == "function" then pcall(CM.transferIfNeeded, actor, item) end
end
''',
     '''-- s152: for her (not the local player) the player-only transfer helpers throw; SolNpcTransfer moves her own items directly
local function npcTransfer(actor)
    local T = g("SolNpcTransfer")
    if type(T) ~= "table" or type(T.on) ~= "function" or type(T.guard) ~= "function" or type(T.transfer) ~= "function" then return nil end
    if T.on() ~= true or T.isLocalPlayer(actor) then return nil end
    return T
end
local function transferIfNeeded(actor, item)
    local T = npcTransfer(actor)
    if T ~= nil then pcall(T.transfer, actor, item); return end
    local CM = g("ISInventoryPaneContextMenu")
    if type(CM) == "table" and type(CM.transferIfNeeded) == "function" then pcall(CM.transferIfNeeded, actor, item) end
end
local function guarded(actor, fn, ...)
    local T = npcTransfer(actor)
    if T ~= nil then return T.guard(actor, fn, ...) end
    return pcall(fn, ...)
end
''')
edit(mag,
     '''        local ok, n = pcall(MG.reloadMagazine, actor, mag)
        return ok and (num(n) or 0) > 0''',
     '''        local ok, n = guarded(actor, MG.reloadMagazine, actor, mag)
        return ok and (num(n) or 0) > 0''')
edit(mag,
     '''    local ok, add = pcall(CM.transferBullets, actor, kind, cur, max)''',
     '''    local ok, add = guarded(actor, CM.transferBullets, actor, kind, cur, max)''')

actions = os.path.join(CLIENT, "SCNativeActions.lua")
edit(actions,
     '''        return pcall(ISReloadWeaponAction.BeginAutomaticReload, actor, weapon)
    end
    if type(menu) ~= "table" or type(menu.transferIfNeeded) ~= "function"
        or type(queue) ~= "table" or type(queue.add) ~= "function"''',
     '''        return pcall(ISReloadWeaponAction.BeginAutomaticReload, actor, weapon)
    end
    -- s152: direct verified move of her own items (single items and lists of rounds), no player-only transfer action
    local npcTransfer = rawget(_G, "SolNpcTransfer")
    if type(npcTransfer) == "table" and type(npcTransfer.guard) == "function" then
        return npcTransfer.guard(actor, ISReloadWeaponAction.BeginAutomaticReload, actor, weapon)
    end
    if type(menu) ~= "table" or type(menu.transferIfNeeded) ~= "function"
        or type(queue) ~= "table" or type(queue.add) ~= "function"''')

print("s152 NPC-safe transfers applied")
