"""Run only after the game is closed. The base scan also proposes a tool chest and a water store, and it counts a Watering Can as farming gear.
usage: apply_s23_lua.py <SolBaseScan.lua>"""
import sys
def patch(p, pairs):
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b in pairs:
        a, b = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a) == 1, (p, a[:70], t.count(a))
        t = t.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("applied to", p)
patch(sys.argv[1], [
("""    local n = { farming = 0, tool = 0, food = 0, total = #items }
""", """    local n = { farming = 0, tool = 0, food = 0, water = 0, total = #items }
"""),
("""            or string.find(kind, "wateringcan", 1, true) or string.find(kind, "compostbag", 1, true)
""", """            or string.find(kind, "wateredcan", 1, true) or string.find(kind, "wateringcan", 1, true) or string.find(kind, "compostbag", 1, true)
"""),
("""            if isTool then n.tool = n.tool + 1
            elseif method(it, "getCategory") == "Food" then n.food = n.food + 1 end
""", """            if isTool then n.tool = n.tool + 1
            elseif string.find(kind, "waterbottle", 1, true) or string.find(kind, "waterdispenser", 1, true) or string.find(kind, "bucketwater", 1, true) then n.water = n.water + 1
            elseif method(it, "getCategory") == "Food" then n.food = n.food + 1 end
"""),
("""    if n.tool >= 1 and n.tool * 2 >= n.total then return "tool" end
""", """    if n.tool >= 1 and n.tool * 2 >= n.total then return "tool" end
    if n.water >= 1 and n.water * 2 >= n.total then return "water" end
"""),
("""    local cls, byClass = {}, { farming = {}, food = {}, tool = {}, general = {}, empty = {} }
""", """    local cls, byClass = {}, { farming = {}, food = {}, tool = {}, water = {}, general = {}, empty = {} }
"""),
("""    for i, c in ipairs(byClass.farming) do if i <= 3 then regs[#regs + 1] = { cat = "farming", c = c } end end
""", """    for i, c in ipairs(byClass.farming) do if i <= 3 then regs[#regs + 1] = { cat = "farming", c = c } end end
    if byClass.tool[1] then regs[#regs + 1] = { cat = "tools", c = nearest(byClass.tool) } end
    if byClass.water[1] then regs[#regs + 1] = { cat = "water", c = nearest(byClass.water) } end
"""),
("""    for _, k in ipairs({ "farming", "tool", "food", "general", "empty" }) do if""", """    for _, k in ipairs({ "farming", "tool", "food", "water", "general", "empty" }) do if"""),
])
