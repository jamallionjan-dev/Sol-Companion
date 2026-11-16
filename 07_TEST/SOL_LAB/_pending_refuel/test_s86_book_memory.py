"""s86 book_memory, offline. Nothing live is touched (digests checked before and after).
  1. apply_s86_book_memory_lua.py on a copy of the lab client (twice: idempotent), switch file, A.FIXES, the one SolWorldScan anchor;
     the Kahlua tonumber gate on SolBookMemory.lua and the patched SolWorldScan.lua.
  2. Lua (lupa): the lab's SolLife + SolText + SolAddressBook + SolAddressPlaces(+Data), the staged SolBookMemory.lua and the patched
     SolWorldScan.lua; a book of every kind; U.writeWorldRaw writes the snapshot JSON; "solBook" read back in Python: our home first,
     sections in the page's order, looted last, distances and 8 directions, no coordinates, at most 40 rows, from him when she is away,
     switch off -> no solBook.
  3. apply_s86_book_memory_mind.py on a copy of the live Mind (twice); in a child process with that copy: her memory line, the answers
     ("شو في عنا عناوين", "وين <name>", the places question with no Mind places), switch off = as before, the card rebuilt when the
     book's names change, the fixed card unchanged.
  4. 05_TOOLS/sol_kahlua/card_check.py on the patched copy (must PASS, the WARN gone) and test_s82_route_eval.py --as-is on it.
Run: set PYTHONIOENCODING=utf-8 & python test_s86_book_memory.py
Offline PASS is not Runtime PASS."""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LAB_CL = os.path.abspath(os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"))
LAB_LUA = os.path.abspath(os.path.join(HERE, "..", "profile", "Zomboid", "Lua"))
LIVE_MIND = os.path.join(ROOT, "05_TOOLS", "sol_mind")
GATE = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "tonumber_check.py")
CARD_CHECK = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "card_check.py")
EVAL = os.path.join(HERE, "test_s82_route_eval.py")
ENVP = dict(os.environ, PYTHONIOENCODING="utf-8")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def read(p): return open(p, encoding="utf-8", newline="").read()
def run(*a): return subprocess.run([sys.executable] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
def digest(d, names=None):
    names = names if names is not None else sorted(n for n in os.listdir(d) if os.path.isfile(os.path.join(d, n)) and not n.endswith(".log"))
    return {n: hashlib.md5(open(os.path.join(d, n), "rb").read()).hexdigest() for n in names if os.path.exists(os.path.join(d, n))}


# ================================================================ child: the patched Mind
def mind_child(mind, snap_path, base_path):
    sys.path.insert(0, mind)
    import chat_service as CS, memory_answers as MA, model_router as MR
    ck("child: the patched copy is what got imported", os.path.dirname(os.path.abspath(MA.__file__)) == os.path.abspath(mind))
    snap = json.load(open(snap_path, encoding="utf-8"))
    base = json.load(open(base_path, encoding="utf-8"))           # the same world with the switch off: no solBook
    ck("snapshot: solBook present, base without it", isinstance(snap.get("solBook"), dict) and "solBook" not in base)

    line = MA.book_line(snap)
    print("      memory line:", line)
    ck("memory line: 'دفتر عناوينك (البعد منك): بيتنا (...)' first", line.startswith("دفتر عناوينك (البعد منك): بيتنا ("), line)
    ck("memory line: at most 8 entries, then 'و<n> غيرهن'", line.count("؛") == 8 and re.search(r"؛ و\d+ غيرهن\.$", line) is not None, line)
    ck("memory line: home's street, a kind and a distance in words", "Jefferson Rd" in line and "مكان سياحي" in line and "كم بالغرب" in line, line)
    ck("memory line: no coordinate of the world in it", not any(str(v) in line for v in (10800, 10100, 10805, 7800, 8000, 13805)), line)
    ck("memory line: compact (<= 700 chars)", len(line) <= 700, len(line))
    ck("memory line: None without solBook (switch off)", MA.book_line(base) is None)

    A = lambda t, s=snap, mem=None: MA.answer(t, s, mem)
    r = A("شو في عنا عناوين")
    ck("'شو في عنا عناوين' -> the book, بيتنا first", r is not None and r.startswith("بالدفتر عندي ") and "بيتنا" in r.split(":", 1)[1][:8] and r.endswith("وغيرهن."), r)
    r = A("شو بالدفتر عندك؟")
    ck("'شو بالدفتر عندك؟' -> the book", r is not None and r.startswith("بالدفتر عندي "), r)
    r = A("وين Coalfield")
    ck("'وين Coalfield' -> name, kind, distance and direction from her", r == "Coalfield (مكان سياحي) حوالي 3 كم بالغرب منّي.", r)
    r = A("وين كولفيلد؟")
    ck("'وين كولفيلد؟' (Arabic spelling) -> Coalfield", r is not None and r.startswith("Coalfield ("), r)
    r = A("وين Dewey Street")
    ck("'وين Dewey Street' -> the house of the listing", r is not None and r.startswith("625 Dewey Street, Muldraugh (بيت للبيع)") and "بالشرق" in r, r)
    r = A("وين E.P. Tools")
    ck("'وين E.P. Tools' -> the shop, looted said", r is not None and r.startswith("E.P. Tools (Louisville)") and r.endswith("، وانزار."), r)
    r = A("وين Louisville")
    ck("'وين Louisville': several rows -> she asks which", r is not None and r.startswith("عندي بالدفتر أكتر من وحدة:"), r)
    ck("'وين المعرض' (no book name): not the book's answer (the old path / the model)", A("وين المعرض") == MA._answer_s85("وين المعرض", snap, None), A("وين المعرض"))
    ck("'وين بيتنا': the home question as before", A("وين بيتنا") == MA._answer_s85("وين بيتنا", snap, None))
    ck("'وين السيارة': the car question as before", A("وين السيارة") == MA._answer_s85("وين السيارة", snap, None))
    r = A("شو الأماكن اللي حفظتيها")
    ck("places question with no Mind places -> the book, not 'لسا ما حفظت ولا مكان'", r is not None and r.startswith("بالدفتر عندي "), r)
    for q in ("شو في عنا عناوين", "وين Coalfield", "شو الأماكن اللي حفظتيها", "وين المعرض", "شو اسم هالشارع"):
        ck("no solBook: '%s' as before" % q, MA.answer(q, base, None) == MA._answer_s85(q, base, None))
    MA.BOOK_ENABLED[0] = False
    ck("switch off (BOOK_ENABLED False): 'وين Coalfield' as before", A("وين Coalfield") == MA._answer_s85("وين Coalfield", snap, None))
    MA.BOOK_ENABLED[0] = True
    empty = dict(snap, solBook={"n": 0, "from": "sol", "rows": []})
    ck("empty book: 'شو في عنا عناوين' -> 'دفتري فاضي...'", A("شو في عنا عناوين", empty) == MA.BOOK_EMPTY and MA.book_line(empty) == "دفتر عناوينك فاضي.")
    away = json.loads(json.dumps(snap)); away["solBook"]["from"] = "player"
    ck("she is away: 'منك' (from him)", A("وين Coalfield", away).endswith("منك.") and "(البعد منه)" in MA.book_line(away))
    names = [n for n, _ in MA.known_names(snap, None)]
    ck("the book's names are known names for the reply gate", "Coalfield" in names and "625 Dewey Street, Muldraugh" in names, names[:12])
    ck("facts carry the book line", "دفتر عناوينك" in MA.facts(snap, None))

    # the chat: memory text and the card
    T = tempfile.mkdtemp(prefix="sol_s86_child_")
    fx = os.path.join(T, "SolFixes_LAB.txt")
    LOG = []
    c = CS.Chat.__new__(CS.Chat)
    c.dir, c.log, c._sheet = T, LOG.append, None
    open(fx, "w", encoding="utf-8").write("model_first=on\r\nbook_memory=on\r\n")
    mt = c._memory_text(snap, None)
    ck("Chat._memory_text: the book line at the end", mt.endswith(line), mt[-200:])
    open(fx, "w", encoding="utf-8").write("model_first=on\r\nbook_memory=off\r\n")
    ck("Chat._memory_text: switch off -> no book line", "دفتر عناوينك" not in c._memory_text(snap, None))
    open(fx, "w", encoding="utf-8").write("model_first=on\r\n")
    ck("Chat._memory_text: switch missing -> no book line", "دفتر عناوينك" not in c._memory_text(snap, None))
    open(fx, "w", encoding="utf-8").write("model_first=on\r\nbook_memory=on\r\n")
    acts = []
    s1 = c._session_sheet(snap, None, acts)
    ck("card: the memory section holds the book line", s1.split("ذاكرتك الآن:", 1)[1].strip().endswith(line))
    ck("card: the fixed part is the card without memory (CARD_BUDGET counts it as before)", s1.rsplit("\n\nذاكرتك الآن:", 1)[0] == MR.sheet(acts, "").rsplit("\n\nذاكرتك الآن:", 1)[0])
    moved = json.loads(json.dumps(snap)); [r.__setitem__("d", (r.get("d") or 0) + 400) for r in moved["solBook"]["rows"]]
    ck("card: distances alone changed -> the cached card stays", c._session_sheet(moved, None, acts) is s1)
    grown = json.loads(json.dumps(snap)); grown["solBook"]["rows"].insert(1, {"g": "house", "n": "1 New Road, Ekron", "c": "Ekron", "d": 50, "dir": 3}); grown["solBook"]["n"] += 1
    s2 = c._session_sheet(grown, None, acts)
    ck("card: a new place in the book -> the card is rebuilt with it", s2 is not s1 and "1 New Road, Ekron" in s2)
    ck("chat source: _memory_text names the address book (card_check's feature check)", re.search(r"address|sol_address|عناوين", __import__("inspect").getsource(CS.Chat._memory_text)) is not None)
    print("CHILD", "ALL PASS" if not FAIL else "FAILED")
    sys.exit(1 if FAIL else 0)


if len(sys.argv) > 1 and sys.argv[1] == "--mind-child":
    mind_child(sys.argv[2], sys.argv[3], sys.argv[4])

from kahlua_env import lua51
live_cl = digest(LAB_CL, ["SolAuthority.lua", "SolAddressBook.lua", "SolWorldScan.lua", "SolBookMemory.lua"])
live_fix = read(os.path.join(LAB_LUA, "SolFixes_LAB.txt"))
live_mind = digest(LIVE_MIND)

# ================================================================ 1. the Lua installer on copies
T = tempfile.mkdtemp(prefix="sol_s86_")
zb = os.path.join(T, "Zomboid"); CL = os.path.join(zb, "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(CL); os.makedirs(os.path.join(zb, "Lua"))
for f in ("SolAuthority.lua", "SolAddressBook.lua", "SolWorldScan.lua"): shutil.copy(os.path.join(LAB_CL, f), CL)
FX = os.path.join(zb, "Lua", "SolFixes_LAB.txt")
open(FX, "w", encoding="utf-8", newline="").write("address_book=on\r\nmodel_first=on")
LUA_APPLY = os.path.join(HERE, "apply_s86_book_memory_lua.py")
r1 = run(LUA_APPLY, CL)
ck("Lua installer applies", r1.returncode == 0 and "s86 book_memory (Lua) applied" in r1.stdout, (r1.stdout[-300:], r1.stderr[-300:]))
d1 = digest(CL)
r2 = run(LUA_APPLY, CL)
ck("Lua installer idempotent", r2.returncode == 0 and digest(CL) == d1 and r2.stdout.count("kept") >= 4, r2.stdout)
ck("SolBookMemory.lua is ASCII", all(ord(ch) < 128 for ch in read(os.path.join(HERE, "SolBookMemory.lua"))))
ws = read(os.path.join(CL, "SolWorldScan.lua"))
ck("SolWorldScan: one guarded block, right before the coverage line", ws.count("snap.solBook = bm") == 1 and re.search(r"if okBM then snap\.solBook = bm end\r?\n    end\r?\n    snap\.coverage = \{", ws) is not None)
ck("SolWorldScan: nothing else changed", re.sub(r"    if type\(SolBookMemory\)[^\n]*\n[^\n]*\n[^\n]*\n    end\r?\n", "", ws, count=1) == read(os.path.join(LAB_CL, "SolWorldScan.lua")))
auth = read(os.path.join(CL, "SolAuthority.lua"))
ck("A.FIXES: book_memory once", auth.count('"book_memory"') == 1)
fx = read(FX)
ck("switch file: book_memory=on once, own line", fx.count("book_memory=on") == 1 and fx.endswith("\r\n") and "model_first=on\r\n" in fx, repr(fx))
for f in (os.path.join(HERE, "SolBookMemory.lua"), os.path.join(CL, "SolWorldScan.lua")):
    g = run(GATE, f); ck("tonumber gate: " + os.path.basename(f), g.returncode == 0, g.stdout[-300:])

# ================================================================ 2. the game side under lupa
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(r"""
NOW = 0
SW = { address_book = true, address_places = true, book_memory = true, sol_home = true }
function getTimestampMs() return NOW end
SolAuthority = { on = function(n) return SW[n] == true end }
MD = {}
ModData = { getOrCreate = function(k) MD[k] = MD[k] or {}; return MD[k] end, transmit = function() end }
Events = { OnGameStart = { Add = function() end }, OnTick = { Add = function() end } }
function require() end
SolBudget = { register = function() end }
LOGS = {}
function print(s) LOGS[#LOGS + 1] = tostring(s) end
local function body(t)
  function t:getX() return self.x end function t:getY() return self.y end function t:getZ() return self.z or 0 end
  function t:getVehicle() return self.vehicle end function t:isDead() return self.dead == true end function t:isAsleep() return self.asleep == true end
  return t end
PLAYER = body({ x = 10800, y = 10100, z = 0 })
SOL = body({ x = 10805, y = 10100, z = 0, id = "sc-1" })
SOL_HERE, FAR = true, nil
function getSpecificPlayer() return PLAYER end
SolUI = { solActor = function() if SOL_HERE then return SOL end return nil end, lang = function() return "ar" end,
          solFarState = function() return FAR end }
SurvivorCompanion = { GameplayUtil = { idOf = function(a) return a.id end, say = function() return true end } }
ROADNAME = "Jefferson Rd"
function SolUI.gpsNearestRoad(x, y) return x, y, 4, ROADNAME end
function getTextOrNull(k) return nil end
function getText(k) return k end
HOME = nil
SolHome = { get = function() return HOME end }
WROTE = nil
function getFileWriter(name, a, b) return { write = function(self, t) WROTE = t end, close = function() end } end
""")
for f in ("SolText.lua", "SolLife.lua"): L.execute(read(os.path.join(LAB_CL, f)))
L.execute(read(os.path.join(CL, "SolAddressBook.lua")))
for f in ("SolAddressPlacesData.lua", "SolAddressPlaces.lua"): L.execute(read(os.path.join(LAB_CL, f)))
L.execute(read(os.path.join(CL, "SolBookMemory.lua")))
L.execute(read(os.path.join(CL, "SolWorldScan.lua")))
L.execute("SolLife.checkIdentity()")
ck("Lua: modules loaded, her life known", L.eval("type(SolBookMemory.snapshot) == 'function' and type(SolUI.writeWorldRaw) == 'function' and SolAddressBook.lifeKey() ~= nil"))
L.execute(r"""
function put(e, cat, looted)
  local ok, how, n = SolAddressBook.record(e)
  if ok and how == "new" then n.cat = cat; n.looted = looted == true; n.street = e.street end
  return ok
end
local sx, sy = SOL.x, SOL.y
put({ kind = "house", x = sx + 1200, y = sy - 30, name = "625 Dewey Street, Muldraugh", city = "Muldraugh", num = "903", src = "houseforsale903" })
put({ kind = "house", x = sx + 40, y = sy + 600, name = "Ducase Apartments", city = "Louisville", src = "ducaseapartments", lease = true })
put({ kind = "place", x = sx - 3000, y = sy, name = "Coalfield", src = "coalfield" }, "tourist")
put({ kind = "place", x = sx + 9000, y = sy - 9000, name = "Art Gallery of Louisville", city = "Louisville", src = "artgalleryoflouisville" }, "tourist")
put({ kind = "place", x = sx + 5, y = sy + 900, name = "E.P. Tools (Louisville)", city = "Louisville", src = "eptoolslv" }, "shop", true)
put({ kind = "place", x = sx + 7, y = sy + 950, name = "Taco del Pancho", city = "Louisville", src = "tacodelpancho" }, "shop")
put({ kind = "place", x = sx - 50, y = sy - 4000, name = "Ekron Community College", city = "Ekron", src = "ekroncollege" }, "public")
put({ kind = "stash", x = sx + 300, y = sy + 300, name = "Map", sub = "Main Street", src = "stash1" })
put({ kind = "area", x = sx + 2000, y = sy - 2000, name = "Louisville Central", src = "LouisvilleMap1" })
put({ kind = "place", x = sx + 100, y = sy, name = "\\u0645\\u062D\\u0644 \\u0627\\u0644\\u062D\\u064A", src = "modpaper" }, "shop")
HOME = { x = sx + 2, y = sy + 1, z = 0 }
SolAddressPlaces.syncHome()
""")
def world_json():
    L.execute("WROTE = nil")
    ok = L.eval("SolUI.writeWorldRaw({ containers = {}, player = { x = PLAYER.x, y = PLAYER.y }, sol = { x = SOL.x, y = SOL.y } })")
    w = L.eval("WROTE")
    return ok, (json.loads(w) if w else None), w
ok, snap, raw = world_json()
ck("writeWorldRaw: the snapshot is written, ASCII JSON", ok is True and snap is not None and all(ord(ch) < 128 for ch in raw))
sb = (snap or {}).get("solBook") or {}
rows = sb.get("rows") or []
print("      solBook:", json.dumps(sb, ensure_ascii=False)[:600])
ck("solBook: 11 rows (10 papers + our home), from her", sb.get("n") == 11 and len(rows) == 11 and sb.get("from") == "sol", (sb.get("n"), len(rows), sb.get("from")))
ck("solBook: our home first, with its street", rows and rows[0] == {"g": "home", "st": "Jefferson Rd", "d": 2}, rows[:1])
order = [r["g"] for r in rows]
ck("solBook: the page's order (home, house, tourist, shop, public, stash, area)", order == ["home", "house", "house", "tourist", "tourist", "shop", "shop", "shop", "public", "stash", "area"], order)
shops = [r for r in rows if r["g"] == "shop"]
ck("solBook: looted last in its section", shops[-1].get("lt") is True and shops[-1]["n"] == "E.P. Tools (Louisville)", shops)
ck("solBook: no coordinates anywhere (no x, y, box or parts keys)", not re.search(r'"(?:x|y|z|x1|y1|x2|y2|bx1|gx|parts)"', json.dumps(sb)))
cf = next((r for r in rows if r.get("n") == "Coalfield"), {})
ck("solBook: Coalfield 3000 tiles west of her (d 3000, dir 7)", cf.get("d") == 3000 and cf.get("dir") == 7, cf)
hs = next((r for r in rows if r.get("n") == "625 Dewey Street, Muldraugh"), {})
ck("solBook: the listing east of her, town kept", hs.get("dir") == 3 and hs.get("c") == "Muldraugh" and 1190 <= hs.get("d", 0) <= 1200, hs)
ck("solBook: a rental marked", any(r.get("ls") for r in rows if r.get("n") == "Ducase Apartments"))
ck("solBook: stash named by its street", any(r["g"] == "stash" and r.get("n") == "Main Street" for r in rows))
ck("solBook: an Arabic name decodes (the game's escapes -> JSON \\u)", any(r.get("n") == "محل الحي" for r in rows), [r.get("n") for r in rows])
snap_path, base_path = os.path.join(T, "snap.json"), os.path.join(T, "base.json")
json.dump(snap, open(snap_path, "w", encoding="utf-8"), ensure_ascii=False)
# she is away: from him
L.execute("FAR = {}")
_, s2, _ = world_json()
cf2 = next((r for r in s2["solBook"]["rows"] if r.get("n") == "Coalfield"), {})
ck("she is away: counted from him", s2["solBook"]["from"] == "player" and cf2.get("d") == 2995, (s2["solBook"]["from"], cf2))
L.execute("FAR = nil")
# switch off
L.execute("SW.book_memory = false")
_, s3, _ = world_json()
ck("switch off: no solBook in the snapshot", s3 is not None and "solBook" not in s3)
json.dump(s3, open(base_path, "w", encoding="utf-8"), ensure_ascii=False)
L.execute("SW.book_memory = true")
# a broken book never costs the snapshot
L.execute("SAVED_E = SolAddressBook.entries; SolAddressBook.entries = function() error('boom') end")
ok4, s4, _ = world_json()
ck("book read fails: the snapshot is still written, without solBook", ok4 is True and s4 is not None and "solBook" not in s4)
L.execute("SolAddressBook.entries = SAVED_E")
# a new life: the book is empty, our home comes from SolHome
L.execute("SOL.id = 'sc-2'; SolLife.checkIdentity()")
_, s5, _ = world_json()
ck("new Sol (her book went with her): only our home, from SolHome", s5["solBook"]["n"] == 1 and s5["solBook"]["rows"][0]["g"] == "home", s5.get("solBook"))
L.execute("HOME = nil")
_, s6, _ = world_json()
ck("no home, empty book: n 0, rows []", s6["solBook"] == {"n": 0, "from": "sol", "rows": []}, s6.get("solBook"))
# a big book: at most 40 rows
L.execute("SolAddressBook.MAX_ENTRIES = 1000; for i = 1, 45 do SolAddressBook.record({ kind = 'area', x = SOL.x + i * 10, y = SOL.y, name = 'Area ' .. i, src = 'a' .. i }) end")
_, s7, _ = world_json()
ck("45 rows in the book: 40 sent, n 45", s7["solBook"]["n"] == 45 and len(s7["solBook"]["rows"]) == 40, (s7["solBook"]["n"], len(s7["solBook"]["rows"])))
ck("no Lua error logged", not any("failed" in str(l) for l in L.eval("LOGS").values()), [l for l in L.eval("LOGS").values() if "failed" in str(l)][:3])

# ================================================================ 3. the Mind installer on a copy, then the child
M = os.path.join(T, "sol_mind")
shutil.copytree(LIVE_MIND, M, ignore=shutil.ignore_patterns("__pycache__", "*.log", "*.bak*", "*.pem"))
MIND_APPLY = os.path.join(HERE, "apply_s86_book_memory_mind.py")
m1 = run(MIND_APPLY, M)
ck("Mind installer applies", m1.returncode == 0 and m1.stdout.count("appended") == 2, (m1.stdout[-300:], m1.stderr[-600:]))
dm = digest(M, ["memory_answers.py", "chat_service.py"])
m2 = run(MIND_APPLY, M)
ck("Mind installer idempotent", m2.returncode == 0 and m2.stdout.count("kept") == 2 and digest(M, ["memory_answers.py", "chat_service.py"]) == dm, m2.stdout)
ck("Mind: only memory_answers.py and chat_service.py differ from the live Mind", {k for k, v in digest(M, list(live_mind)).items() if live_mind.get(k) != v} == {"memory_answers.py", "chat_service.py"})
imp = subprocess.run([sys.executable, "-c", "import sys; sys.dont_write_bytecode = True; sys.path.insert(0, sys.argv[1]); import chat_service, model_router, memory_answers", M], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
ck("Mind copy imports", imp.returncode == 0, imp.stderr[-600:])
c = subprocess.run([sys.executable, os.path.abspath(__file__), "--mind-child", M, snap_path, base_path], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
print("\n".join("   " + l for l in (c.stdout or "").splitlines()))
ck("Mind child: all pass", c.returncode == 0, (c.stderr or "")[-800:])

# ================================================================ 4. card_check and the route replay on the patched copy
cc = subprocess.run([sys.executable, CARD_CHECK, M], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
last = (cc.stdout or "").strip().splitlines()[-1:] or ["?"]
print("      card_check:", last[0])
ck("card_check.py on the patched Mind: PASS", cc.returncode == 0 and "CARD_CHECK: PASS" in cc.stdout, "\n".join(l for l in cc.stdout.splitlines() if l.startswith(("FAIL", "  -")))[-1500:])
ck("card_check: the WARN 'address-book places in her memory' is gone", "address-book places in her memory" not in cc.stdout)
print("      card_check warnings:", [l[:90] for l in cc.stdout.splitlines() if l.startswith("WARN")])
ck("card_check: the far_work memory feature check still sees s85's line through the s86 wrapper", "far_work return report in her memory" not in cc.stdout)
ev = subprocess.run([sys.executable, EVAL, "--as-is", M], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP, cwd=HERE)
print("      route eval:", ((ev.stdout or "").strip().splitlines() or ["?"])[-1])
ck("test_s82_route_eval.py --as-is on the patched Mind: PASS", ev.returncode == 0, "\n".join(l for l in ev.stdout.splitlines() if l.startswith("FAIL"))[-1500:])

# ================================================================ nothing live touched
ck("live lab client, switch file and live Mind untouched",
   digest(LAB_CL, ["SolAuthority.lua", "SolAddressBook.lua", "SolWorldScan.lua", "SolBookMemory.lua"]) == live_cl
   and read(os.path.join(LAB_LUA, "SolFixes_LAB.txt")) == live_fix and digest(LIVE_MIND) == live_mind)
shutil.rmtree(T, ignore_errors=True)
print("RESULT", "ALL PASS" if not FAIL else "%d FAILED: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
