"""Textures for the Sol settings window (section: Sol mind connection system)."""
import json, os
from PIL import Image, ImageDraw, ImageFont
g = {}; exec(open("gen_assets.py").read().split("L = json.load")[0], g)
box, text_img, font, hexc, vgrad, border, rrect_mask = g["box"], g["text_img"], g["font"], g["hexc"], g["vgrad"], g["border"], g["rrect_mask"]
AR, LA, OUT = g["AR"], g["LA"], g["OUT"]
DJ = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
L = json.load(open("settings_layout.json")); W, H = L["W"], L["H"]
WHITE=(240,246,250,255); MUTED=(146,169,184,255); AMBER=(237,188,49,255)
def save(im, n): im.save(os.path.join(OUT, n), optimize=True)
def T(s, size, col=WHITE, w=None, h=None, al="right", wt=500, lang="ar"):
    return text_img(s, font(AR if lang == "ar" else LA, size, wt), col, w, h, al if lang == "ar" else ("left" if al == "right" else al))
def withArrow(label, size, col, lang):
    t = T(label, size, col, wt=600, lang=lang)
    a = text_img("\u2197", ImageFont.truetype(DJ, size), col)
    o = Image.new("RGBA", (t.width + a.width + 4, max(t.height, a.height)), (0,0,0,0))
    o.alpha_composite(a, (0, (o.height-a.height)//2)); o.alpha_composite(t, (a.width+4, (o.height-t.height)//2)); return o
def button(w, h, label, prim=False, lang="ar", arrow=False, size=15):
    b = box(w, h, 10, hexc("#1aa0ff") if prim else hexc("#132738"), hexc("#0a78cc") if prim else hexc("#0d1c29"),
            hexc("#2ea3ff"), 1, glow=None if prim else hexc("#1a8de3", 90))
    t = withArrow(label, size, WHITE, lang) if arrow else T(label, size, wt=600, lang=lang)
    b.alpha_composite(t, ((w-t.width)//2, (h-t.height)//2)); return b
# ---- common chrome
bg = box(W, H, 16, hexc("#0b1a26", 250), hexc("#08141e", 248), hexc("#2a8fd8"), 1, glow=hexc("#1a8de3", 70))
d = ImageDraw.Draw(bg); d.line((1, 56, W-2, 56), fill=hexc("#1f4058")); d.line((22, L["divider"], W-22, L["divider"]), fill=hexc("#1f4058"))
save(bg, "st_bg.png")
for n, (w, h) in (("st_field_420", (420, 42)), ("st_field_556", (556, 42)), ("st_field_356", (356, 42))):
    save(box(w, h, 10, hexc("#07131c"), hexc("#07131c"), hexc("#36586d")), n + ".png")
save(box(556, 230, 12, hexc("#0a1722"), hexc("#0a1722"), hexc("#2c4a62")), "st_list.png")
save(box(540, 40, 8, hexc("#12334b"), hexc("#12334b"), hexc("#2ea3ff")), "st_rowsel.png")
save(box(556, 458, 10, hexc("#0c1d2b", 252), hexc("#0a1824", 252), hexc("#2ea3ff")), "st_dropdown.png")
save(text_img("\u25BE", ImageFont.truetype(DJ, 16), (180,200,214,255), 24, 24), "st_caret.png")
save(text_img("\u26A0", ImageFont.truetype(DJ, 16), AMBER, 24, 24), "st_warn.png")
for n, col in (("ok", (47,212,99,255)), ("err", (230,85,85,255)), ("work", AMBER), ("idle", (140,155,166,255))):
    im = Image.new("RGBA", (42, 42), (0,0,0,0)); ImageDraw.Draw(im).ellipse((0,0,41,41), fill=col); save(im.resize((14,14), Image.LANCZOS), "st_dot_%s.png" % n)
# ---- per language
TX = {
 "ar": {"title": "إعدادات Sol", "back": "‹ رجوع", "section": "نظام توصيل عقل سول", "sub": "من أين تأتي أفكار سول وردودها",
        "chips": {"api": "مفتاح API", "local": "نموذج محلي", "bridge": "الجسر", "manual": "يدوي", "none": "بلا عقل"},
        "provider": "المزوّد", "key": "المفتاح", "models": "النماذج المتاحة لهذا المفتاح", "base": "عنوان الخادم المحلي",
        "warnline": "النماذج المجانية المعلّمة قد تستخدم محادثاتك لتحسين النموذج", "fallback": "المصدر الاحتياطي إن فشل الأساسي",
        "keypage": "المفتاح", "fetch": "تطبيق المفتاح", "paste": "لصق", "test": "اختبار الاتصال", "save": "حفظ", "getkey": "احصل على مفتاح",
        "badges": {"free": "مجاني", "paid": "مدفوع", "tier": "طبقة مجانية", "local": "محلي", "unknown": "غير معروف", "unsup": "غير مدعوم بعد", "nochat": "ليس للمحادثة"},
        "fb": {"none": "بلا احتياطي", "manual": "يدوي", "ollama": "نموذج محلي (Ollama)"},
        "info": {"bridge": ["ChatGPT في المتصفح عبر Sol Link", "ثبّت Sol_Link.user.js في متصفح بلا جسر الأوامر،", "وافتح محادثة سول واضغط «اجعل هذه محادثة سول»."],
                 "manual": ["الوضع اليدوي للاختبار", "تظهر رسائلك في نافذة Sol Mind،", "وتكتب أنت رد سول هناك."],
                 "none": ["بلا عقل", "سول تنفّذ الأوامر الثابتة فقط،", "ولا ترد على المحادثة."]},
        "status": {"bridge_ok": "الجسر متصل: Sol Link يعمل", "bridge_not_connected": "Sol Link غير متصل: افتح محادثة سول في المتصفح",
                   "free_tier_app_only": "نماذج OpenCode المجانية تعمل داخل تطبيقه فقط", "blocked_by_firewall": "حجبت حماية الموقع الاتصال",
                   "idle": "لم يُختبر الاتصال بعد", "working": "جارٍ التنفيذ...", "models_ok": "تم جلب النماذج", "saved": "تم الحفظ",
                   "test_ok": "متصل", "opened": "فُتحت صفحة المفتاح في المتصفح", "key_removed": "حُذف المفتاح",
                   "invalid_key": "المفتاح غير صالح", "forbidden": "المفتاح لا يملك صلاحية", "not_found": "العنوان غير موجود",
                   "rate_limited": "تجاوزت حد الطلبات، حاول لاحقًا", "no_credit": "لا يوجد رصيد في الحساب", "unreachable": "تعذّر الوصول إلى المزوّد",
                   "timeout": "انتهت مهلة الاتصال", "bad_response": "رد غير مفهوم من المزوّد", "no_key": "أدخل مفتاحًا أو الصقه أولًا",
                   "clipboard_empty": "الحافظة فارغة", "no_model": "اختر نموذجًا أولًا", "empty_reply": "النموذج أعاد ردًا فارغًا",
                   "source_has_no_test": "هذا المصدر لا يحتاج اختبارًا", "no_base_url": "أدخل عنوان الخادم", "mind_offline": "Sol Mind غير مشغّل",
                   "unknown_error": "حدث خطأ", "unsupported_model": "هذا النموذج غير مدعوم بعد", "not_a_key": "الحافظة لا تحتوي مفتاحًا", "not_chat_model": "هذا النموذج ليس للمحادثة"}},
 "en": {"title": "Sol settings", "back": "‹ Back", "section": "Sol mind connection", "sub": "Where Sol's thoughts and replies come from",
        "chips": {"api": "API key", "local": "Local model", "bridge": "Bridge", "manual": "Manual", "none": "No mind"},
        "provider": "Provider", "key": "Key", "models": "Models available for this key", "base": "Local server address",
        "warnline": "Marked free models may use your chats to improve the model", "fallback": "Fallback source if the main one fails",
        "keypage": "Key", "fetch": "Apply key", "paste": "Paste", "test": "Test", "save": "Save", "getkey": "Get a key",
        "badges": {"free": "Free", "paid": "Paid", "tier": "Free tier", "local": "Local", "unknown": "Unknown", "unsup": "Not yet", "nochat": "Not for chat"},
        "fb": {"none": "No fallback", "manual": "Manual", "ollama": "Local model (Ollama)"},
        "info": {"bridge": ["ChatGPT in the browser through Sol Link", "Install Sol_Link.user.js in a browser without the command bridge,", "open Sol's chat and press 'Make this Sol's chat'."],
                 "manual": ["Manual test mode", "Your messages appear in the Sol Mind window,", "and you type Sol's reply there."],
                 "none": ["No mind", "Sol follows fixed orders only,", "and does not answer chat."]},
        "status": {"bridge_ok": "Bridge connected: Sol Link is running", "bridge_not_connected": "Sol Link not connected: open Sol's chat in the browser",
                   "free_tier_app_only": "OpenCode free models work only inside its app", "blocked_by_firewall": "The site's protection blocked the connection",
                   "idle": "Connection not tested yet", "working": "Working...", "models_ok": "Models loaded", "saved": "Saved",
                   "test_ok": "Connected", "opened": "Key page opened in the browser", "key_removed": "Key removed",
                   "invalid_key": "Invalid key", "forbidden": "Key has no permission", "not_found": "Address not found",
                   "rate_limited": "Rate limited, try later", "no_credit": "No credit on the account", "unreachable": "Provider unreachable",
                   "timeout": "Connection timed out", "bad_response": "Unreadable reply from provider", "no_key": "Enter or paste a key first",
                   "clipboard_empty": "Clipboard is empty", "no_model": "Choose a model first", "empty_reply": "Model returned an empty reply",
                   "source_has_no_test": "This source needs no test", "no_base_url": "Enter the server address", "mind_offline": "Sol Mind is not running",
                   "unknown_error": "Something went wrong", "unsupported_model": "This model is not supported yet", "not_a_key": "The clipboard does not hold a key", "not_chat_model": "This model is not for chat"}},
}
BADGE_COL = {"free": ((34,140,70), (47,212,99)), "paid": ((120,80,20), (237,156,50)), "tier": ((30,90,140), (46,163,255)),
             "local": ((60,70,120), (140,150,230)), "unknown": ((70,80,90), (150,160,170)), "unsup": ((70,40,40), (190,110,110)), "nochat": ((55,55,62), (130,130,145))}
for lang, tx in TX.items():
    head = Image.new("RGBA", (W, 130), (0,0,0,0))
    head.alpha_composite(T(tx["title"], 26, wt=700, w=300, h=40, lang=lang), (278 if lang == "ar" else 24, 8))
    head.alpha_composite(T(tx["back"], 17, MUTED, w=100, h=40, al="left" if lang == "ar" else "right", lang=lang), (24 if lang == "ar" else 476, 8))
    head.alpha_composite(T(tx["section"], 21, wt=700, w=556, h=34, lang=lang), (22, 70))
    head.alpha_composite(T(tx["sub"], 14, MUTED, w=556, h=22, lang=lang), (22, 102))
    save(head, "st_head_%s.png" % lang)
    for key, lab in tx["chips"].items():
        for on in (True, False):
            c = box(L["chips"]["w"], 38, 19, hexc("#1aa0ff") if on else hexc("#132738"), hexc("#0a78cc") if on else hexc("#0d1c29"), hexc("#1aa0ff") if on else hexc("#2c4a62"))
            t = T(lab, 15, WHITE if on else (214,226,234,255), wt=600 if on else 500, lang=lang)
            c.alpha_composite(t, ((c.width - t.width)//2, (38 - t.height)//2)); save(c, "st_chip_%s_%s_%s.png" % (key, "on" if on else "off", lang))
    for n, k in (("provider", "provider"), ("key", "key"), ("models", "models"), ("fallback", "fallback"), ("base", "base")):
        save(T(tx[k], 15, MUTED, w=556, h=24, lang=lang), "st_lbl_%s_%s.png" % (n, lang))
    wl = T(tx["warnline"], 13, AMBER, w=528, h=22, lang=lang); full = Image.new("RGBA", (556, 22), (0,0,0,0))
    warn = text_img("\u26A0", ImageFont.truetype(DJ, 15), AMBER, 24, 22)
    if lang == "ar": full.alpha_composite(wl, (0, 0)); full.alpha_composite(warn, (532, 0))
    else: full.alpha_composite(warn, (0, 0)); full.alpha_composite(wl, (28, 0))
    save(full, "st_warnline_%s.png" % lang)
    save(button(128, 42, tx["keypage"], lang=lang, arrow=True), "st_btn_keypage_%s.png" % lang)
    save(button(120, 42, tx["fetch"], lang=lang), "st_btn_fetch_%s.png" % lang)
    save(button(64, 42, tx["paste"], lang=lang, size=14), "st_btn_paste_%s.png" % lang)
    save(button(110, 40, tx["test"], lang=lang, size=14), "st_btn_test_%s.png" % lang)
    save(button(110, 40, tx["save"], prim=True, lang=lang), "st_btn_save_%s.png" % lang)
    gk = box(150, 32, 8, hexc("#132738"), hexc("#0d1c29"), hexc("#2c4a62")); t = withArrow(tx["getkey"], 13, (200,226,245,255), lang)
    gk.alpha_composite(t, ((150-t.width)//2, (32-t.height)//2)); save(gk, "st_btn_getkey_%s.png" % lang)
    for b, lab in tx["badges"].items():
        bgc, fg = BADGE_COL[b]; t = T(lab, 13, (255,255,255,255), wt=600, lang=lang)
        bb = box(t.width + 18, 24, 12, bgc+(255,), bgc+(255,), fg+(255,)); bb.alpha_composite(t, (9, (24-t.height)//2)); save(bb, "st_badge_%s_%s.png" % (b, lang))
    for k, lab in tx["fb"].items():
        save(T(lab, 16, WHITE, w=500, h=42, lang=lang), "st_fb_%s_%s.png" % (k, lang))
    for k, lines in tx["info"].items():
        im = box(556, 120, 12, hexc("#0e1d2b"), hexc("#0e1d2b"), hexc("#2c4a62"))
        im.alpha_composite(T(lines[0], 18, wt=700, w=520, h=36, lang=lang), (18, 10))
        im.alpha_composite(T(lines[1], 15, MUTED, w=520, h=30, lang=lang), (18, 48)); im.alpha_composite(T(lines[2], 15, MUTED, w=520, h=30, lang=lang), (18, 78))
        save(im, "st_info_%s_%s.png" % (k, lang))
    for k, lab in tx["status"].items():
        col = (47,212,99,255) if k in ("test_ok", "models_ok", "saved", "opened", "key_removed", "bridge_ok") else AMBER if k in ("working", "idle", "source_has_no_test") else (240,120,110,255)
        save(T(lab, 15, col, w=520, h=30, lang=lang), "st_status_%s_%s.png" % (k, lang))
# enable the settings button art (no change needed: btn_settings_* already exist)
print("ok", len([f for f in os.listdir(OUT) if f.startswith("st_")]), "settings textures")
