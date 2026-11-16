# s117 — Share Sol's shot plan across native hit callbacks

Date: 2026-11-12. Scope: isolated SOL_LAB only. Runtime acceptance is pending.

## Engineer — evidence and change

- Build 42.22.2's `IsoZombie.Hit` selects a damage body part before its downstream `CombatManager.processHit` call. Sol's s116 hooks each created a shot plan independently: `ZombieHitScope` created the damage plan, then `CombatHitScope` advanced the burst sequence again. The physical-part hook could therefore use a different plan from the damage callback for the same shot.
- s117 shares the plan only when attacker and exact weapon object identities match across those two callbacks. The first hook creates the plan; the nested hook reuses it. If callbacks do not match, the code falls back to a new scoped plan rather than borrowing another actor's shot.
- The plan remains Sol-only, ranged-only, and zombie-only for the physical hit. Single mode routes to Head; burst mode routes Chest/Chest/Head using Spine physically and `Torso_Upper`/`Torso_Upper`/`Head` for damage selection.
- Adds one `[SolHeadshot] damagePart=...` trace when the damage callback consumes the planned part. This is selection evidence; `SolDamageProbe` health delta remains the evidence of actual damage.
- Does not change the global player identity, EFZ files, weapon damage formula, ammunition, release, Steam profile, MAIN, or saves. EFZ's `ShotOwner` remains local-player-only, so this patch preserves the engine's native NPC hit and damage path; it does not claim to route Sol's shot through EFZ's player-camera ballistic owner.

## Devil's advocate — what may still fail

- Sharing by Java object identity assumes the game passes the same weapon object into both hooks. If not, the new trace and sequence can expose the mismatch; runtime logs must be checked.
- The patch aligns part selection, not aim, spread, obstruction, critical chance, or guaranteed kills. Native hit chance and damage remain authoritative.
- A selected `Head` or `Torso_Upper` log alone is not proof of health loss. Require the read-only damage probe to show the body part and a positive health delta.
- Another Java patch can affect the same game methods. Startup patch registration and runtime traces remain required.

## Strategist — install/test gate

- Do not touch the Steam profile, release, Workshop assets, or existing saves. The only installation destination is `07_TEST/SOL_LAB/profile/Zomboid/mods/Sol_LAB/42/media/java/SolCombined.jar`.
- Before installation, preserve the s116 JAR under `07_TEST/SOL_LAB/_backup/20261112_before_s117_sol_hitplan` and verify its known hash.
- In the existing isolated save `2026-11-10_02-39-13`, test close stationary zombies with the same gun and ammunition:
  1. `سول قوصي طلقة طلقة`: verify each successful shot logs `damagePart=Head`, `SolDamageProbe body=Head`, positive damage, and ammo decrement.
  2. `سول قوصي رش`: verify successful hit order Chest/Chest/Head, actual `Torso_Upper`/`Head` probe parts, positive damage, and ammo decrement.
  3. Verify player hits, Sol melee, and non-zombie targets retain their existing behavior.
- Roll back by restoring the timestamped backup if patch registration fails or the runtime evidence diverges.

## Build and offline checks

- Candidate: `07_TEST/SOL_LAB/_pending_refuel/build_s117_sol_hitplan_candidate/SolCombined.jar`.
- 25 Java checks passed, including same-actor/same-weapon plan reuse and rejection of cross-actor, cross-weapon, and missing-plan reuse.
- Linkcheck: 12,052 references, 0 mismatches. Patch-access check: 93 patches, 0 problems.
- Candidate SHA-256: `bacce36b672718cc450b20ea3970094f0854e93df75875e28de11c743e1285fc`.
- Candidate has not been installed or accepted in-world yet. Installer refuses while the LAB log is fresh or Java/Project Zomboid processes are present.
