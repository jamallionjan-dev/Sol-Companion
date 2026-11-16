import os, shutil, sys, tempfile, threading, time
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='replace')
HERE=os.environ.get('SOL_MIND_UNDER_TEST') or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE)
import intent_engine as IE
import chat_service as CS
from goal_engine import GoalEngine

FAIL=[]
def ck(name,cond,detail=''):
    print(('PASS  ' if cond else 'FAIL  ')+name+(' -- '+detail if detail else ''))
    if not cond: FAIL.append(name)

q='سول تعالي بسرعة على موقعي الي حددتلك ياه عالماب بدي مساعدة انا محاط بالزومبي'
g=IE.parse_high_confidence(q)
ck('G1 rescue Arabic understood', bool(g and g.get('intent')=='emergency_rescue'), str(g))
ck('G2 marker resolved', g and g['slots']['target']=='marker', str(g))
ck('G3 ordinary summon is not rescue', IE.parse_high_confidence('سول تعالي هنا') is None)
ck('G4 explicit rescue works', (IE.parse_high_confidence('سول انقذيني') or {}).get('intent')=='emergency_rescue')
ck('G5 provider schema exposes registered goal', IE.provider_tool()['function']['parameters']['properties']['intent']['enum']==['emergency_rescue','home_errand'])
from goal_engine import PLANNERS
ck('C1 every advertised goal has a planner and every planner is advertised', set(IE.GOALS)==set(PLANNERS), str(sorted(PLANNERS)))
ck('C2 tool-using models are told every goal and their job', all(n in IE.capabilities_text() for n in IE.GOALS) and 'وظيفتك' in IE.capabilities_text())
ck('C3 text-bridge models get the exact tag for every goal', all(g['tag'] in IE.capabilities_text(tags=True) for g in IE.GOALS.values()))
src=open(CS.__file__,encoding='utf-8').read()
ck('C4 both connection paths send the capabilities', 'IE.capabilities_text()' in src and 'IE.capabilities_text(tags=True)' in src)
ck('C5 no goal list is hard-coded in the bridge primer', 'home_errand' not in CS.LINK_PRIMER and 'emergency_rescue' not in CS.LINK_PRIMER)
ck('E1 unload errand understood', (IE.parse_high_confidence('سول روحي فضي الاغراض بالبيت') or {}).get('intent')=='home_errand')
ck('E2 spelling with ظ understood', (IE.parse_high_confidence('روحي فظي الأغراض بالبيت وارجعي') or {}).get('intent')=='home_errand')
ck('E3 take me home is a routine pickup', ((IE.parse_high_confidence('سول تعي خديني عالبيت') or {}).get('slots') or {}).get('urgency')=='routine')
ck('E4 come and help is a rescue', (IE.parse_high_confidence('بدي ياكي تجي تساعدني') or {}).get('intent')=='emergency_rescue')
ck('E5 home alone is no errand', IE.parse_high_confidence('سول البيت حلو') is None)
ck('BHV1 Sol Mind is explicitly the action layer above LF', 'طبقة Sol العليا' in CS.SYSTEM_BASE and 'تُعطى حاليًا من زر الأوامر' not in CS.SYSTEM_BASE)
ck('BHV2 accepted cook plan is pending, not completed', not CS.action_result_completed({'ok': True, 'reason': 'plan_started:cook (8 steps)'}) and 'لم يتأكد اكتمالها' in CS.action_receipt_note({'ok': True, 'reason': 'plan_started:cook (8 steps)'}))
ck('BHV3 explicit planner done is completion evidence', CS.action_result_completed({'ok': True, 'reason': 'done:cook:all_steps_done'}))
ck('BHV4 accepted tool does not suppress incomplete claim guard', 'لم يصل تأكيد' in CS.guard_claims('قمت بطبخ البيض', action_attempted=True))
ck('BHV5 verified completion permits truthful completion claim', CS.guard_claims('قمت بطبخ البيض', action_attempted=True, completed=True) == 'قمت بطبخ البيض')
ck('BHV6 Sol Link explains its action tag runs after the reply', 'بعد توليد ردك' in CS.LINK_PRIMER and 'لا تقولي إنه اكتمل' in CS.LINK_PRIMER)
ck('BHV7 mixed completed and pending actions remain unconfirmed', not CS.all_action_results_completed([{'ok': True, 'reason': 'done:cook:all_steps_done'}, {'ok': True, 'reason': 'started'}]))
ck('BHV8 rejected completion claims do not count as proof', not CS.action_result_completed({'ok': False, 'status': 'completed', 'reason': 'done:cook'}))
ck('BHV9 rejected bridge action produces an honest failure note', 'ما قدرت أنفّذ' in CS.action_receipt_note({'ok': False, 'reason': 'unsupported_command'}))
ck('BHV10 missing game ack does not look like completion', 'لم يصل تأكيد' in CS.action_receipt_note({'ok': None, 'reason': 'gps_unconfirmed'}))
ck('BHV11 accepted passenger transition retains its actionable Arabic guidance', 'اركب من باب الراكب' in CS.action_receipt_note({'ok': True, 'reason': 'board_passenger'}))

class Mind:
    def __init__(self, in_vehicle=False):
        self.perception={
            'sol':{'position':{'x':0,'y':0,'z':0},'currentVehicle':({'id':'car'} if in_vehicle else None)},
            'player':{'position':{'x':100,'y':100,'z':0},'immediateThreats':3},
            'threats':{'count':3,'immediateCount':2,'visible':[{'zombieId':'z_far','distance':7},{'zombieId':'z_near','distance':2}]}
        }
        self.tools=[]; self.said=[]; self.results={}
    def request_tool(self,t,a=None):
        rid='r%d'%(len(self.tools)+1); self.tools.append((t,a or {})); self.results[rid]={'status':'queued'}; return rid
    def say(self,t): self.said.append(t); return 's%d'%len(self.said)
    def status(self,rid): return self.results.get(rid)
    def finish(self,rid,status='accepted'): self.results[rid]={'status':status,'accepted':status=='accepted'}

scratch=tempfile.mkdtemp(prefix='sol_goal_test_')
try:
    lock=threading.RLock()
    m=Mind(); e=GoalEngine(scratch,m,lock,log=lambda x:None)
    r=e.submit(IE.make_goal('emergency_rescue',{'target':'player','extract':'none'},source='test'))
    ck('G6 goal accepted',r.get('ok') is True,str(r))
    e.tick(); e.tick()
    req=open(os.path.join(scratch,'SolGPS_Request.txt'),encoding='ascii').read()
    ck('G7 rescue drive is solo','solo=1' in req,req)
    ck('G8 rescue targets live player coordinates','x=100' in req and 'y=100' in req,req)
    rid=e.active.get('gpsRid')
    with open(os.path.join(scratch,'SolGPS_State.txt'),'w',encoding='ascii') as f: f.write('ack=%s\nresult=arrived\nphase=arrived\ndistance=0\n'%rid)
    m.perception['sol']['position']={'x':100,'y':100,'z':0}
    e.tick(); ck('G9 arrival advances to secure area',e.active.get('phase')=='secure_area',str(e.active))
    e.tick()
    ck('G10 combat enables fire-at-will through MindCore', any(t=='fire_at_will' for t,_ in m.tools),str(m.tools))
    ck('G11 nearest visible zombie is designated', any(t=='designate_target' and a.get('zombieId')=='z_near' for t,a in m.tools),str(m.tools))
    before=len([1 for t,_ in m.tools if t=='designate_target'])
    e.tick()
    after=len([1 for t,_ in m.tools if t=='designate_target'])
    ck('G12 pending target command is not flooded',before==after,str(m.tools))
    m.perception['player']['immediateThreats']=0; m.perception['threats']={'count':0,'immediateCount':0,'visible':[]}
    e.active['clearSince']=time.time()-3
    e.tick(); e.tick()
    ck('G13 clear area enables hold-fire',any(t=='hold_fire' for t,_ in m.tools),str(m.tools))
    ck('G14 no-home rescue returns to follow',any(t=='follow' for t,_ in m.tools),str(m.tools))
    ck('G15 rescue completes after clear',e.active.get('status')=='completed',str(e.active))

    # If Sol arrives still seated, planner must exit through the reliable AI mailbox first.
    m3=Mind(in_vehicle=True); e3=GoalEngine(scratch,m3,lock,log=lambda x:None)
    e3.submit(IE.make_goal('emergency_rescue',{'target':'player','extract':'none'},source='test'))
    e3.tick(); e3.tick(); rr=e3.active['gpsRid']
    with open(os.path.join(scratch,'SolGPS_State.txt'),'w',encoding='ascii') as f: f.write('ack=%s\nresult=arrived\nphase=arrived\ndistance=0\n'%rr)
    m3.perception['sol']['position']={'x':100,'y':100,'z':0}; e3.tick(); e3.tick()
    ck('G16 seated arrival requests exit_vehicle',any(t=='exit_vehicle' for t,_ in m3.tools),str(m3.tools))
    ck('G17 combat waits until Sol is out of vehicle',not any(t=='fire_at_will' for t,_ in m3.tools),str(m3.tools))
    m3.perception['sol']['currentVehicle']=None; e3.tick()
    ck('G18 combat begins after exit is observed',any(t=='fire_at_will' for t,_ in m3.tools),str(m3.tools))

    # Home extraction is separate and MUST switch back to passenger-waiting/non-solo driving.
    m2=Mind(); e2=GoalEngine(scratch,m2,lock,log=lambda x:None); e2.home=lambda:{'x':10,'y':20,'name':'home'}
    e2.submit(IE.make_goal('emergency_rescue',{'target':'player','extract':'home'},source='test'))
    e2.tick(); e2.tick(); rid2=e2.active.get('gpsRid')
    with open(os.path.join(scratch,'SolGPS_State.txt'),'w',encoding='ascii') as f: f.write('ack=%s\nresult=arrived\nphase=arrived\ndistance=0\n'%rid2)
    m2.perception['sol']['position']={'x':100,'y':100,'z':0}; e2.tick()
    m2.perception['player']['immediateThreats']=0; m2.perception['threats']={'count':0,'immediateCount':0,'visible':[]}
    e2.active['clearSince']=time.time()-3; e2.tick(); e2.tick()
    req2=open(os.path.join(scratch,'SolGPS_Request.txt'),encoding='ascii').read()
    ck('G19 extraction drive is not solo','solo=0' in req2,req2)
    ck('G20 extraction targets saved home','x=10' in req2 and 'y=20' in req2,req2)
    hrid=e2.active.get('gpsRid')
    with open(os.path.join(scratch,'SolGPS_State.txt'),'w',encoding='ascii') as f: f.write('ack=%s\nresult=arrived\nphase=arrived\ndistance=0\n'%hrid)
    e2.tick()
    ck('G21a at home she gets out of the driver seat first',any(t=='exit_vehicle' for t,_ in m2.tools[-2:]) and e2.active.get('status')=='running',str(m2.tools))
    m2.finish(e2.active['exitHomeRid']); e2.tick()
    ck('G21 rescue + home extraction completes',e2.active.get('status')=='completed',str(e2.active))
    ck('G22 after the trip she follows again',m2.tools[-1][0]=='follow',str(m2.tools))

    # A drive that fails on the way (blocked road) finishes on foot instead of abandoning the player.
    m4=Mind(); e4=GoalEngine(scratch,m4,lock,log=lambda x:None)
    e4.submit(IE.make_goal('emergency_rescue',{'target':'player','extract':'none'},source='test'))
    e4.tick(); e4.tick(); r4=e4.active['gpsRid']
    with open(os.path.join(scratch,'SolGPS_State.txt'),'w',encoding='ascii') as f: f.write('ack=%s\nresult=failed\nphase=\nreason=route_blocked\n'%r4)
    e4.tick()
    ck('G23 blocked drive continues on foot',e4.active.get('status')=='running' and e4.active.get('phase')=='secure_area',str(e4.active))

    # The unload errand: alone to the base, LF's job empties the car, back to where the player is now.
    def put(name,body):
        with open(os.path.join(scratch,name),'w',encoding='ascii') as f: f.write(body)
    def ack_act(eng,ok,reason,key='actRid'): put('SolAct_State.txt','ack=%s\nok=%s\nreason=%s\n'%(eng.active[key],'true' if ok else 'false',reason))
    def ack_gps(eng,result='arrived'): put('SolGPS_State.txt','ack=%s\nresult=%s\nphase=%s\ndistance=0\n'%(eng.active['gpsRid'],result,result))
    me=Mind(); ee=GoalEngine(scratch,me,lock,log=lambda x:None)
    ee.submit(IE.make_goal('home_errand',{},source='test')); ee.tick()
    ck('E6 asks the game for the parking area','sol_errand_parking' in open(os.path.join(scratch,'SolAct_Request.txt'),encoding='ascii').read())
    ack_act(ee,True,'parking:40,50'); ee.tick()
    req=open(os.path.join(scratch,'SolGPS_Request.txt'),encoding='ascii').read()
    ck('E7 drives alone to the parking area','solo=1' in req and 'x=40' in req and 'y=50' in req,req)
    ack_gps(ee); ee.tick()
    ck('E7a arrival asks for the precise parking segment first','sol_errand_park' in open(os.path.join(scratch,'SolAct_Request.txt'),encoding='ascii').read() and not me.tools,str(me.tools))
    ack_act(ee,True,'approaching'); ee.tick(); ee.tick()
    ck('E7b polls the parking segment','sol_errand_park_status' in open(os.path.join(scratch,'SolAct_Request.txt'),encoding='ascii').read())
    ack_act(ee,True,'working','pollRid'); ee.tick()
    ck('E7c still parking stays seated',ee.active.get('phase')=='parking' and not me.tools,str(ee.active))
    ee.active['pollAt']=0; ee.tick(); ack_act(ee,True,'done','pollRid'); ee.tick()
    ck('E8 parked gets her out of the car',any(t=='exit_vehicle' for t,_ in me.tools),str(me.tools))
    ee.tick()
    ck('E9 then asks LF to unload','sol_unload_car' in open(os.path.join(scratch,'SolAct_Request.txt'),encoding='ascii').read())
    ack_act(ee,True,'unload_started'); ee.tick()
    ck('E10 waits on the job',ee.active.get('phase')=='unloading',str(ee.active))
    ee.active['pollAt']=0; ee.tick(); ck('E11 polls the job','sol_unload_status' in open(os.path.join(scratch,'SolAct_Request.txt'),encoding='ascii').read())
    ack_act(ee,True,'working:assigned:4','pollRid'); ee.tick()
    ck('E12 unfinished job is not reported done',ee.active.get('phase')=='unloading',str(ee.active))
    ee.active['pollAt']=0; ee.tick(); ack_act(ee,True,'done:0','pollRid'); ee.tick()
    ck('E13 finished job ends base duty','sol_errand_finish' in open(os.path.join(scratch,'SolAct_Request.txt'),encoding='ascii').read())
    me.perception['player']['position']={'x':300,'y':310,'z':0}
    ack_act(ee,True,'finished'); ee.tick()
    req=open(os.path.join(scratch,'SolGPS_Request.txt'),encoding='ascii').read()
    ck('E14 drives back to where the player is now','x=300' in req and 'y=310' in req and 'solo=1' in req,req)
    me.perception['sol']['position']={'x':300,'y':308,'z':0}; ack_gps(ee); ee.tick()
    ck('E15 gets out beside the player',ee.active.get('phase')=='finishing',str(ee.active))
    me.finish('r%d'%len(me.tools)); ee.tick()
    ck('E16 errand completes and she follows',ee.active.get('status')=='completed' and me.tools[-1][0]=='follow',str(ee.active))

    # Honest failure when the save has no base: no drive is sent.
    mf=Mind(); ef=GoalEngine(scratch,mf,lock,log=lambda x:None)
    os.remove(os.path.join(scratch,'SolGPS_Request.txt'))
    ef.submit(IE.make_goal('home_errand',{},source='test')); ef.tick(); ack_act(ef,False,'no_base'); ef.tick()
    ck('E17 no base fails and says so',ef.active.get('status')=='failed' and ef.active.get('reason')=='no_base' and bool(mf.said),str(ef.active))
    ck('E18 no base sends no drive',not os.path.exists(os.path.join(scratch,'SolGPS_Request.txt')))

    # A player order takes the wheel back from a running plan.
    mc=Mind(); ec=GoalEngine(scratch,mc,lock,log=lambda x:None)
    ec.submit(IE.make_goal('home_errand',{},source='test')); ec.tick(); ack_act(ec,True,'parking:40,50'); ec.tick()
    put('SolGPS_State.txt','ack=%s\nresult=stopped\nphase=\n'%ec.active['gpsRid']); ec.tick()
    ck('A1 pressing stop ends the errand quietly',ec.active.get('status')=='cancelled' and ec.active.get('reason')=='player_stopped',str(ec.active))
    said_before=len(mc.said); ec.tick(); ck('A2 a cancelled plan sends nothing more',len(mc.said)==said_before)
    import goal_engine as GE
    p=os.path.join(scratch,'SolAct_Request.txt'); put('SolAct_State.txt','ack=0\n'); first=GE._write_request(p,{'action':'one'}); t0=time.time(); second=GE._write_request(p,{'action':'two'})
    ck('A3 a second sender waits for the first to be taken',time.time()-t0>=1.0 and second>first,str(time.time()-t0))
    put('SolAct_State.txt','ack=%d\n'%second); t0=time.time(); GE._write_request(p,{'action':'three'}); ck('A4 no wait once it was taken',time.time()-t0<0.5)
    mo=Mind(); co=CS.Chat(scratch,log=lambda x:None,mind=mo,mind_lock=lock)
    try:
        co.goals.submit(IE.make_goal('home_errand',{},source='test')); co._player_takes_over('follow')
        ck('A5 a direct order ends the running goal',co.goals.active.get('status')=='cancelled',str(co.goals.active))
        co.goals.submit(IE.make_goal('home_errand',{},source='test')); co._player_takes_over('sol_eat')
        ck('A6 an order that does not move her leaves the goal running',co.goals.active.get('status')=='running',str(co.goals.active))
    finally: co.goals.stop.set()

    # Any model, however small: the mind acts first and speaks for what it did.
    I=CS._intents_core
    ck('D1 the sentence from the screenshot drives to the marker',('drive_to',{'target':'marker','speed':None}) in I('انتي قودي للمكان المحدد على الخريطة'),str(I('انتي قودي للمكان المحدد على الخريطة')))
    ck('D2 the typo in the screenshot too',any(n=='drive_to' and a.get('target')=='marker' for n,a in I('سوفي على المكان المحدد على الخريطة')),str(I('سوفي على المكان المحدد على الخريطة')))
    ck('D3 started drive never asks who drives','؟' not in CS.drive_reply({'ok':True,'confirmed':True,'result':'driving','reason':''}))
    ck('D4 failed drive says why, not success','تمام' not in CS.drive_reply({'ok':False,'reason':'no_marker'}),CS.drive_reply({'ok':False,'reason':'no_marker'}))
    def tag_provider(provider,key,model,msgs,tools,tool,system='',**kw): return 'حاضر [هدف: home_errand]'
    CS.P.chat_with_tools=tag_provider
    ct=CS.Chat(scratch,log=lambda x:None,mind=Mind(),mind_lock=lock); ct.system_prompt=lambda s,m:'BASE'; ct._world=lambda:(None,None)
    try:
        r=ct._ask_provider([{'role':'user','text':'شو رأيك نرتب الوضع'}])
        ck('D5 a model without tool calls still acts by tag',(ct.goals.active or {}).get('intent')=='home_errand' and 'هدف' not in r,r)
    finally: ct.goals.stop.set()
    ck('D6 every model is told to say when a capability is missing','غير متاحة' in IE.capabilities_text() and 'غير متاحة' in IE.capabilities_text(tags=True))
    ck('D7 every model is told never to ask who drives','فلا تسألي من يقود' in IE.capabilities_text())

    # The whole chain from a connected model to the game's mailbox: a reply alone must not be the end of it.
    def mailbox_has(word,seconds=2.0):
        end=time.time()+seconds
        p=os.path.join(scratch,'SolAct_Request.txt')
        while time.time()<end:
            try:
                if word in open(p,encoding='ascii').read(): return True
            except OSError: pass
            time.sleep(0.05)
        return False
    os.remove(os.path.join(scratch,'SolAct_Request.txt'))
    seen={}
    def fake_provider(provider,key,model,msgs,tools,tool,system='',**kw):
        seen['system']=system; seen['tools']=[t['function']['name'] for t in tools]; seen['result']=tool('request_goal',{'intent':'home_errand'}); return 'رح أشوف'
    CS.SS.load_config=lambda:{'source':'api','provider':'x','model':'m'}; CS.S.get=lambda p:'k'; CS.P.chat_with_tools=fake_provider
    c1=CS.Chat(scratch,log=lambda x:None,mind=Mind(),mind_lock=lock); c1.system_prompt=lambda s,m:'BASE'; c1._world=lambda:(None,None)
    try:
        c1._ask_provider([{'role':'user','text':'شو رأيك نرتب الوضع'}])
        ck('M1 API model is told its job and goals on the call','وظيفتك' in seen['system'] and 'home_errand' in seen['system'])
        ck('M2 API model has the tool to act','request_goal' in seen['tools'],str(seen['tools']))
        ck('M3 API model goal is accepted',seen['result'].get('ok') is True,str(seen['result']))
        ck('M4 API model goal reaches the game mailbox',mailbox_has('sol_errand_parking'))
    finally: c1.goals.stop.set()
    os.remove(os.path.join(scratch,'SolAct_Request.txt'))
    class Link:
        def ask(self,text,speak=True): seen['prompt']=text; return 'حاضر [هدف: home_errand]'
    link=Link(); CS.SS.start_link=lambda log:link
    c2=CS.Chat(scratch,log=lambda x:None,mind=Mind(),mind_lock=lock); c2._world=lambda:(None,None)
    try:
        reply=c2._ask_link([{'role':'user','text':'شو رأيك نرتب الوضع'}])
        ck('M5 ChatGPT bridge is told its job and exact tags','وظيفتك' in seen['prompt'] and '[هدف: home_errand]' in seen['prompt'])
        ck('M6 the tag is executed, not shown','هدف' not in reply and (c2.goals.active or {}).get('intent')=='home_errand',reply)
        ck('M7 bridge goal reaches the game mailbox',mailbox_has('sol_errand_parking'))
    finally: c2.goals.stop.set()
finally:
    shutil.rmtree(scratch,ignore_errors=True)
print('SUMMARY %s (%d failed)'%('ALL PASS' if not FAIL else 'FAIL',len(FAIL)))
sys.exit(1 if FAIL else 0)
