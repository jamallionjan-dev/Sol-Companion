# Sol's spatial awareness: doors first, then windows, fences last (`spatial_access`)

## ملخص لجمال

**شو المشكلة (من الكود والسجل، مؤكد):**
- سول بتمشي بـ A* تبع Living Fellows. هاد بيحسب السياج الواطي بـ 2.5 والشباك المفتوح بـ 2.5، والباب المسكّر بـ 2.2 (`SCTopology.lua:943-1011`).
- يعني إذا البوابة أبعد بمربعين، بتنط عن السياج.
- ونقطة الوقفة عند الصندوق كانت جاية من `interactionTargets`، وهاي ما بتفحص الزوايا (`SCNavigation.lua:7591-7606`). فكانت توقف ورا السياج أو ورا الحيط.
- بالسجل: نطّت 4 مرات بالمزرعة، يوم 10-11 بين 04:31 و05:53. ومرة منهن (عند 7402,8264) البوابة الحقيقية كانت على بعد 5 مربعات بس، عند 7402,8259. هالشي طلع من ملفات خريطة اللعبة نفسها.

**شو عملنا (مجهّز، ما انركّب، المفتاح `spatial_access`):**
- `SolPlace.lua`: سول بتعرف شو بين كل مربعين: مفتوح، باب، شباك، إطار شباك، سياج، أو حيط. وبتعرف إذا الباب مفتوح أو مقفول أو مدعّم.
- **الطريق:**
  - الباب بيكلّف تقريباً ولا شي.
  - الشباك بيكلّف متل 25 مربع مشي، والسياج متل 60. والحيط والباب المقفول ممنوعين.
  - يعني بتلف للبوابة إلا إذا كانت أبعد من 30 مربع.
  - الطريق بينحسب شوي شوي بكل فريم، فما بيعمل تقطيع.
- **المشي:** كل `solGoto` تبعها صار يمشي على مراحل: لعند الباب، بعدين بعد الباب، بعدين للهدف.
  - هاد بيغطّي: الترتيب، والمزرعة، والحيوانات، والمشي لباب السيارة، وغيرها.
  - وبنفس الوقت رفعنا سعر السياج والشباك بحساب Living Fellows، إلها هي بس، وبس إذا ما في زومبي قريب.
- **الصندوق:** بتوقف بس من جهتو، يعني ولا سياج ولا حيط ولا باب مسكّر بالنص. وهالشي داخل بالترتيب 0.2.2 وبالمزرعة وبالحيوانات.

**اختبارات خارج اللعبة:** 55/55 على خريطة المزرعة الحقيقية (من ملفات اللعبة)، وعلى أشكال مصنوعة، و150 شبكة عشوائية. والترتيب 64/64.

**باقي:**
- تجربة باللعبة.
- `sol_place dump` بيكتب المربعات الحقيقية حواليها، لأن ملفات الخريطة ما فيها الشي اللي إنت عمّرتو أو كسّرتو.

Status 2026-11-10: research done, built behind switch `spatial_access`, staged in `07_TEST\SOL_LAB\_pending_refuel` (not installed): apply_s70 (place model, sort/farm/animals), apply_s72 (boarding, far walk-in, far car arrival, far speech). Council: `SOL_REVIEW_20261109.md` §36, §37, §39. Sources: §10, §11.6. Far car inside the loaded area (Java SolCarArrive): §11.

Legend: **[C]** = confirmed, with the file:line or bytecode where it was read. **[I]** = inference.

---

## 1. Vanilla pathfinding in 42.22.2

### 1.1 Two pathfinders; the native one is live
- **[C]** `zombie.pathfind.nativeCode.PathfindNative` is a JNI front end:
  - native calls: `findPath`, `updateSquare`, `updateChunk`;
  - library `PZPathFind64.dll` in the game folder.
- **[C]** `useNativeCode` is set to `true` in its static initialiser (javap `PathfindNative.<clinit>`).
- **[C]** `checkUseNativeCode()` switches between the native pathfinder and the Java `PolygonalMap2` from `DebugOptions.pathfindUseNativeCode`.
- **[I]** The native code is a port of the Java one. Its costs cannot be read, so the Java code below is the reference.
- **[C]** `PathFindBehavior2` is the per-character driver:
  - `pathToLocation(F)`, `pathToCharacter`, `pathToNearest(Table)`, `pathToVehicleArea/Seat/Adjacent`;
  - private `checkDoorHoppableWindow`.

### 1.2 What a mover may do
- **[C]** The request flags are `nativeCode.PathFindRequest` fields: `canCrawl, crawling, ignoreCrawlCost, canThump, canClimbFences, canClimbTallFences, avoidFarmingPlants, hasTarget, canBend`, plus `knownBlockedEdges`.
- **[C]** `init()` (`PathFindRequest.java:45-70`) sets all flags false, then fills them in:
  - only animals get `canThump`/`canClimbFences`;
  - zombies get the crawl flags;
  - an **IsoPlayer** gets only `canClimbTallFences = SandboxOptions.easyClimbing || getClimbingFailChanceFloat() < 1`.
- **[I]** For a player, nothing in the request turns off low-fence hopping. Players always hop low fences. There is no "avoid climbing" switch to set from Lua.
- **[C]** `KnownBlockedEdges` is a class with fields x, y, z, w, n, and requests carry a list of them.
  - **[I]** That list is the only per-request way to forbid an edge. Nothing on the Lua side fills it, so using it would need a Java patch.

### 1.3 Edge costs (Java reference `SearchNode.c()`, `SearchNode.java:78-149` from its LineNumberTable)
- **[C]** Square bits (`PolygonalMap2` constants):

  | Bit | Value |
  |---|---|
  | COLLIDE_W | 2 |
  | COLLIDE_N | 4 |
  | WINDOW_W | 2048 |
  | WINDOW_N | 4096 |
  | CAN_PATH_W | 8192 |
  | CAN_PATH_N | 16384 |
  | THUMP_W | 32768 |
  | THUMP_N | 65536 |
  | THUMPABLE | 131072 |
  | DOOR_E | 262144 |
  | DOOR_S | 524288 |
  | WINDOW_W_UNBLOCKED | 1048576 |
  | WINDOW_N_UNBLOCKED | 2097152 |
  | DOOR_W_UNBLOCKED | 4194304 |
  | DOOR_N_UNBLOCKED | 8388608 |
  | HOPPABLE_N | 1<<24 |
  | HOPPABLE_W | 1<<25 |

- **[C]** Cost of a step is `dist + extra + Square.cost` (`SearchNode.java:78-149`).
  - Crossing a **window** (lines 91-105): extra = **20** if unblocked (open or no glass), **200** if shut. This applies to every mover except a walking zombie.
  - THUMPABLE square (109), THUMP edges (129-146), and connections with `CXN_FLAG_THUMP` (114-122): extra = max(extra, 20).
  - **CAN_PATH + COLLIDE** edge, i.e. a hoppable fence (149+): extra = max(extra, **20**).
  - Crawl: +10.
- **[C]** No branch adds anything for a door, so for a player a door is free. `Square.isUnblockedDoorW/N` exists, and only animals use it.
- **[I]** For Sol as a player:
  - a closed door costs 0 and she opens it on the way (`PathFindBehavior2.checkDoorHoppableWindow`);
  - a low fence costs about 20 tiles;
  - an open window costs 20 and a shut one 200.

  So **the engine alone** goes round to a gate up to about 20 tiles away. The bad choices come from the Lua layer above it (§2).
- **[C]** `IsoGridSquare.canReachTo` (`IsoGridSquare.java:1120-1143`) rejects a neighbour across `isWindowBlockedTo`, `isDoorBlockedTo`, a wall (`getWallExcludingList` on WallN/WallW/DoorWall flags), stair tops, or `isWallTo`.
  - `isWallTo` resolves to `isWall(facing)`, which is `collideN/W && !isWindow` (lines 998-1001).
  - `isBlockedTo` (1112-1116) = wall, window blocked, door blocked, or stair.
- **[C]** Low fence tiles (`fencing_01_1`: `HoppableN`, `WallNTrans`, `wall`) carry no `collideN` in the tile definitions (`newtiledefinitions.tiles.txt:34379-34392`).
  - **[I]** The engine derives collide flags from `WallNTrans` when it loads the sprite. Even if it does not, `isHoppableTo` covers fences, and SolPlace asks it first.
- **[C]** `IsoRegions.calculateSquareFlags` (`IsoRegions.java` bytecode ~920-990) builds the room/region flags from `cutN/W`, `WindowN/W`, `windowN/W`, `DoorWallN/W` and `solidfloor`. Low fences are not in that list.

### 1.4 Vanilla Lua (from the subagent's read of `media/lua`; file:line as it reported, spot-checked)
- **[C]** `AdjacentFreeTileFinder.lua`:
  - `privTrySquareForWalls` (4-36) rejects a neighbour across `cutW/N` or `collideW/N`. It accepts one through a `DoorWall` only if the door is not blocked.
  - `Find` (135-184): sides first, corners only if no side qualifies. It takes the candidate closest to the player that passes `canReachTo`.
  - Corners need all four L-legs clear.
- **[C]** `luautils.walkToContainer` (306-361) uses `Find`. Its early return at `DistToProper < 2` (312) has **no `canReachTo` check**, so a container just behind a wall counts as reached.
- **[C]** `ISWalkToTimedAction` (`WalkToTimedAction.lua:10-44`) calls `pathToLocation` and finishes on `Succeeded`/`Failed`.
- **[C]** No vanilla Lua sets any climb or fence preference. The only path calls are the `pathTo*` family.

## 2. How Sol walks today and why she climbs
- **[C]** `U.solGoto(x, y, z)` (`SolActions.lua:580`) goes to `gatewayGoTo` (564). That is LF `AIToolGateway` `go_to`, falling back to `move_to`. So every Sol walk is a Living Fellows navigation request.
- **[C]** LF runs its own time-sliced Lua A* over squares (`SCNavigation.lua`: `passableEdge` 1177-1307, `heuristic` 1310). Edge prices come from `SC.Topology.classifyEdge` (`SCTopology.lua:737`, cached per read batch at 1035-1080):
  - open door **1**, closed door **2.2** (`SCTopology.lua:943`);
  - window open **2.5**, smashed **4**, shut **35** (965-966); window frame **2.5**;
  - **low fence 2.5**, tall fence **4.5** (1009-1011);
  - the same values again in the fallback branch, `SCNavigation.lua:1270-1287`.
- **[C]** So **a fence costs 1.5 more than an open step**. Any gate further than about 1 tile of detour loses to the fence. That is the direct cause of "she jumps over the fence with the gate right there".
- **[C]** Crossing segments run on the engine:
  - `SCNativeActions.lua:834` calls `pathToLocationF`;
  - multi-target interaction approaches use `pathToNearestTable` (`SCNativeActions.lua:753`, chosen at `SCNavigation.lua:7770-7776` when the intent has no `preferVerifiedPath`).
- **[C]** Standing squares come from `Navigation.interactionTargets` (`SCNavigation.lua:7574`).
  - Without `requireDirectAccess` it checks cardinal neighbours with `isBlockedTo` only.
  - It accepts the **four corners with no wall check at all** (7591-7606).
  - It returns the target square itself when nothing qualifies.
- **[C]** Who calls it that way:
  - `SolFarmWork.walkTo` (`_pending_refuel/SolFarmWork.lua:601`);
  - `SolAnimalCare.walk` (`SolAnimalCare.lua:266`);
  - SolSort 0.2.0 (its own 0.2.1 header records this).

  This is the "stands behind the wall/fence" symptom.
- **[C]** Evidence in the lab logs (`profile/Zomboid/Logs`):

  | Log | Line | Time | Square | Context |
  |---|---|---|---|---|
  | `logs_2026-11-10_03-49/2026-11-10_03-48_DebugLog.txt` | 12414 | 05:20:08 | `7402:8264` | `ClimbOverFenceState`; preceded by `solGoto(7402,8265)` (12407) and `LF command follow` (12412) |
  | same | 14279 | 05:44:36 | `7395:8257` | after `solGoto(7400,8256)` |
  | same | 15443 | 05:53:40 | `7395:8257` | after `solGoto(7398,8257)` |
  | same | 10032 | 04:31:37 | `7227:8291` | |
  | `logs_2026-11-09_21-49/2026-11-09_21-47_DebugLog.txt` | 11790 | | `7408:8258` | the fence row north of 8258 |

- **[C]** The vanilla map files (`media/maps/Muldraugh, KY/28_32.lotheader` + `world_28_32.lotpack`, read with `src/extract_place.py`) show:
  - `7402,8264` has `fencing_01_27` (`HoppableW`, the east paddock fence, x=7402);
  - **a gate (door in the fence line) at `7402,8259`, five tiles north**;
  - the fence at x=7396 (`7396,8257` `HoppableW`).

  These fences are the map's own paddocks, not ones he built.

## 3. Community (ideas only, no code copied)
I checked about 320 Workshop mods (subagent survey; paths are under `steamapps/workshop/content/108600`).
- **[C]** None of them changes native pathfinder costs. All of them still walk with `pathToLocationF` and add a Lua layer that picks the entrance and feeds short legs.
- **Project A-Life** (3803984183):
  - Each building gets an entrance list from BuildingDef bounds ±1, with door state read per side and a time-sliced cache (`ALifeEntrances.lua:104-202, 449-620`).
  - Price table: open door 0, closed 2, window 6, glassy window 14, locked 14 (`:28-35`).
  - Routes go round the building's perimeter to the best entry (`:647-791`).
  - Doors it opened are closed behind it (`ALifeObstacleTraversal.lua:962-993`).
  - A climb budget switches to doors only after 3 climbs in 15 s (`:2060-2081`).
- **ProjectSurvivors** (3810955553):
  - Door-first exterior opening choice (`PS_Doors.lua:983-1023`).
  - Room-connectivity graph from RoomDefs (`:1075-1228`); `canReach` by graph (`:1316`).
  - Stand square must be same building, with no wall or window between, and have a way in (`:622-676`).
- **Stay With Me** (3800989007): a plain-walk BFS that refuses doors and climbs, used to test reachability (`BridgeMove.lua:3842-3880`).
- **Living Fellows** (3805760339; Sol's movement): the per-edge costs above, with no building model.
- Web: search backend failed. `github.com/slayer5934/Bandits` returned 404 and `pzwiki.net/wiki/Pathfinding` returned 403. No web sources.

## 4. Design (built; see §6)

### 4.1 Place model
- **Edge between two cardinal neighbours**, read as LF does (`isDoorTo`, `isWindowTo`, `isHoppableTo`, `isBlockedTo`, `getDoor(north)`, `getWindow`, `getThumpableWindow`, `getWindowFrame`). Order: door, then window or frame, then fence, then wall, otherwise open.
  - A tall fence is `isBlockedTo` and not hoppable, so it counts as **wall**.
  - **[I]** A tall-fence climb is never planned. The engine may still do one on its own.
- **Cache:**
  - The **kind** of each edge is cached per 8x8 chunk for 20 s.
  - The **state** of doors and windows (open, locked, barricaded, smashed, glass removed) is read live every time.
  - `OnObjectAdded`, `OnObjectAboutToBeRemoved` and `OnTileRemoved` drop the chunk, if those events exist.
  - **[I]** A per-building cache (BuildingDef) is not needed for correctness. Chunks cover outdoor fences too, which buildings do not.
- **Diagonal stride:** only when both corner squares are standable and all four L-legs are open, the vanilla corner rule.
- **Rooms:** not needed for routing. The edge graph already separates rooms. `IsoRoom` and `BuildingDef` are kept for later uses (A-Life-style entrance lists for far-away buildings).

### 4.2 Cost policy
- A step costs 1 (diagonal 1.414). Crossing adds:

  | Crossing | Extra cost |
  |---|---|
  | open door | 0.3 |
  | closed unlocked door, or locked and LF's `actorCanUnlock` says she can | 2 |
  | open window, or no glass | 25 |
  | shut window | 40 |
  | frame | 25 |
  | low fence | 60 |

- Not crossable: locked door she cannot open, barricaded door or window, wall, tall fence.
- Consequence: a door wins unless the window is about 25 tiles shorter or the fence about 60 tiles shorter. A fence is crossed only when no door or window route exists within that margin.

### 4.3 How walks use it
1. **`U.solGoto` wrapper.** It covers SolSort, SolFarmWork, SolAnimalCare, SolGPS door walk / car boarding, SolFuel, SolCanRefuel and SolOrders.
   - It plans a door-first route with a bounded A*:
     - search box = start/goal ±24;
     - at most 9000 nodes;
     - 600 nodes inline;
     - the rest in SolBudget slices with a clock check every 16 nodes.
   - If the route crosses something, it sends LF **legs**: the square before each crossing, the square after, every 10 tiles on open ground, and the goal.
   - The same goal asked again goes on with the same route.
   - It falls back to the old single order when:
     - the search fails or takes more than 2.5 s;
     - a leg stalls for 9 s;
     - zombies are within 7 tiles (fences are an escape then);
     - she is in a car or on another floor;
     - she is more than 4 tiles off the route (someone else is walking her).
2. **LF's own A* price**, for Sol only and only while no zombie is near: low fence +40 (2.5 to 42.5), window/frame +18.
   - This changes her follow walks and every LF route, including ones not started by `solGoto`.
   - LF caches the result object, so the raised cost goes on a copy, memoised and bounded at 4096.
3. **Access side.** `SolPlace.access(x, y, z)`:
   - the four sides first, corners only when no side works;
   - the square must be standable;
   - nothing between it and the thing: wall, closed door, window, frame or fence. An open door counts as nothing, as in vanilla `canReachTo`.
   - `SolPlace.reach` answers "can she use it from here".
   - Users: SolSort 0.2.2 `access` and `arrived` (also still `canReachTo`), SolFarmWork `walkTo`, SolAnimalCare `walk`. When the list is empty they fall back to LF's list.
4. **Not covered (yet):**
   - LF's own `SC.Vehicle.board` path (`pathToVehicleArea`), which uses the engine at about 20 per fence;
   - SolFar far-car walk-in, which does not call `solGoto`;
   - cross-floor routes (native).

   The LF price (point 2) still applies where LF plans with its A*.

### 4.4 Performance budget
- Planning only runs inside SolBudget slices (each slice ≤ the frame allowance, at most 4 ms), with a clock check every 16 nodes. The inline first call is capped at about 2 ms.
- Offline node counts on the real farm:
  - plot to outside the paddock: **49 nodes**;
  - plot to the west paddock: **492**;
  - yard into the kitchen: **375**;
  - 150 random 24x24 grids: about **60 nodes per route**.
- **[I]** At about 5-10 Java calls per node in game, a typical route is a few ms spread over 1-3 frames.
- Memory: one chunk table per 8x8 area touched, dropped after 20 s.

### 4.5 Switches
- `spatial_access` (A.FIXES, `SolFixes_LAB.txt` on). Off means exactly the old behaviour; this is tested.
- `item_sort` is unchanged; SolSort 0.2.2 only adds the optional SolPlace use.

## 5. Offline tests (`_pending_refuel/test_spatial_access.py`, lupa through `kahlua_env`): 55/55
- **Real map** (`place_fixtures/farm_7404_8262.json`, 53x55 tiles around 7404,8262; tiles and rooms from `28_32.lotheader`/`world_28_32.lotpack` and `media/tile_definitions/*.tiles.txt`; read through stubbed IsoGridSquares, so the live reader code runs):
  - the fence and gate facts above;
  - plot to outside goes through the gate at 7401,8259 to 7402,8259, with legs before and after;
  - the same paddock crosses nothing;
  - the west paddock goes by doors (43 steps, versus the fence);
  - access squares for 7404,8267, 7403,8262, 7396,8269 and 7404,8254 are on their own side;
  - a box on either side of the east fence is never used across it;
  - yard into the kitchen goes through 2 doors; with all doors locked, through a window, never a wall.
- **Synthetic:**
  - fenced yard with a far gate: the gate;
  - no gate: one fence crossing, and none in strict mode;
  - gate 20/24 tiles away: door; 35 tiles away: fence;
  - house: door over a nearby window; locked door: window; locked and barricaded: no route; open window still counts as a climb;
  - window versus fence: window;
  - wall from edge to edge: no route; no corner cutting;
  - access: box against a fence, room-corner diagonal, shut door versus open door.
- **Random:** 150 grids against a Python Dijkstra with the same prices. Costs equal, never through a wall, never a window or fence when a cheaper door-only route exists.
- **Walking through the wrapper** with an engine stub:
  - legs `(7401,8259) (7402,8259) (7403,8264)`, no leg asks the engine across the fence, and she arrives;
  - the way back also goes through the gate;
  - inside the paddock: one plain order;
  - switch off: one plain order;
  - zombie near: one plain order.
- **LF price:** fence 2.5 to 42.5 for Sol only, other companions 2.5, cached results not raised twice, doors untouched, window 2.5 to 20.5.
- **SolSort 0.2.2 on the real map:** standing squares of a box by the fence exclude the far side; standing across the fence is not "arrived"; switch off gives the 0.2.1 rule.
- **Regressions:**
  - `test_sort.py` 64/64 (its version check moved to 0.2.2; `apply_s67.py` accepts 0.2.2);
  - `test_animals.py` 21 pass;
  - `test_kahlua_names.py` and `test_kahlua_scan.py` all pass;
  - `test_farm_work.py` has the same 9 failures before and after this change (old apply_s20-23 checks).
- **Limit:** the map files hold only vanilla objects. What he built, opened or broke in his save is not there. `sol_place dump [r]` writes the live edges around Sol to `Zomboid/Lua/SolPlace_dump.txt` so those can become fixtures. Parsing the B42 save chunks offline (`map/<wx>/<wy>.bin`) was not attempted: it would mean reimplementing IsoObject loading.

## 6. Files (staged, nothing installed)
- `_pending_refuel/SolPlace.lua`: the module, plain ASCII, readable.
- `_pending_refuel/SolSort.lua`: 0.2.2, generated from `src/SolSort_src.lua` by `src/gen.py`.
- `_pending_refuel/SolFarmWork.lua`, `_pending_refuel/SolAnimalCare.lua`: staged copies with the access hook.
- `_pending_refuel/apply_s70_spatial_access.py <client dir>`: game closed, idempotent; run `apply_s67.py` first.
- `_pending_refuel/src/extract_place.py`: the read-only map extractor.
- `_pending_refuel/place_fixtures/farm_7404_8262.json`
- `_pending_refuel/test_spatial_access.py`

## 7. Risks
- **[I]** The engine leg itself could still hop a fence. That needs a short leg whose straight line crosses a fence while the planned path bends round it. Legs stop before and after every crossing and at most 10 tiles apart. The engine's own fence price (about 20) also works against it.
- **[I]** Raising LF's fence cost makes LF's A* expand more nodes before giving up on a fenced-in goal. LF's node budget may then fail where it used to climb. It then falls back to the native route (+20 fence). Watch `navigation` route failures.
- **[I]** `IsoDoor` locked state:
  - `isLocked()` and `isLockedByKey()` are read;
  - a door locked from her side that she can open from inside is "can unlock" only if LF's `actorCanUnlock` says so;
  - a garage or double door counts like any door.
- **[I]** Gates built by the player (`IsoThumpable` doors) rely on `isDoorTo`/`getDoor` covering thumpables, as LF assumes.
- Fleeing: the price raise and the route are off within 7 tiles of a zombie, and the 1 s danger cache can lag one second.
- Doors are left as LF leaves them: LF closes doors it opened (`closeOwnedDoors`). Nothing new here.

## 8. Runtime test plan (after `apply_s70` with the game closed)
1. Paddock: Sol at the plot (about 7400,8265), you just east of the fence at 7403,8264. Order "follow" or "come". Expected: she walks north to the gate (7402,8259) and back south, with no `ClimbOverFenceState` in the log. The log shows `[SolPlace] route ... doors 1 ... fences 0`.
2. Farm work with a water barrel or box on the other side of a paddock fence: the walk goes through gates. `sol_place status` counts routes and crossings.
3. Sort in the house: a box by a wall or fence is used from its own side, and she never stands behind it.
4. All doors of a small shed locked, one window: she goes in through the window. Barricade it: she does not climb a wall, and the old walk reports.
5. Zombies near: she still hops fences to escape, as before.
6. `sol_place dump 20` next to the garden, to keep real fixtures of his own builds.

## 9. Boarding, the far walk-in and the far car arrival (built; `apply_s72_far_arrival.py`, staged)

### 9.1 Door-first boarding and walk-in (switch `spatial_access`)
- **Driver's door walk.** **[C]** `SolGPS.takeWheel` already walks to the door square with `U.solGoto` (`SolGPS.lua:311-330`). The wrapper from §4.3 now routes it.
- **Passenger door walk.** **[C]** `SolOrders.startWalk` (`SolOrders.lua:359-373`) uses LF `Navigation.request` when it holds a supervisor token.
  - New `SolPlace.nextLeg(x, y)` gives the next square on the door-first way to the door.
  - `stepBoard` asks for the following leg as soon as she reaches one (`SolOrders.lua:455`).
- **Far walk-in.** **[C]** "she is here" (`SolFar.lua:~676`) used to send LF `regroup` only. New `SolPlace.goNear(x, y, z, near, onDone)` first walks her to within 3 tiles of him door-first, then sends `regroup` once.
  - If nothing is in the way, `regroup` goes at once.
  - **[C]** The appear-spot search already needs a door-only path (`SolFar.canStep`, `SolFar.lua:286-291`: fences and windows block, an unlocked door is a way through).
- **Test on his home:**
  - Home data is from `Zomboid/Lua/SolWorld_Snapshot.txt`:
    - `solHome` 7411,8258 r20;
    - `solParking` 7413,8264, bay 7411-7415 × 8259-8269.
  - Car 5 was last saved at 7411.5,8276.3 (`Sol_Far` mod data in the save copy).
  - From inside the farmhouse (7411,8252):
    - to the parking bay: 16 steps through the south door (7407,8255 → 7407,8256), 57 nodes;
    - to car 5's saved place: 28 steps, same door, 58 nodes.
  - `nextLeg` gives (7407,8255) then (7407,8256), then nil (plain walk).
  - Synthetic house + fenced garden + car on the street: through the house door, then the garden gate. Never the window or the fence.

### 9.2 Far car: confirmed cause of "record_failed" (2026-11-10 19:47:36)
- **[C]** The lab DebugLog `2026-11-10_18-45_DebugLog.txt`:

  | Line | Time | What |
  |---|---|---|
  | 24844 | | car 5 (hers) |
  | 24846 | | 190 tiles, fuel 0.227 |
  | 24888 | 19:47:31 | `[SolCarMove] 5 -> ok` |
  | 24891 | 19:47:36 | `record_failed` |

- **[C]** The same log shows `[Sol-Diag][gate] production_spawn_ready - no saved Sol is pending` every few seconds from 19:19 to 19:51. That message is `pendingCompanionCount() == 0`, `SCPersistence.lua:4155`. `captureRecord ok id=sc-...` also appears at each save. So she was a **registered companion with no body**, not a saved record.
- **[C]** In that state `SolFar.record()` returns `{ id = "live" }` (`SolFar.lua:76-81`).
- **[C]** `moveTick` handed `"live"` to `persistence.pendingRelocate`. Its first guard is `pending[id] == nil` (`SCPersistence.lua:4176-4178`), so it fails for `"live"` every time.
- **[C]** The walk-in at 19:51:14 ("appearing at 7221,8153") worked because `moveBody` handles `"live"` with `Actor.recover` (`SolFar.lua:321-333`).
- **[C]** The vehicle flag, spawn ticket and quarantine played no part.
- **[C]** The save copy (`global_mod_data.bin`, written 18:22) agrees:
  - her record at 7410,8274;
  - `Sol_Far` car 5 at 7411.5,8276.3, 650 kg, 38.6 l.
- **[C]** In the `vehicles.db` copy, car 5 is one row at 7280.5,8232.5, out of 35 rows.

### 9.3 Arrival as one unit
- **Where (Mind, `road_route.pickup_spot_dir`):**
  - on the game's own street polylines (gazetteer), from the street nodes, not the simplified route;
  - the last point on her way to him that is just outside what is loaded (ring + 2 chunks);
  - clear of buildings;
  - the same street runs straight for 12 tiles ahead and 6 behind (within 20°);
  - heading = that street's direction toward him.
  - A helicopter gets `heli_spot` instead: an open place with no building within 8 tiles, on the straight line toward him.
  - His trip gives (7277.5, 8232.5, heading -90°), 0.5 tiles from the street line, 11 chunks out. Today's spot was 7280.5,8232.5.
- **Before the car moves:** `F.canFollow()` checks she can come with it, either live, or a saved record persistence will move. If not, the car is **not** moved, the reason goes to the log, and she walks.
- **After the move:** a saved record is relocated beside the car (now with a reason on refusal). A live one waits for the car.
- **When the car's chunk loads (`F.arrive`):**
  1. The car is turned along the road. `setAngles` is used (vanilla `ISVehicleAngles.lua:128` uses it), then `getForwardVector` checks the turn took; both signs are tried.
  2. Her body comes back at the driver's door square: loaded, out of his view, safe, nearest by `getEnterSeatDistance(0, …)` (`BaseVehicle` javap).
  3. In the same second she takes the wheel with `SC.Driving.takeWheel` (`SCDriving.lua:164`).
  4. This is retried each second, up to 8 times. Meanwhile poll says "seeking", then "here".
- **Then:** the Mind says "صرت قريبة، عضّة كوساية وبوصل." once and starts `fetch_player`, quietly.
  - `fetch_player` now re-targets when he has moved 12 tiles (was 40; `goal_engine.py:809`).
  - It says "جايتك، استناني." once.
- **Kept as before:**
  - the car moves once (Java, one transaction);
  - fuel is taken once (`settleFuel`). The live log shows it once at 19:52-19:53, and the test shows 0.227 l once;
  - every failure falls back to her walking ("جاية، اصبر شوي.").
- **Not done:**
  - no clearance check on the road tile itself before the move (the chunk is not loaded). Java `spot_taken` checks other vehicles within 8 tiles (`SolCarMoveCore.CLEARANCE`), and an occupied spot falls back to walking;
  - zombies at the spot cannot be seen until it loads. She still gets in: the car is the safe place.
- **Not built (needs his decision):**
  - The spot is just outside what is loaded, so it only loads when he moves toward it. The 2026-10 rule says no chunk loading. A spot inside the loaded area would need a Java move of a live vehicle, which `SolCarMove` refuses by design (`target_loaded`).

### 9.4 Tests
- `test_far_arrival.py` 57/57:
  - the installer: applies, twice changes nothing, either order with `apply_s70b_mind`/`apply_s71_mind`;
  - Kahlua-like compile;
  - **before:** her case reproduced on the unpatched lab `SolFar.lua` with the save-copy data, giving `record_failed`;
  - **after:**
    - one move to 7277.5,8232.5;
    - nothing until the car loads;
    - at the door and at the wheel in the same second;
    - facing north;
    - poll "here";
    - out of his view;
    - fuel 0.227 once;
  - zombies at the spot; a record that cannot move (car not moved); a saved record moved beside the car (then door, then wheel); an occupied spot;
  - Bradley 210 s, KI5 car 180 s, helicopter 60 s;
  - the road spot on the real gazetteer; a curved road (not in the bend); the helicopter's open place;
  - all 60 far lines scanned: no `طرف منطقتك`, `مربع`, `خطوة`, `لتر`, fuel numbers, edge, teleport, record, java, spot, route;
  - the chat: placed says nothing; "here" gives the line, then a quiet drive; `spot_taken`/`move_timeout`/`record_failed`/`loaded` give a walk with "جاية، اصبر شوي.";
  - the `vehicles.db` copy: car 5 is one row.
- `test_spatial_access.py` 61/61, adding home, `nextLeg`, `goNear` and the synthetic house + garden + car.
- Game's own Kahlua compiler (`05_TOOLS/sol_kahlua` scan) on the patched files: 1402 files, 0 compile errors.

## 10. Sources

**Game 42.22.2: javap on `projectzomboid.jar`, line numbers from LineNumberTable**
- `zombie.pathfind.SearchNode.c()` (`SearchNode.java:78-149`).
- `zombie.pathfind.PolygonalMap2` BIT_* and CXN_* constants.
- `zombie.pathfind.Square` (`has`, `isCanPathW`, `isUnblockedDoorW`, …).
- `zombie.pathfind.PMMover`.
- `zombie.pathfind.PathFindRequest`.
- `zombie.pathfind.nativeCode.PathFindRequest.init` (`PathFindRequest.java:45-70`).
- `zombie.pathfind.nativeCode.PathfindNative` (static `useNativeCode = true`, `checkUseNativeCode`, `addRequest`) and `PZPathFind64.dll`.
- `zombie.pathfind.PathFindBehavior2` (`pathTo*`, `checkDoorHoppableWindow`).
- `zombie.ai.KnownBlockedEdges`.
- `zombie.pathfind.VGAStar`.
- `zombie.iso.IsoGridSquare`:
  - `canReachTo` 1120-1143;
  - `isBlockedTo` 1112-1116;
  - `isWall(facing)` 998-1001;
  - `isWallTo` 911-915;
  - `isWindowBlockedTo` 1147-1151;
  - `isDoorBlockedTo` 1159-1163;
  - `isHoppableTo` 1219-1224;
  - `getWallExcludingList` 4620.
- `zombie.iso.areas.isoregion.IsoRegions.calculateSquareFlags` and its BIT_* constants.
- `zombie.iso.IsoLot.load` (the lotpack format) and `zombie.iso.LotHeader`.
- `zombie.vehicles.BaseVehicle`: `save` layout, `setAngles`, `getAngleY`, `getForwardVector`, `getEnterSeatDistance`, `enter`.

**Game Lua and data (`media/`)**
- `lua/shared/luautils.lua:306-361` (`walkToContainer`, early return at 312); 119-157 (`walkAdj`); 229-247; 262-304.
- `lua/shared/Util/AdjacentFreeTileFinder.lua`: 4-36, 43-75, 106-129, 135-184, 231-285.
- `lua/client/TimedActions/WalkToTimedAction.lua`: 10-44.
- `lua/client/Vehicles/ISUI/ISVehicleAngles.lua:128`.
- `maps/Muldraugh, KY/28_32.lotheader` and `world_28_32.lotpack`.
- `tile_definitions/*.tiles.txt`, e.g. `newtiledefinitions.tiles.txt:34365-34725` (fencing_01) and 52232-52243 (fixtures_doors_01_5).

**Sol / Living Fellows (lab copy)**
- `SCTopology.lua`: 737-1080 (`classifyEdge` and its cache), 943-1011 (prices).
- `SCNavigation.lua`:
  - `passableEdge` 1177-1307;
  - `interactionTargets` 7574-7630 (corners unchecked 7591-7606);
  - `requestAny` native nearest 7770-7776.
- `SCNativeActions.lua`: 753 (`pathToNearest`), 834 (`pathToLocationF`).
- `SolActions.lua`: 564-592 (`gatewayGoTo`, `U.solGoto`).
- `SCPersistence.lua`: 3855-3910 (the restore loop), 4141-4167 (pending count and the spawn gate), 4176-4190 (`pendingRelocate`).
- `SolFar.lua`: 33-49, 76-81, 286-333, 564-590.
- `SolGPS.lua:174-330`.
- `SolOrders.lua`: 359-373, 400-476.
- `SCDriving.lua`: 164 (`takeWheel`), 660-672 (heading from `getForwardVector`).
- `SurvivorCompanionBridge.jar`: `SCNativeCompanion.pathToLocation/F` and `pathToCharacter` call IsoPlayer's (javap).

**Logs and save (copies only)**
- `Logs/logs_2026-11-10_03-49/2026-11-10_03-48_DebugLog.txt`: lines 10032, 12407-12414, 14279, 15443.
- `Logs/logs_2026-11-09_21-49/2026-11-09_21-47_DebugLog.txt:11790`.
- `Logs/2026-11-10_18-45_DebugLog.txt`: 24844-24891, 24915-24935.
- Copies of `Saves/Sandbox/2026-11-10_02-39-13`: `global_mod_data.bin`, `vehicles.db`, `players.db`, and map chunks `map/922-928/1029-1035.bin`. The chunks were copied but not parsed.

**Workshop NPC mods (ideas only), under `steamapps/workshop/content/108600`**
- **Project A-Life [ALIFE NPCS]** (3803984183), files under `ProjectALifeNPCs/42.20/media/lua/server/ProjectALife/Movement/`:
  - `ALifeEntrances.lua`: 28-35, 104-202, 449-620, 647-791;
  - `ALifeObstacleTraversal.lua`: 426-468, 546-593, 697-715, 962-993, 2060-2081, 3276-3300;
  - `ALifeMovement.lua`: 318-320, 716-723, 785-812;
  - `ALifeDoorPolicy.lua`: 40-170.
- **Project A-Life Jeem Extension** (3806944055): `Features/DoorMarks`.
- **ProjectSurvivors: Advanced NPC Mod** (3810955553):
  - `PS_Behavior.lua`: 128, 165-173, 255, 285-325, 995-1030, 3037-3043;
  - `PS_Doors.lua`: 39-47, 434, 622-676, 983-1023, 1075-1228, 1316, 1509;
  - `PS_Loot.lua`: 851, 875;
  - `PS_Stash.lua`: 1137.
- **Stay With Me** (3800989007): `BridgeDoors.lua` 261-346; `BridgeMove.lua` 3740, 3842-3880, 5149-5175.
- **Living Fellows: Companion** (3805760339): Sol's own movement layer.
- **Siles Player Carry B42** (3834177369): a trivial follow only.
- No Bandits, Superb Survivors or Knox Event mod is installed.

**Web**
- The search backend failed. `github.com/slayer5934/Bandits` returned 404 and `pzwiki.net/wiki/Pathfinding` returned 403. No web source was used.

## 11. Far car arrival INSIDE the loaded area: the Java part (owner's decision 2026-11-10: he stays where he is)

He stays where he is. She and the car appear on a clear road spot inside the loaded ring around him, just out of his view, and she drives to him. Everything is staged: `apply_s72_far_arrival.py` (upgraded in place; it also upgrades the copy installed at 20:14) and `build_far_arrive.py`. Nothing is installed. Switch `far_car` stays OFF until the in-game test passes.

### 11.1 How the game itself brings a vehicle row into the world (javap 42.22.2; line numbers from LineNumberTable)
- **[C] The table.** `VehiclesDB2$SQLStore` uses `vehicles(id PRIMARY KEY, wx, wy, x, y, inMeta, worldversion, data BLOB)` and opens it with `PRAGMA JOURNAL_MODE=TRUNCATE`.
  - Chunk read: `SELECT id, x, y, data, worldversion, inMeta FROM vehicles WHERE wx=? AND wy=?`.
  - Save: `UPDATE vehicles SET wx, wy, x, y, worldversion, inMeta, data WHERE id=?`.
  - Delete: `DELETE FROM vehicles WHERE id=?`. These are the SQLStore string constants.
- **[C] Row to object, on the world streamer thread.** `VehiclesDB2$WorldStreamerThread.vehicleLoaded` (`VehiclesDB2.java:675-695`):
  1. `square = chunk.getGridSquare(x - wx*8, y - wy*8, 0)`;
  2. `new BaseVehicle(IsoWorld.currentCell)`;
  3. `setSquare(square)`, `setCurrent(square)`;
  4. `load(bb, worldVersion)`. If this throws, the game logs "vehicle %d is being deleted because an error occurred loading it" and runs `store.removeVehicle(id)`;
  5. `sqlId = id`, `chunk = chunk`, `softReset` (for some job types), `chunk.vehicles.add(v)`.
- **[C] Object into the world, on the main thread.** `IsoChunk.doLoadGridsquare` (`IsoChunk.java:3935-3960`), for each chunk vehicle:
  - if it is not added yet but `VehiclesDB2.isVehicleLoaded` is true, it is a duplicate: `removeFromSquare` and it is dropped;
  - otherwise `addToWorld()`;
  - if `sqlId == -1`, `VehiclesDB2.addVehicle` (a new vehicle gets a row).
- **[C] What `addToWorld` does.** `BaseVehicle.addToWorld()` calls `VehiclesDB2.setVehicleLoaded(this)` (into `MainThread.loadedIds`), `IsoMovingObject.addToWorld`, `createPhysics`, `VirtualVehicleManager.removeFromMeta`, `VehicleParts.addToWorld` and `PathfindNative.addVehicle`.
- **[C] Vehicles kept "in meta".** `VehiclesDB2$QueueLoadVehiclesInMeta` (`VehiclesDB2.java:1015-1043`) loads with a dummy square, then on the main thread runs `addToWorld()`, `removeFromWorld()` and `VirtualVehicleManager.addToMeta`. These vehicles live outside chunks.
- **[C] Ids.** `VehiclesDB2$MainThread` has `usedIds`, `loadedIds` and `seenChunks`; `allocateID` gives new ids. Single player keeps the same `sqlId` for a vehicle's life, so one row means one vehicle.
- **[C] Access.** Everything used is public:
  - `BaseVehicle(IsoCell)`, `setSquare`, `setCurrent`, `addToWorld()`, public fields `sqlId` and `chunk`;
  - `IsoObject.load(ByteBuffer, int)` (public final);
  - `IsoChunk.vehicles` (public final);
  - `IsoCell.getChunk(int, int)`, `getGridSquare(int, int, int)`, `getVehicles()`.
  - `VehiclesDB2.main.loadedIds` and the store's `conn` are read by reflection, as `SolCarMove` already does.

### 11.2 The build: the game's own sequence, in three steps
1. **Lua (main thread), `solCarArriveRequest(id, x, y)`.** It is refused when the car is already loaded (`loadedIds`) or the spot's chunk is not loaded. SolFar picks the square live (`F.insideSpot`, at most 24 tiles from the Mind's spot). The square must be:
   - loaded;
   - out of his view (the same `offScreen` as the walk-in);
   - outdoors;
   - on a street floor (sprite name with "street" or "road"); a helicopter needs open ground with nothing within 2 tiles instead;
   - free;
   - with no zombie within 12 tiles and no vehicle within 6.
2. **World streamer thread** (the thread that owns the table; `SolCarMove.onStreamer` → `SolCarArrive.onStreamer`). `SolCarArriveCore.stage` does all of this in one SQLite transaction:
   - the same checks as `SolCarMoveCore`: in meta, blob versus columns, any other row within 8 tiles;
   - `UPDATE` of x, y, wx, wy and the blob's x/y floats, same id;
   - it hands back the patched blob and its `worldversion`.
3. **Main thread, `solCarArriveMain()`.** Lua calls it each tick while the state is staged. It runs the steps of 11.1 (`new BaseVehicle` … `chunk.vehicles.add`, `addToWorld`). In the **same Lua tick**, SolFar's `F.arrive`:
   - turns the car along the road (`setAngles` + `getForwardVector`);
   - brings her body back at the driver's door (`Actor.recover`);
   - puts her at the wheel (`SC.Driving.takeWheel`).
   - A saved record is moved beside the car (`pendingRelocate`) and the restore brings her in.
4. **Then** "صرت قريبة، عضّة كوساية وبوصل." and `fetch_player` drives to him, re-targeting every 12 tiles he moves. Fuel is taken once (`settleFuel`).
- **Mind:** `car_where` ends with `,in` when the Java side is there. `pickup_spot_dir(..., inner=True)` then picks a straight street stretch 4 to (ring−1) chunks from him. For his trip that is (7232.5, 8154.5), heading west, 317 road tiles from the car. The option ends with `,in`.

### 11.3 No loss, no duplicate, even on a crash
- **Crash before the commit:** the row is unchanged; SQLite rolls the transaction back.
- **Crash after the commit, before step 3:** the row is at the spot. On the next load that chunk's own load (11.1) brings it in. There is still exactly one row.
- **He moves and the chunk unloads between 2 and 3:** step 3 answers `deferred` and writes nothing. The chunk's own load brings it when he comes back (tested). SolFar keeps `placed`, so she still gets in then.
- **The game loads it by itself first** (`loadedIds` contains it): step 3 does nothing (`loaded`). `IsoChunk.doLoadGridsquare` would also drop a second copy.
- **`load` throws:** `load_failed`. The row stays where it is; we never delete it, although the game itself would.
- **What is not covered:** a crash *inside* `addToWorld` after `chunk.vehicles.add`. The row is at the spot either way, so the next load is clean.
- Her own body: if the game quits between the car move and her getting in, the car is at the spot and she is where she was. Nothing is lost; the next far call starts from there.

### 11.4 Found in his save
- **[C]** In `vehicles.db` (copy), his **Bradley** (row 6, `Base.RKCBradleyM3`) and one SmallCar (row 9) are `inMeta = 1`. These are kept by `VirtualVehicleManager`, not in a chunk.
- The row-based arrival refuses them (`in_meta`), and she walks instead (tested).
- Bringing a meta vehicle in: built in §12 (far_meta), through the game's own chunk-load merge rather than `QueueLoadVehiclesInMeta`.

### 11.5 Tests and gates
- **`SolCarArriveCoreTest`** (Java, against copies of his `vehicles.db`, a fresh copy per case): 15/15.
  - His car 5: one row, same count, columns and blob x/y only, the bytes handed over equal the table's, the `worldversion`.
  - Crash before commit: unchanged, bytes and all. Crash after commit: at the spot, one copy.
  - `spot_taken`, `in_meta` (the Bradley), `not_in_db`: the table is unchanged.
  - Every row of the save: 33 staged, the 2 meta ones refused, 35 rows throughout.
  - Kinds staged: SmallCar, SmallCar02, CarNormal, CarTaxi2, StationWagon(2), StepVan, Van_Transit, VanSeats(Burnt), PickUpTruck, PickUpVan(+Lumber), SmallCar02Burnt.
- **`SolCarMoveCoreTest`:** still all pass.
- **`build_far_arrive.py`:**
  - javac into a copy of `SolCombined.jar`;
  - link gate `LINKCHECK OK refs=11905 mismatches=0`;
  - patch-access gate `PATCH ACCESS OK patches=88 problems=0`;
  - staged jar sha256 starting `20e77cfea191a7a2`.
  - **ZombieBuddy will ask to approve the changed jar on the next start.**
- **`test_far_arrival.py` 77/77**, adding the inside cases:
  - his trip: a spot 4 chunks out; one request, a street square, out of view; arrived, and at the door and the wheel in the same tick; facing along the road; fuel once; he never moved;
  - a zombie on the spot: a square 12+ tiles away;
  - a car on the spot: 6+ tiles away;
  - him moving during the spawn: `deferred`, then she gets in when he comes back;
  - `in_meta`: she walks;
  - no clear street square: after 20 s she walks;
  - a helicopter: `,heli,in`, 60 s, open ground, at the controls;
  - the Mind: `,in` gives the inside spot, no `,in` gives the outside spot as before;
  - the upgrade from the first s72 (installed 20:14) applies, and twice changes nothing.
- **Other checks:** the game's own Kahlua compiler on the upgraded lab copies: 1398 files, 0 errors. `test_spatial_access.py` 61/61. `test_sort.py` 64/64.
- **Not testable offline:**
  - `BaseVehicle.load`/`addToWorld` on a live cell (the game's world is needed);
  - `setAngles` on a live car;
  - `takeWheel` on a car that appeared the same tick.
  - These are the first things to look at in the game: `[SolCarArrive] 5 -> staged`, then `-> arrived at …`, then `[SolFar] her car is here`, `she is at the wheel`, and `fuel for the trip taken` once.

### 11.6 Sources added (beyond §10)
- `zombie.vehicles.VehiclesDB2`:
  - `$WorldStreamerThread.vehicleLoaded` (675-695);
  - `$QueueLoadVehiclesInMeta.processMain` / `vehicleLoaded` (1015-1043);
  - `$SQLStore` SQL constants and the TRUNCATE journal;
  - `$MainThread` (`loadedIds`, `usedIds`, `allocateID`, `setVehicleLoaded`);
  - `$VehicleBuffer.setBytes`.
- `zombie.iso.IsoChunk.doLoadGridsquare` (3935-3960); `IsoChunk.vehicles`.
- `zombie.vehicles.BaseVehicle`: constructor, `addToWorld` (→ `setVehicleLoaded`, `createPhysics`, `PathfindNative.addVehicle`, `VirtualVehicleManager.removeFromMeta`), `load(ByteBuffer, int, boolean)`, public `sqlId` and `chunk`.
- `zombie.iso.IsoObject.load(ByteBuffer, int)`.
- `zombie.iso.IsoCell.getChunk`, `getGridSquare`, `getVehicles`.
- Sol: `05_TOOLS/sol_nav_java/localplayerbody/SolCarMove.java` (streamer hook, `perform`) and `SolCarMoveCore.java` (blob x/y at 10/14, clearance 8).
- His `vehicles.db` (copy): 35 rows, `inMeta` rows 6 (Bradley) and 9.

## 12. Far arrival for a vehicle kept "in meta" (far_meta; staged 2026-11-10, nothing installed)

Owner's rule: every vehicle feature supports every KI5 vehicle, the Bradley (3.5 min) and the helicopter (1 min) included. His Bradley (row 6) and a SmallCar (row 9) were refused by §11 (`in_meta`) and she walked. Labels: **[C]** confirmed (javap of 42.22.2 or a test on a copy), **[I]** inference, **[G]** needs the in-game test.

### 12.1 What "in meta" is
- **[C]** It is not a KI5 storage. `BaseVehicle.shouldUpdateInMeta()` = `isAlarmActive() || isSirenActive() || isEngineRunning()`. When a chunk unloads, `IsoChunk.removeFromWorld` calls it for each vehicle and, if true, `VirtualVehicleManager.addToMeta(v)`: a `VirtualVehicle` keeps the `BaseVehicle` object alive (parts, sounds, alarm, engine) outside any chunk.
- **[C]** The row gets `inMeta = 1` from `VehiclesDB2$VehicleBuffer.set` (`inMeta = shouldUpdateInMeta()`); `wx`, `wy` are `floor(x / 8)`, `floor(y / 8)` of the vehicle's own x, y. The row still sits at its chunk.
- **[C]** `VirtualVehicleManager.update()` (main thread, `IngameState.UpdateStuff`) updates each kept vehicle; when `VirtualVehicle.shouldUpdateInMeta()` turns false (battery 0, engine off, alarm over) it calls `stopUpdatingInMeta`: `removeFromMeta` + `save()`, which queues `VehiclesDB2.updateVehicle` with the kept object's position and `inMeta = 0`. `VirtualVehicleManager.save()` (called from `GameWindow` at a game save) runs `VirtualVehicle.save()` for every kept one.
- **[C]** At game start `IngameState.enter` calls `VehiclesDB2.loadVehiclesInMeta` (`SELECT ... WHERE inMeta=TRUE`): each one is loaded on a dummy square, `addToWorld`, `removeFromWorld`, `addToMeta`; one already loaded is skipped (`isVehicleLoaded`).
- **[C]** The chunk query (`SELECT id, x, y, data, worldversion, inMeta FROM vehicles WHERE wx=? AND wy=?`) has no `inMeta` filter: when its chunk loads, the game loads a kept vehicle like any other, and `BaseVehicle.addToWorld()` calls `VirtualVehicleManager.removeFromMeta(this)` (single player): the kept copy hands over its parts (`adoptParts`), headlights, lightbar, siren, sounds and alarm, and is dropped. A kept vehicle is not in `loadedIds` (`removeFromWorld` calls `setVehicleUnloaded`).
- **[I]** So the Bradley was most likely left with its engine running (or its alarm on). **[C]** Any vehicle can be kept so: a car, the Bradley, a helicopter.
- **[C]** KI5/Workshop Lua, read only: `RKCBradley` (3834076794) only reads `isEngineRunning`; `UH-1BHelicopter` (3409723807) only spawns burnt wrecks; `AviationCore` (3783444342) keeps its flight state in the vehicle's own modData (`AirbornePersistence`, `Helicopter_SaveLoadZFix`), which travels inside the row's blob. None stores vehicles anywhere else.
- **[C]** In his `vehicles.db` (copy) rows 6 (`Base.RKCBradleyM3`) and 9 (`Base.SmallCar`) decode as fuel 64.0 / 58.5, engine 100, driver door unlocked, hotwired: their row verdict is `ok`. There is no helicopter in that save.

### 12.2 What was built
- **Jar, `SolCarsNearCore`:** a car kept in meta keeps the verdict `in_meta` and gets a 16th field, its row's own verdict (`verdictOfRow`). Every other line keeps its 15 fields.
- **Jar, `SolCarArriveCore`:** `stage(conn, id, x, y, allowMeta)`. A kept row is staged only when `allowMeta`; then exactly as any row (one transaction; x, y, wx, wy and the blob's x/y floats; the `inMeta` column left as the game wrote it); `Staged.inMeta` says it was kept. The old 4-argument `stage` still refuses it. `mainChoice(loaded, stagedInMeta, virtualNow, squareLoaded)` answers `loaded`, `meta_changed`, `deferred`, `meta_deferred` or `spawn`.
- **Jar, `SolCarArrive`:**
  1. `solCarArriveRequest` (main thread) notes whether the vehicle has a `VirtualVehicle` now (`VirtualVehicleManager.vehicles` read by reflection, on the main thread only; `getSqlId()`), and passes it to the streamer as `allowMeta`.
  2. The streamer stages; a kept row whose `VirtualVehicle` was not seen is refused (`in_meta`, nothing written).
  3. `solCarArriveMain` (main thread): `meta_changed` if the row was kept and its `VirtualVehicle` is gone now (the game stopped keeping it and queued its own save: nothing is created, that save decides where the one row ends); `meta_deferred` if he moved (she walks); otherwise the game's own sequence of §11. `addToWorld` takes the kept copy over (`removeFromMeta`); if it is still listed, Sol makes the same public call once. Then `VehiclesDB2.updateVehicle(v)` queues the game's own save of the live vehicle; the streamer runs its queue in order, so it lands after any save the kept copy queued: the one row ends at the spot with the live state.
- **Lua, `apply_s76_far_meta.py` (SolFar.lua):** `parseCars` reads the 16th field; `choose` and `carsAnswer` count a kept car with its row's verdict only when `solCarArriveRequest` exists, so such a car always comes inside, never by the outside move (which refuses it). Without the new jar or without SolCarArrive nothing changes: it is skipped and she comes on foot with the Mind's own line ("جاية مشي، بدي ..."). `meta_changed`, `meta_deferred` or `in_meta` at the arrival: she walks; the reason is in the log only.
- **Fix, `apply_s72_far_arrival.py`:** on the Mind installed at 20:14, `road_route.py` already had the first `pickup_spot_dir` (no `inner=`), so the upgraded `chat_service` would have called `inner=` on it (TypeError). It now appends the new one again when `inner=False` is missing; the later definitions win.
- No new switch: all of it is behind `far_car` (still OFF).

### 12.3 No loss, no duplicate
- **[C]** Crash before the commit: the row is where it was, flag and bytes (test). After it: one row at the spot, still `inMeta = 1`; the game's in-meta query and the chunk query both find it, and the game's own merge makes one vehicle (test on the copy; the merge itself from javap).
- **[C]** The kept copy's own save racing ours, either order (test with the game's UPDATE): after ours, back at its old place and nothing created (`meta_changed`); before ours, staged as a plain row and spawned from the table's bytes.
- **[I]** A game save between the commit and the main thread: the kept copy writes its old place; the spawn still takes it over (it is still listed) and the queued live save puts the row back at the spot. A crash in that window leaves the one row at its old place.
- **[I]** `meta_deferred`: the row is at the spot while the kept copy holds the old place; at its next save the row goes back. She walks, so nothing waits on it.

### 12.4 Tests and gates (offline)
- `SolCarArriveCoreTest` 40/40 (the 15 of §11 unchanged + 25 far_meta), `SolCarMoveCoreTest` 16/16, `SolCarsNearCoreTest` 60/60 (+2), all on copies of his `vehicles.db`.
- `build_far_arrive.py` (now also runs `SolCarsNearCoreTest`): `LINKCHECK OK refs=11922 mismatches=0`, `PATCH ACCESS OK patches=88 problems=0`.
- `test_far_meta.py` 32/32: installer on both lab bases, twice, Kahlua-like compile; tonumber_check: s76 adds no site to SolFar.lua; the s72 Mind upgrade fix; the Bradley kept in meta chosen, `,tracked,in`, 210 s, one request for row 6, arrived, at the wheel, never the outside move; without SolCarArrive, with the old jar, or locked: not chosen; `meta_changed`, `meta_deferred`, `in_meta`: she walks; a helicopter kept in meta `,heli,in`, 60 s, at the controls; her cars answer.
- `test_far_arrival.py` 77/77 unchanged. The game's Kahlua compiler on the patched SolFar.lua: 0 errors.

### 12.5 Needs the in-game test [G]
- `keptInMeta` sees the Bradley's `VirtualVehicle` (log `[SolCarArrive] 6 (kept in meta) -> staged`).
- `addToWorld` on a kept vehicle created from its row: the take-over (`taken over from the kept copy: yes`), engine sound and state, fuel after the take-over, then `settleFuel` once.
- The Bradley on a street square inside his ring; `tracked_mode` driving it to him after it arrived.
- A helicopter kept in meta (left with its rotor running), and AviationCore not lifting it after it appears on the ground.
- The fuel check uses the row's fuel; a kept vehicle with its engine running burns fuel between saves, so the live tank may be a little lower [I].
