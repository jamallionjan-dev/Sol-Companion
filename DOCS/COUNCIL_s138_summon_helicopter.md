# s138 — summon a ready helicopter (2026-11-13)

## Engineer — evidence and acceptance

- Confirmed: AviationCore exposes `AircraftRegistry.GetAircraft()` and registers helicopter scripts by category. Its server spawner uses server-side `addVehicle`, and the game API exposes grid-footprint, vehicle-key, fuel-container, and vehicle-transmission methods.
- Confirmed: `SolHeliGPS.lua` had an unfinished local draft for remembering the last driven helicopter. It called `nowMs()` before its local declaration, which would resolve the wrong symbol in Lua.
- Goal: the exact Mind request “سول فيكي تجيبي هليكوبتر” queues a summon and receives the requested reply “أكيد بقدر”. The server must use the last driven registered helicopter (fallback `Base.UH1BHuey`), choose a safe outdoor footprint near the player, spawn once, grant a key, finalize AviationCore parts/manual, fill and verify its JetFuel tank, and log/report its result.

## Devil's Advocate — failure modes

- Client-side `addVehicle` or debug spawn would bypass authoritative world creation and could behave differently in the normal game. The implementation therefore sends a client command and creates only on the server.
- A model-supplied script name or player coordinates must not be trusted. The server accepts only a registered helicopter script and calculates the spawn point from its player object.
- A tight neighborhood can have no valid landing footprint. In that case the server rejects the request without creating a helicopter; it does not claim a spawn succeeded.
- A queued client request is not proof of server creation. The chat phrase acknowledges that Sol can send the request; server logs and the client result log show whether a helicopter actually spawned.

## Strategist — selected approach

Keep this feature isolated to Sol's action catalog, Mind router/reply path, and one server listener. Do not edit AviationCore or the Steam profile. Track the user's driven script at a one-second interval, use an allowlist lookup, perform one bounded footprint search only on demand, then verify the full JetFuel fill after spawn. Do not launch the game until the card gate, syntax/contract checks, and LAB preflight pass.

## Implementation / verification record

- Status: implementation is installed in WORK and isolated SOL_LAB; offline contract and model-card gates pass. Runtime launch is pending the LAB launcher's process/singleton preflight.
- Required evidence before launch: model-card gate with generated human card; Python route/contract tests; game's Kahlua parser on changed Lua files; launcher `-CheckOnly` against the isolated profile.
- Required in-world check: issue the exact phrase once; verify the reply, `[SolHeliSpawn]` server success, `[SolHeliGPS] summon confirmed`, one helicopter of the saved script, full JetFuel, and an ignition key. Also test no saved model (fallback Huey) only if that state is easy to establish.
- Boundaries: static/Kahlua success does not prove that a clear footprint exists in this save or that the spawned aircraft is physically flight-ready. These need in-world verification.
