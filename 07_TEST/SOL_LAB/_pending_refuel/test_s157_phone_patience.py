"""s157 offline: a copy of the Mind with apply_s157 applied; the model is a stub that times out (or records the wait it was
given). Nothing live is touched. Offline PASS is not Runtime PASS.
Run: python test_s157_phone_patience.py [mind dir]      child: --child <mind copy> <lua dir>"""
import json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
MIND = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.path.abspath(os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind"))
IDS = ["sol_drink", "sol_wash", "sol_open_door", "sol_close_door", "sol_open_window", "sol_horn", "sol_eat", "sol_engine", "sol_give", "sol_headlights"]


def child(mind, lua):
    sys.path.insert(0, mind)
    import chat_service as CS, model_router as MR, providers as P, settings_service as SS, world_knowledge as W, reply_gate as RG
    assert os.path.dirname(os.path.abspath(CS.__file__)) == os.path.abspath(mind)
    W.situation_text = lambda s, m: "world"
    CS.time.sleep = lambda s: None
    GAME, LOG, WAIT, MODE = [], [], [], {"m": "timeout"}
    CS.run_action = lambda d, action, option=None, wait=3.0: (GAME.append([action, option]) or {"ok": True, "reason": ""})
    CS.load_actions = lambda d: [{"id": i, "kind": "sol", "label": i} for i in IDS]
    def model(pid, key, mdl, msgs, system="", custom_base="", max_tokens=0, timeout=0):
        WAIT.append(timeout)
        if MODE["m"] == "timeout": raise P.ProviderError("timeout")
        return MODE["m"]
    P.chat = model
    cfg = {"source": "local", "provider": "custom", "model": "test", "base": ""}
    SS.load_config = lambda: cfg
    def chat():
        c = CS.Chat.__new__(CS.Chat)
        c.dir, c.log, c._forced, c._sheet = lua, LOG.append, None, None
        c._world = lambda: ({"player": {"x": 1, "y": 1, "z": 0}, "sol": {"x": 2, "y": 1, "z": 0}}, None)
        c.gps_state = lambda: {}
        c._pre_intents = lambda h, s, m: []                       # the word lists find nothing
        c._receipt = lambda: "تكرم."
        c._player_takes_over = lambda a: None
        c._remember_action = lambda a, o: None
        c._memory_text = lambda s, m: "لا شيء."
        c._gate_context = lambda h, a, k, n=(): RG.Context(h[-1]["text"], [], [], k, False, (), [])
        c._model_first = lambda: True
        c._station_list = lambda: []
        c._street_now = lambda: ""
        c._gardens = lambda: []
        return c
    out = []
    for text, mode in json.loads(sys.stdin.read()):
        del GAME[:], LOG[:], WAIT[:]
        MODE["m"] = mode
        try: reply = chat()._ask_provider([{"role": "user", "text": text}])
        except Exception as e: reply = "EXC %r" % (e,)
        out.append({"text": text, "reply": reply, "game": GAME[:], "wait": WAIT[:], "log": LOG[:]})
    print(json.dumps(out, ensure_ascii=False))


if len(sys.argv) > 1 and sys.argv[1] == "--child":
    child(sys.argv[2], sys.argv[3]); sys.exit(0)

FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)[:600]) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
tmp = tempfile.mkdtemp(prefix="s157_"); mind = os.path.join(tmp, "mind"); lua = os.path.join(tmp, "Lua"); os.makedirs(lua)
shutil.copytree(MIND, mind, ignore=shutil.ignore_patterns("*.log", "__pycache__", "*.json"))
sw = os.path.join(lua, "SolFixes_LAB.txt"); open(sw, "w", newline="").write("x=on\r\n")
ap = os.path.join(HERE, "apply_s157_phone_patience.py")
r1 = subprocess.run([sys.executable, ap, mind, sw], capture_output=True, text=True)
snap = {f: open(os.path.join(mind, f), "rb").read() for f in ("chat_service.py", "model_router.py")}
r2 = subprocess.run([sys.executable, ap, mind, sw], capture_output=True, text=True)
ck("installer runs", r1.returncode == 0, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout and snap == {f: open(os.path.join(mind, f), "rb").read() for f in snap}, r2.stdout)
ck("switch enabled once", open(sw).read().count("phone_patience=on") == 1)


def run(cases):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--child", mind, lua], input=json.dumps(cases), capture_output=True, text=True, encoding="utf-8", env=env)
    if r.returncode != 0: print(r.stderr[-1500:]); return None
    return json.loads(r.stdout.strip().splitlines()[-1])


DOWN = [("شربي مي", "sol_drink"), ("شربي", "sol_drink"), ("غسلي حالك", "sol_wash"), ("افتحي الباب", "sol_open_door"), ("سول افتحي الباب", "sol_open_door"),
        ("سكري الباب", "sol_close_door"), ("افتحي الشباك", "sol_open_window"), ("سول زمري بالسيارة", "sol_horn"), ("فيكي تجيبي هليكوبتر", "sol_summon_helicopter"),
        ("فيكي تجيبي مروحية", "sol_summon_helicopter")]
got = run([[t, "timeout"] for t, _ in DOWN])
ck("child runs", got is not None)
if got:
    bad = [(g["text"], g["game"], g["reply"]) for g, (_, want) in zip(got, DOWN) if not any(a[0] == want for a in g["game"])]
    ck("model down: his exact orders still run (%d lines of 2026-11-15)" % len(DOWN), not bad, bad)
    ck("the phone model is given 12 seconds, not 4", all(w == 12 for g in got for w in g["wait"]) and any(g["wait"] for g in got), [g["wait"] for g in got])
    ck("the helicopter order without her name does not wait for the model", got[-1]["wait"] == [] and got[-2]["wait"] == [])
TALK = ["الو", "قدمي", "فيكي ولا لا", "وين الباب", "لا تفتحي الباب", "بدي اشرب مي", "كيفك اليوم"]
got = run([[t, "timeout"] for t in TALK])
if got:
    bad = [(g["text"], g["game"]) for g in got if g["game"]]
    ck("model down: talk, questions and negations run nothing", not bad, bad)
    ck("... and he is told she did not understand, at once", all("ما قدرت افهم" in str(g["reply"]) for g in got), [g["reply"] for g in got])
got = run([["اشربي مي", '{"action":"sol_drink","speech":""}'], ["كيفك", '{"action":"none","speech":"منيحة"}']])
if got:
    ck("model up: its answer is used as before", got[0]["game"] and got[0]["game"][0][0] == "sol_drink" and got[1]["game"] == [] and "منيحة" in str(got[1]["reply"]), got)
# switch off: as before
open(sw, "w", newline="").write("phone_patience=off\r\n")
got = run([["شربي مي", "timeout"], ["فيكي تجيبي هليكوبتر", "timeout"]])
if got:
    ck("switch off: 4 seconds, no bank answer, the helicopter needs her name", got[0]["wait"] == [4] and got[0]["game"] == [] and got[1]["game"] == [] and got[1]["wait"] == [4], got)
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)
