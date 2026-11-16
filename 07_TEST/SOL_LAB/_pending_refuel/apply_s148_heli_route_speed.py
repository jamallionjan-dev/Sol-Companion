from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


REPLACEMENTS = (
    (
        "H.headingRetryTimeoutMs = 15000\n",
        "H.headingRetryTimeoutMs = 15000\n"
        "-- Hysteresis keeps the route controller from bouncing between climb and cruise\n"
        "-- when the sampled world altitude jitters around the selected band.\n"
        "H.altitudeCaptureTolerance = 0.35\n"
        "H.altitudeReleaseTolerance = 0.65\n",
    ),
    (
        "    H.selected = level\n"
        "    H.reason = nil\n"
        "    log(\"altitude selected \" .. level .. \" agl=\" .. tostring(H.levels[level]))\n",
        "    if H.selected ~= level then H._altitudeHoldReady = false end\n"
        "    H.selected = level\n"
        "    H.reason = nil\n"
        "    log(\"altitude selected \" .. level .. \" agl=\" .. tostring(H.levels[level]))\n",
    ),
    (
        "        local altitudeReady = false\n"
        "        if ground and z then\n"
        "            H._missingGroundLogged = false\n",
        "        local altitudeReady = false\n"
        "        H._altitudeReferenceReady = false\n"
        "        if ground and z then\n"
        "            H._missingGroundLogged = false\n"
        "            H._altitudeReferenceReady = true\n",
    ),
    (
        "            local deltaZ = targetWorldZ - z\n"
        "            altitudeReady = math.abs(deltaZ) <= 0.22\n"
        "            if not state.liftUp and not state.liftDown then\n",
        "            local deltaZ = targetWorldZ - z\n"
        "            if H._altitudeHoldVehicle ~= v then H._altitudeHoldReady = false end\n"
        "            local routeFix = SolAuthority.on(\"heli_route_ownership\") == true\n"
        "            local enterBand = routeFix and (tonumber(H.altitudeCaptureTolerance) or 0.35) or 0.22\n"
        "            local exitBand = routeFix and (tonumber(H.altitudeReleaseTolerance) or 0.65) or 0.22\n"
        "            if H._altitudeHoldVehicle ~= v then H._altitudeHoldReady = false end\n"
        "            local altitudeBand = routeFix and (H._altitudeHoldReady and exitBand or enterBand) or 0.22\n"
        "            altitudeReady = math.abs(deltaZ) <= altitudeBand\n"
        "            if routeFix then H._altitudeHoldReady, H._altitudeHoldVehicle = altitudeReady, v end\n"
        "            if not state.liftUp and not state.liftDown then\n",
    ),
    (
        "            if not landingAtPoint and not altitudeReady then\n"
        "                -- Climb/descend to the chosen band before applying horizontal GPS steering.\n"
        "                state.yawLeft, state.yawRight = false, false\n"
        "                state.pitchUp, state.pitchDown = false, false\n"
        "                state.rollLeft, state.rollRight = false, false\n"
        "                H.phase = \"climbing\"\n"
        "            elseif not landingAtPoint and H.phase == \"climbing\" then\n",
        "            if not landingAtPoint and not altitudeReady then\n"
        "                if SolAuthority.on(\"heli_route_ownership\") == true then\n"
        "                    -- Vertical and horizontal axes are independent in AviationCore.\n"
        "                    -- Keep the GPS route live while climbing or descending to a new band.\n"
        "                    H.phase = \"climbing\"\n"
        "                else\n"
        "                    state.yawLeft, state.yawRight = false, false\n"
        "                    state.pitchUp, state.pitchDown = false, false\n"
        "                    state.rollLeft, state.rollRight = false, false\n"
        "                    H.phase = \"climbing\"\n"
        "                end\n"
        "            elseif not landingAtPoint and H.phase == \"climbing\" then\n",
    ),
    (
        "        if destination and (altitudeReady or H.landingRequested) then\n",
        "        if destination and ((SolAuthority.on(\"heli_route_ownership\") == true and H._altitudeReferenceReady)\n"
        "            or altitudeReady or H.landingRequested) then\n",
    ),
    (
        "                    local turnLeft, turnRight = applyGuidance(state, error)\n"
        "                    local guidance = (turnLeft and \"left\" or turnRight and \"right\" or \"straight\")\n"
        "                        .. (state.pitchUp and \"+forward\" or \"\")\n",
        "                    local turnLeft, turnRight = applyGuidance(state, error)\n"
        "                    if SolAuthority.on(\"heli_route_ownership\") == true then\n"
        "                        -- Keep thrust only while generally aligned; coordinated yaw/roll\n"
        "                        -- turns the aircraft without carrying it past a close marker.\n"
        "                        state.pitchUp, state.pitchDown = distance > 4.0 and math.abs(error) < 0.75, false\n"
        "                    end\n"
        "                    local guidance = (turnLeft and \"left\" or turnRight and \"right\" or \"straight\")\n"
        "                        .. (state.pitchUp and \"+forward\" or \"\")\n",
    ),
    (
        "                    H.phase, H.reason = \"following\", nil\n",
        "                    H.phase, H.reason = (SolAuthority.on(\"heli_route_ownership\") == true\n"
        "                        and (altitudeReady and \"following\" or \"climbing\")) or \"following\", nil\n",
    ),
)

INPUT_MARKER = "-- GPS autopilot owns flight controls while a destination is active."
INPUT_OLD = (
    "        local v = context.vehicle\n"
    "        local md = call(v, \"getModData\")\n"
)
INPUT_NEW = (
    "        local v = context.vehicle\n"
        "        if SolAuthority.on(\"heli_route_ownership\") == true and (H.destination or H.landingRequested) then\n"
    "            -- AviationCore reads keyboard state globally, not per occupant.\n"
    "            -- Ignore passenger key presses while Sol's GPS owns this flight.\n"
    "            for _, key in ipairs({ \"liftUp\", \"liftDown\", \"yawLeft\", \"yawRight\",\n"
    "                \"pitchUp\", \"pitchDown\", \"rollLeft\", \"rollRight\" }) do\n"
    "                state[key] = false\n"
    "            end\n"
    "        end\n"
    "        local md = call(v, \"getModData\")\n"
)


def transform(text: str) -> str:
    for old, new in REPLACEMENTS:
        if new in text:
            continue
        count = text.count(old)
        if count != 1:
            raise ValueError(f"expected one source block, found {count}: {old.splitlines()[0]}")
        text = text.replace(old, new, 1)
    if INPUT_MARKER not in text:
        count = text.count(INPUT_OLD)
        if count != 1:
            raise ValueError(f"expected one input hook, found {count}")
        text = text.replace(INPUT_OLD, INPUT_MARKER + "\n" + INPUT_NEW, 1)
    required = (
        "H.altitudeCaptureTolerance = 0.35",
        "state.pitchUp, state.pitchDown = distance > 4.0 and math.abs(error) < 0.75, false",
        "destination and ((SolAuthority.on(\"heli_route_ownership\") == true and H._altitudeReferenceReady)",
        "Ignore passenger key presses while Sol's GPS owns this flight.",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise ValueError("transformed source is missing markers: " + ", ".join(missing))
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply s148 continuous helicopter GPS route/speed input.")
    parser.add_argument("target", type=Path, help="Sol client directory to patch")
    parser.add_argument("--backup", type=Path, required=True, help="backup directory for the original files")
    parser.add_argument("--switch-file", type=Path, required=True, help="profile SolFixes_LAB.txt to enable the tested fix")
    args = parser.parse_args()
    client = args.target.resolve()
    backup = args.backup.resolve()
    heli = client / "SolHeliGPS.lua"
    authority = client / "SolAuthority.lua"
    if not client.is_dir() or not heli.is_file() or not authority.is_file():
        raise SystemExit("Refusing: target must be a client directory with SolHeliGPS.lua and SolAuthority.lua")
    raw = heli.read_bytes()
    try:
        source = raw.decode("ascii").replace("\r\n", "\n")
    except UnicodeDecodeError as exc:
        raise SystemExit("Refusing: Lua source must remain ASCII") from exc
    try:
        updated = transform(source)
    except ValueError as exc:
        raise SystemExit("Refusing: " + str(exc)) from exc
    ending = b"\r\n" if b"\r\n" in raw else b"\n"
    updated_bytes = updated.replace("\n", ending.decode("ascii")).encode("ascii")
    auth_raw = authority.read_bytes()
    auth = auth_raw.decode("ascii").replace("\r\n", "\n")
    marker = '    "heli_gps",              -- s121: direct-air GPS guidance and altitude targets for Sol\'s helicopter\n'
    addition = marker + '    "heli_route_ownership", -- s148: keep GPS route and speed active across altitude changes\n'
    if addition not in auth:
        if auth.count(marker) != 1:
            raise SystemExit("Refusing: expected one heli_gps switch registration")
        auth = auth.replace(marker, addition, 1)
    auth_ending = b"\r\n" if b"\r\n" in auth_raw else b"\n"
    auth_new = auth.replace("\n", auth_ending.decode("ascii")).encode("ascii")
    switch_file = args.switch_file.resolve()
    changes = [(heli, raw, updated_bytes), (authority, auth_raw, auth_new)]
    if switch_file.is_file():
        switch_raw = switch_file.read_bytes()
        switch_text = switch_raw.decode("ascii")
        if not any(line.partition("=")[0].strip() == "heli_route_ownership" for line in switch_text.splitlines() if "=" in line):
            switch_text = switch_text.rstrip("\r\n") + "\r\nheli_route_ownership=on\r\n"
        changes.append((switch_file, switch_raw, switch_text.encode("ascii")))
    backup.mkdir(parents=True, exist_ok=True)
    for path, original, _ in changes:
        name = "SolFixes_LAB.txt" if path == switch_file else path.name
        saved = backup / name
        if not saved.exists():
            shutil.copy2(path, saved)
    for path, original, replacement in changes:
        if original == replacement:
            print("KEPT " + str(path))
        else:
            path.write_bytes(replacement)
            print("APPLIED " + str(path))
        print("sha256=" + hashlib.sha256(replacement).hexdigest())


if __name__ == "__main__":
    main()
