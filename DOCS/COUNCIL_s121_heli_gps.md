# s121 — Sol GPS flight controls and altitude modes

Date: 2026-11-12  
Scope: SOL_LAB only until an in-world pass. Steam/Workshop, MAIN, release, and user saves remain unchanged.

## Engineer — confirmed code facts and implementation

- The current Sol GPS sends every destination to `SurvivorCompanion.Driving`, whose route is a road route. Helicopters must branch before that service and use direct world coordinates.
- Read-only inspection of the installed AviationCore workshop source found no usable autopilot command API: `FlightEngine.executeCommand` reports that flight has no commands. Its documented in-mod input seam is `HelicopterInput.GetState(player)` with lift, yaw, pitch, and roll booleans.
- AviationCore's current flight runtime accepts only the local player in seat `0`. Its flight context itself reads `HelicopterInput.GetState`, and its forward heading is computed from `BaseVehicle:getWorldPos(0,0,0)` and `getWorldPos(0,0,1)` using a reusable `Vector3f`.
- The SOL_LAB adapter wraps only that input function, only while the feature switch is on and GPS flight is explicitly active, and only while Sol and local player share a recognized helicopter and the local player occupies seat 0. Per-axis manual input wins. On context loss or Stop, the adapter drops its destination and stops injecting input.
- Map markers remain world-coordinate goals and are never snapped to roads for a helicopter. Car start, speed buttons, preview, and LF route calls retain the existing path.
- Initial height presets are 2.4, 5.2, and up to the AviationCore absolute world-Z ceiling. Altitude values are provisional: the available 11-12 log only records ground-near corrected skid AGL transitions, not Jamal's three stable flight bands.

## Devil's Advocate — rejection risks

- The steering loop is an input adapter, not a native flight autopilot. It has not yet demonstrated stable acceleration, braking, hovering, touchdown, or obstacle avoidance. It may overshoot a marker or fail to hold a preset under terrain/ceiling limits.
- The local-player-seat-0 requirement is a hard integration boundary. If the user or Sol is not in the required shared helicopter context, the GPS must refuse and show a reason rather than silently invoking LF road driving.
- AviationCore controls the aircraft locally; an explicit flight trip will steer the user's pilot input except on axes where the player is actively supplying input. This must be clear in the live test.
- Low and medium height presets are estimates, not measurements. High is limited by the mod's absolute world-Z ceiling and can therefore have less AGL on raised terrain.
- Any error in angle sign, position basis, joystick precedence, terrain floor reference, or event load order can make flight unsafe. The first test must be in a clear area, at low speed, with Stop immediately available.

## Strategist — decision and acceptance gates

- Keep the adapter strictly within Sol's mod and behind `heli_gps`; do not edit AviationCore or reuse its road driver for a helicopter.
- Install in SOL_LAB only after game closure and a dated backup. Keep MAIN/release untouched until runtime PASS.
- Offline acceptance: Lua 5.1 behavior tests cover altitude choices, direct coordinate guidance, manual-input precedence, arrival, context loss, pilot-seat refusal, feature switch, and installer idempotency. Run all launcher preflight gates.
- In-world acceptance: (1) buttons appear only with Sol aboard the helicopter; (2) low/medium/high produce measured, stable, distinct heights; (3) marker flight proceeds off-road directly and stops near the marker; (4) player input overrides GPS per axis; (5) Stop immediately releases control; (6) leaving the pilot seat cancels; (7) car GPS still shows speed and road routing; (8) no new Sol/AviationCore errors. Record actual AGL and log tags for each.
- Until all applicable checks pass, report implementation as LAB candidate, not proven autopilot and not release-ready.

## s122 — Bradley comparison and in-vehicle driver handoff

### Engineer — confirmed Bradley design and transfer lesson

- `SolTracked.lua` documents why Bradley control cannot be treated as ordinary car steering: Trucksmith's normal stabilizer only processes actual local players in the driver seat. Sol's tracked-vehicle path therefore invokes Trucksmith's own `TrackSteer.step` followed by `Stabilizer.step` only for the vehicle Sol drives; it does not patch or replace Trucksmith.
- The Bradley-specific `vehicle_steer_adapt` observes applied steering versus actual yaw and mirrors only when that tracked vehicle turns in the opposite direction. The handoff is therefore a useful integration pattern: identify the owning mod's input seam, gate by vehicle type/context, reuse its native control model, and keep the car/heli controller separate.
- Prior handoff evidence records Jamal's Bradley M3 completing a paved route and turning around a stop-sign corner through Trucksmith (`SOL_HANDOFF.md`, 2026-11-10 17:06). That is evidence for tracked driving only; it does not validate helicopter flight.
- The helicopter uses AviationCore's separate `HelicopterInput.GetState` path. Bradley turn, stabilizer, and road-route code must not be reused for flight. Only the seam/context separation principle transfers.

### Devil's Advocate — seat-switch boundaries

- `sol_let_player_drive` must not call exit/board, replace the vehicle, or move the player. It is limited to single player, Sol in driver seat 0, a stationary vehicle, and a native-reachable empty passenger seat. If the player is outside, the driver seat is freed for him to enter; if he is already a passenger, he remains there.
- If the player is in another vehicle, Sol is moving, the vehicle has no reachable passenger seat, native switching fails, or post-switch occupant verification fails, the action refuses and reports the game reason. It must never evict an occupant or claim success on a pending acknowledgement.
- The native path still needs runtime validation separately for a car, helicopter, and Bradley. An offline Lua harness proves the guarded state transition only, not that each vehicle mod exposes compatible seat-switch behavior.
- AviationCore still requires the local player in pilot seat 0 to accept its flight input. Giving up Sol's driver seat in a helicopter is a seat handoff, not proof that the human can pilot while the flight adapter remains enabled; flight must be stopped/cancelled before the player takes control.

### Strategist — decision and acceptance

- Keep Sol's helicopter GPS as a scoped AviationCore input adapter and direct world-coordinate route. Keep car road-following and Bradley/Trucksmith logic on their existing, separate paths.
- Add the Mind command `سول عطيني الدركسيون` (alternate `خلييني أنا سوق`) as the direct `sol_let_player_drive` action. It cancels any stale movement goal, asks the native seat service to move Sol into a reachable empty passenger seat, and speaks success only after the game confirms the seat change. It is not an exit command.
- Switch `seat_handoff` is explicit. Install into SOL_LAB only after fresh backup, process check, and `launch_lab.ps1 -CheckOnly`; no MAIN/release or user-save changes.
- Offline checks currently pass: s121 helicopter harness 32 checks; s122 handoff harness 14 checks; route replay `ALL PASS`; model card 4549/4600 including horn-held state; Python compilation. Runtime remains pending.
- Runtime acceptance: verify the new phrase while Sol drives a stationary car with player outside; repeat with player already a passenger; then test Bradley and helicopter independently. Verify Sol stays in the same vehicle, the player is not displaced, driver seat is actually free, and the action refuses while moving/no seat. Separately test heli GPS while the human pilots and preserve the existing authority rule; do not infer it from the seat-handoff test.

## Current status

The source is installed in SOL_LAB after backup `07_TEST/SOL_LAB/_backup/20261112_222157_802866_before_s121_heli_gps`; `launch_lab.ps1 -CheckOnly` passes (linkcheck 12058/0, patch access 93/0, tonumber OK, jarcall 0 fail/20 warn, card 4549/4600). Earlier sandboxed launches exited during ZombieBuddy startup with `java.net.SocketException: Permission denied: connect`; a later elevated launch did initialize the isolated lab, so the failure is environment-sensitive. Recheck live processes/log before any new launch.

## s123 — explicit helicopter pilot order and generic control handoff (2026-11-12)

### Engineer — implementation facts
- Added `sol_pilot_helicopter` as a distinct Mind action. `سول طيري بالمروحية` / `خدي مقعد الطيار بالمروحية` seats Sol as pilot in the same stationary AviationCore helicopter; if the player currently pilots, Sol first moves the player to a reachable empty passenger seat. It never ejects anyone and only takes the seat; GPS destination selection and starting flight remain separate steps.
- AviationCore's input proxy is scoped to its `FlightRuntime.lua` caller and feeds Sol only while she owns seat 0; the user remains in the same helicopter. Existing direct-air GPS and altitude controls remain separate from car road driving and tracked-vehicle code.
- `عطيني القيادة` is the generic handoff wording for cars, helicopters, and tracked vehicles: Sol moves from the driver/pilot seat to a reachable empty passenger seat and stays in that vehicle. It does not start driving or eject the user. Old steering-wheel wording was removed from the model card routes.
- Mind entry card regenerated with both actions and examples; LAB authority gates remain `heli_gps=on` and `seat_handoff=on`.

### Devil's Advocate — remaining risk
- Offline seat stubs do not prove Build 42's native `switchSeat` behavior for each Workshop vehicle. Seat graph restrictions can refuse safely. An occupied/no reachable passenger seat or moving aircraft prevents transfer.
- Helicopter seat takeover and actual flight are distinct. Flight control, altitude calibration, landing, and each helicopter model still need in-world evidence; no flight success is inferred from static/offline checks.

### Strategist — installation/test rule
- Keep changes in SOL_LAB only until a live pass; back up before install. Do not update MAIN, Steam, or release yet.
- Required in-world checks: (1) Sol takes pilot seat while user is passenger and pilot seat is free; (2) same when user pilots and a passenger seat is open; (3) generic `عطيني القيادة` frees the control seat while Sol stays inside; (4) refuse safely while moving or with no seat; (5) choose a GPS marker then start flight; measure low/medium/high, direct route, manual override, Stop, and new Sol/AviationCore errors.
- Offline checks pass: s121 helicopter harness, s122 seat handoff harness, and s82 route replay; Python compile and card gate. These are not in-world proof.
- Previous flight test logs showed `start refused: sol_not_pilot`; s123 routes both the pilot-seat order and GPS Start through `H.takePilot()` before activating AviationCore. This is the specific failure addressed here.
- LAB installed after backup `07_TEST/SOL_LAB/_backup/20261112_224501_214054_before_s123_heli_and_handoff`. Preflight passed: LINKCHECK 12058/0, PATCH ACCESS 93/0, TONUMBER OK, JARCALL 0 fail/20 warnings, CARD PASS 4597/4600 (one existing warning). Elevated launch reached `[SolAuthority] Sol_LAB test copy active`, `[SolGPS] ready v0.5.1`, and Sol UI Lua initialization. At handoff the game had not entered the save/world; helicopter seat and flight remain unverified in-world. Startup also emitted `ImportedSkeleton.collectBoneFrames` missing-bone errors plus font/FluidContainer warnings; attribute none to s123 without evidence.

## s124 — pilot-seat lookup, native handoff fallback, and helicopter landing button (2026-11-12)

### Engineer — log-backed diagnosis and changes
- The active 2026-11-12 debug log showed repeated `[SolActions] sol_pilot_helicopter -> false sol_pilot_seat_change_failed:seat_service_unavailable`, followed by `[SolHeliGPS] start refused` with the same reason. `SolHeliGPS.takePilot()` looked up `_G.SC`, but the real public namespace used across this project is `_G.SurvivorCompanion`; the earlier harness defined fake `SC`, masking the runtime defect. The lookup now uses the actual namespace.
- The same log showed `sol_let_player_drive -> nil no_reachable_empty_passenger_seat`. `SCVehicle.shiftFromDriver` and `shiftToDriver` filtered candidates only through `canSwitchSeat`; the new path ranks those native-approved seats first, then tries other installed, empty, unreserved seats through the game's `switchSeat`, and accepts only a verified seat + occupant result. It still refuses a moving vehicle, occupied seat, foreign reservation, absent seat, or failed native transition. It does not eject or relocate another occupant.
- Added a helicopter-only center button `هبطي هون` between `حلّقي` and `وقفي`. It cancels the stale map goal and requests a vertical landing at the helicopter's current coordinates. Car GPS keeps its existing two-button controls. This is a UI control, not a new spoken order, so the Mind card/action catalog is unchanged.

### Devil's Advocate — remaining risk
- The direct native seat-switch fallback intentionally tests the game's actual transition after the reachability hint says no. Runtime may still reject some workshop vehicles; every move is verified, but vehicle-specific car, helicopter and Bradley behavior remains unproven.
- The landing adapter depends on AviationCore's current-ground data and lift input. Offline tests prove its state transitions only, not a safe physical touchdown, slope handling, or landing clearance. The button must be tried in an open flat area with Stop available.
- The former helicopter harness used a fabricated global `SC`. It has been corrected to define `SurvivorCompanion` and leave `SC` absent; this regression matters because the old test otherwise passed while the game failed.

### Strategist — gate before the single lab launch
- Scope stays SOL_LAB only. No MAIN, Steam, release folder, workshop source, or user save is changed. `عطيني القيادة` and pilot-order routing already existed; only their native seat transition is repaired, so no new Mind command/card text is needed.
- Offline batch: s121 flight/landing harness, s122 seat handoff/action/card harness, s124 Lua 5.1 compilation + installer backup/idempotency checks. Then install all five runtime files as one dated-backup batch and require `launch_lab.ps1 -CheckOnly` to pass before starting the game once.
- One live session should test: (1) `سول طيري بالمروحية` while Jamal pilots and while he is a passenger, (2) GPS Fly to a marker, (3) press `هبطي هون` during flight and verify it lands at the current spot rather than the old marker, (4) Stop, (5) `عطيني القيادة` in a parked car with Jamal outside and already a passenger, then separately helicopter/Bradley, (6) safe refusal while moving/no free seat, (7) car GPS unchanged, and (8) no new Sol/LF/AviationCore errors. Record live outcomes separately from offline checks.

## User-provided helicopter flight procedure (2026-11-12)

This section records Jamal's explicit operating method and requirements; it is not an inference from the current implementation.

### Procedure demonstrated/described by Jamal
1. Read the helicopter's operator manual before attempting flight; the manual/knowledge gate is part of the intended workflow and must not be bypassed.
2. Take off and climb to the selected flight altitude before beginning directional travel. Jamal's described manual procedure uses maximum available altitude first, then controls direction and movement, then descends and lands.
3. Steer toward the chosen destination through the air. A helicopter is not a road vehicle: do not snap its route to streets or reuse car road-following behavior.
4. Descend and land at the destination (or at the explicitly requested landing point), and report success only after touchdown is confirmed.

### Sol GPS behavior requested
- Show three flight-altitude choices only while Sol is in a helicopter: low (above tree level), medium (above roughly two-storey buildings), and high (maximum practical altitude). The selected band is the altitude target: Sol must climb to it before horizontal route-following.
- Selecting a GPS destination and starting flight should let Sol take the pilot seat from another helicopter seat when safe, start the aircraft through the native/manual-authorized path, wait for readiness, climb, fly directly to the GPS coordinate, then land only when commanded or when the route's landing behavior explicitly requires it.
- Keep the helicopter workflow separate from car steering and road routing.
- `عطيني القيادة` means hand the vehicle controls to the player by transferring the appropriate seat; `سول طيري بالمروحية` means Sol takes the pilot seat and flies. `هبطي هون` requests landing at the selected/current point. These actions must not be conflated.
- A seat switch, accepted GPS marker, or logged “flight started” is not proof of flight. Verify engine start, climb/altitude change, horizontal movement, and touchdown from runtime evidence.

### Evidence boundary / pending calibration
The procedure above is user-provided and should be treated as the behavioral requirement. Numeric altitude values for low/medium/high were not reliably captured from the earlier manual flight session; do not present provisional numbers as measured. Calibrate the bands against the user's observed tree/building/max-altitude levels before claiming those thresholds are verified.

## s125 — engine-gated GPS flight and altitude-first simulation (2026-11-12)

### Engineer — confirmed evidence and implementation
- The s124 runtime log showed Sol took the pilot seat and accepted GPS, but the sampled helicopter stayed at near-zero speed with `engine_rpm=0`. Source inspection confirmed `H.start()` installed the AviationCore player proxy and labeled flight active without asking the game to start the engine. AviationCore's `FlightRuntime` resets into its engine-off path while `isEngineRunning()` is false.
- `SolHeliGPS.start()` now requests engine start through the game's `ISVehicleMenu.onStartEngine(sol)` path only after `AviationCore.AircraftKnowledge.AuthorizeStartRequest` allows it. That retains the operator-manual/qualification gate and the native timed action's key behavior. Sol's GPS controller remains inactive until the vehicle reports engine running; a bounded 30-second wait then reports a concrete timeout rather than a false flight start.
- When the engine becomes ready, Sol enters `climbing`. It suppresses yaw, pitch and roll GPS steering until the selected altitude is reached, then follows direct world coordinates. Missing ground/altitude data blocks horizontal guidance. Car road routing is untouched.
- Internal tests caught a landing threshold dead zone at AGL 0.20; landing confirmation now accepts the same 0.22 tolerance as the vertical controller.
- Mind actions and routing did not change. `SOL_MODEL_CARD.md` was regenerated only to clear its stale generated section so the standard launcher gate can pass; no Mind command was added.

### Devil's Advocate — failure modes still open
- The control simulation is a deterministic mock of climb, horizontal movement and descent. It does not reproduce AviationCore's physics forces, rotor warmup, a real helicopter model, a real native timed-action queue on Sol, keys, terrain, collisions or operator-manual possession. These require an in-world test.
- If the engine-start wrapper or timed action rejects a non-local Sol actor, the 30-second timeout should expose that; this patch intentionally does not bypass the gate or call `tryStartEngine` directly.
- The existing low/medium/high numeric targets remain provisional until calibrated in the actual helicopter.

### Strategist — acceptance gate
- Scope is source plus isolated SOL_LAB only. MAIN, Steam's regular profile, release packages, Workshop files and saves are not targets.
- Offline evidence required before launch: s121 route/landing regression, s124 handoff/installer regression, s125 authorization/start/timeout/altitude tests, an integrated climb → coordinate travel → landing simulation, Lua 5.1 compilation, launcher preflight and a dated LAB backup.
- Live acceptance remains pending: (1) with the helicopter stopped and Sol qualified, choose a marker and verify native engine start; (2) verify visible climb before horizontal motion; (3) verify direct GPS movement and arrival; (4) press `هبطي هون` and confirm landing; (5) verify manual/qualification denial and no false “flight started” when denied; (6) check Sol/LF/AviationCore logs. Do not call flight fixed or promote the release until these pass.

## s126 — transfer only player-earned helicopter manual knowledge (2026-11-13)

- Live s125 failed before engine start. The log repeatedly reports `[AviationCore][AIRCRAFT_START_BLOCKED] ... reason=missing_type_knowledge`, followed by `[SolHeliGPS] engine start refused`. It also reports `AIRCRAFT_MANUAL_ALREADY_INITIALIZED`; source inspection proves this is a per-vehicle glovebox/manual initialization marker, not proof that either character read the manual.
- AviationCore keeps operating knowledge in each character's own mod data. Its UH-1B definition requires `UH1B_OPERATING`; reading the operator manual grants that key to the reader. Sol's NPC record therefore does not inherit the player's training automatically.
- `SolHeliGPS` now checks Sol's qualification; if she lacks only the aircraft-specific key, it asks AviationCore whether the human player is qualified. Only after that succeeds does it grant the registered operating key to Sol, then re-runs the native authorization before calling the game's engine-start action. This preserves the manual gate and never fabricates knowledge when the player has not read/earned it.
- If the player is also unqualified, the route stops with `operator_missing_type_knowledge` and does not queue an engine start. When Sol is already qualified, it does not modify her knowledge. Car control and the separate AviationCore/FlightRuntime bridge are unchanged.
- Offline s126 checks pass: manual gate rejects both unqualified characters; no grant or engine action on denial; player-read knowledge is copied to Sol with the recorded source; Sol's own qualification still works; native start stays pending until the engine is running; prior climb/GPS/landing regressions and integrated simulated flight pass.
- Live acceptance is still pending. After installing the new file into SOL_LAB following game exit and a dated backup, read the UH-1B operator manual with the player if needed, then choose GPS Fly. Expected sequence: `operator manual knowledge learned from player key=UH1B_OPERATING`, successful AviationCore authorization, engine readiness, selected-altitude climb, direct GPS travel, and touchdown only after the landing command. Do not repeat the current loaded-code attempt or promote a release until this passes.
