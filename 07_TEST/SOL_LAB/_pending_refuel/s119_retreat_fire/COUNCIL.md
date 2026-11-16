# s119: close-range fire while retreating (SOL_LAB only)

## Engineer

Current installed `SCCombat.executeRetreatCounter` has a 3-tile minimum for retreat cover-fire. At or inside the shove distance (default 1.35), it always selects a shove first. Therefore a fierce-plan Sol with a usable loaded firearm can retreat without firing in the close band. The Lab log confirms fierce mode is active and separate headshot kills have succeeded; it does not yet show a retreat-counter action.

## Devil's advocate

Firing at contact distance can be blocked by the animation/action dispatcher, and a short-range bullet may be less safe around the player. The existing retreat gate already refuses counter-fire when encircled, more than one immediate attacker is counted, overrun risk is too high, a friend blocks the lane, the target is obstructed/invisible, the floors differ, or ammunition is unavailable. Keep every gate. Preserve a shove below 0.75 tiles and retain the normal 1.35 shove behavior unless the fierce plan and a safe close firearm shot are both confirmed.

## Strategist / acceptance

Keep the change isolated behind `retreat_close_fire=on` in SOL_LAB. In fierce mode, permit the existing one-shot counter-fire between 0.75 tiles and the normal 3-tile threshold, including the shove band, then let the following decision resume retreat. Other plans retain the current 3-tile minimum and shove priority. Verify in-world at 2.5, 1.2, and 0.6 tiles: expected counter-fire then retreat, normal behavior, and shove respectively. Record actual ammo decrement, hit part/health change, movement/path result, and any runtime error. Static wiring does not prove movement animation or a landed hit. No release or Steam profile change.
