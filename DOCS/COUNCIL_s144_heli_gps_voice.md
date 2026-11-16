# s144 — explicit helicopter GPS flight command

Date: 2026-11-13
Scope: private release candidate only; preserve the existing 0.28.3 and 0.28.4 bundles.

## Engineer

- Existing helicopter GPS route and its UI controls remain the authority for speed, altitude bands, direct-air routing, and landing. The spoken action does not invent a marker, waypoint, or landing coordinate.
- Added a separately gated `heli_voice_fly` action. It requires `heli_gps` and `heli_voice_fly` to be enabled, Sol and the player to occupy the same helicopter, and a previously selected GPS destination. It calls the existing `U.gpsStart(nil, false)` entry point.
- The Mind routes “سول طيري على العلامة” and “طيري للمكان المحدد على الجي بي اس” to this one action. The card now records the operating method Jamal taught: consult the operator guidance, climb to the chosen altitude, navigate by direct air GPS, land at the destination, then verify touchdown, engine-off and exit.

## Devil's advocate

- Static verification proves registration, gating, routing and call wiring only. It does not prove that Kahlua accepts all calls in an actual game session, that the helicopter climbs, that route control persists, or that it lands safely.
- The eligibility check uses the existing `SolHeliGPS` seat predicate and the same-vehicle relationship. A wrong or unavailable vehicle, disabled underlying GPS, missing marker, or player/Sol vehicle mismatch must be refused without changing the selected destination.
- `U.gpsStart` acceptance is not equivalent to arrival. Runtime logs and observed position, altitude, speed, touchdown, engine and seat state are required before claiming completion.
- The card has no spare budget: 4,600/4,600 characters with horn held. Further card edits require a full gate.

## Strategist

- Build a new isolated full bundle from stable 0.28.3, overlay the complete 0.28.4 accumulated candidate, then apply only the s144 action/switch/Mind-card files. This preserves prior features while leaving both existing releases untouched.
- Mark the separate voice switch on in this candidate's MAIN switch file only. Do not alter the Steam profile or user save.
- Promote nothing to stable and make no GitHub update until isolated in-game acceptance passes. Do not launch the game in this task; launch and gameplay are separate evidence boundaries.

## Evidence status

- Confirmed by checks: action registration and route phrase; two required switches; selected-destination and same-helicopter guards; call to the existing GPS start; Lua 5.1 harness accepts the valid case and refuses five invalid/disabled cases; existing flight-controller route simulation reaches two markers, lands, shuts down and exits; model card is within budget and route replay passes.
- Reported by Jamal in earlier gameplay: Sol took the pilot seat, engine started, and a destination-directed takeoff/route succeeded before speed tuning was requested.
- Still needs runtime verification on this candidate: multiple speeds and altitude levels, persistent route progress, stopping, landing at the marked location, engine shutdown, exit, and unchanged ground-vehicle GPS behavior.
