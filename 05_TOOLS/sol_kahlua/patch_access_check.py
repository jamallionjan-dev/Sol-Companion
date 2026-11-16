"""A ZombieBuddy patch body is copied into the game's class, so whatever it calls in our jar must be public on a public class.
Read-only. usage: patch_access_check.py <our jar>  (exit 0 = fine, 1 = not)"""
import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from linkcheck import parse

ACC_PUBLIC = 1
PATCH = "Lme/zed_0xff/zombie_buddy/Patch;"


def flags(b):
    """(class flags, {(name, desc): flags})"""
    cp = parse(b)[0]
    n = struct.unpack(">H", b[8:10])[0]
    i, k = 10, 1
    while k < n:
        t = b[i]
        if t == 1:
            i += 3 + struct.unpack(">H", b[i + 1:i + 3])[0]
        elif t in (3, 4, 9, 10, 11, 12, 17, 18):
            i += 5
        elif t in (5, 6):
            i += 9
            k += 1
        elif t in (7, 8, 16, 19, 20):
            i += 3
        elif t == 15:
            i += 4
        k += 1
    u2 = lambda p: struct.unpack(">H", b[p:p + 2])[0]
    u4 = lambda p: struct.unpack(">I", b[p:p + 4])[0]
    cls = u2(i)
    i += 6 + 2 + 2 * u2(i + 6)
    out = {}
    for _ in range(2):
        c = u2(i)
        i += 2
        for _ in range(c):
            out[(cp[u2(i + 2)][1], cp[u2(i + 4)][1])] = u2(i)
            a = u2(i + 6)
            i += 8
            for _ in range(a):
                i += 6 + u4(i + 2)
    return cls, out


def main(path):
    classes, parsed = {}, {}
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.endswith(".class"):
                b = z.read(n)
                classes[n[:-6]] = flags(b)
                parsed[n[:-6]] = parse(b)[0]
    bad, patches = [], 0
    for name, cp in parsed.items():
        if not any(e and e[0] == "u" and e[1] == PATCH for e in cp):
            continue
        patches += 1
        for e in cp:
            if not e or e[0] not in (9, 10, 11):
                continue
            owner = cp[cp[e[1]][1]][1]
            if owner == name or owner not in classes:
                continue
            nt = cp[e[2]]
            member = (cp[nt[1]][1], cp[nt[2]][1])
            cf, mf = classes[owner]
            if not cf & ACC_PUBLIC:
                bad.append("%s calls %s: that class is not public" % (name, owner))
            elif member in mf and not mf[member] & ACC_PUBLIC:
                bad.append("%s calls %s.%s%s: not public" % (name, owner, member[0], member[1]))
    for b in sorted(set(bad)):
        print("  " + b)
    print("PATCH ACCESS", "OK" if not bad else "FAILED", "patches=%d problems=%d" % (patches, len(set(bad))))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
