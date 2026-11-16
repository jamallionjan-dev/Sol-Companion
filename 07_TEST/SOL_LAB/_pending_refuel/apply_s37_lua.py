"""Run only after the game is closed. Sol never drops her things on the ground; a key in her bag starts the engine too.
usage: apply_s37_lua.py <SCLogistics.lua> <SolActions.lua>"""
import sys
def patch(p, a, b):
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    a, b = a.replace("\n", nl), b.replace("\n", nl)
    assert t.count(a) == 1, (p, a[:60], t.count(a))
    open(p, "w", encoding="utf-8", newline="").write(t.replace(a, b))
    print("applied to", p)
patch(sys.argv[1], """    local square = U().squareOf(actor)
    if not square then states[actor] = nil return false, "drop_square_unavailable" end
    local started, reason = beginTransaction(actor, state, {
        kind = "drop", item = state.item, source = state.source, square = square,
""", """    -- Sol empties her bag into our car or at home, never onto the ground: with nowhere to put it, she keeps it.
    if type(SolUI) == "table" and type(SolUI.solActor) == "function" and SolUI.solActor() == actor then
        moveMemory.note(actor, "drop", state.item, U().nowMs())
        states[actor] = nil
        return false, "sol_keeps_her_things"
    end
    local square = U().squareOf(actor)
    if not square then states[actor] = nil return false, "drop_square_unavailable" end
    local started, reason = beginTransaction(actor, state, {
        kind = "drop", item = state.item, source = state.source, square = square,
""")
patch(sys.argv[2], """    local haveKey = false
""", """    local drivingApi = type(SurvivorCompanion) == "table" and SurvivorCompanion.Driving or nil
    if type(drivingApi) == "table" and type(drivingApi.bringKeyToHand) == "function" then pcall(drivingApi.bringKeyToHand, s, veh) end
    local haveKey = false
""")
