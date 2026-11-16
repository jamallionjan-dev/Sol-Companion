# Sol 0.28.1 (2026-11-10, late)

Built from the lab by `07_TEST\SOL_LAB\_pending_refuel\build_release.py 0.28.1 install`. The main copy reads `C:\Users\JAMAL\Zomboid\Lua\SolFixes_MAIN.txt`. Full status: [DOCS/SOL_LEDGER.md](../DOCS/SOL_LEDGER.md).

## Newly on in MAIN (proven in play 2026-11-10)
- `secret_loadout`: "عطيني سلاحي السري". Both rifles with all parts, full magazine plus a chambered round, and 500 rounds each. Confirmed by Jamal ("نجح").
- `gps_static_roads`: the GPS routes along the whole-map roads when the live router's clipped graph fails ("بيانات الخريطة ناقصة"). The drive to 625 Dewey went along real roads through fog.
- `gps_plain_words`: plain Arabic in the GPS panel instead of codes. Confirmed by Jamal.
- `far_work`: while he is away she keeps the farm (43 jobs over 5 game hours). The shift ends when he comes back.

## In the code, off in MAIN until proven
`horn_hold`, `speed_levels` (20/40/65), `address_target`, `preview_calm`, `stall_ladder`, `veh_shoot_seated`, `compat_vp_harvest`, `place_leg_arrive`, `address_places`, `exit_first`, plus the earlier off list (`far_car`, `animal_care`, `item_sort`, `spatial_access`, `farm_night`, `bleed_get_out`, `instinct_only`, `drive_bypass`).

## Gates on the release copy
- Link check: 0 mismatches.
- ZombieBuddy patch access: OK.
- Lua method check: nothing new missing.
- Every Lua file compiles.
- Route eval over the previously-passing phrases: all pass.
- Mind card check: PASS, 4540 of 4600 chars.
- The installed copy matches the release, 2582 files.

## Backups
`03_BACKUPS\Sol_install_before_0.28.1_20261110` and `03_BACKUPS\Sol_WORK_before_0.28.1_20261110`.
