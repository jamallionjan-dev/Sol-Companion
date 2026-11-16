# سول بتشتغل وجمال بعيد: خطة (2026-11-10)

جمال: "لازم تشتغل بالمزرعة إذا أنا كنت برا محيطها، حتى لو بدها تحمّل المنطقة اللي حواليها."

**الحالة (2026-11-10 بالليل):** انبنى ورا المفتاح `far_work` وانركّب بالمختبر (ON بالمختبر، OFF بالإصدار). **نص نجاح باللعبة:** الشغل صار والتقرير ما انقال. التفاصيل بالقسم 8 تحت، والمجلس بـ `SOL_REVIEW_20261109.md` قسم 38 و43.

## المشكلة
لما جمال يبعد، المنطقة اللي فيها سول بتطلع من الذاكرة. سول بتصير "بعيدة ونايمة": سجل محفوظ بس، بلا جسم، فالمزرعة بتوقف.

## خيارين، بدهن بحث
1. **نخلّي منطقتها محمّلة.**
   - (بحث) هل في طريقة باللعبة تخلّي chunks حوالين نقطة محمّلة بدون لاعب؟ متل `IsoChunkMap` لكل لاعب، و`WorldStreamer`، وأي "chunk loader" بيستعملو مود.
   - الكلفة: ذاكرة وأداء، وخطر إنو اللعبة تبطّأ.
   - على الأغلب صعب أو مش مدعوم، لأنو اللعبة بتحمّل حوالين اللاعبين بس.
2. **حساب الشغل وهي بعيدة** (الأرجح):
   - (بحث) أنظمة الزراعة عند السيرفر (`SFarmingSystem` / `SPlantGlobalObject`) بتضل تحسب عمر الزرع ومياهو وهو مش محمّل؟ والمعالف (`SFeedingTroughSystem`) كمان؟
   - إذا اي: منكتب "دوام سول وهي بعيدة". كل فترة، أو لما الزرعة بتحتاج، منعمل التعديل نفسو اللي كانت رح تعملو: سقاية، وقطاف، وتسميد، ومعالجة. وبنفس الشروط بالضبط (أدوات ومي وبذور من صناديق البيت، كمية محدودة، مواد بتنصرف حقيقي).
   - النتيجة: لما جمال يرجع، بيلاقي الشغل معمول، والأغراض المصروفة مسحوبة فعلاً، والمحصول بالمخزن.

## شروط
- نفس قواعد "اهتمي بالمزرعة" الكاملة، بنفس الأولوية، وما في غش: كل شي بينصرف من مخزون حقيقي.
- الأداء: الحساب كل كم دقيقة لعب، مقسوم على دفعات، بدون أي تقطيع.
- الحفظ: اللي عملتو بينحفظ، وما بيتكرر عند التحميل.
- بتقلّو لما يرجع جملة قصيرة: "سقيت الزرع مرتين وقطفت 12 جزرة."
- ورا مفتاح لحالو (`far_work`)، وتجارب خارج اللعبة على نسخة من الحفظ.

## الترتيب
بحث، بعدين قسم المجلس، بعدين البنا، بعدين التجارب، بعدين باللعبة.


---

## Research and build (English detail, 2026-11-10)

Owner decision: option (2), simulate her work while the farm is unloaded; never keep the area loaded. Owner rule added the same day: she farms at night too (`farm_night`), so the far computation does not skip night hours. Rain rules unchanged.

Legend: **[C]** confirmed from game files / javap / code, with file:line. **[I]** inference, not proven in game.

### 1. How 42.22.2 keeps crops that are not loaded

Game Lua root: `C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media\lua\server`.

- **[C] There is no "catch-up on load" for farming: every plant is simulated all the time, loaded or not.** `SFarmingSystem:EveryTenMinutes` (`Farming/SFarmingSystem.lua` 87-128) loops over `getLuaObjectCount()`, i.e. every global object of the system (`Map/SGlobalObjectSystem.lua` 40-46: `system:getObjectCount()` / `getObjectByIndex`), not over loaded squares. Each game hour it bumps `hoursElapsed`; every 5 hours (PlantResilience 3; 12/8/3/2 for the other settings, lines 98-111) `lowerWaterLvlAndUpDisease` (130-138); every 2 hours `changeHealth` (141-234); every 10 minutes `checkPlant` -> `checkPlant2` (236-290): growth when `hoursElapsed >= nextGrowing`, rain/sun water (`checkWater` 304-320), death by drought or health (`checkStat`, `SPlantGlobalObject.lua` 625-649), rot through `farming_vegetableconf.grow` (`farming_vegetableconf.lua` 283-284).
- **[C] What needs the tile is skipped while unloaded.** `getSquare()` is `getCell():getGridSquare` (`SGlobalObject.lua` 34-36). With no square, `checkPlantSquare` returns early (292-296), so `exterior` and `hasWeeds` keep their last values; `changeHealth` re-reads `exterior`/greenhouse only when a square exists (152-169); sprite/name changes go to the Lua state only (`setSpriteName` 111-124, `getObject()` is nil).
- **[C] State kept per plant** (`SFarmingSystem.lua` 30-35, saved in `gos_farming.bin`): state, nbOfGrow, typeOfSeed, fertilizer, mildewLvl, aphidLvl, fliesLvl, slugsLvl, hasWeeds, waterLvl, waterNeeded, waterNeededMax, lastWaterHour, nextGrowing, hasSeed, hasVegetable, health, badCare, exterior, spriteName, objectName, cursed, compost, bonusYield, naturalLight, owner. The Lua object *is* the Java GlobalObject's modData table (`SGlobalObject.lua` 63-79), so writing a field writes the saved state.
- **[C] On chunk load** `MOFarming.lua` 101-127 -> `SGlobalObjectSystem:loadIsoObject` (133-149) -> `SPlantGlobalObject:stateToIsoObject` (58-90) copies name, sprite and all fields onto the tile; it only resets `lastWaterHour/nextGrowing` when `lastWaterHour > hoursElapsed`. `OnChunkLoaded` (208-222) drops global objects whose tile is gone.
- **[C] Readable and writable while unloaded, from Lua in SP.** Java `GlobalObjectSystem` has `getObjectAt`, `getObjectsInChunk`, `hasObjectsInChunk`, `getObjectCount`, `getObjectByIndex` (javap `zombie.globalObjects.GlobalObjectSystem`); server Lua only guards on `isClient()` (`SFarmingSystem.lua` 1), so in SP it shares the Lua state with client mods. Sol already relies on this: `SolFarmView.tickPlants` reads plants by `getObjectsInChunk` (`_pending_refuel/SolFarmView.lua` 213-246) and `SolFarmAct` calls `plant:water/seed/cure*/fertilize` on the same objects (`SolFarmAct.lua` 88-145).
- **[C] Server calls that work with no square:** `SPlantGlobalObject:water(nil, uses)` (501-518), `cureMildew/Flies/Aphids/Slugs(nil, uses, skill)` (436-497), `fertilize({compost, skill})` (521-564), `seed(type, skill)` (715-734), `harvestThis()` (707-713); each ends in `saveData()`, a no-op without the tile (771-777). **Not** without a square: `SFarmingSystem:plow` (508-535), `removePlant`/`removeObject` (554-560), weeding (tile objects). `SFarmingSystem:harvest` (333-382) needs a player (`player:getPerkLevel` 334, items into `player:getInventory()` 345-358), so the far shift repeats its numbers (`getVegetablesNumber`, `farming_vegetableconf.lua` 17-76) without a player.
- **[C] Rain barrels are global objects too** (`RainBarrel/SRainBarrelSystem.lua` 19, 42-63: `waterAmount` saved and raised by rain while unloaded); `SRainBarrelGlobalObject:stateToIsoObject` (47-78) empties the tile's fluid and refills it from `waterAmount` on load. Water drawn from such a barrel while unloaded is taken from `waterAmount` directly. **[I]** Barrels built through the 42 entity/fluid system may not belong to `SRainBarrelSystem`; those go through the ledger like a tap.

### 2. Sol's farm runner, and what the far shift reuses

Staged copies in `07_TEST\SOL_LAB\_pending_refuel` (lab profile files read only).

- `SolFarmWork.lua`: `SolFarmPlan.next` (100-243) is a pure planner: harvest, water (whole doses, `waterDoses` 72-80, never outdoors in rain), pests (mildew first, `cureDoses` 81), weeds, sow plowed tiles, replant, plow new land, compost (stage <= 3, not winter), carry. `stillNeeded` / `verify` (245-266) judge a task on the live plant. The live runner (`W.tick` 1159-1274) needs her body; with no actor it only times out the job (1170-1178). Stops reach the Mind through `m.stops` (`say` 392-405) and `W.snapshot` (1342-1352), read by `SolWorldScan.lua` 430 and worded by `farm_talk.stop_line` (`05_TOOLS/sol_mind/farm_talk.py` 198-209; `chat_service._farm_watch` 1176-1206).
- `SolFarmKeeper.lua`: standing orders `modes.farm` / `modes.home` in ModData `Sol_Farm`; her body's needs first (86-108).
- `SolFarmView.lua`: zones from the base (98-107), plant rows (`readPlant` 124-131), stock only from the whole-base scan (`tickStock` 423-466; `unloaded > 0` makes it unsure, 458). `locate`/`locateContainer` (559-571) find an item again at a scan row; `places` scored (414-421); `waterSources` from the scan (`SolInventory.lua` 220-223).
- `SolFar.lua`: she is "far" when her registered actor has no square or her one saved record is pending (`record` 76-89, `solFarState` 91-100); `SCPersistence.pendingIds/pendingBootstrap` hold her saved place.
- Reused as is: `SolFarmPlan.next/stillNeeded/verify/key`, `SolFarmView.zones/readPlant/props/month/winter/raining/inSeason/locate/locateContainer/stockDirty`, the `Sol_Farm` stop list. Changed only in the plan's inputs for the far shift (not its code): no tools (so no plow/replant), weeds off, no player, `day = true, nightOk = true`.

### 3. Supplies while unloaded: the ledger

- **[C] Containers in unloaded chunks cannot be read or changed from Lua.** Items live in the chunk and load with it; `getGridSquare` is nil for an unloaded square and the whole-base scan already counts those as `unloaded` (`SolInventory.lua` 211). Containers have no global-object mirror. **[I]** Reading map_*.bin from outside the game is out of scope (every item loader; the save may be open).
- **Design (built), ModData `Sol_FarWork`:**
  - *Basis:* while the farm is loaded and a scan finishes complete (`ready`, `unloaded == 0`), a copy of the house rows (one row per item), food places and water sources is kept with its game hour. When the shift starts the copy (at most 48 game hours old) is frozen. No complete look, no shift: she does not guess.
  - *Reserve now:* each job reserves exact units against the basis (`used[row]`) and writes an entry `{id, op = take|use|pour|draw|give, row, n, hour}`. The plan only sees the basis minus reservations, so she can never use what is not there.
  - *Apply once on load:* when an entry's square loads, the item is removed / used / poured, the source drawn (`IsoObject.useFluid`, javap), produce added with `AddItem` to the best food place (fridge first), the next place when full, the floor beside it when all are full (`IsoGridSquare.AddWorldInventoryItem`, javap). Produce age = hours since she picked it (`InventoryItem.setAge`, javap): nothing comes back fresher than it is.
  - *Never twice:* the object holding the item (or the square) gets `modData.SolFarLedger["<world uid>-<entry id>"] = true` in the same frame as the change. That modData is saved with the chunk, the ledger with the world. If the world save is older than the chunk save (crash, reload), the entry comes back "reserved", finds the mark and closes without touching anything. (Same idea as Story Item Spawner marking squares, workshop 3037988451 `StoryItemSpawnerManager.lua` 609-611.)
  - *Plant changes* are not in the ledger: they go to the plant's global object at once and are saved with it (`gos_farming.bin`). **[I]** It and ModData are written by the same full world save, so a crash rolls both back together.
  - Rain barrels in `SRainBarrelSystem`: drawn from `waterAmount` at once, no ledger needed.

### 4. Her abstract work and the report

- Every game hour, night included, the shift reads the plants of every farm zone within 30 tiles of her saved place whose squares are not loaded, then repeats `SolFarmPlan.next` on them until the hour is used. Cost per job = real seconds of her body for it (water 25, harvest 30, cure 25, compost 25, sow 20, a can refill 45) times game minutes per real second (`1440 / (GameTime:getMinutesPerDay() * 60)`): with a one-hour day that is 6-7 jobs a game hour, never more than 30. After fast time (sleep) up to 6 hours are worked per second. Hours worked are counted in ModData (`lastHour`), so a reload goes on from the same hour.
- Conditions: switch `far_work`, keeper order `modes.farm`, her one saved record (or bodiless registration) near a zone, a complete basis. The shift ends when she is back, he comes near, the keeper order ends or the switch goes off.
- Report: counts in `Sol_FarWork.report` (watering rounds = runs of consecutive watering hours, plants watered, produce per item, tiles sown, plants sprayed, plants fed, what ran out, produce on the floor). When the farm is loaded again, he is within 70 tiles and the ledger is applied (or 30 s passed), one row `far_report` goes to the `Sol_Farm` stop list; the Mind says one line through `farm_talk.far_report_line`, e.g. "سقيت الزرع مرتين وقطفت 12 جزرة." No system words (tested).

### 5. Risks

- **Double application:** covered by the holders' marks (tested with a rolled-back ledger). Plant work lives in one save domain (global objects).
- **Save/reload:** ModData holds plain values only (tested); the hour counter and entry ids persist (tested by reloading the module mid-shift).
- **Vanilla already drains water while unloaded:** she waters by each plant's need at that hour, after vanilla's own drain, so nothing is counted twice. Rain fills outdoor plants; she never waters outdoors in rain.
- **Stale basis [I]:** if he took items from the house after the last complete scan and before leaving, an entry finds less than reserved; it takes what is there, closes as short and logs it. Kept small by requiring a complete scan and freezing it when the farm unloads.
- **Weeds stay stale** while unloaded (vanilla does not update them either); she does not weed, plow or replant from afar.
- **Can size [I]:** a refill counts as 15 doses (3 l); the real can size was not measured.
- **Food place room [I]:** checked by weight when applied, not when reserved.
- **Zombies, her needs, XP:** not simulated while far (owner: she works through the night). No farming XP from far work.
- **Multiplayer:** out of scope (SP only).
- **Performance:** one pass per game hour over the zone's chunk lists (no squares), at most 30 jobs; the ledger applies 8 entries per second.

### 6. Workshop ideas (ideas only)

- Story Item Spawner (3037988451) marks squares in square modData to spawn once; Authentic Z ground spawner (2335368829) keeps `spawnedItems` in ground modData: the same "mark on the saved object" trick the ledger uses. TchernoLib (2986578314) wraps custom global object systems (`SGlobalObjectCreator.lua`), an option if Sol ever needs her own. No installed mod simulates NPC work while unloaded.

### 7. Built (staged, not installed)

- `07_TEST\SOL_LAB\_pending_refuel\SolFarWork.lua` (0.1.0, ASCII); `apply_s74_far_work.py <client dir> <sol_mind dir>` (in place, idempotent: copies the file, adds `far_work` to `A.FIXES` and `far_work=on` to `SolFixes_LAB.txt`, adds `far_report_line` to `farm_talk.py`); `test_far_work.py`.
- `test_far_work.py`: 59/59 offline, on the game's own farming Lua (lupa through `kahlua_env`). Apply with the game closed; restart the Mind afterwards. Offline PASS is not Runtime PASS.

### 8. Runtime result 2026-11-10 night (lab, Jamal playing)

Log: `07_TEST\SOL_LAB\profile\Zomboid\Logs\2026-11-10_21-26_DebugLog.txt`.

- **PASS (log):** `[SolFarWork] shift started at hour 91 with 1478 rows, 50 places, 19 water sources.` (22:46:52), then `hour 92: 9 jobs`, `hour 93: 9 jobs`, `hour 94: 9 jobs`, `hour 95: 7 jobs`, `hour 96: 9 jobs` (43 jobs), then `shift ended (not_at_farm).` (23:05:16) when the farm loaded. The keeper order came from "هتمي بالمزرعة" / "ديري بالك عالزرع" (Mind 22:45:38, 22:46:25, `action=farm_keeper`).
- **FAIL: the return report was not spoken.** The log has `[SolFarWork] report given.` (23:05:26), but no line reached the chat. So the `far_report` row was written and the Mind did not say it (or did not read it). Fix in progress: **s85**.
- Not checked yet: whether the ledger applied the supplies and produce on load (no `[SolFarWork]` ledger lines in this log).
- Status: `far_work` stays **OFF in the release** until the spoken report is proven in play.
