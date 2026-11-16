-- Minimal SPNCC body slots used by Sol's vendored female body and details.
require("NPCs/BodyLocations")
local group = BodyLocations.getGroup("Human")
local names = {
    "SPNCC:Face_Model", "SPNCC:BodyDetail2", "SPNCC:StubbleHead",
    "SPNCC:StubbleBeard", "SPNCC:BodyHair", "SPNCC:BodyDetail",
    "SPNCC:Face", "SPNCC:Muscle", "SPNCC:Blank",
}
local locations = {}
for _, name in ipairs(names) do
    -- Item locations declared by SolIntegratedAppearance.txt are already in the
    -- registry when this Lua file runs. Reuse them; register only if a future
    -- content variant omits the script declaration.
    local location = ItemBodyLocation.get(ResourceLocation.of(name))
    if not location then
        location = ItemBodyLocation.register(name)
    end
    locations[name] = location
    group:getOrCreateLocation(location)
    group:moveLocationToIndex(location, 0)
end
group:setMultiItem(locations["SPNCC:BodyDetail"], true)
group:setMultiItem(locations["SPNCC:BodyDetail2"], true)
