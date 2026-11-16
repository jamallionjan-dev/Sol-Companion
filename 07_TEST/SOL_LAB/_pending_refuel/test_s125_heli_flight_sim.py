from __future__ import annotations

from test_s125_heli_flight_start import check, fixture


def main() -> None:
    lua, heli = fixture(True)
    heli.setAltitude("low")
    heli.setDestination(20, -20)
    assert heli.start() is True
    lua.execute("vehicle.engine=true; runTicks()")

    max_frames = 700
    for frame in range(max_frames):
        state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
        lua.globals().simInput = state
        lua.execute(r'''
            if simInput.liftUp then vehicle.z=vehicle.z+0.06 end
            if simInput.liftDown then vehicle.z=vehicle.z-0.06 end
            if simInput.yawLeft then vehicle.heading=vehicle.heading+0.04 end
            if simInput.yawRight then vehicle.heading=vehicle.heading-0.04 end
            if simInput.pitchUp then
                vehicle.x=vehicle.x+0.12*math.cos(vehicle.heading)
                vehicle.y=vehicle.y-0.12*math.sin(vehicle.heading)
            end
            now=now+50
        ''')
        if heli.phase == "arrived":
            break
    check("flight simulation coordinates yaw and bank to reach an off-axis GPS destination", heli.phase == "arrived" and abs(heli.status().agl - heli.levels.low) <= 0.25 and abs(heli.status().distance or 0) == 0)
    check("flight simulation changes both map coordinates during the turn", lua.globals().vehicle.x >= 10 and lua.globals().vehicle.y <= -10)

    assert heli.landHere()[0] is True
    for frame in range(160):
        state = lua.globals().HelicopterInput.GetState(lua.globals().sol)
        lua.globals().simInput = state
        lua.execute(r'''
            if simInput.liftUp then vehicle.z=vehicle.z+0.06 end
            if simInput.liftDown then vehicle.z=vehicle.z-0.06 end
            if simInput.yawLeft then vehicle.heading=vehicle.heading+0.04 end
            if simInput.yawRight then vehicle.heading=vehicle.heading-0.04 end
            if simInput.pitchUp then
                vehicle.x=vehicle.x+0.12*math.cos(vehicle.heading)
                vehicle.y=vehicle.y-0.12*math.sin(vehicle.heading)
            end
            now=now+50
        ''')
        if heli.phase == "landed":
            break
    status = heli.status()
    check("flight simulation lands at the selected current position", heli.phase == "landed" and (status.agl or 99) <= 0.22)
    print(f"s132 coordinated flight simulation passed: route={lua.globals().vehicle.x:.2f},{lua.globals().vehicle.y:.2f}, AGL={heli.status().agl:.2f}, phase={heli.phase}")


if __name__ == "__main__":
    main()
