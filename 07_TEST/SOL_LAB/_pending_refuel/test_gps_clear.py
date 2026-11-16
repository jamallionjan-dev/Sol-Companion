"""Cancelling a GPS destination: the real functions cut from a patched copy of SolGPS.lua, on mocks."""
import os, sys
from kahlua_env import lua51
H = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(H, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client", "SolGPS.lua"), encoding="utf-8").read().replace("\r\n", "\n")
a = src.index('-- Takes the destination off the screen.'); b = src.index('-- ---------------------------------------------------------------- driving')
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("""
U = {}; G = { preview = {} }
STOPS, PHASE = 0, nil
function U.gpsStatus() return { phase = PHASE } end
function U.gpsStop() STOPS = STOPS + 1 end
""")
L.execute(src[a:b]); g = L.globals(); U = g.U
def dest(name='"Map point"', x=100, y=200, phase="nil"):
    L.execute('G.dest = { x = %d, y = %d, name = %s }; G.preview = { at = 5, route = {}, reason = "r", snap = {}, key = "k" }; G.lastResult = "arrived"; G.reason = "arrived"; PHASE = %s; STOPS = 0' % (x, y, name, phase))
ck("nothing set: fine", U.gpsClear() == (True, "already_clear"))
dest(); ck("clears", U.gpsClear() == (True, "destination_cleared") and g.G.dest is None)
ck("route preview gone", g.G.preview.route is None and g.G.preview.key is None and g.G.preview.snap is None)
ck("old result gone", g.G.lastResult is None)
dest(phase='"following"'); U.gpsClear(); ck("while driving: stops her too", g.STOPS == 1 and g.G.dest is None)
dest(); ck("same spot: cancels", U.gpsMapClick(100, 200, False) == "cleared" and g.G.dest is None)
dest(); ck("within 2 tiles: cancels", U.gpsMapClick(101.5, 198.2, False) == "cleared")
dest(); ck("3 tiles off: a new spot", U.gpsMapClick(103, 200, False) == "set" and g.G.dest is not None)
dest(); ck("while driving a click never cancels", U.gpsMapClick(100, 200, True) == "set" and g.G.dest is not None)
L.execute("G.dest = nil"); ck("no destination: a click sets", U.gpsMapClick(100, 200, False) == "set")
dest('"Gas station gas2go"'); ck("errand clears its station", U.gpsClear("errand") == (True, "destination_cleared") and g.G.dest is None)
dest('"back to the player"'); ck("errand clears its way back", U.gpsClear("errand")[1] == "destination_cleared" and g.G.dest is None)
dest('"Map point"'); ck("errand leaves his own point alone", U.gpsClear("errand") == (True, "not_an_errand_target") and g.G.dest is not None)
dest('"Gas station"', phase='"following"'); U.gpsClear("errand"); ck("errand clear never stops a drive", g.STOPS == 0)
for needle in ['if wx and wy and U.gpsMapClick(wx, wy, clickDriving) == "cleared" then return true end', 'action = "clear" }', 'elseif h.action == "clear" then U.gpsClear()']:
    ck("wired: " + needle[:40], needle in src)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %s" % FAIL)
sys.exit(1 if FAIL else 0)
