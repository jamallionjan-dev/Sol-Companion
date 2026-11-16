"""The generated Levantine lines: every file compiles, every line kept its placeholders, is Arabic, and fits a bubble."""
import glob, json, os, re, sys
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
L = lua51.LuaRuntime(unpack_returned_tuples=True)
files = sorted(glob.glob(os.path.join(HERE, "SolSpeechAR_L*.lua")))
ck("generated files exist", len(files) >= 5, len(files))
for f in files:
    src = open(f, encoding="ascii").read()
    ck("compiles: " + os.path.basename(f), not isinstance(L.globals().loadstring(src), tuple))
    L.execute(src)
t = L.globals().SolSpeechARLines
loaded = dict((k, v) for k, v in t.items())
src = {}
for f in glob.glob(os.path.join(HERE, "speech_tr", "*.out.json")): src.update(json.load(open(f, encoding="utf-8")))
ck("lines loaded", len(loaded) >= 4300, len(loaded))
bad = [k for k, v in loaded.items() if re.search(r"(?<!\\u[0-9A-Fa-f]{0})[A-Za-z]", re.sub(r"\\u[0-9A-Fa-f]{4}", "", v))]
ck("nothing Latin outside the escapes", not bad, bad[:3])
miss = [k for k, v in loaded.items() if sorted(re.findall(r"%\d", k)) != sorted(re.findall(r"%\d", v))]
ck("placeholders kept", not miss, miss[:3])
ck("all in Arabic", all("\\u06" in v for v in loaded.values()))
ck("short enough", max(len(re.sub(r"\\u[0-9A-Fa-f]{4}", "x", v)) for v in loaded.values()) <= 100)
ck("rejected list is small", sum(1 for _ in open(os.path.join(HERE, "speech_rejected.txt"), encoding="utf-8")) <= 50)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
