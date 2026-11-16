# LAB runtime errors — 2026-11-14

Scope: Jamal supplied the complete Mod Report after closing the game. Fixes are staged in `01_WORK/INTEGRATION/SOL_2026-11-14_0.28.6_ERRORFIX/Sol` and applied to the isolated LAB mod after backing up all pre-existing target files. Eleven client files are synchronized; `SolEdgeApi.lua` and `SolKahluaGuard.lua` are new LAB files. The original 0.28.6 release candidate, installed MAIN mod, and Workshop sources are unchanged.

Log: `07_TEST/SOL_LAB/profile/Zomboid/Logs/2026-11-14_01-04_DebugLog.txt`

## Consolidated error families

### V1 — Viewpoint passes a null-sprite object to vanilla menu construction

- Count: x2 in the Viewpoint report; `ISWorldObjectContextMenuLogic.fetch` throws because `spriteName` is null.
- Call path: `ViewpointInteract.harvest` → hidden `ISWorldObjectContextMenu.createMenu` → vanilla `fetch`.
- ProjectViewpointQOL already catches this known error after it occurs, which keeps the interaction gather alive but does not prevent the Java error from being logged.
- Staged fix: SolCompatVP now skips only objects whose `getSpriteName()` returns nil before Viewpoint builds the hidden menu. It is gated by the existing `compat_vp_harvest` switch.

### K1 — Kahlua ReturnValues pool failure across callbacks and timed actions

- Signature: `NullPointerException: Cannot assign field "callFrame" because "a" is null at ReturnValues.put(ReturnValues.java:61)`.
- Reported from Viewpoint `createMenu` / `doBuildMenu`, Viewpoint `onOpenDoor`, and CleanUI's deferred timed-action queue (x8); earlier LAB lines also showed it during vehicle exit.
- These stacks identify the point where the damaged Kahlua pool is used, not the first call that damaged it. Earlier LAB logs with SolKahluaGuard recorded the initiating bad calls in `SolPlace.lua`: `getDoor/getWindow/getThumpableWindow/getWindowFrame` received a Boolean although Build 42.22.2 exposes the corresponding `...To(IsoGridSquare)` methods (verified against the installed game's `IsoGridSquare` class).
- Staged source fix: `SolPlace.liveStruct`, `SCNavigation`, and `SCTopology` now use the `...To(adjacentSquare)` edge methods through `SolEdgeApi`; these match the game's exposed signatures and remove the known failed-overload calls that polluted Kahlua's pooled arguments. The independent `edge_api` switch is enabled in LAB.
- SolKahluaGuard remains enabled in the development source to report any other failed overloads. The current attached report lacks the initiating call, so runtime confirmation is still needed to establish that no other mod contributes to the same pool failure.

### R1 — Sol's NPC reload enters a player-index-only inventory path

- Same `walkToContainer` NPE is attributed to CleanUI, Gunworks-gang, and Sol; these reports are the same event, not three separate failures.
- Exact cause: Sol's reload calls Gunworks `BeginAutomaticReload`; its `transferIfNeeded` delegates to `luautils.haveToBeTransfered` / `walkToContainer`, which looks up the actor with `getSpecificPlayer(playerNum)`. For Sol that lookup is nil, and vanilla `ItemContainer:isInCharacterInventory` receives the null character.
- Staged fix: preserve Gunworks/EFZ's reload selection, but temporarily route Sol's magazine transfer through the actor-based `ISInventoryTransferAction`. The ordinary local-player reload path remains unchanged.

## Engineering review

- **Engineer:** the reload failure has a direct, narrow Sol-side correction; the null-sprite failure has a narrow compatibility guard; and earlier LAB traces identify a stale Boolean overload in `SolPlace` as a confirmed source of K1.
- **Devil's advocate:** a timed-action transfer can still fail if the selected magazine is not actually inside Sol's inventory; the implementation rejects that source instead of asking vanilla to resolve Sol as a local player. The Viewpoint guard skips only objects vanilla cannot process. The Kahlua guard may expose calls made outside Sol's wrappers, so external Mod code can remain a source.
- **Strategist:** stage the source-signature correction, the reload fix, the null-sprite guard, and Kahlua tracing in development. Keep 0.28.6 and installed copies unchanged until an isolated LAB run confirms no further overload failures, no Kahlua exceptions, and successful Sol reloads from a nested bag.

## Verification and release gate

- Jamal confirmed the game was closed. No manual process-state query was performed; the official lab launcher retains its own launch safety gates.
- Offline tests: s84 29/29; s96 27/27; s101 19/19; NPC reload 10/10; Viewpoint null-sprite guard 8/8. Lua/offline installer checks do not prove in-game behavior.
- No release build, merge, install, or MAIN/local-mod update was performed.
- Runtime acceptance still required: (1) Viewpoint hover over a null-sprite corpse/object; (2) Viewpoint loot/menu interaction including a vehicle door; (3) Sol reload with a magazine in her main inventory and in a nested backpack; (4) review any new `[SolKahluaGuard] failed overloaded Java call` entry and resolve its exact signature.
- Do not promote the integration copy or update the release candidate/installed MAIN copy until LAB runtime acceptance is complete.

## Runtime finding — second magazine-fill attempt still fails

- At `2026-11-14 02:43:03.481`, frame `f:13990`, the LAB DebugLog reproduced the reported `ItemContainer.isInCharacterInventory` NPE (`chr == null`). The Lua stack is `CleanUI.transferIfNeeded` -> `Gunworks Magazine.reloadMagazine` (`Magazine.lua:206`) -> `SolMagFill.queueFill` (`SolMagFill.lua:335`) -> `step/poll`.
- At `f:12366`, the first fill pass logged the selected G28 magazine at 4/20. The user reports that first attempt produced no visible reload; the exception appeared on the second attempt. The log confirms the first path was attempted and the second raised the NPE.
- Confirmed gap: s149 wrapped the Gunworks `BeginAutomaticReload` route inside `SCNativeActions`, but `SolMagFill` calls `Magazine.reloadMagazine` directly. Gunworks' function itself calls `ISInventoryPaneContextMenu.transferIfNeeded(playerObj, magazine)`, which reaches the player-only `walkToContainer` path for Sol.
- Result: NPC reload acceptance FAIL / incomplete. Do not merge or promote. Continue the current user test session and gather any remaining errors; stage a complete fix for both `SCNativeActions` and `SolMagFill` only after the user finishes the session.
- 2026-11-14 02:47:02.851 log watch: two `Translator.reportMissingArgumentsFromPastAbuse` warnings for missing arguments in `UI_AliceWeaponSling_Unequip` and `UI_AliceWeaponSling_MoveTo` (`AliceWeaponSling` localization). They are not attributed to Sol; no Sol/Kahlua or reload error accompanied them at that time. Keep them separate from the s149 Sol fixes.

## 2026-11-15 - s152: the magazine-fill path is covered (offline)

- Both live traces (02:43:03 via Gunworks `Magazine.reloadMagazine`, 03:18:32 via `SolMagFill.queueInsert` -> `transferIfNeeded`) end in vanilla `luautils.walkToContainer`, which looks the actor up by player index. `SolNpcTransfer.lua` now moves her own items directly (LF verified move) and answers `transferIfNeeded` for her while the reload helpers run; `SCNativeActions.beginAutomaticReload` uses the same path. Switch: `npc_reload_transfer`.
- Later sessions after s149 (02:33 and 12:19 on 11-14) show no `createMenu`, `doBuildMenu`, `begin` or `ReturnValues.put` exception; the only one left was this `walkToContainer`. Inference, not proof: V1 and K1 are fixed by s149.
- Offline `test_s152_npc_transfer.py` 27/27. Runtime acceptance is still required (see `SOL_NEXT_20261115.md`).
