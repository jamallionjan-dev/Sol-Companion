# What the game and Living Fellows actually do (read from their files, 2026-11-08)

Paths are under `steamapps/common/ProjectZomboid/media` (vanilla) or the mod's `lua/client` (LF, `SC*.lua`).

## Refuelling
- `lua/client/Vehicles/ISUI/ISVehiclePartMenu.lua`, `getNearbyFuelPump`: a pump counts when it is within 2 squares in x and y of the square under `getAreaCenter(part:getArea())`. `onPumpGasoline` exits the car, queues `ISPathFindAction:pathToVehicleArea`, then `ISRefuelFromGasPump`.
- `lua/shared/Vehicles/TimedActions/ISRefuelFromGasPump.lua`: `isValid` is only `vehicle:isInArea(part:getArea(), character)`. `getDuration` is `takeLitres * 50`. `update` sets the tank and the pump by job delta; pumps start at 100 units, 8 units per jerry can.
- `BaseVehicle.isInArea(String, IsoGameCharacter)` tests her exact position against the script's small `area GasTank` rectangle. It is smaller than one square, and Sol's walker stops on whole squares. So `SolRefuelAtCap` copies the vanilla action's functions and accepts arm's length (1.9) as well.
- The walker's refusal `invalid_destination` comes from `SCCommands.lua: handleMoveTo` via `GameplayUtil.isSquareFree`. The old target was the square under the cap, which is under the van.

## Timed actions on a companion
- `lua/client/TimedActions/ISTimedActionQueue.lua` and `ISBaseTimedAction:begin`: `character:StartAction(LuaTimedActionNew)`.
- LF runs vanilla timed actions on companions through the same queue: `SCNativeActions.lua` (near 1584, and the note at 1448 that `SCNativeCompanion` defers `StartAction` until the Lua call unwinds), `SCMedicalUI.lua:210`, `SCChefWork.lua`, `SCFishing.lua:806`. So the action is expected to run on her. **Not yet seen in game.** If it does not, `SolFuel` makes the action's own calls at its pace.

## Being seated again
- `SCDecision.lua` near 927: with the player in a vehicle, follow boards the companion unless `SolAuthority.ownsCarFlow` or `heldOut` says otherwise. `heldOut` was only set by the player's own "get out" order, so the errand's exit was undone 83 frames later (log f:18732 exit, f:18815 board). The errand now holds her out.

## Respawn and clothes
- `SCSpawn.solPulse` makes a new Sol from a bare profile. `SCPersistence.lua` near 2248 keeps no snapshot of a dead companion.
- The old logs do not show where the kit on the last respawn came from, so the cause is **unproven**. `SolDress` now strips any new id regardless of source.
- `media/clothing/clothingItems/*.xml`, `m_Masks` hide the body under an item: T-shirts have none; a bullet vest has 12 only; `Jacket_WhiteTINT`, `Jacket_Padded`, `HoodieUP_WhiteTINT` have 12, 13, 14, 3, 5.

## Numbers that are not from any one place
`GAP_MIN/MAX` (walking gap), `CAR_NEAR` (a car near a pump), `PARK_OFFSETS` (three tiles each way round a pump, last resort). `fullLockCurvature` in `SolNavTrack` is measured car behaviour at speed, not a place or route. Coordinates of his station appear only in tests, as comparisons.
