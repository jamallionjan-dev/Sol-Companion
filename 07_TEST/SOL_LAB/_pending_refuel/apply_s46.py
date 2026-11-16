"""Ladders and the sheet rope on game 42.22. Game closed only. All or nothing.
usage: apply_s46.py <client dir>"""
import os, shutil, sys
CLIENT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
EDITS = {}
def E(p, a, b): EDITS.setdefault(os.path.join(CLIENT, p), []).append((a, b))

E("SolAuthority.lua", "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "rope_climb_4222", "sol_ladders", "ladder_fast_slide",' + NL)

E("SCNativeTraversalActions.lua", """local function climbing(actor)
    local observed, active = invoke(actor, "isCompanionTraversalActive")
""", """local function climbing(actor)
    local onLadder, upLadder = invoke(actor, "isClimbingLadder")
    if onLadder and upLadder == true then return true end
    local onDown, downLadder = invoke(actor, "isClimbingDownLadder")
    if onDown and downLadder == true then return true end
    local observed, active = invoke(actor, "isCompanionTraversalActive")
""")
E("SCNativeTraversalActions.lua", """    local check = down and "canClimbDownSheetRope" or "canClimbSheetRope"
    local checked, climbable = invoke(actor, check, square)
    if not checked then return false, "native sheet-rope climb check is unavailable" end
    if climbable ~= true then return false, "native sheet rope is not climbable" end
    local methodName = down and "climbDownSheetRope" or "climbSheetRope"
    local invoked, failure = invoke(actor, methodName)
""", """    local isLadder = type(intent) == "table" and intent.nativeAffordance == "ladder"
    if isLadder then
        local got, ladder = invoke(actor, down and "getClimbLadderDown" or "getClimbLadder", square)
        if not got then return false, "native ladder check is unavailable" end
        if ladder == nil then return false, "native ladder is not climbable" end
        if down and intent.ladderX ~= nil then
            invoke(actor, "setX", intent.ladderX)
            invoke(actor, "setY", intent.ladderY)
        end
    else
        local check = down and "canClimbDownSheetRope" or "canClimbSheetRope"
        local checked, climbable = invoke(actor, check, square)
        if not checked then return false, "native sheet-rope climb check is unavailable" end
        if climbable ~= true then return false, "native sheet rope is not climbable" end
    end
    local A = rawget(_G, "SolAuthority")
    local newNames = isLadder or (type(A) == "table" and type(A.on) == "function" and A.on("rope_climb_4222") == true)
    local methodName = newNames and (down and "climbDown" or "climb") or (down and "climbDownSheetRope" or "climbSheetRope")
    local invoked, failure = invoke(actor, methodName)
""")

E("SCNavigation.lua", """    local utility = U()
    -- PathFindBehavior2 can route toward stairs, but the stock sheet-rope
""", """    local utility = U()
    local solLadders = rawget(_G, "SolLadders")
    if requestIntent.workCampOnly ~= true and type(solLadders) == "table" and type(solLadders.climbHere) == "function" then
        local ladder = solLadders.climbHere(actor, state, sourceSquare, goalSquare, now)
        if ladder then
            local down = ladder.down == true
            releaseStep(state, actor)
            releaseChoke(state, actor)
            state.path = nil
            state.pathGoalSquare = nil
            state.pathSearch = nil
            state.pathIndex = 1
            state.pathReason = "native_ladder"
            requestIntent.action = down and "climb_down_sheet_rope" or "climb_sheet_rope"
            requestIntent.targetSquare = goalSquare
            requestIntent.nextSquare = goalSquare
            requestIntent.nativeAffordance = "ladder"
            requestIntent.ladderX, requestIntent.ladderY = ladder.x, ladder.y
            requestIntent.mode = "walk"
            requestIntent.weaponReady = false
            state.lastAttemptFrom, state.lastAttemptTo = sourceSquare, sourceSquare
            local moved, movementReason = utility.move(actor, "walk", requestIntent)
            state.lastMovementReason = movementReason
            if moved then
                state.lastProgressAt = now
                SC.WorkRoutes.noteFirstMotion(actor, state, now, "native_ladder")
                return true, true, down and "ladder_descent" or "ladder_climb"
            end
            return true, false, movementReason or "ladder_action_rejected"
        end
    end
    -- PathFindBehavior2 can route toward stairs, but the stock sheet-rope
""")
E("SCNavigation.lua", """    local multiLevelHandled, multiLevelAccepted, multiLevelStatus =
        SC.Navigation._requestMultiLevelPath(
""", """    local solLadderWalk = rawget(_G, "SolLadders")
    if requestIntent.workCampOnly ~= true and type(solLadderWalk) == "table" and type(solLadderWalk.walkGoal) == "function" then
        local ladderSquare = solLadderWalk.walkGoal(actor, state, sourceSquare, goalSquare, now)
        if ladderSquare then
            goalSquare = ladderSquare
            requestIntent.targetSquare, requestIntent.nextSquare = ladderSquare, ladderSquare
        end
    end

    local multiLevelHandled, multiLevelAccepted, multiLevelStatus =
        SC.Navigation._requestMultiLevelPath(
""")

out = {}
for p, ps in EDITS.items():
    t = open(p, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    for a, b in ps:
        a2, b2 = a.replace(NL, nl), b.replace(NL, nl)
        assert t.count(a2) == 1, (p[-24:], a[:60], t.count(a2))
        t = t.replace(a2, b2)
    out[p] = t
bk = os.path.join(HERE, "..", "_backup", "20261109_before_ladders")
os.makedirs(bk, exist_ok=True)
for p in out:
    shutil.copy2(p, bk)
for p, t in out.items():
    open(p, "w", encoding="utf-8", newline="").write(t)
shutil.copy(os.path.join(HERE, "SolLadders.lua"), os.path.join(CLIENT, "SolLadders.lua"))
fix = os.path.join(CLIENT, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
with open(fix, "a", encoding="utf-8", newline="") as h:
    h.write("rope_climb_4222=on" + CRLF + "sol_ladders=on" + CRLF + "ladder_fast_slide=on" + CRLF)
print("applied")
