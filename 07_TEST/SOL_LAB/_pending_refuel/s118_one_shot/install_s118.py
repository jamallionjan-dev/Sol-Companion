import hashlib, os, shutil, time
ROOT = r"C:\Users\JAMAL\Desktop\Sol"
LAB = os.path.join(ROOT, "07_TEST", "SOL_LAB")
PROFILE = os.path.join(LAB, "profile", "Zomboid")
LOG = os.path.join(PROFILE, "Logs", "2026-11-12_17-28_DebugLog.txt")
CLIENT = os.path.join(PROFILE, "mods", "Sol_LAB", "42", "media", "lua", "client")
TARGET = os.path.join(PROFILE, "mods", "Sol_LAB", "42", "media", "java", "SolCombined.jar")
SOURCE = os.path.join(ROOT, "07_TEST", "SOL_LAB", "_pending_refuel", "s118_one_shot", "client")
CANDIDATE = os.path.join(ROOT, "07_TEST", "SOL_LAB", "_pending_refuel", "s118_one_shot", "build_s118_sol_hitplan_candidate", "SolCombined.jar")
BACKUP = os.path.join(LAB, "_backup", "20261112_before_s118_one_shot")
BASE_SHA = "bacce36b672718cc450b20ea3970094f0854e93df75875e28de11c743e1285fc"
CANDIDATE_SHA = "70048f57059624c1a9ccda3db68f06d3899d5c44a59df1edcd73f40c8982fcab"
def sha(p):
    x=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1048576),b""): x.update(b)
    return x.hexdigest()
if not os.path.isfile(LOG) or time.time()-os.path.getmtime(LOG)<60: raise SystemExit("LAB log is active/recent; refusing install")
if not os.path.isfile(TARGET) or sha(TARGET)!=BASE_SHA: raise SystemExit("LAB jar is not the expected s117 base")
if not os.path.isfile(CANDIDATE) or sha(CANDIDATE)!=CANDIDATE_SHA: raise SystemExit("candidate jar hash mismatch")
for n in ("SolAuthority.lua","SolHeadshot.lua"):
    src=os.path.join(SOURCE,n); dst=os.path.join(CLIENT,n)
    if not os.path.isfile(src) or not os.path.isfile(dst): raise SystemExit("missing Lua source/target: "+n)
    text=open(src,encoding="utf-8-sig").read()
    if n=="SolAuthority.lua" and text.count('"sol_one_shot_kill"')!=1: raise SystemExit("switch registration mismatch")
    if n=="SolHeadshot.lua" and "solHeadshotSetLethal" not in text: raise SystemExit("Lua lethal setter not wired")
if os.path.exists(BACKUP): raise SystemExit("backup exists; refusing overwrite")
os.makedirs(BACKUP)
for n in ("SolCombined.s117.jar","SolAuthority.s117.lua","SolHeadshot.s117.lua","SolFixes_LAB.s117.txt"):
    src={"SolCombined.s117.jar":TARGET,"SolAuthority.s117.lua":os.path.join(CLIENT,"SolAuthority.lua"),"SolHeadshot.s117.lua":os.path.join(CLIENT,"SolHeadshot.lua"),"SolFixes_LAB.s117.txt":os.path.join(PROFILE,"Lua","SolFixes_LAB.txt")}[n]
    shutil.copy2(src,os.path.join(BACKUP,n))
    if not os.path.isfile(os.path.join(BACKUP,n)): raise SystemExit("backup failed: "+n)
for n in ("SolAuthority.lua","SolHeadshot.lua"):
    staged=os.path.join(CLIENT,n)+".s118.tmp"
    shutil.copyfile(os.path.join(SOURCE,n),staged)
    os.replace(staged,os.path.join(CLIENT,n))
jar_tmp=TARGET+".s118.tmp"
shutil.copyfile(CANDIDATE,jar_tmp)
if sha(jar_tmp)!=CANDIDATE_SHA: os.remove(jar_tmp); raise SystemExit("staged jar hash mismatch")
os.replace(jar_tmp,TARGET)
if sha(TARGET)!=CANDIDATE_SHA: raise SystemExit("installed jar hash mismatch")
SW=os.path.join(PROFILE,"Lua","SolFixes_LAB.txt")
s=open(SW,encoding="ascii").read().splitlines()
s=[x for x in s if not x.startswith("sol_one_shot_kill=")]
s.append("sol_one_shot_kill=on")
tmp=SW+".s118.tmp"
with open(tmp,"w",encoding="ascii",newline="\n") as f: f.write("\n".join(s)+"\n")
os.replace(tmp,SW)
print("installed s118 into SOL_LAB only")
print("backup="+BACKUP)
print("candidate_sha256="+sha(TARGET))
print("switch=sol_one_shot_kill=on")
