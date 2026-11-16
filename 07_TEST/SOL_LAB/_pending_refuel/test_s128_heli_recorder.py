"""Runtime-shaped Lua harness for the passive helicopter flight examiner."""
from pathlib import Path
from lupa import lua51 as L

SOURCE = Path(__file__).resolve().parents[3] / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client" / "SolDriveRecorder.lua"
lua = L.LuaRuntime(encoding=None)
lua.execute(r'''
clockMs = 1000
files = {}
Events = { OnTick = { Add = function(_) end } }
SolLab = { active = true }
SolAuthority = { on = function(name) return name == "drive_record" end }
FlightConfig = { GetCorrectedSkidAGL = function(z, ground) return z - ground - 0.6 end }
Vector3f = { new = function() return {} end }
getTimestampMs = function() return clockMs end
getFileWriter = function(name, _, _)
    local w = { data = "", closed = false }
    w.write = function(self, s) self.data = self.data .. s end
    w.close = function(self) self.closed = true end
    files[name] = w
    return w
end
vehicle = {
    altitude = 1.2, x = 7590.5, y = 8467.2, ground = 0.4, seat = 0, speed = 0,
    getSeat = function(self, _) return self.seat end,
    getWorldPos = function(self, _, _, _, _) return {
        x = function(_) return self.x end,
        y = function(_) return self.y end,
        z = function(_) return self.altitude end,
    } end,
    getModData = function(self) return { currentGroundZ = self.ground } end,
    getId = function(_) return 254 end,
    getScriptName = function(_) return "Base.UH1BHuey" end,
    getCurrentSpeedKmHour = function(self) return self.speed end,
    getForwardVector = function(_) return { x = function(_) return 0.8 end, z = function(_) return 0.6 end } end,
}
player = { vehicle = vehicle, getVehicle = function(self) return self.vehicle end }
getSpecificPlayer = function(_) return player end
AviationCore = { GetHelicopterType = function(_) return "UH1B" end }
''')

lua.execute(SOURCE.read_text(encoding="utf-8"))
lua.execute(r'''
SolDriveRecorder.recordHelicopter(player, { liftUp=true, liftDown=false, yawLeft=false, yawRight=false,
    pitchUp=false, pitchDown=false, rollLeft=false, rollRight=false })
clockMs = 1100; vehicle.altitude = 2.2; vehicle.x = 7590.8
SolDriveRecorder.recordHelicopter(player, { liftUp=true, liftDown=false, yawLeft=true, yawRight=false,
    pitchUp=false, pitchDown=false, rollLeft=false, rollRight=false })
clockMs = 1200; vehicle.altitude = 4.0; vehicle.x = 7591.1; vehicle.speed = 12.5
SolDriveRecorder.recordHelicopter(player, { liftUp=false, liftDown=false, yawLeft=false, yawRight=true,
    pitchUp=true, pitchDown=false, rollLeft=false, rollRight=true })
clockMs = 1300; vehicle.seat = 1
SolDriveRecorder.recordHelicopter(player, { liftUp=false })
''')

name, data, closed = lua.eval("function() local k = next(files); return k, files[k].data, files[k].closed end")()
assert name.decode().startswith("SolHeliFlight_Record_"), name
assert closed is True, "leaving pilot seat should flush and close the flight file"
text = data.decode()
lines = text.strip().splitlines()
assert lines[0].split(",")[7:12] == ["world_altitude_z", "ground_z", "raw_agl", "skid_agl", "skid_agl_method"]
assert len(lines) == 4, f"expected header + 3 samples, got {len(lines)}"
assert "W=true" in lines[1] and "A=true" in lines[2] and "D=true" in lines[3]
assert ",1.2000,0.4000,0.8000,0.2000,AviationCore," in lines[1], lines[1]
assert ",4.0000,0.4000,3.6000,3.0000,AviationCore,18.0000," in lines[3], lines[3]
print("s128 helicopter examiner PASS: 10Hz samples, world altitude, raw/corrected AGL, vertical rate, controls, pilot-seat close/flush")
