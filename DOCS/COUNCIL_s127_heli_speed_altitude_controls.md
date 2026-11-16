# s127 review — helicopter GPS speed and altitude controls

Date: 2026-11-13

## Confirmed behavior and defect

- `SolGPS.lua` rendered either the speed row or the altitude row. In helicopter mode the altitude buttons replaced speed controls, exactly as Jamal reported.
- AviationCore `FlightEngine.lua` derives the target forward speed from `AviationCoreDebug.flightMaxForwardSpeed` (m/s) when the forward input is held. Its default is 18 m/s. The direct-air GPS controller supplies that forward input while traveling toward a destination.
- The existing car speed action routes through `SurvivorCompanion.Driving.setSpeed`; that API does not control AviationCore helicopter motion.

## Engineer

- Keep the regular speed pills at the top row for all vehicles. Render Low/Medium/High altitude pills at y=36 only when `SolHeliGPS.isSolInHelicopter()` is true.
- On helicopter speed selection, apply the selected km/h as a temporary AviationCore forward-speed limit (`km/h / 3.6` m/s). Tiers are 20/40/65 km/h, matching the existing Sol GPS choices. Preserve the previous debug value and restore it at stop, completed landing, or feature teardown. If the AviationCore debug configuration is unavailable, return an explicit nonfatal result and keep flight safe.
- Car speed selection continues using the existing LF `Driving.setSpeed` path. No GPS route or altitude logic is shared with car driving.
- Keep the existing `heli_gps` authority switch; no new speech action or model-card change is needed.

## Devil's Advocate

- Mutating a shared AviationCore tuning table could affect another controller if not restored. Scope the override to active Sol helicopter control; restore the exact prior value, including nil, whenever control ends. Test start failure, speed changes, stop, and landing.
- Changing the speed limit does not instantly set a measured ground velocity; AviationCore's controller accelerates toward the selected target. In-game acceptance must compare speed telemetry after the transient, not expect immediate exact km/h.
- A missing `AviationCoreDebug` table must not crash or block native engine startup. The altitude row is restricted to helicopter mode so car driving UI remains unchanged.

## Strategist / acceptance

- Install both changed Lua files together in SOL_LAB only, with a dated backup, after offline tests and a no-process check.
- Gate the launch with `launch_lab.ps1 -CheckOnly`; do not touch MAIN, release, Steam/Workshop files, or the player's main save.
- In world, verify: car shows speed only; helicopter shows speed on row one and altitude below; each speed changes the AviationCore target; altitude selection remains independent; GPS destination flight, stop, and landing still function; prior speed setting is restored after stop/landing; no new Lua/AviationCore errors.
- Offline tests and a deterministic mock prove source behavior only. Real helicopter speed and UI appearance remain pending live review.
