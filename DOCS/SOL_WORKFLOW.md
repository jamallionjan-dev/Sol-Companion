# SOL_WORKFLOW: how we work on Sol (read this first)

## Session start: reading order
1. this file
2. the newest `SOL_NEXT_*.md` (the current step and the backlog)
3. `SOL_HANDOFF.md`
4. `SOL_LEDGER.md` (last rows)
5. `SOL_CAPABILITIES.md`
6. `SOL_MODEL_CARD.md`
7. the `PLAN_*.md` / `COUNCIL_*.md` for the item
8. `git status` and `git log -5` This file explains HOW the work is done, so it stays one continuous piece of work. The ledger says WHAT was done.

## 0. Who decides, who talks
- **Owner: Jamal.** Only his own words authorize installing, launching, or restarting the game or the Mind. A note relayed by a coordinator or another session is a colleague's view, not his OK. When unsure, ask him for one word ("موافق").
- **Language:** to Jamal, short polite Levantine Arabic, first person ("ركّبت…", "لقيت…"). No technical words in Sol's own speech, ever.
- **What to send him:** only verified results or concrete steps, not hypotheses or back-and-forth corrections. Technical detail goes to the coordinator ("sent_to_shared_agent").
- **During live tests:** answer each of his messages within ~30 s.
- **Label every claim:** confirmed (code + log), inference, or needs-in-game-test. Never present an inference as a cause.

## 1. Folders and files
| What | Where |
|---|---|
| Root | `C:\Users\JAMAL\Desktop\Sol` |
| Lab game profile | `07_TEST\SOL_LAB\profile\Zomboid` (mod `mods\Sol_LAB\42\media\lua\client`) |
| Lab switches | `07_TEST\SOL_LAB\profile\Zomboid\Lua\SolFixes_LAB.txt` (re-read every 5 s while the game runs; a missing switch counts as ON in the lab) |
| Release switches | `C:\Users\JAMAL\Zomboid\Lua\SolFixes_MAIN.txt` (a missing switch counts as OFF) |
| Staged fixes | `07_TEST\SOL_LAB\_pending_refuel\` (`apply_sNN_*.py`, `test_sNN_*.py`, new Lua files) |
| Backups before each install | `07_TEST\SOL_LAB\_backup\<date>_before_sNN\` |
| Game logs | `...\profile\Zomboid\Logs\` (newest `*_DebugLog.txt`; older ones in `logs_*`) |
| Mind | `05_TOOLS\sol_mind` (log `sol_mind.log`; card in `model_router.py`) |
| Gates | `05_TOOLS\sol_kahlua\tonumber_check.py`, `card_check.py`, `linkcheck.py` |
| Docs | `DOCS\` (ledger, handoff, capabilities, plans, council notes, perf) |
| Perf recordings | `07_TEST\SOL_LAB\perf\*.jfr` |

## 2. Hard rules
- **Launching:** only through `07_TEST\SOL_LAB\launch_lab.ps1` (use `-CheckOnly` for the gates alone), never `SOL_LAB_LAUNCHER.bat`. The Mind starts tied to the game's PID and stops with it.
- **Never touch:**
  - Steam or Workshop files;
  - `projectzomboid.jar`;
  - ZombieBuddy's `mod_approvals.json`.
  - Workshop mods are read-only references. Compatibility fixes go in our own files only (e.g. `SolCompatVP.lua`).
- **While the game runs:** never install files. Only switch flips in `SolFixes_LAB.txt` are allowed live: they are reversible and take effect within 5 s. Tell the coordinator before flipping anything that changes behaviour.
- **Every fix needs all of these:**
  - its own switch, read at call time through `SolAuthority.on("name")`;
  - an idempotent apply script;
  - offline tests;
  - a commit and push.
- **Kahlua:** write `tonumber((f()))`, never `tonumber(f())`. The `tonumber_check` gate enforces it (exit 7). Lua files are ASCII only; Arabic goes in as escapes.
- **Model-first routing:** synonyms go in the card examples only, never as a keyword override. One action per behaviour.
- **Mind changes:** every one updates the card. Run `card_check.py <mind> --lua <client> [--write-doc]`; `launch_lab` exit 8 means the card is out of step.
- **Release (MAIN):** only runtime-PASS items go into the release (`build_release.py <ver> install`). Never merge PRs.
- **Commits:** stage only our own files. End every message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. No model names in commits or PRs.

## 3. The loop for every bug or feature
1. **Evidence first.** Read the live log around the exact time Jamal reports, and his screenshot.
   - Note the lines with times and frame numbers (`f:NNNN`).
   - Correlate in time: what happened 0–2 s before.
   - Compare with earlier sessions (`logs_*`): was it there yesterday?
2. **Find the code.** Use file:line references in our files, LF (`SC*.lua`), vanilla (`ProjectZomboid\media\lua`), and Workshop mods (EFZ, Viewpoint, Gunworks). Don't invent APIs.
3. **Isolate when unsure.** Flip suspect switches off live (backup first), watch the log, flip back. Example from 11-11: turning off the four new switches proved they were not the cause of "Sol never fires".
4. **Council**, in a short `DOCS\COUNCIL_sNN_*.md` for anything non-trivial:
   - Engineer: how it works and the fix;
   - Devil's Advocate: what breaks, risks, edge cases;
   - Strategist: order of work and what goes to MAIN.
5. **Stage** in `_pending_refuel`:
   - `apply_sNN_x.py <client dir>`: edits by exact old→new strings; refuses if a string isn't found exactly once; prints "kept" when already applied. It adds the switch to `SolAuthority A.FIXES` and appends `x=on` to `SolFixes_LAB.txt`.
   - `test_sNN_x.py`: runs the real patched code in `kahlua_env.lua51` with fakes for LF / EFZ / the game.
   - The tests must cover:
     - a replay of the live case;
     - switch off = old behaviour;
     - installer run twice = no change;
     - tonumber gate;
     - ASCII.
   - Test the install ORDER against the other pending fixes, on a temp copy of the live files.
6. **Commit and push** the staged files, with the live evidence in the commit message.
7. **Install**, only with the game closed and Jamal's OK:
   1. back up the files;
   2. run the apply scripts in order;
   3. run `launch_lab.ps1 -CheckOnly`;
   4. update the ledger;
   5. commit;
   6. `launch_lab.ps1`.
8. **Runtime test.** Give Jamal the test phrases, run a log Monitor, report each result. PASS in play → ledger "runtime PASS" → candidate for MAIN.

## 4. Watching the game
- **Use a Monitor** on the newest DebugLog, with a tight grep for the feature's log tags (`[SolX]`), `Exception thrown`, `STACK TRACE` and `attempted index`, plus `chat: route|goal:` from `sol_mind.log`.
  - Filter out known noise, or it floods.
  - Stop monitors you no longer need; they cost quota.
- **Switches reloaded:** the line `[SolAuthority] LAB switches (...)` confirms it.
- **Performance:**
  - `jstat -gcutil <pid>`, and a JFR with `jcmd <pid> JFR.start settings=profile duration=150s filename=...`, using the JDK 25 tools in `C:\Program Files\Eclipse Adoptium\jdk-25*`.
  - Analyse with `jfr view gc-pauses|exception-by-site|allocation-by-class` and by aggregating `jdk.ExecutionSample` on MainThread.
  - JFR can't name Lua functions: Lua shows up as "pure interpreter". Use SolPerf lines for Sol's own Lua.
  - Record at the same point after loading (1 min) so before/after runs compare.

## 5. Traps already learned (do not rediscover)
- **Kahlua `callFrame` NPE:** vanilla `MultiLuaJavaInvoker` double-releases a pooled object on a failed overloaded call. After that it is game-wide until restart. `kahlua_overload_guard` logs the caller.
- **"Break On Error" in the debug UI** pauses the game on caught errors. Tell Jamal to untick it.
- **LF `SCActionSupervisor` retry ledger:** 4 failures of the same action+target marks it `retry_exhausted` for the whole JVM session, even for his explicit orders. Explicit orders must ignore or reset retry (`retry_reset`, s98).
- **LF's inventory walk is capped at 240 items** (180 from the root). 500 loose rounds hid her weapons. Fixes: s99 `weapon_scan`; s100 `item_stacks` (identical items as one counted entry).
- **EFZ guns:**
  - An assembly with `duplicatePath` makes EFZ empty the hands on equip.
  - A two-hander in only one hand gets the pistol pose (`WeaponType` FIREARM needs primary == secondary).
  - Ammo can sit in the chamber, and EFZ/Gunworks accept several magazine types.
- **LF hands some walks to vanilla `PathFindBehavior2`**: `engine_goal` when the search times out, `native_edge` near cars and trees. That pathfinder vaults low railings with no Lua hook; s97b re-aims those walks.
- **The in-game mod manager re-sorts `mods\default.txt`**, so `launch_lab` exit 4 fires. Put SWMG back before Viewpoint, keep mods Jamal enabled, and update `MODS_LAB_MIN.txt`.
- **`SolActions_Snapshot.txt`** is written by the game and depends on game state, e.g. `exit_vehicle` shows up only near a car. It can change the card and fail `card_check` with no Mind change.
- **GC:** `-XX:MaxGCPauseMillis=20 -XX:+UnlockExperimentalVMOptions -XX:G1NewSizePercent=30` in `sol_lab.args` took the longest pause from 333 to 44 ms. The rest of the stutter is the mods' Lua (61% of the main thread).

- **Boolean edge overloads (root cause of the 11-11 Kahlua poisoning):** B42 IsoGridSquare has no getDoor/getWindow/getThumpableWindow/getWindowFrame(Boolean). Use getDoorTo/getWindowTo/getWindowThumpableTo/getWindowFrameTo(otherSquare) through `SolEdgeApi.call` (s101). LF's SCNavigation/SCTopology had the same calls. jarcall_check checks arity only, not argument types: review the types of any overloaded call by hand (javap).
- **Saved EFZ guns doubled their parts on reload:** SCPersistence recreates a saved gun with AddItem, EFZ's OnCreate adds the default preset, then the saved parts go on top (different templates = different PartTypes, both stay). kit_bare (s103) strips first and repairs doubled saves.
- **B42 ItemContainer has only `getAllCategoryRecurse(String, ArrayList)`.** Pass `ArrayList.new()`. jarcall_check (exit 9) catches arity mistakes like this.

## 6. Using helpers (subagents)
- **Delegate** deep research or building to a background agent with a full brief:
  - paths;
  - rules (no lab edits while the game runs, stage only, switch, tests, gates, ASCII, tonumber);
  - the live evidence with times and lines;
  - what to report.
- **Don't duplicate an agent's work.** Forward new evidence to it with SendMessage.
- **Treat an agent's report as a claim.** Re-run its tests yourself before committing, and check its file:line claims before telling Jamal.

## 7. Paperwork after every batch
- **`SOL_LEDGER.md`:** one line per install, PASS or FAIL, with time, commit, switches and evidence.
- **`SOL_NEXT_<date>.md`:** keep it current: the current step, what's installed but untested, open problems, plans not built, his test list.
- **Plans:** `PLAN_*.md` per feature, council notes `COUNCIL_sNN_*.md`, perf `PERF_*.md`.
- **Commit and push after each step.** The session can end at any time (quota).


## 8. More hard rules (Jamal)
- **Fix the class, not the case.** No coordinates and no single items. Fixes must also work with KI5 vehicles and EFZ / Gunworks guns.
- **Performance first.** No per-frame scans. Slice heavy work to at most 4 ms per frame (the `perf_slice` pattern).
- **Sol's chat.**
  - Never technical. Model-first.
  - No duplicate commands (the `CARD_DUPLICATES` map in `model_router.py`).
  - Update the model card with every Mind change.
- **What his words authorize.**
  - "سكرت" / "تم" = OK to install, NOT to launch.
  - "شغل العبة" = OK to launch.
  - Jamal 2026-11-11 14:47: when he asks for fixes plus a test, his request is his OK. Install and launch without asking again; never ask for "موافق" on something he asked for.
  - Never install or launch without his own words.
- **Her gear and the car.**
  - Nothing may be lost from her gear (`gear_recover`).
  - Engine off when she leaves the driver's seat.
  - No leftover temporary backups in the mod folder. Backups live in `_backup`.
- **Installing in batches.** Never batch untested fixes blindly.
  1. Each staged fix passes its own offline test first.
  2. Test the install order on a copy.
  3. Then do one grouped restart.
- **Kahlua / B42.**
  - Never use `next` on Java-backed tables.
  - B42 removed many `Is*`/`is*` helpers. Check that a method exists in the game jar (`linkcheck.py`), or guard the call with `pcall`.
  - Call Java methods through the `SC.Call.method` / `U.call` wrappers.

## 9. Exact tooling
- **Gates.** All the gates run inside `07_TEST\SOL_LAB\launch_lab.ps1`; add `-CheckOnly` for a dry run. Exit codes:

  | Exit | Meaning |
  |---|---|
  | 2 | the game is running |
  | 3 | the Mind is stale |
  | 4 | the mod list differs from `MODS_LAB_MIN.txt` |
  | 5 | linkcheck failed (our Java vs this game build) |
  | 6 | patch access failed |
  | 7 | tonumber |
  | 8 | card_check |

- **Single checks.**
  - `python -I 05_TOOLS\sol_kahlua\tonumber_check.py <file or client dir>`
  - `python -I 05_TOOLS\sol_kahlua\card_check.py 05_TOOLS\sol_mind --lua <client dir> [--write-doc]`. `--write-doc` regenerates the card section of `SOL_MODEL_CARD.md`.
- **Offline tests.**
  - Run: `set PYTHONIOENCODING=utf-8 & python 07_TEST\SOL_LAB\_pending_refuel\test_<name>.py [client dir]`.
  - They use `kahlua_env.py`, a lupa Lua 5.1 stand-in for Kahlua. `run_all.py` runs the whole suite.
  - Two tests already failed before my changes (11-11): `test_model_first.py` (IndexError) and `test_card_complete.py` (`model_router.NOT_ORDERS` is missing). They fail the same way on the previous `model_router.py`.
- **Switch file.** `SolFixes_LAB.txt` holds one `name=on|off` per line, CRLF.
  - `SolAuthority` re-reads it every 5 s; the log line `[SolAuthority] LAB switches (...)` confirms the reload.
  - A missing name means ON in the lab and OFF in MAIN.
- **Live isolation of switches.**
  1. Back up `SolFixes_LAB.txt`.
  2. Flip the switches: `sed -i -E 's/^(a|b)=on/\1=off/' SolFixes_LAB.txt`.
  3. Wait for the reload line in the log.
  4. Test.
  5. Restore the backup.
- **JFR.** The JDK 25 tools are in `C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot\bin`.
  - Record: `jcmd <pid> JFR.start name=x settings=profile duration=150s filename=07_TEST\SOL_LAB\perf\jfr_<time>.jfr`. Start it 60 s after the world loads (`[SolKahluaGuard] ready` in the log).
  - Analyse: `jfr view gc-pauses|exception-by-type|exception-by-site|allocation-by-class <file>`, or `jfr print --json --events jdk.ExecutionSample --stack-depth 64` aggregated on MainThread (see `PERF_STUTTER_20261111.md`).
  - Quick GC check: `jstat -gcutil <pid> 2000 5`.
- **Release refresh.**
  1. Run `python 07_TEST\SOL_LAB\_pending_refuel\build_release.py <version> install`. It builds from the ON/OFF lists with gates, and installs to `C:\Users\JAMAL\Zomboid\mods\Sol` plus `SolFixes_MAIN.txt`.
  2. Turn on in MAIN only switches that passed at runtime.
  3. Push the `release/<version>` branch and update the PR. Never merge.
- **Friend package.** `05_TOOLS\packaging\build_friend_package.ps1` (see `SOL_PUBLIC_RELEASE.md`).

- **jarcall gate (exit 9):** `05_TOOLS\sol_kahlua\jarcall_check.py <client>` checks that every Java method called BY NAME in Sol*.lua (call/invoke/U.call/SC.Call.method) exists in the game jar (plus our jars) with that many arguments. Unknown names are warnings (they may be Lua tables). It caches per jar in `05_TOOLS\sol_kahlua\.cache`.
