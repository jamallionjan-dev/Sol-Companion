"""Sol's per-fix switches as the Mind sees them (s152).

The game reads SolFixes_LAB.txt in the lab copy and SolFixes_MAIN.txt in the main copy (SolAuthority.lua). The Mind used to
read SolFixes_LAB.txt only, so on a normal install (no lab file) every Mind-side switch counted as off: home parking, the
address book's answers, "why did it fail", smart parking, reply-after-result, the short refuel hop.
value(lua_dir, name): True / False when a file names the switch, None when neither does.
A name in SolFixes_LAB.txt wins (the lab, or a hand-made override); otherwise SolFixes_MAIN.txt decides.
Standard library only."""
import os

FILES = ("SolFixes_LAB.txt", "SolFixes_MAIN.txt")
_ON = ("on", "true", "1", "yes")


def _read(path):
    out = {}
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                k, sep, v = line.strip().replace(" ", "").partition("=")
                if sep and k: out[k] = v.lower() in _ON
    except OSError:
        return None
    return out


def value(lua_dir, name):
    for fn in FILES:
        t = _read(os.path.join(lua_dir, fn))
        if t is not None and name in t: return t[name]
    return None


def on(lua_dir, name):
    return value(lua_dir, name) is True
