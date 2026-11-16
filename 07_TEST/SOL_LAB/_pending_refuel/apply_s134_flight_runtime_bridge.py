from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LAB_ROOT = (ROOT / "07_TEST" / "SOL_LAB").resolve()
SOURCE = ROOT / "01_WORK" / "Sol" / "42" / "media" / "lua" / "client" / "SolHeliGPS.lua"
TARGET_NAME = "SolHeliGPS.lua"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def main() -> None:
    parser = argparse.ArgumentParser(description="Install s134 AviationCore pilot bridge fix into SOL_LAB only.")
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
    if not SOURCE.is_file():
        raise SystemExit("Refusing: staged SolHeliGPS.lua is missing.")

    values = {}
    for line in switches.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    if values.get("heli_gps") != "on":
        raise SystemExit("Refusing: expected existing heli_gps=on switch.")

    target = client / TARGET_NAME
    if target.is_file() and sha(target) == sha(SOURCE):
        print("Already installed: LAB SolHeliGPS.lua matches source; no changes made.")
        return
    if args.dry_run:
        print(f"COPY {SOURCE} -> {target}")
        print(f"CHECKPOINT root: {checkpoint_root}")
        print(f"KEEP switches unchanged: {switches}")
        return

    checkpoint = checkpoint_root / (dt.datetime.now().strftime("%Y%m%d_%H%M%S") + "_before_s134_flight_runtime_bridge")
    checkpoint.mkdir(parents=True, exist_ok=False)
    for item in (target, switches, client / "SolAuthority.lua"):
        if item.is_file():
            shutil.copy2(item, checkpoint / item.name)
    shutil.copy2(SOURCE, target)
    if sha(target) != sha(SOURCE):
        raise SystemExit("Installed bytes mismatch: SolHeliGPS.lua")
    print(f"{TARGET_NAME} installed sha256={sha(target)}")
    print(f"ROLLBACK CHECKPOINT {checkpoint}")
    print("SolFixes_LAB.txt and SolAuthority.lua unchanged; no Steam/main profile touched.")


if __name__ == "__main__":
    main()
