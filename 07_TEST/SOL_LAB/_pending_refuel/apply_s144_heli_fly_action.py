from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT
FILES = (
    (Path("01_WORK/Sol/42/media/lua/client/SolActionRegistry.lua"),
     Path("Zomboid/mods/Sol/42/media/lua/client/SolActionRegistry.lua")),
    (Path("01_WORK/Sol/42/media/lua/client/SolAuthority.lua"),
     Path("Zomboid/mods/Sol/42/media/lua/client/SolAuthority.lua")),
    (Path("05_TOOLS/sol_mind/model_router.py"),
     Path("SolMind/model_router.py")),
    (Path("DOCS/SOL_MODEL_CARD.md"), Path("SolMind/SOL_MODEL_CARD.md")),
)
SWITCH = "heli_voice_fly=on"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply only s144 helicopter voice-GPS files to a full release bundle.")
    parser.add_argument("target", type=Path, help="release candidate bundle root")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    source, target = args.source.resolve(), args.target.resolve()
    if not target.is_dir() or not (target / "Zomboid/mods/Sol/42/mod.info").is_file():
        raise SystemExit("Refusing: target is not a full Sol release bundle")
    source_action = (source / FILES[0][0]).read_text(encoding="utf-8")
    source_auth = (source / FILES[1][0]).read_text(encoding="utf-8")
    source_router = (source / FILES[2][0]).read_text(encoding="utf-8")
    required = (
        ("action", "V.sol_heli_fly_marker =" in source_action),
        ("new action switch", '"heli_voice_fly"' in source_auth),
        ("model route", '"sol_heli_fly_marker"' in source_router and "سول طيري على العلامة" in source_router),
        ("pilot method on card", "السرعة والارتفاع والهبوط من GPS" in source_router),
    )
    missing = [name for name, ok in required if not ok]
    if missing:
        raise SystemExit("Refusing: source feature markers missing: " + ", ".join(missing))

    for relative_source, relative_target in FILES:
        src, dst = source / relative_source, target / relative_target
        if not src.is_file() or not dst.parent.is_dir():
            raise SystemExit(f"Refusing missing source or target directory: {src} -> {dst}")
        shutil.copy2(src, dst)
        if sha(src) != sha(dst):
            raise SystemExit("SHA-256 mismatch after copy: " + str(dst))
        print("APPLIED " + str(relative_target))

    fixes = target / "Zomboid/Lua/SolFixes_MAIN.txt"
    if not fixes.is_file():
        raise SystemExit("Refusing: candidate MAIN switches file is missing")
    raw = fixes.read_bytes()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    lines = raw.decode("utf-8-sig").splitlines()
    keys = [line.split("=", 1)[0].strip() for line in lines if "=" in line]
    if "heli_voice_fly" in keys:
        lines = [SWITCH if line.split("=", 1)[0].strip() == "heli_voice_fly" else line for line in lines]
    else:
        lines.append(SWITCH)
    normalized = ("\r\n".join(lines) + "\r\n").encode("utf-8")
    if had_bom:
        normalized = b"\xef\xbb\xbf" + normalized
    if raw != normalized:
        fixes.write_bytes(normalized)
    if sum(line.startswith("heli_voice_fly=") for line in lines) != 1:
        raise SystemExit("MAIN switch is not unique")
    print("APPLIED Zomboid/Lua/SolFixes_MAIN.txt (heli_voice_fly=on)")


if __name__ == "__main__":
    main()
