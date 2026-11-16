"""Add a --headless mode to sol_mind.py (idempotent). Usage: python patch_headless.py <sol_mind.py>"""
import sys
p = sys.argv[1]
raw = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in raw else "\n"
lines = raw.split(nl)
if any("--headless" in l for l in lines):
    print("sol_mind.py: headless already present"); sys.exit(0)
def idx(stripped):
    hits = [i for i, l in enumerate(lines) if l.strip() == stripped]
    if len(hits) != 1: print("ABORT: %r found %d times" % (stripped, len(hits))); sys.exit(2)
    return hits[0]
expected = ['print(HELP)', 'while True:', 'try:', 'line = input("sol> ")', 'except EOFError:', 'break',
            'if not handle(line, runner, log):', 'break']
cands = [k for k, l in enumerate(lines) if l.strip() == "print(HELP)"
         and [x.strip() for x in lines[k:k + len(expected)]] == expected]
if len(cands) != 1:
    print("ABORT: console loop (print(HELP) + input loop) found %d times" % len(cands)); sys.exit(2)
i = cands[0]
ind = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
block = lines[i:i + len(expected)]
new = [ind + "if a.headless:",
       ind + "    stop_file = os.path.join(HERE, \"sol_mind.stop\")",
       ind + "    log(\"headless mode (started by sol_mind_service); stop file: %s\" % stop_file)",
       ind + "    while not os.path.exists(stop_file):",
       ind + "        time.sleep(0.5)",
       ind + "    try:",
       ind + "        os.remove(stop_file)",
       ind + "    except OSError:",
       ind + "        pass",
       ind + "    log(\"headless stop requested (game closed)\")",
       ind + "else:"] + ["    " + l for l in block]
lines[i:i + len(expected)] = new
j = idx("a = ap.parse_args()")
aind = lines[j][:len(lines[j]) - len(lines[j].lstrip())]
lines.insert(j, aind + 'ap.add_argument("--headless", action="store_true", help="no console; stop when sol_mind.stop appears (sol_mind_service)")')
open(p, "w", encoding="utf-8", newline="").write(nl.join(lines))
print("sol_mind.py: headless mode added")
