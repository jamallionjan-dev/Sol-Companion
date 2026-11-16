# s113 — Sol firearm physical head-hit selection (SOL_LAB only)

Date: 2026-11-12. Scope: make successful ranged hits from Sol select the native head body part while preserving the game's firearm, ammunition, and damage path. No Steam, Workshop, MAIN, or release files are changed.

## Engineer

- The first LAB patch changed the body-part event passed through `IsoZombie.Hit`. That is not enough to prove the physical projectile's target part was changed before damage calculation.
- Build 42.22.2 selects a camera-targeted projectile's physical part in `CombatManager.processHit` through `BallisticsController.getCachedTargetedBodyPart`; non-camera hits use `CombatManager.getBodyPart(HitReaction, ShotDirection)`. The native damage path then applies the location multiplier and the weapon/ammunition damage.
- The prepared physical candidate scopes `CombatManager.processHit` to the exact `SCNativeCompanion` actor, ranged weapon, and matching target. It redirects those target-part selection results to `RagdollBodyPart.BODYPART_HEAD` before the native damage calculation. It retains the event-part hook for consistent event reporting.
- It does not set critical state, edit damage, edit weapon/ammo, skip the native hit method, or consume/duplicate a shot. Native weapon/ammunition and head-location damage calculations remain in the game's own hit path.
- Lua polls the existing `SolAuthority` switch once per second; there is no per-frame world or inventory work.

## Live evidence and comparison (2026-11-12)

- Player reference: the same weapon full type `EscapeFromZomboidFirearms.M4A1` produced `FPZombiesHD part=Head` and `SolDamageProbe body=Head`; a recorded head hit reduced health `2.79863 -> 0` and killed the zombie. Another player's M4A1 head hit recorded `0.59292` damage. This validates the observed `Head` label and native damage path for the player's weapon.
- Sol on the currently loaded intermediate JAR: M4A1 event records included `Head` with one health delta `0.52827` and several `0.00000` deltas. The log labels alone do not establish that the physical part was selected before the engine calculated damage. Exact ammunition identity was not logged, so numeric damage parity is not yet proven.
- The current LAB JAR is `A202B3DC0D34E9B374CDC79FC685C303DDAD2FF0D996ACDB3DFA39FFABDD8ED3`; it is the intermediate artifact. The prepared physical candidate is `07_TEST/SOL_LAB/_pending_refuel/build_s113_physical/SolCombined.jar`, SHA256 `9192140883CE630A304971D9107B8E80CD4C6C8AEC251FB172FF4D89CDFE07B0`. It is not installed.
- Runtime log continued changing through 13:33:47 while the test session was open. Do not replace the loaded LAB JAR until the game exits. After installation and relaunch, require `[SolHeadshot] physicalPart=HEAD` for Sol's actual CombatManager path and compare matched M4A1 ammunition, damage, and ammo decrement against the player.

## Devil's advocate

- `BodyPartType.FromIndex` is a shared method, so ZombieBuddy still adds a small advice call there. The one-shot thread-local check and disabled path must be measured in the live game. A global `Rand.NextBool` patch was explicitly rejected as a much hotter interception point.
- The call-site audit is for installed Build 42.22.2, not 42.21. Another mod could alter that bytecode or the native companion's runtime class. Startup patch logs alone are insufficient; the live `SolDamageProbe` part and damage must confirm the active path.
- Head location naturally changes the game's location-specific damage. This fix preserves the native formula; it does not promise that a head hit has the same numeric health delta as a torso hit. A first body-part event alone is not enough: record post-hit health and weapon name, and verify ammunition actually decreases.
- Any patch-link error, Sol hit logged with a non-head part after the corrected JAR is loaded, or unintended other-actor head override is a failure. Turn off `sol_headshots` or restore the timestamped LAB backup; never promote from static checks alone.

## Strategist

- Test sequence after deployment: startup/character spawn; one close standing zombie hit by Sol; repeat several successful hits; test another gun/ammo only after the matched M4A1 case. Inspect `[SolHeadshot]` physical selection, `[SolDamageProbe]` source/weapon/body/pre/post/damage, `FPZombiesHD part`, ammo identity, and ammo decrement. Compare the same weapon and ammunition against the player; do not use one hit's damage as a fixed target.
- Offline evidence for the physical candidate: Java predicate checks 10/10, source checks 16/16, Java linkcheck 12,024 references/0 mismatches, patch access 93/0 problems. Candidate build completed previously; a repeat build was safely refused because the candidate output directory already exists. The LAB launcher must pass check-only immediately before deployment.
- Install and launch only in `07_TEST/SOL_LAB`; MAIN, Steam profile, and release remain untouched. Candidate install and runtime acceptance are pending game exit and a fresh isolated launch. If ZombieBuddy requests approval for the changed Java mod, Jamal must approve it in-game himself.
