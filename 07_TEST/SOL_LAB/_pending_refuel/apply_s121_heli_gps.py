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


def patch_authority(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    key = '    "seat_handoff",'
    if text.count(key) > 1:
        raise SystemExit(f"duplicate seat_handoff switch in {path}")
    if text.count(key) == 1:
        return
    anchor = '    "heli_gps",'
    if text.count(anchor) != 1:
        raise SystemExit(f"expected one authority anchor in {path}, got {text.count(anchor)}")
    text = text.replace(anchor, anchor + '\n    "seat_handoff",           -- Sol moves from driver to an empty passenger seat for player takeover', 1)
    path.write_text(text, encoding="utf-8", newline="\n")


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab-client", type=Path, required=True)
    parser.add_argument("--lab-switches", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    targets = {name: args.lab_client / name for name in FILES}
    targets["SolAuthority.lua"] = args.lab_client / "SolAuthority.lua"
    targets["SolFixes_LAB.txt"] = args.lab_switches
    if not args.lab_client.is_dir():
        raise SystemExit(f"LAB client directory not found: {args.lab_client}")
    if not all((SOURCE / name).is_file() for name in FILES):
        raise SystemExit("one or more staged Sol sources are missing")
    if not targets["SolAuthority.lua"].is_file():
        raise SystemExit("LAB SolAuthority.lua is missing")

    backup = args.backup_root / (dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_before_s123_heli_and_handoff")
    if not args.dry_run:
        backup.mkdir(parents=True, exist_ok=False)
        for name, target in targets.items():
            if target.exists():
                shutil.copy2(target, backup / name)
        print(f"BACKUP {backup}")

    before = {name: sha(target) if target.exists() else None for name, target in targets.items()}
    if args.dry_run:
        for name in FILES:
            print(f"COPY {SOURCE / name} -> {targets[name]}")
        print(f"PATCH {targets['SolAuthority.lua']}")
        print(f"SET heli_gps=on and seat_handoff=on in {args.lab_switches}")
        return

    for name in FILES:
        shutil.copy2(SOURCE / name, targets[name])
    patch_authority(targets["SolAuthority.lua"])
    patch_switches(args.lab_switches)
    for name, target in targets.items():
        print(f"{name} {before[name]} -> {sha(target) if target.exists() else 'missing'}")


if __name__ == "__main__":
    main()
