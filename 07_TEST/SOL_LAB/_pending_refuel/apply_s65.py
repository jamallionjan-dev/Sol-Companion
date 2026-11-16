"""Switch far_car: far away, Sol comes by the nearest usable car within 25 tiles of where she is saved (hers first), not only hers; and she can
say truthfully which cars are around her. Game closed only. Needs the jar from build_far_car.py (SolCarMove + SolCarsNear); without it the
game answers no_java as today.
SolFar.lua is patched IN PLACE (string replacements with asserts, each one skipped when already there), so this and apply_s64.py
(far_wait_speed, waitTick's clock) apply in either order. With far_car off every changed line behaves exactly as before.
usage: apply_s65.py <client dir> <sol_mind dir>      (either may be '-' to skip that side)"""
import os, sys
CL, MIND = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
MARK = "-- ---------------------------------------------------------------- far_car:"
MARK_KEYS = "-- ---------------------------------------------------------------- far_car keys:"

def patch(path, edits):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    for old, new in edits:
        old, new = old.replace(NL, nl), new.replace(NL, nl)
        if new in t: continue
        assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
        t = t.replace(old, new)
    open(path, "w", encoding="utf-8", newline="").write(t)

def lua(cl):
    block = open(os.path.join(HERE, "SolFar_far_car_block.lua"), encoding="utf-8").read().replace(CRLF, NL)
    assert block.startswith(MARK)
    keys = open(os.path.join(HERE, "SolFar_far_car_keys.lua"), encoding="utf-8").read().replace(CRLF, NL)
    assert keys.startswith(MARK_KEYS)
    far = os.path.join(cl, "SolFar.lua")
    if MARK_KEYS not in open(far, encoding="utf-8").read():
        patch(far, [("-- her car, when she can really use it where it is" + NL, keys + NL + "-- her car, when she can really use it where it is" + NL)])
    if MARK not in open(far, encoding="utf-8").read():
        patch(far, [("local function startFarCar(text)" + NL, block + NL + "local function startFarCar(text)" + NL)])
    patch(far, [
        # car_far: the car chosen by car_where (far_car) instead of only hers
        ('    local d = store()' + NL + '    if d == nil or tonumber(d.carSqlId) == nil then return false, "no_car" end' + NL + '    if d.carTowing == true then return false, "towing" end' + NL + '    local cost = fuelCost(d, tiles)',
         '    if farCarOn() then if pick ~= nil and nowMs() - pick.at <= PICK_MS then return startPicked(pick, x, y, tiles) end; return false, "pick_expired" end   -- far_car: only a car car_where chose' + NL +
         '    local d = store()' + NL + '    if d == nil or tonumber(d.carSqlId) == nil then return false, "no_car" end' + NL + '    if d.carTowing == true then return false, "towing" end' + NL + '    local cost = fuelCost(d, tiles)'),
        ('if d == nil or type(req) ~= "function" or loadedCar() ~= nil then lastResult = "loaded"; return end',
         'if d == nil or type(req) ~= "function" or (m.id == nil and loadedCar() ~= nil) then lastResult = "loaded"; return end'),
        ('local okR, sent = pcall(req, d.carSqlId, m.x, m.y)', 'local okR, sent = pcall(req, m.id or d.carSqlId, m.x, m.y)'),
        ('moving = { at = t, x = m.x, y = m.y, cost = m.cost }', 'moving = { at = t, x = m.x, y = m.y, cost = m.cost, id = m.id, mass = m.mass, quality = m.quality }'),
        ('    if d ~= nil then d.carX, d.carY, d.fuelDue = m.x, m.y, m.cost end',
         '    if d ~= nil and m.id ~= nil then d.carSqlId, d.carTowing, d.carZ, d.carMass, d.carQuality, d.carFuel = m.id, false, 0, m.mass, m.quality, nil end   -- far_car: the car she came in is hers now' + NL +
         '    if d ~= nil then d.carX, d.carY, d.fuelDue = m.x, m.y, m.cost end'),
        ('    if fuelIn(car) < MIN_FUEL then return nil, "no_fuel" end' + NL + '    return car' + NL,
         '    if fuelIn(car) < MIN_FUEL then return nil, "no_fuel" end' + NL +
         '    if farCarOn() then local okGo, why = loadedCanGo(car); if not okGo then return nil, why end end   -- far_car: unlocked and she can start it' + NL +
         '    return car' + NL),
        ('        ms = CAR_WAIT_MS' + NL, '        ms = farCarOn() and kindWait(kindOf(call(car, "getScriptName"))) or CAR_WAIT_MS' + NL),
        ('pcall(readAlive); pcall(rememberCar) end' + NL,
         'pcall(readAlive); pcall(rememberCar) end' + NL + '    if farCarOn() and actor() == nil then pcall(carsTick, t, record()) end              -- far_car: the cars near her, kept fresh' + NL),
        ('    if opt == "car_where" then return carWhere() end' + NL,
         '    if opt == "cars" and farCarOn() then return carsAnswer() end                -- far_car' + NL +
         '    if opt == "car_where" and farCarOn() then return carWhereFar() end' + NL +
         '    if opt == "car_where" then return carWhere() end' + NL),
    ])
    sp = os.path.join(cl, "SCPersistence.lua")                                 # her saved keys, read only (far_car)
    if os.path.exists(sp) and "function persistence.pendingKeyIds(" not in open(sp, encoding="utf-8").read():
        patch(sp, [("function persistence.pendingSnapshot()" + NL, PENDING_KEYS + "function persistence.pendingSnapshot()" + NL)])
    auth = os.path.join(cl, "SolAuthority.lua")                                 # after item_sort, so apply_s64's line right under "A.FIXES = {" stays as it wrote it
    if '"far_car"' not in open(auth, encoding="utf-8").read():
        patch(auth, [('    "item_sort",' + NL, '    "item_sort",' + NL + '    "far_car",            -- far away, she comes by the nearest usable car near her, not only hers' + NL)])
    fix = os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
    if os.path.exists(fix) and "far_car=" not in open(fix, encoding="utf-8").read():
        with open(fix, "a", encoding="utf-8", newline="") as h: h.write("far_car=on" + CRLF)

PENDING_KEYS = """-- far_car (SolFar): the key ids in her saved inventory, bags included. Read only; nothing else of the record leaves here.
function persistence.pendingKeyIds(id)
    local entry = type(id) == "string" and pending[id] or nil
    if entry == nil or entry.status == "quarantined" then return nil end
    local saved = entry.record
    local inv = type(saved) == "table" and saved.inventory or nil
    if type(inv) ~= "table" then return nil end
    local out = {}
    local function walk(list, depth)
        if type(list) ~= "table" or depth > 16 then return end
        for _, e in ipairs(list) do
            if type(e) == "table" then
                local k = type(e.key) == "table" and tonumber(e.key.id) or nil
                if k ~= nil and k >= 0 then out[math.floor(k)] = true end
                walk(e.children, depth + 1)
            end
        end
    end
    walk(inv.roots or inv, 0)
    return out
end

"""

MIND_CONST = r'''
# far_car: which cars are around her, read by the game from the saved rows near her. Synonyms go in these word lists only.
_CARS_WORDS = r"(?:سيار(?:ات|ة|ه)|عربيات|عربي[ةه]|مركبات|آليات|اليات)"
_NEAR_HER_WORDS = r"(?:حوالي(?:كي|ك)?|حواليكي|حولك|حوليكي|جنب(?:ك|كي)|قرب(?:ك|كي)|عند(?:ك|كي)|قريب[ةه]? (?:منك|عليكي|عليك)|قريبين (?:منك|عليكي))"
_CARS_Q_RX = re.compile(_CARS_WORDS + r"[^؟?.]*?" + _NEAR_HER_WORDS + "|" + _NEAR_HER_WORDS + r"[^؟?.]*?" + _CARS_WORDS)
_CARS_ASK_RX = re.compile(r"(?:^|\s)(?:شو|ايش|إيش|في|فيه|فيش|كم|قديش|شي|اي|أي|وين|فيكي تشوفي)(?:$|\s)|[؟?]")
_CARS_ORDER_RX = re.compile(r"(?:^|\s)(?:ركبي|اركبي|جيبي|سوقي|تعالي|خدي|خذي)(?:$|\s)")
FAR_CARS_STATE = {"ok": "بتمشي", "no_fuel": "ما فيها بنزين", "fuel_unknown": "ما بعرف قديش فيها بنزين", "locked": "مقفولة", "wreck": "محروقة",
                  "no_engine": "موتورها خربان", "no_tires": "دواليبها خربانة", "no_key": "ما في مفتاحها ولا مشرّطة",
                  "start_unknown": "ما بعرف إذا بقدر شغّلها", "lock_unknown": "ما بعرف إذا مقفولة", "trailer": "مقطورة", "loaded": "قريبة منك", "in_meta": "ما بقدر أوصلها", "unknown_type": "ما عرفت شو هي"}
FAR_CAR_NO.update({"no_car_near": "ما في سيارة بتمشي حواليّ، لا سيارتي ولا غيرها. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "no_fuel_near": "السيارات اللي حواليّ ما فيها بنزين كفاية للطريق. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "picked_no_fuel": "السيارة اللي لقيتها حواليّ ما فيها بنزين كفاية للطريق. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "scanning": "لسا عم شوف شو في سيارات حواليّ، جرب كمان مرة بعد شوي.",
                   "no_key_near": "في سيارات حواليّ بس ما معي مفتاح لوحدة منهن وما في وحدة مشرّطة. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "locked_near": "السيارات اللي حواليّ مقفولة. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "car_locked": "سيارتي مقفولة. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "car_lock_unknown": "ما بعرف إذا سيارتي مقفولة، فما رح جرّب. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "car_no_key": "ما معي مفتاح سيارتي وهي مش مشرّطة. إذا بدك بجي مشي، قلي تعالي مشي."})


def far_cars_line(reason):
    """far_car: the game's list (cars:<n>|id,script,dist,fuel,verdict,mine;...) in her words. Only what the list says."""
    head, _, body = str(reason).partition("|")
    rows = [r.split(",") for r in body.split(";") if r.count(",") == 5]
    if not rows: return "ما في ولا سيارة حواليّ."
    n = len(rows)
    out = ["حواليّ في " + ("سيارة وحدة" if n == 1 else "سيارتين" if n == 2 else "%d سيارات" % n) + ":"]
    for _id, script, d, fuel, verdict, mine in rows[:5]:
        name = script.split(".", 1)[-1] if script != "?" else "سيارة ما عرفت نوعها"
        bit = "%s%s على بعد %s خطوة، %s" % (name, " (سيارتي)" if mine == "1" else "", d, FAR_CARS_STATE.get(verdict, "ما بعرف وضعها"))
        if verdict == "ok" and fuel != "?": bit += "، فيها %s لتر" % fuel
        out.append(bit + ".")
    if n > 5: out.append("وفي غيرهن أبعد.")
    if any(v == "ok" for _i, _s, _d, _f, v, _m in rows): out.append("إذا بدك بجيك بوحدة منهن، قلي تعالي بالسيارة.")
    return " ".join(out)
'''

MIND_METHOD = '''    def _far_cars(self, snap, done):
        """far_car: which cars are around her, from the game's own saved rows. False when she is here or the switch is off (as before)."""
        far = self._far_state(snap)
        if far is None: return False
        r = None
        for _ in range(4):
            r = run_action(self.dir, "sol_far", "cars", wait=2.5)
            if not (isinstance(r, dict) and not r.get("ok") and r.get("reason") == "scanning"): break
            time.sleep(0.8)
        reason = str(r.get("reason")) if isinstance(r, dict) else ""
        if isinstance(r, dict) and r.get("ok") and reason.startswith("cars:"):
            self._forced = far_cars_line(reason)
        elif reason in ("unknown_option", "here", ""):
            return False
        else:
            self._forced = "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي."
        done.append("answered: the cars around her")
        self.log("chat: far cars -> %s" % reason[:300])
        return True

'''

def mind(md):
    p = os.path.join(md, "chat_service.py")
    t = open(p, encoding="utf-8", newline="").read().replace(CRLF, NL)
    start = t.index("FAR_NO_BODY_NEEDED = frozenset(")
    line = t[start:t.index(NL, start) + 1]
    patch(p, [
        (line, line + MIND_CONST.lstrip(NL)),
        ('        """Her body is not here: nothing may be answered as if it were. True when the message was an order and has been answered."""' + NL + "        if not FAR_WAKE: return False" + NL,
         '        """Her body is not here: nothing may be answered as if it were. True when the message was an order and has been answered."""' + NL + "        if not FAR_WAKE: return False" + NL +
         '        if _CARS_Q_RX.search(text or "") and _CARS_ASK_RX.search(text or "") and not _CARS_ORDER_RX.search(text or "") and self._far_cars(snap, done): return True   # far_car' + NL),
        ("    def _far_wake(self, far, coming):" + NL, MIND_METHOD + "    def _far_wake(self, far, coming):" + NL),
        ('        r = run_action(self.dir, "sol_far", "car_where", wait=2.5)' + NL,
         '        for _ in range(4):                                                       # far_car: the list of cars near her may still be on its way' + NL +
         '            r = run_action(self.dir, "sol_far", "car_where", wait=2.5)' + NL +
         '            if not (isinstance(r, dict) and not r.get("ok") and r.get("reason") == "scanning"): break' + NL +
         '            time.sleep(0.8)' + NL),
    ])

if CL != "-": lua(CL)
if MIND != "-": mind(MIND)
print("applied")
