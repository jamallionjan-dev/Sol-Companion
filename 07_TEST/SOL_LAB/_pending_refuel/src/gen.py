import sys
BS = chr(92)
src = open(sys.argv[1], encoding="utf-8").read()
out = "".join(c if ord(c) < 128 else (BS + BS + "u%04X" % ord(c)) for c in src)
open(sys.argv[2], "w", encoding="ascii", newline="\n").write(out)
