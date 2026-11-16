# Sol Behavior Lab v1.1

Permanent pre-release gate for Sol/Living Fellows behavior changes.

Principle: a Planner may only request a capability that is mapped to a real Living Fellows implementation. Offline PASS never promotes native/Java behavior to Runtime PASS.

Run before every repair release:

`python sol_behavior_lab.py --behavior emergency_rescue_showcase`

The gate checks:
1. Source contracts for required Living Fellows capabilities.
2. Whole-mod Lua 5.1 syntax through the project's real `sol_lua_check.py`.
3. Real Lua policy contracts through `lupa` (weapon need, ammunition need, scavenger demand, native driving acquisition boundary).
4. Existing Sol Mind transport harness.
5. Goal/intent planner regression tests.
6. WORK/LIVE parity for behavior-critical modules.
7. Explicit Runtime-only gates: vehicle/native bridge, identity continuity, rendering, and other Java/game behavior remain PENDING until proven in Project Zomboid.

To add a behavior later:
- add its required capability IDs to `capabilities.json`;
- map every capability to the existing Living Fellows owner module;
- add at least one source contract and one behavioral regression where practical;
- do not duplicate an existing Living Fellows behavior in Sol Mind unless the capability audit proves it is absent;
- never promote Runtime-only capability based on this lab alone.

## v1.1
- Fixes Lua single-return normalization in the real-Lua driving contract.
- Failed installs must not leave a new tool tree behind.
- Installers are self-contained and clean superseded installer/package artifacts after verified success.
