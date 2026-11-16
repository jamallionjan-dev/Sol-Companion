"""s159: builds a patched TRIAL copy of SolCombined.jar with SolUnderCloth (nothing is installed).
usage: python build_undercloth_jar.py [input SolCombined.jar]  -> out/build/SolCombined.jar
Steps: shape file (out/undercloth-L.bin from out/undercloth_L.npz), javac SolUnderCloth against the game's classes,
javac + run PatchUnderCloth with ZombieBuddy.jar (shaded ASM), then the offline test UnderClothTest."""
import os, shutil, struct, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid"
LAB = os.path.join(ROOT, "07_TEST", "SOL_LAB", "profile", "Zomboid", "mods")
JAR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(LAB, "Sol_LAB", "42", "media", "java", "SolCombined.jar")
ZB = os.path.join(LAB, "ZombieBuddy", "libs", "ZombieBuddy.jar")
B = os.path.join(HERE, "out", "build")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if not l.startswith("Note:"))
    if r.returncode != 0: print(out); sys.exit("FAILED: " + " ".join(cmd[:3]))
    return out


def shape(size):
    sys.path.insert(0, HERE)
    import fbx_read as F
    from chest_preview import BODY
    d = np.load(os.path.join(HERE, "out", "undercloth_%s.npz" % size))
    raw = F.meshes(F.read(BODY % ("" if size == "L" else size)))[0]["verts"].astype(">f4"); off = d["offset"].astype(">f4")
    assert raw.shape == off.shape
    p = os.path.join(B, "undercloth-%s.bin" % size)
    with open(p, "wb") as f:
        f.write(struct.pack(">i", len(raw))); f.write(raw.tobytes()); f.write(off.tobytes())
    return p


if os.path.isdir(B): shutil.rmtree(B)
os.makedirs(os.path.join(B, "cls")); os.makedirs(os.path.join(B, "tool")); os.makedirs(os.path.join(B, "test"))
src_jar = os.path.join(B, "SolCombined.in.jar"); shutil.copy(JAR, src_jar)
shapes = [shape("L")]
game_cp = os.pathsep.join([src_jar, os.path.join(GAME, "projectzomboid.jar"), os.path.join(GAME, "*")])
run(["javac", "-nowarn", "-d", os.path.join(B, "cls"), "-cp", game_cp, os.path.join(HERE, "java", "localplayerbody", "SolUnderCloth.java")])
run(["javac", "-nowarn", "-d", os.path.join(B, "tool"), "-cp", ZB, os.path.join(HERE, "java", "PatchUnderCloth.java")])
out_jar = os.path.join(B, "SolCombined.jar")
print(run(["java", "-cp", os.pathsep.join([ZB, os.path.join(B, "tool")]), "PatchUnderCloth", src_jar, out_jar,
           os.path.join(B, "cls", "localplayerbody", "SolUnderCloth.class")] + shapes).strip())
test_src = os.path.join(HERE, "java", "localplayerbody", "UnderClothTest.java")
if os.path.exists(test_src):
    cp = os.pathsep.join([out_jar, os.path.join(GAME, "projectzomboid.jar"), os.path.join(GAME, "*")])
    run(["javac", "-nowarn", "-d", os.path.join(B, "test"), "-cp", cp, test_src])
    print(run(["java", "-cp", os.pathsep.join([os.path.join(B, "test"), cp]), "localplayerbody.UnderClothTest", shapes[0], os.path.join(B, "test_out.bin")]).strip())
print("trial jar:", out_jar, os.path.getsize(out_jar), "bytes (input", os.path.getsize(src_jar), ")")
