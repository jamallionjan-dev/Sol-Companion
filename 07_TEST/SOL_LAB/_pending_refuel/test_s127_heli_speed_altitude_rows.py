from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from test_s125_heli_flight_start import check, fixture


ROOT = Path(__file__).resolve().parents[3]
PENDING = Path(__file__).resolve().parent
GPS = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client" / "SolGPS.lua"
APPLY = PENDING / "apply_s127_heli_speed_altitude_rows.py"


def installer_replay() -> None:
    lab_root = ROOT / "07_TEST" / "SOL_LAB"
    with tempfile.TemporaryDirectory(dir=lab_root) as temporary:
        temp = Path(temporary)
        client = temp / "profile" / "mods" / "Sol_LAB" / "42" / "media" / "lua" / "client"
        client.mkdir(parents=True)
        switches = temp / "profile" / "Lua" / "SolFixes_LAB.txt"
        switches.parent.mkdir()
        switches.write_text("heli_gps=on\nseat_handoff=on\npreserve_me=on\n", encoding="ascii")
        (client / "SolAuthority.lua").write_text("authority remains unchanged\n", encoding="ascii")
        (client / "SolGPS.lua").write_text("old gps\n", encoding="ascii")
        (client / "SolHeliGPS.lua").write_text("old heli\n", encoding="ascii")
        backups = temp / "backups"
        command = [sys.executable, str(APPLY), "--lab-client", str(client), "--lab-switches", str(switches), "--backup-root", str(backups)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        first = {name: hashlib.sha256((client / name).read_bytes()).hexdigest() for name in ("SolGPS.lua", "SolHeliGPS.lua")}
        check("installer backs up both previous Lua files", len(list(backups.glob("*_before_s127_heli_speed_altitude_rows/SolGPS.lua"))) == 1 and len(list(backups.glob("*_before_s127_heli_speed_altitude_rows/SolHeliGPS.lua"))) == 1)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        second = {name: hashlib.sha256((client / name).read_bytes()).hexdigest() for name in first}
        check("installer replay is byte-stable", first == second and "Already installed" in result.stdout)
        check("installer leaves switch and authority files unchanged", switches.read_text(encoding="ascii") == "heli_gps=on\nseat_handoff=on\npreserve_me=on\n" and (client / "SolAuthority.lua").read_text(encoding="ascii") == "authority remains unchanged\n")


def main() -> None:
    lua, heli = fixture(True)
    check("speed preference changes without touching AviationCore before flight", heli.setSpeed("fast") is True and abs(lua.globals().AviationCoreDebug.flightMaxForwardSpeed - 18.0) < 0.0001)
    heli.setDestination(20, 0)
    heli.start()
    check("unready engine does not alter flight configuration", abs(lua.globals().AviationCoreDebug.flightMaxForwardSpeed - 18.0) < 0.0001)
    lua.execute("vehicle.engine=true; runTicks()")
    check("selected fast speed is active once the native engine is ready", abs(lua.globals().AviationCoreDebug.flightMaxForwardSpeed - (65 / 3.6)) < 0.0001)
    check("status reports the selected helicopter speed", heli.status().speed == "fast" and heli.status().targetSpeedKmh == 65)
    heli.setSpeed("slow")
    check("changing speed in flight updates the forward-speed limit", abs(lua.globals().AviationCoreDebug.flightMaxForwardSpeed - (20 / 3.6)) < 0.0001)
    heli.stop("test")
    check("stopping flight restores the exact previous AviationCore value", abs(lua.globals().AviationCoreDebug.flightMaxForwardSpeed - 18.0) < 0.0001)

    gps = GPS.read_text(encoding="ascii")
    render = gps[gps.index("function MapEl:render()"):gps.index("function MapEl:onMouseWheel")]
    speed_row = render[:render.index("if heliMode then")]
    altitude_row = render[render.index("if heliMode then"):render.index('"Marker")')]
    check("speed row is always rendered above helicopter-specific altitude controls", all(f'"{item}"' in speed_row for item in ("Fast", "Normal", "Slow")) and "if heliMode then" in altitude_row and all(f'"{item}"' in altitude_row for item in ("Low", "Medium", "High")))
    check("altitude buttons occupy y=36 under speed row and are not rendered for cars", all(token in altitude_row for token in (", 8, 36,", ", 58, 36,", ", 108, 36,")) and 'if heliMode then' in render)
    check("speed clicks choose helicopter speed only in heli mode and preserve LF road speed for cars", 'HeliGPS.setSpeed(h.arg)' in gps and 'if HeliGPS and HeliGPS.isSolInHelicopter' in gps and 'Ds.setSpeed' in gps)
    check("both staged Lua files remain ASCII", all(path.read_bytes().isascii() for path in (GPS, ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client" / "SolHeliGPS.lua")))
    installer_replay()
    print("s127 helicopter speed and altitude row checks passed")


if __name__ == "__main__":
    main()
