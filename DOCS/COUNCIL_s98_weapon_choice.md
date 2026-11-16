# Council note s98: Sol never fires; weapon choice (2026-11-11)

## What went wrong
From 11:18 to 11:36 Sol aimed the G28 in her hands but never fired. She only stomped and shoved. "Carry this weapon" on the M4A1 showed "Could not equip item: retry_exhausted".

1. **EFZ (confirmed in code and log).** This M4A1's assembly is broken: two installed parts share one tree path (`duplicatePath`). Setting it in a hand fires OnEquipPrimary. EFZ's `TW/Runtime.lua` `R.update` then calls `R.refresh`, which writes `md.TW.ready=false` and clears both hands (lines 451-476 and 1062-1064). On later updates, line 1062 clears it again. The broken M4A1 cannot stay in anyone's hands, the player's included. EFZ's own Assembly menu still shows it as "Ready", because `C.stats` does not check for duplicates.
   - Log, 11:18:05.601 and .626, both in frame f:3851: the TW notice and the first `equip_rejected`.
   - Log, 00:22:57, frame f:16: the TW notice and "actor initialization failed: primary hand item could not be equipped". The M4A1 was her saved main weapon.
2. **LF retry ledger (confirmed in code).** After 4 failures, `SCActionSupervisor` marks `equip_weapon` on that weapon as exhausted with no expiry. Every later begin returns `retry_exhausted`, for combat and for the player's order alike.
3. **LF combat.** `SCCombat.execute` dropped the reason and logged `equip_rejected`. The next pulse picked the same M4A1, for ever.
   - Inference: the M4A1 carries LF's own preference marker `SC_ManualEquipFor` from an earlier pick. `chooseWeapon` returns a marked weapon first whenever it counts as usable.
   - Nothing preferred the weapon already in her hands.

## Switches (both default on in SolFixes_LAB.txt; off = old behaviour)

### combat_equip_fallback
- If an equip is refused, the log gives the real reason and the EFZ problem, including the duplicated paths.
- The refused weapon is blocked for 60 s.
- She uses the usable weapon in her hands: she shoots, reloads it if it is empty and there are mags, or unjams it if jammed.
- With nothing usable in her hands, the next pulse picks the next usable weapon, and melee comes last.
- An EFZ weapon with `md.TW.ready == false` is not usable.
- A usable gun in her hands is kept: no swap mid-fight.
- An explicit equip order skips the retry ledger, and a successful one clears it.
- An exhausted `equip_weapon` record expires after 3 minutes. This applies to equip only; other actions are unchanged.

### preferred_weapon
- "Carry this weapon" makes the weapon her preferred one, even when the equip fails. It uses LF's own marker; no new command was added.
- Combat keeps the held or preferred weapon while it can fire. She switches only if it is empty with no ammo, broken, or refused.
- When she switches, she says why in plain Shami, once. Example: "الـM4A1 فيها مشكلة بالقطع، رح ضل عالـG28".
- She also says it instead of the technical halo.
- The preference changes only when he picks another weapon. A new Sol after death has a new id, so the preference is gone.

## Open questions for the council
- Keeping the held gun at close range means she no longer swaps to melee at under 2.2 tiles if a gun is in her hands. Shove and stomp still work. Is that what we want?
- Should the 3-minute expiry of exhausted retries cover all actions? The same bug was already fixed for boarding with `retry_reset`.
- EFZ repair: `TWRuntime.applyTree(weapon, R.read(weapon))` would rebuild the assembly. It drops the duplicate part, empties the magazine and unchambers the round. This is not automated; it is only flagged in the log. The manual fix is EFZ Assembly menu → Remove on the duplicated slot.

## Files and tests
- Staged in `07_TEST/SOL_LAB/_pending_refuel`: `SolCombatEquipFallback.lua`, `apply_s98_combat_equip_fallback.py` and `test_s98_combat_equip_fallback.py` (52/52 offline).
- Install with the game closed. A restart is needed: there is a new Lua file, and SCCombat, SCActionSupervisor and SCUIBridge are patched.
