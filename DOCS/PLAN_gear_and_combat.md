# Plan: the gear page (العتاد) and fighting plans

Jamal's request (2026-11-11 11:41):
- The gear page is weak.
- It should offer her bag, his bag, and what he wears or uses.
- It should have fighting plans: aggressive with guns, aggressive melee, quiet melee, and a table of normal / strong / quiet for every weapon kind: long-range, close-range, firearms and melee.

This is a plan only. Nothing is built. Reader copy (Claude Doc): https://claude.ai/artifact/VabiQA3gAghupd1io79NvH

## What exists today (Living Fellows, read from the code)

- **The page shows:** weapon "-", ammo 88, load 59.4/100, health 98%, injuries, food.
  - Buttons: "her bag", "medical check", "bandage".
  - "Weapon priority" (سلاح ناري) and "carry policy".
- **Underneath, LF already has four combat knobs:**
  - `combatMode`: passive, defensive, aggressive.
  - `combatDoctrine`: close_defense, weapons_free, ranged_support, stealth.
  - `weaponPriority`: best, firearm, quiet.
  - `holdFire`.
- **The gaps:**
  - The page shows only one of these knobs.
  - The weapon he picks is not kept (s98 `preferred_weapon` adds that).
  - There is no way to hand her gear from his bag.
  - There is no "plan" a person can understand in one word.

## Part 1. The gear page

| Section | Contents | Actions |
|---|---|---|
| **In her hands** | The weapon, ammo in it and in her bags, state (ready / empty / jammed / broken parts), condition | "Use this one" (her preferred weapon, s98), reload, unload |
| **Worn** | Her worn items by body slot: helmet, vest, bag, glasses, gloves, boots, with condition | Take off, swap |
| **Her bag** | Weapons, ammo and magazines, medical, food, tools, each as a short list | Give it to me, use it, set as preferred |
| **My bag** | Only what she can use: weapons, ammo for her guns, medical, armour | "Give it to Sol": one tap |
| **Like me** | What he wears or holds that is better than hers, shown side by side | "Take one like mine" (when a spare exists) |
| **Fighting plan** | One choice from the table below, plus "hold fire" | Picked here or by chat |
| **Status line** | e.g. "معي 88 طلقة للـG28، الخوذة 60%" | — |

Rules:
- A weapon she can't use (broken parts, no ammo) shows why in plain words.
- No technical words anywhere.
- Her own lines stay in her voice.

## Part 2. Fighting plans

Each plan is one name. It sets LF's existing knobs plus a few new rules (marked "new"). The weapon kind comes from what is in her hands or her preferred weapon.

| Plan (Arabic name) | Weapon kind | LF knobs | Behaviour |
|---|---|---|---|
| **ذكي** (default, smart mixed) | any | defensive, close_defense, best | Melee for 1–2 zombies; firearm for a group (3+) or anything threatening him; back to melee when only 1–2 are left |
| **عادي** (normal) | firearm | defensive, close_defense, firearm | Shoots threats near him (≤12 tiles), keeps close, reloads behind him |
| **عادي** | melee | defensive, close_defense, best | Fights what reaches them, shoves first, no chasing |
| **شرس** (aggressive, open fight) | firearm | aggressive, weapons_free, firearm | Steps forward, shoots every zombie in sight (≤25), no pause until clear; new: keeps ammo for 1 reload and calls it out |
| **شرس** | melee | aggressive, weapons_free, best (melee) | Goes to each zombie and kills it; new: breaks off when tired or hurt, then goes back to him |
| **إسناد** (support from range) | rifle | defensive, ranged_support, firearm | Stays 4–8 tiles behind him and shoots what comes at him, never in front of his line |
| **حذر** (careful) | any | passive, close_defense | Only fights what touches them, keeps ammo |
| **تخفي** (stealth) | melee | passive, stealth, quiet | Crouches, quiet weapon only, kills from behind, never shoots; new: if seen, falls back to "normal" |
| **تخفي** | firearm (suppressed only) | passive, stealth, quiet | Only a suppressed gun, only when he shoots first |
| **تجنّب** (avoid) | any | passive, stealth | Avoids contact: moves away, keeps him between her and the threat; fights only when cornered or when he is attacked |
| **لا تطلقي** (don't shoot) | any | holdFire | No shots; melee only to save a life |

**Close / long range inside one plan (new):**
- ≤2 tiles: shove or melee, unless the plan is "aggressive firearm".
- 2–8 tiles: the main weapon.
- >8 tiles: shoots only in "aggressive" or "support".

**Safety rules for every plan:**
- Never shoots across him.
- Retreats when health is under 30%.
- Picks a usable weapon (s98).
- A broken gun is never her main weapon.

## Part 3. How he chooses

- On the page: one list (normal / aggressive / support / careful / stealth / don't shoot), with the weapon kind taken from her weapon.
- By chat, with phrases the model maps to one action, `sol_combat_plan <plan>`. Synonyms go in the card examples only (model-first rule). Examples: "قاتلي بشراسة", "اسنديني من بعيد", "خليكي مخفية", "ما تطلقي".
- She confirms in her own voice, e.g. "تمام، رح كون حذرة" or "حاضر، ما بطلق".

## Council (Engineer / Devil's Advocate / Strategist)

- **Engineer:** most of this maps onto LF knobs that already exist, so it is mostly UI plus a plan layer. The new parts are:
  - range bands;
  - "keep 1 reload";
  - "break off when hurt";
  - the stealth fallback;
  - the side-by-side "like me" list.
- **Devil's Advocate:**
  - "Aggressive" makes her die more, and the far-chasing she does today is already a risk. So "aggressive" must still stay within 25 tiles of him and retreat at 30% health.
  - EFZ guns can be broken (duplicatePath), so the page must show it.
  - The LF page code is large; avoid rewriting LF files and add our own page tab instead.
- **Strategist:**
  - First build the plans (most value, small UI), then the "In her hands" and "My bag → give" sections, then "Like me".
  - Ship each behind its own switch, and test each plan in play with one zombie group.

## Order of work (each behind its own switch, offline tests, then a runtime test)

1. `combat_plans`: the plan layer with 6 plans + the chat action + card update + speech lines. (s98 must be installed first.)
2. `gear_page_v2`: our own tab with the "In her hands", "Worn", "Her bag" and "Fighting plan" sections.
3. `gear_give`: "My bag → give to Sol" + "Like me".
4. Range bands + "keep 1 reload" + "break off when hurt".

## Built since (staged, not installed)

| Step | Switch | What | Status |
|---|---|---|---|
| s99 | `mag_fill` | She fills empty or partial magazines with loose rounds of the right calibre when no zombie is within 6 tiles, then inserts and racks. The chambered round counts. Loaded magazines are found past LF's scan cap. | Offline 76/76, `COUNCIL_s99_mag_fill.md` |
| s99 | `weapon_scan` | LF's weapon list also takes weapons its 240-item walk missed. This is the root cause of "carried=1" and the wrench. | Same |
| s99 | `melee_choice` | Melee scored by damage x condition and kind (long blade/blunt over tools). Her melee weapon is his pick, else the katana. A held melee weapon is not kept just for being held. | Same |

## Decisions (coordinator, 2026-11-11 11:45)
1. "Aggressive" stays within 25 tiles of him.
2. Stealth with a firearm only when EFZ reports the gun silenced (`Core.stats(key, TWRuntime.read(w)).silenced`); otherwise melee.
3. After her death the plan resets to the default, "smart mixed" (ذكي).


## Status 13:12
Built and installed in the lab: preferred weapon (s98), the weapon list past the cap + katana melee choice + magazine fill (s99), item stacks (s100). In work: shooting discipline (s104). Not built yet: the fighting plans (combat_plans) and the gear page (gear_page_v2).

## Status 15:25
Installed in the lab: combat_plans (s105, PASS by chat), shooting_discipline + s104b. s107 gear page is integrated into the private 0.28.5 release candidate; offline test 106/106 passed on the candidate dependency set. LAB/UI runtime check remains pending. Left: range bands, keep 1 reload, break off when hurt, work-time sling, gear page polish after runtime review.
