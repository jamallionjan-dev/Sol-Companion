import json, os, sys, tempfile, threading, shutil
tmp = tempfile.mkdtemp(); os.environ["LOCALAPPDATA"] = tmp
zroot = tempfile.mkdtemp(); os.makedirs(os.path.join(zroot, "Saves", "Sandbox", "2026-10-23_14-43-18"))
os.environ["USERPROFILE"] = os.path.dirname(zroot) if False else ""
import world_knowledge as W, providers as P, chat_service as CS
_sf = W.save_folder
W.save_folder = lambda world, zd=None: _sf(world, zd or zroot)
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
snap = json.load(open("/tmp/snapshot_sample.json"))
mem = W.Memory(snap["world"])
check("per-world memory folder created", os.path.isfile(os.path.join(tmp, "SolMind", "worlds", "Sandbox__2026-10-23_14-43-18", "memory.json")))
f = W.food_report(snap)
check("food: apple 1 day before rotting flagged, rice (never rots) not", f["items"] == 2 and f["spoiling_soon"][0][0] == "Apple" and f["calories"] == 600)
w = W.water_report(snap)
check("water: 1.5 L clean, 2 L tainted, tap stops in 3 days", w["clean_liters"] == 1.5 and w["tainted_liters"] == 2 and w["water_off_in_days"] == 3)
nd = W.needs(snap, mem); kinds = {(n["who"], n["need"]) for n in nd}
check("needs from game data: player cold, hungry, wet, bleeding; stock: eat apple first, store water",
      {("player", "warmth"), ("player", "eat"), ("player", "dry_clothes"), ("player", "bandage"), ("stock", "eat_first"), ("stock", "store_water")} <= kinds)
fi = W.find_items(snap, "nail")
check("find nails in the player's bag", fi == [{"name": "Nails", "count": 2, "where": "your bag"}])
check("find planks in the pickup trunk", W.find_items(snap, "plank")[0]["where"] == "Pickup (TruckBed)")
r = W.run_tool("remember_place", {"name": "مستودع المزرعة", "note": "بذور"}, snap, mem)
check("remember place stores items seen there", r["saved"] == "مستودع المزرعة" and r["items_seen"] >= 3)
rc = W.run_tool("recall_places", {"item": "seed"}, snap, mem)
check("recall places that had seeds", rc["places"][0]["name"] == "مستودع المزرعة" and "Seeds Carrot" in rc["places"][0]["matching"])
W.run_tool("set_home", {"name": "بيتنا"}, snap, mem)
mem2 = W.Memory(snap["world"]); check("home + places persist across restarts", mem2.data["home"]["name"] == "بيتنا" and len(mem2.data["places"]) == 1)
os.makedirs(os.path.join(zroot, "Saves", "Sandbox", "other_world"))
s2 = dict(snap); s2["world"] = {"name": "other_world", "mode": "Sandbox"}; m3 = W.Memory(s2["world"])
check("a new world gets its own empty memory", m3.data["home"] is None and m3.data["places"] == [])
shutil.rmtree(os.path.join(zroot, "Saves", "Sandbox", "other_world"))
ghost = W.Memory({"name": "never_saved_here", "mode": "Sandbox"})
removed = W.cleanup_deleted_worlds(zomboid_dir=zroot, log=lambda m: None)
check("save deleted -> its memory deleted; existing save kept", removed == ["Sandbox__other_world"] and os.path.isdir(mem.dir))
check("a memory whose save path was never seen is NOT wiped (wrong-path safety)", os.path.isdir(ghost.dir))
shutil.rmtree(os.path.join(zroot, "Saves", "Sandbox", "2026-10-23_14-43-18"))
check("deleting the played save deletes its memory too", W.cleanup_deleted_worlds(zomboid_dir=zroot, log=lambda m: None) == ["Sandbox__2026-10-23_14-43-18"])
mem = W.Memory(snap["world"])
for h, v in ((10, 0.1), (11, 0.12), (12, 0.14), (13, 0.16)):
    s3 = json.loads(json.dumps(snap)); s3["time"]["ageHours"] = h; s3["player"]["stats"]["HUNGER"] = v; W.hunger_rate(mem, s3)
check("hunger rate measured from the game (0.48/day)", W.hunger_rate(mem, s3) == 0.48)
txt = W.situation_text(snap, mem)
check("situation text has the facts", "air 4.5" in txt and "1.5 L clean" in txt and "Pickup fuel 12/50" in txt and "warmth" in txt)
# ---- v0.6.0: semantic search, supplies table, location / skills / temperatures
s4 = json.loads(json.dumps(snap))
s4["containers"].append({"where": "square", "x": 7006, "y": 8436, "room": "bedroom", "items": [{"type": "Base.Nails_Red", "name": "Fashion Nails - Blood Red", "count": 1, "cat": "Accessory"}]})
check("'nails' finds real nails, not nail polish (problem 16)", [r["name"] for r in W.find_items(s4, "nails")] == ["Nails"])
s5 = json.loads(json.dumps(s4)); s5["containers"] = [c for c in s5["containers"] if c["where"] != "player"]
check("only nail polish around -> it is still found, honestly", [r["name"] for r in W.find_items(s5, "nails")] == ["Fashion Nails - Blood Red"])
rows = {r[0]: r for r in W.supplies_table(snap, mem)}
check("supplies table built from data: nails 2 'little', clean water 1.5 L", rows["مسامير"][1] == "2" and rows["مسامير"][2] == "قليل" and rows["ماء نظيف (لتر)"][1] == "1.5")
check("supplies table: food verdict with spoiling count", "يفسد قريبًا" in rows["طعام"][2])
s6 = json.loads(json.dumps(snap)); s6["player"]["temperatureBody"] = 36.9; s6["sol"]["skills"] = {"Aiming": 3, "Cooking": 1}; s6["sol"]["profession"] = "nurse"
txt6 = W.situation_text(s6, mem)
check("situation has coordinates (problem 11)", "Player position: x 100, y 201" in txt6 and "Sol position: x 101, y 201" in txt6)
check("situation has Sol's skills and profession (problem 9)", "Aiming 3" in txt6 and "Cooking 1" in txt6 and "nurse" in txt6)
check("situation separates outside air and body temperature (problem 10)", "outside air 4.5 C" in txt6 and "body temperature 36.9" in txt6)
# ---- tool-calling loop against a fake OpenAI-compatible server
calls = []
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        calls.append(body)
        tool_msgs = [m for m in body["messages"] if m["role"] == "tool"]
        if not tool_msgs:
            out = {"choices": [{"message": {"content": "", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "find_items", "arguments": json.dumps({"query": "nail"})}}]}}]}
        else:
            got = json.loads(tool_msgs[-1]["content"])["results"][0]
            out = {"choices": [{"message": {"content": "لدينا %d مسامير في %s." % (got["count"], got["where"])}}]}
        b = json.dumps(out).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
srv = ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
P.PROVIDERS["groq"]["base"] = "http://127.0.0.1:%d" % srv.server_address[1]
ran = []
reply = P.chat_with_tools("groq", "k", "openai/gpt-oss-120b", [{"role": "user", "content": "هل لدينا مسامير؟"}], W.TOOLS,
                          lambda n, a: (ran.append((n, a)), W.run_tool(n, a, snap, mem))[1], system="sys")
check("model called find_items with the query", ran == [("find_items", {"query": "nail"})])
check("final answer built from the tool result", reply == "لدينا 2 مسامير في your bag.")
check("tools and reasoning settings sent; system contains situation", calls[0]["tools"][0]["function"]["name"] == "find_items" and calls[0]["reasoning_effort"] == "low")
# chat service builds the situation into the system prompt
lua = tempfile.mkdtemp(); open(os.path.join(lua, W.SNAP), "w").write(json.dumps(snap))
ch = CS.Chat(lua, log=lambda m: None)
s_, m_ = ch._world(); sp = ch.system_prompt(s_, m_)
check("chat system prompt = persona + world rules + live situation", "Situation:" in sp and "find_items" in sp and "1.5 L clean" in sp)
srv.shutdown()
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
