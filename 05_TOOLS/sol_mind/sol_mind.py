"""Sol Mind v0.1 - the brain-side process for the Sol mod (protocol sol-ai-1).

Runs beside Project Zomboid, answers the game's mailbox (ack, single-flight),
and gives you a small console to command Sol.

  python sol_mind.py            live: mailbox in %USERPROFILE%\\Zomboid\\Lua
  python sol_mind.py --demo     offline: runs the REAL SCAI*.lua (Lua 5.1) as a simulated
                                game in a temporary folder - no Project Zomboid, no GPU

Provider (who decides/talks): set in sol_mind.json next to this file, e.g.
  {"provider": "none"}
v0.1 implements "none" (you give the orders). ollama / api / bridge are reserved
names for the next stage and fall back to "none" for now.
"""
import argparse
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mind_core import MindCore  # noqa: E402
from runtime_profile import active_game_mailbox, default_mailbox  # noqa: E402

VERSION = "0.2.0"
PROVIDERS = ("none", "ollama", "api", "bridge")
IMPLEMENTED = ("none",)
SINGLETON_PORT = 8768
DEFAULT_LUA_CLIENT = os.path.normpath(os.path.join(
    HERE, "..", "..", "01_WORK", "Sol", "42", "media", "lua", "client"))
SIMPLE_TOOLS = ("follow", "stay", "regroup", "retreat")
HELP = """commands:
  follow | stay | regroup | retreat
  go_to X Y [Z]          walk to a tile
  check_room X Y [Z]
  say TEXT               Sol speaks (Arabic or English)
  raw TOOL {json}        any gateway tool with JSON arguments
  status                 transport state
  tools                  tools the game announced
  seen                   latest perception snapshot
  results                recent command results
  wait SECONDS           pause (useful when commands are piped in)
  help | quit"""


def now_ms():
    return int(time.time() * 1000)


class Log:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()

    def __call__(self, msg):
        line = time.strftime("%H:%M:%S ") + msg
        with self.lock:
            try:
                print(line, flush=True)
            except UnicodeEncodeError:
                print(line.encode("ascii", "replace").decode(), flush=True)
            try:
                if os.path.exists(self.path) and os.path.getsize(self.path) > 1024 * 1024:
                    os.replace(self.path, self.path + ".old")
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(time.strftime("%Y-%m-%d ") + line + "\n")
            except OSError:
                pass


def load_config(log):
    cfg = {"provider": "none"}
    path = os.path.join(HERE, "sol_mind.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                cfg.update(json.load(f))
        except (OSError, ValueError) as e:
            log("WARN sol_mind.json unreadable (%s); using defaults" % e)
    p = str(cfg.get("provider", "none")).lower()
    if p not in PROVIDERS:
        log("WARN unknown provider %r; using none" % p)
        p = "none"
    elif p not in IMPLEMENTED:
        log("NOTE provider %r is planned for the next stage; v0.1 runs as none" % p)
        p = "none"
    cfg["provider"] = p
    return cfg


def acquire_singleton():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", SINGLETON_PORT))
        s.listen(1)
        return s
    except OSError:
        s.close()
        return None


class Runner:
    def __init__(self, inbox, outbox, log):
        self.lock = threading.Lock()
        self.mind = MindCore(inbox, outbox, log=log)
        self.log = log
        self.stop = threading.Event()
        self.last_frames = 0
        self.last_frame_at = None

    def loop(self):
        while not self.stop.is_set():
            try:
                with self.lock:
                    self.mind.step(now_ms())
                    if self.mind.stats["frames"] != self.last_frames:
                        self.last_frames = self.mind.stats["frames"]
                        self.last_frame_at = time.time()
                time.sleep(0.05)
            except Exception as e:  # keep the brain alive; report and retry
                self.log("ERROR mind step: %r" % (e,))
                time.sleep(1.0)


class DemoGame:
    """The real SCAIMailbox/SCAIToolGateway/SCAIRuntime Lua, driven in real time with engine stubs."""

    def __init__(self, lua_client, mailbox_dir, log):
        from lupa import lua51
        self.dir, self.log = mailbox_dir, log
        self.stop = threading.Event()
        lua = lua51.LuaRuntime()
        g = lua.globals()
        g.py_read = self._read
        g.py_write = self._write
        g.py_event = lambda s: log("[game] " + s)
        g.py_now = now_ms
        lua.execute(r'''
__player, __actor = { kind = "player" }, { kind = "sol" }
function getTimestampMs() return py_now() end
function getCurrentSaveName() return "DemoWorld" end
function getSpecificPlayer(i) return __player end
function getFileWriter(path, create, append)
  local buf = {}
  return { writeln = function(self, s) buf[#buf + 1] = s end,
           close = function(self) py_write(path, table.concat(buf, "\n") .. "\n") end }
end
function getFileReader(path, create)
  local text = py_read(path)
  if text == nil then if not create then return nil end; py_write(path, ""); text = "" end
  if text ~= "" and string.sub(text, -1) ~= "\n" then text = text .. "\n" end
  local lines = {}
  for line in string.gmatch(text, "([^\n]*)\n") do local c = string.gsub(line, "\r$", ""); lines[#lines + 1] = c end
  local i = 0
  return { readLine = function(self) i = i + 1; return lines[i] end, close = function(self) end }
end
SurvivorCompanion = {}
local SC = SurvivorCompanion
local pos = { x = 10800, y = 9400, z = 0 }
SC.Registry = { living = function() return { __actor } end,
  idOf = function(a) if a == __actor then return "sol-demo" end end,
  byId = function(id) return { runtime = {} } end }
SC.GameplayUtil = { nowMs = py_now,
  idOf = function(a) if a == __actor then return "sol-demo" end end,
  say = function(a, text) py_event("Sol says: " .. text); return true end }
SC.Commands = { issue = function(id, cmd, payload, player)
  if cmd == "move_to" and type(payload) == "table" then pos = { x = payload.x, y = payload.y, z = payload.z or 0 } end
  py_event("Sol executes command: " .. cmd); return true, "ok" end }
SC.AIPerceptionAdapter = { snapshot = function(a, p, rt)
  return { sol = { x = pos.x, y = pos.y, z = pos.z }, demo = true } end }
''')
        for name in ("SCAIMailbox.lua", "SCAIToolGateway.lua", "SCAIRuntime.lua"):
            with open(os.path.join(lua_client, name), "r", encoding="utf-8-sig") as f:
                lua.execute(f.read())
        self.R = g.SurvivorCompanion.AIRuntime

    def _read(self, path):
        p = os.path.join(self.dir, path)
        if not os.path.exists(p):
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""

    def _write(self, path, text):
        with open(os.path.join(self.dir, path), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def loop(self):
        ok, why = self.R.start()
        self.log("[game] AIRuntime.start -> %s %s" % (ok, why))
        while not self.stop.is_set():
            self.R.tick()
            time.sleep(0.1)


def handle(cmd, runner, log):
    parts = cmd.strip().split(None, 1)
    if not parts:
        return True
    head = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""
    m = runner.mind
    if head in ("quit", "exit"):
        return False
    if head == "help":
        print(HELP)
    elif head == "wait":
        try:
            time.sleep(min(max(float(rest or 1), 0), 120))
        except ValueError:
            print("usage: wait SECONDS")
    elif head in SIMPLE_TOOLS:
        with runner.lock:
            rid = m.request_tool(head)
        log("queued %s -> %s" % (head, rid))
    elif head in ("go_to", "check_room"):
        try:
            nums = [float(v) for v in rest.split()]
            if len(nums) not in (2, 3):
                raise ValueError
        except ValueError:
            print("usage: %s X Y [Z]" % head)
            return True
        args = {"x": nums[0], "y": nums[1], "z": nums[2] if len(nums) == 3 else 0}
        with runner.lock:
            rid = m.request_tool(head, args)
        log("queued %s %s -> %s" % (head, args, rid))
    elif head == "say":
        if not rest:
            print("usage: say TEXT")
            return True
        with runner.lock:
            rid = m.say(rest)
        log("queued say -> %s" % rid)
    elif head == "raw":
        bits = rest.split(None, 1)
        try:
            args = json.loads(bits[1]) if len(bits) > 1 else {}
            if not isinstance(args, dict):
                raise ValueError
        except ValueError:
            print('usage: raw TOOL {"key": value}')
            return True
        with runner.lock:
            rid = m.request_tool(bits[0], args)
        log("queued raw %s -> %s" % (bits[0], rid))
    elif head == "status":
        with runner.lock:
            silent = None if runner.last_frame_at is None else time.time() - runner.last_frame_at
            inflight = m.inflight["requestId"] if m.inflight else None
            print("session  : %s" % m.session)
            print("game seq : %s   phase: %s   inflight: %s   queued: %d" % (m.last_seq, m.phase, inflight, len(m.queue)))
            print("stats    : %s" % m.stats)
            if silent is None:
                print("game     : no frame received yet (is the game running with Sol spawned?)")
            elif silent > 10:
                print("game     : SILENT for %.0fs (paused, in menu, or closed)" % silent)
            else:
                print("game     : alive (last frame %.1fs ago)" % silent)
    elif head == "tools":
        with runner.lock:
            tools = dict(m.tools)
        if not tools:
            print("no hello received yet")
        for name in sorted(tools):
            spec = tools[name] if isinstance(tools[name], dict) else {}
            print("  %-17s %s" % (name, spec.get("arguments") or []))
    elif head == "seen":
        with runner.lock:
            p = m.perception
        if p is None:
            print("no perception yet")
        else:
            text = json.dumps(p, ensure_ascii=False, indent=1)
            lines = text.splitlines()
            print("\n".join(lines[:60]) + ("\n... (%d more lines)" % (len(lines) - 60) if len(lines) > 60 else ""))
    elif head == "results":
        with runner.lock:
            items = list(m.results.items())[-10:]
        for rid, res in items:
            print("  %s: %s" % (rid, res))
    else:
        print("unknown command; type help")
    return True


def main():
    ap = argparse.ArgumentParser(description="Sol Mind " + VERSION)
    ap.add_argument("--demo", action="store_true", help="offline run against the real Lua in a temp folder")
    ap.add_argument("--lua-dir", default=None,
                    help="mailbox folder (live mode)")
    ap.add_argument("--lua-client", default=DEFAULT_LUA_CLIENT, help="SCAI*.lua folder (demo mode)")
    ap.add_argument("--headless", action="store_true", help="no console; stop when sol_mind.stop appears (sol_mind_service)")
    ap.add_argument("--game-pid", type=int, default=0, help="stop when this process ends")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    log = Log(os.path.join(HERE, "sol_mind.log"))
    guard = acquire_singleton()
    if guard is None:
        print("Sol Mind is already running (port %d busy). Only one brain may own the mailbox." % SINGLETON_PORT)
        return 2
    cfg = load_config(log)
    scratch = game = None
    try:
        if a.demo:
            scratch = tempfile.mkdtemp(prefix="sol_mind_demo_")
            mailbox = scratch
            game = DemoGame(a.lua_client, scratch, log)
        else:
            mailbox = a.lua_dir or active_game_mailbox() or default_mailbox()
            if not os.path.isdir(mailbox):
                print("mailbox folder not found: %s" % mailbox)
                return 1
        inbox = os.path.join(mailbox, "SolAI_Inbox.txt")
        outbox = os.path.join(mailbox, "SolAI_Outbox.txt")
        log("Sol Mind %s | mode=%s | provider=%s | mailbox=%s" % (
            VERSION, "demo" if a.demo else "live", cfg["provider"], mailbox))
        runner = Runner(inbox, outbox, log)
        threading.Thread(target=runner.loop, daemon=True).start()
        try:
            from settings_service import Service as SettingsService
            SettingsService(mailbox, log=log).start()
            log("settings channel ready (SolSettings_*.txt)")
        except Exception as e:
            log("WARN settings channel not started: %r" % (e,))
        try:
            from chat_service import Chat as ChatService
            ChatService(mailbox, log=log, mind=runner.mind, mind_lock=runner.lock).start()
            log("chat channel ready (SolChat_*.txt)")
        except Exception as e:
            log("WARN chat channel not started: %r" % (e,))
        if game:
            threading.Thread(target=game.loop, daemon=True).start()
        if a.headless:
            stop_file = os.path.join(HERE, "sol_mind.stop")
            log("headless mode (started by sol_mind_service); stop file: %s" % stop_file)
            from game_watch import Watch
            watch = Watch(a.game_pid, outbox)
            next_look = 0.0
            while not os.path.exists(stop_file):
                time.sleep(0.5)
                if time.time() >= next_look:
                    next_look = time.time() + 2.0
                    if watch.game_is_gone():
                        log("the game is gone: Sol Mind stops with it")
                        break
            try:
                os.remove(stop_file)
            except OSError:
                pass
            log("headless stop (game closed)")
        else:
            print(HELP)
            while True:
                try:
                    line = input("sol> ")
                except EOFError:
                    break
                if not handle(line, runner, log):
                    break
        runner.stop.set()
        if game:
            game.stop.set()
        time.sleep(0.2)
        log("Sol Mind stopped | stats=%s" % runner.mind.stats)
        return 0
    except KeyboardInterrupt:
        log("Sol Mind interrupted")
        return 0
    finally:
        guard.close()
        if scratch:
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
