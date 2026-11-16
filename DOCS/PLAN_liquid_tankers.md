# سول والتانكرات (Liquid Tankers): خطة (2026-11-11)

جمال بدو سول تشتغل مع مود "Liquid Tankers" (Workshop 3833260073، mod id `JullesLiquidTankers`): تعبي التانكر مي أو بنزين، تعبي منو السيارة والقناني، وتسحب من الكازية للتانكر.

**الحالة:** بحث بس. ما في ولا سطر كود، ولا مفتاح مركّب. كل شي تحت معلَّم **confirmed** (قريتو بملفات المود أو كود سول) أو **inference** (استنتاج، بدو تجربة باللعبة).

---

## 1. Is it installed? (confirmed)

| Where | Result |
|---|---|
| `C:\Program Files (x86)\Steam\steamapps\workshop\content\108600\3833260073` | **Present** (read only). `mods\JullesLiquidTankers\42.20\mod.info`: modVersion 1.5.1, versionMin 42.20.0, `incompatible=\ArcadiaRefillablePropaneTanks_B42`. |
| Same folder, re-checked at the end of this research | **Gone** (no longer on disk. I did not touch it, so Steam most likely unsubscribed it or is downloading it again). Every citation below comes from the v1.5.1 copy read earlier in this session. |
| `C:\Users\JAMAL\Zomboid\mods\default.txt` | **Not enabled** (no `JullesLiquidTankers` line). |
| `07_TEST\SOL_LAB\MODS_LAB_MIN.txt` | **Not listed.** |
| `07_TEST\SOL_LAB\profile\Zomboid\mods\default.txt` | **Not enabled.** |

Related mods in Jamal's own list (`Zomboid\mods\default.txt`), confirmed: `78amgeneralM49A2C`, `78amgeneralM50A3`, `90pierceArrow` are on; `AMGeneralTankerFunctionality`, `tsarslib`, `PZK*`, `SVU*`, `VVE*` are **not** on. `TankWater` is on in both lists (a different mod; overlap unknown, see open questions). None of these are in the lab list except `TankWater`.

Consequence (confirmed from code, see 2.7): with Jamal's current list, the KI5 **Pierce Arrow Quint** water tank becomes a Liquid Tankers tank, but the **M49A2C / M50A3** tanks do **not**, because that switch needs `AMGeneralTankerFunctionality` on (`JullesLiquidTankers_AMG.lua:1-14, 30-33`).

### Mod description (Jamal's post, summary; matches `mod.info`)
- A Chevalier D6 pickup rebuilt as a cab-chassis tanker, 2000 L tank (sandbox), one liquid at a time, any liquid including other mods' fluids.
- 20 company liveries (Fossoil, McCoy, fire dept, rangers, airport, army, Knox Distillery, Scarlet Oak, Mass Gen Fac, Spiffo's, Ovo Farms, Uncloggers, Charlemange, Genuine beer, Citr8, Kimble, March Ridge, Knob Creek, Direct Flame, plain), spawning partly filled near their own yards.
- Rear valve: fill or empty bottles, buckets, cans (right-click or V wheel). Drink at the valve (not fuel, not bleach).
- Rubber hose: pump between tankers, cars, gas pumps, fire hydrants, rain barrels, troughs, wells, sinks, rivers.
- Wet concrete / plaster for brick walls (bucket recipes).
- Propane: pump from station storage tanks; refill propane tanks, blowtorches, lanterns.
- Compat: SVU3, VVE, VVA, PZK VLC, KI5 AM General tankers (M49A2C, M50A3, M967), KI5 Pierce Arrow Quint, Tsar's Common Library trailers, Project Viewpoint (use right-click there). Not compatible with Arcadia's Refillable Propane Tanks. B42.20+.
- Sandbox: spawn rate, tank size, hose reach, propane on/off, one switch per company. Safe to remove.

Paths below are relative to `...\3833260073\mods\JullesLiquidTankers\42.20\media\`.

---

## 2. The real API (confirmed, file:line)

### 2.1 Where the liquid lives
- **Litres** are the vehicle part's container amount (`part:getContainerContentAmount()` / `setContainerContentAmount`), saved and synced like the vanilla gas tank. **Liquid name** (a FluidType string, e.g. `"Water"`, `"Petrol"`, `"TaintedWater"`, `"LiquidPropane"`) is in `part:getModData().JLT_fluid`. `lua/shared/JullesLiquidTankers_Tank.lua:1-4, 9-11`.
- Not a FluidContainer. The part is `LiquidTank`, contentType `"Liquid"`; a tank is **any part whose container contentType is `Liquid`** (`Tank.lua:24-26`). `T.getTanks(vehicle)` lists them in part order (`:29-37`), `T.getTank(vehicle)` gives the first (`:40-45`). KI5/AMG/PZK tanks are switched to the same contentType at load, so the same calls work on them.
- Capacity = part item MaxCapacity, from sandbox `TankCapacity` (default 2000, 100-10000) (`Tank.lua:12-18, 151-159`; `sandbox-options.txt:13-18`).
- `T.getFluidName(part)` → name or nil when empty (`Tank.lua:77-80`). `T.contentsLabel(part)` → display text (`:143-148`). `T.partFluid(part)` also answers `"Petrol"` for a vanilla `GasTank` (`:252-258`).
- Server-side setter `T.setContents(part, fluidName, litres)` clamps, sets modData, `transmitPartModData` (`:162-173`). Sol must **not** call it directly (cheating); she uses the timed actions.
- Container access only from outside the vehicle (`Tank.lua:717-719`).

### 2.2 Rear valve: carried containers (no hose)
- Timed action **`JLT_TankTransfer:new(character, part, item, direction, otherItems)`**, `direction` = `"fill"` (tank → item) or `"pour"` (item → tank); `otherItems` chains the rest (`lua/shared/TimedActions/JLT_TankTransfer.lua:14, 166-176, 117-138`).
- Valid only while the item is in the character's inventory (`:16-19`). Duration 25 ticks per litre; a fill is capped by the character's free carry weight (`:148-164`).
- Checks: `T.fillBlock(part, item)` / `T.pourBlock(part, item)` return a reason key or nil (`Tank.lua:184-215`): `tankempty`, `itemfull`, `otherliquid`, `locked`, `cantholdliquid`, `sealed`, `mixed`, `tankfull`.
- `T.newItemTransfer(...)` picks `JLT_PropaneItem` for propane items, else `JLT_TankTransfer` (`JLT_TankTransfer.lua:880-883`).
- Menu helper `T.queueTransfer(playerObj, part, items, direction)`: exits the car, `ISPathFindAction:pathToVehicleArea(player, vehicle, part:getArea())`, equips the first item, queues the action (`lua/client/JullesLiquidTankers_Menu.lua:129-139`).

### 2.3 Hose: vehicle to vehicle
- **`JLT_VehicleTransfer:new(character, fromPart, toPart)`** (`JLT_TankTransfer.lua:182, 306-314`). Parts are a `LiquidTank` or a vanilla `GasTank` (`Tank.lua:260-268`).
- Needs an item with tag `ItemTag.SIPHON_GAS` (rubber hose) anywhere in the inventory (`JLT_TankTransfer.lua:184-186, 197`).
- Range: distance between the two parts' area centres ≤ `HoseReach` + 0.5 (default 6, 2-10) (`:194-203`; `Tank.lua:234, 240-245, 299-314`; `sandbox-options.txt:23-28`). The menu also refuses when a third car is on the straight line (`Menu.lua:184-194, 211`).
- Rules `T.vehicleBlock(from, to)`: `fromempty`, `propaneoff`, `notfuel` (only Petrol into a gas tank), `tofull`, `otherliquid` (`Tank.lua:271-280`). Speed 10 ticks per litre (`Tank.lua:235`).
- Finder `T.findTransfers(vehicle, onlyTank)` scans a square of `reach+10` tiles around the vehicle and returns `{tank, part, from, to, dir, reason, amount, dist}` sorted by distance (`Menu.lua:199-244`). Helper `T.queueVehicleTransfer(playerObj, t)` walks to the tank's valve, equips the hose, queues (`Menu.lua:302-311`).

### 2.4 Hose: world sources
- **`JLT_WorldTransfer:new(character, part, object, direction)`**, `"fill"` (world → tank) or `"drain"` (tank → world) (`JLT_TankTransfer.lua:321, 458-466`). Hose needed; valve-to-object distance ≤ reach + 0.5 (`:323-329`).
- Sources (`Tank.lua:316-502`): gas pumps (`getPipedFuelAmount() > 0`, 1 unit = 1 L, power rule same as vanilla `ISVehicleMenu`: generator or grid) (`:321-342`); fire hydrants (sprite `street_decoration_01_12`; unlimited while mains water is on, after shutoff 1000-6000 L reserve and needs power) (`:375-418`); anything with `getFluidContainer()` (rain barrels, troughs, wells) or `getFluidAmount() > 0` (sinks, toilets, baths, rivers/lakes) (`:421-444`). Puddles are excluded (`:346-352`). Propane depots (`T.isDepot`) give propane (`:423`).
- Fill only from a source holding the same liquid as the tank, or into an empty tank (`T.worldFillBlock`, `:447-457`). Drain only into objects with their own FluidContainer (barrels, troughs) or a propane depot; never into pumps, hydrants, sinks, rivers (`T.worldDrainBlock`, `:460-481`).
- Speed 5 ticks per litre (`Tank.lua:236`). Pump sound `VehicleAddFuelFromGasPump` (`JLT_TankTransfer.lua:405-409`).
- Finder `T.findWorldSources(part)`: scans `(2·ceil(reach)+1)²` squares round the valve, nearest first, unlimited sources (rivers, piped water) once per name (`Menu.lua:337-378`). Names via `T.worldName(obj)` (`:380-407`). Helper `T.queueWorldTransfer(playerObj, part, obj, direction)` (`:451-462`).

### 2.5 Empty, drink, propane, repair
- `JLT_EmptyTank:new(character, part)`: open the valve onto the ground, liquid lost, 6 ticks/L (`JLT_TankTransfer.lua:472, 553-568`; `Tank.lua:237`).
- `JLT_DrinkFromTank:new(character, part)`: water and Beverage-category liquids only (`JLT_TankTransfer.lua:575-676`; `Tank.lua:119-140`).
- Propane: fluid `LiquidPropane`, 20 L = one full propane tank; switch `SandboxVars.JullesLiquidTankers.Propane` (`lua/shared/JullesLiquidTankers_Propane.lua:14-17, 82-88`). `JLT_PropaneItem:new(character, part, object, item, direction, otherItems)` refills/empties propane items at the valve or at a depot (`JLT_TankTransfer.lua:707-877`). Depot litres live in the anchor tile's modData `JLT_propane` (`Propane.lua:137-270`). Propane never goes into liquid containers (`Tank.lua:184-198`).
- The mod overrides `ISFixVehiclePartAction:complete` for tank parts (vanilla bug fix) (`JLT_TankTransfer.lua:683-699`). Global override, harmless for Sol.

### 2.6 Menus (what Jamal sees)
- Both menus come from one wrap of **`ISVehicleMenu.FillPartMenu(playerIndex, context, slice, vehicle)`**, only when the player is outside the vehicle and within 4 tiles (`Menu.lua:876-885, 735`).
- **V wheel** (`slice`): Fill / Pour / Drink / nearest gas pump / nearest hydrant / nearest propane depot / Empty (`Menu.lua:790-838`). **Right-click**: submenu "Liquid Tank (Water 500 / 2000 L)" with per-item Fill/Pour, Fill all / Pour all, vehicle transfers, world transfers, Drink, Empty Tank (`:841-874`). A non-tanker car next to a tanker gets top-level "Refuel from …" / "Siphon into …" (`:737-741`).
- World right-click on a propane depot: `Events.OnFillWorldObjectContextMenu` (`Menu.lua:958-970`).

### 2.7 KI5 support (confirmed)
- `[Ki5] AM General Tanker Functionality` (mod id `AMGeneralTankerFunctionality`): when on, parts `AMGTF_M49A2CCargoTank` (Petrol), `AMGTF_M50A3CargoTank` (Water) and the M967 trailer `1000FuelTank` (Petrol) become `Liquid` tanks (`lua/shared/JullesLiquidTankers_AMG.lua:1-14, 23-28, 30-33`).
- KI5 Pierce Arrow Quint (mod id `90pierceArrow`): `1500WaterTruckTank` switched when PZK is off; Tsar's `TruckTank` template tanks (`500FuelTank`, `1000FuelTank`) when `tsarslib` is on (`lua/shared/JullesLiquidTankers_KI5.lua:1-15, 59-80`).
- So Sol must find tanks by **contentType `Liquid`** (`T.isTank`), never by part id or vehicle name. This also keeps Jamal's "no vehicle names in code" rule.

### 2.8 Sandbox options (confirmed, `sandbox-options.txt`)
`SpawnRate` (enum, default 3), `TankCapacity` (100-10000, 2000), `HoseReach` (2-10, 6), `SpawnConstruction` (bool), `Propane` (bool), `PropaneDepotCapacity` (20-20000, 3000), `Livery<Company>` booleans (lines 3-205+).

---

## 3. Sol today (confirmed, read only)

Lab client Lua: `07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\lua\client`.

| Piece | What it does | Where |
|---|---|---|
| `refuel_from_can` | "عبي السيارة بنزين": her cans, then cans at home, poured with vanilla `ISAddGasolineToVehicle` into part `GasTank`. **Cans only**, the station is not touched. | `SolCanRefuel.lua:1-3, 20-23, 42-43, 169`; `U.solCanRefuel` `:275` |
| `refuel` (station) | `sol_fuel` find/mark/walk/car/can/status; vanilla `ISRefuelFromGasPump` (car) and `ISTakeFuel` (can) at a remembered pump (Java `SolStations`). | `SolFuel.lua:1-4, 287, 337-346, 361-367, 400-424, 547` |
| `sol_fill_water` | one empty bottle in her bag from the nearest `hasWater` object within 10 tiles, vanilla `ISTakeWaterAction`. | `SolActionRegistry.lua:150-160` |
| Mind card | `refuel_from_can` (example "عبي السيارة بنزين"), `refuel_at_station` ("عبي السيارة بنزين من الكازية"), `sol_fill_water` ("عبي القنينة مي"), `sol_fuel` ("شغلي مضخة البنزين"). | `05_TOOLS\sol_mind\model_router.py:40-41, 47, 345-346` |
| Fuel gate | refuel actions need a fuel word (`FUEL_WORDS`, includes "عبي"); `refuel_from_can` runs straight away. | `chat_service.py:18, 1505-1521` |
| Switches | `refuel_from_can=on`, `refuel_top_up=on`, `refuel_short_hop=on` | `profile\Zomboid\Lua\SolFixes_LAB.txt:26, 32-33` |

None of these know about `Liquid` parts: Sol sees a tanker only as a car with a `GasTank` (inference: `tankOf` / `fillCar` read `getPartById("GasTank")` only).

---

## 4. Mapping (inference unless marked)

### 4.1 Detection, once
`local T = rawget(_G, "JullesLiquidTankers")` and `rawget(_G, "JLT_WorldTransfer")` non-nil, or `getActivatedMods():contains("JullesLiquidTankers")`. Everything is off when missing. No `require` of their files (they load anyway when the mod is on).

### 4.2 Use their actions, not their menu helpers
Their `T.queue*` helpers are written for the human player (`ISVehicleMenu.onExit`, `ISInventoryPaneContextMenu.equipWeapon(item, …, playerNum)`) (`Menu.lua:131-138, 305-310`). Sol already runs vanilla timed actions on her own body (`U.timed`, SolFuel's own walk/park). So Sol should:
1. find the part with `T.getTanks(vehicle)` and read `T.getFluidName` / litres;
2. pick the source with `T.findWorldSources(part)` or `T.findTransfers(vehicle, part)` and test with `T.worldFillBlock` / `T.vehicleBlock` / `T.fillBlock`;
3. walk herself to the valve (`part:getArea()` centre), hold the hose (or the bottle), and queue `JLT_WorldTransfer:new(sol, part, obj, "fill")`, `JLT_VehicleTransfer:new(sol, from, to)` or `JLT_TankTransfer:new(sol, part, item, "fill", rest)` on her own queue;
4. watch the litres change; the action keeps them honest (MP-safe, synced).

Needs in-game test: that these actions run on Sol's character the way vanilla `ISRefuelFromGasPump` does (they derive from `ISBaseTimedAction` and use `faceThisObject`, `setActionAnim`, `getFreeInventoryCapacity`; nothing player-only inside the actions themselves, confirmed by reading `JLT_TankTransfer.lua`).

### 4.3 The hard part: parking within hose reach
World and vehicle hoses need the **valve** (rear, part area centre) within 6 tiles of the source or of the other car's filler (`Tank.lua:299-314, 495-502`). For a river or hydrant Sol must drive the tanker so its back is close. She already has "park by the pump cap" logic (`SolFuel.lua:272-309`), so the plan reuses it with the valve point instead of the fuel cap. For tanker → car, the two vehicles must stand within reach with no third car between; if they are not, she drives one of them over (open question which).

### 4.4 Proposed Mind actions (one per behaviour, no duplicates)

| Jamal says | Action | Why this way |
|---|---|---|
| "عبي التانكر مي من النهر"، "عبي الصهريج مي من الحنفية/البير/البرميل"، "عبي السيترنة من الإطفائية (الحنفية الحمرا)" | **new** `tanker_fill` (option: `water` / `fuel` / source hint `river|hydrant|well|barrel|sink|pump`) | New behaviour: nothing on the card fills a vehicle tank from the world. |
| "اسحبي بنزين من الكازية للتانكر"، "عبي التانكر بنزين" | same `tanker_fill`, option `fuel` (source = gas pump; reuses SolFuel's station memory and power check) | Same behaviour as the line above (tank ← world source). Not a new action. |
| "عبي السيارة من التانكر"، "حطي بنزين بالسيارة من الصهريج" | **new** `tanker_to_car` | New behaviour (vehicle ← vehicle with a hose). Kept **apart** from `refuel_from_can`: "عبي السيارة بنزين" stays **gas can only** (Jamal's rule). |
| "عبيلي قناني مي من التانكر"، "املي المطرات من الصهريج" | **existing** `sol_fill_water`, option `tanker` | Same behaviour (fill bottles with water), new source. Option only. Today it fills one bottle; several bottles = `otherItems` chain of `JLT_TankTransfer`. |
| "قديش في بالتانكر؟"، "شو في بالصهريج؟" | `none`, answered from the snapshot | Add one line per nearby tank to `SolWorld_Snapshot.txt` ("tanker: Water 500/2000 L, 8 m"). No new action. |
| "فضي التانكر"، "كبي اللي بالصهريج" | not proposed now | Irreversible (liquid lost). Only if Jamal asks; then an option of `tanker_fill` (`empty`) behind its own switch. |

Card rule (model-first): the new wordings go on the card as **examples** (`EXAMPLES_S90`, `COMMANDS`, `CARD_ACTIONS`) with `SOL_MODEL_CARD.md` updated in the same change, gated by `card_check.py`. No keyword overrides. Vocabulary to teach as examples: تانكر، صهريج، سيترنة، التنك الكبير، الخزان اللي ورا.

Gate risk (confirmed): `FUEL_WORDS` contains "عبي", so "عبي السيارة من التانكر" passes the fuel gate, and the model could still pick `refuel_from_can`. The card needs contrasting examples ("عبي السيارة بنزين" → can; "عبي السيارة من التانكر" → `tanker_to_car`).

### 4.5 Proposed switches (one change each, `SolFixes_LAB.txt`, OFF in the release until runtime PASS)

| Switch | Change |
|---|---|
| `tanker_seen` | Detection + snapshot line (litres, liquid, distance) for tanks within 30 tiles. Read only. |
| `tanker_fill` | Drive/park the tanker valve within reach, hose, `JLT_WorldTransfer` "fill" from river/hydrant/well/barrel/sink. |
| `tanker_from_station` | Same with a gas pump (station memory, power check, `refuel_short_hop` style approach). |
| `tanker_to_car` | `JLT_VehicleTransfer` tanker `Liquid` part → car `GasTank` (Petrol only; `notfuel` blocks the rest). |
| `tanker_bottles` | `sol_fill_water` option `tanker`: `JLT_TankTransfer` "fill" chain for her empty bottles (water only; tainted named as such). |

### 4.6 Performance (inference, from the code sizes)
- `findWorldSources` = 169 squares at reach 6; `findTransfers` = 33×33 = 1089 squares. Call **once per order**, never per tick.
- The snapshot line should come from the vehicles Sol already scans (`cars_near` / `SolWorldScan`), plus one `getPartCount` loop per vehicle; no new grid scan.
- Durations: 2000 L from a river ≈ 10 000 ticks (5 ticks/L); 60 L into a car ≈ 600 ticks; 1 L bottle ≈ 25 ticks. Sol's watchdogs (`MAX_PUMP_MS` 240 s in `SolFuel.lua:8`) need a longer limit for a full tanker, or a stop at a sensible amount.

---

## 5. Council (المجلس)

**المهندس:**
المود مرتب ومنيح للربط. الليترات بالـ part نفسو واسم السائل بالـ modData، وكل الشغل timed actions مستقلة: `JLT_WorldTransfer` و`JLT_VehicleTransfer` و`JLT_TankTransfer`. يعني سول ما بتغش، بتعمل نفس اللي بيعملو جمال بالضبط، ومنعرف التانك من الـ contentType `Liquid` مش من اسم السيارة، فالـ KI5 بيشتغل لحالو. الشغل الحقيقي عنا مش بالمود، بالتصفيف: لازم ضهر التانكر يوصل لـ 6 بلاطات من النهر أو الحنفية الحمرا أو فم تنك السيارة. عنا منطق "صفي جنب غطا البنزين" بـ `SolFuel`، منعيد استعمالو بنقطة الحنفية الخلفية.

**محامي الشيطان:**
تمهل شوي. أولاً المود **مش مفعّل** لا عند جمال ولا بالمختبر، يعني ولا شي من هاد مجرّب. تانياً الـ M49 والـ M50 تبع KI5 ما بيصيروا تانكرات إلا إذا انحط `AMGeneralTankerFunctionality`، وهو مش بالقائمة، فإذا جمال متوقع شاحنة الجيش تشتغل، رح تخيب. تالتاً "عبي" موجودة بـ `FUEL_WORDS`، فالموديل ممكن يفهم "عبي السيارة من التانكر" عالبدون، ويروح يجيب بدون من البيت. رابعاً الـ helpers تبعهن مكتوبين للاعب (`getPlayerNum`)، وإذا استعملناهن على سول ممكن يفتحو إيد جمال مش إيدها. خامساً تعبئة 2000 ليتر بتاخد وقت طويل، والـ watchdog تبعنا 240 ثانية رح يقطعها بالنص. وكمان `TankWater` مفعّل عندو، وما منعرف إذا بيتعارك مع هاد المود على نفس البراميل.

**الاستراتيجي:**
منمشي خطوة خطوة، وكل خطوة ورا مفتاح. أول شي `tanker_seen` بس: تشوف التانكر وتقول شو فيه، بلا ولا حركة، وهاد بيجاوب على نص أسئلة جمال. بعدين `tanker_bottles` لأنو أسهل وحدة: ما بدها خرطوم ولا تصفيف، وبتركب على `sol_fill_water` كخيار. بعدها `tanker_fill` من النهر والحنفية، وآخر شي `tanker_to_car` و`tanker_from_station`. "عبي السيارة بنزين" بتضل بدون بس، وأي تغيير بمعنى أمر موجود بيروح سؤال لجمال، مش قرار. ومنستعمل الـ actions تبعهن مباشرة على جسم سول، مش الـ queue helpers. وقبل أي شي، جمال لازم يقرر يفعّل المود (ومعو `AMGeneralTankerFunctionality` إذا بدو شاحنات KI5)، وما منركّب شي واللعبة شغالة.

Sources: the mod's own Lua and scripts (cited above, read only, nothing copied); Jamal's Workshop description (summary in section 1); Sol lab Lua and Mind files (section 3).

---

## 6. Arabic test phrases

Must route to the new or extended actions:
1. "عبي التانكر مي من النهر" → `tanker_fill` (water, river)
2. "روحي عبي الصهريج مي من الحنفية الحمرا" → `tanker_fill` (water, hydrant)
3. "عبي السيترنة من البير" → `tanker_fill` (water, well)
4. "اسحبي بنزين من الكازية للتانكر" → `tanker_fill` (fuel, pump)
5. "عبي التانكر بنزين" → `tanker_fill` (fuel)
6. "عبي السيارة من التانكر" → `tanker_to_car`
7. "حطي بنزين بالسيارة من الصهريج" → `tanker_to_car`
8. "عبيلي قناني مي من التانكر" → `sol_fill_water` option `tanker`
9. "املي المطرات من الصهريج" → `sol_fill_water` option `tanker`
10. "قديش في مي بالتانكر؟" → `none`, answer from snapshot

Must **not** change (regression):
11. "عبي السيارة بنزين" → `refuel_from_can` (gas can only)
12. "عبي السيارة بنزين من الكازية" → `refuel_at_station`
13. "عبي القنينة مي" → `sol_fill_water` (normal source, not the tanker)
14. "شغلي مضخة البنزين" → `sol_fuel`

Expected refusals (in character, Levantine):
- Tank holds whiskey and he asks for water → "التانكر فيه ويسكي، ما بقدر حط مي فوقو."
- No rubber hose → "ما معي خرطوم مطاط."
- Pump without power → "المضخة ما فيها كهربا."
- Water into the car → refused by `notfuel`, she says the car takes petrol only.

---

## 7. Open questions for Jamal

1. **Enable the mod?** It is in Workshop but not in any mod list (yours or the lab's). Add `JullesLiquidTankers` to the lab list for testing?
2. **KI5 AM General tanks:** do you want `AMGeneralTankerFunctionality` too? Without it the M49A2C / M50A3 tanks stay plain trucks for Sol and for you.
3. **Meaning of "عبي السيارة بنزين":** it stays gas can only. Should Sol *ever* fall back to a nearby tanker when no can is found (e.g. offer it: "ما في بدون، بعبيها من التانكر؟"), or never?
4. **Which vehicle moves for tanker → car:** Sol drives the tanker to the car, or the car to the tanker?
5. **How much to pump:** fill the tanker to the top (2000 L from a river takes minutes), or a fixed amount / until you say stop?
6. **Tainted water:** may she fill the tanker from a river (tainted by sandbox) and bottles from it, or clean sources only?
7. **Propane, concrete, plaster, drinking at the valve, emptying the tank:** in scope now, or later?
8. **`TankWater` mod:** it is enabled for you and in the lab. What does it do for you, and should Sol keep using it beside Liquid Tankers?
9. **Project Viewpoint:** the mod author says use right-click there; Sol does not use menus, so no effect expected (inference). Confirm nothing else to watch.

---
## Decision (Jamal, 2026-11-11 08:43)

"عبي السيارة بنزين" fills in this order:
1. Her own gas can.
2. The nearest gas can at home or in storage.
3. If there is no gas can, the nearest tanker holding gasoline. She says she filled from the tanker.

Never from a station. This is behind the switch `tanker_to_car` (OFF until played).

---
## Build s94: where I stopped (2026-11-11, paused by priority change)

**State:** research for the build only. No code file written, nothing installed, no switch added (the five switches do not exist anywhere yet; when added they must be appended as `=off`, because in the lab a missing line means ON, `SolAuthority.lua:94-114`).

Findings to build on (confirmed by reading the lab client and the live Mind):
- Live card (one tier, `CARD_TIERS=False`): 4580/4600 chars with her hand on the horn; `card_check.py` PASS. `sol_fill_water` is **not** on the one-tier card today (hidden game action). The s91 keep_engine example also does not reach the one-tier card (it went into the s90 bank).
- The tanker additions (2 list lines + ~5 example lines) cost about 600 chars, so the card needs ~600 chars of compaction. Candidates: s91's `_TRIM_S91` head trims (~60), English game-button labels dropped for buttons with an Arabic example (~90), meaning text dropped for self-explaining phrases (forget_all, why, secret_loadout, follow: ~80), duplicate examples (`خلص انسي كلشي`, `شو في سيارات حواليكي`: ~60), two of the six place questions (~30). Still short; decide what to drop or raise the budget (Jamal).
- Mind route: `tanker_fill` / `tanker_to_car` as `COMMANDS` with phrase `None` need their own branch in `Chat._route_by_model` (the generic COMMANDS branch routes by phrase). Anchor for an in-place insert: just before `if action == "why":`. `card_check` finds the branch by `action == "..."` / `action in (...)`.
- `_can_watch` splits `done:<l>:<pct>` into exactly 3 parts: the tanker fallback must report a different prefix (e.g. `tanker_done:<l>:<pct>`) and the Mind block must word it ("ما لقيت بدون، فعبيتها من التانكر ...").
- Gas-can fallback hook: `SolCanRefuel.lua` `step()`, scan phase, the `return finish("failed", "no_can")` line (only when nothing was poured); the status read `return true, lastResult or "idle"` must also return the tanker job's status.
- `sol_fill_water` is a registry verb (`SolActionRegistry.lua:150`); the registry wraps `U.runAction` at OnGameStart and checks verbs first, so an option `tanker` wrapper must be installed after it (OnGameStart, a file loading after SolActionRegistry).
- Loaded vehicles: `SurvivorCompanion.Vehicle.loadedVehicles()` (cell:getVehicles is gone in 42.21; `SolActions.lua:157`).
- Snapshot hook for `tanker_seen`: wrap `U.scanWorld` and `U.writeWorldRaw(ready)` (sliced path passes the table), add `snap.solTankers`; `SolWorldScan.lua` loads after a file named `SolTanker*`, so wrap lazily.
- Route eval: tanker cases added to `s82_route_eval.json` must carry a marker (e.g. `"needs": "tanker_fill"`) and `test_s82_route_eval.py` must skip them on a Mind without that command, or `card_check` on the live Mind fails.

Next steps: write `SolTanker.lua` (detect `JLT_*` globals, all five switches, no-op without the mod), `apply_s94_tanker_lua.py`, `apply_s94_tanker_mind.py`, `test_s94_tanker.py` (lupa via `kahlua_env`, mocked JLT actions/vehicle/part), compact the card, run `card_check.py` (and `--write-doc` to a staged copy of the doc) and `tonumber_check.py` on the patched copies. Open: who moves for tanker -> car when out of hose reach (no driving planned in the first build), source hint (river/hydrant/well) as an option or picked by the game.
