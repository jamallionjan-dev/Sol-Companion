# s135 — Helicopter full-route simulation and landing sequence (2026-11-13)

## Acceptance target

Before opening Project Zomboid, verify the LAB controller end to end: move Sol from a passenger seat to seat 0, start the helicopter through AviationCore's authorized start path, wait for engine readiness, climb to the selected band, reach multiple nearby GPS markers, descend at the selected landing point, stop the engine, and leave through the companion's existing vehicle-exit service.

## Evidence inventory

- The last live run logged Sol in pilot seat 0, the player in seat 1, an accepted GPS destination, learned UH-1B operating knowledge, an authorized native engine-start request, and engine readiness.
- That run did not log the FlightRuntime pilot handoff, any GPS input, a world-altitude transition, or GPS guidance. The helicopter did not move. This is the runtime failure being addressed; seat acquisition and engine start alone are not a pass.
- Installed AviationCore `FlightRuntime.lua` obtains the local actor through `getPlayer()`, rejects actors outside seat 0, then reads `HelicopterInput.GetState(playerObj)`. The flight physics and actuator remain owned by AviationCore.
- Existing Sol routes exist for engine shutdown (`SolUI.solEngine("off")`) and safe companion exit (`SolOrders.leaveCar()`).

## Engineer

Keep the smallest compatibility bridge: while Sol's GPS flight is active, redirect only `getPlayer()` calls whose bounded Lua stack identifies AviationCore's `FlightRuntime.lua`, and only while Sol is actually in seat 0. Leave all other callers and AviationCore physics untouched. After controlled descent, wait for the vehicle to settle, use Sol's existing engine-off service, then use the canonical companion exit service and verify Sol is out.

## Devil's advocate

- A deterministic controller harness is not B42's native physics and cannot establish real-world flight stability or collision clearance.
- Stack metadata may differ in Kahlua or callback wrappers; a successful synthetic source match does not prove the live source matcher succeeds. The positive route marker and real GPS/world-coordinate changes remain mandatory in-game evidence.
- Automatically exiting after landing could be unsafe if speed/vehicle context is stale. Keep the existing stationary and same-vehicle guards, bound retries/time, and report a failed exit instead of forcing it.
- Do not change the release copy, the user's normal profile/save, LF arbitration, or AviationCore's physics to make the harness pass.

## Strategist decision

Accept the source-scoped bridge and bounded post-landing sequence for SOL_LAB only. The adversarial review rules out treating the simulated actuator as game physics; it also requires a runtime marker at each critical handoff. Make the LAB file and WORK source identical, preserve a pre-sync backup outside the project's two retained backup slots, then run the launcher preflight before opening the isolated test profile. Do not build or install a release from this LAB candidate.

## Implementation

- Expanded the `FlightRuntime.lua` caller search to a small bounded stack window and both `source` and `short_src`, with protected calls and one-time route/miss diagnostics. It still returns the real local player to unrelated callers.
- Added bounded post-landing handling: wait until stationary, turn off the engine through `SolUI.solEngine("off")`, call `SolOrders.leaveCar()`, verify Sol left the same vehicle, and report a timeout/failure rather than silently claiming success.
- Synced the tested LAB `SolHeliGPS.lua` into `01_WORK/Sol/42/media/lua/client/SolHeliGPS.lua`. WORK and LAB SHA-256 are identical: `14CA744E723AC32B3BB908F22C2ADC08313FD61DBDF9A9CC225D621ACF445ED9`.
- Pre-sync WORK copy: `%TEMP%\Sol_s135_before_WORK_sync_20261113_123845.lua`. Previous LAB copy is separately retained in the sandbox TEMP path recorded in the session notes.

## Internal simulation and static checks

`07_TEST/SOL_LAB/_pending_refuel/test_s135_heli_full_route.py` passed the complete deterministic route simulation:

1. Sol moved from a passenger seat to seat 0; the player remained aboard in seat 1.
2. The authorized start request was queued once and GPS control waited for engine-ready.
3. The AviationCore FlightRuntime contract received Sol as its pilot and the controller emitted climb input.
4. The chosen altitude was reached before horizontal guidance began.
5. The aircraft reached two separate GPS coordinates and changed both map axes.
6. `landHere` descended to ground clearance, engine shutdown ran before exit, and Sol left through `SolOrders.leaveCar()`.
7. The bridge and speed override were restored after landing.

Focused regression harnesses passed: `test_s121_heli_gps.py`, `test_s122_seat_handoff.py`, `test_s124_heli_handoff_land.py`, `test_s125_heli_flight_sim.py`, `test_s125_heli_flight_start.py`, `test_s127_heli_speed_altitude_rows.py`, and `test_s135_heli_full_route.py`. The isolated launcher `launch_lab.ps1 -CheckOnly` passed authority, mod-list, Java linkage, patch access, Kahlua `tonumber`, jar-call, and model-card preflight.

## Runtime acceptance — still required

The internal simulation is a kinematic actuator model, not the game's flight physics. It is sufficient to pass the user's gate to open the isolated LAB for live validation, but it is not a claim that native flight works. In the live run require, in order:

1. `pilot seat acquired solFrom=... playerSeat=...` and `engine ready; climb phase started`.
2. `FlightRuntime pilot bridge routed local pilot to Sol`.
3. `GPS input ... controls=W`, rising `worldZ`, and `selected altitude reached`.
4. `GPS guidance=...`, with logged vehicle x/y changing toward at least two markers and an `arrived` result for each.
5. Landing input descends to ground clearance; then `landing complete; engine off and Sol exited through the companion vehicle service`.

If any gate is missing, stop and diagnose that boundary from the same live log. No Steam release or normal save/profile is changed by this test.

## First LAB launch after the internal gate (2026-11-13 12:42)

- The first restricted launch was blocked by a loopback `Permission denied` from ZombieBuddy's SteamWorkshop initializer. It was not a Sol/Lua failure.
- Relaunched through the isolated LAB script with socket permission. The log loaded Sol and reached game boot/render initialization; the restricted process query could not see the elevated game PID. Elevated read-only verification then confirmed game PID `6220` and Sol Mind PID `18104` still alive, with the game window responding. A second launch was correctly refused because the first LAB process was still present.
- Latest log contains `ImportedSkeleton.collectBoneFrames` missing-bone messages during startup; no helicopter runtime markers exist yet because the LAB save has not produced a new in-world flight trace. Do not attribute those model messages to this helicopter patch without further evidence.
- Current live state: LAB remains open, targeting the existing isolated save `2026-11-12_18-08-44`; user must enter the world before runtime flight acceptance can begin. Internal simulation remains separate from the pending native-physics flight test.
