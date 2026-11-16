# s116 — Sol single-head and burst chest/chest/head hit routing

Date: 2026-11-12. Scope: SOL_LAB only. Runtime acceptance is pending.

## Engineer — evidence and smallest change

- The previous s114 burst design alternated Head/Neck. That does not match Jamal's final requested pattern: two chest hits followed by one head hit.
- On the installed Build 42.22.2 game jar, `RagdollBodyPart` contains `BODYPART_SPINE` and `BODYPART_HEAD`, but no chest or neck bone. Local `javap -c -p zombie.core.physics.RagdollBodyPart` shows Spine maps to a randomized `Torso_Upper` or `Torso_Lower` damage index by default. `BodyPartType` separately provides `Torso_Upper` and `Head`.
- s116 builds one hit plan inside `CombatManager.processHit`, for the exact `SCNativeCompanion` attacker, ranged weapons, and an `IsoZombie` target. Single mode chooses physical Head + damage Head. Burst mode cycles Spine/Torso_Upper, Spine/Torso_Upper, Head/Head. The selected plan is shared by the cached-ballistics and hit-reaction fallback hooks and the nested zombie damage-part callback.
- The game's native weapon, ammunition, hit chance, critical state, and damage formula remain in use. Missed shots do not enter `processHit`, so the burst cadence advances per resolved zombie hit, not per trigger pull. The fire-mode log now states this actual pattern.

## Devil's advocate — ways this can still fail

- This does not steer Sol's aim vector or guarantee a hit. It selects the body region for a projectile that already resolved against a zombie. Misses, obstruction, spread, weapon behavior, and zombie state can still prevent damage.
- A Spine selection is the engine's physical torso region, not a separately modeled chest bone. The damage callback is explicitly pinned to `Torso_Upper` to avoid the engine's default random upper/lower torso mapping.
- Burst cadence counts successful hit-resolution callbacks. If the weapon fires rounds that miss, the displayed shot sequence can differ from the pattern of trigger pulls; logs are therefore interpreted as hit sequence evidence.
- Another Java mod may advise the same engine methods. The live startup patch report and s116 per-hit log must confirm these hooks are active on this Build 42.22.2 runtime.
- Exact damage parity with the player's same weapon/ammo is not promised. This change preserves the native formula; the runtime comparison must include weapon full type, exact ammunition, damage delta, and ammo decrement.

## Strategist — scope and acceptance

- Keep `sol_headshots` enabled only in SOL_LAB. Do not change the Steam profile, MAIN, release, Workshop files, or user saves.
- On the isolated save `2026-11-10_02-39-13`, first verify Sol spawns and the changed Java patch is approved/registered. Then test a close, stationary zombie with `سول قوصي طلقة طلقة`; require successful Sol hits to log `selectedPart=HEAD damagePart=Head`, with positive health loss and ammo decrement.
- Switch to `سول قوصي رش`; use a durable zombie and record at least three successful hits. Require the hit logs in order: `CHEST/Torso_Upper`, `CHEST/Torso_Upper`, `HEAD/Head`, repeating. Check `SolDamageProbe` health deltas and ammo decrement. Compare the player using the same weapon and ammunition separately.
- Any non-Sol or melee hit changing parts, missing patch registration, or Sol hit logging a pattern mismatch is a fail. Restore the timestamped LAB backup or turn off `sol_headshots`; do not promote on offline tests alone.

## Implementation and static verification

- Installed in SOL_LAB after backup `07_TEST/SOL_LAB/_backup/20261112_before_s116_chest_head`.
- Installed jar SHA256: `c8bb708f516bae02a285a5b1ea0560c1af3401d5ead1cfb786a072b10b6ae254`.
- Java sequence/scope test: 21 passed. Installer replay/idempotency test: 12 passed. Linkcheck: 12,045 references, 0 mismatches. Patch-access: 93 patches, 0 problems. `tonumber_check`: pass. `jarcall_check`: 0 failures, 20 existing warnings. `launch_lab.ps1 -CheckOnly`: exit 0; card 4590/4600 (one warning).
- These are offline/static checks only. No in-world success has been established yet. Release, Steam, and MAIN remain untouched.
