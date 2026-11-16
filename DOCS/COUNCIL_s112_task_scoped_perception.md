# s112 — Sol Mind task-scoped perception council

Date: 2026-11-11
Scope: read-only design decision before implementation; lab only, no MAIN/release changes.

## Evidence inventory

Confirmed in the current lab copy (`07_TEST/SOL_LAB/profile/Zomboid/mods/Sol_LAB/42/...`):

- `SCDecision.update` asks `SCSenses.snapshot` on the configured 500 ms perception interval and calls `refreshImmediate` on each decision update. `SCSenses` uses `SCPerceptionScan`, a shared native zombie snapshot with a bounded grid fallback. Preserve this safety/combat perception.
- `SolWorldScan.lua` starts a broad snapshot every 60 seconds through `SolBudget`. `SolChat:sendCurrent` and `SolOrders.rescue` also call `U.scanNow`; that function clears any sliced job and runs `U.writeWorld()` synchronously. The send path therefore bypasses the normal slice.
- `SolInventory.lua` starts a broad base/player/Sol/container/vehicle inventory scan automatically every 120 seconds. It uses slices when `perf_slice=on`, but it can run alongside the world snapshot under a separate logical scan job.
- `SolBaseScan.baseScan()` synchronously loops marked base rectangles plus a 30-tile margin, up to 12,000 squares and 500 ms. It is an explicit discovery action, not a reason to repeat that scan for routine farm care once the farm is registered.
- `SolBudget` has a 2 ms target, while `SC.Performance` has a separate LF scheduler budget. The current setup is not one cross-subsystem time budget. The starvation escape can also grant a minimum 1 ms callback after the nominal allowance.
- `SolNavigation`/`SCTopology` provide fine obstacle and edge geometry for movement. This is needed for doors, narrow gaps, poles, vehicle clearance and container approach squares; do not replace it with square-only approximations.
- The current lab config has `instinct_only=off`. In `SolAuthority.allowsDecision`, that bypasses the instinct filter. This is a configuration/code discrepancy to test against the stated Sol Mind authority; do not flip it blindly before tracing the remaining order arbitration.
- “Forget all” cancels Lua orders, vehicle transactions and work, then restores follow. The Python `GoalEngine` cancellation list does not include the `forget_all`/`sol_forget` route, so an active Mind goal can survive the apparent reset.
- The runtime card is one-tier and close to its 4,600-character limit (4,566 in the generated doc). Model-first JSON routing uses `model_router.sheet`; tool-calling and Sol Link assemble different prompt text. The current card checker does not prove that all three paths receive the same canonical instruction card.
- The work copy and lab copy differ for `SolWorldScan.lua` and `SolAuthority.lua`. Do not copy the work tree wholesale into the lab. The repository already contains a large dirty/untracked set; preserve it and touch only named s112 files.
- The newest lab console ends at the main menu on game 42.22.2. It is not evidence of a world-entry or behavior test.

Official engine reference: The Indie Stone described Build 42 `LoadChunk` as a 10×10 square chunk event intended to avoid the performance impact of per-square `LoadGridSquare` callbacks. It is a candidate for static, event-updated geometry caches, not a replacement for dynamic inventory, crops, vehicles, or immediate threat perception. See [Build 42 modding announcement](https://steamcommunity.com/games/108600/announcements/detail/3635004526674526598?l=koreana).

## Engineer — proposal

### Non-negotiable authority invariant

Sol Mind already declares itself the top-level action/plan authority in `chat_service.SYSTEM_BASE` (“طبقة Sol العليا”), while LF provides execution mechanisms. Existing behavior test `BHV1` asserts that wording. This work preserves that architecture; it does not introduce a new controller. Runtime tests must prove the Lua/LF arbitration and each model route actually uphold the existing policy. `instinct_only=off` changes which LF decisions pass through `SolAuthority.allowsDecision`; by itself it does not redefine the Mind's authority, so do not flip it as a proxy fix.

Living Fellows (LF) is a capability/execution layer: it carries out actions delegated by Sol Mind and may provide fallback autonomous behavior only when there is no conflicting Mind task/order. No LF routine may replace, postpone indefinitely, or silently undo a direct Sol Mind order. A newer Sol Mind order supersedes the older task; “انسي كلشي” cancels Mind goals, Lua orders, scanner leases, pending completions, and LF holds before ordinary follow resumes. The direct command wins over LF autonomy, including an ongoing fight, vehicle follow behavior, work, and downtime. Immediate game safety follows Sol Mind's active policy/decision rather than becoming a competing LF authority.

Keep Sol Mind as the sole owner of the user's active task and final command priority. LF remains the capability layer for movement, combat, medical response, survival needs and low-level actions Sol Mind delegates. Its fallback autonomy is allowed only while Sol Mind has no conflicting active intent. Implement a task lease for sensing, with two concurrent logical layers at most:

1. LF's protected immediate/perception layer.
2. One Sol Mind mission layer, which may change phase but never runs two mission scanners together.

Task-to-sensing map:

| User intent | Sensing required | Explicitly avoid |
|---|---|---|
| Idle, ordinary follow, ordinary conversation | LF safety/perception; cached facts | Broad scan on every chat line |
| Fight / retreat / regroup | LF immediate threat perception; exact route only when movement requires it | Inventory, farm and general world scans |
| Farm report / farm care | Registered farm bounds and crop state; inspect required supplies in a sequential phase | Re-scanning the whole base and unrelated containers |
| Inventory question / fetch supplies | Inventory scan/cache with stack grouping; scan only reachable task storage when needed | World geometry sweep unrelated to storage |
| Board a named/near vehicle | Targeted vehicle discovery up to the established 30-tile range, then exact door/approach geometry | Full world snapshot; reducing the 30-tile target range |
| Drive to GPS marker / home | GPS route and exact vehicle-aware obstacle geometry as sequential phases of one drive task | Approximate square-only obstacle representation |
| Refuel at station | Route/station discovery, pump position, vehicle fuel-side alignment and tank check in sequential phases | Simultaneous unrelated inventory/world scans |
| Discover/register a base | Bounded, sliced base scan once; explicit apply remains separate | Repeating base discovery for routine work |
| “انسي كلشي” | Cancel Mind goal, Lua task, scan lease and pending result; return to follow | Deleting persistent home/address/map memory |

Remove synchronous full scans from chat/rescue. A message first uses the latest snapshot with its age. If the selected task requires newer facts, Sol Mind requests that task's scan profile; the game advances it in slices, and Mind acts/replies only after a fresh result or reports that the data is unavailable. Scanner requests carry an owner/generation token so a replaced task cannot consume a late result. Keep the established exact navigation implementation.

All world, inventory and base-scan jobs must acquire the same mission lease. Idle background refreshes may run one at a time, and pause when a user task owns the lease. Enforce the existing ≤4 ms/frame work rule with one shared allowance for Sol-owned scan work; keep urgent LF defense responsive and measure its budget separately rather than silently starving it.

Use one canonical instruction card in `model_router` for JSON, tool-call and Sol Link providers. Transport adapters may specify output syntax, but may not redefine Sol's authority, intent policy, or command meanings. Add the hierarchy and reset contract compactly without exceeding `CARD_BUDGET`; preserve every reachable action/example and the route checker.

## Devil's advocate — rejection risks and controls

- **Stale facts:** removing `scanNow` can make farm, inventory or station answers wrong. Control: per-domain timestamps, task-specific freshness limits, request/ack IDs, and fail closed when a required scan cannot complete.
- **Layer counting ambiguity:** LF perception and its reflex pass are two functions but one protected perception domain; route geometry is a mission phase, not an extra independent mission scan. Log active logical domains and assert the ceiling in tests.
- **Safety starvation:** a hard global cap could delay combat or medical behavior. Control: reserve LF's urgent lane; limit only non-urgent mission scans, and test direct retreat during combat.
- **Lost door/pump/vehicle precision:** reducing sensing to a simple radius/grid can reintroduce known failures. Control: preserve exact edge/footprint checks and test poles, gates, player-blocked doors, and pump alignment.
- **Race after cancellation:** a completed old scan might arrive after a new order or “forget all.” Control: monotonically increasing task generation, reject stale completions, and assert cancellation before following resumes.
- **Slow/unloaded chunks:** 30 tiles of coordinates do not mean all squares are loaded. Report “not found in loaded area” separately from “none nearby”; do not invent a vehicle or pump.
- **Card budget/provider drift:** a shared card may exceed the limit or get duplicated/conflicted by tool prompts. Control: expand `card_check.py` to inspect each transport and keep protocol wrappers minimal.
- **Third-party LF code:** our coordinator cannot guarantee a cap on arbitrary third-party mod scans. Scope claims to Sol-owned jobs and LF APIs we control; keep profiler evidence for the full mod set.
- **Build 42 event uncertainty:** `LoadChunk` can support static cache updates but may not cover later object changes. Do not make it the first fix; validate invalidation before adoption.

## Strategist — decision

Proceed incrementally in the isolated lab. Preserve LF threat/survival behavior and Sol's fine spatial awareness. First enforce a single Sol-owned task/scan lease and make reset/command replacement clear it. Then route only the currently active task to one scanner, remove synchronous chat/rescue scans, and convert the explicit base-discovery scan to bounded slices. Keep periodic world/inventory refreshes mutually exclusive and idle-only until each task-specific path passes. Unify the model card through one source of truth and make the card gate verify every provider route.

Do not touch `01_WORK`, the Steam/Workshop install, the combined JAR, approvals, or MAIN during this phase. Apply through an idempotent lab-only script after offline tests pass, run `launch_lab.ps1 -CheckOnly`, then launch through `launch_lab.ps1`. No task is release-PASS until Jamal completes the in-world interaction and its log evidence is recorded.

## Offline acceptance gates

1. Existing card action completeness, budget, and route replay remain green; every model transport gets the same canonical policy card.
2. A test matrix maps every listed user task to zero or one mission scan profile; LF perception is the protected layer. No test state can hold more than two logical layers.
3. Starting a new direct order cancels the previous Mind goal and scan generation; prove an LF decision that conflicts with the active order is rejected and cannot replace it. “انسي كلشي” cancels Mind goals, Lua work, scan generation and late completions, releases LF holds, restores follow, and preserves persistent memory.
4. `SolChat:sendCurrent` and rescue do not synchronously call `writeWorld`; stale data is never used for an action that requires a fresh result.
5. World/inventory/base scans cannot overlap as independent mission jobs; task phase transitions preserve results and reject stale results.
6. Fake-clock scheduler tests prove bounded per-frame slices, cancellation, fairness and no scan starvation of LF's urgent lane.
7. Exact door, gate, pole, narrow vehicle clearance, 30-tile vehicle discovery, farm bounds, and pump alignment remain represented in route/task APIs.

## In-world checklist (one item at a time)

- [ ] Sol spawns; ordinary follow and combat still work with LF perception intact.
- [ ] During combat, order retreat/follow; Sol Mind's direct order wins promptly.
- [ ] Start a multi-step task, say “انسي كلشي”; task and scan stop, Sol follows, no old task restarts.
- [ ] Ask for inventory; grouped counts are complete and no unrelated world scan starts.
- [ ] Ask for the farm report, then farm care; only the registered farm is inspected and materials are checked before work.
- [ ] Board the selected vehicle within 30 tiles with the player standing in the door path; Sol chooses the correct seat and walks around the player.
- [ ] Drive to the GPS marker past a pole/gate; route stays precise and command to stop takes effect.
- [ ] Refuel at a station; Sol identifies the pump, aligns the correct fuel side and completes the task.
- [ ] Repeat a close-range performance segment; compare slow-frame rate, Sol scan timings and active-layer logs to the pre-change baseline.
- [ ] Check latest DebugLog and Sol Mind log for scan counts, task owner, rejected stale results, exceptions and command completion.

Each item is checked off only after Jamal performs it and the logs corroborate it.

## Runtime review and relaunch attempt (2026-11-12)

### Existing user evidence

- Jamal reports that the task-scoped scan change improved play near Sol, including walking together and opening her inventory, but did not remove all perceived stutter.
- This is valid player-observed evidence; it is not a controlled FPS comparison and is not replaced by the trace notes below.

### Trace observations from the 2026-11-12 lab log

- `decision_load_throttle` is active. The log reports ordinary decisions at 150 ms when load reaches levels 2/3, and 100 ms at lower load; the critical lane remains unchanged.
- `SolScanCoordinator` serialized inventory and world scans. Passive inventory scanning logged that it pauses within 30 tiles of Sol.
- In the 15-second `SolPerf` windows around 01:15–01:17, recorded FPS varied from 28 to 58. Sol-owned budget totals were 75–107 ms per window; individual `item_stacks` rebuilds were 12–17 ms when present.
- At the same period, Viewpoint logged repeated `loot menu` work of about 95–121 ms on slow main-thread frames. This is a measured contributor associated with the loot UI path; the trace alone does not prove it explains all stutter or identify which mod owns the work.
- Treat this as a second performance path to isolate. Do not attribute the whole frame cost to Sol's scans, and do not change third-party Viewpoint code as part of this Sol task.

### Launch attempt

- Reconciled the lab's expected-mod guard with the current profile, which already had `ViewpointMouseRightClick`, `ViewpointCrosshairUse`, and `ShelfContents3D` enabled. The prior guard file was backed up under `07_TEST/SOL_LAB/_backup/launch_preflight_20261112_013853/`; the active mod list itself was not changed.
- `launch_lab.ps1 -CheckOnly` passed: Java link checks, patch access, Kahlua `tonumber`, Java call arity, and model-card checks passed. The game reports Build 42.22.2 in its startup log.
- The launch process exited during early startup, before the main menu; the new console/debug log ends after FMOD initialization and contains no Lua exception. Sol Mind observed the game close and stopped cleanly. This attempt is **not** a runtime performance pass and yielded no new in-world comparison.
- The lab and release remain separate. No source Lua, release files, Steam installation, or save data were modified in this review.
- A second launch was attempted at 01:43 through the same approved lab launcher. Preflight again passed and the launcher started Sol Mind, but the game process exited within seconds before the main menu. The new `01-43_DebugLog.txt` again ends during early FMOD initialization without a Lua error; process checks found neither game nor Sol Mind still running. Stop blind relaunches here until the host-side early exit is understood.

## Phase 1 implementation status (2026-11-11)

- Installed only in `07_TEST/SOL_LAB`; the game was closed and a timestamped backup was made first. `task_scoped_perception=on`; MAIN and the release are unchanged.
- `SolScanCoordinator` allows one Sol mission scan at a time. World, inventory, and the explicit base scan share this lease. LF's independent immediate threat sensing remains outside this lease.
- World and inventory jobs use the existing sliced scheduler while this switch is on. Chat/rescue no longer force an immediate full world write; they queue the world refresh. A new direct order and the existing right-click `O.forget` cancel the active lease; sliced scans drop their result on the next budget tick. The Python `sol_forget` route now preempts the active Mind goal.
- Verification: new s112 test 28/28, existing s99 slice regression 49/49, forget preemption 4/4, Lua syntax/ASCII, and launcher `-CheckOnly` passed (0 link mismatches, 0 patch-access problems, tonumber OK, jarcall 0 failures/20 warnings, card check 0 failures/1 warning).
- This only serializes the explicit base scan; its pre-existing synchronous implementation still has a 500 ms cap. The one-turn test does not yet prove cancellation latency, max-frame latency in Kahlua, freshness-aware task routing, uniform card text for each transport, LF/direct-order arbitration, or improved in-world frame times. These must remain open until implemented or evidenced.
