# s132 — match Sol helicopter steering to Jamal's piloting

Date: 2026-11-13  
Scope: SOL_LAB only; no MAIN, Steam profile, release, or save changes.

## Evidence from Jamal's manual flight

- The LAB examiner file `SolHeliExaminer_1794533693888.txt` records about 526 seconds and roughly 179 map tiles of horizontal travel, with world altitude from about 0.28 to 7.95. It is a manual flight, not proof that Sol flew a GPS route.
- The accompanying `console.txt` trace shows the demonstrated control pattern: W/S for vertical control; UP/DOWN for forward/backward; A/D for yaw; LEFT/RIGHT for bank/side input. Examples include `A+UP+LEFT` and `D+UP+RIGHT`, so turns were coordinated with forward input and same-side bank.
- The previous GPS adapter generated yaw and forward pitch but never coordinated the same-side roll/bank. That is the concrete control mismatch being corrected here.
- The older recording began before the recorder's heading-column fix and its capture did not emit a close marker. Do not use its incomplete heading column to claim calibrated yaw rates; the console trace preserves the control pattern and the movement/altitude record remains useful as approximate telemetry.

## Engineer

- Keep the AviationCore input seam and Sol GPS state machine. At a GPS course correction, pair A with LEFT or D with RIGHT. Keep UP/DOWN, altitude hold, and user-input precedence independent; retain the existing altitude climb gate and destination calculation.
- Use a heading hysteresis band: begin a turn beyond 0.30 rad and release below 0.18 rad. This avoids rapid reversal at the threshold while preserving the controller's existing 0.75 rad forward-alignment gate.
- Emit a transition-only `GPS guidance=...` log with the heading error and whether yaw/roll coordination is active. Do not log every frame.
- Version the controller as 0.4.3. The Mind's command catalog and prompt are unchanged; no new natural-language action was added, so the model card must remain generated from the same Mind actions.

## Devil's advocate

- AviationCore maps LEFT/RIGHT to both lateral motion and roll attitude; adding bank can change the route geometry. This needs real in-game GPS-route testing at a clear, low-risk location.
- The offline harness models position, heading, climb, and landing with simple kinematics. It does not reproduce AviationCore physics, collisions, terrain, aircraft damage, or the UH-1B's flight dynamics.
- Manual telemetry cannot demonstrate autonomous GPS success. The game must show engine readiness, climb, changing X and Y, marker arrival, and a safe landing before this behavior is accepted.
- The capture file is from the previous examiner version; retest the updated 14-column recorder on the next pilot flight before treating its heading values as complete.

## Strategist / acceptance

- Keep the change isolated behind existing `heli_gps` and install it only to SOL_LAB after the game process has ended and a rollback copy has been made.
- Offline acceptance: both turn directions generate matched yaw+bank; straight flight releases both; an off-axis simulated destination changes both map coordinates, arrives, and lands; manual start authorization, altitude logic, and speed restoration still pass.
- Runtime acceptance on save `2026-11-12_18-08-44`: choose a nearby clear GPS marker, start from a stable hover, verify turn transitions in the log, confirm horizontal movement and arrival, then test `هبطي هون`. Record any deviation; do not promote to release until the live route passes.

## Status

- Offline coordinated-guidance and route/landing simulations: PASS.
- Lua parse and LAB launcher gates: pending after LAB sync.
- Real AviationCore GPS flight, collision-free route, and landing: pending live test.
- Release/Steam deployment: not performed.
