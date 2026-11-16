# Council note s99: she loads her own magazines; LF's blind weapon list (2026-11-11)

## What went wrong (11:59-12:05)
- **"Carry this weapon" on the G28** answered `no_usable_weapon (empty)` again and again (DebugLog `2026-11-11_11-53`, lines 17303-17669). Turning `combat_equip_fallback` off at 12:02:19 changed nothing: the refusal is LF's own.
- **She fought with a wrench, not her katana**, and fired no gun: "`weapon=Wrench carried=1 usable=1`" (lines 17488, 17502) and "`combat-engage ... weapon=Base.Wrench band=0.46-1.18`" (17513 onward, one zombie each time).

## Causes (from the code; the inventory size is from the live report)
1. **LF's weapon list is capped.**
   - `SCCombat.inventoryWeapons` takes her weapons from `SC.InventoryIndex`, or from `U.inventoryItemsDeep(inventory, 240)` (`SCCombat.lua:1117-1121`).
   - That walk stops at 240 items, 180 of them from the root container (`SCGameplayUtil.lua:1246-1286`, `SCInventoryIndex.lua:64-113`).
   - She carries about 500 loose 7.62x51 rounds, and each round is one item. The weapons after them are never seen, so "carried=1" is only the wrench in her hand.
   - The katana and the G28 were hers: his carry orders on them reached `equipExactWeapon`, which refuses anything outside her containers (`SCUIBridge.lua:370-373`).
   - The offline replay with LF's own walk gives exactly carried=1 and the wrench.
2. **s98 kept the held weapon, whatever it was.** `SolCombatEquipFallback.choose` returns any usable weapon in her hands while `preferred_weapon` is on (line 212 in 0.2.0). That kept the wrench.
   - At 12:04:26 his carry order put the katana in her hands (line 17656, not refused). From then on the same rule kept the katana.
   - So the 12:03 vs 12:05 difference is only what was in her hands. LF never listed the katana either time.
   - Limits of the evidence:
     - The newest DebugLog ends at 12:04:55, so 12:05 itself is not in it.
     - No equip line shows how the wrench got into her hand before 12:00:58.
     - Whether the katana was attached or in a bag is not logged.
3. **"Empty" is undercounted for EFZ guns.**
   - `weaponRecord` uses `getCurrentAmmoCount` only (`SCCombat.lua:867`). The chambered round is not counted, but B42 racking moves one round out of that count into the chamber (`ISRackFirearm.lua:62-64`). EFZ uses the same vanilla fields (`TW/Runtime.lua:747-751, 823-831`).
   - `hasReloadAmmo` (`SCCombat.lua:1146-1191`) looks only for magazines of `gun:getMagazineType()`, and only inside the truncated index. A magazine he loaded by hand and left in her bag is invisible. EFZ/Gunworks accept a whole list of magazine types (`Magazine.lua:154`).
   - Inference, not verified: the loose-round test compares `tostring(getAmmoType())` with item types. In B42 that is an `AmmoType` object (vanilla calls `:getItemKey()`), so loose rounds probably never match.
4. **Nothing ever loads a magazine on her.** Loose rounds only enter a magazine inside the game's reload actions.

## Switches (all default on in SolFixes_LAB.txt; off = old behaviour)
### mag_fill (`SolMagFill.lua`)
- **Rounds she can fire** = rounds in the magazine + the chambered round.
- **Reload ready** = a compatible magazine (Gunworks profile) holds rounds. It is found with the container's own recursive lookup, so the scan cap does not apply. Loose rounds alone are not a reload in a fight.
- **His order on a gun she can load** is accepted.
- **When she fills.** She must be idle, out of a car, and have no living zombie within 6 tiles on her floor. She then fills empty or partial magazines with loose rounds of a matching calibre:
  - the API: Gunworks `Magazine.reloadMagazine` with the round kind from `Ammo.GetAutomaticReloadAmmoType`;
  - the order: a full magazine goes in as it is; otherwise the fullest magazine she can fill is filled first;
  - with the gun in her hands: `ISInsertMagazine` (it queues its own rack), and `ISRackFirearm` if the chamber is still empty;
  - an empty magazine stuck in the gun is ejected, filled and put back.
- **Which guns:** the gun in her hands; a gun asked for (an "empty" refusal or his order); her preferred gun.
- **Safety:** a zombie within 6 tiles stops her own actions only. s98's fallback stands: another weapon, or melee.
- **What she says**, plain Arabic, once a minute per gun: "عم عبّي مخزن الـG28".
### weapon_scan (`SolWeaponPick.lua`)
- `inventoryWeapons` also takes the weapons the capped walk missed (`getAllCategoryRecurse("Weapon")`).
- It logs once what LF missed and how many items the root holds. That log line confirms cause 1 in play.
### melee_choice (`SolWeaponPick.lua` + `SolCombatEquipFallback` 0.3.0)
- **Melee score** = damage x condition, plus a bonus by kind: long blade +20, axe/blunt +14, spear +12, small blade +4. A tool weapon gets -15.
- **Her melee weapon:**
  - the one he picked with "carry this weapon" on a melee weapon (marker `SolMeleeFor`);
  - otherwise her katana.
  - While it is usable, other melee weapons do not compete with it.
- **Firearm vs melee** stays LF's call (distance, pressure).
- **No holding on:** a melee weapon is no longer kept just because it is in her hands.

## Open questions for the council
1. **Timed actions on the NPC.** `ISLoadBulletsInMagazine` and `ISInsertMagazine` are driven by animation events. LF already runs `BeginAutomaticReload` on her, which uses the same insert, so it should work. EFZ's magazine-loading display (`TW_MagazineLoading.lua:103-144`) will also run on her. A runtime check is needed.
2. **Loose rounds stop counting as a reload for magazine guns.** In a fight with no loaded magazine she switches weapons, and the fill waits until it is safe. Is that the rule we want?
3. **One preferred marker.** LF keeps one `SC_ManualEquipFor`: picking the katana un-prefers the G28. Her melee choice is kept separately (`SolMeleeFor`), but the gun preference still moves with every pick.
4. **The 240-item cap** still applies elsewhere in LF: food, medical, tools. The 500 loose rounds will hide other things too. Box them, or raise `combatInventoryScanLimit`?

## Files and tests
- **Staged** in `07_TEST/SOL_LAB/_pending_refuel`: `SolMagFill.lua`, `SolWeaponPick.lua`, `SolCombatEquipFallback.lua` (0.3.0), `apply_s99_mag_fill.py` and `test_s99_mag_fill.py`. Offline: 76/76.
- **s98 test with the new SolCombatEquipFallback:** 51/52. The one failure is its installer count, because s98 is already in the lab files.
- **Install** with the game closed. A restart is needed: there are new Lua files, and SCCombat is patched.
