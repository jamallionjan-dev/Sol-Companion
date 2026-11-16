# قدرات سول

هذا الملف فيه بس الأشياء اللي اشتغلت فعليًا داخل اللعبة. كل سطر معه تاريخ التجربة والنسخة.
أي شي مبني بس ما انجرب باللعبة موجود بالقسم الأخير، حتى ما ينعاد بناؤه وما ينحسب شغال.

النسخ: `d4b19bf` و`30ed46a` (commit) على فرع `claude/project-thread-af44jm`.

## السواقة والملاحة
| القدرة | التاريخ | النسخة | الدليل |
|---|---|---|---|
| تجاوز الحواجز بالطريق | 2026-11-09 | 30ed46a | جربها جمال، "اجتازت الحواجز" |
| السواقة عالعشب خارج الطريق المعبد لوجهة محددة | 2026-11-08 | d4b19bf | جربها جمال |
| إلغاء الوجهة من الخريطة | 2026-11-08 | d4b19bf | جربها جمال |

## السيارة
| القدرة | التاريخ | النسخة | الدليل |
|---|---|---|---|
| طفي المحرك واستناني | 2026-11-08 | d4b19bf | جربها جمال |

## الكازية والتعبئة
| القدرة | التاريخ | النسخة | الدليل |
|---|---|---|---|
| مشوار التعبئة كامل: سواقة، صف جنب المضخة، نزول، مشي لفتحة البنزين، تعبئة، رجوع | 2026-11-09 | 30ed46a | السجل: `errand_round_trip_complete`، والخزان وصل 99% |

## الذاكرة والأماكن
| القدرة | التاريخ | النسخة | الدليل |
|---|---|---|---|
| اسم الشارع | 2026-11-09 | 30ed46a | جربها جمال |
| اسم المدينة | 2026-11-09 | 30ed46a | جربها جمال |
| اسم الكازية بالشات | 2026-11-08 | d4b19bf | جربها جمال |

## الخريطة والواجهة
| القدرة | التاريخ | النسخة | الدليل |
|---|---|---|---|
| أيقونة سول عالخريطة | 2026-11-08 | d4b19bf | جربها جمال |

## المخزون
| القدرة | التاريخ | النسخة | الدليل |
|---|---|---|---|
| قائمة المخزون بالأسماء والكميات | 2026-11-09 | 30ed46a | جمال طابق كثير أغراض بعينه، و13 غرض انطابقوا مع الفحص |
| "عطيني سلاحي السري": نسخة من سلاحينو (G28 وM4A1) بكل القطع، مخزن مليان وطلقة بالسبطانة، ومع كل واحد 500 طلقة (المفتاح `secret_loadout`) | 2026-11-10 21:29 | 6e2bc39 + fa87525 | السجل: `[SolSecret] give ...G28:efz:loaded=21:...:rounds=500 \| ...M4A1:efz:loaded=31:...:rounds=500`. جمال قال: "نجح" |

## الدرج (42.22)
| القدرة | التاريخ | النسخة | الدليل |
|---|---|---|---|
| سول بتطلع وبتنزل عالدرج تبع اللعبة | 2026-11-09 | `claude/project-thread-riooui` | جربها جمال |
| Shift: نزول سريع وطلوع أسرع (للاعب ولسول) | 2026-11-09 | `claude/project-thread-riooui` | جربها جمال |

## الزراعة
| القدرة | التاريخ | النسخة | الدليل |
|---|---|---|---|
| حراثة ("احرثي الارض") | 2026-11-10 | `claude/project-thread-riooui` | السجل: 31 `plow fallback=applied`، ولا خطأ |
| زراعة ("ازرعي البذور اللي بهاد الموسم") | 2026-11-10 | `claude/project-thread-riooui` | السجل: 44 `sow fallback=applied` |
| سقاية ("اسقي الزرع") | 2026-11-10 | `claude/project-thread-riooui` | السجل: 79 `water fallback=applied` |

## إعداد المودات
| القدرة | التاريخ | الدليل |
|---|---|---|
| ما في شاشة سودا بأول شخص، والجسم كامل من فوق (بعد إعداد صفحة EFZ) | 2026-11-10 | جربها جمال |
| زوم السكوب | 2026-11-10 | جربها جمال |

## العقل
| القدرة | التاريخ | النسخة | الدليل |
|---|---|---|---|
| العقل بيسكر لحاله مع اللعبة خلال 3 لـ 4 ثواني | 2026-11-08 | d4b19bf و30ed46a | السجل، أكثر من مرة |

---

## مبني بس لسا ما انجرب باللعبة
- كرسي الركوب: أول كرسي ركاب فاضي، وكرسي الشوفير بأمر السواقة بس.
- أوامر الركوب والنزول بكل الصيغ من العقل بدون نموذج.
- النموذج بيحكي كأنه سول، وبوابة الأسماء المخترعة (مزارع، حدائق).
- ذاكرة المزارع والحدائق اللي بتمرق جنبها.
- الموت: اللباس بعد الموت، ونسيان الشوارع والكازيات والأماكن.
- أول رسبنة: اللبس الحالي مع الكاتانا.
- الجدول الطويل بيرسم بس الصفوف الظاهرة.
- طلب العدة بأسمائها باللعبة.
- الزراعة: نظام سول الخاص بدل زراعة Living Fellows: تاخد من مخزون الفحص، تحصد، تسقي، تعالج، تسمّد، تقلع العشب، تفلح، تزرع، وتنقل المحصول. أوامر بالعربي الطبيعي، تقرير ونواقص، وضع المزارعة، والراحة بالبيت. (الحراثة والزراعة والسقاية انتقلوا لفوق، نجحوا 2026-11-10. الحصاد والعلاج والتسميد وقلع العشب لسا.)
- الجديد من 2026-11-10، مبني وما انجرب: المدرعة (`tracked_mode` و`vehicle_steer_adapt`)، الدجاج (`animal_care`)، الفرز (`item_sort`)، الصف بكراج البيت، أمر سواقة جديد بيلغي القديم، النزيف وهي سايقة، تعبئة الكازية، تحذير الـ GPS، حماية Ctrl+A. التفاصيل بـ `SOL_HANDOFF.md`.
- أسئلة البذور والأدوات من نفس فحص المخزون.
- كل كلامها فوق راسها بالعربي الشامي.
- مركبات أي مود بالـ Lua: الكرسي المركّب، الصندوق والعجلات بأي اسم، نوع الوقود، باب واحد مشترك.
- "تعالي بالسيارة" إذا سيارتها قريبة ومحمّلة.
- النقطة: صفرا إذا بعيدة ونايمة، خضرا إذا قريبة أو فايقة، رمادية إذا العقل واقف أو ما في سول محمّلة.
- "سول فايقة؟" بالشات أو بالزر: بتصحى وبتجاوب.
- "تعالي مشي": بعد 5 دقايق حقيقية بتظهر خارج شاشتك وبتمشي لعندك. السيارة والهيليكوبتر والبرادلي لسا مو مدعومين من بعيد.

آخر تحديث: 2026-11-10 بالليل. دليل التسليم الكامل: `SOL_HANDOFF.md`. سجل كل التعديلات: `SOL_LEDGER.md`.

## Proven 2026-11-10 (afternoon, lab)
- Drive home parks in the home garage (`home_parks`).
- A new drive order replaces the running one (`drive_replace`).
- GPS warns when the route ends short of the marker (s53).
- Long paved drive keeps to the paved road with no false obstacles (`road_first` + s49).
- Station refuel: straight to the pump, fills while there is room, real numbers (`refuel_top_up`, `refuel_short_hop`).
- Bradley (Trucksmith tracked vehicle): Sol drives it on the paved road, turns with the road and around a stop sign (`tracked_mode`), 2026-11-10.

## Proven 2026-11-10 (evening, lab)
- Ctrl+A in Sol's chat (debug mode) no longer crashes the game (`debug_ctrl_a_guard`; the guard logs nothing when it skips, so the proof is no crash in play).
- Far walk-in: "تعال مشي" -> she appears near him; with game speed-up the 5-minute wait passes in under a minute (`far_wait_speed`).
- The avatar dot stays green while the game is paused (`dot_paused_fix`).
- "رتّبي الأغراض" reaches the sort, not the old errand (s66).
- "رتاحي بالبيت" -> she goes home to rest.
- Bradley drive on the paved road around the stop-sign corner (`tracked_mode`).

## Proven 2026-11-10 (night, lab, Jamal playing)
Only runtime-proven items. Log: `07_TEST\SOL_LAB\profile\Zomboid\Logs\2026-11-10_21-26_DebugLog.txt` (unless named otherwise) and `05_TOOLS\sol_mind\sol_mind.log`. Full fix list: `SOL_LEDGER.md`.

| Capability | Switch | Time | Commit | Evidence |
|---|---|---|---|---|
| Secret weapon: capture of his two firearms, then "عطيني سلاحي السري" gives exact copies | `secret_loadout` | 21:29:17 | 6e2bc39 + fa87525 | `[SolSecret] give EscapeFromZomboidFirearms.G28:efz:loaded=21:spare=0:rounds=500 \| ...M4A1:efz:loaded=31:...`; Mind `action=secret_loadout gate=accepted result=تكرم، السلاحين معي.`; Jamal: "نجح" |
| Survey answer without coordinates or tile counts | (Mind, s77) | 21:35:28 | 33138b4 | Mind: `action=survey ... result=البيت محدد. في مكان محدد لصف السيارات. عنا منطقة وحدة للزراعة...` (the 20:41 survey still said "عند 7411,8258") |
| GPS routes along the roads over the whole map, through fog | `gps_static_roads` | 21:43:59 | 528548e | `[SolStaticRoads] road graph ready: 10761 points, 11943 road pieces, 225 ms.` / `plan 7413,8264 -> 10840,10120: 249 points, 33 ms.` / `router said INCOMPLETE_MAP_DATA: whole-map roads used.`; 255 plans in the session, 3-52 ms each |
| Address book learns by itself when he opens the paper near her | `address_book` | 20:36:34, 23:06:34, 23:08:20 | 12e7692 + 53a665a | `[SolAddressBook] learned house:10840,10120 625 Dewey Street, Muldraugh.` (`logs_2026-11-10_20-32\2026-11-10_20-31_DebugLog.txt`), `learned house:8048,11559 70 Frederick Ln., Rosewood.`, `learned area:13200,2325 Map: Louisville Central.` |
| Far work: the farm shift runs while he is away and ends when the farm loads | `far_work` | 22:46:52-23:05:16 | f091251 | `[SolFarWork] shift started at hour 91 with 1478 rows, 50 places, 19 water sources.`, `hour 92: 9 jobs` ... `hour 96: 9 jobs` (43 jobs), `shift ended (not_at_farm).` (the spoken report is NOT proven, below) |

## Not yet proven, half, or failed (2026-11-10 night)
| Item | Result | Evidence | Next |
|---|---|---|---|
| Long drive home -> 625 Dewey | half: the route held the roads and she got there, about 15 tiles from the marker but on S Main St behind the house | GPS preview `ends 10823,10120, 17 tiles short of the marker` (21:43:59) | s82 `address_target` (GPS to the road in front of the house, honest road_end), installed ~23:12, not played |
| Long drive stalls | FAIL: 22:04:42 idle about 2 min; 22:08:15 `goal_not_free` loop | `[SolDrive] ladder Java way round failed: stalled at 10591.5,11156.4.`; `[SolNav] no plan: goal_not_free.` then `[SolRoadFirst] no way round close to the road: looking wider.` | s81 `stall_ladder`, installed, not played |
| Far work report on his return | FAIL: not spoken | `[SolFarWork] report given.` at 23:05:26, no line in chat | s85 (in progress) |
| cars_near | half: routing right, no answer while she is away at home | Mind 21:35:08 / 21:36:03 / 21:38:56 `action=cars_near ... result=ما قدرت شوف شو في سيارات حواليّ هلأ` | s78 (answers from around HER), installed, not played |
| Street / city question | FAIL (regression): the model said unknown and she asked him back | Mind 22:22:17-22:38:18 `text=شو اسم هالشارع ... action=unknown gate=not_an_action result=asked him` | s82 map fallback after unknown + card examples, in lab |
| Engine word "متور" | FAIL: misrouted to headlights | Mind 22:15:41 `text=سول طفي متور السيارة ... action=sol_headlights` (22:41:48 "محرك" routed right) | s82 engine words, in lab |
| Chat meta leak ("اللاعب") | FAIL | Mind 21:37:44 `result=سول هنصحك على بقية اللاعب` | s78 reply gate (meta words), in lab |
| Rest at home ordered from the car | FAIL: refused | Jamal's report | s85 (in progress) |
| Far car arrival | FAIL: live load read the car's row from byte 0 | 20:44:59 run, fixed in 4b8ad83 | `far_car` stays OFF until re-tested |
| Brochures and other fliers in the address book | FAIL: not captured | only houses from listings and area maps learned | s84 generic capture (in progress) |
| Shooting from a vanilla car seat | FAIL: body through the roof (vanilla seated aim plays standing poses) | Jamal 22:33; council section 42 | s83 `veh_shoot_seated`, installed, not played |
| Viewpoint QOL harvest | FAIL (third party): `getShovel` NPE | 23:05:59 `Lua(Vanilla).getShovel(ISFarmingMenu.lua:134)` exception | `compat_vp_harvest` (in progress) |
| Door-first walk | FAIL: leg stalled | 23:05:51 `[SolPlace] old walk to 7399,8260: leg_stalled.` | fix in progress |
| Horn | single beeps only; a held horn was asked for | Mind 21:47:20 / 22:03:25 `action=sol_horn ... horn_beep` | s79 `horn_hold` installed; its card hook broke in the s82 compaction, fixed in s85 |
| GPS speeds 20/40/65 | not played | - | s80 `speed_levels`, installed |
| FPS drop while driving | mostly the game's own world streaming (inference) | - | watch |
| engine off on exit | exit_engine_off: engine off when she leaves the driver seat; "خلي المحرك شغال" keeps it | 2026-11-11 00:35 | s91 | Jamal: "نجح" |

## Helicopter GPS voice start — candidate only (2026-11-13)
| Capability | Build | Evidence / status |
|---|---|---|
| “سول طيري على العلامة” starts the previously selected direct-air GPS route when Sol and player are in the same helicopter | s144 / 0.28.5 private candidate | Static action/card gate passes. Not yet tested in game on this candidate. Existing report that Sol once took off and headed to a marker refers to an earlier build, not proof of s144. |
| Flight procedure supplied by Jamal: manual first, climb to chosen altitude, direct-air GPS, land, verify touchdown, engine-off and exit | s144 documentation | Recorded as expected pilot workflow; automatic execution of every stage remains unverified. |
