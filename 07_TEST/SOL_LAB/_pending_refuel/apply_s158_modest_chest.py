"""s158 modest_chest: turn on the body patch's own covered-chest (censorship) mode for Sol, switch `modest_chest`.
usage: apply_s158_modest_chest.py <client dir> [SolFixes_LAB.txt]
- copies SolModesty.lua (next to this script) into the client dir
- SolAuthority.lua: registers the switch
"kept" when already applied. The mode is read once per game session: a switch flip needs a game restart."""
import os, re, sys
CLIENT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
lua = open(os.path.join(HERE, "SolModesty.lua"), encoding="utf-8").read().replace(CRLF, NL)
assert all(ord(c) < 128 for c in lua), "SolModesty.lua must be ASCII"
lua = lua.replace(NL, CRLF)
dst = os.path.join(CLIENT, "SolModesty.lua")
if os.path.exists(dst) and open(dst, encoding="utf-8", newline="").read() == lua:
    print("kept SolModesty.lua")
else:
    open(dst, "w", encoding="ascii", newline="").write(lua)
    print("copied SolModesty.lua")
auth = os.path.join(CLIENT, "SolAuthority.lua")
text = open(auth, encoding="utf-8", newline="").read()
nl = CRLF if CRLF in text else NL
changed = False
for name, note in (("modest_chest", "s158: her body patch covers the chest under painted tops (needs a restart)"),
                   ("chest_diag", "s158: the body patch's own diagnostics in the log, for one test run")):
    if '"%s"' % name in text: continue
    old = "A.FIXES = {" + nl
    if text.count(old) != 1: raise RuntimeError(("SolAuthority.lua", "expected one A.FIXES", text.count(old)))
    text = text.replace(old, old + '    "%s",%s-- %s' % (name, " " * max(1, 20 - len(name)), note) + nl)
    changed = True
if changed:
    open(auth, "w", encoding="utf-8", newline="").write(text)
    print("edited SolAuthority.lua")
else:
    print("kept SolAuthority.lua")
if len(sys.argv) > 2:
    sw = sys.argv[2]
    for name in ("modest_chest", "chest_diag"):
        t = open(sw, encoding="utf-8", newline="").read()
        if not re.search(r"(?m)^%s=" % name, t):
            with open(sw, "a", encoding="utf-8", newline="") as f:
                f.write(("" if t.endswith((NL, CRLF)) else CRLF) + name + "=on" + CRLF)
            print("enabled %s in the switch file" % name)
        else:
            print("kept %s switch" % name)
print("s158 modest_chest applied")
