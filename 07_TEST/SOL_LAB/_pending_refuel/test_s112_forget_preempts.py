import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MIND = os.path.join(ROOT, "05_TOOLS", "sol_mind")
sys.path.insert(0, MIND)

import chat_service as CS


class Goals:
    def __init__(self):
        self.calls = []

    def cancel(self, reason):
        self.calls.append(reason)
        return True


def main():
    failures = []

    def check(name, ok, detail=""):
        print(("PASS " if ok else "FAIL ") + name + (" -- " + detail if detail else ""))
        if not ok:
            failures.append(name)

    parsed = CS.intents("خلص انسي كلشي")
    check("forget phrase routes to sol_forget", ("action", {"action": "sol_forget", "option": None}) in parsed, repr(parsed))
    check("sol_forget is a goal-preempting direct order", "sol_forget" in CS.MOVE_ORDERS)

    chat = CS.Chat.__new__(CS.Chat)
    chat.goals = Goals()
    chat.log = lambda _message: None
    chat._player_takes_over("sol_forget")
    check("forget cancels the active Mind goal", chat.goals.calls == ["player_order:sol_forget"], repr(chat.goals.calls))

    with tempfile.TemporaryDirectory(prefix="sol_s112_apply_") as temp:
        staged_mind = os.path.join(temp, "sol_mind")
        os.makedirs(staged_mind)
        staged_file = os.path.join(staged_mind, "chat_service.py")
        shutil.copyfile(os.path.join(MIND, "chat_service.py"), staged_file)
        current = open(staged_file, "rb").read()
        old = b'"sol_drive", "sol_farm", "sol_forget"))'
        original = b'"sol_drive", "sol_farm"))'
        if current.count(old) != 1:
            raise SystemExit("could not create the exact pre-fix fixture")
        with open(staged_file, "wb") as handle:
            handle.write(current.replace(old, original, 1))
        installer = os.path.join(os.path.dirname(__file__), "apply_s112_forget_preempts.py")
        first = subprocess.run([sys.executable, installer, staged_mind], capture_output=True, text=True)
        after_first = open(os.path.join(staged_mind, "chat_service.py"), "rb").read()
        second = subprocess.run([sys.executable, installer, staged_mind], capture_output=True, text=True)
        after_second = open(os.path.join(staged_mind, "chat_service.py"), "rb").read()
        check("apply script succeeds twice without changing result", first.returncode == 0 and second.returncode == 0 and after_first == after_second,
              (first.stdout + second.stdout).strip())

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
