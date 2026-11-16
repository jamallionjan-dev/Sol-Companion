import sys, json
def hx(s):
    try:
        return bytes.fromhex(s).decode("utf-8", "replace")
    except Exception:
        return "<badhex:%s>" % s[:40]
class P:
    def __init__(self, t):
        self.t = t
        self.i = 0
    def until(self, end):
        j = self.t.index(end, self.i)
        v = self.t[self.i:j]
        self.i = j + 1
        return v
    def val(self):
        c = self.t[self.i]
        self.i += 1
        if c == "M":
            n = int(self.until(":"))
            d = {}
            for _ in range(n):
                k = self.val()
                d[str(k)] = self.val()
            return d
        if c == "A":
            n = int(self.until(":"))
            return [self.val() for _ in range(n)]
        if c == "S":
            n = int(self.until(":"))
            v = self.t[self.i:self.i + n]
            self.i += n
            return hx(v)
        if c == "D":
            v = self.until(";")
            try:
                f = float(v)
                return int(f) if f.is_integer() else f
            except Exception:
                return v
        if c == "B":
            b = self.t[self.i]
            self.i += 1
            if b == "1":
                return True
            if b == "0":
                return False
            raise ValueError("invalid boolean at %d" % (self.i - 1))
        if c == "N":
            return None
        raise ValueError("unknown tag %r at %d: %s" % (c, self.i - 1, self.t[self.i - 1:self.i + 60]))
for path in sys.argv[1:]:
    print("==== " + path)
    lines = open(path, "r", encoding="utf-8-sig").read().splitlines()
    print("header=%r trailer=%r lines=%d" % (lines[0] if lines else None, lines[-1] if lines else None, len(lines)))
    if len(lines) < 2:
        continue
    p = P(lines[1].strip())
    try:
        print(json.dumps(p.val(), ensure_ascii=False, indent=1))
        if p.i != len(p.t):
            print("WARNING: %d unparsed chars remain" % (len(p.t) - p.i))
    except Exception as e:
        print("DECODE ERROR: %s" % e)
