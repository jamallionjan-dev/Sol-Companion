"""Type-aware link check: every class, method and field our Java names in the game must exist in this build with the same type.
Read-only. usage: linkcheck.py <game jar> <our jar> [<our jar> ...]  (exit 0 = no mismatch, 1 = mismatch)"""
import re
import struct
import sys
import zipfile

OBJECT = {"getClass", "hashCode", "equals", "toString", "notify", "notifyAll", "wait", "clone", "finalize"}
GAME_PREFIX = ("zombie/", "se/krka/", "fmod/", "astar/")
TYPE = re.compile(r"L((?:zombie|se/krka|fmod|astar)/[\w/$]+);")


def parse(b):
    n = struct.unpack(">H", b[8:10])[0]
    cp, i, k = [None] * n, 10, 1
    while k < n:
        t = b[i]
        if t == 1:
            l = struct.unpack(">H", b[i + 1:i + 3])[0]
            cp[k] = ("u", b[i + 3:i + 3 + l].decode("utf-8", "replace"))
            i += 3 + l
        elif t in (3, 4):
            i += 5
        elif t in (5, 6):
            i += 9
            k += 1
        elif t in (7, 8, 16, 19, 20):
            cp[k] = (t, struct.unpack(">H", b[i + 1:i + 3])[0])
            i += 3
        elif t in (9, 10, 11, 12, 17, 18):
            cp[k] = (t, *struct.unpack(">HH", b[i + 1:i + 5]))
            i += 5
        elif t == 15:
            i += 4
        else:
            raise ValueError(t)
        k += 1
    u2 = lambda p: struct.unpack(">H", b[p:p + 2])[0]
    u4 = lambda p: struct.unpack(">I", b[p:p + 4])[0]
    name = lambda idx: cp[cp[idx][1]][1] if idx else None
    this, sup = name(u2(i + 2)), name(u2(i + 4))
    ifc = u2(i + 6)
    ifs = [name(u2(i + 8 + 2 * x)) for x in range(ifc)]
    i += 8 + 2 * ifc
    members = set()
    for _ in range(2):
        c = u2(i)
        i += 2
        for _ in range(c):
            members.add((cp[u2(i + 2)][1], cp[u2(i + 4)][1]))
            a = u2(i + 6)
            i += 8
            for _ in range(a):
                i += 6 + u4(i + 2)
    return cp, this, sup, ifs, members


def load_game(path):
    game = {}
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.endswith(".class") and "META-INF" not in n:
                _, this, sup, ifs, m = parse(z.read(n))
                game[this] = (sup, ifs, m)
    return game


def has(game, owner, nm, desc, seen):
    """True found. None: reached a JDK parent, which may hold it. False: absent."""
    if owner in seen:
        return False
    seen.add(owner)
    if owner == "java/lang/Object":
        return nm in OBJECT
    if owner not in game:
        return None
    sup, ifs, m = game[owner]
    if (nm, desc) in m:
        return True
    res = False
    for p in [sup] + ifs:
        if p:
            r = has(game, p, nm, desc, seen)
            if r:
                return True
            if r is None:
                res = None
    return res


def check(game, path):
    bad, refs = {}, 0
    with zipfile.ZipFile(path) as z:
        own = {n[:-6] for n in z.namelist() if n.endswith(".class")}
        for n in z.namelist():
            if not n.endswith(".class"):
                continue
            short = n.split("/")[-1][:-6]
            cp = parse(z.read(n))[0]
            for e in cp:
                if not e:
                    continue
                if e[0] == "u":
                    for t in TYPE.findall(e[1]):
                        if t not in game and t not in own:
                            bad.setdefault("MISSING TYPE " + t, set()).add(short)
                elif e[0] == 7:
                    c = cp[e[1]][1]
                    if c.startswith(GAME_PREFIX) and c not in game and c not in own:
                        bad.setdefault("MISSING CLASS " + c, set()).add(short)
                elif e[0] in (9, 10, 11):
                    refs += 1
                    owner = cp[cp[e[1]][1]][1]
                    if owner.startswith("[") or owner in own or not owner.startswith(GAME_PREFIX):
                        continue
                    nt = cp[e[2]]
                    nm, desc = cp[nt[1]][1], cp[nt[2]][1]
                    found = has(game, owner, nm, desc, set())
                    if found is False or (found is None and "zombie/" in desc):
                        bad.setdefault("%s.%s %s" % (owner, nm, desc), set()).add(short)
    return bad, refs


def main(argv):
    game = load_game(argv[1])
    total, refs = 0, 0
    for p in argv[2:]:
        bad, r = check(game, p)
        total += len(bad)
        refs += r
        print("%s: %d refs, %d mismatches" % (p.replace("\\", "/").split("/")[-1], r, len(bad)))
        for k in sorted(bad):
            print("  " + k + " <- " + ", ".join(sorted(bad[k])))
    print("LINKCHECK", "OK" if total == 0 else "FAILED", "refs=%d mismatches=%d" % (refs, total))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
