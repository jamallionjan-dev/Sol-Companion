# Sol 0.28.0 (2026-11-10)

Built from the lab copy (`07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB`) by `07_TEST\SOL_LAB\_pending_refuel\build_release.py`, without the lab marker `SolLab.lua`. The main copy reads `C:\Users\JAMAL\Zomboid\Lua\SolFixes_MAIN.txt`. A switch missing from that file is off.

Full guide, with every switch and its status: [DOCS/SOL_HANDOFF.md](../DOCS/SOL_HANDOFF.md).

## Newly on in MAIN (proven in play, 2026-11-10)
- `road_first` (with the s49 scan fix): the drive keeps to the road.
- `refuel_top_up` and `refuel_short_hop`: refuelling at the station.
- `drive_replace`: a new drive order replaces the old one.
- `home_parks`: she parks in the garage.
- `tracked_mode` (with `vehicle_steer_adapt` as a guard): the Bradley drive.
- `debug_ctrl_a_guard`: the Ctrl+A guard.
- `far_wait_speed` and `dot_paused_fix`: far walk-in, the game-speed timer and the status dot while paused.
- `address_book`: the address book tab. It learned a house by itself, and a click set the GPS marker and started the drive. The crash from 19:02 is fixed.
- Already on and re-proven today: `sol_ladders`, `sol_farm` (till, plant, water), the GPS unreachable warning, home rest, street names, the "دبريلي الارض بغيابي" farm phrase and the s66 sort routing.

## In the code, off in MAIN until proven in the lab
- `secret_loadout`: capturing his two weapons worked live. Handing them over crashed live; the crash is fixed but not re-tested.
- `far_car` and far_meta (the Bradley and other vehicles the game keeps in its background "meta" store):
  - The live load read the car's saved data 2 bytes off. This is fixed: it now reads the data from byte 2, as the game does.
  - A failed load now puts the car back where it was.
  - Not yet proven in play.
- `far_work`, `farm_night`, `spatial_access`, `item_sort` (sort 0.2.2), `animal_care`, `bleed_get_out`.
- `gps_static_roads`: routes the GPS over the whole map's roads when the live router's cut-down road network fails.
- `gps_plain_words`: plain Arabic in the GPS panel instead of raw codes.
- `instinct_only` and `drive_bypass` stay off.

## Code changes that need no switch
- s75: nothing hands a multi-value list to Kahlua's `tonumber` any more. This was the cause of the address book and secret weapon crashes.
  - 97 client files changed: `tonumber(f())` became `tonumber((f()))`, and the shared call helpers now return one value.
  - The new gate (`05_TOOLS\sol_kahlua\tonumber_check.py`, built on a tokenizer) refuses a launch with exit 7.
- Mind changes (`05_TOOLS\sol_mind`):
  - s77: one card action `cars_near` for "which cars are around her", near or far.
  - Coordinates are never spoken in chat: survey, the memory line, the reply gate and `clean_reply` all keep them out.

## Gates run on the release copy
- Java link check against the 42.22 game jar: 11963 references, 0 mismatches.
- ZombieBuddy patch access: 88 patches, 0 problems.
- Lua method check: nothing missing beyond the previous release.
- Every Lua file compiles.
- The installed copy matches the release file by file (SHA-256, 2572 files).

## Backups
- `03_BACKUPS\Sol_install_before_0.28.0_20261110`: the previous installed main (0.27.0).
- `03_BACKUPS\Sol_WORK_before_0.28.0_20261110`: the previous `01_WORK\Sol`.
- Older release backups (`..._before_0.27.0_20261110`) can go once Jamal confirms 0.28.0 works.
