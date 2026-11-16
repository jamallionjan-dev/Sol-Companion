from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client" / "SolHeliGPS.lua"
TARGET_REL = Path("SolHeliGPS.lua")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Install s126 player-read helicopter manual sharing into SOL_LAB only.")
    parser.add_argument("--lab-client", type=Path, required=True)
    parser.add_argument("--lab-switches", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    client = args.lab_client.resolve()
    switches = args.lab_switches.resolve()
    backup_root = args.backup_root.resolve()
    lab_root = (ROOT / "07_TEST" / "SOL_LAB").resolve()
    if not client.is_relative_to(lab_root) or not switches.is_relative_to(lab_root) or not backup_root.is_relative_to(lab_root):
        raise SystemExit("Refusing: all targets and backups must stay inside SOL_LAB.")
    if not client.is_dir() or not (client / "SolAuthority.lua").is_file():
        raise SystemExit("Refusing: installed LAB client or SolAuthority.lua is missing.")
    if not SOURCE.is_file():
        raise SystemExit(f"Staged source missing: {SOURCE}")
    switch_lines = switches.read_text(encoding="utf-8").splitlines() if switches.is_file() else []
    switch_values = {line.split("=", 1)[0].strip(): line.split("=", 1)[1].strip() for line in switch_lines if "=" in line}
    if switch_values.get("heli_gps") != "on" or switch_values.get("seat_handoff") != "on":
        raise SystemExit("Refusing: expected heli_gps=on and seat_handoff=on in the existing LAB switches.")

    target = client / TARGET_REL
    if args.dry_run:
        print(f"COPY {SOURCE} -> {target}")
        print(f"KEEP switches unchanged: {switches}")
        print(f"BACKUP root: {backup_root}")
        return

    backup = backup_root / (dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_before_s126_manual_knowledge_share")
    backup.mkdir(parents=True, exist_ok=False)
    for item in (target, switches, client / "SolAuthority.lua"):
        if item.exists():
            shutil.copy2(item, backup / item.name)
    before = sha(target) if target.is_file() else "missing"
    shutil.copy2(SOURCE, target)
    print(f"BACKUP {backup}")
    print(f"SolHeliGPS.lua {before} -> {sha(target)}")
    print("SolFixes_LAB.txt unchanged")
    print("SolAuthority.lua unchanged")


if __name__ == "__main__":
    main()
