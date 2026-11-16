"""Questions about seeds and farm tools answer from the same scan as the inventory table, on what is "ours" or what she carries."""
import os, sys, tempfile, threading
sys.path.insert(0, r"C:\\Users\\JAMAL\\Desktop\\Sol\\05_TOOLS\\sol_mind")
import chat_service as CS, world_knowledge as W
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
SEEDS = {"type": "Base.BasilSeed", "name": "Basil Seeds", "cat": "Gardening", "count": 5}
TOOL = {"type": "Base.GardenHoe", "name": "Garden Hoe", "cat": "GardeningWeapon", "count": 1}
SPADE = {"type": "Base.Shovel", "name": "Shovel", "cat": "Tool", "count": 1}
SNAP = {"containers": [{"where": "square", "kind": "crate", "items": [SEEDS, TOOL, SPADE, {"type": "Base.Nails", "name": "Nails", "cat": "Material", "count": 9}]},
                       {"where": "sol", "items": [{"type": "Base.CarrotSeed", "name": "Carrot Seeds", "cat": "Gardening", "count": 2}]},
                       {"where": "player", "items": [{"type": "Base.Hammer", "name": "Hammer", "cat": "Tool", "count": 1}]}]}
HERE_SOL = dict(SNAP, sol={"x": 1})
STOCK = {"v": '{"stock": {"seeds": {}, "tools": 0, "cans": 0}}'}
ACT = []
def fake(lua, aid, option=None, wait=3.0):
    ACT.append((aid, option))
    if aid == "sol_farm" and option == "report": return {"ok": True, "reason": "farm:" + STOCK["v"]}
    return {"ok": False, "reason": "none"}
CS.run_action = fake
class Goals:
    sub = []
    def submit(self, g): return {"ok": True}
    def cancel(self, reason=""): return False
    def describe(self): return "none"
tmp = tempfile.mkdtemp(prefix="sol_stock_")
def say(text, snap=HERE_SOL):
    ACT.clear(); c = CS.Chat.__new__(CS.Chat)
    c.dir, c.log, c.goals, c.pending_card, c._forced, c._turn_action_results = tmp, (lambda x: None), Goals(), None, None, []
    c.hist, c.lock, c._save, c.publish = [], threading.Lock(), (lambda: None), (lambda: None)
    c._pre_intents([{"role": "user", "text": text}], snap, None); return c
names = lambda c: [r[0] for r in (c.pending_card or [])]
c = say("وهلا شوفي عنا بذور وادوات زراعة")
ck("our stock: answered from the scan, not the model", c._forced and c._forced.startswith("هاد اللي عنا"), c._forced)
ck("our stock: seeds and tools by their game names", set(names(c)) == {"Basil Seeds", "Carrot Seeds", "Garden Hoe", "Shovel"}, names(c))
ck("our stock: counts and where", [r for r in c.pending_card if r[0] == "Basil Seeds"][0][1] == "5")
ck("nothing about registering", "مسجل" not in c._forced, c._forced)
c = say("شو معك بذور"); ck("hers: only what she carries", names(c) == ["Carrot Seeds"] and ("sol_farm", "report") not in ACT, (names(c), ACT))
c = say("كم عنا بذور", {"containers": [{"where": "square", "items": [{"type": "Base.Nails", "name": "Nails", "cat": "Material", "count": 1}]}], "sol": {"x": 1}})
ck("none: says so, no table", c._forced == "ما لقيت بذور ولا أدوات زراعة بالمخزون اللي فحصته." and c.pending_card is None, c._forced)
c = say("شو معك بذور", {"containers": [], "sol": {"x": 1}}); ck("none with her", c._forced == "ما معي بذور ولا أدوات زراعة.", c._forced)
for t in ["فحص المخزون الي عنا", "شو عندنا مؤن"]:
    ck("the full table is untouched: " + t, ("farm_stock" not in [n for n, a in CS.intents(t)]))
ck("full table keeps everything", any(r[0] == "Nails" for r in W.supplies_table(SNAP)))
# ---- the items in his crates, by the game's own scripts, through the code that counts them
import glob, re
from kahlua_env import lua51
import farm_talk as FT
G = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media"
CL = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\lua\client"
scripts = "".join(open(f, encoding="utf-8", errors="replace").read() for f in glob.glob(G + r"\scripts\generated\items\*.txt"))
def tags(name):
    m = re.search(r"item\s+%s\s*\{(.*?)\n\s*\}" % name, scripts, re.S)
    t = re.search(r"Tags\s*=\s*([^,\n]+)", m.group(1)) if m else None
    return [x.strip() for x in t.group(1).split(";")] if t else []
ck("real scripts: seed exists with its tag", "base:isseed" in tags("BasilSeed"), tags("BasilSeed"))
view = open(CL + r"\SolFarmView.lua", encoding="utf-8").read().replace("\r\n", "\n")
gu_src = open(CL + r"\SCGameplayUtil.lua", encoding="utf-8").read().replace("\r\n", "\n")
def cut(s, start):
    a = s.index(start); return s[a:s.index("\nend\n", a) + 5]
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("""
function call(o, n) if o == nil or o[n] == nil then return nil end return o[n](o) end
function tcall(f, ...) return f(...) end
U = {}
U.call = function(o, n, ...) if o == nil or o[n] == nil then return nil, false end return o[n](o, ...), true end
U.itemType = function(i) return i.full end
CURE_ITEMS = {}
SEEDS = {}
function seedMap() return SEEDS end
function goodSeed() return true end
function drainUses(i) return i.uses or 1 end
function fluidUses() return 1 end
function make(full, list)
    local n = 0
    local tags = { iterator = function() local i = 0; return { hasNext = function() return i < #list end, next = function() i = i + 1; return { getTranslationName = function() return nil end, tostring = list[i] , _s = list[i] } end } end }
    return { full = full, getTags = function() return tags end }
end
""")
L.execute(cut(gu_src, "local function normalizedTagName(value)").replace("local function normalizedTagName", "function normalizedTagName", 1))
L.execute(cut(gu_src, "function U.itemHasTag(item, tag)"))
L.execute("gu = U\n" + cut(view, "local function classify(gu, item, full, st)").replace("local function classify", "function classify", 1))
L.execute("local real = tostring; tostring = function(v) if type(v) == 'table' and v._s then return v._s end return real(v) end")
L.execute("function st() return { seeds = {}, tools = 0, cans = 0, waterUses = 0, sprays = {}, compost = 0, fert = 0 } end")
g = L.globals()
conf = open(G + r"\lua\server\Farming\farming_vegetableconf_herbs.lua", encoding="utf-8", errors="replace").read()
ck("real conf: basil's seed type", '"Base.BasilSeed"' in conf)
L.execute('SEEDS["Base.BasilSeed"] = "Basil"')
def run(full, name):
    item = g.make(full, L.table_from(tags(name))); s = g.st(); g.classify(g.gu, item, full, s); return s
ck("real item: seeds count", run("Base.BasilSeed", "BasilSeed").seeds.Basil == 1)
for name in ("GardenHoe", "Shovel", "HandFork", "GardenFork"): ck("real item digs: " + name, run("Base." + name, name).tools == 1, tags(name))
ck("real item: fertilizer", run("Base.Fertilizer", "Fertilizer").fert == 1, tags("Fertilizer"))
ck("real item: compost bag", run("Base.CompostBag", "CompostBag").compost == 1, tags("CompostBag"))
ck("real item: a rake is not a digging tool", run("Base.Rake", "Rake").tools == 0)
for t_ in ["شتغلي بالمزرعة", "اشتغلي بالمزرعة", "سول اشتغلي بالزراعة", "اشتغلي بالارض", "بلشي بالمزرعة", "اهتمي بالمزرعة"]:
    ck("farm work order: " + t_, FT.order(t_) == ("sol_farm", "keeper"), FT.order(t_))
ck("work not on the farm is not a farm order", FT.order("اشتغلي منيح") is None, FT.order("اشتغلي منيح"))
line = FT.storage_line("storage:scan;regs=farming@1,1,crate|output@2,2,crate#apply;zones=0/0;regs=6/6;fail=")
ck("registered: no number that reads like items", "0 قطعة" not in line and "سجلت 6 مخزن" in line and "مسجلة من قبل" in line, line)
ORDERS = [("سول زكاتك احصدي الحصاد", "harvest"), ("زكاتك حصدي الحصاد", "harvest"), ("زكاتم حصدي الحصاد", "harvest"), ("احصدي الزرع", "harvest"), ("بليز حصدي المحصول", "harvest"), ("الله يخليكي احصدي", "harvest"), ("قطفي الجاهز", "harvest"), ("احصدي الحصاد زكاتك", "harvest"),
    ("زكاتك اسقي الزرع", "water"), ("اسقي", "water"), ("سقي المزرعة", "water"), ("يا سول اسقي النباتات", "water"), ("شو رأيك تسقي الزرع", "water"),
    ("زكاتك عالجي الزرع", "cure"), ("عالجي الزرع من العفن", "cure"), ("داوي النباتات", "cure"), ("رشي الزرع", "cure"),
    ("زكاتك حطي للزرع سماد", "compost"), ("حطي سماد للزرع", "compost"), ("حطي سماد", "compost"), ("سمدي الزرع", "compost"), ("ضيفي سماد عالزرع", "compost"),
    ("زكاتك نظفي الزرع من العشب", "weed"), ("نضفي المزرعة من الاعشاب", "weed"), ("قلعي العشب", "weed"), ("اقلعي العشب من الزرع", "weed"), ("نتشي الحشيش", "weed"),
    ("احرثي الارض", "plow"), ("زكاتك فلحي الارض", "plow"),
    ("زكاتك ازرعي البذور اللي بهاد الموسم", "plant:any"), ("زكاتك زرعي اليذور الي بهاد الموسم", "plant:any"), ("ازرعي", "plant:any"), ("ازرعي بذور الموسم", "plant:any"), ("ازرعي جزر", "plant:Carrots"), ("زكاتك ازرعي بذور جزر", "plant:Carrots")]
for words, op in ORDERS:
    ck("order: " + words, FT.order(words) == ("sol_farm", op), FT.order(words))
for words in ["جربي الحصاد", "نظفي البيت", "نظفي", "عالجي جرحي", "حطي الاكل بالبراد", "اقلعي من هون"]:
    ck("not a farm order: " + words, FT.order(words) is None, FT.order(words))
ck("the internal hook stays", FT.order("sol_farm_try plow") == ("sol_farm_try", "plow"))
for words in ["شو زبط معك بالزراعة", "شو اللي جربتي بالمزرعة"]: ck("what she tried: " + words, FT.order(words) == ("sol_farm", "proven"), FT.order(words))
ck("forget the tries", FT.order("انسي التجارب") == ("sol_farm", "forget"), FT.order("انسي التجارب"))
ck("no codes in chat", all(not any(c.isascii() and c.isalpha() for c in FT.trial_line(op, {"ok": False, "reason": "some_code_x"})) for op in FT.TRY_NAME))
ck("nothing to harvest, in words", FT.trial_line("harvest", {"ok": False, "reason": "nothing_to_try_on"}) == "ما لقيت زرعة بدها حصاد هلأ.")
ck("what she tried, in words", FT.proven_line('proven:{"harvest": {"vanilla": "ok"}, "water": {"vanilla": "stalled"}}') == "زبط معي: الحصاد. ما زبط لسا: السقاية.", FT.proven_line('proven:{"harvest": {"vanilla": "ok"}, "water": {"vanilla": "stalled"}}'))
for op in ("cure", "compost", "weed", "plow"): ck("an answer in her words: " + op, FT.reply_for(op, {"ok": True, "reason": "ok"}) in FT.ACK[op])
ck("trial answer: started", FT.trial_line("harvest", {"ok": True, "reason": "trial:harvest:started"}) == "عم جرب الحصاد هلأ.")
# ---- the scan's own view of a container, with the patch applied, on real items
import shutil, subprocess
d = tempfile.mkdtemp(prefix="sol_scan_"); shutil.copy(CL + r"\SolBaseScan.lua", d); sc = os.path.join(d, "SolBaseScan.lua")
if "rec.farmItems" not in open(sc, encoding="utf-8").read():
    subprocess.check_call([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "apply_s32_lua.py"), sc], stdout=subprocess.DEVNULL)
scan = open(sc, encoding="utf-8").read().replace("\r\n", "\n")
ck("scan still compiles", not isinstance(lua51.LuaRuntime().globals().loadstring(scan), tuple))
L.execute("TOOLWORDS = {}; function method() return nil end; function callf(f, ...) if f == nil then return nil end return f(...) end")
L.execute("U.inventoryItems = function(c, n) return c end; U.itemType = function(i) return i.full end")
L.execute("local call = callf\n" + cut(scan, "local function classify(gu, cont, rec)").replace("local function classify", "function scanClassify", 1))
def crate(*names):
    L.execute("CRATE = {}")
    for n in names:
        L.globals().CRATE[len(L.globals().CRATE) + 1] = g.make("Base." + n, L.table_from(tags(n)))
    L.execute("REC = {}; CLASS = scanClassify(U, CRATE, REC)")
    return g.REC.farmItems, g.CLASS
fi, cl = crate("BasilSeed", "GardenHoe", "Fertilizer"); ck("his seed crate counts", fi == 3 and cl == "farming", (fi, cl))
fi, cl = crate("Crowbar", "PipeWrench", "Plank", "SteelSheet", "HuntingKnife", "BasilSeed", "LeafRake"); ck("his mixed crate still counts as having farm items", fi == 1, (fi, cl))
fi, cl = crate("Plank", "Crowbar"); ck("no farm items: none claimed", (fi or 0) == 0, (fi, cl))
ACT.clear(); c = say("اهتمي بالمزرعة"); ck("farm work: no registering step", ACT[:1] == [("sol_farm", "keeper")], ACT)
for why in ("no_path", "bag_full", "body_lost", "in_vehicle"): ck("a reason in her words: " + why, not any(ch.isascii() and ch.isalpha() for ch in FT.why_ar(why)), FT.why_ar(why))
for words in ["سول صفي السيارة بالكراج", "صفي السيارة", "زكاتك صفي السيارة بالموقف", "ركني السيارة بالكراج", "حطي السيارة بالكراج", "صفي بالكراج", "دخلي الفان عالكراج"]:
    ck("park: " + words, CS.intents(words) == [("park_car", {})], CS.intents(words))
for words in ["صفي معي", "حطي الاكل بالبراد", "وين السيارة"]: ck("not parking: " + words, CS.intents(words) != [("park_car", {})])
_GR = {}
CS.gps_request = lambda lua, f: _GR.update(f) or 1
CS._drive_outcome = lambda lua, rid, base: dict(base, ok=True, reason="driving")
c = say("صفي السيارة بالكراج", dict(HERE_SOL, solParking={"x": 120, "y": 230}))
ck("park: goes to the marked area", _GR.get("x") == 120 and _GR.get("y") == 230 and c._forced == "رايحة صفها بالكراج.", (c._forced, _GR))
c = say("صفي السيارة بالكراج", HERE_SOL); ck("park: no marked area: says so", "حدده" in c._forced, c._forced)
for words in ["مرحبا", "سول مرحبا", "مرحبا!", "صباح الخير", "زكاتك مرحبا", "السلام عليكم"]:
    c = say(words); ck("greeting answered: " + words, c._forced and not any(w in c._forced for w in ("بيت", "خبر")), c._forced)
ck("more than a greeting goes the normal way", CS.greeting_line("مرحبا شو عنا اليوم") is None)
import goal_engine as GE
for reason, failed in [("walking_to_door", False), ("moving_to_wheel", False), ("could_not_reach_door", True), ("no_vehicle_near", True)]:
    ck("the drive to him: %s" % reason, (GE.FetchPlayer._gps_failed(None, {"result": "failed", "reason": reason}) is not None) == failed)
for words in ["هاد المكان هو بيتنا", "سول هاد المكان هو بيتنا", "هون بيتنا", "هاد بيتنا", "هذا هو بيتنا", "بيتنا هون", "اعتبري هاد المكان بيتنا"]:
    ck("home named: " + words, "set_home" in [n for n, a_ in CS.intents(words)], CS.intents(words))
ck("a sentence about home is not naming it", "set_home" not in [n for n, a_ in CS.intents("شو في بالبيت")])
import shutil as _s
_d = tempfile.mkdtemp(prefix="sol_home_"); _s.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_backup", "20261109_043225_night_before_apply", "Sol_LAB", "42", "media", "lua", "client", "SolWorldScan.lua"), _d)
subprocess.check_call([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "apply_s35_lua.py"), os.path.join(_d, "SolWorldScan.lua")], stdout=subprocess.DEVNULL)
_h = open(os.path.join(_d, "SolWorldScan.lua"), encoding="utf-8").read().replace("\r\n", "\n")
ck("world scan still compiles", not isinstance(lua51.LuaRuntime().globals().loadstring(_h), tuple))
_a = _h.index("    if snap.solHome == nil and"); _b = _h.index("    if type(SolFarmWork)", _a)
L2 = lua51.LuaRuntime(unpack_returned_tuples=True)
L2.execute("""snap = {}
SurvivorCompanion = { BaseLife = { active = function() return ZONES end } }
ZONES = { zones = { { kind = 'farm', x1 = 1, x2 = 2, y1 = 1, y2 = 2 }, { kind = 'area', x1 = 100, x2 = 120, y1 = 200, y2 = 220, z = 0 }, { kind = 'area', x1 = 130, x2 = 110, y1 = 240, y2 = 210, z = 0 } } }
function run() """ + _h[_a:_b] + """ end""")
L2.execute("run()")
ck("the base he marked is home, its middle", L2.eval("snap.solHome.x") == 115 and L2.eval("snap.solHome.y") == 220 and L2.eval("snap.solHome.fromBase") is True, L2.eval("snap.solHome.x"))
L2.execute("snap = { solHome = { x = 5, y = 6 } }; run()"); ck("a home he named wins", L2.eval("snap.solHome.x") == 5)
L2.execute("snap = {}; ZONES = {}; run()"); ck("no base, no home", L2.eval("snap.solHome") is None)
L2.execute("snap = {}; ZONES = { zones = { { kind = 'parking', x1 = 10, x2 = 14, y1 = 20, y2 = 30 } } }; run()"); ck("the parking area is known", L2.eval("snap.solParking.x") == 12 and L2.eval("snap.solParking.y") == 25)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
