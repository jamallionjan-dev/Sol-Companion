"""Textures for Sol pages (the Living Fellows features shown inside the Sol window)."""
import os
from PIL import Image, ImageDraw
g = {}; exec(open("gen_assets.py").read().split("L = json.load")[0], g)
box, border, hexc, OUT = g["box"], g["border"], g["hexc"], g["OUT"]
def save(im, n): im.save(os.path.join(OUT, n), optimize=True)
bg = box(600, 640, 16, hexc("#0b1a26", 248), hexc("#08141e", 246), hexc("#2a8fd8"), 1, glow=hexc("#1a8de3", 70))
ImageDraw.Draw(bg).line((1, 56, 598, 56), fill=hexc("#1f4058")); save(bg, "pg_bg.png")
save(box(148, 38, 12, hexc("#1aa0ff"), hexc("#0a78cc"), hexc("#2ea3ff")), "pg_tab_on.png")
save(box(148, 38, 12, hexc("#132738"), hexc("#0d1c29"), hexc("#2c4a62")), "pg_tab_off.png")
save(box(418, 34, 10, hexc("#132738"), hexc("#0d1c29"), hexc("#2c4a62")), "pg_btn.png")
save(box(418, 34, 10, hexc("#16324a"), hexc("#11283b"), hexc("#4cb4ff"), 2), "pg_btn_hover.png")
save(box(418, 34, 10, hexc("#07131c"), hexc("#07131c"), hexc("#36586d")), "pg_combo.png")
save(box(418, 300, 10, hexc("#0c1d2b", 252), hexc("#0a1824", 252), hexc("#2ea3ff")), "pg_list.png")
save(box(418, 30, 8, hexc("#12334b"), hexc("#12334b"), hexc("#2ea3ff")), "pg_list_sel.png")
for on in (True, False):
    b = box(22, 22, 6, hexc("#07131c"), hexc("#07131c"), hexc("#2ea3ff") if on else hexc("#36586d"))
    if on:
        d = ImageDraw.Draw(b); d.line((5, 11, 9, 16), fill=hexc("#2fd463"), width=3); d.line((9, 16, 17, 6), fill=hexc("#2fd463"), width=3)
    save(b, "pg_tick_%s.png" % ("on" if on else "off"))
save(box(110, 32, 10, hexc("#132738"), hexc("#0d1c29"), hexc("#2c4a62")), "pg_back.png")
save(box(20, 16, 4, hexc("#f4d77a"), hexc("#c99a2e"), hexc("#ffe9a6")), "pg_skill_on.png")
save(box(20, 16, 4, hexc("#0b1822"), hexc("#0b1822"), hexc("#2c4a62")), "pg_skill_off.png")
print("page textures ok")
