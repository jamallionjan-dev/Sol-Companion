-- SolFixLook.lua - Sol fix pack v1.0
-- 1) Diagnostics: every spawn-gate and save decision is written to console.txt
--    with the [Sol-Diag] tag, so a second Sol or a lost book can be traced.
-- 2) Fixed appearance: Sol's face and hair are captured once, then reapplied on
--    every spawn so she always matches the mod's thumbnail.
-- ASCII-only source. No game file is patched from here; hooks are installed
-- defensively and every native call is wrapped in pcall.

SolFixLook = SolFixLook or {}
local M = SolFixLook
M.VERSION = "1.0.0"

-- ---------------------------------------------------------------- diagnostics
function M.diag(area, message)
    print("[Sol-Diag][" .. tostring(area) .. "] " .. tostring(message))
end

local function callm(object, name, ...)
    if object == nil or type(name) ~= "string" then return false, nil end
    local method = nil
    local okIndex = pcall(function() method = object[name] end)
    if not okIndex or type(method) ~= "function" then return false, nil end
    local okCall, result = pcall(method, object, ...)
    if not okCall then return false, nil end
    return true, result
end
M.call = callm

-- ---------------------------------------------------------------- fixed look
-- Filled in once M.captureLook has printed a real survivor's values.
-- While LOOK.hairModel is empty, Sol keeps whatever the factory gave her and
-- this module only reports what she looks like.
M.LOOK = {
    hairModel = "",
    hairColor = nil,      -- { r = 0..1, g = 0..1, b = 0..1 }
    skinTexture = "",
    beardModel = "",
}

function M.describeLook(actor)
    local okVisual, visual = callm(actor, "getVisual")
    if not okVisual or visual == nil then return nil, "visual_unavailable" end
    local parts = {}
    local okHair, hair = callm(visual, "getHairModel")
    parts.hairModel = okHair and tostring(hair) or "?"
    local okSkin, skin = callm(visual, "getSkinTextureName")
    parts.skinTexture = okSkin and tostring(skin) or "?"
    local okBeard, beard = callm(visual, "getBeardModel")
    parts.beardModel = okBeard and tostring(beard) or "?"
    local okColor, color = callm(visual, "getHairColor")
    if okColor and color ~= nil then
        local okR, r = callm(color, "getRedFloat")
        local okG, g = callm(color, "getGreenFloat")
        local okB, b = callm(color, "getBlueFloat")
        if okR and okG and okB then
            parts.hairColor = { r = r, g = g, b = b }
        end
    end
    return parts
end

function M.captureLook(actor)
    local look, reason = M.describeLook(actor)
    if look == nil then
        M.diag("look", "capture failed: " .. tostring(reason))
        return nil
    end
    local color = look.hairColor
    M.diag("look", "current hairModel=" .. tostring(look.hairModel)
        .. " skin=" .. tostring(look.skinTexture)
        .. " beard=" .. tostring(look.beardModel)
        .. " hairColor=" .. (color and (string.format("%.3f/%.3f/%.3f", color.r, color.g, color.b)) or "?"))
    return look
end

function M.applyLook(actor)
    local wanted = M.LOOK
    if type(wanted) ~= "table" or type(wanted.hairModel) ~= "string"
        or wanted.hairModel == "" then
        return false, "look_not_configured"
    end
    local okVisual, visual = callm(actor, "getVisual")
    if not okVisual or visual == nil then return false, "visual_unavailable" end
    local changed = false
    local okHair = callm(visual, "setHairModel", wanted.hairModel)
    changed = changed or okHair
    if type(wanted.skinTexture) == "string" and wanted.skinTexture ~= "" then
        local okSkin = callm(visual, "setSkinTextureName", wanted.skinTexture)
        changed = changed or okSkin
    end
    if type(wanted.beardModel) == "string" then
        callm(visual, "setBeardModel", wanted.beardModel)
    end
    local color = wanted.hairColor
    if type(color) == "table" and type(ImmutableColor) == "table" then
        local okNew, made = pcall(function()
            return ImmutableColor.new(color.r, color.g, color.b, 1)
        end)
        if okNew and made ~= nil then
            callm(visual, "setHairColor", made)
            changed = true
        end
    end
    if changed then callm(actor, "resetModelNextFrame") end
    M.diag("look", "applied fixed look hairModel=" .. tostring(wanted.hairModel))
    return changed
end

-- Called right after a successful Sol spawn (patched into SCSpawn.solPulse).
function M.onSolSpawned()
    if type(rawget(_G, "SolLife")) == "table" and type(SolLife.onSpawned) == "function" then pcall(SolLife.onSpawned) end
    local SC = SurvivorCompanion
    if type(SC) ~= "table" or type(SC.Registry) ~= "table"
        or type(SC.Registry.living) ~= "function" then
        M.diag("spawn", "registry unavailable right after spawn")
        return
    end
    local okList, living = pcall(SC.Registry.living)
    if not okList or type(living) ~= "table" or living[1] == nil then
        M.diag("spawn", "no living record right after spawn")
        return
    end
    local record = living[1]
    local actor = type(record) == "table" and record.actor or record
    M.diag("spawn", "Sol spawned; living count=" .. tostring(#living))
    M.captureLook(actor)
    M.applyLook(actor)
end

-- ------------------------------------------------- persistence save tracing
local wrapped = false
function M.installPersistenceTrace()
    if wrapped then return true end
    local SC = SurvivorCompanion
    local persistence = type(SC) == "table" and SC.Persistence or nil
    if type(persistence) ~= "table" then return false end
    if type(persistence.captureRecord) == "function" then
        local original = persistence.captureRecord
        persistence.captureRecord = function(record, vehicleState)
            local snapshot, reason = original(record, vehicleState)
            local id = type(record) == "table" and tostring(record.id) or "?"
            if snapshot == nil then
                M.diag("save", "captureRecord REFUSED id=" .. id .. " reason=" .. tostring(reason))
            else
                M.diag("save", "captureRecord ok id=" .. id)
            end
            return snapshot, reason
        end
        wrapped = true
    end
    if wrapped then M.diag("save", "persistence trace installed") end
    return wrapped
end

if type(Events) == "table" and type(Events.OnGameStart) == "table"
    and type(Events.OnGameStart.Add) == "function" then
    Events.OnGameStart.Add(function()
        pcall(M.installPersistenceTrace)
        M.diag("boot", "Sol fix pack " .. M.VERSION .. " active")
    end)
end

return M
