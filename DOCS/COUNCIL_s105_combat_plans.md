# Council note s105: fighting plans (`combat_plans`) (2026-11-11)

Step 1 of `PLAN_gear_and_combat.md`. Staged in `07_TEST\SOL_LAB\_pending_refuel\`. Not installed, not committed.

## What it is
He says one plan in his own words. The model maps it to one action, `sol_combat_plan`, with `option` = the plan id. The game then sets Living Fellows' own knobs through LF's own commands, the same commands the Loadout page issues: `Commands.issue` with `set_weapon_priority`, `set_combat_doctrine` and `set_hold_fire`. `combatMode` follows the doctrine through LF's `applyDoctrine` (SCCommands.lua:111-123). A few new rules sit on top. She confirms in her own words.

| Plan id | Arabic name | LF knobs (mode / doctrine / priority / hold fire) | New rule |
|---|---|---|---|
| `smart` (default) | ذكي | defensive / close_defense / best / off | Melee for 1-2 zombies. A firearm for 3+ zombies within 10 tiles of her, or for any zombie within 3 tiles of him. She goes back to melee 4 s after the group thins out. At rest she holds melee. |
| `normal` | عادي | defensive / close_defense / firearm or best / off | Firearm when his pick for her (s98 marker) is a gun, or when she has no pick and carries a gun. Otherwise best. |
| `fierce` | شرس | aggressive / weapons_free / firearm or best / off | Never engages a zombie more than 25 tiles from him, unless it is attacking her or holding an ally. |
| `support` | إسناد | defensive / ranged_support / firearm / off | Follow distance 5, LF's band behind him. His own follow distance comes back when he leaves the plan. |
| `careful` | حذر | **passive** / close_defense / best / off | LF has no command for the mode alone, so it is set on LF's state and persisted (`Commands.persist`). |
| `stealth` | تخفي | passive / stealth / quiet / off | She sneaks (move mode comes back on leaving). Melee, or a gun only when EFZ says it is silenced: `TW/Core C.stats(key, TWRuntime.read(w)).silenced`. An unsilenced gun never fires. |
| `avoid` | تجنّب | passive / stealth / best / off | LF's stealth doctrine (`passiveMayFight`, SCCombat.lua:2916): she engages only close threats. No new rule. |
| `hold` | لا تطلقي | defensive / close_defense / melee / **on** | Melee only. |

These rules hold under every plan:
- **She never fires across him.** No shot when he is within 1.2 tiles of her line of fire, 0.8 tiles or more along it, between her and the target. No shot when he is behind the target in the line (up to 15 tiles past it, 1.5 tiles off it). LF's own corridor is 0.8 tiles to the target only.
- **She retreats under 30% health.** The retreat action is set to 500, above every LF or s104 score. Before this, LF only added +35 under 30%.
- **The plan resets after her death.** The plan goes back to `smart`, and the next Sol gets smart's knobs. Death is detected two ways: `OnCharacterDeath` for her actor, and a new Sol id seen by the 2 s tick (the same rule as SolLife).

The plan is stored in ModData `Sol_CombatPlan` as { plan, id of the Sol it was set for, the follow distance and move mode to restore }. A reload keeps it.

## Engineer
- **New file `SolCombatPlans.lua`.** Its switch is `combat_plans`, read at call time.
- **Installer `apply_s105_combat_plans.py`.** It adds three SCCombat hooks, each a single line:
  1. **`Combat.update`**, after LF's weapon preference: `M.preference`. In smart it counts the scored targets (already computed, no new scan). In stealth it returns quiet, in hold melee.
  2. **The top of `chooseWeapon`**: `M.choose`. It runs before LF's manual-marker loop and s98's keep-held, because those would always return his gun. Within the wanted kind, his pick (s98 marker) comes first, then s99's preferred melee (katana), then the weapon in her hands, then the best score. With nothing of that kind usable it returns nil and LF, s98 and s99 decide as before.
  3. **The end of `actionUtilities`**: `M.shape` (retreat under 30%; stealth drops `shoot` with an unsilenced gun). It goes above s104's shape line when that line is there.
- **No SCCombat edit for the other two rules.** `Combat.friendlyFireBlocked` is wrapped at OnGameStart. Every ranged lane check goes through it, vehicle shots included (SCCombat.lua 1773, 2654, 2674, 3245, 3664, 3739, 3997, 4337). `Combat.scoreTargets` is also wrapped, for the fierce leash. Both wrappers act only for Sol, so faction NPCs are untouched.
- **The catalog and the verb.** The `U.actionCatalog` and `U.runAction` wrappers follow SolHornHold's pattern, so card_check finds the switch-gated action.
- **Mind: `apply_s105_combat_plans_mind.py`.**
  - It adds the `CARD_ACTIONS` entry. The card line carries every plan id with its Arabic name, and plan examples go in while the card stays within budget. All 8 examples go to s90's bank.
  - It maps an Arabic plan name the model wrote as the option back to the id. This is not a word override: his words are never matched.
  - Her lines, e.g. "تمام، رح كون حذرة.", "حاضر، ما بطلق.". Refusals are in her words too.
  - With the switch off (the action not in the game's list), the card is exactly the old one.
- **Java calls (javap 42.22.2).** IsoMovingObject `getX`, `getY`, `getZ` (no arguments). IsoGameCharacter `getPrimaryHandItem`, `isDead`. InventoryItem `hasModData`, `getModData`, `getFullType`. HandWeapon `isRanged`. All are looked up before they are called, and no overloaded method is called with a boolean. LF commands are Lua. `set_hold_fire` takes a Lua boolean, which LF's `handleHoldFirePolicy` checks.

## Devil's Advocate
- **The card is at 4599/4600.** To make room:
  - The team-doctrine button (`set_combat_doctrine`, the same behaviour as a plan for one companion) is off the card while plans are on it.
  - s91's two shorter rule wordings are applied.
  - The none rule loses its parenthetical, and the none examples keep a street, a place and a station (`شو اسم هالشارع / وين نحنا هلأ / بأي ضيعة نحنا / شو هالكازية`).
  - Only one plan example line fits (`اسنديني من بعيد`). The other plans rely on the Arabic names on the action line, plus the list example `قاتلي بشراسة`. The next Mind change must trade lines again.
  - Needs-in-game-test: does the phone model map "خليكي مخفية", "ابعدي عن الزومبي" or "رجعي عادي" correctly from the names alone?
- **Duplicates.** With the two-tier card (s90, off today), `set_hold_fire` examples ("لا تطخي") sit beside the `hold` plan. LF's hold-fire tick only toggles hold fire, while the plan also sets melee. Decide before turning tiers on.
- **Equip churn.** Every plan change runs LF's `equipPreferred` (`set_weapon_priority` does it). At rest, smart puts the katana in her hands, even when his M4A1 is marked. That is the rule ("melee for 1-2"), but it may surprise him the first time. The swap to the gun when 3+ appear costs one equip action (EFZ guns take a moment). The 4 s hold stops flapping at the 2/3 boundary.
- **Support is an approximation.** "4-8 tiles behind him" is LF's follow distance 5. Inference, not verified: LF keeps her at that distance, but not strictly behind him. The never-across-him rule covers the shooting side. Needs-in-game-test.
- **The fierce leash ignores the target's floor** (2D distance). LF's scoreTargets already keeps same-floor targets only.
- **A careful mode set directly on LF's state is replaced** if he later changes the doctrine on LF's own page. That is acceptable, since the page wins.
- **The lane rule may hold fire when he walks in front of her.** That is intended. Needs-in-game-test: in a tight corridor with him ahead, she may only melee or shove.
- **After her death the next Sol gets smart's knobs**, which overrides a team doctrine set on LF's page for new recruits.
- **Install order.**
  - The Mind and Lua parts must be installed together. With the patched Mind and the old Lua, card_check fails exactly on "CARD_ACTIONS sol_combat_plan exists in the game catalog" (launch_lab exit 8).
  - s104 can go before or after. Both orders give a byte-identical SCCombat, and all re-runs report "kept".

## Strategist
- **Install with the next grouped restart** (game closed, Jamal's word):
  1. back up;
  2. run `apply_s105_combat_plans.py <client>`;
  3. run `apply_s105_combat_plans_mind.py 05_TOOLS\sol_mind`;
  4. run `card_check.py 05_TOOLS\sol_mind --lua <client> --write-doc`;
  5. run `launch_lab.ps1 -CheckOnly`;
  6. update the ledger;
  7. commit.
- **Both the game and the Mind need a restart.**
- **Runtime tests**, one zombie group each:
  - "خليكي حذرة": her line, then `[SolCombatPlans] plan careful: passive / close_defense / best`.
  - Smart: 1-2 zombies, then the katana; 3+, then the gun (`[SolCombatPlans] smart: firearm (3 near her)`).
  - "قاتلي بشراسة": she does not chase past 25 tiles (`fierce: N zombie(s) beyond 25 tiles of him left alone`).
  - "خليكي مخفية" with an unsilenced M4A1: melee only, no shot.
  - Walk in front of her while she aims: `no shot across him (lane)`.
  - Low health: `health NN% < 30%: she falls back`.
- **Then step 2 (`gear_page_v2`):** the plan picker on the gear page calls the same `SolCombatPlans.run`.
- **MAIN:** only after runtime PASS.

## Offline tests
- **`test_s105_combat_plans.py`: 103/103.** It runs the real LF SCGameplayUtil, SCStableValue, SCCommands and SCCombat (patched), the real SolWeaponPick (s99) and SolCombatEquipFallback (s98), and EFZ's real TW/Core.
  - It covers:
    - each plan's knobs, read back from LF's own state;
    - follow distance and move mode set and restored;
    - smart melee/firearm by count, the 4 s hold, a zombie near him;
    - the real chooseWeapon via `Combat.equipPreferred`;
    - stealth silenced or not, through the real actionUtilities;
    - retreat under 30%;
    - lane geometry through the real friendlyFireBlocked;
    - the 25-tile leash;
    - reset on death and on a new Sol id;
    - switch off.
  - It also checks the installer (idempotent, both s104 orders identical), the tonumber and jarcall gates, and ASCII.
- **`test_s105_combat_plans_mind.py`: 45/45.**
  - The installer is idempotent.
  - Switch off: the card is unchanged.
  - Switch on: 4594/4599 chars (hand off / on the horn) within 4600.
  - The bank has every plan.
  - Routes through the real `Chat._route_by_model` (mocked model): her lines, the Arabic option mapped back, an unknown plan runs nothing, two orders.
  - card_check PASSES on the patched Mind plus the patched Lua with `combat_plans=on` (doc regenerated on a copy). The s82 route eval passes: ALL PASS.
