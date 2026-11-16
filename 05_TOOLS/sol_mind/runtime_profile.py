"""Resolve the active Project Zomboid user's Lua mailbox on Windows."""
import json
import os
import re
import subprocess

NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _processes():
    if os.name != "nt":
        return []
    script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match '^(javaw?|ProjectZomboid.*)\\.exe$' } | "
        "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, errors="replace", timeout=10,
            creationflags=NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
    except ValueError:
        return []
    return data if isinstance(data, list) else [data]


def active_game_mailbox():
    """Return <active user.home>\\Zomboid\\Lua, or None if no PZ process is identifiable."""
    for process in _processes():
        name = str(process.get("Name") or "")
        command = str(process.get("CommandLine") or "")
        args_text = command
        argfiles = re.findall(r'@(?:"([^"]+)"|(\S+))', command)
        for quoted, plain in argfiles:
            argfile = (quoted or plain).strip('"')
            try:
                with open(argfile, "r", encoding="utf-8-sig") as stream:
                    args_text += "\n" + stream.read()
            except OSError:
                continue
        is_game_exe = name.lower().startswith("projectzomboid")
        if not is_game_exe and not re.search(
            r"projectzomboid(?:\.jar|64\.exe)|zombie\.gameStates\.MainScreenState",
            args_text,
            re.IGNORECASE,
        ):
            continue
        match = re.search(r"(?:^|\s)-Duser\.home=(?:\"([^\"]+)\"|(\S+))", args_text)
        user_home = (match.group(1) or match.group(2)).strip('"') if match else os.environ.get("USERPROFILE", "")
        if not user_home:
            return None
        return os.path.join(user_home, "Zomboid", "Lua")
    return None


def default_mailbox():
    """The regular profile mailbox, used only when no active PZ process is found."""
    return os.path.join(os.path.expanduser("~"), "Zomboid", "Lua")
