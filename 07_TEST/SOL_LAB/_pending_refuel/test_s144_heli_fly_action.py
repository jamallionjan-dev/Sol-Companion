from __future__ import annotations

import sys
import argparse
from pathlib import Path

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LUA = ROOT / "01_WORK/Sol/42/media/lua/client"
DEFAULT_MIND = ROOT / "05_TOOLS/sol_mind"


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print("PASS " + name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lua", type=Path, default=DEFAULT_LUA)
    parser.add_argument("--mind", type=Path, default=DEFAULT_MIND)
    args = parser.parse_args()
    lua_file = args.lua if args.lua.is_file() else args.lua / "SolActionRegistry.lua"
    authority_file = lua_file.with_name("SolAuthority.lua")
    router_file = args.mind if args.mind.is_file() else args.mind / "model_router.py"
    lua = lua_file.read_text(encoding="utf-8")
    authority = authority_file.read_text(encoding="utf-8")
    router = router_file.read_text(encoding="utf-8")
    start = lua.index('V.sol_heli_fly_marker =')
    end = lua.index('\nV.sol_summon_helicopter =', start)
    action = lua[start:end]
    check("dedicated heli_voice_fly switch is registered", '"heli_voice_fly"' in authority)
    check("action requires heli_gps and heli_voice_fly switches", 'SolAuthority.on("heli_gps") ~= true' in action and 'SolAuthority.on("heli_voice_fly") ~= true' in action)
    check("action requires Sol to be in a helicopter", 'h.isSolInHelicopter() ~= true' in action)
    check("action requires the player in that same vehicle", 'mcall(p, "getVehicle") ~= v' in action)
    check("action refuses when GPS has no selected destination", 'type(status.dest) ~= "table"' in action and 'return false, "no_destination"' in action)
    check("starts through existing GPS/controller entry point", 'run = function() return U.gpsStart(nil, false) end' in action)
    check("Mind routes a distinct phrase to the new action", '"sol_heli_fly_marker"' in router and '"سول طيري على العلامة"' in router)
    check("Mind card teaches flight method and GPS controls", "طيري على العلامة" in router and "السرعة والارتفاع والهبوط من GPS" in router)

    runtime = LuaRuntime(unpack_returned_tuples=True)
    runtime.execute(r'''
        V={}; enabled={heli_gps=true, heli_voice_fly=true};
        SolAuthority={on=function(name) return enabled[name] end}
        vehicle={}
        sol={getVehicle=function() return vehicle end}
        player={getVehicle=function() return vehicle end}
        marker={x=10,y=20}
        SolHeliGPS={start=function() return true end, isSolInHelicopter=function() return inHelicopter end}
        inHelicopter=true; status={dest=marker}; starts=0; lastDest='unset'; lastMode='unset'
        U={gpsStatus=function() return status end,
           gpsStart=function(dest, mode) starts=starts+1; lastDest=dest; lastMode=mode; return true end}
        mcall=function(obj, name) if obj and obj[name] then return obj[name](obj) end return nil end
    ''')
    snippet = lua[start:end]
    runtime.execute(snippet)
    ok, reason = runtime.eval("V.sol_heli_fly_marker.check(sol, player)")
    check("runtime accepts Sol and player in same helicopter with selected marker", ok and reason == "ok")
    runtime.execute("status={dest=nil}")
    ok, reason = runtime.eval("V.sol_heli_fly_marker.check(sol, player)")
    check("runtime refuses without selected GPS marker", not ok and reason == "no_destination")
    runtime.execute("status={dest=marker}; player={getVehicle=function() return {} end}")
    ok, reason = runtime.eval("V.sol_heli_fly_marker.check(sol, player)")
    check("runtime refuses when player is in a different vehicle", not ok and reason == "player_not_in_same_helicopter")
    runtime.execute("player={getVehicle=function() return vehicle end}; inHelicopter=false")
    ok, reason = runtime.eval("V.sol_heli_fly_marker.check(sol, player)")
    check("runtime refuses when Sol is outside the helicopter", not ok and reason == "sol_not_in_helicopter")
    runtime.execute("inHelicopter=true; enabled.heli_voice_fly=false")
    ok, reason = runtime.eval("V.sol_heli_fly_marker.check(sol, player)")
    check("runtime obeys heli_voice_fly switch", not ok and reason == "heli_voice_fly_disabled")
    runtime.execute("enabled.heli_voice_fly=true; enabled.heli_gps=false")
    ok, reason = runtime.eval("V.sol_heli_fly_marker.check(sol, player)")
    check("runtime obeys underlying heli_gps switch", not ok and reason == "heli_voice_fly_disabled")
    runtime.execute("enabled.heli_gps=true; V.sol_heli_fly_marker.run()")
    check("runtime delegates route start to existing GPS control without selecting a new marker", runtime.eval("starts == 1 and lastDest == nil and lastMode == false"))


if __name__ == "__main__":
    main()
