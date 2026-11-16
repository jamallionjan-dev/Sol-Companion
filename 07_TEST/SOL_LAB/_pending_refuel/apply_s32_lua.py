"""Run only after the game is closed. Every container holding farm items is proposed for farming, not only those mostly full of them.
usage: apply_s32_lua.py <SolBaseScan.lua>"""
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
for a, b in [
("""local function classify(gu, cont)
""", """local function classify(gu, cont, rec)
"""),
("""        if call(gu.itemHasTag, it, "DIG_PLOW") or call(gu.itemHasTag, it, "COMPOST") or string.find(kind, "seed", 1, true)
""", """        if call(gu.itemHasTag, it, "DIG_PLOW") or call(gu.itemHasTag, it, "COMPOST") or call(gu.itemHasTag, it, "FERTILIZER") or string.find(kind, "seed", 1, true)
"""),
("""    if n.farming >= 1 and n.farming * 3 >= n.total then return "farming" end
""", """    if rec ~= nil then rec.farmItems = n.farming end                         -- a shed with one spade in it still has a spade
    if n.farming >= 1 and n.farming * 3 >= n.total then return "farming" end
"""),
("""        c.class = classify(gu, c.cont)
""", """        c.class = classify(gu, c.cont, c)
"""),
("""    for i, c in ipairs(byClass.farming) do if i <= 3 then regs[#regs + 1] = { cat = "farming", c = c } end end
""", """    local farmStores = 0
    for _, c in ipairs(containers) do
        if (c.farmItems or 0) >= 1 and farmStores < 16 then farmStores = farmStores + 1; regs[#regs + 1] = { cat = "farming", c = c } end
    end
"""),
("""    for _, c in ipairs(byClass.general) do pool[#pool + 1] = c end
""", """    for _, c in ipairs(byClass.general) do if (c.farmItems or 0) == 0 then pool[#pool + 1] = c end end
"""),
]:
    a, b = a.replace("\n", nl), b.replace("\n", nl)
    assert t.count(a) == 1, (a[:60], t.count(a))
    t = t.replace(a, b)
open(p, "w", encoding="utf-8", newline="").write(t)
print("applied to", p)
