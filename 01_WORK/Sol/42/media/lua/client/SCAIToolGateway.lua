-- SPDX-License-Identifier: MIT
SurvivorCompanion = SurvivorCompanion or {}
local SC = SurvivorCompanion
SC.AIToolGateway = SC.AIToolGateway or {}
local G = SC.AIToolGateway

G.PROTOCOL = "sol-ai-1"
G.SCHEMA = 1

local allowed = {
    follow = true,
    stay = true,
    regroup = true,
    retreat = true,
    go_to = true,
 check_room = true,
 open_door = true,
 close_door = true,
 board_vehicle = true,
 exit_vehicle = true,
 designate_target = true,
 avoid_target = true,
 fire_at_will = true,
 hold_fire = true,
 drive_to = true,
 prepare_drive = true,
 drive_stop = true,
 drive_status = true,
}

local function finite(value)
    return type(value) == "number" and value == value
        and value ~= math.huge and value ~= -math.huge
end

local function receipt(requestId, tool, accepted, status, reason)
    return {
        protocol = G.PROTOCOL,
        schema = G.SCHEMA,
        requestId = tostring(requestId or ""),
        tool = tool,
        accepted = accepted == true,
        status = status or (accepted and "accepted" or "rejected"),
        reason = reason,
    }
end

local function commandId(actor)
    if not SC.GameplayUtil or type(SC.GameplayUtil.idOf) ~= "function" then
        return nil
    end
    return SC.GameplayUtil.idOf(actor)
end

local function playerOrDefault(player)
    if player ~= nil then return player end
    if type(getSpecificPlayer) == "function" then
        local ok, value = pcall(getSpecificPlayer, 0)
        if ok then return value end
    end
    return nil
end

local function issue(actor, command, payload, player)
    if not SC.Commands or type(SC.Commands.issue) ~= "function" then
        return false, "commands_unavailable"
    end
    local id = commandId(actor)
    if id == nil then return false, "actor_id_unavailable" end
    local ok, accepted, reason, details = pcall(
        SC.Commands.issue, id, command, payload, playerOrDefault(player))
    if not ok then return false, "command_exception:" .. tostring(accepted) end
    return accepted == true, reason, details
end

local function validateGoTo(args)
    if type(args) ~= "table" then return nil, "arguments_required" end
    local x, y, z = tonumber(args.x), tonumber(args.y), tonumber(args.z or 0)
    if not finite(x) or not finite(y) or not finite(z) then
        return nil, "invalid_coordinates"
    end
    if math.abs(x) > 100000 or math.abs(y) > 100000 or math.abs(z) > 32 then
        return nil, "coordinates_out_of_bounds"
    end
    return { x = x, y = y, z = z }
end

function G.supported()
    return {
        follow = { arguments = {} },
        stay = { arguments = {} },
        regroup = { arguments = {} },
        retreat = { arguments = {} },
        go_to = { arguments = { "x", "y", "z" } },
        check_room = { arguments = { "x", "y", "z" } },
        open_door = { arguments = { "target" } },
        close_door = { arguments = { "target" } },
        board_vehicle = { arguments = { "vehicleId", "seat" } },
        exit_vehicle = { arguments = { "vehicleId" } },
        designate_target = { arguments = { "zombieId" } },
        avoid_target = { arguments = { "zombieId" } },
        fire_at_will = { arguments = {} },
        hold_fire = { arguments = {} },
        -- Driving. The native bridge refuses to take the wheel while the player
        -- sits in the car, so a rescue runs in this order: prepare_drive while
        -- Sol is alone in the driver's seat, the player boards, then drive_to.
        prepare_drive = { arguments = {} },
        drive_to = { arguments = { "x", "y", "speedKmh", "stopShortTiles" } },
        drive_stop = { arguments = {} },
        drive_status = { arguments = {} },
    }
end
function G.execute(actor, request, player)
    if actor == nil then
        return receipt(nil, nil, false, "rejected", "actor_missing")
    end
    if type(request) ~= "table" then
        return receipt(nil, nil, false, "rejected", "request_not_table")
    end

    local requestId = request.requestId
    local tool = request.tool
    if type(requestId) ~= "string" and type(requestId) ~= "number" then
        return receipt(nil, tool, false, "rejected", "request_id_missing")
    end
    if type(tool) ~= "string" or allowed[tool] ~= true then
        return receipt(requestId, tool, false, "rejected", "unsupported_tool")
    end

    -- Driving is handled here rather than through SC.Commands: SCDriving owns
    -- its own ActionSupervisor token, route planning and native lease.
    local args = type(request.arguments) == "table" and request.arguments or {}
    if tool == "prepare_drive" or tool == "drive_to"
        or tool == "drive_stop" or tool == "drive_status" then
        if type(SC.Driving) ~= "table" then
            return receipt(requestId, tool, false, "rejected", "driving_unavailable")
        end
        if tool == "drive_status" then
            local status = SC.Driving.jobStatus(actor)
            local result = receipt(requestId, tool, true, "accepted", "status_ready")
            if type(status) == "table" then
                result.details = tostring(status.phase or status.result or "idle")
            else
                result.details = "idle"
            end
            return result
        end
        if tool == "drive_stop" then
            local ok, why = SC.Driving.release(actor, "ai_requested")
            return receipt(requestId, tool, ok == true,
                ok == true and "accepted" or "rejected", why)
        end
        if tool == "prepare_drive" then
            local ok, why = SC.Driving.start(actor, nil)
            return receipt(requestId, tool, ok == true,
                ok == true and "accepted" or "rejected", why)
        end
        local goal, goalReason = validateGoTo(args)
        if goal == nil then
            return receipt(requestId, tool, false, "rejected", goalReason)
        end
        goal.z = 0
        local options = {
            speedKmh = tonumber(args.speedKmh) or 10,
            stopShortTiles = tonumber(args.stopShortTiles) or 0,
        }
        local ok, why = SC.Driving.drive(actor, goal, options)
        return receipt(requestId, tool, ok == true,
            ok == true and "accepted" or "rejected", why)
    end

    local command, payload, validationReason
    if tool == "go_to" or tool == "check_room" then
        payload, validationReason = validateGoTo(args)
        command = tool == "go_to" and "move_to" or "check_room"
    elseif tool == "open_door" or tool == "close_door" then
        if type(args.target) ~= "table" then
            validationReason = "door_reference_required"
        elseif type(SC.AITargetResolver) ~= "table" then
            validationReason = "target_resolver_unavailable"
        else
            local target, reason = SC.AITargetResolver.resolveDoor(args.target)
            if target then payload = { object = target } else validationReason = reason end
        end
        command = tool
    elseif tool == "board_vehicle" then
        if type(SC.AITargetResolver) ~= "table" then
            validationReason = "target_resolver_unavailable"
        else
            local target, reason = SC.AITargetResolver.resolveVehicle(args.vehicleId or args.sqlId)
            if target then
                local seat = args.seat ~= nil and tonumber(args.seat) or nil
                if seat ~= nil and (seat < 0 or seat ~= math.floor(seat)) then
                    validationReason = "invalid_vehicle_seat"
                else
                    payload = { vehicle = target, seat = seat }
                end
            else
                validationReason = reason
            end
        end
        command = "board_vehicle"
    elseif tool == "exit_vehicle" then
        command = "exit_vehicle"
        if args.vehicleId ~= nil or args.sqlId ~= nil then
            if type(SC.AITargetResolver) ~= "table" then
                validationReason = "target_resolver_unavailable"
            else
                local target, reason = SC.AITargetResolver.resolveVehicle(args.vehicleId or args.sqlId)
                if target then payload = { vehicle = target } else validationReason = reason end
            end
        end
    elseif tool == "designate_target" or tool == "avoid_target" then
        if type(SC.AITargetResolver) ~= "table" then
            validationReason = "target_resolver_unavailable"
        else
            local target, reason = SC.AITargetResolver.resolveZombie(args.zombieId or args.id)
            if target then payload = { target = target } else validationReason = reason end
        end
        command = tool
    else
        command = tool
    end
    if validationReason ~= nil then
        return receipt(requestId, tool, false, "rejected", validationReason)
    end
    local accepted, reason, details = issue(actor, command, payload, player)
    local result = receipt(requestId, tool, accepted,
        accepted and "accepted" or "rejected", reason)
    if type(details) == "string" or type(details) == "number"
        or type(details) == "boolean" then
        result.details = details
    end
    return result
end

function G.health()
    return {
        protocol = G.PROTOCOL,
        schema = G.SCHEMA,
        commands = type(SC.Commands) == "table"
            and type(SC.Commands.issue) == "function",
        utility = type(SC.GameplayUtil) == "table"
            and type(SC.GameplayUtil.idOf) == "function",
    }
end

return G
