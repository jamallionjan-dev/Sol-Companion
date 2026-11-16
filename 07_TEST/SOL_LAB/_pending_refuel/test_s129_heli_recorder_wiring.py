"""Exercises the actual AviationCore-input wrapper into the dedicated file-backed examiner."""
from pathlib import Path
from lupa import lua51 as L

ROOT = Path(__file__).resolve().parents[3]
CLIENT = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client"

lua = L.LuaRuntime(encoding=None)
lua.execute(r'''
clockMs = 1000
files = {}
disk = {}
tickCallbacks = {}
Events = { OnTick = { Add = function(fn) tickCallbacks[#tickCallbacks+1] = fn end },
           OnGameStart = { Add = function(_) end } }
SolLab = { active = true }
SolAuthority = { on = function(name) return name == "drive_record" or name == "heli_gps" end }
getTimestampMs = function() return clockMs end
getFileWriter = function(name, _, append)
  local prior = disk[name] or ""
  local w = { data = "", closed = false }
  w.write = function(self, text) self.data = self.data .. text end
  w.close = function(self) self.closed = true; disk[name] = (append and prior or "") .. self.data end
  files[name] = w
  return w
end
localPlayer = nil
getSpecificPlayer = function(n) if n == 0 then return localPlayer end end
Vector3f = { new = function() return { x=function() return 10 end, y=function() return 20 end,
                                        z=function() return 1 end } end }
vehicle = { seat = 0, altitude = 1, ground = 0.4 }
function vehicle:getSeat(_) return self.seat end
function vehicle:getWorldPos(_, _, _, _) return { x=function() return 10 end,
    y=function() return 20 end, z=function() return self.altitude end } end
function vehicle:getModData() return { currentGroundZ = self.ground } end
function vehicle:getId() return 7 end
function vehicle:getScriptName() return "Base.UH1BHuey" end
function vehicle:getCurrentSpeedKmHour() return 0 end
function vehicle:getForwardVector() return { x=function() return 1 end, z=function() return 0 end } end
localPlayer = { vehicle=vehicle, getVehicle=function(self) return self.vehicle end }
AviationCore = { GetHelicopterType=function(v) if v == vehicle then return "UH1B" end end }
FlightConfig = { GetCorrectedSkidAGL=function(z,g) return z-g-0.6 end }
HelicopterInput = { GetState=function() return { liftUp=true, liftDown=false, yawLeft=false, yawRight=false,
    pitchUp=false, pitchDown=false, rollLeft=false, rollRight=false } end }
''')

lua.execute(f'dofile("{(CLIENT / "SolHeliExaminer.lua").as_posix()}")')
lua.execute(f'dofile("{(CLIENT / "SolHeliGPS.lua").as_posix()}")')
lua.globals().SolHeliGPS.ensureInputWrapper()
lua.globals().HelicopterInput.GetState(lua.globals().localPlayer)
name, durableHeader = lua.eval('function() local n=next(disk); return n, disk[n] end')()
assert durableHeader.decode().startswith("ms,vehicle_id,script,seat,controls"), "header must be on disk before takeoff"
lua.execute('clockMs=1100; vehicle.altitude=2; HelicopterInput.GetState(localPlayer)')
lua.execute('clockMs=2000; vehicle.altitude=3; HelicopterInput.GetState(localPlayer)')
assert lua.eval('function() local n=next(disk); return #disk[n] end')() > len(durableHeader), "flight samples must be durable before capture close"
lua.execute('clockMs=2100; localPlayer.vehicle=nil; tickCallbacks[1]()')

name, data, closed, diskData = lua.eval('function() local n=next(files); local d=next(disk); return n, files[n].data, files[n].closed, disk[d] end')()
assert name.decode().startswith("SolHeliExaminer_")
assert closed is True, "leaving pilot seat must flush and close the user's flight record"
rows = diskData.decode().strip().splitlines()
assert len(rows) == 4, f"expected header plus three pilot samples, received {len(rows)}"
assert all("W=true" in row for row in rows[1:])
assert ",1.0000," in rows[1] and ",2.0000," in rows[2] and ",3.0000," in rows[3]
assert all(len(row.split(",")) == 14 for row in rows), "every sample must include both heading components"
assert rows[1].endswith(",1.0000,0.0000"), "forward heading must preserve both vector components"
print("s129 wiring PASS: pilot input -> durable complete samples -> lifecycle close after exit")
