-- SolSkin.lua (v0.5.0) - the Living Fellows window is never shown.
-- Every Living Fellows entry point (Sol panel buttons, right-click "orders", hotkey toggle, status, startup)
-- opens the Sol pages window instead (SolPages.lua). The hidden LF root only serves as the data source.
SolUI = SolUI or {}
local U = SolUI
U.SKIN_VERSION = "0.5.0"
local function log(m) print("[SolUI] " .. tostring(m)) end
local function LF() local sc = SurvivorCompanion; return type(sc) == "table" and sc or nil end

local function hide(UI)
    if UI.instance then UI.instance:setVisible(false) end
    if UI.launcher then UI.launcher:setVisible(false) end
end

function U.installSkin()
    local SC = LF()
    if not SC or type(SC.UI) ~= "table" then log("Living Fellows UI not found"); return false end
    local UI = SC.UI
    if UI.solSkinInstalled then return true end
    UI.solSkinInstalled = true
    UI.solOrigEnsure = UI.ensureControl
    UI.ensureControl = function(...)
        local root = UI.solOrigEnsure(...)
        if root then root:setVisible(false) end
        if UI.launcher then UI.launcher:setVisible(false) end
        return root
    end
    UI.showCollapsedLauncher = function(root) hide(UI); return nil end
    UI.restoreStartupVisibility = function() hide(UI); return true end
    UI.open = function(tab, companionId, description)
        local t = tab
        if UI.normalizeTab then local ok, n = pcall(UI.normalizeTab, tab); if ok and n then t = n end end
        if t == "talk" then if U.openChat then U.openChat() end; return UI.instance end
        if description and not t then t = "status" end
        if U.openPage then U.openPage(t or "status", companionId) end
        hide(UI)
        return UI.instance
    end
    UI.showStatus = function(description) return UI.open("status", type(description) == "table" and (description.id or description.companionId) or nil, description) end
    UI.toggle = function()
        if U.page and U.page:isVisible() then U.closePage() elseif U.togglePanel then U.togglePanel() end
        return UI.instance
    end
    hide(UI)
    log("Living Fellows window replaced by Sol pages v" .. U.SKIN_VERSION)
    return true
end

function U.openTab(tab, companionId)
    if U.openPage then return U.openPage(tab, companionId) end
    return false
end
function U.onLangChanged() if U.page and U.page:isVisible() then U.page:refresh(true) end end

U.installSkin()
if Events and Events.OnGameStart then Events.OnGameStart.Add(function() U.installSkin(); local SC = LF(); if SC and SC.UI then hide(SC.UI) end end) end
