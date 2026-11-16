"""Offline tests for s116's per-Sol burst hit plan and LAB installer."""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from kahlua_env import lua51

ROOT = r"C:\Users\JAMAL\Desktop\Sol"
HERE = os.path.dirname(os.path.abspath(__file__))
LAB_CLIENT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "07_TEST", "SOL_LAB", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
FAIL = []
PASS = 0

def ck(name, ok):
    global PASS
    print(("PASS " if ok else "FAIL ") + name)
    if ok:
        PASS += 1
    else:
        FAIL.append(name)

def main():
    java = open(os.path.join(ROOT, "05_TOOLS", "sol_nav_java", "localplayerbody", "SolHeadshot.java"), encoding="utf-8").read()
    checks = {
        "fire-mode part override is scoped to Sol companion": '"survivorcompanion.bridge.SCNativeCompanion".equals(actorClass)' in java,
        "physical part plan is restricted to zombie targets": "target instanceof IsoZombie" in java,
        "chest plan uses Spine and upper torso": "BODYPART_SPINE, BodyPartType.Torso_Upper" in java,
        "head plan uses Head and Head": "BODYPART_HEAD, BodyPartType.Head" in java,
        "burst plan is two chest then one head": "(shot + 1) % 3" in java and "if (shot < 2)" in java,
        "both physical selection paths use the chosen plan": "current.shotPlan.physicalPart.ordinal()" in java and "return current.shotPlan.physicalPart;" in java,
        "native damage uses the selected damage part": "return current.shotPlan.damagePart;" in java,
        "native fire-mode setter is exposed": 'name = "solHeadshotSetFireMode"' in java,
        "weapon damage and critical values are not overwritten": "setCriticalHit" not in java and "setMinDamage" not in java and "setMaxDamage" not in java,
    }
    for name, ok in checks.items():
        ck(name, ok)

    candidate = os.path.join(HERE, "s118_one_shot", "build_s118_sol_hitplan_candidate", "SolCombined.jar")
    if not os.path.isfile(candidate):
        ck("candidate jar exists for installer replay", False)
        print("%d passed, %d failed" % (PASS, len(FAIL)))
        return 1

    with tempfile.TemporaryDirectory(prefix="sol_s116_install_") as temp:
        profile = os.path.join(temp, "Zomboid")
        client = os.path.join(profile, "mods", "Sol_LAB", "42", "media", "lua", "client")
        os.makedirs(client)
        os.makedirs(os.path.join(profile, "Lua"))
        os.makedirs(os.path.join(profile, "mods", "Sol_LAB", "42", "media", "java"))
        shutil.copyfile(os.path.join(LAB_CLIENT, "SolShootDiscipline.lua"), os.path.join(client, "SolShootDiscipline.lua"))
        shutil.copyfile(os.path.join(LAB_CLIENT, "SolAuthority.lua"), os.path.join(client, "SolAuthority.lua"))
        with open(os.path.join(profile, "Lua", "SolFixes_LAB.txt"), "w", encoding="ascii") as f:
            f.write("sol_headshots=on\n")
        target_jar = os.path.join(profile, "mods", "Sol_LAB", "42", "media", "java", "SolCombined.jar")
        with open(target_jar, "wb") as f:
            f.write(b"old-lab-jar")
        apply = os.path.join(HERE, "apply_s116_chest_head.py")
        first = subprocess.run([sys.executable, apply, client, candidate], text=True, capture_output=True)
        ck("installer wires hit-plan mode and updates isolated jar", first.returncode == 0 and "native hit-plan jar" in first.stdout)
        digest1 = hashlib.sha256(open(target_jar, "rb").read()).hexdigest()
        second = subprocess.run([sys.executable, apply, client, candidate], text=True, capture_output=True)
        digest2 = hashlib.sha256(open(target_jar, "rb").read()).hexdigest()
        ck("installer is idempotent on repeat", second.returncode == 0 and digest1 == digest2)
        updated = open(os.path.join(client, "SolShootDiscipline.lua"), encoding="ascii").read()
        ck("burst/single gate is connected to the native hit plan", "-- s116: route the resolved shot mode to native hit-part plan" in updated and 'hitModeSetter, burst and "burst" or "single"' in updated)
        ck("installer leaves Sol headshot switch enabled", open(os.path.join(profile, "Lua", "SolFixes_LAB.txt"), encoding="ascii").read() == "sol_headshots=on\n")

        runtime = lua51.LuaRuntime(unpack_returned_tuples=True)
        compile_lua = runtime.eval("function(s) local f,e=loadstring(s); return f~=nil,e end")
        compiled, err = compile_lua(updated)
        ck("patched discipline compiles in Lua 5.1/Kahlua syntax", compiled)
        runtime.globals().source = updated
        runtime.execute('''
SW={shooting_discipline=true,sol_headshots=true}; MODES={}; NOW=0
getTimestampMs=function() return NOW end
print=function(_) end
SolAuthority={on=function(n) return SW[n]==true end}
solHeadshotSetFireMode=function(mode) MODES[#MODES+1]=mode end
SurvivorCompanion={GameplayUtil={move=function(a,m,i) a.aiming=true; a.moving=false; return true,"ok" end}}
function actor()
 local a={x=0,y=0,delay=0,moved=0,moving=false,aiming=true}
 function a:getX() return self.x end; function a:getY() return self.y end
 function a:getAimingDelay() return self.delay end; function a:getBeenMovingFor() return self.moved end
 function a:isMoving() return self.moving end; function a:isAiming() return self.aiming end
 return a
end
function zombie(x) local z={x=x,y=0,dead=false}
 function z:getX() return self.x end; function z:getY() return self.y end
 function z:isDead() return self.dead end; function z:isOnFloor() return false end
 function z:isProne() return false end; function z:isCrawling() return false end
 return z end
function gun() local g={mode="Auto"}
 function g:isRanged() return true end; function g:getFireMode() return self.mode end
 function g:setFireMode(m) self.mode=m end
 function g:getFireModePossibilities() return {size=function() return 2 end,get=function(_,i) return i==0 and "Auto" or "Single" end} end
 function g:getAimingTime() return 40 end; function g:getMaxSightRange() return 10 end
 function g:getFullType() return "Base.TestRifle" end
 return g end
''')
        runtime.execute(updated)
        mode_checks = runtime.eval('''function()
 local a,g=actor(),gun(); local zs={zombie(2),zombie(3),zombie(4)}
 local threats={}; for i,z in ipairs(zs) do threats[i]={actor=z,distance=i+1} end
 local target=threats[1]; local w={item=g,ranged=true,equipped=true,ammo=10,range=20}
 SolShootDiscipline.gate(a,nil,{}, {threats=threats},target,w,"aim_settled",0)
 SolShootDiscipline.gate(a,nil,{}, {threats=threats},target,w,"aim_settled",300)
 local burst=MODES[#MODES]=="burst"
 SolShootDiscipline.actors=setmetatable({}, {__mode="k"}); SolShootDiscipline.targets=setmetatable({}, {__mode="k"}); MODES={}
 a,g=actor(),gun(); local z=zombie(4); w={item=g,ranged=true,equipped=true,ammo=10,range=20}
 local t={actor=z,distance=4}; local h={threats={t}}
 SolShootDiscipline.gate(a,nil,{},h,t,w,"aim_settled",500)
 SolShootDiscipline.gate(a,nil,{},h,t,w,"aim_settled",900)
 local single=MODES[#MODES]=="single"
 return burst,single
end''')()
        ck("grouped shots select burst chest/chest/head plan", mode_checks[0])
        ck("isolated shot selects single head plan", mode_checks[1])

    print("%d passed, %d failed" % (PASS, len(FAIL)))
    return 1 if FAIL else 0

if __name__ == "__main__":
    sys.exit(main())
