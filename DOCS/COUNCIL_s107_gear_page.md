# Council s107: the gear page (switch `gear_page`)

Jamal (2026-11-11): the gear tab "العتاد" is nearly empty. It shows the weapon as "-", ammo 88, load, health, four buttons, "أولوية السلاح" and "سياسة الحمل". Plan: `PLAN_gear_and_combat.md` Part 1, step 2 (`gear_page_v2`). The coordinator renamed the switch to `gear_page` and added these points:
- the real weapon in her hands;
- rounds in the magazine + chamber + spare magazines + loose rounds;
- the plan picker uses the chat ids and replaces "weapon priority";
- the gear sources are her bag, his bag (on his click), the car trunk and home storage;
- the rows are virtualised.

Staged (not installed):
- `_pending_refuel/SolGearPage.lua`
- `_pending_refuel/apply_s107_gear_page.py`
- `_pending_refuel/test_s107_gear_page.py` (106/106)

## Engineer: how it works
- **One new file, no LF or SolPages edit.**
  - At OnGameStart, `SolGearPage.lua` wraps SolPages' page class: `refresh`, `drawLoadoutCard` and `onMouseUp`. This is the same pattern as SolAddressBook.
  - With the switch on, the loadout tab draws Sol's page in place of the 236 px card. LF's remaining widgets (carry policy, vehicle) sit below it.
- **The "-" weapon.** LF's row value `equippedWeapon` is replaced by the item really in her hands: the primary hand, else the secondary hand (EFZ guns included).
- **Rounds** reuse earlier work:
  - in the gun: `SolMagFill.loadedRounds` (magazine + chambered, s99);
  - spare magazines: `SolMagFill.magazines` (Gunworks-compatible types);
  - loose rounds: `U.inventoryCount`, which calls `SolItemStacks.count` (s100), which calls the native `getCountTypeRecurse`. The round kinds are the gun's ammo type plus `SolMagFill.roundKind` for each of its magazines.
- **State:**
  - broken: condition 0;
  - jammed: `isJammed`;
  - parts: `SolCombatEquipFallback.whyUnusable` gives "parts" (EFZ `md.TW.ready == false`, s98);
  - empty: no rounds in the gun;
  - otherwise ready.
- **Buttons.** The page reuses the existing paths:
  - "use this one" and "wear": LF's `UIBridge.equipOnCompanion`, the same path as the inventory menu. It marks her preferred weapon (s98) and fills the gun if needed (s99).
  - "reload": `SolMagFill.orderFill`.
  - "set preferred": `SolCombatEquipFallback.markPreferred` for a gun, `SolWeaponPick.markMelee` for melee.
  - "give" (both ways): LF's `transferItemVerified`. Identical items move as one stack. The move needs LF's `validateNearbyActor`.
  - "take off": `removeWornItem(item)`, the 1-arg overload, the way LF itself releases clothing.
- **Fighting plan:**
  - The picker shows the 8 ids of `SolCombatPlans.ORDER`, with a one-line Arabic description each.
  - A pick runs `SolCombatPlans.run(id)` (the same code as the chat verb `sol_combat_plan`), and she confirms in a short plain line.
  - While `combat_plans` is on, LF's "weapon priority" selector and its section are removed, because a plan sets that knob. That leaves one setting. With `combat_plans` off, LF's selector stays.
- **Her bag:** `SolItemStacks.deep`, the cached grouped walk (500 rounds = 1 row "x500"). It is grouped into weapons / ammo and magazines / medical / food / tools / clothing / other. What she holds or wears is left out.
- **My bag:** read only after his click. It lists only what she can use:
  - weapons;
  - rounds and magazines of HER guns;
  - medical;
  - armour (clothing with bite, scratch or bullet defense).
- **Car and home:** rows from `SolInventory`'s last finished scan, with `where = vehicle / house`. It starts no new scan and is shown after his click.
  - Weapons, her calibres and medical only.
  - Read only, because the scan keeps counts, not item references.
- **Like me:**
  - Her worn items are compared with his by slot (protection x condition).
  - The weapon in his hands is compared with hers of the same kind (damage x condition).
  - A row appears only when his is clearly better. "Give her one" appears only when he has a spare of that item that he is not wearing.
- **Performance (Jamal: no stutter):**
  - Virtualised list: a binary search finds the first visible row, and only rows inside the 530 px window are drawn and get click areas. Offline, 600+ rows drew at most 24 per frame.
  - Signatures:
    - The data is rebuilt only when a signature changes: item count + contents weight of her inventory and of every bag the walk opened, her hands, the worn count, the plan, the `combat_plans` switch, his bag when shown, and the scan time.
    - The signatures are checked at most every 500 ms, with a 15 s backstop.
    - A shot fired rebuilds only the hands.
    - LF's quick-action availability is read at build time, not per frame.
  - No OnTick handler; nothing runs while the page is closed.
  - Cost goes to SolPerf as `gear_page`.
- **Java (javap 42.22.2):**
  - `WornItems.size/get(int)`, `WornItem.getItem/getLocation`;
  - `IsoGameCharacter.isEquipped/isEquippedClothing/removeWornItem` (InventoryItem);
  - `ItemContainer.getAllTypeRecurse(String)`, `getCountTypeRecurse(String)`;
  - `InventoryItem.getAmmoType` with `AmmoType.getItemKey`;
  - `Clothing.getBite/Scratch/BulletDefense`, `HandWeapon.isJammed/isRoundChambered/getMaxDamage`.
  - No call passes a boolean, and every overloaded call is picked by its argument count.

## Devil's Advocate: what breaks
- **The plan picker and LF's "weapon priority" could fight.** The selector is removed only while `combat_plans` is on, and the plan sets the knob. Checked offline in both states.
- **Giving 500 rounds is 500 Remove/AddItem calls in one click.** It is capped at 1000 and is a one-off, not per frame. Gifts of stackable items are NOT marked `SC_GivenByPlayer`: that would give each round its own data and break the s100 stacks. Weapons and clothing are still marked, and LF's `noteGift` still runs.
- **The car and home lists can be up to 2 minutes old** (SolInventory's auto scan). The page says it shows what she saw last time. Their rows have no take button, because the scan has no item references.
- **"Take off" bypasses a timed action.** It is LF's own direct path, the one its transfer hook uses. It is refused when she is not near him (`validateNearbyActor`).
- **Two forced refreshes in one millisecond** (a click right after a frame) would skip the filter if it were keyed on the build time. It is keyed on `force` as well; tested.
- **Switching off live:** the next frame restores SolPages' card and LF's widgets. There may be a one-frame overlap, which is cosmetic.
- **Not covered offline:**
  - the real glyph layout of long EFZ names (they are cut to fit with "..");
  - EFZ guns whose magazine is listed only by Gunworks profiles (`SolMagFill.magTypes` covers them; needs an in-game test);
  - the slot words for unusual body locations, which fall back to the game's location name.

## Strategist: order and MAIN
1. Install with the next grouped restart. It is independent of s104/s105/s106 in either order (it only adds `gear_page` to `A.FIXES`). It needs s98, s99, s100 and s105 installed, which they are in the lab.
2. Runtime test (Jamal):
   - open her gear tab with the G28 in her hands: the name, rounds in the gun / magazines / loose, and the state;
   - pick "شرسة" and then "ذكي": her line, and the `[SolCombatPlans] plan` log;
   - "أعطيني" on the bandages;
   - "اعرض" on his bag, then "أعطي سول" on .308 rounds;
   - take off a hat, then swap it;
   - scroll her full bag while watching SolPerf `gear_page` and fps.
3. MAIN only after a runtime PASS, and together with `combat_plans` (the picker needs it). With `combat_plans` off in MAIN, the page keeps LF's selector.
4. Not in this step: "unload", a "keep 1 reload" display, and taking items straight from the car or home (that would need item references in SolInventory).
