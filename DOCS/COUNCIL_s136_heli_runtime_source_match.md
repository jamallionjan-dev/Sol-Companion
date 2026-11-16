# s136 — FlightRuntime source matching review (2026-11-13)

## Engineer — evidence and smallest repair

- Live failure evidence: Sol reached the pilot seat and the helicopter reported engine-ready, but the log had no positive FlightRuntime bridge marker, no emitted GPS controls, no altitude rise, and no coordinate guidance. Therefore the controller's intent state did not prove the AviationCore runtime was receiving Sol as its pilot.
- Installed AviationCore obtains the actor through `getPlayer()` in `FlightRuntime.lua`, then verifies pilot seat 0 before reading `HelicopterInput.GetState(playerObj)`.
- The existing bridge looked only at the bounded debug stack's source metadata. The internal reproduction now supplies the short Kahlua-style source `@FlightRuntime.lua`; the previous matcher declined it. The smallest repair accepts that exact basename in the already bounded stack window while the Sol flight bridge is installed. Other source names keep the real local player.
- Required runtime acceptance remains a positive route marker followed by actual input, world-Z rise, and changing map coordinates. A simulation is not a substitute for those signals.

## Devil's advocate — attack the proposed fix

- A basename can collide with another mod's file named `FlightRuntime.lua`. The guard is constrained by active Sol GPS flight, the limited stack window (levels 2–10), and the existing Sol-in-pilot-seat check; an unrelated source name is covered by a negative regression case. This narrows but does not eliminate collision risk if another active module uses the same basename on the same call stack.
- The synthetic runtime can verify the stack predicate and controller contract, but cannot prove that the target Build 42 Kahlua exposes `short_src` the same way, nor model AviationCore physics. A missing route marker or absent physical movement in the next live run rejects the fix; do not claim real flight is fixed until then.
- Do not broaden the proxy to all `getPlayer()` calls, alter AviationCore's flight physics, modify a normal save, or change the release package to make a test pass.

## Strategist — decision and gates

Accept only the exact-basename fallback for the bounded FlightRuntime stack scan, with diagnostics for routed and unmatched candidates. Keep the change limited to WORK and isolated SOL_LAB. Preserve pre-change copies. Run the focused helicopter regressions, the end-to-end simulated flight, and the isolated launcher's `-CheckOnly` gates before any game launch. If those pass, launch one isolated LAB instance only. The live test must observe: bridge routed to Sol → climb input and increasing world-Z → selected altitude reached → GPS guidance and x/y movement toward markers → arrival and landing. Stop and investigate at the first missing gate. No MAIN save or release promotion.

## Implementation and internal verification

- `SolHeliGPS.lua` now accepts exact short source `FlightRuntime.lua` even when the runtime omits the enclosing AviationCore path, while maintaining the bounded source-stack inspection and actual-pilot-seat guard. A non-routed FlightRuntime candidate receives a diagnostic stack record.
- WORK and SOL_LAB copies are byte-identical (SHA-256 `0E41035A28BDAC70026B06F2D0FA856FC865FB742869F2172B8729DE5E9D2757`).
- PASS: `test_s121_heli_gps.py`, `test_s122_seat_handoff.py`, `test_s124_heli_handoff_land.py`, `test_s125_heli_flight_sim.py`, `test_s125_heli_flight_start.py`, `test_s127_heli_speed_altitude_rows.py`, `test_s128_heli_recorder.py`, `test_s129_heli_flight_analyzer.py`, `test_s129_heli_recorder_wiring.py`, and `test_s135_heli_full_route.py`.
- The s135 deterministic route exercised seat handoff, authorized engine readiness, climb, two GPS legs, landing, engine shutdown, and companion exit. It uses kinematic mocks and does not represent the game's native flight physics.
- PASS: `launch_lab.ps1 -CheckOnly` verified LAB authority, mod list, Java linkage, patch access, Kahlua `tonumber`, jar calls, and model-card consistency. The launcher reported that the lab is newer than the installed release; no release install/build was performed.

## Runtime status and launch-guard incident

- The first guarded launch attempt was made while the user's earlier game session was still open. This was a process-verification failure: the restricted environment could not enumerate the desktop processes, but the launcher treated the empty `Get-Process` result as proof that no game was running. The user's confirmation and file timestamps show the old `12-42` log updated at 13:53:50, immediately before the new `13-53` log began at 13:53:53. Sol Mind also reported port 8768 busy.
- The launch script started a second process (PID 5976), then its isolated brain failed the single-instance port check. The new log stops during startup; no flight runtime evidence was produced. Sol Mind subsequently logged that its attached game disappeared at 13:54:02. Do not describe this as a successful runtime test.
- Hardened `launch_lab.ps1`: it now refuses when Windows process enumeration fails, refuses if a game process is visible, and probes the Sol Mind singleton port before starting the game. PowerShell parser check passed. Running `-CheckOnly` in this restricted environment now refuses with `Windows process enumeration failed`, which is the intended fail-closed behavior.
- No further game process was started after that refusal. Do not relaunch from this restricted session. Run the launcher only from a context that can verify the desktop process list and confirm that no older game session is open. Then verify actual bridge routing, climb, GPS movement, arrivals, landing, engine shutdown, and Sol exit before calling the patch runtime-fixed.
