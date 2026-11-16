# Sol / Living Fellows Capability Map

## Rule
Sol Mind plans goals. Living Fellows owns physical execution. A planner may only use a capability listed here and mapped to real source. Offline proof never upgrades Java/native behavior to Runtime PASS.

## Existing Living Fellows behavior discovered

### World scavenging
Owner: `SCEncounter.lua`
- scans loaded world squares around the actor with bounded budgets;
- discovers containers/corpses and remembers/cools failed or exhausted containers;
- closed-container choice uses honest clues such as room affinity and distance, not hidden contents;
- after opening, item scoring is delegated to `SCLogistics.itemNeedScore()`;
- `scavengeRequestedCategory` can constrain a mission to a supply category.

### Weapon / ammunition need
Owner: `SCLogistics.lua` + `SCEncounter.lua`
- when no usable weapon exists, weapon need is `TIER.desperate`;
- Encounter automatically marks `wanted.weapon=true` for an unarmed companion;
- ammunition becomes `TIER.important` when the companion carries a firearm;
- this is currently ambient/mission-scavenge behavior, not yet a dedicated rescue-preparation transaction.

### Weapon selection, equip and reload
Owner: `SCCombat.lua`
- `weaponAvailability()` distinguishes carried weapons from weapons usable now;
- `chooseWeapon()` applies `weaponPriority` and tactical distance/pressure;
- `equipPreferred()` equips a selected owned weapon through verified action handling;
- `hasReloadAmmo()` matches the weapon's real magazine/ammo type and rejects incompatible/empty sources;
- combat emits a reload action when a ranged weapon is dry but compatible reload supply exists.

### Vehicle boarding
Owner: `SCVehicle.lua`
- passenger seats and driver seat are transactional and verified;
- driver seat zero is only permitted through `boardDriver()` / `driverSeat=true`;
- native entry/exit has verification and rollback.

### Vehicle driving
Owner: `SCDriving.lua` + native `SCBridge`
- route planning/following uses Living Fellows driving and ExpeditionRoute;
- native `driveStart` ownership must be acquired while the local player is outside the vehicle;
- offline tests can validate the Lua ownership boundary and route encoding;
- actual steering, vehicle physics, KI5 compatibility and Java bridge behavior are Runtime-only.

### Sol solo rescue driving
Owner: `SolGPS.lua` (v0.8.0)
- `solo=true` lets the planner request a route while the player is remote;
- normal trips still preserve passenger-waiting behavior;
- this layer is Offline PASS only until in-game driving is proven.

## Design gap to solve next
The old mod has the raw scavenging/loadout/combat behaviors, but it does not expose a single mission API such as:

`prepare_for_mission(type='emergency_rescue', deadline=..., threat=...)`

The correct extension is an adapter/orchestrator that asks existing systems for weapons/ammunition/loadout and waits for verified results. It should not reimplement looting or combat in Sol Mind.

## Required proof ladder
1. Source contract PASS
2. Lua 5.1 syntax PASS
3. Real-Lua behavior contract PASS where feasible
4. Sol Mind / planner regression PASS
5. WORK/LIVE parity PASS
6. Runtime proof in Project Zomboid for native/visual/physics behaviors
