"""Offline proof: runs the REAL SCAIMailbox/SCAIToolGateway/SCAIRuntime Lua (Lua 5.1 via lupa)
with stubbed engine functions and a simulated clock, against the Python Sol Mind.
No Project Zomboid, no GPU. Usage: python harness.py <lua_client_dir> <scratch_dir>
"""
import os
import shutil
import sys

from lupa import lua51

import codec
from mailbox import write_frame
from mind_core import MindCore

LUA_DIR, SCRATCH = sys.argv[1], sys.argv[2]
FAILS = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + (("  -- " + detail) if detail else ""))
    if not cond:
        FAILS.append(name)


if os.path.isdir(SCRATCH):
    shutil.rmtree(SCRATCH)
os.makedirs(SCRATCH)
INBOX = os.path.join(SCRATCH, "SolAI_Inbox.txt")
OUTBOX = os.path.join(SCRATCH, "SolAI_Outbox.txt")


def py_read(path):
    p = os.path.join(SCRATCH, path)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def py_write(path, text):
    with open(os.path.join(SCRATCH, path), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


lua = lua51.LuaRuntime()
g = lua.globals()
g.py_read, g.py_write = py_read, py_write
lua.execute(r'''
__clock = 1000000
__issued, __said = {}, {}
__player = { kind = "player" }
__actor = { kind = "sol" }
function getTimestampMs() return __clock end
function getCurrentSaveName() return "HarnessWorld" end
function getSpecificPlayer(i) return __player end
function getFileWriter(path, create, append)
  local buf = {}
  return { writeln = function(self, s) buf[#buf + 1] = s end,
           close = function(self) py_write(path, table.concat(buf, "\n") .. "\n") end }
end
function getFileReader(path, create)
  local text = py_read(path)
  if text == nil then
    if not create then return nil end
    py_write(path, ""); text = ""
  end
  if text ~= "" and string.sub(text, -1) ~= "\n" then text = text .. "\n" end
  local lines = {}
  for line in string.gmatch(text, "([^\n]*)\n") do
    local clean = string.gsub(line, "\r$", "")
    lines[#lines + 1] = clean
  end
  local i = 0
  return { readLine = function(self) i = i + 1; return lines[i] end, close = function(self) end }
end
SurvivorCompanion = {}
local SC = SurvivorCompanion
SC.Registry = {
  living = function() return { __actor } end,
  idOf = function(a) if a == __actor then return "sol-1" end end,
  byId = function(id) return { runtime = {} } end,
}
SC.GameplayUtil = {
  nowMs = function() return __clock end,
  idOf = function(a) if a == __actor then return "sol-1" end end,
  say = function(a, text) __said[#__said + 1] = text; return true end,
}
SC.Commands = { issue = function(id, cmd, payload, player)
  __issued[#__issued + 1] = cmd; return true, "ok" end }
SC.AIPerceptionAdapter = { snapshot = function(a, p, rt)
  return { sol = { x = 10.5, y = 20.25, z = 0, armed = true }, clock = __clock } end }
''')
for name in ("SCAIMailbox.lua", "SCAIToolGateway.lua", "SCAIRuntime.lua"):
    with open(os.path.join(LUA_DIR, name), "r", encoding="utf-8-sig") as f:
        lua.execute(f.read())
R = g.SurvivorCompanion.AIRuntime
M = g.SurvivorCompanion.AIMailbox

# ---- T1: codec cross-compatibility with the real Lua codec ----
sample = {"protocol": "sol-ai-1", "schema": 1, "type": "say", "sequence": 7, "sessionId": "W:1",
          "worldId": "W", "timestampMs": 1792662906796,
          "payload": {"text": "مرحبا يا سول — hello", "ok": True, "no": False, "pi": 3.25,
                      "list": [1, "two", {"k": "v"}], "gone": None, "empty": {}}}
body = codec.encode_body(sample)
lua_frame = M.decodeFrame(body)
check("T1a Lua decodes Python-encoded frame", lua_frame is not None and lua_frame["payload"]["text"] == sample["payload"]["text"])
relua = M.encodeFrame(lua_frame)
check("T1b Lua re-encode is byte-identical", relua == body, "" if relua == body else "differs")
py_back = codec.decode_body(relua)
check("T1c Python decodes Lua-encoded frame", py_back["payload"]["pi"] == 3.25 and py_back["payload"]["ok"] is True)

# ---- driver ----
logs = []
mind = MindCore(INBOX, OUTBOX, log=lambda s: logs.append(s))


def run(ms, brain=True):
    for _ in range(ms // 50):
        g.__clock = g.__clock + 50
        if g.__clock % 100 == 0:
            R.tick()
        if brain:
            mind.step(g.__clock)


def issued():
    t = g.__issued
    return [t[i] for i in range(1, len(t) + 1)]


def health():
    return R.health()


# ---- T2: stale ack from an old session is in the inbox before start ----
old = {"protocol": "sol-ai-1", "schema": 1, "sessionId": "Old:1", "worldId": "Old", "sequence": 6511,
       "timestampMs": 1, "type": "ack", "payload": {"ackSequence": 12}}
write_frame(INBOX, old)
R.start()
run(300, brain=False)   # game polls first and sees the stale ack before the mind starts
run(3000)
h = health()
check("T2a handshake flows (hello acked, game sequence advanced)", h["sequence"] > 3, "game seq=%s" % h["sequence"])
check("T2b stale old-session ack produced stale_session error and was survived",
      any("stale_session" in s for s in logs))
check("T2c perception received by mind", mind.perception is not None and mind.perception["sol"]["armed"] is True)

# ---- T3: follow end-to-end through the real gateway ----
rid = mind.request_tool("follow")
run(4000)
st = mind.status(rid)
check("T3a follow tool_result accepted", st.get("accepted") is True and st.get("status") == "accepted", str(st))
check("T3b SC.Commands.issue('follow') called exactly once", issued().count("follow") == 1, str(issued()))

# ---- T4: lost command (overwritten before the game polled) is resent, executed once ----
MindCore.GRACE_MS = 0
rid2 = mind.request_tool("go_to", {"x": 100, "y": 200, "z": 0})
for _ in range(200):
    if mind.status(rid2)["status"] != "queued":
        break
    run(50)
else:
    check("T4 queued request leaves queue within the bounded poll window", False,
          str(mind.status(rid2)))
MindCore.GRACE_MS = 700
run(8000)
st2 = mind.status(rid2)
check("T4a lost go_to was resent", mind.stats["resends"] >= 1, "resends=%d" % mind.stats["resends"])
check("T4b go_to accepted after resend", st2.get("accepted") is True, str(st2))
check("T4c move_to executed exactly once", issued().count("move_to") == 1, str(issued()))

# ---- T5: invalid tool is rejected by the gateway with a reason ----
rid3 = mind.request_tool("teleport")
run(4000)
st3 = mind.status(rid3)
check("T5 unsupported tool rejected", st3.get("accepted") is False and st3.get("reason") == "unsupported_tool", str(st3))

# ---- T6: say (Arabic) reaches the speech API ----
mind.say("حاضر، سأتبعك")
run(3000)
said = [g.__said[i] for i in range(1, len(g.__said) + 1)]
check("T6 Arabic say reached GameplayUtil.say", "حاضر، سأتبعك" in said, str(said))

# ---- T7: game restarts the session (new save / reload) ----
seq_before = health()["sequence"]
R.stop()
g.__clock = g.__clock + 5000
R.start()
run(4000)
h7 = health()
check("T7a mind detected the new session", mind.stats["sessions"] == 2, "sessions=%d" % mind.stats["sessions"])
check("T7b new session flows (sequence advanced past hello)", h7["sequence"] > 3, "seq=%s" % h7["sequence"])
rid4 = mind.request_tool("stay")
run(4000)
check("T7c tool works in the new session", (mind.status(rid4) or {}).get("accepted") is True, str(mind.status(rid4)))

# ---- T8: game paused 10s (no ticks) then resumes; mind must not wedge ----
run(10000, brain=True) if False else None
for _ in range(200):
    g.__clock = g.__clock + 50
    mind.step(g.__clock)
seq_p = health()["sequence"]
run(3000)
check("T8 flow resumes after a pause", health()["sequence"] > seq_p, "before=%s after=%s" % (seq_p, health()["sequence"]))

print("STATS", mind.stats)
print("GAME ", {k: health()[k] for k in ("sequence", "criticalQueued", "inFlightType", "requestCache")})
shutil.rmtree(SCRATCH)
print("SUMMARY %s (%d failed)" % ("ALL PASS" if not FAILS else "FAILURES: " + ", ".join(FAILS), len(FAILS)))
sys.exit(1 if FAILS else 0)
