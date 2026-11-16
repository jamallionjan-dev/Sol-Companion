"""Project Zomboid keeps only the low 8 bits of non-ASCII characters in Lua source files (proven 2026-10-24).
Every non-ASCII character in Sol's Lua files becomes \\\\uXXXX (a backslash-u escape that SolText decodes).
Run before packaging; also used by the tests, which refuse non-ASCII Lua."""
import glob, sys
def asciify(text):
    out = []
    for ch in text:
        c = ord(ch)
        if c < 128: out.append(ch)
        elif c <= 0xFFFF: out.append("\\\\u%04X" % c)
        else:
            c -= 0x10000; out.append("\\\\u%04X\\\\u%04X" % (0xD800 + (c >> 10), 0xDC00 + (c & 0x3FF)))
    return "".join(out)
if __name__ == "__main__":
    for f in sorted(glob.glob(sys.argv[1] + "/Sol*.lua")):
        s = open(f, encoding="utf-8").read()
        a = asciify(s)
        if a != s:
            open(f, "w", encoding="ascii", newline="").write(a); print("asciified", f)
