"""s92 come_by_car, Mind side. Pairs with apply_s92_come_car_lua.py.
     appends  goal_engine.py   s92_goal_engine_block.py  (FetchPlayer92 replaces fetch_player's planner; switch off: the old FetchPlayer runs)
              chat_service.py  s92_chat_block.py         (the far car's kind; car=last / by_car on the drive goal; a helicopter: no drive)
Both behind come_by_car (SolFixes_LAB.txt); the Mind reads the switch file each time. Idempotent (marker "s92 come_by_car").
Restart Sol Mind after (launch_lab.ps1 refuses a Mind older than its newest source).
usage: apply_s92_come_car_mind.py <sol_mind dir>"""
import os, py_compile, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MARK = "s92 come_by_car"


def append(path, block_file):
    t = open(path, encoding="utf-8", newline="").read()
    if MARK in t: return "kept"
    block = open(os.path.join(HERE, block_file), encoding="utf-8").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    if not t.endswith(("\n", "\r\n")): t += nl
    open(path, "w", encoding="utf-8", newline="").write(t + block.replace("\n", nl))
    py_compile.compile(path, doraise=True)
    return "appended"


def mind(d):
    assert os.path.isfile(os.path.join(d, "chat_service.py")) and os.path.isfile(os.path.join(d, "goal_engine.py")), "not a sol_mind dir: " + d
    print("goal_engine", append(os.path.join(d, "goal_engine.py"), "s92_goal_engine_block.py"))
    print("chat_service", append(os.path.join(d, "chat_service.py"), "s92_chat_block.py"))


if __name__ == "__main__":
    mind(sys.argv[1])
    print("s92_come_car_mind applied")
