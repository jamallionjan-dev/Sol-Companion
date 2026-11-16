"""s88: apply_s88_lua.py + apply_s88_mind.py on temporary copies (twice: idempotent), then
  Lua (lupa, Lua 5.1, stub game objects): every changed file compiles; SolFailNote.note / bridge / keyLine / orderEnd / the
      solPickCar wrap; SolLF_AR_Orders adds UI_SC_State_base_duty and move_to* in SolLF_AR's own format; tonumber_check clean.
  Mind (a child process on the patched copy, LOCALAPPDATA in a temp dir): "ليش" picks the newest real failure and words it
      without codes, the switch off keeps the old answer; the conversation comes back to the game after a reconnect without a
      new message; a message before the world is known is kept; the card's memory is rebuilt when what she remembers changes.
  card_check.py on the patched copy (PASS, within budget).
Nothing live is touched.
Run: set PYTHONIOENCODING=utf-8 & python test_s88.py [sol_mind dir] [client dir]   (defaults: 05_TOOLS/sol_mind, the lab client; read only)
Offline PASS is not Runtime PASS."""
import json, os, re, shutil, subprocess, sys, tempfile, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LIVE_MIND = os.path.join(ROOT, "05_TOOLS", "sol_mind")
LIVE_CLIENT = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
KAHLUA = os.path.join(ROOT, "05_TOOLS", "sol_kahlua")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)


# ================================================================ child: the patched Mind
def mind_child(mind, lua):
    sys.path.insert(0, mind)
    import chat_service as CS, world_knowledge as W
    ck("child: the patched copy is what got imported", os.path.dirname(os.path.abspath(CS.__file__)) == os.path.abspath(mind))
    ck("child: memory root is the temp dir", os.path.abspath(W._root()).startswith(os.path.abspath(os.environ["LOCALAPPDATA"])), W._root())
    LOG = []
    def fixes(on):
        with open(os.path.join(lua, "SolFixes_LAB.txt"), "w", encoding="utf-8") as f: f.write("fail_reasons=%s\n" % ("on" if on else "off"))
    def chat():
        c = CS.Chat.__new__(CS.Chat)
        c.dir, c.log, c.ack, c.status, c.code = lua, LOG.append, 0, "idle", ""
        c.hist, c._hist_file, c.lock, c.pending_card = [], None, threading.Lock(), None
        c._sheet = None
        return c
    code = re.compile(r"[a-z]+_[a-z_]+")

    # --- wording: her sentence, never the code
    for r in ("no_path", "door_unreachable", "board_timeout", "bridge_failure", "drive_cancelled:no_way_round", "deferred:busy", "x_no_key",
              "preempted", "no_usable_car", "something_new_here", "leg_stalled"):
        line = CS.why_line(r)
        ck("why_line %s -> Arabic, no code (%s)" % (r, line), re.search(r"[؀-ۿ]", line) and not code.search(line), line)
    ck("why_line: an Arabic reason from the game is kept", CS.why_line("ما في بنزين.") == "ما في بنزين.")
    ck("why_line: a reason only REASON_AR knows", CS.why_line("battery_dead") == CS.REASON_AR["battery_dead"])

    # --- run_action keeps the last refused order, never a status question
    CS._run_action_s88_base = lambda d, a, o=None, w=3.0: {"ok": False, "reason": "no_vehicle_near"}
    CS._LAST_FAIL_S88.clear()
    CS.run_action(lua, "sol_far", "status")
    ck("run_action: a refused status question is not a failure", not CS._LAST_FAIL_S88, CS._LAST_FAIL_S88)
    CS.run_action(lua, "board_vehicle", None)
    ck("run_action: a refused order is kept with its time", CS._LAST_FAIL_S88.get("reason") == "no_vehicle_near" and CS._LAST_FAIL_S88.get("source") == "action:board_vehicle", CS._LAST_FAIL_S88)

    # --- "ليش": the newest real failure
    fixes(True)
    c = chat(); c.gps_state = lambda: {}
    CS._LAST_FAIL_S88.clear()
    note = os.path.join(lua, CS.FAIL_FILE_S88)
    with open(note, "w", encoding="ascii") as f: f.write("seq=3\nt=1\nsource=order\nreason=door_unreachable\ndetail=kind=ride secs=41 tries=3\n")
    r = c._why_answer({})
    ck("why: the game's note -> door line", r == CS.WHY_AR_S88["door_unreachable"], r)
    ck("why: one log line with source, reason, detail", any("why -> source=game:order reason=door_unreachable detail=kind=ride" in l for l in LOG), LOG[-2:])
    CS._LAST_FAIL_S88.update(t=time.time() + 5, source="action:board_vehicle", reason="no_vehicle_near", detail="")
    r = c._why_answer({})
    ck("why: a newer refused order wins", r == CS.WHY_AR_S88["no_vehicle_near"], r)
    CS._LAST_FAIL_S88.clear()
    gps = os.path.join(lua, CS.GPS_STATE)
    with open(gps, "w", encoding="ascii") as f: f.write("result=failed\nreason=bridge_failure\n")
    os.utime(gps, (time.time() + 10, time.time() + 10))
    c.gps_state = lambda: {"result": "failed", "reason": "bridge_failure"}
    r = c._why_answer({})
    ck("why: a newer failed drive wins, worded", r == CS.WHY_AR_S88["bridge_failure"], r)
    old = time.time() - 20 * 60
    os.utime(gps, (old, old)); os.utime(note, (old, old))
    r = c._why_answer({"solFarm": {"stop": {"reason": "done", "detail": {"kind": "water"}}}})
    ck("why: nothing in the last 15 min -> the farm's stop line (as before)", r and "خلصت" in r, r)
    r = c._why_answer({})
    ck("why: nothing at all -> 'ما صار شي غلط هلأ.'", r == "ما صار شي غلط هلأ.", r)
    fixes(False)
    os.utime(note, None)
    c.gps_state = lambda: {}
    r = c._why_answer({})
    ck("why: switch off -> the old answer (the note is not read)", r == "ما صار شي غلط هلأ.", r)
    fixes(True)

    # --- reconnect: the conversation back in the game without a new message
    world = {"name": "TestWorld", "mode": "Sandbox"}
    with open(os.path.join(lua, W.SNAP), "w", encoding="ascii") as f: json.dump({"world": world, "sol": {"x": 1, "y": 1}}, f)
    mem = W.Memory(world)
    with open(os.path.join(mem.dir, "chat_history.json"), "w", encoding="utf-8") as f:
        json.dump([{"role": "user", "text": "وين البيت", "t": 1}, {"role": "sol", "text": "هون", "t": 2}, {"role": "user", "text": "تمام", "t": 3}], f, ensure_ascii=False)
    def state():
        with open(os.path.join(lua, CS.STATE), encoding="ascii") as f: return dict(l.split("=", 1) for l in f.read().splitlines() if "=" in l)
    c = chat(); c.publish()
    ck("reconnect: a fresh Mind publishes an empty chat at start", state().get("count") == "0", state().get("count"))
    CS._poll_once_s87 = lambda self: False
    c.poll_once()
    ck("reconnect: the first poll binds the world and publishes its 3 messages", state().get("count") == "3" and len(c.hist) == 3, (state().get("count"), len(c.hist)))
    ck("reconnect: logged", any("conversation of this world back in the game, 3 messages" in l for l in LOG), LOG[-1:])
    n = len(LOG); c.poll_once()
    ck("reconnect: published once, not every poll", not any("back in the game" in l for l in LOG[n:]))

    # --- a message before the world is known
    hist = os.path.join(mem.dir, "chat_history.json")
    def handle_with(fn):
        with open(hist, "w", encoding="utf-8") as f: json.dump([{"role": "sol", "text": "أهلين", "t": 1}], f, ensure_ascii=False)
        c2 = chat(); c2.publish = lambda: None
        c2.ask = lambda h: (c2._world(), "تكرم.")[1]                            # the real ask reads the world first
        fn(c2, "تعالي")
        with open(hist, encoding="utf-8") as f: return [m["text"] for m in json.load(f)]
    before = handle_with(CS._handle_s87)
    ck("before s88 (evidence): his line was lost when the world bound mid-message", before == ["أهلين", "تكرم."], before)
    after = handle_with(lambda c2, t: c2.handle(t))
    ck("s88: his line is kept in the world's history", after == ["أهلين", "تعالي", "تكرم."], after)

    # --- the card's memory follows what she remembers
    built = []
    def fake_sheet(self, snap, m, acts):
        if self._sheet is None: built.append(1); self._sheet = {"text": "sheet%d" % len(built)}
        return self._sheet["text"]
    CS._session_sheet_s87 = fake_sheet
    c = chat()
    c._session_sheet(None, None, [])
    c._session_sheet(None, None, [])
    ck("card: same memory -> built once", len(built) == 1, built)
    c._session_sheet({"sol": {}}, mem, [])
    ck("card: the world came back -> rebuilt", len(built) == 2, built)
    mem.data["home"] = {"x": 5, "y": 5}
    c._session_sheet({"sol": {}}, mem, [])
    ck("card: home set -> rebuilt", len(built) == 3, built)
    c._session_sheet({"sol": {}, "vehicles": [1, 2]}, mem, [])
    ck("card: only the cars around changed -> kept (no rebuild per tick)", len(built) == 3, built)
    print("CHILD_DONE fails=%d" % len(FAIL))
    sys.exit(1 if FAIL else 0)


# ================================================================ Lua with lupa
def lua_part(client_src):
    tmp = tempfile.mkdtemp(prefix="sol_s88_lua_")
    prof = os.path.join(tmp, "Zomboid")
    cl = os.path.join(prof, "mods", "Sol_LAB", "42", "media", "lua", "client")
    os.makedirs(cl); os.makedirs(os.path.join(prof, "Lua"))
    for n in ("SolAuthority.lua", "SolOrders.lua", "SolLF_AR.lua", "SCDriving.lua", "SolCarRules.lua"):
        shutil.copy(os.path.join(client_src, n), cl)
    open(os.path.join(prof, "Lua", "SolFixes_LAB.txt"), "w").write("model_first=on\r\n")
    import apply_s88_lua as A
    for i in (1, 2):
        out = subprocess.run([sys.executable, os.path.join(HERE, "apply_s88_lua.py"), cl], capture_output=True, text=True)
        ck("lua installer run %d exit 0" % i, out.returncode == 0, out.stderr[-400:])
        if i == 2: ck("lua installer is idempotent (second run keeps everything)", "edited" not in out.stdout and "written" not in out.stdout and "=on" not in out.stdout, out.stdout)
    fx = open(os.path.join(prof, "Lua", "SolFixes_LAB.txt")).read()
    ck("SolFixes_LAB: fail_reasons=on once", fx.count("fail_reasons=on") == 1, fx)
    auth = open(os.path.join(cl, "SolAuthority.lua")).read()
    ck("SolAuthority: fail_reasons in A.FIXES once", auth.count('"fail_reasons"') == 1)
    for name, marks in (("SCDriving.lua", ("bridge start", "bridge status", "bridge follow", "no key")), ("SolOrders.lua", ("failText", "endFail", "busyText"))):
        t = open(os.path.join(cl, name)).read()
        for m in marks: ck("%s: %s once" % (name, m), t.count(A.MARKERS[m]) == 1, t.count(A.MARKERS[m]))
    from lupa import lua51
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    for n in ("SolFailNote.lua", "SolLF_AR_Orders.lua", "SCDriving.lua", "SolOrders.lua", "SolAuthority.lua"):
        src = open(os.path.join(cl, n), encoding="ascii").read()
        f, err = L.eval("function(s, n) local f, e = loadstring(s, n); return f ~= nil, tostring(e) end")(src, n)
        ck("compiles: " + n, f is True, err)
    tc = subprocess.run([sys.executable, os.path.join(KAHLUA, "tonumber_check.py"), cl], capture_output=True, text=True)
    ck("tonumber_check clean on the patched client", tc.returncode == 0, (tc.stdout + tc.stderr)[-500:])

    # --- SolFailNote with stubs
    L.execute(r'''
        OUT, FILES, NOW = {}, {}, 100000
        print = function(s) OUT[#OUT + 1] = tostring(s) end
        getTimestampMs = function() return NOW end
        getFileWriter = function(name, a, b) local w = { buf = "" }
            function w:write(s) self.buf = self.buf .. s end
            function w:close() FILES[name] = self.buf end
            return w end
        local function list(t) return { size = function(self) return #t end, get = function(self, i) return t[i + 1] end } end
        function container(items) return { getItems = function(self) return list(items) end } end
        function item(id, ty, inner) return { getKeyId = function(self) return id end, getType = function(self) return ty end,
            getInventory = inner and function(self) return inner end or nil } end
        PICKED = {}
        SolUI = { solActor = function() return HER end,
                  solPickCar = function(vehicles, anchor, radius) PICKED[#PICKED + 1] = #vehicles; return nil, true end }
        HIM = { getInventory = function(self) return container({ item(-1, "Apple"), item(9, "CarKey") }) end }
        getSpecificPlayer = function(i) return HIM end
    ''')
    L.execute(open(os.path.join(cl, "SolFailNote.lua"), encoding="ascii").read())
    g = L.globals()
    FN = g.SolFailNote
    ck("SolFailNote loads, version 0.1.0", FN is not None and FN.VERSION == "0.1.0")
    FN.note("order_board", "door_locked\nx", "kind=ride")
    out = list(g.OUT.values())
    ck("note: one [SolFail] log line, newline cleaned", out[-1] == "[SolFail] source=order_board reason=door_locked x detail=kind=ride", out[-1])
    st = g.FILES[FN.FILE]
    ck("note: SolFail_State.txt has seq, source, reason, detail", "seq=1\n" in st and "source=order_board\n" in st and "reason=door_locked x\n" in st and "detail=kind=ride\n" in st, st)
    job = L.eval("{}")
    route = L.eval("{ points = { {x=1,y=1,width=6}, {x=1.2,y=1,width=6} } }")
    d = FN.bridge("follow", "route must be 2 to 512 points of x,y,width inside the map", job, route)
    ck("bridge: the cause and the route's numbers in job.detail", job.detail == d and d.startswith("follow: route must be") and "points=2" in d, d)
    out = list(g.OUT.values())
    ck("bridge: '[SolDrive] bridge_failure at=follow cause=...' logged", any(o.startswith("[SolDrive] bridge_failure at=follow cause=follow: route must") for o in out), out[-3:])
    ck("bridge: also a [SolFail] note (reason bridge_failure)", "reason=bridge_failure\n" in g.FILES[FN.FILE])
    FN.bridge("start", "vehicle has no controller", job)
    ck("bridge: start site", job.detail == "start: vehicle has no controller", job.detail)
    L.execute(r'''
        local ring = container({ item(5, "CarKey"), item(77, "Key1") })
        HER = { getInventory = function(self) return container({ item(-1, "Bag"), item(-1, "KeyRing", ring) }) end }
        local glove = container({ item(31, "CarKey") })
        function car(id) return { getKeyId = function(self) return id end, getPartCount = function(self) return 2 end,
            getPartByIndex = function(self, i) if i == 0 then return { getItemContainer = function(self) return glove end } end return {} end,
            getScript = function(self) return { getName = function(self) return "Base.CarNormal" end } end,
            isKeysInIgnition = function(self) return false end, isHotwired = function(self) return false end,
            getX = function(self) return 10 end, getY = function(self) return 10 end } end
    ''')
    line = FN.keyLine("drive_start", g.HER, g.car(5))
    ck("keyLine: her key in a key ring found, match=hers", line and "car_key=5" in line and "hers=[5:CarKey,77:Key1]" in line and "match=hers" in line, line)
    ck("keyLine: his keys and the glove box listed", "his=[9:CarKey]" in line and "in_car=[31:CarKey]" in line and "car=Base.CarNormal" in line, line)
    ck("keyLine: same car and place again within 5 s -> not logged twice", FN.keyLine("drive_start", g.HER, g.car(5)) is None)
    line = FN.keyLine("drive_start", g.HER, g.car(31))
    ck("keyLine: key only in the car -> match=in_car", line and "match=in_car" in line, line)
    line = FN.keyLine("drive_start", g.HER, g.car(404))
    ck("keyLine: nobody has it -> match=none", line and "car_key=404" in line and "match=none" in line, line)
    # orderEnd
    L.execute(r'''SolOrders = { AR = { no_path = "NP", busy = "BUSY", generic = "GEN", door_unreachable = "DU" } }''')
    g.NOW = 160000
    FN.orderEnd("NP", L.eval("{ kind = 'ride', since = 100000, tries = 4, noProgress = 3 }"))
    st = g.FILES[FN.FILE]
    ck("orderEnd: reason no_path, how long and how often", "reason=no_path\n" in st and "secs=60" in st and "tries=4" in st and "no_progress=3" in st and "kind=ride" in st, st)
    FN.orderEnd("BUSY (preempted)", None)
    ck("orderEnd: busy with the code in brackets -> preempted", "reason=preempted\n" in g.FILES[FN.FILE], g.FILES[FN.FILE])
    FN.orderEnd("BUSY", None)
    ck("orderEnd: plain busy -> busy", "reason=busy\n" in g.FILES[FN.FILE])
    FN.note("order_board", "passenger door is locked", "")
    FN.orderEnd("GEN", None)
    ck("orderEnd: endFail(failText(why)) keeps failText's code, not 'generic'", "reason=passenger door is locked\n" in g.FILES[FN.FILE], g.FILES[FN.FILE])
    # solPickCar wrap
    g.NOW = 900000
    n0 = len(list(g.OUT.values()))
    best, none = g.SolUI.solPickCar(L.eval("{ car(5), car(404) }"), g.car(1), 20)
    out = list(g.OUT.values())[n0:]
    ck("pick_car: the original still answers (nil, true)", best is None and none is True)
    ck("pick_car: a [SolKeys] line per near car and one [SolFail] no_usable_car", sum(o.startswith("[SolKeys] pick_car") for o in out) == 2 and any("reason=no_usable_car" in o for o in out), out)
    L.execute(open(os.path.join(cl, "SolFailNote.lua"), encoding="ascii").read())
    g.SolUI.solPickCar(L.eval("{}"), g.car(1), 20)
    ck("pick_car: wrapped once even when the file runs twice", g.PICKED[len(g.PICKED)] == 0 and g.SolUI._s88PickWrapped)
    # A9
    L.execute(r'''package.preload["SolLF_AR"] = function() SolLF_AR = SolLF_AR or { ["UI_SC_State_follow"] = "x" } end''')
    L.execute(open(os.path.join(cl, "SolLF_AR_Orders.lua"), encoding="ascii").read())
    ar = g.SolLF_AR
    def dec(s): return re.sub(r"\\u([0-9A-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
    ck("A9: base_duty in Arabic", ar["UI_SC_State_base_duty"] and dec(ar["UI_SC_State_base_duty"]) == "مناوبة بالقاعدة", ar["UI_SC_State_base_duty"])
    ck("A9: move_to in Arabic", dec(ar["UI_SC_State_move_to"]) == "انتقال")
    ck("A9: move_to_seat in Arabic", dec(ar["UI_SC_State_move_to_seat"]) == "ذهاب إلى مقعد")
    ck("A9: an existing key is never overwritten", ar["UI_SC_State_follow"] == "x")
    real = open(os.path.join(cl, "SolLF_AR.lua"), encoding="ascii").read()
    sample = re.search(r'\["UI_SC_State_follow"\] = "([^"]+)"', real).group(1)
    mine = re.search(r'\["UI_SC_State_move_to"\] = "([^"]+)"', open(os.path.join(cl, "SolLF_AR_Orders.lua"), encoding="ascii").read()).group(1)
    ck("A9: same escape format as SolLF_AR (\\\\uXXXX in the source)", sample.startswith("\\\\u") and mine.startswith("\\\\u"), (sample[:12], mine[:12]))
    # A9: Living Fellows' own stateText with the Arabic table -> no English id left
    fmt = open(os.path.join(client_src, "SCUIFormat.lua"), encoding="utf-8").read()
    L.execute(fmt)
    txt = L.eval("function(k) local v = SolLF_AR[k]; return v or k end")
    for v in ("base_duty", "move_to", "move_to_base_storage"):
        shown = g.SurvivorCompanion.UIFormat.stateText(v, txt)
        ck("A9: stateText(%s) shows Arabic, not '%s'" % (v, g.SurvivorCompanion.UIFormat.humanize(v)), shown.startswith("\\u"), shown)
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    mind_src = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else LIVE_MIND
    client_src = sys.argv[2] if len(sys.argv) > 2 else LIVE_CLIENT
    if "--child" in sys.argv:
        i = sys.argv.index("--child"); mind_child(sys.argv[i + 1], sys.argv[i + 2]); return
    lua_part(client_src)
    tmp = tempfile.mkdtemp(prefix="sol_s88_mind_")
    mind = os.path.join(tmp, "sol_mind")
    shutil.copytree(mind_src, mind, ignore=shutil.ignore_patterns("__pycache__", "*.log", "logs"))
    for i in (1, 2):
        out = subprocess.run([sys.executable, os.path.join(HERE, "apply_s88_mind.py"), mind], capture_output=True, text=True, encoding="utf-8")
        ck("mind installer run %d exit 0" % i, out.returncode == 0, out.stderr[-400:])
        if i == 2: ck("mind installer is idempotent", "kept" in out.stdout and "appended" not in out.stdout, out.stdout)
    lua = os.path.join(tmp, "Lua"); os.makedirs(lua)
    env = dict(os.environ, LOCALAPPDATA=os.path.join(tmp, "appdata"), PYTHONIOENCODING="utf-8")
    os.makedirs(env["LOCALAPPDATA"])
    out = subprocess.run([sys.executable, os.path.abspath(__file__), "--child", mind, lua], capture_output=True, text=True, encoding="utf-8", env=env, cwd=tmp)
    print(out.stdout.rstrip())
    ck("mind child exit 0", out.returncode == 0 and "CHILD_DONE fails=0" in out.stdout, out.stderr[-1500:])
    cc = subprocess.run([sys.executable, os.path.join(KAHLUA, "card_check.py"), mind], capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    tail = "\n".join(cc.stdout.strip().splitlines()[-4:])
    print(tail)
    ck("card_check.py PASS on the patched Mind", cc.returncode == 0, (cc.stdout + cc.stderr)[-800:])
    shutil.rmtree(tmp, ignore_errors=True)
    print("s88: %d failed" % len(FAIL) if FAIL else "s88: ALL PASS")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
