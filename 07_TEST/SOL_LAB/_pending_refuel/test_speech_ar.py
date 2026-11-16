# -*- coding: utf-8 -*-
"""Sol's speech above her head: every speech key has Arabic, and no English reaches the bubble.
Uses the real SolSpeechAR, SolDialogueArabic and SolDialogueLines plus the patched U.say and Dialogue.emitResolved taken from a temporary copy of the lab's files
(the apply script is run on that copy, not on the lab). Actor, bubble drawing and getText are mocks: this proves the Lua logic, not the game."""
import glob, os, re, shutil, subprocess, sys, tempfile
from kahlua_env import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
_BEFORE = os.path.join(HERE, "..", "_backup", "20261109_043225_night_before_apply", "Sol_LAB", "42", "media", "lua", "client")   # the files as they were before apply_s34
if os.path.isdir(_BEFORE): LAB = _BEFORE
BS = chr(92)
ESC = re.compile(re.escape(BS) + "u[0-9A-Fa-f]{4}")


def read(p):
    return open(p, encoding="latin1", newline="").read()


def latin_outside_escapes(s):
    return re.search("[A-Za-z]", ESC.sub("", s)) is not None


def is_arabic(s):
    return bool(ESC.search(s)) and not latin_outside_escapes(s)


# --- a Lua string-literal reader (skips comments and long strings) to list the dialogue topics in LF's sources
def lua_strings(t):
    i, n = 0, len(t)
    out = []
    while i < n:
        c = t[i]
        if t.startswith("--", i):
            if t.startswith("--[[", i):
                j = t.find("]]", i); i = n if j < 0 else j + 2
            else:
                j = t.find("\n", i); i = n if j < 0 else j
        elif c in "\"'":
            j, b = i + 1, []
            while j < n and t[j] != c:
                if t[j] == BS:
                    b.append(t[j:j + 2]); j += 2
                else:
                    b.append(t[j]); j += 1
            out.append("".join(b)); i = j + 1
        elif t.startswith("[[", i):
            j = t.find("]]", i); out.append(t[i + 2:j]); i = j + 2
        else:
            i += 1
    return out


TOPIC = re.compile(r"^[a-z_0-9]+(\.[a-z_0-9]+)+$")


def topics():
    out = set()
    for f in glob.glob(os.path.join(LAB, "SC*.lua")):
        if "bak" in f or "Oddball" in f:
            continue
        for s in lua_strings(read(f)):
            if TOPIC.match(s) and not s.endswith((".lua", ".txt", ".json", ".png")):
                out.add(s)
    return sorted(out)


def slice_function(src, header):
    a = src.index(header)
    b = src.index("\nend", a)
    return src[a:b + 4]


work = tempfile.mkdtemp(prefix="sol_speech_")
for name in ("SCGameplayUtil.lua", "SCDialogue.lua", "SolDialogueArabic.lua"):
    shutil.copy(os.path.join(LAB, name), work)
args = [sys.executable, os.path.join(HERE, "apply_s34_lua.py"),
        os.path.join(work, "SCGameplayUtil.lua"), os.path.join(work, "SCDialogue.lua"),
        os.path.join(work, "SolDialogueArabic.lua"), os.path.join(work, "SolSpeechAR.lua")]
first = subprocess.run(args, capture_output=True, text=True)
assert first.returncode == 0, first.stderr
print("1. apply script: every replaced string occurs exactly once")
again = subprocess.run(args, capture_output=True, text=True)
assert again.returncode != 0, "applying twice must fail"
print("2. apply script refuses to run twice")

speech_src = read(os.path.join(HERE, "SolSpeechAR.lua"))
assert all(ord(c) < 128 for c in speech_src), "SolSpeechAR.lua must be pure ASCII"
for bad in ("//", "goto ", "%x"):
    assert bad not in speech_src, bad
assert "tonumber(" not in speech_src
print("3. SolSpeechAR.lua: pure ASCII, %d bytes, no Kahlua-unsafe constructs" % len(speech_src))
for name in ("apply_s34_lua.py",):
    assert all(ord(c) < 128 for c in read(os.path.join(HERE, name)))

L = lua51.LuaRuntime(unpack_returned_tuples=True)
G = L.globals()
loaded = set()
paths = {"SolDialogueArabic": os.path.join(work, "SolDialogueArabic.lua"), "SolSpeechAR": os.path.join(work, "SolSpeechAR.lua")}
import glob as _glob
paths.update({os.path.basename(f)[:-4]: f for f in _glob.glob(os.path.join(HERE, "SolSpeechAR_L*.lua"))})


def load(name):
    if name in loaded:
        return
    loaded.add(name)
    p = paths.get(name, os.path.join(LAB, name + ".lua"))
    L.execute(read(p))


G.require = load
L.execute("""
CLOCK = 1000000
function getTimestampMs() return CLOCK end
SPOKEN, NATIVE = {}, {}
OBJ = {}
Events = { OnGameStart = { Add = function(f) end }, OnTick = { Add = function(f) end } }
ISUIElement = {}
function ISUIElement:new() local o = {}; function o:initialise() end; function o:instantiate() end; function o:addToUIManager() end; return o end
UIFont = { Small = 1 }
function makeActor(id, companion)
    local a = { id = id, companion = companion }
    function a:addLineChatElement(l) NATIVE[#NATIVE + 1] = l end
    function a:Say(l) NATIVE[#NATIVE + 1] = l end
    function a:say(l) NATIVE[#NATIVE + 1] = l end
    function a:setCompanionSpeechDisplayMillis() end
    return a
end
SOL = makeActor("sol", true)
OTHER = makeActor("other", true)
SolUI = { solActor = function() return SOL end }
SolTheme = nil
LFText = {}
function solTextOriginal(key, ...)
    LFText[#LFText + 1] = { key = key, n = select("#", ...) }
    return key
end
UTIL = {}
SurvivorCompanion = { GameplayUtil = UTIL, UI = { solTextOriginal = solTextOriginal } }
SurvivorCompanion.Dialogue = { choose = function(actor, topic) return CHOSEN_LINE, { topic = topic } end }
""")
for f in ("SolOverlay", "SolDialogueLines", "SolDialogueArabic"):
    load(f)
L.execute(read(paths["SolSpeechAR"]))
loaded.add("SolSpeechAR")
L.execute("""
SolOverlay.install()
local realSpeak = SolBubble.speak
SolBubble.speak = function(actor, line, ms)
    local spoken = realSpeak(actor, line, ms)
    if spoken then SPOKEN[#SPOKEN + 1] = line end
    return spoken
end
""")
gu = read(os.path.join(work, "SCGameplayUtil.lua"))
L.execute("local U = UTIL\n"
          "function U.isCompanion(a) return a ~= nil and a.companion == true end\n"
          "function U.config() return nil end\n"
          "function U.call(obj, m, ...) local f = obj and obj[m]; if type(f) ~= 'function' then return nil, false end; return f(obj, ...), true end\n"
          "function U.nowMs() return CLOCK end\n"
          "function U.nameOf(a) return a.id == 'sol' and 'Sol Survivor' or 'Bob' end\n"
          + slice_function(gu, "function U.speechDisplayMillis(textValue)") + "\n"
          + slice_function(gu, "function U.say(actor, textValue)"))
dia = read(os.path.join(work, "SCDialogue.lua"))
L.execute("Dialogue = {}\nlocal function U() return UTIL end\nlocal rt = {}\n"
          "local function runtimeFor(a) rt[a] = rt[a] or {}; return rt[a] end\n"
          + slice_function(dia, "function Dialogue.emitResolved(actor, topic, line, options)"))
SPOKEN, NATIVE, CLOCK = G.SPOKEN, G.NATIVE, lambda: None
advance = L.eval("function(ms) CLOCK = CLOCK + ms end")
reset = L.eval("function() SPOKEN, NATIVE = {}, {} end")


def spoken():
    return [G.SPOKEN[i] for i in range(1, len(G.SPOKEN) + 1)]


def native():
    return [G.NATIVE[i] for i in range(1, len(G.NATIVE) + 1)]


say = L.eval("function(a, l) return UTIL.say(a, l) end")
emit = L.eval("function(a, t, l) return Dialogue.emitResolved(a, t, l) end")
SOL, OTHER = G.SOL, G.OTHER
S = G.SolSpeechAR

# every Arabic value is real Arabic in escapes
count = 0
for tbl in (S.lines, S.default):
    for k in tbl:
        v = tbl[k]
        assert isinstance(v, str) and is_arabic(v), (k, v)
        count += 1
for k in S.pools:
    pool = S.pools[k]
    assert len(pool) > 0, k
    for i in pool:
        assert is_arabic(pool[i]), (k, pool[i])
        count += 1
print("4. all %d authored lines are Arabic in escapes" % count)

# every topic resolves to Arabic
all_topics = topics()
assert len(all_topics) > 500
for t in all_topics:
    p = S.poolFor(t)[0]
    assert p is not None and is_arabic(p[1]), t
print("5. %d dialogue topics from LF's sources all have Arabic" % len(all_topics))

# every line seen this session: Arabic on the bubble, nothing through the game's bubble
logged = []
with open(os.path.join(HERE, "speech_logged_lines.txt"), encoding="utf-8") as f:
    for row in f.read().splitlines():
        topic, _, line = row.partition(chr(9))
        logged.append((topic, line))
assert len(logged) >= 150
exact = pool_only = 0
for topic, line in logged:
    reset(); advance(30000)
    ok, result = emit(SOL, topic, line)[:2]
    assert ok is True, (topic, line, result)
    assert len(spoken()) == 1 and is_arabic(spoken()[0]), (topic, line, spoken())
    assert native() == [], (topic, line, native())
    assert G.SolSpeechAR.lines[line] is not None or S.poolFor(topic) is not None
    exact += 1 if S.lines[line] is not None or "%1" in line else 0
print("6. %d logged lines reach the bubble in Arabic and never the game's own bubble" % len(logged))

# an unknown English line from every topic: Arabic or silence, never English
reset(); leaks = 0
for t in all_topics:
    advance(60000)
    emit(SOL, t, "A brand new English line nobody translated yet.")
    if any(not is_arabic(x) for x in spoken()) or native():
        leaks += 1
assert leaks == 0, leaks
print("7. %d topics with an untranslated English line: only Arabic reaches the bubble" % len(all_topics))

# direct say without a topic: an unknown English line is silence
reset()
r = say(SOL, "Hello there, this line has no translation at all.")
assert r is False and spoken() == [] and native() == [], (r, spoken(), native())
print("8. a direct English line with no translation: she says nothing")

# direct say with a known exact line is Arabic
reset()
assert say(SOL, "Zombie! Watch out!") is True
assert len(spoken()) == 1 and is_arabic(spoken()[0]) and native() == []
print("9. a direct translated line is Arabic above her head")

# LF's choose() remembers the topic for callers that say the line without one
reset(); advance(30000)
G.CHOSEN_LINE = "An English pool line picked by the game."
chosen = L.eval("function() return SurvivorCompanion.Dialogue.choose(SOL, 'danger.one') end")
assert chosen()[0] == "An English pool line picked by the game."
assert say(SOL, "An English pool line picked by the game.") is True
assert len(spoken()) == 1 and is_arabic(spoken()[0])
print("10. a line chosen by the game keeps its topic for a direct say")

# Arabic text (Sol Mind) stays; a stray English word goes
reset()
ar = BS + "u0634" + BS + "u0648" + " " + BS + "u0647" + BS + "u0644" + BS + "u0623 Zomboid."
assert say(SOL, ar) is True
assert len(spoken()) == 1 and is_arabic(spoken()[0]) and "Zomboid" not in spoken()[0]
print("11. Arabic reply with a stray English word: the word is dropped")

# another companion is not touched
reset()
assert say(OTHER, "Just an English line.") is True and native() == ["Just an English line."] and spoken() == []
print("12. another companion keeps its own English bubble")

# the pool does not repeat a line back to back
reset(); advance(30000)
emit(SOL, "banter.routine", "Untranslated chatter one.")
emit(SOL, "banter.routine", "Untranslated chatter two.")
assert len(spoken()) == 1
print("13. the same topic does not repeat inside the gap")

# the 307 warnings: templates get their own placeholders as arguments
reset()
G.LFText = L.table()
L.execute("SolDialogueArabic.reset(); SolDialogueArabic.localize('x', 'force a build now')")
calls = [(G.LFText[i].key, G.LFText[i].n) for i in range(1, len(G.LFText) + 1)]
lf = G.SolLF_AR
bare = [k for k, n in calls if re.search("%[1-9]", lf[k]) and n == 0]
assert calls and not bare, bare[:5]
assert max(n for _, n in calls) <= 4
print("14. %d keys read at first use: none with placeholders is asked without arguments, never more than 4" % len(calls))

shutil.rmtree(work, ignore_errors=True)
print("ALL PASSED on mocks. Not proven in the game: real getText behaviour with placeholder arguments, the drawn bubble, and speech that does not go through U.say.")
