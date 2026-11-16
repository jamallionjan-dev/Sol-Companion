import sys, os
try:
    from lupa import lua51 as L
except Exception:
    import lupa as L
lua = L.LuaRuntime(encoding=None)
check = lua.eval("function(s, n) local f, e = loadstring(s, n); if f then return nil end; return e end")
total = bad = warn = 0
for root in sys.argv[1:]:
    print("ROOT " + root)
    for dp, dn, fn in os.walk(root):
        for f in sorted(fn):
            if not f.lower().endswith(".lua"):
                continue
            p = os.path.join(dp, f)
            data = open(p, "rb").read()
            total += 1
            rel = os.path.relpath(p, root)
            notes = []
            if data.startswith(b"\xef\xbb\xbf"):
                notes.append("BOM")
                data = data[3:]
            if b"`n" in data:
                notes.append("literal-backtick-escape")
            err = check(data, ("@" + f).encode())
            if err is not None:
                bad += 1
                e = err.decode("utf-8", "replace") if isinstance(err, bytes) else str(err)
                print("ERROR  %s  %s" % (rel, e))
            elif notes:
                warn += 1
                print("WARN   %s  %s" % (rel, ",".join(notes)))
print("SUMMARY files=%d errors=%d warnings=%d" % (total, bad, warn))
sys.exit(1 if bad else 0)
