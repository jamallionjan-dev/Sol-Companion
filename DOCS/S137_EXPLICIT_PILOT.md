# s137 Explicit Pilot Handoff

## Change

AviationCore normally gets the local player in its movement and correction callbacks, then rejects that actor unless they occupy seat 0. Sol can be the actual seat-0 pilot while the human is a passenger. The old caller-stack heuristic depended on Kahlua `debug.getinfo`; the game's Kahlua probe reports `debug == nil`.

The local Sol compatibility copy of `AviationCore/Flight/FlightRuntime.lua` calls `SolHeliGPS.runtimePilot()` only in those two callbacks. During active Sol GPS flight, that resolver returns Sol only if `pilotContext()` confirms her helicopter and pilot seat. Otherwise it returns `getPlayer()`. No global player function is replaced. The compatibility file checks that AviationCore is active, then marks `SolAviationRuntimeBridgeReady`; Sol refuses to continue GPS flight when the adapter is missing.

## Evidence and limits

- WORK and SOL_LAB both contain the same patched AviationCore runtime and Sol GPS module. The original upstream source plus SHA-256 are in `08_RUNTIME_TEST/s137_explicit_pilot`.
- Focused controller/seat/GPS tests pass, including a deterministic simulated route. This does not validate native physics or the game's mod file override order.
- The Project Zomboid Kahlua compiler accepted all four modified source files with zero syntax errors. Kahlua reported `debug == nil`.
- The isolated launcher's `-CheckOnly` returned refusal code 2 because process enumeration is unavailable in this desktop session. The game has not been launched for runtime confirmation.

## Next runtime test

From a desktop session that can verify Windows processes, run `07_TEST/SOL_LAB/launch_lab.ps1`. In the isolated LAB save confirm: the log says the explicit adapter is armed; engine-ready transitions to climb; actual world Z rises; input logs show climb then GPS guidance; X/Y moves toward the marker; arrival and landing complete; engine turns off and Sol exits. If the adapter readiness flag is absent, investigate virtual path precedence/load order before tuning flight controls. No release promotion until this route passes.

## Reusable workflow for future models

1. Read the actual upstream caller and callee; locate the actor lookup, seat gate, and input read.
2. Verify the actual embedded runtime's Lua facilities. Do not infer them from desktop Lua or Lupa.
3. Prefer a narrow explicit seam over a global hook or stack-name guess. Keep authorization and seat checks at that seam.
4. Preserve upstream bytes and a fingerprint; make the compatibility patch reproducible and scoped to the intended mod.
5. Test no-debug behavior, unrelated callers, and the full controller state machine. Label mocks as mocks.
6. Compile changed Lua with the game's own compiler. Require process/singleton checks before one isolated game launch. Treat only live movement and log evidence as runtime proof.
