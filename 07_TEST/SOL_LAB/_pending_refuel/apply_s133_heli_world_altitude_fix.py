from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LAB_ROOT = (ROOT / "07_TEST" / "SOL_LAB").resolve()
SOURCE = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client"
FILES = ("SolHeliGPS.lua", "SolHeliExaminer.lua")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def main() -> None:
    parser = argparse.ArgumentParser(description="Install s133 world-altitude GPS fix to SOL_LAB only.")
    parser.add_argument("--lab-client", type=Path, required=True)
    parser.add_argument("--lab-switches", type=Path, required=True)
    parser.add_argument("--checkpoint-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    client = args.lab_client.resolve()
    switches = args.lab_switches.resolve()
    checkpoint_root = args.checkpoint_root.resolve()
    if not all(inside(path, LAB_ROOT) for path in (client, switches, checkpoint_root)):
        raise SystemExit("Refusing: every install and rollback path must stay inside SOL_LAB.")
    if not client.is_dir() or not (client / "SolAuthority.lua").is_file():
        raise SystemExit("Refusing: LAB client or SolAuthority.lua is missing.")
    if not switches.is_file():
        raise SystemExit("Refusing: existing LAB switches file is missing.")
    if not all((SOURCE / name).is_file() for name in FILES):
        raise SystemExit("Refusing: staged helicopter source file is missing.")

    values = {}
    for line in switches.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    if values.get("heli_gps") != "on" or values.get("drive_record") != "on":
        raise SystemExit("Refusing: expected existing heli_gps=on and drive_record=on switches.")

    targets = [client / name for name in FILES]
    if all(target.is_file() and sha(target) == sha(SOURCE / name)
           for name, target in zip(FILES, targets)):
        print("Already installed: both LAB helicopter files match source; no changes made.")
        return
    if args.dry_run:
        for name, target in zip(FILES, targets):
            print(f"COPY {SOURCE / name} -> {target}")
        print(f"CHECKPOINT root: {checkpoint_root}")
        print(f"KEEP switches unchanged: {switches}")
        return

    checkpoint = checkpoint_root / (dt.datetime.now().strftime("%Y%m%d_%H%M%S") + "_before_s133_heli_world_altitude")
    checkpoint.mkdir(parents=True, exist_ok=False)
    for item in (*targets, switches, client / "SolAuthority.lua"):
        if item.is_file():
            shutil.copy2(item, checkpoint / item.name)
    for name, target in zip(FILES, targets):
        shutil.copy2(SOURCE / name, target)
        if sha(target) != sha(SOURCE / name):
            raise SystemExit(f"Installed bytes mismatch: {name}")
        print(f"{name} installed sha256={sha(target)}")
    print(f"ROLLBACK CHECKPOINT {checkpoint}")
    print("SolFixes_LAB.txt and SolAuthority.lua unchanged.")


if __name__ == "__main__":
    main()
