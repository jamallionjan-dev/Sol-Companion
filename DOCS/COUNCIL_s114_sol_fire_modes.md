# s114 — Sol single-shot and burst fire modes

Date: 2026-11-12. Scope: isolated `SOL_LAB` only. Add two natural-language orders for Sol's currently held ranged weapon, with a physical head target and single-shot Head damage or automatic fire whose damage part alternates Head/Neck. No MAIN, Steam profile, Workshop, or release files are changed.

## Engineer

- The mind card maps `سول قوصي طلقة طلقة` to `sol_fire_mode_single` and `سول قوصي رش` to `sol_fire_mode_burst`; `SolActions.run` dispatches both to `SolShootDiscipline.setFireMode`.
- Single mode selects the weapon's native single/semi mode where available, then reasserts it before each shot. Burst mode selects a native Auto/Burst mode where available, and reasserts it before shots. If the held weapon does not expose the requested mode, Sol returns a failure instead of claiming it changed.
- `SolHeadshot` remains scoped to Sol's ranged hits. It keeps the engine-selected physical ragdoll part at Head and the native weapon/ammunition damage path. In single mode the damage body part is Head for every shot. In burst mode the damage body part alternates Head, Neck, Head, Neck.
- Build 42.22.2's `RagdollBodyPart` enum has no Neck entry; `BodyPartType` does. Thus Neck is a damage/body-part selection, not a distinct physical projectile bone. This distinction is recorded in the log.
- Burst mode does not synthesize a burst for guns without native Auto/Burst. It cannot make a semi-only weapon fire faster than the weapon permits.

## Devil's advocate

- Alternating the damage location while retaining the physical Head bone is an approximation imposed by the engine's separate ragdoll and damage-part enums. Live logs and damage must verify that the engine accepts and applies Neck damage as expected; do not describe it as a physically modeled neck bone.
- Other actors and melee attacks must stay vanilla. If their hit parts change, disable `sol_headshots` and restore the LAB backup.
- Native single/automatic modes may be named differently by Gunworks or another weapon mod. The helper checks the offered mode and verifies the result; runtime behavior still needs a test for each used weapon.
- Weapon balance, ammunition type, range, and native damage are not overwritten. This change does not promise equal numeric health loss between Head and Neck or guarantee a hit when aim/line-of-sight fails.

## Strategist

1. Start the isolated LAB and approve the changed Java mod if ZombieBuddy prompts.
2. Spawn Sol and verify she appears; send `سول قوصي طلقة طلقة`; verify the log reports native single/semi plus `physical=Head damage-part=Head`.
3. Fire at a standing, stationary zombie at close range. Confirm logged Sol hits use Head and compare ammo decrement and health change against the player's same weapon and ammunition.
4. Send `سول قوصي رش`; verify native automatic/burst mode and `physical=Head damage-parts=Head/Neck alternating`; fire a short burst and check successive hit body parts alternate Head/Neck.
5. Confirm the player and non-Sol weapons remain unchanged. Record weapon full type, ammunition, hit count, hit part, health before/after, and whether the zombie died.
6. Repeat a requested mode change and one weapon without an automatic/single mode. A refusal must be explicit; do not infer success from Sol's conversational reply.

## Implementation and verification

- Model card and generated `DOCS/SOL_MODEL_CARD.md` updated; card size 4590/4600. `card_check.py --write-doc`: PASS, 0 failures, 1 pre-existing warning about other game actions missing examples. `test_s82_route_eval.py --as-is 05_TOOLS/sol_mind`: ALL PASS.
- Java bridge test: 14 passed, including single always Head and burst Head/Neck alternation. Candidate built at `07_TEST/SOL_LAB/_pending_refuel/build_s114_fire_modes/SolCombined.jar`, SHA256 `d62f3e546176e71a104e3e95815f771d569dd20e2afebdf8b2747b6b91428f79`.
- Candidate static checks: linkcheck 12,033 references/0 mismatches; patch access 93/0. Before s114 was prepared, the s113 head-only candidate passed the launch check-only gate and was installed in LAB. It is not the final s114 candidate.
- Launch attempt crossed the previous Java loopback initialization failure. The console reached `Waiting for Java mods approval…`; the launcher session has not returned and no in-world firing evidence has been recorded. Do not replace the JAR while that process is still alive. After it exits, take a new LAB-only backup, install s114 candidate, verify SHA, run launcher `-CheckOnly`, and launch again.

## Decision

Stage s114 in LAB only after the current Java approval/startup process has ended. Keep the issue open until live single-shot and burst hit evidence is recorded. Do not promote to MAIN, release, Steam, or GitHub before that acceptance.
