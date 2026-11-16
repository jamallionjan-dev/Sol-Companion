import os
root=r"C:\Users\JAMAL\Desktop\Sol"
stage=os.path.join(root,"07_TEST","SOL_LAB","_pending_refuel","s118_one_shot")
java=open(os.path.join(root,"05_TOOLS","sol_nav_java","localplayerbody","SolHeadshot.java"),encoding="utf-8").read()
auth=open(os.path.join(stage,"client","SolAuthority.lua"),encoding="utf-8-sig").read()
lua=open(os.path.join(stage,"client","SolHeadshot.lua"),encoding="utf-8-sig").read()
sw=open(os.path.join(root,"07_TEST","SOL_LAB","profile","Zomboid","Lua","SolFixes_LAB.txt"),encoding="ascii").read()
checks={"lethal hook runs after CombatManager processHit": "finishCombatHit(attacker, target)" in java and 'methodName = "processHit"' in java,
"lethality restricted to native Sol companion firearm": "shouldOneShotKill(oneShotKills" in java and '"survivorcompanion.bridge.SCNativeCompanion".equals(actorClass)' in java,
"death uses engine Kill overload with weapon and attacker": "target.Kill(current.weapon, attacker)" in java,
"lethal toggle registered exactly once": auth.count('"sol_one_shot_kill"')==1,
"Lua sync applies lethal authority toggle": "solHeadshotSetLethal" in lua and 'authority.on("sol_one_shot_kill")' in lua,
"disabling headshots resets the native hit plan to single": 'if not enabled and type(modeSetter) == "function" then pcall(modeSetter, "single") end' in lua,
"LAB switch is enabled": sw.count("sol_one_shot_kill=on")==1,
"weapon damage stats remain untouched": "setMinDamage" not in java and "setMaxDamage" not in java}
for k,v in checks.items(): print(("PASS " if v else "FAIL ")+k)
if not all(checks.values()): raise SystemExit(1)
