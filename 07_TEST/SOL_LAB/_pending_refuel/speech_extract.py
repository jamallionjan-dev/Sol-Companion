# -*- coding: utf-8 -*-
"""Every English line Living Fellows can give Sol to say, split into batches for translation. usage: speech_extract.py"""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
CL = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\lua\client"
FILES = ("SCDialogue.lua", "SCBanter.lua", "SCIntrusiveLines.lua")
SIZE = 900
STR = re.compile(r'"((?:[^"\\]|\\.)+)"')
SKIP = re.compile(r"\b(?:print|log|error|assert|getText|require|logger|warn)\s*\(|\breason\b\s*=|return\s+(?:false|nil)\s*,")
START = re.compile(r"^[A-Z%(\"'.]")
def unlua(s): return s.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
seen, order = set(), []
for name in FILES:
    for raw in open(os.path.join(CL, name), encoding="utf-8", errors="replace"):
        code = raw.split("--", 1)[0] if '"' not in raw.split("--", 1)[-1] else raw
        if SKIP.search(code): continue
        for m in STR.finditer(code):
            s = unlua(m.group(1))
            if len(s.split()) < 2 or not START.match(s) or "_" in s or s in seen: continue
            seen.add(s); order.append(s)
gen = open(os.path.join(HERE, "gen_speech_ar.py"), encoding="utf-8").read()
done = {l.split(" ||| ")[0].strip() for l in gen.splitlines() if " ||| " in l}
todo = [s for s in order if s not in done]
out = os.path.join(HERE, "speech_tr")
os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    if f.endswith(".in.json"): os.remove(os.path.join(out, f))
batches = [todo[i:i + SIZE] for i in range(0, len(todo), SIZE)]
for i, b in enumerate(batches, 1):
    json.dump(b, open(os.path.join(out, "batch_%02d.in.json" % i), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("lines", len(order), "already done", len(order) - len(todo), "to translate", len(todo), "batches", len(batches))
print("tokens", sorted({t for s in todo for t in re.findall(r"%\d|%s|\{[^}]*\}|<[^>]*>|\[[^\]]*\]", s)})[:30])
for s in todo[:4] + todo[-3:]: print("  ", s[:110])
