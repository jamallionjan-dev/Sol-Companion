-- SPDX-License-Identifier: MIT
-- Isolate the Inspect Weapon / Gunworks constructor signature mismatch.
-- Inspect Weapon passes its action duration as argument four; Gunworks uses
-- that same slot for an outcome full type and otherwise expects a string.
local M = {}

local function install()
    if type(ISUpgradeWeapon) ~= "table"
            or type(ISUpgradeWeapon.new) ~= "function" then
        return false
    end

    local universal
    local loaded, result = pcall(require, "WeaponSystems/Utils/UniversalAttachment")
    if loaded and type(result) == "table" then
        universal = result
    end
    if type(universal) ~= "table"
            or type(universal.CanInstallOutcome) ~= "function" then
        return false
    end

    if ISUpgradeWeapon._solGunworksCompatInstalled then
        return true
    end

    local originalNew = ISUpgradeWeapon.new
    ISUpgradeWeapon.new = function(self, character, weapon, part, outcomeFullType)
        -- Inspect Weapon supplies 50 here as a legacy action duration. The
        -- vanilla constructor already computes its own duration, and Gunworks
        -- must receive nil so its normal attachment validation path is used.
        if type(outcomeFullType) == "number" then
            outcomeFullType = nil
        end
        return originalNew(self, character, weapon, part, outcomeFullType)
    end
    ISUpgradeWeapon._solGunworksCompatInstalled = true
    print("[Sol] Gunworks/Inspect Weapon constructor compatibility installed")
    return true
end

M.install = install

if Events and Events.OnGameBoot and type(Events.OnGameBoot.Add) == "function" then
    Events.OnGameBoot.Add(install)
end

return M
