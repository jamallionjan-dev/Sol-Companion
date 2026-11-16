-- SPDX-License-Identifier: MIT

local SC = SurvivorCompanion
SC.Oddballs = SC.Oddballs or {}
local Oddballs = SC.Oddballs

-- Sol profile: authored oddball encounters are disabled.
-- This compatibility surface intentionally preserves the public API expected by
-- Living Fellows modules without loading the original 4005-line coordinator.

function Oddballs.nativeBedFootEntry(bed, actor) return nil end
function Oddballs.findKnightSite(player, stage, previous) return nil end
function Oddballs.notePlayerKill(player, zombie) return false end
function Oddballs.findRoamerLandmark(player, previous, requireDusk, minSeparation) return nil end
function Oddballs.findEbbSite(player, previous) return nil end
function Oddballs.isKnownId(id) return false end
function Oddballs.definition(id) return nil end
function Oddballs.state(group) return group and group.oddball or nil end
function Oddballs.groupForActor(actor) return nil end
function Oddballs.setZombieShelter(actor, enabled) return false end
function Oddballs.isZombieIgnored(actor) return false end
function Oddballs.avoidsZombieCombat(actor, group) return false end
function Oddballs.intentFor(actor, player, snapshot, group) return nil end
function Oddballs.update(actor, player, runtime, intent, group) return false end
function Oddballs.pulseGroup(group, player, current) return false end
function Oddballs.onZombieDead(zombie, attacker, player) return false end
function Oddballs.onCharacterDeath(actor) return false end
function Oddballs.noteChallengeKill(actor, zombie) return false end
function Oddballs.storyAction(groupId, action, player, payload) return false end
function Oddballs.sealedDoorGroup(object, player) return nil end
function Oddballs.menuOptions(group, player) return {} end
function Oddballs.canRecruit(group) return false end
function Oddballs.spawned(group, actor) return false, 'oddballs_disabled' end
function Oddballs.spawnFailed(group, reason) return false end
function Oddballs.retire(group, reason) return false end
function Oddballs.pulse(player, current) return false, 'oddballs_disabled' end
function Oddballs.debugSpawnRandom(player) return false, 'oddballs_disabled' end
function Oddballs.export() return { version = 1, groups = {} } end
function Oddballs.restore(document) return true end
function Oddballs.reset() return true end

Oddballs._otherRoomTileForTests = function() return nil end
Oddballs._nearbyTruckForTests = function() return nil end
Oddballs._auxiliaryKitchenPositionsForTests = function() return {} end
Oddballs._siteForResidentForTests = function() return nil end
