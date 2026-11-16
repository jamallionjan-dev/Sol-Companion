"""Folds the captured Sol_SecretLoadout.txt into the shipped data file SolSecretLoadoutData.lua (this folder, and the mod's
media/lua/shared when a client dir is given), and prints the two weapons with their parts by in-game display name.
usage: fold_secret_loadout.py <Sol_SecretLoadout.txt> [<client dir>]      (game closed for the client copy)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def lua_str(s):
    out = []
    for ch in s:
        if ch in ('"', "\\"): out.append("\\" + ch)
        elif 32 <= ord(ch) < 127: out.append(ch)
        else: out.append("?")                       # Kahlua reads the file as text; the data lines are item types and English names
    return '"' + "".join(out) + '"'

def render(lines):
    body = "".join("        %s,\n" % lua_str(l) for l in lines)
    head = open(os.path.join(HERE, "SolSecretLoadoutData.lua"), encoding="ascii").read().split("SolSecretLoadoutData = {")[0]
    return head + "SolSecretLoadoutData = {\n    lines = {\n" + body + "    },\n}\nreturn SolSecretLoadoutData\n"

def describe(lines):
    t = dict(l.split("=", 1) for l in lines if "=" in l)
    out = []
    for i in (1, 2):
        p = "w%d." % i
        if not t.get(p + "type"): continue
        out.append("%s (%s) [%s]: %s | magazine: %s x%s spare | round: %s" % (t[p + "name"], t[p + "type"], t.get(p + "where", ""),
                   t.get(p + "partnames", "").replace(";", ", ") or "-", t.get(p + "magname") or "-", t.get(p + "spare", "0"), t.get(p + "round", "")))
    return out

if __name__ == "__main__":
    lines = [l.rstrip("\r\n") for l in open(sys.argv[1], encoding="utf-8", errors="replace") if "=" in l]
    assert any(l.startswith("w1.type=") for l in lines) and any(l.startswith("w2.type=") for l in lines), "no two weapons in the file"
    text = render(lines)
    targets = [os.path.join(HERE, "SolSecretLoadoutData.lua")]
    if len(sys.argv) > 2: targets.append(os.path.join(sys.argv[2], "..", "shared", "SolSecretLoadoutData.lua"))
    for p in targets:
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
        open(p, "w", encoding="ascii", newline="\n").write(text)
    for d in describe(lines): print(d)
    print("folded")
