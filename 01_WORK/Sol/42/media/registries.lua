-- Sol-vendored SPNCC appearance IDs; retained for existing saved Face_* and Detail_* items.
-- When the full SPNCC mod is active, it owns these registry IDs. Registering
-- them again returns invalid duplicate ItemBodyLocation values in Build 42.21,
-- which can poison Human's BodyLocationGroup and crash model updates every frame.
local function activatedContains(modId)
    if type(getActivatedMods) ~= "function" then return false end
    local ok, active = pcall(getActivatedMods)
    if not ok or not active then return false end
    for _, id in ipairs({ modId, "\\" .. modId }) do
        local containsOk, found = pcall(function() return active:contains(id) end)
        if containsOk and found == true then return true end
    end
    return false
end

if activatedContains("SPNCC") then
    print("[SolAppearance] using SPNCC-owned registries; skipped duplicate Sol registration")
    return
end

SPNCC = SPNCC or {}
SPNCC.ItemTag = SPNCC.ItemTag or {}
SPNCC.ItemBodyLocation = SPNCC.ItemBodyLocation or {}
local tagNames = { "RemoveOnZombification", "CanHaveBlood", "AppearanceChanger", "AppearanceUnlocker", "Face", "BodyDetail" }
for _, name in ipairs(tagNames) do
    local id = "SPNCC:" .. name
    local tag = ItemTag.get(ResourceLocation.of(id))
    if not tag then
        tag = ItemTag.register(id)
    end
    SPNCC.ItemTag[name] = tag
end
local locationNames = { "Blank", "BodyHair", "Muscle", "Face", "BodyDetail", "StubbleBeard", "StubbleHead", "BodyDetail2", "Face_Model" }
for _, name in ipairs(locationNames) do
    local id = "SPNCC:" .. name
    local location = ItemBodyLocation.get(ResourceLocation.of(id))
    if not location then
        location = ItemBodyLocation.register(id)
    end
    SPNCC.ItemBodyLocation[name] = location
end
