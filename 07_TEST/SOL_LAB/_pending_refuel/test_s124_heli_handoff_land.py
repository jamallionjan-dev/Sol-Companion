from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[3]
PENDING = Path(__file__).resolve().parent
SOURCE = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client"
APPLY = PENDING / "apply_s124_heli_handoff_land.py"
FILES = ("SolGPS.lua", "SolHeliGPS.lua", "SCVehicle.lua", "SolActionRegistry.lua", "SolOrders.lua")


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print("PASS " + name)


def lua_compile() -> None:
    lua = LuaRuntime(unpack_returned_tuples=True)
    for name in ("SolGPS.lua", "SolHeliGPS.lua", "SCVehicle.lua"):
        path = str(SOURCE / name).replace("\\", "/").replace("'", "\\'")
        lua.execute(f"assert(loadfile('{path}'))")
        print(f"PASS Lua 5.1 compile: {name}")


def installer_replay() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        client = root / "profile" / "mods" / "Sol_LAB" / "42" / "media" / "lua" / "client"
        switches = root / "profile" / "Lua" / "SolFixes_LAB.txt"
        backups = root / "backup"
        client.mkdir(parents=True)
        (client / "SolAuthority.lua").write_text('SolAuthority = {}\nA.FIXES = {\n    "heli_gps",\n    "seat_handoff",\n}\n', encoding="ascii")
        switches.parent.mkdir()
        switches.write_text("heli_gps=off\nseat_handoff=off\npreserve_me=on\n", encoding="ascii")
        command = [sys.executable, str(APPLY), "--lab-client", str(client), "--lab-switches", str(switches), "--backup-root", str(backups)]
        for run_number in (1, 2):
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            installed = {name: hashlib.sha256((client / name).read_bytes()).hexdigest() for name in FILES}
            if run_number == 1:
                first = installed
                check("installer backs up the existing lab set", len(list(backups.glob("*_before_s124_heli_handoff_land"))) == 1)
            else:
                check("installer replay is byte-stable", installed == first)
        switch_text = switches.read_text(encoding="ascii")
        check("installer enables only the scoped heli and seat fixes while preserving unrelated switches", "heli_gps=on" in switch_text and "seat_handoff=on" in switch_text and "preserve_me=on" in switch_text)
        check("installer leaves the LAB authority definition intact", '"heli_gps"' in (client / "SolAuthority.lua").read_text(encoding="ascii"))


if __name__ == "__main__":
    lua_compile()
    installer_replay()
    print("s124 batch checks passed")
