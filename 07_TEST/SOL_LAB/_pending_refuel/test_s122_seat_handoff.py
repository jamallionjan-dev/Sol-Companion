from __future__ import annotations

import re
from pathlib import Path

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[3]
LUA = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client"
MIND = ROOT / "05_TOOLS" / "sol_mind" / "model_router.py"


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print("PASS " + name)


def extract(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b]


def vehicle_service_checks() -> None:
    source = (LUA / "SCVehicle.lua").read_text(encoding="ascii")
    body = extract(source, "function vehicleService.shiftFromDriver", "function vehicleService.isNativeSeated")
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        reservations, manifests, records = {}, {}, {}
        vehicleService = {}
        SurvivorCompanion = {
          Actor = { isCompanion=function(actor) return actor.companion == true end,
                    stop=function(actor) return actor.stopOk ~= false end },
          Registry = { idOf=function(actor) return actor.id end,
                       byId=function(id) return records[id] end },
          Call = { method=function(object, name, ...)
            local f = object and object[name]
            if type(f) ~= "function" then return false, nil end
            local ok, a, b = pcall(f, object, ...)
            if not ok then return false, nil end
            return true, a, b
          end }
        }
        SC = SurvivorCompanion
        function finite(v, fallback) v=tonumber(v); return v or fallback end
        function invoke(o,n,...) return SC.Call.method(o,n,...) end
        function vehicleIdentity(v) return {id=v.id,script=v.script} end
        function keyFor(i) return tostring(i.id)..":"..tostring(i.script) end
        function seatKey(i,s) return keyFor(i)..":"..tostring(s) end
        function goneFromWorld(v) return v.gone == true end
        function stationary(v) return v.stopped == true, "vehicle_moving" end
        function multiplayerActive() return false end
        function traceBoarding() end
    ''')
    lua.execute(body)
    lua.execute(r'''
        player = {id="player", vehicle=nil}
        sol = {id="sol", companion=true, vehicle=nil}
        vehicle = {id=10, script="TestTracked", stopped=true, occupants={}}
        function vehicle:getId() return self.id end
        function vehicle:getScriptName() return self.script end
        function vehicle:getX() return 1 end
        function vehicle:getY() return 2 end
        function vehicle:getZ() return 0 end
        function vehicle:getSeat(actor)
          for seat, actorAtSeat in pairs(self.occupants) do if actorAtSeat == actor then return seat end end
          return -1
        end
        function vehicle:getMaxPassengers() return 3 end
        function vehicle:isSeatInstalled(seat) return seat >= 0 and seat <= 2 end
        function vehicle:isSeatOccupied(seat) return self.occupants[seat] ~= nil end
        function vehicle:canSwitchSeat(from, to) return self.allowSwitch ~= false end
        function vehicle:switchSeat(actor, to)
          local from = self:getSeat(actor)
          if from < 0 or self.occupants[to] ~= nil then return false end
          self.occupants[from] = nil; self.occupants[to] = actor; return true
        end
        function vehicle:getCharacter(seat) return self.occupants[seat] end
        function vehicle:playPassengerAnim() end
        function sol:getVehicle() return self.vehicle end
        function player:getVehicle() return self.vehicle end
        function sol:getSeat() return vehicle:getSeat(self) end
        function player:getSeat() return vehicle:getSeat(self) end
        sol.vehicle=vehicle; player.vehicle=vehicle
        vehicle.occupants[0]=sol; vehicle.occupants[2]=player
        records.sol={runtime={vehicle={native=true,vehicle=vehicle,seat=0}}}
        reservations["10:TestTracked:0"]="sol"
        manifests["10:TestTracked"]={assignments={sol=0},assignmentBySeat={[0]="sol"}}
    ''')
    ok, reason = lua.eval("vehicleService.shiftFromDriver(sol, vehicle)")
    check("Sol switches from driver to an empty reachable passenger seat", ok is True and reason == "switched_to_passenger_seat_1")
    lua.execute('driverFreed = vehicle:getCharacter(0) == nil; solStillInside = sol:getVehicle() == vehicle and vehicle:getSeat(sol) == 1; playerUnchanged = player:getVehicle() == vehicle and vehicle:getSeat(player) == 2; manifestUpdated = manifests["10:TestTracked"].assignments.sol == 1 and manifests["10:TestTracked"].assignmentBySeat[1] == "sol"; reservationsUpdated = reservations["10:TestTracked:0"] == nil and reservations["10:TestTracked:1"] == "sol"; recordUpdated = records.sol.runtime.vehicle.seat == 1')
    check("driver seat is free after handoff", lua.globals().driverFreed is True)
    check("Sol remains in the same vehicle and the player stays seated", lua.globals().solStillInside is True and lua.globals().playerUnchanged is True)
    check("seat manifest, reservations, and companion runtime are updated", lua.globals().manifestUpdated is True and lua.globals().reservationsUpdated is True and lua.globals().recordUpdated is True)
    lua.execute('vehicle.occupants[0]=sol; vehicle.occupants[1]=nil; vehicle.occupants[2]=player; reservations["10:TestTracked:0"]="sol"; reservations["10:TestTracked:1"]="other"; manifests["10:TestTracked"].assignments.sol=0; manifests["10:TestTracked"].assignmentBySeat={[0]="sol"}; vehicle.stopped=false')
    ok, reason = lua.eval("vehicleService.shiftFromDriver(sol, vehicle)")
    check("moving vehicle refuses handoff without moving anyone", ok is None and reason == "vehicle_moving" and lua.eval("vehicle:getSeat(sol)") == 0)
    lua.execute('vehicle.stopped=true; vehicle.allowSwitch=false; vehicle.occupants[1]=nil; vehicle.occupants[2]=player; reservations["10:TestTracked:1"]=nil')
    ok, reason = lua.eval("vehicleService.shiftFromDriver(sol, vehicle)")
    check("native seat switch is attempted when canSwitchSeat rejects an otherwise empty passenger seat", ok is True and reason == "switched_to_passenger_seat_1" and lua.eval("vehicle:getSeat(sol)") == 1)
    lua.execute('vehicle.occupants[0]=sol; vehicle.occupants[1]={id="other"}; vehicle.occupants[2]=player; reservations["10:TestTracked:0"]="sol"; reservations["10:TestTracked:1"]="other"; manifests["10:TestTracked"].assignments.sol=0; manifests["10:TestTracked"].assignmentBySeat={[0]="sol"}')
    lua.execute('vehicle.stopped=true; vehicle.occupants[1]={id="other"}; vehicle.occupants[2]=player; reservations["10:TestTracked:1"]="other"')
    ok, reason = lua.eval("vehicleService.shiftFromDriver(sol, vehicle)")
    check("no reachable empty seat refuses safely", ok is None and reason == "no_reachable_empty_passenger_seat" and lua.eval("vehicle:getSeat(sol)") == 0)
    lua.execute('vehicle.occupants[1]=nil; vehicle.occupants[2]=nil; reservations["10:TestTracked:1"]=nil; player.vehicle=nil; vehicle.stopped=true; vehicle.occupants[0]=sol')
    ok, reason = lua.eval("vehicleService.shiftFromDriver(sol, vehicle)")
    check("handoff also works when the player is outside and can take the freed driver seat", ok is True and reason == "switched_to_passenger_seat_1" and lua.eval("vehicle:getCharacter(0) == nil") is True)


def action_and_card_checks() -> None:
    source = (LUA / "SolActionRegistry.lua").read_text(encoding="ascii")
    action = extract(source, "V.sol_let_player_drive", "V.sol_sit_beside")
    router = MIND.read_text(encoding="utf-8")
    check("the action requires Sol driving and rejects a player in a different vehicle", all(x in action for x in ("seat_handoff", "sol_not_driving", "player_in_other_vehicle", "player_already_driving")))
    check("the action calls the seat-switch service and does not issue exit", "shiftFromDriver" in action and "exit_vehicle" not in action)
    check("generic requested phrase maps to the dedicated handoff action", '("عطيني القيادة", "sol_let_player_drive", None)' in router)
    check("pilot command maps to the helicopter action", '("سول طيري بالمروحية", "sol_pilot_helicopter", None)' in router)
    check("old steering-wheel wording is replaced by the generic leadership command", '"سول عطيني الدركسيون"' not in router and '("عطيني القيادة", "sol_let_player_drive", None)' in router)
    chat = (ROOT / "05_TOOLS" / "sol_mind" / "chat_service.py").read_text(encoding="utf-8")
    branch = extract(chat, 'if action == "sol_let_player_drive":', 'if action in MR.COMMANDS:')
    check("Mind executes the handoff action directly and reports pending results honestly", all(x in branch for x in ("_player_takes_over", "run_action(self.dir, action", "NEUTRAL_S109", "action_receipt_note(r)")))
    check("vehicle handoff and helicopter pilot command interrupt stale movement tasks", all(x in (LUA / "SolOrders.lua").read_text(encoding="ascii") for x in ("sol_let_player_drive = true", "sol_pilot_helicopter = true")))
    check("the handoff is switch-controlled in the authority", '"seat_handoff"' in (LUA / "SolAuthority.lua").read_text(encoding="ascii"))


if __name__ == "__main__":
    vehicle_service_checks()
    action_and_card_checks()
    print("s122 seat handoff checks passed")
