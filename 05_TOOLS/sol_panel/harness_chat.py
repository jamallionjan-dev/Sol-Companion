"""End-to-end: real SolPanel + SolText + SolChat (Lua 5.1) <-> real chat_service.py through real files."""
import os, sys, tempfile
sys.path.insert(0, "/home/claude/brain")
tmp = tempfile.mkdtemp(); os.environ["LOCALAPPDATA"] = tmp
from lupa import lua51
from PIL import Image, ImageDraw, ImageFont
import chat_service as CS, providers as P
LUA_DIR = tempfile.mkdtemp() + "/"
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.globals()["TEXOK"] = lambda n: os.path.exists("build/media/textures/SolUI/" + n + ".png")
L.globals()["TEXW"] = lambda n: Image.open("build/media/textures/SolUI/" + n + ".png").size[0]
L.globals()["TEXH"] = lambda n: Image.open("build/media/textures/SolUI/" + n + ".png").size[1]
L.globals()["LUA_DIR"] = LUA_DIR
L.execute(open("harness_stubs.lua").read())
L.globals()["PEXISTS"] = lambda p: os.path.exists(p)
L.globals()["PSIZE"] = lambda p, i: Image.open(p).size[i]
L.execute(r'''
local baseGet = getTexture
function getTexture(p)
  if p:find("SolText/") then local f = "build/" .. p; if not PEXISTS(f) then return nil end
    return { name = f, file = true, getWidth = function() return PSIZE(f, 0) end, getHeight = function() return PSIZE(f, 1) end } end
  return baseGet(p)
end
function ISPanel:setStencilRect() end
function ISPanel:clearStencilRect() end
function ISTextEntryBox:focus() self.focused = true end
''')
for f in ("SolTextData.lua", "SolText.lua", "SolPanel.lua", "SolChat.lua"):
    L.execute(open("build/media/lua/client/" + f, encoding="utf-8").read())
G = L.globals(); res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
replies = ["أهلاً محمد! أنا هنا، كيف أساعدك؟", "Sure, I'm right behind you."]
def ask(hist):
    return replies[0] if any("\u0600" <= ch <= "\u06ff" for ch in hist[-1]["text"]) else replies[1]
svc = CS.Chat(LUA_DIR, log=lambda m: None, ask=ask)
G.ONSTART()
lau = G.SolUI.launcher; lau.onMouseDown(lau, 50, 50); lau.onMouseUp(lau, 50, 50)
pan = G.SolUI.panel; pan.onMouseDown(pan, 440, 280); pan.onMouseUp(pan, 440, 280)
ch = G.SolUI.chat
check("chat button opens the Sol chat window (panel hidden)", ch is not None and ch.visible and not pan.visible)
check("no Sol Mind state yet -> mind_offline shown", (ch.prerender(ch), ch.code)[1] == "mind_offline")
svc.publish(); G.TIME = G.TIME + 400; ch.prerender(ch)
check("Sol Mind state present -> ready", ch.status == "idle")
ch.entry.text = "مرحبا يا سول"           # what the game entry box returns
check("send via Enter (onCommandEntered)", ch.entry.onCommandEntered(ch.entry) is None and ch.pending is not None)
req = open(LUA_DIR + CS.REQ, encoding="ascii").read()
check("request file is pure ASCII with escapes", req.isascii() and "\\u0645" in req)
check("entry cleared after send", ch.entry.text == "")
svc.poll_once(); G.TIME = G.TIME + 400; ch.prerender(ch)
check("Sol reply arrives in the window", ch.status == "ok" and len(ch.msgs) == 2 and ch.pending is None)
txt = "".join(chr(c) for c in ch.msgs[2].cps.values())
check("reply decoded exactly (Arabic)", txt == replies[0])
ch.entry.text = "follow me"; ch.onMouseUp(ch, 30, 640 - 16 - 20); svc.poll_once(); G.TIME = G.TIME + 400; ch.prerender(ch)
check("send button works; English reply for English message", len(ch.msgs) == 4 and "".join(chr(c) for c in ch.msgs[4].cps.values()) == replies[1])
ch.entry.text = "   "; check("empty message not sent", ch.sendCurrent(ch) is False)
def bad(h): raise P.ProviderError("rate_limited", "Groq 429")
svc.ask = bad; ch.entry.text = "رسالة"; ch.sendCurrent(ch); svc.poll_once(); G.TIME = G.TIME + 400; ch.prerender(ch)
check("provider error shown with its code", ch.status == "error" and ch.code == "rate_limited")
svc.ask = ask
ch.entry.text = "هل أنت هنا؟"; ch.sendCurrent(ch)
for _ in range(30): G.TIME = G.TIME + 400; ch.prerender(ch)
check("no Sol Mind reply in 8 s -> mind_offline", ch.code == "mind_offline" and ch.pending is None)
svc.poll_once(); G.TIME = G.TIME + 400; ch.prerender(ch)
check("Sol Mind back: the late reply clears 'offline'", ch.code != "mind_offline" and ch.status == "ok")
ch.onMouseUp(ch, 20, 20); check("close returns to the Sol panel", not ch.visible and pan.visible)
# render preview with a conversation
svc.poll_once(); pan.visible = False; G.SolUI.openChat(); G.TIME = G.TIME + 400
for t in ["أنا خائف قليلاً من الليل", "لا تقلق يا محمد، سأبقى قريبة منك وسنجد مكانًا آمنًا قبل الظلام."]:
    pass
G.DRAWS = L.table(); ch.entry.text = "اكتب هنا"; ch.prerender(ch); n_before = len(list(G.DRAWS.values())); ch.render(ch)
after = list(G.DRAWS.values())[n_before:]
ex, ey = ch.entry.x, ch.entry.y
glyphs = [d for d in after if d[1] == "tex"]
check("typed Arabic is drawn INSIDE the entry box (problem 6)", len(glyphs) >= 6 and all(ex <= d[3] <= ex + ch.entry.w and ey - 4 <= d[4] <= ey + ch.entry.h for d in glyphs))
im = Image.new("RGBA", (560, 640), (40, 62, 46, 255)); fnt = ImageFont.truetype("/home/claude/fonts/NotoSans.ttf", 15)
for d in G.DRAWS.values():
    if d[1] == "tex":
        name = d[2]; path = name if str(name).startswith("build/") else "build/media/textures/SolUI/" + name + ".png"
        t = Image.open(path).convert("RGBA").resize((max(1, int(d[5])), max(1, int(d[6]))))
        if d[7] < 1: t.putalpha(t.getchannel("A").point(lambda v: int(v * d[7])))
        im.alpha_composite(t, (int(d[3]), int(d[4])))
    elif d[1] == "rect":
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
        col = (int(d[7] * 255), int(d[8] * 255), int(d[9] * 255), int(d[6] * 255))
        dr.rectangle((d[2], d[3], d[2] + d[4] - 1, d[3] + d[5] - 1), fill=col); im.alpha_composite(ov)
    elif d[1] == "border":
        ImageDraw.Draw(im).rectangle((d[2], d[3], d[2] + d[4] - 1, d[3] + d[5] - 1), outline=(int(d[7] * 255), int(d[8] * 255), int(d[9] * 255), 255))
    elif d[1] == "text":
        ImageDraw.Draw(im).text((d[3], d[4]), d[2], font=fnt, fill=(240, 246, 250, 255))
im.convert("RGB").save("/tmp/chat_preview.png")
svc.hist.append({"role": "card", "text": "مسامير;1;قليل;amber^طعام;10;يكفي 1.4 يوم;red", "t": 0}); svc.publish()
G.TIME = G.TIME + 400; ch.lastPoll = 0; G.DRAWS = L.table(); ch.prerender(ch)
cards = [it for it in ch.layout(ch)[0].values() if it.card]
check("supplies table message parsed into rows (problem 8)", len(cards) == 1 and len(list(cards[0].card.values())) == 2)
dots = [d for d in G.DRAWS.values() if d[1] == "rect" and d[4] == 8 and d[5] == 8]
check("each row gets its colour dot (amber, red)", len(dots) >= 2)
# 2026-10-24 in game: a reply arrived while the window waited for a newer message -> it was hidden
L.execute("""
SolUI.chat.pending = 99; SolUI.chat.pendingAt = getTimestampMs()
SolUI.chat.msgs = { { role = 'user', cps = SolText.codepoints('a') }, { role = 'user', cps = SolText.codepoints('NEW'), local_ = true } }
SolUI.chat:applyState({ ack = '5', status = 'thinking', count = '2', m1 = 'user|a', m2 = 'sol|REPLY' })
""")
roles = [ (m.role, "".join(chr(c) for c in m.cps.values())) for m in G.SolUI.chat.msgs.values() ]
check("a reply that arrives while a newer message waits is SHOWN (not dropped)", ("sol", "REPLY") in roles and roles[-1] == ("user", "NEW"))
# microphone button inside the chat window (user: 'there is no voice button here')
L.execute("TOGGLED = 0; SolUI.voiceToggle = function() TOGGLED = TOGGLED + 1 end")
mic = L.eval("SolUI.chat") 
L.execute("local c = SolUI.chat; c.dragging = false; c:onMouseUp(122, c:getHeight() - 16 - 44 + 10)")
check("microphone button in the chat toggles the voice", L.eval("TOGGLED") == 1)
G.DRAWS = L.table(); L.execute("SolUI.voice = { listening = true }; SolUI.chat:render()")
reds = [d for d in G.DRAWS.values() if d[1] == "rect" and d[7] > 0.3 and d[8] < 0.3 and d[4] == 44]
check("while listening the microphone is red", len(reds) >= 1)
L.execute("SolUI.voice = nil")
import time as _t
L.execute("function FILL(m) local t = {} for i = 1, 30 do t[#t + 1] = { role = (i % 2 == 0) and 'sol' or 'user', cps = SolText.codepoints(m) } end SolUI.chat.msgs = t; SolUI.chat.layoutDirty = true end")
G.FILL("\\u0644\\u0627 \\u062A\\u0642\\u0644\\u0642 \\u064A\\u0627 \\u0645\\u062D\\u0645\\u062F " * 12)
L.globals()["PSIZE"] = lambda p, i: 20     # the test's texture stub opens PNG files; keep that cost out of the Lua timing
ch.prerender(ch); t0 = _t.time()
for _i in range(40): G.DRAWS = L.table(); ch.prerender(ch); ch.render(ch)
ms = (_t.time() - t0) / 40 * 1000
check("performance: a chat frame with 30 long messages stays cheap (%.1f ms here; was 68 ms before v0.7.2)" % ms, ms < 10)
G.DRAWS = L.table(); ch.render(ch)
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
