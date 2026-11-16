"""Make the existing forget-all command cancel Sol Mind's active multi-step goal."""
import os
import sys

MIND = os.path.abspath(sys.argv[1])
path = os.path.join(MIND, "chat_service.py")
old = 'MOVE_ORDERS = frozenset(("park_car", "drive_take_wheel", "drive_stop", "drive_to", "follow", "stay", "guard", "regroup", "retreat", "board_vehicle", "exit_vehicle", "sol_goto", "sol_drive", "sol_farm"))'
new = 'MOVE_ORDERS = frozenset(("park_car", "drive_take_wheel", "drive_stop", "drive_to", "follow", "stay", "guard", "regroup", "retreat", "board_vehicle", "exit_vehicle", "sol_goto", "sol_drive", "sol_farm", "sol_forget"))'

with open(path, "r", encoding="utf-8", newline="") as handle:
    text = handle.read()
if new in text:
    print("kept chat_service.py")
elif text.count(old) == 1:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace(old, new, 1))
    print("edited chat_service.py")
else:
    raise SystemExit("expected exactly one MOVE_ORDERS definition in " + path)

print("s112 forget preemption applied")
