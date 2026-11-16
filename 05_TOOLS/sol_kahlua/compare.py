"""Runs probe.lua on the game's Kahlua and on lupa (the offline tests' Lua) and prints every behaviour that differs."""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid"
JAR = os.path.join(GAME, "projectzomboid.jar")
JAVA = os.path.join(GAME, "jre64", "bin", "java.exe")
BUILD = os.path.join(HERE, "build")
JHOME = os.path.join(os.environ.get("TEMP", HERE), "sol_kahlua_home")
def kahlua(*args):
    cmd = [JAVA, "-Duser.home=" + JHOME, "-Djava.awt.headless=true", "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-cp", BUILD + os.pathsep + JAR, "KahluaCheck"] + list(args)
    return subprocess.run(cmd, cwd=GAME, capture_output=True, encoding="utf-8", errors="replace", timeout=300)
if __name__ == "__main__":
    r = kahlua("probe", os.path.join(HERE, "probe.lua"))
    open(os.path.join(HERE, "probe_kahlua.txt"), "w", encoding="utf-8").write(r.stdout + r.stderr)
    from lupa import lua51
    out = []
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.globals().print = lambda *a: out.append("\t".join(str(x) for x in a))
    L.execute(open(os.path.join(HERE, "probe.lua"), encoding="utf-8").read())
    open(os.path.join(HERE, "probe_lupa.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    def parse(lines):
        d = {}
        for l in lines:
            if " => " in l: k, v = l.split(" => ", 1); d[k] = v
            elif l.startswith(("GLOBAL ", "LIB ")): p = l.split(" ", 2); d[p[0] + " " + p[1]] = p[2] if len(p) > 2 else ""
        return d
    k, l = parse(r.stdout.splitlines()), parse(out)
    print("kahlua probes:", len(k), "lupa probes:", len(l), "ended:", "END" in r.stdout)
    for n in l:
        if k.get(n) != l[n]:
            print("%-22s K: %s\n%-22s L: %s" % (n, str(k.get(n))[:200], "", l[n][:200]))
