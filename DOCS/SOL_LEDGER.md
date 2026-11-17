# Sol ledger: every fix from s63 onward and the release

سجل كل تعديل: المفتاح، الحالة، والـ commit. أي تعديل جديد بينضاف هون بنفس الدفعة.

Last update: 2026-11-14 (s147 integrated offline-verified work into private 0.28.5 candidate; gameplay proof pending). Linked from `SOL_HANDOFF.md`.

**Status key**
- **staged**: built and tested offline in `07_TEST\SOL_LAB\_pending_refuel`, not installed.
- **in lab**: installed in the lab (`SolFixes_LAB.txt` on, or Mind files live), not yet proven in play.
- **runtime PASS**: worked in Jamal's game; date and log line in `SOL_CAPABILITIES.md`.
- **half**: part of it worked in play, part did not (see the note).
- **in release**: on in `SolFixes_MAIN.txt` of the installed release (0.28.0) or on the ON list of `build_release.py` for the next refresh.
- **OFF**: in the code, switched off (lab and/or release).
- **in progress**: being built now, no commit yet.

Switch "(Mind)" = Sol Mind change in `05_TOOLS\sol_mind`, no game switch. "(no switch)" = always-on code change.

| Fix | Switch | Lab status | Release status | Commit(s) |
|---|---|---|---|---|
| s63 far car phrases never refuse | (Mind) | in lab | Mind (shared) | 6b15976, ba3ec0e, 29363d7 |
| s64 far waits follow game speed | `far_wait_speed` | runtime PASS 2026-11-10 19:51 | in release 0.28.0 (ON) | 6b15976, 07bac33, ba3ec0e |
| s65 far car (nearest usable car within 25 tiles) | `far_car` | OFF (car moved alone; live load 2-byte header bug, fixed in 4b8ad83, not re-tested) | OFF | d87a41b, 0a38c6c, ba3ec0e |
| s66 sort phrase reaches the sort | (Mind) | runtime PASS 2026-11-10 | Mind (shared) | 3066c00, ba3ec0e |
| s67 item_sort 0.2 / 0.2.1 / 0.2.2 | `item_sort` | in lab | OFF | 114d56f, 6bbcd84, 507c1b3, 0af6e16 |
| s68 status dot while paused | `dot_paused_fix` | runtime PASS 2026-11-10 19:48 | in release 0.28.0 (ON) | ba3ec0e |
| s69 address book (listings, stash maps, area maps) | `address_book` | runtime PASS 2026-11-10 20:36 / 23:06 / 23:08 (auto-capture); brochures and other fliers not captured -> s84 | in release 0.28.0 (ON) | 12e7692, a3f89fd, 53a665a |
| s70 door-first routes, access squares | `spatial_access` | in lab; door-route `leg_stalled` 23:05:51 (fix in progress) | OFF | 766a805, 0af6e16 |
| s70b forget_all on the card, no keyword override | (Mind) | in lab | Mind (shared) | 72cfd94, 1f8763d |
| s71 far-away car question answered from her surroundings | (Mind) | in lab | Mind (shared) | f467d08 |
| s72 far arrival: car and Sol arrive together at the wheel | `far_car` | OFF | OFF | 074da4b, c965bd8, 4b8ad83 |
| s73 farm at night with a light | `farm_night` | in lab | OFF | 47c2010, 0af6e16 |
| s74 far work (farm kept while Jamal is far) | `far_work` | half: shift ran and ended right (log hours 92-96, 43 jobs), return report not spoken -> s85 | OFF | f091251 |
| s74 secret weapon (`عطيني سلاحي السري`) | `secret_loadout` | runtime PASS 2026-11-10 21:29 | OFF in 0.28.0; ON list for the next refresh | 6e2bc39, 9d92b59 |
| s75 one value into Kahlua's tonumber + tokenizer gate (launch exit 7) | (no switch) | in lab (gate passes) | in release 0.28.0 | fa87525 |
| s76 far_meta (vehicles the game keeps "in meta") | `far_car` | OFF | OFF | 6cb8a1c |
| s76 GPS over the whole map's roads | `gps_static_roads` | runtime PASS 2026-11-10 21:43:59 | OFF (eligible for ON at the next refresh) | 528548e |
| s76 plain words on the GPS panel | `gps_plain_words` | in lab | OFF | 528548e |
| s77 cars_near action; no coordinates in chat | (Mind) + Lua snapshot | survey without coordinates runtime PASS 21:35:28; cars_near half (no answer while she is away at home) -> s78 | Mind (shared); Lua part in 0.28.0 | 33138b4 |
| s78 cars_near from around HER; come_car phrases; meta-word reply gate | (Mind) + Lua | in lab | not yet | 6fccd7f, 29363d7 |
| s79 horn hold until the drive ends or 5 real minutes | `horn_hold` | in lab; card hook broken by s82 card compaction -> s85 | OFF | a0f31f7, 9d92b59 |
| s80 GPS speeds 20/40/65, jar cruise ceiling 70, bend governor | `speed_levels` | in lab | OFF | 5d708a2 |
| s81 stall ladder (every failed way round feeds the next rung) | `stall_ladder` | in lab | not on the lists yet | adad1d2 |
| s82 GPS to the road in front of the house, honest road_end | `address_target` | in lab | OFF | a2b98c1 |
| s82 calm preview | `preview_calm` | in lab | OFF | a2b98c1 |
| s82 Mind: engine words, place questions, unknown -> map answer, compact card, route regression eval | (Mind) | in lab (Mind live) | Mind (shared); eval is a release gate | a2b98c1, 29363d7 |
| s83 aiming from a vanilla car seat keeps the seated body | `veh_shoot_seated` | in lab | not on the lists yet | 7221a18 |
| s84 address book generic capture (vanilla map reveal hook, places, "بيتنا") | `address_book` (planned) | in progress | - | - |
| s85 far_work report spoken; rest-from-car refusal; horn card hook | `far_work` / (Mind) / `horn_hold` | in progress | - | - |
| s95 station refuel: station survey (Jamal's rule first: a free square always kept between the fuel cap and the pump; station read once per life, drive, check from the real stop, re-park at most 2, walk to the cap not cut by move_check, plain failure lines); evidence: 21 errands, 2 confirmed fills (9.5%), causes in `PLAN_station_survey.md` | `station_survey` (+ Mind lines, no card change) | staged (`apply_s95_station_refuel.py`, `apply_s95_station_refuel_mind.py`, `test_s95_station_refuel.py` 136 PASS offline); not installed; OFF in lab and MAIN | OFF | (this commit) |
| compat_vp_harvest (Viewpoint QOL harvest `getShovel` NPE, third party) | `compat_vp_harvest` (planned) | in progress | - | - |
| door-route `leg_stalled` (23:05:51) | `spatial_access` | in progress | - | - |
| Model card gate `card_check.py` (launch exit 8, release gate) | (no switch) | in lab (gate in `launch_lab.ps1`) | release gate in `build_release.py` | 04864fb |
| Release 0.28.0 + "release before every launch" step | - | installed to main (`C:\Users\JAMAL\Zomboid\mods\Sol`, `SolFixes_MAIN.txt`) | draft PR https://github.com/jamallionjan-dev/Sol/pull/6 (never merge) | 9e29153, 4796dab (`release/0.28.0`) |
| Live Sol Mind snapshot as installed | (Mind) | in lab | - | 29363d7 |

Notes
- Installed after the 21:26-23:08 session (switch file written 23:12): `horn_hold`, `speed_levels`, `stall_ladder`, `address_target`, `preview_calm`, `veh_shoot_seated`, the s78 Lua part. None of them has been played yet.
- `stall_ladder` and `veh_shoot_seated` are on neither list of `build_release.py`; a switch missing from `SolFixes_MAIN.txt` is off, so they ship OFF until added.
- `far_car` is the only new switch that is OFF in the lab too.

## Open items (complete list, 2026-11-10 late)

Jamal: "شتغل على كل الاصلاحات المقرر لاتترك ولا وحدة". Every decided fix or feature that is not done, or done but not runtime-proven. Built from this ledger, `SOL_HANDOFF.md`, `SOL_TODO_20261109.md`, `SOL_MASTER_PLAN.md`, `PLAN_address_book.md`, `PLAN_far_work.md`, `PLAN_spatial_awareness.md`, the council sections of `SOL_REVIEW_20261109.md`, `SOL_CAPABILITIES.md` ("not yet proven"), the lab switches (`SolFixes_LAB.txt`, written 23:36), the release lists (`build_release.py`, 0.28.1) and the git log of 2026-11-08..10. A read-only `card_check.py 05_TOOLS\sol_mind --no-eval` run (PASS, 2 warnings, card 4540/4600) is the source for the card items.

**Rows above that this list supersedes:** s84 (address book generic capture) is now `address_places` (468e523, in lab); s85 is staged and in lab (f5c5661: card within budget, several actions in one reply, `exit_first`, far report in the chat, GPS ready line); `compat_vp_harvest` and the door-route `leg_stalled` fix (`place_leg_arrive`) are staged and in lab (047f6f6). All were installed with the game closed (lab files 23:27-23:36, backup `_backup\20261110_before_s76_85`). Release 0.28.1 is installed to main (69822cd lists; `SolFixes_MAIN.txt` 61 lines). Nothing below has been played since.

State key: **not started** / **staged** (built + offline tests, not installed) / **in lab untested** (installed, switch on in the lab, never played) / **runtime half** / **runtime FAIL** / **blocked**.

### A. Needs code

| ID | Item | Source | Switch | State | To finish | Depends on |
|---|---|---|---|---|---|---|
| A1 | Smart nearby parking: "صفي السيارة" anywhere = list free spots near her, take the nearest that fits the car and blocks no road or door, then check the whole car is inside the spot. Separate from the home garage (`home_parks`). | `SOL_REVIEW` s27 ("المخطط" paragraph, line 568); `SOL_HANDOFF` s6 "Open (older)": "designed, not built"; `SOL_TODO_20261109` #13 | `smart_park` (s87) | staged 2026-11-11: `SolSmartPark.lua` + `apply_s87_lua.py`, `apply_s87_mind.py`; `test_s87.py` ALL PASS offline, card 4558/4600; council s46. Not installed | install (game closed) + in-game test | `road_first`, `home_parks` pattern; card budget (60 chars left) |
| A2 | Address-book places in her Mind memory: the memory section lists `mem.data['places']` only, so a question about a book place gets "none" | `card_check.py` WARN "feature address-book places in her memory" (run 2026-11-10 late) | `address_book` / `address_places` + (Mind) | not started | code: game side writes the book rows (name, kind, town; no coordinates) to the snapshot; Mind adds them to the memory part of the card; card + `SOL_MODEL_CARD.md` in the same change | B9 played; card budget (D3) |
| A3 | Address book: a stash marked "visited" by itself when she arrives and sees the box empty | `PLAN_address_book` s6 (decided), s7 "not done" | `book_visited` (s89) | staged (`SolAddressVisit.lua`: 10 tiles for 6 s = "انزار", once per row; the box itself is not read: no Lua API gives the spawned box) | install (`apply_s89_address_visit.py`), then in game: stand at a stash from the book | B9 |
| A4 | Address book: "شو هالورقة؟ فرجيني ياها" when he opened a paper while she was far | `PLAN_address_book` s2/s6 (marked optional), s7 "not done" | `book_hint` (s89) | staged (papers with a place read while she was far/upstairs/asleep: she asks once when beside him, 5 min gap, 30 min memory) | install, then in game: read a brochure 40 tiles from her, walk to her | B9 |
| A5 | Address book: an area map drives to the nearest entrance of the area on the road (today: the centre, the GPS snaps to the nearest road) | `PLAN_address_book` s6, s7 "not done" | `address_target` (s89 code) | staged (s82 sent an area through its house footprint: a whole-map building scan and an arbitrary end; now the paved road crossing the area's edge nearest him, inside: the road nearest the centre) | install, then in game: tap "Louisville Central" in the car | B4, B9 |
| A6 | Exact failure reason in the log and in "ليش" (door, path, time) instead of one shared line | `SOL_TODO_20261109` #6, #17 | (Mind) / various | partly (`why` action on the card; not checked against a real failure) | code review of the remaining shared lines + test | - |
| A7 | `bridge_failure` cause in the log, then its fix | `SOL_TODO_20261109` #12 | - | not started (`SCDriving.lua` 229/518/638 still emit the bare reason) | code (log the follow reason) + test | - |
| A8 | Log line: her key numbers vs the car's key id | `SOL_TODO_20261109` #29 | - | not started (not found in `SolGPS.lua`) | code | - |
| A9 | Translate "Base duty" and "Move to" in the panel | `SOL_TODO_20261109` #28 | - | not started (`SCBaseWork.lua`, `SCUI.lua` still English) | code | - |
| A10 | "Did not move" check every ~600 ms then a new path; run when far, walk when near, stop at 1.5 tiles | `SOL_TODO_20261109` community table ("لسا، بعد التجربة") | `move_check` (s87) | staged 2026-11-11: `SolMoveCheck.lua` + `apply_s87_lua.py`; `test_s87.py` ALL PASS offline; council s46. Not installed | install (game closed) + in-game test (B26 movement tests cover it) | B26 |
| A11 | Full memory back after a disconnect | `SOL_TODO_20261109` #16 | (Mind) | not verified since 2026-11-09 | check, then code if missing | - |
| A12 | `veh_shoot_seated` step 2: a shot node with the leg mask, only if the body rises with each shot | `SOL_REVIEW` s42 strategist 4 | `veh_shoot_seated` | conditional | code only if B6 shows the rise | B6 |
| A13 | Docs/process: (a) `SOL_CAPABILITIES.md` has no evidence line for `gps_plain_words`, yet 0.28.1 ships it ON ("Confirmed by Jamal" in the changelog only); (b) the 0.28.1 release commit 3bfa9eb sits on `release/0.28.0` (PR #6), not on `release/0.28.1` as the checklist says; (c) the rows s84/s85/door-route above still say "in progress" (this section supersedes them) | `SOL_HANDOFF` s8 release rule; `RELEASE_0.28.1_CHANGELOG.md` | - | open | docs edit (time + log line for `gps_plain_words`); decide whether a `release/0.28.1` branch is needed | C2 |
| A14 | Engine off whenever she gets out of a car she drives (every path: exit_car order, `exit_first`, `follow_exits_car`, refuel from a can, LF native exit / "player left the car" policy / far regroup, bleed stop, park/stall ends), unless his order says to leave it running ("سول نزلي من السيارة وخلي المحرك شغال", "خلي الموتور شغال" -> `exit_car` option `keep_engine`, model-first, one card example, no keyword). He drives: his engine is never touched. Held horn let go on her exit. Headlights unchanged (vanilla `shutOff` never touches them) | Jamal 2026-11-10 (s91) | `exit_engine_off` | staged (`SolExitEngine.lua` wraps `SC.Vehicle.exit`; `test_s91_engine_off_exit.py` 101 PASS; card 4594/4600 with every switch on; adds to s90's example bank when present) | install `apply_s91_engine_off_exit_lua.py` + `apply_s91_engine_off_exit_mind.py` (after s90), `card_check.py --write-doc`; in game: "انزلي" while she drives (log `engine off before exit`), then "نزلي من السيارة وخلي المحرك شغال" (log `engine kept on by order`), then he drives and she gets out | s85, s90 |

### B. Needs only an in-game test (code installed in the lab)

All of these are ON in the lab and OFF in release 0.28.1 unless the row says otherwise. Promotion to the ON list of `build_release.py` only after a runtime PASS line in `SOL_CAPABILITIES.md`.

| ID | Item | Source | Switch | State | Test | Depends on |
|---|---|---|---|---|---|---|
| B1 | Held horn until the GPS drive ends, 5 real minutes, or "بس"; card hook restored in s85 | s79 a0f31f7/9d92b59; s85 f5c5661 | `horn_hold` | in lab untested (single beeps only, 21:47/22:03) | order the horn while she drives; then "بس" | - |
| B2 | GPS speeds 20/40/65, jar cruise ceiling 70, bend governor | s80 5d708a2 | `speed_levels` | in lab untested; jar changed 23:12, ZombieBuddy will ask (Jamal approves) | each GPS button on a long paved drive; watch bends | ZB approval |
| B3 | Stall ladder: every failed way round feeds the next rung; all failed = one line + another road | s81 adad1d2 | `stall_ladder` | in lab untested (fixes the 22:04:42 / 22:08:15 FAIL) | the same long drive (home -> 625 Dewey) | - |
| B4 | GPS to the road in front of the house, honest `road_end` | s82 a2b98c1 | `address_target` | in lab untested (fixes the 21:43 half: 15 tiles off, behind the house) | drive to 625 Dewey from the book | - |
| B5 | Calm preview | s82 a2b98c1 | `preview_calm` | in lab untested | any GPS preview | - |
| B6 | Shooting from a vanilla car seat keeps the seated body (window must be open); KI5 left to damnlib (`ki5_seat_poses`) | s83 7221a18; `SOL_REVIEW` s42 | `veh_shoot_seated` | in lab untested (22:33 FAIL: body through the roof) | van, window open, Sol driving, aim + shoot; then a KI5 car (expect no change) | - |
| B7 | Viewpoint QOL harvest `getShovel` NPE guard (no third-party file edited) | s84 047f6f6 | `compat_vp_harvest` | in lab untested (23:05:59 FAIL) | harvest through Viewpoint's interaction menu | - |
| B8 | Door-route leg counts as reached at LF's radius; another order ends the route | s85 047f6f6 | `place_leg_arrive` (with `spatial_access`) | in lab untested (23:05:51 `leg_stalled` FAIL) | paddock gate walk (`PLAN_spatial_awareness` s8 test 1) | - |
| B9 | Every paper or map with a place goes into her book by kind; "بيتنا" pinned; site roads for big places | s84 468e523; `SOL_REVIEW` s44; `PLAN_address_book` s8 | `address_places` | in lab untested (brochures FAIL 23:07) | open the Coalfield and Ekron College brochures beside her; tap a row in the car; open one while she is far (nothing learned) | - |
| B10 | Exit the car first for on-foot orders (rest at home from the car) | s85 f5c5661 (`SolExitFirst.lua`) | `exit_first` | in lab untested (rest-from-car refusal FAIL) | in the car: "رتاحي بالبيت" | - |
| B11 | s85 Mind: far report said once in the chat and kept in memory; several actions in one reply; "شوفي عنا بالمخزون" -> farm_report; GPS ready line names the button | s85 f5c5661 | (Mind) | in lab untested (Mind files changed; live at the next `launch_lab.ps1`) | multi-order sentence; stock question; GPS ready line | - |
| B12 | `far_work`: spoken report on his return + the supply ledger applied once on load (no `[SolFarWork]` ledger lines in the 21:26 log) | s74 f091251; s85; `PLAN_far_work` s8 | `far_work` (**ON in lab and in 0.28.1**) | runtime half (shift PASS 22:46-23:05, report FAIL) | keeper order, go far, come back: hear the line; check stock and produce moved once | C2 |
| B13 | Cars question near and far answered naturally from around HER; come_car phrases; meta-word reply gate ("اللاعب") | s77 33138b4 (survey PASS); s78 6fccd7f | (Mind) + Lua (no switch) | in lab untested (cars_near half 21:35-21:38; meta leak FAIL 21:37) | "شو في سيارات حواليكي" while she is home and he is far, then beside her | - |
| B14 | Street/city question after the model's "unknown" -> map answer; "متور"/"موتور" -> engine | s82 a2b98c1 | (Mind) | in lab untested (22:22-22:38 FAIL; 22:15 misroute) | "شو اسم هالشارع"; "طفي متور السيارة" | - |
| B15 | `spatial_access` door-first routes. **Wiring verified in the lab code:** passenger boarding `SolOrders.lua:363` (`SolPlace.nextLeg`; next leg at once, 466); driver's door walk via `U.solGoto` (`SolGPS.lua:317-334`), which `SolPlace.install` wraps (`SolPlace.lua:676-714`); far walk-in `SolFar.lua:930` (`SolPlace.goNear`, then regroup); sort, farm and animal access squares. Far car pickup: no walk (body placed at the driver's door square and `takeWheel` in the same tick, `SolFar.lua:860-917`); a car already loaded near him goes through `takeWheel` -> the wrapped `U.solGoto` | s70 766a805; `PLAN_spatial_awareness` s8, s9.1; `SOL_REVIEW` s36-37 | `spatial_access` | in lab, runtime FAIL once (`leg_stalled` 23:05:51 -> B8) | `PLAN_spatial_awareness` s8 tests 1-6 + "اركبي جنبي" from inside the house + "خدي السيارة" | B8 |
| B16 | `item_sort` 0.2.2 (each thing to its container, from the container's own side) | s67 114d56f/507c1b3/0af6e16 | `item_sort` | in lab untested | "رتّبي الأغراض" in the house | B15 |
| B17 | `animal_care` (chickens: water, feed, eggs to a powered fridge) | 5624ad6, 53a665a | `animal_care` | in lab untested (two-value tonumber crash fixed in 53a665a, not re-tested) | "اهتمي بالدجاج", "اجمعي البيض", "وقفي شغل الدجاج" | B15 |
| B18 | `farm_night` (farms outdoors at night with a light; zombies still pause her) | s73 47c2010 | `farm_night` | in lab untested | "اهتمي بالمزرعة" after dark | - |
| B19 | `bleed_get_out` (bleeding while seated and stopped, no zombie within 6 -> out, bandage, resume <=120 s) | 8537552; `SOL_REVIEW` s28 | `bleed_get_out` | in lab untested | a controlled cut while she drives | - |
| B20 | Address book death wipe. **Code verified:** `SolLife.lua:58-59` calls `solAddressBookForget` (`SolAddressBook.lua:151-159`) beside streets, stations and farm; `address_places` rows go with it. **Offline tests exist:** `test_address_book.py` 243-256 (reload keeps, respawn empties, relearn, an old life never shown) and `test_s84_address_places.py` 287-291 (+ home row back when home is known) | `PLAN_address_book` s2/s6/s8 rule 3; `SOL_TODO_20261109` #21, #23 | `address_book` | in lab, offline PASS, never tested with a real death | a real death + respawn on a COPY of the world: book, streets, stations, farm memory empty; a reload of the same life keeps them | a copy of the save |
| B21 | `far_car` far arrival: the car comes in with her at the wheel on a safe street spot inside his loaded ring (out of view, no zombie within 12, no car within 6), turned along the road, fuel once. Live load from byte 2 + rollback on a failed live load (4b8ad83, in the lab jar since 20:51). **Never proven in a real game run:** `BaseVehicle.load` + `addToWorld` + `setAngles` + `takeWheel` in one tick, and the rollback, are proven only on copies of `vehicles.db` (Java tests) | s65 d87a41b, s72 074da4b/c965bd8, 4b8ad83; `SOL_REVIEW` s32, s37, s39; `PLAN_spatial_awareness` s9.3, s11 | `far_car` (**OFF in lab and release**) | runtime FAIL 20:44:59 (byte-0 read) -> fixed, not re-tested | on a COPY of the save: `far_car=on` in the lab only, ZB approval, ~190 tiles away "تعالي بالسيارة"; log `[SolCarArrive] N -> staged`, `arrived at`, `she is at the wheel`, `fuel for the trip taken` once; then force one failure and check the row is rolled back | D1 |
| B22 | `far_meta`: the Bradley (3.5 min) and a helicopter (1 min) kept "in meta" come with her | s76 6cb8a1c; `SOL_REVIEW` s41; `PLAN_spatial_awareness` s12.5 | `far_car` | in the lab jar, OFF | "تعالي بالبرادلي": `(kept in meta) -> staged`, `taken over from the kept copy: yes`; then a helicopter left with its rotor running | B21 |
| B23 | KI5 coverage (Jamal's rule "KI5 vehicles must work"): board, drive, refuel, park, far car, seated aim with a KI5 car | `SOL_REVIEW` s19 (scripts checked; driving "needs in-game test"), s41, s42; `SOL_HANDOFF` s8 | various | never runtime-proven with a KI5 car | one KI5 car through the whole car list | B6, B21 |
| B24 | Farm verbs not yet seen in play: harvest, cure, fertilize, weed | `SOL_CAPABILITIES` "not yet proven" (till/sow/water PASS 2026-11-10) | `sol_farm` | in lab untested | "زكاتك احصدي الحصاد", "عالجي الزرع" | - |
| B25 | Older built-not-proven list: seat rule (first free passenger seat, driver only on a drive order); board/exit phrases from the Mind; persona and invented-name gate; farms/gardens she passes remembered; clothes after death and first-respawn katana; long table draws visible rows only; tools by game names; seed/tool questions from the scan; all overhead speech in Arabic; vehicles of any mod (seat, trunk, wheels, fuel type, shared door); "تعالي بالسيارة" when her car is loaded near; dot yellow (far asleep) / grey (Mind down); "سول فايقة؟" | `SOL_CAPABILITIES` "مبني بس لسا ما انجرب" | various (on) | in lab untested | one pass through the list | - |
| B26 | Older movement and car switches on in lab and release with no PASS line: `walk_no_resend`, `order_jog`, `walk_search_fast`, `order_breaks_rest`, `order_engine_path`, `refuel_from_can`, `car_eligible_only`, `follow_exits_car`; `vehicle_steer_adapt` has never seen a mirrored vehicle | `SOL_HANDOFF` s5; `SOL_TODO_20261109` #1-5 | those switches | on, untested | record PASS/FAIL during the B tests | - |
| B27 | Older Mind changes in the lab: s63 far car phrases never refuse; s70b `forget_all` on the card; s71 far car question | s63, s70b, s71 rows above | (Mind) | in lab untested | "انسي كلشي"; far car phrases while she is far | - |

### C. Needs Jamal's decision

| ID | Question | Source | Switch | State | Options |
|---|---|---|---|---|---|
| C1 | Map markers that mods draw from Lua into the Java world map (TrueHelicopterEvents `THE_Heard.lua` 303-331 `addTexture/addTranslatedText`; ProjectALifeNPCs camp marker `ALifeSafehouseClient.lua` 605-622): catch them into her book? | `SOL_REVIEW` s44 (devil's advocate: "لازم قرار") | would be new (Java patch on `WorldMapSymbolsV2` in `SolCombined.jar`) | not started | yes = Java patch + ZB approval; no = leave out (THE marks are heard helicopters, not fixed places) |
| C2 | `far_work` is ON in installed 0.28.1 (`build_release.py` ON list, `SolFixes_MAIN.txt`), but `PLAN_far_work` s8 and the s74 row say OFF in release until the spoken report is proven | 69822cd vs `PLAN_far_work` s8 | `far_work` | shipped ON | keep ON (shift proven, report pending) or OFF at the next refresh |
| C3 | Fatigue threshold that stops farm work (higher?) | `SOL_TODO_20261109` #8 ("بانتظار قرارك") | `sol_farm` | waiting | a value from Jamal |
| C4 | Home and her last car at her death: forget or keep? | `SOL_TODO_20261109` #22 ("بانتظار قرارك") | (death forget) | waiting | forget both / keep home only / keep both |
| C5 | `tonumber` gate allowlist: no allowlist is decided anywhere in the docs; `tonumber_check.py` flags every unsafe site and has none (exit 7) | `launch_lab.ps1`; fa87525 | (gate) | none | keep no allowlist (current) or allow named, proven-safe sites |
| C6 | Phone model evaluation cadence: the only rule is "never while he plays, tell him first"; the s52 full-card latency/accuracy eval is unfinished (`SOL_TODO_20261109` #20) | `SOL_HANDOFF` s3, s6, s0 item 8 | `model_first` | not scheduled | e.g. one eval with the game closed before each release |
| C7 | 38 game actions the Mind runs if named are never shown on the card (`board_vehicle`, `sol_drive`, `sol_take_wheel`, `sol_cook`, ...) | `card_check.py` WARN (b) | (Mind) | warning only | keep hidden (budget 4540/4600) or put some on the card |
| C8 | Nicer seated aiming via the WIP "Project Viewpoint - Drive-By Shooting" mod (needs Viewpoint 0.1.7) | `SOL_REVIEW` s42 strategist 4 | - | not needed unless B6 looks bad | only if he wants more than B6 |

### D. Blocked

| ID | Item | Blocked by |
|---|---|---|
| D1 | `far_car` / `far_meta` runtime proof (B21, B22) | his-only steps: approving the changed jar in ZombieBuddy and playing on a copy of the save; `far_car` stays OFF until then |
| D2 | `item_sort` and `animal_care` release ON | `spatial_access` + `place_leg_arrive` in play (B8, B15) |
| D3 | A2 (book places in the Mind memory) | card budget: 4540 of 4600 chars used |
| D4 | s52 full model card | C6 (phone eval) |
| D5 | Player-made map marks into the book | no game event when he places a mark (`PLAN_address_book` s7) |
| D6 | Driving to one of the 14 named places inside Coalfield (Saloon, Bank, ...) | the game data has names only, no coordinates; she drives to the Coalfield entrance and says so |
| D7 | Promotion of every B item to the release ON list | its runtime PASS |
| D8 | Clearing `_backup\20261109_*` and `20261110_*` (to the Recycle Bin) | the matching tests passing |

### Decisions taken without asking (Jamal 23:44: "لاتوقف", decide by the rules), 2026-11-10 late

- **C1 (mod map markers drawn from Java, TrueHelicopterEvents / ProjectALifeNPCs):**
  - Not captured for now. Jamal's capture rule is "an item he opens", and these markers come from no item.
  - A Java patch on `WorldMapSymbolsV2` is risky for the gain. Deferred, not dropped.
- **C2 (`far_work`):** stays ON in 0.28.1.
  - The shift is proven in play: 43 jobs, and it ended on time.
  - The spoken report is fixed in s85. Its in-game check is B11.
- **C3 (fatigue level that stops farm work):** unchanged until a test shows a problem.
- **C4 (her home and last car on her death):** home stays, since SolHome is Jamal's base. Her car follows the existing rule.
- **C5 (tonumber gate allowlist):** none. The gate is clean, 0 hits.
- **C6 (phone model eval):** run live after every Mind change, only while Jamal is not playing. It was run tonight: 71/75, then fixed to 75/75 offline.
- **C7 (the 38 game actions not shown to the model):** REVERSED (coordinator, per Jamal's rule that every Mind action is on the card with an example). Two-tier card: tier 1 always sends an index of all actions; tier 2 retrieves the most relevant examples per message. Being built as s90.
- **C8 (Drive-By Shooting mod):** only if B6 fails in game.
- **A13:**
  - 0.28.1 lives on release/0.28.0, PR #6 (title updated).
  - `gps_plain_words` evidence is Jamal's own confirmation, 23:35: "شتغلت".

### In progress (started 23:45)

- A1 smart nearby parking + A10 move check: s87.
- A6–A9 + A11 diagnostics, translations and memory restore: s88.
- A3–A5 address-book extras: s89.
- A2 the book in her Mind memory: s86.

### State at 00:20 (2026-11-11). Session paused for the usage limit; resume here first.

1. **far_car "تعالي لعندي بالسيارة" (s92), Jamal's TOP priority.**
   - The end-to-end review and the automated copied-save proof were stopped mid-work. A partial probe exists, uncommitted: `05_TOOLS\sol_nav_java\localplayerbody\SolVehicleLoadProbe.java`.
   - `far_car` stays OFF in the lab and in the release.
   - Next session, in order:
     1. Rerun the review: states (1)–(6) from the s92 brief. The near and loaded cases go first.
     2. Run the real-game proof on a COPY of the save: `launch_lab.ps1 -TestWorld`, 5 runs in a row (car near home, car near another spot, a KI5 vehicle, the Bradley, a forced fail with rollback).
     3. Only then turn far_car ON in the lab.
2. **Two-tier card (s90).**
   - Installed, but set to `CARD_TIERS = False` in `model_router.py`.
   - Reason: on the live phone model (qwen3-4b) it scored 94/113, and some of the old 75 regressed (engine/headlights options, board/come mix-ups, awake, park).
   - The one-tier card is active now: 4558/4600 chars. card_check PASS with 1 warning (the 38 actions hidden again).
   - Next:
     - Fix the option format, the confusable names in the index and the lost meanings, then re-enable.
     - The bar: the live eval reaches at least the old 75 with no regression.
     - Misses: scratchpad live_eval2.txt (also the MISS list in this session's log).
3. **Installed tonight, not yet played:**
   - book_memory, book_visited, book_hint, fail_reasons
   - smart_park, move_check, exit_engine_off
   - address_places, compat_vp_harvest, place_leg_arrive
   - exit_first, horn_hold, speed_levels, stall_ladder
   - address_target, preview_calm, veh_shoot_seated
   - All of these are OFF in the release.

- 2026-11-11 00:35: s91 exit_engine_off: runtime PASS (Jamal: "نجح"), now ON in MAIN. s93 restore_hands: runtime PASS (Sol came back on load and drove). Her weapon back in hand still needs a look.

- 2026-11-11 00:37–00:41, refuel at the pump: FAIL.
  - The car stood beside the pump. `sol_fuel` returned `no_way_to_pump` 3 times: "every square near the work was tried" / "no free square within reach", because both squares by the fuel cap were blocked (pump island, bin, the other car).
  - Her chat line still said she was going and coming back, so the failure was not told.
  - Next: when the cap side is blocked, re-position the car (nudge or pull to the other side of the pump) or use the other pump. Report a failed refuel errand in chat. Detect "already at a powered pump" and refuel in place instead of a drive errand.

- 2026-11-11 00:43: s87 smart_park PASS (Jamal: "نجحت"), ON in MAIN.

- 2026-11-11 00:45: s85 exit_first PASS ("رتاحي بالبيت" from the car; Jamal: "نجحت"), ON in MAIN.

- 2026-11-11 00:49: street/town question PASS: routed to the map answer, "نحنا برا البلدات" (home is outside town limits).
  - Next: also name the nearest town and its distance in words.
  - Also (coordinator): outside towns, include the current road name, e.g. "نحنا على KY-163، برّا البلدات، أقرب بلدة X على بعد N كم" (road from the street gazetteer under the player). Confirmed on KY-163 by Jamal's map at 00:49.

- 2026-11-11 01:12: Jamal: "كلو شغال" for the whole test list. Runtime PASS: horn_hold, street+town questions, address_places + book_memory (Coalfield + "شو في عنا عناوين"), fail_reasons ("ليش ما زبطت"), speed_levels 20/40/65. All ON in MAIN.

- 2026-11-11 01:14: s83 veh_shoot_seated PARTIAL. He stays seated (no pop out of the roof), but:
  - it fires only ONE shot. Check: fire rate, the aim state reset each shot, the seated aim anim not looping, EFZ auto/semi handling;
  - the character model twists into itself. This existed before our change; possibly the seated aim anim blending with the Viewpoint camera.
  - ON in the lab, OFF in MAIN until fixed.
- 2026-11-11 01:18: s85 compound orders PASS ("سول طفي المحرك ونزلي"; Jamal: "نجح"). Mind only, no switch.

### Final state of the night, 2026-11-11 01:20

- **Release:** 0.28.3, installed in main and pushed to PR #6 (release/0.28.0 branch, 36c7147). Not merged.
- **ON in MAIN:**
  - the earlier proven set;
  - secret_loadout, gps_static_roads, gps_plain_words, far_work;
  - exit_engine_off, smart_park, exit_first, horn_hold;
  - address_places, book_memory, fail_reasons, speed_levels, restore_hands.
- **Compound orders (s85):** passed in play. It is Mind only, so the release needs no switch for it.

**Next session, in order:**
1. far_car "تعالي لعندي بالسيارة" (s92 WIP, not installed, OFF). Review, then 5/5 automated runs on a copied save, then ON in the lab.
2. Two-tier card s90 (installed, CARD_TIERS=False). Fix the live phone regression (94/113), then re-enable.
3. Refuel with the fuel-cap side blocked: reposition the car or use the other pump, say why on failure, and refuel in place when already at a pump.
4. veh_shoot_seated: only one shot fires, and the model twists (pre-existing). OFF in MAIN.
5. City answer outside towns: add the current road and the nearest town with its distance.
6. Resolved: bare "تعالي لعندي" maps to come_car (Jamal's rule).
- 2026-11-11 08:40: Mind route timeout provider-aware (6fbfb3a), no switch. One-click friend package and build script in 05_TOOLS\packaging. Groq no-reply fix UNCONFIRMED.
- 2026-11-11 08:43: Jamal rule update: "عبي السيارة بنزين" = gas can first (hers, then home/storage); with no can, the nearest gasoline tanker (says so); never a station. Plan: PLAN_liquid_tankers.md. Code staged (switches OFF); the mod is not yet subscribed.
- 2026-11-11 09:20: s95 station_survey installed in the lab (ON in the lab, OFF in MAIN). Release 0.28.3 unchanged, because nothing new passed in play. Launch for Jamal's station test.

## 2026-11-11 10:50 lab install (Jamal's OK 09:47: "اعمل الاصلاحات وثبتها وبس تخلص شغل العبة")
Backup: `07_TEST/SOL_LAB/_backup/20261111_before_s96_s97`. All are lab only; MAIN unchanged (no new runtime PASS).
| Fix | Commit | Switch (lab) | State |
|---|---|---|---|
| s96 leg_yield: a SolPlace leg yields only to a new order name (base_duty's own serial bumps ended sort walks 10:36-10:42) | 198554c | `place_leg_arrive` on | in lab untested |
| s95b station approach: approach point beside the pose's open lane end, then the short turn in (planner ran out of 60000 states from 30 m away) | 489abaf | `station_survey` on | in lab untested; station refuel PASS 10:31 (one station) |
| s95b tank gate (Mind): reads HER car (sitting in / nearest to her within 15); >=99% refuse, 90-99% "فيها X%، رح كمّلها" | 489abaf | (Mind) | in lab untested |
| s97 two_hand_grip: equip goes on when a throwing OnEquip handler left the item in the hand; 2 s check puts a two-hander in both hands | 0e8f899 | `two_hand_grip` on | in lab untested |
| kahlua_overload_guard (file apply_s96_kahlua_overload_guard.py): logs every pcall'd "No implementation found for function" with the call site; Sol's own call helpers stop repeating a known-bad signature | this commit | `kahlua_overload_guard` on | diagnostic; grep `[SolKahluaGuard]` next session |
| item_sort | - | **off** in lab | off until the overload caller is found |
Root cause of the game-wide `callFrame` NPE (251+ in the 10:19 session, also hit the player's own hotbar equip and gave both him and Sol a one-hand rifle grip): vanilla Kahlua `MultiLuaJavaInvoker.call` releases one pooled MethodArguments twice when no overload fits; every pcall'd failed overloaded call adds a duplicate, each nested Java->Lua->Java call then NPEs once. Reproduced offline (`s96_Repro.java`). Only a JVM restart clears it. Onset 0.7 s after SolSort started (inference: the sort made a failing overloaded call per item; caller not yet named).
Still open (not installed): calm walking vaulted the porch railing between two planned legs at 10:40:51 and her helmet fell (IsoFallingClothing 7406.197,8258.394), not picked up; agent working on `walk_no_vault` + `gear_recover`. Work-time rifle sling designed, not installed.
- 2026-11-11 11:04 runtime PASS: `two_hand_grip` (s97): at load the check put the G28 in both hands (10:59:48 "[SolTwoHandGrip] both hands on EscapeFromZomboidFirearms.G28"); Jamal's screenshot: she holds it at the grip. Stutter diagnosis: `DOCS/PERF_STUTTER_20261111.md` (no fix applied).
- 2026-11-11 11:13 lab install: walk_no_vault + gear_recover (cd9e0a7) ON in lab, untested in play. Lab mod list: JullesLiquidTankers kept (Jamal enabled it in the in-game manager 10:56), SWMG moved back before Viewpoint; MODS_LAB_MIN.txt updated.
- 2026-11-11 11:53 staged for the next launch: GC flags in 07_TEST/SOL_LAB/sol_lab.args (-XX:MaxGCPauseMillis=20 -XX:+UnlockExperimentalVMOptions -XX:G1NewSizePercent=30), verified with the game JRE (-XX:+PrintFlagsFinal). Revert: copy 07_TEST/SOL_LAB/_backup/sol_lab.args.before_gc over sol_lab.args. Baseline: JFR 11:16 (7 GC pauses 514 ms, one 333 ms).
- 2026-11-11 11:53 lab install: s98 combat_equip_fallback + preferred_weapon ON (4cb0b2a), with the GC flags; backup _backup/20261111_before_s98.
- 2026-11-11 12:20 lab install (game closed, Jamal's OK): s97b walk_no_vault upgrade (f8eee8c, offline 48/48), s99 mag_fill + weapon_scan + melee_choice + SolCombatEquipFallback 0.3.0 (4733a0f, 75/76 on the live dir; the 1 fail is 'installer already applied'), perf_slice (875e89d, 49/49). Switches on: walk_no_vault, mag_fill, weapon_scan, melee_choice, perf_slice. Backup _backup/20261111_before_s99. Lab mod list: SWMG moved back before Viewpoint; ViewpointVisibleLoot (enabled in-game 11:5x) kept, MODS_LAB_MIN updated. NOT launched. Gate exit 8: card_check (b) exit_vehicle now listed (the game snapshot of 12:19 lists it as an enabled loadout button) without an example; (e) doc out of date. s100 item_stacks (identical items as one entry with a count) still being built.
- 2026-11-11 12:38 runtime PASS: walk_no_vault s97b (Jamal: she follows by the right way instead of vaulting; log: 11 'engine path ... vanilla walks to <gap> first' re-aims, 0 calm vaults since 12:26). Note: Jamal reports long pauses before her decisions; the callFrame poisoning was active (5 NPEs) - recheck after s101.
- 2026-11-11 13:12 lab install (game closed, Jamal: "اعمل كل الاصلاحات ... وبعدين شغل العبة"): the s99 fix files (SolWeaponPick, SolMagFill: getAllCategoryRecurse with ArrayList, b70ee37), s100 item_stacks (1d2f4bf), s101 edge_api (1d381e7, the root cause of the Kahlua callFrame poisoning), s102 reaim_hold (b3c8faa), s103 kit_bare + parts_delivery (c5aa69b). mag_fill, weapon_scan, melee_choice back ON. All gates incl. jarcall OK. Backup _backup/20261111_before_s100_s103. runtime PASS 13:10 (Jamal): she carries and fires the M4 after he rebuilt it; FAIL: very poor shooting (whole magazine, no kill) -> s104 shooting_discipline in work.
- 2026-11-11 13:28-13:30 session (log 2026-11-11_13-12):
  - runtime PASS:
    - parts_delivery: 39 items to Jamal, flag set.
    - kit_bare: Sol's M4 and G28 rebuilt with 12 and 18 defaults removed; 0 duplicatePath.
    - edge_api (s101): 0 callFrame NPE and 0 failed overloaded calls this session (earlier sessions had 5-251).
  - not exercised (no log evidence):
    - katana melee: no combat-engage this session;
    - mag_fill: the only SolMagFill lines were M4 ammo-count notes;
    - porch walk_no_vault: no re-aim this session; it already passed at 12:38.
  - item_stacks: not grouping live (fix in work).
  - The JFR was cut short: the game closed at 13:30, so no GC numbers.
- 2026-11-11 13:33 runtime PASS by Jamal's report: melee_choice (katana used), mag_fill (she refilled the magazine after emptying it), M4 equip and fire after kit_bare. Remaining: gear plan (combat_plans s105 in work) and stutter.
- 2026-11-11 14:48 lab install (Jamal: his request is his OK): s104 shooting_discipline, s105 combat_plans (Lua + Mind, card 4571/4600), item_stacks 0.2.0 + cache, s106 lua_profiler (off). Gates OK. Backup _backup/20261111_before_s104_s106. Standing rule (Jamal 14:47): when he asks for fixes plus a test, install and launch without asking again.
- 2026-11-11 15:18 lab install (game closed): s104b shooting (8d5c36d), item_stacks 0.3.0 (5eda70c), s107 gear_page (b5a29a1), s109 reply_after_result Lua+Mind (0b0ebc8). Gates OK, card 4571/4600. Backup _backup/20261111_before_s107. s108 perf_hotspots not yet reported -> next restart.
- 2026-11-11 15:22 lab install: s108 perf_hotspots (switch reads on the frame clock; bag walk only on change; LF per-system breakdown [SolPerfHot] every 15 s). Offline 36/36. Finding: LF SCRuntime@L1344 is LF's whole AI tick (35 ms/s real work, not cut); a 396-443 ms/s LF spike 14:52-14:53 while following past the porch fence, cause to be named by the breakdown.
- 2026-11-11 15:25 project plan written: DOCS/SOL_PLAN_20261111.md (done list with switches/commits/tests/state, remaining in priority order).

### 2026-11-11 s110/s111 combined runtime incident and correction

- First run used isolated save `07_TEST/SOL_LAB/profile/Zomboid/Saves/Sandbox/2026-11-10_02-39-13`.
- Confirmed failure: `2026-11-11_18-28_DebugLog.txt` repeatedly throws `attempted index: ordinaryInterval of non-table: null` at `SCRuntime.lua:487` in `decisionTaskCore`. Cause: bare `require "SolDecisionBudget"` did not bind the helper's returned table; the dereference occurred even with the feature switch off. This explains why Sol's ordinary decision loop failed during Jamal's follow/order attempts.
- The `SolDamageProbe` initialized, but no attributed hit/kill entries were logged. Jamal could not complete the test; no valid damage comparison or performance result was obtained.
- After Jamal closed the game, backed up both runtimes and the switch file at `07_TEST/SOL_LAB/_backup/20261111_before_s110_require_guard`. Corrected s110 installer/source/lab runtime to bind the returned helper locally and guard its call behind the switch with a base-interval fallback. Lab switch currently ON; damage probe ON. MAIN/release unchanged.
- Verification after correction: s110 offline 23/23, s111 probe 10/10, `launch_lab.ps1 -CheckOnly` exit 0 (linkcheck 11963/0, patch access 88/0, tonumber OK, jarcall 0 fail/20 warn, card 4571/4600). These are static/offline results, not Kahlua/runtime proof.
- Research before first s110: official Rockstar benchmark/frame-time parameters and published performance patch notes; Oracle JFR profiling guidance. They inform measurement methodology, not Rockstar's proprietary internal optimization practices and not proof of expected improvement. See `DOCS/COUNCIL_s110_decision_load_throttle.md` for the scope and adversarial review.
- Next authorized step: fresh lab launch on the same isolated save; verify Sol spawns, follows, and obeys a direct command before continuing shooting and comparable stutter measurements. Do not promote s110/s111 to MAIN until runtime criteria pass.

### 2026-11-11 22:16 — s112 phase 1 installed in SOL_LAB

- Backup: `07_TEST/SOL_LAB/_backup/20261111_221659_before_s112_task_scoped_perception`.
- Lab-only switch: `task_scoped_perception=on`. Added one mission scan lease shared by world, inventory and base scans; sliced world/inventory work; queued chat/rescue refreshes; cancellation on new direct order and the existing right-click “انسي كلشي”; Python `sol_forget` preempts the active Mind goal. LF's immediate threat sensing and Sol Mind's existing authority stay unchanged. MAIN/release untouched.
- Offline checks: s112 28/28, s99 perf slicing 49/49, forget preemption 4/4, Python compile, Lua syntax/ASCII, card check pass (one pre-existing warning), `launch_lab.ps1 -CheckOnly` exit 0 (linkcheck 0 mismatch, patch access 0 issues, tonumber OK, jarcall 0 fail/20 warn).
- State: installed, awaiting runtime launch and Jamal's in-world checks; no gameplay/performance PASS. Known limitation: the explicit base discovery remains synchronous (up to 500 ms); task-freshness routing and shared prompt verification are still open.
- First launch attempt closed before the menu because `Get-CimInstance` is blocked in this environment; the short game log had no Lua exception. Updated `launch_lab.ps1` to use `Get-Process` for game/own-Mind liveness, with a safe refusal if Python processes exist but cannot be identified. Parser + second `-CheckOnly` passed; retry launch is pending.

### 2026-11-12 12:48 — s113 installed in SOL_LAB (runtime pending)

- Backup: `07_TEST/SOL_LAB/_backup/20261112_124818_before_s113_sol_headshots`.
- Change: LAB-only `sol_headshots=on`; exact Sol ranged-hit scope substitutes native `BodyPartType.Head` selection. No critical flag, weapon/ammo stat, native hit, global RNG, Steam, MAIN, or release changes.
- Evidence: installer/Lua 12/12; Java 7/7; linkcheck 11995/0; patch access 90/0; tonumber OK; jarcall 0 fail/20 warnings. `launch_lab.ps1 -CheckOnly` exited 0 after restoring `default.txt` to the pre-existing approved `MODS_LAB_MIN.txt`; previous `default.txt` is preserved in the same backup folder.
- Next: launch `2026-11-10_02-39-13`; inspect ZB patch and Lua initialization. Then require Jamal's live combat report and `[SolDamageProbe]` hit/damage evidence. No gameplay PASS or release refresh yet.

### 2026-11-12 16:05 — s116 installed in SOL_LAB (runtime pending)

- Backup: `07_TEST/SOL_LAB/_backup/20261112_before_s116_chest_head` (previous LAB JAR and `SolShootDiscipline.lua`).
- Replaced the earlier burst Head/Neck alternation with a scoped plan: single Head; burst Spine/Torso_Upper, Spine/Torso_Upper, Head/Head. The pattern advances for resolved zombie hits only. Native weapon/ammunition stats and damage formula are retained.
- Installed LAB JAR SHA256: `c8bb708f516bae02a285a5b1ea0560c1af3401d5ead1cfb786a072b10b6ae254`. Fire-mode log wording updated. LAB switch `sol_headshots=on`; MAIN/Steam/release unchanged.
- Verification: Java unit 21/21; installer/idempotency 12/12; linkcheck 12045/0; patch access 93/0; tonumber pass; jarcall 0 fail/20 warnings; `launch_lab.ps1 -CheckOnly` exit 0 (card 4590/4600, one warning).
- Runtime status: not proven in-world. Next: launch with `07_TEST/SOL_LAB/launch_lab.ps1`, load `2026-11-10_02-39-13`, verify ZombieBuddy patch registration, then test single and burst hits while monitoring `[SolHeadshot]` and `[SolDamageProbe]`. No release promotion before a live pass.
## 2026-11-12 — s119/s120 fierce combat follow-ups (LAB only)

- Installed with backup `_backup\20261112_before_s119_s120_combat`.
- `retreat_close_fire`: in fierce plan only, allows one safe firearm counter-shot from 0.75 tiles up to the existing cover-fire minimum, preserving existing encirclement, overrun-risk, visibility, floor, range, obstruction, and friendly-fire gates; below 0.75 retains shove behavior. The next decision resumes retreat.
- `grounded_fire`: in fierce plan only, offers a safe firearm finisher for a nearby grounded/crawling target within 3 tiles; other plans retain LF stomp/melee behavior. Uses ammo, same-floor, visibility, and friendly-fire checks; SolShootDiscipline limits this aim wait to 200 ms.
- `fierce_fast_react`: urgent fierce target aim wait capped at 250 ms (normal discipline remains unchanged outside fierce/urgent cases).
- Backup contains pre-install copies of `SCCombat.lua`, `SolShootDiscipline.lua`, `SolAuthority.lua`, and `SolFixes_LAB.txt`.
- Offline: `test_s104b_shooting_discipline.py` PASS 64/64; `test_s120_fierce_combat.py` PASS 5 assertions including Lua parse, grounded-fire plan boundary, and 200/250 ms caps. Launcher preflight: LINKCHECK 12058/0, PATCH ACCESS 93/0, tonumber PASS, JARCALL 0 fail/20 warn, CARD PASS.
- Runtime: elevated LAB launch bypassed the executor's loopback restriction; log reached Sol Lua initialization with `[SolAuthority] Sol_LAB test copy active` and `[SolShootDiscipline] loaded 0.2.0`. No gameplay proof yet. Verify: (1) fierce close retreat shots at about 2.5 and 1.2 tiles then retreat; shove at <0.75; (2) safe grounded/crawling target within 3 tiles consumes a round in fierce; (3) smart/other plan still stomps; (4) urgent response within 250 ms; capture actual ammo/hit-part/health and Sol errors. MAIN, release, Steam profile, and user saves untouched.

### 2026-11-12 — s123 helicopter pilot seat and generic vehicle handoff (LAB only)

- `SolHeliGPS.H.start()` now takes Sol to the helicopter pilot seat before starting GPS flight; if the player is in seat 0, Sol moves the player to the first installed, reachable, empty passenger seat and verifies the transition. Failure rolls back the player's seat when possible. This addresses the observed `start refused: sol_not_pilot` case.
- Added Mind order `سول طيري بالمروحية` (alternate `خدي مقعد الطيار بالمروحية`) for seat takeover without starting flight. GPS destination selection and Fly remain separate. `عطيني القيادة` is the generic in-vehicle handoff wording; Sol frees the driver/pilot seat by moving to an empty passenger seat while staying in the same stationary vehicle.
- Updated model card and action text. Offline tests: s121 and s122 pass, s82 route replay ALL PASS, Python compile pass. `card_check`: 4597/4600, one existing warning.
- Installed into SOL_LAB after fresh backup `07_TEST/SOL_LAB/_backup/20261112_224501_214054_before_s123_heli_and_handoff`; LAB preflight LINKCHECK 12058/0, PATCH ACCESS 93/0, TONUMBER OK, JARCALL 0 fail/20 warnings, CARD PASS. Elevated launch reached `[SolAuthority] Sol_LAB test copy active` and `[SolGPS] ready v0.5.1`; game remains before world entry. Thus no live flight/seat-switch success is claimed. Startup also logged missing-bone ImportedSkeleton errors and font/FluidContainer warnings; root cause not established. MAIN, Steam, release and user saves untouched.

### s121 — helicopter GPS and altitude modes (2026-11-12)

- Source candidate: `SolHeliGPS.lua` wraps AviationCore `HelicopterInput.GetState`; `SolGPS.lua` bypasses LF road routing for helicopters and uses direct marker coordinates. Low/medium/high controls appear only while Sol is aboard a helicopter; cars retain their road route and speed controls.
- The adapter activates only after pressing Fly. AviationCore requires Sol and the local player in the same helicopter, with the local player in seat 0. Manual input takes precedence per axis; Stop or loss of pilot context releases control.
- Presets (2.4, 5.2, and the world-Z ceiling) are provisional; the 11-12 log only contains ground-level samples. Measure all modes in game.
- Installed in SOL_LAB after backup `07_TEST/SOL_LAB/_backup/20261112_210655_402428_before_s121_heli_gps`; restored the one-line `RealLimbs` difference in LAB `default.txt` after backing it up in the same folder. Launcher preflight passed (LINKCHECK 12058/0, patch access 93/0, tonumber, JARCALL 0 fail/20 warn, card 4590/4600 with one warning). LAB launched through `launch_lab.ps1`; log `2026-11-12_21-08_DebugLog.txt` confirms `Sol_LAB`, `[SolAuthority] Sol_LAB test copy active`, and `[SolGPS] ready v0.5.1`. No in-world helicopter behavior verified yet. No MAIN/release promotion before runtime PASS.

### s122 — Bradley controller review and seat handoff (2026-11-12)

- Bradley M3 source review confirms a separate Trucksmith integration: Sol's `SolTracked.lua` calls Trucksmith `TrackSteer.step` and `Stabilizer.step` only for tracked vehicles she drives. The optional steering/yaw adaptation is tracked-vehicle-specific. Its transferable lesson is narrow native-input bridging; it does not inform helicopter equations or road routing.
- Added `SC.Vehicle.shiftFromDriver` and action `sol_let_player_drive`, guarded by `seat_handoff`. Sol must be the driver in a stopped single-player vehicle, and the target must be an empty reachable passenger seat. The service verifies seat ownership, updates reservations/manifest, and never exits. Player may be outside or a passenger; a player in a different vehicle is refused.
- Mind card and routing updated: `سول عطيني الدركسيون` (alternate `خلييني أنا سوق`). The direct action cancels a competing movement goal and only reports success after the game confirms the seat transition.
- Offline checks: s121 flight harness 32/32, s122 seat-handoff tests pass (14 checks), s82 route replay ALL PASS, `py_compile` pass, card check pass at 4549/4600 (one existing catalog warning).
- Installed to SOL_LAB after backup `07_TEST/SOL_LAB/_backup/20261112_222157_802866_before_s121_heli_gps`; `launch_lab.ps1 -CheckOnly` passed (linkcheck 12058/0, patch access 93/0, tonumber OK, jarcall 0 fail/20 warnings, card 4549/4600). Both normal and elevated launches exited before Sol Lua/mod initialization because ZombieBuddy failed opening its loopback selector (`java.net.SocketException: Permission denied: connect` in `SteamWorkshop.<clinit>`). No game process remains; runtime checks are pending. Required LAB checks: stationary car with player outside and inside as passenger, then Bradley and helicopter separately. Confirm no exit, same vehicle, driver seat free, no displaced occupant, and safe refusal for motion/no reachable seat. Helicopter GPS and AviationCore pilot-seat behavior must be tested separately from the handoff. No MAIN/release promotion.

### s124 — 2026-11-12: pilot seat, driver handoff, and heli landing batch

- Log diagnosis: `[SolActions] sol_pilot_helicopter` failed `sol_pilot_seat_change_failed:seat_service_unavailable`; source looked up `_G.SC` although Living Fellows publishes `_G.SurvivorCompanion`. Prior harness masked this. Corrected the namespace.
- `sol_let_player_drive` failed `no_reachable_empty_passenger_seat`; candidate selection relied solely on `canSwitchSeat`. Now tries installed, vacant, unreserved seats with reachable candidates first and verifies native occupant/seat state. Still stationary + single-player only; no occupant displacement.
- Added helicopter-only GPS button `هبطي هون` between Fly and Stop. It drops the stale marker and commands vertical landing at current helicopter coordinates. Car controls stay unchanged. It is not a spoken command; Mind card unchanged.
- Tests now passing: `test_s121_heli_gps.py`, `test_s122_seat_handoff.py`, `test_s124_heli_handoff_land.py`; Lua 5.1 compile + installer backup/replay checks included. Harness no longer defines fake global `SC`.
- Scope: stage and install only in SOL_LAB, after a fresh process check, dated backup and launcher `-CheckOnly`. Do not start game until the complete batch is installed and preflight passes. Live movement/landing/vehicle compatibility is still pending; MAIN/release/Workshop/user saves untouched.

### s124 batch launch status — 2026-11-12

- Complete batch installed in SOL_LAB after backup `20261112_232058_830259_before_s124_heli_handoff_land`; all s121/s122/s124 offline tests and `launch_lab.ps1 -CheckOnly` passed before the one launch.
- The first restricted launch could not open ZombieBuddy's loopback selector. The single approved elevated launch succeeded; `Sol_LAB`, `SolAuthority`, and `SolGPS` loaded and the lab entered isolated save `2026-11-12_18-08-44`.
- Current screen is in-world, paused, with the debug command console open. `SolScanCoordinator` shows initial world scan acquisition. Runtime behavior is not yet accepted.
- Startup also has unrelated font texture errors, an existing missing mannequin-zone property, and a translation-format warning. No new Sol-specific runtime failure has been observed at this checkpoint.
- Keep the game open for the user's combined test. Do not launch a second instance or promote to MAIN/release before results.

### s124 live test checkpoint — helicopter GPS did not move (2026-11-12)

- User confirmed the seat transfer succeeded, but Sol did not fly to the selected destination.
- Log confirms `pilot seat acquired solFrom=1 playerSeat=7` and `flight started target=7628,8560 altitude=low`; later map destinations were accepted, but the flight log contains no arrival or movement confirmation. The live drive trace stayed around x=7603.9,y=8486.1 with speed near zero and engineRPM=0 in the sampled interval.
- Source review finds a missing control step: `H.start()` changes seat, marks the GPS controller active, and installs the player proxy, but does not request the aircraft engine start. AviationCore's `FlightRuntime` takes its engine-off path when `vehicle:isEngineRunning()` is false, so accepting a route cannot produce takeoff in that state. No `AIRCRAFT_START_TRACE` appeared for this attempt.
- Required follow-up: implement the GPS Fly flow as one guarded sequence—Sol reaches seat 0, AviationCore-authorized engine start/readiness (respect operator-manual qualification; no gate bypass), then altitude and direct-world destination control. Keep the car controller separate. Add tests for starting from each occupied passenger seat, engine already running, start blocked by missing manual/qualification, and route activation only after engine start.
- The live game session is still open. Do not copy files into the installed LAB profile or relaunch until the user exits; source analysis can continue, but runtime remains an incomplete/failed acceptance check.

## User-provided helicopter flight procedure (2026-11-12)

This section records Jamal's explicit operating method and requirements; it is not an inference from the current implementation.

### Procedure demonstrated/described by Jamal
1. Read the helicopter's operator manual before attempting flight; the manual/knowledge gate is part of the intended workflow and must not be bypassed.
2. Take off and climb to the selected flight altitude before beginning directional travel. Jamal's described manual procedure uses maximum available altitude first, then controls direction and movement, then descends and lands.
3. Steer toward the chosen destination through the air. A helicopter is not a road vehicle: do not snap its route to streets or reuse car road-following behavior.
4. Descend and land at the destination (or at the explicitly requested landing point), and report success only after touchdown is confirmed.

### Sol GPS behavior requested
- Show three flight-altitude choices only while Sol is in a helicopter: low (above tree level), medium (above roughly two-storey buildings), and high (maximum practical altitude). The selected band is the altitude target: Sol must climb to it before horizontal route-following.
- Selecting a GPS destination and starting flight should let Sol take the pilot seat from another helicopter seat when safe, start the aircraft through the native/manual-authorized path, wait for readiness, climb, fly directly to the GPS coordinate, then land only when commanded or when the route's landing behavior explicitly requires it.
- Keep the helicopter workflow separate from car steering and road routing.
- `عطيني القيادة` means hand the vehicle controls to the player by transferring the appropriate seat; `سول طيري بالمروحية` means Sol takes the pilot seat and flies. `هبطي هون` requests landing at the selected/current point. These actions must not be conflated.
- A seat switch, accepted GPS marker, or logged “flight started” is not proof of flight. Verify engine start, climb/altitude change, horizontal movement, and touchdown from runtime evidence.

### Evidence boundary / pending calibration
The procedure above is user-provided and should be treated as the behavioral requirement. Numeric altitude values for low/medium/high were not reliably captured from the earlier manual flight session; do not present provisional numbers as measured. Calibrate the bands against the user's observed tree/building/max-altitude levels before claiming those thresholds are verified.

## s125 — flight start and internal control simulation (2026-11-12)

- Root evidence: s124 accepted the pilot seat and GPS marker, but the helicopter remained stopped (`engine_rpm=0`). `SolHeliGPS.start()` did not request engine start, and AviationCore intentionally follows its engine-off branch in that state.
- Change staged: call AviationCore authorization, then the game's `ISVehicleMenu.onStartEngine(sol)` path; wait for actual engine running before activating the Sol pilot bridge. Missing qualification is refused and failure to start times out clearly. GPS climbs to selected altitude before direct-air navigation; no ground reference means no horizontal steering.
- Internal deterministic simulation passed climb → GPS coordinate travel → `هبطي هون` touchdown. It caught an AGL 0.20 landing dead zone, fixed by aligning the land threshold with the existing vertical tolerance.
- Offline s121, s124, s125 state/authorization/timeout tests; integrated simulation; Lua 5.1 and Python compile; model-card gate passed. This does not emulate B42 physics or prove Sol can run the native start action in-world.
- Pending: back up/install only in SOL_LAB, pass `launch_lab.ps1 -CheckOnly`, then verify the real engine starts, Sol climbs before moving, follows GPS, and lands. Main Steam profile and release remain untouched until live evidence.

## s126 — player-earned helicopter manual knowledge handoff (2026-11-13)

- Live evidence: the GPS marker was accepted, but every start was blocked by AviationCore `missing_type_knowledge`. `AIRCRAFT_MANUAL_ALREADY_INITIALIZED` was also present; it indicates the vehicle's manual initialization only.
- AviationCore stores `UH1B_OPERATING` per character; reading `Base.UH1BOperatorManual` grants it to that reader. Sol's NPC knowledge is separate from the player's.
- Staged change: if Sol lacks the operating key, validate the player's own qualification through AviationCore; transfer only the registered key when the player qualifies; then authorize Sol again through the regular native engine-start gate. Otherwise fail closed and do not queue a start. No gate bypass.
- Internal tests plus s121/s124 regressions and integrated climb/travel/landing simulation passed. The currently running game loaded s125, so no runtime fix has yet been exercised.
- Pending: after the user exits the game, install to SOL_LAB with dated backup and preflight; if needed, read the UH-1B operator manual as the player, then live-test engine start, climb, GPS travel, and landing. No release/main profile update until live PASS.
## 2026-11-13 — s127 combined helicopter flight/UI fix (SOL_LAB)

- User stopped the current run to combine the pending s126 operator-knowledge correction with the s127 GPS controls correction.
- Changed only `SolGPS.lua` and `SolHeliGPS.lua`: speed row remains visible; altitude row is conditional on Sol being inside a helicopter; helicopter speed levels adjust AviationCore's forward target and restore the previous value at stop/landing. Car speed remains on LF Driving.
- Internal evidence: s127 behavior/UI contract and installer replay PASS; s126 manual-knowledge, s121 GPS, s124 seat/landing tests PASS; deterministic climb → travel → touchdown simulation PASS; Lua 5.1 syntax and Kahlua tonumber gates PASS.
- Isolated installation: `07_TEST/SOL_LAB/_backup/20261113_001216_965325_before_s127_heli_speed_altitude_rows`. `launch_lab.ps1 -CheckOnly` passed (linkcheck 12,058/0, patch access 93/0, tonumber OK, jarcall 0 failures/20 warnings, card 0 failures/1 known warning). Main Steam profile and release untouched. Runtime acceptance still pending for in-game display, speed response, altitude separation, and game error review.

## s128 — manual helicopter control telemetry and isolated-save mod reference repair (2026-11-13)

- User supplied the AviationCore control mapping: W/S lift, A/D yaw, Up/Down pitch, Left/Right roll; confirmed against the installed `Helicopter_Input.lua` source.
- Added passive `[SolHeliTrace]` logging in `SolHeliGPS.lua` before the Sol-GPS active-state early return. It samples only the local player in helicopter pilot seat, logs control transitions plus a 1-second heartbeat, and includes vehicle x/y/z, currentGroundZ/AGL, speed, and forward vector. It does not alter controls.
- The missing-mod warning was traced to the isolated save containing `Sol_LAB` while the package `mod.info` declares `id=Sol`. Inventory found all other 63 saved IDs available in the local/Workshop sources. Restored the original 64-mod test set and changed only that ID to `Sol` in the isolated lab template, profile default list, and lab save `mods.txt`.
- Rollback copies of the four edited setup files are in `%TEMP%\\SOL_LAB_s128_modlist_20261113_010609`. No main Steam profile or save data files were changed; the lab world binaries remain as they were.
- Lua syntax parse and the trace marker/static wiring checks passed. Runtime confirmation is still required: start the lab with the corrected full mod list, verify Sol and helicopter mods load, then capture a short pilot input sample in the existing lab save and confirm a readable `[SolHeliGPS] [SolHeliTrace]` line before any training flight.
- Relaunched through SOL_LAB_LAUNCHER.bat with the restored 64-entry list; profile default and existing save lists both contain 64 entries with Sol (not Sol_LAB). New log:  7_TEST/SOL_LAB/profile/Zomboid/Logs/2026-11-13_01-07_DebugLog.txt. Source/LAB SolHeliGPS.lua hashes match. Runtime test is waiting for the user to load the existing save and tap one control while seated as pilot; no flight training should start until the trace line is verified.


## s128 runtime recorder test — PASS; manual flight capture pending (2026-11-13)

- In the existing isolated save `Sandbox/2026-11-12_18-08-44`, the recorder emitted `[SolHeliGPS] [SolHeliTrace]` while the local player occupied the UH-1B pilot seat.
- Evidence from `07_TEST/SOL_LAB/profile/Zomboid/Logs/2026-11-13_01-07_DebugLog.txt`: at 01:12:01.652, `keys=-/-/A/-/-/-/-/-`, position `7590.66,8467.45,0.00`, ground `0.40`, AGL `-0.40`, speed `-0.00 km/h`, forward `0.97,0.26`. The stationary A-key tap is recorded with vehicle state; this satisfies the preflight recorder runtime gate, not flight-control training.
- Current session is now capturing the user's manual flight. Expected phases: W climb, A/D yaw, arrow-key pitch/roll, S descent/landing. Review transitions and position/AGL/speed changes before deriving any flight behavior. Keep the isolated save and main Steam profile separate.

## Examiner preservation and reuse guide (2026-11-13)

- Preserved the existing Lab vehicle examiner as the reference: `01_WORK/Sol/42/media/lua/client/SolDriveRecorder.lua`. It records the player vehicle at approximately 10 Hz, buffers and periodically flushes rows, and is gated by `SolLab.active` plus `SolAuthority.on("drive_record")`.
- Added `DOCS/SOL_EXAMINER_GUIDE.md` documenting its architecture, safe reuse recipe, passive/Lab-only requirement, test layers, and evidence boundaries for new examiners.
- The helicopter recorder is a distinct passive path in the same Lua module and uses Aviation Core state/input seams; its deterministic harness passed earlier. This does not yet prove a full manually flown runtime profile or calibrate the logged altitude/coordinate labels.
- Documentation-only change in this step. No Lua behavior, save, launch setup, or release package was changed; no game was launched.
- Clarification from Jamal: the helicopter training dataset must be his own manual piloting while he is in pilot seat 0. Sol's autonomous flight is a later validation target, not the source of the demonstration data.

## s131 — dedicated helicopter examiner (2026-11-13)
- Added passive Lab-only `SolHeliExaminer.lua`; `SolHeliGPS` now calls it directly from the local pilot's Aviation Core input-state wrapper. It logs readiness, file creation, periodic capture heartbeat, and close; records controls, physical world position/altitude, ground/AGL, vertical rate, speed, and heading.
- Left car recording and release files unchanged. Backed up touched WORK/LAB Lua sources in `08_RUNTIME_TEST/s131_heli_examiner_backup_20261113`.
- Offline tests PASS: s129 integrated wiring, s128 sample/fields, s129 analyzer. Runtime capture still PENDING; require READY + CAPTURE_STARTED markers and actual LAB output file before asking Jamal to take off.
- Runtime startup confirmed `[SolHeliExaminer] READY lab_only=true file_api=true` in the isolated LAB profile after all launch gates passed. Still at main menu; pilot-seat capture start/file verification pending. No flight requested yet.

## s135 — full helicopter route simulation and verified landing sequence (2026-11-13)

- The failed live attempt reached Sol seat 0 and engine-ready but had no FlightRuntime handoff, GPS input, altitude transition, or guidance. This is the relevant prior failure evidence.
- Expanded the source-scoped `getPlayer()` bridge diagnostics for AviationCore `FlightRuntime.lua` only; added bounded post-landing wait, engine shutdown through `SolUI.solEngine("off")`, and verified exit through `SolOrders.leaveCar()`.
- Full deterministic LAB simulation passed: seat handoff → authorized engine start → climb → two nearby GPS destinations → landing → engine off → companion exit. Focused regressions s121, s122, s124, s125 flight/start, s127, and s135 passed. `launch_lab.ps1 -CheckOnly` passed all preflight gates.
- The simulation uses a kinematic mock and does not emulate Build 42/AviationCore physics. It passes the internal gate to launch LAB only; live runtime still must confirm the bridge marker, actual altitude/x-y movement, both GPS arrivals, touchdown, engine shutdown, and Sol exit.
- Synced the exact candidate from LAB to WORK; WORK/LAB hashes match. Preserved prior WORK and LAB source files in TEMP. Release and normal Steam profile/save remain unchanged.
- After the internal gate passed, launched the isolated LAB through `launch_lab.ps1` with Steam socket access. The initial restricted attempt hit ZombieBuddy's loopback permission denial; the authorized relaunch is alive as Java PID 6220 with Sol Mind PID 18104, responsive window, and the intended isolated profile/save. A duplicate-launch refusal prevented a second game instance. No world flight trace exists yet; runtime acceptance remains pending.

## s136 — exact FlightRuntime source fallback (2026-11-13)

- The live failure reached engine-ready but emitted no bridge-routed, GPS-input, altitude-rise, or guidance markers. Source inspection confirms AviationCore's `FlightRuntime.lua` obtains its pilot via `getPlayer()` and reads that actor's helicopter input.
- Reproduced the source-match miss with a short `@FlightRuntime.lua` frame. Added a bounded exact-basename fallback, retaining the active-flight and Sol pilot-seat guards, with negative coverage for other modules. Updated the stale s121 static contract to check the new narrow rule.
- Backed up both pre-change Lua copies under `08_RUNTIME_TEST/s136_flight_runtime_bridge_backup`; synchronized WORK and SOL_LAB. Their SHA-256 values match (`0E41035A28BDAC70026B06F2D0FA856FC865FB742869F2172B8729DE5E9D2757`).
- PASS: all ten focused/regression tests from s121 through s135 listed in `DOCS/COUNCIL_s136_heli_runtime_source_match.md`, including deterministic seat → engine → climb → two GPS legs → landing/exit simulation. This is mock/controller proof, not B42 physics.
- PASS: isolated launcher `launch_lab.ps1 -CheckOnly`; all code/profile gates passed. It reported LAB is newer than the installed release. No MAIN save, release install, or model card was changed.
- Runtime launch was attempted while the user's earlier session was still active because the restricted process query returned no visible processes. The old log updated at 13:53:50, the new log began at 13:53:53, and Sol Mind reported port 8768 busy. No flight test occurred; the newly started game stopped during startup.
- Hardened `launch_lab.ps1` to fail closed if Windows process enumeration fails, if a game process is present, or if Sol Mind port 8768 is occupied. Parser check passed; `-CheckOnly` safely refused in this environment because process enumeration is unavailable. Do not relaunch here. Runtime acceptance still requires an environment that can confirm the desktop process list, then bridge routing, climb, two GPS legs, arrival, landing, engine off, and Sol exit.


## s137 — explicit AviationCore pilot handoff (2026-11-13)

- Replaced the unreliable debug-stack/global `getPlayer()` approach with a narrow adapter: the compatible local copy of `AviationCore/Flight/FlightRuntime.lua` resolves its pilot through `SolHeliGPS.runtimePilot()` at movement and correction ticks only. Sol is returned only while her GPS flight is active and she occupies seat 0; ordinary callers retain the real local player.
- The local AviationCore copy checks that the AviationCore mod is active, retains the upstream source and SHA-256 in `08_RUNTIME_TEST/s137_explicit_pilot`, and sets a readiness flag. Sol aborts the flight if that adapter did not load. WORK and SOL_LAB sources were synchronized.
- PASS: focused helicopter tests s121, s122, s124, s125 flight/start, s127, and s135. The route simulation is a mocked controller test, not native helicopter physics.
- PASS: the game's own Kahlua compiler scanned the modified WORK/LAB Sol and FlightRuntime files: 4 Lua files, 0 compile errors. Runtime probe confirmed `debug == nil`; the probe harness was locally corrected to pass an empty argument array to `pcall`.
- `launch_lab.ps1 -CheckOnly` REFUSED with exit 2 because this session cannot enumerate Windows processes. No game launched; do not claim in-game success. The desktop must run the launcher in a process-visible session, then test Sol pilot routing, actual climb, GPS movement, arrival, landing, shutdown, and exit before promoting the change.
- Reusable model guidance: inspect the exact upstream runtime source and call sites first; preserve a fingerprinted upstream copy; avoid caller-stack heuristics when Kahlua lacks `debug`; add a targeted explicit adapter; test absent-debug behavior and unrelated player calls; run the game's own Kahlua compiler; separate mocked movement from in-game proof; launch only when singleton/process guards pass.

## s138 — summon a fueled helicopter by Mind command (2026-11-13)

- Added exact Mind phrase `سول فيكي تجيبي هليكوبتر` / `سول فيكي تجيبي مروحية`, deterministic action `sol_summon_helicopter`, and the requested acknowledgement `أكيد بقدر` after queue acceptance. Updated both runtime routing and `DOCS/SOL_MODEL_CARD.md`.
- Client remembers the local player's last driven helicopter script at most once per second and requests a summon. Server validates an AviationCore-registered helicopter, performs a bounded safe outdoor footprint search on demand, creates it server-side, finalizes AviationCore parts/manual, provides a key, and fills/verifies the JetFuel tank. Missing/unregistered model falls back to `Base.UH1BHuey`; result is logged under `[SolHeliSpawn]` and reported to the client.
- Corrected the source draft's Lua declaration-order issue by placing the `nowMs` helper before the helicopter-memory callback. WORK/LAB copies match for `SolHeliGPS.lua`, `SolActionRegistry.lua`, and `SolHelicopterSummonServer.lua` (SHA-256 verified).
- Backup before changes: `08_RUNTIME_TEST/s138_summon_backup_20261113_172034`; LAB rollback: `08_RUNTIME_TEST/s138_lab_backup_20261113_172508`.
- PASS: focused contract tests (3/3); game Kahlua parser (3 changed Lua files, 0 errors); model-card gate (0 failures, one existing warning); launcher preflight (all gates passed).
- PASS: isolated LAB launch reached world initialization in `07_TEST/SOL_LAB/profile/Zomboid/Logs/2026-11-13_17-29_DebugLog.txt`; `[SolActions] ready v0.4.2`, `[SolHeliSpawn] server request listener ready`, and `[SolHeliGPS] AviationCore input adapter ready` were logged. `SolMind_Alive.txt` continued updating and settings report `active=api:custom/qwen3-4b-2507`.
- Runtime behavior not yet proven: the user still needs to issue the exact phrase in-world once and confirm the reply, then verify `[SolHeliSpawn] spawned ... fuel=full`, the aircraft model/key/fuel, and client confirmation. Startup also logged unrelated font/asset and mannequin-zone errors; no Sol s138 Lua exception appeared in the observed log interval.

## s139 — Kahlua numeric conversion in helicopter summon (2026-11-13)

- Live evidence from the first summon: Sol Mind routed the exact phrase to `sol_summon_helicopter`, queued the request, and replied with the requested 9-character acknowledgement. The server then raised `ClassCastException: Double cannot be cast to String` at `findSpawnSquare` line 92.
- Root cause: `invoke()` returns `(value, called)`. Passing `tonumber(invoke(...))` forwards both Lua results; B42 Kahlua interprets the boolean second result as `tonumber`'s base argument, producing the reported Java cast exception.
- Added `numberMethod()`, which stores only the first `invoke` result before numeric conversion. Replaced every direct `tonumber(invoke(...))` in vehicle proximity, player X/Y/Z, fuel capacity, and fuel readback. Source and LAB SHA-256 match (`EB9F485C66BD5EE2465AB8981D418F401BE9C6D24110011E99FFAB9D9F6F35F1`).
- Backup: `08_RUNTIME_TEST/s139_kahlua_tonumber_fix_20261113` (WORK and LAB server source).
- PASS: summon contract/regression tests 4/4; game Kahlua compiler 1 Lua file, 0 syntax errors; no remaining `tonumber(invoke(...))` occurrences. Runtime retry is still required to verify footprint selection, actual spawn, key, and full JetFuel. The user declined the separately suggested secret-weapon addition; no weapon changes were made.
- Runtime retry evidence: the request passed the prior Kahlua conversion and spawned a `BaseVehicle` with a `Base.CarKey`, then failed at `configureVehicle` line 130 because the script indexed `AircraftFactoryParts.FinalizeVehicle` on nil. See s140 below; this is a second, separate binding defect.

## s140 — capture AviationCore module returns (2026-11-13)

- Root cause from live trace: `AircraftFactoryParts` and `OperatorManuals` are module return values; stock AviationCore stores them as `local X = require ...`. Sol's summon script required both without assigning the returns, then indexed nonexistent globals. `AircraftRegistry` had the same latent issue.
- Captured all three module return tables locally. Finalizer calls now verify function availability, protect execution, and log returned failures using the stock spawn path's diagnostic pattern.
- Backup: `08_RUNTIME_TEST/s140_aviationcore_module_binding_fix_20261113` (pre-change WORK/LAB copies; both SHA-256 `EB9F485C66BD5EE2465AB8981D418F401BE9C6D24110011E99FFAB9D9F6F35F1`).
- PASS: focused summon tests 5/5; project Lua syntax checker 0 errors; Kahlua `tonumber` gate clean; WORK/LAB server-file SHA-256 match `DC6594552107BBB5F404BABF963A6C5AF8F4E6766C5701B77CABAE1F0C096F6D`.
- Runtime retry pending: the current game session loaded pre-s140 code. Restart is required before verifying server success, key, and full JetFuel in-world.

| s143 private full release candidate 0.28.4 | bundle | package assembled; static checks pass with one card warning and three unchanged legacy TONUMBER findings | not yet gameplay-proven; no Steam/GitHub promotion | `01_WORK/RELEASE/SOL_2026-11-13_0.28.4_FULL` |
| s144 private full release candidate 0.28.5 helicopter | full bundle | copied from 0.28.3 + complete 0.28.4 overlay + narrow heli voice/GPS action; card gate PASS (0 fail/1 existing warning, 4600 chars), route replay ALL PASS, s144 focused checks 8/8, TONUMBER OK, Kahlua 288/0, Python compile PASS | no game launch; takeoff/progress/speed/altitude/landing/engine-off/exit still need isolated runtime acceptance; no Steam/GitHub promotion | `01_WORK/RELEASE/SOL_2026-11-13_0.28.5_HELICOPTER_RC` |
| s145 0.28.5 helicopter speed-tier review | isolated LAB staging | candidate Lua 5.1 simulation PASS for slow/normal/fast/slow = 20/40/65/20 km/h, route remains active, altitude is independent, speed config restores on stop; full route simulation and GPS UI checks PASS | launched isolated save `2026-11-12_18-08-44`; in-game speed telemetry and physical flight still pending; no MAIN/Steam/GitHub promotion | backup `_backup/20261113_222644_before_0.28.5_speed_test`; candidate `01_WORK/RELEASE/SOL_2026-11-13_0.28.5_HELICOPTER_RC` |

## s145 follow-up — candidate identity, model card, and launch source (2026-11-13)

- User explicitly has not flight-tested this session; no runtime PASS is added.
- Candidate inventory matches the current WORK source except 12 archived `.bak` files; the packaged and LAB `SolCombined.jar` hashes match WORK. Loadout custom controls remain in `SCUI.lua` and are rendered by `SolPages.lua`.
- Corrected stale LAB nested mod version and old candidate/LAB readme labels to 0.28.5. Backups: `07_TEST/SOL_LAB/_backup/20261113_before_s145_version_label_repair`.
- Regenerated the model card from the current Mind and synchronized `DOCS/SOL_MODEL_CARD.md` with the candidate package. `card_check` PASS: 0 failures, 1 existing warning.
- TONUMBER, patch-access (88/0), and Java linkcheck (11,963/0) pass. Offline Lua simulations were attempted but could not run: Python has no `lupa` module. Previously documented simulation results are not a new verification.
- LAB startup is blocked while PID 24528 (`ProjectZomboid64.exe`, normal Steam process, not the Java process from `launch_lab.ps1`) is active. The launcher singleton guard is preserved. Wait for Jamal to close it before LAB launch; no gameplay test has occurred.

## s146 — detailed gear page in 0.28.5 candidate (2026-11-13)

- Integrated s98/s99/s100/s105 prerequisites and s107 `SolGearPage.lua` into `01_WORK/RELEASE/SOL_2026-11-13_0.28.5_HELICOPTER_RC`. Existing release bundles and stable install were not changed. Backup: `07_TEST/SOL_LAB/_backup/20261113_2300_before_s146_restore_gear_page`.
- Offline candidate-derived test: 106/106 PASS. Covered equipped weapon/ammo/state, worn gear swap/take-off, both bags and transfers, preferred weapons, combat plans, car/home snapshot, comparison rows, virtualization/performance, switch-off fallback.
- Candidate Mind/card synchronized; `card_check` 0 failures/1 existing warning, 4,581/4,600; route replay ALL PASS; s105 Mind test 46/46.
- Runtime UI and inventory interaction are still pending; helicopter runtime acceptance remains pending. Not promoted to MAIN/Steam.

## s147 — merge verified staged work into private 0.28.5 candidate (2026-11-14)

- Snapshot: `07_TEST/SOL_LAB/_backup/20261113_2300_before_s146_restore_gear_page/pre_s147`.
- Integrated s99/s112 task-scoped perception, s104b shooting discipline, s116/s118 native head/chest routing and lethal hook, s119/s120 fierce combat refinements, and restored staged s108 performance work. Kept the existing s107 detailed gear page, candidate Mind/card, s144 GPS voice action, helicopter controller/speed/altitude/manual data, summon feature, and unrelated package contents.
- s108 candidate test 36/36; s112 29/29; s99 sliced scans/catalog 48/48; s104b 64/64; s105 combat plans 103/103; s107 gear page 106/106; s116 16/16; s118 8/8; s120 5/5; s144 15/15; full two-marker flight-route simulation PASS. Synthetic s99 worst-frame results: world 5.99 ms including largest 2.69 ms unit vs 66.53 ms unsliced; inventory 4.11 vs 8.99 ms; catalog 4.00 vs 10.77 ms. These are offline fixture measurements, not game FPS.
- Candidate gates: 298 client Lua files parse, 0 errors; TONUMBER OK; JARCALL 0 fail/20 warnings; linkcheck 12,058/0; patch access 93/0; card gate 0 fail/1 existing warning, 4,581/4,600; Mind route replay ALL PASS.
- Offline evidence only. No game launch or save interaction this turn; gear-page UI/transfers, combat impact and physical helicopter operation remain unverified in-world. No stable/MAIN, Steam or Workshop promotion.

## s148 — continuous helicopter GPS route and passenger-input ownership (2026-11-14)

- Full pre-work backup: `07_TEST/SOL_LAB/_backup/20261114_before_heli_route_speed_fix_complete` (LAB 2,607 files; installed package 2,578 files; `manifest.json`). Exact pre-install backup: `07_TEST/SOL_LAB/_backup/20261114_before_s148_lab_install`.
- Installed s148 only in `07_TEST/SOL_LAB/profile/Zomboid/mods/Sol_LAB`: altitude hysteresis, route guidance during altitude changes, aligned cruise input using existing 20/40/65 km/h caps, and GPS ownership of flight axes while routing/landing. Added `heli_route_ownership=on` to LAB switches. MAIN and the private release candidate were not changed.
- Offline route simulation PASS (32 checks); installer idempotence PASS; Python compile PASS; TONUMBER PASS; candidate-Mind card gate PASS (0 failures/1 existing warning); official launcher preflight PASS (linkcheck 12,058/0; patch-access 93/0; JARCALL 0 failures/20 warnings).
- Launched via `07_TEST/SOL_LAB/launch_lab.ps1` using candidate Mind, game PID 30560 / Mind PID 13740, isolated save `2026-11-12_18-08-44`. This is runtime pending, not gameplay PASS. Monitor the DebugLog and Mind log through the in-world acceptance list in `S148_HELICOPTER_ROUTE_ACCEPTANCE.md`.
- No release/MAIN/Workshop promotion until actual route, altitude change, speed tiers, passenger-key isolation, arrival, landing, engine-off and control restoration pass in-world.

- Runtime acceptance update 2026-11-14: Jamal reports all six s148 flight checks passed. The captured LAB DebugLog independently confirms first-marker arrival, speed targets and measured speed responding at 20/40/65 km/h, medium altitude reached during route, and destination replacement mid-flight with continued guidance. No Sol/AviationCore error was found in the captured flight segment; the late log was dominated by physics impulses, so final arrival/landing/control restoration are user-confirmed. Runtime PASS accepted; candidate/Main promotion authorized.
- Release packaging review found `build_release.py` did not include either `heli_gps` or the newly runtime-proven `heli_route_ownership` in its MAIN ON switch list. Added both so release defaults preserve the tested helicopter GPS behavior. Build a new 0.28.6 candidate and run gates; do not install while the LAB session is still writing its log. Backup and install to WORK and local Zomboid mod only after game closure.
- Final live telemetry: 01:14:26.162 `landed at destination; controls released; shutdown and exit queued`; 01:14:26.485 `landing complete; engine off and Sol exited through the companion vehicle service`. Process check confirmed LAB game PID 30560 still running afterward. The user requests no restart while testing; leave the running session intact and install only after it closes.
- Built `01_WORK/RELEASE/SOL_2026-11-14_0.28.6` from the tested LAB. Release gates PASS: linkcheck 12,058/0; patch access 93/0; no new missing Lua methods; Lua compilation PASS; route replay PASS; card check 0 failures/1 existing warning. The release `SolHeliGPS.lua` and `SolAuthority.lua` hashes exactly match LAB; `SolFixes_MAIN.txt` has `heli_gps=on` and `heli_route_ownership=on`; release `mod.info` is 0.28.6; Lab marker absent. Installation to `01_WORK/Sol` and `C:\Users\JAMAL\Zomboid\mods\Sol` is pending because game PID 30560 is still active.

## s149 — runtime error batch, 0.28.6 isolated integration (2026-11-14)

- User supplied the full Mod Report after closing the game. Grouped it into: Viewpoint null-sprite menu dereference; Kahlua `ReturnValues.put` failures observed later across Viewpoint/CleanUI; and one NPC reload `walkToContainer` failure shared by Sol/Gunworks/CleanUI.
- Earlier LAB guard logs identify SolPlace Boolean overload calls (`getDoor/getWindow/getThumpableWindow/getWindowFrame`) as a concrete source of failed Kahlua overloads. Build 42.22.2's `IsoGridSquare` signatures were checked against the installed `projectzomboid.jar`; changed them to the corresponding `...To(adjacentSquare)` calls.
- Added the Sol-side Viewpoint null-sprite skip and actor-based NPC magazine transfer while preserving Gunworks reload selection. Added Kahlua call-site diagnostics and exact-signature repeat blocking for Sol calls.
- Working source `01_WORK/Sol` was older than the latest candidate, so fixes were transferred only into `01_WORK/INTEGRATION/SOL_2026-11-14_0.28.6_ERRORFIX/Sol`, then to the isolated LAB mod after backups in `07_TEST/SOL_LAB/_backup/20261114_before_runtime_errorfix`. The release candidate and installed MAIN remain unchanged.
- Static API review only; no tests or game launch were run. LAB runtime acceptance is still required before promoting the integration copy or updating MAIN/local release copies. Details/checklist: `DOCS/RUNTIME_ERRORS_20261114.md`.

## s149 — isolated runtime error batch staged in LAB (2026-11-14)

- Synced 11 client Lua files from `01_WORK/INTEGRATION/SOL_2026-11-14_0.28.6_ERRORFIX/Sol/42/media/lua/client` into `07_TEST/SOL_LAB/profile/Zomboid/mods/Sol_LAB/42/media/lua/client`; SHA-256 matched for every file. Existing target files were backed up under `_backup/20261114_before_runtime_errorfix`; `SolEdgeApi.lua` and `SolKahluaGuard.lua` are newly added files.
- Focused offline checks passed: s84 Viewpoint/Kahlua compatibility 29/29; s96 Kahlua overload guard 27/27; s101 edge API 19/19; s149 NPC reload transfer 10/10; s149 null-sprite guard 8/8. These do not establish runtime pass.
- LAB switches enabled: `edge_api`, `kahlua_overload_guard`, `npc_reload_transfer`, `vp_null_sprite_guard`; existing `compat_vp_harvest` remains enabled.
- The 0.28.6 release candidate and installed MAIN/local copy remain unchanged. Runtime validation is still pending: Viewpoint interaction, Sol reload from top-level/nested inventory, and review for new overload failures or Kahlua pool exceptions.
- Runtime launch update 2026-11-14 02:33: `launch_lab.ps1 -CheckOnly` passed after restoring the existing s105 Mind/card patch; the official launcher started LAB PID 17816 and paired Mind PID 13624 on isolated save `2026-11-12_18-08-44`. Log monitoring is active. At the latest check the game was still in `MainScreenState`; in-world acceptance has not started. Three startup `AngelCodeFont` texture-load errors appeared from the game media path; no targeted Sol/Kahlua exception has appeared so far. These unrelated engine errors are recorded separately and do not count as a clean total log.
- 2026-11-14 02:43:03 runtime result: s149 reload test failed on SolMagFill's direct Gunworks `Magazine.reloadMagazine` path (`f:13990`, `walkToContainer` -> `isInCharacterInventory(chr=nil)`). The prior patch only covers `SCNativeActions.BeginAutomaticReload`; do not promote. User requested active log monitoring, so collect further findings and defer edits until testing session ends.

## s151 — refuel errand parsing and pump approach (2026-11-14)

- LAB-only install after pre-change backup `07_TEST/SOL_LAB/_backup/20261114_before_s151_refuel_fix`; `station_survey=on` preserved. MAIN, installed local mod, and release candidate unchanged.
- Fixed “بدونات/بدونة” fuel-can slot recognition, repeated-order cancellation/restart, model card examples, and station-aware parking with s95b approach routing.
- Offline PASS: refuel suite; s95 136/136; s95b 49/49; s151 backup-replay/idempotence/parser test; card check (0 failed, 1 existing warning); tonumber; jarcall (0 failures); linkcheck 12,058/0; patch access 93/0.
- Runtime: pending. `launch_lab.ps1 -CheckOnly` was blocked at Windows process enumeration because `tasklist.exe` returned a username/password error. No launch attempted; do not promote until in-world filling and interruption tests pass.

## s152-s154 + release 0.28.7 (2026-11-15) - offline PASS, runtime pending

Jamal's request: fix the runtime errors, build a complete release that runs on any PC with nothing to download, lose no feature; then: a phone model must connect without fiddling and stay saved (for any phone, not only his), and the model card must match the actions.

- **s152 `npc_reload_transfer` (existing switch):** new `SolNpcTransfer.lua`. Her own magazine/rounds move from her bag to her main inventory with LF's verified move (rollback), no player-only helper. `SolMagFill` (Gunworks `Magazine.reloadMagazine`, `transferBullets`, insert) and `SCNativeActions.beginAutomaticReload` use it. Evidence: LAB DebugLog 2026-11-14 02:43:03 f:13990 and 03:18:32 f:80416 (`chr is null` in `walkToContainer`). Offline 27/27.
- **s152 Mind:** `sol_fixes.py`: the Mind read only `SolFixes_LAB.txt`, so on a normal install home_parks, book_memory, fail_reasons, smart_park, reply_after_result, refuel_short_hop were off. Now the lab file, else `SolFixes_MAIN.txt`. `providers._http`: an address without http(s) is `unreachable`, not a settings loop error (931 repeats on 2026-10-25).
- **s152b:** `SolAuthority` main copy falls back to `SolFixesDefault` (shared Lua written by `build_release.py`) when `SolFixes_MAIN.txt` is missing or silent; the lab is unchanged. Offline 6/6.
- **s153 phone model:** `providers.py`: home-network https servers trusted on first use and recognised by certificate fingerprint (`%LOCALAPPDATA%\SolMind\lan_hosts.json`); a moved phone is found on the same /24 by that fingerprint (no key sent); typed address tried as https/http, with/without /v1; the app's `sha256//` TLS pin is checked when pasted; short keys allowed for Custom. `settings_service.py`: pasted text may hold address + key + pin; Apply or Test success saves source/provider/address/model; keyless Custom allowed. `SolSettings.lua` shows what was saved. His own 192.168.1.140 pem path is untouched. Offline 40/40 against a real local TLS server, also with the packaged Mind on the bundled Python.
- **s154 `card_extra_actions` (Mind switch, on in LAB):** the card is unchanged; a game action the card does not list is added as one example only for the line that asks for it (s90 bank, similarity >= 0.6, max 2, no duplicates, no disabled actions). Offline: the 76 eval lines for card actions get the same card byte for byte; 24/24 possible off-card lines get their action. NOT run on the live phone model.
- **Release:** `01_WORK/RELEASE/SOL_2026-11-15_0.28.7`, built with `build_release.py 0.28.7 lab-switches` (the LAB's switches: 103 on, 5 off). Gates PASS: linkcheck 12,058/0; patch access 93/0; no new missing methods; Lua compile; route eval; card check 0 failed / 1 warning. Leftover `.bak*` files excluded. NOT installed to MAIN or `01_WORK/Sol`.
- **Package:** `08_PUBLIC/Sol-0.28.7.zip` (mod + Mind + bundled Python 3.12.10 + launchers). Verified from the extracted zip: mod identical to the release (2,598 files), Mind imports and starts on the bundled Python, launcher dry run on a fresh and on an upgrading profile. The launcher now keeps the old copy in `Zomboid\SolBackups` (not `mods\Sol.old`, which duplicated the mod id) and replaces the switch file on a version change.
- **Suite:** 113 offline tests: 74 ok. 38 fail the same way on the pre-change files (stale tests); `test_s151_refuel_intent.py` fails only its byte-parity check of `chat_service.py`, which s152/s154 changed on purpose.
- **Not done / limits:** no game launch, so everything above is offline PASS only. ZombieBuddy (Workshop) and an AI model or key are still needed. Voice input needs `sounddevice`, which is not in the bundled Python. PermissionError lines in `sol_mind.log` (11-11..11-13) were not reproduced; none on 11-14.
- Backups: `07_TEST/SOL_LAB/_backup/20261115_before_s152_npc_transfer`, `..._before_s153_phone_model`, `..._before_s154_card_extra`.

## s155 - every game action on the card (2026-11-15) - offline PASS, live model eval pending

- Jamal: an action that exists but that the model is never told about is a bug, and s154 (shown only when his line resembles a stored example) did not fix it.
- `model_router.py`: after the old card's list, one line per remaining catalog action in the card's own format (`id: | "his words" | option: ...`), from the s90 bank: 35 lines (eat, drink, wash, cook, cook_and_serve, read, reload, equip_best, give, fetch, fill_water, take_pill, bandage_player, replace_bandage, open/close door, window, stove on/off, go_inside, goto, rest, attack_nearest, gps_clear, plan status/cancel, drive to a named place, car_wait, sit_beside, take_wheel, and the five squad ticks). `CARD_BUDGET` 4600 -> 6600; the old card is still built within 4600, so none of its lines changed (diff: 0 removed). `LIST_ALL_S155 = False` restores the old card.
- Not listed on purpose: `exit_vehicle`, `board_vehicle`, `set_combat_doctrine` (CARD_DUPLICATES of exit_car / board_car / sol_combat_plan) and `sol_fuel` (helper of the refuel goals). `open_health` and `bandage` are game buttons the old card lists only while the game reports them usable (within 2 tiles); unchanged.
- card_check: PASS, 0 failed; the warning went from 39 unlisted actions to those 4; card 6094/6600; `SOL_MODEL_CARD.md` regenerated. Route eval (mocked model) ALL PASS. `test_s155_card_all_actions.py` 12/12, also on the packaged Mind with the bundled Python.
- Risk, stated plainly: the card is about 1,500 characters longer and holds names close to existing ones (sol_drive / drive, sol_rest / go_home_rest, sol_sit_beside / board_car, sol_take_wheel). s90 regressed on the phone model for similar reasons. The live phone eval (114 lines) has NOT been run; it is the first thing to do with the phone connected. `test_s82_mind.py` (already failing before) now also fails its hard-coded 4600 check.
- Release `SOL_2026-11-15_0.28.7` and `08_PUBLIC/Sol-0.28.7.zip` rebuilt with it; gates PASS; zip re-verified.
- Backup: `07_TEST/SOL_LAB/_backup/20261115_before_s155_card_all`.

## s155 v2 - live phone eval (2026-11-15 evening, qwen3-4b-2507 on Jamal's iPhone, game closed)

- `test_s82_route_eval.py --live --yes-jamal-is-not-playing`, 114 lines, same phone, same evening:
  - old card (`LIST_ALL_S155 = False`): **68/114**.
  - s155 v1 (the 35 list lines, no descriptions): **95/114** (30 lines better, 3 worse).
  - s155 v2 (short descriptions in `DESC_S155`, `sol_` prefix restored, on/off default on): **100/114**, no empty replies. One earlier v2 run gave 67/114 with 42 consecutive empty replies at the end: the phone stopped answering mid-run, not a card result.
- The 14 misses of the 100/114 run: three are actions kept off the card on purpose (`board_vehicle`, `exit_vehicle`, `sol_fuel`); two-order lines where the model answers only the first order (also missed on the old card); "ركبي بالسيارة" -> board_car (old card too); `sol_eat`, `sol_equip_best`, `sol_plan_status`, `set_ride_with_player` answered as small talk (`none`); `sol_goto` -> go_inside; "دبريلي الارض بغيابي" -> plow (the old card gives plow too in three repeats: phone variance, not s155); `sol_horn` option; "سول عطيني الدركسيون" -> sol_take_wheel.
- After that run, spot-checked live (not a full 114 run):
  - `SAID_S155`: sol_take_wheel's list phrase is now "قعدي محل السواق"; "سول عطيني الدركسيون" and "عطيني القيادة" -> sol_let_player_drive, "قعدي ورا الدركسيون بس لا تمشي" -> sol_take_wheel, 2/2 each.
  - `SHOTS_S155`: one card example for honking; "سول زمري بالسيارة" -> option once again (3/3). Bare "زمري" still answers option stop, as on the old card.
  - `parse`: `{"action":A,..,{"action":B}}` and `{"action":A,..,"actions":[B]}` are read as two steps. The model still often answers only the first order of a two-order line.
- Final card 6565/6600 chars; card_check PASS (0 failed, 1 warning: the 4 unlisted on purpose); route eval (mocked) ALL PASS; `test_s155_card_all_actions.py` 13/13. Release 0.28.7 and `08_PUBLIC/Sol-0.28.7.zip` rebuilt and re-verified.
- Owed: one full live run on the final card; in-game check that the newly listed actions execute (the eval checks routing, not what she does in the world).

## s156 `wardrobe` - Sol's dressing room (2026-11-15) - LAB install, offline PASS, runtime pending

- Jamal: a box in her window to change her clothes to any clothing in the game (vanilla or mods) and her hair, with a drop-down that does not stutter, a live view of her, one apply button per part, zoom, Sol's theme; clothes are created when she lacks them; what she takes off stays in her bag (he deletes it himself).
- New `SolWardrobe.lua` (generated from `_pending_refuel/SolWardrobe.src.lua` by `apply_s156_wardrobe.py`; Arabic as escapes). A tab "clothes & hair" under Status opens a separate Sol-themed window: preview (the game's `ISUI3DModel` on the real Sol: drag to turn, wheel or buttons to zoom, pan, turn), eight parts (top, jacket, trousers/skirt, dress/suit, shoes, hat, accessories, hair), each with a list (search box, virtual rows) and an apply button.
- Catalog: every item script with a body location and a clothing item, built once per session at 3 ms a frame; each list sorted on first open, a bucket a frame.
- The preview is the real Sol, so her own body and the body patch's fitting are what is shown. A chosen piece is therefore worn by her as a trial; closing the window or choosing another piece takes it back (her own pieces return, the trial piece is removed). Apply keeps it. Nothing of hers is deleted.
- Finding: `SolCombined.jar` (the VSGirl body code) contains its own garment fitting (ClothingModels, ClothSolver, GarmentGeometry, ClothingWeights ...), so game clothing is adapted to her body at render time; the mod has no clothing made for her body as files.
- Offline `test_s156_wardrobe.py` 38/38 (parts, sliced catalog of 6,000 items, sort, search, trial / take back / apply incl. a dress over a trial skirt, failures leave nothing behind, hair, tab, switch off). tonumber, jarcall (0 fail), Lua compile PASS. The window drawing and the 3D preview are NOT covered offline.
- Installed in LAB only (`wardrobe=on`), backup `_backup/20261115_before_s156_wardrobe`. Not in release 0.28.7 as built earlier today.
- Runtime list: the tab appears; the window opens without a hitch; Sol is shown with her own body; zoom/pan/turn; a list of thousands scrolls and searches smoothly; a picked piece shows on her at once; Apply keeps it and the old piece is in her bag; closing without Apply restores her; hair change and apply; reload the save and confirm clothes and hair persist; watch that LF does not re-dress her.

## 2026-11-15 - first in-game run of s152-s156 (Jamal, new world, LAB, Hotsco + EX on) and what followed
Runtime, his words (36-item list): PASS s152 magazine fill, Viewpoint corpse/car door, wardrobe tab/window/zoom/turn/list/search/
trial/apply/persist after reload, LF does not re-dress her, phone connection, no red errors. FAIL / notes below.

### s157 phone_patience (Mind switch, LAB on) - confirmed cause, offline PASS, runtime NOT tested
- Cause (sol_mind.log): the s155 card is ~6650 chars (was ~4600); the phone answered in ~5 s; the chat call waited 4 s. 28 of 31
  lines ended ProviderError('timeout') and fell to the word lists, which do not know the newer actions. Days before: 0-2 timeouts.
- Fix `apply_s157_phone_patience.py`: phone wait 12 s; model down + word lists empty -> `MR.offline_answer_s157` (example bank,
  similarity >= 0.85, plus the short forms he typed) through the normal route checks; the helicopter order without her name.
- Test `test_s157_phone_patience.py` 11/11. Cost: her answer takes ~5 s with the full card. `LIST_ALL_S155 = False` is the short card.

### s156b wardrobe 0.2.0 - offline PASS (45/45), runtime NOT tested
- His notes: no way out of a list without keeping a piece; no list for armor; a trial piece stayed after closing (the log shows
  4 take-backs on the window's own close, so another way of closing is the likely cause - inference).
- `edit_s156b_wardrobe_src.py`: "back, no change" in every list (header back leaves the list first); 15 lists (armor, vest, face,
  neck, hands, waist/bags, underwear added; unknown mod locations -> other); `WD.guard` takes a trial back when the window is
  gone by any way (tick) and on save. The per-part apply button is now inside the list.

### Hotsco - diagnosis (agent report, javap; no Java source for the body classes)
- confirmed: HNB keeps vanilla meshes but 414 clothingItems XML point m_FemaleModel at `HNBJavaMorph/Finished/*`, 278 swap
  m_BaseTextures to `hnb_surfacelink/*`. Sol's fitter (ClothingModels/AccessoryModels.select) takes whatever the winning XML
  names, so her garment starts from an HNB mesh shaped for Hotsco's chest and is fitted again: chest too big under mesh tops.
- confirmed (bytecode): HNB EX `Main.fail` latches `failed=true`; the log has one `NATIVE_IMPORT_NOT_VALIDATED
  model=garment_kate_trousers` at frame 140 between Sol's garment-fit lines -> EX morphing off for the session (trigger = inference).
- confirmed: `SolNPCAdapter.ok` gives the VSGirl body to every living female NPC IsoPlayer, not only Sol.
- not proven: why painted T-shirts change; the player's hair/shoes offset; the headless creation avatar.
- Plan (not built): remap to the vanilla model/texture names for private-body owners; tighten SolNPCAdapter.ok to the Sol marker.

### Lab mod list changed by Jamal in game (21:10), adopted on his word ("same current lab")
- +16: TombBody, TombBodyCompat, TombBodyCustom, TombBodyTexNUDE, TombFit, TombGothHair, TombGothMakeup, TombGothTexNUDE,
  TombWardrobeALT, SPNCCDetails, SPNCCDetailsHD, SpnCloth, SpnHair, SpnHairAPI, SpnOpenCloth, SpnOpenClothBase, FemaleModelFix, FH.
  -1: HotscoNewBodyEX (not in his list now). MODS_LAB_MIN.txt = his default.txt. His creation-screen screenshots (female: no
  head, shoes and hair off) were taken with THIS list, so they do not test the min list + Hotsco diagnosis.
- Backup `_backup/20261115_before_s157_and_modlist`. launch_lab.ps1 -CheckOnly: OK.

### s156c/d wardrobe 0.3.1 and s158 modest_chest (LAB, 2026-11-15 evening)
- s156c/d: SCLogistics selectOwnedClothingUpgrade re-wore pieces the wardrobe took off (log: 'applied jacket: none' x9). Applied pieces get SC_ManualWearFor, taken-off pieces SolWardrobeOff, Logistics.clothingUpgrade wrapped. Offline 51/51. Runtime: not reported yet.
- s158 modest_chest (SolModesty.lua 0.1.0 installed; switch on): one call LocalPlayerVSGirlCensorship.configure(true) at Lua load. Log confirmed: '[VSGirlBodyExtension] Censorship startup=ON'. Jamal's words: the change works, keep it; without clothes she is back to the natural look. He did not test it fully.
- SolModesty.lua 0.2.0 (bra under a top) sits in _pending_refuel and is NOT installed: he reports a bra does not hide the details in game.
- Lab mod list adopted again on his word: HotscoNewBody and TombFit are no longer in it (removed by him in game).

## 2026-11-16 - s159 under_cloth, release 0.28.8, main install, GitHub
- s159 under_cloth (switch read by SolCombined.jar itself): under a painted top Sol's chest takes the shape Jamal accepted from offline renders (05_TOOLS/sol_cloth, chest_preview6 column 3; method after BodySlide outfit presets and the Daz Clothing Breast Helper: tips gone, bust held, valley and under-bust partly bridged). BraGeometry.fitted replaced for size L at the end of its constructor; Physics.bra / PreviewSupport.bra also true for painted tops. Bare shape never written. M and S keep the patch's own shape.
- Offline: UnderClothTest 11/11, linkcheck 12119 refs 0 mismatches, patch access 93/0. Runtime (lab log): 'under-cloth chest on 1621 vertices', no errors; one body refused ('body not recognised', which one is not known). Jamal's words: acceptable and much better than before.
- Rejected on the way (his words): tenting the whole bust into one mass (three variants), overall smoothing ('like bombs'), the patch's censorship mode (white cloth on bare skin, pokes through mesh sweaters, gone on pause) -> modest_chest=off.
- release 0.28.8: build_release.py 0.28.8 lab-switches install (gates PASS; installed copy matches, 2600 files); friend package 08_PUBLIC/Sol-0.28.8.zip; main SolFixes_MAIN.txt written (under_cloth=on, modest_chest=off).
- Main game mod list replaced by the lab's list on his word (81 mods; before: 72), backup 03_BACKUPS/main_modlist_20261116/default.before.txt.
- GitHub: commit 05cc3f88e pushed to claude/project-thread-riooui. main not touched (diverged: branch 260 ahead, main 20 ahead).
- Open: wardrobe preview vs world, mesh garments pierced by the chest (coat, corset, wool), hips under trousers, hide the bag, M/S sizes, hair on the Hotsco/Tomb player body, vacuum cleaner and lawn mower idea.

## 2026-11-16 - main game after 0.28.8 (Jamal live): stutter, Viewpoint 0.1.7, mod list
- Details: `DOCS/SOL_NEXT_20261116.md`, section 'Main game, later the same day'. Sol's code: no errors in these sessions.
- confirmed: heap 3072M at 93% with ~18 collections/s (jstat/jcmd on the running game) -> `-Xmx8192m` in ProjectZomboid64.json on his word; effect not measured.
- confirmed: Viewpoint 0.1.7 disabled itself in the 03:57 session ('PVNV cannot patch lib/sample_sprite.glsl', 20 programs not linked); PVNV = ProjectViewpointNearVegetation. Restart result not confirmed.
- confirmed: PoolPit NoSuchMethodError every tick (10,000+). Kept on his word.
- offline only: SolFixDGVEyes (local override of DGVE_Blocks.lua, one guarded call) enabled after the HUD mod.
- Main mod list 218; Hotsco last; tools: main_body_mod_order.py, check_mod_order.py, scan_viewpoint_addons.py, build_dgv_eyes_fix.py, write_mod_list_doc.py.
