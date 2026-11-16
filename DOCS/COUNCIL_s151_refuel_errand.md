# Council s151: refuel errand parsing and station approach (2026-11-14)

## Confirmed evidence

- Mind log `05_TOOLS/sol_mind/sol_mind.log` records refuel goals failing at `could_not_reach_door`, `goal_not_reached`, and `pump_too_far`. A repeated request canceled goal-3 as `player_order:refuel_again` and created goal-4; later take-wheel/exit requests also interrupted attempts.
- `intent_engine._refuel` recognizes fuel-can nouns through `_CAN_WORDS`; “بدونات” and “بدونة” were absent. “بدون سيارة” already means on foot and must not be reclassified as a can.
- `chat_service.Chat._pre_intents` canceled and resubmitted an active refuel goal on repetition. `GoalEngine.submit` already reports `already_running` while retaining the current phase.
- The staged station survey has offline replay against the captured pump forecourt and shipped Java planner. Direct parking plans failed; the newer approach-point route reaches a viable pose in replay.

## Engineer

Keep the existing refuel goal and phase when the same order repeats. Add only the missing dialect spellings for fuel cans; preserve the distinction between a can, a car, and “without a car.” Use the existing `station_survey` switch and its station/vehicle-aware pose survey, with the s95b approach point before turning into the chosen pump pose. Update the model card with examples for both car and can refueling at a station.

## Devil's advocate

- Station geometry and the actual pump transaction still depend on Build 42, modded vehicle shapes, pump access, power, and the player not taking over. Offline replay is not proof that every in-world pump is reachable.
- A repeated identical order must not restart the errand, but a genuinely new order (take wheel, exit, cancel) must still replace it through existing order handling.
- “بدون سيارة” must remain a walking instruction, not match the new can spelling. Keep that negative case in parser tests.

## Strategist decision

Install only to isolated LAB, retain `station_survey=on`, leave MAIN/release untouched, and require offline parser/goal/geometry tests plus launcher safety gates before gameplay. Promote only after an in-world test confirms: can wording selects cans; car wording selects the car; approach and parking reach the pump; filling visibly completes; repeating the same order does not restart; and take-wheel/exit still interrupts safely.

## Implementation and verification

- Added exact-anchor Mind installer `07_TEST/SOL_LAB/_pending_refuel/apply_s151_refuel_intent.py` and backup-replay test `test_s151_refuel_intent.py`.
- Applied to LAB: s95 station survey + Mind failure reporting, s95b station approach-point parking, and s151 can parsing / duplicate-order continuity / model card wording.
- Offline: refuel suite PASS; s95 136/136 PASS; s95b 49/49 PASS; s151 backup replay, idempotence, source parity and parser checks PASS; card_check PASS (0 failures, 1 existing warning, 4600/4600 characters); tonumber PASS; jarcall PASS (0 failures, 20 warnings); Java linkcheck 12,058/0; patch access 93/0.
- Gameplay is pending. Official `launch_lab.ps1 -CheckOnly` stopped at its process-safety guard because Windows `tasklist.exe` returned `ERROR: The user name or password is incorrect.` No attempt was made to bypass the guard or launch another game instance.
