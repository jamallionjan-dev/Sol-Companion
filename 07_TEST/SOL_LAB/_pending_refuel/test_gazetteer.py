"""The map index with real coordinates, and what she may say about it."""
import os, sys
M = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind"
sys.path.insert(0, M)
import gazetteer as GZ, memory_answers as MA, reply_gate as RG, world_knowledge as W
W_PLACE = W._supply_place
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
class Mem:
    def __init__(self): self.data = {"places": []}; self.saved = 0
    def save(self): self.saved += 1
g = GZ.load()
ck("index loads", g is not None)
for name, x, y in [("Riverside", 6450, 5430), ("Muldraugh", 10754, 9926), ("West Point", 11654, 6864), ("Rosewood", 8159, 11661), ("Louisville", 13077, 2238), ("Fallas Lake", 7253, 8279), ("Valley Station", 13447, 5278), ("March Ridge", 10130, 12801), ("Ekron", 634, 9746), ("Irvington", 2427, 14185), ("Echo Creek", 3589, 10952), ("Brandenburg", 2056, 6070)]:
    t = g.town_at(x, y); ck("town at its own label: " + name, t and t["n"] == name, t and t["n"])
for name, x, y in [("Fallas Lake", 7317, 8182), ("Muldraugh", 10800, 9600), ("West Point", 11900, 6900), ("Louisville", 12800, 1500), ("Riverside", 6500, 5300), ("Rosewood", 8100, 11500)]:
    t = g.town_at(x, y); ck("town inside: %s at %d,%d" % (name, x, y), t and t["n"] == name, t and t["n"])
ck("out in the country: no town", g.town_at(5200, 12400) is None, g.town_at(5200, 12400))
ck("every town has an Arabic name", all(t["n"] in GZ.TOWN_AR for t in g.towns), [t["n"] for t in g.towns if t["n"] not in GZ.TOWN_AR])
counts = {k: len(v) for k, v in g.by_kind.items()}
print("     buildings by kind:", sorted(counts.items(), key=lambda kv: -kv[1])[:20])
for k in ("gas", "hotel", "hospital", "police", "school", "church", "bank", "grocery", "restaurant", "house"): ck("has some: " + k, counts.get(k, 0) > 0, counts.get(k))
every = lambda x, y: True
b = g.nearest_kind("gas", 7317, 8182, every); ck("the nearest station to his forecourt is close", b and abs(b["x"] - 7317) < 40 and abs(b["y"] - 8182) < 40, b)
ck("a brand has its name", b and "كازية" in b["label"], b)
b = g.building_at(10000, 10000, 3); ck("nothing in the woods is no building", b is None or isinstance(b, dict), b)
named = [p for p in g.places() if "Sunstar" in p[0]]; ck("named building from the game", bool(named), [p[0] for p in g.places()][:8])
ck("a landmark by name", any("Knox" in p[0] or "Hospital" in p[0] for p in g.places()))
ck("streets loaded with geometry", len(g.streets) > 50 and g.street_point("Oak St", 11000, 6700) is not None, len(g.streets))

m = Mem()
ck("nowhere yet", not GZ.visited(m, 7317, 8182))
ck("a new place is noted", GZ.mark_visited(m, 7317, 8182) is True)
ck("here counts", GZ.visited(m, 7317, 8182)); ck("within reach counts", GZ.visited(m, 7340, 8182)); ck("far does not", not GZ.visited(m, 7500, 8182))
ck("the same place is not new", GZ.mark_visited(m, 7318, 8183) is False)
GZ.mark_visited(m, 7317, 8182, 7500, 8182); ck("the road between two looks counts", GZ.visited(m, 7420, 8182))
ck("beside that road too", GZ.visited(m, 7420, 8200)); ck("but not well off it", not GZ.visited(m, 7420, 8400))

HERE = {"player": {"x": 7317, "y": 8182}, "sol": {"x": 7318, "y": 8182}, "currentStreet": "Main St", "knownStreets": ["Main St", "Oak Ave"]}
been = Mem(); GZ.mark_visited(been, 7317, 8182)
def ask(t, snap=HERE, mem=been): return MA.answer(t, snap, mem, None, None, g)
for q in ["شو اسم هالمدينة", "سول شو اسم البلدة", "شو اسم هالضيعة", "وين نحنا بأي مدينة"]:
    r = ask(q); ck("town: " + q, r and "فالاس ليك" in r, r)
r = ask("وين نحنا"); ck("where we are has street and town", r and "Main St" in r and "فالاس ليك" in r, r)
r = ask("شو اسم الشارع"); ck("street question is not swallowed", r and "Main St" in r, r)
r = ask("شو هالبناية"); ck("this building: something real", r and r.startswith("هاد"), r)
r = ask("شو هاد المحل", {"player": {"x": 7000, "y": 12000}, "sol": {"x": 7000, "y": 12000}}, Mem()); ck("this building where she has not been", r == MA.NOT_BEEN, r)
r = ask("في فندق قريب"); ck("no hotel she has been near", r == MA.NOT_BEEN, r)
for q in ["في كازية قريب", "وين اقرب كازية؟"]: ck("stations stay with the station memory: " + q, ask(q) is None, ask(q))
for q in ["عبي بنزين من اقرب كازية", "سوقي لأقرب كازية", "الجو بارد هون؟", "الدكتور في البيت", "روحي عالفندق"]: ck("not a place question: " + q, ask(q) is None, ask(q))
r = ask("وين مدينة لويزفيل؟"); ck("another town by name is not this town", r == MA.NOT_BEEN, r)
r = ask("شو أقرب مدينة؟"); ck("nearest town: only one she knows", r and "فالاس ليك" in r and "مولدرو" not in r, r)
r = ask("شو أقرب مدينة؟", {"player": {"x": 5200, "y": 12400}, "sol": {"x": 5200, "y": 12400}}, Mem()); ck("nearest town when she knows none", r == MA.NOT_BEEN, r)
r = ask("شو اسم هالمدينة", {"player": {"x": 5200, "y": 12400}, "sol": {"x": 5200, "y": 12400}}); ck("out in the country: says so, names nowhere she has not been", r == "نحنا برا البلدات.", r)
trip = Mem(); h = g.buildings[g.by_kind["hotel"][0]]; GZ.mark_visited(trip, 7317, 8182); GZ.mark_visited(trip, h[0], h[1])
r = ask("وين في فندق", HERE, trip); ck("a hotel she has passed: which way", r and "فندق" in r and "منك" in r, r)
for q in ["كيف بروح عـ مولدرو", "كيف بروح ع مولدرو", "وين مولدرو", "where is Muldraugh"]:
    r = ask(q); ck("not been there: " + q, r == MA.NOT_BEEN, r)
went = Mem(); GZ.mark_visited(went, 10754, 9926)
for q in ["كيف بروح عـ مولدرو", "وين مولدرو", "وين مولدراف"]:
    r = ask(q, HERE, went); ck("been there: " + q, r and "مولدرو" in r and "منك" in r, r)
for q in ["وين انتي", "وين البيت", "وين السيارة"]:
    r = ask(q, HERE, been); ck("her other answers still come first: " + q, r != MA.NOT_BEEN, r)
# his four lines, and the farm question in general
FARM = {"player": {"x": 7317, "y": 8182}, "sol": {"x": 7318, "y": 8182}, "currentStreet": "Main St"}
for q in ["سول في شي مزرعة قريبة علينا بالمنطقة", "في حقل قريب"]:
    r = MA.answer(q, FARM, Mem(), None, None, g, lambda: None); ck("no farm she has been near, honestly: " + q, r == MA.NOT_BEEN, r)
r = MA.answer("تذكري مرينا شي من جنب مزرعة او بيت فيه حديقة زراعية", FARM, Mem(), None, None, g, lambda: None); ck("has not passed one: says so", r and "ما بتذكر" in r, r)
mg = Mem(); GZ.mark_visited(mg, 7317, 8182)
r = MA.answer("تذكري مرينا شي من جنب مزرعة او بيت فيه حديقة زراعية", FARM, mg, None, None, g, lambda: [(7330, 8190), (9000, 9000)]); ck("a garden she saw: which way, where", r and "حديقة زراعية" in r and "منك" in r and r.startswith("إيه") and "فالاس ليك" in r, r)
r = MA.answer("سول في شي مزرعة قريبة علينا بالمنطقة", FARM, mg, None, None, g, lambda: [(7330, 8190)]); ck("nearby garden: found", r and "حديقة زراعية" in r, r)
f0 = next(i for i in g.by_kind["farm"] if g.kinds[g.buildings[i][4]] == "farmland"); fb = g.buildings[f0]
mf = Mem(); GZ.mark_visited(mf, fb[0], fb[1]); SNEAR = {"player": {"x": fb[0] + 20, "y": fb[1]}, "sol": {"x": fb[0] + 20, "y": fb[1]}}
r = MA.answer("في مزرعة قريبة", SNEAR, mf, None, None, g, lambda: None); ck("farm land from the game's own zones", r and ("مزرعة" in r or "زراعية" in r), r)
ck("no garden data: still answers", MA.answer("في مزرعة قريبة", SNEAR, mf, None, None, g, None) is not None)
ck("parse gardens", MA.parse_gardens("gardens:1,2;3,4") == [(1, 2), (3, 4)] and MA.parse_gardens("gardens:") == [] and MA.parse_gardens("gardens:x,y;5,6") == [(5, 6)])
ck("a street near a point", g.street_near(11000, 6700) is not None, g.street_near(11000, 6700)); ck("no street in the far woods", g.street_near(100, 100) is None)
import chat_service as CS0
for t, want in [("ركبي السيارة", "board_vehicle"), ("سول اركبي السيارة", "board_vehicle"), ("اركبي الفان", "board_vehicle"), ("يلا اركبي", "board_vehicle"), ("اركبي", "board_vehicle"), ("طلعي عالسيارة", "board_vehicle"), ("نزلي", "exit_vehicle"), ("سول نزلي", "exit_vehicle"), ("انزلي من السيارة", "exit_vehicle"), ("اطلعي من السيارة", "exit_vehicle"), ("الحقيني", "follow"), ("اتبعيني", "follow"), ("ضلي هون", "stay")]:
    a = [x[1].get("action") for x in CS0.intents(t) if x[0] == "action"]; ck("order, no model: " + t, a == [want], list(CS0.intents(t)))
for t, want in [("سوقي", "drive_take_wheel"), ("سول سوقي السيارة", "drive_take_wheel"), ("وقفي", "drive_stop")]: ck("order, no model: " + t, [x[0] for x in CS0.intents(t)] == [want], list(CS0.intents(t)))
for t in ["وين ركبت السيارة", "مين نزلي بالخبر", "دوري"]: ck("not an order: " + t, not [x for x in CS0.intents(t) if x[0] == "action" and x[1].get("action") in ("board_vehicle", "exit_vehicle")], list(CS0.intents(t)))
for full, shown in [("Base.HandShovel", "Gardening Trowel"), ("Base.Shovel", "Spade"), ("Base.WateredCan", "Watering Can"), ("Base.CompostBag", "Compost Bag"), ("Base.CarrotSeed", "Carrot Seeds")]: ck("the game's own name: " + full, CS0.item_name(full) == shown, CS0.item_name(full))
r = CS0.role_reply("farmer", {"ok": False, "reason": "gate:farmer;miss=farm_supplies,out_storage;have=seed:3,tool:0,can:0,compost:0,spray:0,stor:1,unloaded:0"})
ck("she asks by the game's names, and only for what is missing", "Gardening Trowel" in r and "Watering Can" in r and "Compost Bag" in r and "Carrot Seeds" not in r, r)
ck("a room has one name", W_PLACE({"where": "house", "room": "shed"}) == "السقيفة" and W_PLACE({"where": "house", "room": "kitchen"}) == "المطبخ", W_PLACE({"where": "house", "room": "shed"}))
ck("no index: the question falls through", MA.answer("شو اسم هالمدينة", HERE, been, None, None, None) is None)
f = MA.facts(HERE, been, [(7330, 8182, 50, "gas2go")], g); ck("facts for a model carry the town", "البلدة: فالاس ليك" in f, f)
n = MA.known_names(HERE, been, None, g); ck("the gate knows the town she is in", any(x[0] == "فالاس ليك" for x in n), n[:5])
ck("the gate does not know a town she has not been to", not any(x[0] == "مولدرو" for x in n))
ck("a misspelt town is put right", RG.match_name("فالاس لاك", n) == "فالاس ليك", RG.match_name("فالاس لاك", n))
import chat_service as CS
class Goals: pass
c = CS.Chat.__new__(CS.Chat); c.log = lambda x: None; c.goals = Goals(); c._last_at = (1, 1)
died = Mem(); died.data["deaths"] = 0; GZ.mark_visited(died, 7317, 8182); died.data["places"] = [{"name": "x"}]
ck("she is alive: her map stays", c._life_watch({"solLife": {"deaths": 0}}, died) is False and GZ.visited(died, 7317, 8182))
ck("she came back: told", c._life_watch({"solLife": {"deaths": 1}}, died) is True)
ck("death: her map is gone", not GZ.visited(died, 7317, 8182) and died.data["places"] == [] and died.saved == 1)
ck("death: the next look does not draw a line from her old body", c._last_at is None)
r = ask("وين مولدرو", HERE, died); ck("death: she no longer knows a place she knew", r == MA.NOT_BEEN, r)
tr = Mem(); c._last_at = None; c._note_where_she_is({"sol": {"x": 1000, "y": 1000}}, tr); c._note_where_she_is({"sol": {"x": 1100, "y": 1000}}, tr)
ck("the Mind notes her path between two looks", GZ.visited(tr, 1050, 1000) and tr.saved >= 2, tr.saved)
c._note_where_she_is({"sol": {"x": 4000, "y": 4000}}, tr); ck("a jump is not a road", not GZ.visited(tr, 2500, 2500))
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
