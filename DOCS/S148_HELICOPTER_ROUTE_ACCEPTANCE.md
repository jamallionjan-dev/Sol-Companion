# s148 helicopter route acceptance

## Tested offline

- Sol takes seat 0 and the explicit AviationCore pilot bridge supplies the actor.
- GPS pitch/yaw/roll remains active while Sol climbs to a new altitude.
- Altitude reading jitter within the release band does not drop route control.
- Slow/normal/fast select the 20/40/65 km/h forward caps and route pitch remains asserted while within the heading window.
- Passenger key inputs opposing GPS are ignored only during active route/landing control.
- The destination can be replaced in flight; two route markers, temporary heading loss/recovery, arrival, landing, engine-off and exit all complete in the simulation.
- With the feature switch off, manual passenger keyboard state follows the previous behavior.

## In-world test result — 2026-11-14

- Jamal reports all six in-world checks passed: speed tiers, altitude changes during flight, live destination changes, passenger input handling, reaching the marker, and the landing/engine/control handoff checks.
- Captured DebugLog independently confirms: direct GPS flight started; the first marker reached the `arrived` phase; speed targets switched among 20/40/65 km/h with measured speed responding; medium altitude was selected and reached while the active route continued; the marker was replaced in flight and navigation resumed toward it; at 01:14:26.162 the helicopter landed and released controls, and at 01:14:26.485 landing completed with engine off and Sol exited.
- Jamal observed changing altitude while holding forward input; after releasing it, Sol changed altitude and continued. This is a reported observation, not yet isolated as a causal input conflict. The route continued in the log during the altitude transition.
- No Sol/AviationCore exception was found in the captured flight segment. The log became dominated by repeated physics impulse output after the completed landing, but the landing/engine-off/exit events are present in the log.
- Runtime status: **PASS by user confirmation**, with the above independent telemetry corroboration. This authorizes s148 release promotion.

## Original acceptance checklist

1. Start the isolated LAB save with Sol in pilot seat and the player in a passenger seat.
2. Set one distant direct-air GPS marker and choose slow, then normal, then fast. Watch both `kmh` and `targetKmh` in `[SolHeliGPS] GPS progress`.
3. During flight change low/medium/high altitude; the destination distance must keep decreasing and the phase must not bounce repeatedly at the altitude threshold.
4. Change the GPS marker during flight. Sol must turn toward the new marker and continue without restarting the engine.
5. Briefly press a conflicting flight key from the passenger seat. The active GPS route must retain control.
6. Reach the marker, request landing, verify touchdown, engine off, Sol exits, and manual flight input works after GPS releases control.

All six checks were reported passed by Jamal on 2026-11-14. See the runtime result above.
