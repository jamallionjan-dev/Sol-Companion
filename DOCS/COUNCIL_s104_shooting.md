# Council note s104: she sprays a magazine and kills nothing (2026-11-11)

## Root cause, verified
Sol fires her EFZ Colt M4A1 on full auto at the engine's own cadence. LF never makes her wait for the engine's aim. LF also never limits how far away she shoots.
- **Full auto, no recoil gate.** The M4A1 script has `FireMode = Auto` (TW_Items.txt:12718-12719, Auto/Single). B42 `IsoGameCharacter.getFireMode()` returns the primary weapon's mode. `CombatManager.calculateAttackVars` (bytecode 745-777) sets a recoil delay for a ranged attack only when the mode is not "Auto". LF's only cadence brake is `combatReadiness` (recoil > 0, SCNativeActions.lua:3155-3163), so it never holds her.
- **Fast hits, then a dry gun.** Her hits came 72-114 ms apart: 13:09:43.060, .155 and .269. LF's own aim lasts at least 220 ms (SCCombat.lua:3257-3264), so these came faster than LF can fire. The 8 FPZombiesHD hits between 13:09:43 and 13:09:48 were hers. At 13:09:58 she reports `weapon=none`: the magazine was empty.
- **LF's aim does not match the engine's.** LF's aim is wall time, 220-1800 ms (`prepareRangedShot`, SCCombat.lua:3239-3283). The engine's hit chance subtracts `getAimDelayPenalty(getAimingDelay())` (`CombatManager.calculateHitChanceData`).
- **Range is not gated.** LF offers `shoot` at any visible distance and scores far shots higher: `54 + min(weapon.range, d) * 2` (SCCombat.lua:2672-2681). Here `weapon.range` is `getMaxRange()` = 60 (SCCombat.lua:872; TW_Items.txt:12705). The final firearm gate has no range check (`nativeAttackRange` returns true, SCNativeActions.lua:340).

## Evidence
### The live log
Log: logs_2026-11-11_12-26/2026-11-11_12-24_DebugLog.txt.
- **13:09:41.375:** `SolCombatEquipFallback preferred weapon: Colt M4A1`.
- **13:09:42.166:** `combat-engage outcome=attacking weapon=EscapeFromZomboidFirearms.M4A1 actions=1`.
- **13:09:43.060 - 13:09:48.788:** 8 hits from `FPZombiesHD hit: weapon=M4A1`: 1 Head, 4 Torso_Upper, 3 Torso_Lower. No kill was reported.
- **13:09:58.796:** `weapon=none`, so the magazine was spent. `safety-hold threats=2 nearest=6.2`.

### The "[TW-SHOT] baseline shot: collision:isometric-view" lines are Jamal's shots, not hers
- EFZ `ShotOwner.given()` counts a shot only if `ourWeapon()` holds, which requires `IsoPlayer.isLocalPlayer()` (ShotOwner.java:1745-1748, 1781-1790).
- LF's companion overrides `isLocalPlayer()` to false outside two callback contexts (SCNativeCompanion bytecode).
- The counter went from givenShots=5 (13:09:05) to givenShots=6 (13:09:56): Jamal fired exactly one shot in between.
- EFZ never owns an NPC shot (`not-local-player-zero`, ShotOwner.java:1712). Her rounds are vanilla CombatManager shots.

### Her Aiming level is 10
SolWorld_Snapshot.txt lists `"Aiming":10` for the actor holding the M4A1. Her base to-hit is therefore high: `HitChance 50 + AimingPerkHitChanceModifier 4 x 10` (TW_Items.txt:12709, 12658), capped at MAXIMUM_START 95.

### Engine facts (javap, projectzomboid.jar 42.22.2)
- **Aim delay.**
  - `resetAimingDelay`: when she is not aiming, aimingDelay = the weapon's AimingTime (40 for the M4A1, TW_Items.txt:12710).
  - `updateAimingDelay`: while she aims and recoilDelay <= 0, aimingDelay -= 0.625 x mult x (1 + 0.05 x Aiming).
  - LF's bridge runs it for the companion: `SCNativeCompanion.updateCompanionAimingDelay` reflects on `updateAimingDelay`.
  - After every shot, `CombatManager.setAimingDelay` adds RecoilDelay x 0.25 + AimingTime x 0.05.
- **Range.** `getDistanceModifier`: past the weapon's MaxSightRange (10), each tile costs -(d-10) x (4 + 0.3 x (d-10)). At 22 tiles that is about -91, which leaves the 5% floor. Inside the band there is a bonus of up to +15.
- **Movement.** `getMovePenalty` uses `getBeenMovingFor()`, reduced by (Aiming + Nimble) / 40. `beenMovingFor` decays only 0.625 x mult per tick. `holdCombatPosition` (SCNativeActions.lua:3130-3139) stops her path, but the first shots still carry the penalty.
- **Damage.** Firearm damage is a uniform MinDamage..MaxDamage = 1-1.6 (`getDamage`, no perk factor for ranged). A head hit is split x3 (HEAD_HIT_DAMAGE_SPLIT_MODIFIER).

### Shots fired from the Sol bridge
- **The shot sequence.** `attack()` runs `holdCombatPosition`, `faceLocationF`, `setCompanionAimTarget`, `setIsAiming(true)`, `setAttackType(SHOT)`, then `DoAttack(0)`. All of this happens in the same pulse (SCNativeActions.lua:3177-3403).
- **Movement at the shot.** She is stopped at the shot. LF's retreat cover fire is a single shot during a retreat, at up to `weapon.range` (SCCombat.lua:3658-3672).

## Inference (not verified)
- **Why 8 hits did not kill.**
  - The hits may have been spread over two zombies (threats=2 at 13:09:58).
  - The torso hits, 1-1.6 damage each, may not have been enough against this sandbox's zombie toughness. The zombie's health is not in the log.
  - The single Head hit not killing points to a different zombie, or to toughness.
- **The shooting distance is not logged.** `nearest=none` appears on every `attacking` line. Range is a likely cause, not a proven one.
- **The replay model** (test, Aiming 10) shows the cadence is the main loss: about 45 rounds in 6 s. With Aiming 10 the aim delay settles fast, so for her the cadence and range matter more than the aim delay.
- **Head aim is not available to an NPC.** The body part comes from B42 ballistics. EFZ's bore-aligned shot is for the local player only. Head hits rise only through a settled aim, a closer range and crits (Aiming).

## Target choice
- **Downed zombies.** LF never offers `shoot` against a grounded target (`if weapon and not grounded`, SCCombat.lua:2644, 2664). Downed zombies are left to the finisher (melee or stomp).
- **Switching targets.** LF may switch target after its commit time (650-1000 ms, SCCombat.lua:3020-3060). In Auto, one trigger pull is several rounds, and they can land on a zombie that is already falling.

## How other NPC mods do it
- **ProjectSurvivors** (Workshop 3810955553) skips the engine's shot entirely (PS_Combat.lua `resolveShot`):
  - its own roll: `HitChance/100 + difficulty`;
  - x1.15 within 40% of the range, then dropping to x0.75 at the full range;
  - clamped 15-95%;
  - then `zombie:Hit(weapon, npc, damage, false, 1.0)`;
  - fixed fire stages.
- **Bandits and Superb Survivors** are not in the Workshop folder, so this is from memory and unverified:
  - **Bandits** rolls its own accuracy: a fixed shot cadence, single shots or short bursts per weapon, a stationary stance, then a direct hit.
  - **Superb Survivors** drives the vanilla aim and attack and is known for poor accuracy. It compensates with NPC perk levels and a delay between shots.
- **Our choice:** keep the engine's shot (FPZombiesHD, EFZ ballistics, sound and XP all stay native). Fix only the discipline around it.

## Fix: switch `shooting_discipline` (SolShootDiscipline.lua). Off means LF as before.
- **Single shot.** On her first gated shot the weapon is set to Single (or Semi) if it offers one. Gunworks then re-applies its stat layers, so EFZ's RecoilDelay comes back.
- **Aim gate.** This runs after LF's own aim. She fires only when all of these hold:
  - she is not moving and `getBeenMovingFor() <= 6`;
  - `getAimingDelay() <= 15%` of AimingTime;
  - at least 300 ms have passed.
  - If the aim never settles, she fires at 2500 ms and logs it. With an immediate threat elsewhere, the limit is 600 ms. At point blank (3 tiles or less) she fires at once.
- **Range.** A `shoot` past MaxSightRange + 2 (12 tiles for the M4A1) becomes `hold_range`: she stands, aims and waits. A zombie within 3 tiles of Jamal, or one that is attacking, is still shot. Retreat cover fire also stops at that range.
- **Per zombie.** At most 5 aimed shots per zombie, until it comes 2 tiles nearer. Never a whole magazine into one zombie.
- **Short bursts.** When 3 or more zombies are within 5 tiles, she gets 3 quicker shots: the aim is half settled and the minimum wait is 120 ms. Then a full settle.
- **Reserve.** With no loaded spare magazine, she keeps the one in the gun for zombies within 5 tiles, at Jamal, or attacking. The count uses SolMagFill's lookup, else `getAllTypeRecurse(getMagazineType())`.
- **Tactical reload.** At 25% of the magazine or less, with a loaded spare and no zombie within 6 tiles. It uses vanilla `BeginAutomaticReload`, which ejects the current magazine and inserts the best one.
- **Target order.** With a firearm in her hands, zombies nearer Jamal score higher (+3 per tile under 10). Zombies past the effective range score lower.

## Staged (07_TEST/SOL_LAB/_pending_refuel)
- `SolShootDiscipline.lua`
- `apply_s104_shooting_discipline.py`: idempotent. It edits SCCombat.lua (5 hooks marked `s104`), SolAuthority.A.FIXES and SolFixes_LAB.txt.
- `test_s104_shooting_discipline.py`: 51 PASS, including the tonumber and jarcall gates.

## Risks
- **She may stand too long.** A zombie that stays beyond 12 tiles, or one that took 5 shots and does not come nearer, keeps her standing and aiming while combat lasts. Watch for her not following Jamal.
- **Fire mode stays changed.** The fire mode is set on the weapon itself. If Jamal takes the gun back, it is on Single.
- **Timeout fallback.** If the bridge stops updating aimingDelay, every shot waits 2.5 s. Watch for the log line "without a settled aim".
- **Restart needed.** It is Lua only, so a restart (or a Lua reload) is needed after install. Install with the game closed.

## Live check
- **Log lines to look for:**
  - `[SolShootDiscipline] fire mode Auto -> Single`;
  - one `shot aimed n=.. d=.. aimingDelay=..` line per shot, with d at 12 or less and aimingDelay at 6 or less;
  - `hold: out of effective range` for far zombies.
- **Expected behaviour:** no more than 5 shots per zombie between approaches, and no magazine-in-5-seconds dumps.

## s104b (live 14:55-14:57, DebugLog 2026-11-11_14-48)

### What the live run showed
- Accuracy was fine.
- Zombies took 5 or more hits.
- The cap of 5 shots held fire at a zombie she was hitting.
- The log said "RealAuto -> Single" every 0.5 s.

### Damage per hit: nothing in LF or the bridge lowers her damage
- **LF and Sol Lua.** The SC*/Sol* Lua has no damage scaling for zombie hits. `SCFactions.onWeaponHitCharacter` only reads the hit.
- **The bridge (`SCNativeCompanion`).** It overrides `isLocalPlayer` and `IsoPlayer.Hit` (when she is hit), but nothing on her outgoing hits.
- **The engine.** The firearm damage path is the same for every shooter:
  - `getHitDamage` (no panic, stress, endurance or tired factor for ranged);
  - `applyRangeHitLocationDamage`: head x3 (HEAD_HIT_DAMAGE_SPLIT); arm or leg x0.05; clothing defense through `calculateTotalDefense`;
  - `processHitDamage`: x1.5 (`NON_PLAYER_RECEIVED`), x(0.3 + 0.1 x `getWeaponLevel`), x1.5 by facing, crit x2, and x0.5 for a two-hander held in one hand;
  - `hitConsequences` then `applyDamage`.
- **Weapon level is 0 for firearms.** `getWeaponLevel` only knows the melee categories, so the multiplier is 0.3 for both Jamal and Sol.
- **Only three factors depend on the shooter:**
  - a two-hander held in one hand (x0.5): `SolTwoHandGrip` re-grips every 2 s;
  - crit chance (Aiming; she has 10);
  - facing.
- **RealLimbs** (`readHit`) touches health only for its `headshotKills` option, which is off in this save.

### The part shown in FPZombiesHD is not where the round struck
- FPZombiesHD's "part" comes from `OnHitZombie`.
- `IsoZombie.Hit` raises that event with a random Torso_Upper / Torso_Lower, or Head on a critical hit (bytecode 21-70).
- So "Head" in those lines means a crit, not a headshot.

### What a kill takes
**Zombie health**
- Sandbox Toughness 4 (Random): health is U(0.5, 3.5) + U(0, 0.3) (`IsoZombie.resetForReuse`). The mean is 2.15 and the maximum 3.8.
- DeadWorksZeds / FPZombiesHD change visuals only: wounds and crawler variants. They never touch health.

**Damage per 5.56 hit (M4A1 MinDamage 1.0, MaxDamage 1.6)**

| Hit | Damage |
|---|---|
| Torso, no armour, front | 1.0-1.6 x 1.5 x 0.3 = 0.45-0.72 (mean 0.585) |
| Torso, with the x1.5 facing bonus | mean 0.88 |
| Ballistic head hit | x3 |
| Critical hit | x2 |
| Zombie clothing | lowers it further (`ZombiesArmorFactor` 2.0, `ZombiesMaxDefense` 85) |

**Hits and rounds per kill**
- **Torso hits:** about 4 on average and up to 7 with no armour; about 3, up to 5, with the facing bonus. More when the zombie wears thick clothing.
- **Head hits:** 1-3.
- **Rounds:** at her hit rate (about 85%), about 4-5 rounds per kill on average and up to about 8. 5 hits without a kill is normal for a tough zombie.

### s104b changes (SolShootDiscipline 0.2.0, same switch)
- **Cap on misses, not hits.**
  - A miss is a shot with no `OnHitZombie` naming her for that zombie within 400 ms.
  - 3 misses in a row, or 12 rounds, hold her until the zombie is 2 tiles nearer.
  - Hits keep her firing.
- **RealSingle.** A Gunworks gun gets "RealSingle". EFZ `TW_FireModeSwitch.lua:47-55`, on `OnWeaponSwing`, turns a standard "Single" back to the last Gunworks mode it saw. The mode is set only just before a shot and logged once per weapon.
- **Downed zombies are never shot.** This holds even at point blank. LF's finisher (a stomp with a gun in hand) takes them.
- **Kill ledger.** A read-only line per dead zombie:
  `kill: <gun> hits sol=a jamal=b solRounds=n health-before-each-hit=s2.6>j2.0c>...`
  It compares her damage per hit with his, from live data.
