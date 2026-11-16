# Plan s144 — Sol starts the selected helicopter GPS route by voice

## User-visible behavior

With Sol and the player inside the same helicopter and a destination already selected in Sol GPS, “سول طيري على العلامة” starts the existing direct-air route. Sol's seat command remains separate: “سول طيري بالمروحية” only transfers her to the pilot seat. The existing GPS speed controls stay visible; helicopter altitude choices appear only in the helicopter. No route is synthesized when no marker is selected.

## Flight method supplied by Jamal

1. Follow the helicopter operator guidance before flight.
2. Rise first to the selected flight band: low above trees, medium above typical two-storey buildings, or high toward the aircraft's supported maximum.
3. Use direct-air GPS navigation; do not apply car road-following rules to a helicopter.
4. Keep speed and altitude controls available independently.
5. At the destination, descend and land; confirm touchdown, stop the engine, then exit.

These are procedural requirements. Exact altitude numbers and supported control APIs must come from the active AviationCore/helicopter implementation and in-game observation, not assumptions.

## Implementation boundaries

- Own switch: `heli_voice_fly`; it is effective only with `heli_gps` enabled.
- One Mind action, separate from seat transfer, summon, car drive, and GPS UI start.
- Refuse unless Sol is in a helicopter, the player is in that same vehicle, and the GPS already has a destination.
- Delegate to `SolHeliGPS`'s existing `U.gpsStart(nil, false)` path to retain its qualification, pilot handoff, speed and altitude logic.
- Keep all speed, altitude, landing and stop controls available in the helicopter GPS UI; do not replace speed buttons with altitude buttons.

## Acceptance sequence for isolated LAB

1. Verify the candidate loaded its own profile and `heli_gps=on`, `heli_voice_fly=on`; inspect the Mind log for the card and route.
2. In the same helicopter, test voice start with a marker selected: Sol in pilot seat, engine authorization, takeoff and progress to the marker.
3. Repeat with each speed and each altitude control; ensure speed buttons remain visible and altitude controls appear only in a helicopter.
4. Change to a second nearby GPS marker during flight; verify direct-air progress updates and does not use road routing.
5. Land at the chosen destination. Verify grounded state, engine stopped, and safe exit.
6. Negative cases: no marker, Sol outside, player outside/different vehicle, and disabled `heli_voice_fly`; all must refuse cleanly.
7. Verify normal car GPS controls/routes remain unchanged.
8. Review DebugLog and Mind log for Lua/Kahlua errors and `[SolHeliGPS]` / AviationCore flight state. Record each result in the ledger.

## Current status

The action gate was exercised with a Lua 5.1 harness: valid same-helicopter/marker is accepted; no marker, different player vehicle, Sol outside, and either disabled switch are refused; accepted execution delegates to the existing GPS start without changing the marker. Existing s135 controller simulation also reaches two destinations, lands, stops the engine and exits. These are offline simulations, not a native game session. Gameplay acceptance has not been run on this candidate. Do not label stable or gameplay-passed until the sequence above passes in-game.
