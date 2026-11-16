# s115 combat motion review — 2026-11-12

## Engineer

- Confirmed from the user's report and image: Sol can aim and shoot while a zombie closes, but her movement during retreat looks unnatural and interrupted.
- Confirmed in LAB source: firearm close-spacing previously only offered a backstep below `combatFirearmMinDistance`; the shooter could remain the selected action when already in a poor aiming band. The backstep path already has navigation steering and a tactical-retreat/strafe interface.
- Smallest proposed fix: offer the existing routed backstep up to 0.5 tiles beyond the minimum firing distance, give it priority over shooting only in that close band, keep the target as Sol's facing target, and preserve the weapon-ready tactical retreat. Keep the emergency immediate-shot bypass limited to contact range and an attacking target.
- Acceptance: Sol creates distance while still facing/aiming at the attacker; movement is accepted and not rejected as blocked/locked; she resumes controlled fire once safe; weapon and ammunition damage remain native.

## Devil's Advocate

- A high backstep score can make Sol retreat when a shot would be safe, or loop if the zombie advances at the same speed. The bound is therefore only the existing minimum-distance band plus 0.5 tiles, and must be observed across a sustained encounter.
- A blocked route can reject the movement. Do not repeatedly submit the same rejected vector; use existing navigation result/diagnostics to identify a blocked path and fall back to the existing close-defense behavior.
- Tactical strafe/facing flags may not produce the intended animation in every weapon/animation state. Static checks cannot prove the visual result.
- Restricting emergency shots can make Sol hesitate at very short range. Preserve a narrowly scoped contact exception only when the target is attacking; do not widen it to ordinary near-range firing.
- This change does not by itself prove head-shot accuracy or damage parity. Keep those measurements separate from movement acceptance.

## Strategist and implementation boundary

- Applied to the isolated LAB Lua files only. Created a pre-change backup at `07_TEST/SOL_LAB/_backup/20261112_before_s115_combat_motion`.
- Installed LAB change: offer and prioritize a facing, weapon-ready tactical backstep inside the close firearm band; let the shooting discipline request space rather than immediately firing in the unsafe aim band. Immediate emergency fire remains restricted to contact-range attackers.
- No release, Steam installation, main profile, or main save was modified.

## Verification

- Focused source test: 64 passed, 0 failed. Lua syntax/compatibility checks in the harness passed.
- Launcher preflight: LINKCHECK 12,024 references/0 mismatches; patch access 93/0; tonumber check passed; jarcall 0 failures/20 warnings; model card passed with one warning.
- Runtime attempt: the lab launcher started game PID 19772 and Sol Mind PID 11424, but both exited during game initialization. `DebugLog` and `console.txt` stop immediately after display/audio initialization and contain no Lua exception or reported crash cause. Therefore no in-world combat or movement result is claimed; the launcher/startup exit must be diagnosed before visual acceptance.
- Next acceptance run must use the isolated save selected by LAB (`2026-11-10_02-39-13`): one attacker at close range, observe backstep while facing the zombie, then safe-range fire, and record movement diagnostics, physical hit part, health delta, and ammo decrement.

## Runtime update

The first restricted launch failed during ZombieBuddy initialization: `java.net.SocketException: Permission denied: connect` from its loopback selector. An approved elevated LAB run passes that boundary and loads the isolated mod set, including `[SolShootDiscipline] loaded 0.2.0`, `[SolWeaponPick] ready`, and `[SolWorld] world scanner ready`. The LAB game session is open on save `2026-11-10_02-39-13`. Startup log warnings/errors are base-game font assets, fluid-name sanitization, and a translation format warning; none points to Sol combat. The visual combat acceptance test remains pending.
