"""s100 item_stacks: identical stateless items are ONE entry with a count.
Live (s99 notes): LF's inventory walk (SCGameplayUtil.inventoryItemsDeep) is capped at 240 entries, 180 from the root;
her ~500 loose 7.62x51 rounds are 500 entries, so the katana, the G28, food, medicine and tools after them are never seen.
item_stacks (SolItemStacks.lua, read at call time via SolAuthority.on; off = the old code paths):
  SCGameplayUtil  inventoryItemsDeep -> SolItemStacks.deep: one entry per distinct thing (cap 240 kept, the root/bag
                  reserve kept); further members of a stack fill the budget left AFTER the distinct entries (callers that
                  want 3 Money or 10 Nails still find them); third return value = { reps, count[rep], byType, distinct }.
                  U.inventoryCount(actorOrInventory, fullType): native getCountTypeRecurse (500 without a walk).
  SCInventoryIndex  rebuild classifies the distinct entries only; itemCountByType / looseAmmoByType add the stack count;
                  itemSet still holds every listed item (touchItem); entry.stackCount / entry.countByFullType.
  SolInventory    itemRead: a stateless type is read once, later items of it reuse the record (count per item unchanged).
  SolWorldScan    itemInfo: same.
Never merged: weapons, containers, clothing, food, drainables, keys, radios, literature, maps, animals, moveables,
fluid containers, magazines, items with modData, items with getCount ~= 1.
Edits: SCGameplayUtil.lua (2), SCInventoryIndex.lua (4), SolInventory.lua (2), SolWorldScan.lua (2); copies
SolItemStacks.lua; SolAuthority.lua (A.FIXES += item_stacks); <Zomboid>/Lua/SolFixes_LAB.txt (item_stacks=on when the
file exists and has no line for it). Apply after s99 mag_fill and s99 perf_slice. Game closed only. Idempotent.
usage: apply_s100_item_stacks.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "item_stacks"
HOOK = 'do local S_ = rawget(_G, "SolItemStacks"); '

EDITS = [
    ("SCGameplayUtil.lua",
     "function U.inventoryItemsDeep(inventory, limit, containerLimit)\n    if inventory == nil then return {}, {} end\n",
     "function U.inventoryItemsDeep(inventory, limit, containerLimit)\n    if inventory == nil then return {}, {} end\n"
     "    " + HOOK + 'if type(S_) == "table" and type(S_.deep) == "function" and S_.enabled() then return S_.deep(U, inventory, limit, containerLimit) end end   -- s100 item_stacks\n'),
    ("SCGameplayUtil.lua",
     "function U.inventoryContains(inventory, item)\n",
     "-- s100 item_stacks: how many of a full type she carries (bags included), without walking the list\n"
     "function U.inventoryCount(actorOrInventory, fullType)\n"
     "    " + HOOK + 'if type(S_) == "table" and type(S_.count) == "function" then return S_.count(U, actorOrInventory, fullType) end end\n'
     "    local inventory = actorOrInventory\n"
     '    if select(1, U.call(actorOrInventory, "getItems")) == nil then inventory = U.inventory(actorOrInventory) end\n'
     '    return tonumber((U.call(inventory, "getCountTypeRecurse", tostring(fullType)))) or 0\n'
     "end\n\n"
     "function U.inventoryContains(inventory, item)\n"),
    ("SCInventoryIndex.lua",
     "    local items, containers = utility.inventoryItemsDeep(inventory, limit)\n",
     "    local items, containers, stacks_ = utility.inventoryItemsDeep(inventory, limit)   -- s100 item_stacks: stacks_ only when on\n"),
    ("SCInventoryIndex.lua",
     "    entry.count, entry.weight = contentsFingerprint(inventory)\n",
     "    entry.count, entry.weight = contentsFingerprint(inventory)\n"
     '    if type(stacks_) == "table" and type(stacks_.reps) == "table" then   -- s100 item_stacks: classify one entry per stack\n'
     "        for _, it_ in ipairs(items or {}) do entry.itemSet[it_] = true end\n"
     "        entry.stackCount, entry.countByFullType = stacks_.count, stacks_.byType\n"
     "        items = stacks_.reps\n"
     "    end\n"),
    ("SCInventoryIndex.lua",
     "            entry.itemCountByType[key] = (entry.itemCountByType[key] or 0) + 1\n",
     "            entry.itemCountByType[key] = (entry.itemCountByType[key] or 0) + (stacks_ and stacks_.count[item] or 1)   -- s100\n"),
    ("SCInventoryIndex.lua",
     "                    (entry.looseAmmoByType[key] or 0) + 1\n",
     "                    (entry.looseAmmoByType[key] or 0) + (stacks_ and stacks_.count[item] or 1)   -- s100\n"),
    ("SolInventory.lua",
     "local function itemRead(it)\n",
     "local function itemRead(it)\n"
     "    " + HOOK + 'if type(S_) == "table" and type(S_.cachedRead) == "function" then local d_ = S_.cachedRead(it, "inv"); if d_ ~= nil then return d_ end end end   -- s100 item_stacks\n'),
    ("SolInventory.lua",
     '    if is(it, "InventoryContainer") then d.bag = method(it, "getInventory") end\n    return d\nend\n',
     '    if is(it, "InventoryContainer") then d.bag = method(it, "getInventory") end\n'
     "    " + HOOK + 'if type(S_) == "table" and type(S_.remember) == "function" then S_.remember(it, d, "inv") end end   -- s100 item_stacks\n'
     "    return d\nend\n"),
    ("SolWorldScan.lua",
     "local function itemInfo(it)\n",
     "local function itemInfo(it)\n"
     "    " + HOOK + 'if type(S_) == "table" and type(S_.cachedRead) == "function" then local d_ = S_.cachedRead(it, "ws"); if d_ ~= nil then return d_ end end end   -- s100 item_stacks\n'),
    ("SolWorldScan.lua",
     '    if cmax and cmax > 0 then d.cond = round((num(call(it, "getCondition")) or 0) / cmax, 2) end\n    return d\nend\n',
     '    if cmax and cmax > 0 then d.cond = round((num(call(it, "getCondition")) or 0) / cmax, 2) end\n'
     "    " + HOOK + 'if type(S_) == "table" and type(S_.remember) == "function" then S_.remember(it, d, "ws") end end   -- s100 item_stacks\n'
     "    return d\nend\n"),
]


def main(cl):
    cl = os.path.abspath(cl)
    ap = os.path.join(cl, "SolAuthority.lua")
    assert os.path.isfile(ap), "not a Sol client dir: " + cl
    for _, old, new in EDITS:
        assert all(ord(c) < 128 for c in old + new)
    # check every edit first, write nothing unless all of them fit
    texts, changed = {}, {}
    for fn, old, new in EDITS:
        p = os.path.join(cl, fn)
        if p not in texts: texts[p] = open(p, encoding="utf-8", newline="").read()
        t = texts[p]
        nl = CRLF if CRLF in t else NL
        o, n = old.replace(NL, nl), new.replace(NL, nl)
        if n in t: continue
        assert t.count(o) == 1, (fn, t.count(o), old[:70])
        texts[p] = t.replace(o, n)
        changed.setdefault(p, 0)
        changed[p] += 1
    for p in sorted(texts):
        if p in changed:
            open(p, "w", encoding="utf-8", newline="").write(texts[p])
            print("edited %s (%d)" % (os.path.basename(p), changed[p]))
        else:
            print("kept " + os.path.basename(p))
    src = os.path.join(HERE, "SolItemStacks.lua")
    dst = os.path.join(cl, "SolItemStacks.lua")
    if os.path.exists(dst) and open(dst, "rb").read() == open(src, "rb").read():
        print("kept SolItemStacks.lua")
    else:
        shutil.copy(src, dst)
        print("copied SolItemStacks.lua")
    a = open(ap, encoding="utf-8", newline="").read()
    if '"%s"' % FIX in a:
        print("kept SolAuthority.lua")
    else:
        anl = CRLF if CRLF in a else NL
        old = "A.FIXES = {" + anl
        assert a.count(old) == 1
        a = a.replace(old, old + '    "%s",   -- s100: identical stateless items are one entry with a count (500 rounds = one stack); LF walk keeps 240 distinct' % FIX + anl)
        open(ap, "w", encoding="utf-8", newline="").write(a)
        print("edited SolAuthority.lua")
    fixfile = os.path.normpath(os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt"))
    if os.path.exists(fixfile):
        have = open(fixfile, encoding="utf-8", newline="").read()
        if FIX + "=" not in have:
            with open(fixfile, "a", encoding="utf-8", newline="") as h:
                if have and not have.endswith(NL): h.write(CRLF)
                h.write(FIX + "=on" + CRLF)
            print("SolFixes_LAB", FIX + "=on")


if __name__ == "__main__":
    main(sys.argv[1])
    print("s100 item_stacks applied")
