"""The fixes of the full review (DOCS/SOL_REVIEW_20261109.md) that can be run off the game. Offline PASS is not Runtime PASS."""
import os, re, sys
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
MIND = os.path.abspath(os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind"))
LIVE = os.path.abspath(os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"))
sys.path.insert(0, MIND)
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def read(n): return open(os.path.join(LIVE, n), encoding="utf-8").read().replace("\r\n", "\n")

# ---------------------------------------------------------------- the gate strips the clause, not the reply
import reply_gate as RG
def speech(s, user="سول احكيلي", known="", ran=False):
    c = RG.Context(user, [], [], known, False, (), [("Broadway St", ())])
    r = RG.check_speech({"speech": s}, c, ran)
    return r[0], r[1], c
for line, kept in [("مرحبا، طفيتها!", "مرحبا"), ("مرحبا، بيتنا بالقرب", "مرحبا"), ("أهلين، بس جبت الأكل", "أهلين"), ("الجو حلو، فتحت الباب", "الجو حلو")]:
    t, why, c = speech(line); ck("only the bad clause goes: " + line, why is None and t == kept and c.stripped, (t, why))
for line, reason in [("رحت، بس ما بينا ببيت", "claims_an_action"), ("طفيتها", "claims_an_action"), ("دوري، ما بتحتاجين ماء", "speaks_to_herself")]:
    t, why, c = speech(line); ck("nothing worth keeping: safe line: " + line, why == reason and (t in RG.SAFE_NOT_DONE or t in RG.SAFE_UNKNOWN), (t, why))
t, why, c = speech("مرحبا، بيتنا بالقرب", user="وين بيتنا؟"); ck("a question does not get a bare hello", why is not None and t in RG.SAFE_UNKNOWN, (t, why))
t, why, c = speech("طفيتها، لأن الجو حر، ماشي"); ck("a clause leaning on the removed one goes with it", why is None and t == "ماشي", (t, why))
t, why, c = speech("طفيتها، بس الجو حلو"); ck("a leading but is trimmed", why is None and t == "الجو حلو", (t, why))
t, why, c = speech("ماشي، أنا معك."); ck("a clean line is untouched", why is None and t == "ماشي، أنا معك." and not c.stripped, (t, why))
t, why, c = speech("طفيتها", ran=True); ck("a claim stands when the action ran", why is None and t == "طفيتها", (t, why))
t, why, c = speech("كازية Shell، ماشي"); ck("an invented name is stripped", why is None and t == "ماشي", (t, why))
t, why, c = speech("شارع Broadway St، 300 متر", known="300"); ck("a named place grounds the distance beside it", why is None and "Broadway St" in t and "300" in t, (t, why))
t, why, c = speech("ومسافة 3.5 كم", known=""); ck("a decimal point is not a clause end", why is not None, (t, why))
for line in ["فرحت فيك كتير", "تعلمت منك شغلة", "ما طفيتها لسا", "ما وصلت لهون", "خبيت الأكل", "ما في طريقة غيرها"]:
    t, why, c = speech(line); ck("not a claim about the world: " + line, why is None and t == line, (t, why))
for w, yes in [("بيتنا", True), ("ببيت", True), ("البيت", True), ("خبيت", False), ("طريقة", False), ("طريق", True), ("مدينتنا", True)]:
    ck("world word: " + w, RG.about_the_world(w) == yes)

# ---------------------------------------------------------------- home words
sys.modules.setdefault("win32api", None)
try:
    import chat_service as CS
except Exception as e:
    CS = None; ck("chat_service imports", False, repr(e))
if CS:
    def home(t): return any(n == "set_home" for n, _ in CS.intents(t))
    for t in ["هاد بيتنا", "هون بيتنا", "هون البيت", "هاد البيت بيتنا", "هون رح يكون بيتنا", "اعتبري هون بيتنا"]: ck("sets home: " + t, home(t))
    for t in ["هاد بيتنا؟", "مو هاد بيتنا", "بيتنا هنيك", "ما بدي هون بيتنا", "هاد البيت حلو"]: ck("does not set home: " + t, not home(t))
    ck("no home yet: said in Arabic", CS.reason_ar("home_not_set") == "لسا ما حددنا بيتنا")
    ck("drive home without a home names the right reason", CS.drive_to("", {"target": "home"}, type("M", (), {"data": {}})())["error"] == "home_not_set")
    ck("walking to the door is not a failed trip", "walking_to_door" in open(os.path.join(MIND, "goal_engine.py"), encoding="utf-8").read().split("WAITING=", 1)[1][:60])
    ck("parking is a move order", "park_car" in CS.MOVE_ORDERS)
import farm_talk as FT
for t in ["رتاحي بالبيت", "سول ضلي رتاحي بالبيت", "ضلي بالبيت ارتاحي"]:
    hit = FT.order(t); ck("rest at home: " + t, hit is not None and hit[1] == "home", hit)
ck("not ready is said as not ready", "المخازن" in FT.reply_for("short", {"ok": True, "reason": "not_ready"}))
ck("farmhome is said as both", FT.reply_for("home", {"ok": True, "reason": "mode:home:farmhome"}) in FT.ACK["both"])
ck("the new reasons are in Arabic", FT.why_ar("body_busy") != FT.why_ar("nonsense") and FT.why_ar("target_unloaded") != FT.why_ar("nonsense"))
ck("an unknown storage is listed as unsure", "مو متأكد" in FT.shortages_text([{"storage": "food", "unsure": True}]) or "متأكدة" in FT.shortages_text([{"storage": "food", "unsure": True}]), FT.shortages_text([{"storage": "food", "unsure": True}]))

# ---------------------------------------------------------------- the first free passenger seat
src = read("SCVehicle.lua")
ck("a removed car is refused in all four doors", src.count("if goneFromWorld(vehicle) then return nil") == 4)
ck("no nearest-door search is left in the seat choice", "bestDistance" not in src)

# ---------------------------------------------------------------- SolBypass heading bins on the game's %
b = read("SolBypass.lua")
m = re.search(r"local function bin\(th\) (.*?) end", b)
ck("bin normalises the sign", m and "+ tau) % tau" in m.group(1), m and m.group(1))

# ---------------------------------------------------------------- SolFar: registered, no body
W = r"""
NOW = 100000; function getTimestampMs() return NOW end
print = function() end; require = function() end
TASKS = {}; SolBudget = { register = function(n, f) TASKS[n] = f end }
SQ = "sq"
BODY = { getCurrentSquare = function() return SQ end, getX = function() return 1600 end, getY = function() return 1000 end, getZ = function() return 0 end }
SolUI = { solActor = function() return BODY end }
PL = { getX = function() return 1000 end, getY = function() return 1000 end, getZ = function() return 0 end }
function getSpecificPlayer() return PL end
RECOVERED = nil
SurvivorCompanion = { Actor = { recover = function(a, s) RECOVERED = s; return true end },
    GameplayUtil = { gridSquare = function(x, y, z) if x > 1500 then return nil end return "grid" end, idOf = function() return "s" end },
    Persistence = { pendingIds = function() return {} end, pendingBootstrap = function() return nil end } }
"""
L = lua51.LuaRuntime(unpack_returned_tuples=True); L.execute(W); L.execute(read("SolFar.lua")); g = L.globals()
ck("a body on a square is here", g.SolUI.solFarState() is None)
L.execute("SQ = nil"); ck("no square for a moment: still here", g.SolUI.solFarState() is None)
L.execute("NOW = NOW + 2500"); ck("no square for 2 s: far, though still registered", g.SolUI.solFarState() == "far", g.SolUI.solFarState())
ck("status answers for her", g.SolUI.solFar("status") == (True, "far:600"), g.SolUI.solFar("status"))
ck("catch-up is told to wait while her square is unloaded", g.SolUI.solFarUnloaded(g.BODY) is True)
ck("a poll with nothing under way is not a failure", g.SolUI.solFar("poll") == (True, "idle"), g.SolUI.solFar("poll"))
L.execute("SQ = 'back'"); ck("square again: here", g.SolUI.solFarState() is None)

# ---------------------------------------------------------------- SolAuthority: the farm keeps her legs
A = lua51.LuaRuntime(unpack_returned_tuples=True)
A.execute("SolUI = { solActor = function() return 'sol' end, solFarmHeld = function() return HELD end }; HELD = true; print = function() end")
A.execute(read("SolAuthority.lua"))
for k, want in [("logistics", False), ("base_work", False), ("downtime", False), ("combat", True), ("medical", True)]:
    ck("while farm-held, %s allowed = %s" % (k, want), A.globals().SolAuthority.allowsDecision("sol", k) == want, A.globals().SolAuthority.allowsDecision("sol", k))
A.execute("HELD = false")
ck("off the farm logistics is hers again", A.globals().SolAuthority.allowsDecision("sol", "logistics") is True)

print("SUMMARY", "ALL PASS" if not FAIL else "FAILED: " + str(FAIL[:6]))
sys.exit(1 if FAIL else 0)
