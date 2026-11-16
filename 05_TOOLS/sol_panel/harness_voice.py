"""Voice button in the game: press -> start, press -> stop; Sol Mind's state drives what the chat shows."""
import os, sys, tempfile
from lupa import lua51
L = lua51.LuaRuntime(unpack_returned_tuples=True)
D = tempfile.mkdtemp() + "/"
L.globals()["D"] = D
L.execute(r'''
T0 = 1000
function getTimestampMs() return T0 end
function getFileWriter(n) local f = io.open(D .. n, "w"); return { write = function(_, s) f:write(s) end, close = function() f:close() end } end
function getFileReader(n) local f = io.open(D .. n, "r"); if not f then return nil end
  return { readLine = function() return f:read("*l") end, close = function() f:close() end } end
TICK = nil; Events = { OnTick = { Add = function(f) TICK = f end } }
SolUI = { openChat = function() OPENED = true end }
''')
L.execute(open("build/media/lua/client/SolVoice.lua", encoding="ascii").read())
G = L.globals(); U = G.SolUI; res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
rd = lambda n: dict(l.split("=", 1) for l in open(D + n).read().splitlines() if "=" in l)
U.voiceToggle()
r1 = rd("SolVoice_Request.txt")
check("first press: 'start' request and the chat opens", r1["action"] == "start" and G.OPENED and U.voice.listening)
G.T0 = 2000; U.voiceToggle()
r2 = rd("SolVoice_Request.txt")
check("second press: 'stop' with a newer id", r2["action"] == "stop" and int(r2["id"]) > int(r1["id"]) and not U.voice.listening)
open(D + "SolVoice_State.txt", "w").write("ack=%s\nstatus=done\ncode=\ntext=x\n" % r2["id"])
G.T0 = 2500; G.TICK()
check("Sol Mind's 'done' is picked up", U.voice.status == "done")
G.T0 = 3000; U.voiceToggle(); r3 = rd("SolVoice_Request.txt")
open(D + "SolVoice_State.txt", "w").write("ack=%s\nstatus=error\ncode=mic_unavailable\ntext=\n" % r3["id"])
G.T0 = 3400; G.TICK()
check("an error ends listening and keeps its code for the chat", U.voice.listening is False and U.voice.code == "mic_unavailable")
G.T0 = 4000; U.voiceToggle(); G.T0 = 4000 + 32000; G.TICK()
check("forgotten second press: listening ends by itself after 30 s", U.voice.listening is False)
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
