import os, sys
from lupa import lua51
from PIL import Image
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("package.path = 'build/media/lua/client/?.lua;' .. package.path")
L.globals()["TEXOK"] = lambda p: os.path.exists(p)
L.execute('''
DRAWS = {}
function getTexture(p) local f = "build/" .. p; if not TEXOK(f) then return nil end
  return { f = f, getWidth = function() return TEXW(f) end, getHeight = function() return TEXH(f) end } end
UI = { drawTextureScaled = function(self, t, x, y, w, h, a, r, g, b) DRAWS[#DRAWS + 1] = { t.f, x, y, w, h } end }
''')
L.globals()["TEXW"] = lambda f: Image.open(f).size[0]
L.globals()["TEXH"] = lambda f: Image.open(f).size[1]
L.execute(open("build/media/lua/client/SolTextData.lua", encoding="utf-8").read())
L.execute(open("build/media/lua/client/SolText.lua", encoding="utf-8").read())
G = L.globals(); T = G.SolText
res = []
def check(n, c): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n)
cps = lambda s: list(T.codepoints(s).values())
check("UTF-8 decode", cps("سول") == [0x633, 0x648, 0x644])
check("Kahlua-style chars decode (codes > 255)", list(T.codepoints(L.eval("{0x633, 0x648}")).values()) == [0x633, 0x648])
check("escape/unescape round trip", list(T.unescape(T.escape(L.table(*[0x645, 0x631, 65, 92]))).values()) == [0x645, 0x631, 65, 92])
sh = list(T.shape(T.codepoints("سول")).values())
check("shaping: seen initial, waw final, lam isolated", sh == [0xFEB3, 0xFEEE, 0xFEDD])
sh = list(T.shape(T.codepoints("لا")).values()); check("lam-alef ligature", sh == [0xFEFB])
sh = list(T.shape(T.codepoints("سلام")).values()); check("lam-alef final in a word", sh == [0xFEB3, 0xFEFC, 0xFEE1] or sh == [0xFEB3, 0xFEFC, 0xFEE2])
lines = T.wrap("مرحبا يا محمد، أنا سول وسأبقى معك في هذا العالم الخطير", 200, 0.7)
check("wrap produces several lines within width", len(lines) >= 2 and all(T.width(l, 0.7) <= 200 for l in lines.values()))
def render(text, w=520, scale=0.8, path=None):
    G.DRAWS = L.table(); h = T.draw(G.UI, text, 10, 5, w, L.eval("{scale=%s}" % scale))
    im = Image.new("RGBA", (w + 20, int(h) + 15), (12, 26, 38, 255))
    for d in G.DRAWS.values():
        t = Image.open(d[1]).convert("RGBA").resize((max(1, int(d[4])), max(1, int(d[5]))))
        im.alpha_composite(t, (int(d[2]), int(d[3])))
    return im
samples = ["مرحباً يا محمد! أنا سول، كيف أستطيع مساعدتك؟", "الحالة: صحة 100% — السلاح AK74M والمسافة 2.0", "لا تقلق، سأبقى قريبة منك (اتبعيني)", "Hello Sol, follow me to the car", "أنا سول، رفيقتك الناجية في عالم الزومبي."]
ims = [render(s) for s in samples]
out = Image.new("RGBA", (540, sum(i.height for i in ims) + 10), (12, 26, 38, 255)); y = 0
for i in ims: out.alpha_composite(i, (0, y)); y += i.height
out.save("/tmp/soltext.png")
print("%d/%d PASS" % (sum(res), len(res)))
