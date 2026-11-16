"""Run only after the game is closed, after copying SolFar.lua and dot_far.png into place. Sol far away in an unloaded area: her saved record can be moved, the action exists, the panel shows it.
usage: apply_s30_lua.py <SCPersistence.lua> <SolActions.lua> <SolPanel.lua>"""
import sys
def E(s):
    """Lua source for a text the game's own text drawing decodes: every Arabic letter as a backslash-u escape."""
    return "".join("\\\\u%04X" % ord(c) if ord(c) > 126 else c for c in s)
def patch(p, pairs):
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b in pairs:
        a, b = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a) == 1, (p, a[:70], t.count(a))
        t = t.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("applied to", p)
patch(sys.argv[1], [
("""function persistence.isPending(id)
""", """-- Sol, when her body is not in the world: her saved tile moves, the normal restore does the rest.
function persistence.pendingIds()
    local ids = {}
    for _, id in ipairs(pendingOrder) do if pending[id] ~= nil and pending[id].bucket == "companions" then ids[#ids + 1] = id end end
    return ids
end
function persistence.pendingRelocate(id, x, y, z)
    local entry = type(id) == "string" and pending[id] or nil
    if entry == nil or entry.vehicle == true or entry.spawnTicket ~= nil or entry.status == "quarantined" then return false end
    local saved = entry.record
    local position = type(saved) == "table" and saved.position or nil
    if type(position) ~= "table" then return false end
    position.x, position.y, position.z = x, y, z
    local rawPosition = type(entry.raw) == "table" and entry.raw.position or nil      -- a save before she is restored writes this copy
    if type(rawPosition) == "table" then rawPosition.x, rawPosition.y, rawPosition.z = x, y, z end
    entry.nextAt = 0
    return true
end

function persistence.isPending(id)
"""),
])
patch(sys.argv[2], [
("""    if id == "sol_fuel" and type(U.solFuel) == "function" then return U.solFuel(option) end
""", """    if id == "sol_fuel" and type(U.solFuel) == "function" then return U.solFuel(option) end
    if id == "sol_far" and type(U.solFar) == "function" then return U.solFar(option) end
"""),
])
ASK = E("سول فايقة؟")
FAR, AWAKE, COMING = E("بعيدة"), E("فايقة"), E("جاية")
HINT, ON_WAY = E("قلها تعالي مشي"), E("جاية لعندك")
patch(sys.argv[3], [
("""local function inside(x, y, r) return x >= r[1] and y >= r[2] and x < r[1] + r[3] and y < r[2] + r[4] end
""", """local function inside(x, y, r) return x >= r[1] and y >= r[2] and x < r[1] + r[3] and y < r[2] + r[4] end
-- green near or awake, yellow dormant far away, grey only when there is no Sol or her systems are not up
local function dotName(sol)
    if type(U.solDotState) == "function" then
        local ok, state = pcall(U.solDotState)
        if ok and state then return "dot_" .. state end
    end
    return sol and "dot_on" or "dot_off"
end
"""),
("""    draw(sol and "dot_on" or "dot_off", R.dot[1], R.dot[2], R.dot[3], R.dot[4])
""", """    draw(dotName(sol), R.dot[1], R.dot[2], R.dot[3], R.dot[4])
"""),
("""    local d = tex(U.solActor() and "dot_on" or "dot_off")
""", """    local d = tex(dotName(U.solActor()))
"""),
("""    draw("status_" .. (sol and "on" or "off") .. "_" .. lang, R.status[1], R.status[2], R.status[3], R.status[4])
""", """    local far = sol == nil and type(U.solFarState) == "function" and U.solFarState() or nil
    if far and SolText then
        local label = lang == "en" and (far == "coming" and "On her way" or far == "awake" and "Awake" or "Far away") or (far == "coming" and \"""" + COMING + """\" or far == "awake" and \"""" + AWAKE + """\" or \"""" + FAR + """\")
        SolText.drawLine(self, SolText.codepoints(label), R.status[1], R.status[2], R.status[3], { scale = 0.5, align = "right", r = 0.95, g = 0.72, b = 0.25 })
    else
        draw("status_" .. (sol and "on" or "off") .. "_" .. lang, R.status[1], R.status[2], R.status[3], R.status[4])
    end
"""),
("""    draw("speech_" .. lang, R.speech[1], R.speech[2], R.speech[3], R.speech[4])
""", """    if far and SolText then
        -- far away: this box is the way to wake her, then what comes next
        self:drawRect(R.speech[1], R.speech[2], R.speech[3], R.speech[4], 0.92, 0.07, 0.16, 0.26)
        local eta = type(U.solFarEta) == "function" and U.solFarEta() or nil
        local left = eta and (" " .. math.floor(eta / 60) .. ":" .. ((eta % 60) < 10 and "0" or "") .. (eta % 60)) or ""
        local text = far == "coming" and ((lang == "en" and "On her way to you" or \"""" + ON_WAY + """\") .. left)
            or far == "awake" and (lang == "en" and "Tell her: come on foot" or \"""" + HINT + """\")
            or (lang == "en" and "Sol, are you awake?" or \"""" + ASK + """\")
        SolText.drawLine(self, SolText.codepoints(text), R.speech[1] + 8, R.speech[2] + 28, R.speech[3] - 16, { scale = 0.62, align = "center", r = 0.95, g = 0.95, b = 0.95 })
        if far == "far" and over and inside(mx, my, R.speech) then self:drawRect(R.speech[1], R.speech[2], R.speech[3], R.speech[4], 0.12, 1, 1, 1) end
    else
        draw("speech_" .. lang, R.speech[1], R.speech[2], R.speech[3], R.speech[4])
    end
"""),
("""    local b = self:hitButton(x, y)
    if b then
        if not b.enabled then log(b.key .. " is not available yet"); return true end
""", """    if inside(x, y, R.speech) and type(U.solFarState) == "function" and U.solFarState() == "far" and type(U.sendChat) == "function" then
        local t = getTimestampMs and getTimestampMs() or 0                       -- the button is the same question as typing it in the chat
        if t - (self.farAskedAt or 0) > 5000 then self.farAskedAt = t; U.sendChat({ text = \"""" + ASK + """\" }) end
        return true
    end
    local b = self:hitButton(x, y)
    if b then
        if not b.enabled then log(b.key .. " is not available yet"); return true end
"""),
])
