"""Gate: every tonumber call must be safe under Kahlua.

Kahlua's BaseLib.tonumber (projectzomboid.jar, BaseLib.java:411-439) only takes the one-argument path when it receives
EXACTLY one argument. With two or more it does `(String) arg0` (line 419), so a number, boolean or table as the first
argument crashes ("Double cannot be cast to String"), and a string with a nil/non-number second argument returns nil.
Real Lua 5.1 (lupa) ignores both, so offline tests miss it. Two ways it happens:
  1. tonumber(f(...)) / tonumber(o:m(...)) / tonumber(...): the last argument is a call (or ...), so every value it
     returns is passed on. Safe form: tonumber((f(...))) -- the extra parentheses keep exactly one value.
  2. tonumber(x, b) where b is not a number literal.

The previous version matched `local function name(...) ... \\nend` with a regex; a one-line function before a helper
(`local function log(m) ... end` has no "\\nend") swallowed the helper, so `call` in SolSecretLoadout.lua was never
looked at. This version tokenizes Lua (strings, long strings, comments, numbers) and needs no knowledge of helpers:
it flags the call site itself.

usage: tonumber_check.py <dir or .lua file> [...]      exit 0 = clean, 1 = found (one line per site)
       tonumber_check.py --sites <dir>                 JSON list of sites (used by apply_s75_onevalue.py's generator)
Read-only."""
import glob, json, os, re, sys

KEYWORDS = {"and", "break", "do", "else", "elseif", "end", "false", "for", "function", "if", "in", "local", "nil", "not",
            "or", "repeat", "return", "then", "true", "until", "while", "goto"}
OPS3 = ("...",)
OPS2 = ("==", "~=", "<=", ">=", "..", "::", "//", "<<", ">>")
BINARY = {"+", "-", "*", "/", "%", "^", "..", "==", "~=", "<", "<=", ">", ">=", "and", "or", "&", "|", "~", "<<", ">>", "//"}
UNARY_START = {"not", "-", "#", "~"}


class Tok:
    __slots__ = ("kind", "text", "start", "end", "line")

    def __init__(self, kind, text, start, end, line):
        self.kind, self.text, self.start, self.end, self.line = kind, text, start, end, line

    def __repr__(self):
        return "%s:%r@%d" % (self.kind, self.text, self.line)


def _long_bracket(src, i):
    """At src[i] == '[': returns the end index (exclusive) of a long bracket [==[ ... ]==], or -1 if not one."""
    m = re.compile(r"\[(=*)\[").match(src, i)
    if not m:
        return -1
    close = "]" + m.group(1) + "]"
    j = src.find(close, m.end())
    if j < 0:
        raise SyntaxError("unfinished long string/comment at offset %d" % i)
    return j + len(close)


def tokenize(src):
    toks, i, n, line = [], 0, len(src), 1
    name_re = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
    num_re = re.compile(r"0[xX][0-9a-fA-F]+|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1; i += 1; continue
        if c in " \t\r\f\v":
            i += 1; continue
        if src.startswith("--", i):
            if i + 2 < n and src[i + 2] == "[":
                e = _long_bracket(src, i + 2)
                if e >= 0:
                    line += src.count("\n", i, e); i = e; continue
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "[" and i + 1 < n and src[i + 1] in "[=":
            e = _long_bracket(src, i)
            if e >= 0:
                toks.append(Tok("str", src[i:e], i, e, line)); line += src.count("\n", i, e); i = e; continue
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == "\\":
                    j += 1
                elif src[j] == "\n":
                    raise SyntaxError("unfinished string at line %d" % line)
                j += 1
            if j >= n:
                raise SyntaxError("unfinished string at line %d" % line)
            toks.append(Tok("str", src[i:j + 1], i, j + 1, line)); line += src.count("\n", i, j + 1); i = j + 1; continue
        m = num_re.match(src, i) if (c.isdigit() or (c == "." and i + 1 < n and src[i + 1].isdigit())) else None
        if m:
            toks.append(Tok("num", m.group(0), i, m.end(), line)); i = m.end(); continue
        m = name_re.match(src, i)
        if m:
            w = m.group(0)
            toks.append(Tok("kw" if w in KEYWORDS else "name", w, i, m.end(), line)); i = m.end(); continue
        for op in OPS3 + OPS2:
            if src.startswith(op, i):
                toks.append(Tok("op", op, i, i + len(op), line)); i += len(op); break
        else:
            toks.append(Tok("op", c, i, i + 1, line)); i += 1
    return toks


OPEN, CLOSE = {"(": ")", "[": "]", "{": "}"}, {")", "]", "}"}


def match_close(toks, k):
    """toks[k] is ( [ or {: index of its matching closer."""
    depth = 0
    for j in range(k, len(toks)):
        t = toks[j]
        if t.kind == "op" and t.text in OPEN:
            depth += 1
        elif t.kind == "op" and t.text in CLOSE:
            depth -= 1
            if depth == 0:
                return j
    raise SyntaxError("unbalanced bracket at line %d" % toks[k].line)


def split_args(toks, a, b):
    """Top-level comma split of toks[a:b] -> list of (start, end) index ranges. Blocks (function...end) count as depth."""
    args, depth, block, s = [], 0, 0, a
    for j in range(a, b):
        t = toks[j]
        if t.kind == "op" and t.text in OPEN: depth += 1
        elif t.kind == "op" and t.text in CLOSE: depth -= 1
        elif t.kind == "kw" and t.text in ("function", "if", "do", "repeat"): block += 1
        elif t.kind == "kw" and t.text in ("end", "until") and block: block -= 1
        elif depth == 0 and block == 0 and t.kind == "op" and t.text == ",":
            args.append((s, j)); s = j + 1
    if s < b or args:
        args.append((s, b))
    return args


def classify(toks, a, b):
    """Kind of the expression toks[a:b]: 'multi' (ends in a call or is ...), 'paren' (wrapped), or 'single'."""
    if a >= b:
        return "single"
    first = toks[a]
    if first.kind == "kw" and first.text == "function":
        return "single"
    if first.text in UNARY_START and first.kind in ("op", "kw"):
        return "single"
    depth, block = 0, 0
    for j in range(a, b):
        t = toks[j]
        if t.kind == "op" and t.text in OPEN: depth += 1
        elif t.kind == "op" and t.text in CLOSE: depth -= 1
        elif depth == 0 and t.text in BINARY and t.kind in ("op", "kw"):
            return "single"                                   # a binary expression yields exactly one value
    if b - a == 1:
        return "multi" if first.text == "..." else "single"
    last = toks[b - 1]
    if last.kind == "op" and last.text in (")", "}"):
        # find the opener of the trailing group
        depth = 0
        for j in range(b - 1, a - 1, -1):
            t = toks[j]
            if t.kind == "op" and t.text in CLOSE: depth += 1
            elif t.kind == "op" and t.text in OPEN:
                depth -= 1
                if depth == 0:
                    if j == a:
                        return "paren" if last.text == ")" else "single"     # (expr) or a table constructor
                    return "multi"                                            # f(...), o:m(...), f{...}
        return "single"
    if last.kind == "str":
        return "multi"                                        # f"..." (b - a > 1 here)
    return "single"


def sites(path, src=None):
    """Every tonumber call in a file: list of dicts {file, line, start, end, arg_start, arg_end, issue}."""
    if src is None:
        src = open(path, encoding="utf-8", errors="replace").read()
    toks = tokenize(src)
    out = []
    for k, t in enumerate(toks):
        if t.kind != "name" or t.text != "tonumber":
            continue
        if k > 0 and toks[k - 1].kind == "op" and toks[k - 1].text in (".", ":"):
            continue                                          # some table's own tonumber field
        if k > 0 and toks[k - 1].kind == "kw" and toks[k - 1].text == "function":
            continue                                          # local function tonumber(...) definition
        if k + 1 >= len(toks) or not (toks[k + 1].kind == "op" and toks[k + 1].text == "("):
            continue                                          # used as a value, or tonumber"5" (one literal)
        close = match_close(toks, k + 1)
        args = split_args(toks, k + 2, close)
        site = {"file": path, "line": t.line, "start": t.start, "end": toks[close].end,
                "text": src[t.start:toks[close].end]}
        if len(args) == 1:
            kind = classify(toks, args[0][0], args[0][1])
            if kind == "multi":
                site.update(issue="multi", arg_start=toks[args[0][0]].start, arg_end=toks[args[0][1] - 1].end)
                out.append(site)
        elif len(args) >= 2:
            base = args[1]
            ok = len(args) == 2 and base[1] - base[0] == 1 and toks[base[0]].kind == "num"
            if not ok:
                site.update(issue="base")
                out.append(site)
    return out


def wrapped(src):
    """src with every 'multi' site rewritten tonumber(X) -> tonumber((X)) (pure; for generators, never run by the gate)."""
    inserts = []                                              # original offsets, so nested sites stay correct
    for s in sites(None, src):
        if s["issue"] == "multi":
            inserts += [(s["arg_start"], "("), (s["arg_end"], ")")]
    for pos, ch in sorted(inserts, key=lambda p: -p[0]):
        src = src[:pos] + ch + src[pos:]
    return src


def lua_files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
        else:
            yield from sorted(glob.glob(os.path.join(p, "**", "*.lua"), recursive=True))


def check(*paths):
    found = []
    for f in lua_files(paths):
        try:
            for s in sites(f):
                what = ("last argument is a call: wrap it as tonumber((...))" if s["issue"] == "multi"
                        else "second argument is not a number literal")
                found.append("%s:%d %s  -- %s" % (os.path.relpath(f, paths[0]) if os.path.isdir(paths[0]) else os.path.basename(f),
                                                   s["line"], " ".join(s["text"].split())[:110], what))
        except SyntaxError as e:
            found.append("%s: cannot tokenize (%s)" % (f, e))
    return found


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--sites":
        allsites = []
        for f in lua_files(sys.argv[2:]):
            allsites.extend(sites(f))
        print(json.dumps(allsites, ensure_ascii=False, indent=1))
        sys.exit(0)
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    out = check(*sys.argv[1:])
    for l in out:
        print(l)
    print("TONUMBER CHECK", "OK" if not out else "FOUND %d" % len(out))
    sys.exit(1 if out else 0)
