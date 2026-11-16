#!/usr/bin/env python3
from pathlib import Path
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time

HERE=Path(__file__).resolve().parent
CAPS=json.loads((HERE/'capabilities.json').read_text(encoding='utf-8'))

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='replace')

CONTRACT_PATTERNS={
 'movement.follow': [('client/SCCommands.lua',r'local function handleFollow'),('client/SCNavigation.lua',r'follow_formation')],
 'movement.go_to': [('client/SCAIToolGateway.lua',r'go_to'),('client/SCCommands.lua',r'move_to')],
 'scavenge.world_containers': [('client/SCEncounter.lua',r'local function candidateContainers'),('client/SCEncounter.lua',r'scavengeOffsets'),('client/SCEncounter.lua',r'scoreContainer')],
 'loadout.weapon_need': [('client/SCLogistics.lua',r'function Logistics.needTier'),('client/SCLogistics.lua',r'category == "weapon"'),('client/SCEncounter.lua',r'wanted.weapon = true')],
 'loadout.ammunition_need': [('client/SCLogistics.lua',r'category == "ammunition"'),('client/SCLogistics.lua',r'TIER.important')],
 'combat.weapon_select_equip_reload': [('client/SCCombat.lua',r'local function chooseWeapon'),('client/SCCombat.lua',r'function Combat.equipPreferred'),('client/SCCombat.lua',r'local function hasReloadAmmo'),('client/SCCombat.lua',r'action.kind == "reload"')],
 'combat.target_control': [('client/SCAIToolGateway.lua',r'designate_target'),('client/SCAIToolGateway.lua',r'fire_at_will'),('client/SCAIToolGateway.lua',r'hold_fire')],
 'vehicle.board_driver': [('client/SCVehicle.lua',r'function vehicleService.boardDriver'),('client/SCVehicle.lua',r'intent.driverSeat = true')],
 'vehicle.route_drive': [('client/SCDriving.lua',r'function Driving.drive'),('client/SCDriving.lua',r'driveStart'),('client/SCDriving.lua',r'driveFollow'),('client/SCDriving.lua',r'player_aboard')],
 'vehicle.solo_rescue_drive': [('client/SolGPS.lua',r'G.solo'),('client/SolGPS.lua',r'function U.gpsStart'),('client/SolGPS.lua',r'solo driving')],
 'persistence.identity': [('client/SCPersistence.lua',r'id = saved.id'),('shared/SCRegistry.lua',r'requestedId'),('shared/SCRegistry.lua',r'record.id')],
}

def run(cmd, cwd=None, extra_env=None):
    env=os.environ.copy()
    env['PYTHONIOENCODING']='utf-8'
    if extra_env:
        env.update(extra_env)
    try:
        p=subprocess.run(cmd,cwd=cwd,text=True,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,env=env,timeout=60)
        return p.returncode,p.stdout
    except subprocess.TimeoutExpired as exc:
        out=exc.stdout or ''
        if isinstance(out,bytes): out=out.decode('utf-8','replace')
        return 124,'[TIMEOUT after 60s]\n'+out

def main():
    ap=argparse.ArgumentParser(description='Permanent Sol behavior release gate')
    ap.add_argument('--root', default=r'C:\Users\JAMAL\Desktop\Sol')
    ap.add_argument('--live', default=r'C:\Users\JAMAL\Zomboid\mods\Sol\42')
    ap.add_argument('--behavior', default='emergency_rescue_showcase')
    ap.add_argument('--static-only', action='store_true')
    a=ap.parse_args()
    root=Path(a.root); work=root/'01_WORK'/'Sol'/'42'; lua=work/'media'/'lua'; mind=root/'05_TOOLS'/'sol_mind'; tools=root/'05_TOOLS'; live=Path(a.live)
    failures=[]; blocked=[]; evidence={}
    print('==== SOL BEHAVIOR LAB ====')
    print('behavior='+a.behavior)
    print('work='+str(work))

    required=CAPS['behavior_requirements'].get(a.behavior)
    if not required:
        raise SystemExit('Unknown behavior: '+a.behavior)

    print('==== CAPABILITY SOURCE CONTRACTS ====')
    for cid in required:
        tests=CONTRACT_PATTERNS[cid]; ok=True; detail=[]
        for rel,pat in tests:
            p=lua/rel
            if not p.is_file(): ok=False; detail.append(rel+':MISSING'); continue
            s=p.read_text(encoding='utf-8-sig')
            if not re.search(pat,s,re.M): ok=False; detail.append(rel+':NO_MATCH:'+pat)
        print(('PASS  ' if ok else 'FAIL  ')+cid+((' -- '+'; '.join(detail)) if detail else ''))
        evidence[cid]={'source_contract':ok}
        if not ok: failures.append(cid)

    if failures:
        print('RELEASE_GATE=FAIL')
        return 1
    if a.static_only:
        print('RELEASE_GATE=PASS_STATIC_ONLY')
        return 0

    print('==== LUA 5.1 WHOLE-MOD SYNTAX ====')
    code,out=run([sys.executable,str(tools/'sol_lua_check.py'),str(lua)])
    print('\n'.join(out.splitlines()[-25:]))
    if code: failures.append('lua_syntax')

    print('==== REAL LUA BEHAVIOR CONTRACTS ====')
    code,out=run([sys.executable,str(HERE/'lua_behavior_contracts.py'),str(lua)])
    print(out.rstrip())
    if code==2: blocked.append('lua_behavior_contracts:lupa_unavailable')
    elif code: failures.append('lua_behavior_contracts')

    print('==== SOL MIND TRANSPORT HARNESS ====')
    scratch=Path(tempfile.mkdtemp(prefix='sol_behavior_transport_'))
    try:
        code,out=run([sys.executable,str(mind/'harness.py'),str(lua/'client'),str(scratch)])
        print('\n'.join(out.splitlines()[-40:]))
        if code: failures.append('transport_harness')
    finally:
        shutil.rmtree(scratch,ignore_errors=True)

    goal_test=HERE/'tests'/'test_goal_engine.py'
    if goal_test.is_file() and (mind/'goal_engine.py').is_file():
        print('==== GOAL / RESCUE PLANNER CONTRACTS ====')
        code,out=run([sys.executable,str(goal_test)],extra_env={
            'SOL_MIND_UNDER_TEST':str(mind), 'PYTHONDONTWRITEBYTECODE':'1'})
        print('\n'.join(out.splitlines()[-45:]))
        if code: failures.append('goal_engine')

    print('==== WORK/LIVE CHANGED-BEHAVIOR PARITY ====')
    parity_files=['client/SolGPS.lua','client/SCAIToolGateway.lua','client/SCDriving.lua','client/SCVehicle.lua','client/SCCombat.lua','client/SCEncounter.lua','client/SCLogistics.lua']
    import hashlib
    def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
    for rel in parity_files:
        w=lua/rel; l=live/'media'/'lua'/rel
        ok=w.is_file() and l.is_file() and sha(w)==sha(l)
        print(('PASS  ' if ok else 'FAIL  ')+rel)
        if not ok: failures.append('parity:'+rel)

    # Runtime-only native/Java capabilities can never be promoted by this lab.
    print('==== RUNTIME-ONLY GATES ====')
    for cid in required:
        row=next(x for x in CAPS['capabilities'] if x['id']==cid)
        if 'runtime' in row['status'] and row['status'] not in ('runtime_proven_history',):
            print('PENDING  '+cid+' -- offline tests cannot prove Project Zomboid Java/native runtime')

    print('==== RESULT ====')
    if failures:
        print('RELEASE_GATE=FAIL')
        print('FAILURES='+','.join(failures))
        return 1
    print('RELEASE_GATE=PASS_OFFLINE')
    print('RUNTIME_PROOF=REQUIRED')
    if blocked: print('BLOCKED_NONFATAL='+','.join(blocked))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
