"""refuel_from_can and car_eligible_only. Station refuel (SolFuel, refuel_errand) is not edited. Game closed only. All or nothing.
usage: apply_s45.py <sol_mind dir> <client dir>"""
import os, shutil, sys
MIND, CLIENT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
ON = '(type(rawget(_G, "SolAuthority")) == "table" and SolAuthority.on("car_eligible_only") == true)'
EDITS = {}
def E(p, a, b): EDITS.setdefault(p, []).append((a, b))

GPS = os.path.join(CLIENT, "SolGPS.lua"); ACT = os.path.join(CLIENT, "SolActions.lua"); AUTH = os.path.join(CLIENT, "SolAuthority.lua")
E(GPS, """    local best, bd = nil, 30 * 30
    for _, v in ipairs(vehicles) do
        local vx, vy = tonumber(call(v, "getX")), tonumber(call(v, "getY"))
        if vx and vy then
""", """    if type(U.solPickCar) == "function" and U.solCarRulesOn() then
        local picked, none = U.solPickCar(vehicles, anchor, 30)
        U._noEligibleCar = none == true
        if picked == nil then log("no car she may use within 30 tiles") end
        return picked
    end
    local best, bd = nil, 30 * 30
    for _, v in ipairs(vehicles) do
        local vx, vy = tonumber(call(v, "getX")), tonumber(call(v, "getY"))
        if vx and vy then
""")
E(GPS, """    if not veh then G.lastResult, G.reason = "failed", "no_vehicle_near"; return false, G.reason end
""", """    if not veh then G.lastResult, G.reason = "failed", (U._noEligibleCar == true) and "no_usable_car" or "no_vehicle_near"; return false, G.reason end
""")
E(ACT, """    local best, bd = nil, (radius or 30) ^ 2
    for _, v in ipairs(vehicles) do
        local okd, d = pcall(function() return (v:getX() - p:getX()) ^ 2 + (v:getY() - p:getY()) ^ 2 end)
""", """    if type(U.solPickCar) == "function" and U.solCarRulesOn() then return (U.solPickCar(vehicles, p, radius or 30)) end
    local best, bd = nil, (radius or 30) ^ 2
    for _, v in ipairs(vehicles) do
        local okd, d = pcall(function() return (v:getX() - p:getX()) ^ 2 + (v:getY() - p:getY()) ^ 2 end)
""")
E(AUTH, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "refuel_from_can", "car_eligible_only",' + NL)

CS = os.path.join(MIND, "chat_service.py"); MR = os.path.join(MIND, "model_router.py")
E(MR, """    "survey":        (""", """    "refuel_from_can":   ("تعبي السيارة من بدون بنزين", None),
    "refuel_at_station": ("تروح تعبي السيارة من الكازية", "عبي السيارة بنزين من الكازية"),
    "survey":        (""")
E(MR, """EXTRA_EXAMPLE = {"survey": "فحصي المكان", "why": "ليش ما زبطت"}""", """EXTRA_EXAMPLE = {"survey": "فحصي المكان", "why": "ليش ما زبطت", "refuel_from_can": "عبي السيارة بنزين"}""")
E(CS, """        if action == "why":
            r = self._why_answer(snap); done_line("model", action, "-", r); return r
""", """        if action == "refuel_from_can":
            r = run_action(self.dir, "refuel_from_can", None, wait=3.0)
            done_line("model", action, "accepted", r)
            if isinstance(r, dict) and r.get("ok") and str(r.get("reason")) in ("started", "busy"):
                self._can_waiting = {"t": time.time()}
                return "حاضر، بجيب بدون وبعبيها."
            return CAN_REFUEL_AR.get(str((r or {}).get("reason")), "ما قدرت عبيها هلأ.")
        if action == "why":
            r = self._why_answer(snap); done_line("model", action, "-", r); return r
""")
E(CS, """            for watch in (self._park_watch, self._farm_pending_watch):
""", """            for watch in (self._park_watch, self._farm_pending_watch, self._can_watch):
""")
E(CS, """    def _farm_pending_watch(self):
""", """    def _can_watch(self):
        w = getattr(self, "_can_waiting", None)
        if not w: return
        if time.time() - w["t"] > 600:
            self._can_waiting = None
            return
        r = run_action(self.dir, "refuel_from_can", "status", wait=2.5)
        reason = str(r.get("reason")) if isinstance(r, dict) else ""
        if reason.startswith("done:"):
            self._can_waiting = None
            _, litres, pct = reason.split(":")
            self._say_later("عبيتها: %s لتر، وصار البنزين %s%%." % (litres, pct))
        elif reason.startswith("failed:"):
            self._can_waiting = None
            self._say_later(CAN_REFUEL_AR.get(reason[7:], "ما قدرت عبيها هلأ."))

    def _farm_pending_watch(self):
""")
E(CS, """import model_router as MR
""", """import model_router as MR
CAN_REFUEL_AR = {"no_can": "ما لقيت بدون فيه بنزين، لا معي ولا بالبيت.", "cans_empty": "البدونات خلصو والسيارة لسا ما تعبت.", "no_car": "ما في سيارة قريبة أعبيها.",
                 "car_not_loaded": "السيارة بعيدة عني هلأ.", "no_tank": "ما لقيت خزان بهالسيارة.", "wrong_fuel": "هالسيارة وقودها مو بنزين.", "tank_full": "السيارة مليانة.",
                 "fix_off": "هالشغلة مطفية هلأ.", "no_sol": "مو هون هلأ.", "no_way": "ما قدرت أوصل لعند الخزان.", "cannot_take_can": "ما قدرت آخد البدون."}
""")
E(CS, """    "hotwiring": "ما في مفتاح، رح شرّطها، وبس خلّص قلي نمشي",
""", """    "hotwiring": "ما في مفتاح، رح شرّطها، وبس خلّص قلي نمشي",
    "no_usable_car": "السيارات القريبة كلها مقفلة وما معنا مفتاحها",
""")

out = {}
for p, ps in EDITS.items():
    t = open(p, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    for a, b in ps:
        a2, b2 = a.replace(NL, nl), b.replace(NL, nl)
        assert t.count(a2) == 1, (p[-20:], a[:60], t.count(a2))
        t = t.replace(a2, b2)
    if p.endswith(".py"): compile(t, p, "exec")
    out[p] = t
for p, t in out.items(): open(p, "w", encoding="utf-8", newline="").write(t)
for f in ("SolCanRefuel.lua", "SolCarRules.lua"): shutil.copy(os.path.join(HERE, f), os.path.join(CLIENT, f))
fix = os.path.join(CLIENT, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
with open(fix, "a", encoding="utf-8", newline="") as h: h.write("refuel_from_can=on" + CRLF + "car_eligible_only=on" + CRLF)
print("applied")
