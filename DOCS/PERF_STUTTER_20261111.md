# Stutter diagnosis, 2026-11-11

Diagnosis only. No fix has been applied.

## Measurements

### Slow frames on the main thread

These come from Viewpoint's own "slow frame" log lines, which it writes for any frame over about 50 ms.

| Session | Slow frames | Per minute | Median | p90 | Max |
|---|---|---|---|---|---|
| 11-11 00:31–02:29 | 2224 | ~19 | 99 ms | 116 ms | – |
| 11-11 10:19–10:51 | 883 | ~28 (40+ during the sort) | 106 ms | 137 ms | – |
| 11-11 10:53–11:05, clean restart | 160 in 5.3 min | ~30 | 165 ms | 193 ms | 683 ms |

- In the latest session she was frozen for 25.5 s out of 5.3 min, about 8% of the time.
- Viewpoint attributes about 2 ms of each slow frame to itself. The rest it labels "the game's update, the collector's pauses", which means Lua plus Java on the main thread.
- The stutter is **not new today**. Last night's sessions already had about 19 per minute at about 100 ms each. Today the stalls are about 60% longer: median 165 ms against 100 ms.

### Java and GC (jstat/jcmd, read-only, 11:04)

- JDK 25.0.5, G1 garbage collector (the default; `sol_lab.args` sets no GC), `-Xmx8192m`.
- 162 young collections in about 10 min, 2.5 s in total, averaging about 15 ms each. 60 concurrent cycles, 0.25 s in total. 0 full GCs.
  - **The garbage collector is not the cause** (confirmed): it accounts for about 0.5% of the time, in 15 ms pieces, not 165 ms ones.
- Heap use is 3.0 GB of 5.4 GB committed. The old generation is 90% of committed, which is worth watching.
- The process has 14.5 GB of private memory, mostly native (textures and Viewpoint). The PC had 8.8 GB of RAM free out of 32 GB.
- The game used about 220% CPU, i.e. 2.2 of 16 logical cores. The machine is not saturated. The cost sits on one thread, the game's main thread.

### Sol's own Lua time (SolPerf, 15 s windows)

| Item | Cost |
|---|---|
| `pages` (the Sol panel drawing itself) | 0.5–1.3 s per 15 s, ~2 ms per frame, max 14 ms; only while the panel is open |
| `world_scan` | ~95 ms, one frame, about every 15–30 s |
| `inventory` | up to 53 ms in one frame, 344 ms per 15 s |
| `actions_catalog` | 58 ms, once |
| `budget` | max 25–53 ms |

- Sol accounts for a few long frames per minute (`world_scan`, `inventory`, `actions_catalog`) plus about 2 ms per frame while the panel is open.
- **She does not explain 30 slow frames a minute at 165 ms** (inference from the numbers).

### The Mind

pythonw is idle: CPU time 12 s since launch. Not a factor (confirmed).

## Ranked causes

1. **Unattributed main-thread work: about 85% of the stall time.** Most likely candidates (inference):
   - per-tick Lua from the 100+ mods (EFZ/Gunworks stat recompute, Living Fellows decision systems, Viewpoint's Lua-side snapshot);
   - chunk streaming right after load.
   This cannot be split further without a profiler.
2. **New since last night, possibly behind the longer stalls (165 ms against 100 ms)** (inference):
   - `kahlua_overload_guard` turns the global `pcall` into a Lua wrapper, which adds a frame to every `pcall` from every mod;
   - the `two_hand_grip` check runs every 2 s (it is cheap).
   The 5-minute sample came straight after loading, so streaming inflates it.
3. **Sol's single-frame spikes**: `world_scan` 95 ms, `inventory` 53 ms, `actions_catalog` 58 ms. Confirmed as frames, but only about 4–8 per minute.
4. **The Sol panel**: ~2 ms per frame while open (confirmed).
5. **GC**: about 0.5% (confirmed, minor).

## Options

| # | Option | Expected gain | Risk | Effort |
|---|---|---|---|---|
| A | **Measure:** a 2-minute JFR profile (`jcmd <pid> JFR.start settings=profile duration=120s`) during play at the next launch. The JDK 25 tools are installed. It shows the hot Java methods, Kahlua calls included. | Names the real cause | ~1% overhead, no behaviour change | 5 min |
| B | **A/B on a copy of the save:** one run with `kahlua_overload_guard=off`, one with Sol idle, one with all Sol switches as now, all at the same spot, 3 minutes each, counting slow frames per minute. | Separates Sol from the modpack | Low (the switches are read at call time) | 15 min of Jamal's time |
| C | **Time-slice Sol's spikes:** split `world_scan`, `inventory` and `actions_catalog` across frames at ≤4 ms per frame. | Removes about 4–8 frames of 50–100 ms per minute | Low | Medium (1–2 h, offline tests) |
| D | **Narrow the guard:** keep watching Sol's own call helpers only and stop replacing the global `pcall`. | Up to the extra cost per pcall (unknown, A measures it) | Low; loses detection of other mods' bad calls | Small |

**Recommended order:** A first (it gives the answer), then D and C. B only if A is unclear. GC tuning is not worth it.

## JFR (11:16:58–11:19:28, 150 s, Jamal playing, Sol following)

Recorded with `jcmd 10204 JFR.start settings=profile duration=150s`. File: `07_TEST/SOL_LAB/perf/jfr_20261111_1116.jfr`. fps 23–51 (SolPerf).

### Main thread: 13,264 samples (busy about 88% of the time)

| Share | What |
|---|---|
| **61.5%** | **Lua interpreter itself** (KahluaThread, no Java call underneath) |
| 43.7% | of it under `IngameState.onTick` (the OnTick handlers of every mod) |
| 3.8% | of it under `IsoPlayer.updateInternal2` (OnPlayerUpdate) |
| 2.6% | of it under `IngameState.updateInternal` |
| 25.3% | rendering (vanilla + Viewpoint; Viewpoint's own Java about 0.3%) |
| 15.5% | game update in Java, outside Lua |
| 3.5% | Living Fellows / SurvivorCompanion bridge Java |
| 1.7% | EFZ Java (GripIK 0.9%) |
| 0.5% | Sol's Java (SolStations etc.) |
| 2.4% | Java methods called from Lua, all together; the largest is 0.14% |

So almost all of it is Lua code. JFR cannot say WHICH mod's Lua, because Kahlua runs every mod in one interpreter.

### Sol's own measured Lua (SolPerf, same window)

20–220 ms per 15 s, i.e. 0.1–1.5%. The single-frame spikes are `world_scan` 90–129 ms (every ~45 s), `inventory` max 38 ms and `actions_catalog` 51 ms.

Living Fellows' own Lua (SCDecision etc.) is NOT in SolPerf.

### GC

- 7 pauses, 514 ms in total.
- **One young pause of 333 ms** at 11:17:11, then 32–43 ms each.
- **Allocation: 84% of everything allocated is `double[]` from EFZ `GripIK.unitRotation` (line 5465)**, via `wristTwist ← holdEval ← holdTry`. That is the EFZ firearms grip IK. It drives the young GCs. Confirmed from the allocation samples.

### Exceptions: 5,932 in 150 s (40 per second), all on the main thread

- **5,280 `ClassNotFoundException: org.lwjgl.opengl.Display`** from ViewpointFPS (`Config.detectHz:332 ← displayHz ← clampTargetToDisplayOnce ← FrameGovernor.onFrameStart:144`). It runs every frame, and the game runs with `-XX:-OmitStackTraceInFastThrow`, so each one builds a full stack trace.
- 309 NPEs in `ControllerSettings.getPadText/getToggle` via `Ref.call:158`, from a mod's controller UI.
- 218 `IllegalArgumentException` from vanilla `SkinningBoneHierarchy` (vehicle bones).

### Ranked culprits (main-thread time)

1. **Lua OnTick handlers of all mods: about 44–61%.** Not attributable per mod with JFR.
   - Sol's own measured part is ≤1.5%.
   - LF's decision Lua is unmeasured.
   - Inference: the bulk is the 100+ mods' per-tick Lua.
2. Rendering: about 25%. Normal for this mod set.
3. Java game update: about 15%.
4. GC spikes driven by EFZ GripIK allocation: one 333 ms freeze plus ~40 ms pauses about every 20–40 s.
5. ViewpointFPS exception storm: ~35 per second, a few ms per second (small but constant).

### Options (not applied)

| # | Option | Expected gain | Risk | Effort |
|---|---|---|---|---|
| 1 | **Lua profiler:** a ZombieBuddy patch (behind a switch, diagnostic) that times every Lua event callback and sums the time by source file, i.e. by mod. Report every 15 s. | Names exactly which mods eat the 61% | Low (timing only); jar change, so ZB approval | 1–2 h |
| 2 | **A/B without Sol:** one 3-min run with Sol_LAB + SurvivorCompanion disabled on a copy of the save, same place. | Splits Sol + LF from the rest at once | None to the save (copy) | 15 min of Jamal's time |
| 3 | **GC flags in `sol_lab.args`:** `-XX:MaxGCPauseMillis=20 -XX:G1NewSizePercent=30` (G1 aims for shorter pauses with a larger young generation). | Cuts the 333 ms and ~40 ms GC freezes | Low (lab only, reversible) | 5 min |
| 4 | **Sol's spikes:** time-slice `world_scan`, `inventory` and `actions_catalog` (≤4 ms per frame). | Removes Sol's 50–130 ms frames | Low | 1–2 h |

Mods we cannot edit (report upstream): ViewpointFPS `detectHz` (cache the failed lookup) and EFZ GripIK (reuse its arrays).

## External engineering review (2026-11-12)

Primary-source review:

- The Indie Stone's Build 42 modding note says `LoadGridSquare` can cause an annoying performance impact for work that can instead use the chunk-load event; for many such uses, `LoadChunk` needs about 1% as many event calls. This supports event/chunk-triggered indexing for stable world data, not replacing exact local geometry or emergency sensing with coarse squares: [The Indie Stone Build 42 modding note](https://store.steampowered.com/news/posts/?appids=108600&enddate=1681381566&feed=steam_community_announcements).
- Epic's CPU guidance recommends intervals/timers for recurring non-frame-critical work and splitting large synchronous batches across frames. It also cautions that event-driven checks are not automatically cheaper when events fire repeatedly. Unreal's behavior-tree guidance describes waking on relevant state changes rather than reevaluating an unchanged decision tree each frame. These are transferable design principles, not Project Zomboid API guarantees: [CPU and memory guidance](https://dev.epicgames.com/documentation/en-us/unreal-engine/common-memory-and-cpu-performance-considerations-in-unreal-engine?lang=en-US), [event-driven behavior trees](https://dev.epicgames.com/documentation/unreal-engine/behavior-tree-in-unreal-engine---overview).
- Microsoft PIX, NVIDIA Nsight Systems, and Oracle JFR all point to comparing frame-time outliers against CPU/GPU/thread timelines and sampled call stacks, rather than inferring CPU cost from an activity/latency counter. JFR specifically recommends comparing a recording from a good period with one from a bad period and notes that continuous recording is low-overhead; heap statistics can add pauses and should stay off during this latency test: [PIX timing captures](https://learn.microsoft.com/en-us/windows/win32/direct3dtools/pix/articles/timing-captures/pix-timing-captures), [NVIDIA stutter workflow](https://developer.nvidia.com/blog/using-nsight-systems-for-fixing-stutters-in-games/), [Oracle JFR performance troubleshooting](https://docs.oracle.com/en/java/javase/24/troubleshoot/troubleshoot-performance-issues-using-jfr.html).

Applied to Sol, the previous s106 Lua profile already gave a useful attribution: LF's `SCRuntime` OnTick handler was about 35 ms/s and our `SolBudget` handler about 12 ms/s in that capture. The latest runtime run is better by Jamal's report while walking and opening the bag, and bag scans are now mostly skipped when unchanged. The current counters still vary, so this is not proof that either handler alone caused the earlier near-4-FPS freeze. `navigation.first-motion` measures request-to-first-movement latency, not CPU time; exclude it as a compute-cost metric.

### Recommended next step

Do not remove any sensing layer or make another speculative timing change yet. First inspect the current lab's two attributed Lua hot paths (`SCRuntime` decision/production tick and `SolBudget`) and use short, targeted per-function timings to separate their immediate safety/command work from noncritical repeat work. Keep the existing mission scan gate and exact geometry. Any candidate optimization should affect only stable/nonurgent work (event-trigger it, cache unchanged inputs, stagger it, or slice its workload); keep danger reflexes, movement control, direct-command grace, and route obstacle geometry on their proven fast paths.

Then take one matched A/B capture on a backup of the same lab save: same location, camera, mod list and warmed-up period; record a steady-away control and near-Sol idle → movement → bag-open windows. Use JFR CPU/thread/GC samples plus the Sol/LF Lua counters and frame-time percentiles. Avoid heap-statistics profiling and avoid pausing the game for screenshots during measurement. Only implement if one named callback or repeat scan rises with the bad frame windows. Acceptance is repeatable near-Sol frame pacing close to the same-session away control, without delaying a direct order, an emergency response, exact navigation, or a requested inventory/farm scan. Keep all edits in SOL_LAB and make a timestamped backup first.

## After the GC flags (JFR 12:00, 150 s, same point after load)

Flags: `-XX:MaxGCPauseMillis=20 -XX:+UnlockExperimentalVMOptions -XX:G1NewSizePercent=30`.

| | Before (11:16) | After (12:00) |
|---|---|---|
| GC pauses | 7 | 8 |
| Total pause | 514 ms | **185 ms** |
| Longest pause | **333 ms** | **43.9 ms** |
| Median pause | 32.2 ms | 21.1 ms |
| fps (SolPerf, 15 s windows) | 23–51 | 16–74 (most 53–74 after the first minute) |

- The long GC freezes are gone. The longest pause is now 44 ms instead of 333 ms.
- The Lua share of the main thread is unchanged (expected). That is the remaining stutter, still unattributed per mod.
- Viewpoint wrote no slow-frame lines in either run, so slow frames per minute can't be compared from that source.

## Per-mod Lua profile (s106, 14:52:28-14:54:38, two 15 s windows)

Lua in these four events took 241-271 ms/s (about 25% of wall time). The profiler's own overhead was 10-12 ms/s. The rest of the 61% interpreter time is Lua outside these events (UI render, timed actions, other events).

| Mod | ms/s |
|---|---|
| EscapeFromZomboidFirearms | 71-79 |
| Sol_LAB (incl. LF) | 62-69 |
| AviationCore | 30-37 |
| vanilla | 20-24 |
| Trucksmith | 15-17 |
| Tank Water | 14 |
| Gunworks | (smaller) |

Top single handlers:
| Event | ms/s | Handler |
|---|---|---|
| OnTick | 35.3 | LF `SCRuntime.lua` fn@L1344 |
| OnTick | 15.8 | vanilla `ISVehicleDashboard.lua` @L660 |
| OnTick | 14.8 | AviationCore `Helicopter_Core.lua` @L505 |
| OnTick | 12.2 | ours, `SolBudget.lua` @L22 |
| OnTick | 8.9 | AviationCore `HelicopterNightLightService` |
| OnTick | 7.6 | EFZ `TW_ShotOwner.lua` |
| OnPlayerUpdate | 12.9 | `TankWater_Client.lua` @L599 |
| OnPlayerUpdate | 6.8 | EFZ `TW_TacHoldOverride.lua` |

OnRenderTick (6.4 ms/s) and OnZombieUpdate (5.3 ms/s) are small.

Next targets, ours first:
- LF `SCRuntime` @L1344 at 35 ms/s: what runs every tick there, and can it be sliced or throttled?
- `SolBudget` @L22 at 12 ms/s: our own budget manager.

Then see whether the mod settings of EFZ (many per-tick first-person features in an isometric game), AviationCore and TankWater can turn features off. No Workshop edits.
