# s148 — helicopter route ownership and continuous altitude guidance

## Confirmed evidence

- The live LAB trace at 2026-11-14 00:57 shows repeated `selected altitude reached` and phase changes between `following` and `climbing` while world Z stays about 7.28 AGL and target Z is 7.80. The original capture rule was a hard `abs(deltaZ) <= 0.22`, with floating samples around the boundary.
- In the later live trace at 01:01:04–01:01:11, GPS still had `targetKmh=65`; actual speed fell from 35.8 to 7.4 km/h while distance moved 1264.8 to 1234.8. Input signatures alternated every few frames between all axes released and `W` only (vertical lift); the horizontal pitch slot remained released. This directly matches the controller dropping route input as the altitude phase flips.
- The installed AviationCore `Helicopter_Input.lua` reads all eight keyboard controls with global `isKeyDown(keyCode)`; the `player` parameter is used only for joypad state. This confirms passenger key presses can enter the flight input even when Sol owns seat 0.
- `FlightEngine.lua` uses `forwardAxis * flightMaxForwardSpeed` as the forward target. Sol's current speed selector changes that maximum to 20/40/65 km/h; the controller must continue providing forward input while pointed reasonably toward the marker for these levels to take effect.

## Engineer

Add a `heli_route_ownership` LAB switch. Use altitude hysteresis (0.35 capture / 0.65 release tiles), so a held altitude band survives normal sample jitter. Keep GPS direction updates active whenever the current world altitude reference is valid, even while lift input is changing altitude. Keep forward thrust only while heading error is below 0.75 radians and distance exceeds the 4-tile arrival radius; coordinated yaw/roll can turn without pushing blindly through the marker. While Sol's route or landing autopilot owns the helicopter, clear the keyboard/joypad axes returned by the globally scoped AviationCore input before applying Sol's GPS axes. Leave native inputs unchanged when the switch is off, GPS has arrived, or GPS is idle. The marker remains replaceable during flight and is read on every controller update.

## Devil's advocate

- Taking control input away from the passenger is deliberately scoped to an active GPS destination or landing. Arrival, stop, failure, and switch-off must restore the existing manual controls. Confirm this in-game.
- Continuous forward input at every heading could make the helicopter circle or miss a close target. Keep the existing alignment window and arrival radius; do not force thrust during a large turn or missing heading sample.
- Offline simulation cannot prove the physics response, player seat routing, or whether keyboard input from another seat is applied elsewhere in the mod. Gameplay acceptance remains mandatory before release promotion.
- The patch changes only Sol files and a LAB switch. Workshop sources remain read-only. No MAIN/release copy is touched before runtime PASS.

## Strategist / acceptance order

1. Preserve the complete LAB package, installed package, and player profile. The full package snapshot for this work is `07_TEST/SOL_LAB/_backup/20261114_before_heli_route_speed_fix_complete`.
2. Run the s148 Lua 5.1 route simulation, patcher idempotence, ASCII/compile checks, and the `tonumber_check` gate against a clean source copy.
3. Install only into isolated LAB after the game closes; run `launch_lab.ps1 -CheckOnly` and launch via the official PowerShell launcher.
4. In-world: confirm seat-0 Sol, set a distant GPS marker, compare slow/normal/fast, change altitude mid-route, change the marker in flight, hold conflicting passenger keys briefly, reach the marker, land, stop and verify manual control returns. Keep DebugLog and Mind logs under monitoring.
5. Record each result. Promote to the release candidate and installed MAIN only after in-world route, altitude, speed, passenger-input isolation, arrival, and landing all pass.

## Current status

- Offline simulation: PASS (route start, two markers, altitude transition and jitter, speed tiers, passenger-key isolation, heading retry, landing, engine-off, and switch-off restoration).
- Patcher rerun: PASS/idempotent. `tonumber_check`: PASS. Python compile: PASS.
- LAB installation and in-world proof: pending because the LAB game is currently running. No active game files were changed.
