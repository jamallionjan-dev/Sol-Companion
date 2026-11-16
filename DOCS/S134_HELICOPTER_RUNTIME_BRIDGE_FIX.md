# s134 — helicopter engine starts but AviationCore does not move it

## Live evidence

- In the 2026-11-13 LAB run, Sol acquired pilot seat 0 while the player was in seat 1. The route marker was accepted and the native engine reported ready.
- The controller never logged a GPS input transition, world-altitude update, altitude reached, or GPS guidance. On shutdown AviationCore persisted the helicopter at `7523.461,9274.734,0.282`, still grounded. Thus the last live attempt did not prove takeoff or travel.
- The log shows a first flight stop at `04:01:01` (`gps_stop`), a second route at `04:01:04`, then the engine was turned off at `04:01:17`. Neither attempt produced a movement/control trace.

## Source contract and diagnosis

- **Confirmed:** the installed AviationCore `FlightRuntime.lua` obtains the local actor through global `getPlayer()` and `checkValid()` immediately rejects any actor not in seat 0. `FlightContext.build()` only reads `HelicopterInput.GetState()` after that gate.
- **Confirmed:** Sol was in seat 0 and the human player in seat 1 in the logged attempt.
- **Inference:** the narrow source check in Sol's global `getPlayer` proxy did not route at least one FlightRuntime call to Sol, so the runtime kept seeing the passenger and returned before constructing flight input. This matches the absence of any input-adapter or altitude-transition log.
- **Unknown until the next live trace:** whether the game/mod callback wrapper inserts a stack frame that prevented the previous single-level source check from matching. The next build emits a one-time positive route marker so this can be falsified directly.

## Engineer → Devil's Advocate → Strategist

- **Engineer:** retain AviationCore as physics owner; only redirect its own `FlightRuntime.lua` `getPlayer()` call to Sol while the GPS flight is active and she owns seat 0. Search a small bounded stack range for the runtime source and log the first successful route. All unrelated callers continue to receive the real local player.
- **Devil's advocate:** a stack-shape change could still evade a bounded scan; an overly broad proxy could redirect unrelated game/mod behavior; per-call stack inspection could add overhead. A missing route marker after engine-ready disproves this proposed repair. Restrict the scan to levels 3–6, keep the source substring exact, bound work, log only once per flight, and never replace the local actor for other callers.
- **Strategist:** the prior altitude fix remains, because it is a separate correct gate. Apply only the source-match hardening to WORK and SOL_LAB, make a dated LAB rollback copy, and require both the one-time bridge marker and actual world movement before accepting. Do not update release or Steam.

## Implementation and static verification

- `SolHeliGPS.lua` version `0.4.5` scans the bounded Lua stack for the exact AviationCore FlightRuntime source and logs `FlightRuntime pilot bridge routed local pilot to Sol` on the first successful handoff. The existing world-altitude correction, climb gate, GPS steering, speed/altitude UI, and stop/landing behavior remain.
- The start test simulates a non-tail FlightRuntime call, verifies it receives Sol, verifies ordinary callers still receive the human player, and checks climb/guidance state outputs.
- Passing this Lua harness is not a substitute for Project Zomboid physics/runtime evidence.

## Live test gate

Use only SOL_LAB save `2026-11-12_18-08-44`. Keep the player in a passenger seat and Sol in pilot seat 0. Set GPS speed to Slow and altitude Low, choose a short clear route, press `سوقي` once, and wait without canceling/restarting.

Pass requires all of:

1. `FlightRuntime pilot bridge routed local pilot to Sol`.
2. `GPS input ... controls=W` and a rising `worldZ` toward `targetZ`.
3. `selected altitude reached` followed by a `GPS guidance` transition.
4. Both map coordinates changing toward the marker, then arrival.
5. `هبطي هون` produces descent and the landed/released log.

If the one-time bridge marker is absent, stop; do not repeat the flight. Inspect the new callback stack evidence rather than changing altitude or flight physics again.
