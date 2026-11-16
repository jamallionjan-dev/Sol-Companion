# s147 — Merge completed LAB work into 0.28.5 candidate

## Evidence

- The release candidate was created from 0.28.3 plus the 0.28.4 overlay and s144 heli routing. It already had the detailed s107 gear page and the helicopter changes; those must remain intact.
- The candidate lacked the s99 sliced action/world/inventory scanners, s112 shared scan coordinator, s104b `SolShootDiscipline.lua`, s116/s118 native hit-plan classes, and s119/s120 fierce close-fire/grounded-fire wiring. Some corresponding MAIN switches were present despite missing implementation.
- The staged s112 installer requires the s99 `perf_slice` prerequisite. Its original test pointed at a deleted historical backup. On a disposable copy of the 0.28.5 candidate, s99 then s112 passed 29 checks.
- The old s116 installer assumed obsolete fire-mode log text and did not connect Lua's per-shot mode to `solHeadshotSetFireMode`. The updated installer now connects the existing burst/single decision to the native Java shot plan; a Lua 5.1 fixture verified burst selects `burst` and an isolated shot selects `single`.
- The s118 native JAR adds only the nine `SolHeadshot` classes to the candidate's existing 432 Java classes (441 total, no removed classes). It contains the combined chest/head plan and opt-in lethal hit hook; it leaves weapon damage values untouched.

## Engineer

Overlay the staged implementations in dependency order: s99 frame slicing → s112 scan ownership; s104b shooting discipline → s116 native hit-plan connection and s118 lethal hook → s119/s120 combat refinements. Preserve the candidate's own Mind, gear page, heli UI/controller, and all unrelated package assets. Enable only feature switches already on in the candidate, and register each corresponding switch in `SolAuthority`.

## Devil's advocate

- Integrating code that has only offline proof does not establish that Build 42, ZombieBuddy, EFZ, or AviationCore behave correctly in-world. Mark gameplay acceptance pending.
- The s118 jar is based on an earlier LAB jar, so compare its class table with the candidate before copying. The checked artifact adds the expected nine classes and changes no existing class files.
- The archive's MAIN switches must not be mistaken for implementation. Recheck each code/module/Java path and run the package launch gates after the merge.
- Avoid replacing whole candidate folders from WORK/LAB; that would erase release metadata and risk reintroducing the missing gear page.

## Strategist / acceptance

Use a pre-s147 snapshot under the existing s146 backup root, test the full installer order on a candidate-derived temporary profile, then overlay only the verified result files. Run focused Lua/Kahlua tests, candidate Mind/card checks, Java `linkcheck` and `patch_access_check`, `tonumber_check`, and the release launcher in `-CheckOnly` mode. Report offline proof separately from in-world proof; do not promote MAIN, Steam, or Workshop.

## Execution record — 2026-11-14

- Snapshot preserved before the merge: `07_TEST/SOL_LAB/_backup/20261113_2300_before_s146_restore_gear_page/pre_s147`.
- Candidate now carries s99/s112 task-scoped scan ownership, s104b shooting discipline, s116/s118 head/chest hit routing and opt-in lethal hook, s119/s120 fierce retreat/grounded-fire behavior, and the previously staged s108 frame-clock/bag-cache/LF performance diagnostics. Existing detailed gear page, heli GPS/manual controls, helicopter summon and candidate Mind were retained.
- s108 had been recorded as installed historically but was absent from the release candidate; restored it from the reviewed staged source and enabled `perf_hotspots=on` in this candidate's MAIN switches. Its candidate-derived harness passes 36/36; 100-second synthetic inventory replay preserved gift detection and reduced Java calls 72,080 -> 18,781.
- Candidate-focused checks: gear page 106/106; scan coordinator 29/29; sliced world/inventory/action catalog 48/48; shooting discipline 64/64; combat plans 103/103; chest/head routing 16/16; one-shot wiring 8/8; fierce combat 5/5; s144 GPS voice action 15/15; full two-marker flight route simulation PASS; s108 performance 36/36.
- The final s99 harness compares the s112-integrated candidate with the preserved pre-s147 candidate. Synthetic world scan worst frame was 5.99 ms including its largest 2.69 ms unit, compared with 66.53 ms one-shot; inventory worst 4.11 ms compared with 8.99 ms; action catalog worst 4.00 ms compared with 10.77 ms. These are harness timings, not in-game FPS.
- Final candidate gates: 298 client Lua files parse with zero errors; TONUMBER OK; JARCALL 0 failures/20 existing warnings; Java linkcheck 12,058/0; patch access 93/0; candidate card PASS, 0 failures/1 existing warning, 4,581/4,600, route evaluation ALL PASS.
- A direct s99 slicing harness and the old s108 installer assumptions do not apply to an already integrated candidate; s112 and the updated s108 candidate harness provide the applicable integration evidence. No release launcher or game was started during this merge. UI, inventory transfer, combat effects and physical helicopter movement remain in-world acceptance items.
- Scope: private 0.28.5 candidate only. No save, Steam/Workshop, installed MAIN, or other release folder changed.
