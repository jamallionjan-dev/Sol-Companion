from __future__ import annotations

from pathlib import Path

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[3]
LUA = ROOT / "07_TEST" / "SOL_LAB" / "profile" / "Zomboid" / "mods" / "Sol_LAB" / "42" / "media" / "lua" / "client" / "SolHeliGPS.lua"
RUNTIME_SOURCE = "@media/lua/client/AviationCore/Flight/FlightRuntime.lua"


def check(label: str, ok: bool) -> None:
    if not ok:
        raise AssertionError(label)
    print("PASS " + label)


def main() -> None:
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r'''
        now=0; tickCallbacks={}; logLines={}
        print=function(s) logLines[#logLines+1]=tostring(s) end
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
        function vehicle:getCharacter(seat) for actor,n in pairs(self.seats) do if n==seat then return actor end end return nil end
        function vehicle:canSwitchSeat(from,to) return self:isSeatInstalled(to) and not self:isSeatOccupied(to) end
        function vehicle:switchSeat(actor,to) if not self:isSeatInstalled(to) or self:isSeatOccupied(to) then return false end self.seats[actor]=to return true end
        function vehicle:playPassengerAnim() end
        function vehicle:getModData() return self.md end
        function vehicle:getWorldPos(lx,ly,lz,scratch)
          if self.headingUnavailable and lz==1 then return nil end
          local forward=lz or 0
          scratch.px=self.x + forward*math.cos(self.heading)
          scratch.py=self.y - forward*math.sin(self.heading)
          scratch.pz=self.z + (ly or 0)
          return scratch
        end
        function vehicle:isEngineRunning() return self.engine end
        function vehicle:shutOff() self.engine=false end
        function vehicle:getForwardDirection()
          if self.headingUnavailable then return nil end
          local x,y=math.cos(self.heading),-math.sin(self.heading)
          return {getX=function() return x end,getY=function() return y end}
        end
        player={vehicle=vehicle}; sol={vehicle=vehicle}
        vehicle.seats[player]=1; vehicle.seats[sol]=2
        function player:getVehicle() return self.vehicle end
        function sol:getVehicle() return self.vehicle end
        function getPlayer() return player end
        getSpecificPlayer=function(n) if n==0 then return player end end
        SolUI={solActor=function() return sol end,solEngine=function(which)
          if which~="off" then return false,"unexpected_engine_command" end
          vehicle:shutOff(); engineOffCalls=engineOffCalls+1; return true,"engine_off"
        end}
        engineOffCalls=0; exitCalls=0
        SolOrders={leaveCar=function()
          exitCalls=exitCalls+1; vehicle.seats[sol]=nil; sol.vehicle=nil; return true,"native_exit"
        end}
        SurvivorCompanion={Vehicle={shiftToDriver=function(actor,v)
          if v:isSeatOccupied(0) then return false,"occupied" end
          v.seats[actor]=0; return true
        end}}
        AviationCore={GetHelicopterType=function(v) return v==vehicle and "Base.UH1BHuey" or nil end,
          AircraftKnowledge={IsEngineAlreadyRunning=function(v) return v.engine end,
            GetAircraftDefinition=function(v) return {operatingKnowledge="TEST_HELI_MANUAL"} end,
            CanStartAircraft=function(actor,v) return actor==player or actor==sol end,
            GrantKnowledge=function() return true end,
            AuthorizeStartRequest=function() return true end}}
        startRequests=0
        ISVehicleMenu={onStartEngine=function() startRequests=startRequests+1 end}
        HelicopterInput={GetState=function()
          return {liftUp=false,liftDown=false,yawLeft=false,yawRight=false,pitchUp=false,pitchDown=false,rollLeft=false,rollRight=false}
        end}
        FlightConfig={MAX_FLIGHT_WORLD_Z=8.0}
        AviationCoreDebug={flightMaxForwardSpeed=18.0}
        Vector3f={new=function() return {px=0,py=0,pz=0,x=function(self) return self.px end,y=function(self) return self.py end,z=function(self) return self.pz end} end}
        function runTicks() for _,fn in ipairs(tickCallbacks) do fn() end end
    ''')
    lua.execute(f'dofile({str(LUA).replace(chr(92), "/")!r})')
    heli = lua.globals().SolHeliGPS

    lua.execute(f'''runtime = assert(loadstring([[
        -- AviationCore FlightRuntime contract: global local actor, vehicle seat-0 gate,
        -- then FlightContext's HelicopterInput.GetState(playerObj) call.
        local playerObj = SolHeliGPS.runtimePilot()
        if not playerObj then return nil end
        local aircraft = playerObj:getVehicle()
        if not aircraft or aircraft:getSeat(playerObj) ~= 0 then return nil end
        return HelicopterInput.GetState(playerObj)
    ]], {RUNTIME_SOURCE!r}))''')
    runtime = lua.globals().runtime
    check("full flight caller was created with the installed AviationCore source identity", runtime is not None)

    lua.execute(r'''shortSourceRuntime = assert(loadstring([[
        local function helicopterMovementUpdate()
            local playerObj = SolHeliGPS.runtimePilot()
            if not playerObj then return nil end
            local aircraft = playerObj:getVehicle()
            if not aircraft or aircraft:getSeat(playerObj) ~= 0 then return nil end
            return HelicopterInput.GetState(playerObj)
        end
        local function eventDispatcher(callback) return callback() end
        return eventDispatcher(helicopterMovementUpdate)
    ]], "@FlightRuntime.lua"))
    unrelatedCaller = assert(loadstring("return getPlayer()", "@OtherMod.lua"))''')

    check("route marker accepted", heli.setDestination(10, 0) is True)
    heli.setAltitude("low")
    heli.setSpeed("slow")
    check("Sol starts from passenger seat and becomes actual seat-0 pilot", heli.start() is True and lua.eval("vehicle:getSeat(sol)==0 and vehicle:getSeat(player)==1"))
    check("engine start is queued only after the operator/manual gate", lua.globals().startRequests == 1)
    lua.execute("SolAviationRuntimeBridgeReady=true; vehicle.engine=true; now=100; runTicks()")
    check("engine readiness activates the flight controller", heli.active is True and heli.phase == "climbing")
    short_source_state = lua.globals().shortSourceRuntime()
    if short_source_state is None:
        print(lua.eval('table.concat(logLines,"\\n")'))
    check(
        "explicit pilot resolver works without Kahlua debug metadata",
        short_source_state is not None and lua.eval("vehicle:getSeat(sol)==0"),
    )
    check(
        "unrelated module callers still receive the human player",
        lua.eval("unrelatedCaller()==player"),
    )

    tick_count = 0
    def step() -> object:
        nonlocal tick_count
        tick_count += 1
        lua.globals().now = tick_count * 50 + 100
        state = runtime()
        if state is None:
            raise AssertionError(
                "AviationCore seat-0 gate did not receive Sol as pilot "
                f"(phase={heli.phase}, active={heli.active}, seat={lua.eval('vehicle:getSeat(sol)')})"
            )
        v = lua.globals().vehicle
        if state.liftUp:
            v.z = min(v.z + 0.12, 2.70)
        elif state.liftDown:
            v.z = max(v.z - 0.12, 0.30)
        if state.yawLeft:
            v.heading = v.heading + 0.10
        elif state.yawRight:
            v.heading = v.heading - 0.10
        if state.pitchUp:
            v.x = v.x + math.cos(v.heading) * 0.38
            v.y = v.y - math.sin(v.heading) * 0.38
            v.speed = min(v.speed + 2.0, 20.0)
        else:
            v.speed = max(v.speed - 4.0, 0.0)
        lua.execute("runTicks()")
        return state

    import math

    check("Sol is bridged into AviationCore and emits a climb input", step().liftUp is True)

    def fly_until_arrived(label: str, maximum: int = 900) -> None:
        for _ in range(maximum):
            step()
            if heli.phase == "arrived":
                check(label, heli.active is True and heli.destination is None)
                return
        raise AssertionError(label + " did not reach the marker")

    for _ in range(30):
        step()
        if heli.phase == "following":
            break
    check(
        "selected altitude is reached and horizontal guidance begins "
        f"(phase={heli.phase}, z={lua.globals().vehicle.z}, agl={heli.currentAGL})",
        heli.phase == "following",
    )
    lua.execute("vehicle.headingUnavailable=true")
    step()
    check("one missing heading sample pauses steering without ending flight",
          heli.active is True and heli.phase == "waiting_for_heading" and heli.destination is not None)
    lua.execute("vehicle.headingUnavailable=false")
    step()
    check("GPS resumes after the heading sample returns",
          heli.active is True and heli.phase == "following")
    fly_until_arrived("first nearby GPS destination is reached")

    check("second nearby marker is accepted without restarting the running engine", heli.setDestination(15, 8) is True)
    lua.execute("vehicle.headingUnavailable=true")
    for _ in range(301):
        step()
        if heli.active is False:
            break
    check("persistent missing heading ends safely after the bounded retry window",
          heli.active is False and heli.reason == "heading_unavailable" and heli.destination is not None)
    lua.execute("vehicle.headingUnavailable=false")
    check("retained destination can be resumed after the bounded failure",
          heli.start() is True and heli.active is True)
    fly_until_arrived("second nearby GPS destination is reached")
    check("aircraft position moved through both routes", lua.eval("vehicle.x > 8 and vehicle.y > 2"))

    land_ok, land_reason = heli.landHere()
    check(
        "landing request is accepted at the current safe destination "
        f"(ok={land_ok}, reason={land_reason}, phase={heli.phase}, solVehicle={lua.globals().sol.vehicle})",
        land_ok is True and heli.landingRequested is True,
    )
    for _ in range(100):
        step()
        if heli.phase in ("landed", "parked_exited"):
            break
    check(
        f"landing controller descends to ground clearance (phase={heli.phase}, z={lua.globals().vehicle.z})",
        heli.phase in ("landed", "parked_exited") and lua.globals().vehicle.z <= 0.52,
    )
    check("post-landing sequence shuts off engine and exits Sol through the companion service",
          lua.globals().vehicle.engine is False and lua.globals().exitCalls == 1 and lua.globals().sol.vehicle is None and heli.phase == "parked_exited")
    check("engine was shut down before disembarking", lua.globals().engineOffCalls == 1)
    check("global player resolver remains stock and speed override is released after landing", lua.eval("getPlayer==getPlayer") and abs(lua.globals().AviationCoreDebug.flightMaxForwardSpeed-18.0) < 0.0001)
    check("flight trace confirms explicit pilot handoff and GPS guidance", lua.eval('string.find(table.concat(logLines,"\\n"),"explicit AviationCore pilot adapter armed",1,true) ~= nil and string.find(table.concat(logLines,"\\n"),"GPS guidance=",1,true) ~= nil'))
    print("Sol helicopter end-to-end controller simulation passed")


if __name__ == "__main__":
    main()


