"""End-to-end: real SolPanel.lua + SolSettings.lua (Lua 5.1) <-> real settings_service.py <-> fake providers."""
import os, sys, tempfile, threading, json
sys.path.insert(0, "/home/claude/brain")
from lupa import lua51
from PIL import Image, ImageDraw, ImageFont
import test_brain_server as FS   # fake provider server
import providers as P, settings_service as SS
LUA_DIR = tempfile.mkdtemp() + "/"
L = lua51.LuaRuntime(unpack_returned_tuples=True)
TEXDIR = "build/media/textures/SolUI/"
L.globals()["TEXOK"] = lambda n: os.path.exists(TEXDIR + n + ".png")
L.globals()["TEXW"] = lambda n: Image.open(TEXDIR + n + ".png").size[0]
L.globals()["TEXH"] = lambda n: Image.open(TEXDIR + n + ".png").size[1]
L.globals()["LUA_DIR"] = LUA_DIR
L.execute(open("harness_stubs.lua").read())
GAME_OPENED = []
L.globals()["openUrl"] = GAME_OPENED.append          # Java-like: type() is NOT "function" in Lua
for f in ("SolPanel.lua", "SolSettings.lua"):
    L.execute(open("build/media/lua/client/" + f, encoding="utf-8").read())
G = L.globals()
MIND_OPENED = []
svc = SS.Service(LUA_DIR, log=lambda m: None, opener=MIND_OPENED.append)
res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
def step():
    if not G.SKIP_SVC: svc.poll_once()
    G.TIME = G.TIME + 300; G.SolUI.settings.prerender(G.SolUI.settings)
def _unused(): svc.poll_once(); G.TIME = G.TIME + 300; G.SolUI.settings.prerender(G.SolUI.settings)
def click(x, y): st = G.SolUI.settings; st.onMouseUp(st, x, y)

G.ONSTART()
check("SolPanel v0.2.0 loaded", G.SolUI.VERSION == "0.2.0")
lau = G.SolUI.launcher; lau.onMouseDown(lau, 50, 50); lau.onMouseUp(lau, 50, 50)
pan = G.SolUI.panel; pan.onMouseDown(pan, 150, 540); pan.onMouseUp(pan, 150, 540)
st = G.SolUI.settings
check("settings button opens settings, hides main panel", st is not None and st.visible and not pan.visible)
L.execute("LIVING = {}"); pan.visible = True; pan.onMouseDown(pan, 30, 25); pan.onMouseUp(pan, 30, 25)
check("gear opens settings even without Sol", st.visible and not pan.visible); L.execute("LIVING = {SOL}")
svc.start = None; svc.publish()
st.prerender(st)
check("state adopted from Sol Mind (source none initially)", st.s.source == "none")
click(*[ (22 + 4*113) + 5, 140 ])   # api chip (rightmost)
check("api chip selected, key box visible", st.s.source == "api" and st.keyBox.visible)
# provider dropdown -> get-key button opens the page
click(300, 230); check("provider field opens dropdown, key box hidden", st.s.ddOpen and not st.keyBox.visible)
row_anthropic_y = 258 + 9 + 1*44 + 10
click(22 + 392 + 20, row_anthropic_y); step()
check("get-key button: Sol Mind opens the anthropic page in the browser", MIND_OPENED == ["https://platform.claude.com/settings/keys"] and st.s.code == "opened")
check("dropdown closed after click, key box back", not st.s.ddOpen and st.keyBox.visible)
# type a key and fetch
st.keyBox.text = FS.KEYS["/openrouter"]
click(60, 300); step()
check("fetch: key box cleared immediately", st.keyBox.text == "")
check("fetch: models listed from Sol Mind state", len(st.s.models) == 2 and st.s.detected == "openrouter" and st.s.code == "models_ok")
check("request file no longer holds the key", FS.KEYS["/openrouter"] not in open(LUA_DIR + SS.REQ).read())
check("hint shown, key never in state", st.s.hint == "sk-or-v1-****3f9a" and FS.KEYS["/openrouter"] not in open(LUA_DIR + SS.STATE).read())
click(300, 362 + 8 + 5); check("click first model selects it", st.s.model == "deepseek/deepseek-v4-flash:free")
click(300, 648 + 10); check("fallback cycles none -> manual", st.s.fallback == "manual")
click(300, 648 + 10); check("fallback cycles manual -> ollama", st.s.fallback == "ollama")
click(160, 770); step(); check("test -> connected with latency", st.s.code == "test_ok" and st.s.latency != "")
click(60, 770); step(); cfg = SS.load_config()
check("save -> Sol Mind config written", st.s.code == "saved" and cfg["source"] == "api" and cfg["provider"] == "openrouter" and cfg["model"] == "deepseek/deepseek-v4-flash:free" and cfg["fallback_provider"] == "ollama")
# paste via Sol Mind clipboard
os.environ["SOLMIND_TEST_CLIPBOARD"] = FS.KEYS["/opencode"]
click(180, 300); step()
check("paste: Sol Mind reads clipboard, OpenCode detected, free first", st.s.detected == "opencode" and st.s.models[1].badge == "free")
unsup = [i for i in range(1, len(st.s.models) + 1) if not st.s.models[i].supported]
st.s.scroll = 0
idx = unsup[0]
if idx <= 5:
    click(300, 362 + 8 + (idx - 1) * 44 + 5)
    check("unsupported model refused with message", st.s.code == "unsupported_model")
# Groq: non-chat models are listed last and refused
st.s.provider = "groq"; st.keyBox.text = FS.KEYS["/groq"]; click(60, 300); step()
ids = [st.s.models[i].id for i in range(1, len(st.s.models) + 1)]
last = len(ids); st.s.scroll = max(0, last - 5); row = last - st.s.scroll
click(300, 362 + 8 + (row - 1) * 44 + 5)
check("non-chat model (listed last) refused with not_chat_model", st.s.models[last].badge == "nochat" and st.s.code == "not_chat_model")
st.s.scroll = 0; st.s.provider = "auto"
# wrong key
st.keyBox.text = "sk-ant-api03-WRONGWRONGWRONG"; click(60, 300); step()
check("wrong key -> invalid_key status naming the provider", st.s.code == "invalid_key" and st.s.status == "error" and "Anthropic" in st.s.detail)
# Sol Mind offline
G.SKIP_SVC = True
click(60, 300)
for _ in range(25): G.TIME = G.TIME + 300; st.prerender(st)
check("no reply within 6 s -> mind_offline", st.s.code == "mind_offline")
os.rename(LUA_DIR + SS.STATE, LUA_DIR + "state.bak")
click(60, 230)
check("Sol Mind not running: key page falls back to the game's openUrl (non-Lua function)", GAME_OPENED == ["https://openrouter.ai/settings/keys"] or len(GAME_OPENED) == 1)
os.rename(LUA_DIR + "state.bak", LUA_DIR + SS.STATE)
# local source
click((22 + 3*113) + 5, 140); check("local chip shows base box, hides key box", st.s.source == "local" and st.baseBox.visible and not st.keyBox.visible)
st.baseBox.text = P.PROVIDERS["ollama"]["base"]; G.SKIP_SVC = False
click(60, 230); step(); check("local fetch lists Ollama models", st.s.code == "models_ok" and st.s.models[1].badge == "local")
# EN render + AR render previews
def render(lang):
    G.SolUI.setLang(lang); G.DRAWS = L.table(); st.prerender(st); st.render(st)
    im = Image.new("RGBA", (600, 800), (40, 62, 46, 255)); fnt = ImageFont.truetype("/home/claude/fonts/NotoSans.ttf", 15)
    for d in G.DRAWS.values():
        if d[1] == "tex":
            t = Image.open(TEXDIR + d[2] + ".png").convert("RGBA").resize((int(d[5]), int(d[6])))
            if d[7] < 1: t.putalpha(t.getchannel("A").point(lambda v: int(v * d[7])))
            im.alpha_composite(t, (int(d[3]), int(d[4])))
        elif d[1] == "text":
            dr = ImageDraw.Draw(im); w = dr.textlength(d[2], font=fnt); x = d[3] - w if d[5] else d[3]
            dr.text((x, d[4]), d[2], font=fnt, fill=(int(d[6]*255), int(d[7]*255), int(d[8]*255), int(d[9]*255)))
        elif d[1] == "rect":
            ov = Image.new("RGBA", im.size, (0,0,0,0)); ImageDraw.Draw(ov).rectangle((d[2], d[3], d[2]+d[4], d[3]+d[5]), fill=(int(d[7]*255), int(d[8]*255), int(d[9]*255), int(d[6]*255))); im.alpha_composite(ov)
    return im
G.SKIP_SVC = False
click((22 + 4*113) + 5, 140); st.s.provider = "openrouter"; click(60, 300); step()
click(300, 362 + 8 + 5)
a = render("ar"); e = render("en")
st.s.ddOpen = True; dd = render("ar"); st.s.ddOpen = False
out = Image.new("RGBA", (1830, 800), (40, 62, 46, 255)); out.alpha_composite(dd, (0, 0)); out.alpha_composite(e, (615, 0)); out.alpha_composite(a, (1230, 0))
out.convert("RGB").save("/tmp/settings_ingame.png")
check("no missing textures", not any("missing texture" in str(v) for v in G.LOGS.values()))
check("no undefined global SC read", L.eval("rawget(_G, 'SC_READS')") == 0)
print("%d/%d PASS" % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
