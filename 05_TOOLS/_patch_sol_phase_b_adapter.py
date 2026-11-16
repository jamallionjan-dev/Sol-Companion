from pathlib import Path
import shutil, time
p=Path.home()/"Desktop"/"Sol"/"03_CHATGPT_BRIDGE"/"chatgpt_bridge"/"chatgpt_bridge_server.py"
if not p.exists(): raise SystemExit("MISSING="+str(p))
s=p.read_text(encoding="utf-8")
b=p.with_name("chatgpt_bridge_server.py.before_sol_mailbox_adapter_"+time.strftime("%Y%m%d_%H%M%S")+".bak")
shutil.copy2(p,b)
marker='ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}\n'
insert=r"""
# Sol/PZ mailbox -> existing browser queue adapter.
# Phase-B transport proof: queue one complete current Game->Brain frame, then stop.
SOL_OUTBOX = Path.home() / "Zomboid" / "Lua" / "SolAI_Outbox.txt"
_sol_outbox_thread = None

def _sol_read_complete_frame():
    try:
        raw = SOL_OUTBOX.read_text(encoding="utf-8-sig")
    except (FileNotFoundError, OSError):
        return None
    lines = raw.splitlines()
    if len(lines) < 3 or lines[0].strip() != "SOL_AI_FRAME_V1" or lines[-1].strip() != "END":
        return None
    return raw.strip() if lines[1].strip() else None

def _sol_mailbox_pump():
    global _sol_next_id
    deadline = time.time() + 120.0
    while time.time() < deadline:
        try:
            frame = _sol_read_complete_frame()
            if frame:
                prompt = (
                    "SOL GAME FRAME / PHASE-B ROUND-TRIP. This is machine transport, not a human request. "
                    "Using the established Sol protocol, return exactly one executable PowerShell code block. "
                    "The command must write a valid Brain->Game SOL_AI_FRAME_V1 ACK to "
                    "$HOME\\Zomboid\\Lua\\SolAI_Inbox.txt for the exact Game->Brain sequence in this frame. "
                    "Preserve protocol sol-ai-1, schema 1, sessionId and worldId exactly. "
                    "Use a fresh numeric inbound sequence. Do not alter game/mod files. "
                    "After writing, print SOL_PHASE_B_ACK_WRITTEN plus the acked sequence. FRAME:\n" + frame
                )
                with _sol_queue_lock:
                    item={"id":_sol_next_id,"message":prompt}
                    _sol_next_id += 1
                    _sol_queue.append(item)
                log("SOL phase-B frame queued for browser id=%s" % item["id"])
                return
        except Exception as exc:
            log("SOL mailbox pump error: %r" % (exc,))
        time.sleep(0.35)
    log("SOL mailbox pump stopped: no complete frame within 120s")
"""
if "_sol_mailbox_pump" not in s:
    if marker not in s: raise SystemExit("MARKER_GLOBALS_NOT_FOUND")
    s=s.replace(marker,marker+insert+"\n",1)
serve="    server.daemon_threads = True\n"
start=r"""    global _sol_outbox_thread
    if _sol_outbox_thread is None or not _sol_outbox_thread.is_alive():
        _sol_outbox_thread = threading.Thread(target=_sol_mailbox_pump, name="SolMailboxPump", daemon=True)
        _sol_outbox_thread.start()
        print(f"Sol phase-B mailbox adapter watching: {SOL_OUTBOX}", flush=True)
"""
if "SolMailboxPump" not in s:
    if serve not in s: raise SystemExit("MARKER_SERVER_START_NOT_FOUND")
    s=s.replace(serve,start+serve,1)
compile(s,str(p),"exec")
p.write_text(s,encoding="utf-8")
print("PATCHED="+str(p))
print("BACKUP="+str(b))
print("PYTHON_COMPILE=PASS")
print("PHASE_B_ADAPTER_PRESENT="+str("_sol_mailbox_pump" in s and "SolMailboxPump" in s))
