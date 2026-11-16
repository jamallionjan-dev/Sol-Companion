-- SolGearPage.lua - switch gear_page (s107, PLAN_gear_and_combat.md Part 1; COUNCIL_s107_gear_page.md).
-- The gear tab of her window (SolPages "loadout", LF's Loadout page read hidden) gets Sol's own gear page:
--   in her hands   the weapon she really holds (her primary hand, else the other hand; EFZ guns too), rounds in the gun
--                  (magazine + chambered round, s99 SolMagFill.loadedRounds), spare magazines and their rounds, loose rounds
--                  of its calibre (U.inventoryCount -> s100 SolItemStacks.count -> getCountTypeRecurse); state ready / empty /
--                  jammed / parts problem (s98 SolCombatEquipFallback.whyUnusable) / broken; "use this one" (LF's own
--                  equip order, which marks her preferred weapon, s98) and reload (s99 SolMagFill.orderFill)
--   her favourites her preferred firearm (LF marker SC_ManualEquipFor) and melee weapon (s99 SolWeaponPick, SolMeleeFor),
--                  changeable here among the weapons she carries
--   fighting plan  the 8 plans of s105 SolCombatPlans (same ids as the chat verb sol_combat_plan), one line each; with
--                  combat_plans on it replaces LF's "weapon priority" selector (a plan sets that knob), so there is one setting
--   worn           her worn items by body slot with condition: take off, swap (another item for the same slot in her bag)
--   her bag        SolItemStacks' grouped walk (x count) by kind: weapons, ammo and magazines, medical, food, tools,
--                  clothing, other: give to me, use, set preferred
--   my bag         only after he asks for it, and only what she can use (weapons, her guns' rounds / magazines, medical,
--                  armour): give to Sol
--   car and home   what SolInventory's last finished scan saw in the vehicles and the home / base area (no new scan):
--                  weapons, her guns' rounds and magazines, medical. Read only; shown after he asks for it
--   like me        what he wears or holds that protects / hits better than hers, side by side; "give her one" when he has
--                  a spare of the same item
-- Performance: the page is one virtualised list (only rows inside the visible window are drawn and get click areas); the
-- data is rebuilt only when a signature changes (item count + contents weight of each inventory and of each bag the grouped
-- walk opened, the hands, the worn count, the plan, the last SolInventory scan), checked at most every SIG_MS, with a
-- MAX_AGE_MS backstop; her bag reuses SolItemStacks' own per-inventory cache. No per-frame scan. Cost -> SolPerf "gear_page".
-- Switch gear_page read at call time (SolAuthority.on). Off: SolPages' own loadout card and LF's widgets exactly as before.
-- Java calls (javap 42.22.2): IsoGameCharacter getPrimaryHandItem/getSecondaryHandItem/getInventory/getWornItems/
-- isEquipped(InventoryItem)/isEquippedClothing(InventoryItem)/removeWornItem(InventoryItem) (the 1-arg overload);
-- WornItems size/get(int); WornItem getItem/getLocation; ItemBodyLocation toString; InventoryItem getDisplayName/getFullType/
-- getCategory/getDisplayCategory/getCondition/getConditionMax/getContainer/hasModData/getModData/IsFood/IsClothing/
-- getBodyLocation/getAmmoType/getMaxAmmo/getCurrentAmmoCount/isRanged; AmmoType getItemKey; HandWeapon isJammed/
-- isRoundChambered/getMaxDamage; Clothing getBiteDefense/getScratchDefense/getBulletDefense; ItemContainer getItems/
-- getContentsWeight/getAllTypeRecurse(String) (the 1-arg overload). No boolean argument to any Java call.
-- ASCII only: page text and her lines are \u escapes (SolText / SolBubble).
require "SolPages"
SolUI = SolUI or {}
local U = SolUI
SolGearPage = SolGearPage or {}
local GP = SolGearPage
GP.VERSION = "0.1.0"
GP.SIG_MS = 500             -- the signatures are compared at most this often
GP.MAX_AGE_MS = 15000       -- a full rebuild after this long even with equal signatures (a preference set by chat)
GP.MAX_BAG = 240            -- SolItemStacks.deep limit (LF's own)
GP.MAX_CONT = 12
GP.MAX_SRC = 300
GP.MAX_STACK_MOVE = 1000
GP.stats = { full = 0, hands = 0, checks = 0 }

-- geometry: SolPages' content area (W 600, H 640, CX 14, CW 418, CY 66, CH = H - CY - 44)
local CX, CW, CY, CH = 14, 418, 66, 530
GP.GEOM = { CX = CX, CW = CW, CY = CY, CH = CH }
local SCALE_TXT, SCALE_SUB, SCALE_SEC, SCALE_BTN = 0.52, 0.44, 0.64, 0.46
local H_SEC, H_KV, H_ITEM, H_BTNS, H_PLAN, H_NOTE, H_PAIR = 32, 26, 40, 38, 44, 24, 46
local BW, BGAP = 74, 4
local BLUE, MUTED, GOOD, WARN, BAD, GOLDC = { 0.42, 0.72, 1.0 }, { 0.62, 0.71, 0.78 }, { 0.18, 0.83, 0.39 }, { 0.93, 0.74, 0.19 }, { 0.94, 0.47, 0.43 }, { 1.0, 0.86, 0.45 }

-- ---------------------------------------------------------------- words (Arabic, plain, no technical words)
local W = {
    sec_hands = "\\u0628\\u0625\\u064A\\u062F\\u0647\\u0627", sec_prefs = "\\u0633\\u0644\\u0627\\u062D\\u0647\\u0627 \\u0627\\u0644\\u0645\\u0641\\u0636\\u0651\\u0644", sec_plan = "\\u062E\\u0637\\u0629 \\u0627\\u0644\\u0642\\u062A\\u0627\\u0644", sec_worn = "\\u0644\\u0627\\u0628\\u0633\\u0629",
    sec_bag = "\\u062D\\u0642\\u064A\\u0628\\u062A\\u0647\\u0627", sec_mine = "\\u062D\\u0642\\u064A\\u0628\\u062A\\u064A", sec_src = "\\u0628\\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629 \\u0648\\u0627\\u0644\\u0628\\u064A\\u062A", sec_like = "\\u0645\\u062A\\u0644\\u064A",
    weapon = "\\u0627\\u0644\\u0633\\u0644\\u0627\\u062D", in_gun = "\\u0628\\u0627\\u0644\\u0633\\u0644\\u0627\\u062D", spare = "\\u0645\\u062E\\u0627\\u0632\\u0646 \\u0632\\u064A\\u0627\\u062F\\u0629", loose = "\\u0631\\u0635\\u0627\\u0635 \\u0641\\u0631\\u0637", state = "\\u0627\\u0644\\u062D\\u0627\\u0644\\u0629",
    cond = "\\u0627\\u0644\\u062D\\u0627\\u0644\\u0629", none = "\\u0625\\u064A\\u062F\\u064A\\u0647\\u0627 \\u0641\\u0627\\u0636\\u064A\\u0629",
    st_ready = "\\u062C\\u0627\\u0647\\u0632", st_empty = "\\u0641\\u0627\\u0636\\u064A", st_jammed = "\\u0639\\u0627\\u0644\\u0642", st_parts = "\\u0641\\u064A\\u0647 \\u0645\\u0634\\u0643\\u0644\\u0629 \\u0628\\u0627\\u0644\\u0642\\u0637\\u0639", st_broken = "\\u0645\\u0643\\u0633\\u0648\\u0631",
    b_use = "\\u0627\\u0633\\u062A\\u0639\\u0645\\u0644\\u064A\\u0647", b_reload = "\\u0639\\u0628\\u0651\\u064A", b_pref = "\\u0627\\u0644\\u0645\\u0641\\u0636\\u0651\\u0644", b_give_me = "\\u0623\\u0639\\u0637\\u064A\\u0646\\u064A", b_wear = "\\u0627\\u0644\\u0628\\u0633\\u064A\\u0647",
    b_off = "\\u0634\\u064A\\u0644\\u064A\\u0647", b_swap = "\\u0628\\u062F\\u0651\\u0644\\u064A", b_give_sol = "\\u0623\\u0639\\u0637\\u064A \\u0633\\u0648\\u0644", b_show = "\\u0627\\u0639\\u0631\\u0636", b_hide = "\\u062E\\u0628\\u0651\\u064A",
    b_give_one = "\\u0623\\u0639\\u0637\\u064A\\u0647\\u0627 \\u0648\\u062D\\u062F\\u0629", b_bag = "\\u062D\\u0642\\u064A\\u0628\\u062A\\u0647\\u0627", b_med = "\\u0641\\u062D\\u0635 \\u0637\\u0628\\u064A", b_bandage = "\\u062A\\u0636\\u0645\\u064A\\u062F", b_choose = "\\u0627\\u062E\\u062A\\u0627\\u0631\\u064A",
    firearm = "\\u0646\\u0627\\u0631\\u064A", melee = "\\u0623\\u0628\\u064A\\u0636", nothing = "\\u0645\\u0627 \\u0641\\u064A", chosen = "\\u0647\\u0648 \\u0627\\u0644\\u0645\\u0641\\u0636\\u0651\\u0644",
    g_weapons = "\\u0623\\u0633\\u0644\\u062D\\u0629", g_ammo = "\\u0630\\u062E\\u064A\\u0631\\u0629 \\u0648\\u0645\\u062E\\u0627\\u0632\\u0646", g_medical = "\\u0625\\u0633\\u0639\\u0627\\u0641", g_food = "\\u0623\\u0643\\u0644", g_tools = "\\u0623\\u062F\\u0648\\u0627\\u062A",
    g_clothing = "\\u0645\\u0644\\u0627\\u0628\\u0633", g_other = "\\u063A\\u064A\\u0631 \\u0634\\u064A",
    bag_empty = "\\u062D\\u0642\\u064A\\u0628\\u062A\\u0647\\u0627 \\u0641\\u0627\\u0636\\u064A\\u0629", mine_hint = "\\u0628\\u0633 \\u0627\\u0644\\u0644\\u064A \\u0628\\u062A\\u0642\\u062F\\u0631 \\u062A\\u0633\\u062A\\u0639\\u0645\\u0644\\u0647", mine_empty = "\\u0645\\u0627 \\u0645\\u0639\\u0643 \\u0634\\u064A \\u0628\\u064A\\u0646\\u0641\\u0639\\u0647\\u0627",
    src_hint = "\\u0645\\u0646 \\u0622\\u062E\\u0631 \\u0645\\u0631\\u0629 \\u0634\\u0627\\u0641\\u062A \\u0627\\u0644\\u0623\\u063A\\u0631\\u0627\\u0636", src_empty = "\\u0645\\u0627 \\u0641\\u064A \\u0634\\u064A \\u0628\\u064A\\u0646\\u0641\\u0639\\u0647\\u0627 \\u0647\\u0648\\u0646\\u064A\\u0643", src_car = "\\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629", src_home = "\\u0627\\u0644\\u0628\\u064A\\u062A",
    yours = "\\u0639\\u0646\\u062F\\u0643", hers = "\\u0639\\u0646\\u062F\\u0647\\u0627", like_none = "\\u0645\\u0627 \\u0639\\u0646\\u062F\\u0643 \\u0634\\u064A \\u0623\\u062D\\u0633\\u0646 \\u0645\\u0646 \\u062A\\u0628\\u0639\\u0647\\u0627", no_spare = "\\u0645\\u0627 \\u0639\\u0646\\u062F\\u0643 \\u0648\\u062D\\u062F\\u0629 \\u0632\\u064A\\u0627\\u062F\\u0629",
    health = "\\u0627\\u0644\\u0635\\u062D\\u0629", load = "\\u0627\\u0644\\u062D\\u0645\\u0644", no_sol = "\\u0633\\u0648\\u0644 \\u0645\\u0634 \\u0647\\u0648\\u0646 \\u0647\\u0644\\u0642", plans_off = "\\u062E\\u0637\\u0637 \\u0627\\u0644\\u0642\\u062A\\u0627\\u0644 \\u0645\\u0637\\u0641\\u064A\\u0629",
    rounds = "\\u0637\\u0644\\u0642\\u0629", mags = "\\u0645\\u062E\\u0632\\u0646",
    slot_head = "\\u0627\\u0644\\u0631\\u0627\\u0633", slot_eyes = "\\u0627\\u0644\\u0639\\u064A\\u0648\\u0646", slot_face = "\\u0627\\u0644\\u0648\\u062C\\u0647", slot_chest = "\\u0627\\u0644\\u0635\\u062F\\u0631", slot_back = "\\u0627\\u0644\\u0636\\u0647\\u0631",
    slot_hands = "\\u0627\\u0644\\u0625\\u064A\\u062F\\u064A\\u0646", slot_feet = "\\u0627\\u0644\\u0631\\u062C\\u0644\\u064A\\u0646", slot_legs = "\\u0627\\u0644\\u0631\\u062C\\u0644\\u064A\\u0646 \\u0648\\u0627\\u0644\\u0628\\u0646\\u0637\\u0644\\u0648\\u0646", slot_waist = "\\u0627\\u0644\\u062E\\u0635\\u0631",
    slot_body = "\\u0627\\u0644\\u062C\\u0633\\u0645", slot_neck = "\\u0627\\u0644\\u0631\\u0642\\u0628\\u0629",
}
GP.W = W
GP.GROUPS = { "weapons", "ammo", "medical", "food", "tools", "clothing", "other" }
-- the 8 plans: the chat verb's ids (SolCombatPlans.ORDER), a name and one line each
GP.PLANS = {
    { id = "smart",   name = "\\u0630\\u0643\\u064A",      line = "\\u0623\\u0628\\u064A\\u0636 \\u0644\\u0632\\u0648\\u0645\\u0628\\u064A \\u0623\\u0648 \\u0627\\u062A\\u0646\\u064A\\u0646\\u060C \\u0648\\u0627\\u0644\\u0646\\u0627\\u0631\\u064A \\u0644\\u0645\\u062C\\u0645\\u0648\\u0639\\u0629 \\u0623\\u0648 \\u0625\\u0630\\u0627 \\u062D\\u062F\\u0627 \\u0642\\u0631\\u0651\\u0628 \\u0645\\u0646\\u0643" },
    { id = "normal",  name = "\\u0639\\u0627\\u062F\\u064A",     line = "\\u0628\\u062A\\u0642\\u0627\\u062A\\u0644 \\u0627\\u0644\\u0644\\u064A \\u0628\\u064A\\u0642\\u0631\\u0628 \\u0648\\u0628\\u062A\\u0636\\u0644 \\u0642\\u0631\\u064A\\u0628\\u0629 \\u0645\\u0646\\u0643" },
    { id = "fierce",  name = "\\u0634\\u0631\\u0633\\u0629",     line = "\\u0628\\u062A\\u0647\\u062C\\u0645 \\u0648\\u0628\\u062A\\u0646\\u0636\\u0651\\u0641 \\u0627\\u0644\\u0645\\u0643\\u0627\\u0646\\u060C \\u0628\\u0633 \\u0645\\u0627 \\u0628\\u062A\\u0628\\u0639\\u062F \\u0639\\u0646\\u0643 \\u0623\\u0643\\u062A\\u0631 \\u0645\\u0646 25 \\u062E\\u0637\\u0648\\u0629" },
    { id = "support", name = "\\u0625\\u0633\\u0646\\u0627\\u062F",    line = "\\u0628\\u062A\\u0636\\u0644 \\u0648\\u0631\\u0627\\u0643 \\u0648\\u0628\\u062A\\u062D\\u0645\\u064A\\u0643 \\u0645\\u0646 \\u0628\\u0639\\u064A\\u062F" },
    { id = "careful", name = "\\u062D\\u0630\\u0631\\u0629",     line = "\\u0628\\u062A\\u0642\\u0627\\u062A\\u0644 \\u0628\\u0633 \\u0627\\u0644\\u0644\\u064A \\u0628\\u064A\\u0648\\u0635\\u0644\\u0647\\u0627 \\u0648\\u0628\\u062A\\u0648\\u0641\\u0651\\u0631 \\u0627\\u0644\\u0631\\u0635\\u0627\\u0635" },
    { id = "stealth", name = "\\u062A\\u062E\\u0641\\u0651\\u064A",    line = "\\u0628\\u062A\\u0645\\u0634\\u064A \\u0628\\u0647\\u062F\\u0648\\u0621\\u060C \\u0623\\u0628\\u064A\\u0636 \\u0623\\u0648 \\u0633\\u0644\\u0627\\u062D \\u0645\\u0643\\u062A\\u0648\\u0645 \\u0628\\u0633" },
    { id = "avoid",   name = "\\u062A\\u062C\\u0646\\u0651\\u0628",    line = "\\u0628\\u062A\\u0628\\u0639\\u062F \\u0639\\u0646\\u0647\\u0645 \\u0648\\u0645\\u0627 \\u0628\\u062A\\u0642\\u0627\\u062A\\u0644 \\u0625\\u0644\\u0627 \\u0625\\u0630\\u0627 \\u0627\\u0646\\u062D\\u0635\\u0631\\u062A" },
    { id = "hold",    name = "\\u0644\\u0627 \\u062A\\u0637\\u0644\\u0642\\u064A", line = "\\u0645\\u0627 \\u0628\\u062A\\u0637\\u0644\\u0642 \\u0623\\u0628\\u062F\\u0627\\u064B\\u060C \\u0628\\u0627\\u0644\\u0623\\u0628\\u064A\\u0636 \\u0628\\u0633 \\u0625\\u0630\\u0627 \\u0644\\u0627\\u0632\\u0645" },
}
-- her short answers (Sol's bubble takes the \u escapes)
GP.SAY = {
    smart = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0628\\u062A\\u0635\\u0631\\u0651\\u0641 \\u062D\\u0633\\u0628 \\u0627\\u0644\\u0645\\u0648\\u0642\\u0641.", normal = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0628\\u0642\\u0627\\u062A\\u0644 \\u0639\\u0627\\u062F\\u064A.", fierce = "\\u062D\\u0627\\u0636\\u0631\\u060C \\u0631\\u062D \\u0647\\u0627\\u062C\\u0645.",
    support = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0628\\u062D\\u0645\\u064A\\u0643 \\u0645\\u0646 \\u0648\\u0631\\u0627.", careful = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0631\\u062D \\u0643\\u0648\\u0646 \\u062D\\u0630\\u0631\\u0629.", stealth = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0631\\u062D \\u0636\\u0644 \\u0645\\u062E\\u0641\\u064A\\u0629.",
    avoid = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0631\\u062D \\u0627\\u0628\\u0639\\u062F \\u0639\\u0646\\u0647\\u0645.", hold = "\\u062D\\u0627\\u0636\\u0631\\u060C \\u0645\\u0627 \\u0628\\u0637\\u0644\\u0642.", give = "\\u062A\\u0641\\u0636\\u0651\\u0644.",
}

-- ---------------------------------------------------------------- helpers
local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); if type(f) == "function" then local ok, v = pcall(f); if ok and type(v) == "number" then return v end end; return 0 end
local function log(m) print("[SolGearPage] " .. tostring(m)) end
local function num(v) return tonumber(v) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or type(f) ~= "function" then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function isA(o, cls)
    local f = g("instanceof")
    if type(f) ~= "function" or o == nil then return false end
    local ok, r = pcall(f, o, cls)
    return ok and r == true
end
local function LF() local sc = g("SurvivorCompanion"); return type(sc) == "table" and sc or nil end
local function GU() local SC = LF(); return SC and type(SC.GameplayUtil) == "table" and SC.GameplayUtil or nil end
local function mod(name) local m = g(name); return type(m) == "table" and m or nil end
function GP.on() local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("gear_page") == true end
local function sw(fix) local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on(fix) == true end
local function player() local f = g("getSpecificPlayer"); if type(f) ~= "function" then return nil end; local ok, p = pcall(f, 0); return ok and p or nil end
local function list(jl, cap)
    local out = {}
    if jl == nil then return out end
    local n = num((call(jl, "size"))) or 0
    for i = 0, math.min(n, cap or 64) - 1 do
        local it = call(jl, "get", i)
        if it ~= nil then out[#out + 1] = it end
    end
    return out
end
local function int(v) return tostring(math.floor((num(v) or 0) + 0.5)) end
local function pct(r) return int((num(r) or 0) * 100) .. "%" end
local function condRatio(it)
    local c, m = num((call(it, "getCondition"))), num((call(it, "getConditionMax")))
    if c and m and m > 0 then return math.max(0, math.min(1, c / m)) end
    return 1
end
GP.condRatio = condRatio
local function nameOf(it) return tostring(call(it, "getDisplayName") or call(it, "getFullType") or "?") end
local function fullType(it) return tostring(call(it, "getFullType") or "?") end
local function equippedBy(who, it)
    return call(who, "isEquipped", it) == true or call(who, "isEquippedClothing", it) == true
        or call(who, "getPrimaryHandItem") == it or call(who, "getSecondaryHandItem") == it
end
local function idOf(actor)
    local gu = GU()
    if actor == nil or gu == nil or type(gu.idOf) ~= "function" then return nil end
    local ok, id = pcall(gu.idOf, actor)
    return ok and id or nil
end

-- ---------------------------------------------------------------- what an item is
function GP.kind(it)
    if call(it, "IsFood") == true then return "food" end
    local cat = tostring(call(it, "getCategory") or "")
    local dc = string.lower(tostring(call(it, "getDisplayCategory") or ""))
    if isA(it, "HandWeapon") or cat == "Weapon" then return "weapons" end
    if string.find(dc, "ammo", 1, true) or (num((call(it, "getMaxAmmo"))) or 0) > 0 then return "ammo" end
    if string.find(dc, "firstaid", 1, true) or string.find(dc, "medic", 1, true) then return "medical" end
    if cat == "Food" or dc == "food" then return "food" end
    if call(it, "IsClothing") == true or cat == "Clothing" or isA(it, "InventoryContainer") then return "clothing" end
    if string.find(dc, "tool", 1, true) then return "tools" end
    return "other"
end
-- protection of a worn item: bite + scratch + bullet defense x condition (0 for what is not clothing)
function GP.armour(it)
    if it == nil or call(it, "IsClothing") ~= true then return 0 end
    local d = (num((call(it, "getBiteDefense"))) or 0) + (num((call(it, "getScratchDefense"))) or 0) + (num((call(it, "getBulletDefense"))) or 0)
    return d * condRatio(it)
end
function GP.weaponScore(it)
    if it == nil then return 0 end
    return (num((call(it, "getMaxDamage"))) or 0) * (0.25 + 0.75 * condRatio(it))
end
local function isGun(it) return it ~= nil and call(it, "isRanged") == true end
local function locOf(it, loc)
    local s = loc ~= nil and tostring(loc) or nil
    if s == nil then local b = call(it, "getBodyLocation"); s = b ~= nil and tostring(b) or "" end
    return s
end
-- a worn slot in her words
function GP.slotWord(loc)
    local s = string.lower(tostring(loc or ""))
    s = string.gsub(s, "^.*:", ""); s = string.gsub(s, "_", "")
    local function has(w) return string.find(s, w, 1, true) ~= nil end
    if has("fanny") or has("belt") or has("holster") or has("waist") then return W.slot_waist end
    if has("hat") or has("helmet") or has("head") then return W.slot_head end
    if has("eye") then return W.slot_eyes end
    if has("mask") or has("face") then return W.slot_face end
    if has("neck") or has("scarf") then return W.slot_neck end
    if has("vest") or has("cuirass") or has("torsoextra") then return W.slot_chest end
    if has("back") then return W.slot_back end
    if has("hand") or has("glove") then return W.slot_hands end
    if has("shoe") or has("sock") or has("boot") then return W.slot_feet end
    if has("pants") or has("leg") or has("skirt") or has("short") then return W.slot_legs end
    if has("shirt") or has("jacket") or has("sweater") or has("dress") or has("suit") or has("torso") or has("robe") then return W.slot_body end
    return tostring(loc or "")
end
local SKIP_LOC = { "bandage", "wound", "makeup", "tattoo", "zeddmg", "bloat" }
local function skipLoc(loc)
    local s = string.lower(tostring(loc or ""))
    for _, w in ipairs(SKIP_LOC) do if string.find(s, w, 1, true) then return true end end
    return false
end

-- ---------------------------------------------------------------- her gun: rounds and state
-- the loose-round kinds of this gun: its own ammo type, and the kind each of her magazines for it takes (Gunworks)
function GP.roundKinds(actor, gun, mags)
    local out, seen = {}, {}
    local at = call(gun, "getAmmoType")
    local key = at ~= nil and call(at, "getItemKey") or nil
    if type(key) == "string" and key ~= "" then seen[key] = true; out[#out + 1] = key end
    local MF = mod("SolMagFill")
    if MF and type(MF.roundKind) == "function" then
        for _, m in ipairs(mags or {}) do
            local ok, k = pcall(MF.roundKind, actor, m.item)
            if ok and type(k) == "string" and k ~= "" and not seen[k] then seen[k] = true; out[#out + 1] = k end
        end
    end
    return out
end
local function invCount(actor, key)
    local gu = GU()
    if gu and type(gu.inventoryCount) == "function" then
        local ok, n = pcall(gu.inventoryCount, actor, key)
        if ok and num(n) then return num(n) end
    end
    return num((call(call(actor, "getInventory"), "getCountTypeRecurse", key))) or 0
end
function GP.loaded(gun)
    local MF = mod("SolMagFill")
    if MF and type(MF.loadedRounds) == "function" and type(MF.on) == "function" and MF.on() then
        local ok, n = pcall(MF.loadedRounds, gun, nil)
        if ok and num(n) then return num(n) end
    end
    local n = num((call(gun, "getCurrentAmmoCount"))) or 0
    if n < 0 then n = 0 end
    if call(gun, "isRoundChambered") == true then n = n + 1 end
    return n
end
-- ready / empty / jammed / parts / broken (nil for no weapon)
function GP.state(it, inGun)
    if it == nil then return nil end
    if condRatio(it) <= 0 then return "broken" end
    if isGun(it) and call(it, "isJammed") == true then return "jammed" end
    local G = mod("SolCombatEquipFallback")
    if G and type(G.whyUnusable) == "function" then
        local ok, why = pcall(G.whyUnusable, it, nil)
        if ok and why == "parts" then return "parts" end
    end
    if isGun(it) and (num(inGun) or 0) <= 0 then return "empty" end
    return "ready"
end
function GP.hands(actor)
    local it = call(actor, "getPrimaryHandItem") or call(actor, "getSecondaryHandItem")
    if it == nil then return { none = true } end
    local h = { item = it, name = nameOf(it), ranged = isGun(it), cond = condRatio(it) }
    if h.ranged then
        local inv = call(actor, "getInventory")
        h.inGun = GP.loaded(it)
        local MF = mod("SolMagFill")
        local mags = {}
        if MF and type(MF.magazines) == "function" then local ok, l = pcall(MF.magazines, inv, it); if ok and type(l) == "table" then mags = l end end
        h.mags, h.magRounds = #mags, 0
        for _, m in ipairs(mags) do h.magRounds = h.magRounds + (num(m.count) or 0) end
        h.loose = 0
        for _, k in ipairs(GP.roundKinds(actor, it, mags)) do h.loose = h.loose + invCount(actor, k) end
        h.canReload = MF ~= nil and type(MF.on) == "function" and MF.on() and type(MF.magTypes) == "function" and #MF.magTypes(it) > 0
    end
    h.state = GP.state(it, h.inGun)
    return h
end

-- ---------------------------------------------------------------- her weapons and favourites
local function herWeapons(actor)
    local WP = mod("SolWeaponPick")
    local inv = call(actor, "getInventory")
    local out, seen = {}, {}
    local held = call(actor, "getPrimaryHandItem")
    if held ~= nil and isA(held, "HandWeapon") then seen[held] = true; out[1] = held end
    local l
    if WP and type(WP.weapons) == "function" then local ok, r = pcall(WP.weapons, inv); if ok and type(r) == "table" then l = r end end
    local AL = g("ArrayList")
    if l == nil and AL ~= nil then l = list(call(inv, "getAllCategoryRecurse", "Weapon", AL.new()), 64) end
    l = l or {}
    for _, it in ipairs(l) do if not seen[it] then seen[it] = true; out[#out + 1] = it end end
    return out
end
GP.herWeapons = herWeapons
local function markedGun(it, id)
    if id == nil or call(it, "hasModData") ~= true then return false end
    local md = call(it, "getModData")
    return type(md) == "table" and md.SC_ManualEquipFor == id and isGun(it)
end
function GP.prefs(actor, weapons)
    local id = idOf(actor)
    local p = { guns = {}, melee = {} }
    for _, it in ipairs(weapons) do
        if isGun(it) then p.guns[#p.guns + 1] = it; if p.gun == nil and markedGun(it, id) then p.gun = it end
        else p.melee[#p.melee + 1] = it end
    end
    local WP = mod("SolWeaponPick")
    if WP and type(WP.preferredMelee) == "function" then local ok, m = pcall(WP.preferredMelee, actor); if ok then p.melee1 = m end end
    p.canGun = mod("SolCombatEquipFallback") ~= nil and sw("preferred_weapon")
    p.canMelee = WP ~= nil and type(WP.markMelee) == "function" and sw("melee_choice")
    return p
end
-- every round kind and magazine type her guns take (for his bag and the car / home lists)
function GP.herAmmo(actor, weapons)
    local set = {}
    local MF = mod("SolMagFill")
    local inv = call(actor, "getInventory")
    for _, it in ipairs(weapons) do
        if isGun(it) then
            local mags = {}
            if MF and type(MF.magTypes) == "function" then
                local ok, l = pcall(MF.magTypes, it)
                if ok and type(l) == "table" then for _, t in ipairs(l) do set[t] = true end end
                if type(MF.magazines) == "function" then local ok2, ml = pcall(MF.magazines, inv, it); if ok2 and type(ml) == "table" then mags = ml end end
            else
                local mt = call(it, "getMagazineType"); if mt ~= nil and tostring(mt) ~= "" then set[tostring(mt)] = true end
            end
            for _, k in ipairs(GP.roundKinds(actor, it, mags)) do set[k] = true end
        end
    end
    return set
end

-- ---------------------------------------------------------------- worn
function GP.worn(who)
    local out = {}
    local wi = call(who, "getWornItems")
    local n = num((call(wi, "size"))) or 0
    for i = 0, math.min(n, 64) - 1 do
        local w = call(wi, "get", i)
        local it = call(w, "getItem")
        local loc = call(w, "getLocation")
        if it ~= nil and not skipLoc(loc) then out[#out + 1] = { item = it, loc = locOf(it, loc), name = nameOf(it), cond = condRatio(it) } end
    end
    return out
end

-- ---------------------------------------------------------------- a bag, grouped (SolItemStacks' cached walk)
function GP.grouped(who, keep)
    local inv = call(who, "getInventory")
    local S, gu = mod("SolItemStacks"), GU()
    local reps, count, containers = {}, {}, {}
    if S and type(S.deep) == "function" and gu then
        local ok, _, conts, info = pcall(S.deep, gu, inv, GP.MAX_BAG, GP.MAX_CONT)
        if ok and type(info) == "table" then reps, count, containers = info.reps or {}, info.count or {}, conts or {} end
    elseif gu and type(gu.inventoryItemsDeep) == "function" then
        local ok, l = pcall(gu.inventoryItemsDeep, inv, GP.MAX_BAG)
        if ok and type(l) == "table" then reps = l end
    end
    local groups = {}
    for _, k in ipairs(GP.GROUPS) do groups[k] = {} end
    local n = 0
    for _, it in ipairs(reps) do
        if not equippedBy(who, it) then
            local kind = GP.kind(it)
            local e = { item = it, name = nameOf(it), n = num(count[it]) or 1, kind = kind, ft = fullType(it), cond = condRatio(it),
                        stack = (num(count[it]) or 1) > 1 }
            if keep == nil or keep(e) then local gl = groups[kind]; gl[#gl + 1] = e; n = n + 1 end
        end
    end
    for _, k in ipairs(GP.GROUPS) do table.sort(groups[k], function(a, b) if a.name ~= b.name then return a.name < b.name end return a.n > b.n end) end
    return groups, n, containers
end

-- ---------------------------------------------------------------- like me
function GP.likeMe(actor, me, herWornList, herHands, herList)
    local out = {}
    local hers = {}
    for _, w in ipairs(herWornList) do hers[w.loc] = w end
    local myInv = call(me, "getInventory")
    local function spareOf(it)
        for _, c in ipairs(list(call(myInv, "getAllTypeRecurse", fullType(it)), 32)) do
            if c ~= it and not equippedBy(me, c) then return c end
        end
        return nil
    end
    -- weapon in his hands against hers of the same kind
    local mine = call(me, "getPrimaryHandItem")
    if mine ~= nil and isA(mine, "HandWeapon") then
        -- hers of the same kind: the one in her hands, else her best one of that kind
        local herW = herHands and herHands.item or nil
        if herW ~= nil and isGun(herW) ~= isGun(mine) then herW = nil end
        if herW == nil then
            for _, it in ipairs(herList or {}) do
                if isGun(it) == isGun(mine) and (herW == nil or GP.weaponScore(it) > GP.weaponScore(herW)) then herW = it end
            end
        end
        local ms, hs = GP.weaponScore(mine), GP.weaponScore(herW)
        if ms > hs * 1.1 + 0.1 then
            out[#out + 1] = { slot = W.weapon, mine = mine, myName = nameOf(mine), myStat = pct(condRatio(mine)),
                              her = herW, herName = herW and nameOf(herW) or W.nothing, herStat = herW and pct(condRatio(herW)) or "",
                              spare = spareOf(mine) }
        end
    end
    for _, w in ipairs(GP.worn(me)) do
        local a = GP.armour(w.item)
        if a > 0 then
            local h = hers[w.loc]
            local b = h and GP.armour(h.item) or 0
            if a > b * 1.1 + 1 then
                out[#out + 1] = { slot = GP.slotWord(w.loc), mine = w.item, myName = w.name, myStat = pct(w.cond),
                                  her = h and h.item or nil, herName = h and h.name or W.nothing, herStat = h and pct(h.cond) or "",
                                  spare = spareOf(w.item) }
            end
        end
    end
    return out
end

-- ---------------------------------------------------------------- car and home (SolInventory's last finished scan)
function GP.sources(ammoSet)
    local out = {}
    local f = U.invLast
    local last = type(f) == "function" and f() or nil
    if type(last) ~= "table" then return out, nil end
    for _, r in ipairs(last.rows or {}) do
        if #out >= GP.MAX_SRC then break end
        if (r.where == "vehicle" or r.where == "house") and ((r.grp == "ammo" and ammoSet[r.type]) or r.grp == "weapons" or r.grp == "medical") then
            out[#out + 1] = { name = tostring(r.name or r.type), n = num(r.count) or 1, where = r.where, label = r.label }
        end
    end
    return out, last.t
end

-- ---------------------------------------------------------------- the whole model
-- st: { showMine, showSrc }. Pure data; the rows are made from it.
function GP.build(actor, me, st)
    st = st or {}
    local m = { actor = actor }
    if actor == nil then return m end
    m.hands = GP.hands(actor)
    local weapons = herWeapons(actor)
    m.prefs = GP.prefs(actor, weapons)
    local CP = mod("SolCombatPlans")
    m.plansOn = CP ~= nil and type(CP.on) == "function" and CP.on()
    if m.plansOn then local ok, p = pcall(CP.current, actor); m.plan = ok and p or nil end
    m.worn = GP.worn(actor)
    m.bag, m.bagN, m.herConts = GP.grouped(actor)
    -- swap candidates: clothing in her bag for a slot she wears
    local bySlot = {}
    for _, e in ipairs(m.bag.clothing) do
        local loc = locOf(e.item)
        if loc ~= "" then bySlot[loc] = bySlot[loc] or {}; local l = bySlot[loc]; l[#l + 1] = e.item end
    end
    for _, w in ipairs(m.worn) do w.alt = bySlot[w.loc] and bySlot[w.loc][1] or nil end
    local ammo = GP.herAmmo(actor, weapons)
    m.ammoSet = ammo
    if st.showMine and me ~= nil then
        m.mine, m.mineN, m.hisConts = GP.grouped(me, function(e)
            if e.kind == "weapons" or e.kind == "medical" then return true end
            if e.kind == "ammo" then return ammo[e.ft] == true end
            if e.kind == "clothing" then return GP.armour(e.item) > 0 end
            return false
        end)
    end
    if st.showSrc then m.src, m.srcAt = GP.sources(ammo) end
    m.like = me ~= nil and GP.likeMe(actor, me, m.worn, m.hands, weapons) or {}
    -- LF's quick actions: availability asked once per build, not per frame
    m.lf = {}
    for _, c in ipairs({ "open_inventory", "open_health", "bandage" }) do
        m.lf[c] = type(U.lfAvailable) == "function" and U.lfAvailable(c) == true
    end
    local rv = U.pageRow
    if type(rv) == "table" then m.health, m.loadW, m.loadCap = rv.health, num(rv.loadWeight), num(rv.loadCapacity) end
    return m
end

-- ---------------------------------------------------------------- signatures
local function contSig(c) return tostring(num((call(call(c, "getItems"), "size")))) .. ":" .. tostring(num((call(c, "getContentsWeight")))) end
function GP.invSig(who, containers)
    if who == nil then return "-" end
    local parts = { contSig(call(who, "getInventory")) }
    for _, c in ipairs(containers or {}) do parts[#parts + 1] = contSig(c) end
    parts[#parts + 1] = "w" .. tostring(num((call(call(who, "getWornItems"), "size"))))
    parts[#parts + 1] = tostring(call(who, "getPrimaryHandItem")) .. "/" .. tostring(call(who, "getSecondaryHandItem"))
    return table.concat(parts, "|")
end
function GP.handsSig(actor)
    if actor == nil then return "-" end
    local it = call(actor, "getPrimaryHandItem") or call(actor, "getSecondaryHandItem")
    local s = tostring(it)
    if it ~= nil then
        s = s .. ":" .. tostring(num((call(it, "getCurrentAmmoCount")))) .. ":" .. tostring(call(it, "isRoundChambered") == true)
            .. ":" .. tostring(call(it, "isJammed") == true) .. ":" .. tostring(num((call(it, "getCondition"))))
    end
    local CP = mod("SolCombatPlans")
    if CP and type(CP.on) == "function" and CP.on() then local ok, p = pcall(CP.current, actor); s = s .. "|" .. tostring(ok and p or "?") end
    return s
end

-- ---------------------------------------------------------------- rows (one flat list: the virtualised page)
-- name fitted to a width once per build (a code point table SolText draws as is)
local function fit(s, w, scale)
    local T = g("SolText")
    if type(T) ~= "table" or type(T.width) ~= "function" or type(T.codepoints) ~= "function" or type(T.rawWidth) ~= "function" then return s end
    local ok, tw = pcall(T.width, s, scale)
    if not ok or (num(tw) or 0) <= w then return s end
    local cps = T.codepoints(s)
    local lo, hi = 1, #cps
    while lo < hi do
        local mid = math.floor((lo + hi + 1) / 2)
        local part = {}
        for i = 1, mid do part[i] = cps[i] end
        part[#part + 1] = 46; part[#part + 1] = 46
        if T.rawWidth(part, scale) <= w then lo = mid else hi = mid - 1 end
    end
    local out = {}
    for i = 1, lo do out[i] = cps[i] end
    out[#out + 1] = 46; out[#out + 1] = 46
    return out
end
GP.fit = fit
local function textW(nb) return CW - nb * (BW + BGAP) - 10 end
local STATE_C = { ready = GOOD, empty = WARN, jammed = BAD, parts = BAD, broken = BAD }
function GP.rows(m, st)
    st = st or {}
    local rows, y = {}, 0
    local function add(r, h) r.y, r.h = y, h; rows[#rows + 1] = r; y = y + h end
    local function sec(t, btn) add({ kind = "sec", text = t, btns = btn and { btn } or nil }, H_SEC) end
    local function kv(k, v, c) add({ kind = "kv", text = k .. ": " .. v, c = c }, H_KV) end
    local function note(t) add({ kind = "note", text = t }, H_NOTE) end
    local function item(name, sub, btns, c, sel)
        local nb = btns and #btns or 0
        add({ kind = "item", name = fit(name, textW(nb), SCALE_TXT), sub = sub, btns = btns, c = c, sel = sel }, H_ITEM)
    end
    if m.actor == nil then note(W.no_sol); return rows, y end
    -- status line and LF's quick actions
    local line = W.health .. " " .. ((U.pageFmt and U.pageFmt.pct and m.health ~= nil) and U.pageFmt.pct(m.health) or "-")
    if m.loadW and m.loadCap then line = line .. "    " .. W.load .. " " .. int(m.loadW) .. " / " .. int(m.loadCap) end
    add({ kind = "kv", text = line, c = MUTED }, H_KV)
    add({ kind = "btns", btns = { { a = "lf", cmd = "open_inventory", t = W.b_bag, on = m.lf.open_inventory },
                                  { a = "lf", cmd = "open_health", t = W.b_med, on = m.lf.open_health },
                                  { a = "lf", cmd = "bandage", t = W.b_bandage, on = m.lf.bandage } } }, H_BTNS)
    -- 1. in her hands
    sec(W.sec_hands)
    local h = m.hands or { none = true }
    if h.none then note(W.none)
    else
        item(h.name, W.cond .. " " .. pct(h.cond), { { a = "use", it = h.item, t = W.b_use, on = true },
            h.ranged and { a = "reload", it = h.item, t = W.b_reload, on = h.canReload == true } or nil })
        if h.ranged then
            kv(W.in_gun, int(h.inGun) .. " " .. W.rounds, BLUE)
            kv(W.spare, int(h.mags) .. " " .. W.mags .. " (" .. int(h.magRounds) .. " " .. W.rounds .. ")    " .. W.loose .. ": " .. int(h.loose))
        end
        kv(W.state, W["st_" .. tostring(h.state)] or "-", STATE_C[h.state])
    end
    -- 2. favourites
    sec(W.sec_prefs)
    local p = m.prefs or { guns = {}, melee = {} }
    local function prefList(kindWord, cur, items, can, a)
        kv(kindWord, cur and nameOf(cur) or W.nothing, cur and GOLDC or MUTED)
        for _, it in ipairs(items) do
            if it ~= cur then item(nameOf(it), pct(condRatio(it)), { { a = a, it = it, t = W.b_choose, on = can } })
            end
        end
    end
    prefList(W.firearm, p.gun, p.guns, p.canGun, "pref_gun")
    prefList(W.melee, p.melee1, p.melee, p.canMelee, "pref_melee")
    -- 3. fighting plan
    sec(W.sec_plan)
    if not m.plansOn then note(W.plans_off)
    else
        for _, pl in ipairs(GP.PLANS) do
            add({ kind = "plan", id = pl.id, name = pl.name, line = fit(pl.line, CW - 20, SCALE_SUB), sel = (m.plan == pl.id) }, H_PLAN)
        end
    end
    -- 4. worn
    sec(W.sec_worn)
    if #(m.worn or {}) == 0 then note(W.nothing) end
    for _, w in ipairs(m.worn or {}) do
        item(w.name, GP.slotWord(w.loc) .. "   " .. pct(w.cond), { { a = "takeoff", it = w.item, t = W.b_off, on = true },
            w.alt and { a = "wear", it = w.alt, t = W.b_swap, on = true } or nil })
    end
    -- 5. her bag
    sec(W.sec_bag)
    if (m.bagN or 0) == 0 then note(W.bag_empty) end
    for _, k in ipairs(GP.GROUPS) do
        local gl = m.bag and m.bag[k] or {}
        if #gl > 0 then
            add({ kind = "group", text = W["g_" .. k] }, H_NOTE)
            for _, e in ipairs(gl) do
                local btns = { { a = "give_me", e = e, t = W.b_give_me, on = true } }
                if k == "weapons" then btns[2] = { a = "use", it = e.item, t = W.b_use, on = true }; btns[3] = { a = isGun(e.item) and "pref_gun" or "pref_melee", it = e.item, t = W.b_pref, on = isGun(e.item) and p.canGun or p.canMelee }
                elseif k == "clothing" then btns[2] = { a = "wear", it = e.item, t = W.b_wear, on = true } end
                local sub = (e.n > 1 and ("x" .. int(e.n)) or "") .. ((k == "weapons" or k == "clothing") and ("  " .. pct(e.cond)) or "")
                item(e.name, sub, btns)
            end
        end
    end
    -- 6. my bag (only when he asks)
    sec(W.sec_mine, { a = "toggle_mine", t = st.showMine and W.b_hide or W.b_show, on = true })
    if st.showMine then
        note(W.mine_hint)
        if (m.mineN or 0) == 0 then note(W.mine_empty) end
        for _, k in ipairs(GP.GROUPS) do
            local gl = m.mine and m.mine[k] or {}
            if #gl > 0 then
                add({ kind = "group", text = W["g_" .. k] }, H_NOTE)
                for _, e in ipairs(gl) do item(e.name, e.n > 1 and ("x" .. int(e.n)) or pct(e.cond), { { a = "give_sol", e = e, t = W.b_give_sol, on = true } }) end
            end
        end
    end
    -- car and home
    sec(W.sec_src, { a = "toggle_src", t = st.showSrc and W.b_hide or W.b_show, on = true })
    if st.showSrc then
        note(W.src_hint)
        if #(m.src or {}) == 0 then note(W.src_empty) end
        for _, r in ipairs(m.src or {}) do
            item(r.name, "x" .. int(r.n) .. "   " .. (r.where == "vehicle" and W.src_car or W.src_home) .. (r.label and ("  " .. tostring(r.label)) or ""), nil)
        end
    end
    -- 7. like me
    sec(W.sec_like)
    if #(m.like or {}) == 0 then note(W.like_none) end
    for _, l in ipairs(m.like or {}) do
        add({ kind = "pair", slot = l.slot, mine = fit(W.yours .. ": " .. l.myName .. " " .. l.myStat, CW / 2 - 8, SCALE_SUB),
              hers = fit(W.hers .. ": " .. l.herName .. " " .. l.herStat, CW / 2 - BW - 12, SCALE_SUB),
              btns = { { a = "give_one", it = l.spare, t = l.spare and W.b_give_one or W.no_spare, on = l.spare ~= nil } } }, H_PAIR)
    end
    add({ kind = "pad" }, 8)
    return rows, y
end

-- ---------------------------------------------------------------- the per-page state and the rebuild rule
function GP.state0(page)
    local s = page.gear
    if s == nil then s = { st = { showMine = false, showSrc = false }, sigAt = -1, builtAt = -1, dirty = true }; page.gear = s end
    return s
end
-- returns "full" / "hands" / nil (nothing changed)
function GP.ensure(page, actor, me)
    local s = GP.state0(page)
    local t = nowMs()
    if not s.dirty and s.rows ~= nil and s.actor == actor and t - s.sigAt < GP.SIG_MS and t >= s.sigAt then return nil end
    s.sigAt = t
    GP.stats.checks = GP.stats.checks + 1
    local function invSigs(m)
        local srcT = ""
        if s.st.showSrc and type(U.invLast) == "function" then local l = U.invLast(); srcT = tostring(type(l) == "table" and l.t or "") end
        local CP = mod("SolCombatPlans")
        local plansOn = CP ~= nil and type(CP.on) == "function" and CP.on()
        return GP.invSig(actor, m and m.herConts) .. "#" .. (s.st.showMine and GP.invSig(me, m and m.hisConts) or "-") .. "#" .. srcT .. "#" .. tostring(plansOn)
    end
    local hs = GP.handsSig(actor)
    local full = s.dirty or s.rows == nil or s.actor ~= actor or t - s.builtAt >= GP.MAX_AGE_MS or t < s.builtAt or invSigs(s.model) ~= s.sigInv
    local what
    if full then
        s.model = GP.build(actor, me, s.st)
        s.builtAt = t
        s.sigInv = invSigs(s.model)
        GP.stats.full = GP.stats.full + 1
        what = "full"
    elseif hs ~= s.sigHands then
        s.model.hands = GP.hands(actor)
        local CP = mod("SolCombatPlans")
        if s.model.plansOn and CP then local ok, p = pcall(CP.current, actor); s.model.plan = ok and p or nil end
        GP.stats.hands = GP.stats.hands + 1
        what = "hands"
    else
        return nil
    end
    s.sigHands = hs
    s.actor = actor
    s.dirty = false
    s.rows, s.H = GP.rows(s.model, s.st)
    return what
end

-- ---------------------------------------------------------------- drawing (only the visible rows)
local texCache = {}
local function tex(n) local t = texCache[n]; if t == nil then local f = g("getTexture"); t = type(f) == "function" and f("media/textures/SolUI/" .. n .. ".png") or false; texCache[n] = t end; return t or nil end
local function inside(x, y, r) return x >= r[1] and y >= r[2] and x < r[1] + r[3] and y < r[2] + r[4] end
local function text(ui, s, x, y, w, scale, align, c, a)
    local T = g("SolText")
    if type(T) ~= "table" then return end
    T.drawLine(ui, s, x, y, w, { scale = scale, align = align or "right", r = c and c[1] or 0.94, g = c and c[2] or 0.96, b = c and c[3] or 0.98, a = a or 1 })
end
local function box(ui, n, r, a) local t = tex(n); if t then ui:drawTextureScaled(t, r[1], r[2], r[3], r[4], a or 1, 1, 1, 1) end end
-- the first row whose bottom is below the top of the window (binary search on y)
function GP.firstVisible(rows, top)
    local lo, hi = 1, #rows
    while lo < hi do
        local mid = math.floor((lo + hi) / 2)
        local r = rows[mid]
        if r.y + r.h <= top then lo = mid + 1 else hi = mid end
    end
    return lo
end
local function hitRect(hits, r, h)
    local y1, y2 = math.max(r[2], CY), math.min(r[2] + r[4], CY + CH)
    if y2 <= y1 then return end
    h.r = { r[1], y1, r[3], y2 - y1 }
    hits[#hits + 1] = h
end
local function buttons(ui, hits, btns, x, y, mx, my, over)
    local k = 0
    for i = 1, 3 do
        local b = btns[i]
        if b ~= nil then
            local r = { x + k * (BW + BGAP), y, BW, 28 }
            box(ui, "pg_btn", r, b.on and 1 or 0.5)
            if b.on and over and inside(mx, my, r) then box(ui, "pg_btn_hover", r) end
            text(ui, b.t, r[1] + 2, r[2] + 3, r[3] - 4, SCALE_BTN, "center", nil, b.on and 1 or 0.45)
            if b.on then hitRect(hits, r, { b = b }) end
            k = k + 1
        end
    end
    return k
end
function GP.draw(ui, s, scroll, mx, my)
    local rows = s.rows or {}
    local hits = {}
    local over = ui.isMouseOver ~= nil and ui:isMouseOver() == true
    local drawn = 0
    local top = scroll
    local i = GP.firstVisible(rows, top)
    while i <= #rows do
        local r = rows[i]
        if r.y >= top + CH then break end
        local y = CY + r.y - scroll
        drawn = drawn + 1
        if r.kind == "sec" then
            text(ui, r.text, CX, y + 4, CW - 6, SCALE_SEC, "right", BLUE)
            if r.btns then buttons(ui, hits, r.btns, CX + 2, y + 2, mx, my, over) end
        elseif r.kind == "kv" then
            text(ui, r.text, CX + 6, y + 2, CW - 12, SCALE_TXT, "right", r.c)
        elseif r.kind == "note" then
            text(ui, r.text, CX + 6, y + 2, CW - 12, SCALE_SUB, "right", MUTED)
        elseif r.kind == "group" then
            text(ui, r.text, CX + 6, y + 2, CW - 12, SCALE_SUB, "right", GOLDC)
        elseif r.kind == "btns" then
            local n = #r.btns
            local bw = (CW - (n - 1) * 6) / n
            for k, b in ipairs(r.btns) do
                local rect = { CX + CW - k * bw - (k - 1) * 6, y + 2, bw, 32 }
                box(ui, "pg_btn", rect, b.on and 1 or 0.5)
                if b.on and over and inside(mx, my, rect) then box(ui, "pg_btn_hover", rect) end
                text(ui, b.t, rect[1], rect[2] + 3, rect[3], SCALE_TXT, "center", nil, b.on and 1 or 0.45)
                if b.on then hitRect(hits, rect, { b = b }) end
            end
        elseif r.kind == "item" then
            local rect = { CX, y + 1, CW, r.h - 3 }
            box(ui, "pg_btn", rect, 0.55)
            local nb = r.btns and buttons(ui, hits, r.btns, CX + 4, y + 6, mx, my, over) or 0
            local tx = CX + nb * (BW + BGAP) + 6
            text(ui, r.name, tx, y + 1, CW - (tx - CX) - 8, SCALE_TXT, "right", r.c)
            if r.sub and r.sub ~= "" then text(ui, r.sub, tx, y + 20, CW - (tx - CX) - 8, SCALE_SUB, "right", MUTED) end
        elseif r.kind == "plan" then
            local rect = { CX, y + 1, CW, r.h - 3 }
            box(ui, r.sel and "pg_list_sel" or "pg_btn", rect, r.sel and 1 or 0.6)
            if not r.sel and over and inside(mx, my, rect) then box(ui, "pg_btn_hover", rect) end
            text(ui, r.name, CX + 8, y + 1, CW - 16, SCALE_TXT, "right", r.sel and GOLDC or nil)
            text(ui, r.line, CX + 8, y + 21, CW - 16, SCALE_SUB, "right", MUTED)
            if not r.sel then hitRect(hits, rect, { b = { a = "plan", id = r.id, on = true } }) end
        elseif r.kind == "pair" then
            local rect = { CX, y + 1, CW, r.h - 3 }
            box(ui, "pg_btn", rect, 0.55)
            text(ui, r.slot, CX + CW / 2, y + 1, CW / 2 - 8, SCALE_SUB, "right", GOLDC)
            text(ui, r.mine, CX + CW / 2, y + 22, CW / 2 - 8, SCALE_SUB, "right", GOOD)
            local nb = buttons(ui, hits, r.btns, CX + 4, y + 9, mx, my, over)
            text(ui, r.hers, CX + nb * (BW + BGAP) + 6, y + 22, CW / 2 - nb * (BW + BGAP) - 12, SCALE_SUB, "right", MUTED)
        end
        i = i + 1
    end
    s.drawn = drawn
    s.hits = hits
    return drawn
end

-- ---------------------------------------------------------------- what the buttons do
local function say(actor, key)
    local line = GP.SAY[key]
    if actor == nil or line == nil then return false end
    local B = mod("SolBubble")
    if B and type(B.speak) == "function" then local ok, r = pcall(B.speak, actor, line, 5000); if ok and r == true then return true end end
    return false
end
GP.say = say
local function near(actor, me)
    local SC = LF()
    local Br = SC and SC.UIBridge
    if type(Br) ~= "table" or type(Br.validateNearbyActor) ~= "function" then return true end
    local ok, v = pcall(Br.validateNearbyActor, actor, me, Br.NEARBY_DISTANCE)
    return ok and v == true
end
local function touched(actor, inv)
    local SC = LF()
    if SC and SC.InventoryIndex and type(SC.InventoryIndex.touch) == "function" and actor ~= nil then pcall(SC.InventoryIndex.touch, actor) end
    local S = mod("SolItemStacks")
    if S and type(S.invalidate) == "function" then pcall(S.invalidate, inv) end
end
-- moves one entry (a whole stack for identical items) from one character to another; returns how many moved
function GP.move(from, to, e, gift)
    local gu = GU()
    if gu == nil or type(gu.transferItemVerified) ~= "function" or e == nil or e.item == nil then return 0 end
    local dst = call(to, "getInventory")
    local items = { e.item }
    if e.stack then
        items = {}
        for _, it in ipairs(list(call(call(from, "getInventory"), "getAllTypeRecurse", e.ft), GP.MAX_STACK_MOVE)) do
            if not equippedBy(from, it) then items[#items + 1] = it end
        end
    end
    local moved = 0
    for _, it in ipairs(items) do
        if not equippedBy(from, it) then
            local ok, done = pcall(gu.transferItemVerified, call(it, "getContainer"), dst, it)
            if ok and done == true then
                moved = moved + 1
                if gift and not e.stack then
                    local md = call(it, "getModData")
                    if type(md) == "table" then md.SC_GivenByPlayer = true end
                end
            end
        end
    end
    if moved > 0 and gift then
        local SC = LF()
        if SC and SC.Logistics and type(SC.Logistics.noteGift) == "function" then pcall(SC.Logistics.noteGift, to, e.item) end
    end
    touched(gift and to or from, call(from, "getInventory"))
    touched(nil, dst)
    return moved
end
local function equipOn(actor, me, it, kind)
    local SC = LF()
    local Br = SC and SC.UIBridge
    if type(Br) ~= "table" or type(Br.equipOnCompanion) ~= "function" then return false end
    local ok, r = pcall(Br.equipOnCompanion, actor, it, me, kind)
    return ok and r == true
end
function GP.act(page, b)
    local s = GP.state0(page)
    local actor = type(U.solActor) == "function" and U.solActor() or nil
    local me = player()
    local a = b.a
    local done = false
    if a == "lf" then
        if type(U.issueLF) == "function" then done = U.issueLF(b.cmd) == true end
    elseif a == "toggle_mine" then s.st.showMine = not s.st.showMine; done = true
    elseif a == "toggle_src" then s.st.showSrc = not s.st.showSrc; done = true
    elseif actor == nil then done = false
    elseif a == "plan" then
        local CP = mod("SolCombatPlans")
        if CP and type(CP.run) == "function" then local ok, r = pcall(CP.run, b.id); done = ok and r == true end
        if done then say(actor, b.id) end
    elseif a == "use" then done = equipOn(actor, me, b.it, "weapon")
    elseif a == "wear" then done = equipOn(actor, me, b.it, "wear")
    elseif a == "reload" then
        local MF = mod("SolMagFill")
        if MF and type(MF.orderFill) == "function" then local ok, r = pcall(MF.orderFill, actor, b.it); done = ok and r == true end
    elseif a == "pref_gun" then
        local G = mod("SolCombatEquipFallback")
        if G and type(G.markPreferred) == "function" then local ok, r = pcall(G.markPreferred, actor, b.it); done = ok and r == true end
    elseif a == "pref_melee" then
        local WP = mod("SolWeaponPick")
        if WP and type(WP.markMelee) == "function" then local ok, r = pcall(WP.markMelee, actor, b.it); done = ok and r == true end
    elseif a == "takeoff" then
        if near(actor, me) and call(actor, "isEquippedClothing", b.it) == true then
            call(actor, "removeWornItem", b.it)
            local te = g("triggerEvent"); if type(te) == "function" then pcall(te, "OnClothingUpdated", actor) end
            call(actor, "resetModelNextFrame")
            done = call(actor, "isEquippedClothing", b.it) ~= true
        end
    elseif a == "give_me" then
        if near(actor, me) then done = GP.move(actor, me, b.e, false) > 0; if done then say(actor, "give") end end
    elseif a == "give_sol" then
        if near(actor, me) then done = GP.move(me, actor, b.e, true) > 0 end
    elseif a == "give_one" then
        if near(actor, me) and b.it ~= nil then done = GP.move(me, actor, { item = b.it, ft = fullType(b.it) }, true) > 0 end
    end
    log("button " .. tostring(a) .. (b.id and (" " .. tostring(b.id)) or "") .. (b.it and (" " .. fullType(b.it)) or "") .. (b.e and (" " .. tostring(b.e.ft) .. " x" .. tostring(b.e.n)) or "") .. ": " .. tostring(done))
    s.dirty = true
    return done
end

-- ---------------------------------------------------------------- the page hooks (SolPages' class, wrapped once)
-- LF's widgets that the gear page replaces: the quick actions (its own row) and, with combat_plans on, the weapon priority
-- selector and its section (a plan sets that knob)
local DROP_CMD = { open_inventory = true, open_health = true, bandage = true }
function GP.filterItems(items)
    local CP = mod("SolCombatPlans")
    local plans = CP ~= nil and type(CP.on) == "function" and CP.on()
    local out = {}
    for i, it in ipairs(items or {}) do
        local drop = it.command ~= nil and DROP_CMD[it.command] == true
        if plans and it.command == "set_weapon_priority" then drop = true end
        if plans and it.kind == "section" then
            local nx = items[i + 1]
            if nx ~= nil and nx.command == "set_weapon_priority" then drop = true end
        end
        if not drop then out[#out + 1] = it end
    end
    return out
end
local function shiftTo(page, h)
    local old = page.cardH or 0
    if old == h then return end
    for _, r in ipairs(page.rows or {}) do r.y = r.y + (h - old) end
    page.contentH = (page.contentH or 0) + (h - old)
    page.cardH = h
end
function GP.installPage()
    local P = U.PageClass
    if type(P) ~= "table" or P.solGearPage then return false end
    P.solGearPage = true
    local baseRefresh = P.refresh
    P.refresh = function(self, force, follow)
        local before = self.lastBuild
        local r = baseRefresh(self, force, follow)
        if self.tab == "loadout" and GP.on() and (force or self.lastBuild ~= before) then   -- the base rebuilt LF's widgets
            local ok, err = pcall(function()
                self.items = GP.filterItems(self.items)
                self:layout()
                self.cardH = 0
                local s = GP.state0(self)
                shiftTo(self, s.H or 0)
                self.gearActive = true
            end)
            if not ok then log("refresh failed: " .. tostring(err)) end
        end
        return r
    end
    local baseCard = P.drawLoadoutCard
    P.drawLoadoutCard = function(self, mx, my)
        if not GP.on() then
            if self.gearActive then self.gearActive = false; self.gear = nil; self.lastBuild = 0 end   -- back to the old card on the next refresh
            return baseCard(self, mx, my)
        end
        if not self.gearActive then self.lastBuild = 0; return end                                 -- switched on live: the next refresh lays it out
        local t0 = nowMs()
        local ok, err = pcall(function()
            local s = GP.state0(self)
            GP.ensure(self, type(U.solActor) == "function" and U.solActor() or nil, player())
            shiftTo(self, s.H or 0)
            GP.draw(self, s, self.scroll or 0, mx, my)
        end)
        if not ok then log("draw failed: " .. tostring(err)) end
        if type(U.perfAdd) == "function" then U.perfAdd("gear_page", nowMs() - t0) end
    end
    local baseUp = P.onMouseUp
    P.onMouseUp = function(self, x, y)
        if self.tab == "loadout" and GP.on() and self.gearActive and not self.dragging and not self.dd and self.gear then
            for _, h in ipairs(self.gear.hits or {}) do
                if inside(x, y, h.r) then
                    local ok, err = pcall(GP.act, self, h.b)
                    if not ok then log("button failed: " .. tostring(err)) end
                    if h.b.a == "lf" then self:refresh(true) end
                    return true
                end
            end
        end
        return baseUp(self, x, y)
    end
    log("page ready")
    return true
end
function GP.install()
    if GP._installed then return end
    GP._installed = true
    local ok = GP.installPage()
    log("ready v" .. GP.VERSION .. " page=" .. tostring(ok) .. " (switch gear_page=" .. tostring(GP.on()) .. ")")
end
do local E = g("Events"); if E and E.OnGameStart and type(E.OnGameStart.Add) == "function" then E.OnGameStart.Add(GP.install) end end
return GP
