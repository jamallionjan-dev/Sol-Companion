# Sol AI Bridge Protocol

Status: IN PROGRESS
Protocol draft: sol-ai-1

## Architecture
- Living Fellows remains the local body/autonomy/execution layer.
- Sol AI is an external planner/conversation brain.
- Local survival reflexes, collision handling, movement continuity, combat reaction, and path following never wait for the external model.
- External AI receives structured observations and issues only validated high-level tool requests.
- No arbitrary Lua, Java reflection, shell command, or raw game-object handle is exposed to the external AI.

## Transport
Implemented work-copy transport: bounded overwrite mailbox files using deterministic `SOL_AI_FRAME_V1`, not JSONL.
- Brain -> Game: `SolAI_Inbox.txt`
- Game -> Brain: `SolAI_Outbox.txt`
- Physical frame: line 1 `SOL_AI_FRAME_V1`, line 2 encoded body, line 3 `END`.
- Game writer uses overwrite semantics.
- Limits: `MAX_CHARS = 131072`, `MAX_VALUES = 4096`, `MAX_DEPTH = 12`.
- Runtime integration is statically integrated but still awaits Project Zomboid runtime proof.

Game -> Brain types currently emitted:
- `hello`
- `perception_snapshot`
- `tool_result`
- `heartbeat`
- `error`

Brain -> Game types currently handled:
- `ack`
- `ping`
- `say`
- `tool_request`
- `memory_write` / `memory_query` are recognized but rejected as `not_implemented`.
- Other types are rejected as `unsupported_message_type`.

ACK / single-flight contract:
- `payload.ackSequence` must numerically equal the exact `sequence` of the current Game -> Brain in-flight frame.
- Only one Game -> Brain frame may be in flight.
- A stale, future, non-numeric, or no-in-flight ACK does not release it.
- Perception is coalesced to one pending snapshot while transport is busy.
- Critical messages use a bounded queue of 32 entries.
- Heartbeats coalesce and may be discarded to make room; non-heartbeat critical items are not evicted.
- A tool request is deferred before execution when no critical-result capacity exists; polling pauses with `deferred_tool_pending` until capacity returns.

Required runtime envelope fields:
- `protocol = "sol-ai-1"`
- `schema = 1`
- `sessionId`
- `worldId`
- `sequence`
- `requestId` when applicable
- `timestampMs`
- `type`
- `payload`

Inbound runtime validation enforces protocol, `schema = 1`, numeric `sequence`, exact sessionId, exact worldId, and string `type`.
Brain-side rules (from source; implemented in 05_TOOLS/sol_mind):
- The inbox holds one frame and the game gives no read receipt, so the brain writes one frame at a time: a command is written first and kept for a grace period, then replaced by the ack.
- A command is proven consumed only by its tool_result; if missing after several game frames it is resent with the SAME requestId (the game's request cache makes the replay side-effect free).
- A new sessionId resets brain transport state. Writes are atomic (temp file + replace).
- Lua drops nil-valued map keys and cannot hold nil inside arrays; the brain never sends either.

## Perception source mapping
Primary source: SCSenses.snapshot / SCSenses.refreshImmediate.
Additional sources: SC.Commands.peek, SC.ActionSupervisor.summary, SC.Navigation.status, SC.Driving.jobStatus, persistence/world identity, actor inventory/medical facts, and enabled-mod catalog.
External snapshots contain normalized facts only; never raw Lua/Java object references.

Core snapshot sections:
- sol: identity, position, room/indoors, health, wounds, needs, equipment, inventory summary, current order, supervised action, vehicle state
- player: position, health/danger, vehicle state, distance/direction from Sol
- threats: bounded visible/heard threats, nearest threat, immediate count, pressure, encircled/escape state
- world: exits, escape candidates, nearby doors/windows/containers, building/room, local traversability facts
- navigation: goal, path state, path failure, moving/stuck state, route reason
- vehicle: current vehicle, seat/driver state, route/lane status
- memory_context: active goals, recent important events, known locations
- mods: enabled mod ids and learned per-mod capability notes

## Decision cadence
- Living Fellows remains the fast local reflex/execution layer.
- `sol-ai` runs through the existing `SC.Scheduler` at 100 ms; there is no second global `OnTick`.
- `SCAIRuntime` internally gates mailbox polling at 250 ms, perception snapshots at 750 ms, and heartbeat at 5000 ms.
- External AI is therefore a low-frequency executive/conversation layer, never a per-frame controller.

## Tool gateway v1 - implemented set
`tool_request.payload` uses `tool` plus optional table `arguments`. `requestId` is mandatory.
Implemented gateway tools:
1. `follow`
2. `stay`
3. `regroup`
4. `retreat`
5. `go_to`
6. `check_room`
7. `open_door`
8. `close_door`
9. `board_vehicle`
10. `exit_vehicle`
11. `designate_target`
12. `avoid_target`

The gateway validates/resolves coordinates and stable door/object/vehicle/zombie references, then routes execution through `SC.Commands.issue`. Navigation, driving, and ActionSupervisor remain the mature Living Fellows execution/safety layers rather than being reimplemented in the AI runtime.

## Tool request idempotency and results
- Maximum remembered request ids: `MAX_REQUEST_CACHE = 128`.
- A deterministic signature is computed from `tool` and normalized table `arguments`.
- Same requestId + same signature replays the cached result without repeating the side effect.
- Same requestId + different signature returns a rejected `tool_result` with `reason = "request_id_conflict"`.
- Gateway exceptions become rejected `tool_result` records instead of escaping the AI runtime.
- A request is not executed while critical-result capacity is unavailable; it is held as the single deferred tool request.
## Memory
1. Session memory: recent dialogue, observations, active goals, tool results.
2. World/save memory: known locations, vehicles, containers, hazards, tasks, discoveries.
3. Long-term Sol profile: stable preferences/knowledge, enabled-mod catalog, and learned per-mod notes.
AI memory writes are proposals; game-side code validates size/type and namespaces them by world/session.

## Conversation and voice
- Arabic and English text use the same transport.
- Player message -> conversation_user.
- AI response -> say.
- SCNativeCompanion.addLineChatElement can display Sol speech in world.
- Final Sol window will contain chat and push-to-talk and hide legacy Living Fellows panels.
- Voice phase: push-to-talk -> STT externally -> conversation_user -> AI -> say + TTS.

## Safety and ownership
- Living Fellows local autonomy and ActionSupervisor remain authoritative for physical execution and survival behavior.
- External AI receives normalized facts, not raw Lua/Java object handles.
- Inbound protocol/schema/session/world mismatches and missing numeric sequence are rejected.
- AI startup fails closed with `world_identity_unavailable` if no real save/world identity is available; it never publishes `worldId=unknown`.
- AI actor resolution succeeds only when exactly one living registered companion exists, matching the one-Sol runtime design.
- Tool side effects are protected by requestId/signature replay semantics.
- Mailbox duplicate suppression keys the last inbound frame by sessionId, sequence, requestId, and type.
- Game -> Brain transport is single-flight. Failed writes restore the logical item for retry, but retry sequences may contain gaps because sequence is assigned before mailbox write.
- Bridge/AI failure is intended to leave the local Sol body functional; AI start/stop failures are diagnostic-only in SCRuntime.
## Validation phases
A. Export one normalized Sol snapshot from SCSenses without changing behavior.
B. Prove mailbox round-trip with ping/ack only.
C. Prove one harmless tool: follow/stay.
D. Prove go_to with ActionSupervisor receipt.
E. Add event/delta publication and failure receipts.
F. Add text conversation and in-world speech.
G. Add persistent memory and mod catalog.
H. Add STT/TTS.
I. Add AI navigation/vehicle goals while retaining LF execution.

## Current proof status
- LF body/spawn: Runtime PASS.
- Follow: Runtime PASS by user observation.
- Zombie avoidance: Runtime PASS by user observation.
- LF Senses/Navigation/Driving/ActionSupervisor: Source proof PASS.
- SCAIMailbox, SCAITargetResolver, SCAIToolGateway, SCAIPerceptionAdapter, and SCAIRuntime: work-copy Static PASS.
- Bootstrap require order and required-function contracts: Static PASS.
- AI scheduler/start/stop lifecycle integration in SCRuntime: Static PASS.
- SOL_AI_FRAME_V1 mailbox wire, ACK, single-flight, backpressure, duplicate suppression, and idempotency semantics: Static source proof PASS.
- Integrated Project Zomboid runtime proof of the AI bridge: PENDING.
- memory_write / memory_query: recognized but not implemented.
- Text chat UI, Arabic/English Sol window redesign, STT/TTS, persistent memory, mod catalog, and broader AI tool set: PENDING.
- 2026-10-22: SOL_AI_FRAME_V1 codec cross-checked with an exact Python port (byte-identical re-encode) and the real Lua runtime under Lua 5.1: offline PASS.
- 2026-10-22: live game AI runtime start + hello frame observed (session 2026-10-22_11-53-35); no brain process existed to ack it.
- 2026-10-22: brain process 05_TOOLS/sol_mind v0.1: offline PASS. Integrated Project Zomboid runtime proof: PENDING.

