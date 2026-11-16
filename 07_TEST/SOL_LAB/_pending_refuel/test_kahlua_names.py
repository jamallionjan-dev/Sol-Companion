"""Standard Lua names the game's Kahlua does not have, each one found the hard way in the running game. None may be called from our Lua."""
import glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
CL = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
ABSENT = ("next",)   # "Tried to call nil" at SolFarmWork.lua:1044, 2026-11-09
FAIL = []
files = {}
for f in glob.glob(os.path.join(CL, "Sol*.lua")) + glob.glob(os.path.join(HERE, "Sol*.lua")): files[f] = os.path.basename(f)
hits = {}
for f, name in files.items():
    if name.startswith("SolSpeechAR_L"): continue
    s = re.sub(r'"(?:[^"\\]|\\.)*"', '""', open(f, encoding="utf-8", errors="replace").read())
    s = re.sub(r"--.*", "", s)
    for fn in ABSENT:
        if re.search(r"(?<![\w.:])%s\s*\(" % fn, s) and not re.search(r"local\s+(?:function\s+)?%s\b" % fn, s): hits.setdefault(name, []).append(fn)
print(("PASS " if not hits else "FAIL ") + "no call to a name the game does not have" + ((" : " + str(hits)) if hits else ""))
print("SUMMARY", "ALL PASS" if not hits else "FAILED")
sys.exit(1 if hits else 0)
