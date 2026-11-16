# Sol Runtime Examiner Guide

This guide preserves the pattern used by the Lab vehicle examiner and records how to build future examiners without guessing at game or mod behavior.

## Existing reference

- Source: `01_WORK/Sol/42/media/lua/client/SolDriveRecorder.lua` (`SolDriveRecorder`).
- The vehicle recorder samples the local player's current vehicle at about 10 Hz, buffers rows, flushes periodically, and writes a timestamped text/CSV-style file through the game's `getFileWriter` API. It records position, forward-vector values, speed, steering/throttle/braking, gear/RPM, driver identity, and floor name where those APIs are available.
- Recording is Lab-only and gated by `SolLab.active` plus `SolAuthority.on("drive_record")`. Game methods are accessed defensively; failed or unavailable APIs produce empty fields rather than stopping the game loop.
- The same source contains `recordHelicopter`. It is a separate telemetry path: local player must occupy a recognized helicopter's pilot seat, and it passively records the input state supplied by the Aviation Core input seam. It captures W/S lift, A/D yaw, arrow-key pitch/roll, world position, ground reference, raw/corrected AGL when available, vertical rate, speed, and forward-vector values. It does not change flight controls.
- Output names are `SolDrive_Record_<timestamp>.txt` and `SolHeliFlight_Record_<timestamp>.txt`, created in the active profile's `Zomboid/Lua` directory. The helicopter row labels and coordinate conventions must be checked against runtime data before using them to calibrate behavior.
- Runtime correction (2026-11-13): the earlier flight recorder harness and `[SolHeliTrace]` log did not prove that `SolDriveRecorder.recordHelicopter` actually ran in-game. The observed session had trace lines but no recorder marker or output file. The live helicopter input wrapper now calls the focused `SolHeliExaminer` directly; it reports `READY`, `CAPTURE_STARTED`, periodic `CAPTURE_HEARTBEAT`, and `CAPTURE_CLOSED`, and writes `SolHeliExaminer_<timestamp>.txt`. The former helicopter writer remains legacy code and is not the active capture path.

## Recipe for a new examiner

1. **Write the question and success evidence.** Specify exactly what needs to be known (for example, whether a vehicle is moving, which seat is occupied, or whether altitude changes during a climb). Decide what observation would prove or disprove it.
2. **Find the source of truth first.** Read the relevant game API and the active mod's source. Trace the value from input to simulation to reported state. Do not infer altitude from floor `getZ()`, infer a hit from a selected body-part label, or infer movement from an accepted order.
3. **Choose the narrowest observation seam.** Prefer a state/input API already called by the game or mod. Attach to the existing local event/tick flow, scope it to the intended local actor, vehicle type, and seat, and sample only as often as the question needs.
4. **Keep the examiner passive.** It should observe and record; it must not issue movement, change controls, alter damage, or become an additional decision-maker. Put any behavioral experiment in a separate, explicitly named test path.
5. **Make the recorder bounded and recoverable.** Use timestamped files, a header row, stable field names, a small buffer, periodic flush, and close/flush on leaving the measured state. Guard optional game/mod methods and file access. Avoid full-world scans in a high-frequency callback.
6. **Gate it to the Lab.** Require the Lab flag and a dedicated `SolAuthority` switch. Scope the actor and vehicle before sampling. A recorder used for research should not silently run in the release mod.
7. **Test in layers.** First run a deterministic harness with mocked APIs (sampling interval, missing fields, state transitions, file open/write/close, and expected values). Then run Lua/Kahlua syntax and API checks. Finally install only into the isolated Lab profile and verify both the log marker and the actual output file while performing a controlled in-game sequence.
8. **Compare measured phases, not impressions.** Record a stationary baseline, apply one control at a time, release it, hold/hover, then stop/land. Check timestamps, positions, rates, control states, and ground references. Repeat once to reveal noisy or stale values.
9. **Document evidence boundaries.** Mark each claim as source-confirmed, harness-tested, or runtime-confirmed. Do not promote a Lab examiner or behavior change to the release copy until its required runtime evidence passes.

## Helicopter measurement notes

- The UH-1B depends on Aviation Core; consult both installed mod sources before changing the recorder. Workshop references: [Aviation Core](https://steamcommunity.com/sharedfiles/filedetails/?id=3783444342) and [UH-1B Helicopter](https://steamcommunity.com/sharedfiles/filedetails/?id=3409723807).
- **Training source is Jamal's piloting.** Record the local player while he occupies pilot seat 0 and manually flies. Do not use Sol's autonomous attempts as the demonstration dataset; those are later validation runs after the recorded phases have been studied and translated into Sol's controller.
- For altitude, use the physical world-position Z and Aviation Core's ground/AGL calculation where available. `vehicle:getZ()` is a floor level, not the helicopter's physical altitude.
- Record the actual input-state booleans and correlate them with position, speed, heading, and altitude over time. A single trace line or button press cannot prove takeoff, route travel, or landing.
- Keep the flight model separate from car/Bradley road steering. Similar file writing and sampling infrastructure does not mean their control or motion semantics are interchangeable.
- The current helicopter harness validates the recorder's sampling and field wiring. A real flight capture is still required before claiming the altitude profile, coordinate labels, or flight phases are calibrated in game.
- For the active examiner, first verify `READY` at mod load and `CAPTURE_STARTED` while Jamal is seated as pilot. Confirm the timestamped file appears under the active profile's `Zomboid/Lua` before asking for takeoff. A code harness alone is not runtime proof.
- After the user flight capture, analyze phase transitions (engine/run-up, lift, hover, yaw, pitch/roll, cruise, descent, touchdown) and correlate each input with movement before implementing behavior for Sol. Do not blindly replay key durations: derive a feedback controller from the helicopter's measured state and test each phase separately.

## Preservation rule

Treat `SolDriveRecorder.lua` as the reference implementation. Extend it only when a new examiner genuinely shares its lifecycle and data-writing needs; otherwise create a focused `Sol<Domain>Recorder.lua` and reuse this recipe. Preserve the existing vehicle recording behavior and keep new instrumentation behind a Lab-only switch.
