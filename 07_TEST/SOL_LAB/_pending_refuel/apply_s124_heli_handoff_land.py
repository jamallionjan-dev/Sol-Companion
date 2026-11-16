from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client"
FILES = ("SolGPS.lua", "SolHeliGPS.lua", "SCVehicle.lua", "SolActionRegistry.lua", "SolOrders.lua")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch_switches(path: Path) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines()
    for name in ("heli_gps", "seat_handoff"):
        found = [i for i, line in enumerate(lines) if line.strip().startswith(name + "=")]
        if len(found) > 1:
            raise SystemExit(f"duplicate {name} entries in {path}")
        if found:
            lines[found[0]] = name + "=on"
        else:
            lines.append(name + "=on")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="ascii", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install the s124 seat/landing batch into SOL_LAB only.")
    parser.add_argument("--lab-client", type=Path, required=True)
    parser.add_argument("--lab-switches", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.lab_client.is_dir():
        raise SystemExit(f"LAB client directory not found: {args.lab_client}")
    missing = [name for name in FILES if not (SOURCE / name).is_file()]
    if missing:
        raise SystemExit("staged source missing: " + ", ".join(missing))
    authority = args.lab_client / "SolAuthority.lua"
    if not authority.is_file():
        raise SystemExit(f"LAB authority file missing: {authority}")

    targets = {name: args.lab_client / name for name in FILES}
    targets["SolFixes_LAB.txt"] = args.lab_switches
    if args.dry_run:
        for name in FILES:
            print(f"COPY {SOURCE / name} -> {targets[name]}")
        print(f"KEEP authority unchanged: {authority}")
        print(f"SET heli_gps=on and seat_handoff=on: {args.lab_switches}")
        return

    backup = args.backup_root / (dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_before_s124_heli_handoff_land")
    backup.mkdir(parents=True, exist_ok=False)
    for name, target in targets.items():
        if target.exists():
            shutil.copy2(target, backup / name)
    shutil.copy2(authority, backup / authority.name)
    print(f"BACKUP {backup}")

    before = {name: sha(target) if target.is_file() else "missing" for name, target in targets.items()}
    for name in FILES:
        shutil.copy2(SOURCE / name, targets[name])
    patch_switches(args.lab_switches)
    for name, target in targets.items():
        print(f"{name} {before[name]} -> {sha(target)}")


if __name__ == "__main__":
    main()
