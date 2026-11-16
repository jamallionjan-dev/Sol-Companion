"""s159 under_cloth: Sol's chest takes the accepted "under cloth" shape while a painted top covers it; bare she is unchanged.
usage: apply_s159_under_cloth.py <mod 42 dir> <SolFixes_LAB.txt> [off]
- media/java/SolCombined.jar is replaced by the trial jar built by 05_TOOLS/sol_cloth/build_undercloth_jar.py
  (the same jar plus localplayerbody/SolUnderCloth.class, undercloth-L.bin and four patched methods; see PatchUnderCloth.java).
  The jar it replaces is kept beside this script as SolCombined.before_s159.jar (not inside the mod folder).
- media/lua/client/SolAuthority.lua: registers the switch name
- the switch file: under_cloth=on (the Java side reads this line itself, once per game session)
"off": only writes under_cloth=off (the jar stays; with the switch off both hooks return at once).
"kept" when already applied. Never run while the game is running. ZombieBuddy asks Jamal to approve the changed jar."""
import hashlib, os, re, shutil, sys, zipfile
MOD, SW = sys.argv[1], sys.argv[2]
OFF = len(sys.argv) > 3 and sys.argv[3] == "off"
HERE = os.path.dirname(os.path.abspath(__file__))
TRIAL = os.path.normpath(os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_cloth", "out", "build", "SolCombined.jar"))
NL, CRLF = chr(10), chr(13) + chr(10)


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def switch(value):
    t = open(SW, encoding="utf-8", newline="").read()
    line = "under_cloth=" + value
    if re.search(r"(?m)^under_cloth=", t):
        new = re.sub(r"(?m)^under_cloth=\w*", line, t)
        if new == t: print("kept switch " + line); return
        open(SW, "w", encoding="utf-8", newline="").write(new)
    else:
        with open(SW, "a", encoding="utf-8", newline="") as f: f.write(("" if t.endswith((NL, CRLF)) else CRLF) + line + CRLF)
    print("switch " + line)


if OFF:
    switch("off"); print("s159 under_cloth switched off"); sys.exit(0)
jar = os.path.join(MOD, "media", "java", "SolCombined.jar")
if not os.path.isfile(TRIAL): raise RuntimeError("build the trial jar first: " + TRIAL)
names = zipfile.ZipFile(TRIAL).namelist()
if "localplayerbody/SolUnderCloth.class" not in names or "localplayerbody/undercloth-L.bin" not in names:
    raise RuntimeError("the trial jar is not an under-cloth jar")
if sha(jar) == sha(TRIAL):
    print("kept SolCombined.jar")
else:
    if "localplayerbody/SolUnderCloth.class" in zipfile.ZipFile(jar).namelist():
        print("replacing an earlier under-cloth jar")
    else:
        keep = os.path.join(HERE, "SolCombined.before_s159.jar")
        if not os.path.exists(keep): shutil.copy2(jar, keep); print("kept the jar it replaces: " + os.path.basename(keep))
    shutil.copy2(TRIAL, jar)
    print("installed SolCombined.jar " + sha(jar)[:12])
auth = os.path.join(MOD, "media", "lua", "client", "SolAuthority.lua")
text = open(auth, encoding="utf-8", newline="").read()
if '"under_cloth"' in text:
    print("kept SolAuthority.lua")
else:
    nl = CRLF if CRLF in text else NL
    old = "A.FIXES = {" + nl
    if text.count(old) != 1: raise RuntimeError(("SolAuthority.lua", "expected one A.FIXES", text.count(old)))
    text = text.replace(old, old + '    "under_cloth",        -- s159: her chest under a painted top (read by SolCombined.jar itself; needs a restart)' + nl)
    open(auth, "w", encoding="utf-8", newline="").write(text)
    print("edited SolAuthority.lua")
switch("on")
print("s159 under_cloth applied")
