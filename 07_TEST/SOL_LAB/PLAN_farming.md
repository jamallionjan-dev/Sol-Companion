# Sol farming plan

Written 2026-11-09. For one companion only: Sol. No crews, groups, worker assignment per field or multi-NPC scheduling, in code or in anything she says.

Rules that hold throughout:
- General for any base. His base is one test case, never a target.
- Ideas from other mods only, no copied code (`05_TOOLS\reference\NOTES_farming_mods.md` has the study).
- Do not run alongside NPC Crew, Smart Crop Care or Smart Animal Care on the same fields (double harvests, fertiliser overdose: a second dose costs 25 health).
- Each phase is tested offline, then by him in game, before the next starts.

## What exists today

Sol sits on Living Fellows' base and job system. Its `SCFarmWork.lua` already harvests, waters, treats pests, replants and picks a crop by season. Keeping that base is better than replacing it.

| Problem found | Cause |
|---|---|
| Farmer role refused with 0 of everything | Only her bag and registered storages count, and he has 0 registered (`SolGate.lua`) |
| Watering Can never counted | Check looks for `wateringcan`, the item is `Base.WateredCan` (`SolGate.lua`, `SCFarmWork.lua:257`) |
| Role accepted, then harvest fails | Gate needs `output` storage, harvest needs `food` storage |
| Fertilizer ignored | Job uses only the COMPOST tag or Compost Bag |
| No new furrows, no weeding | Not in `SCFarmWork.lua` |
| "44 plants, all watered" is wrong | Counts 15 tiles around him, flat threshold of 40 (`sol_templates.py:104`) |
| Seeds and fertiliser sentence never prints | Looks up rows that no longer exist (`sol_templates.py:117`) |
| Why work stopped never reaches chat | Job-level reasons are not passed on |
| Farming orders are all one role | No single-task order |

## Phase A: the truth about the farm and the stock

1. **Farm view from native data.** Read every plant in every farm zone through the farming global-object system by chunk (`SFarmingSystem.instance.system:hasObjectsInChunk` / `getObjectsInChunk`), not by walking tiles. For each plant: crop, stage (`nbOfGrow`), `waterLvl` against its own `waterNeeded`, `hasVegetable`, `hasSeed`, `health`, `mildewLvl`, `aphidLvl`, `slugsLvl`, `fliesLvl`, `hasWeeds`, `fertilizer`, `compost`, `state`. Also plowed empty tiles.
2. **Stock she can really use.** Fix the gate (Watering Can, food storage, count only what the job can borrow).
3. **One order to set up storage.** `SolBaseScan` already proposes storages but nothing calls it. She proposes and registers farming, tools, water, output and food storage, and says what is missing.
4. **Shortage list by the game's names**, with amount needed and amount held. "Unsure" when a container is not loaded, never a false shortage.
5. **Honest farm report** in chat: per zone, ready to harvest, thirsty, pests by name, dead, empty, weeds, what is short.

## Phase B: the farm work, her own order of work

Most urgent first, recomputed from live plant state, interrupted by any order from him:

1. Harvest ripe crops (rotting soon first).
2. Water by each plant's own need, in whole doses. Skip outdoor beds in rain.
3. Treat pests: mildew first (the only one that stops growth), then flies, then aphids and slugs near harvest. Dose count is computed.
4. Weeds, reporting once what cannot be cleared (trees, bushes).
5. Plant empty plowed tiles with in-season seed from storage. New furrows in empty farm-zone land, in a bed and path pattern.
6. Feed: one fertiliser or compost dose at stage 3 or earlier, never in winter, reading `plant.fertilizer` live.
7. Carry produce to storage.

Details that matter:
- Re-read the live plant right before every change and judge success by state afterwards.
- A bed that keeps failing is paused and she says why, once.
- Skip a bed within two tiles of him.
- **Native actions:** nobody has shown that vanilla farming actions run on a companion, and `ISPlowAction` uses `getPlayerNum` in single player, which is a specific risk. First a low-stakes test of each action on Sol. Where one does not work: real animation, sound and tool in hand, then the same server calls its `complete()` makes.

**Orders the Mind catches itself:** "اسقي"، "احصدي"، "ازرعي بندورة بهالقطعة"، "شوفي شو ناقصنا"، and:

- **"دبري/اهتمي بالمزرعة بغيابي" (farm-keeper mode):** she stays at the base and works through the list until he gives another order.
- **"ضلي بالبيت ارتاحي" (home mode):** stays at base, treats her wounds, eats, drinks, sleeps when tired, washes, changes dirty or wet clothes (body never changed), comes when called.
- The two combine, her needs first: health, then hunger and thirst, then hygiene, then farm work.

She says naturally what she is doing when asked, and why she stopped if blocked. Reasons are rate-limited so she does not repeat herself.

## Phase C: she remembers and warns

What she planted, where and when it is due. "The tomatoes are ready", "the north plot is thirsty", "winter is coming, the carrots should go in next month". Forgotten on death like the rest.

## Phase D: livestock (after farming is proven)

Troughs, eggs, milking, shearing, hutch cleaning, dung to compost, and slaughter only by his rules, never young, pregnant or named animals. Same order-of-work model.

## How the Mind stays in command

The Mind decides from orders and questions, and gives the model the facts. The game side reports state and does the work. The model never starts farm work and never states a farm fact the Mind does not hold.

## Performance budget

All of this runs under one Sol scheduler: a fixed time allowance per frame shared by every subsystem, deferring work when over.
- Farm view by chunk, about 2 ms per slice at most, near zones often and far ones rarely.
- Storage read row by row and resumable, cached, refreshed on container change.
- No per-frame work when nothing changed.
- Numbers measured before and after on the same scene.

## Tests

- Offline: state-machine test of the order of work on mocked plants. Layouts: 1 and several zones, small and large, plants at every stage, every pest, every shortage, unloaded containers, seasons, rain. His base is one case among them.
- Mode tests: needs interrupting farm work, his orders interrupting everything, reload mid-job, death wiping memory.
- In game: one action of each type on Sol first, then each phase by him.

## Risks

- Vanilla actions may not run on Sol (above).
- Living Fellows' `base-maintenance` task is switched off when `instinct_only` is on, and the job scan depends on it.
- Fertiliser overdose if anything else doses the same plant, so `plant.fertilizer` is read live.
