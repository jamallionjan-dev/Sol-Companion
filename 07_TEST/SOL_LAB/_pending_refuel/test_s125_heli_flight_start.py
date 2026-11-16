from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client" / "SolHeliGPS.lua"
APPLY = Path(__file__).resolve().parent / "apply_s125_heli_engine_flight.py"


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print("PASS " + name)


def first(value):
    return value[0] if isinstance(value, tuple) else value


def fixture(player_qualified: bool = True, sol_qualified: bool = False) -> tuple[LuaRuntime, object]:
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        now=0; tickCallbacks={};
        getTimestampMs=function() return now end
        Events={OnTick={Add=function(fn) tickCallbacks[#tickCallbacks+1]=fn end},OnGameStart={Add=function() end}}
        SolAuthority={on=function(name) return name=="heli_gps" end}
        vehicle={x=0,y=0,z=0.5,heading=0,speed=0,seats={},engine=false,md={currentGroundZ=0.4}}
        function vehicle:getX() return self.x end
        function vehicle:getY() return self.y end
        function vehicle:getZ() return 0 end
        function vehicle:getSeat(actor) return self.seats[actor] or -1 end
        function vehicle:getCurrentSpeedKmHour() return self.speed end
        function vehicle:getMaxPassengers() return 4 end
        function vehicle:isSeatInstalled(seat) return seat>=0 and seat<=3 end
        function vehicle:isSeatOccupied(seat) for actor,n in pairs(self.seats) do if n==seat then return true end end return false end
        function vehicle:getCharacter(seat) for actor,n in pairs(self.seats) do if n==seat then return actor end end end
        function vehicle:canSwitchSeat(from,to) return self:isSeatInstalled(to) and not self:isSeatOccupied(to) end
        function vehicle:switchSeat(actor,to) if not self:isSeatInstalled(to) or self:isSeatOccupied(to) then return false end self.seats[actor]=to return true end
        function vehicle:playPassengerAnim() end
        function vehicle:getModData() return self.md end
        -- AviationCore exposes world altitude through getWorldPos():z(); getZ()
        -- is only the floor level. Keep them deliberately different to guard
        -- against the regression that prevented GPS climb completion in-game.
        function vehicle:getWorldPos(lx,ly,lz,scratch)
          local fwd=lz or 0
          scratch.px=self.x + fwd*math.cos(self.heading)
          scratch.py=self.y - fwd*math.sin(self.heading)
          scratch.pz=self.z + (ly or 0)
          return scratch
        end
        function vehicle:isEngineRunning() return self.engine end
        function vehicle:getForwardDirection()
          local x,y=math.cos(self.heading),-math.sin(self.heading)
          return {getX=function() return x end,getY=function() return y end}
        end
        player={vehicle=vehicle}; sol={vehicle=vehicle}; vehicle.seats[player]=1; vehicle.seats[sol]=2
        characterKnowledge={}
        function player:getVehicle() return self.vehicle end
        function sol:getVehicle() return self.vehicle end
        function getPlayer() return player end
        getSpecificPlayer=function(n) if n==0 then return player end end
        SolUI={solActor=function() return sol end}
        SurvivorCompanion={Vehicle={shiftToDriver=function(actor,v) if v:isSeatOccupied(0) then return false,"occupied" end v.seats[actor]=0 return true end}}
        AviationCore={GetHelicopterType=function(v) if v==vehicle then return "TestHeli" end end,AircraftKnowledge={
          IsEngineAlreadyRunning=function(v) return v.engine end,
          GetAircraftDefinition=function(v) if v==vehicle then return {operatingKnowledge="TEST_HELI_OPERATING"} end end,
          CanStartAircraft=function(character,v) local ok=characterKnowledge[character]==true; return ok, ok and nil or {reason="missing_type_knowledge"} end,
          GrantKnowledge=function(character,key,source) characterKnowledge[character]=true; knowledgeGrants=knowledgeGrants+1; grantSource=source; return true end,
          AuthorizeStartRequest=function(character,v,source) return AviationCore.AircraftKnowledge.CanStartAircraft(character,v) end
        }}
        knowledgeGrants=0; grantSource=nil; startRequests=0
        ISVehicleMenu={onStartEngine=function(character) startRequests=startRequests+1; startQueued=true end}
        HelicopterInput={GetState=function() return {liftUp=false,liftDown=false,yawLeft=false,yawRight=false,pitchUp=false,pitchDown=false,rollLeft=false,rollRight=false} end}
        FlightConfig={MAX_FLIGHT_WORLD_Z=8.0}
        AviationCoreDebug={flightMaxForwardSpeed=18.0}
        Vector3f={new=function() return {px=0,py=0,pz=0,x=function(self) return self.px end,y=function(self) return self.py end,z=function(self) return self.pz end} end}
        function runTicks() for _,fn in ipairs(tickCallbacks) do fn() end end
    ''')
    lua.globals().playerQualified = player_qualified
    lua.globals().solQualified = sol_qualified
    lua.execute("if playerQualified then characterKnowledge[player]=true end; if solQualified then characterKnowledge[sol]=true end")
    lua.execute("dofile(" + repr(str(SOURCE).replace("\\", "/")) + ")")
    return lua, lua.globals().SolHeliGPS


def installer_replay() -> None:
    lab_root = ROOT / "07_TEST" / "SOL_LAB"
    with tempfile.TemporaryDirectory(dir=lab_root) as temporary:
        temp = Path(temporary)
        client = temp / "profile" / "mods" / "Sol_LAB" / "42" / "media" / "lua" / "client"
        client.mkdir(parents=True)
        switches = temp / "profile" / "Lua" / "SolFixes_LAB.txt"
        switches.parent.mkdir()
        switches.write_text("heli_gps=on\nseat_handoff=on\npreserve_me=on\n", encoding="ascii")
        (client / "SolAuthority.lua").write_text("keep authority\n", encoding="ascii")
        target = client / "SolHeliGPS.lua"
        target.write_text("old lab copy\n", encoding="ascii")
        backups = temp / "backup"
        command = [sys.executable, str(APPLY), "--lab-client", str(client), "--lab-switches", str(switches), "--backup-root", str(backups)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        installed_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        check("installer preserves original LAB Lua in a dated backup", len(list(backups.glob("*_before_s126_manual_knowledge_share/SolHeliGPS.lua"))) == 1)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        check("installer replay is byte-stable", hashlib.sha256(target.read_bytes()).hexdigest() == installed_hash)
        check("installer leaves authority and all switches unchanged", (client / "SolAuthority.lua").read_text(encoding="ascii") == "keep authority\n" and switches.read_text(encoding="ascii") == "heli_gps=on\nseat_handoff=on\npreserve_me=on\n")


def main() -> None:
    denied, denied_module = fixture(False)
    denied_module.setDestination(20, 0)
    result = denied_module.start()
    check("player without read manual or qualification cannot authorize Sol flight", result[0] is False and denied_module.reason == "operator_missing_type_knowledge")
    check("denied flight never queues engine start", denied.globals().startRequests == 0)
    check("denied flight does not grant Sol fabricated manual knowledge", denied.globals().knowledgeGrants == 0)

    lua, heli = fixture(True)
    lua.execute("originalGetPlayer=getPlayer")
    heli.setDestination(20, 0)
    result = heli.start()
    check("authorized start queues native engine action", result is True and lua.globals().startRequests == 1)
    check("player-read aircraft knowledge is recorded for Sol before native authorization", lua.globals().characterKnowledge[lua.globals().sol] is True and lua.globals().grantSource == "SolHeliGPS:player_manual_read")
    check("route stays inactive until engine actually runs", heli.active is False and heli.phase == "starting_engine")
    lua.execute("playerResolverUntouched=getPlayer==originalGetPlayer")
    check("global player resolver stays unchanged before engine readiness", lua.globals().playerResolverUntouched is True)
    heli.start()
    check("repeated start does not queue duplicate engine actions", lua.globals().startRequests == 1)

    lua.execute("SolAviationRuntimeBridgeReady=true; vehicle.engine=true; runTicks()")
    check("engine readiness activates Sol pilot bridge", heli.active is True and heli.phase == "climbing")
    check("normal helicopter speed is applied only after flight activation", abs(lua.globals().AviationCoreDebug.flightMaxForwardSpeed - (40 / 3.6)) < 0.0001)
    lua.execute("SolAviationRuntimeBridgeReady=true; debug=nil; runtimePilot=SolHeliGPS.runtimePilot(); runtimeRouted=runtimePilot==sol; ordinaryPilot=getPlayer(); ordinaryPreserved=ordinaryPilot==player")
    check("explicit AviationCore pilot handoff works without debug metadata", lua.globals().runtimeRouted is True)
    check("global player resolver remains untouched for unrelated game code", lua.globals().ordinaryPreserved is True)
    check("non-AviationCore callers retain the real local player", lua.globals().ordinaryPreserved is True)
    state = lua.globals().HelicopterInput.GetState(lua.globals().runtimePilot)
    check("low-altitude takeoff climbs without horizontal steering", state.liftUp is True and state.pitchUp is False and state.yawLeft is False and heli.phase == "climbing")
    check("controller uses actual world altitude instead of tile getZ", heli.status().worldZ == 0.5 and lua.globals().vehicle.getZ(lua.globals().vehicle) == 0)

    lua.execute("vehicle.z=2.7")
    state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
    check("GPS steering begins only after altitude band is reached", state.pitchUp is True and heli.phase == "following")
    check("repeated start preserves the active flight phase", first(heli.start()) is True and heli.phase == "following")
    heli.setDestination(0, 20)
    state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
    check("right GPS correction coordinates D yaw with RIGHT bank", state.yawRight is True and state.rollRight is True and state.yawLeft is False and state.rollLeft is False)
    heli.setDestination(0, -20)
    state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
    check("left GPS correction coordinates A yaw with LEFT bank", state.yawLeft is True and state.rollLeft is True and state.yawRight is False and state.rollRight is False)
    heli.setDestination(20, 0)
    state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
    check("aligned GPS course releases yaw and bank while moving forward", state.pitchUp is True and state.yawLeft is False and state.yawRight is False and state.rollLeft is False and state.rollRight is False)
    check("fast speed button raises the helicopter forward-speed target", heli.setSpeed("fast") is True and abs(lua.globals().AviationCoreDebug.flightMaxForwardSpeed - (65 / 3.6)) < 0.0001)
    check("slow speed button lowers the helicopter forward-speed target", heli.setSpeed("slow") is True and abs(lua.globals().AviationCoreDebug.flightMaxForwardSpeed - (20 / 3.6)) < 0.0001)
    check("invalid helicopter speed mode is refused", heli.setSpeed("warp")[0] is False)

    missing_ground, missing_ground_heli = fixture(True)
    missing_ground_heli.setDestination(20, 0)
    missing_ground_heli.start()
    missing_ground.execute("vehicle.engine=true; vehicle.md.currentGroundZ=nil; runTicks()")
    state = missing_ground.globals().HelicopterInput.GetState(missing_ground.globals().sol)
    check("missing ground reference blocks horizontal GPS motion", state.pitchUp is False and missing_ground_heli.active is True)

    timeout, timeout_heli = fixture(True)
    timeout_heli.setDestination(20, 0)
    timeout_heli.start()
    timeout.execute("now=30001; runTicks()")
    check("failed native engine start times out with explicit reason", timeout_heli.phase == "failed" and timeout_heli.reason == "engine_start_timeout")

    lua.execute("HelicopterInput.solHeliGPSWrapped=false; SolHeliGPS.stop('test')")
    check("stopping flight restores AviationCore's prior speed configuration", abs(lua.globals().AviationCoreDebug.flightMaxForwardSpeed - 18.0) < 0.0001)
    lua.execute("proxyRestored=getPlayer==originalGetPlayer")
    check("stop leaves global player resolver unchanged", lua.globals().proxyRestored is True)
    already_qualified, qualified_heli = fixture(False, True)
    qualified_heli.setDestination(20, 0)
    check("Sol's own manual qualification works without relying on player transfer", qualified_heli.start() is True and already_qualified.globals().knowledgeGrants == 0)
    installer_replay()
    print("helicopter authorization and coordinated-guidance checks passed")


if __name__ == "__main__":
    main()
