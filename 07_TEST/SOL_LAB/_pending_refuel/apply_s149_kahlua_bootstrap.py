"""Load s96's global Kahlua guard before the rest of Sol's client modules."""
import os
import sys

client = sys.argv[1]
path = os.path.join(client, "SCBootstrap.lua")
text = open(path, encoding="utf-8", newline="").read()
nl = chr(13) + chr(10) if chr(13) + chr(10) in text else chr(10)
old = 'require "SCCall"' + nl
new = old + 'require "SolKahluaGuard"' + nl + 'if type(SolKahluaGuard) == "table" then SolKahluaGuard.install() end' + nl
if new in text:
    print("kept Kahlua guard bootstrap")
elif text.count(old) == 1:
    open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new))
    print("installed Kahlua guard bootstrap")
else:
    raise RuntimeError(("SCBootstrap.lua", "expected one SCCall require", text.count(old)))
