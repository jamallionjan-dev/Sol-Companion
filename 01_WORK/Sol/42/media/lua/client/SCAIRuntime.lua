-- SPDX-License-Identifier: MIT
SurvivorCompanion=SurvivorCompanion or {}
local SC=SurvivorCompanion
SC.AIRuntime=SC.AIRuntime or {}
local R=SC.AIRuntime
R.PROTOCOL="sol-ai-1";R.SCHEMA=1
R.POLL_MS=250;R.PERCEPTION_MS=750;R.HEARTBEAT_MS=5000
R.MAX_CRITICAL_QUEUE=32;R.MAX_REQUEST_CACHE=128
local S={started=false,sessionId=nil,worldId=nil,seq=0,inFlight=nil,deferredTool=nil,q={},perception=nil,cache={},order={},pollAt=0,perceptionAt=0,heartbeatAt=0}

local function now()
 if SC.GameplayUtil and type(SC.GameplayUtil.nowMs)=="function" then
  local ok,v=pcall(SC.GameplayUtil.nowMs);if ok and type(v)=="number" then return v end
 end
 if type(getTimestampMs)=="function" then local ok,v=pcall(getTimestampMs);if ok and type(v)=="number" then return v end end
 return 0
end

local function worldId()
 if type(getCurrentSaveName)=="function" then
  local ok,v=pcall(getCurrentSaveName);if ok and v~=nil and tostring(v)~="" then return tostring(v) end
 end
 if type(getWorld)=="function" then
  local ok,w=pcall(getWorld)
  if ok and w and type(w.getWorld)=="function" then
   local wok,v=pcall(w.getWorld,w);if wok and v~=nil and tostring(v)~="" then return tostring(v) end
  end
 end
 return nil,"world_identity_unavailable"
end

local function player()
 if type(getSpecificPlayer)~="function" then return nil end
 local ok,v=pcall(getSpecificPlayer,0);return ok and v or nil
end

local function actor()
 if type(SC.Registry)~="table" or type(SC.Registry.living)~="function" then return nil end
 local ok,l=pcall(SC.Registry.living);if not ok or type(l)~="table" or #l~=1 then return nil end
 return l[1]
end

local function runtime(a)
 if not a or type(SC.Registry)~="table" or type(SC.Registry.idOf)~="function" or type(SC.Registry.byId)~="function" then return nil end
 local id=SC.Registry.idOf(a);if not id then return nil end
 local rec=SC.Registry.byId(id);return type(rec)=="table" and rec.runtime or nil
end

local function frame(t,p,req)
 S.seq=S.seq+1
 return {protocol=R.PROTOCOL,schema=R.SCHEMA,sessionId=S.sessionId,worldId=S.worldId,sequence=S.seq,requestId=req,timestampMs=now(),type=t,payload=p or {}}
end

local function critical(t,p,req)
 local item={type=t,payload=p or {},requestId=req}
 if t=="heartbeat" then
  for i=#S.q,1,-1 do
   if S.q[i].type=="heartbeat" then S.q[i]=item;return true,"coalesced" end
  end
 end
 if #S.q>=R.MAX_CRITICAL_QUEUE then
  local heartbeat=nil
  for i=1,#S.q do if S.q[i].type=="heartbeat" then heartbeat=i;break end end
  if heartbeat then table.remove(S.q,heartbeat) else return false,"critical_queue_full" end
 end
 S.q[#S.q+1]=item
 return true,"queued"
end

local function hasCriticalCapacity()
 if #S.q<R.MAX_CRITICAL_QUEUE then return true end
 for i=1,#S.q do if S.q[i].type=="heartbeat" then return true end end
 return false
end
local function sendIdle()
 if S.inFlight then return false,"busy" end
 if type(SC.AIMailbox)~="table" or type(SC.AIMailbox.write)~="function" then return false,"mailbox_unavailable" end
 local x
 if #S.q>0 then x=table.remove(S.q,1)
 elseif S.perception then x={type="perception_snapshot",payload=S.perception};S.perception=nil
 else return false,"empty" end
 local f=frame(x.type,x.payload,x.requestId)
 local ok,why=SC.AIMailbox.write(f)
 if ok==true then S.inFlight=f;return true,"sent" end
 if x.type=="perception_snapshot" then S.perception=x.payload else table.insert(S.q,1,x) end
 return false,why or "write_failed"
end

local function requestSignature(p)
  if type(SC.AIMailbox)~="table" or type(SC.AIMailbox.encodeFrame)~="function" then return nil,"mailbox_encoder_unavailable" end
  local body,why=SC.AIMailbox.encodeFrame({protocol=R.PROTOCOL,schema=R.SCHEMA,sessionId="",worldId="",sequence=0,timestampMs=0,type="tool_request",payload={tool=p.tool,arguments=type(p.arguments)=="table" and p.arguments or {}}})
  if not body then return nil,why or "signature_encode_failed" end
  return body
end
local function remember(id,result)
 if id==nil then return end
 local k=tostring(id)
 if S.cache[k]==nil then
  S.order[#S.order+1]=k
  if #S.order>R.MAX_REQUEST_CACHE then local old=table.remove(S.order,1);S.cache[old]=nil end
 end
 S.cache[k]=result
end

local function valid(f)
 if type(f)~="table" then return false,"frame_not_table" end
 if f.protocol~=R.PROTOCOL then return false,"protocol_mismatch" end
 if tonumber(f.schema)~=R.SCHEMA then return false,"schema_mismatch" end
 if tonumber(f.sequence)==nil then return false,"sequence_missing" end
 if tostring(f.sessionId or "")~=tostring(S.sessionId or "") then return false,"stale_session" end
 if tostring(f.worldId or "")~=tostring(S.worldId or "") then return false,"stale_world" end
 if type(f.type)~="string" then return false,"type_missing" end
 return true
end

local function reject(f,why)
 critical("error",{code=why,inboundType=type(f)=="table" and f.type or nil},type(f)=="table" and f.requestId or nil)
end

local function ack(f)
 local p=type(f.payload)=="table" and f.payload or {}
 local n=tonumber(p.ackSequence)
 if not S.inFlight then return false,"ack_without_inflight" end
 if n==nil or n~=tonumber(S.inFlight.sequence) then return false,"ack_sequence_mismatch" end
 S.inFlight=nil;sendIdle();return true,"acked"
end

local function say(f)
 local a=actor();if not a then return false,"actor_missing" end
 local p=type(f.payload)=="table" and f.payload or {};local text=p.text
 if type(text)~="string" or text=="" then return false,"text_missing" end
 if #text>2048 then text=string.sub(text,1,2048) end
 if type(SC.GameplayUtil)~="table" or type(SC.GameplayUtil.say)~="function" then return false,"speech_unavailable" end
 local ok,v=pcall(SC.GameplayUtil.say,a,text);if not ok then return false,"speech_exception" end
 return v==true,v==true and "spoken" or "speech_rejected"
end

local function tool(f)
  local id=f.requestId;if id==nil then reject(f,"request_id_missing");return false,"request_id_missing" end
  local k=tostring(id)
  local p=type(f.payload)=="table" and f.payload or {}
  local sig,sigWhy=requestSignature(p)
  if not sig then reject(f,sigWhy);return false,sigWhy end
 if not hasCriticalCapacity() then S.deferredTool=f;return true,"deferred_backpressure" end
  local cached=S.cache[k]
 if cached then
   if cached.signature~=sig then
    local conflict={protocol=R.PROTOCOL,schema=R.SCHEMA,requestId=k,tool=p.tool,accepted=false,status="rejected",reason="request_id_conflict"}
    critical("tool_result",conflict,id);return false,"request_id_conflict"
  end
  critical("tool_result",cached.result,id);return true,"replayed"
 end
 local req={requestId=id,tool=p.tool,arguments=type(p.arguments)=="table" and p.arguments or {}}
 local a=actor();local result
 if type(SC.AIToolGateway)~="table" or type(SC.AIToolGateway.execute)~="function" then
  result={protocol=R.PROTOCOL,schema=R.SCHEMA,requestId=k,accepted=false,status="rejected",reason="tool_gateway_unavailable"}
 else
  local ok,v=pcall(SC.AIToolGateway.execute,a,req,player())
  result=ok and v or {protocol=R.PROTOCOL,schema=R.SCHEMA,requestId=k,tool=req.tool,accepted=false,status="rejected",reason="tool_gateway_exception"}
 end
 remember(id,{signature=sig,result=result});critical("tool_result",result,id);return true,"tool_processed"
end

local function inbound(f)
 local ok,why=valid(f);if not ok then reject(f,why);return false,why end
 if f.type=="ack" then return ack(f) end
 if f.type=="ping" then local q,w=critical("heartbeat",{replyTo=f.requestId,pong=true,health=R.health()},f.requestId);return q,w end
 if f.type=="say" then local s,w=say(f);if not s then reject(f,w) end;return s,w end
 if f.type=="tool_request" then return tool(f) end
 if f.type=="memory_write" or f.type=="memory_query" then reject(f,"not_implemented");return false,"not_implemented" end
 reject(f,"unsupported_message_type");return false,"unsupported_message_type"
end

local function poll()
 if S.deferredTool then return false,"deferred_tool_pending" end
 if type(SC.AIMailbox)~="table" or type(SC.AIMailbox.readNext)~="function" then return false,"mailbox_unavailable" end
 local f,why=SC.AIMailbox.readNext();if not f then return false,why end
 return inbound(f)
end

local function perceive()
 local a=actor();if not a then return false,"actor_missing" end
 if type(SC.AIPerceptionAdapter)~="table" or type(SC.AIPerceptionAdapter.snapshot)~="function" then return false,"perception_unavailable" end
 local snap,why=SC.AIPerceptionAdapter.snapshot(a,player(),runtime(a));if not snap then return false,why end
 S.perception=snap;return true,"ready"
end

function R.start()
 if S.started then return true,"already_started" end
 local wid,worldWhy=worldId();if not wid then return false,worldWhy or "world_identity_unavailable" end
 S.worldId=wid;S.sessionId=tostring(S.worldId)..":"..tostring(now());S.seq=0;S.inFlight=nil;S.deferredTool=nil;S.q={};S.perception=nil;S.cache={};S.order={}
 local tools={}
 if type(SC.AIToolGateway)=="table" and type(SC.AIToolGateway.supported)=="function" then local ok,v=pcall(SC.AIToolGateway.supported);if ok and type(v)=="table" then tools=v end end
 local n=now();S.pollAt=n;S.perceptionAt=n;S.heartbeatAt=n+R.HEARTBEAT_MS;S.started=true
 critical("hello",{schema=R.SCHEMA,transport=type(SC.AIMailbox)=="table" and SC.AIMailbox.FORMAT or nil,tools=tools})
 sendIdle();return true,"started"
end

function R.stop()
 S.started=false;S.inFlight=nil;S.deferredTool=nil;S.q={};S.perception=nil
 return true
end

function R.tick()
 if not S.started then return false,"not_started" end
 local n=now()
 if n>=S.pollAt then
  S.pollAt=n+R.POLL_MS
  if S.deferredTool and hasCriticalCapacity() then
   local f=S.deferredTool
   S.deferredTool=nil
   tool(f)
  elseif not S.deferredTool then
   poll()
  end
 end
 if n>=S.perceptionAt then S.perceptionAt=n+R.PERCEPTION_MS;perceive() end
 if n>=S.heartbeatAt then S.heartbeatAt=n+R.HEARTBEAT_MS;critical("heartbeat",{health=R.health()}) end
 sendIdle();return true,"tick"
end

function R.health()
 local mailbox=nil
 if type(SC.AIMailbox)=="table" and type(SC.AIMailbox.health)=="function" then local ok,v=pcall(SC.AIMailbox.health);if ok and type(v)=="table" then mailbox=v end end
 return {protocol=R.PROTOCOL,schema=R.SCHEMA,started=S.started,sessionId=S.sessionId,worldId=S.worldId,sequence=S.seq,
  inFlightSequence=S.inFlight and S.inFlight.sequence or nil,inFlightType=S.inFlight and S.inFlight.type or nil,
  criticalQueued=#S.q,deferredTool=S.deferredTool~=nil,perceptionPending=S.perception~=nil,requestCache=#S.order,
  mailbox=mailbox}
end
return R
