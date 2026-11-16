"""Generate the Sol panel textures (1:1 screen pixels). Layout constants are mirrored in SolPanel.lua."""
import json, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
OUT = "build/media/textures/SolUI"
AR = "fonts/NotoSansArabic.ttf"; LA = "fonts/NotoSans.ttf"
SS = 3  # supersampling

def font(path, size, wght=400):
    f = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    try: f.set_variation_by_axes([wght, 100] if path == AR else [wght, 100])
    except Exception: pass
    return f
def hexc(h, a=255): h = h.lstrip('#'); return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16), a)
def vgrad(w, h, c1, c2):
    g = Image.new("RGBA", (w, h)); px = g.load()
    for y in range(h):
        t = y / max(1, h-1); c = tuple(int(c1[i]*(1-t)+c2[i]*t) for i in range(4))
        for x in range(w): px[x, y] = c
    return g
def rrect_mask(w, h, r):
    m = Image.new("L", (w*SS, h*SS), 0); ImageDraw.Draw(m).rounded_rectangle((0,0,w*SS-1,h*SS-1), r*SS, fill=255)
    return m.resize((w, h), Image.LANCZOS)
def border(w, h, r, col, width=1):
    m = Image.new("RGBA", (w*SS, h*SS), (0,0,0,0))
    ImageDraw.Draw(m).rounded_rectangle((0,0,w*SS-1,h*SS-1), r*SS, outline=col, width=width*SS)
    return m.resize((w, h), Image.LANCZOS)
def box(w, h, r, c1, c2, bcol, bw=1, glow=None):
    im = vgrad(w, h, c1, c2); im.putalpha(Image.composite(Image.new("L",(w,h),c1[3]), Image.new("L",(w,h),0), rrect_mask(w,h,r)))
    if glow:  # inner glow along the border
        g = Image.new("RGBA", (w, h), (0,0,0,0)); gb = border(w, h, r, glow, 6).filter(ImageFilter.GaussianBlur(6))
        g.alpha_composite(gb); m = rrect_mask(w,h,r); g.putalpha(Image.composite(g.getchannel("A"), Image.new("L",(w,h),0), m)); im.alpha_composite(g)
    im.alpha_composite(border(w, h, r, bcol, bw))
    return im
def text_img(s, f, col, w=None, h=None, align="center"):
    tmp = ImageDraw.Draw(Image.new("RGBA",(10,10)))
    bb = tmp.textbbox((0,0), s, font=f)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    W = w or tw+4; H = h or th+8
    im = Image.new("RGBA", (W, H), (0,0,0,0)); d = ImageDraw.Draw(im)
    x = {"center": (W-tw)//2, "right": W-tw-2, "left": 2}[align] - bb[0]
    d.text((x, (H-th)//2 - bb[1]), s, font=f, fill=col)
    return im
def save(im, name): im.save(os.path.join(OUT, name), optimize=True)

L = json.load(open("layout.json"))
W, H = L["panelW"], L["panelH"]
# ---------- panel background ----------
bg = box(W, H, 16, hexc("#0b1a26", 246), hexc("#08141e", 244), hexc("#2a8fd8"), 1, glow=hexc("#1a8de3", 70))
hdr = vgrad(W-2, L["headerH"]-1, hexc("#0f2130"), hexc("#0a1824"))
hm = rrect_mask(W-2, L["headerH"]+20, 15).crop((0,0,W-2,L["headerH"]-1)); hdr.putalpha(hm); bg.alpha_composite(hdr, (1,1))
d = ImageDraw.Draw(bg); d.line((1, L["headerH"], W-2, L["headerH"]), fill=hexc("#1f4058"), width=1)
gx, gy, gs = L["gear"]
gear = text_img("\u2699", ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34), (200,208,214,255), gs, gs)
gm = gear.getchannel("A"); gg = vgrad(gs, gs, (242,245,247,255), (91,103,112,255)); gg.putalpha(gm)
sh = Image.new("RGBA",(gs,gs),(0,0,0,0)); sh.putalpha(gm.point(lambda v: v*0.6)); sh = Image.composite(Image.new("RGBA",(gs,gs),(0,0,0,160)), Image.new("RGBA",(gs,gs),(0,0,0,0)), gm)
bg.alpha_composite(sh, (gx, gy+2)); bg.alpha_composite(gg, (gx, gy))
tx, ty, tw, th = L["title"]
bg.alpha_composite(text_img("Sol", font(LA, 34, 700), (243,248,251,255), tw, th, "right"), (tx, ty))
dvx = L["divider"][0]; d.line((dvx, 14, dvx, L["headerH"]-14), fill=hexc("#2b4c64"), width=1)
cx, cy, cs = L["close"]
xi = Image.new("RGBA", (cs*SS, cs*SS), (0,0,0,0)); xd = ImageDraw.Draw(xi); p = 9*SS
xd.line((p, p, cs*SS-p, cs*SS-p), fill=(223,232,238,255), width=3*SS); xd.line((cs*SS-p, p, p, cs*SS-p), fill=(223,232,238,255), width=3*SS)
bg.alpha_composite(xi.resize((cs, cs), Image.LANCZOS), (cx, cy))
sx, sy, sw, shh = L["speech"]
bg.alpha_composite(box(sw, shh, 16, hexc("#152a3b"), hexc("#0e1d2b"), hexc("#33506a")), (sx, sy))
save(bg, "panel_bg.png")
# ---------- language pill ----------
px_, py_, pw, ph = L["lang"]
for on in ("ar", "en"):
    pill = box(pw, ph, ph//2, hexc("#0f2232"), hexc("#0f2232"), hexc("#2b4c64"))
    half = pw//2
    seg = box(half, ph, ph//2, hexc("#1aa0ff"), hexc("#0a78cc"), hexc("#1aa0ff"))
    if on == "ar": seg = seg.crop((0,0,half,ph)); pill.alpha_composite(seg, (0,0)); pill.alpha_composite(vgrad(10,ph,hexc("#1aa0ff"),hexc("#0a78cc")).crop((0,0,10,ph)), (half-10,0))
    else: pill.alpha_composite(seg, (half,0)); pill.alpha_composite(vgrad(10,ph,hexc("#1aa0ff"),hexc("#0a78cc")), (half,0))
    pill.putalpha(Image.composite(pill.getchannel("A"), Image.new("L",(pw,ph),0), rrect_mask(pw,ph,ph//2)))
    f = font(LA, 18, 700)
    pill.alpha_composite(text_img("AR", f, (255,255,255,255), half, ph), (0,0))
    pill.alpha_composite(text_img("EN", f, (229,237,243,255), half, ph), (half,0))
    save(pill, f"lang_{on}.png")
# ---------- buttons ----------
bw, bh = L["btnW"], L["btnH"]
save(box(bw, bh, 12, hexc("#132738"), hexc("#0d1c29"), hexc("#2c4a62")), "btn_normal.png")
save(box(bw, bh, 12, hexc("#132738"), hexc("#0d1c29"), hexc("#2ea3ff"), 1, glow=hexc("#1a8de3", 110)), "btn_primary.png")
save(border(bw, bh, 12, hexc("#4cb4ff"), 2), "btn_hover.png")
# icons
def load_icon(p, size):
    im = Image.open(p).convert("RGBA"); im.thumbnail((size, size), Image.LANCZOS); return im
icons = {k: load_icon(f"src/ico_{k}.png", 50) for k in ("chat","mic","gun","bag")}
def gen_icon(kind):
    S = 50*SS; im = Image.new("RGBA", (S,S), (0,0,0,0)); d = ImageDraw.Draw(im)
    if kind == "status":
        d.rounded_rectangle((4*SS,10*SS,46*SS,44*SS), 6*SS, fill=(150,40,40,255), outline=(222,120,100,255), width=2*SS)
        d.rectangle((21*SS,16*SS,29*SS,38*SS), fill=(255,236,236,255)); d.rectangle((14*SS,23*SS,36*SS,31*SS), fill=(255,236,236,255))
    elif kind == "orders":
        for r_, w_ in ((20,3),(12,3)): d.ellipse(((25-r_)*SS,(25-r_)*SS,(25+r_)*SS,(25+r_)*SS), outline=(70,180,255,255), width=w_*SS)
        d.ellipse((21*SS,21*SS,29*SS,29*SS), fill=(120,205,255,255))
        for a,b,c,e in ((25,0,25,9),(25,41,25,50),(0,25,9,25),(41,25,50,25)): d.line((a*SS,b*SS,c*SS,e*SS), fill=(70,180,255,255), width=3*SS)
    elif kind == "tasks":
        d.rounded_rectangle((9*SS,6*SS,41*SS,47*SS), 4*SS, fill=(160,112,60,255), outline=(214,165,98,255), width=2*SS)
        d.rounded_rectangle((18*SS,2*SS,32*SS,10*SS), 2*SS, fill=(190,195,200,255))
        for yy in (18,26,34): d.line((15*SS,yy*SS,35*SS,yy*SS), fill=(250,236,210,255), width=3*SS)
    elif kind == "settings":
        g = text_img("\u2699", ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 52*SS), (214,163,82,255), S, S)
        im.alpha_composite(g)
    return im.resize((50,50), Image.LANCZOS)
for k in ("status","orders","tasks","settings"): icons[k] = gen_icon(k)
labels = {
 "chat": ("مراسلة (نص)", "Message (text)", "chat"), "voice": ("تحدث (صوت)", "Talk (voice)", "mic"),
 "bag": ("الحقيبة", "Backpack", "bag"), "equip": ("التجهيز", "Loadout", "gun"),
 "status": ("الحالة", "Status", "status"), "orders": ("الأوامر", "Orders", "orders"),
 "tasks": ("المزيد", "More", "tasks"), "settings": ("الإعدادات", "Settings", "settings"),
}
for key, (ar, en, ic) in labels.items():
    for lang, s, fpath in (("ar", ar, AR), ("en", en, LA)):
        im = Image.new("RGBA", (bw, bh), (0,0,0,0))
        lab = text_img(s, font(fpath, 21, 600), (240,246,250,255))
        icon = icons[ic]; gap = 18
        total = lab.width + gap + icon.width; x0 = (bw - total)//2
        if lang == "ar":   # RTL: icon on the right
            im.alpha_composite(lab, (x0, (bh-lab.height)//2)); im.alpha_composite(icon, (x0+lab.width+gap, (bh-icon.height)//2))
        else:
            im.alpha_composite(icon, (x0, (bh-icon.height)//2)); im.alpha_composite(lab, (x0+icon.width+gap, (bh-lab.height)//2))
        save(im, f"btn_{key}_{lang}.png")
for lang, s, fpath in (("ar","قريباً",AR),("en","Soon",LA)):
    t = text_img(s, font(fpath, 13, 600), (255,255,255,255))
    b = box(t.width+14, 20, 10, hexc("#3a4f60"), hexc("#2b3c4a"), hexc("#5d7a8f")); b.alpha_composite(t, ((b.width-t.width)//2, (20-t.height)//2))
    save(b, f"soon_{lang}.png")
# ---------- speech + status line ----------
for lang, l1, l2, fpath, al in (("ar","مرحباً! أنا Sol","كيف أستطيع مساعدتك؟",AR,"right"),("en","Hi! I'm Sol","How can I help you?",LA,"left")):
    im = Image.new("RGBA", (sw-48, 84), (0,0,0,0)); f = font(fpath, 24, 400)
    im.alpha_composite(text_img(l1, f, (240,246,250,255), sw-48, 42, al), (0,0)); im.alpha_composite(text_img(l2, f, (240,246,250,255), sw-48, 42, al), (0,42))
    save(im, f"speech_{lang}.png")
for lang, av, un, fpath, al in (("ar","متاحة","غير متاحة",AR,"right"),("en","Available","Unavailable",LA,"left")):
    for state, s, col in (("on", av, (47,212,99,255)), ("off", un, (140,155,166,255))):
        t = text_img(s, font(fpath, 16, 500), col); dot = Image.new("RGBA",(12*SS,12*SS),(0,0,0,0)); ImageDraw.Draw(dot).ellipse((0,0,12*SS-1,12*SS-1), fill=col); dot = dot.resize((12,12), Image.LANCZOS)
        im = Image.new("RGBA", (sw-48, 26), (0,0,0,0))
        if lang == "ar": x = im.width - t.width - 20; im.alpha_composite(t, (x, (26-t.height)//2)); im.alpha_composite(dot, (im.width-14, 7))
        else: im.alpha_composite(dot, (2, 7)); im.alpha_composite(t, (20, (26-t.height)//2))
        save(im, f"status_{state}_{lang}.png")
# ---------- portraits ----------
P = Image.open("src/sol_portrait.png").convert("RGBA")
def ring(size, inner, ringw):
    m = size+24; im = Image.new("RGBA", (m*SS, m*SS), (0,0,0,0)); d = ImageDraw.Draw(im); o = 12*SS
    d.ellipse((o-4*SS, o-4*SS, o+size*SS+4*SS, o+size*SS+4*SS), outline=(26,156,255,90), width=8*SS)
    im = im.filter(ImageFilter.GaussianBlur(5*SS)); d = ImageDraw.Draw(im)
    d.ellipse((o, o, o+size*SS, o+size*SS), fill=(6,17,27,255), outline=(46,163,255,255), width=ringw*SS)
    im = im.resize((m, m), Image.LANCZOS)
    p = P.resize((inner, inner), Image.LANCZOS); off = 12 + (size-inner)//2; im.alpha_composite(p, (off, off))
    return im
save(ring(150, 134, 4), "portrait_ring.png")   # 174x174 (12px glow margin)
lau = ring(110, 96, 3)                           # 134x134
canvas = Image.new("RGBA", (134, 166), (0,0,0,0)); canvas.alpha_composite(lau, (0,0))
lbl = text_img("Sol", font(LA, 22, 600), (233,243,249,255), 134, 32); shl = Image.new("RGBA", lbl.size, (0,0,0,0)); shl.putalpha(lbl.getchannel("A").point(lambda v: int(v*0.8)))
canvas.alpha_composite(Image.composite(Image.new("RGBA",lbl.size,(0,0,0,255)), Image.new("RGBA",lbl.size,(0,0,0,0)), lbl.getchannel("A")), (0, 134)); canvas.alpha_composite(lbl, (0, 132))
save(canvas, "launcher.png")
for name, col in (("dot_on", (34,214,92,255)), ("dot_off", (120,132,140,255))):
    im = Image.new("RGBA", (24*SS, 24*SS), (0,0,0,0)); d = ImageDraw.Draw(im)
    d.ellipse((0,0,24*SS-1,24*SS-1), fill=(6,17,27,255)); d.ellipse((2*SS,2*SS,22*SS-1,22*SS-1), fill=col)
    save(im.resize((24,24), Image.LANCZOS), f"{name}.png")
print("ok", len(os.listdir(OUT)), "files")
