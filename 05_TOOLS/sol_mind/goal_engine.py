"""Stateful, extensible goal planner for Sol Mind.

The goal engine owns *multi-step* intent execution. Lua remains authoritative for
physical execution and game truth. Planners use only confirmed game channels:
MindCore perception/tool requests, SolGPS, SolActions and saved world memory.
"""
import json
import math
import os
import threading
import time

import intent_engine as IE
import world_knowledge as W

GPS_REQ, GPS_STATE = "SolGPS_Request.txt", "SolGPS_State.txt"
GOAL_STATE = "SolGoal_State.txt"
ACT_REQ, ACT_STATE = "SolAct_Request.txt", "SolAct_State.txt"


def _esc(text):
    out=[]
    for ch in str(text or ""):
        c=ord(ch)
        if ch == "\\": out.append("\\\\")
        elif 32 <= c < 127 and ch not in "|=": out.append(ch)
        elif ch in "\r\n\t": out.append(" ")
        elif c > 0xFFFF:
            c-=0x10000; out.append("\\u%04X\\u%04X" % (0xD800+(c>>10),0xDC00+(c&0x3FF)))
        else: out.append("\\u%04X" % c)
    return "".join(out)


def _unesc(s):
    import re
    def rep(m): return "\\" if m.group(0)=="\\\\" else chr(int(m.group(1),16))
    txt=re.sub(r"\\\\|\\u([0-9A-Fa-f]{4})",rep,s or "")
    return txt.encode("utf-16","surrogatepass").decode("utf-16","replace")


def _read_kv(path):
    try:
        with open(path, encoding="ascii", errors="replace") as f:
            return dict(line.split("=",1) for line in f.read().splitlines() if "=" in line)
    except OSError:
        return {}


_RID_LOCK=threading.Lock()
_RID_LAST=[0]


def next_request_id():
    """A request id that is unique and strictly increasing across every thread of this process."""
    with _RID_LOCK:
        rid=max(int(time.time()*1000),_RID_LAST[0]+1)
        _RID_LAST[0]=rid
        return rid


_STATE_OF={ACT_REQ:ACT_STATE,GPS_REQ:GPS_STATE}
_SENT={}
_SEND_LOCK=threading.Lock()
SEND_WAIT=1.6                                                                     # the game looks at the mailbox once a second


def _write_request(path, fields):
    """The game reads one request per mailbox and keeps only the newest, so two senders (a planner, the chat) could erase
    each other. Every sender comes through here: the previous request gets a moment to be taken before the next replaces it."""
    with _SEND_LOCK:
        last=_SENT.get(path)
        state=_STATE_OF.get(os.path.basename(path))
        if last and state:
            state_path=os.path.join(os.path.dirname(path),state)
            end=last[1]+SEND_WAIT
            while time.time()<end and str(_read_kv(state_path).get("ack") or "")!=str(last[0]):
                time.sleep(0.03)
        rid=next_request_id()
        tmp=path+".tmp"
        with open(tmp,"w",encoding="ascii",newline="\n") as f:
            f.write("id=%d\n" % rid)
            for k,v in fields.items():
                if v is not None: f.write("%s=%s\n" % (k,_esc(v)))
        os.replace(tmp,path)
        _SENT[path]=(rid,time.time())
        return rid


class Planner:
    intent = None
    def __init__(self, engine, goal): self.e,self.goal=engine,goal
    def tick(self, now): raise NotImplementedError


PLANNERS={}
def register(cls):
    PLANNERS[cls.intent]=cls
    return cls


class DrivingPlanner(Planner):
    def _perception(self): return self.e.perception()
    def _positions(self):
        p=self._perception() or {}; sol=(p.get("sol") or {}).get("position") or {}; pl=(p.get("player") or {}).get("position") or {}
        return sol,pl
    def _distance(self):
        s,p=self._positions()
        if s.get("x") is None or p.get("x") is None: return None
        return math.hypot(float(s["x"])-float(p["x"]),float(s["y"])-float(p["y"]))
    def _speak(self,text): self.e.say_once(self.goal,text)
    def _gps(self,fields):
        rid=_write_request(os.path.join(self.e.lua_dir,GPS_REQ),fields); self.goal["gpsRid"]=rid; self.goal["phaseSince"]=time.time(); return rid
    def _gps_state(self): return _read_kv(os.path.join(self.e.lua_dir,GPS_STATE))
    def _player_stopped(self,st):
        """The player pressed stop or gave another order on this drive: it is his call, not a failure to report."""
        return str(st.get("ack") or "")==str(self.goal.get("gpsRid") or "") and st.get("result") in ("stopped","interrupted")
    def _tool(self,key,tool,args=None):
        rid=self.e.request_tool(self.goal,tool,args or {})
        self.goal[key]=rid
        return rid
    def _tool_done(self,key):
        rid=self.goal.get(key)
        if not rid: return True
        st=self.e.tool_status(rid) or {}
        return st.get("status") in ("accepted","rejected","failed")


@register
class HomeErrand(DrivingPlanner):
    """Drive alone to the base parking area, let LF's verified job empty the trunk, drive back to the player."""
    intent="home_errand"
    DRIVE_TIMEOUT=420.0
    UNLOAD_TIMEOUT=300.0
    PARK_SECONDS=35.0
    ACK_SECONDS=8.0
    POLL_SECONDS=3.0
    NEAR_PLAYER=12.0
    REDIRECT_OVER=25.0
    MAX_REDIRECTS=3
    WAITING=("moving_to_wheel","walking_to_door","await_destination","board_passenger","")
    TELL={"no_base":"ما عندي قاعدة محددة بالبيت، حددها أول.","no_parking_area":"ما في موقف سيارات محدد بالقاعدة، حدده أول.",
          "car_not_parked_at_base":"ما قدرت أصف السيارة جوا موقف القاعدة، فما فضيتها.","fix_off":"هالمشوار لسا مش مفعّل."}

    def _act(self,name):
        rid=_write_request(os.path.join(self.e.lua_dir,ACT_REQ),{"action":name})
        self.goal["actRid"]=rid; self.goal["phaseSince"]=time.time()
    def _act_result(self):
        st=_read_kv(os.path.join(self.e.lua_dir,ACT_STATE))
        if str(st.get("ack") or "")!=str(self.goal.get("actRid") or ""): return None
        return st.get("ok")=="true", _unesc(st.get("reason") or "")
    def _poll(self,g,now,name,every):
        """One status request at a time; returns (ok, reason) when the game answers it, else None."""
        if g.get("pollRid"):
            st=_read_kv(os.path.join(self.e.lua_dir,ACT_STATE))
            if str(st.get("ack") or "")==str(g["pollRid"]):
                g["pollRid"]=None
                return st.get("ok")=="true", _unesc(st.get("reason") or "")
            if now-g.get("pollAt",now)>self.ACK_SECONDS: g["pollRid"]=None
        if not g.get("pollRid") and now-g.get("pollAt",0)>=every:
            g["pollRid"]=_write_request(os.path.join(self.e.lua_dir,ACT_REQ),{"action":name}); g["pollAt"]=now
        return None
    def _leave_car(self,g,now):
        g["pollRid"]=None; self._tool("exitRid","exit_vehicle"); self._next(g,"leaving_car",now)
    def _stop(self,g,reason):
        self._speak(self.TELL.get(reason) or "ما قدرت أكمل المشوار.")
        return self.e.fail(g,reason)
    def _next(self,g,phase,now): g["phase"]=phase; g["phaseSince"]=now
    def _drive_back(self,g):
        _s,pl=self._positions()
        self._gps({"action":"drive","x":int(pl["x"]),"y":int(pl["y"]),"name":"back to player","solo":"1","car":"last","speed":"normal"})
    def _drive_result(self,g,now):
        st=self._gps_state()
        if str(st.get("ack") or "")!=str(g.get("gpsRid") or ""):
            return "lost" if now-g.get("phaseSince",now)>self.ACK_SECONDS else None
        if self._player_stopped(st): return "stopped"
        if st.get("result")=="failed" and (st.get("reason") or "") not in self.WAITING:
            return "failed:"+(st.get("reason") or "drive_failed")
        if st.get("result")=="arrived" or st.get("phase")=="arrived": return "arrived"
        if now-g.get("phaseSince",now)>self.DRIVE_TIMEOUT: return "failed:drive_timeout"
        return None

    def tick(self,now):
        g=self.goal; phase=g.get("phase") or "resolve"
        if not self._perception(): return self.e.wait(g,"waiting_perception")

        if phase=="resolve":
            if self._positions()[1].get("x") is None: return self.e.wait(g,"player_position_unavailable")
            self._act("sol_errand_parking"); g["phase"]="await_parking"; return

        if phase in ("await_parking","await_park","await_unload","await_finish"):
            res=self._act_result()
            if res is None:
                if now-g.get("phaseSince",now)>self.ACK_SECONDS: return self._stop(g,"action_unconfirmed")
                return
            ok,reason=res
            if phase=="await_parking":
                if not ok: return self._stop(g,reason)
                x,y=reason.split(":",1)[1].split(",")
                self._speak("رايحة أفضي الأغراض بالبيت، وبرجعلك.")
                self._gps({"action":"drive","x":int(x),"y":int(y),"name":"home errand","solo":"1","car":"last","speed":"normal"})
                g["phase"]="driving_home"; return
            if phase=="await_park":
                # A refused last segment is not fatal: the unload step checks the footprint and reports it honestly.
                if not ok: g["parkRefused"]=reason; return self._leave_car(g,now)
                self._next(g,"parking",now); return
            if phase=="await_unload":
                if not ok: return self._stop(g,reason)
                if reason=="nothing_to_unload":
                    self._speak("السيارة فاضية أصلاً، راجعتلك.")
                    self._act("sol_errand_finish"); g["phase"]="await_finish"; return
                self._next(g,"unloading",now); g["unloadSince"]=now; return
            self._drive_back(g); g["phase"]="driving_back"; g["redirects"]=0; return

        if phase=="driving_home":
            r=self._drive_result(g,now)
            if r is None: return
            if r=="stopped": return self.e.cancel(g,"player_stopped")
            if r!="arrived": return self._stop(g,"gps_unconfirmed" if r=="lost" else r.split(":",1)[1])
            self._act("sol_errand_park"); g["phase"]="await_park"; return

        if phase=="parking":
            res=self._poll(g,now,"sol_errand_park_status",1.0)
            if res is not None and (not res[0] or res[1]=="done"):
                if not res[0]: g["parkRefused"]=res[1]
                return self._leave_car(g,now)
            if now-g.get("phaseSince",now)>self.PARK_SECONDS: return self._leave_car(g,now)
            return

        if phase=="leaving_car":
            if (self._perception().get("sol") or {}).get("currentVehicle") is None:
                self._act("sol_unload_car"); g["phase"]="await_unload"; return
            if now-g.get("phaseSince",now)>15: return self._stop(g,"cannot_exit_vehicle")
            return

        if phase=="unloading":
            res=self._poll(g,now,"sol_unload_status",self.POLL_SECONDS)
            if res is not None:
                ok,reason=res
                if not ok: return self._stop(g,reason)
                if reason.startswith("done:"):
                    left=reason.split(":",1)[1]
                    self._speak("فضيت السيارة، راجعتلك." if left in ("0","-1") else "فضيت اللي قدرت عليه وضل شوية بالسيارة، راجعتلك.")
                    g["left"]=left; self._act("sol_errand_finish"); g["phase"]="await_finish"; return
            if now-g.get("unloadSince",now)>self.UNLOAD_TIMEOUT:
                self._act("sol_errand_finish"); return self.e.fail(g,"unload_timeout")
            return

        if phase=="driving_back":
            d=self._distance()
            r=self._drive_result(g,now)
            if r=="stopped": return self.e.cancel(g,"player_stopped")
            if r is None and not (d is not None and d<=self.NEAR_PLAYER): return
            if r is not None and r!="arrived" and not (d is not None and d<=self.NEAR_PLAYER):
                return self._stop(g,"gps_unconfirmed" if r=="lost" else r.split(":",1)[1])
            if d is not None and d>self.REDIRECT_OVER and g.get("redirects",0)<self.MAX_REDIRECTS:
                g["redirects"]=g.get("redirects",0)+1; self._drive_back(g); return   # the player moved while she drove
            self._tool("exitBackRid","exit_vehicle"); self._next(g,"finishing",now); return

        if phase=="finishing":
            if not self._tool_done("exitBackRid") and now-g.get("phaseSince",now)<=15: return
            if not g.get("followRid"): self._tool("followRid","follow")
            self._speak("رجعت.")
            return self.e.complete(g,"home_errand_complete")


@register
class EmergencyRescue(DrivingPlanner):
    intent="emergency_rescue"
    DRIVE_TIMEOUT=180.0
    COMBAT_CLEAR_SECONDS=2.5
    BESIDE_TILES=5.0

    def tick(self,now):
        g=self.goal; phase=g.get("phase") or "resolve"
        per=self._perception()
        if not per:
            return self.e.wait(g,"waiting_perception")
        slots=g.get("slots") or {}

        if phase=="resolve":
            sol,pl=self._positions()
            if pl.get("x") is None:
                return self.e.wait(g,"player_position_unavailable")
            g["phase"]="dispatch"; g["phaseSince"]=now
            self._speak("جاييتك هلأ." if slots.get("urgency")=="routine" else "وصلتني الاستغاثة. جاييتك، حاول تضل حي.")
            return

        if phase=="dispatch":
            target=slots.get("target","player")
            fields={"action":"drive","solo":"1","speed":"fast"}
            if target=="marker": fields["target"]="marker"
            else:
                _s,pl=self._positions()
                if pl.get("x") is None or pl.get("y") is None:
                    g["phase"]="resolve"; return self.e.wait(g,"player_position_unavailable")
                fields.update(x=int(float(pl["x"])),y=int(float(pl["y"])),name="player rescue")
            self._gps(fields); g["phase"]="driving_to_player"; g["reason"]="rescue_drive_sent"; return

        if phase=="driving_to_player":
            st=self._gps_state(); rid=str(g.get("gpsRid") or "")
            if self._player_stopped(st): return self.e.cancel(g,"player_stopped")
            if str(st.get("ack") or "") != rid:
                if now-g.get("phaseSince",now)>8: return self.e.fail(g,"gps_unconfirmed")
                return
            reason=st.get("reason") or ""; result=st.get("result") or ""; ph=st.get("phase") or ""
            if result=="failed" and reason not in ("moving_to_wheel","walking_to_door","await_destination","board_passenger",""):
                # Vehicle is preferred, not mandatory: if we know the player coordinates, fall back to foot.
                if reason in ("map_not_opened","no_marker") and slots.get("target")=="marker":
                    _s,pl=self._positions()
                    if pl.get("x") is not None:
                        self._gps({"action":"drive","x":int(pl["x"]),"y":int(pl["y"]),"name":"player rescue","solo":"1","speed":"fast"})
                        g["reason"]="marker_unavailable_live_player_fallback"; return
                if reason in ("no_vehicle_near","driving_unavailable","cannot_take_wheel"):
                    _s,pl=self._positions()
                    if pl.get("x") is not None:
                        self.e.request_tool(g,"go_to",{"x":pl["x"],"y":pl["y"],"z":pl.get("z",0)})
                        g["phase"]="approaching_on_foot"; g["phaseSince"]=now; g["reason"]="vehicle_unavailable_foot_fallback"; return
                # Sol: the car got her part of the way (blocked road, no route on, turn failed):
                # she gets out and finishes on foot instead of giving up on the player.
                if self._positions()[1].get("x") is not None:
                    g["reason"]="drive_failed_%s_on_foot" % (reason or "unknown")
                    g["phase"]="secure_area"; g["phaseSince"]=now; g["clearSince"]=None
                    return
                return self.e.fail(g,reason or "rescue_drive_failed")
            d=self._distance()
            try: gpsd=float(st.get("distance"))
            except (TypeError,ValueError): gpsd=None
            if result=="arrived" or ph=="arrived" or (d is not None and d<=12) or (gpsd is not None and gpsd<=8):
                g["phase"]="secure_area"; g["phaseSince"]=now; g["clearSince"]=None
                return
            if now-g.get("phaseSince",now)>self.DRIVE_TIMEOUT: return self.e.fail(g,"rescue_drive_timeout")
            return

        if phase=="approaching_on_foot":
            d=self._distance()
            if d is not None and d<=12:
                g["phase"]="secure_area"; g["phaseSince"]=now; g["clearSince"]=None; return
            if now-g.get("phaseSince",now)>90: return self.e.fail(g,"foot_approach_timeout")
            return

        if phase=="secure_area":
            sol=(per.get("sol") or {})
            # Leave the vehicle through the reliable AI mailbox before combat.
            if sol.get("currentVehicle") is not None:
                if not g.get("exitRid"): self._tool("exitRid","exit_vehicle")
                if now-g.get("phaseSince",now)>12: return self.e.fail(g,"cannot_exit_vehicle")
                return
            if not g.get("fireRid"):
                self._tool("fireRid","fire_at_will")
            # Out of the car: go to the player and fight beside him (Living Fellows' follow + combat instincts).
            if not g.get("followRid") and self._tool_done("fireRid"):
                self._tool("followRid","follow")

            threats=(per.get("threats") or {})
            visible=threats.get("visible") or []
            player=per.get("player") or {}
            immediate=int(player.get("immediateThreats") or 0)
            # Pick the nearest real zombie and never flood the single-flight mailbox.
            candidates=[z for z in visible if z.get("zombieId")]
            cand=min(candidates,key=lambda z: float(z.get("distance") or 1e9)) if candidates else None
            if cand and self._tool_done("targetRid") and now-g.get("lastTargetAt",0)>=1.0:
                self._tool("targetRid","designate_target",{"zombieId":cand["zombieId"]})
                g["lastTargetAt"]=now

            local_count=int(threats.get("immediateCount") or threats.get("count") or 0)
            if immediate<=0 and local_count<=0:
                if g.get("clearSince") is None: g["clearSince"]=now
                d=self._distance()
                beside=d is not None and d<=self.BESIDE_TILES
                # Clear and standing beside the player (or clear for a long while: do not hang forever).
                if now-g["clearSince"]>=self.COMBAT_CLEAR_SECONDS and (beside or now-g["clearSince"]>=25):
                    if not g.get("holdRid"): self._tool("holdRid","hold_fire")
                    g["phase"]="extract"; g["phaseSince"]=now
                    self._speak("هيا، رح آخدك عالبيت. امشي معي عالسيارة.")
                    return
            else: g["clearSince"]=None
            if now-g.get("phaseSince",now)>120: return self.e.fail(g,"combat_timeout")
            return

        if phase=="extract":
            home=self.e.home()
            if slots.get("extract")=="none" or not home:
                if not g.get("followRid"): self._tool("followRid","follow")
                return self.e.complete(g,"player_rescued_no_home")
            # solo=0: wait for the player to board; car=last: the car she came in, not whatever is nearest.
            self._gps({"action":"drive","x":home["x"],"y":home["y"],"name":home.get("name") or "home","solo":"0","car":"last","speed":"normal"})
            g["phase"]="returning_home"; g["reason"]="waiting_for_player_then_home"; return

        if phase=="returning_home":
            st=self._gps_state(); rid=str(g.get("gpsRid") or "")
            if self._player_stopped(st): return self.e.cancel(g,"player_stopped")
            if str(st.get("ack") or "") != rid:
                if now-g.get("phaseSince",now)>self.DRIVE_TIMEOUT+90: return self.e.fail(g,"return_home_unanswered")
                return
            result,reason,ph=st.get("result") or "",st.get("reason") or "",st.get("phase") or ""
            if result=="failed" and reason not in ("board_passenger","moving_to_wheel","walking_to_door","await_destination",""):
                return self.e.fail(g,reason or "return_home_failed")
            if reason=="board_passenger":
                # She sits at the wheel waiting for the player: that wait is his to end, not a timeout.
                self._speak("أنا بالسيارة، اركب.")
                g["phaseSince"]=now
                return
            if result=="arrived" or ph=="arrived":
                self._speak("وصلنا عالبيت.")
                # A driver keeps her seat until told otherwise: at home she parks, gets out and follows again.
                if not g.get("exitHomeRid"): self._tool("exitHomeRid","exit_vehicle")
                if not self._tool_done("exitHomeRid"): return
                if not g.get("followHomeRid"): self._tool("followHomeRid","follow")
                return self.e.complete(g,"rescue_and_extraction_complete")
            if now-g.get("phaseSince",now)>self.DRIVE_TIMEOUT+90: return self.e.fail(g,"return_home_timeout")


class GoalEngine:
    def __init__(self,lua_dir,mind=None,mind_lock=None,log=print):
        self.lua_dir=lua_dir; self.mind=mind; self.mind_lock=mind_lock; self.log=log
        self.lock=threading.RLock(); self.active=None; self.planner=None; self.history=[]; self.seq=0; self.stop=threading.Event()

    def start(self,interval=0.25):
        def loop():
            while not self.stop.is_set():
                try: self.tick()
                except Exception as e: self.log("goal: ERROR %r" % (e,))
                self.stop.wait(interval)
        t=threading.Thread(target=loop,name="sol-goals",daemon=True); t.start(); return t

    def perception(self):
        if self.mind is None: return None
        if self.mind_lock:
            with self.mind_lock: return self.mind.perception
        return self.mind.perception

    def submit(self,goal):
        if not isinstance(goal,dict) or not goal.get("ok"):
            return goal if isinstance(goal,dict) else {"ok":False,"error":"invalid_goal"}
        cls=PLANNERS.get(goal.get("intent"))
        if cls is None: return {"ok":False,"error":"planner_unavailable","intent":goal.get("intent")}
        with self.lock:
            # Emergency goals may pre-empt; duplicate rescue requests merge into the current goal.
            if self.active and self.active.get("status")=="running":
                if self.active.get("intent")==goal.get("intent"):
                    self.active["slots"].update(goal.get("slots") or {})
                    self.active["updatedAt"]=time.time(); self._publish();
                    return {"ok":True,"goalId":self.active["id"],"status":"already_running","phase":self.active.get("phase")}
                self.active["status"]="preempted"; self.active["endedAt"]=time.time(); self.history.append(self.active)
            self.seq+=1
            g=dict(goal); g.update(id="goal-%d"%self.seq,status="running",phase="resolve",reason="accepted",startedAt=time.time(),updatedAt=time.time())
            self.active=g; self.planner=cls(self,g); self._publish()
            self.log("goal: accepted %s %s" % (g["id"],g["intent"]))
            return {"ok":True,"goalId":g["id"],"status":"running","phase":g["phase"]}

    PHASE_LIMIT=480.0      # no phase of any plan may run longer than this without moving on
    MAX_ERRORS=3

    def tick(self):
        with self.lock:
            if not self.active or self.active.get("status")!="running" or not self.planner: return
            g=self.active; now=time.time()
            g["updatedAt"]=now
            if g.get("_phase")!=g.get("phase"): g["_phase"]=g.get("phase"); g["_phaseEnter"]=now
            try:
                self.planner.tick(now); g["_errors"]=0
            except Exception as e:
                # A bug in one plan must end that plan, not leave it "running" for ever and refuse
                # every later request as already_running.
                g["_errors"]=g.get("_errors",0)+1
                self.log("goal: ERROR in %s/%s: %r" % (g.get("intent"),g.get("phase"),e))
                if g["_errors"]>=self.MAX_ERRORS and g.get("status")=="running":
                    self.fail(g,"planner_error:%s" % type(e).__name__); return
            if g.get("status")=="running":
                since=max(g.get("_phaseEnter",now), g.get("phaseSince",0) or 0)
                limit=getattr(self.planner,"PHASE_LIMIT",self.PHASE_LIMIT)
                if now-since>limit:
                    self.fail(g,"phase_timeout:%s:%s" % (g.get("phase"),g.get("reason"))); return
            self._publish()

    def cancel(self,g=None,reason="player_order"):
        """The player took over: the running goal ends quietly and stops steering her."""
        with self.lock:
            g=g or self.active
            if not g or g.get("status")!="running": return False
            g["status"]="cancelled"; g["reason"]=reason; g["endedAt"]=time.time(); self.history.append(dict(g)); self.log("goal: CANCEL %s %s"%(g.get("id"),reason));
            if g.get("intent")=="refuel_errand":
                try: _write_request(os.path.join(self.lua_dir,"SolAct_Request.txt"),{"action":"sol_fuel","option":"cancel"})
                except OSError: pass
            self._publish(); return True

    def wait(self,g,reason): g["reason"]=reason
    def wait_answer(self,goal_id,seconds=3.0):
        """The words a question-goal came up with, once it has them. Called from the chat thread while the goal loop runs."""
        end=time.time()+seconds
        while time.time()<end:
            for g in [self.active]+list(self.history):
                if isinstance(g,dict) and g.get("id")==goal_id and g.get("answer"): return g["answer"]
            time.sleep(0.1)
        return None
    def fail(self,g,reason):
        g["status"]="failed"; g["reason"]=reason; g["endedAt"]=time.time(); self.history.append(dict(g)); self.log("goal: FAIL %s %s"%(g.get("id"),reason)); self._publish(); return False
    def complete(self,g,reason):
        g["status"]="completed"; g["reason"]=reason; g["endedAt"]=time.time(); self.history.append(dict(g)); self.log("goal: PASS %s %s"%(g.get("id"),reason)); self._publish(); return True

    def request_tool(self,g,tool,args=None):
        if self.mind is None: return None
        if self.mind_lock:
            with self.mind_lock: rid=self.mind.request_tool(tool,args or {})
        else: rid=self.mind.request_tool(tool,args or {})
        g["lastTool"]={"tool":tool,"requestId":rid,"at":time.time()}; return rid

    def tool_status(self,rid):
        if self.mind is None or not rid: return None
        if self.mind_lock:
            with self.mind_lock: return self.mind.status(rid)
        return self.mind.status(rid)

    def say_once(self,g,text):
        key="said:"+text
        if g.get(key): return
        g[key]=True
        if self.mind is not None:
            if self.mind_lock:
                with self.mind_lock: self.mind.say(text)
            else: self.mind.say(text)

    def home(self):
        snap=W.load_snapshot(self.lua_dir)
        if not snap or not (snap.get("world") or {}).get("name"): return None
        try: h=W.Memory(snap["world"]).data.get("home")
        except Exception: h=None
        if not h:
            # Sol's own home set in game ("this is home", SolHome.lua) when Sol Mind's memory has none.
            sh=snap.get("solHome")
            if isinstance(sh,dict) and sh.get("x") is not None and sh.get("y") is not None:
                h={"name":"home","x":int(sh["x"]),"y":int(sh["y"]),"z":sh.get("z",0)}
        return h

    def describe(self):
        with self.lock:
            g=self.active
            if not g or g.get("status")!="running": return "none"
            return "%s status=%s phase=%s reason=%s"%(g.get("intent"),g.get("status"),g.get("phase"),g.get("reason"))

    def _publish(self):
        g=self.active or {"status":"idle"}
        data={k:v for k,v in g.items() if not k.startswith("said:") and not k.startswith("_")}
        tmp=os.path.join(self.lua_dir,GOAL_STATE+".tmp"); dst=os.path.join(self.lua_dir,GOAL_STATE)
        try:
            with open(tmp,"w",encoding="ascii",newline="\n") as f: json.dump(data,f,ensure_ascii=True,separators=(",",":"))
            os.replace(tmp,dst)
        except OSError: pass


# --------------------------------------------------------------------------- shared driving helpers
class GpsPlanner(Planner):
    """Everything a planner needs to make Sol actually move: perception, the GPS channel,
    the AI tool mailbox and the in-game action channel (SolAct_Request.txt)."""
    ACT_REQ, ACT_STATE = "SolAct_Request.txt", "SolAct_State.txt"
    ARRIVE_TILES = 12.0

    def _perception(self): return self.e.perception()

    def _positions(self):
        p = self._perception() or {}
        sol = (p.get("sol") or {}).get("position") or {}
        pl = (p.get("player") or {}).get("position") or {}
        return sol, pl

    def _player_xy(self):
        _s, pl = self._positions()
        if pl.get("x") is None: return None
        return int(float(pl["x"])), int(float(pl["y"]))

    def _distance_to(self, x, y):
        sol, _pl = self._positions()
        if sol.get("x") is None or x is None: return None
        return math.hypot(float(sol["x"]) - float(x), float(sol["y"]) - float(y))

    def _speak(self, text): self.e.say_once(self.goal, text)

    def _gps(self, fields):
        rid = _write_request(os.path.join(self.e.lua_dir, GPS_REQ), fields)
        self.goal["gpsRid"] = rid; self.goal["phaseSince"] = time.time(); return rid

    def _gps_state(self):
        st = _read_kv(os.path.join(self.e.lua_dir, GPS_STATE))
        if str(st.get("ack") or "") != str(self.goal.get("gpsRid") or ""): return None
        return st

    def _gps_failed(self, st):
        """A real refusal, not one of the waiting states the GPS reports while it works."""
        result = st.get("result") or ""
        # The player gave an order himself, or pressed stop: his word ends the plan. Re-sending the
        # drive here is exactly the fight this avoids.
        if result == "stopped":
            return "player_took_over" if (st.get("reason") or "") in ("player_order", "player_stop") else "drive_stopped"
        if (st.get("reason") or "") == "player_in_control": return "player_took_over"
        if result != "failed": return None
        reason = st.get("reason") or ""
        if reason in ("board_passenger", "moving_to_wheel", "walking_to_door", "await_destination", ""): return None   # still on her way to the car
        return reason

    def _gps_arrived(self, st, x=None, y=None):
        if (st.get("result") or "") == "arrived" or (st.get("phase") or "") == "arrived": return True
        try: gpsd = float(st.get("distance"))
        except (TypeError, ValueError): gpsd = None
        if gpsd is not None and gpsd <= 8: return True
        d = self._distance_to(x, y) if x is not None else None
        return d is not None and d <= self.ARRIVE_TILES

    def _tool(self, key, tool, args=None):
        rid = self.e.request_tool(self.goal, tool, args or {})
        self.goal[key] = rid; return rid

    def _tool_done(self, key):
        rid = self.goal.get(key)
        if not rid: return True
        st = self.e.tool_status(rid) or {}
        return st.get("status") in ("accepted", "rejected", "failed")

    def _once_tool(self, key, tool, args=None):
        """Send a tool request once and report whether the game has answered it."""
        if not self.goal.get(key): self._tool(key, tool, args)
        return self._tool_done(key)

    def _action(self, key, action, option=None):
        """The in-game action channel: the same verbs the order window uses (SolActions)."""
        if self.goal.get(key): return self.goal[key]
        try:
            rid = _write_request(os.path.join(self.e.lua_dir, self.ACT_REQ), {"action": action, "option": option})   # one writer: a chat turn must not erase this
        except OSError:
            return None
        self.goal[key] = rid; return rid

    def _action_result(self, key):
        """None while the game has not answered yet, otherwise (ok, reason)."""
        rid = self.goal.get(key)
        if not rid: return None
        st = _read_kv(os.path.join(self.e.lua_dir, self.ACT_STATE))
        if str(st.get("ack") or "") != str(rid):
            if ("r%s" % rid) not in st: return None                              # the game keeps the last few answers: another sender's may be on top
            ok, _, why = st["r%s" % rid].partition("|")
            return ok == "true", _unesc(why)
        return st.get("ok") == "true", _unesc(st.get("reason") or "")

    def _destination(self, kind, place=""):
        """home / marker / a remembered place -> GPS fields, or (None, reason)."""
        if kind == "marker": return {"target": "marker"}, None
        if kind == "home":
            h = self.e.home()
            if not h: return None, "home_not_set"
            return {"x": int(h["x"]), "y": int(h["y"]), "name": h.get("name") or "home"}, None
        snap = W.load_snapshot(self.e.lua_dir)
        world = (snap or {}).get("world") or {}
        if not world.get("name"): return None, "no_world_data"
        try: places = W.Memory(world).data.get("places") or []
        except Exception: places = []
        want = (place or "").strip()
        for p in reversed(places):
            name = str(p.get("name") or "")
            if want and name and (want in name or (len(name) >= 3 and name in want)):
                return {"x": int(p["x"]), "y": int(p["y"]), "name": name}, None
        return None, "unknown_place:" + want


@register
class ErrandRoundTrip(GpsPlanner):
    """She drives there alone, does the task, and drives back to the player by herself."""
    intent = "errand_round_trip"
    DRIVE_TIMEOUT = 300.0
    WORK_SECONDS = 150.0

    def tick(self, now):
        g = self.goal; slots = g.get("slots") or {}
        phase = g.get("phase") or "resolve"
        if not self._perception(): return self.e.wait(g, "waiting_perception")

        if phase == "resolve":
            fields, why = self._destination(slots.get("destination") or "home", slots.get("place"))
            if fields is None: return self.e.fail(g, why)
            g["destFields"] = fields
            g["phase"] = "outbound"; g["phaseSince"] = now
            self._speak("ماشي، رايحة ورجعالك.")
            return

        if phase == "outbound":
            f = dict(g["destFields"]); f.update(action="drive", solo="1", speed=slots.get("speed") or "normal")
            self._gps(f)
            g["phase"] = "driving_out"; g["reason"] = "driving_out"; return

        if phase == "driving_out":
            st = self._gps_state()
            if st is None:
                if now - g.get("phaseSince", now) > 8: return self.e.fail(g, "gps_unconfirmed")
                return
            why = self._gps_failed(st)
            if why: return self.e.fail(g, "outbound_%s" % why)
            if self._gps_arrived(st, g["destFields"].get("x"), g["destFields"].get("y")):
                g["phase"] = "working"; g["phaseSince"] = now; g["reason"] = "arrived_doing_the_task"; return
            if now - g.get("phaseSince", now) > self.DRIVE_TIMEOUT: return self.e.fail(g, "outbound_timeout")
            return

        if phase == "working":
            per = self._perception() or {}
            if (per.get("sol") or {}).get("currentVehicle") is not None:
                if not self._once_tool("exitRid", "exit_vehicle"):
                    if now - g.get("phaseSince", now) > 12: return self.e.fail(g, "cannot_exit_vehicle")
                    return
            if not g.get("outSince"): g["outSince"] = now      # the unload clock starts once she is out
            if (slots.get("task") or "none") == "unload":
                # LF's quartermaster carries the unload_vehicle / haul / sort jobs: that is the real
                # in-game worker for "empty the car into the base's storage".
                self._action("roleRid", "sol_role", "quartermaster")
                res = self._action_result("roleRid")
                if res is None:
                    if now - g.get("outSince", now) > 10: return self.e.fail(g, "unload_unconfirmed")
                    return
                ok, reason = res
                if not ok: return self.e.fail(g, "unload_refused:%s" % (reason or "unknown"))
                if not g.get("workSince"): g["workSince"] = now; self._speak("وصلت، عم فضي السيارة.")
                if now - g["workSince"] < self.WORK_SECONDS:
                    g["reason"] = "unloading"; return
                self._action("roleBackRid", "sol_role", "generalist")
                if self._action_result("roleBackRid") is None:
                    # one lost write must not leave her a quartermaster for good: ask once more
                    if now - g["workSince"] > self.WORK_SECONDS + 5 and not g.get("roleBackRetried"):
                        g["roleBackRetried"] = True; g.pop("roleBackRid", None)
                        self._action("roleBackRid", "sol_role", "generalist")
                    if now - g["workSince"] < self.WORK_SECONDS + 15: return
            g["phase"] = "homeward" if (slots.get("then") or "return_to_player") == "return_to_player" else "done"
            g["phaseSince"] = now; return

        if phase == "done":
            self._once_tool("stayRid", "stay")
            return self.e.complete(g, "errand_done_waiting_there")

        if phase == "homeward":
            xy = self._player_xy()
            if xy is None: return self.e.wait(g, "player_position_unavailable")
            g["backTo"] = {"x": xy[0], "y": xy[1]}
            self._gps({"action": "drive", "x": xy[0], "y": xy[1], "name": "back to the player",
                       "solo": "1", "car": "last", "speed": slots.get("speed") or "normal"})
            g["phase"] = "driving_back"; g["reason"] = "driving_back"
            self._speak("خلصت، جايتك.")
            return

        if phase == "driving_back":
            st = self._gps_state()
            if st is None:
                if now - g.get("phaseSince", now) > 8: return self.e.fail(g, "gps_unconfirmed_back")
                return
            why = self._gps_failed(st)
            if why: return self.e.fail(g, "return_%s" % why)
            back = g.get("backTo") or {}
            if self._gps_arrived(st, back.get("x"), back.get("y")):
                if not self._once_tool("exitBackRid", "exit_vehicle"): return
                self._once_tool("followRid", "follow")
                return self.e.complete(g, "errand_round_trip_complete")
            # He moved far from where she set off to: re-aim at where he is now.
            xy = self._player_xy()
            if xy and back.get("x") is not None and math.hypot(xy[0] - back["x"], xy[1] - back["y"]) > 40:
                g["phase"] = "homeward"; g["phaseSince"] = now; return
            if now - g.get("phaseSince", now) > self.DRIVE_TIMEOUT: return self.e.fail(g, "return_timeout")
            return


@register
class FetchPlayer(GpsPlanner):
    """"تعي لعندي" / "خذيني عالبيت": she drives to him, then optionally drives him home. No rescue drama."""
    intent = "fetch_player"
    DRIVE_TIMEOUT = 300.0

    def tick(self, now):
        g = self.goal; slots = g.get("slots") or {}
        phase = g.get("phase") or "resolve"
        if not self._perception(): return self.e.wait(g, "waiting_perception")

        if phase == "resolve":
            xy = self._player_xy()
            if xy is None: return self.e.wait(g, "player_position_unavailable")
            g["toPlayer"] = {"x": xy[0], "y": xy[1]}
            self._gps({"action": "drive", "x": xy[0], "y": xy[1], "name": "to the player",
                       "solo": "1", "speed": slots.get("speed") or "fast"})
            g["phase"] = "driving_to_player"; g["reason"] = "driving_to_player"
            if not g.get("spoke") and not slots.get("quiet"): self._speak("جايتك، استناني.")      # far_arrival: once, and not over her arrival line
            g["spoke"] = True
            return

        if phase == "driving_to_player":
            st = self._gps_state()
            if st is None:
                if now - g.get("phaseSince", now) > 8: return self.e.fail(g, "gps_unconfirmed")
                return
            why = self._gps_failed(st)
            if why == "player_took_over": return self.e.fail(g, "player_took_over")
            if why:
                # No car, no route: she comes on foot with Living Fellows' own follow instinct.
                if why == "no_sol": return self.e.fail(g, "no_sol")                   # no body to send: saying she is coming would be untrue
                self._once_tool("followRid", "follow")
                return self.e.complete(g, "coming_on_foot:%s" % why)
            to = g.get("toPlayer") or {}
            if self._gps_arrived(st, to.get("x"), to.get("y")):
                if (slots.get("then") or "stay_with_player") == "take_player_home":
                    home = self.e.home()
                    if not home: return self.e.fail(g, "home_not_set")
                    self._gps({"action": "drive", "x": int(home["x"]), "y": int(home["y"]),
                               "name": home.get("name") or "home", "solo": "0", "car": "last", "speed": "normal"})
                    g["phase"] = "taking_home"; g["reason"] = "waiting_for_player_then_home"; return
                if not self._once_tool("exitRid", "exit_vehicle"): return
                self._once_tool("followRid", "follow")
                return self.e.complete(g, "arrived_at_player")
            xy = self._player_xy()
            if xy and to.get("x") is not None and math.hypot(xy[0] - to["x"], xy[1] - to["y"]) > 12:      # far_arrival: where he is now
                g["phase"] = "resolve"; g["phaseSince"] = now; return
            if now - g.get("phaseSince", now) > self.DRIVE_TIMEOUT: return self.e.fail(g, "drive_to_player_timeout")
            return

        if phase == "taking_home":
            st = self._gps_state()
            if st is None:
                if now - g.get("phaseSince", now) > self.DRIVE_TIMEOUT + 90: return self.e.fail(g, "take_home_unanswered")
                return
            why = self._gps_failed(st)
            if why: return self.e.fail(g, "take_home_%s" % why)
            if (st.get("reason") or "") == "board_passenger":
                self._speak("أنا بالسيارة، اركب.")
                g["phaseSince"] = now; return
            home = self.e.home() or {}
            if self._gps_arrived(st, home.get("x"), home.get("y")):
                self._speak("وصلنا عالبيت.")
                if not self._once_tool("exitHomeRid", "exit_vehicle"): return
                self._once_tool("followHomeRid", "follow")
                return self.e.complete(g, "player_taken_home")
            if now - g.get("phaseSince", now) > self.DRIVE_TIMEOUT + 90: return self.e.fail(g, "take_home_timeout")
            return


_BRAND_AR = {"gas2go": "غاز تو غو", "fossoil": "فوس أويل"}
_COMPASS = ("بالشرق", "بالجنوب الشرقي", "بالجنوب", "بالجنوب الغربي", "بالغرب", "بالشمال الغربي", "بالشمال", "بالشمال الشرقي")


def _parse_station(reason):
    """"station:x,y,fuel,brand,distance,power,dx,dy" -> dict, or None."""
    if not str(reason or "").startswith("station:"): return None
    a = reason[8:].split(",")
    if len(a) != 8: return None
    try:
        return {"x": int(a[0]), "y": int(a[1]), "fuel": int(a[2]), "brand": a[3], "distance": int(a[4]), "power": a[5] == "1", "dx": float(a[6]), "dy": float(a[7])}
    except ValueError:
        return None


def _direction(st):
    """In this world y grows to the south."""
    return _COMPASS[int(round(math.atan2(st["dy"], st["dx"]) / (math.pi / 4))) % 8]


def _count_line(reason):
    """"count:N:brand,brand" -> what she says."""
    part = str(reason).split(":", 2)
    n = int(part[1]) if len(part) > 1 and part[1].isdigit() else 0
    if n == 0: return "لسا ما بعرف ولا كازية."
    names = [_BRAND_AR[b] for b in (part[2].split(",") if len(part) > 2 else []) if b in _BRAND_AR]
    names = list(dict.fromkeys(names))
    tail = "، منها %s" % " و".join(names) if names and n > 1 else (" هي %s" % names[0] if names else "")
    if n == 1: return "بعرف كازية وحدة%s." % tail
    if n == 2: return "بعرف كازيتين%s." % tail
    return "بعرف %d كازيات%s." % (n, tail)


def _rough(n):
    if n < 15: return "قريبة كتير"
    return "حوالي %d متر" % (int(round(n / 10.0)) * 10)


@register
class StationQuery(GpsPlanner):
    """"وين أقرب كازية؟": she answers from memory and marks it on the GPS. She does not leave."""
    intent = "station_query"

    def _answer(self, g, text):
        g["answer"] = text                                               # the chat shows this too: he asked there
        self._speak(text)

    def tick(self, now):
        g = self.goal
        if not g.get("markRid"):
            self._action("markRid", "sol_fuel", g.get("markOption") or ("count" if (g.get("slots") or {}).get("ask") in ("count", "count_map") else "mark"))
            if not g.get("phaseSince"): g["phaseSince"] = now
            if not g.get("markRid"): return self.e.wait(g, "cannot_ask_the_game")
            return
        res = self._action_result("markRid")
        if res == (True, "ranking"):                                            # she is measuring the roads: one route every few frames
            g.pop("markRid", None); g["markOption"] = "rank"
            res = None
            if now - g.get("phaseSince", now) <= 8: return
        if res is None:
            if now - g.get("phaseSince", now) > 8:
                self._answer(g, "مو متذكرة هلأ، اسألني كمان شوي.")
                return self.e.fail(g, "station_query_unanswered")
            return
        ok, reason = res
        if ok and str(reason).startswith("count:"):
            line = _count_line(reason)
            if (g.get("slots") or {}).get("ask") == "count_map": line = "بالخريطة كلها ما بعرف. " + line.replace("بعرف", "اللي مرينا منهن:", 1) if not line.startswith("لسا") else line
            self._answer(g, line)
            return self.e.complete(g, "stations_counted")
        st = _parse_station(reason) if ok else None
        if st is None:
            self._answer(g, "لسا ما مرينا من كازية بتذكرها.")
            return self.e.complete(g, "no_station_known")
        name = "كازية %s" % _BRAND_AR[st["brand"]] if st["brand"] in _BRAND_AR else "كازية"
        tail = " بس الكهربا مقطوعة عندها." if not st["power"] else ""
        self._answer(g, "أقرب وحدة بعرفها %s، %s %s منك. علّمتلك ياها عالـ GPS.%s" % (name, _rough(st["distance"]), _direction(st), tail))
        return self.e.complete(g, "station_marked")


# s95b tank check: the car SHE would fill (SolFuel: her last car within 15, her seat, the nearest to her), from the snapshot
TANK_FULL_PCT, TANK_TOP_UP_PCT = 99.0, 90.0
def her_tank(snap):
    """(litres, capacity, percent) of the car she would fill, or None. The car she sits in, else the nearest to her within 15."""
    s = snap or {}
    me = s.get("sol") or {}
    x, y = me.get("x"), me.get("y")
    if x is None or y is None: return None
    reach = 3.0 if me.get("inVehicle") else 15.0
    best, bd = None, reach * reach
    for v in list(s.get("vehicles") or []) + list(s.get("solVehicles") or []):
        if not isinstance(v, dict) or v.get("x") is None or v.get("y") is None: continue
        d = (v["x"] - x) ** 2 + (v["y"] - y) ** 2
        if d < bd: best, bd = v, d
    if best is None: return None
    fuel, cap = best.get("fuel"), best.get("fuelMax")
    if not isinstance(fuel, (int, float)) or not isinstance(cap, (int, float)) or cap <= 0: return None
    return (fuel, cap, 100.0 * fuel / cap)
def tank_gate(snap):
    """("full" | "top_up" | "go", percent as the game's panel shows it), or (None, None) when her car's tank is not known."""
    t = her_tank(snap)
    if t is None: return None, None
    shown = int(math.floor(t[2] + 1e-9))
    if t[2] >= TANK_FULL_PCT: return "full", shown
    if t[2] >= TANK_TOP_UP_PCT: return "top_up", shown
    return "go", shown
TANK_FULL_SAY = "السيارة مليانة (%d%%)، ما بدها تعبية."
TANK_TOP_UP_SAY = "فيها %d%%، رح كمّلها."

@register
class RefuelErrand(ErrandRoundTrip):
    """Takes a car to the nearest remembered pump, fills the car and/or a can with the game's own actions, comes back. On foot she fills a can only."""
    intent = "refuel_errand"
    PUMP_TIMEOUT = 260.0
    WALK_TIMEOUT = 900.0
    ACK_SECONDS = 10.0
    POLL_SECONDS = 3.0
    TELL = {
        "no_station_known": "لسا ما مرينا من كازية بتذكرها.", "stations_unavailable": "مو متذكرة وين الكازيات هلأ.", "no_power": "الكهربا مقطوعة، المضخة ما بتشتغل.",
        "no_can": "ما لقيت غالون أعبيه.", "no_car": "ما في سيارة قريبة أعبيها.", "no_gas_tank": "هالسيارة ما بقدر أعبيها.", "no_pump_near": "ما قدرت أقرب من المضخة.",
        "no_way_to_pump": "ما لقيت طريق للمضخة.", "no_way_round": "ما لقيت طريق من هون، وقفت.", "pump_too_far": "ما قدرت أصف جنب المضخة.", "pump_failed": "ما طلع بنزين من المضخة.", "refuel_unavailable": "ما عم بقدر أعبي هلأ.", "walking_unavailable": "ما بقدر أوصل مشي هلأ.",
        "no_vehicle_near": "ما لقيت سيارة آخدها.", "no_key": "ما معي مفتاح السيارة.", "no_fuel": "السيارة فاضية وما بتمشي.", "fix_off": "ما بقدر أعبي هلأ.", "no_sol": "ما بقدر هلأ.", "no_position": "ما بقدر هلأ.",
    }
    GENERIC = "ما قدرت أكمل المشوار."
    TELL = dict(TELL, **{                                         # s95 station_survey: why, from the game's own checks
        "survey_no_pump": "ما في ولا مضخة فيها بنزين وعليها كهربا بهالكازية.",
        "survey_no_pose": "ما في محل فاضي جنب المضخات، ما رح جرّب صف.",
        "survey_no_stand": "صفّيت، بس ما في محل وقّف فيه جنب غطا البنزين.",
        "survey_drive_failed": "ما قدرت وصّل السيارة لجنب المضخة، الطريق مسكّر.",
        "survey_no_cap": "ما عرفت وين غطا البنزين بهالسيارة.",
        "wrong_fuel": "هالسيارة ما بتمشي على بنزين.",
    })
    PARK_SAY = {                                                  # s95: said once each, while she moves the car
        "other_pump": "الخرطوم ما بيوصل من هالجهة، عم غيّر المضخة.",
        "other_side": "غطا البنزين مو جهة المضخة، عم صف من الجهة التانية.",
        "blocked": "في شي سادد الطريق، عم جرّب محل تاني.",
    }
    ALREADY_THERE = 14.0
    PARK_OFFSETS = ((0, 3), (3, 0), (0, -3), (-3, 0))           # beside the pump, one side after another

    def _clear_own_target(self):
        """The station or the way back must not stay on his GPS. A destination he picked himself is left alone."""
        self._action("clearRid", "sol_gps_clear", "errand")

    def _fail(self, g, why):
        key = str(why or "").split(":")[0]
        self._speak(self.TELL.get(key) or self.GENERIC)
        self._action("cancelRid", "sol_fuel", "cancel")
        self._clear_own_target()
        if g.get("exitRid"): self._once_tool("followRid", "follow")               # she got out for this: she does not stay at the pump
        return self.e.fail(g, why)

    def _next(self, g, phase, now):
        g["phase"] = phase; g["phaseSince"] = now; g["reason"] = phase

    def _ask(self, g, now, key, option):
        """Sends once. None while waiting; (ok, reason) when answered; ("timeout") becomes a spoken failure."""
        self._action(key, "sol_fuel", option)
        res = self._action_result(key)
        if res is None and now - g.get("phaseSince", now) > self.ACK_SECONDS: return (False, "refuel_unavailable")
        return res

    def _status(self, g, now):
        """One status request at a time; None until the game answers one."""
        if g.get("pollRid"):
            res = self._action_result("pollRid")
            if res is not None:
                g.pop("pollRid", None)
                return res
            if now - g.get("pollAt", now) <= self.ACK_SECONDS: return None
            g.pop("pollRid", None)                                  # lost: ask again
        if now - g.get("pollAt", 0) >= self.POLL_SECONDS:
            self._action("pollRid", "sol_fuel", "status"); g["pollAt"] = now
        return None

    def _park_status(self, g, now):
        if g.get("parkPollRid"):
            res = self._action_result("parkPollRid")
            if res is not None:
                g.pop("parkPollRid", None)
                return res
            if now - g.get("parkPollAt", now) <= self.ACK_SECONDS: return None
            g.pop("parkPollRid", None)
        if now - g.get("parkPollAt", 0) >= 0.5:
            self._action("parkPollRid", "sol_fuel", "park_status"); g["parkPollAt"] = now
        return None

    def _still_pumping(self, g, res, line):
        """Under way, and says so only when the game's action is really running on her."""
        if res == (True, "pumping") and not g.get("saidPumping"):
            g["saidPumping"] = True
            self._speak(line)
        return res is None or res in ((True, "pumping"), (True, "walking"), (True, "starting"))

    def _fix_on(self, name):
        import sol_fixes                                                         # s152: the lab file, else the main copy's file
        return sol_fixes.on(self.e.lua_dir, name)

    def _pump_in_reach(self, g, slots):
        """Already at the station in the car: she parks at the pump from here. The road is for getting to the station."""
        if not self._fix_on("refuel_short_hop") or slots.get("target") not in ("car", "both"): return False
        if ((self._perception() or {}).get("sol") or {}).get("currentVehicle") is None: return False
        d = g["destFields"]
        near = self._distance_to(d["x"], d["y"])
        return near is not None and near <= 30

    def _tank_read(self):
        """(litres, capacity) of the car nearest her, from the game's own report."""
        snap = W.load_snapshot(self.e.lua_dir) or {}
        who = snap.get("sol") or {}
        x, y = who.get("x"), who.get("y")
        if x is None or y is None: return None
        best, bd = None, 15 * 15
        for v in snap.get("vehicles") or []:
            if not isinstance(v, dict) or v.get("x") is None or v.get("y") is None or v.get("fuel") is None: continue
            d = (v["x"] - x) ** 2 + (v["y"] - y) ** 2
            if d < bd: best, bd = v, d
        return (best["fuel"], best.get("fuelMax")) if best else None

    def _say_tank(self, g):
        """Real numbers only: a reading that has not moved yet is not reported as a result."""
        before, after = g.pop("tankBefore", None), self._tank_read()
        if before and after and after[1] and after[0] > before[0]:
            self._speak("كان فيها %.1f، عبيتها لـ %.1f من %d." % (before[0], after[0], after[1]))
        else:
            self._speak("عبيت السيارة.")

    def _after_car(self, g, now):
        g.pop("saidPumping", None)
        self._next(g, "pump_can" if (g.get("slots") or {}).get("target") == "both" else "finish", now)

    def tick(self, now):
        g = self.goal; slots = g.get("slots") or {}
        phase = g.get("phase") or "resolve"
        if phase in ("homeward", "driving_back"):
            done = ErrandRoundTrip.tick(self, now)
            if g.get("status") == "failed": self._speak(self.GENERIC)
            if g.get("status") in ("failed", "completed"): self._clear_own_target()
            return done
        if not self._perception(): return self.e.wait(g, "waiting_perception")
        if not g.get("phaseSince"): g["phaseSince"] = now

        if phase == "resolve":
            res = self._ask(g, now, "findRid", g.get("findOption") or "find")
            if res == (True, "ranking"):
                g.pop("findRid", None); g["findOption"] = "rank"
                return
            if res is None: return
            ok, reason = res
            st = _parse_station(reason) if ok else None
            if st is None: return self._fail(g, reason if not ok else "no_station_known")
            if not st["power"]: return self._fail(g, "no_power")
            g["station"] = st
            brand = (" " + st["brand"]) if st["brand"] else ""
            g["destFields"] = {"x": st["x"], "y": st["y"], "name": "Gas station" + brand}
            return self._next(g, "check_can" if slots.get("target") in ("can", "both") else "leave", now)

        if phase == "check_can":
            res = self._ask(g, now, "canRid", "check_can")
            if res is None: return
            ok, reason = res
            if not ok:
                if slots.get("target") == "can": return self._fail(g, "no_can")
                slots["target"] = "car"
                self._speak("ما لقيت غالون، بعبي السيارة بس.")
            return self._next(g, "leave", now)

        if phase == "leave":
            topUp = None
            if slots.get("transport") != "foot" and slots.get("target") in ("car", "both"):          # s95b: her car's real tank, before any drive
                gate, pct = tank_gate(W.load_snapshot(self.e.lua_dir) or {})
                if gate == "full" and slots.get("target") == "car":
                    self._speak(TANK_FULL_SAY % pct)
                    return self.e.complete(g, "tank_full")
                if gate == "full":
                    slots["target"] = "can"
                    self._speak("السيارة مليانة (%d%%)، بعبي الغالون بس." % pct)
                elif gate == "top_up": topUp = pct
            if slots.get("transport") == "foot":
                self._speak("ماشي، رايحة مشي عالكازية.")
                return self._next(g, "walk", now)
            if self._pump_in_reach(g, slots):
                if topUp is not None: self._speak(TANK_TOP_UP_SAY % topUp)
                self._speak("الكازية قدامي، بصف جنب المضخة.")
                return self._next(g, "park_check", now)
            self._speak(TANK_TOP_UP_SAY % topUp if topUp is not None else "ماشي، رايحة عالكازية.")
            f = dict(g["destFields"]); f.update(action="drive", solo="1", speed=slots.get("speed") or "normal")
            self._gps(f)
            return self._next(g, "driving_out", now)

        if phase == "driving_out":
            st = self._gps_state()
            if st is None:
                if now - g.get("phaseSince", now) > 8: return self._fail(g, "gps_unconfirmed")
                return
            why = self._gps_failed(st)
            if why == "player_took_over": return self.e.fail(g, why)
            if why == "no_vehicle_near" and slots.get("target") in ("can", "both"):
                slots["target"] = "can"; slots["transport"] = "foot"
                self._speak("ما لقيت سيارة، بروح مشي وبعبي الغالون.")
                return self._next(g, "walk", now)
            d = g["destFields"]
            near = self._distance_to(d["x"], d["y"])
            if why and near is not None and near <= self.ALREADY_THERE:          # no road to draw when she's already at the station
                return self._next(g, "park_check" if slots.get("target") in ("car", "both") else "get_out", now)
            if why: return self._fail(g, why)
            if g.get("parkTries") and now - g.get("phaseSince", now) < 3: return    # a fresh order can read the last trip's "arrived" for a moment
            if st.get("result") == "arrived" or st.get("phase") == "arrived":         # the driver has stopped, not merely come close
                return self._next(g, "park_check" if slots.get("target") in ("car", "both") else "get_out", now)
            if now - g.get("phaseSince", now) > self.DRIVE_TIMEOUT: return self._fail(g, "outbound_timeout")
            return

        if phase == "park_check":
            res = self._ask(g, now, "parkRid", "car_near")
            if res is None: return
            ok, reason = res
            g.pop("parkRid", None)
            if ok: return self._next(g, "get_out", now)
            if reason != "pump_too_far": return self._fail(g, reason)
            if g.get("parkDrawn", 0) < 2:                                        # first with the drawn path, which knows the gap she needs to walk in
                g["parkDrawn"] = g.get("parkDrawn", 0) + 1
                g.pop("parkAskRid", None)
                return self._next(g, "parking", now)
            tries = g.get("parkTries", 0)
            if tries >= len(self.PARK_OFFSETS): return self._fail(g, reason)
            g["parkTries"] = tries + 1
            dx, dy = self.PARK_OFFSETS[tries]
            d = g["station"]
            self._gps({"action": "drive", "x": d["x"] + dx, "y": d["y"] + dy, "name": g["destFields"]["name"], "solo": "1", "car": "last", "speed": "slow"})
            return self._next(g, "driving_out", now)

        if phase == "parking":
            res = self._ask(g, now, "parkAskRid", "park")
            if res is None: return
            ok, reason = res
            g.pop("parkAskRid", None)
            if not ok:
                g["parkDrawn"] = 9
                if reason == "park_unavailable": return self._next(g, "park_check", now)
                return self._fail(g, reason)
            return self._next(g, "parking_wait", now)

        if phase == "parking_wait":
            res = self._park_status(g, now)
            if res is not None and res[0] and str(res[1]).startswith("parking:"):     # s95 station_survey: another side or pump, said once
                why = str(res[1]).split(":", 1)[1]
                said = g.setdefault("parkSaid", [])
                if why not in said:
                    said.append(why)
                    if self.PARK_SAY.get(why): self._speak(self.PARK_SAY[why])
                res = (True, "parking")
            if res is not None and not res[0] and str(res[1]).startswith("survey_"): return self._fail(g, res[1])
            if res is None or res == (True, "parking"):
                if now - g.get("phaseSince", now) > 130: return self._fail(g, "pump_too_far")
                return
            if not res[0]: return self._next(g, "park_check", now)
            return self._next(g, "park_check", now)

        if phase == "get_out":
            if not g.get("holdRid"): self._action("holdRid", "sol_fuel", "hold")      # he may be sitting in the car: she must not be seated again the moment she is out
            if ((self._perception() or {}).get("sol") or {}).get("currentVehicle") is None:
                return self._next(g, "pump_car" if slots.get("target") in ("car", "both") else "pump_can", now)
            self._once_tool("exitRid", "exit_vehicle")
            if now - g.get("phaseSince", now) > 15: return self._fail(g, "cannot_exit_vehicle")
            return

        if phase == "walk":
            res = self._ask(g, now, "walkRid", "walk")
            if res is None: return
            ok, reason = res
            if not ok: return self._fail(g, reason)
            return self._next(g, "walking", now)

        if phase == "walking":
            d = g["destFields"]
            dist = self._distance_to(d["x"], d["y"])
            if dist is not None and dist <= 4: return self._next(g, "pump_can", now)
            if now - g.get("phaseSince", now) > self.WALK_TIMEOUT: return self._fail(g, "walk_timeout")
            return

        if phase == "pump_car":
            res = self._ask(g, now, "carRid", "car")
            if res is None: return
            ok, reason = res
            if not ok: return self._fail(g, reason)
            if reason == "tank_full":
                self._speak("السيارة مليانة.")
                return self._after_car(g, now)
            g["tankBefore"] = self._tank_read()
            return self._next(g, "pumping_car", now)

        if phase == "pumping_car":
            res = self._status(g, now)
            if self._still_pumping(g, res, "عم عبي السيارة."):
                if now - g.get("phaseSince", now) > self.PUMP_TIMEOUT: return self._fail(g, "pump_failed")
                return
            if not res[0]: return self._fail(g, res[1])
            self._say_tank(g)
            return self._after_car(g, now)

        if phase == "pump_can":
            res = self._ask(g, now, "fillRid", "can")
            if res is None: return
            ok, reason = res
            if not ok: return self._fail(g, reason)
            if reason == "can_full": return self._next(g, "finish", now)
            return self._next(g, "pumping_can", now)

        if phase == "pumping_can":
            res = self._status(g, now)
            if self._still_pumping(g, res, "عم عبي الغالون."):
                if now - g.get("phaseSince", now) > self.PUMP_TIMEOUT: return self._fail(g, "pump_failed")
                return
            if not res[0]: return self._fail(g, res[1])
            return self._next(g, "finish", now)

        if phase == "finish":
            if slots.get("transport") == "foot":
                self._speak("عبيت الغالون، جايتك.")
                self._once_tool("followRid", "follow")
                self._clear_own_target()
                return self.e.complete(g, "refuel_done_on_foot")
            g["phase"] = "homeward"; g["phaseSince"] = now
            return
