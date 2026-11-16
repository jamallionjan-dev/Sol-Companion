-- SolText.lua - Arabic + Latin text renderer for Project Zomboid UI (the game's fonts have no Arabic).
-- Shaping (contextual forms, lam-alef), right-to-left ordering with embedded Latin/number runs,
-- word wrapping, drawing from per-glyph textures (media/textures/SolText/gXXXX.png).
require "SolTextData"
SolText = SolText or {}
local T = SolText
local D = SolTextData
T.VERSION = "0.2.2"
local HEX = "0123456789ABCDEF"
local function hex4(n)
    local out = ""
    for _ = 1, 4 do local d = n % 16; out = string.sub(HEX, d + 1, d + 1) .. out; n = math.floor(n / 16) end
    return out
end
T.hex4 = hex4
local LAM, ZWJ = 0x644, 0x200D

-- ---------------------------------------------------------------- decoding
-- PROVEN IN GAME (2026-10-24): when Project Zomboid loads a Lua file, every non-ASCII character in it keeps only
-- its low 8 bits ("\\u0633\\u0648\\u0644" becomes "3HD"; the main menu then looked Arabic once ASCII was mapped back). So Sol's
-- Lua files are pure ASCII and every Arabic text in them is written as \uXXXX escapes (backslash, u, 4 hex).
-- codepoints() decodes those escapes; any other character uses string.byte (ASCII, or a real Java char > 255
-- coming from the game at runtime, e.g. typed text). UTF-8 bytes are decoded too (tests on standard Lua).
local HEXV = {}
for i = 0, 9 do HEXV[string.byte(tostring(i))] = i end
for i, ch in ipairs({ "a", "b", "c", "d", "e", "f" }) do HEXV[string.byte(ch)] = 9 + i; HEXV[string.byte(string.upper(ch))] = 9 + i end
local function hexAt(s, i)
    local v = 0
    for k = 0, 3 do
        local d = HEXV[string.byte(s, i + k) or 0]
        if d == nil then return nil end
        v = v * 16 + d
    end
    return v
end
-- the user wants digits as 0-9 everywhere: Arabic-Indic (U+0660-0669) and Persian (U+06F0-06F9) digits -> 0-9
function T.westernDigit(cp)
    if cp >= 0x660 and cp <= 0x669 then return cp - 0x660 + 48 end
    if cp >= 0x6F0 and cp <= 0x6F9 then return cp - 0x6F0 + 48 end
    return cp
end
function T.codepoints(s)
    if type(s) == "table" then return s end
    s = tostring(s or "")
    local out, i, n = {}, 1, string.len(s)
    while i <= n do
        local c = string.byte(s, i)
        if c == 92 and string.byte(s, i + 1) == 117 and i + 5 <= n and hexAt(s, i + 2) then
            out[#out + 1] = T.westernDigit(hexAt(s, i + 2)); i = i + 6
        elseif c > 255 or c < 0x80 then out[#out + 1] = T.westernDigit(c); i = i + 1
        else
            local need = (c >= 0xF0 and 3) or (c >= 0xE0 and 2) or (c >= 0xC0 and 1) or 0
            local cp, ok = c, need > 0 and i + need <= n
            if ok then
                cp = c % (2 ^ (6 - need))
                for k = 1, need do
                    local cc = string.byte(s, i + k)
                    if cc < 0x80 or cc > 0xBF then ok = false; break end
                    cp = cp * 64 + (cc - 0x80)
                end
            end
            if ok then out[#out + 1] = T.westernDigit(math.floor(cp)); i = i + need + 1 else out[#out + 1] = c; i = i + 1 end
        end
    end
    return out
end

-- one-time self check printed to console.txt (helps prove the decoding in the real game)
function T.selfCheck()
    local cps = T.codepoints("\\u0633\\u0648\\u0644 Sol")
    local ok = (cps[1] == 0x633 and cps[2] == 0x648 and cps[3] == 0x644 and cps[5] == 83)
    print("[SolText] decode escapes cps=" .. tostring(cps[1]) .. "," .. tostring(cps[2]) .. "," .. tostring(cps[3]) .. " ok=" .. tostring(ok))
    return ok
end

-- "\\u0628" escapes <-> code points (file channels stay pure ASCII whatever the file encoding)
function T.unescape(s)
    local out, i, n = {}, 1, string.len(s or "")
    while i <= n do
        local c = string.byte(s, i)
        if c == 92 and string.sub(s, i + 1, i + 1) == "u" and i + 5 <= n then
            out[#out + 1] = tonumber(string.sub(s, i + 2, i + 5), 16) or 63; i = i + 6
        elseif c == 92 and string.sub(s, i + 1, i + 1) == "\\" then out[#out + 1] = 92; i = i + 2
        else out[#out + 1] = c; i = i + 1 end
    end
    return out
end
function T.escape(cps)
    local parts = {}
    for _, cp in ipairs(cps) do
        if cp == 92 then parts[#parts + 1] = "\\\\"
        elseif cp >= 32 and cp < 127 then parts[#parts + 1] = string.char(cp)
        elseif cp == 10 or cp == 13 or cp == 9 then parts[#parts + 1] = " "
        else parts[#parts + 1] = "\\u" .. hex4(cp) end
    end
    return table.concat(parts)
end

-- ---------------------------------------------------------------- classification
local function isDiacritic(cp) return (cp >= 0x64B and cp <= 0x652) or cp == 0x670 or cp == ZWJ end
local function isArabic(cp) return (cp >= 0x600 and cp <= 0x6FF) or (cp >= 0xFB50 and cp <= 0xFEFF) end
local function isLatin(cp) return (cp >= 65 and cp <= 90) or (cp >= 97 and cp <= 122) or (cp >= 0xC0 and cp <= 0x24F) end
local function isDigit(cp) return (cp >= 48 and cp <= 57) or (cp >= 0x660 and cp <= 0x669) end
T.isArabic = isArabic

-- ---------------------------------------------------------------- shaping (logical order)
local function joinsNext(cp) local f = D.forms[cp]; return f ~= nil and f.ini ~= nil end
local function joinsPrev(cp) local f = D.forms[cp]; return f ~= nil and f.fin ~= nil end
function T.shape(cps)
    local clean = {}
    for _, cp in ipairs(cps) do if not isDiacritic(cp) then clean[#clean + 1] = cp end end
    local out, i = {}, 1
    while i <= #clean do
        local cp = clean[i]
        local prev = clean[i - 1]
        local prevJoins = prev ~= nil and joinsNext(prev)
        if cp == LAM and D.lamalef[clean[i + 1] or 0] then
            local lig = D.lamalef[clean[i + 1]]
            out[#out + 1] = (prevJoins and lig.fin) or lig.iso
            i = i + 2
        else
            local f = D.forms[cp]
            if f then
                local nextCp = clean[i + 1]
                local nextJoins = f.ini ~= nil and nextCp ~= nil and joinsPrev(nextCp)
                if nextCp == LAM and D.lamalef[clean[i + 2] or 0] then nextJoins = f.ini ~= nil end
                local g
                if prevJoins and nextJoins then g = f.med
                elseif prevJoins then g = f.fin
                elseif nextJoins then g = f.ini end
                out[#out + 1] = g or f.iso or cp
            else
                out[#out + 1] = cp
            end
            i = i + 1
        end
    end
    return out
end

-- ---------------------------------------------------------------- bidi (one line, shaped glyphs)
local MIRROR = { [40] = 41, [41] = 40, [91] = 93, [93] = 91, [123] = 125, [125] = 123, [60] = 62, [62] = 60, [0xAB] = 0xBB, [0xBB] = 0xAB }
local function strongDir(cp)
    if isArabic(cp) and not isDigit(cp) then return "R" end
    if isLatin(cp) or isDigit(cp) then return "L" end
    return nil
end
-- bidi v2 (a subset of Unicode UAX#9): numbers are WEAK, not strong. The old rule made every digit a strong left-to-right letter, so a line that
-- started with a number was laid out left to right, and a neutral between a number and Latin text was glued to them ("48.9/55, 93fordElgin").
-- Here: the paragraph direction comes from the first LETTER; a number after Arabic letters is an Arabic number (it reads left to right but counts
-- as right-to-left for the punctuation around it); "52.2" and "3,000" stay one number; a "%" or "$" next to a number belongs to it; the neutrals
-- between two runs of the same direction take that direction, else the paragraph's. Levels and reordering follow rules I1, I2 and L2.
local function btype(cp)
    if isDigit(cp) then return "EN" end
    if isArabic(cp) then return "AL" end
    if isLatin(cp) then return "L" end
    if cp == 43 or cp == 45 then return "ES" end
    if cp == 35 or cp == 36 or cp == 37 or cp == 0xA2 or cp == 0xA3 or cp == 0xB0 then return "ET" end
    if cp == 44 or cp == 46 or cp == 47 or cp == 58 or cp == 0xA0 then return "CS" end
    return "N"
end
function T.baseDir(cps)
    local sawDigit = false
    for _, cp in ipairs(cps) do
        if isDigit(cp) then sawDigit = true
        elseif isArabic(cp) then return "R"
        elseif isLatin(cp) then return "L" end
    end
    return sawDigit and "L" or "R"          -- a line of digits only keeps reading left to right
end
-- returns glyphs in visual (left-to-right drawing) order
function T.visual(glyphs, base)
    base = base or T.baseDir(glyphs)
    local n = #glyphs
    local out = {}
    if n == 0 then return out end
    local ty = {}
    for i = 1, n do ty[i] = btype(glyphs[i]) end
    local sos = (base == "R") and "R" or "L"
    -- W2: a number after Arabic letters is an Arabic number
    local last = sos
    for i = 1, n do
        local t = ty[i]
        if t == "L" or t == "AL" then last = t
        elseif t == "EN" and last == "AL" then ty[i] = "AN" end
    end
    -- W4: one separator between two numbers of the same kind belongs to the number
    for i = 2, n - 1 do
        local a, t, b = ty[i - 1], ty[i], ty[i + 1]
        if t == "ES" and a == "EN" and b == "EN" then ty[i] = "EN"
        elseif t == "CS" and (a == "EN" or a == "AN") and b == a then ty[i] = a end
    end
    -- W5: terminators next to a European number belong to it
    local i = 1
    while i <= n do
        if ty[i] == "ET" then
            local j = i
            while j + 1 <= n and ty[j + 1] == "ET" do j = j + 1 end
            if (i > 1 and ty[i - 1] == "EN") or (j < n and ty[j + 1] == "EN") then for k = i, j do ty[k] = "EN" end end
            i = j + 1
        else
            i = i + 1
        end
    end
    -- W6: what is left of separators and terminators is neutral
    for k = 1, n do if ty[k] == "ES" or ty[k] == "ET" or ty[k] == "CS" then ty[k] = "N" end end
    -- W7: a European number after left-to-right letters is left-to-right
    last = sos
    for k = 1, n do
        local t = ty[k]
        if t == "L" or t == "AL" then last = t
        elseif t == "EN" and last == "L" then ty[k] = "L" end
    end
    -- N0: a pair of brackets takes the direction of what it encloses (the paragraph's when it encloses that direction, else the opposite one when the text before it is of that direction too)
    local function infl(t) if t == "L" then return "L" end if t == "R" or t == "AL" or t == "EN" or t == "AN" then return "R" end return nil end
    local CLOSE = { [40] = 41, [91] = 93, [123] = 125, [0xAB] = 0xBB }
    local stack, pairsList = {}, {}
    for p = 1, n do
        local g = glyphs[p]
        if ty[p] == "N" then
            if CLOSE[g] then stack[#stack + 1] = { at = p, want = CLOSE[g] }
            else
                for s2 = #stack, 1, -1 do
                    if stack[s2].want == g then
                        pairsList[#pairsList + 1] = { stack[s2].at, p }
                        for _ = #stack, s2, -1 do stack[#stack] = nil end
                        break
                    end
                end
            end
        end
    end
    table.sort(pairsList, function(a, b) return a[1] < b[1] end)
    for _, pr in ipairs(pairsList) do
        local a, b = pr[1], pr[2]
        local sawE, sawO = false, false
        for p = a + 1, b - 1 do
            local d = infl(ty[p])
            if d == base then sawE = true elseif d then sawO = true end
        end
        local dir = nil
        if sawE then dir = base
        elseif sawO then
            local before = base
            for p = a - 1, 1, -1 do local d = infl(ty[p]); if d then before = d; break end end
            if before ~= base then dir = before else dir = base end
        end
        if dir then ty[a] = dir; ty[b] = dir end
    end
    -- N1 / N2: neutrals between runs of one direction take it (numbers count as right-to-left here), else the paragraph's
    local k = 1
    while k <= n do
        if ty[k] == "N" then
            local j = k
            while j + 1 <= n and ty[j + 1] == "N" do j = j + 1 end
            local before = (k > 1) and infl(ty[k - 1]) or base
            local after = (j < n) and infl(ty[j + 1]) or base
            local d = (before == after) and before or base
            for m = k, j do ty[m] = d end
            k = j + 1
        else
            k = k + 1
        end
    end
    -- I1 / I2: embedding levels
    local lvl = {}
    for m = 1, n do
        local t = ty[m]
        local isR = (t == "R" or t == "AL")
        if base == "L" then
            if t == "L" then lvl[m] = 0 elseif isR then lvl[m] = 1 else lvl[m] = 2 end
        else
            if isR then lvl[m] = 1 else lvl[m] = 2 end
        end
    end
    -- L2: reverse every run at or above each level, from the highest down to the lowest odd one
    local order = {}
    local maxLevel, minOdd = 0, 99
    for m = 1, n do
        order[m] = m
        if lvl[m] > maxLevel then maxLevel = lvl[m] end
        if lvl[m] % 2 == 1 and lvl[m] < minOdd then minOdd = lvl[m] end
    end
    for level = maxLevel, minOdd, -1 do
        local p = 1
        while p <= n do
            if lvl[order[p]] >= level then
                local q = p
                while q + 1 <= n and lvl[order[q + 1]] >= level do q = q + 1 end
                local a, b = p, q
                while a < b do order[a], order[b] = order[b], order[a]; a = a + 1; b = b - 1 end
                p = q + 1
            else
                p = p + 1
            end
        end
    end
    for m = 1, n do
        local idx = order[m]
        local g = glyphs[idx]
        if lvl[idx] % 2 == 1 then g = MIRROR[g] or g end       -- L4: mirror at odd levels
        out[m] = g
    end
    return out
end

-- ---------------------------------------------------------------- metrics and wrapping
local function advOf(g) return D.adv[g] or D.adv[63] or 10 end
function T.rawWidth(cps, scale)
    local glyphs = T.shape(T.codepoints(cps))
    local w = 0
    for _, g in ipairs(glyphs) do w = w + advOf(g) end
    return w * (scale or 1)
end
function T.width(cps, scale)
    return T.prepared(cps, nil).total * (scale or 1)      -- T.prepared is defined with the drawing code below
end
function T.lineHeight(scale) return D.lh * (scale or 1) end

-- logical code-point lines that fit maxW (by words; very long words are cut)
local wrapCache, wrapCount = {}, 0
function T.wrap(cps, maxW, scale)
    local wk = (type(cps) == "table" and tostring(cps) or tostring(cps)) .. "|" .. tostring(maxW) .. "|" .. tostring(scale)
    local hit = wrapCache[wk]
    if hit then return hit end
    local lines = T.wrapRaw(cps, maxW, scale)
    wrapCount = wrapCount + 1
    if wrapCount > 800 then wrapCache = {}; wrapCount = 1 end
    wrapCache[wk] = lines
    return lines
end
function T.wrapRaw(cps, maxW, scale)
    cps = T.codepoints(cps)
    local words, cur = {}, {}
    for _, cp in ipairs(cps) do
        if cp == 10 then words[#words + 1] = cur; words[#words + 1] = "\n"; cur = {}
        elseif cp == 32 then if #cur > 0 then words[#words + 1] = cur end; cur = {}
        else cur[#cur + 1] = cp end
    end
    if #cur > 0 then words[#words + 1] = cur end
    local lines, line = {}, {}
    local function flush() lines[#lines + 1] = line; line = {} end
    for _, w in ipairs(words) do
        if w == "\n" then flush()
        else
            local cand = {}
            for _, cp in ipairs(line) do cand[#cand + 1] = cp end
            if #cand > 0 then cand[#cand + 1] = 32 end
            for _, cp in ipairs(w) do cand[#cand + 1] = cp end
            if #line == 0 or T.rawWidth(cand, scale) <= maxW then line = cand
            else flush(); line = w end
            while T.rawWidth(line, scale) > maxW and #line > 1 do
                local cut = #line
                while cut > 1 and T.rawWidth({ unpack(line, 1, cut) }, scale) > maxW do cut = cut - 1 end
                lines[#lines + 1] = { unpack(line, 1, cut) }
                line = { unpack(line, cut + 1) }
            end
        end
    end
    if #line > 0 or #lines == 0 then flush() end
    return lines
end

-- ---------------------------------------------------------------- drawing
local texCache = {}
local function glyphTex(g)
    local t = texCache[g]
    if t == nil then t = getTexture("media/textures/SolText/g" .. hex4(g) .. ".png") or false; texCache[g] = t end
    return t or nil
end
-- draw one logical line; align = "right" | "left" | "center" inside [x, x + w]
-- prepared lines are cached: shaping + bidi + width were redone for every label on every frame
local lineCache, lineCount = {}, 0
local function keyOf(cps) if type(cps) == "table" then return cps end return tostring(cps) end
local function prepared(cps, dir)
    local k = keyOf(cps)
    local byDir = lineCache[k]
    local e = byDir and byDir[dir or "auto"]
    if e then return e end
    local glyphs = T.shape(T.codepoints(cps))
    local base = dir or T.baseDir(glyphs)
    local vis = T.visual(glyphs, base)
    local total = 0
    for _, g in ipairs(vis) do total = total + advOf(g) end
    e = { vis = vis, base = base, total = total }
    if not byDir then
        lineCount = lineCount + 1
        if lineCount > 1500 then lineCache = {}; lineCount = 1 end
        byDir = {}; lineCache[k] = byDir
    end
    byDir[dir or "auto"] = e
    return e
end
T.prepared = prepared
function T.drawLine(ui, cps, x, y, w, opts)
    opts = opts or {}
    local scale = opts.scale or 1
    local pe = prepared(cps, opts.dir)
    local base, vis = pe.base, pe.vis
    local total = pe.total * scale
    local align = opts.align or (base == "R" and "right" or "left")
    local px = x
    if align == "right" then px = x + w - total elseif align == "center" then px = x + (w - total) / 2 end
    local r, gg, b, a = opts.r or 1, opts.g or 1, opts.b or 1, opts.a or 1
    for _, g in ipairs(vis) do
        local adv = advOf(g) * scale
        if g ~= 32 then
            local t = glyphTex(g)
            if t then
                ui:drawTextureScaled(t, math.floor(px - D.pad * scale + 0.5), math.floor(y + 0.5),
                    t:getWidth() * scale, t:getHeight() * scale, a, r, gg, b)
            end
        end
        px = px + adv
    end
    return total
end
-- draw wrapped text, returns the height used
function T.draw(ui, text, x, y, w, opts)
    opts = opts or {}
    local scale = opts.scale or 1
    local lines = T.wrap(text, w, scale)
    local lh = D.lh * scale * (opts.lineGap or 0.82)
    local base = opts.dir or T.baseDir(T.codepoints(text))
    for i, line in ipairs(lines) do
        T.drawLine(ui, line, x, y + (i - 1) * lh, w, { scale = scale, dir = base, align = opts.align, r = opts.r, g = opts.g, b = opts.b, a = opts.a })
    end
    return #lines * lh
end
function T.height(text, w, opts)
    opts = opts or {}
    local scale = opts.scale or 1
    return #T.wrap(text, w, scale) * D.lh * scale * (opts.lineGap or 0.82)
end
