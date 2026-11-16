# Station refuel: station survey (s95, switch `station_survey`, OFF)

Order: "عبي السيارة بنزين من الكازية" -> model action `refuel_at_station` -> Mind goal `refuel_errand` -> game verbs `sol_fuel find / car_near / park / park_status / car / status`.
Jamal (2026-11-11): it works about 1 time in 10; she often does not know where the pump is. He wants a small system, used only for this order, that learns the station and parks with the fuel cap beside a pump.

Labels: **confirmed** = in a log line or the game's code; **inference** = reasoned from logs and dumps, not seen directly; **needs in-game test**.

## 1. What the logs say (all attempts)

Sources:
- Mind log `05_TOOLS/sol_mind/sol_mind.log`: every `refuel_errand` goal and its end, 2026-11-08 to 2026-11-11.
- Lab DebugLogs: `07_TEST/SOL_LAB/profile/Zomboid/Logs/*DebugLog.txt` and the `logs_*` folders; tags `[SolActions] sol_fuel`, `[SolFuel]`, `[SolNav]`, `[SolMoveCheck]`, `[SolDrive]`.
- Main profile logs `C:\Users\JAMAL\Zomboid\Logs`: no `sol_fuel` or `[SolFuel]` line at all. The station errand was never run in MAIN.
- Station layout: `profile/Zomboid/Lua/SolPerception_1794354139165.txt` (00:42, tiles and car outlines round the gas2go forecourt). The cars' poses during the 00:37-00:41 attempts come from the dumps written every 20 s.

**21 errands. Two fills are confirmed by the game log, so the real success rate is 2/21 = 9.5% (confirmed).** Jamal's "1 in 10" is right.

| Outcome | Count | Evidence |
|---|---|---|
| Car filled (game log `status -> true done:N`) | 2 | 2026-11-09 00:30 `done:15`; 2026-11-10 18:04 `done:2` (the drive back then failed on an unrelated LF action, `return_compatibility_action_owned:visual:loot_container`) |
| Mind PASS with no game log for that hour | 2 | 2026-11-10 01:09 (38 s in all, `exit_vehicle` refused "vehicle is moving", so very likely no fill) and 01:17. Not verifiable. |
| Failed before the pump (not a station problem) | 8 | `bridge_failure` 5 (11-08 21:58, 11-09 21:54 x2, 11-10 01:10, 01:12); `outbound_timeout` 2 (11-08 22:38, 22:49); `drive_job_active` 1 (11-09 00:27) |
| Failed at the pump | 9 | see below |

At the pump, 11 errands reached the station and 2 filled (18%). On the code since 2026-11-10, 1 of 6 filled.

Failures at the pump, by cause:

| Cause | Count | When | Evidence | Label |
|---|---|---|---|---|
| Her walk to the cap was cut by `move_check` ("N tiles from him: there"). He sat in or stood by the car, and her target square was within 2.5 tiles of him, so every `solGoto` was answered "arrived" and LF made her `stay`. | 2 | 11-11 00:37, 00:38 | Log: each `solGoto(7308,8180)` / `(7308,8179)` is followed in the same frames by `[SolMoveCheck] 1.4 / 0.7 tiles from him: there` and `LF command stay`, then `every square near the work was tried`, then `no_way_to_pump`. Replayed offline. | confirmed |
| Car at the pump by the game's 5x5 test, but no free square by the cap. The body stood 0.72 tiles from the island, and every square within reach of the cap was the pump, the bin, the lamp post or under the car. | 1 | 11-11 00:40 | `car_near -> true near`, then `no free square within reach of the work`. Body 7305.9-7309.27 x 8179.72-8181.13 in the 00:40:59 dump. Replay: heading west with the cap on the island side reproduces both log lines. | inference (reproduced) |
| The Java park found no pose at all (`no_parking_spot` in under a second), then four blind GPS hops round the pump, all `pump_too_far`. | 2 | 11-11 01:51 (fossoil, 4 pumps), 02:14 (gas2go, 2 pumps) | `[SolNav] no plan: no_parking_spot`. The planner logs no reason. Replayed with `S95ParkReplay.java` on the 00:42 layout it finds 3-6 poses, so the forecourt at 02:14 was different. A Bradley stood there with its engine on at 02:14:02. Fossoil: no dump. | cause **not provable** from the logs |
| Walk refused: the old target square was under the car | 2 | 11-08 23:17, 23:21 | `the walk was refused` x8 each | confirmed, fixed 11-09 (work squares) |
| Park plan `out_of_time` x2, then hops | 1 | 11-08 21:20 | `parking failed: failed:out_of_time` | confirmed, old planner budget |
| The action started while she was not at the cap (`isValid` false) | 1 | 11-08 21:57 | `pumping into the car` then `pump_failed` 4 s later | confirmed, pre-walk code |

Asked-for classes not seen in any attempt:
- wrong pump: 0;
- pump without fuel or power: 0 (one pump had only 272 units, but not 0);
- LF seated her again: 0 (the errand's `hold` worked);
- KI5 multi-tank or odd cap: 0 (all attempts used the same small car).

## 2. Research: what the game itself does (B42.22 Lua, read)

- `ISVehiclePartMenu.getNearbyFuelPump(vehicle)` (`lua/client/Vehicles/ISUI/ISVehiclePartMenu.lua:25`):
  - takes the square under `vehicle:getAreaCenter(part:getArea())` of part `GasTank`;
  - scans dx, dy in -2..2 and returns the first object with `getPipedFuelAmount() > 0`;
  - returns nil if any of the 25 squares is not loaded;
  - has no power test. The menu adds one (`ISVehicleMenu.lua:1088`): `hasGridPower()`, or `AllowExteriorGenerator` and `haveElectricity()`.
- `onPumpGasoline`: get out, `ISPathFindAction:pathToVehicleArea(player, vehicle, GasTank area)` (`PathFindBehavior2.pathToVehicleArea`), then `ISRefuelFromGasPump`. If the path fails: "IGUI_PlayerText_NoWayToFuelTankInlet".
- `ISRefuelFromGasPump:isValid` is only `vehicle:isInArea(area, character)`. Duration is litres x 50. The pump loses 8 units per `Vehicles.JerryCanLitres`.
- The `area GasTank` rectangle is in the vehicle script, in the car's own frame, outside the body:
  - small car: `-0.5989 -0.6703` (right rear);
  - 46 vanilla scripts: `0.6758 -0.788` (left rear);
  - others: right side, or further forward.
  - So the cap side and position must be read per vehicle (`getAreaCenter`), never assumed. This is also what makes KI5 vehicles work.
- The standing position the game uses is that area itself. So the walk target is `getAreaCenter(GasTank area)` (what SolFuel already used), and a square counts only if it is free now and not under any car.
- `CarRefuelRequiresHose` appears in sandbox dumps. No Lua line in the pump path reads it (grep). Open: it may be read in Java.

## 3. Design

### Jamal's rule (2026-11-11, verbatim): "لازم تحسب مربع فاضي دايما بين غطاء البنزين والمضخة"

This is the **first** constraint when choosing a pose, not something searched for after parking:
- The fuel cap faces the pump, with one free square between the car body and the pump or island. She stands on that square to refuel.
- That square touches the pump square. Seen from the cap, the pump lies beyond it. The body stays 0.3 clear of it.
- It holds no car, bin, post or player, and she can walk to it from her door.
- It is within the game's reach of both the cap (the cap's square within 2 of the pump) and the pump. The gap is computed from the vehicle's real size and its real cap point, so KI5 vehicles are covered.
- A car flush against the island is never accepted, even when the game's 5x5 test would pass. That was the 00:40 case.
- If no pose at any pump keeps that square, she says so **before** parking ("ما في محل فاضي جنب المضخات") and does not try.
- After the stop, the same rule is checked again from the real pose (`no_free_square_between`), which leads to a re-park.

### Engineer
New file `SolStationSurvey.lua`, used only by `sol_fuel car_near / park / park_status` and by the walk squares of `sol_fuel car`, and only while `station_survey` is on.

1. **Survey, once per station per life.**
   - Reads the 25 x 25 squares round the pump: pumps with fuel (the game's own test), squares nobody can stand on (`isSquareFree`, the walker's own test), and walls between squares (`isBlockedTo`).
   - Kept in ModData `Sol_StationSurvey` under her life key (`Sol_Life` id#deaths); a new life empties it.
   - Read again after 24 game hours, or when it finds no pose from a cached read.
   - Fuel, power, other cars (`isIntersectingSquare`) and the player are read fresh each time. No per-tick work: the only OnTick work is the park order's state machine while one runs.
2. **Poses.** For each pump with fuel and power, 4 grid headings, and every square touching the pump (the free square between, see the rule above):
   - the car centre that puts this car's cap point beside the standing square (side cap: body 0.3 from the square; end cap: same at the end);
   - the cap's square within 2 squares of the pump (the game's rule) and within 1.5 of the standing square;
   - the body plus 0.15 on free squares, with no wall through it;
   - a clear lane ahead or behind, one body long;
   - a walk round the parked body from her door (seat area from the script; both sides when it has none) to the standing square.
   - Score: distance, turning, the free square straight across from the pump rather than diagonal, lanes open at both ends, her own door. The lane wanted is one body long, at most 6 squares, so long trucks are not refused for a 30 m run. The best pose per pump and heading is kept.
   - It logs how many poses each check removed (reach / body / lane / door), so a "no pose" is always explained.
3. **Drive.** `solNavPlan` (the existing Java planner, path follower and stall handling) to the best pose's centre and heading.
   - A failed plan goes to the next pose (at most 8).
   - After the stop: the game's own `getNearbyFuelPump` from where the car really is, power, a free square by the real cap, and a walk to it from her door.
   - If that check fails she re-parks at the next pose (other side or other pump), at most 2 times, and says why once ("الخرطوم ما بيوصل من هالجهة، عم غيّر المضخة" / "غطا البنزين مو جهة المضخة، عم صف من الجهة التانية").
4. **Before she gets out**, `car_near` runs that same check. A car already at a usable pump is filled where it stands. A stop with the cap side blocked (the 00:40 case) re-parks instead of failing on foot.
5. **Walk.** The squares within 1.5 of the real cap point that are free now, not under any car and not his square, nearest the cap first.
   - `move_check` no longer answers "there" to her walk to the cap (`SolUI.solFuelWalking()`, only while the switch is on and the walk is running). Every other walk is unchanged.
6. **Plain failure lines** from real checks, spoken by the Mind:
   - `survey_no_pump` "ما في ولا مضخة فيها بنزين وعليها كهربا بهالكازية."
   - `survey_no_pose` "ما في محل فاضي جنب المضخات، ما رح جرّب صف." (said before any drive)
   - `survey_no_stand` (after 2 re-parks)
   - `survey_drive_failed`
   - `survey_no_cap`
   - Each also goes to `SolFailNote` for "ليش".
   - A `survey_*` failure ends the errand at once. Before, there were four blind GPS hops.

### Devil's Advocate
- *Grid headings only*: a station built on a diagonal would get no pose. Every station seen so far is on the grid, and the log counts "body" hits so it will show. If it happens, add the pump-island axis as a fifth heading.
- *Lua scan cost*: about 2,000 method calls, once per station per life (measured offline: 1,903 square reads the first time, 28 the next). Java would be faster, but a jar change needs a ZombieBuddy approval for a one-off read.
- *The planner may stop off the pose*: this is what happened at 00:37 (a diagonal stop). That is why the check runs after every stop, with at most 2 re-parks.
- *`move_check` exemption*: only while her fuel-cap walk runs and the switch is on. A walk to him still stops 1.5 tiles from him (tested).
- *Not fixed here*: `bridge_failure` and `outbound_timeout` (8 of 21 errands) happen before the station; they are separate items (A7). The 01:51/02:14 `no_parking_spot` cause is unknown; the survey now logs its counts.
- *The other agent (s94 tankers)* may touch `refuel_from_can`, `SolCanRefuel` and the card. This change anchors only on station lines in SolFuel (`solFuelHeld`, after `local s = actor()`, the `workSquares` line), the near-him line in SolMoveCheck, and `parking_wait` / `GENERIC` in `RefuelErrand`. No card change.

### Strategist
- Ships OFF, in the lab too (`station_survey=off` is written, because a missing switch reads ON in the lab). Turn it on for one test session at the gas2go station: the same car, him in the passenger seat, both lanes, then a parked car in one lane.
- Watch `[SolStation]` (poses, counts, after-the-stop check), `[SolFuel] walking to the fuel cap`, and the absence of `[SolMoveCheck] ... from him: there` during the walk.
- Next, if needed: a diagonal heading; the Java scan if the read ever shows in `[SolPerf]`; the pump-island axis taken from the pumps' own sprites.

## 4. Files (staged in `07_TEST/SOL_LAB/_pending_refuel`)

- `SolStationSurvey.lua` (new).
- `apply_s95_station_refuel.py <client dir> [<switch file>]`: hooks in `SolFuel.lua` and `SolMoveCheck.lua`, `"station_survey"` in `SolAuthority.A.FIXES`, `station_survey=off` in `SolFixes_LAB.txt`. Idempotent; refuses when an anchor is not found exactly once.
- `apply_s95_station_refuel_mind.py <sol_mind dir>`: `RefuelErrand.TELL` lines, `PARK_SAY`, and `parking_wait`. The model card is unchanged; `card_check` PASS on a patched copy (4580/4600).
- `test_s95_station_refuel.py`: 136 checks, ALL PASS offline:
  - installers on copies: idempotent, Kahlua compile, ASCII, tonumber gate;
  - a 10 x 7 matrix of station shapes and vehicles (cap right / left / rear, no seat area, KI5 9 m truck, 15 m tractor). Every chosen pose is re-checked by an independent Python checker, which also asserts that the free square lies between cap and pump. Narrow lanes where the square cannot be kept must give no pose;
  - a car flush against the island: not accepted, re-parked, then a free square lies between the real cap and the pump;
  - replays of 00:37, 00:38 and 00:40 on the real forecourt (old code reproduces the logged failures; survey on fills);
  - faults: failed plan, bad stop, re-park limit, every lane taken, no power, pump dry;
  - the per-life cache;
  - the Mind `parking_wait`;
  - a check that the code holds no names or map numbers.
- `S95ParkReplay.java`: evidence only (the shipped Java park on the real forecourt), not in the jar.

## 5. Install (game closed, Mind stopped)

1. Back up `SolFuel.lua`, `SolMoveCheck.lua`, `SolAuthority.lua`, `SolFixes_LAB.txt` and `05_TOOLS/sol_mind/goal_engine.py` into `_backup/<date>_before_s95`.
2. `set PYTHONIOENCODING=utf-8`, then run:
   - `python apply_s95_station_refuel.py ..\profile\Zomboid\mods\Sol_LAB\42\media\lua\client`
   - `python apply_s95_station_refuel_mind.py C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind`
3. Run `card_check.py 05_TOOLS\sol_mind` (expect PASS), then `test_s95_station_refuel.py`.
4. To test: set `station_survey=on` in `SolFixes_LAB.txt`, launch with `launch_lab.ps1`.
5. Rollback: `station_survey=off` (the old paths come back exactly), or copy the backups back.

## s95b (2026-11-11, after the 10:26 lab run): approach point first; the tank of HER car

**What happened at 10:26.** The survey worked: 3 good poses (2 west-facing south of the islands, 1 south-facing between
them). The Java planner answered `no_path_found` for all 3 and the errand ended `survey_drive_failed`.

**Cause (evidence).** The GPS leg ended on the road 28-36 m west of the pumps, the car facing north (perception dumps
10:26:05 -> 10:26:25). `S95bPlanReplay.java` replays the three `solNavPlan` calls through the shipped planner on the forecourt
of the 10:26 dumps: poses 1 and 2 spend all 60000 search states (`MAX_NODES`) and return `no_path_found`; pose 3 needs 59335
of 60000 offline (the game adds an off-road cost the dump does not keep, so it ran out there). Not the goal handoff: the same
three goals are found at once from 8 m east of the islands (centre -> rear axle, heading vector and cap side are right).
Not the reverse limit: with `solNavMayTurnBack` the far poses still spend all 60000 states. A pose facing back the way she
came, 30 m off, does not fit in the search.

**Fix (Lua only, SolStationSurvey.lua 0.2.0).** Further than 8 m, she first drives to an approach point beside the pose's
open lane end (2.5 / 4 m either side, the body on free squares, facing from the car towards it), then plans the short turn
into the pose from where she stopped. Through the lane ahead she backs in (`solNavMayTurnBack` for that plan only). A failed
approach -> the next (3 at most) -> the pose straight -> the next pose. Replay with the real planner: pose 1 by approach
(1 + 9426 states), poses 2 and 3 likewise; the s95 Lua on the same replay gives the logged 3 failures.

**Tank (Mind).** At 10:27:38 the model branch said "مليانة (100%)" while the Dart had 57.121 / 59 (96.8%): it read the car
nearest HIM (he was at the station's own parked car). Now `goal_engine.tank_gate` reads the car she would fill (the one she
sits in, else the nearest to her within 15): >= 99% she refuses with the number and does not drive; 90-99% "فيها 96%، رح
كمّلها." and goes; below 90% she goes. Used by the model branch and by the errand before any drive.

**Install.** Lua: `python apply_s95b_station_approach.py ..\profile\Zomboid\mods\Sol_LAB\42\media\lua\client` (game closed,
or a debug reload of SolStationSurvey.lua alone: the file adds no second tick when reloaded). Mind:
`python apply_s95b_tank_mind.py C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind`, then restart the Mind.
Test: `test_s95b_station_approach.py` (49 checks).
