"""s86 book_memory, Mind side (card_check WARN "address-book places in her memory"). Pairs with apply_s86_book_memory_lua.py, which
puts a compact copy of her address book into SolWorld_Snapshot.txt ("solBook": group, name, town, distance in tiles, one of 8
directions; no coordinates).

1. Her memory on the card (Chat._memory_text, the section after "ذاكرتك الآن:", which card_check keeps apart from CARD_BUDGET):
   one line "دفتر عناوينك (البعد منك): بيتنا (...)؛ <name> (<kind>، حوالي 1.2 كم بالشمال)؛ ... و<n> غيرهن." with "بيتنا" first and
   at most BOOK_CARD_MAX (8) entries. The cached card is rebuilt when the book's names change (not when distances change).
2. memory_answers.answer (the none path and s82's after-unknown path): "شو في عنا عناوين" / "شو بالدفتر" lists the book, "وين <name>"
   names a place of the book with its distance and direction, before the map's own "ما رحت لهونيك"; "شو الأماكن اللي حفظتيها" with
   no Mind places reads the book instead of "لسا ما حفظت ولا مكان". The book's names count as known names for the reply gate.
3. All behind switch book_memory (SolFixes_LAB.txt, read by the Mind as fix_on): off -> as before.
The fixed card (model_router) is not changed: CARD_BUDGET and the card's text stay as they are.
Blocks appended at the end of memory_answers.py and chat_service.py (redefinitions; needs s82 in memory_answers.py and s85 in
chat_service.py). Mind only; needs a Mind restart. In place, idempotent. Afterwards: card_check.py <mind> (no --write-doc needed).
usage: apply_s86_book_memory_mind.py <sol_mind dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
MARK = "# ---------------------------------------------------------------- s86 book_memory: her address book in her memory"
NEED = {"memory_answers.py": "# ---------------------------------------------------------------- s82 engine words, place questions, compact card",
        "chat_service.py": "# ---------------------------------------------------------------- s85 card budget, two orders in one line, exit first, far report"}


def append(path, block):
    t = open(path, encoding="utf-8", newline="").read()
    if MARK in t: return "kept"
    assert NEED[os.path.basename(path)] in t, "the stage before s86 is not installed in " + path
    nl = CRLF if CRLF in t else NL
    sep = "" if t.endswith(nl) else nl
    open(path, "w", encoding="utf-8", newline="").write(t + sep + nl + nl + (MARK + NL + block).replace(NL, nl))
    return "appended"


MA = r'''# The game writes a compact copy of her address book into the snapshot ("solBook", apply_s86_book_memory_lua.py): rows
# { g: group, n: name, c: town, st: home's street, ls: rental, lt: looted, d: tiles, dir: 1..8 = N..NW }, "from": sol | player.
# Her memory line for the card, and the answers to "شو في عنا عناوين" / "وين <name>" from it. No coordinates anywhere.
BOOK_ENABLED = [True]                                                          # chat_service sets it from the switch book_memory
BOOK_MAX = 8
BOOK_GROUP_AR = {"home": "بيتنا", "house": "بيت للبيع", "tourist": "مكان سياحي", "shop": "محل", "public": "خدمات", "stash": "مخبأ", "area": "منطقة"}
BOOK_LEASE_AR = "للإيجار"
BOOK_DIR_AR = ("بالشمال", "بالشمال الشرقي", "بالشرق", "بالجنوب الشرقي", "بالجنوب", "بالجنوب الغربي", "بالغرب", "بالشمال الغربي")
BOOK_LIST_WORDS = ("عناوين", "دفتر", "addresses", "address book")
BOOK_EMPTY = "دفتري فاضي، لسا ما شفت معك ولا ورقة فيها عنوان."
BOOK_NOT_ASKED = SELF + HOME + THE_CAR + WHERE_WE_ARE


def book_rows(snap):
    """The book's rows from the snapshot, or None when the game sent none (switch off, older game files)."""
    if not BOOK_ENABLED[0]: return None
    b = (snap or {}).get("solBook")
    if not isinstance(b, dict) or not isinstance(b.get("rows"), list): return None
    return [r for r in b["rows"] if isinstance(r, dict) and r.get("g") in BOOK_GROUP_AR]


def _book_total(snap, rows):
    n = (snap.get("solBook") or {}).get("n")
    return n if isinstance(n, int) and n >= len(rows) else len(rows)


def book_name(r):
    g, n = r.get("g"), str(r.get("n") or "").strip()
    if g == "home": return "بيتنا"
    if g in ("stash", "area"): return BOOK_GROUP_AR[g] + ((" " + n) if n else "")
    return n or BOOK_GROUP_AR[g]


def book_kind(r):
    g, c = r.get("g"), str(r.get("c") or "").strip()
    if g == "home": return str(r.get("st") or "").strip() or None
    k = (BOOK_LEASE_AR if r.get("ls") else BOOK_GROUP_AR[g]) if g == "house" else (None if g in ("stash", "area") else BOOK_GROUP_AR[g])
    if c and c not in book_name(r): k = (k + "، " + c) if k else c
    return k


def book_where(r):
    """Distance and direction in words ("حوالي 1.2 كم بالشمال"), None when the game sent no distance."""
    d = r.get("d")
    if not isinstance(d, (int, float)) or isinstance(d, bool): return None
    if d < 15: return "قريب"
    if d < 1000: how = "حوالي %d متر" % (int(round(d / 10.0)) * 10)
    else:
        km = round(d / 1000.0, 1)
        how = "حوالي %s كم" % (("%d" % km) if km == int(km) else ("%.1f" % km))
    k = r.get("dir")
    if isinstance(k, int) and not isinstance(k, bool) and 1 <= k <= 8: how += " " + BOOK_DIR_AR[k - 1]
    return how


def book_sig(snap):
    """What changes the card's memory: the names and the looted marks, not the distances."""
    rows = book_rows(snap)
    if rows is None: return None
    return (_book_total(snap, rows),) + tuple((r.get("g"), r.get("n"), bool(r.get("lt"))) for r in rows[:BOOK_MAX])


def book_line(snap, most=BOOK_MAX):
    """Her memory line for the card: بيتنا first, at most `most` entries, distances in words; None without the book."""
    rows = book_rows(snap)
    if rows is None: return None
    if not rows: return "دفتر عناوينك فاضي."
    bits = []
    for r in rows[:most]:
        info = [x for x in (book_kind(r), book_where(r), "انزار" if r.get("lt") else None) if x]
        bits.append(book_name(r) + ((" (" + "، ".join(info) + ")") if info else ""))
    who = "منك" if (snap.get("solBook") or {}).get("from") == "sol" else "منه"
    line = "دفتر عناوينك (البعد %s): %s" % (who, "؛ ".join(bits))
    total = _book_total(snap, rows)
    if total > len(bits): line += "؛ و%d غيرهن" % (total - len(bits))
    return line + "."


def book_list(snap):
    rows = book_rows(snap)
    if rows is None: return None
    if not rows: return BOOK_EMPTY
    total = _book_total(snap, rows)
    names = [book_name(r) + (" (انزار)" if r.get("lt") else "") for r in rows[:MAX_NAMED]]
    line = "بالدفتر عندي %s: %s" % (_plural(total, "عنوان واحد", "عنوانين", "عناوين"), "، ".join(names))
    return line + ("، وغيرهن." if total > len(names) else ".")


def _book_aliases(r):
    name = str(r.get("n") or "").strip()
    out = []
    head = name.split(",")[0].strip()                                          # "625 Dewey Street, Muldraugh" -> "625 Dewey Street"
    bare = re.sub(r"^\d+\s+", "", head).strip()                               #                               -> "Dewey Street"
    plain = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()                      # "E.P. Tools (Louisville)" -> "E.P. Tools"
    for a in (name, head, bare, plain):
        if a and a != book_name(r) and a not in out: out.append(a)
    return tuple(out)


def _book_words(s): return re.findall(r"[a-z0-9]+", str(s or "").lower())


def book_find(rest, rows):
    """The book's rows this spelling names (one, several, or none). Our home is the home question's."""
    cands = [r for r in rows if r.get("g") != "home"]
    if not rest or not cands: return []
    right = RG.match_name(rest, [(book_name(r), _book_aliases(r)) for r in cands])
    hits = [r for r in cands if book_name(r) == right] if right is not None else []
    if not hits:
        toks = [t for t in _book_words(rest) if len(t) >= 3]
        if toks: hits = [r for r in cands if all(t in _book_words(str(r.get("n") or "") + " " + str(r.get("c") or "")) for t in toks)]
    return hits


def book_answer(text, snap):
    """"شو في عنا عناوين" / "وين <name>" from her book; None when the question is not about it (or the game sent no book)."""
    rows = book_rows(snap)
    if rows is None: return None
    n = norm(text)
    if not n: return None
    if any(w in n for w in BOOK_LIST_WORDS) and (any(w in n for w in HOW_MANY) or any(w in n for w in WHICH) or _word(n, "عنا") or RG.is_question(text)):
        return book_list(snap)
    if any(w in n for w in BOOK_NOT_ASKED): return None
    who = "منّي" if (snap.get("solBook") or {}).get("from") == "sol" else "منك"
    for go in GO_WORDS:
        at = n.find(go)
        if at < 0: continue
        rest = re.sub(r"^(?:ـ|ال)\s*", "", n[at + len(go):]).strip(" .؟?!")
        rest = re.sub(r"\s+(?:من\s*هون|منا|مننا|منك|مني)$", "", rest).strip(" .؟?!")
        hits = book_find(rest, rows)
        if not hits: return None
        if len(hits) > 1: return "عندي بالدفتر أكتر من وحدة: %s. أيا وحدة؟" % "، ".join(book_name(r) for r in hits[:4])
        r = hits[0]
        kind, where = book_kind(r), book_where(r)
        name = book_name(r) + ((" (%s)" % kind) if kind else "")
        if where is None: line = "%s عندي بالدفتر، بس ما بعرف قديش بعيد هلأ." % name
        else: line = "%s %s %s." % (name, where, who)
        return line[:-1] + "، وانزار." if r.get("lt") else line
    return None


_answer_s85 = answer
NO_PLACES = "لسا ما حفظت ولا مكان."


def answer(text, snap, mem, stations=None, street_now=None, gaz=None, gardens=None):
    said = book_answer(text, snap)
    if said: return said
    said = _answer_s85(text, snap, mem, stations, street_now, gaz, gardens)
    if said == NO_PLACES and book_rows(snap): said = book_list(snap)
    return said


_known_names_s85 = known_names


def known_names(snap, mem, got=None, gaz=None):
    out = _known_names_s85(snap, mem, got, gaz)
    for r in book_rows(snap) or []:
        if r.get("g") != "home": out.append((book_name(r), _book_aliases(r)))
    return out


_facts_s85 = facts


def facts(snap, mem, got=None, gaz=None):
    text = _facts_s85(snap, mem, got, gaz)
    line = book_line(snap)
    return (text + "\n" + line).strip() if line else text
'''

CS = r'''# Her address book (game side: SolAddressBook.lua, action sol_address) reaches her memory on the card through the snapshot's
# "solBook" (switch book_memory): at most BOOK_CARD_MAX entries, بيتنا first, distances and directions in words, no coordinates.
# The memory section stays apart from CARD_BUDGET (card_check counts the card without it). The card is rebuilt when the book's
# names change. memory_answers answers "شو في عنا عناوين" / "وين <name>" from the same rows (none and after-unknown paths).
BOOK_CARD_MAX = 8
BOOK_FIX = "book_memory"
_memory_text_s85b = Chat._memory_text


def _memory_text_s86(self, snap, mem):
    """As before (s85 keeps the far_report line, what she did بغيابك), plus her address book (sol_address, the game's book):
    one compact line of at most BOOK_CARD_MAX entries."""
    text = _memory_text_s85b(self, snap, mem)
    MA.BOOK_ENABLED[0] = fix_on(self.dir, BOOK_FIX)
    try: line = MA.book_line(snap, BOOK_CARD_MAX)
    except Exception as e:
        self.log("chat: address book memory failed: %r" % (e,)); line = None
    return (text + " " + line) if line else text


_session_sheet_s85 = Chat._session_sheet


def _session_sheet_s86(self, snap, mem, acts):
    MA.BOOK_ENABLED[0] = fix_on(self.dir, BOOK_FIX)
    sig = MA.book_sig(snap)
    if sig != getattr(self, "_book_sig", None):
        if getattr(self, "_book_sig", None) is not None or sig is not None: self._sheet = None    # her book changed: new memory on the card
        self._book_sig = sig
    return _session_sheet_s85(self, snap, mem, acts)


_route_by_model_s85b = Chat._route_by_model


def _route_by_model_s86(self, history, c, key, snap, mem):
    MA.BOOK_ENABLED[0] = fix_on(self.dir, BOOK_FIX)                           # the book's answers only with the switch on
    return _route_by_model_s85b(self, history, c, key, snap, mem)


Chat._memory_text = _memory_text_s86
Chat._session_sheet = _session_sheet_s86
Chat._route_by_model = _route_by_model_s86
'''


if __name__ == "__main__":
    if len(sys.argv) != 2: print(__doc__); sys.exit(2)
    mind = sys.argv[1]
    for name in ("memory_answers.py", "chat_service.py"):
        assert os.path.isfile(os.path.join(mind, name)), "not a sol_mind dir: " + mind
    print("memory_answers", append(os.path.join(mind, "memory_answers.py"), MA))
    print("chat_service", append(os.path.join(mind, "chat_service.py"), CS))
    print("s86 book_memory (Mind) applied")
