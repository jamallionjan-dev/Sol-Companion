-- SolChores.lua - base chores by voice. Sol takes a Living Fellows base role (farmer, woodcutter, ...).
-- Verb sol_role (option = a role id or a plain word such as farm / wood / clean) -> LF command set_base_role.
-- LF's own handler enters base duty with that job, so the work itself is LF's farm / lumber / maintenance code.
-- Honest by construction: the verdict returned is LF's own. Nothing is claimed here that LF did not accept.
-- Debug mode stops the game on any error, even a caught one, so every call below is guarded before it is made.
SolUI = SolUI or {}
local U = SolUI
U.CHORES_VERSION = "0.1.0"
local function log(m) print("[SolChores] " .. tostring(m)) end

-- the role ids LF defines in BaseLife.ROLES (read from SCBaseLife.lua)
local ROLES = {
    generalist = true, guard = true, builder = true, quartermaster = true, medic = true,
    farmer = true, angler = true, chef = true, woodcutter = true, corpsekeeper = true, maintainer = true,
}
-- plain words the brain or the player may use -> the LF role that does that work
local ALIAS = {
    farm = "farmer", farming = "farmer", farmer = "farmer", crops = "farmer", harvest = "farmer", plants = "farmer",
    wood = "woodcutter", lumber = "woodcutter", chop = "woodcutter", logs = "woodcutter", woodcutter = "woodcutter",
    fish = "angler", fishing = "angler",
    clean = "maintainer", maintain = "maintainer", repair = "maintainer",
    cook = "chef", normal = "generalist", general = "generalist",
}

local function LF()
    local sc = SurvivorCompanion
    if type(sc) == "table" then return sc end
    return nil
end

local function normalize(option)
    local o = string.lower(tostring(option or ""))
    o = string.gsub(o, "^%s+", ""); o = string.gsub(o, "%s+$", "")
    if ROLES[o] then return o end
    return ALIAS[o]
end

function U.solRole(option)
    local role = normalize(option)
    if not role then return false, "unknown_role" end
    if role == "farmer" then                                                  -- farming is hers now, not a Living Fellows role
        if type(U.solFarmOrder) ~= "function" then return false, "lf:farm_unavailable" end
        local okF, whyF = U.solFarmOrder("keeper")
        if okF then return true, "base_role_farmer" end
        return false, "lf:" .. tostring(whyF)
    end
    local sol = type(U.solActor) == "function" and U.solActor() or nil
    if sol == nil then return false, "sol_not_available" end
    local SC = LF()
    if not (SC and type(SC.Commands) == "table" and type(SC.Commands.issue) == "function"
            and type(SC.GameplayUtil) == "table" and type(SC.GameplayUtil.idOf) == "function") then
        return false, "lf_unavailable"
    end
    local okId, id = pcall(SC.GameplayUtil.idOf, sol)
    if not okId or type(id) ~= "string" or id == "" then return false, "no_actor_id" end
    local player = getSpecificPlayer and getSpecificPlayer(0) or nil
    local ok, accepted, reason = pcall(SC.Commands.issue, id, "set_base_role", { role = role }, player)
    if not ok then return false, "lf_error" end
    if accepted ~= true then return false, tostring(reason or "refused") end
    log("role " .. role .. " accepted")
    if type(SolAuthority) == "table" then                      -- Sol: this ordered work may run; "normal" ends it
        if role == "generalist" then pcall(SolAuthority.clearWork, "role_generalist") else pcall(SolAuthority.grantWork, role, "sol_role") end
    end
    return true, "base_role_" .. role
end

local function install()
    if U._choresInstalled then return end
    U._choresInstalled = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_role" then
            local ok, a, b = pcall(U.solRole, option)
            if not ok then return false, "chores_error" end
            return a, b
        end
        return base(id, option)
    end
    log("verb installed v" .. U.CHORES_VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(install) end
log("ready v" .. U.CHORES_VERSION)
