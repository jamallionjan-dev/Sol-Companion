"""Insert the chat-channel hook into sol_mind.py after the settings hook (idempotent)."""
import sys
p = sys.argv[1]
raw = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in raw else "\n"
lines = raw.split(nl)
if any("chat_service" in l for l in lines):
    print("sol_mind.py: chat hook already present"); sys.exit(0)
idx = [i for i, l in enumerate(lines) if l.strip() == 'log("WARN settings channel not started: %r" % (e,))']
if len(idx) != 1:
    print("ABORT: settings hook anchor found %d times (run patch_sol_mind.py first)" % len(idx)); sys.exit(2)
i = idx[0]
ind = lines[i - 1][:len(lines[i - 1]) - len(lines[i - 1].lstrip())]   # indentation of 'except ...:'
hook = [ind + "try:",
        ind + "    from chat_service import Chat as ChatService",
        ind + "    ChatService(mailbox, log=log).start()",
        ind + "    log(\"chat channel ready (SolChat_*.txt)\")",
        ind + "except Exception as e:",
        ind + "    log(\"WARN chat channel not started: %r\" % (e,))"]
lines[i + 1:i + 1] = hook
open(p, "w", encoding="utf-8", newline="").write(nl.join(lines))
print("sol_mind.py: chat hook inserted")
