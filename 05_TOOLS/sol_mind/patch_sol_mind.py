"""Insert the settings-channel hook into sol_mind.py (idempotent). Usage: python patch_sol_mind.py <sol_mind.py>"""
import sys, re
p = sys.argv[1]; s = open(p, encoding="utf-8").read()
if "settings_service" in s:
    print("sol_mind.py: hook already present"); sys.exit(0)
anchor = "threading.Thread(target=runner.loop, daemon=True).start()"
lines = s.split("\n"); idx = [i for i, l in enumerate(lines) if l.strip() == anchor]
if len(idx) != 1:
    print("ABORT: anchor found %d times" % len(idx)); sys.exit(2)
i = idx[0]; ind = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
hook = [ind + "try:",
        ind + "    from settings_service import Service as SettingsService",
        ind + "    SettingsService(mailbox, log=log).start()",
        ind + "    log(\"settings channel ready (SolSettings_*.txt)\")",
        ind + "except Exception as e:",
        ind + "    log(\"WARN settings channel not started: %r\" % (e,))"]
lines[i + 1:i + 1] = hook
nl = "\r\n" if "\r\n" in s else "\n"
out = "\n".join(lines)
if nl == "\r\n": out = out.replace("\r\n", "\n").replace("\n", "\r\n")
open(p, "w", encoding="utf-8", newline="").write(out)
print("sol_mind.py: hook inserted after line %d" % (i + 1))
