"""Offline tests for the switchable, read-only s111 damage probe."""
import os
import sys
import tempfile
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51

base = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
tmp = tempfile.mkdtemp(prefix="s111_probe_")
profile = os.path.join(tmp, "profile", "Zomboid")
client = os.path.join(profile, "mods", "Sol_LAB", "42", "media", "lua", "client")
os.makedirs(client)
for name in os.listdir(base):
    if name.endswith(".lua"):
        shutil.copy2(os.path.join(base, name), client)
switchdir = os.path.join(profile, "Lua")
os.makedirs(switchdir)
with open(os.path.join(switchdir, "SolFixes_LAB.txt"), "w", encoding="utf-8") as h:
    h.write("shooting_discipline=on\r\ndecision_load_throttle=on\r\n")
proc = subprocess.run([sys.executable, os.path.join(HERE, "apply_s111_damage_probe.py"), client], capture_output=True, text=True)
proc2 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s111_damage_probe.py"), client], capture_output=True, text=True)
fails = []
def ck(label, ok):
    print(("PASS " if ok else "FAIL ") + label)
    if not ok: fails.append(label)
ck("installer applies", proc.returncode == 0 and "applied" in proc.stdout)
ck("installer idempotent", proc2.returncode == 0 and "edited" not in proc2.stdout)
probe = open(os.path.join(client, "SolDamageProbe.lua"), encoding="utf-8").read()
auth = open(os.path.join(client, "SolAuthority.lua"), encoding="utf-8").read()
ck("switch listed", '"shooting_damage_probe"' in auth)
ck("probe is ASCII", all(ord(c) < 128 for c in probe))
L = lua51.LuaRuntime()
compile_lua = L.eval("function(s) local f, e = loadstring(s); return f ~= nil, e end")
ok, err = compile_lua(probe)
ck("probe compiles in Lua 5.1", ok)
L.execute('''
SW={shooting_damage_probe=true}; SolAuthority={on=function(n) return SW[n] == true end}
LOG={}; print=function(s) LOG[#LOG+1]=tostring(s) end
Events={OnHitZombie={Add=function(f) Events.OnHitZombie.fn=f end},OnTick={Add=function(f) Events.OnTick.fn=f end}}
function weapon() local w={}; function w:isRanged() return true end; function w:getFullType() return "Base.M4A1" end; return w end
function actor(localPlayer) local a={localPlayer=localPlayer}; function a:isLocalPlayer() return self.localPlayer end; return a end
function zombie(hp) local z={hp=hp}; function z:getHealth() return self.hp end; return z end
SolShootDiscipline={_isSol=function(a) return a.kind == "sol" end}
''')
L.execute(probe)
ev = L.eval
ck("Sol hit pre/post exact health delta", ev('''(function()
 local z=zombie(2.0); local a=actor(false); a.kind="sol"
 assert(SolDamageProbe.onHit(z,a,"Torso_Upper",weapon())); z.hp=1.375
 SolDamageProbe.flush(); return string.find(LOG[#LOG], "source=Sol") ~= nil
   and string.find(LOG[#LOG], "pre=2.00000 post=1.37500 damage=0.62500") ~= nil
 end)()'''))
ck("player hit is separately attributed", ev('''(function()
 local z=zombie(1.375); local a=actor(true); assert(SolDamageProbe.onHit(z,a,"Torso_Upper",weapon()))
 z.hp=0.875; SolDamageProbe.flush(); return string.find(LOG[#LOG], "source=Jamal") ~= nil
   and string.find(LOG[#LOG], "damage=0.50000") ~= nil end)()'''))
ck("switch off does not record hits", ev('''(function()
 SW.shooting_damage_probe=false; local before=#SolDamageProbe.pending; local z=zombie(2); local a=actor(true)
 local accepted=SolDamageProbe.onHit(z,a,"Torso_Upper",weapon()); SW.shooting_damage_probe=true
 return accepted == false and #SolDamageProbe.pending == before end)()'''))
ck("empty tick does no scan work", ev('''(function()
 SolDamageProbe.pending={}; local n=SolDamageProbe.flush(); return n == 0 and #SolDamageProbe.pending == 0 end)()'''))
switches = open(os.path.join(switchdir, "SolFixes_LAB.txt"), encoding="utf-8").read()
ck("test lab switch is on", "shooting_damage_probe=on" in switches)
ck("source contains no health or weapon mutations", all(x not in probe for x in ("setHealth", "setMinDamage", "setMaxDamage", "setDamage")))
print("%d passed, %d failed" % (10-len(fails), len(fails)))
sys.exit(1 if fails else 0)
