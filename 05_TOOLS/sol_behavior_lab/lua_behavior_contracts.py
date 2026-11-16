#!/usr/bin/env python3
"""Runs small behavioral contracts against the REAL Living Fellows Lua files via lupa Lua 5.1.
This proves Lua policy/branch behavior, not Java engine/runtime behavior.
"""
from pathlib import Path
import sys

try:
    from lupa import lua51
except Exception as exc:
    print(f"BLOCKED  Lua behavior contracts -- lupa unavailable: {exc}")
    raise SystemExit(2)

lua_root = Path(sys.argv[1])
client = lua_root / "client"
fails=[]

def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ")+name+(f" -- {detail}" if detail else ""))
    if not cond: fails.append(name)

def lua_pair(value):
    """Normalize a Lua call that may return one value or multiple values via lupa."""
    if isinstance(value, tuple):
        return (value[0] if len(value) > 0 else None, value[1] if len(value) > 1 else None)
    return value, None

# ---- Logistics + Encounter: actual policy functions ----
lua=lua51.LuaRuntime(unpack_returned_tuples=True)
g=lua.globals()
lua.execute(r'''
SurvivorCompanion={}
local SC=SurvivorCompanion
__carried=0; __usable=0
SC.GameplayUtil={
  call=function(obj,name,...)
    if type(obj)=="table" and type(obj[name])=="function" then return obj[name](obj,...),true end
    return nil,false
  end,
  each=function(list,limit,fn) if type(list)=="table" then for i=1,math.min(#list,limit or #list) do if fn(list[i])==false then break end end end end,
  characterStatValue=function() return 0 end,
  config=function() return nil end,
  nowMs=function() return 1000 end,
  itemType=function(item) return item and item.type end,
  itemWeight=function() return 1 end,
  inventory=function() return {} end,
  inventoryItemsDeep=function() return {},{} end,
  inventoryContains=function() return true end,
  instanceOf=function() return false end,
  stableHash=function() return 1 end,
  itemName=function(item) return item and item.type or "item" end,
}
SC.Combat={ weaponAvailability=function() return __carried,__usable end }
function require() return true end
''')
for name in ("SCLogistics.lua","SCEncounter.lua"):
    lua.execute((client/name).read_text(encoding="utf-8-sig"))
SC=g.SurvivorCompanion
actor=lua.table()
audit=lua.table_from({"counts": lua.table_from({}), "role":"generalist", "capacity":20, "weight":0, "hardRatio":0.9, "softRatio":0.7})
g.__carried=0; g.__usable=0
weapon_tier=SC.Logistics.needTier(actor,"weapon",audit,False)
check("B1 unarmed survivor makes weapon desperate", weapon_tier==SC.Logistics.TIER.desperate, str(weapon_tier))
g.__carried=1; g.__usable=1
ammo_tier=SC.Logistics.needTier(actor,"ammunition",audit,False)
check("B2 firearm carrier makes ammunition important", ammo_tier==SC.Logistics.TIER.important, str(ammo_tier))
g.__carried=0; g.__usable=0
wanted=SC.Encounter._wantedCategories(actor,lua.table(),lua.table())
check("B3 Encounter implicitly searches for weapon when unarmed", wanted["weapon"] is True)
cmd=lua.table_from({"scavengeRequestedCategory":"ammunition"})
wanted2=SC.Encounter._wantedCategories(actor,cmd,lua.table())
check("B4 explicit ammunition request reaches scavenger category", wanted2["ammunition"] is True)

# ---- Driving: actual ownership boundary and route encoder ----
lua2=lua51.LuaRuntime(unpack_returned_tuples=True)
g2=lua2.globals()
lua2.execute(r'''
SurvivorCompanion={}
local SC=SurvivorCompanion
__driveStartCalls=0
__sameVehicle=false
vehicle={}
actor={ getVehicle=function(self) return vehicle end, getInventory=function(self) return {haveThisKeyId=function() return nil end} end }
player={ getVehicle=function(self) if __sameVehicle then return vehicle else return nil end end }
function getSpecificPlayer(i) return player end
SC.GameplayUtil={nowMs=function() return 1000 end}
SC.Actor={isCompanion=function(a) return a==actor end}
SC.Vehicle={boardDriver=function() return true,"driver_boarded" end}
SC.ActionSupervisor={
 Priority={TRAVEL=10},
 begin=function(a,o) return {actor=a},"ok" end,
 transition=function() return true,"ok" end,
 isCurrent=function() return true end,
 cancel=function() return true,"cancelled" end,
}
SC.Call={
 method=function(obj,name,...)
   if obj==vehicle and name=="getDriver" then return true,actor end
   if obj==vehicle and name=="getKeyId" then return true,1 end
   if obj==vehicle and name=="getMaxPassengers" then return true,4 end
   if obj==vehicle and name=="getCharacter" then return true,nil end
   if type(obj)=="table" and type(obj[name])=="function" then return true,obj[name](obj,...) end
   return false,nil
 end,
 static=function(api,name,...)
   if name=="driveStatus" then local args={...}; local out=args[2]; out.active=false; out.reason=""; return true,true end
   if name=="driveStart" then __driveStartCalls=__driveStartCalls+1; return true,true end
   if name=="getLastFailure" then return true,"" end
   if name=="driveStop" then return true,true end
   return true,true
 end,
}
SCBridge={driveStart=true,driveSet=true,driveStop=true,driveStatus=true,scanLane=true,driveFollow=true,driveApproach=true,driveTurnAround=true}
''')
lua2.execute((client/"SCDriving.lua").read_text(encoding="utf-8-sig"))
D=g2.SurvivorCompanion.Driving
route=lua2.table_from([lua2.table_from({"x":1,"y":2,"width":5}),lua2.table_from({"x":3,"y":4,"width":5})])
text,why=lua_pair(D.routeText(route))
check("B5 Driving encodes bounded native route", text=="1.00,2.00,5.0;3.00,4.00,5.0", str(text))
g2.__sameVehicle=True
ok,reason=lua_pair(D.start(g2.actor,lua2.table_from({"x":100,"y":100,"z":0})))
check("B6 native ownership refuses when local player already aboard", ok is False and reason=="player_aboard", str(reason))
check("B7 refused ownership never calls native driveStart", int(g2.__driveStartCalls)==0, str(g2.__driveStartCalls))

print("SUMMARY %s (%d failed)" % ("ALL PASS" if not fails else "FAIL", len(fails)))
raise SystemExit(1 if fails else 0)
