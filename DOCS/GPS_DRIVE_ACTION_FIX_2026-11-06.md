# GPS drive action fix — 2026-11-06

## Evidence from the reported run

- The log at `C:\Users\JAMAL\Zomboid\Logs\2026-11-06_19-09_DebugLog.txt` records two `take the wheel -> true moving_to_wheel` results and GPS route previews.
- It contains no `driving to ...` or `drive refused ...` record for those previews. A later `follow` order superseded the pending wheel task.
- Static inspection found `sol_drive` advertised in the Sol action catalog, but missing from `U.runAction`. The separate `sol_take_wheel` action only requested the driver seat.

## Change

- Implemented the `sol_drive` dispatch through SolOrders using the currently selected Sol GPS destination.
- If Sol is a passenger, the existing verified vehicle state machine handles exiting, approaching the driver door, and taking the driver seat.
- When the player is nearby, the normal trip waits for them to board; the response distinguishes this pending state from a car that has started moving.
- No selected GPS destination returns `no_destination`. Taking the wheel and starting a route now have distinct action descriptions.
- Updated the canonical launch folder and Bridge24 candidate; refreshed the canonical package manifest.

## Verification status

- Lua 5.1 parser: 225 client files, zero errors, one pre-existing warning in `SCNavigation.lua`.
- Runtime: still pending. Pass criteria are verified Sol driver seat, GPS drive-start event, vehicle movement toward the selected destination, and arrival or a truthful failure reason.
