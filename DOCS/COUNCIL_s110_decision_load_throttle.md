# Council s110: load-aware ordinary decision cadence

## Evidence and scope

The lab log `07_TEST/SOL_LAB/profile/Zomboid/Logs/2026-11-11_16-19_DebugLog.txt` reports at 16:59:28 and 16:59:43 that the combined Sol/LF tick used 428-447 ms/s. `decision.evaluate` used 276-277 ms/s at about 7 evaluations/s; delegation used 98-119 ms/s at about 5.4 calls/s. In the same run, Viewpoint reported main-thread frames around 170-219 ms while its own main/render work was mostly 2-9 ms, and the sampled frame had no GC pause. These measurements make the Sol/LF AI loop a confirmed contributor, not the sole confirmed cause of every long frame.

`SCRuntime.lua` currently asks the ordinary decision lane every 100 ms. Cached danger/grab actors instead use a separate 50 ms critical lane. `SCPerformance` already measures frame pressure and increases load level. The decision scheduler is registered as critical, so it currently bypasses the scheduler's normal interval scaling.

## Engineer: proposed fix

Add the lab-only switch `decision_load_throttle`. When performance load reaches level 2 or 3, move only the ordinary decision cadence from 100 ms to at most 150 ms. Keep the critical lane at its configured 50 ms interval. `SCCommands.issue` marks the actor urgent for one second after every newly issued command; that grace preserves the original 100 ms decision cadence so fresh player orders are not delayed by this optimization. The interval decision is isolated in a pure helper and tested independently.

Measure at the same loaded location with the Sol UI closed and open: ordinary decision evaluations/s, `decision.evaluate` ms/s, `scheduler.decision` ms/s, p95/max frame time, GC pause, and visible command/combat response. The expected effect is fewer routine evaluations under load (about one third when the baseline is 100 ms); no claim of a GTA V-level performance outcome is made without a comparable measurement.

## Devil's Advocate: risks and assumptions

- Cached threat classification determines entry into the unchanged 50 ms lane. A newly arriving threat may wait up to 50 ms longer for ordinary discovery than before, though an observed threat stays critical.
- A single companion's routine needs/formation updates also slow to 150 ms under sustained load. This remains well inside the existing 250 ms movement-input lease, but real play must verify walking, combat acquisition, self-care, and driving.
- The frame-pressure signal may rise because of unrelated mods or rendering. This intentionally trades a small amount of ordinary AI freshness for headroom only while the whole game is already over budget.
- This does not repair EFZ, AviationCore, TankWater, ViewpointFPS, or any other Workshop code. Their profiler entries require separate evidence and upstream-safe settings or compatibility work in our files.

## Strategist: rollout

Stage and test the helper, switch, and notification path offline. Install only into the isolated `07_TEST/SOL_LAB/profile/Zomboid` copy with the game closed, back up touched lab files, run `launch_lab.ps1 -CheckOnly`, and launch only through `launch_lab.ps1`. Collect a new 120-second JFR and the existing 15-second Sol/LF profile during a comparable in-world segment. Keep MAIN/release untouched until runtime results pass; do not push this change without separate authorization.

## Acceptance

1. Switch OFF or load below level 2 returns to the exact configured interval.
2. Load level 2/3 caps ordinary cadence at 150 ms; fresh command grace uses the original interval.
3. Critical danger/grab service remains 50 ms.
4. Gates pass; runtime profile shows fewer ordinary evaluations and lower decision cost without missed/late orders, combat response, or movement stalls.

## Incident review: first combined runtime attempt (2026-11-11)

### Confirmed

- The first lab attempt did not produce usable follow/combat evidence. The live log repeatedly reports `attempted index: ordinaryInterval of non-table: null` at `SCRuntime.lua:487` inside `decisionTaskCore` (for example frames 18, 2467, 4267, and 6085).
- The s110 installer used a standalone `require "SolDecisionBudget"`, while the helper returns its table and does not create a global. The runtime then dereferenced the missing global. It computed this value before the switch could protect the call, so turning `decision_load_throttle=off` live did not stop the exception.
- `SolDamageProbe` initialized, but the log contains no attributed hit/kill records. The user could not complete the combat comparison while the decision core was failing.
- The actual game was closed before this correction. MAIN/release was not touched.

### Engineer: correction

The installer now assigns the returned helper as `local SolDecisionBudget = require "SolDecisionBudget"`. The call is guarded by the feature switch and by table/function checks, with the unmodified base interval as the fallback. The critical lane remains untouched. Regression tests now execute both disabled-with-missing-helper and enabled-with-returned-module cases.

### Devil's Advocate

The added local tests prove Lua 5.1 behavior and installer idempotence, but do not prove this Build 42 Kahlua runtime loaded the returned module or that Sol's decisions resume. Nor does a functioning decision loop prove the cadence change improves stutter. A clean in-world follow/order check and comparable performance samples are still required. No firing-damage conclusion is possible until both characters shoot the same weapon at comparable targets and the read-only before/after health ledger records hits.

### Strategist: status and next check

Keep the correction and both probes in the isolated lab only. Run `launch_lab.ps1 -CheckOnly`, then a fresh lab session on `2026-11-10_02-39-13`. First verify Sol appears, follows on a direct order, and responds to a new command. Then record the same in-world segment with the UI closed and open. Only after responsiveness is confirmed should the Jamal/Sol damage comparison run. Do not promote s110 or claim the stutter improved from this failed round.

### Research actually completed

Before the first s110 implementation, public primary-source research covered Rockstar's published GTAV benchmark/frame-time parameters and patch notes, plus Oracle's JFR profiling guidance. These sources support repeatable frame-time measurement and using execution/GC traces; they do not expose Rockstar's internal optimization methods or prove a specific Sol change will match GTA V. This research was too general to catch the Lua module-return/global-name bug. The corrected implementation is now covered by an integration-shaped offline test and still requires Kahlua runtime proof.
