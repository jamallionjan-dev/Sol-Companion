"""address_book: Sol's address book (DOCS/PLAN_address_book.md). Game closed only. Idempotent: a second run changes nothing.
  Lua   SolAddressBook.lua (new module: the three captures, her per-life book, the "Address Book" tab under Family, the click that drives)
        SolAuthority.lua   switch address_book in A.FIXES
        SolLife.lua        a respawn empties her book, beside the streets and the stations (solAddressBookForget)
        SolFixes_LAB.txt   address_book=on (every capture path is proven from the 42.22.2 files; see the module's header)
  Mind  chat_service.py    one action, sol_address: "shu fi 3anna 3anawin" -> list, "khdini 3al3inwan X" -> go, "khlasna mno" -> looted;
                           checked before the model, the far-away orders and the drive words, so "take me to the stash" is never a drive to a place
                           named "the stash"
        model_router.py    one card entry, address_book (no second drive action)
usage: apply_s69_address_book.py <client dir> <sol_mind dir>"""
import os, shutil, sys
CL, MIND = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (path, old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

# ---------------------------------------------------------------- Lua
shutil.copy(os.path.join(HERE, "SolAddressBook.lua"), os.path.join(CL, "SolAddressBook.lua"))
A = os.path.join(CL, "SolAuthority.lua")
if '"address_book"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "address_book",       -- Sol\'s address book: listings, stash maps and area maps she saw him read' + NL)
L = os.path.join(CL, "SolLife.lua")
edit(L, "    L.last = nil" + NL + "    log(\"she came back without what she had learned, death \" .. life.deaths)" + NL,
     "    local forgetBook = rawget(_G, \"solAddressBookForget\")                       -- address_book: her address book goes with her" + NL +
     "    if type(forgetBook) == \"function\" then pcall(forgetBook) end" + NL +
     "    L.last = nil" + NL + "    log(\"she came back without what she had learned, death \" .. life.deaths)" + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "address_book=" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("address_book=on" + CRLF)

# ---------------------------------------------------------------- Mind
CS = os.path.join(MIND, "chat_service.py")
ADDR = '''# address_book: Sol's address book lives in the game (SolAddressBook.lua, action sol_address). One action; these are its words.
ADDR_TOWNS = (("مولدرو", "Muldraugh"), ("مولدراو", "Muldraugh"), ("ويست بوينت", "West Point"), ("وست بوينت", "West Point"), ("روزوود", "Rosewood"),
              ("ريفرسايد", "Riverside"), ("لويفيل", "Louisville"), ("لويزفيل", "Louisville"), ("براندنبرغ", "Brandenburg"), ("اكرون", "Ekron"),
              ("إكرون", "Ekron"), ("ايرفينغتون", "Irvington"), ("إيرفينغتون", "Irvington"), ("مارش ريدج", "March Ridge"), ("ديكسي", "Dixie"),
              ("ايكو كريك", "Echo Creek"), ("إيكو كريك", "Echo Creek"))
ADDR_HOUSE = re.compile(r"(?:إعلان|اعلان)|للبيع|للإيجار|للايجار")
ADDR_STASH = re.compile(r"مخب[أاى]|غنيم|كنز")
ADDR_AREA = re.compile(r"منطق[ةه]")
ADDR_CUE = re.compile(r"عنوان|عناوين|دفترك|منطق[ةه]\s*(?:اللي|يلي)|دفتر\\s*(?:ال)?عناوين|(?:إعلان|اعلان)|للبيع|للإيجار|للايجار|مخب[أاى]|غنيم|كنز")
ADDR_LIST = re.compile(r"عناوين|دفترك|دفتر\\s*(?:ال)?عناوين")
ADDR_GO = re.compile(r"خديني|خذيني|وديني|وصليني|رجعيني|روحي|سوقي|امشي|خلينا\\s*نروح|بدي\\s*روح|يلا\\s+ع")
ADDR_LOOTED = re.compile(r"خلصنا\\s*(?:من|منو|منه)|زرنا|انزار|فضّ?يناه|فضّ?ينا|اخدنا\\s+(?:كل\\s*)?(?:شي|الغراض|الغنيمة)")
def address_intent(text):
    """The option for sol_address, or None when the sentence is not about her address book."""
    t = western_digits(text or "")
    if not ADDR_CUE.search(t): return None
    if ADDR_STASH.search(t) and ADDR_LOOTED.search(t): verb = "looted"
    elif ADDR_GO.search(t): verb = "go"
    elif ADDR_LIST.search(t): return "list"
    else: return None
    kind = "house" if ADDR_HOUSE.search(t) else "stash" if ADDR_STASH.search(t) else "area" if ADDR_AREA.search(t) else "any"
    words = re.findall(r"[A-Za-z]+|\\d+", t)
    for ar, en in ADDR_TOWNS:
        if ar in t: words.append(en)
    return "%s:%s:%s" % (verb, kind, " ".join(words).lower())
def address_reply(r):
    """Her own line from the game; a code (switch off, no answer yet) becomes a short line."""
    if not isinstance(r, dict) or r.get("ok") is None: return "لحظة، عم دوّر بالدفتر."
    why = str(r.get("reason") or "")
    if re.search(r"[\\u0600-\\u06FF]", why): return why
    return "ما قدرت إفتح الدفتر هلأ."
'''
GIVE = 'GIVE_ANY = re.compile(r"(أعطيني'
t = open(CS, encoding="utf-8", newline="").read()
if "def address_intent(" not in t:
    nl = CRLF if CRLF in t else NL
    assert t.count(GIVE) == 1
    t = t.replace(GIVE, ADDR.replace(NL, nl) + GIVE, 1)
    open(CS, "w", encoding="utf-8", newline="").write(t)
FAR = "        if self._far_order(text, snap, done, (history[-1].get(\"said\") if history else None) or text): return done" + NL
edit(CS, FAR,
     "        addr = address_intent(text)" + NL +
     "        if addr is not None:                                                     # address_book: one action, the book lives in the game" + NL +
     "            r = run_action(self.dir, \"sol_address\", addr, wait=3.0)" + NL +
     "            self._turn_action_results.append(r)" + NL +
     "            done.append(\"action sol_address %s -> %s\" % (addr, json.dumps(r, ensure_ascii=False)))" + NL +
     "            self.log(\"chat: address %s -> %s\" % (addr, r))" + NL +
     "            self._forced = address_reply(r)" + NL +
     "            return done" + NL + FAR)
edit(CS, "        if not self._model_first() or not history: return None" + NL + "        text = history[-1][\"text\"]" + NL,
     "        if not self._model_first() or not history: return None" + NL + "        text = history[-1][\"text\"]" + NL +
     "        if address_intent(text) is not None: return None                       # address_book: her own words run it, before any guess" + NL)
MR = os.path.join(MIND, "model_router.py")
edit(MR, '    "animal_stop":   ("توقف شغل الدجاج", "وقفي شغل الدجاج"),' + NL,
     '    "animal_stop":   ("توقف شغل الدجاج", "وقفي شغل الدجاج"),' + NL +
     '    "address_book":  ("دفتر عناوينها: بيوت للبيع، مخابئ ومناطق شافتها معه؛ بتقول شو فيه أو بتاخدو لعنوان منو", "شو في عنا عناوين"),' + NL)
edit(MR, '("صفيها", "park"), ', '("صفيها", "park"), ("شو الأماكن اللي سجلتيها", "address_book"), ')
print("applied")
