# SOL_LAB s134 helicopter live test

Save: `2026-11-12_18-08-44`  
Purpose: verify Sol uses Jamal's demonstrated coordinated yaw+bank steering for a short GPS flight.  
Do not use the Steam/main profile for this check.

## Before flight

1. Confirm the LAB save is loaded, Sol is visible, and the helicopter is stopped on clear ground.
2. Confirm the player and Sol are in the same UH-1B; leave Sol the pilot seat using her helicopter command if needed. Avoid starting while the player still occupies the controls.
3. Open Sol GPS. Set speed to **Slow** and altitude to **Low**. Place a marker nearby in open terrain, away from buildings, wires, trees, and roadsides.
4. Press **سوقي** once. The controller now treats repeated clicks as continuation and will not restart the climb phase. Wait through climb; do not change the destination during this short test.

## Observe expected behavior

1. **Engine/authority:** Sol holds seat 0 and the native engine becomes ready. Expected log: `engine ready` or `engine already running`; no `missing_type_knowledge` or pilot-seat refusal.
2. **Pilot handoff:** after engine-ready, expect the one-time log `FlightRuntime pilot bridge routed local pilot to Sol`. This proves AviationCore's local-pilot gate receives Sol in seat 0 while the human remains a passenger.
3. **Takeoff:** the controller reads world altitude from the same `getWorldPos(...):z()` API as AviationCore, not the floor-level `getZ()`. She climbs to the selected altitude before route steering. Expected phase: `climbing` then `following`; logs include `GPS input ... worldZ=... targetZ=...` and horizontal input is suppressed during climb.
4. **Course correction:** observe Sol turn and continue toward the marker. Expected logs include `GPS guidance=left` or `right`, `coordinatedYawRoll=true` while correcting, followed by `GPS guidance=straight+forward` as she aligns. The associated control state should pair A+LEFT or D+RIGHT; the direction should match the marker.
5. **Movement/arrival:** confirm both map coordinates change toward the marker and the distance decreases. Expected log: `arrived; holding selected altitude` (or `destination reached` in the route state).
6. **Landing:** press **هبطي هون** once. Expected log: `landing requested`, vertical descent, then `landed at destination; flight controls released`.

## Stop conditions and evidence

- If she remains stationary after the engine is ready, starts turning away from the marker, descends unexpectedly, or the distance grows for several seconds, press GPS **وقفي** and do not repeat the flight. Report the last visible phase and marker direction.
- If she arrives but does not land, use **هبطي هون** once; do not manually switch seats while airborne.
- After the attempt, capture the lines around `[SolHeliGPS]`, `[SolHeliExaminer]`, and `[AviationCore]` from the current LAB `console.txt`. Also retain the matching `SolHeliExaminer_*.txt` file; the updated examiner should close it when the local pilot leaves seat 0.

## Pass criteria

All five phases above must be observed without Sol/AviationCore Lua exceptions, flight-control oscillation that prevents travel, or uncommanded descent. Source tests and the kinematic replay alone do not satisfy live acceptance.

Status before this run: the previous attempt failed live acceptance. Log showed pilot seat, learned manual, and engine ready, but no selected-altitude or GPS-guidance transition; world coordinates stayed fixed. This build fixes the altitude API mismatch and makes repeated start idempotent. The live result is still pending.
