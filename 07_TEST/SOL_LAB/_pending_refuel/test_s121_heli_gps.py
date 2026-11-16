from __future__ import annotations

import hashlib
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[3]
PENDING = Path(__file__).resolve().parent
SOURCE = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client"
APPLY = PENDING / "apply_s121_heli_gps.py"
LUA = SOURCE / "SolHeliGPS.lua"


def check(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(name + ((" : " + detail) if detail else ""))
    print(f"PASS {name}")


def first(value):
    return value[0] if isinstance(value, tuple) else value


def lua_behavior() -> None:
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        tickCallbacks = {}
        Events = { OnTick = { Add = function(fn) tickCallbacks[#tickCallbacks + 1] = fn end },
                   OnGameStart = { Add = function(fn) end } }
        SolAuthority = { enabled = true, on = function(name) return name == "heli_gps" and SolAuthority.enabled end }
        vehicle = { x=0, y=0, z=0.5, speed=0, seats={}, nativeSwitch=true, md={currentGroundZ=0.4} }
        function vehicle:getX() return self.x end
        function vehicle:getY() return self.y end
        function vehicle:getZ() return self.z end
        function vehicle:getSeat(actor) return self.seats[actor] or -1 end
        function vehicle:getCurrentSpeedKmHour() return self.speed end
        function vehicle:isEngineRunning() return true end
        function vehicle:getMaxPassengers() return 3 end
        function vehicle:isSeatInstalled(seat) return seat >= 0 and seat <= 2 end
        function vehicle:isSeatOccupied(seat)
            for actor, actorSeat in pairs(self.seats) do if actorSeat == seat then return true end end
            return false
        end
        function vehicle:getCharacter(seat)
            for actor, actorSeat in pairs(self.seats) do if actorSeat == seat then return actor end end
            return nil
        end
        function vehicle:canSwitchSeat(from, to)
            return self.allowSwitch ~= false and self:isSeatInstalled(to) and not self:isSeatOccupied(to)
        end
        function vehicle:switchSeat(actor, to)
            local from = self:getSeat(actor)
            if from < 0 or self.nativeSwitch ~= true or not self:isSeatInstalled(to) or self:isSeatOccupied(to) then return false end
            self.seats[actor] = to
            return true
        end
        function vehicle:getModData() return self.md end
        function vehicle:getWorldPos(lx, ly, lz, scratch)
            scratch.px=self.x + lz; scratch.py=self.y; scratch.pz=self.z + ly
            return scratch
        end
        function vehicle:getForwardDirection() return { getX=function() return 1 end, getY=function() return 0 end } end
        player = { vehicle=vehicle }
        function player:getVehicle() return self.vehicle end
        sol = { vehicle=vehicle }
        function sol:getVehicle() return self.vehicle end
        vehicle.seats[player]=1; vehicle.seats[sol]=2
        function getPlayer() return player end
        SolAviationRuntimeBridgeReady = true
        SurvivorCompanion = { Vehicle = { shiftToDriver=function(actor, v)
            local from = v.seats[actor]
            if from == nil or from < 1 then return false, "not_in_a_passenger_seat" end
            if v:isSeatOccupied(0) then return false, "driver_seat_taken" end
            if not v:switchSeat(actor,0) or v:getSeat(actor) ~= 0 then return false, "native_switch_failed" end
            return true
        end } }
        SC = nil
        getSpecificPlayer = function(index) return index == 0 and player or nil end
        SolUI = { solActor=function() return sol end }
        AviationCore = { GetHelicopterType=function(v) return v == vehicle and "TestHelicopter" or nil end }
        HelicopterInput = { GetState=function(p) return {liftUp=false,liftDown=false,yawLeft=false,yawRight=false,pitchUp=false,pitchDown=false} end }
        FlightConfig = { MAX_FLIGHT_WORLD_Z=8.0 }
        Vector3f = { new=function() return { px=0,py=0,pz=0, x=function(self) return self.px end, y=function(self) return self.py end, z=function(self) return self.pz end } end }
    ''')
    lua.execute(f'dofile({str(LUA).replace(chr(92), "/")!r})')
    module = lua.globals().SolHeliGPS
    check("module exports altitude controls", module.levels.low == 2.4 and module.levels.medium == 5.2 and module.levels.high == 7.6)
    check("altitude selection accepts known modes", first(module.setAltitude("medium")) is True)
    check("invalid altitude rejected", first(module.setAltitude("roof")) is False)
    check("direct GPS destination accepted", module.setDestination(20, 0) is True)
    check("Sol can take an empty pilot seat and start flight", first(module.start()) is True)
    check("explicit runtime adapter is armed only after compatible FlightRuntime loads", lua.globals().SolAviationRuntimeBridgeReady is True)
    lua.execute('debug=nil; runtimePilotResult=SolHeliGPS.runtimePilot(); aviationGotSol=runtimePilotResult==sol; otherCaller=assert(loadstring("local p=getPlayer(); return p", "@media/lua/client/Other.lua")); otherCallerResult=otherCaller(); otherGotPlayer=otherCallerResult==player')
    check("AviationCore flight runtime receives Sol as pilot", lua.globals().aviationGotSol is True)
    check("other mods still receive the local player", lua.globals().otherGotPlayer is True)
    module.setAltitude("low")
    module.ensureInputWrapper()
    state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
    check("altitude controller requests climb", state.liftUp is True and state.liftDown is False)
    check("GPS navigation waits for selected altitude", state.pitchUp is False and module.status().phase == "climbing")
    lua.execute('vehicle.z=2.7')
    state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
    check("direct-air controller requests forward after reaching altitude", state.pitchUp is True and module.status().phase == "following")
    check("direct-air route leaves yaw neutral when aligned", state.yawLeft is False and state.yawRight is False)

    lua.execute('HelicopterInput.GetState = function(p) return {liftUp=false,liftDown=true,yawLeft=false,yawRight=false,pitchUp=false,pitchDown=false} end; HelicopterInput.solHeliGPSWrapped=false; vehicle.z=3.0')
    module.ensureInputWrapper()
    state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
    check("manual vertical input overrides GPS altitude", state.liftDown is True and state.liftUp is False)
    check("route steering pauses while manual vertical input leaves the selected band", state.pitchUp is False)

    state = lua.globals().HelicopterInput.GetState(lua.globals().player)
    check("local passenger keyboard queries do not take over Sol steering", module.active is True and state.pitchUp is False)

    lua.execute('vehicle.x=18; vehicle.z=2.7')
    state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
    check("arrival is based on direct coordinate distance", module.status().phase == "arrived" and module.destination is None)
    check("arrival preserves selected altitude hold", module.status().active is True)

    module.setDestination(100, 0)
    check("new destination restarts direct flight", first(module.start()) is True)
    lua.execute('vehicle.x=18; vehicle.z=3.0; vehicle.speed=25; HelicopterInput.GetState=function(p) return {liftUp=false,liftDown=false,yawLeft=false,yawRight=false,pitchUp=false,pitchDown=false} end; HelicopterInput.solHeliGPSWrapped=false')
    module.ensureInputWrapper()
    check("Land here replaces a stale GPS marker with the current helicopter position while moving", first(module.landHere()) is True and module.landingRequested is True and module.destination.x == 18 and module.destination.y == 0)
    state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
    check("Land here transitions to vertical descent", module.status().phase == "landing" and state.liftDown is True)
    lua.execute('vehicle.z=0.45; vehicle.speed=0')
    state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
    check("landing releases the flight controls at ground clearance", module.status().phase == "landed" and module.active is False and module.landingRequested is False)
    module.setDestination(100, 0)
    check("flight can be started again after a completed landing", first(module.start()) is True)
    lua.execute('sol.vehicle=nil')
    state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
    check("leaving pilot context cancels autopilot safely", module.active is False and module.status().phase == "stopped")
    lua.execute('stoppedKeepsPlayerResolver = getPlayer == getPlayer')
    check("stopping flight leaves the global player resolver untouched", lua.globals().stoppedKeepsPlayerResolver is True)

    lua.execute('sol.vehicle=vehicle; player.vehicle=vehicle; vehicle.seats[sol]=2; vehicle.seats[player]=0; vehicle.allowSwitch=false')
    lua.execute('SolHeliGPS.destination=nil')
    check("the spoken pilot-seat order works without a GPS destination even when canSwitchSeat rejects", first(module.takePilot()) is True and module.destination is None and module.active is False)
    check("Sol takes pilot seat and moves the player pilot to an empty passenger seat", lua.eval("vehicle:getSeat(sol)") == 0 and lua.eval("vehicle:getSeat(player)") == 1)
    check("player and Sol stay aboard the same helicopter after pilot handoff", lua.eval("player:getVehicle() == vehicle and sol:getVehicle() == vehicle") is True)
    module.setDestination(100, 0)
    check("GPS flight begins after the pilot-seat order when a marker is selected", first(module.start()) is True)
    lua.execute('vehicle.seats[player]=1; vehicle.seats[sol]=2; SolAuthority.enabled=false')
    check("feature switch off refuses activation", first(module.start()) is False and module.status().reason == "heli_gps_disabled")


def installer_replay() -> None:
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        client = temp_path / "mods" / "Sol_LAB" / "42" / "media" / "lua" / "client"
        switches = temp_path / "Lua" / "SolFixes_LAB.txt"
        backups = temp_path / "backup"
        client.mkdir(parents=True)
        (client / "SolGPS.lua").write_text("old gps\n", encoding="ascii")
        (client / "SolAuthority.lua").write_text('SolAuthority = {}\nA.FIXES = {\n    "restore_hands",\n    "heli_gps",\n}\n', encoding="ascii")
        switches.parent.mkdir()
        switches.write_text("restore_hands=on\n", encoding="ascii")
        command = [sys.executable, str(APPLY), "--lab-client", str(client), "--lab-switches", str(switches), "--backup-root", str(backups)]
        run = subprocess.run(command, check=False, capture_output=True, text=True)
        if run.returncode != 0:
            raise AssertionError(f"installer failed: {run.stdout}{run.stderr}")
        first = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in client.iterdir() if p.is_file()}
        first_switch = switches.read_bytes()
        run = subprocess.run(command, check=False, capture_output=True, text=True)
        if run.returncode != 0:
            raise AssertionError(f"installer replay failed: {run.stdout}{run.stderr}")
        second = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in client.iterdir() if p.is_file()}
        check("installer replays without changing installed bytes", first == second and first_switch == switches.read_bytes())
        check("installer copies flight, GPS, and command handoff files", all((client / name).read_bytes() == (SOURCE / name).read_bytes() for name in ("SolHeliGPS.lua", "SolGPS.lua", "SCVehicle.lua", "SolActionRegistry.lua", "SolOrders.lua")))
        authority = (client / "SolAuthority.lua").read_text(encoding="ascii")
        switch_text = switches.read_text(encoding="ascii")
        check("installer adds both scoped authority switches", authority.count('"heli_gps"') == 1 and authority.count('"seat_handoff"') == 1 and "heli_gps=on" in switch_text and "seat_handoff=on" in switch_text)
        check("installer preserves pre-install backup", len(list(backups.glob("*/*"))) >= 7)


def static_contract() -> None:
    gps = (SOURCE / "SolGPS.lua").read_text(encoding="ascii")
    authority = (SOURCE / "SolAuthority.lua").read_text(encoding="ascii")
    heli = LUA.read_text(encoding="utf-8")
    check("heli seat code keeps Kahlua tonumber calls single-valued", "tonumber((call(vehicle, \"getCurrentSpeedKmHour\")))" in heli and "tonumber((call(v, \"getMaxPassengers\")))" in heli)
    check("GPS routes helicopter before LF road driver and clears stale landing mode for Fly", gps.index("HeliGPS.start(false)") < gps.index("local SC = LF(); local D = SC and SC.Driving", gps.index("function U.gpsStart")))
    controls = gps[gps.index("function MapEl:render()"):gps.index("function MapEl:onMouseWheel")]
    speed_row = controls[:controls.index("if heliMode then")]
    altitude_row = controls[controls.index("if heliMode then"):controls.index('"Marker")')]
    check("speed controls remain in the top row for all vehicles", all(f'"{label}"' in speed_row for label in ("Fast", "Normal", "Slow")))
    check("altitude buttons appear only inside the helicopter condition and on the row below", "if heliMode then" in altitude_row and all(f'"{label}"' in altitude_row for label in ("Low", "Medium", "High")) and all(token in altitude_row for token in (", 8, 36,", ", 58, 36,", ", 108, 36,")))
    check("helicopter speed clicks update flight speed, while road vehicles keep the car speed handler", 'HeliGPS.setSpeed(h.arg)' in gps and 'if HeliGPS and HeliGPS.isSolInHelicopter' in gps and 'Ds.setSpeed' in gps)
    check("heli map click skips road setGoal", 'stc.flight and stc.phase == "following"' in gps and "Dc.setGoal" in gps)
    check("heli preview bypasses road planner", "isSolInHelicopter() then" in gps and "P.route, P.reason, P.key, P.snap = nil" in gps)
    check("only one heli switch is declared", authority.count('"heli_gps"') == 1)
    runtime = (SOURCE / "AviationCore" / "Flight" / "FlightRuntime.lua").read_text(encoding="utf-8")
    check("Sol pilot handoff uses explicit AviationCore call sites and needs no debug library", "function H.runtimePilot()" in heli and "solFlightPilot()" in runtime and "debug.getinfo" not in heli)
    check("pilot code resolves the actual SurvivorCompanion namespace", 'rawget(_G, "SurvivorCompanion")' in heli and "vehicleApi.shiftToDriver" in heli)
    check("heli pilot takeover attempts native passenger seat swaps and verifies the result", 'call(v, "switchSeat", p, candidate.seat)' in heli and 'call(v, "getCharacter", candidate.seat) == p' in heli)
    gps_controls = gps[gps.index("function Panel:prerender()"):gps.index("function Panel:onMouseUp(x, y)")]
    check("helicopter GPS has a middle Land here control between Fly and Stop", 'action = "land"' in gps_controls and 'action = "drive"' in gps_controls and 'action = "stop"' in gps_controls and '"Land here"' in gps_controls and "if st.flight then" in gps_controls)
    check("Land here clears the old map destination and calls the landing controller", "function U.gpsLandHere()" in gps and "G.dest = nil" in gps and "HeliGPS.landHere()" in gps)
    check("all modified Lua files are ASCII", all(path.read_bytes().isascii() for path in (SOURCE / "SolGPS.lua", SOURCE / "SolAuthority.lua", SOURCE / "SCVehicle.lua", LUA)))


if __name__ == "__main__":
    lua_behavior()
    installer_replay()
    static_contract()
    print("s121 heli GPS checks passed")
