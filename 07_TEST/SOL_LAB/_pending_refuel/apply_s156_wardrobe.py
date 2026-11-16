"""s156 wardrobe: Sol's dressing room (clothes + hair, live preview), switch `wardrobe`.
usage: apply_s156_wardrobe.py <client dir> [SolFixes_LAB.txt]
- builds SolWardrobe.lua from SolWardrobe.src.lua next to this script (every non-ASCII character becomes a \\uXXXX escape,
  written in the Lua source with a doubled backslash, as in SolPages.lua) and copies it into the client dir
- SolAuthority.lua: registers the switch
"kept" when already applied."""
import os, re, sys
CLIENT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
BS = chr(92)


def build():
    src = open(os.path.join(HERE, "SolWardrobe.src.lua"), encoding="utf-8").read().replace(CRLF, NL)
    out = []
    for ch in src:
        o = ord(ch)
        out.append(ch if o < 128 else "%s%su%04X" % (BS, BS, o))
    text = "".join(out)
    assert all(ord(c) < 128 for c in text)
    return text.replace(NL, CRLF)


lua = build()
dst = os.path.join(CLIENT, "SolWardrobe.lua")
if os.path.exists(dst) and open(dst, encoding="utf-8", newline="").read() == lua:
    print("kept SolWardrobe.lua")
else:
    open(dst, "w", encoding="ascii", newline="").write(lua)
    print("copied SolWardrobe.lua")

auth = os.path.join(CLIENT, "SolAuthority.lua")
text = open(auth, encoding="utf-8", newline="").read()
if '"wardrobe"' in text:
    print("kept SolAuthority.lua")
else:
    nl = CRLF if CRLF in text else NL
    old = "A.FIXES = {" + nl
    if text.count(old) != 1: raise RuntimeError(("SolAuthority.lua", "expected one A.FIXES", text.count(old)))
    text = text.replace(old, old + '    "wardrobe",           -- s156: her dressing room (clothes and hair with a live preview)' + nl)
    open(auth, "w", encoding="utf-8", newline="").write(text)
    print("edited SolAuthority.lua")

if len(sys.argv) > 2:
    sw = sys.argv[2]
    t = open(sw, encoding="utf-8", newline="").read()
    if not re.search(r"(?m)^wardrobe=", t):
        with open(sw, "a", encoding="utf-8", newline="") as f:
            f.write(("" if t.endswith((NL, CRLF)) else CRLF) + "wardrobe=on" + CRLF)
        print("enabled wardrobe in the switch file")
    else:
        print("kept wardrobe switch")
print("s156 wardrobe applied")
