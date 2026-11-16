# Sol — دليل التسليم (Handoff)

**The current project plan is `DOCS/SOL_PLAN_20261111.md`.**

**Current handoff - 2026-11-16:** release 0.28.8 is built from the lab, installed on the main game (not opened since), packaged (`08_PUBLIC/Sol-0.28.8.zip`) and merged to GitHub `main`. State, what was done on 2026-11-15/16 and the open list by priority: `DOCS/SOL_NEXT_20261116.md`. Newest pieces: wardrobe (s156), phone_patience (s157), under_cloth chest shape in `SolCombined.jar` (s159, tools in `05_TOOLS/sol_cloth`). `modest_chest` must stay off.

**Current handoff — s147, 2026-11-14:** The private `01_WORK/RELEASE/SOL_2026-11-13_0.28.5_HELICOPTER_RC` candidate now includes the missing staged s108 performance work plus the verified s99/s112 scan, s104b/s116/s118/s119/s120 combat, and hit-routing changes. The full interactive s107 gear page, candidate Mind/card, helicopter GPS/speed/altitude/manual features, and summon feature were preserved. Evidence and limits are recorded in `DOCS/COUNCIL_s147_merge_0.28.5_candidate.md`, `DOCS/SOL_NEXT_20261113.md`, and `DOCS/SOL_LEDGER.md`. Offline tests and package gates pass; actual game acceptance is pending. No game was launched, and no save, Steam/Workshop, installed MAIN, or other release bundle was touched. Pre-merge copy: `07_TEST/SOL_LAB/_backup/20261113_2300_before_s146_restore_gear_page/pre_s147`.

**Lab launch note — 2026-11-12:** Run `07_TEST\SOL_LAB\launch_lab.ps1` from a PowerShell session and leave that session attached until the game closes. The launcher now waits on the game PID so managed command sessions do not terminate the child game on shell exit. In the Codex restricted executor, ZombieBuddy's Java startup needs loopback access: sandboxed launch failed at `SteamWorkshop.<clinit>` with `SocketException: Permission denied: connect`; elevated `launch_lab.ps1` then loaded mods and reached in-game Lua initialization. This was a launcher permission boundary, not a Sol combat error. `console.txt` may show stock font/FluidContainer warnings; check for `GameThread exited` and the loopback exception before calling startup a failure.

**Combat batch — 2026-11-12:** s119 close-range retreat counterfire + s120 fierce-only nearby grounded-target fire and urgent aim timeout are installed in `SOL_LAB` only, backed up at `_backup\20261112_before_s119_s120_combat`. Offline Lua tests pass; in-world behavior is still awaiting Jamal's test. Do not promote to MAIN/release before observed firing, actual hit/damage records, retreat resumption, and no new Sol Lua errors.

**Read `DOCS/SOL_WORKFLOW.md` first (how we work: rules, fix cycle, gates, tools, traps).** Update 2026-11-11 13:12: current state and the test list are in `SOL_NEXT_20261111.md`.

**Current handoff — 2026-11-12 20:09:** s119/s120 are installed in SOL_LAB only after backup `_backup\20261112_before_s119_s120_combat`; offline and launcher gates pass. The elevated lab launch is alive at `MainScreenState` (not yet in-world), with `[SolAuthority] Sol_LAB test copy active` and `[SolShootDiscipline] loaded 0.2.0`; no Sol Lua runtime error has appeared during startup. The current save session is `2026-11-12_18-08-44`. Load it and test fierce counterfire while retreating, fierce grounded-target shots, preserved stomp behavior outside fierce, and urgent reaction. Keep the PowerShell launcher session open until the game closes. MAIN, Steam and release remain untouched.

**Latest handoff — s123, 2026-11-12:** Added the distinct `سول طيري بالمروحية` pilot-seat order and standardized `عطيني القيادة` for the existing in-vehicle handoff. Sol's pilot-seat takeover can move the player from seat 0 to an empty reachable passenger seat; GPS Start also takes Sol to seat 0 before requesting flight. Offline tests and card/preflight gates pass. Latest elevated lab launch reached Sol Lua initialization and `[SolGPS] ready`; the save/world has not been entered, so helicopter flight remains unverified. Backup: `07_TEST/SOL_LAB/_backup/20261112_224501_214054_before_s123_heli_and_handoff`. Load isolated save `2026-11-12_18-08-44` and test pilot takeover, marker+Fly, altitude modes, Stop and errors. Do not promote to MAIN/release before live pass.

## ملخص بالعربي
هاد الملف لأي حدا (أو أي نموذج) بدو يكمّل شغل مود سول بعدنا.
- **وين كل شي:** المجلد الأساسي `C:\Users\JAMAL\Desktop\Sol`، والمختبر `07_TEST\SOL_LAB`.
- **التشغيل:** دايماً عن طريق `launch_lab.ps1`، وما بنستعمل `SOL_LAB_LAUNCHER.bat` أبداً.
- **التعديلات:** كل تعديل ورا مفتاح لحالو بملف `SolFixes_LAB.txt`. وكل تعديل بيتجرّب خارج اللعبة أول، وبعدين باللعبة.
- **الحالة الحالية:** القسم 0 تحت (آخر تحديث 2026-11-10 بالليل). كل تعديل من s63 لـ s85 مع مفتاحو وحالتو والـ commit: [`SOL_LEDGER.md`](SOL_LEDGER.md). اللي نجح باللعبة مع الأدلة: `SOL_CAPABILITIES.md`.
- **اللي نجح باللعبة 2026-11-10:**
  - الدرج مع Shift، أسماء الشوارع والمدن، الشاشة السودا بـ Viewpoint والزوم.
  - الزراعة: حراثة 31 مربع، زراعة 44، سقاية 79.
  - الصف بكراج البيت، أمر السواقة الجديد بيلغي القديم، الكازية، تحذير الـ GPS، المدرعة، حماية Ctrl+A، الجيّة مشي من بعيد، النقطة الخضرا.
  - بالليل: السلاح السري، الفحص بلا إحداثيات، الـ GPS عالطرقات بكل الخريطة، ودفتر العناوين بيتعلّم لحالو.
- **انركّب وما انجرّب لسا:** الزمّور الممسوك، السرعات 20/40/65، `stall_ladder`، `address_target`، `preview_calm`، القواص من مقعد السيارة، والدجاج والفرز.
- **قواعد جمال** بالقسم الأخير. أهمها:
  - عربي شامي مهذب.
  - نحكي الصدق: مؤكد، أو استنتاج، أو بدها تجربة.
  - ما منلمس ملفات Steam وWorkshop ولا موافقات ZombieBuddy.
  - ما في دمج.
  - ما في أوامر مكررة.

---

## 0. Current state (2026-11-10 night)

- **Game:** closed. Last lab session 21:26-23:08 (`profile\Zomboid\Logs\2026-11-10_21-26_DebugLog.txt`). Installed after it (switch file 23:12): `horn_hold`, `speed_levels`, `stall_ladder`, `address_target`, `preview_calm`, `veh_shoot_seated`, the s78 Lua part. None played yet.
- **Mind:** live as committed in 29363d7 (s63-s82); card gate `card_check.py` in `launch_lab.ps1` exit 8 and in `build_release.py` (04864fb).
- **Release:** 0.28.0 built and installed to main (`C:\Users\JAMAL\Zomboid\mods\Sol`, `SolFixes_MAIN.txt`), branch `release/0.28.0` (4796dab), draft PR https://github.com/jamallionjan-dev/Sol/pull/6. Never merge. `secret_loadout` is now on the ON list for the next refresh.
- **Every fix, switch, status and commit:** [`SOL_LEDGER.md`](SOL_LEDGER.md). Runtime evidence: `SOL_CAPABILITIES.md` ("Proven 2026-11-10 (night)" and "Not yet proven"). Council: `SOL_REVIEW_20261109.md` section 43.
- **Tonight's runtime (Jamal playing):**
  - PASS: secret weapon capture + give (Jamal: "نجح"); survey without coordinates; `gps_static_roads` (route along the roads through fog, 249 points, plans 3-52 ms); address book auto-capture (625 Dewey, 70 Frederick Ln, Louisville Central map).
  - Half: long drive to 625 Dewey (arrived about 15 tiles from the marker but on S Main St behind the house -> s82 `address_target`, installed); `far_work` (shift hours 92-96, 43 jobs, ended when the farm loaded; report not spoken -> s85); `cars_near` (routing right, no answer while she is away at home -> s78, installed).
  - FAIL, fixed or in progress: two stalls 22:04:42 / 22:08:15 (-> s81 `stall_ladder`, installed); street/city question regression (-> s82 map fallback + card examples); "متور" misroute (-> s82); rest-from-car refusal (-> s85); meta leak "اللاعب" (-> s78 reply gate); `far_car` live load 2-byte header (-> 4b8ad83, `far_car` OFF); brochures not captured (-> s84); shooting from the car seat through the roof (-> s83, installed); Viewpoint QOL harvest `getShovel` NPE, third party (-> `compat_vp_harvest`); door route `leg_stalled` 23:05:51 (in progress); held horn's card hook broken by the s82 compaction (-> s85).
  - FPS drop while driving: mostly the game's own world streaming (inference).

### Open items and next steps (priority order)
1. **s85** (in progress): `far_work` report spoken on his return; "rest at home" from the car no longer refused; `horn_hold` card hook back on the compact card. Card updated in the same change, `card_check.py` passes.
2. **s84** (in progress): address book generic capture via the vanilla map reveal hook, named places, "بيتنا". Rules in `PLAN_address_book.md` section 8.
3. **`compat_vp_harvest`** (in progress): guard the Viewpoint QOL harvest `getShovel` NPE without touching Workshop files.
4. **Door route `leg_stalled`** (in progress, `spatial_access`).
5. Commit + push each of them as it is staged; update DOCS after the batch; install only with the game closed.
6. Release refresh before the next launch (0.28.x): `secret_loadout` ON; `gps_static_roads` is runtime PASS and eligible for ON; add `stall_ladder` and `veh_shoot_seated` to the OFF list until proven.
7. Jamal's in-game test of the installed batch: speeds 20/40/65, held horn, a long drive to a house (`address_target`, `stall_ladder`), shooting from a car seat (`veh_shoot_seated`), `cars_near` while she is away, the street/city question, "طفي المتور".
8. Later: `far_car` re-test (4b8ad83), `item_sort` / `animal_care` / `farm_night` / `spatial_access` in play, s52 full card eval (not while he plays), backups to clear after passes.

## 1. Project layout

| Path | What |
|---|---|
| `01_WORK\Sol\42\...` | Working copy of the mod sources (Lua, scripts, `SolCombined.jar`). Not what the lab runs. |
| `05_TOOLS\sol_mind\` | **Sol Mind** (Python): chat routing, model card, word lists, goal engine. Runs live from here. |
| `05_TOOLS\sol_nav_java\localplayerbody\` | Java sources compiled into `SolCombined.jar` (SolNav, SolSteerAdapt, SolDebugGuard, SolLadderFast, SolBypass helpers, …). |
| `05_TOOLS\sol_kahlua\` | Gates and checkers: `linkcheck.py` (type-aware Java link check against the game jar), `patch_access_check.py` (ZB patch bodies call only public members), `lua_method_check.py`, `JarRetarget4222.java`. |
| `07_TEST\SOL_LAB\` | **The lab** that is actually played. |
| `07_TEST\SOL_LAB\profile\Zomboid\` | Game profile (`-Duser.home`). Mod: `mods\Sol_LAB\42\media\lua\client\*.lua`, jar `mods\Sol_LAB\42\media\java\SolCombined.jar`. Switches: `Lua\SolFixes_LAB.txt`. Logs: `console.txt`, `Logs\<date>_DebugLog.txt`. Saves: `Saves\Sandbox\…`. |
| `07_TEST\SOL_LAB\_pending_refuel\` | Staged changes: `apply_sNN.py` installers, new Lua files, `build_*.py` jar builders, offline tests `test_*.py`. |
| `07_TEST\SOL_LAB\_backup\<date>_before_<x>\` | Backups taken right before each install. Delete only after Jamal's in-game test passes, and to the Recycle Bin. |
| `07_TEST\SOL_LAB\MODS_LAB_MIN.txt` | The mod list the launcher expects (must equal `profile\Zomboid\mods\default.txt`). |
| `07_TEST\SOL_LAB\sol_lab.args` | JVM args for the lab (`-Xmx8192m`, `-Duser.home=…`). |
| `DOCS\` | `SOL_REVIEW_20261109.md` = council sections per change (Engineer / Devil's Advocate / Strategist), `SOL_CAPABILITIES.md` = proven-in-game list, `SOL_LEDGER.md` = every fix -> switch -> status -> commit, `SOL_MODEL_CARD.md` = the model's entry card, `PLAN_*.md` = plans, this file. |

Git: branch `claude/project-thread-riooui`, draft PR https://github.com/jamallionjan-dev/Sol/pull/4. Stage only the files you changed (the tree has other people's uncommitted work). Never merge.

## 2. Build, test, launch

**Launch only with `07_TEST\SOL_LAB\launch_lab.ps1`.** Never `SOL_LAB_LAUNCHER.bat`. The launcher starts the game first, then Sol Mind tied to the game PID (`sol_mind.py --lua-dir … --headless --game-pid N`). It refuses with these exit codes:
- exit 2: the game is already running.
- exit 3 (`REFUSED: Sol Mind PID … started before <file> changed`): a Mind older than its newest `.py` is running. Stop it, then launch again.
- No exit: `RELEASE REMINDER` when the lab mod is newer than the installed release.
- exit 4: the mod list differs from `MODS_LAB_MIN.txt`. If Jamal changed his mods on purpose, copy `profile\Zomboid\mods\default.txt` over `MODS_LAB_MIN.txt` after a backup.
- exit 5: `linkcheck.py` found a Java reference the game no longer has.
- exit 6: `patch_access_check.py` found a ZombieBuddy patch body calling a non-public member.
- exit 7: `tonumber_check.py` found a `tonumber(...)` that can receive two values (Kahlua crash; s75).
- exit 8: `card_check.py` found the model card out of step with the Mind (action without example, entry without handler, over budget, stale `SOL_MODEL_CARD.md`, or the s82 route replay fails).
- exit 5 (after start): Sol Mind did not stay up.

**Release / launch checklist** (every time, in this order, game closed):
1. Install staged fixes only with the game closed (backup first).
2. Mind changed? Update the card in the same change (`model_router.py` + `card_check.py <sol_mind> --write-doc`).
3. Commit + push every staged fix (`git push -u origin claude/project-thread-riooui`).
4. Release: bump the version, `build_release.py <version> install`, commit on `release/<version>`, push, draft PR. Never merge.
5. **Update DOCS:** `SOL_HANDOFF.md` (section 0), `SOL_LEDGER.md`, `SOL_CAPABILITIES.md`, the council section; commit + push.
6. `launch_lab.ps1` (all gates must pass), then watch the DebugLog and `sol_mind.log` during the test.

**Switches.** Every change is behind its own switch:
- `profile\Zomboid\Lua\SolFixes_LAB.txt` holds `name=on|off` lines.
- The switch must also be listed in `A.FIXES` in `SolAuthority.lua`.
- Lua reads it with `SolAuthority.on("name")`.
- Java switches are set from a tiny Lua file each tick, e.g. `solSteerAdaptSet(on)`.

**Jar rebuild** (pattern of `_pending_refuel\build_guard.py`, `build_steer.py`):
1. Compile with `javac -cp projectzomboid.jar;ZombieBuddy.jar;SolCombined.jar` into a scratch folder.
2. Copy `SolCombined.jar` and replace only the rebuilt classes.
3. Run `linkcheck.py <game jar> <new jar>`, then `patch_access_check.py <new jar>`.
4. Run any offline Java test.
5. Deploy only with the game closed (the build script's `deploy` argument checks `tasklist`).

Rules:
- ZombieBuddy inlines patch bodies into game classes, so every method a patch body calls must be `public` on a `public` class. `IllegalAccessError` happened once with `SolLadderFast.step`.
- `@Patch.OnEnter(skipOn = true)` means the original method is skipped when the enter method returns `true` (ByteBuddy `OnNonDefaultValue`).

**ZombieBuddy approval.** After any jar change, ZB asks at load. **Jamal approves it himself.** Never edit `profile\.zombie_buddy\mod_approvals.json`.

**Offline tests.** `lupa` (Lua 5.1) runs Sol's Lua on stub game objects, and the Mind's Python runs on copies of `05_TOOLS\sol_mind`. Every `apply_sNN.py` is first run on copies, by a dry run or the matching `test_*.py`. Run Python as plain `python` (not `-I`) when `lupa` is needed.

**Install / backup / rollback** (game closed, Mind stopped):
1. Copy every file you will change into `_backup\<date>_before_<x>\`.
2. Run the `apply_sNN.py` scripts in order. They are idempotent and refuse if their anchor text is not found exactly once.
3. Check that Lua compiles and the Mind imports.
4. Launch with `launch_lab.ps1` and read the first minute of the log.
5. Rollback: copy the backup files back and set the switch to `off`.

## 3. Sol Mind
- `05_TOOLS\sol_mind\`. Routing is model-first (`model_first=on`). The phone model `qwen3-4b` at `<phone address>` gets an entry card built from `model_router.py` `COMMANDS` (one action per behaviour, plus an example phrase). The model picks an action, the Mind swaps the text for the action's canonical phrase and runs it through the word lists:
  - `chat_service.py` `action_intents` table (regex → `(verb, option)`),
  - `farm_talk.py` `order()` (farm verbs `sol_farm <op>`).
- **No duplicate orders:** a new wording is a regex synonym of an existing action, never a new action.
- Do **not** run model evaluations on the phone while Jamal plays; tell him first.
- Per-world memory: `%LOCALAPPDATA%\SolMind\worlds\<mode>__<save>`.
- Game ↔ Mind files: `profile\Zomboid\Lua\SolAI_Inbox.txt`, `SolAI_Outbox.txt`, `SolActions_Snapshot.txt`, `SolWorld_Snapshot.txt`, `SolMind_Alive.txt`.

## 4. Logs
- `console.txt` is rewritten each launch and is **not followed live on this Windows box** (`tail -F` sees nothing). Read `profile\Zomboid\Logs\<date>_DebugLog.txt` directly, by grep or awk on time windows.
- Useful tags:
  - Driving and navigation: `[SolDrive] ladder …`, `[SolBypass] measured the car …`, `[SolGPS] preview … tiles short of the marker`, `[SolNav]`.
  - Vehicles: `[SolSteerAdapt] vehicle … turns the other way`, `[SolTracked] turning … through Trucksmith`.
  - Farm: `[SolFarmAct] <plow|sow|water|…> fallback=applied`, `[SolFarmWork]`.
  - New modules: `[SolAnimalCare] start|done|failed …`, `[SolSort] start|done …`.
  - Debug guard: `[ZB] Found patch class: localplayerbody.SolDebugGuard$Guard`.
- Third-party: `[TWZB]`/`[TW]` (EFZ Firearms), `[EFZPvadsBridge]`, `[Viewpoint]`, `[ProjectViewpoint] aim`, `Trucksmith: …`.

## 5. Switches (lab, 2026-11-10)

Status key: **PASS** = worked in Jamal's game, with date; **built** = offline tests pass, not proven in game; **on (older)** = from before this thread, status in `SOL_CAPABILITIES.md` / `SOL_REVIEW_20261109.md`.

| Switch / change | What it does | Status | Main files |
|---|---|---|---|
| Version gate 42.21+ (`SCGameVersion`) | Refuses to run Java parts on an older game build | PASS (game loads, 2026-11-09) | `SolCombined.jar` |
| PZArrayList retarget (`JarRetarget4222`) | 42.22 removed `zombie.util.list.PZArrayList`; jar calls retargeted to `java.util.List`/`ArrayList` | PASS (loads, no NoClassDefFound, 2026-11-09) | `SolCombined.jar` |
| `sol_ladders` | Sol uses the game's own ladders (`climb`/`climbDown`); rope calls removed | PASS 2026-11-09 | `SolLadders.lua` |
| `ladder_fast_slide` | Shift (run key) = fast slide down / faster climb, player and Sol | PASS 2026-11-09 | `SolLadderFast.java`, `SolLadders.lua` |
| `model_first` | Chat goes to the model first with the entry card | on; card in use; full card (s52) NOT installed (latency eval unfinished) | `chat_service.py`, `model_router.py` |
| `refuel_from_can` | Fill the car from a jerry can | on (older); not re-tested this thread | Lua refuel, Mind |
| `car_eligible_only` | Only cars she can really drive are offered | on (older); not re-tested | Lua |
| `follow_exits_car` | On "follow", she leaves the car | on (older) | Lua |
| `road_first` | Paved road preferred, dirt when the goal is on dirt, grass only to pass an obstacle or into a driveway; corridor + re-route | built; partially seen in play | `SolRoadFirst.lua`, `SCExpeditionRoute.lua`, `SolNav.java`, `SCDriving.lua` |
| s49 scanAhead fix (under `road_first`) | No false obstacles from side-offset scan; route points spaced (no "smallest_gap 0.04" refusals) | built (installed 2026-11-10) | `SolBypass.lua`, `SCDriving.lua`, `SolRoadFirst.lua` |
| `refuel_top_up` | Fills whenever the tank has real room (margin 0.01), real numbers spoken | built (installed 2026-11-10); Mind side live earlier | `SolFuel.lua`, Mind |
| `refuel_short_hop` | At the station: straight to the pump, no loop via the street | built | Mind, Lua |
| s53 GPS diag | Preview logs origin/end/gap; yellow line + "الطريق بيوقف قبل العلامة" when route ends >15 tiles short | built | `SolGPS.lua` |
| `drive_replace` | A new drive order replaces the running one | built | `SolGPS.lua`, `SCDriving.lua` |
| `home_parks` | "سوقي عالبيت" = nearest free parking zone of the home (≤60 tiles); none → stop on the road beside the house and say so | built | `SolWorldScan.lua`, `chat_service.py`, `SolGPS.lua` |
| `bleed_get_out` | Bleeding while seated and stopped, no zombie within 6 tiles → gets out, bandages, resumes the same trip (≤120 s) | built | `SolBleedStop.lua` |
| `debug_ctrl_a_guard` | Debug-mode Ctrl+A ("add animal" client command) crashes SP to menu; skipped when there is no server connection | built (patch class loads; not reproduced) | `SolDebugGuard.java`, `SolDebugGuard.lua` |
| `vehicle_steer_adapt` | For vehicles with no steered wheel, learns from real yaw vs applied steering and mirrors her steering if reversed (6 clear samples) | built (live since 2026-11-10 02:47; no turning vehicle yet to learn from) | `SolSteerAdapt.java`, `SolNav.java` hook |
| `tracked_mode` | Trucksmith turns tracked vehicles only for player drivers; runs Trucksmith's `TrackSteer.step` + `Stabilizer.step` for the vehicle Sol drives | built (installed 2026-11-10 05:1x) | `SolTracked.lua` |
| `animal_care` | "اهتمي بالدجاج" (keeper, every minute) / "اجمعي البيض" / "وقفي شغل الدجاج": water, feed, eggs (fertilized stay) to a powered kitchen fridge | built (21/21 offline) | `SolAnimalCare.lua`, `SolAuthority.lua` hold, Mind |
| `item_sort` | "رتّبي الأغراض": each thing to the nearest home container of its kind (fridge only if powered; favourites, keys, protected stay) | built (18/18 offline) | `SolSort.lua`, `SolAuthority.lua` hold, Mind |
| Farm phrase fixes (s62) | Synonyms only: "خلص وقفي زراعة" → farm stop; "دبريلي الارض بغيابي" → keeper | built (tested on copies) | `farm_talk.py` |
| `sol_farm` (older) | Her own farm runner; "اهتمي بالمزرعة" is the full cycle (harvest > water > cure > weed > sow > replant > till new land > fertilize > carry) | **PASS 2026-11-10**: till 31, plant 44, water 79, no errors | `SolFarmWork.lua`, `SolFarmAct.lua`, `SolFarmView.lua` |
| Other older switches | `retry_reset`, `driver_keeps_seat`, `car_flow`, `door_squares`, `order_menu`, `sol_home`, `rescue_gps`, `drive_passenger`, `home_errand`, `solo_drive`, `gps_trails`, `order_arbiter`, `drive_record`, `road_bypass`, `walk_search_fast`, `order_jog`, `walk_no_resend`, `order_breaks_rest`, `farm_keep_tools`, `drive_fast`, `order_engine_path` | on (older; see review/capabilities) | various |
| Off | `instinct_only=off`, `drive_bypass=off` | off | — |

## 6. Runtime results this thread
- **PASS:**
  - Ladders, plus Shift fast slide and climb (2026-11-09).
  - Street and city names (2026-11-09).
  - Fuelling once the tank was not "full".
  - Viewpoint black first-person screen and missing body parts, fixed by the EFZ-page setup (2026-11-10).
  - Scope zoom (2026-11-10).
  - Farm: till 31, plant 44, water 79, no errors (2026-11-10).
- **Vanilla:** shooting from a car works with the seat's window open.
- **Tonight (2026-11-10 night):** see section 0 and `SOL_CAPABILITIES.md`.
- **Open (older):**
  - s52 full model card: latency/accuracy eval on the phone not finished. The current card stays.
  - GPS short-route cause: needs the s53 log numbers.
  - A "park nearby" order ("صفي السيارة") that picks a free spot near any place: designed, not built.
  - Untested in game: drive home to garage, `drive_replace`, `bleed_get_out`, station top-up and short hop, GPS warning, Ctrl+A guard, Bradley with `tracked_mode` + `vehicle_steer_adapt`, `animal_care`, `item_sort`.
  - Backups to clear after the tests pass: `_backup\20261109_*`, `20261110_*`.

## 7. Third-party setup (lab)
- Load order (game list): `ZombieBuddy` … `SWMG`, `Viewpoint`, `ProjectViewpointADS`, `EscapeFromZomboidFirearms`, `EFZPvadsBridge` … `EscapeFromZomboidFirearmsServer`. This follows the EFZ Workshop page (ZombieBuddy → SWMG → Viewpoint → EFZ), with the bridge loaded after ADS and EFZ (its `loadModAfter`).
- `sol_lab.args`: `-Xmx8192m` (EFZ page: at least 8192 MB; the PC has 32 GB).
- `profile\Zomboid\viewpoint-live.properties`:
  - `game.releaseIsoChunkTextures=false`, so the top-down images are kept across view switches.
  - `chunks.buildBudgetMs=6.0` and `chunks.buildMaxMs=16.0` (were 3 and 9).
  - Backup: `_backup\20261110_before_s58`.
- Disabled:
  - `DGVViewpointEyes` (Workshop 3825098116): its `DGVEReach` class still uses the removed `PZArrayList`.
  - Earlier Viewpoint-family mods broken on 42.22: see `MODS_LAB_MIN.removed_42_22_note.txt`.
  - Never edit Workshop files; disable from lists only.
- Trucksmith (Workshop 3812497744) turns tracked vehicles (e.g. RKC Bradley, all wheels `front = false`) from `getCurrentSteering()`, but only in its player-driver loop (`Trucksmith_Stabilizer.lua` `S.onTick`). That is why `tracked_mode` exists.
- EFZ keys:
  - `9` opens the sights menu.
  - "Sights: switch active sight" has no default key; bind it under Options → Mods → "EFZ: Controls".
  - Zoom: Left Alt + mouse wheel while aiming.
  - Zero distance: PgUp / PgDn.
- Vanilla quirks:
  - Debug Ctrl+A in single player → NPE in `GameClient.sendClientCommand` → back to the main menu. `debug_ctrl_a_guard` covers it.
  - The debug Items List search with `(`, `%` or `[` throws "unfinished capture". Search plain words.

## 8. Jamal's standing rules
- **Language and reporting:**
  - Talk to him in short, polite Levantine Arabic ("لو سمحت"), first person.
  - Send only finished results or steps only he can do.
  - Report through the project channel tool only.
- **Honesty:**
  - Label everything **confirmed / inference / needs in-game test**.
  - No partial hypotheses presented as answers.
  - Never claim done before it is verified.
- **Autonomy:**
  - Decide, implement and test yourself.
  - Ask only for irreversible steps or his-only steps (closing the game, ZB approval).
- **Research first:**
  - Community mods, docs, Workshop pages, game code. Ideas only, never copied code.
  - Downloads only into `05_TOOLS`.
  - Cite sources in the council section.
- **Council per change:** Engineer → Devil's Advocate → Strategist → implement → test, written in `SOL_REVIEW_20261109.md`.
- **Switches and tests:** one change per switch in `SolFixes_LAB.txt`, tested offline and then in game.
- **Behaviour:**
  - General behaviour only; never special-case his example (no vehicle or place names in code).
  - KI5 vehicles must work.
  - Single companion.
  - Performance first; Java where it is faster.
  - Exact in-game item names in speech.
  - Sol speaks in character, in Levantine Arabic, never meta (it is a live stream).
  - Sol obeys the Mind only.
- **No duplicate orders:** new wordings are synonyms of existing actions.
- **Game safety:**
  - Never install files while the game runs. A Python-only Mind restart is accepted.
  - Launch only with `launch_lab.ps1`.
  - Never touch Steam or Workshop copies or `projectzomboid.jar`.
  - Never edit `mod_approvals.json`.
- **Git:**
  - Never merge.
  - No model identifiers in commits or PRs.
  - Stage only your own files.
- **Release before every launch (Jamal 2026-11-10 20:21):** "قبل ماتشغل العبة حدث نسخة الاطلاق دايما". After every update and before launching the game:
  1. Bump the version and run `07_TEST\SOL_LAB\_pending_refuel\build_release.py <version> install`. Its ON list holds only runtime-PASS switches; everything untested ships OFF.
  2. Commit `01_WORK\Sol` and `01_WORK\RELEASE_<version>_CHANGELOG.md` on `release/<version>`, push it, and open a draft PR. Never merge.
  3. `launch_lab.ps1` prints a warning when the lab mod is newer than the installed release.
  - 0.28.0: PR https://github.com/jamallionjan-dev/Sol/pull/6.
- **Model card with every Mind change (Jamal):** "لاتنسة تحدث بطاقة العقل دايما مع العقل بطاقة العقل الورقة الي بيستلمها اي نموذج ورقة التعريف". Every Mind change updates, in the same change, the runtime card (`model_router.py`: `sheet()`, `COMMANDS`, `CARD_ACTIONS`, `EXAMPLES`, rules) and `DOCS\SOL_MODEL_CARD.md` (`card_check.py <sol_mind> --write-doc`). The gate `05_TOOLS\sol_kahlua\card_check.py` refuses in `launch_lab.ps1` (exit 8) and in `build_release.py`.
- **Tonight's rules (Jamal 2026-11-10 night):**
  - **Commit + push after every staged fix** (branch `claude/project-thread-riooui`; retry the push on network errors).
  - **Update DOCS after every batch:** `SOL_HANDOFF.md` section 0, `SOL_LEDGER.md`, `SOL_CAPABILITIES.md` (runtime PASS only in the PASS table), the council section.
  - **Address book:** capture only at the moment he opens the paper while Sol is within 12 tiles (same floor, alive, awake) or in the same car; no backfill of papers opened before; wiped on her real death.
  - **GPS speeds:** 20 / 40 / 65 km/h (`speed_levels`; jar cruise ceiling 70).
  - **Horn hold:** she holds the horn until the GPS drive ends or 5 real minutes, or until told to stop (`horn_hold`).
  - **Model first:** the model routes; new wordings and synonyms go on the card as examples only, never as keyword overrides or new actions.
  - **No install while the game runs** (repeat of the game-safety rule; a Python-only Mind restart is accepted).
  - **Never merge** (the release PRs stay drafts).
- **Backups:** no leftover backups; delete (to the Recycle Bin) only after his tests pass.
- **Logs and the phone model:**
  - Watch the logs during every test.
  - Don't load his phone model with evaluations while he plays.

## Note 2026-11-10 16:45: mod order keeps reverting
When Jamal turns mods on or off in the game's Mods menu, the game rewrites `profile\Zomboid\mods\default.txt` and SWMG can land after Viewpoint again. Neither mod's `mod.info` has a rule that does this (SWMG: `loadModAfter=HBVCEFb42`; Viewpoint: `require=\ZombieBuddy` only). So the menu's own rewrite is the likely cause (inference). The EFZ author's order is ZombieBuddy, SWMG, Viewpoint, ProjectViewpointADS, EscapeFromZomboidFirearms, EFZPvadsBridge. After any menu edit, check that order in `default.txt`, the world's `mods.txt` and `MODS_LAB_MIN.txt` before launching.
ShelfContents3D (Workshop 3828905319) still uses `zombie.util.list.PZArrayList` and is off in the lab lists for 42.22.

## Runtime results 2026-11-10 afternoon (Jamal, lab)
PASS in play: `home_parks` ("سوقي عالبيت" parks in the home garage), `drive_replace` (a new drive order replaces the old one), s53 GPS warning (route ends short of the marker), `road_first` with the s49 scan fix and route spacing on a long paved drive, `refuel_top_up` + `refuel_short_hop` at the station. These are eligible to turn ON in MAIN at the next release (the installed 0.27.0 is unchanged).
Staged, not installed (game running, Jamal live): `apply_s63_mind.py` (far-Sol car orders: never refuse; by car when far_car works, else on foot with a natural line; Mind only), `apply_s64.py` (`far_wait_speed`: far waits follow game speed 1x/5x/20x/40x, paused stops; 10/10 offline). `far_car` (nearest usable car within 25 tiles, SolCarMove in the jar) is being built and tested on a copy of the save.
Far walk-in seen at 17:40 game time did not finish while the game was paused: the wait counts only unpaused time.
- 2026-11-10 17:06 PASS (Jamal): Bradley on the paved road to a marker past the stop-sign corner, turning with the road and around the sign: `tracked_mode` (log: "[SolTracked] turning Base.RKCBradleyM3 for Sol through Trucksmith"). `vehicle_steer_adapt` logged no mirroring in that run, so the Bradley's steering direction matched her steering without it (it stays on as a guard). Eligible for MAIN at the next release.
- Closed: Bradley second drive 2026-11-10 18:00 (marker 7316,8178, route 39 tiles short). The log shows SolNav planned the last stretch (492 poses, 1.5 s) and finished it ("[SolNav] done" at f:170044); Jamal then had her get out at 7307,8179, about 9 tiles from the marker. So it reached the end of its plan; it took 3.5 min because the off-road stretch was long. No fix needed.
- Planned (not built): Sol's address book, see `DOCS\PLAN_address_book.md` (per-life knowledge, wiped on real death, learned only when she sees the paper, tap-to-drive). UI: a button "دفتر العناوين" (EN "Address Book") inside the main panel section "المزيد" (More): a tab in the right-hand tab column directly under "العائلة" (after الحالة, المهارات, الأوامر, العتاد, العائلة), same style; not a new top-level button.

## Batch installed 2026-11-10 ~19:00 (lab, game closed, backups in 07_TEST\SOL_LAB\_backup\20261110_before_s63_66)
All built-not-proven until Jamal tests them in game:
- `far_car` (jar: SolCarsNear/SolCarsNearCore/SolCarBlob/SolCarMove; Lua: apply_s65): far Sol picks the nearest usable car within 25 tiles (unlocked AND key in ignition / key with her / key in car / hotwired), moves it to the edge of his area, deducts fuel, waits (car 180 s, tracked 210 s, heli 60 s), then drives to him. Offline: Java 58/58 + 16/16, Lua/Mind 108/108. ZombieBuddy may ask to approve the changed jar.
- `far_wait_speed` (apply_s64): far waits follow game speed 1x/5x/20x/40x, paused stops. 10/10.
- Far car phrases never refuse (apply_s63_mind, Mind only). 4/4.
- Sort phrase is the sort order, not the old errand (apply_s66_mind). 9/9.
- `dot_paused_fix` (apply_s68_dot): the avatar dot read the Mind heartbeat only on OnTick, so it went grey after 20 s of pause; the panel now reads it. 7/7.
- `item_sort` v0.2 (apply_s67): scan once, plan first, one visit per container per round, batched verified transfers, Arabic progress + summary. 58/58. Readable source in _pending_refuel\src.
- `address_book` (apply_s69): listings, stash maps, area maps captured on read when Sol sees it (12 tiles / same car), per life, wiped on respawn, tab under العائلة in المزيد, click in car = marker + drive. 67/67. Left out: player-named map marks (no game event), auto-looted detection.
- 2026-11-10 19:59 PASS (Jamal): Ctrl+A in Sol's chat in debug mode, no crash (`debug_ctrl_a_guard`). Also PASS today: `dot_paused_fix` (dot green while paused, screenshot 19:48), far walk-in with `far_wait_speed` (arrived in under a minute at speed-up, 19:51-19:52), sort phrase routing (s66).
- Eligible to turn ON in MAIN at the next release (proven in play 2026-11-10): `debug_ctrl_a_guard`, `far_wait_speed`, `dot_paused_fix`, `tracked_mode` (+ `vehicle_steer_adapt` as a guard), `home_parks`, `drive_replace`, `road_first` (+ s49), `refuel_top_up`, `refuel_short_hop`, s53 GPS warning, s66 sort phrase. Not eligible yet: `far_car` (car moved alone, Sol not with it), `item_sort` (walls/doors, waiting for spatial_access), `address_book` / `animal_care` (crash fixed, not re-tested), `spatial_access` (not installed).
- 2026-11-10 20:17: the debug main menu's "Scenarios" list ("Basic Debug Scenario") starts a NEW game with its own character and repoints Continue/latestSave to it (new save 4445572914162594730). His world 2026-11-10_02-39-13 was untouched (player alive); backup copy in 03_BACKUPS\world_2026-11-10_02-39-13_copy_2021. Load his world from Load, never from Scenarios.

## Open at pause (2026-11-11 00:30). Resume in this order
1. **s93 `restore_hands`:**
   - What happened: at load, Sol's record was quarantined ("primary hand item could not be equipped").
   - The fix: the item goes to her bag, the restore continues, and the item is put back in her hand once she stands (two-hand aware).
   - Status: ON in MAIN and installed in the main mod. In the lab it is NOT installed yet, because the game was running. On "اي سكّر": run `apply_s93_restore_hands.py <lab client>`, then relaunch.
   - Confirm in game: Sol is back with her weapon in hand and no gear lost. Watch `[SolRestoreHands] back in her ... hand`.
2. **far_car "تعالي لعندي بالسيارة" (s92), top priority:**
   - The WIP is not installed: `_pending_refuel/apply_s92_*`, `SolFarComeCar.lua`, `test_s92_come_car.py`, `SolVehicleLoadProbe.java`.
   - far_car stays OFF.
   - Next: review states (1)–(6), then pass 5/5 automated runs on a COPIED save via `launch_lab.ps1 -TestWorld`.
3. **Two-tier card (s90):**
   - Installed, but `CARD_TIERS = False`, because the live phone eval regressed (94/113).
   - Fix the option format and confusable names, re-enable, and require ≥ the old 75 live.
4. **Not yet played:** everything installed 2026-11-10 night. See SOL_LEDGER "Open items".

## Active task — s122 (2026-11-12)

- Bradley findings: `SolTracked.lua` invokes Trucksmith steering/stabilizer only for Sol-driven tracked vehicles. Reuse the narrow native-input integration principle, not its road or track controller for helicopters.
- LAB now contains the helicopter GPS/altitude candidate and `sol_let_player_drive` seat-handoff command. Say **سول عطيني الدركسيون** (also **خلييني أنا سوق**): in a stopped vehicle where Sol drives, she moves directly into an empty reachable passenger seat and stays inside. The game action verifies occupancy; no exit behavior. Mind cancels a competing movement order.
- Updated `DOCS/SOL_MODEL_CARD.md` and model routing/card rules with the new command. Offline checks: heli harness 32/32, handoff harness 14 checks, route replay ALL PASS, Python compile pass, card 4549/4600 (one existing catalog warning).
- Installed after backup: `07_TEST/SOL_LAB/_backup/20261112_222157_802866_before_s121_heli_gps`. Preflight passed (linkcheck 12058/0, patch access 93/0, tonumber OK, jarcall 0 fail/20 warnings). No MAIN/Steam/release/user-save changes.
- LAB launch failed before Sol initialization: ZombieBuddy Java startup threw `java.net.SocketException: Permission denied: connect` while opening its loopback selector. Same result in normal and elevated launches; no game process remains. Do not claim gameplay validation or repeat launches until resolving this loopback boundary.
- Still pending in-game: stationary car with player outside, then passenger; same checks in Bradley and helicopter separately; verify Sol stays inside, player is not displaced, driver seat frees, unsafe/moving/no-seat cases refuse. Separately test heli GPS route, each altitude, manual override, stop/context loss, and unchanged car routing.

## Latest handoff — s144 / 0.28.5 helicopter candidate (2026-11-13)
- New full bundle: `01_WORK\RELEASE\SOL_2026-11-13_0.28.5_HELICOPTER_RC`. Built as a copy of stable 0.28.3, overlaid with complete 0.28.4 accumulated state, then s144 files. Existing 0.28.3 and 0.28.4 directories were not edited.
- s144 adds a separate `heli_voice_fly` switch and Mind action “سول طيري على العلامة”. It requires `heli_gps`, Sol and player in the same helicopter, and an already selected GPS destination, then calls the existing direct-air GPS start. Seat transfer remains a distinct action; speed/altitude controls remain the GPS UI's job.
- Updated release Mind and model card, enabled `heli_voice_fly` in this candidate's MAIN switch file, and added s144 council/plan/next-step docs. Jamal's flight procedure (read manual, climb to chosen altitude, direct-air GPS, land, verify touchdown, engine off and exit) is recorded as the intended procedure, not claimed as automatic behavior already proven.
- Static/simulated checks: s144 Lua 5.1 action harness 15/15; s135 existing flight-controller route simulation PASS (two destinations, landing, engine-off and exit); card gate PASS with 0 failures/1 existing warning and 4,600/4,600 chars; route replay ALL PASS; `tonumber_check` OK; Kahlua scan 288/0; linkcheck 11,963/0; patch access 88/0; Mind/helper Python compile pass.
- Runtime is not tested on 0.28.5. Jamal previously reported takeoff/route once on an earlier build, but persistent travel, speeds, altitudes, landing and stop/exit on this candidate remain pending. Do not promote as stable or install to Steam based on static checks alone.

## Latest handoff — s145 / 0.28.5 speed review (2026-11-13)
- Offline test on the actual 0.28.5 candidate passed all three speed tiers (20/40/65 km/h), changing tiers during an active route, independent altitude selection, speed restoration on stop, and full route/landing simulation.
- Candidate is staged in `SOL_LAB` only. Backup: `07_TEST/SOL_LAB/_backup/20261113_222644_before_0.28.5_speed_test`.
- `launch_lab.ps1` started isolated save `2026-11-12_18-08-44` (game PID 19508; paired Mind PID 15168). In-game speed readout and real flight remain to be checked by Jamal. The Mind startup line says `provider=none`; use the GPS speed buttons for this test, which do not require a chat request. Keep the launcher session open until the game closes. No MAIN/Steam/release promotion.
- No game launch, user save change, main Steam profile change, or GitHub update was performed in s144.

## Previous handoff — s143 / 0.28.4 private candidate (2026-11-13)
- Candidate: `01_WORK\RELEASE\SOL_2026-11-13_0.28.4_FULL` (complete bundle, not just a raw mod). Prior 0.28.3 full package retained unchanged.
- Candidate includes current Sol Lua, Mind runtime, updated MAIN switch defaults, existing bundle assets/launchers, and six new functional Lua modules. Launcher preserves the previous mod copy and merges only missing switch keys while keeping existing user settings.
- Static gates: 302 Lua files compile; linkcheck 11,963/0; patch access 88/0; Python compile 5/5; card 0 failures/1 warning; launcher parse pass. TONUMBER checker still flags three conservative legacy sites byte-identical to 0.28.3.
- Runtime status is pending. Do not describe the candidate as gameplay-proven or stable until isolated LAB tests cover helicopter pilot handoff, takeoff/route/speeds/altitudes/landing, summon and fuel/key, combat fire behavior, and normal follow/work. No Steam copy, original save, or GitHub was touched in s143.
- Candidate notes: `01_WORK\RELEASE\SOL_2026-11-13_0.28.4_FULL\RELEASE_NOTES_AR.md`.

## s146 handoff — detailed gear page restored (2026-11-13)
- Candidate remains `01_WORK/RELEASE/SOL_2026-11-13_0.28.5_HELICOPTER_RC`; s146 integrated the requested wide interactive gear page and its s98/s99/s100/s105 dependencies. Earlier release directories were not changed.
- Offline page check on a candidate-derived staging copy: **106/106 PASS**. Mind card check: **PASS**, 0 failures, 1 existing warning, 4,581/4,600 chars; route replay ALL PASS. Candidate card and `DOCS/SOL_MODEL_CARD.md` are synchronized.
- The candidate page includes hands/ammunition/state, weapon preferences, clothing take-off/swap, Sol's bag, player bag on click, giving items, last car/home scan, comparison with player gear, and combat plan selection. `gear_page=on`; disabling it restores LF's prior gear UI.
- No game was launched in this step. Next LAB session must verify the restored view visually, swap one clothing item and one weapon, transfer an item each direction, inspect 500+ inventory rows/scrolling, then separately continue the pending helicopter flight test. Do not promote to MAIN until runtime evidence exists.

**Current handoff — s149, 2026-11-14:** The consolidated runtime error fixes are now synchronized into the isolated LAB from the 0.28.6 integration copy (11 client Lua files; all SHA-256 hashes match). Pre-existing LAB files are backed up at `07_TEST\SOL_LAB\_backup\20261114_before_runtime_errorfix`. Focused offline tests pass: 29/29, 27/27, 19/19, 10/10, and 8/8 across the compatibility, overload, edge API, NPC reload, and null-sprite checks. This is not gameplay proof. Launch through `07_TEST\SOL_LAB\launch_lab.ps1` after its preflight. Test Viewpoint on the reported object/door, Sol reload with top-level and nested magazines, and inspect `[SolKahluaGuard]` plus Kahlua exceptions. Do not promote to the release candidate or installed MAIN/local mod until these in-world checks pass.

**Live session update — s149, 2026-11-14 02:33:** Preflight passed and `launch_lab.ps1` started game PID 17816 with paired Mind PID 13624. Latest log evidence still showed `MainScreenState`, so no gameplay interaction has yet been proven. Three `AngelCodeFont` texture-load errors occurred at startup; no targeted Sol/Kahlua error has appeared in the monitored log so far. Continue with Viewpoint interaction, top-level/nested Sol reload, then recheck the log. Keep release/MAIN unchanged until runtime acceptance.
