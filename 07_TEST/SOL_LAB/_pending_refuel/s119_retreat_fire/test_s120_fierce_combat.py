import os, sys
from lupa import LuaRuntime
client = os.path.abspath(sys.argv[1])
L = LuaRuntime(unpack_returned_tuples=True)
compile_lua = L.eval('function(s) local f,e=load(s); return f~=nil,e end')
for name in ('SCCombat.lua','SolShootDiscipline.lua','SolAuthority.lua'):
    ok, err = compile_lua(open(os.path.join(client,name),encoding='utf-8').read())
    assert ok, f'{name}: {err}'
L.execute('''
SW={shooting_discipline=true,grounded_fire=true,fierce_fast_react=true}
PLAN='fierce'; NOW=0; getTimestampMs=function() return NOW end
SolAuthority={on=function(n) return SW[n]==true end}
SolCombatPlans={current=function() return PLAN end}
LOG={}; print=function(s) LOG[#LOG+1]=tostring(s) end
SurvivorCompanion={GameplayUtil={move=function(a,m,i) a.aiming=true; a.moving=false; return true,'ok' end}}
function gun()
 local x={mode='Auto'}
 function x:getMaxSightRange() return 10 end
 function x:getAimingTime() return 40 end
 function x:getFireMode() return self.mode end
 function x:setFireMode(m) self.mode=m end
 function x:getFireModePossibilities() return {size=function() return 2 end,get=function(_,i) return i==0 and 'Auto' or 'Single' end} end
 return x
end
function actor()
 local a={x=0,y=0,delay=40,moved=0,moving=false,aiming=false}
 function a:getX() return self.x end; function a:getY() return self.y end
 function a:getAimingDelay() return self.delay end; function a:getBeenMovingFor() return self.moved end
 function a:isMoving() return self.moving end; function a:isAiming() return self.aiming end
 return a
end
function zombie(d,down,attack)
 local z={x=d,y=0,dead=false,down=down}
 function z:getX() return self.x end; function z:getY() return self.y end
 function z:isDead() return self.dead end; function z:isOnFloor() return self.down end
 function z:isProne() return false end; function z:isCrawling() return false end
 return z
end
function rec(z,d,extra) local r={actor=z,distance=d,distanceSq=d*d}; for k,v in pairs(extra or {}) do r[k]=v end; return r end
''')
L.execute(open(os.path.join(client,'SolShootDiscipline.lua'),encoding='utf-8').read())
checks = L.eval('''function()
 local M=SolShootDiscipline
 local a,z,g=actor(),zombie(2,true,false),gun()
 local w={item=g,equipped=true,ranged=true,ammo=8,range=30}
 local t=rec(z,2,{grounded=true,visible=true,obstructed=false})
 local acts={{kind='shoot',score=140,solGroundedFire=true}}
 M.shape(a,nil,{threats={}},t,w,nil,acts,2,nil)
 local fierce_shape=acts[1].kind=='shoot'
 PLAN='smart'; acts={{kind='shoot',score=140,solGroundedFire=true}}
 M.shape(a,nil,{threats={}},t,w,nil,acts,2,nil)
 local other_shape=acts[1].kind=='hold_range' and acts[1].sdHold=='target_down'
 PLAN='fierce'; a,z,g=actor(),zombie(2,true,false),gun(); w={item=g,equipped=true,ranged=true,ammo=8,range=30}; t=rec(z,2,{grounded=true,visible=true,obstructed=false})
 local h1=M.gate(a,nil,{}, {threats={}},t,w,'aim_settled',0)
 local h2=M.gate(a,nil,{}, {threats={}},t,w,'aim_settled',200)
 local downed_gate=h1==true and h2==false
 a,z,g=actor(),zombie(5,false,true),gun(); w={item=g,equipped=true,ranged=true,ammo=8,range=30}; t=rec(z,5,{attacking=true,visible=true,obstructed=false})
 local f1=M.gate(a,nil,{}, {threats={}},t,w,'aim_settled',1000)
 local f2=M.gate(a,nil,{}, {threats={}},t,w,'aim_settled',1249)
 local f3=M.gate(a,nil,{}, {threats={}},t,w,'aim_settled',1250)
 local quick=f1==true and f2==true and f3==false
 return fierce_shape,other_shape,downed_gate,quick
end''')
results = checks()
labels=('fierce allows safe nearby downed shot','non-fierce retains physical finisher','fierce downed shot caps aim wait at 200ms','urgent fierce reaction fires by 250ms')
for label, ok in zip(labels,results): print(('PASS ' if ok else 'FAIL ')+label)
if not all(results): raise SystemExit(1)
print('PASS Lua parse for SCCombat, SolShootDiscipline, SolAuthority')
