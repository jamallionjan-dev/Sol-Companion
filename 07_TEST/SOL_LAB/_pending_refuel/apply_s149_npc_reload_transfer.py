"""s149 NPC magazine transfer. Exact, idempotent patch for the 0.28.6 client files."""
import os
import sys

CLIENT = sys.argv[1]
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


actions = os.path.join(CLIENT, "SCNativeActions.lua")
edit(actions, 'require "TimedActions/ISTimedActionQueue"',
     'require "TimedActions/ISTimedActionQueue"' + NL + 'require "TimedActions/ISInventoryTransferAction"')
old_reload = '''local function reload(actor, intent, provider)'''
helper = '''-- s149: NPCs cannot use player-index inventory transfer helpers safely.
local function isLocalPlayerActor(actor)
    if actor == nil or type(getSpecificPlayer) ~= "function" then return false end
    local playerNumOk, playerNum = invoke(actor, "getPlayerNum")
    if not playerNumOk or playerNum == nil then return false end
    local ok, player = pcall(getSpecificPlayer, playerNum)
    return ok and player == actor
end

local function beginAutomaticReload(actor, weapon)
    local menu = rawget(_G, "ISInventoryPaneContextMenu")
    local queue = rawget(_G, "ISTimedActionQueue")
    if isLocalPlayerActor(actor) then
        return pcall(ISReloadWeaponAction.BeginAutomaticReload, actor, weapon)
    end
    local authority = rawget(_G, "SolAuthority")
    if type(authority) ~= "table" or type(authority.on) ~= "function"
        or authority.on("npc_reload_transfer") ~= true then
        return pcall(ISReloadWeaponAction.BeginAutomaticReload, actor, weapon)
    end
    if type(menu) ~= "table" or type(menu.transferIfNeeded) ~= "function"
        or type(queue) ~= "table" or type(queue.add) ~= "function"
        or type(ISInventoryTransferAction) ~= "table"
        or type(ISInventoryTransferAction.new) ~= "function" then
        return false, "NPC-safe magazine transfer is unavailable"
    end

    local originalTransfer = menu.transferIfNeeded
    local actorInventoryOk, actorInventory = invoke(actor, "getInventory")
    if not actorInventoryOk or actorInventory == nil then
        return false, "NPC inventory is unavailable"
    end

    local function transferForActor(playerObj, item, ...)
        if playerObj ~= actor then return originalTransfer(playerObj, item, ...) end
        if type(instanceof) ~= "function" then return false end
        local itemOk, isInventoryItem = pcall(instanceof, item, "InventoryItem")
        if not itemOk or isInventoryItem ~= true then return false end
        local sourceOk, source = invoke(item, "getContainer")
        if not sourceOk or source == nil then return false end
        if source == actorInventory then return true end
        local belongsOk, belongsToActor = invoke(source, "isInCharacterInventory", actor)
        if not belongsOk or belongsToActor ~= true then return false end
        local action = ISInventoryTransferAction:new(actor, item, source, actorInventory)
        local addOk, result = pcall(queue.add, action)
        return addOk and result ~= false
    end

    menu.transferIfNeeded = transferForActor
    local results = SC.Call.pack(pcall(ISReloadWeaponAction.BeginAutomaticReload, actor, weapon))
    if menu.transferIfNeeded == transferForActor then menu.transferIfNeeded = originalTransfer end
    return SC.Call.unpack(results)
end

local function reload(actor, intent, provider)'''

action_text = open(actions, encoding="utf-8", newline="").read()
if "beginAutomaticReload(actor, weapon)" not in action_text:
    edit(actions, old_reload, helper)
else:
    print("kept NPC reload helper in SCNativeActions.lua")
edit(actions, 'local ok, failure = pcall(ISReloadWeaponAction.BeginAutomaticReload, actor, weapon)',
     'local ok, failure = beginAutomaticReload(actor, weapon)')

authority = os.path.join(CLIENT, "SolAuthority.lua")
authority_text = open(authority, encoding="utf-8", newline="").read()
if '"npc_reload_transfer"' not in authority_text:
    edit(authority, 'A.FIXES = {' + NL,
         'A.FIXES = {' + NL + '    "npc_reload_transfer", -- s149: transfer nested magazines through the NPC actor' + NL)
else:
    print("kept npc_reload_transfer switch in SolAuthority.lua")

if len(sys.argv) > 2:
    switches = sys.argv[2]
    text = open(switches, encoding="utf-8", newline="").read()
    if not __import__("re").search(r"(?m)^npc_reload_transfer=", text):
        with open(switches, "a", encoding="utf-8", newline="") as output:
            output.write(("" if text.endswith((NL, CRLF)) else CRLF) + "npc_reload_transfer=on" + CRLF)
        print("enabled npc_reload_transfer in LAB switches")
    else:
        print("kept npc_reload_transfer LAB switch")

print("s149 NPC magazine transfer applied")
