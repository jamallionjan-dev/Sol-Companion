# s133 — helicopter starts but does not move

## Evidence from the failed live run

- Sol reached pilot seat 0; the player moved to seat 6.
- The UH-1B manual knowledge was accepted; the engine reached `ready`.
- A GPS marker was accepted, but there was no `selected altitude reached` or `GPS guidance` transition.
- `SolHeliExaminer` samples remained at world position `7523.4688, 9274.7188, 0.2817`; the helicopter did not move.
- The user pressed the flight-start control again later; each repeat logged `engine already running; climb phase started`, resetting the controller phase.

## Root cause

AviationCore's `FlightContext` obtains actual aircraft altitude from `vehicle:getWorldPos(...):z()`. `SolHeliGPS` instead used `vehicle:getZ()` to decide whether the selected altitude had been reached. In this aircraft API, `getZ()` represents the floor/tile level, not the aircraft's world altitude. Consequently `altitudeReady` could remain false, keeping horizontal GPS steering suppressed. The Flight Examiner already recorded `getWorldPos` altitude, which exposed this mismatch.

Repeated clicks were a second control-flow defect: when the engine was already running, every `start()` call reset the phase to `climbing`. That made recovery confusing and could restart climb after a marker change. It is now idempotent for the active helicopter and reports that it is continuing the current phase.

## Changes

- `SolHeliGPS.lua` now uses the aircraft world-position Z for AGL, target-altitude, and status readings, matching AviationCore.
- It logs input transitions with phase, world Z, ground Z, target Z, and remaining GPS distance, so a future failure identifies whether climb controls or route controls are reaching `HelicopterInput`.
- Repeated starts do not restart an active flight; marker changes preserve a current climb phase.
- Controller version: `0.4.4`.
- Installed only in SOL_LAB with final rollback checkpoint `07_TEST/SOL_LAB/_backup/20261113_035249_before_s133_heli_world_altitude`.

## Review / falsification

- Engineer: the altitude API mismatch directly explains why route steering never started despite engine readiness and a fixed world position. This matches the official AviationCore `FlightContext` implementation inspected locally.
- Devil's advocate: repeated button presses could explain a restarted climb, but cannot explain the first two minutes with no movement. The world-altitude mismatch is independently sufficient to block the route. If live logs show target altitude reached and GPS input toggles but position stays fixed, this diagnosis is incomplete and the next investigation is AviationCore's player-to-Sol runtime bridge and native input consumer.
- Strategist: keep the fix LAB-only. Require a live trace showing input transitions, altitude changes, both horizontal coordinates changing toward a marker, arrival, and commanded landing before release promotion.

## Verification and current gate

- `test_s121_heli_gps.py`, `test_s125_heli_flight_start.py`, `test_s125_heli_flight_sim.py`, `test_s127_heli_speed_altitude_rows.py`, `test_s128_heli_recorder.py`, `test_s129_heli_recorder_wiring.py`, and `test_s129_heli_flight_analyzer.py` pass after the test fixture explicitly distinguishes tile Z from world Z.
- The flight simulation is a kinematic control replay, not the game's physics engine.
- Live acceptance is pending. Follow `DOCS/S132_HELICOPTER_LIVE_TEST.md` for the exact LAB test sequence.
- No Steam/main profile, save, release directory, or model action catalog was changed.
