from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client"
FILES = ("SolGPS.lua", "SolHeliGPS.lua")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Install combined s126+s127 helicopter fix into SOL_LAB only.")
    parser.add_argument("--lab-client", type=Path, required=True)
    parser.add_argument("--lab-switches", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    client = args.lab_client.resolve()
    switches = args.lab_switches.resolve()
    backup_root = args.backup_root.resolve()
    lab_root = (ROOT / "07_TEST" / "SOL_LAB").resolve()
    if any(not path.is_relative_to(lab_root) for path in (client, switches, backup_root)):
        raise SystemExit("Refusing: LAB client, switches, and backups must remain inside SOL_LAB.")
    if not client.is_dir() or not (client / "SolAuthority.lua").is_file():
        raise SystemExit("Refusing: installed LAB client or SolAuthority.lua is missing.")
    if not all((SOURCE / name).is_file() for name in FILES):
        raise SystemExit("Refusing: one or more staged source files are missing.")
    switch_lines = switches.read_text(encoding="utf-8").splitlines() if switches.is_file() else []
    switch_values = {line.split("=", 1)[0].strip(): line.split("=", 1)[1].strip()
                     for line in switch_lines if "=" in line}
    if switch_values.get("heli_gps") != "on" or switch_values.get("seat_handoff") != "on":
        raise SystemExit("Refusing: expected heli_gps=on and seat_handoff=on in existing LAB switches.")

    targets = [client / name for name in FILES]
    if all(target.is_file() and sha(target) == sha(SOURCE / name)
           for name, target in zip(FILES, targets)):
        print("Already installed: both LAB Lua files match staged sources; no changes made.")
        return
    if args.dry_run:
        for name, target in zip(FILES, targets):
            print(f"COPY {SOURCE / name} -> {target}")
        print(f"KEEP switches unchanged: {switches}")
        print(f"BACKUP root: {backup_root}")
        return

    backup = backup_root / (dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_before_s127_heli_speed_altitude_rows")
    backup.mkdir(parents=True, exist_ok=False)
    for item in (*targets, switches, client / "SolAuthority.lua"):
        if item.exists():
            shutil.copy2(item, backup / item.name)
    for name, target in zip(FILES, targets):
        shutil.copy2(SOURCE / name, target)
        if sha(target) != sha(SOURCE / name):
            raise SystemExit(f"Installed bytes mismatch: {name}")
        print(f"{name} installed sha256={sha(target)}")
    print(f"BACKUP {backup}")
    print("SolFixes_LAB.txt unchanged; heli_gps remains the owner switch.")
    print("SolAuthority.lua unchanged.")


if __name__ == "__main__":
    main()
