"""Run only after the game is closed. The answer slot keeps the last few answers, so two senders cannot erase each other's. usage: apply_s10_lua.py <SolActions.lua>"""
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
a = """    if okw and w then w:write("ack=" .. id .. "\\nok=" .. tostring(res == true) .. "\\nreason=" .. tostring(reason or "") .. "\\n"); w:close() end
""".replace("\n", nl)
b = """    U._acks = U._acks or {}
    table.insert(U._acks, 1, "r" .. id .. "=" .. tostring(res == true) .. "|" .. tostring(reason or ""))
    if #U._acks > 8 then table.remove(U._acks) end
    if okw and w then w:write("ack=" .. id .. "\\nok=" .. tostring(res == true) .. "\\nreason=" .. tostring(reason or "") .. "\\n" .. table.concat(U._acks, "\\n") .. "\\n"); w:close() end
""".replace("\n", nl)
assert t.count(a) == 1, t.count(a)
open(p, "w", encoding="utf-8", newline="").write(t.replace(a, b))
print("applied to", p)
