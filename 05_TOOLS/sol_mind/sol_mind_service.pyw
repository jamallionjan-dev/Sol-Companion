"""Sol Mind service: starts Sol Mind (hidden) when Project Zomboid starts and stops it when the game closes.
Runs hidden at Windows logon (HKCU Run -> pythonw). Logs to sol_mind_service.log next to this file.
Stop the service itself by creating sol_mind_service.stop in this folder."""
import os, socket, subprocess, sys, time
from runtime_profile import active_game_mailbox, default_mailbox
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "sol_mind_service.log")
MIND = os.path.join(HERE, "sol_mind.py")
MIND_STOP = os.path.join(HERE, "sol_mind.stop")
SVC_STOP = os.path.join(HERE, "sol_mind_service.stop")
PORT = 8769
POLL = float(os.environ.get("SOLSVC_POLL", "3"))
NO_WINDOW = 0x08000000 if os.name == "nt" else 0

def log(msg):
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > 1_000_000:
            os.replace(LOG, LOG + ".1")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass

def game_mailbox():
    fake = os.environ.get("SOLSVC_FAKE_GAME")          # tests only: a file whose existence means "game running"
    if fake is not None:
        return (os.environ.get("SOLSVC_FAKE_LUA_DIR") or default_mailbox()) if os.path.exists(fake) else None
    mailbox = active_game_mailbox()
    if mailbox:
        return mailbox
    return None

def pythonw():
    exe = sys.executable
    w = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return w if os.path.exists(w) else exe

def start_mind(mailbox):
    try: os.remove(MIND_STOP)
    except OSError: pass
    cmd = [os.environ.get("SOLSVC_PYTHON", pythonw()), MIND, "--lua-dir", mailbox, "--headless"]
    out = open(os.path.join(HERE, "sol_mind_log.txt"), "a", encoding="utf-8", errors="replace")   # readable when something goes wrong
    p = subprocess.Popen(cmd, cwd=HERE, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL,
                         stdout=out, stderr=subprocess.STDOUT)
    log("game mailbox %s -> Sol Mind started (pid %d)" % (mailbox, p.pid))
    return p

def stop_mind(p, why):
    if p is None or p.poll() is not None:
        return
    open(MIND_STOP, "w").close()
    try:
        p.wait(timeout=15); log("%s -> Sol Mind stopped cleanly (exit %s)" % (why, p.returncode))
    except subprocess.TimeoutExpired:
        p.terminate(); log("%s -> Sol Mind did not stop in 15 s; terminated" % why)
    try: os.remove(MIND_STOP)
    except OSError: pass

def main():
    guard = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        guard.bind(("127.0.0.1", PORT))
    except OSError:
        return 0                                       # already running: exit silently
    try: os.remove(SVC_STOP)
    except OSError: pass
    log("service started (pid %d, poll %.1fs)" % (os.getpid(), POLL))
    mind, mind_mailbox, restarts, blocked, gave_up = None, None, [], False, False
    try:
        while not os.path.exists(SVC_STOP):
            mailbox = game_mailbox()
            g = mailbox is not None
            alive = mind is not None and mind.poll() is None
            if alive and g and mailbox != mind_mailbox:
                stop_mind(mind, "game mailbox changed")
                mind, mind_mailbox, alive = None, None, False
            if g and not alive:
                if mind is not None:
                    log("Sol Mind exited while the game runs (exit %s)" % mind.returncode)
                    if mind.returncode == 2:
                        blocked = True
                        log("another Sol Mind already owns the mailbox (manual run?); not restarting until the game restarts")
                    mind = None
                if not blocked:
                    restarts = [t for t in restarts if time.time() - t < 300]
                    if len(restarts) < 3:
                        restarts.append(time.time()); mind = start_mind(mailbox); mind_mailbox = mailbox
                    elif not gave_up:
                        gave_up = True; log("ERROR Sol Mind failed 3 times in 5 min; waiting for the next game start")
            elif g is False:
                if alive:
                    stop_mind(mind, "game closed")
                mind, mind_mailbox, restarts, blocked, gave_up = None, None, [], False, False
            time.sleep(POLL)
    finally:
        stop_mind(mind, "service stopping")
        try: os.remove(SVC_STOP)
        except OSError: pass
        log("service stopped")
        guard.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
