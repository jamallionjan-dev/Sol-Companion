"""The long supplies table: what one frame costs, before and after, measured by drawing calls on the real drawing code with the game's text stubbed."""
import os, shutil, subprocess, sys, tempfile, time
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
CL = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\lua\client"
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
current = open(os.path.join(CL, "SolChat.lua"), encoding="utf-8").read().replace("\r\n", "\n")
tmp = tempfile.mkdtemp(prefix="sol_chat_")
before = current
if "only the rows inside the window" not in current:
    for n in ("SolChat.lua", "SolCarry.lua", "SolActions.lua"): shutil.copy(os.path.join(CL, n), tmp)
    p = os.path.join(tmp, "SolActions.lua")
    t = open(p, encoding="utf-8", newline="").read()
    if "U._acks" not in t:
        subprocess.check_call([sys.executable, os.path.join(HERE, "apply_s10_lua.py"), p], stdout=subprocess.DEVNULL)
    subprocess.check_call([sys.executable, os.path.join(HERE, "apply_s12_lua.py"), os.path.join(tmp, "SolChat.lua"), os.path.join(tmp, "SolCarry.lua"), p], stdout=subprocess.DEVNULL)
    current = open(os.path.join(tmp, "SolChat.lua"), encoding="utf-8").read().replace("\r\n", "\n")
HARNESS = r"""
LINES, RECTS = 0, 0
T = {}
function T.wrap(cps, w, s) local out, cur = {}, {} for _, c in ipairs(cps) do cur[#cur + 1] = c; if #cur >= 28 then out[#out + 1] = cur; cur = {} end end if #cur > 0 or #out == 0 then out[#out + 1] = cur end WRAPS = (WRAPS or 0) + 1; return out end
function T.drawLine() LINES = LINES + 1 end
function T.draw() LINES = LINES + 1 end
function T.width(l) return #l * 7 end
function T.lineHeight() return 20 end
C = { frame = 0, header = 0, line = 0, border = 0, text = { 1, 1, 1 }, muted = { .5, .5, .5 }, amber = { 1, 1, 0 }, red = { 1, 0, 0 }, green = { 0, 1, 0 }, sol = 0, solLine = 0, me = 0 }
MSG = { title = {}, empty = {}, ready = {}, thinking = {} }
PAD, HEAD, INPUT_H, SMALL, SCALE = 10, 60, 40, .4, .5
UIFont = { Medium = 1 }
function rect() RECTS = RECTS + 1 end
function border() end
function getTexture() return nil end
function nowMs() return 0 end
function inside() return false end
U = {}
Chat = {}
Chat.__index = Chat
"""
def cut(src):
    a = src.index("local BUBBLE_W, BUBBLE_PAD, GAP"); b = src.index("-- error line under the list")
    return src[a:b] + "\n    return\nend\n"
def build(src):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(HARNESS); L.execute(cut(src))
    L.execute(r"""
function NEW(rows)
    local cps = {}
    for r = 1, rows do
        for _, c in ipairs({ 65, 66, 67, 59, 53, 59, 68, 69, 70, 59, 103, 114, 101, 101, 110 }) do cps[#cps + 1] = c end
        cps[#cps + 1] = 94
    end
    local c = setmetatable({ msgs = { { role = "card", cps = cps } }, scroll = 0, layoutDirty = true, status = "ok" }, Chat)
    c.getWidth = function() return 560 end; c.getHeight = function() return 640 end
    c.poll = function() end
    c.drawTextureScaled = function() end; c.drawRect = function() end; c.drawText = function() end
    c.setStencilRect = function() end; c.clearStencilRect = function() end
    return c
end
function FRAME(c) LINES, RECTS = 0, 0; c:prerenderBody(); return LINES end
""")
    return L
def frame_cost(L, rows, n=60):
    c = L.globals().NEW(rows); f = L.globals().FRAME
    first = f(c); t0 = time.perf_counter()
    for _ in range(n): f(c)
    return first, (time.perf_counter() - t0) / n * 1000, c
old = build(before if "only the rows inside" not in before else None) if "only the rows inside" not in before else None
new = build(current)
if old is not None:
    lb, tb, _ = frame_cost(old, 300)
    print("     before, 300 rows: %d text draws per frame, %.3f ms per frame in this harness" % (lb, tb))
la, ta, c = frame_cost(new, 300)
print("     after,  300 rows: %d text draws per frame, %.3f ms per frame in this harness" % (la, ta))
l20, _, _ = frame_cost(new, 20)
ck("after: a 300-row table draws no more than a screenful", la <= 70, la)
ck("after: 300 rows cost about what 20 rows cost", la <= l20 + 40, (la, l20))
if old is not None: ck("after: at least 5 times fewer text draws than before", la * 5 <= lb, (la, lb))
g = new.globals(); total = c.layoutCache[2] if False else None
c.scroll = 3000; n = g.FRAME(c); ck("scrolled to the middle: still only what is on screen, and something is", 0 < n <= 70, n)
c.scroll = 100000; n = g.FRAME(c); ck("scrolled past the end: the last rows are drawn", n > 0, n)
c.scroll = 0; g.WRAPS = 0; c.layoutDirty = True; g.FRAME(c); ck("a new message does not re-measure a table it already measured", g.WRAPS == 0, g.WRAPS)
c2 = g.NEW(300); c2.getWidth = new.eval("function() return 700 end"); g.WRAPS = 0; g.FRAME(c2); ck("a new width does measure again", g.WRAPS > 0, g.WRAPS)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
