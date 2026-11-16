"""s105 item_stacks live fix: SolItemStacks 0.1.0 -> 0.2.0. s100 is installed but grouped nothing live.
Root cause (projectzomboid.jar 42.22, javap): Item.InstanceItem makes every ItemType=normal item a ComboItem and copies
the script Count onto it (Base.308Bullets / Base.556Bullets: Count = 5). 0.1.0 listed "ComboItem" as stateful and took
getCount ~= 1 as per-item state, so every loose round (and nail, pill...) was its own entry: the capped walk was the
old one, with s100 on. 0.2.0: ComboItem is stackable, the count is part of the stack key; one temporary log line
"[SolItemStacks] grouped N items into M entries" the first time a walk merges something.
The grouped walk is cached per inventory (signature: getItems():size() + getContentsWeight() of the root and of each
bag opened, ItemContainer, javap 42.22; also rebuilt after 10 s); each rebuild reports its ms to SolPerf ("item_stacks").
Only SolItemStacks.lua changes (the s100 hooks stay as installed). The switch is still item_stacks (SolAuthority.on).
Needs s100 installed. Game closed only. Idempotent.
0.3.0 (after the 14:54 live run still merged nothing): identical modData groups too; one-shot diagnostic block
"[SolItemStacks] diag ..." when a walk merges nothing (class, category, instanceof, hasModData, modData keys, getCount,
getMaxAmmo, verdict and reason of the first 3 root items and of the first repeated types).
usage: apply_s105_item_stacks_live.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = 'do local S_ = rawget(_G, "SolItemStacks"); if type(S_) == "table" and type(S_.deep) == "function" and S_.enabled() then return S_.deep(U, inventory, limit, containerLimit) end end   -- s100 item_stacks'


def main(cl):
    cl = os.path.abspath(cl)
    gu = os.path.join(cl, "SCGameplayUtil.lua")
    ix = os.path.join(cl, "SCInventoryIndex.lua")
    au = os.path.join(cl, "SolAuthority.lua")
    for p in (gu, ix, au):
        assert os.path.isfile(p), "not a Sol client dir: " + cl
    assert HOOK in open(gu, encoding="utf-8", newline="").read(), "s100 hook missing in SCGameplayUtil.lua: apply s100 first"
    assert "stacks_ = utility.inventoryItemsDeep" in open(ix, encoding="utf-8", newline="").read(), "s100 edits missing in SCInventoryIndex.lua"
    assert '"item_stacks"' in open(au, encoding="utf-8", newline="").read(), "item_stacks not in A.FIXES"
    src = os.path.join(HERE, "SolItemStacks.lua")
    body = open(src, "rb").read()
    assert b'S.VERSION = "0.3.0"' in body and all(b < 128 for b in body)
    dst = os.path.join(cl, "SolItemStacks.lua")
    if os.path.exists(dst) and open(dst, "rb").read() == body:
        print("kept SolItemStacks.lua")
    else:
        shutil.copy(src, dst)
        print("copied SolItemStacks.lua (0.3.0)")


if __name__ == "__main__":
    main(sys.argv[1])
    print("s105 item_stacks_live applied")
