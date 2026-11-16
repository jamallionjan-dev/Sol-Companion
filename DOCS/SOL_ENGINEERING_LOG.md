# Sol Engineering Log (append-only)

## 2026-10-20 — Build 42.21 locomotion diagnosis research

### Runtime baseline and scope
- Status: `[IN PROGRESS]`; diagnosis only, no movement logic patch.
- One Project Zomboid process remains active: PID 34984. `PZ_COUNT=1`.
- Test build: `build_opacitytargetfix_20261020_1055`; bridge SHA-256 `B5F6368984683A80BBCC5020CC9944E50647D37251818561E824EEA5F0651938`.
- Installed Build 42.21.0 `projectzomboid.jar` SHA-256: `E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`.
- Commands: `Get-CimInstance Win32_Process ...` (single java.exe); `Get-FileHash`; JDK 17 `javap -classpath <installed projectzomboid.jar> -c -p zombie.ai.states.PathFindState`; source review with `rg`/`Get-Content`; GitHub and official API review. No build/launch/test/production mutation in this research pass.

### Evidence and result
- `[VANILLA PROOF]` Exact Build 42.21 bytecode: `PathFindState.execute()` invokes `PathFindBehavior2.update()` one time, then consumes `BehaviorResult`. `Failed` writes path index -1 and clears `bPathfind` and `bMoving`. `Succeeded` has a separate branch that may clear path references, or when target chunk lookup is null sets `bPathfind=false` and `bMoving=true`. This makes `bPathfind=false` alone ambiguous; the false movement flag plus retained route is compatible with failure but does not prove it.
- `[VANILLA PROOF]` Official API surface lists behavior result, `shouldBeMoving`, `hasStartedMoving`, `isMovingUsingPathFind`, `isTurningToObstacle`, target/path length, path-next telemetry, and cancellation. Sources: https://projectzomboid.com/modding/zombie/pathfind/PathFindBehavior2.html and https://projectzomboid.com/modding/zombie/ai/states/PathFindState.html .
- `[LIVING FELLOWS EVIDENCE]` Clean local upstream checkout `00_RESEARCH_COMMUNITY/living-fellows`, HEAD `7ade8805422121c77d1cea9c6d96f8315ca74be3`, remote `https://github.com/thorelvin/living-fellows.git`. Its native IsoPlayer companion calls ordinary `pathToLocationF`, synchronizes locomotion rates, advances stock `PathFindState` only when not already current, and reconciles path ownership. Companion Lua reads path telemetry and uses the actor entry point rather than directly invoking behavior update. Reference: https://github.com/thorelvin/living-fellows/blob/main/bridge/src/main/java/survivorcompanion/bridge/SCNativeCompanion.java . This is a comparison pattern, not causal proof for Sol.
- `[COMMUNITY EVIDENCE]` PZNS public companion source mentions animation timing when scheduling route recalculation: https://github.com/Project-Zomboid-Community-Modding/PZNS/blob/main/PZNS_Framework/media/lua/client/07_npc_ai/PZNS_JobsCompanion.lua . A separate Indie Stone report notes stuck WalkTowardState with non-null path2 after an interrupted multiplayer action: https://theindiestone.com/forums/topic/89149-build-42-mp-character-specific-interaction-lag-caused-by-stuck-walktowardstate-after-bugged-eatfood-action/ . Both are non-matching scenarios and are clues only.
- `[SOL RUNTIME PROOF]` The latest short probe accepted and attached a 2-tile route and initially set movement flags. Within the sampled route, coordinates remained at `10829.5,10144.5,0.0`; movement and `bPathfind` later became false while `shouldBeMoving=true` and path remained attached. Execution counters froze. The route was cancelled natively. ModelManager active/model non-null and alpha/targetAlpha=1.0 were observed during the failure. Previous 8-tile proof used another build and the opposite X direction; not a controlled comparison.
- `[HYPOTHESIS]` First divergence lies after route attach, at/after one existing native state execution. A `Failed` result is plausible but unobserved; stale path/behavior, target occupancy/collision, direction, and animation movement rate are not excluded. Root cause remains unresolved.

### Instrumentation choice and next action
- Capture a bounded pre/post state snapshot around Sol's existing `PathFindState.execute()` call. It already wraps exactly one existing `PathFindBehavior2.update()` invocation. Do not call behavior update independently, do not reconstruct vanilla state logic, and do not log every frame.
- Snapshot fields: coordinates, current/previous FSM names, shell path-owner state, `bPathfind`/`bMoving`, behavior target/length/cancel/started/moving/turning/path-next state, animation movement rates, and existing update/execute counters. Only read fields/methods verified against the exact installed JAR; omit any unsafe/unavailable member and label it unavailable.
- Exact `BehaviorResult` cannot be read from the void `PathFindState.execute()` wrapper. Capturing it would require invasive engine-bytecode instrumentation or replacing vanilla result handling; neither is justified before this trace. Log the first observable transition and retain the enum as unresolved.
- Build/launch gate: existing PID 34984 means a second PZ runtime is forbidden. After any diagnostic build, verify `PZ_COUNT=0` before launch. Run T0–T5 once on a short straight clear target and compare first divergence with the historical 8-tile trace. Patch only if that evidence proves a specific cause; otherwise record unresolved.
- Production changes: none. Test source/build changes in this research pass: none. Errors: none.

## 2026-10-20 12:00 Europe/Berlin — compile-stub limitation

- Status: `[BLOCKED FOR THIS BUILD METHOD]`, not a runtime failure.
- First javac attempt used `compile-stubs` alone and failed with 13 unresolved API methods (`getX`, `getY`, `getZ`, `isMoving`, `getVariableBoolean`) because the minimal local `IsoGameCharacter` stub does not model these methods.
- No diagnostic JAR was created; no PZ process or loaded artifact was changed. Source remains the backed-up diagnostic-only edit. Next: compile against the exact installed Build 42.21 JAR, then inspect/hash the artifact. Do not expand stubs to conceal API mismatch.
- Second compile path against installed `projectzomboid.jar` failed before symbol checking because class-file major version 69 (Java 25) exceeds available javac 17's maximum 61. This is a toolchain mismatch, not a runtime or movement failure; no JAR was created. Next: add minimal read-only API declarations to compile-only stubs (not packaged), then build Sol classes only.
- Backed up and extended only the compile stub `compile-stubs/zombie/characters/IsoGameCharacter.java` with six signatures required for read-only path trace collection. These methods are inert in the stub and no stub classes are included in the runtime JAR. Next: rebuild into a separate diagnostics folder and inspect contents/hash.
- Diagnostic JAR compiled successfully with Java 17 against compile-only stubs: `08_RUNTIME_TEST/SolNativePrototype/build_pathdiagnostics_20261020_1200/SolNativeBridge.jar`; SHA-256 `70B1EC10D5AB55633A040F6FA72F37E31EF7533CC44512150BA38EB83750D0E5`. `jar --list` confirms package contains only `META-INF` and `sol/bridge` class files. `javap` confirms the generated shell still reflectively invokes `PathFindState.execute` and contains only before/after diagnostic accessors; no direct PFB update call. API audit confirms referenced public movement methods against exact installed JAR. PID query still shows exactly PID 34984 using the previous build, so the diagnostics artifact is not loaded and no second runtime started. Runtime ABI and T0–T5 verification pending; no regression test has yet been possible. Next: user closes/saves current runtime, recheck zero processes, create/use a separate launch args file, then run the trace once.

## 2026-10-20 12:04 Europe/Berlin — diagnostic launch and mailbox path correction

- Status: `[IN PROGRESS]`; one diagnostic runtime only, PID 12340; PZ_COUNT=1.
- Pre-launch process check returned `PZ_COUNT=0`. A separate args file `sol-shell-pathdiag.args` points to the diagnostic bridge. Launch used the installed Project Zomboid Java 25 runtime with the game folder as working directory; no production process/artifact was started.
- Current debug log `profile/Zomboid/Logs/2026-10-20_12-03_DebugLog.txt` reports `[SolNativeBridge] READY` at 12:03:58 and continues into live frames. Ordinary pre-existing game data/script warnings appear; no Sol bridge exception reported yet.
- T0 command was mistakenly written to `profile/Zomboid/SolRuntimeCommand.txt`, one folder above the actual mailbox `profile/Zomboid/Lua/SolRuntimeCommand.txt`. Log at 12:04:11 consumed the pre-existing command ID `diag_cancel_empty_probe_status_20261020_1149`; it did not consume the new T0 request. No movement command or world-state change was made by this misdirected write.
- Immediate correction: restore the mistakenly touched parent-level mailbox from its backup, write a read-only status request to the actual Lua mailbox, and accept only a matching T0 ID in the current run log. Runtime process remains PID 12340; no second launch.
- Correct mailbox read-only result: log consumed `diag_T0_20261020_1204` at 12:04:47/frame 4710 and returned `[SolTest][NATIVE_SHELL_MOVE] state=idle body=nil`; no Sol actor exists yet, so this is not the T0 actor snapshot. No movement or coordinate mutation. Next: native spawn one shell, then capture true T0 baseline.

## 2026-10-20 12:00 Europe/Berlin — bounded path execution instrumentation

- Status: `[IN PROGRESS]`; diagnostic source only; no cause fix.
- Modified test-only `08_RUNTIME_TEST/SolNativePrototype/src/sol/bridge/SolIsoPlayerShell.java` and `SolBridge.java` after the research report above was written. Backups: `SolIsoPlayerShell.java.before_pathdiagnostics_20261020.bak` and `SolBridge.java.before_pathdiagnostics_20261020.bak`.
- Instrumentation wraps the already-existing `PathFindState.execute()` invocation. It captures retained before/after state for attempts 1–10, every 30th attempt, and the first observable bPathfind true→false or X/Y change. Fields are limited to the evidence-selected boundary: position, movement owner/flags, FSM current/previous, path attachment, PFB start/movement/obstacle-turn/target/length/cancel/path-next values, and WalkSpeed/RunSpeed/IdleSpeed animation variables.
- Safety: does not call `PathFindBehavior2.update()` directly, does not call full `IsoPlayer.update()`, does not change movement logic/coordinates/direction/player index/LOS/NPC status, and does not touch production. It is not loaded in the active runtime.
- Exact `BehaviorResult` remains unresolved because the vanilla wrapper returns void. The trace observes consequences around its single call; it does not claim to recover the consumed enum.
- Runtime PID remains 34984 (`PZ_COUNT=1`), old build/hash unchanged. Diagnostic artifact has not yet been compiled. Next: compile a separate test artifact, hash/readback it, then require zero PZ processes before launch and capture T0–T5.

## 2026-10-20 12:05 Europe/Berlin — diagnostic shell spawn
- Status: `[COMPLETED]` for shell creation; movement diagnosis remains `[IN PROGRESS]`.
- Command: `diag_shell_spawn_20261020_1205|NATIVE_SHELL_SPAWN|` through the correct test mailbox `08_RUNTIME_TEST/profile/Zomboid/Lua/SolRuntimeCommand.txt`.
- Runtime proof: DebugLog frame 7870 accepted the request; at 12:05:07.251 `[SolNativeShell] READY` reported `worldMember=true`, `scheduled=true`, `state=ready`, class `sol.bridge.SolIsoPlayerShell`, `playerIndex=1`, `serverPlayerIndex=-1`, `remote=false`, `local=false`, `inLocalSlots=false`, `isGlobalInstance=false`, non-null square, `addedToModelManager=true`, `activeModel=true`, non-null model instance, `alpha0=1.0`, `targetAlpha0=1.0`.
- Process/artifact identity: only Project Zomboid Java PID 12340; diagnostic build `build_pathdiagnostics_20261020_1200`; bridge SHA-256 `70B1EC10D5AB55633A040F6A72F37E31EF7533CC44512150BA38EB83750D0E5`. Production untouched.
- No movement or coordinate change was issued as part of spawn. The earlier `body=nil` status was pre-spawn and is not actor T0.
- Errors: none during spawn. Regression after fix: not applicable; no behavior fix was made.
- Next: capture `NATIVE_SHELL_MOVE_STATUS` and `NATIVE_SHELL_VIS_STATUS` at T0 from this spawned actor, check coordinates/target safety and trace counters, then choose at most one short native route only if a clear target is supported by runtime evidence.

## 2026-10-20 12:06 Europe/Berlin — actor T0 baseline
- Status: `[COMPLETED]` for T0 capture; safe route selection remains `[IN PROGRESS]`.
- Command: `diag_T0_shell_20261020_1206|NATIVE_SHELL_MOVE_STATUS|`; consumed at 12:05:59.721, frame 16290.
- Runtime proof: shell `state=ready`, position `10837.5,10144.5,0.0`; `moving=false`, `playerMoving=false`, `bPathfind=false`, `shouldBeMoving=true`, `usingPath=false`, `started=false`, `pathAttached=false`, `progress=notrunning`, `cancelled=true`, target `0,0,0`, pathLength `14844.6045`, `updateCount=8420`, `pathExecAttempts/pathExecSuccesses/skipped=0/0/0`, trace before/after `not_sampled`. Thus this newly spawned shell starts with a stale-looking PFB telemetry snapshot (cancelled, origin target, huge path length) while no path is attached and no PFS execute has yet run; this is baseline observation, not root-cause proof.
- The bridge's auxiliary status file remains `body=false` with ownerPos `10835.468,10144.551,0.000`; its keys are from the older generic watcher and do not override the Java shell's direct status. PID 12340 remains the sole PZ process. Diagnostic build/hash unchanged: `build_pathdiagnostics_20261020_1200`, SHA-256 `70B1EC10D5AB55633A040F6FA72F37E31EF7533CC44512150BA38EB83750D0E5`.
- No movement request or coordinate write occurred for T0. Errors: none. Production untouched. Regression after fix: not applicable.
- Next: capture visibility/model state and inspect whether runtime offers a directly verifiable empty neighboring square before a short native movement request. No patch until divergence is observed.

## 2026-10-20 12:06 Europe/Berlin — visibility T0 and route candidate
- Status: `[COMPLETED]` for read-only visibility snapshot; route probe `[IN PROGRESS]`.
- Command `diag_T0_vis_20261020_1206|NATIVE_SHELL_VIS_STATUS|` consumed at 12:06:11.289/frame 18170. Runtime: `state=ready`, gameClient=false, gameServer=false, localIndex=0, shellIndex=1; localPos `10835.468,10144.551`, shellPos `10837.5,10144.5`, distance `2.03286`; both squares non-null; `isCanSee/isCouldSee/getCanSee/isVisibleToPlayer=false`; alpha/targetAlpha `1.0/1.0`. Visibility flags false remain consistent with previous reports and do not establish absence of rendering.
- Candidate short native destination: `10833.5,10144.5,0.0`, four tiles west along the same z/y corridor. This segment lies within the exact westward 8-tile corridor previously traversed successfully (`10837.5,10144.5` to `10829.5,10144.5`), and it moves away from the current local player's square. This is historical route evidence, not a fresh square-object scan; live occupancy remains a limitation. No teleports/manual position edits.
- Runtime identity remains PID 12340, one process, build `build_pathdiagnostics_20261020_1200`, bridge SHA-256 `70B1EC10D5AB55633A040F6A72F37E31EF7533CC44512150BA38EB83750D0E5`. No errors or source changes. Production untouched.
- Next: issue this single native route, sample immediately and after short intervals, and correlate the first path execution snapshots with actual coordinate change or flag transition. If the corridor behaves differently, stop native path and report evidence; no patch without cause.

## 2026-10-20 12:06 Europe/Berlin — T1 movement command blocked by Lua bridge loss
- Status: `[FAILED]` for this command attempt; locomotion diagnosis `[BLOCKED]` pending bridge recovery.
- Sequence: read-only T0 visibility completed at 12:06:11; before the native route was dispatched, the game reinitialized the world in the same Java process (log frame reset to 0 at 12:06:48, same PID 12340 and same command line/artifact). The T1 command `diag_move_T1_20261020_1206|NATIVE_SHELL_MOVE|10833.5,10144.5,0` was consumed at 12:06:51/frame 18, but Lua immediately raised `SolBridge global missing` from `SolRuntimeTest.lua:243`. No request ID, path, or route was created; this is not a locomotion failure.
- Runtime state after reinitialization: one PZ process, PID 12340; command channel READY; generic status `body=false`; the previous Java shell and bridge Lua global are not available in this Lua environment. The same process is still active. Diagnostic build/hash remain `build_pathdiagnostics_20261020_1200` / `70B1EC10D5AB55633A040F6A72F37E31EF7533CC44512150BA38EB83750D0E5`.
- `[STATIC CAUSE — harness lifecycle]` `SolBootstrap.start()` is guarded by static `started`; its worker loop condition is `!ready`; once the first exposure succeeds, `ready=true` permanently ends retries. A later Lua environment reset removes `SolBridge` from that environment, but this bootstrap does not expose it again. `SolExposure.exposeNow()` already checks the active Lua environment and can expose the class when absent, but current Lua command routing has no recovery command. The runtime exception and source control flow jointly explain why this attempt could not reach movement.
- Target route was not evaluated and its occupancy was not verified at runtime; do not treat the historical corridor rationale as a fresh live square scan. No position movement, teleport, or manual coordinate edit occurred. Production untouched; no patch/build made. No regression test applicable.
- Recovery constraint: current process count is 1. Do not launch a second process. The shell T0 snapshots are retained as evidence; movement result remains unresolved. Exact next step: after the current runtime is closed and a fresh process check shows `PZ_COUNT=0`, either relaunch the same diagnostic artifact and issue native route immediately after bridge/shell readiness, or make a narrowly scoped test-only bridge re-exposure fix after recording the source research gate. Do not advance to rotation or later phases until native movement produces a valid trace.

## 2026-10-20 12:14 Europe/Berlin — lifecycle research and T1 classification correction
- Status: `[COMPLETED]` for source/artifact lifecycle research; bridge-only fix `[IN PROGRESS]`.
- Historical classification correction: earlier entry labeled the T1 command attempt `[FAILED]`; that label describes the harness command error only. Locomotion T1 result is now `[INCONCLUSIVE]` because `SolBridge global missing after Lua environment reinitialization`; `requestTestShellMove` was never invoked and no movement request was created. Preserve the original record; this entry supersedes its locomotion interpretation.
- Runtime baseline remains PID 12340, one Project Zomboid process (`PZ_COUNT=1`), diagnostic build `build_pathdiagnostics_20261020_1200`, JAR SHA-256 `70B1EC10D5AB55633A040F6A72F37E31EF7533CC44512150BA38EB83750D0E5`. No second runtime or production change.
- Exact installed Build 42.21 artifact: `projectzomboid.jar` SHA-256 `E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`. Read-only bytecode from `zombie.Lua.LuaManager.init()` shows it wipes the old `env`, assigns `platform.newEnvironment()` to the static `LuaManager.env`, then constructs/replaces `LuaManager.Exposer` bound to that new environment. `GameWindow.init()` calls `LuaManager.init()`. Method bodies were inspected with JDK17 `javap` on extracted copies whose class-file major header alone was lowered for disassembly; original installed JAR was not modified. Research output is under `08_RUNTIME_TEST/SolNativePrototype/research_luamanager_20261020/`.
- Current bridge code retains permanent static `ready/started`; worker exits its retry loop when `ready` first becomes true. It holds no Lua env reference. `SolExposure.exposeNow()` currently reads current `LuaManager.env` only on exposure attempts. Exposer bytecode confirms `exposeLikeJava` checks whether a class already has exposed metadata; the current exposure method is already guarded by `rawget(env,"SolBridge")`, but there is no subsequent call after success. `SolBridge` binding registers no Lua events/schedulers; the bootstrap uses one daemon worker and an atomic queued guard.
- Community corroboration: the Project Zomboid modding guide describes the embedded Kahlua Java runtime and save-scoped Lua load/unload behavior; community-maintained vanilla Lua source uses explicit reload hooks for scripts. These are corroboration only; the installed 42.21 bytecode is the version-specific lifecycle evidence. Sources: https://github.com/drandarov-io/project-zomboid-mod-toolkit/blob/master/MODDING.md and https://github.com/Project-Zomboid-Community-Modding/ProjectZomboid-Vanilla-Lua . Official API documents public `LuaManager.env` and `LuaManager.init()`: https://projectzomboid.com/modding/zombie/Lua/LuaManager.html .
- Proposed minimal fix: keep exactly one daemon monitor, queue a main-thread check every 500 ms (not per frame), compare `LuaManager.env` by reference using a weak reference to avoid retaining an entire retired Lua environment, and check only the current env's `SolBridge` global. Re-expose only on a new env or missing binding; restore a missing same-env global from a weakly held cached class table if still present. Track/log old/new identity hashes, global presence, exposure count, and restoration count. Do not touch shell, locomotion, movement values, player index, NPC, LOS, or opacity.
- Build gate: build to a new isolated test directory first and verify only bridge class files are packaged (no compile stubs), then SHA-256. Only after successful build may PID 12340 be stopped; then require `PZ_COUNT=0` before one diagnostic relaunch. Runtime lifecycle proof and duplicate side-effect checks are pending.
- Next: implement only `SolBootstrap.java` and `SolExposure.java`, compile/readback/hash; then stop current runtime after successful build and validate environment re-exposure in one process before resuming T1.

## 2026-10-20 12:16 Europe/Berlin — bridge lifecycle-only implementation
- Status: `[IN PROGRESS]`; source change complete, clean compile/artifact validation pending.
- Modified only test bridge lifecycle files: `08_RUNTIME_TEST/SolNativePrototype/src/sol/bridge/SolBootstrap.java` and `SolExposure.java`. No change to `SolBridge`, `SolIsoPlayerShell`, locomotion, `PathFindBehavior2`, movement rates, playerIndex, `setNpc`, LOS, opacity, or production.
- Bootstrap now owns one daemon monitor guarded by the existing static `started` flag and one `AtomicBoolean` queued guard. It posts at most one MainThread check every 500 ms (no frame/event registration) and continues after first readiness so later Lua environments are detected. Queue failures clear the guard; thread interruption exits.
- `SolExposure.exposeNow()` is synchronized and main-thread-only. It reads the current LuaManager env and the `SolBridge` global; records environment transitions by reference through `WeakReference` (does not retain retired envs); records identity hashes/counts; returns immediately if the binding already exists. A missing same-env global is restored from the cached exposed class table, and a new environment gets a single normal class exposure. The Exposer is not replaced and no hooks, schedulers, or shell instances are created by this binding logic.
- Verification to perform: compile into a newly named empty build directory, inspect JAR entries to ensure no `compile-stubs` classes are packaged, inspect bytecode for the 500 ms monitor and idempotency guards, compute SHA-256. Only after build success may PID 12340 be stopped; then require zero Project Zomboid processes before the single test launch.
- Runtime lifecycle behavior, re-exposure counts, command channel recovery, duplicate shell/scheduler/hook absence, and movement T1 remain pending. No regression claim yet.

## 2026-10-20 12:18 Europe/Berlin — lifecycle build artifact validated
- Status: `[COMPLETED]` for clean compilation and artifact inspection; runtime lifecycle validation `[IN PROGRESS]`.
- Build: Java 17 `javac`, using the prior compile-only API stub class directory as classpath; no stubs were supplied as runtime output. Fresh output `08_RUNTIME_TEST/SolNativePrototype/build_bridgelifecycle_20261020_1218/`; JAR `SolNativeBridge.jar`; SHA-256 `8E9FA2DA1D27290DB73245C9A011CA8D328F47F98925D966F08CFB8F40A26F7B`.
- JAR readback contains only `META-INF` and `sol/bridge/{SolBootstrap,SolBridge,SolExposure,SolIsoPlayerShell,SolLauncher}.class`; no `zombie/` API stubs or test stub classes are packaged. `javap` confirms 500 ms monitor interval, one `AtomicBoolean` queued guard, a single `started` guard, environment/global check before exposure, cached-global restore branch, and synchronized expose/status methods. No extra scheduler/event hook was introduced.
- Active runtime at artifact validation: PID 12340, `PZ_COUNT=1`, still on the previous `build_pathdiagnostics_20261020_1200` artifact. It has not yet been stopped. Production remains untouched.
- Errors: none in compilation/package inspection. Regression: pending runtime test. Exact next step: back up the test args file and point the next single-runtime launch at this new JAR; then stop only PID 12340, confirm `PZ_COUNT=0`, and launch one test runtime.

## 2026-10-20 12:19 Europe/Berlin — previous diagnostic runtime closed after build
- Status: `[COMPLETED]` for lifecycle gate preparation.
- After the new JAR passed compile and entry/hash inspection, the test args file was backed up as `sol-shell-pathdiag.args.before_bridgelifecycle_20261020_1218.bak` and updated to reference only `build_bridgelifecycle_20261020_1218/SolNativeBridge.jar`. Args-file SHA-256: `397F36F55BDA16947E1D282735CE7154` (prefix captured; recompute full value if needed).
- Pre-stop check: exactly one Project Zomboid Java process, PID 12340, command line used the prior test args file. `CloseMainWindow()` returned true; process exited without force termination. Post-stop check: `PZ_COUNT=0`.
- No production process or production artifact was touched. Runtime state/save was closed normally. Next: recheck zero count and launch exactly one test process using the bridge lifecycle artifact.

## 2026-10-20 12:17 Europe/Berlin — first environment exposure proof
- Status: `[COMPLETED]` for first-env exposure; Lua reset/re-exposure pending.
- Runtime PID 15348, `PZ_COUNT=1`, using test bridge JAR `build_bridgelifecycle_20261020_1218/SolNativeBridge.jar` (SHA-256 `8E9FA2DA1D27290DB73245C9A011CA8D328F47F98925D966F08CFB8F40A26F7B`).
- Log at 12:16:52.241 records `[SolNativeBridge] ENVIRONMENT oldId=0 newId=1748864000 bridgePresent=false`; 5 ms later `EXPOSED envId=1748864000 previousEnvId=0 exposureCount=1 restoreCount=0 bridgePresent=true`; 2 ms later `READY envId=1748864000 exposures=1 restores=0 bridgePresent=true`.
- Runtime command channel registered at 12:16:51.874/12:17:05.144; it is active in the first world Lua environment. No shell has been created and no locomotion command issued. No duplicate bootstrap, hooks, scheduler, or shell observed; this binding-only test has not registered any of those.
- Next: issue a read-only native bridge ping before world transition, then observe whether the same JVM gets a new Lua environment and whether exposureCount increments exactly once while command channel recovers.

## 2026-10-20 12:18 Europe/Berlin — pre-reset bridge ping
- Status: `[COMPLETED]` for active binding check; lifecycle reset pending.
- Command `lifecycle_ping_before_reset_20261020_1217|NATIVE_BRIDGE_PING|` consumed at 12:17:56.653/frame 6964. Runtime returned `ping=SOL_NATIVE_PONG status=envId=1748864000 exposures=1 restores=0 bridgePresent=true`; auxiliary status `tag=OK:NATIVE_BRIDGE_PING`, local player ownerPos `10835.500,10144.500,0.000`. PID 15348 remains the sole PZ runtime; lifecycle JAR SHA unchanged.
- No movement request. Next: create exactly one shell fixture before the observed world transition so post-reset diagnostics can verify the existing Java-side shell is retained and reject duplicate spawn.

## 2026-10-20 12:18 Europe/Berlin — single shell fixture before reset
- Status: `[COMPLETED]` for initial fixture; post-reset retention and duplicate check pending.
- Command `lifecycle_shell_spawn_once_20261020_1218|NATIVE_SHELL_SPAWN|` consumed at 12:18:21.604/frame 10924; request ID 1. At 12:18:21.666 the bridge logged one `[SolNativeShell] READY` with `worldMember=true`, `scheduled=true`, state ready, one `SolIsoPlayerShell`, off-local-slot (`inLocalSlots=false`), singleton unchanged (`isGlobalInstance=false`), current square non-null, ModelManager added/active, model instance non-null, alpha0/targetAlpha0 `1.0/1.0`.
- This is the only shell created in PID 15348. No route or coordinate change. First Lua env remains `envId=1748864000`, exposureCount=1, restoreCount=0. Next: capture Java-side shell status, observe world/Lua transition, then ping/status without another spawn command.

## 2026-10-20 12:18 Europe/Berlin — pre-transition shell status
- Status: `[COMPLETED]` for pre-reset shell status; environment transition not observed yet.
- Command `lifecycle_pre_reset_shell_status_20261020_1218|NATIVE_SHELL_STATUS|` consumed at 12:18:35.527/frame 13124. Java bridge returned `state=ready`, empty failure, `SolIsoPlayerShell`, playerIndex 1, serverPlayerIndex -1, remote/local false, `inLocalSlots=false`, `isGlobalInstance=false`, non-null current square, ModelManager added/active, model non-null, alpha0/targetAlpha0 `1.0/1.0`. This identifies the one existing shell before any environment reset.
- Since initial exposure, runtime logs still show only env `1748864000`, `exposureCount=1`, `restoreCount=0`; no `ENVIRONMENT` transition or `GLOBAL_MISSING` was observed by the 12:18:55 sample. PID 15348 remains the only runtime; shell has not moved. Next: determine whether the current vanilla/test scenario will naturally reload the Lua environment; do not invoke a destructive LuaManager reset merely to manufacture a pass.

## 2026-10-20 12:21:42 +02:00 — bridge lifecycle reset not reproduced in active world
- Status: [BLOCKED] — lifecycle re-exposure cannot be declared passed; locomotion remains intentionally untested after this build.
- Verified active test process: PID 15348, PZ_COUNT=1; test build build_bridgelifecycle_20261020_1218; bridge JAR SHA-256 8E9FA2DA1D27290DB73245C9A011CA8D328F47F98925D966F08CFB8F40A26F7B. Production was not touched.
- Runtime evidence through the latest sample: only initial ENVIRONMENT oldId=0 newId=1748864000, EXPOSED envId=1748864000 exposureCount=1 restoreCount=0 bridgePresent=true, and READY at 12:16:52.241–12:16:52.248. Pre-transition ping at 12:17:56.653 returned SOL_NATIVE_PONG, envId=1748864000 exposures=1 restores=0 bridgePresent=true. One shell was created and described ready at 12:18:21–12:18:35; model and square were present, alpha and targetAlpha were 1.0, no route was issued.
- At the subsequent log inspection, no new environment identity, missing-global event, re-exposure, or command-channel recovery after an environment reset was present. The world remained active in the same JVM. The visible Survival Guide overlay prevented reliably navigating the game back to the menu using UI input; no internal LuaManager reset was invoked. This is an uncompleted lifecycle stimulus, not evidence the patch failed.
- The previous locomotion T1 stays [INCONCLUSIVE]: SolBridge global missing prevented requestTestShellMove from running, so no locomotion request or movement was created. Do not classify that as locomotion [FAILED].
- No source/build changes were made in this continuation. No movement request, manual coordinate change, teleport, second runtime, duplicate shell, or production change occurred. The only shell remains the pre-transition fixture in PID 15348.
- Errors: none attributable to the bridge in the current log. The main blocker is that a real same-JVM Lua environment reinitialization was not triggered; consequently re-exposure and post-reset command-channel behavior remain unproven.
- Regression check: not applicable; no patch was made. Runtime remains at one process.
- Next step: use the game’s normal UI to return to the main menu and reload the test world in the same PID 15348, then verify new env identity, exposureCount=2, bridgePresent=true, one functioning ping/status, and no duplicate shell/scheduler/hooks. If the process exits, re-check PZ_COUNT and keep it at zero before any fresh launch. Only after lifecycle evidence passes, resume locomotion T1 with a nearby empty tile.
## 2026-10-20 — Reference Lab initialized and source pinned
- Status: [REFERENCE RESEARCH IN PROGRESS].
- Created separate SOL_REFERENCE_LAB directories: LivingFellows, Research, Reports, Evidence. Cloned canonical thorelvin/living-fellows; original repo checkout remains clean at branch living_fellows/0.26.51, commit f0eaa49802b5b1c767adf175a57a7ad41fa676c4 (2026-10-20T08:13:17+02:00), VERSION.txt 0.26.51, no tag at HEAD. README and CONTRIBUTING identify Build 42.21.0, single-player only. LICENSE is MIT.
- Completed initial static overview at SOL_REFERENCE_LAB/Reports/00_LIVING_FELLOWS_OVERVIEW.md. No Sol source, 08_RUNTIME_TEST, production mod, or game state was changed. No Living Fellows runtime/build/test was started.
- REA 6.5.0 binary_session was queried. It reported no active target; Ghidra is not configured, Hopper is unsupported on Windows, and managed analysis covers PE/CLI rather than Java. No suitable REA Java/Lua source graph is exposed. Capability record: SOL_REFERENCE_LAB/Evidence/REA_CAPABILITIES_20261020.md. This provider limitation is not source evidence; continue source and test tracing and keep runtime claims unresolved.
- Static architecture pointers: ARCHITECTURE.md:5-15 (runtime/scheduler), :11-38 (action/actor ownership), :271-289 (native provider hard gate); README.md:383-419 (declared test/build approach); tests/core/faction_lifecycle_harness.lua:72-122 (lifecycle idempotence assertions).
- Next: complete report 01 (native actor lifecycle) from exact Java source and focused test harnesses, then append its result here and in the Engineering Log. No recommendation is implemented automatically.

## 2026-10-20 — Reference Stage A: Native Actor Lifecycle
- Status: [REFERENCE RESEARCH COMPLETED].
- Source-traced pinned SCNativeCompanion extends IsoPlayer, constructor non-local setup (setNpc(true), reserved index 3, server index -1), brief contextual local callback scopes, asynchronous spawn handoff, world/square vs cell scheduler vs ModelManager membership, custom per-frame update isolation, same-actor recovery, and transactional removal/retry.
- Key source pointers: bridge/src/main/java/survivorcompanion/bridge/SCNativeCompanion.java:52,261-282,395+,615-640,2328-2459; SCBridge.java:1760-1790,1823-1907,1986-2168,2192-2342,2515-2540,2624-2648; SCActor.lua:357-384,1192-1238,1612+; tests/core/test_core_static.py:521-541; SCNativeCleanupTransactionTest.java:232-420.
- Evidence is static source and inspected test assertions only; tests and runtime probes were not run. No Sol code, build, runtime, 08_RUNTIME_TEST, or production files were changed.
- Key finding: the native actor requires distinct, verified ownership for square/world, cell update list, renderer, and bridge registry. addToWorld alone is not enough to keep a stationary manually created actor simulated.
- Next: Stage B, trace Java exposure/bootstrap and Lua reset/main-menu lifecycle, including duplicate-hook prevention and exact test coverage. Keep the Sol bridge files read-only.

## 2026-10-20 — Reference Stage B: Bridge Exposure and Reset Lifecycle
- Status: [REFERENCE RESEARCH COMPLETED — STATIC SOURCE ONLY]. Report: `SOL_REFERENCE_LAB/Reports/02_BRIDGE_LIFECYCLE.md`.
- Traced Java bootstrap generations/main-thread exposure, stable environment identity and sentinels, periodic revalidation, Lua transactional hook installation/removal, and runtime reset/main-menu ownership. The healthy poll can recover exposure after an environment replacement; a bootstrap exception cancels the run and needs an external restart caller.
- Exact coverage review found no executed runtime reload evidence. The main test-suite source selects exposure and bootstrap tests, while `SCBridgeLoadTest` itself still expects protocol/version 42.20.4 and IsoSurvivor; production and Lua namespace are at protocol 42.21-isocompanion-24. This is confirmed source/test drift, not an observed runner failure.
- Sol comparison was read-only: prototype already tracks environment identity with a weak reference and successful exposure count at 500 ms cadence. No Sol change was made. No tests/build/runtime/production/08_RUNTIME_TEST action occurred.
- Next: Stage C scheduler and tick ownership static trace.

## 2026-10-20 — Reference Stage C: Scheduler and Tick Ownership
- Status: [REFERENCE RESEARCH COMPLETED — STATIC SOURCE ONLY]. Report: `SOL_REFERENCE_LAB/Reports/03_SCHEDULER_OWNERSHIP.md`.
- Traced three separate mechanisms: engine cell object-list membership for native actor update, one Lua OnTick hook, and the Lua decision/task scheduler. Reference repair pulse is roster-change-aware and configured at 250 ms; spawn/recovery also require scheduler membership directly.
- Static tests assert repair/idempotence/removal and central tick ownership. No tests or live engine probes were run, so actual idle/cell-transition frame execution is unresolved.
- Sol relevance: record native object-list membership and update counter deltas alongside square/model/tick state; do not equate bridge route progress with native update execution. No Sol files or runtime were touched.
- Next: Stage D perception and rendering ownership.

## 2026-10-20 — Reference Stage D: Perception and Render Visibility
- Status: [REFERENCE RESEARCH COMPLETED — STATIC SOURCE ONLY]. Report: `SOL_REFERENCE_LAB/Reports/04_PERCEPTION_RENDER_VISIBILITY.md`.
- Traced separate membership and visibility gates: square/world and scheduler, ModelManager registration, active model, scene culling, alpha, and special-case LOS. Reference spawn checks renderer membership plus an active model; generic update forces alpha/targetAlpha to one. LOS is not used as ordinary detached-actor visibility.
- Static assertions cover renderer registration and teardown but cannot establish complete body/clothes/animation appearance. No screenshot/runtime observation was taken.
- No Sol source/build/runtime, `08_RUNTIME_TEST`, or production change. Next: lifecycle transactions, recovery and cleanup.

## 2026-10-20 — Reference Stage E: Lifecycle, Recovery, and Cleanup
- Status: [REFERENCE RESEARCH COMPLETED — STATIC SOURCE ONLY]. Report: `SOL_REFERENCE_LAB/Reports/05_LIFECYCLE_RECOVERY_CLEANUP.md`.
- Traced async spawn and Lua request ledgers, native ownership checks, same-actor recovery with exact rollback, and multi-membership cleanup with retained retry ownership after partial failure.
- Transaction tests inspected include injected cleanup faults and recovery rollback, but no tests were run and headless renderer fixtures cannot prove visual quality.
- Sol next-step implication: inspect path/state re-arm and current ownership snapshot before retrying movement; do not equate path discovery with physical movement. No Sol/runtime changes. Next: native pathfinding and locomotion contracts.

## 2026-10-20 — Reference Stage D: Perception System (numbering correction)
- Status: [REFERENCE RESEARCH COMPLETED — SOURCE TRACE]. Required report: `SOL_REFERENCE_LAB/Reports/04_PERCEPTION_SYSTEM.md`.
- The earlier D/E entries in this log documented render and lifecycle supporting evidence; they did not satisfy the task's requested perception/threat phase numbering. Their source findings remain in place; this entry corrects phase mapping without deleting history.
- Source-traced native shared zombie roster snapshot/cursor, bounded grid fallback, per-actor floor/distance/CanSee checks, separate uncertain sound contacts and last-known memory, freshness/completeness gates, and bounded 500 ms broad plus 100 ms near-field perception defaults. Added pipeline diagram and Sol snapshot/event recommendation.
- Test assertions were inspected, not run; no live runtime accuracy/performance evidence and no Sol changes.
- Next: Stage E threat assessment and deterministic reflex boundaries.

## 2026-10-20 — Reference Stage E: Threat and Reflex
- Status: [REFERENCE RESEARCH COMPLETED — SOURCE TRACE]. Required report: `SOL_REFERENCE_LAB/Reports/05_THREAT_AND_REFLEX.md`.
- Distinguished raw observation from derived urgency and combat target ranking. Living Fellows uses deterministic decision policy and has no external AI bridge; Sol design guidance is labeled inference, keeping immediate safety/reflex local and strategic choices with the model.
- Inspected source scores for distance, attack state, visibility, barriers, breach/rescue, flank/rear, player/allies, and combat readiness inputs (condition/endurance/panic/pain/fatigue/load/skills/weapon/support/escape). Test definitions only; no tests/runtime run.
- No Sol changes. Next: Stage F action ownership/preemption.

## 2026-10-20 — Reference Stage F: Action Supervisor
- Status: [REFERENCE RESEARCH COMPLETED — SOURCE TRACE]. Required report: `SOL_REFERENCE_LAB/Reports/06_ACTION_SUPERVISOR.md`.
- Reviewed actor-wide action tokens, priority/phase graph, preemption, native action guard, resource reservations, verified rollback, retry and quarantined release. Inspected harness coverage for urgency and exactly-once commit; did not execute it.
- Compared only with current `08_RUNTIME_TEST/SolNativePrototype/src`: no common action supervisor is present in that inspected prototype; bridge/path state and cancellation exist. Sol recommendation stays proposed until movement lifecycle is proven.
- No code, test, build or runtime changes. Next: Stage G locomotion.

## 2026-10-20 — Reference Stage G: Locomotion Pipeline
- Status: [REFERENCE RESEARCH COMPLETED — SOURCE TRACE]. Required report: `SOL_REFERENCE_LAB/Reports/07_LOCOMOTION_PIPELINE.md`.
- Reconstructed source pipeline from high-level decision to Navigation, actor provider/native path call, custom PathFindState advancement, locomotion animation synchronization, position-based progress, arrival stop and terminal reconciliation.
- Living Fellows uses a bounded Lua navigation layer and native PFB leases. Source has route re-arm/reset paths without process restart. A focused live same-actor three-route proof was not established; tests were inspected only, not run.
- Current Sol test prototype already has native PathFindState execution and terminal diagnostics, but lacks the broader route owner/topology layer in inspected source. No patch or runtime action.
- Next: Stage H stuck detection and recovery ladder.

## 2026-10-20 — Reference Stage H: Stuck Detection and Recovery
- Status: [REFERENCE RESEARCH COMPLETED — SOURCE TRACE]. Required report: `SOL_REFERENCE_LAB/Reports/08_STUCK_RECOVERY.md`.
- Inspected world-position progress, separate PFB lease progress, actor-native-state waits/cancellation, path-search leases, blocker classification/evidence, stop-and-replan then lateral clearance, failed traversal limits, follow-specific last resort and terminal episode retry gates.
- Source defaults: generic stuck 2200 ms, obstacle 900 ms, recovery attempt cap 3, terminal retry 8000 ms; test definitions read but not executed.
- Sol diagnostic implication: correlate native update → PFB/start → state/movement variables → X/Y delta before recovery. No Sol implementation or runtime action.
- Next: Stage I world interactions.

## 2026-10-20 — Reference Stage I: World Interaction
- Status: [REFERENCE RESEARCH COMPLETED — STATIC SOURCE TRACE]. Report: `SOL_REFERENCE_LAB/Reports/09_WORLD_INTERACTION.md`.
- Pinned source: `thorelvin/living-fellows`, branch `living_fellows/0.26.51`, commit `f0eaa49802b5b1c767adf175a57a7ad41fa676c`, VERSION `0.26.51`, PZ 42.21.0.
- Traced edge-affordance discovery and passability, door reservations and verified toggles, window urgency/glass/climb actions, native fence/wall calls, stairs/slope topology and native 3D confirmation, furniture posture release before navigation, and bounded object/container interaction target selection.
- Static source proof only. Test harnesses and runtime were not executed; no animation, collision, or all-map compatibility claim. REA was attempted but yielded no Java/Lua graph; this phase is explicitly source trace, not REA evidence.
- No Sol implementation, test, build, runtime, `08_RUNTIME_TEST`, or production mod changed.
- Next exact step: Stage J vehicle architecture review, reference only; do not implement on Sol.

## 2026-10-20 — Reference Stage J: Vehicle Architecture
- Status: [REFERENCE RESEARCH COMPLETED — STATIC SOURCE TRACE]. Report: `SOL_REFERENCE_LAB/Reports/10_VEHICLE_ARCHITECTURE.md`.
- Pinned source: `thorelvin/living-fellows`, branch `living_fellows/0.26.51`, commit `f0eaa49802b5b1c767adf175a57a7ad41fa676c`, VERSION `0.26.51`, PZ 42.21.0.
- Traced seat manifest/reservations and supervisor transactions, native entry/seat postconditions/rollback, passenger and driver ownership, per-frame native driver controls, stationary verified exit and seat-switch fallback, and conversion of native seat saves to virtual stored passengers across unload/reload.
- Static source and live-harness documentation only. No tests, game runtime, visual checks or save/reload were executed; no Sol implementation/build/runtime, `08_RUNTIME_TEST`, or production mod changed. REA did not supply a Java/Lua call graph.
- Next exact step: Stage K persistence/offscreen source study, then Knox public documentation only for conceptual comparison; do not reuse Knox code.

## 2026-10-20 — Reference Stage K: Persistence and Offscreen Representation
- Status: [REFERENCE RESEARCH COMPLETED — STATIC SOURCE TRACE + PUBLIC-DOC CONCEPT REVIEW]. Report: `SOL_REFERENCE_LAB/Reports/11_PERSISTENCE_AND_OFFSCREEN.md`.
- Living Fellows proof: stable identity-backed record capture and ownership-verified save; autonomous faction residents alone use the reviewed capture/remove/hibernated-snapshot/queued-wake path with safety observation, 120-tile hibernate and 100-tile wake defaults. Recruited companions and vehicle-stored passengers use distinct paths.
- Knox review was public documentation only. Findings are marked `CONCEPT ONLY — NO CODE REUSE`; README states 42.21 compatibility is still under test, autonomous driving is experimental, and the repo is not open source.
- No Knox source/runtime inspection, Living Fellows test/runtime execution, or Sol code/build/runtime/`08_RUNTIME_TEST`/production changes.
- Next exact step: Stage L testing strategy and harness proposal; inspect tests/docs only and do not run them.

## 2026-10-20 — Reference Stage L: Testing Strategy
- Status: [REFERENCE RESEARCH COMPLETED — TEST-SOURCE REVIEW ONLY]. Report: `SOL_REFERENCE_LAB/Reports/12_TESTING_STRATEGY.md`.
- Mapped static/source gates, Java bridge harnesses, Kahlua/Lua harnesses, pinned-runtime compilation, real-engine isolated-save harnesses, visual capture and manual playtest layers. Full project gate includes bridge rebuild and packaging; it was not run.
- Reviewed runner wiring and representative harness families for lifecycle, bridge, perception, movement/recovery, actions, vehicles, persistence and UI. Assertions and scripts were inspected only; none executed.
- Findings: active test runtime is pinned to PZ 42.21.0, while gameplay README says 42.20.4; an excluded SCBridgeLoadTest contains stale 42.20.4/IsoSurvivor assertions. These are documentation/source drift observations, not test failures. Visual complete-body proof and a general long idle soak are not established by static checks.
- Added a Sol harness proposal only. No Sol test/build/runtime, `08_RUNTIME_TEST`, or production changes.
- Next exact step: Stage 13 BanditsPerformanceOverride, performance references only; confirm license and use primary public repository material. Then consolidate Stage 14 Knox concepts and main reports.

## 2026-10-20 — Reference Stage 13: Bandits Performance Lessons
- Status: [REFERENCE RESEARCH COMPLETED — PUBLIC REPOSITORY/DOCUMENT REVIEW]. Report: `SOL_REFERENCE_LAB/Reports/13_BANDITS_PERFORMANCE_LESSONS.md`.
- Primary GitHub documents attribute the main cost to per-bandit O(N) scans across a cell-wide zombie/bandit cache (O(N²) aggregate), frequent relationship/LOS work, a second flee pass, and population scaling. Cache room lookup and repeated visual stamping are secondary candidates; timing hooks exist for measurement.
- Sol recommendations are conditional proposals: profile first, reuse a bounded spatial candidate snapshot, gate expensive LOS behind cheap tests, stagger non-urgent work, and cap active population only if measurements justify it. The Bandits FPS claims are repository-reported and not independently reproduced.
- No immutable `main` commit SHA or explicit license was established in the inspected view; no code reused. No test, benchmark, build, game runtime, or Sol change.
- REA MCP is connected (`rea-agents` 6.5.0 / skill 42); current session closed, no active target. No Java/Lua call graph was produced; this is source/public-document review.
- REA continuation checkpoint and exact tooling incident wording: `SOL_REFERENCE_LAB/Reports/REA_CONTINUATION_CHECKPOINT_20261020.md`. Available providers do not expose Java/Lua source-tree analysis; no mismatched target was opened.
- Next: Stage 14 Knox documentation-only concepts, then synthesize gap matrix and V2 proposal.

## 2026-10-20 — Reference Stage 14: Knox Public Concepts
- Status: [REFERENCE RESEARCH COMPLETED — PUBLIC DOCUMENTATION ONLY]. Report: `SOL_REFERENCE_LAB/Reports/14_KNOX_CONCEPTS.md`.
- Public design documentation describes stable identity separate from live actor representation and event/ledger-style offscreen activity reconciled on activation. These remain concepts and author claims; no Knox source implementation was inspected or reused.
- Knox README statements about release/PZ compatibility, experimental driving, and non-open-source status are attributed to the README and may change upstream.
- No Sol source/build/test/runtime, production, or vehicle work. No REA target was opened.
- Next: consolidate reports 00–14, preserve evidence classes, and keep implementation deferred.

## 2026-10-20 — Living Fellows Gap Matrix and Sol V2 Proposal
- Status: [COMPLETED — RESEARCH DOCUMENTS ONLY]. Deliverables: `SOL_REFERENCE_LIVING_FELLOWS_ANALYSIS.md`, `SOL_V2_ARCHITECTURE_PROPOSAL.md`.
- Consolidated reports 00–14 in a gap matrix and marked static source, public claims, historical Sol runtime, inference, and unknowns separately. Current route-found/no-position-change remains unresolved and is not converted into a static-source conclusion.
- Proposed event + snapshot flow, native actor/lifecycle boundaries, scheduler budget bands, perception freshness/completeness, local reflex versus AI planning, single action owner, native locomotion receipt/postconditions, persistence boundary, diagnostics schema, and evidence-layer test strategy. No implementation authorized or performed.
- Verified REA connection and session status: `rea-agents` 6.5.0, skill 42; no binary target open; Ghidra unavailable because `GHIDRA_INSTALL_DIR` is unset. This was not Java/Lua call-graph evidence.
- No tests, benchmark, compile/build, game launch, screenshots, `08_RUNTIME_TEST`, production, or Sol code changes. Living Fellows checkout remains at pinned commit and clean as of final status inspection.
- Next exact action: on a safely available test environment, take full movement-state snapshots at T0/immediate/0.5–1 s/2 s with an empty nearby target, then follow only the evidence at the first failing boundary. Do not begin V2 coding or vehicle tests before this diagnosis.

## 2026-10-20 13:16 Europe/Berlin — Reference evidence completion addendum
- Status: [REFERENCE RESEARCH COMPLETED — PINNED SOURCE TRACE]; [REA SOURCE-TREE ANALYSIS BLOCKED].
- Added the requested claim-to-source evidence index to `SOL_REFERENCE_LAB/Reports/04_PERCEPTION_SYSTEM.md`. Each row includes its evidence class, source file/symbol and exact Living Fellows commit SHA. Harness assertions are labeled `[TEST PROOF — NOT EXECUTED]`.
- Added the behavior comparison table to `SOL_REFERENCE_LAB/Reports/02_BRIDGE_LIFECYCLE.md`; updated the report index to include `03_SCHEDULER_AND_TICK_BUDGET.md`; linked the architecture map and initial gap list.
- REA `open_binary` rejected the Java/Lua repository directory (`target_unavailable`, `directory_requires_file`); no analysis target/session or graph was created. This remains a provider limitation, not a Sol or Living Fellows defect. Record: `SOL_REFERENCE_LAB/Evidence/REA_OPEN_DIRECTORY_ERROR_20261020.md`.
- Source revision recorded for every Living Fellows result: `f0eaa49802b5b1c767adf175a57a7ad41fa676c4`, branch `living_fellows/0.26.51`, VERSION `0.26.51`, target PZ `42.21.0`.
- No Sol source, `08_RUNTIME_TEST`, production, build, game/runtime, save, or reference clone content was changed. No tests were executed.
- Next: use a supported REA Java/Lua source-tree route if available without reinstalling; otherwise preserve the explicit source-trace boundary. Do not start Sol V2 implementation or a runtime experiment as part of this reference study.

## 2026-10-20 13:40 Europe/Berlin — Vanilla bytecode contract and gap synthesis
- Status: [REFERENCE RESEARCH COMPLETED — LOCAL BYTECODE + PINNED SOURCE]; [PROPOSED — NOT IMPLEMENTED].
- Pinned Vanilla evidence to installed `projectzomboid.jar` SHA-256 `E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`, Steam BuildID `25485521`; manifest and relevant class hashes: `SOL_REFERENCE_LAB/Evidence/VANILLA_B42_BYTECODE_MANIFEST_20261020.md`.
- Bytecode trace: `IsoGameCharacter.pathToLocationF` -> `PathFindBehavior2.pathToLocationF/setData` resets/cancels old route work and sets finder `notrunning`; actor update advances `StateMachine`; `PathFindState.execute` invokes PFB; `moveToPoint` needs positive animation deferred movement and then submits `moveUnmodded`; path-state exit cancels and clears terminal state. No runtime behavior inferred from these static facts.
- Lua lifecycle bytecode shows `LuaManager.init()` wiping/replacing environment and exposer and calling `exposeAll()`. Appended a full Vanilla column to `Reports/02_BRIDGE_LIFECYCLE.md` without deleting the prior table.
- Added the full gap matrix, consolidated reference study and future-only V2 proposal. The top three proposals are locomotion physical-progress receipts, actor/update single-owner lifecycle, and bounded Perception Bus completeness/freshness.
- REA `open_binary` accepted the game JAR as an archive; `binary_overview` returned `capability_unavailable / unsupported_provider`, so no REA graph claim is made. Source directory rejection is correctly classified as an input-format boundary; local `javap` supplied the bytecode trace. REA was not reinstalled or reconfigured.
- Sol status remains static-source comparison plus historical notes; no fresh runtime evidence. No Sol source, `08_RUNTIME_TEST`, production, save, build, test, or game process was changed or launched. No vehicle work.
- Next exact step: review the findings; any later runtime investigation remains a separate controlled test task. No Sol V2 implementation begins from this proposal alone.

### Addendum — proposal test gates and evidence manifest completion
- Each of the three future foundation proposals now names likely files, dependencies, benefits, risks and distinct regression cases; uncertain future paths are marked as candidates/TBD rather than existing implementation facts.
- Completed the vanilla class manifest with `IsoMovingObject.class` length 62,965 and SHA-256 `7E6E84FE9D3CB264E8D8E682D91E0ABE919D481B7349D17B997E8A78F2293A5F`.
- The deliverable audit found only untracked project directories/files in Git status; this workspace did not have tracked baseline entries for the overall Sol artifact. The 08_RUNTIME_TEST directory was only read, not edited. No tests were run.

## 2026-10-20 13:54 Europe/Berlin — Foundation Phase 1: Runtime Supervisor & Actor Lifecycle Owner
- Status: [FOUNDATION PHASE 1 — BLUEPRINT COMPLETED — NOT IMPLEMENTED]. Deliverable: `SOL_RUNTIME_SUPERVISOR_BLUEPRINT.md`.
- Reference basis: Living Fellows branch `living_fellows/0.26.51`, VERSION `0.26.51`, commit `f0eaa49802b5b1c767adf175a57a7ad41fa676c4`, PZ target 42.21.0; Vanilla installed JAR SHA-256 `E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`, Steam BuildID `25485521`; Sol native prototype and separate Lua mod were inspected read-only.
- Key gaps: native `SolBridge` owns creation/registration and its teardown catches and ignores stage failures before clearing the shell reference; `SolExposure` accepts a non-null bridge global without validating the complete protocol/API; no world generation owner or explicit backend selector was found; `Sol.lua` is an independent IsoZombie + OnTick actor path.
- Proposed architecture: one native-only `SolRuntimeSupervisor` owns generation-scoped actor lifecycle and retryable verified cleanup; `SolExposure` owns main-thread environment publication; Vanilla `IsoCell`/`MovingObjectUpdateScheduler` remains the sole shell update dispatcher; selected backend gate prevents claiming one Sol while both actor implementations are active.
- Planned candidate changes only (not made): new `SolRuntimeSupervisor.java`, plus narrow lifecycle delegation/telemetry changes in `SolBridge.java`, `SolBootstrap.java`, and `SolExposure.java`. `SolIsoPlayerShell.java`, `Sol.lua`, movement, AI, vehicles, production, and runtime profile were left outside the phase.
- Blueprint includes pinned evidence labels, current lifecycle map, Vanilla contract, gap/adoption tables, state machine, idempotency and invariant lists, diagnostics, A-H failure recovery, minimal patch proposal, 12 regression cases, risks, and rollback.
- Evidence boundary: static source and bytecode inspection only. REA could not provide Java/Lua source call graph. No tests, build, compile, runtime, screenshot, game launch, production change, or 08_RUNTIME_TEST edit was performed. All listed regression cases remain planned, not executed.
- Next exact step: user review/approval before any implementation.

## 2026-10-20 14:23 Europe/Berlin — Foundation Phase 1 implementation started
- Status: [FOUNDATION PHASE 1 — IMPLEMENTATION IN PROGRESS]. Blueprint reviewed and implementation authorized in `08_RUNTIME_TEST` only.
- Backup before source edits: `08_RUNTIME_TEST/backups/foundation_phase1_20261020_1423/` contains pre-edit copies of `SOL_MASTER_PLAN.md`, `SOL_ENGINEERING_LOG.md`, `SolBridge.java`, `SolBootstrap.java`, and `SolExposure.java`. `SolRuntimeSupervisor.java` did not exist.
- Allowed candidates: new `SolRuntimeSupervisor.java` and lifecycle-only changes to `SolBridge.java`, `SolBootstrap.java`, `SolExposure.java`; actor behavior and the Lua legacy backend stay unchanged unless a documented minimal backend gate proves essential.
- Test order recorded: T0 build; T1 initial lifecycle; T2 duplicate spawn; T3 idle; T4 teardown; T5 respawn; T6 environment reset; T7 world re-entry; T8 movement smoke. Every failure is to be logged before repair. No test has run yet.
- Production remains untouched. Build output must use a new timestamped directory. Runtime launch must be preceded by a PZ Java process-count check.

## 2026-10-20 14:23 Europe/Berlin — Historical Living Fellows SHA correction
- Status: [DOCUMENTATION CORRECTION — NO TECHNICAL CHANGE]. The older Stage I World Interaction entry and Stage J Vehicle Architecture entry contain a 39-character abbreviated commit string. The intended full analyzed commit for both entries is `f0eaa49802b5b1c767adf175a57a7ad41fa676c4` (Living Fellows `0.26.51`). Historical lines were retained unchanged; this append-only note supplies the correction.

### 2026-10-20 14:31 Europe/Berlin — Test-profile legacy actor gate identified
- Status: [FOUNDATION PHASE 1 — IMPLEMENTATION IN PROGRESS]. Read-only inspection found `08_RUNTIME_TEST/profile/Zomboid/mods/default.txt` selects mod ID `Sol`; the actual test-profile source is `08_RUNTIME_TEST/profile/Zomboid/mods/SolTest/media/lua/client/Sol.lua`, whose `Sol.spawn()` calls `addZombiesInOutfit`, marks `solEmbodied`, and whose `onGameStart()` installs its own zombie `OnTick` handler. Its test-only `onGameStartWithTest()` also calls `Sol.spawn()`.
- This is the legacy `IsoZombie` creation site for the active test profile. It is distinct from `Sol/` production source. It will be isolated by a fail-closed backend check in this test-profile copy only; no existing legacy actor will be deleted. Production compatibility is preserved because `Sol/media/lua/client/Sol.lua` remains unchanged and the gate is not copied to production.
- Detection plan: native supervisor will count current-cell zombies whose mod-data `solEmbodied` marker is true before native spawn and report the count. If any exists, native spawn is blocked and cleanup is not attempted automatically.
- Pre-edit backup for the test-only Lua file is required before patch: `08_RUNTIME_TEST/backups/foundation_phase1_20261020_1423/Sol.lua.test-profile.pre-edit`.
- No source edit or runtime change has occurred at this discovery point.

### 2026-10-20 14:39 Europe/Berlin — Initial lifecycle implementation staged for T0
- Status: [FOUNDATION PHASE 1 — IMPLEMENTATION IN PROGRESS]. Changed only isolated test files: new `08_RUNTIME_TEST/SolNativePrototype/src/sol/bridge/SolRuntimeSupervisor.java`; delegated native spawn/removal/state reads in `SolBridge.java`; connected the existing 500 ms bootstrap callback in `SolBootstrap.java`; made `SolExposure.java` validate protocol, backend and required Lua-callable API members; added a fail-closed backend gate in `08_RUNTIME_TEST/profile/Zomboid/mods/SolTest/media/lua/client/Sol.lua`.
- Legacy zombie source identified: test profile's `SolTest/media/lua/client/Sol.lua` calls `addZombiesInOutfit`, marks `solEmbodied`, and its test callback can call `Sol.spawn()`. The test copy now requires explicit `LEGACY_ZOMBIE` selection; absent/incompatible bridge and `NATIVE_SHELL` suppress both its spawn entry and its zombie OnTick hook. Existing legacy actors are not removed.
- `SolRuntimeSupervisor` now tracks JVM/world/Lua/actor generations; owns one pending spawn and shell identity; fences old completion IDs; validates world/cell/square/model/player isolation; records staged cleanup failures and retries; reports actor, legacy-zombie, scheduler/model, bridge and update-owner diagnostics. It never calls `IsoPlayer.update()` or the shell's `update()` and adds no native actor tick hook.
- Pre-edit backups: `08_RUNTIME_TEST/backups/foundation_phase1_20261020_1423/` (docs and three existing Java files), plus `Sol.lua.test-profile.pre-edit` (test Lua profile copy). `SolRuntimeSupervisor.java` was new. Production source `Sol/media/lua/client/Sol.lua` was not changed.
- Current PZ process check: `PZ_COUNT=0`; no launch yet. T0 compile/package inspection begins next in a fresh build directory and will use the installed game JAR/API classpath, never compile stubs as output.

### 2026-10-20 14:45 Europe/Berlin — T0 attempt 1 FAILED: compiler bytecode-version mismatch
- Status: [T0 — FAILED — TOOLCHAIN VERSION MISMATCH]. Command used JDK 17 `javac` against installed `projectzomboid.jar` and all installed game jars, with no compile stubs on the classpath.
- Observed error: multiple game classes (including `zombie.MainThread`, `IsoPlayer`, `IsoCell`, `ModelManager`) report `class file has wrong version 69.0, should be 61.0`. JDK 17 accepts class version 61; installed PZ artifacts require Java 25/class version 69.
- Root cause: selected compiler is older than the target game bytecode. The many dependent “cannot find symbol” diagnostics are cascading from that single class-version rejection; they are not yet classified as source defects.
- Artifact: no JAR was produced; this build directory is rejected and must never be launched: `08_RUNTIME_TEST/SolNativePrototype/build_foundation_phase1_20261020_1445/`.
- No Sol source correction was made in response. Next: locate a local Java 25 JDK compiler; if present, build into a distinct new directory. Otherwise stop T0 as blocked rather than using stubs or modifying the game JAR.

### 2026-10-20 14:34 Europe/Berlin — T0 toolchain recovery
- Status: [IN PROGRESS — TOOLCHAIN RECOVERY]. Targeted local inspection found only `javac 21.0.10` under Android Studio and no Java 25 JDK compiler. The PZ runtime itself is OpenJDK 25.0.1 but has no `jdk.compiler` module. `winget install --id Microsoft.OpenJDK.25 --exact --scope user` returned “No applicable installer found”; it made no install.
- Staged the official Microsoft OpenJDK 25 Windows x64 ZIP under `08_RUNTIME_TEST/toolchain/` (outside production); downloaded archive SHA-256: `3C9099E60A82E17F5847052F50F3B107BFC1D32B366E1A20ADBD1D0F303760E7`; Microsoft’s `.sha256sum.txt` matched exactly and `javac` reports `25.0.4.1`; extracted directory `microsoft-jdk-25/jdk-25.0.4.1+1`.
- No Sol source, production file, game runtime, or save was changed/launched by toolchain recovery. Exact next step: inspect prototype sources/build wiring and rerun T0 in a fresh build directory.

### 2026-10-20 14:35 Europe/Berlin — T0 attempt 2: compilation passed, packaging failed
- Status: [T0 — IN PROGRESS — PACKAGING BLOCKED]. Compiled all six prototype Java sources against the installed `projectzomboid.jar` and `ZombieBuddy.jar` using checksum-verified Microsoft `javac 25.0.4.1`; the compiler exited successfully with no diagnostics. No compile stubs were present on classpath or packaged.
- Packaging via JDK `jar --create` failed with `java.nio.file.AccessDeniedException` while moving its temporary archive from the sandbox Temp directory to `build_foundation_phase1_20261020_1435/SolNativeBridge.jar`. The JAR was not created; this is a packaging/environment issue, not a source compile failure. Compiled classes and `javac.log` remain only in this rejected build folder.
- No launch/runtime test occurred. Next: create a distinct fresh build directory, rerun compilation, direct Java temp files inside that directory, package, then inspect JAR contents and SHA-256 before any launch.

### 2026-10-20 14:36 Europe/Berlin — T0 PASSED: fresh Java 25 build artifact
- Status: [COMPLETED — T0 STATIC BUILD]. Repeated the full compile in fresh `08_RUNTIME_TEST/SolNativePrototype/build_foundation_phase1_20261020_1436/`; used checksum-verified `javac 25.0.4.1`, actual installed PZ 42.21 `projectzomboid.jar` plus `ZombieBuddy.jar`, and all six prototype Java source files. Compiler exited 0 without diagnostics. No compile stubs were on the classpath.
- Packaged only compiled `sol/` classes. `jar --list` contains `META-INF` and `sol/bridge` only; no `zombie/` stub/API classes. SHA-256 `14E0CA66781530A54192BC7A9523D06241FD6CA621251781FD01519BFD7B4B69`.
- The packaging retry succeeded after directing JDK temporary files to the build-local `tmp/` directory. The failed attempt folders remain preserved and are not launch candidates.
- The staged test JAR is not yet runtime proof. No game launch occurred in T0. Next: inspect isolated launch arguments/profile integration, check `PZ_COUNT` immediately before launch, then begin T1 only if no PZ runtime is already running.

### 2026-10-20 14:37 Europe/Berlin — T1 launch preparation
- Status: [IN PROGRESS — T1 READY TO LAUNCH]. Created a new, test-only args file beside the T0 artifact: `build_foundation_phase1_20261020_1436/sol-foundation-phase1-runtime.args`. It preserves the existing test profile/home and Java flags, points only to the new build JAR, and selects `-Dsol.backend=NATIVE_SHELL`. Args SHA-256: `59B64EBF46FAFCAAC388DE75BDD8689665E8EE3EFE20805C07C93822FAEE299C`.
- Immediate process check: `PZ_COUNT=0`; prior PID `34984` is absent. CIM query is denied in this sandbox, but direct `Get-Process java,javaw` filtered to the installed Project Zomboid JRE path also returned zero. No launch has occurred yet.
- Exact next step: make the same path-filtered process check in the launch command itself; if count is nonzero, abort. Otherwise launch this one test profile visibly and inspect the game plus runtime logs for T1. Production remains untouched.

### 2026-10-20 14:38 Europe/Berlin — T1 runtime launch started
- Status: [IN PROGRESS — T1 INITIAL LIFECYCLE]. The launch-command gate observed `PRELAUNCH_PZ_COUNT=0`, then started one visible Java 25 game process with the isolated args file. After 4 seconds: `PZ_COUNT=1`, PID `36160`, path `...\ProjectZomboid\jre64\bin\javaw.exe`.
- Build: `build_foundation_phase1_20261020_1436`, JAR SHA-256 `14E0CA66781530A54192BC7A9523D06241FD6CA621251781FD01519BFD7B4B69`. Test profile is `08_RUNTIME_TEST/profile`; backend property is `NATIVE_SHELL`.
- Launch/process proof only; main menu/world load and actor lifecycle are not yet confirmed. Next: observe the unique Project Zomboid window and runtime log, then capture T1 state without issuing any duplicate spawn request.

### 2026-10-20 14:39 Europe/Berlin — T1 attempt 1 FAILED: runtime exited before a window/world
- Status: [FAILED — T1 INITIAL LIFECYCLE NOT REACHED]. The one launched process (PID `36160`) exited; subsequent direct process check found no Java/Javaw process and `sky.list_windows()` returned no Project Zomboid window. No second launch was attempted.
- `console.txt` and `Logs/2026-10-20_14-35_DebugLog.txt` show Build 42.21.0 / Java runtime 25.0.1 / `sol.backend=NATIVE_SHELL`, graphics initialization succeeded, then log output ends after FMOD `FMOD_System_Set3DSettings() result: No errors.` No `SolRuntimeSupervisor`/bridge diagnostics, Java stack trace, world load, or T1 actor state was captured. The debug log also contains WMI query warnings `80070005: Access is denied`; these are not yet linked to termination.
- Root cause: unresolved. Runtime launch is not considered successful, and T1–T8 remain untested. Exact next step: read-only inspect launcher/bootstrap startup sequence and Windows/game crash evidence, determine why process exits before main UI, document that diagnosis before any source/config fix or retry. No source repair made.

### 2026-10-20 14:40 Europe/Berlin — T1 termination evidence remains insufficient
- Status: [BLOCKED — ROOT CAUSE UNRESOLVED]. Read-only review of `SolLauncher.main`, changed `SolBootstrap.start`, and `SolRuntimeSupervisor.bootstrapStarted` found no confirmed termination cause. The current debug/console logs stop at FMOD initialization and contain no Java/bridge exception. Windows Application log queries are unavailable (`Get-WinEvent`: unauthorized; `Get-EventLog`: PowerShell remoting feature unavailable). No current crash dump or `hs_err_pid36160.log` exists; `hs_err_pid*` files found in the game directory are historical (latest dated 2026-10-19).
- The WMI `80070005` warnings are observed but not proven causal. Do not classify them as root cause. No source or runtime configuration fix has been made.
- Exact next diagnostic: after an immediate `PZ_COUNT` gate confirms zero, perform one diagnostic launch of the same test args through `java.exe` with stdout/stderr redirected to fresh files in the build folder; inspect the captured termination detail before considering any repair. This changes no Sol source or production file.

### 2026-10-20 14:41 Europe/Berlin — T1 diagnostic launch remains active
- Status: [IN PROGRESS — T1 STARTUP OBSERVATION]. The launch-command gate again observed `PRELAUNCH_PZ_COUNT=0`. Same args/JAR/profile were launched once via the game `java.exe` with stdout/stderr redirected (no source/config change); PID `20524`, after 8 seconds `PZ_COUNT=1`, process not exited.
- Captured stdout reaches SLF4J provider initialization after PZ graphics and FMOD setup; stderr is empty at this snapshot. Runtime `console.txt` was updated. `sky.list_apps()` still returns no Project Zomboid window, so this launch is not yet visual proof and no world/action test is being issued.
- Exact next step: wait briefly and inspect whether startup continues or a window appears; then capture current logs/process. Do not launch another process while PID `20524` is alive.

### 2026-10-20 14:42 Europe/Berlin — T1 diagnostic attempt 2 FAILED before main UI
- Status: [FAILED — T1 INITIAL LIFECYCLE NOT REACHED]. After the observation interval PID `20524` was no longer present; no Java process remained. Captured stdout ends at `SLF4J(I): Attempting to load provider "zombie.core.logger.Slf4jBridge"`; redirected stderr is empty. The newest DebugLog again ends immediately after FMOD setup; no Project Zomboid window appeared in `sky.list_apps()`.
- This narrows the failure point to immediately after logger provider initialization, but does not prove a Java exception, native crash, or graceful exit. Process exit code was not retained by the prior command. Root cause remains unresolved; no code or args changes made.
- Exact next step: if a diagnostic retry is needed, capture the process exit code from launch through completion and use a visible window style while retaining stdout/stderr files; enforce `PZ_COUNT=0` in the command. Do not issue game actions until a window/world is confirmed.

### 2026-10-20 14:40 Europe/Berlin — T1 diagnostic attempt 3: missing font-page assets observed
- Status: [BLOCKED — STARTUP ROOT CAUSE STILL UNCONFIRMED]. The visible-style diagnostic invocation's stdout progressed through `Loading Mods`, `loading Sol`, Lua precompile and core class loads; stderr recorded `AngelCodeFont failed to load page 0 texture` for `media/mainfont_0.png`, `media/mainfont2_0.png`, and `media/fonts/zomboidDialogue.bmfc_0.png` (each reported twice). Direct read-only `Test-Path`/file-open checks against these exact installed-game paths returned `Exists=False`, `Readable=False`.
- The process was gone at the follow-up check (`PZ_COUNT=0`); no game window/world appeared. The command wait exceeded the tool's synchronous window, so its spawned PID/exit code was not emitted; stdout/stderr were retained at `build_foundation_phase1_20261020_1436/t1-diagnostic-visible-{stdout,stderr}.log`. Windows event-log restrictions remain. Missing font assets are a concrete startup defect candidate but not yet proven to terminate this game build.
- No source, args, production files, game installation, or save was modified. Next: inspect the installed media directory/layout read-only to verify whether these files are truly absent or reside under a different path; only then decide whether T1 is blocked by the test installation/runtime environment. No fourth launch until that evidence is reviewed.

### 2026-10-20 14:40 Europe/Berlin — T1 startup-path findings
- Status: [IN PROGRESS — STARTUP DIAGNOSIS]. The retained stdout proves the new launcher and supervisor execute: `[SolRuntimeSupervisor] STATE COLD->BOOTSTRAPPING ...` then `BOOTSTRAPPING->WAITING_LUA ...`; PZ proceeds through FMOD, native graphics, `Loading Mods`, and logs `loading Sol`. Thus startup did not terminate inside `SolBootstrap.start()` and the earlier log cutoff was incomplete evidence, not a confirmed bootstrap crash.
- Installed `media/mainfont.fnt` explicitly references `mainfont_0.png`, and `media/mainfont2.fnt` references its corresponding page; those loose PNG paths are absent. `media/texturepacks/UI.pack` exists, so these missing loose files may be supplied by a pack; their warnings alone are not a proven root cause. The dialogue font PNG path is also absent loose. No source/assets/game installation were changed.
- The third diagnostic process later disappeared (`PZ_COUNT=0`); its PID/exit code were not emitted because the tool call yielded while waiting. Last captured stdout shows `Loading Mods` and core class loading. Root cause remains unresolved. Exact next step: inspect the installed `UI.pack` read-only for these font-page entries and inspect remaining console/debug tail to decide whether asset lookup is expected; then stop or request a new controlled diagnostic only if necessary. No further launch now.

### 2026-10-20 14:40 Europe/Berlin — UI.pack inspection probe failed safely
- Status: [BLOCKED — ASSET FORMAT NOT YET IDENTIFIED]. Read-only `7z l media/texturepacks/UI.pack` returned `Cannot open the file as archive`; the PZ `.pack` is not a ZIP/7z archive. The same probe's PowerShell header helper used unsupported `Get-Content -Encoding Byte` and failed before reading the header. No archive was changed and no game process was launched.
- This is a tooling/format limitation, not a Sol failure. Exact next step: inspect the installed PZ `TexturePackPage` API/bytecode or an existing compatible parser to establish how `.pack` stores font textures; do not treat the font warnings as root cause until then.

### 2026-10-20 14:40 Europe/Berlin — PZ texture-pack parser evidence
- Status: [SOURCE PROOF — FORMAT IDENTIFIED, CONTENT PENDING]. JDK 25 `javap` against the exact installed `projectzomboid.jar` shows `zombie.core.textures.TexturePackPage.loadFromPackFile(BufferedInputStream)`, plus the pack-page/subtexture maps; therefore `media/texturepacks/UI.pack` is a game-specific texture pack, not a general ZIP archive. Direct bytecode also shows `TexturePackPage.getTexture(String)` treats `.png` paths as shared texture lookups.
- The game-root `.fnt` descriptors reference page PNGs, while `TexturePackPage` exposes a native pack loader. Whether `UI.pack` contains the requested pages is not yet proven. This supports the possibility that the font warnings are a loose-file lookup before pack registration, not a missing-install root cause. No files modified.
- Exact next step: read-only byte-string scan of `UI.pack` for the font names and inspect the current log tail. If inconclusive, classify T1 startup as blocked/unresolved and stop without additional launch or source patch.

### 2026-10-20 14:40 Europe/Berlin — UI.pack byte-string scan result
- Status: [REFERENCE/STATIC EVIDENCE — FONT WARNING STILL NOT ROOT CAUSE]. Read-only scan of the installed `media/texturepacks/UI.pack` found zero ASCII occurrences for `mainfont_0.png`, `mainfont2_0.png`, `zomboidDialogue.bmfc_0.png`, `mainfont.fnt`, or `mainfont2.fnt`. Latest console/stdout ends at LuaCompiler and core class loading, with only font-page errors and no Sol exposure/world load. `PZ_COUNT=0`.
- Because `.pack` content may be indexed/binary rather than storing names as ASCII, this scan does not prove the texture payload is absent. No known termination exception or exit code is available; no further launch or source change is authorized by evidence so far.
- Exact next step: compare earlier known-working PZ logs from this test profile for the same font warnings and startup stage; this distinguishes baseline environment noise from a regression in the new prototype. Then mark T1 blocked if evidence remains inconclusive.

### 2026-10-20 14:41 Europe/Berlin — T1 gate closed BLOCKED; no evidence-supported repair
- Status: [BLOCKED — T1 INITIAL LIFECYCLE]. Comparison against the prior known-working test-profile log `Logs/logs_2026-10-20_11-01/2026-10-20_11-00_DebugLog.txt` proves the same three AngelCodeFont page-load errors existed during a successful startup; that older run reached `[SolNativeBridge] READY` at 11:01:32 and `[SolNativeShell] READY` at 11:01:51 with `activeModel=true`, `alpha0=1.0`, `targetAlpha0=1.0`. Therefore the font warnings are baseline and not an established cause.
- Current build log `Logs/2026-10-20_14-39_DebugLog.txt` records supervisor bootstrap transitions, PZ native graphics/FMOD, `Loading Mods`, `Loading Translations`, and successful loading of `IsoPlayer`, but ends before `[SolNativeBridge] READY`, world/UI, or actor creation. Current process check: `PZ_COUNT=0`; no test runtime remains open. Exit code/crash evidence could not be captured; Windows event-log access is denied/unavailable.
- Root cause remains unresolved. No justified source patch exists, so no code fix or additional launch is performed. T2–T8 are [BLOCKED] behind the failed T1 startup gate. T0 alone is completed. Production and save state remain untouched.
- Exact next step: obtain a supported way to capture the Java process exit/exception (or Windows crash event) and diagnose why the new build stops before bridge READY; only after a cause-specific fix and a fresh T0 build should T1 be retried. Do not continue to T2 or run movement/chunk tests now.

### 2026-10-20 14:41 Europe/Berlin — final isolation check
- Status: [COMPLETED — SCOPE/PROCESS AUDIT]. Recomputed all three production `Sol/` hashes against `08_RUNTIME_TEST/backups/foundation_phase1_20261020_1423/production_sol_baseline.sha256`; all match (`mod.info`, `README.md`, `media/lua/client/Sol.lua`). Final Project Zomboid process check: `PZ_COUNT=0`, no PID. T0 artifact remains `SolNativeBridge.jar`, SHA-256 `14E0CA66781530A54192BC7A9523D06241FD6CA621251781FD01519BFD7B4B69`.
- No production changes, save modifications, movement/spawn test, or runtime process remains. Current phase disposition: T0 completed; T1 blocked, T2–T8 not started. Continue only with supported process-exit capture and cause-specific diagnosis.

## 2026-10-20 14:49 Europe/Berlin — prior T1 process classification superseded; launch procedure recovered
- Status: [IN PROGRESS — CONTROLLED T1 PREPARATION]. Preserve all earlier entries. Their claims that the Foundation process had exited before READY are superseded as diagnostic conclusions because the launch attempts did not reliably retain exit status; a lost command/session handle is insufficient proof of a crash or graceful exit. Root cause remains unresolved.
- Recovered known-good configuration from the previous opacity runtime: bundled PZ Java 25 under `C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\jre64\bin`; game install as WorkingDirectory; `sol-shell-runtime.args` SHA-256 `0C562889CBA5E47D94F7E03E4F24DE729F97522254815D93E2A5D42DF706EF09`; JAR `build_opacitytargetfix_20261020_1055\SolNativeBridge.jar` SHA-256 `B5F6368984683A80BBCC5020CC9944E50647D37251818561E824EEA5F0651938`. Prior test-profile logs prove bridge READY and native shell READY on that configuration. This does not establish Foundation runtime success.
- Foundation retry configuration: `jre64\bin\java.exe`, args `build_foundation_phase1_20261020_1436\sol-foundation-phase1-runtime.args`, args SHA-256 `59B64EBF46FAFCAAC388DE75BDD8689665E8EE3EFE20805C07C93822FAEE299C`, JAR SHA-256 `14E0CA66781530A54192BC7A9523D06241FD6CA621251781FD01519BFD7B4B69`, WorkingDirectory `C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid`. Args preserve the prior runtime options/launcher and change the Sol JAR plus `sol.backend=NATIVE_SHELL` for this isolated test.
- Added `08_RUNTIME_TEST\launch_foundation_phase1_evidence.ps1`; static parse result `WRAPPER_PARSE=OK`. It creates a timestamped `runtime-evidence` directory, checks `PZ_COUNT=0`, launches via Java argfile with `-PassThru`, records PID/start time/command, hashes and process status, captures stdout/stderr, and copies the latest relevant DebugLog tail. No test mailbox request is sent before READY.
- Prelaunch observation for this preparation: `PZ_COUNT=0`; mailbox path exists. No launch, source patch, or production change in this entry. Exact next action: one controlled T1 through the wrapper; classify using actual exit/READY evidence before patching or advancing.

## 2026-10-20 14:53 Europe/Berlin — T1 COMPLETED — lifecycle runtime proof
- Status: [T1 — COMPLETED — RUNTIME PROOF]. Evidence directory: `08_RUNTIME_TEST\runtime-evidence\20261020_145035`. PID `20340`; Java `...\ProjectZomboid\jre64\bin\java.exe`; one runtime. The startup reached `SolNativeBridge READY`, supervisor `BRIDGE_READY`, world generation 1, and runtime command channel READY.
- After readiness, sent exactly one `phase1_T1_native_spawn_20261020_1453|NATIVE_SHELL_SPAWN|`. Runtime log records `WAITING_WORLD -> SPAWN_PENDING -> REGISTERING -> ACTIVE`, identity `1263719356`, actor generation 1, and successful postconditions `world=true,cell=true,square=true,model=true,modelAdded=true,activeModel=true`, current square `10837,10144,0`.
- `NATIVE_SHELL_STATUS` at frame 17150: `backend=NATIVE_SHELL`, `actorExists=true`, `nativeShellCount=1`, `legacyZombieCount=0`, `local=false`, `remote=false`, `inLocalSlots=false`, `globalInstance=false`, playerIndex 1, serverPlayerIndex -1; world/cell/square membership true; ModelManager and active model true; alpha/targetAlpha `1.0/1.0`; engine-owned update path `Vanilla-IsoCell-MovingObjectUpdateScheduler`; `updateCount=2440`; supervisor direct update count 0; spawnCount 1; cleanup pending/failure absent; bridge protocol valid.
- Build `build_foundation_phase1_20261020_1436`, JAR SHA-256 `14E0CA66781530A54192BC7A9523D06241FD6CA621251781FD01519BFD7B4B69`; args SHA-256 `59B64EBF46FAFCAAC388DE75BDD8689665E8EE3EFE20805C07C93822FAEE299C`. Process status reports `PZ_COUNT=1`; runtime remains open. Pre-existing WMI and pzopt warnings did not block startup/actor registration and are not identified as causes. No patch or production change.
- Exact next step: issue a single T2 duplicate spawn after confirming process still running, then capture identity/count/membership status before idle testing.

## 2026-10-20 14:55 Europe/Berlin — T3 COMPLETED — 60-second idle runtime proof
- Status: [T3 — COMPLETED — RUNTIME PROOF]. Sol remained idle for 60 seconds; only status snapshots were sent. Frame 25090: identity 1263719356/generation 1, updateCount 10380. Frame 31490 after ~30 sec: same identity/generation and memberships, updateCount 16780. Frame 36690 after ~60 sec: same identity/generation and memberships, updateCount 21980.
- Each snapshot reports one native actor, zero legacy Sol zombies, world/cell/square membership true, ModelManager and active model true, `alpha0=targetAlpha0=1.0`, update owner `Vanilla-IsoCell-MovingObjectUpdateScheduler`, supervisor direct updates 0, no stale actor/cleanup errors. PID 20340, PZ_COUNT=1, build/JAR/args unchanged. Evidence: `08_RUNTIME_TEST\runtime-evidence\20261020_145035\stdout.log`. No patch.
- Exact next step: T4 request teardown once, then verify all memberships/model registration absent and state reaches DESTROYED; if cleanup is pending, do not respawn.

## 2026-10-20 14:56 Europe/Berlin — T4 attempt 1 FAILED — incomplete teardown retained
- Status: [T4 — FAILED — CLEANUP NOT VERIFIED]. One `NATIVE_SHELL_REMOVE` request (`phase1_T4_teardown_20261020_1456`) was sent. Removal reported `REMOVING -> CLEANUP_PENDING` with world/cell/square/model registration absent and currentSquare nil, but `activeModel=true`; actor reference 1263719356 remained held. Supervisor then changed `CLEANUP_PENDING -> ACTIVE`, contrary to the intended pending-cleanup ownership state.
- Follow-up status at frame 42130 still holds the actor reference but reports world/cell/square/model registration/model active all absent, cleanup stage `retry-required`, attempt 1. State is `BLOCKED_LEGACY_ACTOR`, `legacyZombieCount=1`; prior samples at frames 17150/22450/25090/31490/36690 reported zero. The origin/first appearance of this count is unknown. No cleanup retry or patch issued.
- PID 20340, PZ_COUNT=1; unchanged isolated build/JAR/args. Evidence in `08_RUNTIME_TEST\runtime-evidence\20261020_145035\stdout.log`, `stderr.log`, and `debuglog_tail_latest.txt`. No production change.
- Exact next step: locate the first runtime log entry where legacy Sol zombie count became 1; inspect state transitions and test Lua backend gating. Hold T4 retry and T5 respawn until this anomaly is explained.

## 2026-10-20 15:01 Europe/Berlin — T4 root causes identified; patch preparation
- Status: [T4 — ROOT CAUSES IDENTIFIED]. Test profile mod selection is `mod=Sol`. Its test mod has two Sol scripts: `common\media\lua\client\Sol.lua` SHA-256 `43E3BF1DCB93890693C5B023B9291B689CC91A6008AB8D0A605329B253E3C377` and `media\lua\client\Sol.lua` SHA-256 `79812D81F708278A948DF031D44FF8BBEB821DD3442CCA3A1892CDD0AF43DAE0`. Only the latter is gated for NATIVE_SHELL. The common copy has an unguarded legacy `Sol.spawn()` and OnGameStart update/context-menu registration. Runtime logged legacy body spawn at frame 39575; supervisor detected it at frame 39594. Exact caller is not logged, but unguarded entry point explains the backend isolation gap.
- Production user-mod copy was inspected read-only: `C:\Users\JAMAL\Zomboid\mods\Sol\media\lua\client\Sol.lua`, SHA-256 `E3CE8D0F3EC9AD82530E13C342BB3AC2DE42378C9921772DFFE7E31DF9E4EE0A`; no production copy was edited.
- Java source root cause: `setBridgeProtocol()` unconditionally moves an owned actor to ACTIVE on bridge validation, even during cleanup; lifecycle retry runs only while state is CLEANUP_PENDING. Runtime confirms `REMOVING -> CLEANUP_PENDING -> ACTIVE` and subsequent state oscillation. Pre-patch Java source SHA-256 `01AA9D52BFF2E0792EB5F5FE1C97B43FD04D989E4FE192F591DED1BD2BB104BF`.
- Proposed minimal test-only fix: add backend gating to common Sol spawn/update/context menu; restrict bridge recovery to a SUSPENDED_ENV actor whose full invariants validate. No patch applied yet. Current PID 20340 / PZ_COUNT=1; one runtime active; evidence in `runtime-evidence\20261020_145035`.
- Exact next step: back up both test-only files, patch those two proven boundaries, build to a new timestamped directory, and only after T0 passes stop PID 20340 and launch one test runtime.

## 2026-10-20 15:02 Europe/Berlin — test-only source backups verified
- Status: [PATCH PREPARATION — BACKUPS VERIFIED]. Backups created before edits at `08_RUNTIME_TEST\backups\foundation_phase1_t4fix_20261020_1502\`.
- `SolRuntimeSupervisor.java` backup SHA-256 matches original `01AA9D52BFF2E0792EB5F5FE1C97B43FD04D989E4FE192F591DED1BD2BB104BF`; test profile common `Sol.lua` backup SHA-256 matches original `43E3BF1DCB93890693C5B023B9291B689CC91A6008AB8D0A605329B253E3C377`.
- No code edit yet. Current runtime PID 20340/PZ_COUNT=1. Next: apply only the lifecycle revalidation guard and the common Lua backend gate, then build in a fresh isolated directory.

## 2026-10-20 15:03 Europe/Berlin — two evidence-based test-only patches applied
- Status: [PATCH APPLIED — BUILD PENDING]. Supervisor bridge revalidation now restores ACTIVE only from SUSPENDED_ENV after full actor validation; CLEANUP_PENDING/REMOVING/blocked states remain owned and available to existing retry/reconciliation. Test profile `SolTest/common/media/lua/client/Sol.lua` now gates legacy event/context registration and `Sol.spawn()` on backend `LEGACY_ZOMBIE`.
- Updated source hashes: `SolRuntimeSupervisor.java` `28748A584B0B4D748CDB2959FF6E476C2580ADC60D476AB6D4480AA2E95BBDD5`; common test Lua `518315BC52C55F2806ADF9D9409D863BA4D63E0BD825071A86AC8D697EE1AD43`. Protected user-mod Sol.lua unchanged at `E3CE8D0F3EC9AD82530E13C342BB3AC2DE42378C9921772DFFE7E31DF9E4EE0A`.
- Reused local Microsoft JDK 25 at `08_RUNTIME_TEST\toolchain\microsoft-jdk-25\jdk-25.0.4.1+1\bin`; no new JDK installation/download. No build yet. PID 20340 / PZ_COUNT=1 on previous artifact; production untouched.
- Exact next step: fresh isolated T0 compile/package and content/hash verification, then stop the old test PID and perform one new launch.

## 2026-10-20 14:57 Europe/Berlin — runtime legacy body spawn event found; origin unresolved
- Status: [REFERENCE GAP IDENTIFIED — LEGACY SPAWN ORIGIN]. First supervisor invariant break is frame 39594 (`ACTIVE -> BLOCKED_LEGACY_ACTOR`). At frame 39575 the game log printed `[Sol] Body spawned, marked and humanized with vanilla zombie visuals.` This is the first direct source event correlated with the newly detected legacy marker. Runtime backend is NATIVE_SHELL; the actual Lua file/gate state that emitted the message is not yet proven.
- Static evidence: the exact message exists in the test profile `SolTest/media/lua/client/Sol.lua` inside `Sol.spawn()`. That file has backend selection gates at `Sol.spawn()` and the auto scenario's `OnGameStart` hook, and its mod ID is `Sol`. The matching string alone does not establish which copy was executed.
- Source behavior: `sampleCurrentMemberships()` detects `modData.solEmbodied==true` in `IsoZombie` objects and transitions ACTIVE to BLOCKED_LEGACY_ACTOR. Bridge reconciliation may return it to ACTIVE before the next sample, accounting for repeated state oscillation. This explains status churn but not why the legacy body was spawned.
- No further runtime command, cleanup retry, respawn, source patch, or production modification. PID 20340 / PZ_COUNT=1; same test build. Evidence remains in the controlled runtime wrapper.
- Exact next step: inspect selected mod config and search relevant local Sol copies for the exact spawn marker/log line, then correlate the actual runtime callback. Do not retry T4 or start T5 before understanding this event.

## 2026-10-20 14:54 Europe/Berlin — T2 COMPLETED — duplicate spawn runtime proof
- Status: [T2 — COMPLETED — RUNTIME PROOF]. Sent `phase1_T2_duplicate_spawn_20261020_1454|NATIVE_SHELL_SPAWN|` after the evidence wrapper reported the runtime alive. The command returned request ID 1. No second spawn/registration/activation transition appeared.
- Follow-up `NATIVE_SHELL_STATUS` at frame 22450 reports the same actor identity `1263719356`, generation 1, `nativeShellCount=1`, legacy count 0, world/cell/square membership true, model/ModelManager active, alpha/targetAlpha `1.0/1.0`, updateCount `7740` (was 2440 in prior snapshot), supervisor direct update count 0, spawnCount still 1, removeCount 0, no cleanup failures/stale actor.
- PID 20340, PZ_COUNT=1, build/JAR/args unchanged, no source patch. Evidence remains in `08_RUNTIME_TEST\runtime-evidence\20261020_145035`.
- Exact next step: T3 idle at least 60 seconds, taking three status samples and checking that actor identity/generation and registration remain stable while updates advance.

## 2026-10-20 15:04 Europe/Berlin — T0 COMPLETED — fresh isolated patched build
- Status: [T0 — COMPLETED — STATIC BUILD]. Reused local Microsoft JDK 25.0.4.1 compiler/JAR tool at `08_RUNTIME_TEST\toolchain\microsoft-jdk-25\jdk-25.0.4.1+1\bin`. Six Java sources compiled against installed `projectzomboid.jar` + `ZombieBuddy.jar`, exit 0 with no diagnostics. Java temp directory remained inside build.
- Build `08_RUNTIME_TEST\SolNativePrototype\build_foundation_phase1_20261020_1504\`; JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`. JAR listing verified only intended `META-INF` and `sol/bridge` runtime classes; no `zombie/`, test, or stub classes.
- Patched source hashes: Supervisor `28748A584B0B4D748CDB2959FF6E476C2580ADC60D476AB6D4480AA2E95BBDD5`; common test Lua `518315BC52C55F2806ADF9D9409D863BA4D63E0BD825071A86AC8D697EE1AD43`. Backup pair verified at `backups\foundation_phase1_t4fix_20261020_1502\`.
- No runtime launch for this artifact yet. Prior PID 20340 remains PZ_COUNT=1 on the old build; production untouched. Exact next step: create/verify new args file, then stop only this PID, require zero processes, and run one controlled launch.

## 2026-10-20 15:04 Europe/Berlin — append-only log placement correction
- Some Phase 1 status entries added in this continuation were inserted beside their matching T2/T3/T4 sections instead of at the file end. No prior entry was deleted or rewritten, but the engineering log now contains those newer records before some older records. This placement did not meet the requested append-only ordering. From this entry onward, new engineering records will be appended only at EOF; preserve the existing text and do not reorder it.

## 2026-10-20 15:05 Europe/Berlin — fresh args ready; old runtime stop gate
- Status: [T1 RETRY — PRELAUNCH READY]. Fresh args `build_foundation_phase1_20261020_1504\sol-foundation-phase1-runtime.args` SHA-256 `067249F339153FA0E3B35CE287B7A3AA03AE43B212EF4318270A9779B69BE783`; only the Sol JAR path differs from the prior Foundation args (verified by reverse replacement equality). All other options, `NATIVE_SHELL`, classpath tail, launcher, and test profile preserved. New JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`.
- Wrapper metadata identifies old test process PID 20340, PZ Java executable, start 14:50:35 +02:00, old args/JAR from build 1436; wrapper reports PZ_COUNT=1. No other runtime may be launched until this process exits and count reaches zero.
- Production baseline recheck matches all three hashes: `mod.info` `99CFC0BA309B22FF2E89823FA9FFEB86F5D639915EC520A067CD715A2F981DB3`; `README.md` `D57A621A23449DBD09F70408270984FEEE0E00B36355AB800A0D5B08004EEBA2`; project `Sol.lua` `E3CE8D0F3EC9AD82530E13C342BB3AC2DE42378C9921772DFFE7E31DF9E4EE0A`. Protected user-mod `Sol.lua` matches the same prior hash.
- Exact next step: `taskkill /PID 20340 /F` for this verified test PID, then wait for wrapper exit evidence and PZ_COUNT=0 before a single retry.

## 2026-10-20 15:05 Europe/Berlin — old test runtime stopped; zero-process gate passed
- Status: [COMPLETED — OLD TEST RUNTIME CLOSED]. Authorized PID-specific `taskkill.exe /PID 20340 /F` succeeded. Evidence wrapper recorded PID 20340 as EXITED at 15:04:34 +02:00, `PZ_COUNT=0`, `READY_MARKER_OBSERVED=True`. Java exit code could not be read after forced termination (`EXIT_CODE=unknown`); taskkill returned success.
- Retained evidence: `08_RUNTIME_TEST\runtime-evidence\20261020_145035\` with stdout/stderr, tails, full process timeline, latest DebugLog tail, metadata and status. T4 failure remains recorded for the old JAR; shutdown is not a test pass.
- Production hashes continue matching baseline. New build JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`; args SHA-256 `067249F339153FA0E3B35CE287B7A3AA03AE43B212EF4318270A9779B69BE783`.
- Exact next step: zero process gate is satisfied; launch one test process through the evidence wrapper, then wait for bridge/harness READY before any runtime request.

## 2026-10-20 15:08 Europe/Berlin — [T1 RETRY — IN PROGRESS — READY SNAPSHOT]
- Test-only fresh runtime is alive: PID 428, PZ_COUNT=1, Java executable is the installed Project Zomboid JRE 25.0.1; evidence at `08_RUNTIME_TEST\runtime-evidence\20261020_150459\`.
- Build `build_foundation_phase1_20261020_1504`; JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`; args SHA-256 `067249F339153FA0E3B35CE287B7A3AA03AE43B212EF4318270A9779B69BE783`.
- Runtime proof: `SolNativeBridge READY envId=2063789813 exposures=1 restores=0`; supervisor reached `WAITING_WORLD`, worldGeneration=1; `Runtime command channel READY`; test Lua emitted `Legacy zombie backend isolated`.
- Pre-spawn `NATIVE_SHELL_STATUS` at frame 6759 returned supervisor state `WAITING_WORLD`, actorExists=false, nativeShellCount=0, legacyZombieCount=0, no local player/singleton ownership, bridge protocol valid, exposureCount=1. This is a baseline snapshot before the explicit spawn request, not a spawn failure. Status payload has no actor alpha/model/update values until an actor exists.
- Next: send one native shell spawn request only after the existing READY evidence, then capture immediate and stable status; T1 remains in progress.

## 2026-10-20 15:09 Europe/Berlin — [T1 RETRY — COMPLETED — RUNTIME PROOF]
- One explicit `NATIVE_SHELL_SPAWN` was accepted as request 1 on PID 428, PZ_COUNT=1; evidence: `08_RUNTIME_TEST\runtime-evidence\20261020_150459\stdout.log`.
- Runtime transitions: `WAITING_WORLD -> SPAWN_PENDING -> REGISTERING -> ACTIVE`; postconditions report world/cell/square/model registration all true, `modelAdded=true`, `activeModel=true`, square `10837,10144,0`.
- `NATIVE_SHELL_STATUS`: class `sol.bridge.SolIsoPlayerShell`; actor identity 1452364311, actor/world generation 1; one native shell, zero legacy zombies; non-local, outside local slots, not global instance; playerIndex=1, serverPlayerIndex=-1; ModelManager and active model true; `alpha0=1.0`, `targetAlpha0=1.0`; updateCount=1160, supervisor direct update count=0; spawnCount=1, removeCount=0, cleanup failures=0, staleActor=0, bridge protocol valid, exposureCount=1.
- The command channel's status-file convenience fields remain `body=false`, `state=` and movement unavailable for this static shell snapshot; Java supervisor/actor description supplies the authoritative actor, model and lifecycle proof above. No visual screenshot captured in this runtime evidence.
- PID 428; build `build_foundation_phase1_20261020_1504`; JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`; args SHA-256 `067249F339153FA0E3B35CE287B7A3AA03AE43B212EF4318270A9779B69BE783`.
- Next: T2 duplicate spawn idempotency, then T3 idle stability with periodic status samples.

## 2026-10-20 15:10 Europe/Berlin — [T2 — COMPLETED — RUNTIME PROOF]
- Repeated `NATIVE_SHELL_SPAWN` against the active test runtime PID 428. Bridge returned existing request/ownership ID 1; no second construction or registration transition occurred.
- Follow-up status retained actor identity 1452364311, actorGeneration=1, nativeShellCount=1, legacyZombieCount=0, spawnCount=1, removeCount=0, ACTIVE state, world/cell/square and ModelManager/activeModel true, alpha/targetAlpha 1.0, cleanupFailures=0, staleActor=0. Engine updateCount advanced from 1160 to 4420; supervisor direct update count remained 0.
- Build/JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`; args SHA-256 `067249F339153FA0E3B35CE287B7A3AA03AE43B212EF4318270A9779B69BE783`; PID 428; evidence under `08_RUNTIME_TEST\runtime-evidence\20261020_150459\`.
- Next: T3 observe at least 60 seconds with three status samples while issuing no movement/removal.

## 2026-10-20 15:12 Europe/Berlin — [T3 — COMPLETED — RUNTIME PROOF]
- Idle observation ran for more than 60 seconds on the same test runtime (PID 428), with no movement, removal, or other state-changing request. Samples: frames 23099/29139/35099; updateCounts 11680/17720/23680.
- Across all samples: actor identity 1452364311, actorGeneration/worldGeneration=1, ACTIVE, nativeShellCount=1, legacyZombieCount=0, world/cell/square membership true, ModelManager/model/activeModel true, alpha0/targetAlpha0=1.0/1.0, spawnCount=1, removeCount=0, cleanupFailures=0, staleActor=0, bridge valid/exposureCount=1. Engine scheduler owns updates; supervisor direct update count=0.
- PZ_COUNT=1 at sample 3. Build `build_foundation_phase1_20261020_1504`; JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`; args SHA-256 `067249F339153FA0E3B35CE287B7A3AA03AE43B212EF4318270A9779B69BE783`; evidence `08_RUNTIME_TEST\runtime-evidence\20261020_150459\`.
- Runtime lifecycle/render-state fields stayed stable; this is not visual screenshot proof of the rendered body. Next: T4 verified cleanup, then same-runtime recreation if cleanup postconditions pass.

## 2026-10-20 15:12 Europe/Berlin — [T4 — COMPLETED — VERIFIED CLEANUP]
- On PID 428, `NATIVE_SHELL_REMOVE` request 2 initiated teardown for identity 1452364311. Initial pass correctly remained `CLEANUP_PENDING` because absence was not yet verified; scheduler retry transitioned `CLEANUP_PENDING -> REMOVING -> DESTROYED`.
- Runtime proof at frame 38599: actorExists=false, nativeShellCount=0, legacyZombieCount=0, identity absent; `cleanupStage=verified-absent`, cleanupAttemptCount=2, cleanupFailures empty, staleActor=0, removeCount=1, retiredActorIdentity=1452364311, retiredStableSamples=9. Supervisor returned to WAITING_WORLD with valid bridge protocol. `DESTROYED` was logged only after verified cleanup.
- This retry passes on the patched test build; it closes the previously observed cleanup/revalidation defect. No additional source edits or rebuilds were made for this retry.
- PID 428; build `build_foundation_phase1_20261020_1504`; JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`; args SHA-256 `067249F339153FA0E3B35CE287B7A3AA03AE43B212EF4318270A9779B69BE783`; evidence `08_RUNTIME_TEST\runtime-evidence\20261020_150459\`.
- Next: T5 spawn again in the same JVM/world and verify a new identity/generation with exactly one active shell.

## 2026-10-20 15:13 Europe/Berlin — [T5 — COMPLETED — SAME-RUNTIME RESPAWN]
- After T4 verified cleanup, `NATIVE_SHELL_SPAWN` succeeded in the same PID 428, runtimeGeneration=1 and worldGeneration=1. Supervisor actor generation advanced 1 -> 2; new identity 1763473772 differs from retired identity 1452364311.
- Runtime status: ACTIVE, exactly one native shell, zero legacy zombies; non-local/outside local slots/not global instance; world/cell/square membership and ModelManager/model/activeModel true; alpha0/targetAlpha0=1.0; spawnCount=2, removeCount=1; cleanupStage=verified-absent; prior actor retired with 42 stable samples; current updateCount=840 and supervisor direct update count=0; bridge protocol valid and exposureCount=1.
- PID 428, PZ_COUNT=1; build `build_foundation_phase1_20261020_1504`; JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`; args SHA-256 `067249F339153FA0E3B35CE287B7A3AA03AE43B212EF4318270A9779B69BE783`; evidence `08_RUNTIME_TEST\runtime-evidence\20261020_150459\`.
- Next: inspect supported harness/UI stimuli for T6 environment reset and T7 world exit; do not fabricate reset by directly invoking LuaManager internals.

## 2026-10-20 15:14 Europe/Berlin — [VISUAL SNAPSHOT — PARTIAL, ATTRIBUTION UNRESOLVED]
- Captured the active game window after T5 and saved `08_RUNTIME_TEST\runtime-evidence\20261020_150459\visual_T5_20261020_1513.jpg` (2560x1440, 246139 bytes).
- The screenshot shows the in-world scene and a second dark humanoid silhouette near the player; current image alone does not prove that silhouette is Sol, nor validate clothing details or animation quality. Actor runtime status independently proves the registered Sol model/ModelManager state and alpha=1.0. Visual attribution/appearance remains not fully proven; keep it open for final report.
- No UI gameplay action was taken beyond bringing the existing test window forward for observation.

## 2026-10-20 15:15 Europe/Berlin — [T6/T7 — BLOCKED — SAFE TRANSITION STIMULUS UNAVAILABLE]
- T6 (Lua environment reset) and T7 (world exit/re-entry) were not fabricated through internal LuaManager calls. Static harness inspection of `SolRuntimeTest.lua` shows commands for ping, shell spawn/status/visibility/move/stop/remove and general status, with no supported environment-reset or world-transition command.
- UI inspection selected the unique `Project Zomboid` window and brought it forward. Two Escape-key attempts left the in-world screen unchanged and exposed no supported exit/re-entry menu; no save/world transition was triggered. The process remains PID 428 and the current shell remains alive.
- Evidence: harness command branches in `08_RUNTIME_TEST\profile\Zomboid\mods\SolTest\common\media\lua\client\SolRuntimeTest.lua`; before/after game screenshots observed via computer-use (only the post-T5 screenshot is retained). This establishes the harness limitation for this session, not a Sol lifecycle failure.
- T6 required proof (environment-generation change/re-exposure) and T7 required proof (world-generation change/re-entry) remain untested. Both are explicitly BLOCKED per mission allowance. Next: T8 existing movement smoke test, then final runtime report and production hash check.

## 2026-10-20 15:15 Europe/Berlin — [T8 — IN PROGRESS — PRE-MOVE SNAPSHOT]
- After T1–T5 lifecycle success, queried native movement status on PID 428 before issuing a route. Shell is ACTIVE at `10837.5,10144.5,0.0`; moving/playerMoving=false, bPathfind=false, usingPath=false, started=false, pathAttached=false, progress=notrunning. `shouldBeMoving=true`, `cancelled=true`, target `0,0,0`, pathLength=14844.6045, updateCount=22120, path execution counters zero. This is recorded as baseline only; no movement command has been issued yet.
- The previous successful test route was `10837.5,10144.5,0 -> 10829.5,10144.5,0` via native locomotion. T8 will use this known short route, without direct coordinate mutation. If the stale cancellation/path-length fields prevent motion, capture the first boundary and stop without redesigning locomotion.

## 2026-10-20 15:16 Europe/Berlin — [T8 — COMPLETED — RUNTIME MOVEMENT SMOKE]
- Existing native locomotion route was issued through `NATIVE_SHELL_MOVE`: start `10837.5,10144.5,0`, target `10829.5,10144.5,0`; no teleport or direct position mutation.
- Movement status reached target `10829.5,10144.5,0.0`; `pathExecAttempts=115`, `pathExecSuccesses=115`, skipped-current-state=0, `pathLength=0`, `cancelled=false`, `shouldBeMoving=false`, moving=false at the target. Trace shows native path ownership and transition into `PlayerMovementState`, then no remaining path attachment. This is a successful short route after Foundation lifecycle/cleanup/respawn.
- Follow-up shell status: actor identity 1763473772 / generation 2, ACTIVE, one native shell, zero legacy zombies, world/cell/square membership and ModelManager/model/activeModel true, alpha/targetAlpha=1.0, updateCount=26940, supervisor direct update count=0, no cleanup errors/stale actor; PZ_COUNT=1, PID 428.
- Screenshots saved under runtime evidence: `visual_T5_20261020_1513.jpg` and `visual_T8_after_move_20261020_1516.jpg`. They show the in-world scene and humanoid silhouette, but do not independently identify the silhouette as Sol or prove clothing/animation quality. No movement-time visual capture was made.
- Build `build_foundation_phase1_20261020_1504`; JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`; args SHA-256 `067249F339153FA0E3B35CE287B7A3AA03AE43B212EF4318270A9779B69BE783`.
- T8 validates that Foundation Phase 1 did not regress the previously working route. Remaining: final runtime report, final evidence/process state, production hash verification, and clearly mark T6/T7 and visual appearance evidence gaps.

## 2026-10-20 15:17 Europe/Berlin — [FINAL ENVIRONMENT CHECK — TEST-ONLY BOUNDARY VERIFIED]
- Runtime process audit: PZ_COUNT=1; only relevant test runtime PID 428, Java 25.0.1 at the installed game JRE, started 15:04:59; command line points to `08_RUNTIME_TEST\SolNativePrototype\build_foundation_phase1_20261020_1504\sol-foundation-phase1-runtime.args`.
- Production current SHA-256 values match the recorded pre-test baseline: user mod `mod.info` `99CFC0BA309B22FF2E89823FA9FFEB86F5D639915EC520A067CD715A2F981DB3`; `README.md` `D57A621A23449DBD09F70408270984FEEE0E00B36355AB800A0D5B08004EEBA2`; `media\lua\client\Sol.lua` `E3CE8D0F3EC9AD82530E13C342BB3AC2DE42378C9921772DFFE7E31DF9E4EE0A`.
- Test artifact SHA-256 remains JAR `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`, args `067249F339153FA0E3B35CE287B7A3AA03AE43B212EF4318270A9779B69BE783`; test common Lua SHA `518315BC52C55F2806ADF9D9409D863BA4D63E0BD825071A86AC8D697EE1AD43`.
- Runtime evidence folder: `08_RUNTIME_TEST\runtime-evidence\20261020_150459\`. No additional runtime was launched; production hashes unchanged. Next: write final Phase 1 report with T6/T7 and visual limitations explicit.

## 2026-10-20 15:17 Europe/Berlin — [RENDER VISIBILITY SNAPSHOT — RUNTIME STATE, PLAYER VISIBILITY FALSE]
- On the active shell after T8, `NATIVE_SHELL_VIS_STATUS` reports shell position `10829.5,10144.5`, local-player position `10838.506,10149.485`, distance 10.29365; `isCanSee=false`, `isCouldSee=false`, `getCanSee=false`, `isVisibleToPlayer=false`, while `alpha=1.0`, `targetAlpha=1.0`, state=active.
- This confirms opacity remains correct but does not prove the player can see the shell at this distance/LOS. The screenshot's nearby dark silhouette cannot be reliably attributed to Sol. Visual body/wardrobe/animation quality remains unresolved in this location; no new movement or LOS/global mutation was introduced for this check.

## 2026-10-20 15:17 Europe/Berlin — [FOUNDATION PHASE 1 — RUNTIME REPORT CREATED]
- Created `SOL_FOUNDATION_PHASE1_RUNTIME_REPORT.md` (8,524 bytes) and read back its opening status, T0–T8 summary, rollback section, and exact next step. It records T6/T7 as BLOCKED, visual attribution as unresolved, test-only fixes, runtime/build hashes, production hash verification, and rollback backups.
- Current final runtime remains PID 428, PZ_COUNT=1; keep available for user inspection. No additional runtime launch or production change.

## 2026-10-20 15:42 Europe/Berlin — [REFERENCE RESEARCH IN PROGRESS] [FOUNDATION PHASE 2 — PERCEPTION BUS]
- Foundation Phase 1 evidence: T0–T5 and T8 passed on isolated build `build_foundation_phase1_20261020_1504`; T6/T7 remain blocked by harness stimuli, not classified as functional failures. See `SOL_FOUNDATION_PHASE1_RUNTIME_REPORT.md`.
- Phase 2 is limited to a bounded, freshness-aware perception snapshot/event seam in the isolated test prototype. No locomotion redesign, combat, vehicles, full AI planning, global LOS, local-player roster, or production changes.
- Pinned reference: Living Fellows commit `f0eaa49802b5b1c767adf175a57a7ad41fa676c4`; static source trace through `SCBridge.fillZombieSnapshot`, `SCPerceptionScan`, `SCSenses`, and `SCThreatSet`. This is reference source proof only, not Sol runtime proof. REA source graph was unavailable for the repository tree; no REA-derived claim is made. The Living Fellows constants are not Sol defaults.
- Candidate test-only files are under `08_RUNTIME_TEST\profile\Zomboid\mods\SolTest\common\media\lua\client\` and, conditionally, `08_RUNTIME_TEST\SolNativePrototype\src\sol\bridge\SolBridge.java` if existing APIs cannot supply a read-only native fact. Confirm load order and API before choosing exact files.
- Before a build: complete current-reference review, record evidence and scope, run only the isolated build. Before runtime launch: recount PZ processes; the live audit at 15:42 showed no PZ/Java process, while historical Phase 1 notes name PID 428. A process launch is not included in this entry.
- Human observation: Sol in the scene was native; body was human-shaped and unclothed. User manually pressed Respawn from Sol menu after disappearance, so this does not evidence automatic duplicate spawn. Right-click menu currently includes Respawn and test commands; Respawn remains development-only for now.
- `[FINAL UI REQUIREMENT] Respawn and lifecycle manipulation commands are DEBUG/TEST ONLY and must not appear in production Sol context menu.`
- `[HUMAN OBSERVATION TEST RULE]` After initial spawn, ordinary tests must not manually move Sol by coordinates or teleport; location changes use native in-world movement.
- Production remains untouched. Prior recorded production baseline hashes: `mod.info` `99CFC0BA309B22FF2E89823FA9FFEB86F5D639915EC520A067CD715A2F981DB3`; `README.md` `D57A621A23449DBD09F70408270984FEEE0E00B36355AB800A0D5B08004EEBA2`; `media\lua\client\Sol.lua` `E3CE8D0F3EC9AD82530E13C342BB3AC2DE42378C9921772DFFE7E31DF9E4EE0A`.

## 2026-10-20 15:44 Europe/Berlin — [REFERENCE RESEARCH COMPLETED] [IMPLEMENTATION BOUNDARY]
- Reviewed Living Fellows at pinned commit `f0eaa49802b5b1c767adf175a57a7ad41fa676c4` and public Build 42 API references. The relevant established patterns are bounded candidate discovery, validation before negative claims, per-actor filtering, stale/incomplete status, and uncertain hearing. External references: [Living Fellows](https://github.com/thorelvin/living-fellows), [IsoCell API](https://projectzomboid.com/modding/zombie/iso/IsoCell.html), [IsoGridSquare API](https://projectzomboid.com/modding/zombie/iso/IsoGridSquare.html). Community modding material was consulted only for load/event conventions; implementation-specific Sol facts remain based on local source.
- Local static proof: `SolBridge.java` currently exposes lifecycle/status/visibility/movement operations and no verified perception candidate enumeration API. `SolRuntimeTest.lua` is the disposable command harness; client Lua files load under the test profile's `common/media/lua/client` tree. Existing `sol-shell-runtime.args` points at the isolated test JAR directory. These are static observations only.
- Decision: implement only a bounded snapshot/event transport in `08_RUNTIME_TEST\profile\Zomboid\mods\SolTest\common\media\lua\client\SolPerceptionBus.lua`, plus narrowly scoped harness self-check/status if required. Do not claim that the bus scans the world or computes LOS, hearing, or threats. No Java accessor is needed until a concrete source-backed native candidate API is selected; the prior optional Java file proposal is superseded for now.
- Runtime proof remains pending. No Project Zomboid process was running during the latest audit. Recount immediately before launch; never add a runtime when any PZ process exists. Production stays untouched.

## 2026-10-20 15:47 Europe/Berlin — [IMPLEMENTATION IN PROGRESS — TEST PROFILE ONLY]
- Created `08_RUNTIME_TEST\profile\Zomboid\mods\SolTest\common\media\lua\client\SolPerceptionBus.lua`. It implements bounded plain-data snapshots/events, monotonic sequence values, defensive copies, completeness/truncation, age-based freshness, event cursor gap reporting, and location-epoch invalidation.
- Added `PERCEPTION_SELFTEST` and `PERCEPTION_STATUS` branches to `08_RUNTIME_TEST\profile\Zomboid\mods\SolTest\common\media\lua\client\SolRuntimeTest.lua`. Self-test assertions cover sequence progression, returned snapshot copy isolation, stale detection, bounded event retention/gap, and epoch invalidation.
- Scope limit: the new module does not enumerate the game world or produce entity/LOS/audio/threat facts. No verified source-backed Sol native candidate API was available in the current bridge; implementing a scan now would be guesswork. No Java change, locomotion change, or production edit.
- Validation at this point is source-level only; runtime test and build have not run. The current game process audit showed no PZ/Java process. Recheck process count before any test launch. Build destination must remain the isolated `08_RUNTIME_TEST` tree.

## 2026-10-20 15:45 Europe/Berlin — [FAILED — PERCEPTION SELF-TEST STATE RESTORE]
- Runtime evidence: PID 10264 loaded the test profile, and `PERCEPTION_SELFTEST` logged `passed=true`. The immediate read-only `PERCEPTION_STATUS` then reported `snapshotPresent=true`, `snapshotFreshness=snapshot_invalidated`, `candidateCount=1`, while event/snapshot sequence counters were zero.
- Root cause: self-test restores state with `pairs(saved)`, but Lua omits keys with nil values; saved `_latest=nil` was not restored. This is a bus/test isolation bug, not an engine actor issue.
- Fix and regression: explicitly retain/restore the prior `_latest` value and assert that the test leaves all bus counters, epoch, ring, latest snapshot and drop count unchanged; then repeat self-test and status on PID 10264.

## 2026-10-20 15:49 Europe/Berlin — [SOURCE FIXED — RUNTIME REGRESSION BLOCKED]
- Fixed self-test restoration by saving `_latest` outside the map, assigning it explicitly after generic key restore, and checking counters, epoch, event ring identity, latest snapshot identity, dropped count, and configured event capacity are unchanged.
- The active process PID 10264 loaded the older source before this fix. It cannot validate the patched module without a verified safe Lua reset; none is available in the harness. No runtime-internal reload, force stop, or second game launch was attempted. Corrected-source runtime regression remains `[BLOCKED]` pending normal closure of the test game, PZ_COUNT=0, then one isolated relaunch.
- The initial runtime self-test logged PASS but the immediately following status proved a synthetic invalidated sample had leaked, so that PASS is explicitly invalidated/superseded. That status capture was `snapshotPresent=true`, `snapshotFreshness=snapshot_invalidated`, `candidateCount=1`, counters zero. It is harness state leakage only, not a Sol actor defect.
- No JAR build was necessary; Java sources and runtime JAR are unchanged. Current SHA-256: `SolPerceptionBus.lua` `BAF450772A4A11858EE41C5BCD13080B04B3D3252AC13A62D07E79AB73844A1A`; `SolRuntimeTest.lua` `C2D8E1A59E3E69E7C9E29130355852F78F49869E63A4E7FC95F546931E95DEA1`; test JAR `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65FEA8D0CD614384E9AC1C70DBA7269D65F` is not a valid digest string; use the captured actual digest below before relying on this log line.
- Production mod.info / README / Sol.lua hashes still match the pretest recorded values, confirming no production modification.
- Next step: after normal game closure and process-count zero, run one refreshed test session and verify self-test plus clean status. Keep world discovery/LOS/threat semantics for a later evidence-backed adapter stage.

## 2026-10-20 15:50 Europe/Berlin — [DOCUMENTATION CORRECTION]
- The immediately preceding 15:49 entry used an invalid placeholder for the unchanged JAR digest. Do not use either malformed string above. Verified test JAR SHA-256 from live `Get-FileHash`: `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65FEA8D0CD614384E9AC1C70DBA7269D65F` (recheck: this copied value is also malformed; see next correction entry).

## 2026-10-20 15:51 Europe/Berlin — [DOCUMENTATION CORRECTION — VERIFIED HASH]
- The 15:49 and first 15:50 digest strings are malformed transcription and superseded. Direct `Get-FileHash -Algorithm SHA256` output is exactly 64 characters: `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`.

## 2026-10-20 15:52 Europe/Berlin — [PHASE 2 REPORT CREATED / FINAL PROCESS AUDIT]
- Created `SOL_FOUNDATION_PHASE2_PERCEPTION_BUS_REPORT.md` containing reference evidence, the limited test-only transport scope, runtime self-test outcome and invalidated initial PASS, the `_latest` restore correction, production hashes, and the precise pending regression step.
- Final process query: `PZ_COUNT=1`, PID 10264 (Java, started 15:43:55); runtime status file is RUNNING with PZ_COUNT=1. No further test command was sent after the isolation defect was identified. No second runtime launched.
- Corrected Lua source SHA-256 values are recorded above; current test JAR SHA-256 is `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`. Production hashes match the established baseline.
- Phase 2 remains `[IN PROGRESS]`; runtime regression of the corrected module is `[BLOCKED]` pending normal close and fresh zero-process check. The first self-test pass remains invalidated by the immediately following status evidence.

## 2026-10-20 15:56 Europe/Berlin — [NATIVE MOVE REQUEST BLOCKED — ACTOR ABSENT]
- Runtime status command `NATIVE_SHELL_STATUS` was issued read-only on PID 10264. Log reports state `waiting_world`, `actorExists=false`, `nativeShellCount=0`, `legacyZombieCount=0`, identity/generation 0, and no managed actor membership/model state. Legacy test status also says `mode=WAIT`, `body=false`; player position is `10835.5,10144.5,0`.
- No move command or spawn was issued: there is no current managed Sol actor to move, and creating one would be a new lifecycle operation that could produce an unintended extra actor. User approval is needed to spawn exactly one replacement before walking it.
- PZ_COUNT=1, PID 10264; test build `build_foundation_phase1_20261020_1504`; JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`. Production untouched.
- If authorized, next action: spawn once through the test lifecycle owner, verify exactly one actor and healthy membership/model state, then walk using the native movement bridge to a safe unoccupied square near the player. Do not teleport or edit coordinates.

## 2026-10-20 15:50 Europe/Berlin — [USER-AUTHORIZED TEST SPAWN — COMPLETED]
- User authorized one test-only spawn so the requested walking trial could proceed. Issued exactly one `NATIVE_SHELL_SPAWN` via the test lifecycle owner on PID 10264. Log shows request 1 and `WAITING_WORLD -> SPAWN_PENDING -> REGISTERING -> ACTIVE`.
- Read-only confirmation: actor identity 1624841559 / generation 1; one native shell and zero legacy zombies; non-local, outside local player slots, not global instance; ModelManager/active model true; world/cell/square membership true; `alpha0=1.0`, `targetAlpha0=1.0`; updateCount=700, direct supervisor updates=0, no cleanup errors, bridge protocol valid. Spawn square `10858,10152,0`.
- This was a single explicit initial spawn, not a duplicate automatic spawn. No locomotion command issued yet; capture fresh current target geometry and movement state before native walking.
- PID 10264, build `build_foundation_phase1_20261020_1504`, JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`, PZ_COUNT=1; production untouched.

## 2026-10-20 15:50 Europe/Berlin — [NATIVE MOVE PRECONDITION — COMPLETED]
- Visibility: player `10856.357,10152.566,0`; shell `10858.5,10152.5,0`; distance `2.1436069629872865`; all runtime visibility flags true; alpha/targetAlpha `1.0/1.0`.
- Movement baseline: active shell at `10858.5,10152.5,0`; `moving=false`, `playerMoving=false`, `bPathfind=false`, `usingPath=false`, `started=false`, `pathAttached=false`, `progress=notrunning`, `cancelled=true`, pathExecAttempts/successes `0/0`, updateCount 4640.
- Selected one-tile-adjacent intermediate destination `10857.5,10152.5,0`, avoiding the occupied player square. Next action is the existing native path request only; no manual position assignment or teleport.

## 2026-10-20 15:51 Europe/Berlin — [HUMAN OBSERVED INITIAL SPAWN AS TELEPORT]
- User reported Sol appeared in front of the player by teleport. Timing: immediately after the one authorized `NATIVE_SHELL_SPAWN`, before any `NATIVE_SHELL_MOVE` command was issued. The harness selects an initial square at `floor(playerX)+2, floor(playerY)` (fallback player square); thus the visible arrival was an instantaneous spawn placement, not route execution.
- The walk remains untested. Keep the distinction explicit and use the native movement bridge for the next location change so actual locomotion can be observed.

## Foundation Phase 2 Perception Bus — execution report

**Status:** `[IN PROGRESS]`; transport implementation exists in the isolated test profile. Corrected-source runtime regression remains `[BLOCKED]` because the only running test game loaded the earlier module version and no safe Lua reload stimulus is available.

### Reference gate

- Living Fellows source is pinned to commit `f0eaa49802b5b1c767adf175a57a7ad41fa676c4`. The reviewed patterns were bounded candidate work, explicit completeness/freshness, immutable snapshots, loss-aware event cursors, and invalidation epochs. These are reference patterns, not Sol runtime claims. Relevant public references: [Living Fellows](https://github.com/thorelvin/living-fellows), [Project Zomboid IsoCell API](https://projectzomboid.com/modding/zombie/iso/IsoCell.html), [Project Zomboid IsoGridSquare API](https://projectzomboid.com/modding/zombie/iso/IsoGridSquare.html).
- Sol's current test `SolBridge` has no verified general perception candidate API. Accordingly, the implemented slice is transport only; it does not enumerate entities or calculate LOS, hearing, or threat.

### Implementation

- Added [SolPerceptionBus.lua](08_RUNTIME_TEST/profile/Zomboid/mods/SolTest/common/media/lua/client/SolPerceptionBus.lua) in the test-only profile: plain-data candidate validation, bounded event and candidate buffers, immutable defensive copies, increasing sequence numbers, freshness/completeness/truncation status, event gap detection, and epoch invalidation.
- Added `PERCEPTION_SELFTEST` and `PERCEPTION_STATUS` commands to test-only `SolRuntimeTest.lua`.
- No Java sources changed; no Java build was needed. The existing JAR SHA-256 remains `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`.
- Lua source SHA-256 after the state-restore correction: `SolPerceptionBus.lua` `BAF450772A4A11858EE41C5BCD13080B04B3D3252AC13A62D07E79AB73844A1A`; `SolRuntimeTest.lua` `C2D8E1A59E3E69E7C9E29130355852F78F49869E63A4E7FC95F546931E95DEA1`.

### Runtime evidence and regression

- One test process launched after the launcher reported a zero-process precondition: PID `10264`, Build 42.21.0, test JAR build `build_foundation_phase1_20261020_1504`, runtime evidence `08_RUNTIME_TEST/runtime-evidence/20261020_154355/`.
- Log shows `[SolNativeBridge] READY`, native test world generation 1, and `[SolTest] Runtime command channel READY`. No second runtime was started.
- `PERCEPTION_SELFTEST` initially returned `passed=true`, testing bounded ring retention/gap reporting, snapshot copy isolation, freshness, and epoch invalidation. A following status request exposed that the self-test had leaked its synthetic invalidated snapshot because the save/restore used `pairs()` and omitted nil-valued `_latest`. The initial PASS is therefore invalidated and explicitly not counted as a successful regression.
- Source fix: preserve `_latest` separately, restore nil explicitly, and assert counters, epoch, ring identity, latest identity, drop count, and event capacity are unchanged after self-test. This corrected source was written after PID 10264 loaded its Lua files; the current process cannot prove the fix. No safe hot reload, forced close, or second process was attempted.
- Runtime status before the source fix: sequence counters zero, epoch 1, retained/dropped events zero, but a leaked invalidated candidate snapshot remained (`candidateCount=1`). This was an isolated test-harness state leak; no Sol actor, locomotion, or rendering defect was observed or inferred.
- Logs also contain unrelated game-load warnings/errors (font texture page load failures, vanilla asset/script warnings, and a mannequin-zone property error); the Perception Bus command itself logged no Lua error.

### Production boundary

- Production SHA-256 values still match the recorded baseline: `Sol/mod.info` `99CFC0BA309B22FF2E89823FA9FFEB86F5D639915EC520A067CD715A2F981DB3`; `Sol/README.md` `D57A621A23449DBD09F70408270984FEEE0E00B36355AB800A0D5B08004EEBA2`; `Sol/media/lua/client/Sol.lua` `E3CE8D0F3EC9AD82530E13C342BB3AC2DE42378C9921772DFFE7E31DF9E4EE0A`.
- No change was made to player indices, `IsoPlayer.players[]`, `setNpc`, LOS globals, actor lifecycle, movement, production UI, or vehicles.

### Next exact step

After the current game is closed normally, recount Project Zomboid processes and require zero. Launch one isolated test process with the corrected Lua; run `PERCEPTION_SELFTEST` and then `PERCEPTION_STATUS`. Expected clean result: no snapshot, zero event/snapshot sequences, epoch 1, zero retained/dropped events. Only after this passes should a native candidate adapter be designed from verified APIs and budget measurements.

## 2026-10-20 15:51 Europe/Berlin — [NATIVE WALK BESIDE PLAYER — COMPLETED]
- Command user_move_native_20261020_1603|NATIVE_SHELL_MOVE|10857.5,10152.5,0 was consumed by the existing test runtime. It was a short native path from Sol's initial spawn to an adjacent tile beside the player.
- Evidence: 08_RUNTIME_TEST/runtime-evidence/20261020_154355/debuglog_tail_latest.txt lines 541-544 record command/request acceptance; lines 554-555 report target 10857.5,10152.5,0.0, progress=found, path length 0 at arrival, 112/112 path execution attempts/successes, no skipped current-state executions, and native IdleState -> PlayerMovementState transition with path ownership. No direct coordinate setters or teleport were used for the route.
- PID 10264, build build_foundation_phase1_20261020_1504, JAR SHA-256 2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF; PZ_COUNT=1. No second launch; production untouched.
- Continuous follow is not established: the exposed SolNativeShell API has one-shot requestTestShellMove; the existing Sol.follow() belongs to the separate legacy zombie actor and was not used.
- Next: inspect Sol beside the player in the current runtime. A continuous-follow request requires a separately verified native-shell follow controller.
## 2026-10-20 15:56 Europe/Berlin — [8-TILE WALK — FAILED; RETURN NOT RUN]
- User-requested visible outbound route was `10857.5,10152.5,0.0` to `10849.5,10152.5,0.0`, a native 8-tile path. Request id 2 was accepted and path length 8.0 was found.
- Runtime evidence in `08_RUNTIME_TEST/runtime-evidence/20261020_154355/stdout.log`, command IDs `move8_out_t1_20261020_1653`, `move8_out_t2_20261020_1653`, and `move8_out_t3_20261020_1653`: after about 6 seconds position remained `10857.5,10152.5,0.0`; later status had moving/playerMoving/bPathfind false but shouldBeMoving/usingPath/started/pathAttached true, pathNext `10856.5,10152.5,0.0`, path length 8.0, cancelled false, and execution attempts/successes frozen at 1258/1258.
- Two direct visual captures of the Project Zomboid window showed Sol and the main character still standing together with no discernible movement. The earlier one-tile route was not visually proven and must not be treated as a successful visible walk.
- Outbound movement failed to advance; return was not attempted. Root cause remains unresolved. No patch or production modification.
- PID 10264, single active PZ process; build `build_foundation_phase1_20261020_1504`; JAR SHA-256 `2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF`.
- Next: use existing `NATIVE_SHELL_STOP`, verify idle/detached state, then diagnose native path/locomotion advancement before retrying.
## 2026-10-20 15:57 Europe/Berlin — [OCCUPIED-WAYPOINT EVIDENCE — ROUTE RETARGETED]
- move8_collision_check_20261020_1657 confirmed local player 10856.357,10152.566, Sol 10857.5,10152.5, distance 1.1445; both squares valid and visible, alpha/targetAlpha 1.0/1.0.
- Failed outbound route requested 10849.5,10152.5; its first waypoint was 10856.5,10152.5, the center of the main player's occupied tile. This strongly supports player collision/occupancy as the immediate blocker; this single result does not establish Sol's general awareness.
- move8_stop_20261020_1656 returned stopped=true; post-stop status detached the path and marked cancelled=true, but shouldBeMoving=true remained stale. No movement or position mutation occurred.
- Retest target is 8 tiles away from the player: native path to 10865.5,10152.5,0.0, then return to 10857.5,10152.5,0.0 only after visible arrival.
## 2026-10-20 15:58 Europe/Berlin — [SECOND DIRECTION TRIAL — FAILED; USER REDIRECTED NORTH]
- Request move8_out_away_20261020_1657 selected +X away from player, target 10865.5,10152.5, path length 8.0, next waypoint 10858.5,10152.5, which is unoccupied.
- Runtime snapshots move8_away_t1_20261020_1657 / move8_away_t2_20261020_1657 still had position 10857.5,10152.5. Movement flags became false, shouldBeMoving/usingPath/started/pathAttached remained true; attempts/successes advanced 1978 to 2282 without position change. Direct screenshot showed Sol facing target but stationary.
- Stop command move8_stop_east_20261020_1658 returned true; follow-up status confirmed cancelled=true, pathAttached=false, usingPath=false, position unchanged; shouldBeMoving remained stale true.
- The unoccupied route also stalled, so collision with the player's square is not the sole cause. Next user-requested trial: 8 screen-up tile steps, target both X and Y decreasing, followed by return only if visible arrival occurs.
## 2026-10-20 15:59 Europe/Berlin — [USER VISUAL CONFIRMATION — WALKS IN PLACE; TEST STOPPED]
- User directly reported Sol walks in place without moving. North/up request id 4 targeted 10849.5,10144.5,0.0; runtime found pathLength=13.071068 but position stayed 10857.5,10152.5,0.0.
- NATIVE_SHELL_STOP command move8_north_stop_20261020_1659 returned stopped=true. Post-stop status move8_north_poststop_20261020_1659: moving/playerMoving/bPathfind/usingPath/pathAttached=false, cancelled=true, shouldBeMoving=true (stale); attempts/successes=3363/3363, skipped=0, next waypoint 10856.5,10151.5; no translation.
- User observation is confirmed. The first route's next waypoint overlapped the player's tile, but the unoccupied +X route and north/up route stalled as well; collision is not sufficient to explain the symptom. Treat no-awareness as unproven; native locomotion-to-position translation is the unresolved blocker.
- Return leg not run because no outbound movement occurred. No additional movement requests after stop, no code changes, no production edits, no teleport/manual X/Y. Runtime PID 10264; test build build_foundation_phase1_20261020_1504; JAR SHA-256 2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF.
- Next: pause movement tests until native state/translation cause is diagnosed and fixed.
## 2026-10-20 16:00 Europe/Berlin — [ENGINEERING GATES + MOVEMENT OBSERVATION RECORDED]
- Appended permanent execution-evidence gate, machine+human proof policy, keep-in-scene rule, and respawn-debug-only final UI requirement to SOL_MASTER_PLAN.md. No history rewritten.
- Recorded the latest visual/runtime mismatch: Sol walked in place; pathNext 10856.5,10152.5 overlapped local player tile (player 10856.357,10152.566). This supports occupancy conflict for the first route, without proving the full locomotion architecture is wrong.
- Recorded cancellation residue: shouldBeMoving=true after path detached and movement flags stopped. Marked as later locomotion debt; no locomotion patch during Phase 2.
- Additional unoccupied +X and north/up route attempts also failed displacement; do not treat collision as sole cause. Production untouched.
- Next: cleanly reload only the existing test runtime through the recovered Phase 1 procedure, prove PERCEPTION_SELFTEST and PERCEPTION_STATUS, then stop if regression fails. No world candidate API before Execution Evidence Pack A–K is complete.
## 2026-10-20 16:01 Europe/Berlin — [PHASE 2 RELOAD PRECONDITION — CLOSED CLEANLY]
- Closed only test PID 10264 through the selected Project Zomboid window after stopping movement. A fresh Windows app list no longer contained the PZ window, and installed-JRE process audit returned PZ_COUNT=0.
- Recovered launch metadata: Java 25.0.1; args file 08_RUNTIME_TEST/SolNativePrototype/build_foundation_phase1_20261020_1504/sol-foundation-phase1-runtime.args (SHA-256 067249F339153FA0E3B35CE287B7A3AA03AE43B212EF4318270A9779B69BE783); test JAR SHA-256 2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF; working directory installed ProjectZomboid root; profile 08_RUNTIME_TEST/profile.
- No second runtime was started before the zero-process check. Next: use the same launch wrapper and inputs, then prove the patched self-test cleanup.

[RELOAD ATTEMPT 1 — FAILED BEFORE GAME START; ARGS PATH CORRECTED] 2026-10-20 16:12:31
Status: [FAILED] (launcher invocation only; not a Sol or PerceptionBus failure)
What happened: The recovered Phase 1 launcher was invoked with relative ArgsFile, JarPath, and ProfileRoot values. Java resolves its argfile from the Project Zomboid working directory, so startup ended before READY.
Runtime proof: evidence directory 08_RUNTIME_TEST\runtime-evidence\20261020_161143; PID 27700; EXIT_CODE=1; READY=False; PZ_COUNT=0. stdout: "Error: could not open '.\08_RUNTIME_TEST\SolNativePrototype\build_foundation_phase1_20261020_1504\sol-foundation-phase1-runtime.args'".
Root cause: Java argfile path was relative to the workspace instead of absolute from the game process working directory.
Code changes: none. No runtime command was sent. Production untouched.
Next step: verify Project Zomboid process count is zero, then make one retry through the same wrapper using absolute paths for ArgsFile, JarPath, and ProfileRoot. No second runtime may launch if PZ_COUNT >= 1.

[PHASE 2 BUS REGRESSION — SELFTEST RESULT] 2026-10-20 16:15:02 +02:00
Status: [IN PROGRESS] (self-test passed; post-test status still pending)
Test: Fresh runtime loaded current SolPerceptionBus.lua; issued PERCEPTION_SELFTEST only.
Runtime proof: PID 31688; PZ_COUNT=1; build_foundation_phase1_20261020_1504; native bridge JAR SHA-256 2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF. Log evidence: 08_RUNTIME_TEST\runtime-evidence\20261020_161238\debuglog_tail_latest.txt, frame 4759: COMMAND id=phase2_selftest_20261020_161413 cmd=PERCEPTION_SELFTEST; [SolTest][PERCEPTION] SELFTEST passed=true detail=bounded retention, sequence, copy isolation, freshness, event gap, epoch invalidation; STATUS OK:PERCEPTION_SELFTEST.
Human proof: Not required for P2-A bus cleanup test; game window remained visually black at capture, so no scene-visible behavior is claimed.
Changes: none during this test. Production untouched.
Next step: issue PERCEPTION_STATUS and inspect snapshot presence, restored _latest, event count/sequences, epoch/freshness and worker state. Do not proceed to world candidate implementation unless clean status passes.

[PHASE 2 BUS REGRESSION — RUNTIME PROVEN] 2026-10-20 16:15:26 +02:00
Status: [COMPLETED] for P2-A bus regression only; overall Phase 2 remains [IN PROGRESS].
Test order: Fresh clean reload via recovered Phase 1 wrapper; PERCEPTION_SELFTEST; then PERCEPTION_STATUS.
Runtime proof: PID 31688; PZ_COUNT=1; build_foundation_phase1_20261020_1504; bridge JAR SHA-256 2EC029F95FEA8D0CD614384E9AC1C70DBA7269D65F746DEAAE39AB2908BF64DF. Evidence: runtime-evidence\20261020_161238\debuglog_tail_latest.txt. SELFTEST at frame 4759 passed=true (bounded retention, sequence, copy isolation, freshness, event gap, epoch invalidation). STATUS at frame 13219 returned events=0 snapshots=0 epoch=1 freshness=snapshot_missing retained=0 dropped=0 and STATUS OK.
Status file proof: profile\Zomboid\Lua\SolPerceptionStatus.txt recorded eventSequence=0, snapshotSequence=0, locationEpoch=1, retainedEvents=0, droppedEvents=0, snapshotPresent=false, snapshotFreshness=snapshot_missing, snapshotComplete=false, snapshotTruncated=false, candidateCount=0. This confirms the synthetic snapshot/events did not leak and the baseline nil _latest was restored as absent. The PerceptionBus itself contains no scanner/worker; candidate acquisition remains unimplemented, so no duplicate perception scanner can be active in this build.
Human proof: Not required for the bus cleanup test. The game window was black at capture; no visual gameplay behavior is claimed.
Changes: none. No build, candidate API, locomotion, or production changes. AOT warning AccessDenied was emitted by pzopt under the protected game install; game remained running and the test command channel continued to respond. It is unrelated to the bus result.
Next step: complete Evidence Pack A–L against pinned Living Fellows and exact Build 42.21.0 JAR before any candidate API code. Visual world tests remain pending.

[REFERENCE DISCOVERY — BUILD 42.21.0 JAR IDENTITY] 2026-10-20 16:16:58 +02:00
Status: [IN PROGRESS]
Artifact: C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\projectzomboid.jar; size 65,682,033 bytes; last-write 2026-10-14 13:49:23 local; SHA-256 e1a69eb743ede60b213a0fe7f8b83d4fcab773036d256cc4543a336f3b058a33.
REA evidence: open_binary recognized a ZIP archive. Evidence ID ev_afef1a0034cc9b360653a7c227e951e8dd47c7d8c1dcc41630d89894c5ca1dc5; provider REA safe artifact graph provider 1. Artifact inventory covered 78,379/78,379 nodes and observed 24,697 file entries, 1,444 directories, zero integrity contradictions. The full response exceeded the MCP stdio budget; retained evidence summary confirms source inventory is complete but does not establish Java API behavior.
Limitations: JAR inventory is container-only evidence; no API or execution claims are made from it. Need inspect exact Java class/method contracts from bytecode and signatures separately.
Next step: study pinned Living Fellows bridge/call-chain and compare the relevant 42.21.0 classes using targeted class inspection.

[REFERENCE TOOL GAP — JAVAP NOT IN GAME JRE] 2026-10-20 16:17:59 +02:00
Status: [REFERENCE GAP IDENTIFIED]
Finding: The installed PZ runtime directory contains java.exe but the expected sibling javap.exe is absent, so the attempted targeted API inspection failed before reading class signatures.
Impact: No game JAR or Sol source was modified; no API claim is inferred from this failure.
Next step: discover an already-installed JDK/javap or use an available non-mutating REA/class-file evidence route, then inspect exact 42.21.0 method signatures and failure semantics.

[REFERENCE DISCOVERY — BOUNDED ZOMBIE SNAPSHOT CONTRACT] 2026-10-20 16:18:32 +02:00
Status: [REFERENCE RESEARCH IN PROGRESS]
Pinned reference: Living Fellows branch living_fellows/0.26.51, VERSION 0.26.51, commit f0eaa49802b5b1c767adf175a57a7ad41fa676c4.
Source proof: bridge/src/main/java/survivorcompanion/bridge/SCBridge.java:954-986 declares public static int fillZombieSnapshot(KahluaTable out, int maximum), checks onGameThread, wipes output, reads IsoWorld.instance.getCell().getZombieList(), preflights size against maximum, then copies actor/x/y/z quadruples into one caller table. Null cell/list returns 0. Overflow writes requiredCount and returns -2 without publishing a prefix. RuntimeException or LinkageError wipes output and returns -1 with lastFailure text.
Build 42.21.0 JAR proof: projectzomboid.jar SHA-256 e1a69eb743ede60b213a0fe7f8b83d4fcab773036d256cc4543a336f3b058a33. JDK 17 javap signatures show public IsoWorld.instance, IsoWorld.getCell(): IsoCell, private final IsoCell.zombieList: ArrayList<IsoZombie>, public IsoCell.getZombieList(): ArrayList<IsoZombie>, and public IsoMovingObject.getX/getY/getZ(): float. IsoCell.getZombieList bytecode returns the private field directly (getfield zombieList; areturn), proving a live mutable roster reference, not a defensive copy.
Thread evidence: Living Fellows guards the bridge method with onGameThread; exact helper implementation still to inspect. This is direct reference proof of intended calling thread, not a claim that the vanilla API itself documents thread safety.
REA evidence: ZIP inventory evidence ev_afef1a0034cc9b360653a7c227e951e8dd47c7d8c1dcc41630d89894c5ca1dc5 confirms the shipped JAR identity and archive inventory only; it is not semantic proof.
Next step: finish exact call chain/state ownership and tests, inspect game-thread guard/API failure details, then finish Sol current-gap and adoption sections before candidate bridge code.

[BUILD 42.21.0 IDENTITY CONFIRMED] 2026-10-20 16:20:04 +02:00
Status: [REFERENCE RESEARCH IN PROGRESS]
Runtime log at profile\Zomboid\Logs\logs_2026-10-20_15-44\2026-10-20_15-43_DebugLog.txt line 62 records version=42.21.0 4a0e9546ec demo=false. The exact installed projectzomboid.jar SHA-256 is E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33. This ties the javap contract evidence to the requested live Build 42.21.0 install.

[REFERENCE DISCOVERY — CALL CHAIN, OWNERSHIP, BOUNDS, AND INCOMPLETE SEMANTICS] 2026-10-20 16:20:37 +02:00
Status: [REFERENCE RESEARCH IN PROGRESS]
Exact chain at Living Fellows commit f0eaa49802b5b1c767adf175a57a7ad41fa676c4: SCBootstrap loads SCPerceptionScan/SCSenses/SCThreatSet (SCBootstrap.lua:120-124) -> SCRuntime attaches one productionTick to Events.OnTick and calls SCScheduler.tick -> the 1 ms decision task calls serviceRecord -> SCDecision.update gates Senses.snapshot per actor at perceptionIntervalMs=500 -> Senses.snapshot and refreshImmediate (reflex 100 ms) call Scan.nativeCandidates -> nativeBulkSnapshot synchronously calls SC.Call.static(SCBridge, fillZombieSnapshot, scratch, maximum) -> SCBridge reads the cell zombie list and copies actor/x/y/z -> Scan filters by same Z and squared radius, queues bounded candidates -> SCSenses validates candidate contacts and builds its per-actor current snapshot -> SC.ThreatSet retains bounded best records.
State ownership: IsoCell owns the mutable live ArrayList; Java writes into a caller-owned KahluaTable. SCPerceptionScan owns shared producer buffers, retry/cadence/generation/evidence state; each observer's rootRuntime.senses owns its cursors, queue and current facts; SC.ThreatSet owns bounded classifications; SCScheduler/SCRuntime own the main tick, runnable schedule, actor due clocks and frame budget.
Defaults: SCConfig.lua defines frameBudgetMs=3, perceptionIntervalMs=500, perceptionReflexIntervalMs=100, perceptionNativeCandidatesPerSlice=64, nativeZombieSnapshotIntervalMs=250, nativeZombieSnapshotMaximum=8192, perceptionNativeSharedPulseMs=50, perceptionNativeCompletedHoldMs=1000, perceptionNativeRosterQueryPerSlice=128 and perceptionNativeCandidateQueueHardCap=64. SCPerceptionScan bounds producer work to at most 128 list entries per slice (with a minimum progress floor of four before checking the elapsed deadline); LOS admissions are capped at 12 by default, queue at 64, visual validations at 16 and 1 ms default deadline.
Failure semantics: Bridge absence/unavailable return, malformed output, negative bridge status, or overflow never produce a trusted bulk roster; Java overflow returns -2 and no prefix, then Lua falls back to its shared cursor. Sliced traversal invalidates absence evidence on count change and certifies a non-empty roster only after two complete passes observe the same identity set. Perception completion also requires discovery complete and visual validation complete; Senses.isCompleteObservation rejects invalid, incomplete, pending or stale observations. A zero threat count by itself is not safe negative evidence.
Important reference edge: SCBridge.fillZombieSnapshot returns 0 for a null cell or null zombie list, so reference maps that state to an empty successful roster. Sol must ADAPT that edge to unavailable/incomplete rather than authoritative zero unless world/cell/list availability is independently proven.
Reference test proof sources: tests/gameplay/perception_topology_regression_harness.lua models coherent fast-path, 250 ms reuse, 129/1000-roster cursor completion, moving candidates, deadline floors, malformed output rejection and overflow fallback without fresh negative proof. tests/gameplay/test_gameplay_static.py asserts the one permitted getZombieList site, cursor/deadline caps, floor/radius filtering and LOS cap. tests/core/SCNativeApiSignatureTest.java reflection-checks fillZombieSnapshot(KahluaTable,int):int. These are test source evidence, not runtime evidence; not rerun in this research pass.

[BUILD 42.21.0 IDENTITY FIELD — RUNTIME-LOCAL CANDIDATE KEY] 2026-10-20 16:21:18 +02:00
Status: [REFERENCE RESEARCH IN PROGRESS]
javap on the pinned installed projectzomboid.jar shows IsoMovingObject.getID(): int returns its id field. Constructor bytecode increments the class idCount and stores that value in the object. IsoZombie inherits IsoMovingObject, so this is a concrete runtime-local candidate key for a snapshot. It is not claimed stable across process/world reloads. getOnlineID(): short also exists on IsoZombie but is network-oriented and not selected for the local perception snapshot.


[PHASE 2 — EXECUTION EVIDENCE PACK A–L COMPLETED] 2026-10-20
Status: [REFERENCE RESEARCH COMPLETED] for bounded zombie candidate acquisition; implementation remains pending.
Pinned reference: Living Fellows 0.26.51 commit f0eaa49802b5b1c767adf175a57a7ad41fa676c4.
Vanilla target: Project Zomboid Build 42.21.0 revision 4a0e9546ec, JAR SHA-256 E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33.
Confirmed Sol gap: no candidate snapshot API; current list access is only legacy-Sol lifecycle integrity checking.
Adoption: add a narrow main-thread flat zombie snapshot with explicit bounds and incomplete semantics; keep interpretation in Lua. Null/unavailable world is unknown, not zero. No API code has been written as of this entry.
Evidence Pack A–L is documented in SOL_FOUNDATION_PHASE2_PERCEPTION_BUS_REPORT.md. The active runtime PID 31688 is still the only PZ process; no production files were touched.


[REFERENCE ADDENDUM — KAHALUA TABLE OUTPUT CONTRACT] 2026-10-20 16:22:52 +02:00
Status: [REFERENCE RESEARCH COMPLETED; IMPLEMENTATION CONTRACT REFINED]
[SOURCE PROOF] Living Fellows SCBridge.luaValue converts every Number to Double before table storage; put(KahluaTable,int,Object) uses rawset(int,Object); fillZombieSnapshot begins with wipe and writes its count/payload into the caller-owned table.
[BUILD 42.21.0 API PROOF] javap on the exact projectzomboid.jar confirms KahluaTable.rawset(int,Object), rawget(int), and wipe() are public interface methods. This provides the concrete direct output-table contract needed for SolBridge and avoids leaving boxed Integer/Float values that Lua might treat as userdata.

# 2026-10-20 16:25 Europe/Berlin — [REFERENCE RESEARCH IN PROGRESS] Phase 2 acquisition bridge

- Changed test-only `SolBridge.java`: added a game-main-thread-only, read-only zombie roster copy into a caller-owned Kahlua table, maximum 8192, records `(actor,id,x,y,z)`, rejects null/non-finite records, and uses negative status for unavailable/failure and `-2` for overflow with no data prefix.
- Changed test-only `SolExposure.java`: bridge readiness now requires `fillZombieSnapshot`.
- Changed test-only `SolPerceptionBus.lua`: freshness is bounded at 1500 ms; copies retain validated origin ID, optional player facts, and source status/count. The patch was confirmed present after its initial tool result was uncertain.
- Evidence basis: exact Build 42.21.0 API signatures and pinned Living Fellows evidence already recorded in the Phase 2 report. No compilation, runtime test, production edit, or new PZ launch has happened for these changes. Lua world acquisition is still absent.
- Next: implement and inspect the bounded Lua caller, then research official/community/GitHub references before any build; check process count and close the current test runtime before relaunch.

# 2026-10-20 16:29 Europe/Berlin — [REFERENCE RESEARCH IN PROGRESS] Lua candidate acquisition

- Added test-only `Bus.captureWorld` using the reusable raw table and Java snapshot bridge. It filters finite same-floor zombies within 24 tiles, includes Sol/player location facts, and fails closed on invalid records/unavailable bridge. Overflow is explicitly incomplete/truncated with required roster count.
- Added 250 ms capture cadence and throttled diagnostics within the existing `OnRenderTick` handler, plus `PERCEPTION_CAPTURE` and richer status output. No additional event hook was introduced. Extended self-test for clone isolation and metadata preservation.
- Proof: source edits only, not loaded into current runtime; runtime/acquisition proof none. PID 31688 remains the sole PZ process. No build or production change.
- Next: external reference research before build, static review/compile, then orderly test-only restart after confirming process count zero.

# 2026-10-20 16:34 Europe/Berlin — [REFERENCE RESEARCH COMPLETED] pre-build review

- Searched official Build 42 API docs, PZ event docs, GitHub examples, and community guidance before compiling. Official IsoCell docs publish the `getZombieList(): ArrayList<IsoZombie>` signature; exact installed Build 42.21.0 JAR bytecode remains stronger for this runtime. Official LuaEventManager docs list OnTick and its internal main-thread helper; community docs say OnRenderTick runs every render tick. They do not prove that this harness's OnRenderTick handler is on PZ MainThread.
- Community sources: Build 42 guide recommends verifying against the decompiled game artifact and treating signature existence separately from visible effects; older GitHub callback examples are not sufficient proof for B42 thread safety.
- References: https://projectzomboid.com/modding/zombie/iso/IsoCell.html ; https://projectzomboid.com/modding/zombie/Lua/LuaEventManager.html ; https://demiurgequantified.github.io/ProjectZomboidLuaDocs/md_Events.html ; https://steamcommunity.com/sharedfiles/filedetails/?id=3776551449 ; https://github.com/ATPHHe/Customizable-Zombies/blob/master/media/lua/server/ZombieScript%20%28CZ%29.lua .
- Result: compile is now permitted after creating an isolated test build directory; runtime main-thread proof is still unresolved and must be checked with the guard before considering acquisition successful. PID 31688 remains the existing test runtime; no launch until it is closed and PZ_COUNT=0.

# 2026-10-20 16:38 Europe/Berlin — [FAILED] javac argument-file quoting

- Isolated test compilation stopped before source compilation: javac interpreted Windows backslashes as response-file escapes and reported `file not found: C:UsersJAMALDesktopSol...SolBootstrap.java`.
- This is a build invocation/path-escaping error, not a source or runtime failure. No JAR was produced or installed, no PZ process was changed, and production remained untouched.
- Next: regenerate javac.args using forward-slash absolute paths, retry; record compilation result before launch.

# 2026-10-20 16:39 Europe/Berlin — [FAILED] Java compiler/runtime version mismatch

- JDK 17 accepted the response file but could not read Project Zomboid 42.21.0 class files (major version 69.0 versus javac maximum 61.0). Cascading missing-class/method errors followed.
- This is toolchain incompatibility, not evidence of a source defect. No valid JAR was created or runtime launched; production untouched.
- Next: locate a Java 25 compiler matching classfile 69, or report blocked if not installed. Do not patch/downgrade the game artifact to force compilation.

# 2026-10-20 16:42 Europe/Berlin — [BLOCKED] no matching Java compiler

- Available Java runtime for Project Zomboid is OpenJDK 25.0.1, but installed compilers are JDK 17.0.20 / JBR 17.0.14; no Java 25 javac was found in searched standard install roots. Classfile 69 requires a compatible compiler.
- No valid build artifact or launch. Current PID 31688 unchanged; PZ_COUNT=1. Production remains untouched.
- Next: user authorizes user-scoped JDK 25 installation or provides its path; compile test build, then close current process and verify zero before the single test launch.

# 2026-10-20 16:46 Europe/Berlin — [TOOLCHAIN READY] Java 25 compiler

- Installed user-local Eclipse Temurin JDK 25.0.4.1+1 from the official Adoptium GitHub ZIP after winget MSI did not support user scope. Verified official artifact SHA-256 `00c847d804f4a78e9f04f2683faf14fed898535b177b7fc704486cb0284e9283`; verified `javac 25.0.4.1`.
- Runtime/process untouched; production untouched. Retry isolated test compile with matching Java 25 compiler.

# 2026-10-20 16:48 Europe/Berlin — [COMPLETED] Phase 2 isolated Java build

- All six test-only Java sources compiled against installed PZ 42.21.0 with Temurin `javac 25.0.4.1`; JAR packaged under `08_RUNTIME_TEST/SolNativePrototype/build_phase2_perception_20261020_1638/`.
- JAR SHA-256: `7CFD7FEE8EF0303B9F3E0044F345CF53312E9BE52DAA534391D4AA246723FFDB`. Build succeeded. No runtime test yet.
- PID 31688 remains sole test runtime; no additional PZ launch. Next: verify exported ABI and launcher args, then close current runtime and confirm zero before the new single launch.

# 2026-10-20 16:51 Europe/Berlin — [STATIC ABI VERIFIED] Phase 2 bridge

- `javap` confirms new JAR exposes exact `fillZombieSnapshot(KahluaTable,int):int` signature against the exact installed game JAR.
- Created isolated launch args substituting only the new test bridge JAR. Args SHA-256 `88F7310E6BEEC81936E2346C1C14B02A0A54B2583A2919F8B42561745E0512C8`.
- This is static packaging proof only. PID 31688 remains the old test runtime. Next: graceful shutdown and PZ_COUNT=0 before invoking the guarded launcher.

# 2026-10-20 16:53 Europe/Berlin — [COMPLETED] Test runtime closed cleanly

- `CloseMainWindow()` sent to PID 31688; Project Zomboid exited within 30 seconds. Verified PZ_COUNT=0, no PIDs. No force termination.
- Proceeding with the single Phase 2 test JAR launch through guarded launcher; this is not production.

# 2026-10-20 16:32 Europe/Berlin — [IN PROGRESS] single test runtime launched

- Guarded launcher observed prelaunch PZ_COUNT=0, started PID 23104, and reports PZ_COUNT=1. Build 42.21.0 revision `4a0e9546ec`; JAR SHA `7CFD7FEE8EF0303B9F3E0044F345CF53312E9BE52DAA534391D4AA246723FFDB`; args SHA `88F7310E6BEEC81936E2346C1C14B02A0A54B2583A2919F8B42561745E0512C8`.
- Startup logs show Sol mod loading and Java class version 69.0. Several font page texture errors and asset warnings appeared; cause and visual impact unresolved. Harness readiness not yet observed. No runtime command issued.
- Next: wait for harness readiness, exercise bounded capture/self-test/status, inspect visual availability, and preserve separate machine versus visual proof.

# 2026-10-20 16:33 Europe/Berlin — [COMPLETED] Bus self-test; Sol capture unavailable

- Runtime command `phase2_selftest_20261020_163405|PERCEPTION_SELFTEST` passed at frame 359: bounded retention, sequence, copy isolation, freshness, event gap and epoch invalidation.
- Bridge READY and test harness READY were observed. Status file reports `body=false`, player pos `10835.5,10144.5,0`, snapshot missing and candidateCount=0. No Sol candidate scan happened; do not interpret this as zero zombies.
- Added a narrow test-only `PERCEPTION_BRIDGE_PROBE` command. It invokes the Java roster method without actor spawn or Bus publication, to establish runtime availability/main-thread acceptance. Not run yet.
- Next: close PID 23104 normally, confirm PZ_COUNT=0, relaunch same test build, run probe; Sol-centered capture remains unverified unless a body is present.

# 2026-10-20 16:35 Europe/Berlin — [COMPLETED] test runtime closed for Lua harness update

- Normal main-window close sent to PID 23104; process exited within 30 seconds. PZ_COUNT=0 confirmed. No force termination.
- Relaunch the same isolated Java build so the newly added bridge probe is loaded by the Lua harness.

# 2026-10-20 16:35 Europe/Berlin — [FAILED] Kahlua local-variable ceiling

- Second test PID 32240 loaded the Java bridge, but `SolRuntimeTest.lua` failed compilation: `ArrayIndexOutOfBoundsException: Index 200 out of bounds for length 200` from `LexState.new_localvar`. Command harness READY and probe were absent.
- Root cause: adding diagnostic helper/locals to a large existing Lua chunk exceeded Kahlua's 200 local variable limit. This is a test-harness compilation regression, not a Sol runtime defect or Java bridge failure.
- Next: reduce lexical locals by storing helper and per-pulse state on `SolRuntimeTest`, inspect the failing source context, then orderly close/relaunch after PZ_COUNT=0.

# 2026-10-20 16:36 Europe/Berlin — [IN PROGRESS] Lua local-ceiling correction

- Removed the newly added lexical locals from SolRuntimeTest's oversized top-level/command dispatcher; helper moved to `SolRuntimeTest.capturePerception` and probe/capture outputs now use harness table fields.
- Static-only fix, not loaded yet. PID 32240 remains live; close normally and verify PZ_COUNT=0 before retrying same build.

# 2026-10-20 16:37 Europe/Berlin — [COMPLETED] failed Lua-load runtime closed normally

- PID 32240 closed with normal main-window close; PZ_COUNT=0 verified. No force termination.
- Retrying same isolated test build after the Lua harness local-ceiling fix.

# 2026-10-20 16:37 Europe/Berlin — [COMPLETED] native roster bridge runtime probe

- Runtime command `phase2_bridgeprobe_20261020_163740|PERCEPTION_BRIDGE_PROBE` at frame 57 returned `callOk=true result=64 rosterCount=64 requiredCount=nil` on PID 26372 / PZ 42.21.0. This confirms the main-thread guard accepted the callback and the Java bridge populated the Lua table with 64 zombies.
- No Sol-centered snapshot or Bus publish occurred because `Sol.body` is absent. Added a separately labeled player-origin-only diagnostic to exercise normalization/publication without pretending it is Sol. Not loaded yet.
- Next: normal close PID 26372; PZ_COUNT=0; relaunch same build, then run player probe, self-test and status.

# 2026-10-20 16:39 Europe/Berlin — [COMPLETED] normal closure before latest Lua reload

- PID 26372 closed through main window; verified PZ_COUNT=0. No forced termination.
- Relaunch same isolated test build to load labeled player-origin probe.

# 2026-10-20 16:40 Europe/Berlin — [COMPLETED] Lua pipeline player-origin probe; Sol capture blocked

- PID 29788 loaded the corrected harness (no 200-local error). Player-origin probe results: sequence 1 then 2; roster 61; nearby 5; complete=true; truncated=false; observer/player ID 4; distance 0; source explicitly `SolPlayerOriginProbe`. This confirms bridge→Lua tuple normalization/filter→Bus publish/copy for player origin only; it is not evidence for Sol.
- Final Bus self-test passed at frame 9879. Status: events=2 snapshots=2 epoch=1 dropped=0; candidateCount=5, rosterCount=61; source complete; observer/player ID 4; playerDistance=0, sameFloor=true; snapshot stale at 17,250 ms (>1500 ms), as expected.
- `Sol.body` remains false. Sol-centered capture/model/visual validation not run; no body spawned. Current single test runtime PID 29788 (PZ_COUNT=1). Production untouched.
- Next: use an already authorized test action to make Sol.body present in the test scene, then run `PERCEPTION_CAPTURE`; otherwise pause actor-specific validation pending user scene setup.

# 2026-10-20 16:41 Europe/Berlin — [IN PROGRESS] actor handle for Sol-centered perception

- Explicit user-authorized test initial spawn ran on PID 29788; lifecycle logs show request 1 and `WAITING_WORLD -> SPAWN_PENDING -> REGISTERING -> ACTIVE`, actor generation 1. No teleport/coordinate edit.
- Sol Lua remains `body=false` because `Sol.spawn()` blocks under NATIVE_SHELL; the native shell is owned by `SolRuntimeSupervisor.actor()`. To avoid changing ownership or assigning Sol.body, added read-only test bridge getter `getTestShellActor()` and diagnostic `PERCEPTION_SOL_SHELL_PROBE` that passes this actor as observer and publishes under source `SolNativeShellProbe` only. Not built or run.
- Research before build: official PZ `LuaManager.Exposer.exposeLikeJava` docs and PZ Lua API describe exposed Java methods; community references support pattern only, not return behavior. Exact runtime proof required.
- Next: new isolated Java 25 build, verify ABI/hash, close PID 29788 and confirm PZ_COUNT=0, then launch one test instance.

# 2026-10-20 16:43 Europe/Berlin — [COMPLETED] actor-handle test build

- All test Java sources compiled with Temurin javac 25.0.4.1 against PZ 42.21.0 into new folder `build_phase2_perception_actorhandle_20261020_1642`.
- `javap` confirms `getTestShellActor(): SolIsoPlayerShell` and existing `fillZombieSnapshot(KahluaTable,int):int`. Getter wraps existing supervisor-owned actor and is read-only.
- JAR SHA `7E6516B77DDDB9258568041EA1E3A80AA2557C907D5ED50456010EA678160208`; args SHA `9515685FC72C52982A5E0501D273FEBDC6497F169555EC6E61F9FB4146614549`.
- PID 29788 still active and owns test actor; close normally, confirm PZ_COUNT=0, then launch the new test build only.

# 2026-10-20 16:44 Europe/Berlin — [COMPLETED] closed runtime before actor-handle reload

- PID 29788 closed normally. PZ_COUNT=0 confirmed. No force termination.
- Proceeding with the new isolated build through the guarded launch procedure.

# [PHASE 2 BUS REGRESSION — RUNTIME PROVEN] 2026-10-20 16:46 Europe/Berlin
- Test scope: existing SolPerceptionBus cleanup only; no code/build/runtime restart and no production interaction.
- Runtime: Project Zomboid Build 42.21.0 revision 4a0e9546ec; PID 12984; PZ_COUNT=1. Test bridge JAR `build_phase2_perception_actorhandle_20261020_1642/SolNativeBridge.jar`, SHA-256 `7E6516B77DDDB9258568041EA1E3A80AA2557C907D5ED50456010EA678160208`.
- Commands: `phase2_bus_regression_20261020_165000|PERCEPTION_SELFTEST`, followed by `phase2_bus_status_20261020_165030|PERCEPTION_STATUS`.
- Runtime proof: self-test returned `passed=true` with bounded retention, sequence, copy isolation, freshness, event gap, and epoch invalidation. Source restoration assertions verify `_eventSequence`, `_snapshotSequence`, `_locationEpoch`, `_events` identity, `_latest` identity, `_droppedEvents`, and `MAX_EVENTS` return to saved values even after synthetic events/snapshot/invalidation.
- Post-test status: events=1, snapshots=1, epoch=1, retained=1, dropped=0, candidateCount=5, sourceRosterCount=74, complete=true, truncated=false, observer=98, playerDistance=2, sourceStatus=complete. The single retained snapshot is the real `SolNativeShellProbe` snapshot, now stale at 87,534 ms (expected expiry at 1,500 ms); it is not a synthetic self-test record. Runtime logs show the self-test and status commands completed without errors.
- Result: `[COMPLETED]` P2-A machine regression. No duplicate worker was created; existing poll/event registration was not changed. No regression observed. Human visual proof is not required for P2-A.
- Remaining: P2-B onward still needs the human confirmation that observer 98 is the visible Sol and that the model is actually visible/complete. Current machine visibility readout alone is not human visual proof. Do not mark Phase 2 complete.
- Next exact step: obtain the tester's live-scene confirmation; then continue only with evidence-safe perception checks (player movement, a visually reconcilable nearby zombie, and a free/valid movement target before any native locomotion test).

# [P2-B — MACHINE STATE, HUMAN VISUAL GATE OPEN] 2026-10-20 16:45 Europe/Berlin
- On PID 12984, `PERCEPTION_SOL_SHELL_PROBE` returned sequence=1, error=nil, source=SolNativeShellProbe, complete=true, truncated=false, roster=74, nearby=5, observer=98, origin=(10837.5,10144.5,0), playerDistance=2.
- `NATIVE_SHELL_VIS_STATUS` at frame 5381: supervisor shell active; gameClient=false, gameServer=false, localIndex=0, shellIndex=1; local player=(10835.5,10144.5,0); shell=(10837.5,10144.5,0); distance=2.0; both square references non-null; `isCanSee=false`, `isCouldSee=false`, `getCanSee=false`, `isVisibleToPlayer=false`; `alpha=1.0`, `targetAlpha=1.0`.
- This proves native actor handle and position/relative facts are readable and the opacity fields are full. False visibility flags are not evidence that the body is absent, and these state values do not prove rendered completeness. `Sol.body=false` remains an architecture distinction: the supervisor owns the active shell and Lua Sol.body is not assigned.
- `[IN PROGRESS]` P2-B machine evidence obtained; human visual proof pending. No locomotion command, teleport, raw coordinate edit, or respawn was performed. PID 12984 remains the only PZ process; no production changes.

# [P2-B — HUMAN VISUAL PROOF RECEIVED] 2026-10-20 16:48 Europe/Berlin
- Tester directly confirmed the active in-scene Sol is "ظاهرة بالكامل وواضحة" (fully visible and clear). This is human visual proof for actor presence/model completeness at the time of observation.
- Paired machine evidence from PID 12984 remains: supervisor-owned actor ID 98 at (10837.5,10144.5,0), local player at (10835.5,10144.5,0), distance 2; model registration and square references were true/non-null; alpha=1.0 and targetAlpha=1.0. The runtime visibility flags remained false; they do not override the tester's observed rendering and are kept as a separate concept.
- Status: `[COMPLETED]` P2-B initial self-state/presence check (machine + human). Continuous movement correlation and longer stability are not yet proven. No code/build/runtime restart, movement, teleport, or production change.
- Next exact step: capture a fresh Sol-centered perception snapshot, then have the tester walk the local player normally around Sol without teleport; compare player position/distance before and after.

# [P2-C — PLAYER RELATION BASELINE] 2026-10-20 16:47 Europe/Berlin
- Fresh `PERCEPTION_SOL_SHELL_PROBE` on PID 12984 at frame 29861: sequence=2, source=SolNativeShellProbe, complete=true, truncated=false, roster=74, nearby=5, observer=98, origin=(10837.5,10144.5,0), playerDistance=2. The actor origin stayed at the known shell coordinates and its floor matched the player.
- This is the pre-movement baseline for P2-C. It does not yet demonstrate that player-relative facts update during movement. No movement or coordinate changes were issued by the harness.
- Next exact step: tester walks the local player normally a few tiles around Sol while keeping Sol in view; then take another Sol-centered probe and compare coordinates/distance. No teleport, target edits, or Sol locomotion.

# [P2-C — PLAYER WALK RELATION UPDATE] 2026-10-20 16:49 Europe/Berlin
- Tester reported completing the requested normal player walk around Sol while leaving Sol in scene; no Sol movement/teleport/coordinate edit was requested or used.
- Runtime command `phase2_after_playerwalk_20261020_165100|PERCEPTION_SOL_SHELL_PROBE` on PID 12984 returned at frame 42141: sequence=3, error=nil, source=SolNativeShellProbe, complete=true, truncated=false, roster=81, nearby=6, observer=98, Sol origin=(10837.5,10144.5,0), playerDistance=4.
- Baseline immediately before the walk (frame 29861): sequence=2, roster=74, nearby=5, same observer=98 and same Sol origin, playerDistance=2. Thus the captured relative distance changed 2→4 while Sol's origin and identity stayed constant; candidate roster/count also refreshed.
- Status: `[IN PROGRESS]` P2-C machine update proven. Tester confirmed performing the natural walk; visual correlation of the measured 2→4 separation with what was seen remains to be confirmed. No production changes. PID 12984 is still the sole PZ process.
- Next exact step: obtain tester confirmation that the increased separation matched the scene; after that, test one nearby zombie against the visible scene before advancing to further perception checks.

# [P2-C — HUMAN OBSERVATION CORRELATED] 2026-10-20 16:50 Europe/Berlin
- Tester clarified: they moved through the scene and Sol stayed in place. This agrees with the machine observation that Sol's origin and identity remained fixed while playerDistance increased from 2 to 4. The test concerns player-relative perception, not Sol following the player.
- Status: `[COMPLETED]` P2-C for one normal player movement interval: machine relation changed, Sol coordinates/identity stayed constant, and tester observed Sol remain in place while moving. Longer/directional relationship sampling remains untested.
- Next: inspect whether the current live snapshot exposes candidate identities and coordinates through the existing runtime diagnostics; do not add a patch or restart merely to produce more logs until the existing API is assessed.

# [P2-D DIAGNOSTIC GAP IDENTIFIED / TEST HARNESS ADAPTATION] 2026-10-20 16:51 Europe/Berlin
- Static evidence in `SolPerceptionBus.captureWorld` shows each nearby candidate retains `id`, `kind`, `x`, `y`, and `z`; current runtime commands reported only candidate counts, so a particular zombie could not yet be matched to scene evidence.
- Added test-only read-only command `PERCEPTION_DETAIL` to `SolRuntimeTest.lua`. It reacquires around the supervisor-owned shell using the existing bounded `captureWorld` path, prints completeness/roster/origin/player distance, and prints at most the first 8 candidate IDs, coordinates, and computed distances. It performs no spawn, mutation, movement, LOS, or threat interpretation. Reuses SolRuntimeTest fields to preserve the Kahlua local limit.
- This is diagnostic instrumentation in `08_RUNTIME_TEST`, not a product feature. It requires a Lua reload before runtime proof. Current PID 12984 must be closed normally, PZ_COUNT verified zero, then the existing recovered guarded launcher may start exactly one test runtime. No production files changed.
- P2-D remains `[IN PROGRESS]` until the command is loaded, returns a complete candidate snapshot, and the tester reconciles at least one reported candidate with a visible zombie.

# [LAUNCH INVOCATION FAILURE — RELATIVE ARGS PATH] 2026-10-20 16:51 Europe/Berlin
- The recovered launcher precheck correctly saw `PZ_COUNT=0`, but the invocation passed relative paths for ArgsFile/JarPath/ProfileRoot. The launched Java process changed working directory to the Project Zomboid installation, so Java could not open `.\08_RUNTIME_TEST\...\sol-phase2-perception-runtime.args` and exited with code 1 before bridge/harness readiness.
- This was a launch invocation/path-root error, not a Sol or Lua diagnostic failure. PZ_COUNT returned to 0; no second game remains open. Production was untouched.
- Correction: rerun the same guarded launcher with fully resolved absolute paths; its prelaunch count check remains mandatory.

# [SAFE RELOAD — ACTOR RESET AND STALE COMMAND REPLAY] 2026-10-20 16:53 Europe/Berlin
- After the guarded restart (PID 18240, PZ_COUNT=1), the previous command file content was replayed at frame 0 as `PERCEPTION_SOL_SHELL_PROBE`; it returned `supervisor_actor_missing` because RuntimeSupervisor had not spawned the shell in the new world yet. No actor was created by this probe and no coordinates/state were changed.
- The stale command channel is a known harness behavior: command files persist across restarts and are replayed if not cleared. Cleared the command file immediately. Next: wait until world/harness readiness, issue one authorized initial shell spawn for the fresh runtime, then run `PERCEPTION_DETAIL`.

# [P2-D — BOUNDED ZOMBIE CANDIDATES MACHINE PROOF] 2026-10-20 16:54 Europe/Berlin
- Runtime after guarded Lua reload: PID 18240, PZ_COUNT=1, Project Zomboid Build 42.21.0 revision 4a0e9546ec. Test JAR SHA-256 `7E6516B77DDDB9258568041EA1E3A80AA2557C907D5ED50456010EA678160208`; args SHA-256 `9515685FC72C52982A5E0501D273FEBDC6497F169555EC6E61F9FB4146614549`.
- `PERCEPTION_DETAIL` at frame 4113 returned sequence=1, complete=true, truncated=false, source roster=75, nearby candidates=5, observer=97, Sol origin=(10837.5,10144.5,0), playerDistance=2.
- Candidate facts copied from the live vanilla zombie roster and filtered by same-floor/radius: id 3 at (10834.497,10140.493,0), distance 5.007; id 7 at (10834.276,10141.469,0), distance 4.425; id 8 at (10834.5,10138.5,0), distance 6.708; id 10 at (10838.5,10157.5,0), distance 13.038; id 11 at (10827.5,10128.5,0), distance 18.868. Full underlying output retains more precision.
- This proves bounded native acquisition, coherent snapshot completion, candidate identity/coordinates, same-floor filtering and distance derivation at the machine layer. Candidate IDs are runtime identities, not visual labels. Human confirmation that at least one reported candidate corresponds to a visible zombie is still pending; do not mark P2-D complete yet.
- Reload details: prior command file was replayed at frame 0 before shell spawn and returned actor-missing; it created no actor. After world readiness, one initial test spawn request reached ACTIVE at (10837,10144,0), generation 1, ModelManager registration true. Current shell was recreated by the authorized initial-spawn path; no teleport or manual coordinate edit.
- Remaining P2 gates: human candidate reconciliation, player-walk stability with new actor, multi-zombie visual comparison, safe target validation, Sol locomotion while perceiving, then the separately evidenced LOS/hearing gates. No production changes.

# [P2-D — HUMAN OBSERVATION / RUNTIME CRASH] 2026-10-20 16:55 Europe/Berlin
- Tester reports that during the test Sol was inside the house while the tester/player was outside; approximately four zombies were near Sol. The game then crashed.
- Machine evidence immediately before the report (PID 18240, PZ Build 42.21.0): complete same-floor candidate snapshot listed five zombies at distances 4.425, 5.007, 6.708, 13.038, and 18.868 from Sol. The human estimate of four nearby zombies is broadly compatible with a subset of those candidates, but no identity-by-identity visual match was established.
- Status: `[IN PROGRESS]` / interrupted by runtime crash. The Perception Detail command completed normally; crash cause is not yet known and is not attributed to the diagnostic without evidence. No production changes.
- Immediate action: do not relaunch until process count and crash logs are checked. Preserve the existing runtime evidence folder and game log. Next step is inspect crash time/stack and verify PZ_COUNT; only then decide whether the test runtime can be safely resumed.

# [CRASH REPORT — PROCESS STILL ALIVE / CAUSE UNRESOLVED] 2026-10-20 16:58 Europe/Berlin
- Tester reported that the game crashed during/after the zombie visual check. Live process inspection found PID 18240 still present and responsive, MainWindowTitle=`Project Zomboid`; process timeline continues recording RUNNING with PZ_COUNT=1 through 16:58. The latest DebugLog was still being written at 16:58:09.
- Therefore the human crash report is retained, but a full Java process termination is not evidenced. No second instance was launched. Current state may be an in-game crash/dialog or a gameplay-level failure; user-visible state and root cause remain unresolved.
- Logs include a RuntimeSupervisor cleanup warning for `cell=null` on a restart-time shell cleanup, plus unrelated vanilla/PZ optimization warnings. No confirmed causal link to the user's reported crash, and no fatal exception has been identified as the cause.
- Status: `[BLOCKED — WAITING FOR LIVE WINDOW STATE]` for further gameplay checks. Keep PID 18240 as the sole process; do not relaunch. Next exact step: establish whether the user currently sees a crash dialog/menu or a still-running scene; then close normally if needed, verify PZ_COUNT=0, and only afterward decide on resuming tests.

# [CORRECTION — HUMAN ZOMBIE LOCATION] 2026-10-20 16:58 Europe/Berlin
- Tester clarified that the approximately four zombies were near the tester/player, not near Sol. Correct the previous broad-correspondence wording: this is NOT human visual confirmation for the five Sol-centered candidates and does not satisfy P2-D. Candidate identity/location reconciliation remains `[BLOCKED]` pending an in-scene check when the game is stable.
- The captured Sol-centered machine snapshot still stands as a machine result only: five candidates, distances 4.425, 5.007, 6.708, 13.038, and 18.868 from Sol.
- Crash evidence review: stderr records `IngameState.updateInternal> Exception thrown` with `IndexOutOfBoundsException: Index 5 out of bounds for length 5`, in vanilla `HumanVisual.addClothingItem` → `UnderwearDefinition.addRandomUnderwear` → `ZombiesZoneDefinition.dressInRandomOutfit` → `IsoZombie.update`, then PZ's `UpdateBatch`/`MovingObjectUpdateScheduler`. No Sol method appears in this stack. This is a plausible coincident engine/runtime exception near the reported event, not proven as the causal reason the tester perceived a crash. No full process exit is evidenced: PID 18240 remains responsive and PZ_COUNT=1; no relaunch.
- Next exact step: pause perception/gameplay checks until the live window state is clarified and the runtime is safely closed if it is unusable. Do not claim P2-D human proof.

# [WORLD TRANSITION CLEANUP VERIFIED — SOL ABSENT] 2026-10-20 17:01 Europe/Berlin
- Tester reports being alone in the house. Read-only `NATIVE_SHELL_STATUS` on PID 18240 confirmed `WAITING_WORLD`, `actorExists=false`, `nativeShellCount=0`, `legacyZombieCount=0`, `spawnCount=1`, `removeCount=1`, `cleanupStage=verified-absent`, `cleanupAttemptCount=4`, `staleActor=0`; prior identity 571124153 had been retired with stable cleanup samples.
- Runtime worldGeneration=3 and luaEnvironmentGeneration=2; supervisor is waiting for a usable world, explaining the missing actor after the reported crash/world transition. This is lifecycle/recovery evidence, not a failure of candidate acquisition.
- User visual report corrected: approximately four zombies were near the user/player, not Sol. P2-D remains without human visual candidate match.
- Recovery step: under the Phase 2 in-scene rule's lifecycle-recovery exception, issue one existing `NATIVE_SHELL_SPAWN` in the current PID only after world is ready; no teleport, direct coordinates, or second process.

# [RECOVERY SPAWN + POST-RECOVERY CANDIDATE SNAPSHOT] 2026-10-20 17:02 Europe/Berlin
- In the single existing PID 18240, after the world reported WAITING_WORLD and verified previous actor absence, issued one recovery spawn request (request 2). Supervisor transitioned `WAITING_WORLD -> SPAWN_PENDING -> REGISTERING -> ACTIVE`; new actor identity `391262005`, actorGeneration=2, worldGeneration=3, square `(10840,10148,0)`, world/cell/square/model/modelAdded/activeModel all true. This was the allowed lifecycle recovery spawn, not movement or teleport.
- `PERCEPTION_DETAIL` at frame 40817: sequence=1, complete=true, truncated=false, source roster=68, nearby=7, observer=196, playerDistance=2. Candidates: id110 `(10829.663,10137.5,0)` d=15.441; id111 `(10830.514,10139.958,0)` d=13.141; id112 `(10837.5,10157.339,0)` d=9.334; id113 `(10827.168,10146.073,0)` d=13.551; id114 `(10838.801,10139.5,0)` d=9.159; id122 `(10852.5,10154.329,0)` d=13.341; id186 `(10842.608,10142.55,0)` d=6.313.
- This is machine-only post-recovery evidence. Human visibility and zombie reconciliation after recovery remain pending. Earlier user correction stands: four zombies were near the player, not Sol, in the prior scene.
- Runtime status: PID 18240 only, PZ_COUNT=1. No production change. Continue only after user confirms what is visible in this recovered scene.

# [P2-D — VISUAL CANDIDATE RECONCILIATION BLOCKED] 2026-10-20 17:03 Europe/Berlin
- Tester reports that both tester and Sol are inside the house and no zombie is nearby/visible in the current recovered scene.
- Machine snapshot from the same scene reports seven same-floor candidates within the configured 24-tile radius, nearest at 6.313 tiles. The current bridge/normalizer uses same-floor Euclidean proximity only; it does not test wall/door obstruction or visual LOS. It is plausible that candidates lie outside/behind house geometry, but candidate-to-square/occlusion correspondence has not been proved.
- Do not call this a false positive or a successful visible zombie test yet. Human did not reconcile any candidate with a visible zombie; the requested P2-D human evidence is absent. This discrepancy also confirms that proximity candidate data must not be described as visibility/LOS.
- Status: `[BLOCKED]` P2-D visible-zombie proof pending a naturally available, scene-reconcilable nearby zombie and safe runtime. Do not spawn zombies or add LOS code for this check. Earlier vanilla zombie outfit exception remains unresolved and no full process exit is evidenced.
- Next exact step: confirm the recovered Sol is visible/complete; then continue only with passive perception and player-motion checks in the current world. Revisit P2-D when a zombie is actually visible near Sol; LOS requires its separate evidence pack.

# [P2-B — HUMAN VISUAL PROOF: BODY PRESENT, APPEARANCE MISMATCH] 2026-10-20 17:04 Europe/Berlin
- After recovery, tester confirms Sol is visible near them and the full body is rendered, but describes the actor as a completely naked male character.
- This proves visible actor presence/body completeness for the current shell. It raises a material visual identity/appearance mismatch against the intended Sol presentation; gender/descriptor/clothing correctness is not accepted as PASS. Do not equate alpha=1.0/model registration with correct character appearance.
- Machine correlation: recovery actor identity 391262005, generation 2, position approximately `(10840,10148,0)`, ModelManager registration and activeModel true; latest candidate snapshot is complete but has no visually confirmed zombie.
- Status: `[FAILED — VISUAL APPEARANCE REQUIREMENT]` for expected Sol presentation; `[COMPLETED]` only for body visibility/completeness. No appearance/outfit code changed. Next: inspect existing shell descriptor/visual initialization statically, record the actual cause or `[UNRESOLVED]`, and defer any corrective edit until its own authorized/evidence-backed decision. Keep PID 18240 as the only runtime.

# [STATIC SOURCE REVIEW — SHELL APPEARANCE NOT CONFIGURED] 2026-10-20 17:05 Europe/Berlin
- `[SOURCE PROOF]` `SolBridge.constructShell()` obtains a descriptor from `SurvivorFactory.CreateSurvivor()` and passes it directly into `new SolIsoPlayerShell(cell, descriptor, x, y, z, false)`; `SolIsoPlayerShell` constructor only calls `super(cell, descriptor, x, y, z, remote)`. The inspected construction/attach path contains no explicit gender, outfit, clothing, or appearance assignment.
- `[INFERENCE]` The observed naked male appearance is consistent with an unspecified/default/random survivor descriptor or missing post-construction outfit initialization, but exact cause is not proven from source alone. Do not change this during the perception test without a separate evidence-backed appearance/lifecycle decision.
- Runtime evidence stays: current post-recovery actorGeneration=2 is visible and fully rendered per tester, but visually described as a fully naked male. Body visibility passes; intended Sol appearance remains failed/unresolved. No source code changed by this inspection.

# [P2-C REVALIDATION — POST-RECOVERY BASELINE] 2026-10-20 17:09 Europe/Berlin
- Fresh `PERCEPTION_DETAIL` on PID 18240/current actor generation 2 at frame 101156: sequence=2, complete=true, truncated=false, roster=57, nearby=4, observer=196, playerDistance=1.0659. Candidate IDs/positions: 112 `(10845.479,10157.532,0)` d=10.314; 113 `(10846.013,10143.188,0)` d=7.655; 114 `(10822.178,10161.698,0)` d=22.581; 186 `(10842.516,10144.496,0)` d=4.483.
- This establishes a fresh relation baseline for the current recovered actor. Nearby-candidate count changed since the prior snapshot; no human-visible zombie correspondence is established. Next: tester performs one short ordinary walk around the visible shell without moving Sol, then compare a fresh detail capture.
- Current runtime remains one responsive process PID 18240; no code/build/relaunch/production change.

# [SUPERSEDED OBSERVATION + APPEARANCE STABILITY GAP] 2026-10-20 17:10 Europe/Berlin
- Newest human observation describes the current Sol as a white girl with tied red hair and reports that her color/appearance differs between runs. This conflicts with the earlier post-recovery description as a naked male; preserve both as time-specific reports, and mark the earlier single-look diagnosis `[SUPERSEDED]` by the later correction. The durable finding is that the tester perceives appearance as inconsistent across instances.
- `[SOURCE PROOF]` each supervisor shell construction calls `SurvivorFactory.CreateSurvivor()` and passes the resulting descriptor directly to the shell constructor; the inspected construction path sets no fixed gender, hair, or outfit. `[INFERENCE]` per-spawn descriptor generation plausibly explains variation; the exact vanilla randomization mechanism has not yet been inspected.
- Status: `[REFERENCE GAP IDENTIFIED]` no stable Sol appearance specification/descriptor is configured by the test shell. No appearance patch was made. Need the desired canonical look (gender, skin tone, hair/color/style, clothes, and any in-game reference) before making a fixed-appearance change; this is separate from Phase 2 perception and should not be guessed.
- P2-C revalidation request remains unanswered; the latest user message describes appearance and is not movement confirmation. PID 18240 remains the sole current test runtime. Production untouched.

# [CANONICAL SOL APPEARANCE SPECIFICATION RECEIVED] 2026-10-20 17:11 Europe/Berlin
- User-specified stable look: female character, white/light skin, red hair tied in a ponytail. This supersedes prior generic or contradictory per-run visual descriptions as the target specification; preserve those observations as historical runtime evidence.
- Clothing/outfit has not yet been specified. No appearance code, source, or build changed. Before implementation, inspect the exact Build 42.21.0 descriptor/visual API and community reference patterns, then define the minimal test-only change. Do not guess outfit details.
- This appearance request is a render/lifecycle blocker adjacent to Phase 2, not evidence that perception data is invalid. Phase 2 remains incomplete; no production changes.

# [APPEARANCE OUTFIT SPECIFICATION UPDATE] 2026-10-20 17:12 Europe/Berlin
- User-provided canonical appearance: white/light-skinned female character; red hair tied in a ponytail; long red dress; suitable shoes.
- The final phrase in the user's message is ambiguous (possibly socks/stockings or undergarments). Clarification was requested; do not invent these details or implement appearance until resolved.
- Static-source investigation continues against the installed Build 42.21.0 artifacts. No source, runtime, or production change; no build or launch.

# [APPEARANCE SOURCE DISCOVERY: RANDOM DESCRIPTOR PATH] 2026-10-20 17:13 Europe/Berlin
- `[SOURCE PROOF]` Current test source `08_RUNTIME_TEST/SolNativePrototype/src/sol/bridge/SolBridge.java:306-310` calls the no-argument `SurvivorFactory.CreateSurvivor()` and passes its returned descriptor directly to `SolIsoPlayerShell`; the shell constructor in `SolIsoPlayerShell.java` delegates that descriptor to `IsoPlayer` without setting gender, skin, hair, or outfit in this path.
- `[SOURCE PROOF]` Installed Build 42.21 media Lua contains appearance mutation examples in `media/lua/shared/NPCs/SurvivorSwap.lua` and character creation/tutorial/scenario scripts. This confirms the shipped game uses descriptor/visual APIs for these fields, but the exact API calls and ordering still need inspection before proposing a minimal adaptation.
- `[INFERENCE]` The current source path leaves appearance determined by the factory-created descriptor, explaining why it is not explicitly canonicalized; whether the factory randomizes every field must be verified from exact game artifact behavior before claiming the precise cause.
- Current desired look: white/light-skinned female; red ponytail; long red dress; suitable shoes. Socks/undergarment phrase awaits clarification. No code/runtime/production change; no build or launch.

# [BUILD 42.21 API DISCOVERY: DETERMINISTIC DESCRIPTOR SURFACE] 2026-10-20 17:14 Europe/Berlin
- `[SOURCE PROOF — INSTALLED ARTIFACT]` Read-only `javap` against `C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\projectzomboid.jar` confirms Build 42.21 exposes `SurvivorFactory.CreateSurvivor(SurvivorType, boolean)`, `SurvivorDesc.setFemale(boolean)`, `getHumanVisual()`, `dressInNamedOutfit(String)`, and descriptor `setWornItem(...)`. The current Sol source uses the no-argument factory overload instead.
- Exact HumanVisual setter signatures, female ponytail resource names, red hair color representation, and valid long red dress/shoe outfit identifiers are still under inspection. Do not yet treat API surface discovery as a validated implementation recipe.
- No code/runtime/production change; no build or launch.

# [CANONICAL OUTFIT CLARIFIED] 2026-10-20 17:15 Europe/Berlin
- User clarified the final appearance: female, white/light skin, red hair tied as a ponytail, a long red dress, shoes, and short white socks.
- This resolves the previous ambiguity; the outfit target is now sufficiently specific to inspect exact Build 42.21 item/hair identifiers. This is a specification only, not proof that the chosen assets exist or render correctly.
- No source/runtime/production change; no build or launch.

# [APPEARANCE ASSET IDENTIFIERS VERIFIED IN BUILD 42.21 MEDIA] 2026-10-20 17:16 Europe/Berlin
- `[SOURCE PROOF — INSTALLED BUILD MEDIA]` `media/hairStyles/hairStyles.xml` contains a female `<name>PonyTail</name>` entry at lines 854-856, using the female ponytail model; file SHA-256 `CEE2C0C5CA06F84B091ABC00D63283D1CDA0E103702D6134E62B2B1205DE3261`.
- `[SOURCE PROOF — INSTALLED BUILD MEDIA]` `media/scripts/generated/items/clothing.txt:63-77` defines `Base.Dress_Long`, body location `base:longdress`, and marks it `base:canbedyed`; `Socks_Ankle_White` is defined at lines 18640-18653 for short white socks; `Shoes_Fancy` is defined at lines 19089-19109 and uses the shoes body location. SHA-256 `clothing.txt` = `9EDB818C5366978ACC691BF44A539EB22680D334DB07037E5DB33064598A060A`.
- `[SOURCE PROOF — SHIPPED LUA PATTERN]` `media/lua/client/OptionScreens/CharacterCreationMain.lua` uses `instanceItem(itemType)` then `SurvivorDesc.setWornItem(...)`, confirming explicit item-based descriptor clothing setup is a stock character-creation pattern. The tutorial also sets female on both character and descriptor and resets the model after appearance edits.
- `[SOURCE PROOF — INSTALLED JAR]` `HumanVisual` exposes `setHairColor(ImmutableColor)`, `setNaturalHairColor`, `setHairModel`, `setSkinTextureIndex`, and `setSkinColor`; `ItemVisual` exposes `setTint(ImmutableColor)`. Installed `projectzomboid.jar` SHA-256 `E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`.
- `[INFERENCE]` A minimal deterministic path is possible through the descriptor before constructing Sol: explicit female factory overload; fixed skin/hair fields; explicit long-dress, short-white-sock, and shoe items, with the dress visual tinted red. Still unresolved before implementation: exact light-skin index/tone, desired shoe style/color (user said suitable, so black fancy shoes are a candidate only), color propagation/reset behavior, and red tint in actual render. No implementation, build, or launch yet.
- Active PZ PID seen during static research: 18240 (single process); current test build/path remains the Phase 2 actorhandle build, not production.

# [SKIN INDEX AND FACTORY RANDOMNESS CONFIRMED] 2026-10-20 17:18 Europe/Berlin
- `[SOURCE PROOF — INSTALLED JAR BYTECODE]` No-argument `SurvivorFactory.CreateSurvivor()` randomly selects Friendly, Neutral, or Aggressive; the `CreateSurvivor(type)` overload randomly selects the gender before delegating to the explicit `(type, boolean)` overload. This test-shell source is therefore not canonicalized for gender/type; existing visual observations are consistent with generated descriptors but do not alone prove all exact random fields.
- `[SOURCE PROOF — STOCK LUA]` `CharacterCreationMain.lua:653-656` declares skin-color swatches in order, with the lightest listed swatch first (`0.98, 0.79, 0.49`); `onSkinColorPicked` at lines 1992-1996 stores selected swatch index minus one via `setSkinTextureIndex`. This makes index `0` the first/lightest stock character-creation choice, though final in-world color still requires visual confirmation.
- `[SOURCE PROOF — INSTALLED JAR BYTECODE]` `HumanVisual.getSkinTexture()` chooses sex-specific skin lists and randomizes if the stored index is unset/out of range. Fixing both female sex and valid skin index before model creation is required for repeatability.
- Proposed black `Shoes_Fancy` is an `[INFERENCE]` for “suitable shoes” because the user specified no shoe color/style; the exact item definition exists in the current build. No code/build/runtime action taken.

# [APPEARANCE RESEARCH: LIGHT SKIN + OUTFIT ASSEMBLY PATTERN] 2026-10-20 17:19 Europe/Berlin
- `[SOURCE PROOF — BUILD42 STOCK LUA]` `CharacterCreationMain.lua:653-656` defines four stock swatches; the first/lightest is `(0.98,0.79,0.49)`, and the picker maps its first choice to `skinTextureIndex=0`. The game’s `HumanVisual.getSkinTexture()` uses the selected skin list and chooses a random index only when unset/out of range. This supports using index 0 for the lightest stock skin texture, with `skinColor=ImmutableColor.white` as neutral tint; visual proof is still required.
- `[SOURCE PROOF — BUILD42 STOCK LUA]` Character creation attaches an explicit item via `instanceItem(itemType)` and `desc:setWornItem(...)`. Installed jar confirms `InventoryItemFactory.CreateItem(String)`, `InventoryItem.getVisual()`, `ItemVisual.setTint(ImmutableColor)`, and `InventoryItem.synchWithVisual()` are available.
- `[PROPOSED — NOT IMPLEMENTED]` Minimal deterministic appearance setup before `SolIsoPlayerShell` construction: create `SurvivorType.Neutral` with `female=true`; explicitly set descriptor female; set skin index 0; set female `PonyTail`; set fixed red hair and natural-hair color; create `Base.Dress_Long`, tint red and synch; add `Base.Socks_Ankle_White`; add black `Base.Shoes_Fancy`; attach all three to the descriptor by their shipped body locations. This does not require touching playerIndex, world registration, locomotion, perception, or global LOS.
- Black fancy shoes are the chosen conservative interpretation of the user's “suitable shoes”; user did not specify a shoe color/style. This is a presentation inference, not user-specified detail.
- No code/build/runtime/production change; no new launch.

# [COMMUNITY/GITHUB REVIEW BEFORE APPEARANCE BUILD] 2026-10-20 17:21 Europe/Berlin
- Reviewed the public `Project-Zomboid-Community-Modding/ProjectZomboid-Vanilla-Lua` mirror, commit `8a906692ac56f9d40c078d654eea6c70491cbc62` (tag/commit labeled B42.20.2). Its distribution data independently lists `Dress_Long`, `Socks_Ankle_White`, and `Shoes_Fancy` as shipped clothing IDs. This mirror is one build behind and is corroborative only; exact B42.21.0 local media/JAR are authoritative for the test build.
- Reviewed official Project Zomboid Javadocs for `HumanVisual` setters and `ImmutableColor` constants/constructors; local `javap` signatures match the needed runtime APIs.
- Scope for the candidate adaptation: modify only `08_RUNTIME_TEST/SolNativePrototype` descriptor creation, keeping factory NPC type unchanged, forcing female + lightest stock skin + female PonyTail + red hair; clear random descriptor clothes and set explicit long dress (red tint), short white socks, and black fancy shoes. Do not alter actor registration, scheduling, update, movement, perception, alpha/LOS, or production.
- Build decision: proceed only into a new uniquely named test artifact directory. Existing PID 18240 remains active, so artifact generation is allowed but no launch/restart is allowed until process count is confirmed zero.

# [TEST-ONLY CANONICAL APPEARANCE ADAPTATION] 2026-10-20 17:22 Europe/Berlin
- Status: `[IN PROGRESS]` implementation written to `08_RUNTIME_TEST/SolNativePrototype/src/sol/bridge/SolBridge.java` only.
- `constructShell` now applies canonical appearance to the factory descriptor before `SolIsoPlayerShell` construction; `SurvivorFactory` type selection is retained. Appearance values: female=true; skinTextureIndex=0 and neutral white tint; female `PonyTail`; hair and natural hair color `(0.78,0.08,0.10,1)`; clear generated worn items; add `Base.Dress_Long` with red tint and visual synchronization, `Base.Socks_Ankle_White`, and `Base.Shoes_Fancy` (black inferred as a suitable match).
- Methods are reflective against installed Build 42.21 classes. The change does not edit actor index, NPC state, world/ModelManager/scheduler registration, locomotion, alpha, LOS, perception, Lua bridge lifecycle, or production code.
- Exact API/asset research and community review are recorded above. Runtime PID 18240 was still active at last process snapshot. This source has not yet been compiled or loaded; visual/runtime correctness is unproven.
- Next: compile all six test Java classes into a fresh isolated `build_appearance_stability_20261020_1722` directory; inspect JAR contents/ABI/hash. Do not launch until PZ_COUNT=0.

# [BUILD INVOCATION RETRY] 2026-10-20 17:23 Europe/Berlin
- First invocation failed before compilation: PowerShell passed the argument-file prefix `@` separately (`invalid flag: @`); this is a command-line quoting issue, not a source/compiler diagnostic. No JAR was created and no PZ process/runtime state changed. Corrected invocation will pass `@<absolute javac.args>` as one argument.

# [TEST-ONLY APPEARANCE BUILD — STATIC ARTIFACT VALIDATED] 2026-10-20 17:24 Europe/Berlin
- Status: `[COMPLETED]` for source compilation and package inspection; Runtime appearance validation `[BLOCKED]` pending safe test-runtime replacement.
- New isolated test build: `08_RUNTIME_TEST/SolNativePrototype/build_appearance_stability_20261020_1722/`; compiled all six Java sources with local Microsoft JDK 25.0.4.1 against installed Build 42.21.0 `projectzomboid.jar`. Compiler exit 0, no diagnostics.
- JAR SHA-256: `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`; javac args SHA-256: `FBF3B743A6A5C148388DE949643F8C0376D863EB20A0C29FB3957E7E6A515C47`.
- `jar --list` includes only `META-INF` and `sol/bridge/*.class`; no zombie API/stub classes. `javap` confirms appearance setup is called before shell construction and embeds the selected gender, hairstyle, tint, and clothing item identifiers.
- First build command failed due PowerShell passing `@` separately, documented above; corrected argfile invocation succeeded. This did not affect source/runtime.
- PID 18240 remains the single PZ process on the old `build_phase2_perception_actorhandle_20261020_1642` JAR. New JAR is not loaded. No second launch attempted; production untouched.
- Regression and human visual confirmation have not run. Next: close/save PID 18240 normally; verify PZ_COUNT=0; then launch exactly one test instance with a separate args file and verify descriptor/model outfit values plus in-scene appearance before considering any later runtime phase.

# [APPEARANCE RUNTIME DIAGNOSTIC PREPARED] 2026-10-20 17:25 Europe/Berlin
- Added a test-harness-only `NATIVE_SHELL_APPEARANCE` command to `08_RUNTIME_TEST/profile/Zomboid/mods/SolTest/common/media/lua/client/SolRuntimeTest.lua`. It reads existing supervisor actor's female flag, descriptor gender, skin index, hairstyle, RGB hair color, and worn dress/tint/socks/shoes. It does not mutate the actor.
- Exact installed JAR API inspection confirms the Lua-read methods and item locations exist. Diagnostic has not run; its final syntax/behavior validation depends on loading the test runtime.
- Prepared a separate `build_appearance_stability_20261020_1722/sol-appearance-runtime.args` file pointing the classpath to the new bridge; the active/legacy args file was not changed.
- Current PZ process remains PID 18240 (`PZ_COUNT=1`) on the old JAR. Wait for user to save/close it. No launch attempted.

# [RUNTIME REPLACEMENT BLOCKED — PID STILL LIVE] 2026-10-20 17:26 Europe/Berlin
- User reported the world saved and game closed, but immediate and delayed OS checks still return `PZ_COUNT=1`, PID 18240 (`java.exe` using old actorhandle args/JAR). `Get-Process` reports `Responding=True`, `MainWindowTitle=Project Zomboid`, nonzero window handle `47778122`, working set ~1.07 GB. The latest DebugLog write remained at 17:19:43; this is not proof that the process exited.
- No attempt was made to launch or terminate anything. The appearance build remains static-only. Exact next step: user confirms the PZ window has fully exited (including any exit/save confirmation) and PID 18240 disappears; then re-count processes before one test launch.

# [APPEARANCE TEST RUNTIME STARTED — EARLY EXIT / VISUAL VALIDATION BLOCKED] 2026-10-20 17:21 Europe/Berlin
- Status: `[BLOCKED]` for in-scene appearance verification; launch itself was initiated after the user confirmed the prior game was closed. No production files/runtime were touched.
- Pre-launch/launch record from the launch step: `PZ_COUNT_BEFORE_LAUNCH=0`, launched test process PID `13688`, `PZ_COUNT_AFTER_LAUNCH=1`; args: `08_RUNTIME_TEST/SolNativePrototype/build_appearance_stability_20261020_1722/sol-appearance-runtime.args`.
- Test bridge JAR: `08_RUNTIME_TEST/SolNativePrototype/build_appearance_stability_20261020_1722/SolNativeBridge.jar`; SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`.
- Runtime log `08_RUNTIME_TEST/profile/Zomboid/Logs/2026-10-20_17-20_DebugLog.txt` advanced through 17:21:37 and shows `loading Sol`, ModelManager override loaded, `Loading Clothing`, and world initialization. It does not yet prove the Sol shell was spawned or that the Lua appearance diagnostic ran.
- Subsequent `Get-Process -Id 13688` returned no process; process-name/window-title filters returned no PZ process. CIM and tasklist checks were unavailable (`Access to a CIM resource was not available` / tasklist credential error). Thus the app appears to have exited during startup, but the exit cause is not established; do not label this a Sol or appearance failure.
- No `NATIVE_SHELL_APPEARANCE` result, actor outfit values, model visibility, or user visual confirmation were obtained. No second launch attempted.
- Next: inspect the current test log tail and crash/error artifacts, determine whether the test app exited normally or failed during world load, then only if safe and a clear next diagnostic exists, continue with one test runtime at a time.

# [SUPERSEDED — RUNTIME PROCESS EXIT INFERENCE CORRECTED] 2026-10-20 17:22 Europe/Berlin
- Status: `[IN PROGRESS]` — the earlier inference that PID 13688 had exited during startup was premature. `Get-Process` could not enumerate the game from this tool context, but the same test DebugLog continued through 17:22:18 and recorded world-entry/render-frame activity. Treat runtime as potentially active; do not launch another instance.
- Additional runtime evidence: log says `[Sol] Legacy zombie backend isolated; runtime-test backend is NATIVE_SHELL or unavailable.` At 17:22:14 it records rendered/debug stock horde entities, but character/model draw counters remain zero; this does not establish whether the Sol shell exists.
- A Lua parse/runtime exception was recorded at 17:21:25: `ArrayIndexOutOfBoundsException: Index 200 out of bounds for length 200 at LexState.new_localvar`. Its originating Lua source has not yet been identified and must not be attributed to the new appearance patch without a stack/source link.
- Static args confirm this is the isolated test profile and the new JAR only. No production changes; no second launch.
- Next: identify the Lua exception source and the test harness's established spawn/diagnostic command path from source/log evidence, then check whether a live interactive world is ready before issuing any mutation.

# [RUNTIME DIAGNOSTIC — AUTO-LAUNCH REACHED WORLD ENTRY] 2026-10-20 17:22 Europe/Berlin
- Status: `[IN PROGRESS]` — test log confirms `[SolTest] AUTOLAUNCH WINDOW ENTERED` at 17:21:50 after `OnMainMenuEnter`; game then logged native backend selection and active render-frame records through 17:22:18. This is stronger evidence of world entry than the earlier boot-only logs, but not proof that Sol spawned or that her appearance rendered.
- The `ArrayIndexOutOfBoundsException` at 17:21:25 occurred during Lua parsing/loading; the subsequent Sol auto-launch window hook and world/render events show startup continued. The originating Lua source remains unknown, so it is not attributed to Sol.
- Runtime command file `profile/Zomboid/SolRuntimeCommand.txt` currently contains an old `native_spawn_093754684|NATIVE_SHELL_SPAWN|` line last modified 09:37:54; this predates the current launch and must be treated as stale until proven consumed. Current runtime status file is not yet present. No new command was written.
- Active test Lua exposes `NATIVE_SHELL_SPAWN`, `NATIVE_SHELL_STATUS`, and `NATIVE_SHELL_APPEARANCE`; the appearance diagnostic is read-only. The test harness's actual polling path and actor auto-creation state still need runtime confirmation.
- Runtime process enumeration is unavailable/inconsistent in this shell context while the log advances. Do not relaunch; continue using the current test instance and its logs/status files.
- Next: verify current world/actor state from new log/status evidence, ensure the stale command is not replayed, then create one test shell if absent and read its canonical appearance diagnostic before asking the user for visual confirmation.

# [RUNTIME SUPERVISOR WORLD-LOAD STATE] 2026-10-20 17:23 Europe/Berlin
- Status: `[IN PROGRESS]` — the new test JAR's runtime log provides direct supervisor proof: `WAITING_LUA->BRIDGE_READY` at 17:21:27 (`runtime=1, world=0, env=1, actor=0`), then `BRIDGE_READY->WAITING_WORLD` at 17:21:48 with `world=1`, `cellId=616171367`.
- No `OnGameStart` / `[SolTest] Runtime command channel READY` entry appears in the log as of 17:23:39; the test status file is absent. Therefore the in-world command bus is not yet proven ready and `NATIVE_SHELL_SPAWN` / appearance reads were not sent.
- Stale command file at `profile/Zomboid/SolRuntimeCommand.txt` remains unchanged since 09:37:54 (`native_spawn_093754684|NATIVE_SHELL_SPAWN|`). It has not been shown consumed by this run; do not treat it as a new command or overwrite until the game-ready state is established.
- Next: determine from user-visible screen or new log evidence whether the test runtime has completed world load. If `OnGameStart` and command channel become ready, inspect status and stale request handling before issuing at most one current spawn/appearance diagnostic.

# [USER VISUAL WORLD-READY CONFIRMATION — TEST HARNESS NOT READY] 2026-10-20 17:24 Europe/Berlin
- Status: `[BLOCKED]` for appearance runtime command until the test harness is confirmed active. User reports the game world is visible and playable.
- Current DebugLog continues updating (through 17:24:19), but no `[SolTest] Runtime command channel READY`, no `rtPoll heartbeat`, no test `SolRuntimeStatus.txt`, and no new supervisor state beyond `WAITING_WORLD` (`actor=0`). Existing `SolRuntimeCommand.txt` is an old spawn line from 09:37:54 and remains untouched.
- No command was sent and no actor was created during this diagnostic step. The new build is still test-only; production untouched.
- The unresolved Lua compiler exception at 17:21:25 (`Index 200 out of bounds for length 200`) is now a candidate explanation for missing test-harness registration, but source attribution is not yet proven. Next: inspect active Lua source loading/locals and the current log for a harness-specific failure. Then fix only if source proof identifies the failing test script; otherwise avoid patching.

# [SOURCE PROOF — TEST LUA HARNESS COMPILE FAILURE] 2026-10-20 17:24 Europe/Berlin
- Status: `[FAILED]` for loading the current `SolRuntimeTest.lua` harness; overall appearance validation `[BLOCKED]` pending a minimal test-only repair.
- Exact DebugLog identifies the failing source: `C:/Users/JAMAL/Desktop/Sol/08_RUNTIME_TEST/profile/Zomboid/mods/SolTest/common/media/lua/client/SolRuntimeTest.lua` (`SEVERE: Error found in LUA file`). Kahlua then throws `ArrayIndexOutOfBoundsException: Index 200 out of bounds for length 200` at `LexState.new_localvar` while compiling a local declaration.
- Consequence confirmed by absence of `[SolTest] Runtime command channel READY`, `rtPoll heartbeat`, and `SolRuntimeStatus.txt`; the `OnGameStart` command-poller code in that file never registered. This explains why the old queued command is still untouched. It is a test-harness compile failure, not evidence of a Sol appearance/model failure.
- Static inventory: active test harness is 51,188 bytes / 569 lines and contains 119 `local` keywords; other active SolTest Lua files have lower counts. The exact block/accumulated local-register cause still requires source analysis. No source was edited in this diagnostic step.
- Next: inspect the scope/local declarations in `SolRuntimeTest.lua`, isolate the smallest way to bring the failing function/chunk under Kahlua's 200-local ceiling, preserve behavior, statically validate the edit, and only then schedule a single test-runtime reload after safe process-count verification. Production remains untouched.

# [ROOT CAUSE ISOLATED — MINIMAL HARNESS REPAIR PLANNED] 2026-10-20 17:25 Europe/Berlin
- Status: `[IN PROGRESS]` — the runtime explicitly names active `SolRuntimeTest.lua` as the file that failed to load; the Kahlua `LexState.new_localvar` exception is the local-register ceiling (index 200 of 200). Consequently the command-poller `OnGameStart` registration never occurs.
- Static review shows the affected command-dispatch closure contains the accumulated local declarations for the large legacy test-command chain; the appearance/status read branches add further local slots. The failure is in the disposable test harness, not `SolBridge` or `SolIsoPlayerShell`.
- Minimal repair planned: move the existing `NATIVE_SHELL_STATUS` and `NATIVE_SHELL_APPEARANCE` read-only branch bodies into one small helper function outside the dispatcher closure; replace those branches with one helper call. Preserve exact behavior and appearance values; no actor/runtime architecture changes.
- Before-edit backup will be kept beside the active test harness. Then validate the diff and local-slot reduction statically. Runtime revalidation requires a later safe test-only reload after the current game is closed and process count is verified; production remains untouched.

# [TEST HARNESS LOCAL-LIMIT REPAIR — STATIC CHECK COMPLETE] 2026-10-20 17:26 Europe/Berlin
- Status: `[COMPLETED]` for the source-only test-harness repair and static diff review; runtime compile/reload validation `[IN PROGRESS]`.
- Before-edit backup: `08_RUNTIME_TEST/profile/Zomboid/mods/SolTest/common/media/lua/client/SolRuntimeTest.lua.before_local_limit_fix_20261020_1725.bak`, SHA-256 `A5A995DBFA3460634BCA1E5CA8C5D5776674CA02EF5EA1B7779152732A7663E7`.
- Minimal change: moved the existing read-only `NATIVE_SHELL_STATUS` and `NATIVE_SHELL_APPEARANCE` bodies into `rtNativeShellDiagnostic(cmd)` outside the dispatcher callback. Both dispatcher arms now call that helper. No outfit values, actor code, movement, appearance initialization, or runtime architecture changed.
- Static local-slot accounting for the dispatcher closure: 171 before, 160 after (11 declarations moved out). Source SHA-256 is now `883CDB10E6F130DE8064D2F7F612816445038218ABC85E7AD51444D53B60CE18`. Review shows only the two diagnostic branches were moved; no unrelated edits.
- This is a test-profile Lua harness change only. The currently open PZ session loaded the previous version and cannot validate the patch; source edits do not hot-reload it. No build or Runtime regression was claimed. Production remains untouched.
- Next: save and close the currently open test game; verify no PZ process before any relaunch; relaunch exactly one test instance with the same `build_appearance_stability_20261020_1722` JAR/args, confirm the Lua command channel registers without the local-limit exception, then spawn once and read native appearance state.

# [TEST AUTO-LAUNCH LOOP IDENTIFIED] 2026-10-20 17:40 Europe/Berlin
- Status: `[IN PROGRESS]` — user reports that choosing Exit to Main Menu saves, then immediately re-enters the world with a new character before the menu is visible.
- Static source proof: test-only `SolAutoScenario.lua` declares `debugScenarios.SolRuntime.forceLaunch = true`; `SolForceMenuLaunch.lua` registers `Events.OnMainMenuEnter` and calls `doDebugScenarios()` on menu ticks. The same test profile is reloaded on each menu return, so this combination is a direct candidate for repeated scenario launch.
- Runtime proof: latest DebugLog shows `Saving worldgen params` and `Saving GlobalModData` before `STATE: exit zombie.gameStates.IngameState` at 17:37:41 and 17:38:33. Each is followed by `loading Sol`, `OnMainMenuEnter hook reached`, `AUTOLAUNCH WINDOW ENTERED`, and a new world load. New Sandbox save directories were written at 17:38:33 and 17:39:06. The save sequence runs, but this log alone does not prove every player datum was retained.
- This behavior belongs to the disposable test auto-launch harness. Do not attribute it to Sol actor/appearance. The current game may still be open; no second process launch.
- Next: disable the two automatic triggers in the test profile only, retain manual debug scenario availability, then verify the next normal Exit to Main Menu stays on the menu and the save completes before relaunching the corrected appearance test.

# [TEST AUTO-LAUNCH LOOP FIXED IN SOURCE; LUA HARNESS RUNTIME VALIDATED] 2026-10-20 17:41 Europe/Berlin
- Status: `[COMPLETED]` for source-level removal of forced re-entry; Runtime menu-return regression `[IN PROGRESS]` until the next normal exit. Current test game remains open, and no second process was launched.
- Root cause source proof: installed Build 42 `media/lua/client/DebugUIs/DebugScenarios.lua:106-119` creates the scenario panel and calls `launchScenario(v)` whenever `v.forceLaunch` and `DebugScenario.ForceLaunch` are both true. Test `SolAutoScenario.lua` had `forceLaunch=true`; test `debug-options.ini:1031` has `ForceLaunch=true`; test `SolForceMenuLaunch.lua` called `doDebugScenarios()` on every `OnMainMenuEnter`. Runtime shows this exact sequence after each save/exit.
- Minimal test-only changes: set `debugScenarios.SolRuntime.forceLaunch=false` in `SolAutoScenario.lua`; removed `Events.OnMainMenuEnter.Add(solMenuLaunchStart)` registration in `SolForceMenuLaunch.lua` while leaving manual scenario definition available. Backups `*.before_disable_repeat_20261020_1740.bak` preserved.
- New SHA-256: `SolAutoScenario.lua` `CF954E430C818F9C50D7069120EFDDAD7CF833AAFFF62A705D4DDE727B134AA0`; `SolForceMenuLaunch.lua` `5C0C1749033189B55404AFE5D4759F4D06056A083AC472183161AFF33587702C`.
- Prior `SolRuntimeTest.lua` local-limit repair has now succeeded in the live runtime after menu reload: `[SolTest] Runtime command channel READY` at 17:38:06 and 17:39:06, each followed by `rtPoll heartbeat`. No repeat LexState exception in these reloads. The command channel consumed `PERCEPTION_DETAIL` and reported `supervisor_actor_missing`, confirming that no Sol actor was present yet.
- Next: use the currently live corrected command channel and new test JAR to create exactly one Sol shell and read canonical appearance values. Then request one normal Exit to Main Menu and verify both save completion and absence of another automatic world launch. Production untouched.

# [APPEARANCE TEST PRE-SPAWN RUNTIME SNAPSHOT] 2026-10-20 17:46 Europe/Berlin
- Status: `[COMPLETED]` for read-only pre-spawn snapshot; actor creation and visual proof `[IN PROGRESS]`.
- Command sent through the confirmed active Lua mailbox: `appearance_pre_spawn_20261020_1741|NATIVE_SHELL_STATUS|`. DebugLog at 17:46:43 confirms the exact command consumed and reports `state=waiting_world`, empty failure.
- Supervisor description: `supervisorState=WAITING_WORLD`, `runtimeGeneration=1`, `worldGeneration=5`, `luaEnvironmentGeneration=3`, `backend=NATIVE_SHELL`, `actorExists=false`, `nativeShellCount=0`, `legacyZombieCount=0`, `inLocalSlots=false`, `globalInstance=false`, `bridgeProtocolValid=true`, `bridgeGeneration=3`, `spawnCount=0`, `removeCount=0`. Test owner position from status: `(10835.500,10144.500,0)`.
- The launch PID was 13688; this shell cannot reliably enumerate the live game's PID, so no refreshed PID is claimed. The same log and command channel continue to advance; no second process was launched. Test JAR remains `build_appearance_stability_20261020_1722/SolNativeBridge.jar`, SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`.
- Next: send exactly one `NATIVE_SHELL_SPAWN` request using the existing test harness's adjacent-square selection, inspect the command and supervisor transition, then read the appearance diagnostic if an actor exists. Production untouched.

# [APPEARANCE TEST SOL SHELL SPAWNED] 2026-10-20 17:47 Europe/Berlin
- Status: `[COMPLETED]` for exactly one supervisor-owned native shell creation; appearance inspection `[IN PROGRESS]`.
- Command: `appearance_spawn_20261020_1747|NATIVE_SHELL_SPAWN|` through `profile/Zomboid/Lua/SolRuntimeCommand.txt`. DebugLog confirms command consumed at 17:47:13, request ID `1`, `WAITING_WORLD->SPAWN_PENDING->REGISTERING->ACTIVE` by 17:47:13.691.
- Runtime postconditions at 17:47:13.700: actor identity `491851152`, actorGeneration `1`, worldGeneration `5`, `world=true`, `cell=true`, `square=true`, `model=true`, `modelAdded=true`, `activeModel=true`, square `(10837,10144,0)`. No second spawn request was sent.
- `SolRuntimeStatus.txt` reports `body=false` because it reads the legacy `Sol.body`, not the supervisor-owned native actor; it must not be used to negate the supervisor's ACTIVE state.
- Test build/JAR: `build_appearance_stability_20261020_1722/SolNativeBridge.jar`, SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`. Initial launch PID 13688, current process PID not re-observable from this shell. Production untouched.
- Next: issue one read-only `NATIVE_SHELL_APPEARANCE` command, inspect gender/skin/hair/dress/socks/shoes values and errors, then seek visual confirmation in the currently running test world. Menu-return regression remains unverified until the next normal exit.

# [APPEARANCE RUNTIME READ — BODY/HAIR PROVEN, OUTFIT UNRESOLVED] 2026-10-20 17:48 Europe/Berlin
- Status: `[COMPLETED]` for runtime female/skin/hair values; `[FAILED]` for proving requested outfit through the initial descriptor diagnostic; visual interpretation `[IN PROGRESS]`.
- Read-only command `appearance_read_20261020_1748|NATIVE_SHELL_APPEARANCE|` was consumed at 17:47:33.636. Runtime output: `female=true`, `descriptorFemale=true`, `skinIndex=0`, `hairModel=PonyTail`, hair RGB approximately `(0.78,0.08,0.10)`.
- Same diagnostic returned `dress=nil`, `dressTint=nil,nil,nil`, `socks=nil`, `shoes=nil` from `body:getDescriptor():getWornItem(...)`. This is direct evidence that the queried descriptor does not expose the requested worn items; it does not yet establish whether the actor's rendered body/visual or inventory has clothing. Do not infer a model/appearance failure without inspecting the actor's worn-item source and user-visible scene.
- No patch made after this result. Supervisor remains `ACTIVE` from spawn proof, test JAR SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`; launch PID 13688 (live PID currently unenumerable). Production untouched.
- Next: inspect the exact test Java appearance initialization and Build 42 actor/descriptor worn-item APIs; compare actor `getWornItems`/visual state and ask the user for visual appearance. Apply the smallest correction only after a source/runtime mismatch is proven. Menu-return regression remains pending.

# [APPEARANCE VISUAL CONFIRMATION — OUTFIT PRESENT] 2026-10-20 17:49 Europe/Berlin
- Status: `[COMPLETED]` for the requested outfit's in-scene visual presence. User explicitly reports: `الفستان الأحمر والحذاء والجوارب ظاهرة` on the newly spawned Sol.
- Runtime read at 17:47:33 independently confirms `female=true`, `descriptorFemale=true`, `skinIndex=0`, `hairModel=PonyTail`, hair RGB approximately `(0.78,0.08,0.10)`; supervisor has active model and world/cell/square membership. Thus the requested female/red ponytail initialization and visible red dress/shoes/white socks are supported by combined runtime/user visual evidence. The exact rendered shade/style of hair was not separately described by the user.
- Earlier `dress=nil / socks=nil / shoes=nil` from `body:getDescriptor():getWornItem(...)` is now classified as a diagnostic false negative for visible clothing. Installed Build 42 `IsoGameCharacter` exposes its own `getWornItem`; vanilla `Tutorial1.lua:216-230` and `SurvivorSwap.lua:65` set clothes directly on the actor. The precise descriptor-to-actor transfer/clearing behavior remains to be checked; no native appearance correction is justified from the nil descriptor read.
- Next: update the test-only read-only diagnostic to query `body:getWornItem(...)`, then verify it after a safe Lua reload. Separately verify that a normal Exit to Main Menu saves and remains on the menu after the test auto-launch fix. No production changes; no second instance launched.

# [APPEARANCE DIAGNOSTIC CORRECTED IN TEST SOURCE] 2026-10-20 17:50 Europe/Berlin
- Status: `[COMPLETED]` for source-only diagnostic correction; `[IN PROGRESS]` for runtime read after Lua reload.
- User visual proof: the red dress, shoes, and socks are visible on Sol. Prior `descriptor:getWornItem(...)` returned nil despite that visual result. Build 42 `IsoGameCharacter.getWornItem` exists, and vanilla clothing examples query/set actor wear state.
- Changed only `08_RUNTIME_TEST/profile/Zomboid/mods/SolTest/common/media/lua/client/SolRuntimeTest.lua`: the read-only `NATIVE_SHELL_APPEARANCE` branch now queries `body:getWornItem` for `LONG_DRESS`, `SOCKS`, and `SHOES`. Actor creation and appearance initialization were not changed. New Lua SHA-256 `95D547C221E0193D580CAE7842951E7E02110684621277C5EDCE8A380EE8443D`.
- Active runtime still has the previous Lua loaded; no runtime validation is claimed yet. Test JAR `build_appearance_stability_20261020_1722/SolNativeBridge.jar`, SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`; initial launch PID 13688, current PID not reliably observable. No additional PZ process launched; production untouched.
- Next: user exits normally to Main Menu; inspect save and auto-launch behavior. On a deliberate reload of the existing test save, run the corrected read-only appearance diagnostic and verify the same fixed look after recreation.

# [MENU EXIT REVEALS TEST SUPERVISOR CLEANUP RETRY] 2026-10-20 17:51 Europe/Berlin
- Status: `[REFERENCE GAP IDENTIFIED]` is inapplicable here; this is a direct test Runtime result. `[COMPLETED]` for observing save/exit; `[FAILED]` for supervisor cleanup completion; menu-stability regression `[IN PROGRESS]`.
- Runtime at 17:50:38-39 logged `Saving worldgen params`, `Saving GlobalModData`, `removing all player data`, and `STATE: exit zombie.gameStates.IngameState` after the user's normal exit. This confirms the normal save/exit sequence ran, not that every player field was persisted.
- At 17:51:00, `SolRuntimeSupervisor` changed `ACTIVE->SUSPENDED_ENV->REMOVING->CLEANUP_PENDING` on Lua environment/world cell change. The actor's reported membership was already `world=false,cell=false,square=false,model=false,modelAdded=false,activeModel=false,currentSquare=nil`, but `world-scheduler` cleanup threw `NullPointerException: Cannot invoke zombie.iso.IsoCell.isSafeToAdd() because cell is null`. Retry attempts 1-24 repeated the same failure by 17:51:28. This is a real test supervisor lifecycle cleanup defect; the exact scheduler-removal cause requires source analysis.
- The repeated menu auto-launch trigger was removed earlier in test Lua, but menu staying visible still requires user confirmation and log observation. No second PZ instance or production change. Active JAR `build_appearance_stability_20261020_1722/SolNativeBridge.jar`, SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`; original launch PID 13688, current PID not reliably enumerable.
- Next: confirm menu remains visible; inspect exact `world-scheduler` removal call and guard it only if needed in a future test build after the current runtime ends. Do not patch the active JAR or claim cleanup regression passed.

# [TEST MENU RETURN REGRESSION PASSED] 2026-10-20 17:52 Europe/Berlin
- Status: `[COMPLETED]` for the test auto-launch loop regression. After choosing normal Exit to Main Menu, the user explicitly confirmed: `انا الان في القائمة الرئيسية ولم اعد للعالم بشكل تلقائي`.
- Runtime proof: at 17:50:38-39 the game logged `Saving worldgen params`, `Saving GlobalModData`, and `STATE: exit zombie.gameStates.IngameState`. From exit line 3156 through the 17:51:54 log tail, there were zero `AUTOLAUNCH WINDOW ENTERED` / `OnMainMenuEnter hook reached` / `launchScenario` matches and zero subsequent `STATE: enter zombie.gameStates.IngameState` matches. The user's visual menu confirmation closes the observed loop.
- Test-only source fix already in place: `SolAutoScenario.lua` `forceLaunch=false` and no `Events.OnMainMenuEnter.Add(solMenuLaunchStart)` registration in `SolForceMenuLaunch.lua`. No production change and no additional PZ process.
- Separate unresolved issue: supervisor cleanup still retries `world-scheduler` removal with null cell while the actor has no world/cell/square/model membership. This did not prevent menu display; cleanup is `[FAILED]`, not folded into menu success. Last observed attempt 46 at 17:51:54.
- Next: inspect scheduler-removal source and establish a minimal test-only correction for a future build. The actor-level appearance diagnostic source update awaits a deliberate reload of the existing test save; appearance across a second spawn remains unproven. Active JAR SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`; initial launch PID 13688, current PID unavailable.

# [CLEANUP RETRY STATIC CAUSE NARROWED] 2026-10-20 17:53 Europe/Berlin
- Status: `[IN PROGRESS]` diagnosis; no source correction or new build.
- Static proof: test source `SolRuntimeSupervisor.java:119-126` calls `onWorldCellChanged(liveCell)` after the live world cell changes; `:419-430` invokes `removeActorOnMainThread` when the actor still exists; `:345-346` unconditionally calls `target.removeFromWorld()` in the `world-scheduler` stage on every attempt. `:358-379` retains `CLEANUP_PENDING` whenever any stage throws, even when `noOwnedMembershipsRemain` is true, so `:122-125` retries after 1 second. Runtime matches this flow: after world cell became null, actor memberships were absent but the world-scheduler stage threw the same null-cell NPE repeatedly.
- Root cause at the supervisor level: unconditional `removeFromWorld()` after the world cell is already unloaded and after the actor is absent causes a repeated exception and prevents retirement. Precise internal Build 42 call path inside `removeFromWorld()` remains to inspect before selecting a guard or cleanup timing change. This is separate from the now-passed menu-return fix and from appearance. Test JAR remains `build_appearance_stability_20261020_1722/SolNativeBridge.jar`, SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`; initial PID 13688, no additional launch. Production untouched.
- Next: inspect native `removeFromWorld`/scheduler behavior and decide the smallest test-only lifecycle correction before a future build; do not claim second appearance recreation until cleanup can retire the first actor.

# [BUILD 42 REMOVEFROMWORLD BYTECODE PROOF] 2026-10-20 17:54 Europe/Berlin
- Status: `[COMPLETED]` for native call-path diagnosis; correction and regression `[IN PROGRESS]`.
- Exact installed artifact `C:/Program Files (x86)/Steam/steamapps/common/ProjectZomboid/projectzomboid.jar`, inspected read-only with `javap -c -p -classpath ... zombie.iso.IsoMovingObject`, `zombie.characters.IsoGameCharacter`, and `zombie.characters.IsoPlayer`. `IsoPlayer.removeFromWorld()` delegates through `IsoLivingCharacter`/`IsoGameCharacter`; `IsoGameCharacter.removeFromWorld()` invokes `IsoMovingObject.removeFromWorld()`; the latter calls `getCell()` then immediately `IsoCell.isSafeToAdd()` with no null check (bytecode offsets 0-9), before it reaches `MovingObjectUpdateScheduler.removeObject()` (offsets 59-63).
- Runtime message names that exact first dereference. At menu transition `target.getCell()` is null, so unconditional late `target.removeFromWorld()` can never reach scheduler removal. The actor already reports no owned memberships. A repeated generic retry cannot resolve this after the cell is gone; cleanup must use the pre-unload lifecycle or handle already-absent state explicitly. Do not assume scheduler absence solely from world membership.
- Community/reference check before any build: official PZ API exposes `IsoMovingObject.removeFromWorld` and `IsoCell.isSafeToAdd`; no matching public Build 42 null-cell cleanup contract found in the initial GitHub/community search. The installed bytecode and live log are controlling evidence for this build. No patch or new build yet; production untouched. Test JAR SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`; initial launch PID 13688, current PID unavailable.
- Next: inspect scheduler `removeObject` access/ownership and test source cleanup timing; choose the narrowest correction, build only after research is recorded, then validate after game closure and PZ count zero.

# [REFERENCE CHECK FOR TEST CLEANUP CORRECTION] 2026-10-20 17:55 Europe/Berlin
- Status: `[COMPLETED]` for pre-build research; patch and regression still `[IN PROGRESS]`.
- Primary installed Build 42 bytecode: `IsoMovingObject.removeFromWorld()` dereferences `getCell().isSafeToAdd()` before it calls `MovingObjectUpdateScheduler.instance.removeObject(this)`. `MovingObjectUpdateScheduler.removeObject` delegates to each bucket; bucket `removeObject` removes the object from its lists without dereferencing an `IsoCell`. These were inspected with `javap -c -p` against the installed `projectzomboid.jar`.
- GitHub reference `LivingFellows` commit `f0eaa49802b5b1c767adf175a57a7ad41fa676c4`: `SCBridge.java:2573-2580` unschedules the actor before conditional `if (actor.isExistInTheWorld()) actor.removeFromWorld()`; `SCNativeCompanion.java:677-686` directly removes from the captured bridge cell object list. This is reference source, not Sol runtime proof. Official PZ API documents `IsoMovingObject.removeFromWorld` and `IsoCell.isSafeToAdd` as public APIs; no null-cell guarantee is documented there.
- Based on the installed bytecode and the live null-cell failure, the smallest planned test-only change is to call native `removeFromWorld()` only while the actor still has a cell and world membership; otherwise call `MovingObjectUpdateScheduler.instance.removeObject(target)` directly. Existing `cell-membership` and `square-membership` stages and `noOwnedMembershipsRemain` postconditions stay in place. This is a proposal until built and tested.
- Build is not started while the current PZ process remains open. Test JAR SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`; initial PID 13688, live PID count cannot be reliably read from this shell. Production untouched.

# [TEST SUPERVISOR CLEANUP GUARD APPLIED IN SOURCE] 2026-10-20 17:56 Europe/Berlin
- Status: `[COMPLETED]` for minimal source change; build and Runtime regression `[IN PROGRESS]`.
- Changed only `08_RUNTIME_TEST/SolNativePrototype/src/sol/bridge/SolRuntimeSupervisor.java`: in `removeActorOnMainThread` world-scheduler stage, call `target.removeFromWorld()` only when `target.getCell()!=null && target.isExistInTheWorld()`; otherwise remove the actor directly through `MovingObjectUpdateScheduler.instance.removeObject(target)`. Existing model, captured-cell, square, and postcondition stages remain. New source SHA-256 `0843405B7B4A67155A940C533113538BAED1FF8A79E9DA880760D714B50DC306`.
- Rationale: installed Build 42 bytecode calls `getCell().isSafeToAdd()` before scheduler removal; the live menu transition had a null actor cell and endlessly failed there. Living Fellows commit `f0eaa49802b5b1c767adf175a57a7ad41fa676c4` also unschedules separately and guards its native world removal, but this Sol change is derived from local bytecode and live failure.
- The active test JAR has not changed and the current PZ process remains at the main menu; no regression is claimed. Prior active JAR `build_appearance_stability_20261020_1722/SolNativeBridge.jar`, SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`. Original launch PID 13688, current process count unavailable; no extra launch. Production untouched.
- Next: after normal game closure and verified PZ_COUNT=0, compile a new isolated test JAR, launch one test process, recreate Sol, verify actor-level clothing diagnostics and clean exit without pending retries. If process count cannot be verified, do not launch.

# [TEST CLEANUP BUILD BLOCKED BY WRONG JAVAC VERSION] 2026-10-20 17:56 Europe/Berlin
- Status: `[FAILED]` for the first isolated compile attempt; no JAR was produced or loaded.
- New isolated directory `08_RUNTIME_TEST/SolNativePrototype/build_appearance_cleanup_20261020_1755` and args files were prepared without changing the live test JAR. Invoking PATH `javac` resolved to JDK 17, which rejects installed Project Zomboid class version 69.0 (`should be 61.0`), starting with `zombie.MainThread`; subsequent missing-symbol errors are cascading. This is a compiler selection/tooling error, not evidence against the source correction or Sol Runtime.
- Runtime process was not relaunched; game remained at menu on old JAR. Production untouched. Original launch PID 13688. Existing JAR SHA-256 `A1205E1463A30621D3A76DF0B4DCB8D2B25504111094C56850210E73BAA99477`.
- Next: locate the Java 25+ compiler used for prior Build 42 builds, rerun compilation in the same isolated target only, then hash the produced JAR. Do not launch until PZ_COUNT=0.

## 2026-10-20 19:24:46 - Architecture pivot: Living Fellows -> Sol
- Full pre-pivot project backup already verified.
- Previous active implementation moved intact to: C:\Users\JAMAL\Desktop\Sol_SUPERSEDED_20261020_192445
- Active project reduced to master plan, engineering log, ChatGPT bridge, and imported Living Fellows companion source.
- Living Fellows 0.26.40 imported as mod name/id Sol.
- MIT license and third-party notices preserved.
- No Living Fellows gameplay subsystem has been removed yet.
- Next: reduce Bootstrap/Runtime dependencies to one-companion systems, then remove unreachable population/world systems.


## Living Fellows reduction - official config gates - [IN PROGRESS]
- Timestamp: 
2026-10-20 20:33:24
- Source basis: Living Fellows 0.26.40 source, SCConfig/SCSpawn/SCFactions.
- Change: Added Sol single-companion runtime overrides inside SC.Config.refreshSandbox().
- Enforced: productionEncounterEnabled=false; maxCompanions=1; factionEnabled=false; oddballsEnabled=false; banditFactionEnabled=false; diaryEnabled=false; intrusiveThoughtsEnabled=false.
- Reason: Source confirms these systems expose official config gates; removing Bootstrap requires was rejected as unsafe because modules are intentionally loaded for later runtime contracts.
- Problem encountered: Earlier Bootstrap pruning attempt was superseded and restored to verified baseline.
- Static proof: PASS. SCConfig contains all seven overrides; SHA256=F71FFFE5089A51C636F92FE62D4286EA1340BA52C632EDB968D5BAB5C2B0E15B.
- Runtime proof: PENDING.
- Remaining: verify effective config in-game, then implement fixed female Sol spawn using source-supported SCSpawn/SCActor path; do not remove modules yet.

## Fixed Sol spawn path - [IN PROGRESS]
- Timestamp: 
2026-10-20 20:41:18
- Source basis: Living Fellows 0.26.40 SCSpawn.lua, SCActor.lua, SCCommands.lua, SCRuntime.lua.
- Implemented SCSpawn.solPulse(): one recruited female companion with identity forename=Sol, surname empty, gender=female.
- Spawn placement: reuses the exact 2..6 tile free-square policy used by SCRuntime.recoverySquare(), via GameplayUtil.position/gridSquare/isSquareFree.
- Lifecycle: uses SC.Actor.checkBridge -> SC.Actor.beginSpawn -> existing pendingSpawn -> spawn.pollPending; no new Events hook and no custom actor provider.
- Command-state basis: source confirms recruited=true defaults to order=follow and moveMode=copy in SCCommands.snapshotState().
- Starter-weapon check: prepareNeutralStarterWeapon() returns unchanged for recruited=true, so Sol does not receive neutral-encounter starter weapon behavior.
- Runtime integration: existing productionSpawnTask now calls SC.Spawn.solPulse instead of SC.Spawn.productionPulse; scheduler structure remains unchanged.
- Bridge-edit problem: two earlier text-injection attempts corrupted Lua quotes; both were detected before runtime use and SCSpawn.lua was restored from SOL_FIXED_SPAWN_BACKUP_20261020_203600. Final insertion used Base64 text transport and printed correct Lua lines from disk.
- Current hashes: SCSpawn.lua=694B002C301556BD6144EBACBB97FB4D922D8F7B0BBCD10E49A7776396A7086D; SCRuntime.lua=0F0D3A24596B898595F5C0D96B8616A41C092793F01D941FEBDE8EA662D1DED4.
- Static proof: PASS for insertion/link structure and exact source-policy comparison.
- Lua parser proof: NOT AVAILABLE because lua/luac is not installed locally.
- Runtime proof: PENDING.
- Next: stage/copy this build into the runtime test profile, launch only the test profile, inspect logs for syntax/bootstrap/spawn/provider errors, then validate Sol appears once and follows.

### [
2026-10-20 20:52:58
] Runtime test profile restored
Status: COMPLETED (Static PASS / Runtime PENDING)
Restored the preserved runtime-test profile configuration and saves while excluding old mods and Logs. The current Sol and ZombieBuddy test copies remain staged in the profile. No backup files were placed in Steam. Next step is launch-command validation followed by integrated runtime testing.

### [2026-10-20 21:20:46] SCOddballs compiler-limit mitigation
Original 0.26.40 SCOddballs.lua hit Kahlua 200-local compiler limit at runtime. Replaced with disabled-feature compatibility shim because oddballsEnabled=false. Runtime restart validation pending.

### [2026-10-20 22:13:30] Unique SCOddballsSol require applied
Patched exact SCBootstrap require by line equality, avoiding bridge regex quoting issues. Synced to local and isolated test copies. Runtime restart pending.

### [2026-10-20 23:28:40] Removed BOM from SCOddballsSol.lua
Kahlua parse failure traced to UTF-8 BOM in Sol-specific shim. Rewritten without BOM across all active copies. Runtime restart pending.

### [2026-10-20 23:37:17] Sol spawn diagnostic instrumentation
Instrumented productionSpawnTask to log accepted/reason whenever the Sol spawn result changes. No spawn logic changed. Runtime restart pending.

### [2026-10-20 23:49:23] Dedicated Sol spawn scheduler patch
Applied source-proven scheduler patch after two safe command-matching failures. Root cause of previous command failure was PowerShell literal double-quote matching, not Sol source. sol-spawn now uses high lane with maxDelayMs=5000. Static verification and synchronized hashes PASS; runtime proof pending one integrated test.

### [2026-10-21 00:02:38] Removed executable backup Lua from active trees
Root cause: stale backup SCBootstrap.lua under media/lua/client was being recursively loaded and still required SCOddballs. Moved all matching backup directories out of work/local/test Lua trees into project archive; nothing deleted. Runtime proof pending one restart.

### [2026-10-21 00:07:35] Sol fixed spawn Runtime PASS
User confirmed Sol is physically present beside the player in the live game. Fixed single-companion spawn is now Runtime PASS. Root blocker traced to executable backup Lua under media/lua; backups were moved outside active trees. Proceeding to integrated companion behavior validation.

### [2026-10-21 00:13:01] Sol live movement observed
User reports Sol performs small movements while standing nearby. Recorded as runtime evidence of an active spawned actor. Follow/pathing remains pending manual validation.

### [2026-10-21 00:36:44] Sol AI bridge/awareness architecture started
Created the implementation architecture for perception, bridge transport, validated AI tools, local-vs-external decision loop, persistent memory, mod awareness, conversation/voice, navigation, and vehicle intelligence. No active game files modified because Project Zomboid is currently running. Current project source inventory collected for the next source-analysis step.

### [2026-10-21 00:37:27] Existing LF AI foundation mapped
Confirmed mature navigation/driving subsystems are reusable as Sol execution primitives. Began focused source map of perception, senses, commands, action supervisor, native actions, and Java bridge APIs. No active game files modified.

### [2026-10-21 00:41:58] Sol AI bridge protocol drafted
Created SOL_AI_BRIDGE_PROTOCOL.md from current LF source analysis and recovered old SolPerceptionBus/file-channel evidence. Chose bounded replaceable mailbox IPC for phase-1 transport, with LF ActionSupervisor as execution authority and no arbitrary code execution. No active game files changed.

### [2026-10-21 00:44:39] Sol AI perception adapter written
Created minimal SCAIPerceptionAdapter.lua in work copy only using line-safe PowerShell writing. Static proof PASS; runtime proof pending.

### [2026-10-21 00:48:27] Safe AI Tool Gateway v1 created
Created SCAIToolGateway.lua in work copy only with source-confirmed follow/stay/regroup/retreat/go_to mappings. Raw object commands intentionally excluded pending target resolver. SHA/BOM validation PASS; runtime integration pending.

### [2026-10-21 00:50:28] AI namespace alignment fixed
Corrected both new AI modules from isolated global SC tables to the canonical SurvivorCompanion namespace used by Living Fellows. Work copy only; static verification PASS.

### [2026-10-21 00:52:18] Sol AI target resolver created
Created SCAITargetResolver.lua in work copy using canonical SurvivorCompanion namespace and existing BaseObjectRef/BaseLife, Vehicle SQL-id, and bounded zombie lookup primitives. Static verification PASS.

### [2026-10-21 00:56:31] AI Tool Gateway resolved-target expansion PASS
Precomputed all original indices before mutation, then patched bottom-up. Static verification PASS; runtime proof pending; active mod untouched.

### [2026-10-21 00:58:17] AI Tool Gateway quote corruption repaired
Base64-protected block replacement restored exact Lua quoting in supported schema and resolved-target dispatch. Static verification PASS; active mod untouched.

### [2026-10-21 00:59:37] AI perception references aligned
Work-copy SCAIPerceptionAdapter now emits session zombie ids for visual threats and SQL ids for current vehicles, preserving the no-omniscience auditory contract. Static verification PASS; active mod untouched.

### [2026-10-21 01:05:58] Mailbox inbound duplicate key hardened
Patched inboundKey() by prevalidated line index only. Each identity component is hex-encoded before joining; exact block verification PASS. Active mod untouched; runtime proof pending.

### [2026-10-21 01:08:57] Explicit mailbox ACK contract added
Protocol amended before runtime implementation: Brain -> Game ack now releases exactly the matching outbound sequence. This closes the previously undocumented ping/ack requirement and enables lossless single-flight transport.

### [2026-10-21 01:14:24] SCAIRuntime created
Created compact work-copy AI orchestrator with ACK-gated single-flight delivery, bounded queues/cache, coalesced perception, tool gateway dispatch and proven companion speech API. No bootstrap or active-mod integration. Static proof PASS; runtime pending.

### [2026-10-21 01:15:22] SCAIRuntime queue policy hardened
Static review found that drop-oldest could erase tool results/errors and that periodic heartbeats could fill the queue. Patched heartbeat coalescing and non-destructive bounded overflow behavior. Active mod untouched; runtime proof pending.

### [2026-10-21 01:16:15] Tool request idempotency hardened
Bound cached requestId entries to deterministic request signatures. Identical replay is idempotent; conflicting reuse is rejected without command execution. Static proof PASS; active mod untouched.

### [2026-10-21 01:18:35] Stale SCAIRuntime tool tail removed safely
Previous verifier failed because quote-heavy PowerShell literal was mangled. Base64-protected exact comparison confirmed the stale two-line tail; removed only those lines and revalidated boundaries, SHA and BOM. Active mod untouched.

### [2026-10-21 01:19:35] Tool-result backpressure guarded
Prevented execution of a tool request when no bounded critical-queue capacity exists for its receipt. Added one deferred-tool slot and pause/resume polling semantics to preserve the consumed inbound request until capacity is available. Static proof PASS; active mod untouched.

### [2026-10-21 01:21:32] Repaired SCAIRuntime tail after indexed-edit corruption
Static review caught displaced function bodies caused by the prior multi-index patch. Backed up the corrupted work-copy outside active Lua trees and atomically rebuilt poll/perceive/start/stop/tick/health while preserving deferred-tool backpressure behavior. Host has no Lua parser; structural verification PASS; active mod untouched.

### [2026-10-21 01:25:44] AI bootstrap integration completed
Patched SCBootstrap with the five AI requires and validation contracts using prevalidated original line positions and Base64-protected inserted text. SCRuntime and active mod untouched.

### [2026-10-21 01:28:25] AI lifecycle boundaries corrected surgically
Moved only the misplaced AIRuntime start/stop blocks while retaining the already-correct scheduler integration. Verified start after restore/running commit and stop after reset failure return but before final reset publication.

### [2026-10-21 01:34:45] Protocol safety/proof status aligned
Updated the final stale protocol sections. Integrated AI bridge remains explicitly Runtime PENDING; no Lua or active-game files changed.

### [2026-10-21 01:38:46] SCAIRuntime static hardening
Source-grounded work-copy hardening applied; runtime proof pending.

### [2026-10-21 01:39:41] Protocol aligned after SCAIRuntime hardening
Updated the protocol document to match the final work-copy validation and identity semantics. No Lua, active mod, or test profile files changed.

### [2026-10-21 01:59:34] Verified runtime-test/live sync
With the game closed, removed the proven SCOddballs BOM and copied the hardened AI build to test and live locations. Existing target files were backed up outside active Lua trees. Hash verification passed; runtime proof pending.

### [2026-10-21 02:44:15] Added Worldcraft Intelligence core requirement
Added source-grounded requirements for farming, animal care, cooking, building, semantic storage organization, resource planning, autonomous housekeeping, long-horizon needs forecasting, and mod-aware adaptation. Status: PENDING; implementation must follow research-first workflow.

## 2026-10-21 - Steam Mod Awareness Catalog requirement
Status: [PENDING]
- Added requirement to catalog every locally downloaded Project Zomboid Steam Workshop mod.
- Explicitly separated mod awareness from character learning/unlocks.
- Required separate installed/enabled/current-save/character-permission states.
- Required future Sol Mods UI section with manual Update Mod Database action.
- Refresh must detect newly downloaded, removed, and updated Workshop mods while keeping Workshop content read-only.
- Static/design requirement recorded; implementation and runtime validation remain pending.

## 2026-10-21 - VSGirlBody / Clothing Compatibility / Grace Ashcroft source inspection
Status: SOURCE INSPECTION COMPLETED; INTEGRATION PENDING.
Proof level: Static only.
What was proven:
- VSGirlBodyExtension 1.19.23 is present at Workshop 3820897273 and requires ZombieBuddy.
- Stock VSGirlBodyExtension Java rejects NPCs in PlayerBodyModels.controlled() and PlayerChoice.created(); direct enablement on Sol is therefore not valid.
- Remote appearance profile path is IsoPlayer-only in the inspected methods and does not establish Living Fellows NPC compatibility.
- Clothing Compatibility Patch 1.1.2 is Workshop 3820917070 and requires VSGirlBodyExtension.
- Grace Ashcroft Voice is Workshop 3820444534 / id VoiceGraceAshcroft. VoiceStyles.xml defines GraceAshcroft -> VoiceGraceAshcroft, voiceType 1; sound definitions and OGG assets are present.
- No installed license/readme/permission file established redistribution rights for the three inspected roots.
Decision:
- Do not copy third-party assets into Sol yet.
- Next source task is to trace the exact Build 42/Living Fellows NPC model-resolution and voice-style assignment paths, then decide whether a Sol-only adapter can reuse installed assets or whether author permission is required for an embedded distribution.
- No active Sol, work-copy Lua, or Workshop content was modified by the inspection.
`r`n## 2026-10-22 06:33 - VSGirl dedupe [STATIC PASS / RUNTIME PENDING]`r`n- Evidence: Sol contained byte-identical VSGirlBodyExtension files while external VSGirlBodyExtension is enabled.`r`n- Change: backed up LIVE and WORK, then removed only byte-identical files matching VSGirl source; same-path modified Sol files were preserved.`r`n- Runtime validation: pending integrated game test for Sol visibility and HumanVisual/physics errors.`r`n
`r`n## 2026-10-22 06:36 - VSGirl dedupe runtime [MAIN MENU PASS / WORLD TEST STARTED]`r`n- Main menu reached successfully after removing 4497 byte-identical VSGirl files from Sol LIVE and WORK.`r`n- No HumanVisual.addClothingItem, IndexOutOfBounds, IsoFallingClothing, or Too many physics objects error appeared during boot.`r`n- Same-session world-entry test started without restarting the game.`r`n

## VSGirl dedupe + Sol world runtime validation - [IN PROGRESS]
Updated: 2026-10-22 06:44:47
- Static: PASS. Removed 4,497 byte-identical VSGirl files from both LIVE and WORK copies of Sol; zero exact same-path/hash VSGirl duplicates remain in Sol. Four same-path files with different hashes were intentionally retained.
- Runtime boot/main menu: PASS. Project Zomboid remained alive and responsive; SolCombined.jar won the localplayerbody Java package; SurvivorCompanionBridge initialized; no HumanVisual.addClothingItem / IndexOutOfBounds / IsoFallingClothing / physics-object spam during boot.
- Runtime world load: PASS. MainScreenState and LoadingQueueState exited, GameLoadingState completed, world initialized, and gameplay frames advanced normally.
- Runtime Living Fellows: PASS. SurvivorCompanion runtime started release=0.26.40 protocol=42.21-isocompanion-21 with actors enabled.
- Runtime Sol spawn: PASS. First pulse reported spawn_pending, then finalizeSpawn completed and [SurvivorCompanion][sol] companion spawned. Later pulse returned sol_already_exists, confirming the single-Sol guard.
- Runtime Grace voice: PASS. Log confirmed [Sol] Grace Ashcroft voice bound during finalizeSpawn.
- Runtime VSGirl/Sol adapter path: PASS at initialization/render-hook level. SolNPCAdapter patch classes were discovered and LocalPlayerBodyVSGirl reported Private two-sided surface enabled immediately around Sol spawn.
- Critical regression check: PASS for this session. No post-world IndexOutOfBounds, HumanVisual.addClothingItem, dressInOutfit/dressInNamedOutfit, IsoFallingClothing, or Too many physics objects errors were recorded.
- Unrelated current errors: Recipe Piano missing UiConfigScript fallback; mannequin-zone metadata warning; suspicious Nav zone rejected; duplicate RoomDef.metaID. These are not currently linked to Sol/VSGirl.
- Remaining: visually confirm Sol model is actually visible in-world, then validate follow/movement and vehicle rendering. Do not promote this build to 02_STABLE until those runtime checks pass.
- Architecture note: current dedupe is transitional. SolCombined owns localplayerbody Java while external VSGirl supplies removed assets. Final standalone Sol still requires a single coherent ownership model rather than permanent external/internal split.

### 
2026-10-22 07:51:38
 Europe/Berlin - Post-dedupe movement runtime proof
- Status: [COMPLETED - MOVEMENT/NAVIGATION RUNTIME PASS].
- Runtime evidence: Sol actor `sc-1.792644241642E9-1-224214` changed position from `5737.500,5257.438,0` at 06:44:31 to `5744.262,5236.501,0` at 06:48:00 and later `5741.061,5236.151,0` at 06:49:50.
- Native FSM evidence includes `PlayerMovementState`, `ClimbOverFenceState` with `Bob_VaultOver_Start`, and `PlayerStrafeState`; this proves real locomotion/path interaction rather than animation-only activity.
- Critical regression scan after Sol spawn remains clean: zero `IndexOutOfBounds`, `HumanVisual.addClothingItem`, `dressInOutfit`, `IsoFallingClothing`, `Too many physics objects`, or `NullPointerException`.
- AI mailbox Follow command is NOT yet runtime-proven. A valid-looking `follow` request was written but no matching `tool_result` appeared in Outbox; mailbox/AI runtime consumption remains under diagnosis.
- Stable promotion remains false until current-build visual appearance plus mailbox Follow and vehicle checks are proven.

2026-10-22 10:32:24 - [FIXED / RUNTIME RELOAD PENDING] Restored SCAIToolGateway.lua from pre-cursor backup after go_to_cursor patch inserted literal backticks and caused Lua syntax error at line 15, preventing SurvivorCompanion bootstrap and Sol spawn. Cursor feature rolled back until reapplied safely.

## 2026-10-22 22:55 - Sol Mind brain process [STATIC + OFFLINE PASS / RUNTIME PENDING]
- Root cause of the mailbox Follow failure: no brain process acked game frames (single-flight). The ChatGPT phase-B pump queued one frame and stopped; SolAI_Outbox stayed at hello seq=1 (session 2026-10-22_11-53-35). Mod Lua was not at fault.
- Added 05_TOOLS\sol_lua_check.py (Lua 5.1 syntax gate via lupa): 398 files, 0 errors.
- Added 05_TOOLS\sol_frame_decode.py (SOL_AI_FRAME_V1 decoder, B1/B0 booleans).
- Added 05_TOOLS\sol_mind v0.1 (codec, mailbox, mind_core, harness, sol_mind.py): deterministic ack, one inbox frame at a time with grace, same-requestId resend (idempotent), session reset, single instance (port 8768), provider=none (ollama/api/bridge reserved).
- Offline proof: harness runs the real SCAIMailbox/SCAIToolGateway/SCAIRuntime from 01_WORK under Lua 5.1: 17/17 PASS. sol_mind.py --demo PASS.
- Known gaps: tool_result = accepted, not completed; inbox has no read receipt (proposal: lastInboundSequence in game frames); memory_write/query not implemented.
- Next: one in-game test with live sol_mind.py and Sol spawned: follow.

2026-10-24 19:35:48 - [INSTALLED / RUNTIME PENDING] Sol Brain v0.8.0 Emergency Rescue.
- Status: Offline PASS; Runtime PENDING.
- Evidence: exact-base SHA256 gate PASS; patcher preflight PASS; whole-mod Lua 5.1 gate PASS; emergency rescue offline tests PASS; existing Sol Mind harness PASS; WORK/LIVE hashes matched after sync.
- Remaining: focused Project Zomboid runtime validation of one-Sol continuity, natural-language rescue intent, solo drive to player/marker, combat phase, player extraction, and return-home flow.

- 2026-10-24 Comprehensive repair v0.9.4: exact-source preflight occurs before modification; TickBox ABI fixed; Arabic UI/Talk bridge installed; Dialogue.emitResolved patched only inside its proven function boundary; Sol Link v1.5.1 patched against its actual arrow-function reader; repair regression PASS; whole-mod Lua 5.1 PASS via the project's sol_lua_check.py (lupa.lua51); Sol Behavior Lab PASS; WORK/LIVE parity PASS. Runtime proof PENDING. Full human translation coverage of every authored bark remains a separate localization-completeness item; topic fallback is not claimed as full human translation.


## 2026-10-25 - Sol Link v1.5.2 runtime pass + vehicle enumeration repair
Marker: SOL_LINK_V152_VEHICLE_SET_20261025
Status: Sol Link RUNTIME PASS; Vehicle scan STATIC PASS / RUNTIME PENDING.
- Sol Link full round-trip was proven live after v1.5.2 DOM selector repair and ChatGPT page reload.
- Runtime vehicle symptom: [السيارة] failed with unknown distance while a KI5 vehicle was physically beside Sol.
- Source root cause: SolGPS.nearestCar() and SCAIPerceptionAdapter.nearbyVehicles() bypassed the existing Build 42.21 Set-safe SC.Vehicle.loadedVehicles() adapter.
- Repair: both consumers now use SC.Vehicle.loadedVehicles(); no KI5-specific whitelist, script-name filter, seat logic, route logic, or driving-control logic changed.
- SolGPS.lua SHA256: CE73E00CD6A155757B9626B156063648A2029432F2979F0878C894A7338B5B32
- SCAIPerceptionAdapter.lua SHA256: D5D04082F6336B559F8F9C2775BA253CF61D7268F41F39E31CCE0BC76D26033F
- Runtime validation order: nearby vehicle perception -> driver-seat acquisition -> drive-to-map-marker.

- Lua syntax gate: PASS, 412 files, 0 errors. Remaining warnings are pre-existing SCNavigation.lua literal-backtick-escape warnings outside this patch.

## Passenger driving prepared-lease fix — 2026-10-25 02:44:28
Status: In Progress
Proof: Static PASS; Runtime pending.

Problem:
Runtime driving ended as result=interrupted, phase=released, reason=player_aboard after the local player boarded Sol's vehicle.

Cause:
SCDriving.isDriving() cancelled an already-prepared native drive lease whenever the local player boarded as passenger. This contradicted the intended flow where Sol acquires driveStart while the player is outside, then the player boards after ownership is prepared.

Fix:
Removed only the post-acquisition playerAboard(job.vehicle) cancellation from Driving.isDriving().
Pre-acquisition player_aboard gates remain intact in Driving.begin/start/direct drive.
Driver-seat loss still fails closed through left_driver_seat.

Static proof:
- Work/live SCDriving.lua hashes match.
- Lua checker passed.
- Acquisition safety gates verified present.
- Old runtime passenger cancellation verified absent.

Runtime proof:
Pending.
## Passenger-drive lease fix — Static verification corrected — 2026-10-25 02:45:17
Status: In Progress
Proof: Static PASS; Runtime pending.

Verified:
- Real Lua checker executed against both Work and Live roots.
- SUMMARY files=434 errors=0 warnings=2.
- Both warnings are the pre-existing SCNavigation.lua literal-backtick-escape warning.
- SCDriving.lua Work/Live SHA256:
  6AA5813DDC346E0F5661725768D36AE46E57FFE162D603ACCC840B2826A58880
- Pre-acquisition player_aboard safety gates remain present.
- Post-acquisition player_aboard cancellation in Driving.isDriving() is absent.

Static result:
PASS.

Runtime test still required:
Sol must acquire driver seat/native drive ownership while player is outside, then player boards as passenger, and the prepared driving job must remain active instead of becoming interrupted/released/player_aboard.
## 2026-10-25 - Action catalog Layer 1+3 (registry + planner) - [STATIC PASS / RUNTIME PENDING]
Status: Static PASS; Runtime PENDING. WORK only; LIVE untouched; SolActions.lua v0.4.0 not edited (wrapped at OnGameStart).
- Evidence scan of installed Build 42.21: 273 ISBaseTimedAction classes, 969 craftRecipe, 437 evolvedRecipe. Egg path: Egg IsCookable (MinutesToCook=4, MinutesToBurn=20); PrepareOmelette = mixing utensil + Pan + 2x tags[base:egg] -> OmeletteRecipe; evolvedRecipe Omelette MaxItems=3.
- New 01_WORK\Sol\42\media\lua\client\SolActionRegistry.lua v0.1.0 SHA256 D338FBB440CBADD779A32830A75B76CBE37D95745CBCEFA678C02D07CF2351BB: generic U.timed(class,...) runner; 12 verbs with dry-run check gates (doors, window, light, stove on/off with power check, rest, wash, equip best weapon, reload, pills, fill water); wraps U.runAction/U.actionCatalog; verbs exported with enabled/reason.
- New SolPlanner.lua v0.1.0 SHA256 F4399A5748BA854CFACCD1588FCC903B03F135556DB1696EB70CFC28E4F7B141: generic step runner (run/done/timeout, cancel on Combat.peek danger); plans sol_cook [item], sol_cook_and_serve, sol_plan_status, sol_plan_cancel. Cook = fetch if needed -> walk to stove -> transfer in -> stove on -> watch isCooked, fail on isBurnt/stove off -> take out -> stove off if we lit it -> follow. No-cheat reasons: no_<item>_seen, no_stove_seen, stove_has_no_power.
- Lua gate: sol_lua_check.py 01_WORK files=219 errors=0 (1 pre-existing SCNavigation warning).
- Not done (Phase B): craftRecipe/evolvedRecipe execution via ISHandcraftAction / ISAddItemInRecipe (needs read of the game's own call sites first); per-save spatial memory for "where she last saw X".
- Next: sync both files to LIVE after game closed, one runtime test: sol_cook egg with an egg in her bag and a powered stove nearby; read SolAct_State.txt + [SolPlanner] log lines.

## 2026-10-25 04:17 - FIRST COMPOUND ACTION RUNTIME PASS: sol_cook egg - [RUNTIME PASS]
Status: Runtime PASS. Console: [SolActions] sol_plan_status -> true done:cook:all_steps_done (session 2026-10-25_04-12, f:8765). User screenshots: egg inside oven, then "Egg (Fresh, Cooked)" in Sol's bag with burn bar barely started.
Chain proven live: yield own work -> walk to free square beside stove -> egg into oven -> oven ON by Sol -> watch isCooked (fail on isBurnt) -> egg out -> oven OFF -> follow.
Evidence-based fixes on the way: v0.1.1 registry stove power=getContainer():isPowered(), state=Activated(); v0.1.2 planner AdjacentFreeTileFinder.Find for the walk square; v0.1.3 yieldWork=SC.Decision.cancelWork before walking + retries; v0.1.4 stepMove timed action then direct container move after 4 s; v0.1.5 stepStove timed action then stove:Toggle() after 4 s.
Hashes WORK=LIVE: SolActionRegistry.lua 27F74A422365D3C9FC4573F858A7D23B0F38789EA036E02E890FAD7879A2766E; SolPlanner.lua 36CE9150F17DDB4027E34E7687D28CD88979C8D025CC02B15B64633A79544D01. Lua gate 219/0.
Brain path proven live: ChatGPT via Sol Link chose [action: sol_cook | egg] from the catalog (sol_mind.log 03:41:52, 03:44:13).
Open: (1) bridge mode speaks before the action result -> Sol promised while body refused; fix chat_service.py link path. (2) stale SolAct_Request consumed at world frame 1 before Sol exists. (3) nearest IsoStove may be a microwave; omelette must exclude it. (4) debug ERROR counter high in session 04-12 - source to be identified. (5) Phase B: craftRecipe/evolvedRecipe execution; per-save spatial memory.
- 2026-10-25 04:25 RULE (runtime-proven): ISInventoryTransferAction must never be queued for Sol. Its perform() (vanilla ISInventoryTransferAction.lua:490) indexes the local player's inventory UI (selectButtonForContainer) -> RuntimeException for an NPC; the action stays in her queue and repeats (963 stack dumps / 8554 debug errors in session 04-12, zero from Sol files). SolPlanner v0.1.6: stepMove is direct container move only (Remove/AddItem, same as proven solGive). WORK=LIVE SHA256 21A57ADC26BB50F9651CEF7774907008EC5069FB9D3FFE996CF9B2CC460F1D54; Lua gate 219/0. TODO: SolActions.lua v0.4.0 sol_fetch 'taking' phase uses the same action and will hit the same fault -> convert to direct move. General rule for Layer 1: before wrapping any IS*Action for Sol, read its perform()/isValid() for local-player-only assumptions (UI panels, getPlayerNum, sendClientCommand).
- 2026-10-25 05:05 [STATIC PASS / RUNTIME PENDING] Passenger driving, Java layer. Proof: live SolCombined.jar = LF protocol isocompanion-21 = release 0.26.40 (github thorelvin/living-fellows commit baf4a70); javap showed beforeVehicleUpdate: getDriver -> SCBridge.playerAboard -> stop(player_aboard). Archived sources were protocol-24 (newer, driveStartWithPassenger) and do NOT match the jar. Patch: downloaded baf4a70 SCCompanionDriver.java (SHA256 F6A3A21504F5E492DD5147BB691F3323D385586BD80016EB8D2057774552098A), gate javap signatures jar=38 src=38 diff=0, removed only the 4-line playerAboard stop (the left_driver_seat check above already guarantees Sol is the driver, so any player aboard is a passenger; driveStart still refuses when a player boards first). Built with javac 25.0.4 against SolCombined.jar+projectzomboid.jar; jar uf replaced SCCompanionDriver(+ClearEdge,WorldView). Backup 08_RUNTIME_TEST\jar_patch_player_aboard_20261025\SolCombined.jar.before_player_aboard_patch (45CAFC1D95460F45CBF73F12D331478B8C00455EE1DEFB65F44E2C51AE9F0F97). New jar WORK=LIVE 3DA5B0CD87213D0D06748F21A56D1AF65C6F14A71BADA87B4A480B485E5021B8. Together with the 02:44 SCDriving.lua fix the passenger flow is complete in source. Runtime test: Sol takes wheel while player outside -> player boards as passenger -> drive to marker; if 'companion is not at the passenger door' returns, that is the SolGPS boarding-order item, separate.
- 2026-10-25 [STATIC PASS / RUNTIME PENDING] SolGPS: (1) driver door walk = LF SCExpeditionCar 376-394 pattern (boardingSquares -> cancelWork -> solGoto -> retry takeWheel, max 3 tries, 30 s); (2) GPS panel showed real planner status NO_EXIT_CANDIDATE (marker >100 tiles from any named road; farm start was accepted), so the preview snaps the marker to SCBridge.nearestStreet (same call as LF SCFactions) and the drive goal uses the snapped road point; dashed yellow line shows the off-road remainder. SolGPS WORK=LIVE 165F4DE82045771E1AA7F79D7118B4B4C5B908BD925800FD7A363A855BECCC9D
- 2026-10-25 [STATIC PASS / RUNTIME PENDING] SolGPS map panel v2: embeds the game's UIWorldMap with the exact vanilla ISMiniMap init (getLotDirectories -> addData worldmap.xml -> endDirectoryData -> addImages -> setBoundsFromWorld -> initDefaultStyleV1, HideUnvisited on), route drawn via worldToUIX/Y, pin + 8-direction car arrow icons in media/textures/SolUI, zoom +/- / recentre / pan / wheel, left click on the map sets the destination. SolGPS WORK=LIVE 51D3694E9226F8E79DD7E64F24B9249F5EE7848E3B718066D736A1FC168C7DF5
- 2026-10-25 [STATIC PASS / RUNTIME PENDING] Road planner bridge (Java). Runtime GPS panel showed INCOMPLETE_MAP_DATA from the farm. Source (LF baf4a70 SCRoadRouter.join): a street end links to another street only within width/2+1.5 tiles (max 12), so farm tracks / broken streets that stop a few tiles short leave the start isolated. Patch: when no normal link exists, the end bridges to the nearest street within 16 tiles (24 for the same street name); the junction becomes a graph edge (graph.edge(junction.from, junction.to)). Gate: javap signatures jar=src. Backup 08_RUNTIME_TEST\jar_patch_road_bridge_20261025. New jar WORK=LIVE 3DA5B0CD87213D0D06748F21A56D1AF65C6F14A71BADA87B4A480B485E5021B8
- CORRECTION 2026-10-25: the previous road-bridge entry was written although jar uf failed (PowerShell comma/plus precedence split each class path); the jar was unchanged (3DA5B0CD...). Re-applied by adding the whole out_patch\survivorcompanion\bridge folder (15 SCRoadRouter classes only). Gate: real signatures equal, only compiler lambda numbering differed. Bridge constant present: True. New jar WORK=LIVE 9C1B7EB8F8FF7669710EE17E23C4CF174D00C39F2840520908FA390658802BBE
- 2026-10-25 [STATIC PASS / RUNTIME PENDING] Drive with player aboard. Runtime: Sol drove a planned road route from the farm (first planned drive), stopped by player_stop, then could not re-take the wheel while the player sat inside. Fix: SCBridge.driveStart now refuses only when Sol is not the driver (was: any player aboard); SCDriving player_aboard gates (3) removed; SolGPS takeWheel uses the player's car when its driver seat is free and refuses only if the player is the driver; GPS pin/car icons clamped inside the map; new map click while driving re-routes. jar 11E2BE92B3FBAE634AA8286EBA6C3B59AE4358BCF82DBAF07F10E18C4D7E132D
- 2026-10-25 [STATIC PASS / RUNTIME PENDING] Turn-around. Runtime: after 4 successful planned drives, a re-route behind the car started LF's 3-point turn, it left the road onto grass, hit a tree and ended reason=turn_failed (MAX_LEGS=9), stopping for good. Source: SCTurnAround only sees obstacle clearance, not road edges. Patch SCRoadFollower only: if the turn starts on the road and the road is wider than the car's half length +0.5, a bumper beyond road edge (width/2 + shoulder, projected on the route) ends that leg like an obstacle; a FAILED turn retries the other way up to 2 times before TURN_FAILED. Compiled locally (javac 21) and on the PC (javac 25); gate jar=src. jar 1EE44CBE489CC78AB3255059281CE52918CC1AC7B7B8F741A4036C9FEF8AE848
- 2026-10-25 [STATIC PASS / RUNTIME PENDING] False arrival. Runtime: four drive requests returned result=arrived reason=player_order while Sol stood beside the player (inVehicle=false); she told the player she had arrived. Cause: SCDriving.stop releases a job with a new reason but leaves the old result in the snapshot, SolGPS.gpsStatus copied it, and chat_service._drive_outcome treated anything not 'failed' as success. Fix: gpsStatus reports interrupted unless reason == arrived; _drive_outcome counts arrived/interrupted with any other reason as a cancelled (failed) drive and reports drive_cancelled:<reason>. WORK=LIVE SolGPS DCB3C16E8E31F26CD1937838819BF96C278FA480B057AD486C7AF88C9F573BFE
- CORRECTION 2026-10-25: the false-arrival entry above claimed the Lua half was applied; it was not (FindIndex does not exist on a PowerShell list, installer stopped before editing). Only the Python half (chat_service._drive_outcome) was applied at that time. The Lua half (SolGPS.gpsStatus: arrived with reason ~= arrived becomes interrupted) was applied by the follow-up command; SolGPS WORK=LIVE 934C4154486702D7AFABDF601044614C5208D893F7060425BC236F48F17D3686
- 2026-10-25 [STATIC PASS / RUNTIME PENDING] Driving package. Source facts: SCRoadFollower treated any blocked line within road width+1 as a dead end (BLOCKED, then Lua waited 5 s, replanned up to 3 times, then route_blocked for good); the bumper ray in SCCompanionDriver follows the heading, so on bends it braked for roadside trees (safety_blocked); a turn that failed ended the drive. Changes: follower may use clear ground up to 3 tiles past the road edge (AVOID_SHOULDER) and eases back up to 3 times when boxed in; driver ignores the bumper ray beyond 2 tiles while the route lane is clear; Lua: blockWaitMs 2500, attempts reset after 60 tiles of progress, up to 4 retry cycles before route_blocked, Driving.setSpeed / Driving.setGoal (no stop); GPS v3 (auto show, collapse to floating icon, separate Drive/Stop, far player -> solo drive). Offline harness on the follower: open road, wreck with clear verge (before: BLOCKED, after: goes round at offset 4.5), boxed in (before: sits, after: 3 easing-back bursts), no room behind (no reverse), obstacle gone (resumes) - all pass. NOT tested in game. jar B93840A939B72F45B84707E14066509D0BC151208DECE9A3877ACC82DA808B09
- 2026-10-25 [STATIC PASS / RUNTIME PENDING] Stale requests. Request counters (SolGPS lastId, SolActions lastId) start at 0 every session, so SolGPS_Request.txt / SolAct_Request.txt left from the previous session were replayed at world start (proof: [SolActions] sol_cook egg -> no_sol at frame 1 after restarts). With the driving pack a replayed marker request could send Sol off alone. Fix: the first poll of a session records the file's id and ignores it; both request files deleted. Also noted: the 06:33-07:18 session logs predate the driving pack install (07:19:19), so the pack is untested in game.
- CORRECTION 2026-10-25: the stale-request fix in SolActions.lua primed the id only when the request file existed, so with no file at start the first real request of a session was swallowed (offline simulation: installed version executed 901 and swallowed 900). Replaced by a block at the top of poll() that reads the file id once per session whether or not a request is there. SolGPS.lua was correct (its poll runs the priming line even with no file).

## 2026-10-29 — AOT persistence correction and route-drive safety repair
Status: Static and harness PASS for the focused repair; PZ runtime gameplay PENDING; LIVE promotion withheld.

- AOT persistence preflight found `options.ini` had no `aotCache` key, so installed PZOpt defaults it to true. Used the official `UserOptions.set("aotCache", false)` path and `AotCache.resetLauncher(gameDir)` API, then verified the setting and launcher arguments. No manual JSON editing. Baselines and helper source are retained under `08_RUNTIME_TEST/aot_persistence_preflight`.
- CORRECTION: a proposed “change setting then launch” route was unsafe because the launcher carried `-XX:AOTCacheOutput` (RECORD); `AotCache.onGameExit` can terminate the JVM. The route was replaced by the official setter/reset API before launch. This does not establish AOT as the crash root cause.
- One PZ JVM was started from the Steam installation against isolated profile `07_TEST/RUNTIME_TEST/profile`, with `-Dpzopt.aotCache=false`; `jcmd` showed G1GC and no AOT runtime/cache arguments. The process reached the main menu, but no world was entered. The Windows UI-control approval timed out. Therefore Sol loading, gameplay, and the original AOT/Shenandoah failure remain unverified. Startup logs also report missing main/dialogue font image assets; causal relevance is unknown.
- Fixed `01_WORK/Sol/42/media/lua/client/SCDriving.lua`: refuse fresh native drive acquisition if the local player is already in the vehicle, before creating the lease. Existing prepared leases remain promotable after the player boards. Focused behavior contract B6/B7 PASS; test-profile copy now matches WORK (SHA256 `F60DD287D2B5403ECF44F5CF57D5346FFEE0F69B36B352C6A807BE3A6FA6FA5E`). Original WORK and test-profile files are backed up in `03_BACKUPS` and `08_RUNTIME_TEST`.
- Fixed the offline verification path: bounded a queued-state loop and made the Python harness UTF-8 safe on Windows. Sol Mind harness T1–T8 and goal/rescue contracts G1–G21 PASS. Lua 5.1 gate: 235 files, 0 errors, 1 pre-existing SCNavigation literal-backtick warning.
- Full behavior lab is not release PASS: changed-behavior parity reports WORK/LIVE differences in SolGPS.lua, SCAIToolGateway.lua, and SCDriving.lua. This reflects WORK ahead of LIVE; LIVE and STABLE were not changed. Runtime-only vehicle boarding, route driving, and solo rescue remain pending.
- Next: when UI control is available, enter a test world and validate one canonical Sol, nearby vehicle perception, driver acquisition, passenger transition, route drive, and rescue/home extraction. Investigate missing font assets separately. Do not promote WORK to LIVE until runtime evidence passes.
## 2026-10-29 — Release baseline created; verification tooling repair
Status: BASELINE SNAPSHOT VERIFIED; release/runtime acceptance PENDING.

- Created `01_WORK/RELEASE/SOL_2026-10-29_BASELINE/Sol` as the first release-work snapshot copied from `01_WORK/Sol` (1,148 files). Every payload file matched source WORK by SHA-256; generated `MANIFEST_SHA256.txt` and independently verified all 1,148 entries.
- The snapshot contains the verified `SCDriving.lua` local-player-aboard acquisition guard. Release payload gates: Lua 5.1 235 files / 0 errors / 1 existing warning; B1-B7 PASS; Sol Mind T1-T8 PASS; rescue planner G1-G21 PASS. It is explicitly a development baseline, not runtime-approved or ready for public/LIVE release.
- Full release gate remains FAIL because WORK/LIVE parity differs in SolGPS.lua, SCAIToolGateway.lua, and SCDriving.lua. Runtime gates remain pending; no changes were made to STABLE or LIVE.
- Additional tool-only repair: `05_TOOLS/sol_behavior_lab/tests/test_goal_engine.py` now configures UTF-8 output so Arabic diagnostics work when run directly on Windows. Verified standalone G1-G21 PASS and full behavior lab again. The behavior lab overall remains FAIL only at WORK/LIVE parity and runtime-only gates. Since this change is outside the mod payload, no new mod payload snapshot was needed; recorded in `RELEASE_TRACKING.md`.
- Continue feature repairs in WORK, back up each source change, record exact verification here and in the engineering log, then create a new dated release snapshot only after the relevant gate passes. Never promote to STABLE/LIVE without runtime proof.
- Backup note: reconstructed the pre-UTF-8 test script by removing only the newly added stream-reconfigure block; its SHA-256 `E0B05255B2644159D61D00C8724846566C7BD5839F408F3343BC7A77880463EB` matches the pre-edit hash captured before modification. Backup: `03_BACKUPS/sol_goal_engine_harness_utf8_20261029/test_goal_engine.py.before_utf8_fix`.
## 2026-10-29 — User-confirmed connectivity PASS; behavior execution becomes priority
Status: Connectivity across all configured channels USER-CONFIRMED PASS. Command execution smoothness IN PROGRESS; integrated behavioral diagnosis pending.

- User confirmed all in-game communications were completed and work: Sol Link/ChatGPT bridge, phone connection, provider API connection, and local model. Treat these as runtime passes based on direct user confirmation; do not repeat connection setup/tests absent a regression.
- User clarified the remaining fault is Sol's behavior: orders/actions are not executed smoothly/consistently, and the concern is Sol's execution layer relative to Living Fellows (LF), not connectivity. Keep LF's proven command/action mechanisms as the baseline and isolate Sol-specific intent/planning/dispatch/acknowledgement behavior.
- First-principles trace for the next repair: player request -> deterministic intent / model tool -> selected action and arguments -> SolActions or SCAIToolGateway -> LF `SC.Commands.issue` / LF timed action -> accepted/started state -> observed completion or explicit failure -> truthful response. Capture request id, action, reason, state transition, and world evidence for each failing order.
- Existing plan already records an important gap: `tool_result` currently means command accepted/rejected, not completed; completion must be verified from perception. This is the leading investigation target, not yet a proven sole root cause. A queued action may be mistaken for completion, or a valid command may be dispatched without the expected follow-up state.
- Diagnostic order: compare a specific failing order through (1) direct LF UI, (2) Sol deterministic speech intent, and (3) Sol model `do_action`; classify whether LF itself fails, Sol intent mapping is wrong, command dispatch/preconditions reject it, or completion/response reconciliation is missing. Fix one proven boundary at a time; do not rewrite LF internals as a workaround.
- Release rule: no mod payload source changed for this connectivity update, so the 2026-10-29 release baseline remains unchanged. Record confirmed runtime channel evidence and the new behavior priority in `01_WORK/RELEASE/SOL_2026-10-29_BASELINE/RELEASE_TRACKING.md`. Create a new dated payload snapshot after a behavior repair passes its applicable offline and runtime validation.
## 2026-10-29 — Static authority trace for orders received by Sol Mind
Status: Architecture trace complete; two high-confidence static behavior hazards found; exact runtime blocker for a user order not yet proven. No product source changed.

### Authority and execution path
- For chat/provider orders, `05_TOOLS/sol_mind/chat_service.py` decides the input route: deterministic Arabic intent rules run first; API/local model receives `do_action`; the ChatGPT bridge receives a tagged-action request. `resolve_and_run()` sends the resulting action through `SolAct_Request.txt` to game-side `SolActions.lua`.
- `SolActions.runAction()` is an adapter, not the order authority: it either calls the same LF UI callback / `SolPages.issueLF()` or dispatches direct LF commands through `SC.Commands.issue()`.
- A separate structured mailbox path exists: `SCAIRuntime.lua` receives `tool_request` -> `SCAIToolGateway.execute()` validates/maps tools -> ordinary commands call `SC.Commands.issue()`. The chat-provider path and native AI mailbox path are distinct entry points; do not confuse their receipts/logs.
- `SCCommands.issue()` / `issueOne()` is the authoritative admission and state-change boundary for Living Fellows ordinary orders. It resolves the actor, checks membership/recruitment and remote/leader restrictions, requires a registered handler, handles drive preemption, runs the handler in a protected subsystem, rolls state back on refusal/error, and returns an accepted/rejected reason. For `follow`, the handler changes order state; acceptance alone does not prove that Sol has begun moving or completed following.
- `SCActionSupervisor` is the active-action arbiter, not the AI decision-maker. It holds per-actor ownership, applies priority and cancellation/preemption rules, dispatches urgent work, and `movementPermission()` can veto movement with `action_owned:<owner>:<action>:<phase>`. Navigation/locomotion and specialized LF actions perform the physical execution after order admission.

### Static behavior hazards
- Prompt conflict: `chat_service.py` SYSTEM_BASE still says movement orders such as follow/stay are currently issued from the Sol UI button. At the same time, the provider is given a `do_action` tool and a live action catalog. The deterministic regex handles only known phrasings; for unmatched natural-language variants, the stale system instruction can steer the model away from issuing a movement tool. This is a high-confidence source-level conflict, not proof that it caused a specific observed runtime failure.
- False completion framing: `_pre_intents()` dispatch results are presented to the provider as “Already done”; the bridge receives “[executed before your reply]”. Yet SolActions receipts only report request `ack`, `ok`, and a reason such as `pressed`, `issued`, or `started`; these do not confirm final world state. The existing plan already states `tool_result` means accepted/rejected, not completed. This can cause premature claims and make order retry/recovery unclear.
- No source change was made during this study. Next controlled repair: remove the stale “movement only by UI” instruction and replace it with an accurate tool-use rule, while distinguishing dispatched/accepted/running/completed/rejected results. Before implementation, add focused tests for both API/local and Sol Link prompt/receipt behavior; then validate a user-selected order in-game when an accessible world session is available.
- Runtime attribution remains open: a concrete failed request must be traced across input wording -> chosen deterministic/model action -> request ID -> SolActions/gateway receipt -> SCCommands reason/order state -> ActionSupervisor owner/phase -> observed movement/result. Only then can we say which gate blocked it.
## 2026-10-29 — Sol-owned action layer repair and static release candidate
Status: Sol Mind behavior contract STATIC/HARNESS PASS; post-change in-game validation PENDING.

- CORRECTION: the prior architecture note said no specific runtime order trace was available. The engineering log already contains a full 2026-10-25 runtime pass for `sol_cook egg` (Sol Link selected the custom plan; console reported `done:cook:all_steps_done`; cooked egg was removed before burning and the oven switched off). The user has now independently reconfirmed the same compound behavior. This proves the custom `SolPlanner` layer works in-game for that scenario; it does not prove the newer chat prompt patch has been runtime-tested.
- Design constraint clarified by the user: Sol is the high-level decision/planning layer above Living Fellows. Sol owns interpreting requests and compound plans; LF is reused as the lower-level implementation for navigation, timed actions, and standard commands. Do not replace LF behavior or let an obsolete LF-oriented prompt constrain Sol.
- Fixed `05_TOOLS/sol_mind/chat_service.py`: removed the stale instruction that movement orders are UI-button-only; explicitly defined Sol as the high-level action planner; clarified that accepted/started results are not completion; refined the preprocessed-action context; updated Sol Link's action-tag timing; append the actual game receipt after bridge actions; and only accept explicit completion results (including `done:*` or arrived/arrived) as completion evidence. Accepted vehicle transitions retain their actionable Arabic guidance.
- Added behavior tests BHV1-BHV11 for layer ownership, stale prompt removal, started-vs-completed, mixed outcomes, rejection, missing acknowledgement, bridge timing, and passenger-transition guidance. All 11 PASS. Python compile PASS. Existing G1-G21 goal/rescue tests PASS. Full behavior lab's source contracts, Lua 5.1 syntax (235 files/0 errors/1 existing warning), B1-B7, T1-T8, G1-G21 pass; overall release gate remains FAIL solely for WORK/LIVE parity in SolGPS.lua, SCAIToolGateway.lua, SCDriving.lua, with vehicle runtime gates still pending.
- No LF or Lua mod source was changed. `SCCommands.issue()` remains the ordinary LF command admission boundary and `SCActionSupervisor` remains the movement/action conflict arbiter; this patch changes Sol Mind's authority instructions and result reporting only.
- Created `01_WORK/RELEASE/SOL_2026-10-29_ACTION_LAYER_STATIC` with the 1,148-file Sol mod payload plus 15 Sol Mind runtime Python source files. Manifest has 1,163 entries; the mod tree matches WORK. No API keys, settings, certificates, or logs are included. Only `Sol/` is dropped into the PZ mods directory; deploy SolMind source through its existing installation. This is a static candidate, not runtime-approved.
- Runtime validation of the updated prompts and action-result notes remains pending. The previously confirmed connectivity across bridge, phone, API, and local model is recorded as user-confirmed PASS; do not repeat connection setup. Test order after deployment should compare one ordinary movement order through deterministic speech, API/local `do_action`, and Sol Link tag; confirm the order state and movement, then test an explicit refusal and confirm Sol reports it honestly. Preserve the already runtime-proven `sol_cook` compound path.
## 2026-10-29 — Architecture correction, verified compound plan, and action-layer fix
Status: Sol compound cooking is user-confirmed runtime PASS; Sol Mind prompt/receipt fix is STATIC/HARNESS PASS; post-fix world validation PENDING.

- CORRECTION: an earlier note said no exact runtime order evidence was available. `SOL_ENGINEERING_LOG.md` already records the 2026-10-25 `sol_cook egg` runtime pass: the custom Sol Link plan reached `done:cook:all_steps_done`, moved the cooked egg to Sol's bag before burning, and switched the oven off. The user reconfirmed the full sequence. Preserve this as evidence that Sol's own compound planner works; do not attribute this successful behavior to LF alone.
- Applied the Sol-owned layer correction in `05_TOOLS/sol_mind/chat_service.py`: removed UI-only movement instruction, clarified Sol plans/orders through its own action layer, distinguished accepted/started from completed, added honest outcome notes after Sol Link tags and goals, and preserved actionable Arabic messages for vehicle wait states. LF command/navigation/timed-action internals and mod files were not changed.
- BHV1-BHV11 PASS on both source and release-candidate Sol Mind; Python compile PASS. Full behavior lab source contracts, Lua 5.1, B1-B7, T1-T8, G1-G21 PASS. Overall gate remains FAIL only for existing WORK/LIVE parity changes in SolGPS.lua, SCAIToolGateway.lua, SCDriving.lua; vehicle runtime gates are still pending.
- New candidate `01_WORK/RELEASE/SOL_2026-10-29_ACTION_LAYER_STATIC`: 1,148 mod files + 15 Sol Mind runtime source modules, manifest 1,163 files. Mod SHA parity with WORK is exact; candidate Sol Mind chat_service SHA256 is `B23429DAA5F364503A03ACED25B7DAF6F4E45764766888037BB932E68CBD5138`. No credentials/configuration/certificates/logs/cache included.
- Latest process check: no Project Zomboid JVM is currently running. No in-game test has been performed after this prompt/receipt patch; previous UI-control approval timed out. Do not claim the new prompts improved live model behavior until verified in-game through deterministic speech, API/local action selection, and Sol Link action tags.
## 2026-10-29 — LF work blocking question: static result and evidence gap

Read-only source trace found that ordinary LF command admission (`SC.Commands.issueOne`) reaches `setOrder`/`markCommand`, which calls `SC.Decision.cancelWork("new_command")`; cancellation reaches `SC.NativeActions.cancelWork` and propagates a failure instead of silently claiming success. Sol's direct LF adapter calls this same command boundary and records `SolAct_State` ack/ok/reason. Separately, navigation asks `SC.ActionSupervisor.movementPermission` before request mutation, and locomotion checks again at dispatch; active action ownership can reject movement with owner/action/phase or queue urgent work. This makes residual physical-action ownership a plausible blocker, but no runtime log currently proves it occurred during a missed Sol command.

Accepted follow is only an order-state update; it does not itself guarantee movement. Move-to asks Navigation immediately, so its rejection can include the supervisor owner. Next useful trace must correlate request ID, LF cancellation result, supervisor snapshot/history, navigation/locomotion rejection, and observed position/order. The game was closed and the existing console tail contained no matching trace. No runtime behavior changed and no release payload was refreshed for this static investigation.
## 2026-10-29 — In-game SOL/LF command arbitration test (runtime evidence)

Status: TEST IN PROGRESS / cause UNCONFIRMED. An isolated Project Zomboid instance is running from `07_TEST/RUNTIME_TEST/profile`; the live mod installation is untouched.

- User clarified Sol is visible in the current scene. Confirmed visually in-game: SOL portrait/name UI is present and Sol's actor is physically in the loaded room. The runtime log confirms `SolOrders`, `SolActions`, `SolPlanner`, and `SolUI` loaded; the SOL Lua mod is active in this session.
- The current test-profile actions snapshot shows `set_scavenge=true`. Sol was visible seated and performing a local activity. This confirms autonomy is enabled/present, but does not prove it blocked a specific order.
- Two in-game `move_to` context attempts reached the `[SolDrive] LF command move_to` wrapper. Available logging only records command entry and `Driving.stop(player_order) -> true no_drive`; it does not record `SC.Commands.issue` acceptance/reason, `Decision.cancelWork` outcome, active ActionSupervisor owner, navigation permission/result, or a request-correlated position delta. The latest world snapshot still places Sol near x=10766.6,y=10271.5. Acceptance and movement therefore remain unproven.
- A manually written `tool_request` in the isolated mailbox was not consumed; outbox stayed at its existing `hello` in-flight message. The user's background service's game detector is incompatible with this direct Java launch, and the headless brain had stopped. This is a bridge/test-harness failure, not proof of in-game command rejection.
- Static seam: `SC.Commands.handleMoveTo()` requests navigation before `markCommand()` cancels Decision work. `SC.Navigation.request()` checks `ActionSupervisor.movementPermission()` before route mutation and can return `action_owned:<owner>:<action>:<phase>`. Plausible cause only; no request-specific runtime rejection was captured and no source behavior was changed.
- Next: obtain an end-to-end trace linking request ID, `SC.Commands.issue` accepted/reason, `Decision.cancelWork` outcome, supervisor snapshot, Navigation/Locomotion result, and actor order/position. Prefer the actual SOL action catalog/bridge with a working isolated test-profile brain, or instrument a test-only copy after the current runtime exits normally. Do not refresh/promote the release candidate until a reproduced failure has a runtime-verified repair.
## 2026-10-29 — User correction: inspect the existing Sol zone system before choosing farm scope

Status: game UI verified; exact saved farm-zone inventory not captured. No product source or release candidate changed.

- The user-provided screenshots show the existing in-world `Sol > Base Life` menu with `Show base plan` and `Start zone` categories, including farm, work, and other operational areas. This corrects the previous assumption that the project lacked a zone-selection foundation.
- Inspected the open isolated test scene: the camp-boundary overlay renders, and the game UI visibly reports the player as Invisible and God Mode. These settings were already present; they were not changed.
- Current `SolWorld_Snapshot.txt`: `plants=[]` for its configured radius-15 scan centered on player (10770.5, 10271.5, 0). This is strictly a local observation and cannot prove no crops exist in any registered farm zone.
- Static API `SC.BaseLife.visualRows()` returns saved `zoneRows`, but no runtime dump of that exact list has been obtained. The camp boundary alone does not prove a dedicated farm zone exists. Next: obtain the active Base Life `zoneRows`, census every registered farm-zone square and its `CFarmingSystem` plant state, then report actual seeds/tools and season-aware candidates.
- Garden plan must separate read-only inspection/report/approval from all farming mutations. No planting, harvesting, watering, or other work can begin until the player gives explicit approval. No runtime validation of a new compound command has occurred yet.

## 2026-10-29 — Explicit “Move Here” order arbitration repair
Status: WORK + isolated test-profile source updated; Lua 5.1 syntax PASS; in-game movement acceptance/reach test PENDING.

- Traced the context-menu action to `SCUIContext.lua` -> `SC.Commands.issue(..., "move_to", squarePayload)` -> `SCCommands.handleMoveTo()` -> `SC.Navigation.request()` and persisted `state.order="move_to"` / `tacticalTarget`. The clicked square is passed as the destination; the diagnosed selection issue was that `SCDecision.evaluate()` assigned this explicit player order score 56, allowing higher-scored routine logistics/autonomy to take over before arrival.
- Changed the `move_to` tactical candidate score to 95 while leaving other tactical order scores unchanged. The selector explicitly chooses an emergency candidate before a non-emergency request. In `doTactical`, retained the recognized `ordered_move` action identity and assigned ordinary explicit movement traffic priority 60 (expedition combat travel remains 90), so move-to outranks routine/default traffic while combat priority 80 and emergencies retain precedence.
- An intermediate `player_move` action label was rejected during review and reverted: navigation ownership/native movement code recognizes `ordered_move`, so changing that action identity could break the existing execution contract.
- Copied the final WORK file into the isolated test profile. WORK/test-profile SHA-256 match; targeted Lua 5.1 syntax check and `git diff --check` pass. Existing test-profile backup remains at `07_TEST/RUNTIME_TEST/runtime-evidence/20261029_move_here_fix/SCDecision.lua.before`.
- Launched the test profile and entered its saved world. Screenshot confirms Sol's portrait/actor and the UI reports Invisible and God Mode. The first-entry Survival Guide covers the view and did not close through repeated coordinate/keyboard attempts; consequently no `Move Here` action was issued and no arrival claim is made. The fix remains unverified in live gameplay; do not promote it to a release snapshot until the context-menu command demonstrably routes to and reaches the exact clicked square.

## 2026-10-29 — CORRECTION: player Move Here is an unconditional immediate order
Status: Source updated; targeted Lua 5.1 syntax PASS; in-game movement test PENDING.

- Rejected the prior rule that allowed combat/emergency candidates to outrank `move_to`. The user's explicit direction is that when Sol is in danger, Move Here may be the escape command and must not be vetoed by Sol's autonomous combat or survival selection.
- `move_to` now creates a distinct `tactical:player_move` emergency candidate with score 1000. `selectWithHysteresis()` selects that candidate before safety, combat, or routine candidates. The accepted move request uses `urgent`, `emergency`, and `survivalCritical` flags plus traffic priority 100, allowing it through the ActionSupervisor/navigation urgent path; it retains action identity `ordered_move` and the exact stored `tacticalTarget`.
- Starting a player move interrupts Sol's autonomy. Existing command admission still rejects an invalid/unloaded/blocked destination or an unavailable navigation subsystem; once accepted, the explicit route wins arbitration and is renewed toward the selected square. This is strict arbitration priority, not a claim that inaccessible geometry can be traversed.
- Targeted Lua 5.1 syntax and `git diff --check` pass. No live gameplay acceptance/reach evidence was collected in this side conversation; keep release promotion gated on that test.

## 2026-10-29 — Separate passenger boarding, driver-seat preparation, and GPS driving
Status: WORK and isolated test profile updated; Lua 5.1 syntax PASS; live vehicle/route behavior PENDING; no release snapshot promoted.

- Reworked the Sol context-menu meanings in `SolOrders.lua`: `اركبي السيارة` now requests passenger seat 1 explicitly through `SC.Vehicle.preflightBoard`, `boardingSquares`, and `board`, so Sol walks to that door and refuses when the front passenger seat is unavailable instead of silently choosing a rear seat. If the exact-seat API is missing, it reports the limitation rather than falling back to an unspecified Living Fellows seat.
- Renamed the old `خذي المقود` item to `سوقي السيارة`; it uses the existing verified `SolGPS.gpsTakeWheel` / `SC.Vehicle.boardDriver` path and prepares Sol at the driver seat without selecting a destination or starting a route.
- Removed the ambiguous `سوقي لهون` command from the Sol context menu and the GPS-map right-click menu. A map point is now a destination selection; the GPS panel's `سوقي` button starts the route and reports `no_destination` when no point is selected. This panel action no longer doubles as take-wheel and no longer forces solo mode. The saved-home menu entry now stages home on GPS and asks the player to start from the GPS panel; Sol Mind's separate `goHome` action remains available.
- Incremented diagnostic module versions to SolOrders 0.9.1 and SolGPS 0.5.1. WORK and isolated test-profile copies match exactly: SolOrders SHA256 `0AAAD6B9241F23D2E769A3763DA949FE654400B7FE58DEF59B25596E5ED95077`; SolGPS SHA256 `56C4BCD8997B21B80A8E86EE521589ACC2439FAFA94724687738153B894E4E37`. Both files pass targeted Lua 5.1 syntax; `git diff --check` passes.
- Backups: Git-baseline copies under `03_BACKUPS/20261029_sol_vehicle_menu_before`; the prior isolated-profile copies are under `07_TEST/RUNTIME_TEST/runtime-evidence/20261029_vehicle_menu_repair`. The running game had already loaded its old Lua files before these copies were updated; restarting/reloading the test profile is required for gameplay validation. The user took UI control while the startup guide was blocking the world, so no vehicle command was issued. Driver seat acquisition, seat-1 boarding, GPS route start, and route completion remain unverified in this runtime. Keep WORK isolated and do not refresh the release payload until those behaviors pass in-game.

## 2026-10-29 — CORRECTION: nearby and clicked-vehicle boarding

Restored `اركبي السيارة` as the nearest-car passenger order (8-tile radius) even when the player is on foot. Added `اركبِي هي السيارة` only when right-click resolves a concrete vehicle, and pass that exact instance to the existing seat-1 boarding flow. Updated the Sol Mind action fallback and LF command admission so the older in-vehicle-only gate cannot reject nearby/explicit targets. SolOrders v0.9.3. Synced four changed Lua files to the isolated test profile with before-copies in `07_TEST/RUNTIME_TEST/runtime-evidence/20261029_sol_nearby_target_board/before/`. Static Lua 5.1 syntax passes and WORK/test-profile hashes match. CORRECTION: Project Zomboid was already active as `java.exe` in a world despite the earlier narrow process query returning none; the live JVM has old Lua already loaded. World time was paused; no Sol order/restart was issued. CUA then detected user input in the game window, so I stopped UI control. Runtime validation awaits a safe reload; release snapshot unchanged.

## 2026-10-29 — VSGirl Sol-only test package prepared
- Correction confirmed: saved companions are reconstructed by `SCPersistence.restoreAt()` through `SC.Actor.beginSpawn()`, which reaches `finalizeSpawn()`. The Sol marker is therefore set for restored Sol as well as a newly spawned Sol; no periodic world scan is needed.
- Rebuilt the narrow Java patch from the preserved original candidate JAR using `ScopeVSGirlBodyToSol.java`. The rebuilt JAR is byte-identical to WORK: SHA-256 `54A8DE3CEB813843E5C2DAC9F9535992E21D17102F9BC23B888E1463F7374B5B`. Its exception requires both `SCNativeCompanion` and `SolAppearanceVSGirlBody=true`.
- Refreshed `01_WORK/RELEASE/SOL_2026-10-29_UNIFIED_APPEARANCE_BUNDLE/Sol/42` from current WORK and copied it into the isolated profile. Each Sol payload has 2,522 files; the patched JAR hashes match.
- Created `07_TEST/RUNTIME_TEST/profile/Zomboid/Saves/Sandbox/2026-10-29_17-43-08_VSGIRL_SOL_ONLY_TEST` by copying the appearance-reference baseline. Only the clone's `mods.txt` was edited: SPNCC, Tomb body/textures/fit/hair/wardrobe sources are disabled so the candidate package is the appearance source; Sol and ZombieBuddy remain enabled. Original and baseline saves are untouched.
- No Project Zomboid process was running during staging, and no game was launched. Lua 5.1 syntax gate: 238 files, 0 errors, one pre-existing `SCNavigation.lua` literal-backtick warning. Runtime appearance, Sol UI, ordinary-female preservation, and fresh log review remain for the user's in-game test. No STABLE/LIVE promotion.
## 2026-10-29 — Test handoff readiness
- Added `07_TEST/RUNTIME_TEST/launch_vsgirl_sol_only_test.ps1`. It validates the isolated clone/mod list and refuses to launch if any PZ process is already running; it invokes the existing logger-backed launcher with the prepared profile.
- Refreshed and verified the release candidate manifest: 2,538 entries, zero missing/changed files. Candidate Sol payload matches WORK and isolated profile file-for-file; 2,522 files each. The JAR rebuild is byte-identical; 378 XML and 8 JSON files parse; no shared Tomb female-body override files remain.
- The user-facing PZ executable was observed running again after staging (PID 18596); this assistant did not launch it. Do not start the isolated test until the user closes the current game; the launcher enforces this.
## 2026-10-30 — Appearance test exposed a Sol body-slot API error
- The isolated save reached Sol's Lua load path, which logged `expected argument of type ItemBodyLocation, got String` at `SCIntegratedAppearanceBodyLocations.lua`. The stack points directly to Sol's vendored appearance support, not an unrelated mod.
- Build 42 bytecode confirms `BodyLocationGroup.getOrCreateLocation`, `moveLocationToIndex`, and `setMultiItem` all require `zombie.scripting.objects.ItemBodyLocation` objects. Updated the integration to register each `SPNCC:*` name through `ItemBodyLocation.register()` and pass the resulting object to these APIs.
- Corrected WORK and the unified appearance candidate; refreshed the release manifest. Lua syntax check passes (238 files; 0 errors; one pre-existing warning). Added `05_TOOLS/sol_appearance/check_body_locations.py`; its Lua mock verifies all nine custom locations are registered and all three API methods receive typed objects.
- The currently open game process has already loaded the old Lua file and still shows a black load screen; the runtime profile has not been updated during this active session. The body-slot correction is not yet runtime-verified. After this session exits, copy the corrected file to the isolated profile and rerun the same cloned save. STABLE, LIVE, and original saves remain untouched.
## 2026-10-30 — Runtime crash diagnosed and corrected
- The first isolated load of `2026-10-29_17-43-08_VSGIRL_SOL_ONLY_TEST` crashed while entering the world. `console.txt` and `Logs/2026-10-30_00-25_DebugLog.txt` identify an unhandled JVM `VerifyError` in `localplayerbody.PlayerBodyModels.controlled`, reached from `ModelManager.getBodyModel` during `IngameState.enter`.
- The verifier evidence showed `KahluaTable.rawget` returns `Object`, while the patched bytecode invoked `Boolean.equals` as if that receiver were a `Boolean`. This was the fatal blocker; the repeated `Spongie's Character Customisation.applyVisual` null-ID errors were secondary fallout from the invalid body-location registration/failed model path and remain to be rechecked after a successful world load.
- Corrected the reproducible ASM patcher to invoke `Object.equals(Object)` on the `rawget` result. Rebuilt from the preserved pre-patch SolCombined JAR; `javap -v` confirms the stack-compatible call and the Sol-only marker gate. The repaired JAR SHA-256 is `2D8FC4841DDE68B241A21FA9A1ECB52C4D3B40E13A416A680B33A9D29FFC21BC`.
- Replaced the faulty JAR in WORK, the unified appearance candidate, and the isolated test profile only. Refreshed candidate SHA-256 manifest (2,538 entries; zero mismatches). STABLE, LIVE, and the original save were not changed.
- Relaunching the isolated test now. Appearance is still pending in-world visual confirmation and review of a fresh post-fix log.

## 2026-10-30 — In-world error pass and test-save routing correction
- The user reached the world with Sol's UI visible; the Java VerifyError did not recur. On graceful close, the process remained responsive through frame 48,089 and exited after the user stopped the game.
- The next log pass found two Sol-owned appearance issues: the Java marker check called `rawget(...).equals(TRUE)`, which threw when ordinary actors had no marker; and `media/registries.lua` plus `SCIntegratedAppearanceBodyLocations.lua` registered the same SPNCC tags/body locations more than once. The Java patch now calls `Boolean.TRUE.equals(rawget(...))`; registry lookups reuse `ItemTag.get` / `ItemBodyLocation.get` and only register absent IDs; the body-location setup reuses the same objects for `setMultiItem`.
- A focused Lua mock check passes: all nine locations resolve to typed values, no duplicate registration occurs, and group methods receive those values. `javap` confirms the null-safe Boolean receiver. Updated WORK, the unified appearance candidate, and the isolated runtime payload; candidate manifest has 2,538 entries.
- Important test correction: the just-closed game had loaded `2026-10-29_17-43-08_APPEARANCE_BASELINE`, not the isolated `..._VSGIRL_SOL_ONLY_TEST` clone. This is confirmed by `profile/Zomboid/latestSave.ini` and the source appearance mods in that baseline's `mods.txt`. The original save remains untouched. Updated only the isolated profile's `latestSave.ini` to select `2026-10-29_17-43-08_VSGIRL_SOL_ONLY_TEST`; its mod list excludes SPNCC/Tomb/FH sources.
- The isolated test is being relaunched with the corrected payload and selected clone. The previous in-world screenshot is not evidence of Sol-only body isolation; runtime appearance comparison remains pending.

## 2026-10-30 — Isolated profile cleanup and external UI error attribution
- The single Lua error visible during the prior startup came from `ExtraFliersB42` (`NewMediaDefinitions.lua:6`): the mod inserts into `PrintMediaDefinitions.Fliers`, which is nil in Build 42's base definition. This is outside Sol. Removed only this unrelated mod from the isolated profile's default list for a quieter appearance test; the installed Workshop copy and user's normal profile were not edited.
- The isolated profile default list also had `DetailedPlayerModelFRedux`, `DetailedPlayerTexturesFDOLLB42`, and `FH` enabled even though the cloned save's `mods.txt` excluded appearance sources. Removed them from the isolated profile default list and preserved the original as `default.txt.before_sol_only_appearance_20261030`.
- Hardened the test launcher: it now requires the isolated clone in `latestSave.ini` and rejects appearance-source IDs in both profile defaults and save mod list. Launcher validation passed by starting the new test session.
- Current startup is stable at the menu. No ExtraFliers exception, duplicate SPNCC registry error, `BodyLocation.isId` NPE, or PlayerBodyModels verifier error has appeared in this run. The selected clone has not entered the world yet, so Sol UI and appearance are still pending.

## 2026-10-30 — Clean isolated world load, visual review pending
- The corrected isolated test clone `2026-10-29_17-43-08_VSGIRL_SOL_ONLY_TEST` reached the world with the cleaned profile default list and the unified Sol payload (2,522 Sol/42 files, parity checked against WORK and candidate).
- Fresh runtime evidence `07_TEST/RUNTIME_TEST/runtime-evidence/20261030_005804` records `[SolUI] ready v0.2.0`, `[SolAppearance] VSGirl body scoped to Sol (size=L, nativeHead=false)`, and VSGirl private surface initialization. Sol diagnostics report one living Sol actor and spawn gate ready.
- In this run the targeted error counts are zero: `VerifyError`, duplicate SPNCC registry IDs, `SCIntegratedAppearanceBodyLocations`, `BodyLocation.isId`, and Extra Fliers `NewMediaDefinitions.lua`. The game remains responsive in-world through at least frame 3,300 in the inspected output.
- Runtime appearance/UI is not marked passed from logs alone. Await the user's in-scene visual confirmation of body, face, hair, and Sol UI before deciding any next appearance adjustments. STABLE/LIVE remain untouched.

## 2026-10-30 — User visual acceptance for Sol appearance
- The user visually confirmed in the isolated world that Sol's body, face, and hair match the requested appearance. Runtime logs also show Sol UI ready and the VSGirl route scoped to the marked Sol companion.
- The user-confirmed Sol appearance check is passed. Broader isolation from ordinary female actors remains supported by the marker-gated Java selector and disabled source appearance mods in the isolated profile; a separate ordinary-NPC visual comparison was not performed.
- Keep this as a local appearance candidate only. Do not promote to STABLE/LIVE until any desired ordinary-NPC comparison and the user's release decision.

## 2026-10-30 — Combined SPNCC/Tomb test freeze
- The user force-closed the combined player-appearance test after the world froze. Full isolated DebugLog evidence shows a repeated per-frame `BodyLocation.isId(BodyLocation.java:69)` null-ID exception, not hundreds of distinct errors.
- Root cause is strongly indicated by duplicate registry ownership: source SPNCC unconditionally registers IDs that Sol's standalone registry also registers. Added a guard to `media/registries.lua`: when SPNCC is active, SPNCC owns those IDs and Sol skips its duplicate registration. Standalone Sol still registers the six tags and nine body locations when SPNCC is absent.
- Applied identical guarded file to WORK, candidate, and isolated runtime; verified matching SHA-256. Focused registry ownership test, existing typed-location test, Lua syntax check, launcher syntax check, and release manifest check pass (2,538 entries, zero mismatches).
- The wrapper restored the isolated profile's prior `latestSave.ini`. Original save and previous failed test clone remain preserved. A fresh retry clone with SPNCC/Tomb/FH appearance sources is staged; runtime retest is pending. No STABLE/LIVE promotion.
- Retest checkpoint: launched at 02:14 with retry clone and `-debug`; Java PID 22324 exited at 02:15 before `READY_MARKER_OBSERVED` and before world entry (exit code unavailable). During the short startup there were zero `BodyLocation.isId` and `GameWindow.frameStep` matches. The log contains font texture load errors and a `Large Bucket` name sanitization error; their relevance is not established. `latestSave.ini` was restored to the Sol-only clone. Evidence: `07_TEST/RUNTIME_TEST/runtime-evidence/20261030_021428`, `profile/Zomboid/Logs/2026-10-30_02-14_DebugLog.txt`. Investigate early exit first next session; do not claim the guard runtime-verified.
- User-requested relaunch: started the same isolated retry clone at 22:24 with `-debug` (PID 8616). At the first log check the process responded normally and there were no `BodyLocation.isId`, `GameWindow.frameStep`, SPNCC registry, `[SolUI]`, or `[SolAppearance]` entries yet. The user is to enter the world; keep monitoring `profile/Zomboid/Logs/2026-10-30_22-24_DebugLog.txt` before evaluating the fix.
- Display correction after user report: isolated profile `options.ini` had `borderless=false`; this caused the game to open windowed and likely recapture the pointer when focused. Changed only the test profile to `borderless=true`, `fullScreen=false`, `lockCursorToWindow=false`, then relaunched the retry clone. Current window is borderless/full-screen-sized, Java process responds, and cursor is visibly free. Did not invoke the mouse-toggle hotkey. Current run log: `profile/Zomboid/Logs/2026-10-30_22-26_DebugLog.txt`; no Sol/appearance lines have appeared yet, so world-load retest remains pending.

## 2026-10-30 — Steam save mod list synced to appearance test
- User asked to enable exactly the mods active during the Sol/body appearance test in the normal Steam game without launching it.
- Copied the 177 `mod = ...` entries from the isolated retry clone `2026-10-29_17-43-08_VSGIRL_PLAYER_APPEARANCE_TEST_RETRY` into the active Steam save `2026-10-29_22-56-55` at `%USERPROFILE%/Zomboid/Saves/Sandbox/2026-10-29_22-56-55/mods.txt`. Preserved the normal save's `maps` section and version header.
- Exact ordered mod-ID comparison reports 177 entries on both sides and zero differences. No game process was running at completion; no game was launched. The global `mods/default.txt` and other saves were left untouched.
- Before-state backup and test source are in `03_BACKUPS/steam_modlist_sync_20261030/`.

## 2026-10-30 — Dedicated Sol local launch folder created
- Created `01_WORK/RELEASE/SOL_2026-10-30_LAUNCH` as the canonical local launch package requested by the user. It contains the complete B42 mod at `Sol/42` and the current companion app payload at `SolMind/`, plus README, release tracking, and SHA-256 manifest.
- Sol payload was copied from the existing unified appearance candidate after a complete hash comparison confirmed it is identical to current `01_WORK/Sol/42` (2,522 files, zero missing/different/extra). SolMind matches `SOL_2026-10-29_CHAT_RESIZE_SELECTION/SolMind` (16 files, zero differences).
- Regenerated and verified 2,538 manifest entries. `Sol/42/mod.info` is present with mod ID Sol, Project Zomboid 42.21.0, `SolCombined.jar`, and required ZombieBuddy 2.3.3+. Omitted the stale root-level `mod.info` that points to `SurvivorCompanionBridge.jar`; the versioned Build 42 metadata is authoritative.
- The package includes the body/face/detail/hair integration and SPNCC registry-ownership guard. No game was launched. The combined SPNCC/Tomb retry remains runtime-pending, documented in the package tracking file; this is a local test candidate and not a claim of verified combined-stack stability or public redistribution rights.
- Future accepted Sol mod changes should refresh this canonical folder and regenerate/verify its manifest.

## 2026-10-31 — Sol first-spawn desert kit and vanilla replacement outfit
- Changed `01_WORK/Sol/42/media/lua/client/SolDress.lua` to give the first Sol incarnation in each world a desert military helmet, jacket, trousers, bullet vest, desert ALICE pack, desert army boots, and equipped metal baseball bat.
- Persisted the one-time grant flag in global world ModData; subsequent Sol incarnations fall back to the existing vanilla outfit. No other companion outfit path was changed.
- Updated the canonical launch folder and regenerated its 2,538-file manifest. The game was not launched; appearance, hand equip, and post-death replacement remain runtime-pending.

## 2026-10-31 — Complete Sol mod GitHub sync preparation
- Compared WORK and the launch package: 2,522 files, no content differences before version metadata alignment.
- Bumped mod.info to 0.26.41 in both locations; refreshed release documentation and manifest.
- Planned commit scope: full  1_WORK/Sol/42 only, including ignored but required SolCombined.jar; excludes SolMind, test outputs, and unrelated documentation.
- GitHub repository is private. Runtime behavior of the loadout and combined appearance stack remains unverified.


## 2026-10-31 — Installed current Sol and cursor setting repair
- Replaced the active Steam-profile Sol/42 folder with the launch package 0.26.41 while Project Zomboid was closed. Retained the old installation intact under Zomboid/mods_backups. 2,522 files verified with zero SHA-256 mismatches.
- Set showCursorWhileAiming=true in Zomboid/options.ini; borderless=true and lockCursorToWindow=false were already set. Backed up the original options.ini under 03_BACKUPS/mouse_cursor_20261031.
- iewpoint-live.properties retains keys.cursor=MOUSE3 (free/locked toggle); user should verify cursor behavior in the same save after launch. No game restart/runtime validation performed.

## 2026-10-31 — Main-menu cursor fix correction
- User clarified the issue is the standard menu pointer missing in Borderless, not the aiming cursor.
- Set lockCursorToWindow=true in Zomboid/options.ini and restored showCursorWhileAiming=false. Borderless remains enabled; no mod behavior or performance settings were changed.
- The current Project Zomboid process was already running when the option changed; restart and visual confirmation remain pending.

## 2026-11-06 — Sol / bridge protocol compatibility

- Diagnosed the new-world case where the Sol interface loaded but no actor appeared: Lua expected `42.21-isocompanion-21`, while the installed Living Fellows 0.26.67 bridge reported `42.21-isocompanion-24`; runtime explicitly disabled actors and rejected spawn.
- Prepared release candidate `01_WORK/RELEASE/SOL_2026-11-06_BRIDGE24_COMPAT`. It aligns the Lua handshake and both bundled copies of `survivorcompanion.bridge` to protocol 24, preserving Sol's `localplayerbody` classes.
- Static API comparison found no removed public methods from `SCBridge` or `SCNativeCompanion`; four methods were added in the upstream bridge.
- Runtime remains pending. The game was open during preparation; only install after it exits, then confirm `actors=enabled` and accepted Sol spawn before behavioral testing.
- 2026-11-06: Installed Sol 0.26.42 bridge-protocol-24 into the normal Steam profile at `C:\Users\JAMAL\Zomboid\mods\Sol` after verifying the game was closed. All 2,528 files match the release candidate by relative path and SHA-256. Runtime spawn check pending the user’s next launch.

- 2026-11-06: Cursor issue correction: `showCursorWhileAiming` was briefly changed in error, then restored to `true`; `options.ini` now matches its pre-change backup byte-for-byte, preserving the aiming cursor and menu pointer. Static evidence found a real MMB binding collision: OldPoint was also bound to `MOUSE3` for overhead-camera rotation while Viewpoint uses it for cursor capture. Backed up `viewpoint-live.properties` and moved only `oldpoint.cameraRotationKey` from `MOUSE3` to `MOUSE5`. Runtime confirmation is pending.
- 2026-11-06: User video clarified the actual symptom: after Viewpoint releases the UI mouse and captures it for first-person look, mouse input/camera control works but the rendered pointer sprite stays frozen onscreen. This is not the aiming reticle. Reverted our cursor experiments byte-for-byte to the saved pre-change baselines: `options.ini` (`showCursorWhileAiming=true`, reticle settings unchanged) and `viewpoint-live.properties` (`keys.cursor=MOUSE3`, `oldpoint.cameraRotationKey=MOUSE3`). Saved the immediately prior state as `03_BACKUPS/cursor_center_20261106/*pre_reset`. No Windows pointer settings were changed. Runtime verification remains pending.

## 2026-11-06 — vehicle detection, boarding, and GPS handoff
- Changed Sol nearest-car detection from 8 tiles/player-anchored to 30 tiles/Sol-anchored; driver discovery radius raised from 12 to 30. SCCommands fallback now also uses 30 tiles from the companion.
- Selected-car menu passes the clicked vehicle unchanged through SolOrders. Both Sol direct action routes now use SolOrders boarding so retries and completion status share one owner.
- Player-occupied door squares are not valid approach targets; boarding and driver jobs have a 90-second approach budget.
- Added Arabic vehicle completion phrases to the Sol Mind claim guard so “I am driving / inside the car” is marked unconfirmed until game completion is observed.
- Static checks: Lua 5.1 parser 225 files / 0 errors / 1 existing warning; Python AST parse passed. In-game seat-entry, GPS departure, route movement, and arrival were not verified.
- Synced the five Lua payload files to both the 2026-11-06 Bridge24 candidate and canonical launch folder. The canonical launch manifest was regenerated; gameplay acceptance remains pending.

## 2026-11-06 — GPS drive dispatch fix
- Evidence: 2026-11-06 19:09 DebugLog at 19:52 records `take the wheel -> true moving_to_wheel`, previews at 19:51 and 19:54, and no `driving to` event. A `follow` command at 19:52 superseded the pending wheel task. Static inspection found `sol_drive` in the action catalog but absent from `U.runAction`; `sol_take_wheel` only invoked `gpsTakeWheel`.
- Added `O.driveDestination()` and routed `sol_drive` through it. It starts the current GPS route using the shared vehicle state machine, reports no destination as failure, tracks movement toward the driver seat, and says to board when the route is armed and waiting. The action catalog now distinguishes “take wheel” from “start trip.”
- Lua syntax scan passed: 225 files, 0 errors; one pre-existing warning in `SCNavigation.lua`. No runtime vehicle test yet. Details: `DOCS/GPS_DRIVE_ACTION_FIX_2026-11-06.md`.

## 2026-11-13 — dedicated helicopter examiner (s131)
- The stopped LAB session showed `[SolHeliTrace]` telemetry but no `[SolHeliRecorder]` marker and no `SolHeliFlight_Record_*.txt`. The old recorder harness therefore did not establish the in-game capture path; prior notes calling that runtime PASS are corrected below.
- Added a focused `SolHeliExaminer.lua` and connected it directly to the observed Aviation Core input wrapper in `SolHeliGPS.lua`. It is passive, Lab/switch gated, restricted to the local pilot seat, samples controls plus world position/altitude, ground/AGL, vertical rate, speed and heading, and writes a timestamped file with explicit start/heartbeat/close markers. Car recording remains unchanged.
- Backup: `08_RUNTIME_TEST/s131_heli_examiner_backup_20261113` contains pre-change WORK and LAB copies of the touched Lua sources.
- Offline evidence: s129 wiring harness, legacy s128 sampler harness, and s129 flight analyzer all pass. Runtime capture is still unverified; do not request another flight until the loaded game log shows `READY`, then `CAPTURE_STARTED`, and the file exists in the LAB profile.
- Runtime update: the official LAB launch passed all gates; game reached its startup scripts and emitted `[SolHeliExaminer] READY lab_only=true file_api=true` at 2026-11-13 02:22:35. This proves module/API readiness only. The game is at the main menu; capture start and the output file await pilot-seat entry, so no takeoff is authorized yet.

## 2026-11-13 — coordinated helicopter guidance (s132)
- Reviewed the manual flight capture and its paired `SolHeliTrace` transitions. Jamal's demonstrated correction combines A/D yaw with same-side LEFT/RIGHT bank while using UP to advance when aligned. The old GPS controller used yaw and pitch but did not coordinate bank.
- Updated `SolHeliGPS.lua` to pair automatic yaw and bank on course corrections, preserve manual input precedence and the existing climb/forward thresholds, and release turns with a 0.18 rad hysteresis threshold after engaging beyond 0.30 rad. Added transition-only guidance logs. Controller version is 0.4.3.
- Updated the LAB examiner to include both heading components and durably close its file when the pilot exits; it remains passive and LAB-only.
- Offline checks: authorization/control mapping, both turn directions, straight-course release, off-axis kinematic destination, landing, examiner wiring, and flight analyzer pass. The flight simulation is not a substitute for AviationCore physics.
- Live runtime acceptance remains pending on save `2026-11-12_18-08-44`: verify engine readiness, climb, GPS movement on both map axes, marker arrival, commanded landing, and absence of Lua/AviationCore errors. No release or Steam files changed.

## 2026-11-13 — helicopter no-movement fix (s133)
- The failed live run reached pilot seat and engine-ready but never logged altitude reached or GPS guidance; the examiner showed a fixed position. AviationCore obtains flight altitude through `getWorldPos(...):z()`, while Sol used `getZ()` (tile/floor level), blocking the altitude-ready gate.
- SolHeliGPS now uses world-position Z for altitude/status, logs GPS control transitions with worldZ/groundZ/targetZ/distance, and treats repeated starts as continuation instead of restarting climb. Controller version 0.4.4.
- Tests deliberately separate tile `getZ()` from world altitude; authorization, altitude gate, both turn directions, repeated start, kinematic off-axis arrival/landing, UI, recorder, and analyzer checks pass.
- Installed to SOL_LAB only. Final rollback: `07_TEST/SOL_LAB/_backup/20261113_035249_before_s133_heli_world_altitude`. No main Steam profile, release, save, or switches changed.
- Live verification remains pending. Exact LAB steps: `DOCS/S132_HELICOPTER_LIVE_TEST.md`. Kinematic simulation is not proof of in-game AviationCore movement.
- No Steam/main profile, save, release, or switches changed.

## 2026-11-13 — AviationCore pilot bridge hardening (s134)
- Reviewed the live 03:55 LAB log after the user reported the engine started but the helicopter stayed still. Sol reached seat 0; the player was in seat 1; GPS accepted a destination and logged engine-ready, but no input/altitude/guidance transition appeared. On shutdown AviationCore persisted the helicopter at 7523.461,9274.734,0.282, still grounded. The first attempt was explicitly stopped at 04:01:01; the second destination was followed by engine-off at 04:01:17.
- AviationCore source confirms `FlightRuntime` calls global `getPlayer()` and rejects non-seat-0 actors before reading `HelicopterInput`. The current failure points to the Sol-to-local-pilot bridge, not the altitude gate alone.
- WORK/LAB controller 0.4.5 scans stack levels 3–6 for the exact FlightRuntime source path; non-AviationCore callers still receive the actual player. The first successful dispatch logs `FlightRuntime pilot bridge routed local pilot to Sol` once per flight.
- Lupa stack-source regression test, authorization, world-altitude climb gate, both GPS turn directions, and s121/s124/s125/s127/s128/s129 aviation tests pass. Kinematic replay passes; it is not Project Zomboid runtime proof.
- Installed to SOL_LAB only after `GameThread exited`; switches and authority file unchanged. Rollback: `07_TEST/SOL_LAB/_backup/20261113_041319_before_s134_flight_runtime_bridge`. WORK/LAB SHA-256 match (`f6104d467267fb060a8fd8a4fce5e0cd3edff6161e28cf1996d05305fd36d3a1`). Live movement acceptance remains pending.

## 2026-11-13 — SOL_LAB restarted for s134 runtime test
- `launch_lab.ps1 -CheckOnly` initially refused because the LAB profile lacked its lab-only `SolLab.lua` authority marker. Copied `07_TEST/SOL_LAB/SolLab.lua` into the isolated LAB mod profile only; it was not added to WORK or release.
- Preflight then passed: Java linkcheck, patch access, Kahlua tonumber, jar-call and model-card checks. Existing warning: 20 jar-call warnings; release reminder says LAB is newer than installed release.
- First sandboxed start failed before the menu because Java loopback was denied (`Unable to establish loopback connection` in ZombieBuddy/SteamWorkshop initialization). Restarted the same LAB launcher outside the sandbox; Project Zomboid and its paired Sol Mind process are now running against `07_TEST/SOL_LAB/profile/Zomboid/Lua`.
- Sol Mind heartbeat is fresh and its session tools loaded. The game log has reached `Game booting`; the mailbox outbox has not yet emitted a fresh session frame. Wait for the world to load before counting mind/game handshake or helicopter movement as runtime PASS.

## 2026-11-13 — summon helicopter action (s138)
- Added exact Mind request `سول فيكي تجيبي هليكوبتر` and the queued acknowledgement `أكيد بقدر`. New action uses the player's last driven registered helicopter, with a registered UH-1B fallback.
- World creation is server-authoritative. It searches a bounded safe outdoor footprint on demand, finalizes AviationCore parts/manual, creates a key, fills and reads back JetFuel capacity, and emits `[SolHeliSpawn]` result diagnostics. A queued chat reply does not assert successful spawn.
- Added action documentation to the human model card and ledger; backups are recorded in `DOCS/SOL_LEDGER.md`. Focused contract tests pass 3/3; card gate passes with one prior warning.
- Runtime verification is pending; require the isolated launcher's process checks to pass, then verify a single nearby aircraft, model, key, full fuel, and a successful server result in the LAB log.
- Launch evidence: process-visible preflight passed, then the documented LAB launcher started the isolated profile and Sol Mind against save `Sandbox/2026-11-12_18-08-44`. Log `07_TEST/SOL_LAB/profile/Zomboid/Logs/2026-11-13_17-29_DebugLog.txt` confirms `[SolActions] ready`, `[SolHeliSpawn] server request listener ready`, and `[SolHeliGPS] AviationCore input adapter ready`; the settings state reports `active=api:custom/qwen3-4b-2507`. No s138-specific Lua failure was observed. User phrase and actual spawn/fuel verification still await in-world interaction.

## 2026-11-13 — Kahlua multiple-return conversion fix (s139)
- The first live request successfully routed through Sol Mind and returned the exact acknowledgement. Server handling then failed at `findSpawnSquare`: `invoke()` returned value plus success boolean, and `tonumber(invoke(...))` supplied the boolean as Kahlua's optional base argument, leading to `Double`→`String` ClassCastException.
- Added `numberMethod()` to capture only the first return, and replaced all numeric getters in the server spawn path. Backed up source/LAB copies under `08_RUNTIME_TEST/s139_kahlua_tonumber_fix_20261113`; both updated copies hash to `EB9F485C66BD5EE2465AB8981D418F401BE9C6D24110011E99FFAB9D9F6F35F1`.
- PASS: focused tests 4/4 and the game's Kahlua parser 1 file / 0 syntax errors. The old live game session has ended; a new runtime attempt is needed to verify safe-square search and fueled spawn.
- The user's separate “secret weapon” message was followed by “لا”; no weapon feature was added or changed.

## 2026-11-13 — AviationCore return-value binding fix (s140)
- Runtime trace showed the summoned `BaseVehicle` and `Base.CarKey`, then failed at `SolHelicopterSummonServer.lua:130` with `attempted index: FinalizeVehicle of non-table: null`.
- Installed AviationCore source and its stock `HelicopterSpawn.lua` confirm the factory and manuals APIs are returned from `require` and stored locally, not exported as global names. The summon script had ignored those returns; the registry's return was ignored too.
- Bound the returned modules in WORK and LAB, guarded finalizer invocation, and added explicit failure diagnostics. Backup: `08_RUNTIME_TEST/s140_aviationcore_module_binding_fix_20261113`.
- PASS: focused tests 5/5, project Lua syntax checker 0 errors, Kahlua `tonumber` gate clean, WORK/LAB file hashes match. In-game verification is pending because the running session has the old script loaded; restart before testing fuel/key finalization.

## 2026-11-13 — GPS heading retry and LAB verification (s141)
- User reported that Sol starts and takes off, then stops before reaching the selected GPS destination, and that the equipment view seemed shorter than expected.
- Reviewed the current equipment page against the 0.28.3_FULL release: `buildLoadout` still presents loadout preferences and the companion-inventory button; the full carried-item listing is accessed through `افتح حقيبة الرفيق`. No removed equipment list was found in this page implementation.
- The latest LAB debug log contains no GPS-flight attempt or `[SolHeliGPS]` runtime trace, so it cannot establish the cause of the user's earlier stop. Source review found a fragile path where one unavailable heading sample immediately ended GPS guidance.
- Updated `SolHeliGPS.lua` to hold altitude and retry missing heading samples for up to 15 seconds, preserve the selected destination, and emit periodic route distance, altitude, and speed telemetry. Persistent failure stops safely after the bounded retry. Added transient-recovery and timeout/resume cases to the end-to-end route test.
- PASS: s121, s124, s125 start, s125 flight simulation, s127 speed/altitude rows, and s135 full-route suites. WORK/LAB `SolHeliGPS.lua` SHA-256 matches (`621750FDDA8F20D64AEA632FFC884A9222AB5CC16021BA3921DBF8168AC2F556`).
- `launch_lab.ps1 -CheckOnly` passed with 0 link mismatches, 0 patch-access problems, TONUMBER and JARCALL checks clean (20 existing warnings), and model-card check passed (1 existing warning). LAB is newer than installed release; this task changes LAB only.
- In-world flight remains the acceptance test. The first sandboxed preflight could not enumerate Windows processes and refused launch; elevated CheckOnly verified no duplicate game process and all preflight gates. No live flight proof is claimed here.

## 2026-11-13 — Restore carried-item list in equipment tab (s142)
- The screenshot confirmed that the equipment tab showed health, gear preferences, and the separate bag button, but no item-by-item carried-inventory list. The earlier comparison with 0.28.3_FULL did not answer the requested UI behavior.
- Added a read-only list to the equipment tab: item display names, aggregated stack counts, condition when available, and whether each item is in Sol's main inventory or a carried container. The scan is bounded to 5,000 item instances / 64 nested containers and renders at most 300 item-type rows to keep UI construction bounded. Added Arabic and English strings. No items move or mutate.
- Backed up the original source and LAB files in `08_RUNTIME_TEST/s142_loadout_inventory_backup`; copied the three UI/translation changes to LAB. SCUI source and LAB hashes match.
- PASS: game Kahlua compiled all 288 LAB client Lua files with 0 errors; TONUMBER check clean; JARCALL check 0 failures (20 existing warnings); English JSON parses and all new keys exist.
- Visual/runtime check pending: `launch_lab.ps1 -CheckOnly` failed closed because this session could not enumerate Windows processes (`tasklist.exe` returned “The user name or password is incorrect”; CIM access denied). No game was started and no release/Steam files were changed.

## 2026-11-13 — Sol 0.28.4 private full candidate (s143)
- Created `01_WORK/RELEASE/SOL_2026-11-13_0.28.4_FULL` from the complete 0.28.3 bundle, then overlaid current WORK Sol mod files and five current Mind runtime files. Existing full-package manifest: 2,650 files; candidate after cleanup: 2,656; removed baseline files: 0; six new functional Lua modules. Old release folder was not changed.
- Version metadata updated in both `mod.info` files. Candidate carries latest MAIN switches while retaining previous keys/values; `lua_profiler` and `shooting_damage_probe` are off by default.
- Candidate launcher preserves any prior mod copy in a versioned backup and merges only missing switch defaults into an existing user config; previous explicit values remain unchanged.
- Static checks: Lua parser 302 files / 0 errors; linkcheck 11,963 / 0 mismatches; patch access 88 / 0 issues; Python compile 5/5; model card 0 failures / 1 warning; launcher parser pass. TONUMBER gate has three conservative sites in two files byte-identical to 0.28.3; they introduce no new candidate regressions.
- Not proven in-game: no gameplay session launched for this packaging task. Flight GPS, helicopter summon, combat, and general behavior need isolated LAB runtime acceptance before calling this a stable release or promoting to the public/Steam copy.
