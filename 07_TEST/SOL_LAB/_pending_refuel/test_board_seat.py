"""Which seat "get in" picks, in every way the seats can be taken. Runs O.board cut from SolOrders.lua with apply_s11 applied to a copy."""
import os, re, subprocess, sys, tempfile
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
C = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\lua\client\SolOrders.lua"
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
src = open(C, encoding="utf-8").read().replace("\r\n", "\n")
if "that takes an order to drive" not in src:
    tmp = os.path.join(tempfile.mkdtemp(prefix="sol_seat_"), "SolOrders.lua")
    open(tmp, "w", encoding="utf-8", newline="").write(src)
    subprocess.check_call([sys.executable, os.path.join(HERE, "apply_s11_lua.py"), tmp], stdout=subprocess.DEVNULL)
    src = open(tmp, encoding="utf-8").read().replace("\r\n", "\n")
a = src.index("function O.board(targetVehicle)"); b = src.index("-- by car to a point", a)
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(r"""
O, U, SAID, JOB, WHEEL = {}, {}, nil, nil, 0
AR = setmetatable({}, { __index = function(_, k) return k end })
function say(t) SAID = t end
function log() end
function nowMs() return 1000 end
function freshFlow() end
function vehApi() return true end
function seat() return "out" end
function sol() return nil end
function stepBoard() end
function O.takeWheel() WHEEL = WHEEL + 1 end
U.gpsTakeWheel = function() end
function car(max, occupied) return { getMaxPassengers = function() return max end, isSeatOccupied = function(_, i) return occupied[i] == true end } end
MINE = nil
function playerVehicle() return MINE end
""")
L.execute("local job\n" + "local function capture() JOB = job end\n" + src[a:b].replace("return stepBoard(nowMs())", "JOB = job; return stepBoard(nowMs())"))
g = L.globals()
def board(max_, occ, mine=True):
    L.execute("SAID, JOB, WHEEL = nil, nil, 0; MINE = car(%d, { %s }); THECAR = MINE; %s" % (max_, ", ".join("[%d] = true" % i for i in occ), "" if mine else "MINE = nil; U.nearestVehicle = function() return THECAR end"))
    g.O.board(g.THECAR)
    return (g.JOB.seat if g.JOB else None), g.WHEEL, g.SAID
for name, args, want in [
    ("van, he drives: the seat beside him", (6, [0]), (1, 0)),
    ("van, he is behind: the seat in front", (6, [3]), (1, 0)),
    ("van, he is beside the driver: the first free seat behind, not the wheel", (6, [1]), (2, 0)),
    ("two seats, he drives: the seat beside him", (2, [0]), (1, 0)),
    ("van, front two taken: the first free seat behind", (6, [0, 1]), (2, 0)),
    ("van, nearly full: the one seat left", (6, [0, 1, 2, 3, 4]), (5, 0)),
]:
    r = board(*args); ck(name, r[:2] == want, r)
r = board(2, [1]); ck("two seats, he is beside the driver, no order to drive: no seat", r == (None, 0, "no_seat"), r)
r = board(6, [1, 2, 3, 4, 5]); ck("only the wheel is free, no order to drive: no seat", r == (None, 0, "no_seat"), r)
r = board(6, [0, 1, 2, 3, 4, 5]); ck("full: says so", r == (None, 0, "no_seat"), r)
import itertools
n = bad = 0
for seats in (2, 4, 6, 8):
    for bits in itertools.product([False, True], repeat=seats):
        occ = [i for i, b in enumerate(bits) if b]
        for mine in (True, False):
            r = board(seats, occ, mine); n += 1
            free = [i for i in range(1, seats) if i not in occ]
            want = (free[0], 0, "boarding") if free else (None, 0, "no_seat")
            if r != want:
                bad += 1
                if bad <= 8: print("     seats", seats, "taken", occ, "his car", mine, "got", r, "want", want)
ck("no order to drive, every way the seats can be taken, 2 to 8 seats (%d cases): first free passenger seat, never the wheel" % n, bad == 0, bad)
# ordered to drive: the wheel, whatever else is taken
take = src[src.index("function O.takeWheel()"):src.index("-- Start the route already selected on Sol's GPS")]
L.execute(r"""
function failText(reason) return reason end
function follow() FOLLOWED = true end
G_OCC = {}
U.gpsTakeWheel = function() ASKED = (ASKED or 0) + 1; if G_OCC[0] == "him" then return false, "player_is_driver" end if G_OCC[0] == "other" then return false, "requested vehicle seat is unavailable" end return true, "board_passenger" end
""")
L.execute(take)
n = bad = 0
for seats in (2, 4, 6, 8):
    for bits in itertools.product([False, True], repeat=seats):
        occ = [i for i, b in enumerate(bits) if b]
        for driver in ("him", "other"):
            L.execute('SAID, ASKED = nil, 0; G_OCC = {}; %s' % ('G_OCC[0] = "%s"' % driver if 0 in occ else ""))
            g.O.takeWheel(); n += 1
            want = ("player_is_driver" if driver == "him" else "requested vehicle seat is unavailable") if 0 in occ else "wheel_ok"
            if g.SAID != want or g.ASKED != 1: bad += 1
ck("ordered to drive (%d cases): the wheel if it is free, says so if it is not" % n, bad == 0, bad)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
